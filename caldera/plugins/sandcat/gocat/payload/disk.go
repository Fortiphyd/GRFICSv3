// Package payload provides functions for working with payloads on disk and in memory.
package payload

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/mitre/gocat/output"
)

// Downloads the specified payload data to disk with the specified filename.
// Returns filepath of the payload and any errors that occurred.
// If the payload already exists then no error will be returned.
func WriteToDisk(filename string, payloadBytes []byte) (string, error) {
	location := filepath.Join(filename)
	if !FileExists(location) {
		output.VerbosePrint(fmt.Sprintf("[*] Writing payload %s to disk at %s", filename, location))
		return location, WriteBytes(location, payloadBytes)
	}
	output.VerbosePrint(fmt.Sprintf("[*] File %s already exists", filename))
	return location, nil
}

// Writes given payload data to the given location.
func WriteBytes(location string, payload []byte) error {
	dst, err := os.Create(location)
	if err != nil {
		return err
	} else {
		defer dst.Close()
		if _, err = dst.Write(payload); err != nil {
			return err
		} else if err = os.Chmod(location, 0700); err != nil {
			return err
		} else {
			return nil
		}
	}
}

// Returns the name of payloads not found on disk.
func CheckIfOnDisk(payloads []string) []string {
	var missing []string
	for i := range payloads {
		if !FileExists(filepath.Join(payloads[i])) {
			missing = append(missing, payloads[i])
		}
	}
	return missing
}

// Checks if the given file path exists.
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err == nil {
		return true
	}
	if os.IsNotExist(err) {
		return false
	}
	return true
}
