package proxy

import (
	"sync"

	"github.com/mitre/gocat/contact"
)

// Define MessageType values for P2pMessage
const (
	GET_INSTRUCTIONS = 1
	GET_PAYLOAD_BYTES = 2
	SEND_EXECUTION_RESULTS = 3
	RESPONSE_INSTRUCTIONS = 4
	RESPONSE_PAYLOAD_BYTES = 5
	ACK_EXECUTION_RESULTS = 6
	SEND_FILE_UPLOAD_BYTES = 7
	RESPONSE_FILE_UPLOAD = 8
)

// P2pReceiver defines required functions for relaying messages between peers and an upstream peer/c2.
type P2pReceiver interface {
	InitializeReceiver(agentServer *string, upstreamComs *contact.Contact, waitgroup *sync.WaitGroup) error
	RunReceiver() // must be run as a go routine
	UpdateAgentPaw(newPaw string)
	Terminate()
	GetReceiverAddresses() []string
}

// P2pClient will implement the contact.Contact interface.

// Defines message structure for p2p
type P2pMessage struct {
	SourcePaw string // Paw of agent sending the original request.
	SourceAddress string // return address for responses (e.g. IP + port, pipe path)
	MessageType int
	Payload []byte
	Populated bool
}

var (
	// P2pReceiverChannels contains the possible P2pReceiver implementations
	P2pReceiverChannels = map[string]P2pReceiver{}

	// Contains the C2 Contact implementations strictly for peer-to-peer communications.
	P2pClientChannels = map[string]contact.Contact{}

	// Contains the base64-encoded JSON-dumped list of available proxy receiver information
	// in the form [["Proxy protocol 1","Proxy receiver 1"], ... ["Proxy protocol N","Proxy receiver N"]]
	encodedReceivers = ""

	// XOR key for the encoded proxy receiver info.
	receiverKey = ""
)