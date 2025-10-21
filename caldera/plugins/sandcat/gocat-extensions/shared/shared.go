// +build cgo

package main

import "C"
import (
	"strings"

	"github.com/mitre/gocat/contact"
	"github.com/mitre/gocat/core"
)

var (
	key = "JWHQZM9Z4HQOYICDHW4OCJAXPPNHBA"
	server = "http://localhost:8888"
	paw = ""
	group = "red"
	listenP2P = false
	c2Protocol = "HTTP"
	c2Key = ""
	httpProxyGateway = ""
)

//export VoidFunc
func VoidFunc() {
	trimmedServer := strings.TrimRight(server, "/")
	contactConfig := map[string]string{
		"c2Name": c2Protocol,
		"c2Key": c2Key,
		"httpProxyGateway": httpProxyGateway,
	}
	tunnelConfig, err := contact.BuildTunnelConfig("", "", trimmedServer, "", "")
	if err != nil {
		return
	}
	core.Core(trimmedServer, tunnelConfig, group, 0, contactConfig, listenP2P, false, paw, "")
}

func main() {}
