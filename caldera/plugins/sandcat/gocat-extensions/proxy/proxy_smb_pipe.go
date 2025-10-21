//go:build windows
// +build windows

/*
 * This file contains implementations for a P2P client (SmbPipeAPI) and P2P receiver (SmbPipeReceiver)
 * Agents using SMB pipes to communicate upstream will do so using the P2P client, and the upstream agents receiving
 * the SMB pipe messages will need to have the SMB P2P receivers running. An agent can use both the SmbPipeAPI p2p
 * client and the SmbPipeReceiver at the same time, in which case it would act as an SMB forwarder, using SMB for
 * both upstream and downstream communications.
 *
 * Each agent using SMB Pipe P2P will have one SmbPipeAPI struct that implements the contact.Contact interface to
 * provide full communication between the agent and the upstream C2 (get payloads, get instructions, etc).
 * The SMB pipe API client assumes that it is talking to an SMB Pipe p2p receiver that knows how to process the
 * client messages accordingly. When using the SMB Pipe P2P client, the agent will generate a random pipe path
 * to listen on (a mailbox pipe) - this pipe will receive response messages when the agent sends requests upstream
 * for itself.
 * But if an agent has downstream agents to forward messages for, those requests will also flow through the same
 * SMB pipe API client. Thus, the agent will open up new random mailbox pipes for each downstream agent that it is
 * servicing, and the SmbPipeAPI struct will keep track of which mailbox pipe is for which downstream agent so that
 * it can forward the responses appropriately.
 *
 * Each agent listening for SMB pipe P2P messages will activate an SMB pipe receiver that listens on a particular
 * pipe path. This pipe path is randomly generated using the hostname as the seed, so that a client agent
 * can calculate the pipe path for its upstream agent if it only knows the hostname.
 * As the SMB pipe receiver gets messages from downstream
 * agents, it will forward the message upstream and return the response.  Each upstream P2P message via SMB pipes
 * must contain the requesting agent's mailbox pipe path for response messages, so the P2P receiver knows where to send
 * the responses.
 */

package proxy

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"regexp"
	"sync"
	"time"

	"github.com/mitre/gocat/contact"
	"github.com/mitre/gocat/output"
)

var (
	// lock for SMBPipeAPI client when editing the ReturnMailBoxPipePaths and ReturnMailBoxListeners for
	// API users (this agent and any downstream agents reaching out to this agent via P2P)
	// Needed because multiple go routines will use the same SmbPipeAPI if the agent is acting
	// as a receiver for multiple client agents, and the upstream comms for the receiver is type SmbPipeAPI.
	apiClientMutex sync.Mutex

	// For writes to the upstream pipe.
	upstreamPipeLock sync.Mutex

	protocolName = "SmbPipe"
)

// SmbPipeAPI communicates through SMB named pipes. Implements the Contact interface.
type SmbPipeAPI struct {
	// Maps agent paws to full pipe paths for receiving forwarded responses on their behalf.
	returnMailBoxPipePaths map[string]string

	// Maps agent paws to Listener objects for the corresponding local pipe paths.
	returnMailBoxListeners map[string]net.Listener
	name                   string
	upstreamDestAddr       string // agent's upstream dest addr
}

//PipeReceiver forwards data received from SMB pipes to the upstream destination. Implements the P2pReceiver interface
type SmbPipeReceiver struct {
	agentPaw             string // paw of agent running this receiver
	receiverName         string
	mainPipeName         string
	localMainPipePath    string           // full pipe path from a local perrspective. \\.\pipe\<pipename>
	externalMainPipePath string           // full pipe path from an external perspective. \\hostname\pipe\<pipename>
	upstreamComs         *contact.Contact // Contact implementation to handle upstream communication.
	listener             net.Listener     // Listener object for this receiver.
	agentServer          *string          // refers to agent's current server value
	waitgroup            *sync.WaitGroup
	receiverContext      context.Context
	receiverCancelFunc   context.CancelFunc
}

func init() {
	contact.CommunicationChannels[protocolName] = &SmbPipeAPI{
		make(map[string]string),
		make(map[string]net.Listener),
		protocolName,
		"",
	}
	P2pReceiverChannels[protocolName] = &SmbPipeReceiver{}
}

/*
 * SmbPipeReceiver Implementation (implements P2pReceiver interface).
 */

func (s *SmbPipeReceiver) InitializeReceiver(agentServer *string, upstreamComs *contact.Contact, waitgroup *sync.WaitGroup) error {
	hostname, err := os.Hostname()
	if err != nil {
		return err
	}
	s.mainPipeName = getMainPipeName(hostname)
	s.localMainPipePath = "\\\\.\\pipe\\" + s.mainPipeName
	s.externalMainPipePath = "\\\\" + hostname + "\\pipe\\" + s.mainPipeName
	s.listener, err = listenPipeFullAccess(s.localMainPipePath)
	if err != nil {
		return err
	}
	s.agentServer = agentServer
	s.upstreamComs = upstreamComs
	s.receiverName = protocolName
	s.waitgroup = waitgroup
	s.receiverContext, s.receiverCancelFunc = context.WithTimeout(context.Background(), 5*time.Second)
	return nil
}

// Listen on agent's main pipe for client connection. This method must be run as a go routine.
func (s *SmbPipeReceiver) RunReceiver() {
	output.VerbosePrint(fmt.Sprintf("[*] Starting SMB pipe proxy receiver on local pipe path %s", s.localMainPipePath))
	output.VerbosePrint(fmt.Sprintf("[*] SMB pipe proxy receiver has upstream contact type %s", (*s.upstreamComs).GetName()))
	s.startReceiverHelper()
}

// Update paw of agent running this receiver.
func (s *SmbPipeReceiver) UpdateAgentPaw(newPaw string) {
	s.agentPaw = newPaw
}

func (s *SmbPipeReceiver) Terminate() {
	defer func() {
		s.waitgroup.Done()
		s.receiverCancelFunc()
	}()
	if err := s.listener.Close(); err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Error when closing pipe listener: %s", err.Error()))
	}
}

func (s *SmbPipeReceiver) GetReceiverAddresses() []string {
	addrList := make([]string, 1)
	addrList[0] = s.externalMainPipePath
	return addrList
}

// Helper method for StartReceiver.
func (s *SmbPipeReceiver) startReceiverHelper() {
	// Whenever a client connects to pipe with a request, process the request using a go routine.
	for {
		totalData, err := fetchDataFromPipe(s.listener)
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error with reading client input: %s", err.Error()))
			continue
		}
		message, err := bytesToP2pMsg(totalData)
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error converting data to p2p message: %s", err.Error()))
		} else if msgIsEmpty(message) {
			output.VerbosePrint("[!] Error - downstream agent sent an empty P2P message.")
			continue
		}
		switch message.MessageType {
		case GET_INSTRUCTIONS:
			go s.forwardGetBeaconBytes(message)
		case GET_PAYLOAD_BYTES:
			go s.forwardPayloadBytesDownload(message)
		case SEND_EXECUTION_RESULTS:
			go s.forwardSendExecResults(message)
		case SEND_FILE_UPLOAD_BYTES:
			go s.forwardSendUploadBytes(message)
		default:
			output.VerbosePrint(fmt.Sprintf("[!] ERROR: invalid instruction type for receiver-bound p2p message: %d", message.MessageType))
		}
	}
}

// Pass the beacon request to the upstream destination, and return the response.
func (s *SmbPipeReceiver) forwardGetBeaconBytes(message P2pMessage) {
	// Message payload contains profile to send upstream
	clientProfile := make(map[string]interface{})
	if err := json.Unmarshal(message.Payload, &clientProfile); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error extracting client profile from p2p message: %s", err.Error()))
		return
	}
	clientProfile["server"] = *s.agentServer

	// Update peer proxy chain information to indicate that the beacon is going through this agent.
	updatePeerChain(clientProfile, s.agentPaw, s.externalMainPipePath, s.receiverName)
	output.VerbosePrint(fmt.Sprintf("[*] Forwarding instructions request on behalf of paw %s", message.SourcePaw))
	response := (*s.upstreamComs).GetBeaconBytes(clientProfile)

	// Connect to client mailbox to send response back to client.
	if len(message.SourceAddress) > 0 {
		pipeMsgData, err := buildP2pMsgBytes("", RESPONSE_INSTRUCTIONS, response, "")
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error building response message for client: %s", err.Error()))
			return
		}
		if _, err = sendDataToPipe(message.SourceAddress, pipeMsgData); err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error sending response message to client: %s", err.Error()))
			return
		}
		output.VerbosePrint(fmt.Sprintf("[*] Sent beacon response to paw %s", message.SourcePaw))
	} else {
		output.VerbosePrint(fmt.Sprintf("[-] ERROR. P2p message from client did not specify a return address."))
	}
}

// Pass the payload bytes download request to the upstream destination, and return the response.
func (s *SmbPipeReceiver) forwardPayloadBytesDownload(message P2pMessage) {
	// Message payload contains client profile and requested payload name.
	var requestInfo payloadRequestInfo
	if err := json.Unmarshal(message.Payload, &requestInfo); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error extracting payload request info from p2p message: %s", err.Error()))
		return
	}

	// Get upstream response, which contains payload data and name, and forward response to client.
	if requestInfo.Profile == nil {
		output.VerbosePrint("[!] Error - client did not send profile information in payload request.")
		return
	}
	if len(requestInfo.PayloadName) == 0 {
		output.VerbosePrint("[!] Error - client did not send payload name in payload request.")
		return
	}

	requestInfo.Profile["server"] = *s.agentServer
	output.VerbosePrint(fmt.Sprintf("[*] Forwarding payload bytes request for payload %s on behalf of paw %s", requestInfo.PayloadName, message.SourcePaw))
	payloadData, payloadName := (*s.upstreamComs).GetPayloadBytes(requestInfo.Profile, requestInfo.PayloadName)
	respInfo := payloadResponseInfo{
		PayloadData: payloadData,
		PayloadName: payloadName,
	}
	respData, err := json.Marshal(respInfo)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error marshaling payload response info: %s", err.Error()))
		return
	}
	if len(message.SourceAddress) > 0 {
		pipeMsgData, err := buildP2pMsgBytes("", RESPONSE_PAYLOAD_BYTES, respData, "")
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error building payload response message: %s", err.Error()))
			return
		}
		sendDataToPipe(message.SourceAddress, pipeMsgData)
		output.VerbosePrint(fmt.Sprintf("[*] Sent %d payload bytes for payload %s to client paw %s", len(payloadData), payloadName, message.SourcePaw))
	} else {
		output.VerbosePrint(fmt.Sprintf("[-] ERROR. P2p message from client did not specify a return address."))
	}
}

func (s *SmbPipeReceiver) forwardSendExecResults(message P2pMessage) {
	// message payload contains client profile and result info.
	clientProfile := make(map[string]interface{})
	if err := json.Unmarshal(message.Payload, &clientProfile); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error extracting execution result info from p2p message: %s", err.Error()))
		return
	}
	resultInfo, ok := clientProfile["results"]
	if !ok {
		output.VerbosePrint("[!] Error. Client did not include execution results.")
		return
	}
	result := resultInfo.([]interface{})[0]
	clientProfile["server"] = *s.agentServer

	// Send execution results upstream. No response will be sent to client.
	output.VerbosePrint(fmt.Sprintf("[*] Forwarding execution results on behalf of paw %s", message.SourcePaw))
	(*s.upstreamComs).SendExecutionResults(clientProfile, result.(map[string]interface{}))
}

func (s *SmbPipeReceiver) forwardSendUploadBytes(message P2pMessage) {
	if len(message.SourceAddress) == 0 {
		output.VerbosePrint(fmt.Sprintf("[-] ERROR. P2p message from client did not specify a return address."))
		return
	}

	// Message payload contains client profile and file upload name/data.
	var requestInfo uploadRequestInfo
	if err := json.Unmarshal(message.Payload, &requestInfo); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error extracting file upload request info from p2p message: %s", err.Error()))
		s.sendUploadResultsToClient(message.SourceAddress, "", false)
		return
	}
	if len(requestInfo.UploadName) == 0 {
		output.VerbosePrint("[!] Error - client did not send upload name in upload request.")
		s.sendUploadResultsToClient(message.SourceAddress, "", false)
		return
	}
	if requestInfo.UploadData == nil {
		output.VerbosePrint("[!] Error. Client did not include file data for upload.")
		s.sendUploadResultsToClient(message.SourceAddress, requestInfo.UploadName, false)
		return
	}
	requestInfo.Profile["server"] = *s.agentServer
	output.VerbosePrint(fmt.Sprintf("[*] Forwarding upload request for file %s on behalf of paw %s", requestInfo.UploadName, message.SourcePaw))
	successfulUpload := true
	if err := (*s.upstreamComs).UploadFileBytes(requestInfo.Profile, requestInfo.UploadName, requestInfo.UploadData); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error uploading file bytes for client: %s", err.Error()))
		successfulUpload = false
	}

	// Send response to client
	s.sendUploadResultsToClient(message.SourceAddress, requestInfo.UploadName, successfulUpload)
}

func (s *SmbPipeReceiver) sendUploadResultsToClient(address string, uploadName string, successful bool) {
	respInfo := uploadResponseInfo{
		UploadName: uploadName,
		Result:     successful,
	}
	respData, err := json.Marshal(respInfo)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error marshaling upload response info: %s", err.Error()))
		return
	}
	pipeMsgData, err := buildP2pMsgBytes("", RESPONSE_FILE_UPLOAD, respData, "")
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error building upload response message: %s", err.Error()))
		return
	}
	sendDataToPipe(address, pipeMsgData)
}

/*
 * SmbPipeAPI implementation (implements contact.Contact interface)
 */

func (s *SmbPipeAPI) GetBeaconBytes(profile map[string]interface{}) []byte {
	requestingPaw := getPawFromProfile(profile)
	mailBoxPipePath, mailBoxListener, err := s.fetchClientMailBoxInfo(requestingPaw, true)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error obtaining mailbox and listener for client paw %s: %s", requestingPaw, err.Error()))
		return nil
	}
	output.VerbosePrint(fmt.Sprintf("[*] P2P Client: going to fetch beacon bytes for paw %s", requestingPaw))

	// Send instruction request
	payload, err := json.Marshal(profile)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error marshaling profile: %s", err.Error()))
		return nil
	}
	upstreamPipeLock.Lock()
	err = sendRequestToUpstreamPipe(s.upstreamDestAddr, requestingPaw, GET_INSTRUCTIONS, payload, mailBoxPipePath)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error sending beacon request to upstream dest: %s", err.Error()))
		upstreamPipeLock.Unlock()
		return nil
	}

	// Process response.
	respMessage, err := getResponseMessage(mailBoxListener)
	upstreamPipeLock.Unlock()
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error obtaining instruction response from upstream dest: %s", err.Error()))
		return nil
	} else if msgIsEmpty(respMessage) {
		output.VerbosePrint("[!] Error. Empty message from upstream dest.")
		return nil
	} else if respMessage.MessageType != RESPONSE_INSTRUCTIONS {
		output.VerbosePrint(fmt.Sprintf("[!] Error: upstream dest sent invalid response type for getting instructions: %d", respMessage.MessageType))
		return nil
	}
	// Message payload contains beacon bytes.
	return respMessage.Payload
}

// Will obtain the payload bytes in memory to be written to disk later by caller.
func (s *SmbPipeAPI) GetPayloadBytes(profile map[string]interface{}, payload string) ([]byte, string) {
	if _, ok := profile["paw"]; !ok {
		output.VerbosePrint("[!] Error - paw not included in profile for payload request.")
		return nil, ""
	}
	paw := profile["paw"].(string)

	// Set up mailbox pipe and listener if needed.
	mailBoxPipePath, mailBoxListener, err := s.fetchClientMailBoxInfo(paw, true)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error obtaining mailbox and listener for client paw %s: %s", paw, err.Error()))
		return nil, ""
	}

	// Download payload bytes for a single payload. Create SMB Pipe message with
	// payload as a map[string]interface{} specifying the file name and agent profile.
	requestInfo := payloadRequestInfo{
		PayloadName: payload,
		Profile:     profile,
	}
	msgPayload, err := json.Marshal(requestInfo)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error marshalling payload request info: %s", err.Error()))
		return nil, ""
	}
	output.VerbosePrint(fmt.Sprintf("[*] P2p Client Downloading new payload: %s", payload))
	upstreamPipeLock.Lock()
	err = sendRequestToUpstreamPipe(s.upstreamDestAddr, paw, GET_PAYLOAD_BYTES, msgPayload, mailBoxPipePath)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error sending payload request to upstream dest: %s", err.Error()))
		upstreamPipeLock.Unlock()
		return nil, ""
	}

	// Process response.
	respMessage, err := getResponseMessage(mailBoxListener)
	upstreamPipeLock.Unlock()
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error obtaining payload response from upstream dest: %s", err.Error()))
		return nil, ""
	} else if msgIsEmpty(respMessage) {
		output.VerbosePrint("[!] Error: upstream dest sent back empty message for payload request.")
	} else if respMessage.MessageType != RESPONSE_PAYLOAD_BYTES {
		output.VerbosePrint(fmt.Sprintf("[!] Error: upstream dest sent invalid response type for getting getting payload bytes: %d", respMessage.MessageType))
		return nil, ""
	}

	// Message payload contains payload bytes and true filename.
	var responseInfo payloadResponseInfo
	if err = json.Unmarshal(respMessage.Payload, &responseInfo); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error unmarshalling payload response info: %s", err.Error()))
		return nil, ""
	}
	if len(responseInfo.PayloadName) == 0 {
		output.VerbosePrint("[!] Error. Upstream dest did not send payload name.")
		return nil, ""
	}
	return responseInfo.PayloadData, responseInfo.PayloadName
}

// Check if current upstream destination is a full pipe path. If not, return config with new pipe path using
// current upstream destination value and default generated pipe name.
func (s *SmbPipeAPI) C2RequirementsMet(profile map[string]interface{}, criteria map[string]string) (bool, map[string]string) {
	if len(s.upstreamDestAddr) == 0 {
		output.VerbosePrint("[!] Upstream destination address not yet set for SMB Pipe contact.")
		return false, nil
	}
	match, err := regexp.MatchString(`^\\\\[^\\]+\\pipe\\[^\\]+$`, s.upstreamDestAddr)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Regular expression error: %s", err.Error()))
		return false, nil
	} else if !match {
		config := make(map[string]string)
		config["upstreamDest"] = "\\\\" + s.upstreamDestAddr + "\\pipe\\" + getMainPipeName(s.upstreamDestAddr)
		return true, config
	}
	return true, nil
}

func (s *SmbPipeAPI) SetUpstreamDestAddr(upstreamDestAddr string) {
	s.upstreamDestAddr = upstreamDestAddr
}

func (s *SmbPipeAPI) SendExecutionResults(profile map[string]interface{}, result map[string]interface{}) {
	requestingPaw := getPawFromProfile(profile)

	// Set up mailbox pipe and listener if needed.
	mailBoxPipePath, _, err := s.fetchClientMailBoxInfo(requestingPaw, true)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] ERROR setting up mailbox listener: %s", err.Error()))
	}

	// Build SMB pipe message for sending execution results.
	// payload will contain JSON marshal of profile, with execution results
	profileCopy := make(map[string]interface{})
	for k, v := range profile {
		profileCopy[k] = v
	}
	results := make([]map[string]interface{}, 1)
	results[0] = result
	profileCopy["results"] = results
	msgPayload, err := json.Marshal(profileCopy)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Cannot send results. Error with profile marshal: %s", err.Error()))
	}
	output.VerbosePrint(fmt.Sprintf("[*] P2p Client: sending execution results to %s", s.upstreamDestAddr))
	upstreamPipeLock.Lock()
	err = sendRequestToUpstreamPipe(s.upstreamDestAddr, requestingPaw, SEND_EXECUTION_RESULTS, msgPayload, mailBoxPipePath)
	upstreamPipeLock.Unlock()
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error sending execution results upstream: %s", err.Error()))
	}
}

func (s *SmbPipeAPI) UploadFileBytes(profile map[string]interface{}, uploadName string, data []byte) error {
	requestingPaw := getPawFromProfile(profile)

	// Set up mailbox pipe and listener if needed.
	mailBoxPipePath, mailBoxListener, err := s.fetchClientMailBoxInfo(requestingPaw, true)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] ERROR setting up mailbox listener: %s", err.Error()))
	}

	// Build SMB pipe message for sending file upload data.
	// payload will contain JSON marshal of the profile, filename, and file data.
	requestInfo := uploadRequestInfo{
		UploadName: uploadName,
		UploadData: data,
		Profile:    profile,
	}
	msgPayload, err := json.Marshal(requestInfo)
	if err != nil {
		return err
	}
	output.VerbosePrint(fmt.Sprintf("[*] P2p Client: uploading file %s to %s", uploadName, s.upstreamDestAddr))
	upstreamPipeLock.Lock()
	err = sendRequestToUpstreamPipe(s.upstreamDestAddr, requestingPaw, SEND_FILE_UPLOAD_BYTES, msgPayload, mailBoxPipePath)
	if err != nil {
		upstreamPipeLock.Unlock()
		return err
	}

	// Process response.
	respMessage, err := getResponseMessage(mailBoxListener)
	upstreamPipeLock.Unlock()
	if err != nil {
		return err
	} else if msgIsEmpty(respMessage) {
		return errors.New("[!] Error: upstream sent back empty message for upload request.")
	} else if respMessage.MessageType != RESPONSE_FILE_UPLOAD {
		return errors.New(fmt.Sprintf("[!] Error: upstream sent invalid response type for upload request: %d", respMessage.MessageType))
	}

	// Message payload indicates true or false for upload success.
	var responseInfo uploadResponseInfo
	if err = json.Unmarshal(respMessage.Payload, &responseInfo); err != nil {
		return err
	}
	if !responseInfo.Result {
		return errors.New(fmt.Sprintf("Failed upload for file %s", responseInfo.UploadName))
	}
	return nil
}

func (s *SmbPipeAPI) GetName() string {
	return s.name
}

func (s *SmbPipeAPI) SupportsContinuous() bool {
	return false
}
