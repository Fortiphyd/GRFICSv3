package native

import (
	"errors"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
	"github.com/google/shlex"

	"github.com/mitre/gocat/execute"
	"github.com/mitre/gocat/execute/native/util"

	_ "github.com/mitre/gocat/execute/native/discovery" // necessary to initialize all submodules
	_ "github.com/mitre/gocat/execute/native/aws" // necessary to initialize all submodules
)

type NativeExecutor struct {
	shortName string
	pid int
	pidStr string
}

func init() {
	pid := os.Getpid()
	pidStr := strconv.Itoa(pid)
	executor := &NativeExecutor{
		shortName: "native",
		pid: pid,
		pidStr: pidStr,
	}
	execute.Executors[executor.shortName] = executor
}

func (n *NativeExecutor) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	return n.runNativeExecutor(command, timeout)
}

func (n *NativeExecutor) String() string {
	return n.shortName
}

func (n *NativeExecutor) CheckIfAvailable() bool {
	return true
}

func (n *NativeExecutor) DownloadPayloadToMemory(payloadName string) bool {
	return false
}

func (n *NativeExecutor) UpdateBinary(newBinary string) {
	// pass
}

func (n *NativeExecutor) runNativeExecutor(command string, timeout int) (execute.CommandResults) {
	done := make(chan util.NativeCmdResult, 1)
	status := execute.SUCCESS_STATUS
	executionTimestamp := time.Now().UTC()
	methodName, methodArgs, err := getMethodAndArgs(command)
	if err != nil {
		errorBytes := []byte(fmt.Sprintf("Unable to parse command line: %s", err.Error()))
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: errorBytes,
			ExitCode: execute.ERROR_EXIT_CODE,
			StatusCode: execute.ERROR_STATUS,
			Pid: n.pidStr,
			ExecutionTimestamp: executionTimestamp,
		}
	}
	go func() {
		done <- runCommand(methodName, methodArgs)
	}()
	select {
	case <-time.After(time.Duration(timeout) * time.Second):
		errorBytes := []byte("Timeout reached, unable to end go routine")
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: errorBytes,
			ExitCode: execute.ERROR_EXIT_CODE,
			StatusCode: execute.ERROR_STATUS,
			Pid: n.pidStr,
			ExecutionTimestamp: executionTimestamp,
		}
	case cmdResult := <-done:
		stdoutBytes := cmdResult.Stdout
		stderrBytes := cmdResult.Stderr
		exitCode := cmdResult.ExitCode
		if cmdResult.Err != nil {
			status = execute.ERROR_STATUS
		}
		return execute.CommandResults{
			StandardOutput: stdoutBytes,
			StandardError: stderrBytes,
			ExitCode: exitCode,
			StatusCode: status,
			Pid: n.pidStr,
			ExecutionTimestamp: executionTimestamp,
		}
	}
}

func runCommand(method string, args []string) util.NativeCmdResult {
	var errMsg string
	if toCall, ok := util.NativeMethods[method]; ok {
		return toCall(args)
	}
	errMsg = fmt.Sprintf("Method name %s not supported.", method)
	return util.NativeCmdResult{
		Stdout: nil,
		Stderr: []byte(errMsg),
		Err: errors.New(errMsg),
		ExitCode: execute.ERROR_EXIT_CODE,
	}
}

func getMethodAndArgs(commandLine string) (string, []string, error) {
	if runtime.GOOS == "windows" {
		commandLine = strings.ReplaceAll(commandLine, "\\", "\\\\")
	}
	split, err := shlex.Split(commandLine)
	if err != nil {
		return "", nil, err
	}
	return split[0], split[1:], nil
}
