package testutil

import (
	"testing"

	"github.com/mitre/gocat/execute/native/util"
)

func VerifyResult(t *testing.T, result util.NativeCmdResult, expectedStdout, expectedStderr, expectedErrMsg string) {
	if string(result.Stdout) != expectedStdout {
		t.Errorf("Expected stdout of '%s', got: %s", expectedStdout, string(result.Stdout))
	}
	if string(result.Stderr) != expectedStderr {
		t.Errorf("Expected stderr of '%s', got: %s", expectedStderr, string(result.Stderr))
	}
	if len(expectedErrMsg) > 0 {
		if result.Err == nil {
			t.Errorf("Expected error, received none.")
		} else if result.Err.Error() != expectedErrMsg {
			t.Errorf("Expected error message '%s', got: %s", expectedErrMsg, result.Err.Error())
		}
	} else if result.Err != nil {
		t.Errorf("Expected no error, got %v", result.Err)
	}
}