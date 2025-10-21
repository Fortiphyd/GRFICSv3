package shells

import (
	"errors"
	"fmt"
	"os/exec"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/mitre/gocat/execute"
)

const MOCK_CWD = "/mock/working/dir"
const PROC_NAME = "proc"
const DUMMY_ERROR_MSG = "dummy error msg"
const DUMMY_PID = 123
const DUMMY_PID_STR = "123"
const WINDOWS_OS = "windows"
const LINUX_OS = "linux"
const DUMMY_OS = "DummyOS"
const TEST_TIMEOUT = 10
var TEST_TIME = time.Date(2000, time.November, 10, 15, 0, 0, 0, time.UTC)

func MockGetCwd() (string, error) {
	return MOCK_CWD, nil
}

func MockGetWindowsOsName() string {
	return WINDOWS_OS
}

func MockGetLinuxOsName() string {
	return LINUX_OS
}

func MockGetDummyOsName() string {
	return DUMMY_OS
}

func MockPidGetter() int {
	return DUMMY_PID
}

func MockFileDeleter(file string) error {
	return nil
}

func MockFileDeleteFail(file string) error {
	return errors.New(DUMMY_ERROR_MSG)
}

func MockTimeGenerator() time.Time {
	return TEST_TIME
}

func MockStandardCmdRunner(name string, args []string, timeout int) (execute.CommandResults) {
	return execute.CommandResults{[]byte(fmt.Sprintf("%s; %s; %d", name, strings.Join(args, ","), timeout)), []byte{}, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME}
}

func MockCmdHandleRunner(handle *exec.Cmd) error {
	return nil
}

func MockCmdHandleRunnerFail(handle *exec.Cmd) error {
	return errors.New(DUMMY_ERROR_MSG)
}

func MockGetHandlePid(handle *exec.Cmd) int {
	return DUMMY_PID
}

func DummyInstructionInfo() execute.InstructionInfo {
	return execute.InstructionInfo{
		Profile: nil,
		Instruction: nil,
		OnDiskPayloads: nil,
		InMemoryPayloads: nil,
	}
}

func compareFunctionAddr(t *testing.T, outputFunc interface{}, wantFunc interface{}) {
	outputFuncAddr := fmt.Sprintf("%v", outputFunc)
	wantFuncAddr := fmt.Sprintf("%v", wantFunc)
	if outputFuncAddr != wantFuncAddr {
		t.Errorf("got '%s' func address; expected '%s'", outputFuncAddr, wantFuncAddr)
	}
}

func generateProcExecutor(osGetter OsGetter) *Proc {
	procFuncHandles := &ProcFunctionHandles{
		cwdGetter: MockGetCwd,
		osGetter: osGetter,
		pidGetter: MockPidGetter,
		fileDeleter: MockFileDeleter,
		timeStampGenerator: MockTimeGenerator,
		standardCmdRunner: MockStandardCmdRunner,
		cmdHandleRunner: MockCmdHandleRunner,
		cmdHandlePidGetter: MockGetHandlePid,
	}
	return GenerateProcExecutor(procFuncHandles)
}

func TestGenerateProcExecutor(t *testing.T) {
	want := &Proc{
		currDir: MOCK_CWD,
		name: PROC_NAME,
		osName: DUMMY_OS,
		pidStr: DUMMY_PID_STR,
		fileDeleter: MockFileDeleter,
		timeStampGenerator: MockTimeGenerator,
		standardCmdRunner: MockStandardCmdRunner,
		cmdHandleRunner: MockCmdHandleRunner,
		cmdHandlePidGetter: MockGetHandlePid,
	}
	generated := generateProcExecutor(MockGetDummyOsName)
	if generated.currDir != want.currDir {
		t.Errorf("got '%s' as executor's current dir; expected '%s'", generated.currDir, want.currDir)
	}
	if generated.name != want.name {
		t.Errorf("got '%s' as executor's name; expected '%s'", generated.name, want.name)
	}
	if generated.osName != want.osName {
		t.Errorf("got '%s' as executor's OS; expected '%s'", generated.osName, want.osName)
	}
	if generated.pidStr != want.pidStr {
		t.Errorf("got '%s' as executor's process ID string; expected '%s'", generated.pidStr, want.pidStr)
	}
	compareFunctionAddr(t, generated.fileDeleter, want.fileDeleter)
	compareFunctionAddr(t, generated.timeStampGenerator, want.timeStampGenerator)
	compareFunctionAddr(t, generated.standardCmdRunner, want.standardCmdRunner)
	compareFunctionAddr(t, generated.cmdHandleRunner, want.cmdHandleRunner)
	compareFunctionAddr(t, generated.cmdHandlePidGetter, want.cmdHandlePidGetter)
}

func TestProcString(t *testing.T) {
	p := generateProcExecutor(MockGetDummyOsName)
	want := PROC_NAME
	output := p.String()
	if output != want {
		t.Errorf("got '%s'; expected '%s'", output, want)
	}
}

func TestProcCheckIfAvailable(t *testing.T) {
	p := generateProcExecutor(MockGetDummyOsName)
	want := true
	output := p.CheckIfAvailable()
	if output != want {
		t.Errorf("got '%t'; expected '%t'", output, want)
	}
}

func TestProcDownloadPayloadToMemory(t *testing.T) {
	p := generateProcExecutor(MockGetDummyOsName)
	want := false
	output := p.DownloadPayloadToMemory("dummy")
	if output != want {
		t.Errorf("got '%t'; expected '%t'", output, want)
	}
}

func TestGetExeAndArgsWindowsNoArgs(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "C:\\Users\\Public\\executable.exe"
	wantCmd := cmd
	outputCmd, outputArgs, err := p.getExeAndArgs(cmd)
	if outputCmd != wantCmd {
		t.Errorf("got '%s'; expected '%s'", outputCmd, wantCmd)
	}
	if len(outputArgs) != 0 {
		t.Errorf("got nonempty args %v; expected empty args", outputArgs)
	}
	if err != nil {
		t.Errorf("got non-nil error with message '%s'; expected no error", err.Error())
	}
}

func TestGetExeAndArgsWindowsNoPath(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "executable.exe arg1 arg2 \"arg with space\" -45"
	wantCmd := "executable.exe"
	wantArgs := []string{"arg1", "arg2", "arg with space", "-45"}
	outputCmd, outputArgs, err := p.getExeAndArgs(cmd)
	if outputCmd != wantCmd {
		t.Errorf("got '%s'; expected '%s'", outputCmd, wantCmd)
	}
	if !reflect.DeepEqual(outputArgs, wantArgs) {
		t.Errorf("got '%v'; expected '%v'", outputArgs, wantArgs)
	}
	if err != nil {
		t.Errorf("got non-nil error with message '%s'; expected no error", err.Error())
	}
}

func TestGetExeAndArgsLinuxNoArgs(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "/bin/bash"
	wantCmd := cmd
	outputCmd, outputArgs, err := p.getExeAndArgs(cmd)
	if outputCmd != wantCmd {
		t.Errorf("got '%s'; expected '%s'", outputCmd, wantCmd)
	}
	if len(outputArgs) != 0 {
		t.Errorf("got nonempty args %v; expected empty args", outputArgs)
	}
	if err != nil {
		t.Errorf("got non-nil error with message '%s'; expected no error", err.Error())
	}
}

func TestGetExeAndArgsLinuxNoPath(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "binary -c arg1 arg2 \"arg with space\" -45 > file.txt"
	wantCmd := "binary"
	wantArgs := []string{"-c", "arg1", "arg2", "arg with space", "-45", ">", "file.txt"}
	outputCmd, outputArgs, err := p.getExeAndArgs(cmd)
	if outputCmd != wantCmd {
		t.Errorf("got '%s'; expected '%s'", outputCmd, wantCmd)
	}
	if !reflect.DeepEqual(outputArgs, wantArgs) {
		t.Errorf("got '%v'; expected '%v'", outputArgs, wantArgs)
	}
	if err != nil {
		t.Errorf("got non-nil error with message '%s'; expected no error", err.Error())
	}
}

func testAndValidateCmd(t *testing.T, p *Proc, cmd, wantOutMsg, wantErrMsg, wantExitCode, wantStatus, wantPid string, wantTimestamp time.Time) {
	var commandResults execute.CommandResults
	commandResults = p.Run(cmd, TEST_TIMEOUT, DummyInstructionInfo())
	outputMsgBytes := commandResults.StandardOutput
	errorMsgBytes := commandResults.StandardError
	exitCode := commandResults.ExitCode
	outputStatus := commandResults.StatusCode
	outputPid := commandResults.Pid
	outputTimestamp := commandResults.ExecutionTimestamp

	outputMsg := string(outputMsgBytes)
	errorMsg := string(errorMsgBytes)
	if outputMsg != wantOutMsg {
		t.Errorf("got '%s'; expected '%s'", outputMsg, wantOutMsg)
	}
	if errorMsg != wantErrMsg {
		t.Errorf("got '%s'; expected '%s'", errorMsg, wantErrMsg)
	}
	if exitCode != wantExitCode {
		t.Errorf("got '%s'; expected '%s'", exitCode, wantExitCode)
	}
	if outputStatus != wantStatus {
		t.Errorf("got '%s'; expected '%s'", outputStatus, wantStatus)
	}
	if outputPid != wantPid {
		t.Errorf("got '%s'; expected '%s'", outputPid, wantPid)
	}
	if !outputTimestamp.Equal(wantTimestamp) {
		t.Errorf("got '%s'; expected '%s'", outputTimestamp.String(), wantTimestamp.String())
	}
}

func TestDeleteSingleFileWindows(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "del C:\\path\\to\\file"
	wantOutMsg := "Removed file C:\\path\\to\\file."
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestDeleteMultipleFileWindows(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "del C:\\path\\to\\file1 .\\file2 file3.txt"
	wantOutMsg := "Removed file C:\\path\\to\\file1.\nRemoved file .\\file2.\nRemoved file file3.txt."
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestDeleteMultipleFilesFailureWindows(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	p.fileDeleter = MockFileDeleteFail
	cmd := "del C:\\path\\to\\file1 .\\file2 file3.txt"
	wantOutMsg := ""
	wantErrMsg := fmt.Sprintf("Failed to remove C:\\path\\to\\file1: %s\nFailed to remove .\\file2: %s\nFailed to remove file3.txt: %s",
						   DUMMY_ERROR_MSG, DUMMY_ERROR_MSG, DUMMY_ERROR_MSG)
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.ERROR_EXIT_CODE, execute.ERROR_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestDeleteSingleFileLinux(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "del /path/to/file"
	wantOutMsg := "Removed file /path/to/file."
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestDeleteMultipleFileLinux(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "del /path/to/file1 ./file2 file3.txt"
	wantOutMsg := "Removed file /path/to/file1.\nRemoved file ./file2.\nRemoved file file3.txt."
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestDeleteMultipleFilesFailureLinux(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	p.fileDeleter = MockFileDeleteFail
	cmd := "del /path/to/file1 ./file2 file3.txt"
	wantOutMsg := ""
	wantErrMsg := fmt.Sprintf("Failed to remove /path/to/file1: %s\nFailed to remove ./file2: %s\nFailed to remove file3.txt: %s",
						   DUMMY_ERROR_MSG, DUMMY_ERROR_MSG, DUMMY_ERROR_MSG)
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.ERROR_EXIT_CODE, execute.ERROR_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestRunCmdWindows(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "C:\\path\\to\\executable.exe arg1 arg2 \"arg with space\" -45 .\\path\\to\\file"
	wantOutMsg := fmt.Sprintf("C:\\path\\to\\executable.exe; arg1,arg2,arg with space,-45,.\\path\\to\\file; %d", TEST_TIMEOUT)
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestRunCmdLinux(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "/path/to/executable arg1 arg2 \"arg with space\" -flag -45 ../path/to/file"
	wantOutMsg := fmt.Sprintf("/path/to/executable; arg1,arg2,arg with space,-flag,-45,../path/to/file; %d", TEST_TIMEOUT)
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestRunBackgroundCmdWindows(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	cmd := "exec-background C:\\path\\to\\executable.exe arg1 arg2 \"arg with space\" -45 .\\path\\to\\file"
	wantOutMsg := "Executed background process C:\\path\\to\\executable.exe with PID 123 and args: arg1, arg2, arg with space, -45, .\\path\\to\\file"
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestRunBackgroundCmdLinux(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	cmd := "exec-background /path/to/executable arg1 arg2 \"arg with space\" -flag -45 ../path/to/file"
	wantOutMsg := "Executed background process /path/to/executable with PID 123 and args: arg1, arg2, arg with space, -flag, -45, ../path/to/file"
	wantErrMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, wantErrMsg, execute.SUCCESS_EXIT_CODE, execute.SUCCESS_STATUS, DUMMY_PID_STR, TEST_TIME)
}

func TestRunBackgroundCmdWindowsError(t *testing.T) {
	p := generateProcExecutor(MockGetWindowsOsName)
	p.cmdHandleRunner = MockCmdHandleRunnerFail
	cmd := "exec-background C:\\path\\to\\executable.exe arg1 arg2 \"arg with space\" -45 .\\path\\to\\file"
	wantOutMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, DUMMY_ERROR_MSG, execute.ERROR_EXIT_CODE, execute.ERROR_STATUS, execute.ERROR_PID, TEST_TIME)
}

func TestRunBackgroundCmdLinuxError(t *testing.T) {
	p := generateProcExecutor(MockGetLinuxOsName)
	p.cmdHandleRunner = MockCmdHandleRunnerFail
	cmd := "exec-background /path/to/executable arg1 arg2 \"arg with space\" -flag -45 ../path/to/file"
	wantOutMsg := ""
	testAndValidateCmd(t, p, cmd, wantOutMsg, DUMMY_ERROR_MSG, execute.ERROR_EXIT_CODE, execute.ERROR_STATUS, execute.ERROR_PID, TEST_TIME)
}