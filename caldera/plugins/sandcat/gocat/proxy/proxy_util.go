package proxy

import (
	"encoding/base64"
	"encoding/json"
	"net"
)

// Build p2p message and return the bytes of its JSON marshal.
func buildP2pMsgBytes(sourcePaw string, messageType int, payload []byte, srcAddr string) ([]byte, error) {
	p2pMsg := &P2pMessage{
		SourcePaw: sourcePaw,
		SourceAddress: srcAddr,
		MessageType: messageType,
		Payload: payload,
		Populated: true,
	}
	return json.Marshal(p2pMsg)
}
// Convert bytes of JSON marshal into P2pMessage struct
func bytesToP2pMsg(data []byte) (P2pMessage, error) {
	var message P2pMessage
	if err := json.Unmarshal(data, &message); err == nil {
		return message, nil
	} else {
		return message, err
	}
}

// Check if message is empty.
func msgIsEmpty(msg P2pMessage) bool {
	return !msg.Populated
}

func decodeXor(ciphertext string, xorKey string) string {
	decoded := ""
	key_length := len(xorKey)
	for index, _ := range ciphertext {
		decoded += string(ciphertext[index] ^ xorKey[index % key_length])
	}
	return decoded
}

// Returns map mapping proxy receiver protocol to list of peer receiver addresses.
func GetAvailablePeerReceivers() (map[string][]string, error) {
	peerReceiverInfo := make(map[string][]string)
	if len(encodedReceivers) > 0 && len(receiverKey) > 0 {
		ciphertext, err := base64.StdEncoding.DecodeString(encodedReceivers)
		if err != nil {
			return nil, err
		}
		decodedReceiverInfo := decodeXor(string(ciphertext), receiverKey)
		if err = json.Unmarshal([]byte(decodedReceiverInfo), &peerReceiverInfo); err != nil {
			return nil, err
		}
	}
	return peerReceiverInfo, nil
}

// Given the client profile, append the forwarder's paw, receiver address, and peer protocol to the peer proxy
// chain information in the profile to update the peer-to-peer hops. Modifies the given client profile.
func updatePeerChain(clientProfile map[string]interface{}, forwarderPaw string, receiverAddr string, peerProtocol string) {
	// Proxy chain must be a list of length-3 lists ([forwarder paw, receiver address, peer protocol])
	var proxyChain []interface{}
	if _, ok := clientProfile["proxy_chain"]; ok {
		proxyChain = clientProfile["proxy_chain"].([]interface{})
	} else {
		proxyChain = make([]interface{}, 0)
	}
	nextHop := make([]string, 3)
	nextHop[0] = forwarderPaw
	nextHop[1] = receiverAddr
	nextHop[2] = peerProtocol
	proxyChain = append(proxyChain, nextHop)
	clientProfile["proxy_chain"] = proxyChain
}

// check if a given address/paw is contained in the peer chain
func isInPeerChain(clientProfile map[string]interface{}, searchPaw string) bool {
    // Proxy chain is a list of length-3 lists ([forwarder paw, receiver address, peer protocol])
	if _, ok := clientProfile["proxy_chain"]; ok {
		proxyChain := clientProfile["proxy_chain"].([]interface{})
		for _, peer := range proxyChain {
		    if peer.([]interface{})[0].(string) == searchPaw {
		        return true
		    }
		}
	}
	return false
}

// Return list of local IPv4 addresses for this machine (exclude loopback and unspecified addresses)
func GetLocalIPv4Addresses() ([]string, error) {
	var localIpList []string
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, err
	}
	for _, iface := range ifaces {
		addrs, err := iface.Addrs()
		if err != nil {
			return nil, err
		}
		for _, addr := range addrs {
			var ipAddr net.IP
			switch v:= addr.(type) {
			case *net.IPNet:
				ipAddr = v.IP
			case *net.IPAddr:
				ipAddr = v.IP
			}
			if ipAddr != nil && !ipAddr.IsLoopback() && !ipAddr.IsUnspecified() {
			    ipv4Addr := ipAddr.To4()
			    if ipv4Addr != nil {
				    localIpList = append(localIpList, ipv4Addr.String())
			    }
			}
		}
	}
	return localIpList, nil
}
