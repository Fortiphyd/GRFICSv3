// +build windows darwin linux

package shells

import (
	"os/exec"
	"runtime"

	"github.com/mitre/gocat/execute"
)

type PowershellCore struct {
	shortName string
	path string
	execArgs []string
}

func init() {
	var path string
	if runtime.GOOS == "windows" {
		path = "pwsh.exe"
	} else {
		path = "pwsh"
	}
	shell := &PowershellCore{
		shortName: "pwsh",
		path: path,
		execArgs: []string{"-C"},
	}
	if shell.CheckIfAvailable() {
		execute.Executors[shell.shortName] = shell
	}
}

func (p *PowershellCore) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	return runShellExecutor(*exec.Command(p.path, append(p.execArgs, command)...), timeout)
}

func (p *PowershellCore) String() string {
	return p.shortName
}

func (p *PowershellCore) CheckIfAvailable() bool {
	return checkExecutorInPath(p.path)
}

func (p *PowershellCore) DownloadPayloadToMemory(payloadName string) bool {
	return false
}

func (p *PowershellCore) UpdateBinary(newBinary string) {
	p.path = newBinary
}