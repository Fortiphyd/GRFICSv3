// Reference: https://gist.github.com/svett/5d695dcc4cc6ad5dd275

package contact

import (
	"fmt"
	"io"
	"math/rand"
	"net"
	"strconv"
	"time"

	"golang.org/x/crypto/ssh"

	"github.com/mitre/gocat/output"
)

var (
	minLocalPort = 50000
	maxLocalPort = 65000
)

// Will implement the Tunnel interface.
type SshTunnel struct {
	name string
	sshUsername string
	sshPassword string
	tunneledProtocol string
	localTunnelEndpoint string // localhost and random local port
	serverTunnelEndpoint string // server IP/hostname and SSH port
	remoteEndpoint string // localhost (from server's perspective) and true dest port for underlying contact
	config *ssh.ClientConfig
}

func init() {
	rand.Seed(time.Now().UTC().UnixNano())
	CommunicationTunnelFactories["SSH"] = SshTunnelFactory
}

func SshTunnelFactory(tunnelConfig *TunnelConfig) (Tunnel, error) {
	clientConfig := &ssh.ClientConfig{
		User: tunnelConfig.Username,
		Auth: []ssh.AuthMethod{
			ssh.Password(tunnelConfig.Password),
		},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}

	sshServerAddr, sshPort, err := getSSHServerAddrAndPort(tunnelConfig)
	if err != nil {
		return nil, err
	}
	localPortNum := getRandomListeningPort()
	relativeRemoteAddr := getRelativeRemoteAddr(sshServerAddr, tunnelConfig.RemoteAddr)
	tunnel := &SshTunnel{
		name: tunnelConfig.Protocol,
		sshUsername: tunnelConfig.Username,
		sshPassword: tunnelConfig.Password,
		localTunnelEndpoint: fmt.Sprintf("localhost:%d", localPortNum),
		serverTunnelEndpoint: fmt.Sprintf("%s:%d", sshServerAddr, sshPort),
		remoteEndpoint: fmt.Sprintf("%s:%d", relativeRemoteAddr, tunnelConfig.RemotePort),
		config: clientConfig,
		tunneledProtocol: tunnelConfig.TunneledProtocol,
	}
	return tunnel, nil
}

// Returns the remote addr with respect to the the SSH server. For instance, if both
// the sshServerAddr and remoteAddr are the same, the relative remote addr for the SSH tunnel
// would be localhost.
func getRelativeRemoteAddr(sshServerAddr, remoteAddr string) string {
	if sshServerAddr == remoteAddr {
		return "localhost"
	}
	return remoteAddr
}

func getSSHServerAddrAndPort(tunnelConfig *TunnelConfig) (string, int, error) {
	// Check if provided tunnel endpoint is just a port
	sshEndpoint := tunnelConfig.TunnelEndpoint
	if portNum, err := strconv.Atoi(sshEndpoint); err == nil {
		// Only a port was provided. Use the same IP address as the one provided for the remote destination.
		return tunnelConfig.RemoteAddr, portNum, nil
	}
	return splitAddrAndPort(sshEndpoint, tunnelConfig.TunneledProtocol)
}

func (s *SshTunnel) GetName() string {
	return s.name
}

func (s *SshTunnel) GetLocalEndpoint() string {
	return fmt.Sprintf("%s://%s", s.tunneledProtocol, s.localTunnelEndpoint)
}

func (s *SshTunnel) GetRemoteEndpoint() string {
	return fmt.Sprintf("%s://%s", s.tunneledProtocol, s.remoteEndpoint)
}

// Must be run as go routine.
func (s *SshTunnel) Start(tunnelReady chan bool) {
	output.VerbosePrint(fmt.Sprintf("Starting local tunnel endpoint at %s", s.localTunnelEndpoint))
	output.VerbosePrint(fmt.Sprintf("Setting server tunnel endpoint at %s", s.serverTunnelEndpoint))
	output.VerbosePrint(fmt.Sprintf("Setting remote endpoint at %s", s.remoteEndpoint))
	listener, err := net.Listen("tcp", s.localTunnelEndpoint)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error setting SSH tunnel listener: %s", err.Error()))
		tunnelReady <- false
		return
	}
	defer listener.Close()
	// Tell caller we're ready for connections
	tunnelReady <- true
	for {
		output.VerbosePrint("[*] Listening on local SSH tunnel endpoint")
		localConn, err := listener.Accept()
		output.VerbosePrint("[*] Accepted connection on local SSH tunnel endpoint")
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] Error accepting local SSH tunnel connection: %s", err.Error()))
			continue
		}
		go s.forwardConnection(localConn)
	}
}

func (s *SshTunnel) forwardConnection(localConn net.Conn) {
	output.VerbosePrint("[*] Forwarding connection to server")
	serverConn, err := s.connectToServerSsh()
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error connecting to server SSH endpoint: %s", err.Error()))
		localConn.Close()
		return
	}

	// Get remote connection through tunnel
	remoteConn, err := serverConn.Dial("tcp", s.remoteEndpoint)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error connecting to remote endpoint: %s", err.Error()))
		localConn.Close()
		serverConn.Close()
		return
	}
	output.VerbosePrint("[*] Opened remote connection through tunnel")
	forwarderFunc := func(writer, reader net.Conn) {
		defer writer.Close()
		defer reader.Close()

		_, err:= io.Copy(writer, reader)
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[!] I/O copy error when forwarding through tunnel: %s", err.Error()))
			localConn.Close()
			remoteConn.Close()
			serverConn.Close()
		}
	}
	go forwarderFunc(localConn, remoteConn)
	go forwarderFunc(remoteConn, localConn)
}

func (s *SshTunnel) connectToServerSsh() (*ssh.Client, error) {
	return ssh.Dial("tcp", s.serverTunnelEndpoint, s.config)
}

func getRandomListeningPort() int {
	return rand.Intn(maxLocalPort - minLocalPort) + minLocalPort
}