package sockets

//Contact defines required functions for communicating with the server
type Contact interface {
	Listen(udp string, http string, inbound int, profile map[string]interface{} ) 
}

//CommunicationChannels contains the contact implementations
var CommunicationChannels = map[string]Contact{}
