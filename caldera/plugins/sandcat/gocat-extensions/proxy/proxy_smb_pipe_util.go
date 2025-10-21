// +build windows

package proxy

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"math/rand"
	"net"
	"os"
	"time"

	"github.com/mitre/gocat/output"

	"gopkg.in/natefinch/npipe.v2"
)

// Pipe-related constants.
const (
	pipeCharacters = "abcdefghijklmnopqrstuvwxyz1234567890"
	numPipeCharacters = int64(len(pipeCharacters))
	clientPipeNameMinLen = 10
	clientPipeNameMaxLen = 15
	maxChunkSize = 5*4096 // chunk size for writing to pipes.
	pipeDialTimeoutSec = 10 // number of seconds to wait before timing out of pipe dial attempt.
)

// Auxiliary struct that defines P2P message payload structure for an ability payload request
type payloadRequestInfo struct {
	PayloadName string
	Profile map[string]interface{}
}

// Auxiliary struct that defines P2P message payload structure for an ability payload response
type payloadResponseInfo struct {
	PayloadName string
	PayloadData []byte
}

// Auxiliary struct that defines P2P message payload structure for an ability upload request
type uploadRequestInfo struct {
	UploadName string
	UploadData []byte
	Profile map[string]interface{}
}

// Auxiliary struct that defines P2P message payload structure for an ability upload response
type uploadResponseInfo struct {
	UploadName string
	Result bool
}

/*
 * SMB Read/Write helper functions
 */

// Send a P2pMessage to the specified server pipe path with specified paw, message type, payload, and return mailbox path.
func sendRequestToUpstreamPipe(pipePath string, paw string, messageType int, payload []byte, returnMailBoxPipePath string) error {
    pipeMsgData, err := buildP2pMsgBytes(paw, messageType, payload, returnMailBoxPipePath)
    if err != nil {
    	return err
    }
    _, err = sendDataToPipe(pipePath, pipeMsgData)
    return err
}

// Returns the P2pMessage sent to the pipe path for the specified listener.
func getResponseMessage(listener net.Listener) (P2pMessage, error) {
	responseData, err := fetchDataFromPipe(listener)
    if responseData == nil || err != nil {
    	return P2pMessage{}, err
    }
    return bytesToP2pMsg(responseData)
}

// Sends data to specified pipe path. Returns total number of bytes written and errors if any.
func sendDataToPipe(pipePath string, data []byte) (int, error) {
	// Connect to pipe.
	timeout := pipeDialTimeoutSec * time.Second
	conn, err := npipe.DialTimeout(pipePath, timeout)
    if err != nil {
        return 0, err
    }
    defer conn.Close()

    // Write data in chunks.
    writer := bufio.NewWriter(conn)
    endIndex := 0
    startIndex := 0
    dataSize := len(data)
    counter := 0
    for ; endIndex < dataSize; {
        endIndex = startIndex + maxChunkSize
        if dataSize <= endIndex {
            endIndex = dataSize
        }
        dataToSend := data[startIndex:endIndex]
        numWritten, err := writePipeData(dataToSend, writer)
        if err != nil {
            output.VerbosePrint(fmt.Sprintf("[!] Error sending data chunk: %v", err))
            return counter, err
        } else {
            counter = counter + numWritten
        }
        startIndex = endIndex
    }
    return counter, nil
}

// Helper function that waits for a connection to the listener and then returns sent data.
func fetchDataFromPipe(listener net.Listener) ([]byte, error) {
    conn, err := listener.Accept()
    if err != nil {
        output.VerbosePrint(fmt.Sprintf("[!] Error with accepting connection to listener: %v", err))
        return nil, err
    }
    defer conn.Close()

    // Read in the data and close connection. If message has been split into chunks,
    // we should read everything in one shot.
    pipeReader := bufio.NewReader(conn)
    receivedData, err := readPipeData(pipeReader)
    if err != nil {
        return nil, err
    }
    return receivedData, nil
}

// Returns data read, along with any non-EOF errors.
func readPipeData(pipeReader *bufio.Reader) ([]byte, error) {
    buffer := make([]byte, 4*1024)
    totalData := make([]byte, 0)
    for {
        n, err := pipeReader.Read(buffer[:cap(buffer)])
        buffer = buffer[:n]
        if n == 0 {
            if err == nil {
                // Try reading again.
                time.Sleep(200 * time.Millisecond)
                continue
            } else if err == io.EOF {
                // Reading is done.
                break
            } else {
                 output.VerbosePrint("[!] Error reading data from pipe")
                 return nil, err
            }
        }

        // Add data chunk to current total
        totalData = append(totalData, buffer...)
        if err != nil && err != io.EOF {
             output.VerbosePrint("[!] Error reading data from pipe")
             return nil, err
        }
    }
    return totalData, nil
}

// Write data using the Writer object. Returns number of bytes written, and an error if any.
func writePipeData(data []byte, pipeWriter *bufio.Writer) (int, error) {
    if data == nil || len(data) == 0 {
        output.VerbosePrint("[!] Warning: attempted to write nil/empty data byte array to pipe.")
        return 0, nil
    }
    if pipeWriter == nil {
        return 0, errors.New("Nil writer object for sending data to pipe.")
    }
    numBytes, err := pipeWriter.Write(data)
    if err != nil {
        if err == io.ErrClosedPipe {
	        output.VerbosePrint("[!] Pipe closed. Not able to flush data.")
	        return numBytes, err
	    } else {
	        output.VerbosePrint(fmt.Sprintf("[!] Error writing data to pipe\n%v", err))
            return numBytes, err
	    }
    }
    err = pipeWriter.Flush()
	if err != nil {
	    if err == io.ErrClosedPipe {
	        output.VerbosePrint("[!] Pipe closed. Not able to flush data.")
	        return numBytes, err
	    } else {
	        output.VerbosePrint(fmt.Sprintf("[!] Error flushing data to pipe\n%v", err))
		    return numBytes, err
	    }
	}
	return numBytes, nil
}

/*
 * Other auxiliary functions
 */

// Fetch the client mailbox path and listener for the specified paw. If none exists, create new ones if the
// flag is set and return the newly made path and listener. Will update mappings in that case.
func (s *SmbPipeAPI) fetchClientMailBoxInfo(paw string, createNewMailBox bool) (string, net.Listener, error) {
	var err error
	mailBoxPipePath, pipePathSet := s.returnMailBoxPipePaths[paw]
	mailBoxListener, listenerSet := s.returnMailBoxListeners[paw]
	if (!pipePathSet || !listenerSet) && createNewMailBox {
		output.VerbosePrint(fmt.Sprintf("[*] P2P Client: will create new mailbox info for paw %s", paw))
		mailBoxPipePath, mailBoxListener, err = createNewReturnMailBox()
		if err != nil {
			return "", nil, err
		}
		s.updateClientPawMailBoxInfo(paw, mailBoxPipePath, mailBoxListener)
		output.VerbosePrint(fmt.Sprintf("[*] P2P Client: set mailbox pipe path %s for paw %s", mailBoxPipePath, paw))
	}
	return mailBoxPipePath, mailBoxListener, nil
}

// Updates the mailbox information maps for the given paw.
func (s *SmbPipeAPI) updateClientPawMailBoxInfo(paw string, pipePath string, listener net.Listener) {
	apiClientMutex.Lock()
	defer apiClientMutex.Unlock()
	s.returnMailBoxPipePaths[paw] = pipePath
	s.returnMailBoxListeners[paw] = listener
}

// Set up random pipe name and listener for a new return mailbox.
func createNewReturnMailBox() (string, net.Listener, error) {
    // Generate random pipe name for return mail box pipe path.
    pipeName := getRandPipeName(time.Now().UnixNano())
    hostname, err := os.Hostname()
    if err != nil {
        return "", nil, err
    }

	// Create listener for Pipe
	localPipePath := "\\\\.\\pipe\\" + pipeName
	mailBoxListener, err := listenPipeFullAccess(localPipePath)
	if err != nil {
		return "", nil, err
	}
	mailBoxPipePath := "\\\\" + hostname + "\\pipe\\" + pipeName
	output.VerbosePrint(fmt.Sprintf("[*] Created return mailbox pipe path %s", mailBoxPipePath))
    return mailBoxPipePath, mailBoxListener, nil
}

// Helper function that listens on pipe and returns listener and any error.
func listenPipeFullAccess(pipePath string) (net.Listener, error) {
    return npipe.Listen(pipePath)
}

// Helper function that creates random pipename of random length, using specified seed.
func getRandPipeName(seed int64) string {
    rand.Seed(seed)
    length := rand.Intn(clientPipeNameMaxLen - clientPipeNameMinLen) + clientPipeNameMinLen
    buffer := make([]byte, length)
    for i := range buffer {
        buffer[i] = pipeCharacters[rand.Int63() % numPipeCharacters]
    }
    return string(buffer)
}

// Helper function that creates a static main pipename using the given string to calculate seed for RNG.
// Pipe name length will also be determined using the string.
func getMainPipeName(seedStr string) string {
	seedNum := 0
	for i, rune := range seedStr {
		seedNum += i*int(rune)
	}
	return getRandPipeName(int64(seedNum))
}

// Return the paw from the profile.
func getPawFromProfile(profile map[string]interface{}) string {
	if profile["paw"] != nil {
		return profile["paw"].(string)
	}
	return ""
}