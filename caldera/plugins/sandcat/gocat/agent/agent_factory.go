package agent

import (
	"github.com/mitre/gocat/contact"
)

// Creates and initializes a new Agent. Upon success, returns a pointer to the agent and nil Error.
// Upon failure, returns nil and an error.
func AgentFactory(server string, tunnelConfig *contact.TunnelConfig, group string, c2Config map[string]string, enableLocalP2pReceivers bool, initialDelay int, paw string, originLinkID string) (*Agent, error) {
	newAgent := &Agent{}
	if err := newAgent.Initialize(server, tunnelConfig, group, c2Config, enableLocalP2pReceivers, initialDelay, paw, originLinkID); err != nil {
		return nil, err
	} else {
		newAgent.Sleep(newAgent.initialDelay)
		return newAgent, nil
	}
}