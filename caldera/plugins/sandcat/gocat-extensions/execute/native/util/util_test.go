package util_test

import (
	"errors"
	"testing"

	"github.com/mitre/gocat/execute/native/testutil"
	"github.com/mitre/gocat/execute/native/util"
)

func TestGenerateErrorResult(t *testing.T) {
	want := "test error msg"
	result := util.GenerateErrorResult(errors.New(want), util.PROCESS_ERROR_EXIT_CODE)
	testutil.VerifyResult(t, result, "", want, want)
}

func TestGenerateErrorResultFromString(t *testing.T) {
	want := "test error msg"
	result := util.GenerateErrorResultFromString(want, util.PROCESS_ERROR_EXIT_CODE)
	testutil.VerifyResult(t, result, "", want, want)
}