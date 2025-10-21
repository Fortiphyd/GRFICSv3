package contact

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

// Tunnel defines required functions for providing a comms tunnel between agent and C2.
type Tunnel interface {
	GetName() string
	Start(tunnelReady chan bool) // must be run as a go routine
	GetLocalEndpoint() string // agent-side endpoint for tunnel
	GetRemoteEndpoint() string // tunnel destination endpoint
}

type TunnelConfig struct {
	Protocol string // Name of Tunnel protocol
	TunnelEndpoint string // Address used to connect to or start tunnel
	Username string // Username to authenticate to tunnel
	Password string // Password to authenticate to tunnel
	RemoteAddr string // IP address or hostname that tunnel will ultimately connect to
	RemotePort int // Port that tunnel will ultimately connect to
	TunneledProtocol string // protocol that the tunnel will carry
}

// CommunicationTunnels contains maps available Tunnel names to their respective factory methods.
var CommunicationTunnelFactories = map[string]func(tunnelConfig *TunnelConfig) (Tunnel, error){}
var defaultProtocolPorts = map[string]string{
	"http": "80",
	"https": "443",
}

func GetAvailableCommTunnels() []string {
	tunnelNames := make([]string, 0, len(CommunicationTunnelFactories))
	for name := range CommunicationTunnelFactories {
		tunnelNames = append(tunnelNames, name)
	}
	return tunnelNames
}

func BuildTunnelConfig(protocol, tunnelEndpoint, destEndpoint, user, password string) (*TunnelConfig, error) {
	tunneledProtocol, remoteEndpoint := getTunneledProtocolAndRemoteAddr(destEndpoint)
	remoteAddr, remotePort, err := splitAddrAndPort(remoteEndpoint, tunneledProtocol)
	if err != nil {
		return nil, err
	}
	return &TunnelConfig{
		Protocol: protocol,
		TunnelEndpoint: tunnelEndpoint,
		Username: user,
		Password: password,
		RemoteAddr: remoteAddr,
		RemotePort: remotePort,
		TunneledProtocol: tunneledProtocol,
	}, nil
}

// Determine which protocol will be tunneled as well as the remote endpoint,
// based on the address provided by tunnelConfig.TunnelDest. If the protocol is not specified,
// "http" will be returned along with the remote endpoint addr.
//
// Examples:
//	https://10.10.10.10:8888 -> https, 10.10.10.10:8888
//	10.10.10.10.:8888 -> http, 10.10.10.10:8888
func getTunneledProtocolAndRemoteAddr(remoteAddr string) (string, string) {
	protocolSplit := strings.Split(remoteAddr, "://")
	if len(protocolSplit) == 1 {
		// No protocol was specified.
		return "http", protocolSplit[0]
	} else {
		return protocolSplit[0], protocolSplit[1]
	}
}

// Split string of the form address:port or hostname:port into the IP address and port pair. Only supports IPv4.
// If no port is explicitly provided, the default according the provided protocol will be returned.
func splitAddrAndPort(addrAndPort string, protocol string) (string, int, error) {
	addrPortSplit := strings.Split(addrAndPort, ":")
	addr := addrPortSplit[0]
	var portStr string
	if len(addrPortSplit) == 1 {
		// No port specified. Use default port according to protocol.
		if defaultPort, ok := defaultProtocolPorts[protocol]; ok {
			portStr = defaultPort
		} else {
			return "", -1, errors.New(fmt.Sprintf("Could not get default port for protocol %s", protocol))
		}
	} else {
		portStr = addrPortSplit[1]
	}
	if len(addr) == 0 {
		return "", -1, errors.New("Empty address/hostname provided.")
	}
	if len(portStr) == 0 {
		return "", -1, errors.New("Empty port provided.")
	}
	if portNum, err := strconv.Atoi(portStr); err == nil {
		return addr, portNum, nil
	}
	return "", -1, errors.New(fmt.Sprintf("Invalid endpoint provided: %s", addrAndPort))
}

// Parse endpoint addr string (e.g. http://192.168.10.1:8888) into the protocol, IP/hostname, and port string.
// Returns error if addr string is not of expected format. Only supports IPv4.
func getEndpointInfo(endpointAddr string) (string, string, string, error) {
	protocolSplit := strings.Split(endpointAddr, "://")
	var addrAndPort string
	protocol := ""
	if len(protocolSplit) == 1 {
		// No protocol was specified.
		addrAndPort = protocolSplit[0]
	} else {
		addrAndPort = protocolSplit[1]
		protocol = protocolSplit[0]
	}
	addrPortSplit := strings.Split(addrAndPort, ":")
	addr := addrPortSplit[0]
	var port string
	if len(addrPortSplit) == 1 {
		// No port specified. Use default port according to protocol.
		if defaultPort, ok := defaultProtocolPorts[protocol]; ok {
			port = defaultPort
		} else {
			return "", "", "", errors.New(fmt.Sprintf("Could not get default port for protocol %s", protocol))
		}
	} else {
		port = addrPortSplit[1]
	}
	if len(addr) == 0 {
		return "", "", "", errors.New("Empty address/hostname provided.")
	}
	if len(port) == 0 {
		return "", "", "", errors.New("Empty port provided.")
	}
	return protocol, addr, port, nil
}