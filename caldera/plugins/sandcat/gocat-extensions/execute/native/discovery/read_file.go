package discovery

import (
	"bytes"
	"errors"
	"os"
	"strings"

	"github.com/mitre/gocat/execute/native/util"
)

func init() {
	util.NativeMethods["cat"] = ReadFileContents
	util.NativeMethods["Get-FileContents"] = ReadFileContents
	util.NativeMethods["type"] = ReadFileContents
}

// Reads specified files and returns their contents.
func ReadFileContents(fileList []string) util.NativeCmdResult {
	if len(fileList) == 0 {
		stderr := "No file(s) provided."
		return util.NativeCmdResult{
			Stdout: nil,
			Stderr: []byte(stderr),
			Err: errors.New(string(stderr)),
			ExitCode: util.INPUT_ERROR_EXIT_CODE,
		}
	}
	return readFiles(fileList)
}

func readFiles(fileList []string) util.NativeCmdResult {
	var resultErr error
	var stderr string
	var stdout []byte
	var stdoutLines [][]byte
	var stderrLines []string
	for _, filePath := range fileList {
		stdout, stderr = readSingleFile(filePath)
		if stdout != nil {
			stdoutLines = append(stdoutLines, stdout)
		}
		if len(stderr) > 0 {
			stderrLines = append(stderrLines, stderr)
		}
	}
	exitCode := util.SUCCESS_EXIT_CODE
	if len(stderrLines) > 0 {
		stderr = strings.Join(stderrLines[:], "\n")
		resultErr = errors.New(stderr)
		exitCode = util.PROCESS_ERROR_EXIT_CODE
	}
	return util.NativeCmdResult{
		Stdout: bytes.Join(stdoutLines, []byte("\n")),
		Stderr: []byte(stderr),
		Err: resultErr,
		ExitCode: exitCode,
	}
}

func readSingleFile(filePath string) ([]byte, string) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err.Error()
	}
	return data, ""
}