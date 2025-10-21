package proxy

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/rand"
	"net"
	"net/http"
	"io"
	"sync"
	"strconv"
	"time"

	"github.com/mitre/gocat/output"
	"github.com/mitre/gocat/contact"
	"github.com/grandcat/zeroconf"
)

var (
	beaconEndpoint = "/beacon"
	payloadEndpoint = "/file/download"
	uploadEndpoint = "/file/upload"
	httpProxyName = "HTTP"
	maxPortRetries = 5
	minReceiverPort = 50000
	maxReceiverPort = 63000
	maxMemory = int64(20*1024*1024)
)

//HttpReceiver forwards data received from HTTP requests to the upstream server via HTTP. Implements the P2pReceiver interface.
type HttpReceiver struct {
	agentPaw string // paw of agent running this receiver.
	agentServer *string // refers to agent's current server value
	port int
	bindPortStr string
	receiverName string
	upstreamComs *contact.Contact
	httpServer *http.Server
	waitgroup *sync.WaitGroup
	receiverContext context.Context
	receiverCancelFunc context.CancelFunc
	urlList []string // list of HTTP urls that external machines can use to reach this receiver.
	dnsServer *zeroconf.Server
}

func init() {
	P2pReceiverChannels[httpProxyName] = &HttpReceiver{}
}

func (h *HttpReceiver) InitializeReceiver(agentServer *string, upstreamComs *contact.Contact, waitgroup *sync.WaitGroup) error {
	err := h.initializeReceiverPort()
	if err != nil {
		return err
	}
	h.receiverName = httpProxyName
	h.agentServer = agentServer
	h.upstreamComs = upstreamComs // contact will keep track of upstream dest addr.
	h.httpServer = &http.Server{
		Addr: h.bindPortStr,
		Handler: nil,
	}
	h.urlList, err = h.getReachableUrls()
	if err != nil {
		return err
	}
	h.waitgroup = waitgroup
	h.receiverContext, h.receiverCancelFunc = context.WithTimeout(context.Background(), 5*time.Second)
	return nil
}

func (h *HttpReceiver) RunReceiver() {
	output.VerbosePrint(fmt.Sprintf("[*] Starting HTTP proxy receiver on local port %d", h.port))
	output.VerbosePrint(fmt.Sprintf("[*] HTTP proxy receiver is using upstream contact %s", (*h.upstreamComs).GetName()))
	h.broadcastReceiverChannel(h.port)
	h.startHttpProxy()
}

func (h *HttpReceiver) Terminate() {
	defer func() {
		h.waitgroup.Done()
		h.receiverCancelFunc()
 		h.dnsServer.Shutdown()
	}()
	if err := h.httpServer.Shutdown(h.receiverContext); err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Error when shutting down HTTP receiver server: %s", err.Error()))
	}
}

// Update paw of agent running this receiver.
func (h *HttpReceiver) UpdateAgentPaw(newPaw string) {
	h.agentPaw = newPaw
}

func (h *HttpReceiver) GetReceiverAddresses() []string {
	return h.urlList
}

// Helper method for StartReceiver. Starts HTTP proxy to forward messages from peers to the C2 server.
func (h *HttpReceiver) startHttpProxy() {
	http.HandleFunc(beaconEndpoint, h.handleBeaconEndpoint)
	http.HandleFunc(payloadEndpoint, h.handlePayloadEndpoint)
	http.HandleFunc(uploadEndpoint, h.handleUploadEndpoint)
	if err := http.ListenAndServe(h.bindPortStr, nil); err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] HTTP proxy error: %s", err.Error()))
	}
}

// Handle beacon/execution results sent to /beacon
func (h *HttpReceiver) handleBeaconEndpoint(writer http.ResponseWriter, reader *http.Request) {
	// Get data from the message that client peer sent.
	body, err := io.ReadAll(reader.Body)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error: could not read data from beacon request: %s", err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		return
	}
	reader.Body = io.NopCloser(bytes.NewReader(body))

	// Extract profile from the data.
	profileData, err := base64.StdEncoding.DecodeString(string(body))
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error: malformed profile base64 received: %s", err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		return
	}
	profile := make(map[string]interface{})
	if err = json.Unmarshal(profileData, &profile); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error: malformed profile data received on beacon endpoint: %s", err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		return
	}

	//make sure our paw is not in the peer chain (loop scenario)
	if isInPeerChain(profile, h.agentPaw) {
	    output.VerbosePrint(fmt.Sprintf("[!] Error: agent paw already in proxy chain, loop detected"))
	    http.Error(writer, "peer loop detected", http.StatusInternalServerError)
	    return
	}

	// Update server value in profile with our agent's server value.
	profile["server"] = *h.agentServer

	// Get local address that received the request
	receiverAddress, err := h.getLocalAddressForRequest(reader)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error getting local address: %s", err.Error()))
	    http.Error(writer, "Could not get local address from request", http.StatusInternalServerError)
	    return
	}

	// Check if profile contains execution results
	if results, ok := profile["results"]; ok {
		output.VerbosePrint("[*] HTTP proxy: handling execution results from client.")
		resultList := results.([]interface{})
		if len(resultList) > 0 {
			(*h.upstreamComs).SendExecutionResults(profile, resultList[0].(map[string]interface{}))
		} else {
			output.VerbosePrint("[!] Error: client sent empty result list.")
			http.Error(writer, "Empty result list received from client", http.StatusInternalServerError)
		}
	} else {
		output.VerbosePrint("[*] HTTP proxy: handling beacon request from client.")

		// Update peer proxy chain information to indicate that the beacon is going through this agent.
		updatePeerChain(profile, h.agentPaw, receiverAddress, h.receiverName)
		beaconResponse := (*h.upstreamComs).GetBeaconBytes(profile)
		encodedResponse := []byte(base64.StdEncoding.EncodeToString(beaconResponse))
		if err = sendResponseToClient(encodedResponse, nil, writer); err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error sending response to client: %s", err.Error()))
			http.Error(writer, err.Error(), http.StatusInternalServerError)
		}
	}
}

// Handle payload requests sent to /file/download
func (h *HttpReceiver) handlePayloadEndpoint(writer http.ResponseWriter, reader *http.Request) {
	output.VerbosePrint("[*] HTTP proxy: handling payload request from client.")

	// Get filename, paw, and platform from headers
	filenameReqHeader, ok := reader.Header["File"]
	if !ok {
		output.VerbosePrint("[!] Error: Client did not include filename in payload request.")
		http.Error(writer, "Filename required in payload request", http.StatusInternalServerError)
		return
	}
	filename := filenameReqHeader[0]
	platformHeader, ok := reader.Header["Platform"]
	if !ok {
		output.VerbosePrint("[!] Error: Client did not include platform in payload request.")
		http.Error(writer, "Platform required in payload request", http.StatusInternalServerError)
		return
	}
	platform := platformHeader[0]
	pawHeader, ok := reader.Header["Paw"]
	if !ok {
		output.VerbosePrint("[!] Error: Client did not include paw in payload request.")
		http.Error(writer, "Paw required in payload request", http.StatusInternalServerError)
		return
	}
	clientPaw := pawHeader[0]

	// Build profile to send request upstream.
	profile := make(map[string]interface{})
	profile["server"] = *h.agentServer
	profile["platform"] = platform
	profile["paw"] = clientPaw
	payloadBytes, realFilename := (*h.upstreamComs).GetPayloadBytes(profile, filename)

	// Prepare response for client
	responseHeaders := make(map[string][]string)
	contentDispHeader := make([]string, 1)
	contentDispHeader[0] = fmt.Sprintf("attachment; filename=%s", realFilename)
	responseHeaders["CONTENT-DISPOSITION"] = contentDispHeader
	filenameRespHeader := make([]string, 1)
	filenameRespHeader[0] = realFilename
	responseHeaders["FILENAME"] = filenameRespHeader
	if err := sendResponseToClient(payloadBytes, responseHeaders, writer); err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Error sending payload response to client: %s", err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
	}
}

func (h *HttpReceiver)  handleUploadEndpoint (writer http.ResponseWriter, reader *http.Request) {
	output.VerbosePrint("[*] HTTP proxy: handling upload request from client.")

	// Get client paw and hostname from headers
	pawHeader, ok := reader.Header["X-Paw"]
	if !ok {
		output.VerbosePrint("[!] Error: Client did not include paw in upload request.")
		http.Error(writer, "Paw required in upload request", http.StatusInternalServerError)
		return
	}
	clientPaw := pawHeader[0]

	hostHeader, ok := reader.Header["X-Host"]
	if !ok {
		output.VerbosePrint("[!] Error: Client did not include hostname in upload request.")
		http.Error(writer, "Hostname required in upload request", http.StatusInternalServerError)
		return
	}
	clientHost := hostHeader[0]

	// Parse multipart form to get upload name and data
	uploadName, data, err := getUploadNameAndData(reader)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error processing upload request for client paw %s: %s", clientPaw, err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		return
	}

	// Build profile to send request upstream.
	profile := make(map[string]interface{})
	profile["server"] = *h.agentServer
	profile["paw"] = clientPaw
	profile["host"] = clientHost

	output.VerbosePrint(fmt.Sprintf("[*] Forwarding file upload request for client paw %s. File: %s. Size: %d", clientPaw, uploadName, len(data)))
	if err = (*h.upstreamComs).UploadFileBytes(profile, uploadName, data); err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error uploading file %s for client paw %s: %s", uploadName, clientPaw, err.Error()))
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		return
	}
}

func getUploadNameAndData(reader *http.Request) (string, []byte, error) {
	if err := reader.ParseMultipartForm(maxMemory); err != nil {
		return "", nil, err
	}
	uploadFile, fileHeader, err := reader.FormFile("file")
	defer uploadFile.Close()
	if err != nil {
		return "", nil, err
	}
	uploadName := fileHeader.Filename
	if len(uploadName) == 0 {
		return "", nil, errors.New("No file name or empty file name specified in upload request")
	}
	buf := make([]byte, fileHeader.Size)
	if bytesRead, err := io.ReadFull(uploadFile, buf); err != nil {
		return "", nil, err
	} else if int64(bytesRead) < fileHeader.Size {
		return "", nil, errors.New(fmt.Sprintf("Could not read entire file from upload. %d bytes read, %d required", bytesRead, fileHeader.Size))
	}
	return uploadName, buf, nil
}

func sendResponseToClient(data []byte, headers map[string][]string, writer http.ResponseWriter) error {
	if headers != nil {
		for header, val := range headers {
			writer.Header().Set(header, val[0])
			for i := 1; i < len(val); i++ {
				writer.Header().Add(header, val[i])
			}
		}
	}
	_, err := writer.Write(data)
	return err
}

// Port must be set for the HTTP receiver before calling this method.
func (h *HttpReceiver) getReachableUrls() ([]string, error) {
	var urlList []string
	ipAddrs, err := GetLocalIPv4Addresses()
	if err != nil {
		return nil, err
	}
	for _, addr := range ipAddrs {
		url := "http://" + addr + ":" + strconv.Itoa(h.port)
		urlList = append(urlList, url)
	}
	return urlList, nil
}

// Helper method for initializing the receiver port.
func (h *HttpReceiver) initializeReceiverPort() error {
	// Try 5 random ports before giving up.
	retryCount := 0
	for (retryCount < maxPortRetries) {
		currPort := generateRandomPort(minReceiverPort, maxReceiverPort)
		currBindPortStr := ":" + strconv.Itoa(currPort)

		// Check if port is already in use.
		if ln, err := net.Listen("tcp", currBindPortStr); err != nil {
			output.VerbosePrint(fmt.Sprintf("[-] Error trying to use random port %d: %s", currPort, err.Error()))
		} else {
			h.port = currPort
			h.bindPortStr = currBindPortStr
			return ln.Close()
		}
	}
	return errors.New(fmt.Sprintf("Failed to find available port %d consecutive times.", maxPortRetries))
}

// Generate random port for the receiver in the range [minPort, maxPort]
func generateRandomPort(minPort int, maxPort int) int {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(maxPort - minPort) + minPort
}

func (h *HttpReceiver) broadcastReceiverChannel(port int) {
    for h.agentPaw == "" {time.Sleep(1)}
    info := []string{"HTTP"}
    server, err := zeroconf.Register(h.agentPaw, "_service._comms", "local.", port, info, nil)
    if err != nil {
        output.VerbosePrint(fmt.Sprintf("unable to start mdns server, error: %s" , err))
    }
    h.dnsServer = server
    output.VerbosePrint(fmt.Sprintf("advertising agent on mdns (_service._comms)"))
}

func (h *HttpReceiver) getLocalAddressForRequest(request *http.Request) (string, error) {
	addr, ok := request.Context().Value(http.LocalAddrContextKey).(net.Addr)
	if !ok {
		return "", errors.New("Could not access local address for HTTP request")
	}
	return "http://" + addr.String(), nil
}