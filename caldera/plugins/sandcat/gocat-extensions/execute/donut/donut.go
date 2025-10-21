// +build windows

package donut

import (
	"fmt"
	"strings"
	"runtime"
	"time"

	"github.com/mitre/gocat/execute"
	"github.com/mitre/gocat/output"
)

type Donut struct {
	archName string
}

func init() {
	runner := &Donut{
		archName: "donut_" + runtime.GOARCH,
	}
	if runner.CheckIfAvailable() {
		execute.Executors[runner.archName] = runner
	}
}

const COMMANDLINE string = "rundll32.exe"

func (d *Donut) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	// Setup variables
	stdoutBytes := make([]byte, 1)
	stderrBytes := make([]byte, 1)
	var eventCode uint32
	inMemoryPayloads := info.InMemoryPayloads
	payload, bytes := getDonutBytes(inMemoryPayloads)

	if bytes != nil && len(bytes) > 0 {
		// Create sacrificial process
		output.VerbosePrint(fmt.Sprintf("[i] Donut: Creating sacrificial process '%s'", COMMANDLINE))
		handle, pid, stdout, stderr := CreateSuspendedProcessWithIORedirect(COMMANDLINE)
		output.VerbosePrint(fmt.Sprintf("[i] Donut: Created sacrificial process with PID %d", pid))

		// Run the shellcode and wait for it to complete
		output.VerbosePrint(fmt.Sprint("[i] Donut: Running shellcode"))
		executionTimestamp := time.Now().UTC()
		task, err := Runner(bytes, handle, stdout, &stdoutBytes, stderr, &stderrBytes, &eventCode)
		output.VerbosePrint(fmt.Sprint("[i] Donut: Shellcode execution finished"))

		// Assemble the final output
		if task {
			return execute.CommandResults{
				StandardOutput: []byte(string(stdoutBytes)),
				StandardError: []byte(string(stderrBytes)),
				ExitCode: fmt.Sprint(eventCode),
				StatusCode: execute.SUCCESS_STATUS,
				Pid: fmt.Sprint(pid),
				ExecutionTimestamp: executionTimestamp,
			}
		}

		// Covers the cases where an error was received before the remote thread was created
		errorBytes := []byte(fmt.Sprintf("Shellcode execution failed. Error message: %s", fmt.Sprint(err)))
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: errorBytes,
			ExitCode: fmt.Sprint(eventCode),
			StatusCode: execute.ERROR_STATUS,
			Pid: fmt.Sprint(pid),
			ExecutionTimestamp: executionTimestamp,
		}
	} else {
		// Empty payload
		errorBytes := []byte(fmt.Sprintf("Empty payload: %s", payload))
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: errorBytes,
			ExitCode: execute.ERROR_EXIT_CODE,
			StatusCode: execute.ERROR_STATUS,
			Pid: "-1",
			ExecutionTimestamp: time.Now().UTC(),
		}
	}
}

func (d *Donut) String() string {
	return d.archName
}

func (d *Donut) CheckIfAvailable() bool {
	return IsAvailable()
}

func (d* Donut) DownloadPayloadToMemory(payloadName string) bool {
	return strings.HasSuffix(payloadName, ".donut")
}

// Since donut abilities only require one payload, grab the first in-memory payload available.
func getDonutBytes(inMemoryPayloads map[string][]byte) (string, []byte) {
	for payloadName, payloadBytes := range inMemoryPayloads {
		return payloadName, payloadBytes
	}
	return "", nil
}

func (d *Donut) UpdateBinary(newBinary string) {
	return
}