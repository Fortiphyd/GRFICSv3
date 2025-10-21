// +build windows

package shells

import (
	"github.com/mitre/gocat/execute"
	"os/exec"
	"strings"
	"syscall"
)

type Cmd struct {
	shortName string
	path string
	execArgs []string
}

func init() {
	shell := &Cmd{
		shortName: "cmd",
		path: "cmd.exe",
		execArgs: []string{"/C"},
	}
	if shell.CheckIfAvailable() {
		execute.Executors[shell.shortName] = shell
	}
}

func (c *Cmd) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	cmd := *exec.Command(c.path)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	commandLineComponents := append(append([]string{c.path}, c.execArgs...), command)
	cmd.SysProcAttr.CmdLine = strings.Join(commandLineComponents, " ")
	return runShellExecutor(cmd, timeout)
}

func (c *Cmd) String() string {
	return c.shortName
}

func (c *Cmd) CheckIfAvailable() bool {
	return checkExecutorInPath(c.path)
}

func (c* Cmd) DownloadPayloadToMemory(payloadName string) bool {
	return false
}

func (c* Cmd) UpdateBinary(newBinary string) {
	c.path = newBinary
}
