package agent

import (
	"errors"
	"fmt"

	"github.com/mitre/gocat/contact"
	"github.com/mitre/gocat/output"
)

func (a *Agent) StartTunnel(tunnelConfig *contact.TunnelConfig) error {
	a.usingTunnel = false
	tunnelFactoryFunc, ok := contact.CommunicationTunnelFactories[tunnelConfig.Protocol]
	if !ok {
		return errors.New(fmt.Sprintf("Could not find communication tunnel factory for protocol %s", tunnelConfig.Protocol))
	}
	tunnel, err := tunnelFactoryFunc(tunnelConfig)
	if err != nil {
		return err
	}
	a.tunnel = tunnel
	output.VerbosePrint(fmt.Sprintf("[*] Starting %s tunnel", tunnel.GetName()))
	tunnelReady := make(chan bool)
	go a.tunnel.Start(tunnelReady)

	// Wait for tunnel to be ready
	ready := <-tunnelReady
	if ready {
		output.VerbosePrint(fmt.Sprintf("[*] %s tunnel ready and listening on %s.", a.tunnel.GetName(), a.tunnel.GetLocalEndpoint()))
		a.updateUpstreamDestAddr(a.tunnel.GetLocalEndpoint())
		a.usingTunnel = true
		return nil
	}
	return errors.New(fmt.Sprintf("Failed to start communication tunnel %s", a.tunnel.GetName()))
}