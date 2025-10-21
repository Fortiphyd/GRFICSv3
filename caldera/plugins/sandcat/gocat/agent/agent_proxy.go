package agent

import (
	"errors"
	"fmt"

	"github.com/mitre/gocat/output"
	"github.com/mitre/gocat/proxy"
)

func (a *Agent) ActivateLocalP2pReceivers() {
	for receiverName, p2pReceiver := range proxy.P2pReceiverChannels {
		if err := p2pReceiver.InitializeReceiver(&a.server, &a.beaconContact, a.p2pReceiverWaitGroup); err != nil {
			output.VerbosePrint(fmt.Sprintf("[-] Error when initializing p2p receiver %s: %s", receiverName, err.Error()))
		} else {
			output.VerbosePrint(fmt.Sprintf("[*] Initialized p2p receiver %s", receiverName))
			a.localP2pReceivers[receiverName] = p2pReceiver
			a.p2pReceiverWaitGroup.Add(1)
			a.storeLocalP2pReceiverAddresses(receiverName, p2pReceiver)
			go p2pReceiver.RunReceiver()
		}
	}
}

func (a *Agent) TerminateLocalP2pReceivers() {
	for receiverName, p2pReceiver := range a.localP2pReceivers {
		output.VerbosePrint(fmt.Sprintf("[*] Terminating p2p receiver %s", receiverName))
		p2pReceiver.Terminate()
	}
	a.p2pReceiverWaitGroup.Wait()
}

func (a *Agent) storeLocalP2pReceiverAddresses(receiverName string, p2pReceiver proxy.P2pReceiver) {
	for _, address := range p2pReceiver.GetReceiverAddresses() {
		if _, ok := a.localP2pReceiverAddresses[receiverName]; !ok {
			a.localP2pReceiverAddresses[receiverName] = make([]string, 0)
		}
		a.localP2pReceiverAddresses[receiverName] = append(a.localP2pReceiverAddresses[receiverName], address)
	}
}

// Attempts to look for any compatible peer-to-peer proxy clients for available proxy receivers.
// Sets the first valid one it can find. Returns an error if no valid proxy clients are found.
func (a *Agent) findAvailablePeerProxyClient() error {
	if len(a.availablePeerReceivers) == 0 {
		// Either we used all available peers, or we simply never had any to start with. Refresh
		// the used peers if possible.
		if len(a.exhaustedPeerReceivers) == 0 {
			return errors.New("No peer proxy receivers available to connect to.")
		}
		output.VerbosePrint("[*] All available peer proxy receivers have been tried. Retrying them.")
		a.refreshAvailablePeerReceivers()
	}
	for proxyChannel, receiverAddresses := range a.availablePeerReceivers {
		if len(receiverAddresses) > 0 {
			output.VerbosePrint(fmt.Sprintf("[-] Verifying proxy channel %s", proxyChannel))

			// Attempt to set the new coms channel.
			if err := a.AttemptSelectComChannel(nil, proxyChannel); err != nil {
				output.VerbosePrint(fmt.Sprintf("[!] Error attempting to use proxy channel %s: %s", proxyChannel, err.Error()))

				// Remove the invalid proxy channel from the pool. Safe to remove during iteration.
				delete(a.availablePeerReceivers, proxyChannel)
				continue
			}
			// Successfully set the channel. Update dest address.
			a.usingPeerReceivers = true
			addressToUse := receiverAddresses[0]
			a.updateUpstreamDestAddr(addressToUse)
			output.VerbosePrint(fmt.Sprintf("[*] Updated agent's destination address to proxy peer address: %s", addressToUse))

			// Mark proxy channel and peer receiver address as used.
			a.markPeerReceiverAsUsed(proxyChannel, addressToUse)
			a.peerProxyReceiverDisplay()
			return nil
		}
	}
	return errors.New("No available compatible peer-to-peer proxy clients found.")
}

// Mark the peer proxy channel and receiver address as exhausted, so the agent doesn't try using it again
// before trying the remaining ones.
func (a *Agent) markPeerReceiverAsUsed(proxyChannel string, usedAddress string) {
	if _, ok := a.exhaustedPeerReceivers[proxyChannel]; !ok {
		a.exhaustedPeerReceivers[proxyChannel] = make([]string, 0)
	}
	a.exhaustedPeerReceivers[proxyChannel] = append(a.exhaustedPeerReceivers[proxyChannel], usedAddress)
	if receiverAddresses, ok := a.availablePeerReceivers[proxyChannel]; ok {
		a.availablePeerReceivers[proxyChannel] = deleteStringFromSlice(receiverAddresses, usedAddress)
		// Clear map key if this was the last remaining address for the proxy channel.
		if len(a.availablePeerReceivers[proxyChannel]) == 0 {
			delete(a.availablePeerReceivers, proxyChannel)
		}
	}
}

// Should only be called once the agent's availablePeerReceivers map is empty.
// Will repopulate availablePeerReceivers with the exhausted peer receivers so that the agent
// can try them again.
func (a *Agent) refreshAvailablePeerReceivers() {
	a.availablePeerReceivers = a.exhaustedPeerReceivers
	a.exhaustedPeerReceivers = make(map[string][]string)
}

// Utility function to remove a given string from a string slice.
// Returns the new slice (not necessarily in the same order).
// If the element to delete does not exist in the slice, the original slice will be returned.
func deleteStringFromSlice(deleteFrom []string, toDelete string) []string {
	indexToDelete := -1
	maxIndex := len(deleteFrom) - 1
	for i, element := range deleteFrom {
		if element == toDelete {
			indexToDelete = i
			break
		}
	}
	if indexToDelete >= 0 {
		deleteFrom[indexToDelete] = deleteFrom[maxIndex]
		return deleteFrom[:maxIndex]
	}
	return deleteFrom
}

// Display some output about the available/used peer proxy receivers.
func (a* Agent) peerProxyReceiverDisplay() {
	output.VerbosePrint("[*] Valid peer proxy receivers used so far: ")
	for channel, addrs := range a.exhaustedPeerReceivers {
		for _, addr := range addrs {
			output.VerbosePrint(fmt.Sprintf("\t%s : %s", channel, addr))
		}
	}
	output.VerbosePrint("[*] Valid peer proxy receivers left to try out: ")
	for channel, addrs := range a.availablePeerReceivers {
		for _, addr := range addrs {
			output.VerbosePrint(fmt.Sprintf("\t%s : %s", channel, addr))
		}
	}
}
