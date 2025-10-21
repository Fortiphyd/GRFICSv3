package shells

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"
	"github.com/google/shlex"

	"github.com/mitre/gocat/execute"
	"github.com/mitre/gocat/output"
)

// Compatible with the exec.Cmd struct
type ProcCmdHandle interface {
	Start() error
}

type CwdGetter func() (string, error)
type OsGetter func() string
type PidGetter func() int
type FileDeleter func(string) error
type TimeGenerator func() time.Time
type StandardCmdRunner func(string, []string, int) (execute.CommandResults)
type CmdHandleRunner func (*exec.Cmd) error // wrapper for exec.Cmd.Run()
type CmdHandlePidGetter func(*exec.Cmd) int // wrapper for handle.Process.Pid


type Proc struct {
	name string
	currDir string
	osName string
	pidStr string
	fileDeleter FileDeleter
	timeStampGenerator TimeGenerator
	standardCmdRunner StandardCmdRunner
	cmdHandleRunner CmdHandleRunner
	cmdHandlePidGetter CmdHandlePidGetter
}

func getOsName() string {
	return runtime.GOOS
}

func getUtcTime() time.Time {
	return time.Now().UTC()
}

func startCmdHandle(handle *exec.Cmd) error {
	return handle.Start()
}

func getCmdPid(handle *exec.Cmd) int {
	return handle.Process.Pid
}

type ProcFunctionHandles struct {
	cwdGetter CwdGetter
	osGetter OsGetter
	pidGetter PidGetter
	fileDeleter FileDeleter
	timeStampGenerator TimeGenerator
	standardCmdRunner StandardCmdRunner
	cmdHandleRunner CmdHandleRunner
	cmdHandlePidGetter CmdHandlePidGetter
}

func GenerateProcExecutor(funcHandles *ProcFunctionHandles) *Proc {
	cwd, _ := funcHandles.cwdGetter()
	osName := funcHandles.osGetter()
	pid := funcHandles.pidGetter()
	return &Proc{
		name: "proc",
		currDir: cwd,
		osName: osName,
		pidStr: strconv.Itoa(pid),
		fileDeleter: funcHandles.fileDeleter,
		timeStampGenerator: funcHandles.timeStampGenerator,
		standardCmdRunner: funcHandles.standardCmdRunner,
		cmdHandleRunner: funcHandles.cmdHandleRunner,
		cmdHandlePidGetter: funcHandles.cmdHandlePidGetter,
	}
}

func init() {
	procFuncHandles := &ProcFunctionHandles{
		cwdGetter: os.Getwd,
		osGetter: getOsName,
		pidGetter: os.Getpid,
		fileDeleter: os.Remove,
		timeStampGenerator: getUtcTime,
		standardCmdRunner: runStandardCmd,
		cmdHandleRunner: startCmdHandle,
		cmdHandlePidGetter: getCmdPid,
	}
	executor := GenerateProcExecutor(procFuncHandles)
	execute.Executors[executor.name] = executor
}

func (p *Proc) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	exePath, exeArgs, err := p.getExeAndArgs(command)
	if err != nil {
		errMsg := fmt.Sprintf("[!] Error parsing command line: %s", err.Error())
		output.VerbosePrint(errMsg)
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: []byte(errMsg),
			ExitCode: execute.ERROR_EXIT_CODE,
			StatusCode: execute.ERROR_STATUS,
			Pid: execute.ERROR_PID,
			ExecutionTimestamp: p.timeStampGenerator(),
		}
	}
	output.VerbosePrint(fmt.Sprintf("[*] Starting process %s with args %v", exePath, exeArgs))
	if exePath == "del" || exePath == "rm" {
		return p.deleteFiles(exeArgs)
	} else if exePath == "exec-background" {
		return p.runBackgroundCmd(exeArgs[0], exeArgs[1:])
	}
	return p.standardCmdRunner(exePath, exeArgs, timeout)
}

func (p *Proc) String() string {
	return p.name
}

func (p *Proc) CheckIfAvailable() bool {
	return true
}

func (p *Proc) DownloadPayloadToMemory(payloadName string) bool {
	return false
}

func (p *Proc) getExeAndArgs(commandLine string) (string, []string, error) {
	if p.osName == "windows" {
		commandLine = strings.ReplaceAll(commandLine, "\\", "\\\\")
	}
	split, err := shlex.Split(commandLine)
	if err != nil {
		return "", nil, err
	}
	return split[0], split[1:], nil
}

func (p *Proc) UpdateBinary(newBinary string) {
	return
}

func (p *Proc) deleteFiles(files []string) (execute.CommandResults) {
	var outputMessages []string
	var errorMessages []string
	var msg string
	var err error
	exitCode := execute.SUCCESS_EXIT_CODE
	status := execute.SUCCESS_STATUS
	executionTimestamp := p.timeStampGenerator()
	for _, toDelete := range files {
		err = p.fileDeleter(toDelete)
		if err != nil {
			msg = fmt.Sprintf("Failed to remove %s: %s", toDelete, err.Error())
			status = execute.ERROR_STATUS
			exitCode = execute.ERROR_EXIT_CODE
			errorMessages = append(errorMessages, msg)
		} else {
			msg = fmt.Sprintf("Removed file %s.", toDelete)
			outputMessages = append(outputMessages, msg)
		}
	}
	return execute.CommandResults{
		StandardOutput: []byte(strings.Join(outputMessages, "\n")),
		StandardError: []byte(strings.Join(errorMessages, "\n")),
		ExitCode: exitCode,
		StatusCode: status,
		Pid: p.pidStr,
		ExecutionTimestamp: executionTimestamp,
	}
}

func runStandardCmd(exePath string, exeArgs []string, timeout int) (execute.CommandResults) {
	return runShellExecutor(*exec.Command(exePath, append(exeArgs)...), timeout)
}

func (p *Proc) runBackgroundCmd(exePath string, exeArgs []string) (execute.CommandResults) {
	handle := exec.Command(exePath, append(exeArgs)...)
	err := p.cmdHandleRunner(handle)
	if err != nil {
		return execute.CommandResults{
			StandardOutput: []byte{},
			StandardError: []byte(err.Error()),
			ExitCode: execute.ERROR_EXIT_CODE,
			StatusCode: execute.ERROR_STATUS,
			Pid: execute.ERROR_PID,
			ExecutionTimestamp: p.timeStampGenerator(),
		}
	}
	pid := p.cmdHandlePidGetter(handle)
	pidStr := strconv.Itoa(pid)
	retMsg := fmt.Sprintf("Executed background process %s with PID %d and args: %s", exePath, pid, strings.Join(exeArgs, ", "))
	return execute.CommandResults{
		StandardOutput: []byte(retMsg),
		StandardError: []byte{},
		ExitCode: execute.SUCCESS_EXIT_CODE,
		StatusCode: execute.SUCCESS_STATUS,
		Pid: pidStr,
		ExecutionTimestamp: p.timeStampGenerator(),
	}
}