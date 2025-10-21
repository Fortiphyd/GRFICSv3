// +build windows darwin linux

package shells

import (
	"os/exec"
	"runtime"
	"fmt"
	"strings"

	"github.com/mitre/gocat/execute"
)

type Python struct {
	shortName string
	path string
	execArgs []string
}

func init() {
	python3Detected := setExecutor("python3")
	python2Detected := setExecutor("python2")
	pythonDetected := setExecutor("python")
	if !(python3Detected || python2Detected || pythonDetected) {
		// if no versions found
		fmt.Print("No python versions detected\n")
	}
}

func setExecutor(name string) bool {
// Checks if python3, python2, or python is available on the system and
// sets the shell executor with the appropriate path
	var path string
	var val string
	var sName string
	
	if runtime.GOOS == "windows" {
		path = name + ".exe"
	} else {
		path = name
	}

	if name == "python" {
		val = checkVersion(name)
		sName = "python" + val
	} else {
		sName = name
	}

	shell := &Python {
		shortName: sName,
		path: path,
		execArgs: []string{"-c"},
	}
	if shell.CheckIfAvailable() {
		execute.Executors[shell.shortName] = shell
		fmt.Print(sName, " detected \n")
		return true
	} 
	return false
}

// checks the python version and returns the major version
func checkVersion(name string) string {
	var str_ver string
	version, err := exec.Command("python", "-c", "import platform; print(platform.python_version().split('.')[0])").CombinedOutput()
	str_ver = strings.TrimSpace(string(version))
	if err != nil {
		return ""
	}
	return str_ver
}

func (p *Python) Run(command string, timeout int, info execute.InstructionInfo) (execute.CommandResults) {
	return runShellExecutor(*exec.Command(p.path, append(p.execArgs, command)...), timeout)
}

func (p *Python) String() string {
	return p.shortName
}

func (p *Python) CheckIfAvailable() bool {
	return checkExecutorInPath(p.path)
} 

func (p *Python) DownloadPayloadToMemory(payloadName string) bool {
	return false
}

func (p *Python) UpdateBinary(newBinary string) {
	p.path = newBinary
}
