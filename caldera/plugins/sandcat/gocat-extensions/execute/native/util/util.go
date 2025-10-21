package util

import (
	"errors"
)

const (
	SUCCESS_EXIT_CODE 		= "0"
	PROCESS_ERROR_EXIT_CODE = "1"
	INPUT_ERROR_EXIT_CODE 	= "2"
)

type NativeCmdResult struct {
	Stdout []byte
	Stderr []byte
	Err error
	ExitCode string
}

type NativeMethod func ([]string) NativeCmdResult

// Map command names to golang functions
var NativeMethods map[string]NativeMethod


func init() {
	NativeMethods = make(map[string]NativeMethod)
}

func GenerateErrorResult(err error, exitCode string) NativeCmdResult {
	return NativeCmdResult{
		Stdout: nil,
		Stderr: []byte(err.Error()),
		Err: err,
		ExitCode: exitCode,
	}
}

func GenerateErrorResultFromString(errMsg string, exitCode string) NativeCmdResult {
	return NativeCmdResult{
		Stdout: nil,
		Stderr: []byte(errMsg),
		Err: errors.New(errMsg),
		ExitCode: exitCode,
	}
}