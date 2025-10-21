package main

import (
	"flag"
	"fmt"
	"strconv"
	"strings"

	"github.com/mitre/gocat/contact"
	"github.com/mitre/gocat/core"
)

/*
These default  values can be overridden during linking - server, group, and sleep can also be overridden
with command-line arguments at runtime.
*/
var (
	key       = "JWHQZM9Z4HQOYICDHW4OCJAXPPNHBA"
	server    = "http://localhost:8888"
	paw       = ""
	group     = "red"
	c2Name    = "HTTP"
	c2Key     = ""
	listenP2P = "false" // need to set as string to allow ldflags -X build-time variable change on server-side.
	httpProxyGateway = ""
)

func main() {
	parsedListenP2P, err := strconv.ParseBool(listenP2P)
	if err != nil {
		parsedListenP2P = false
	}
	server := flag.String("server", server, "The FQDN of the server")
	httpProxyUrl :=  flag.String("httpProxyGateway", httpProxyGateway, "URL for the HTTP proxy gateway. For environments that use proxies to reach the internet.")
	paw := flag.String("paw", paw, "Optionally specify a PAW on initialization")
	group := flag.String("group", group, "Attach a group to this agent")
	c2Protocol := flag.String("c2", c2Name, "C2 Channel for agent")
	delay := flag.Int("delay", 0, "Delay starting this agent by n-seconds")
	verbose := flag.Bool("v", false, "Enable verbose output")
	listenP2P := flag.Bool("listenP2P", parsedListenP2P, "Enable peer-to-peer receivers")
	originLinkID := flag.String("originLinkID", "", "Optionally set originating link ID")
	tunnelProtocol := flag.String("tunnelProtocol", "", "C2 comms tunnel type to use.")
	tunnelAddr := flag.String("tunnelAddr", "", "Address used to connect to or start the tunnel.")
	tunnelUsername := flag.String("tunnelUser", "", "Username used to authenticate to the tunnel.")
	tunnelPassword := flag.String("tunnelPassword", "", "Password used to authenticate to the tunnel.")

	flag.Parse()

	trimmedServer := strings.TrimRight(*server, "/")
	tunnelConfig, err := contact.BuildTunnelConfig(*tunnelProtocol, *tunnelAddr, trimmedServer, *tunnelUsername, *tunnelPassword)
	if err != nil && *verbose {
		fmt.Println(fmt.Sprintf("[!] Error building tunnel config: %s", err.Error()))
		return
	}
	contactConfig := map[string]string{
		"c2Name": *c2Protocol,
		"c2Key": c2Key,
		"httpProxyGateway": *httpProxyUrl,
	}
	core.Core(trimmedServer, tunnelConfig, *group, *delay, contactConfig, *listenP2P, *verbose, *paw, *originLinkID)
}
