package util

import (
	"fmt"
	"time"
	"os/exec"
	"strings"
)

type ListFlags []string

func (l *ListFlags) String() string {
	return fmt.Sprint(*l)
}

func (l *ListFlags) Set(value string) error {
	for _, item := range strings.Split(value, ",") {
		*l = append(*l, item)
	}
	return nil
}

//DetermineExecutors looks for available execution engines
func DetermineExecutors(executors []string, platform string, arch string) []string {
	platformExecutors := map[string]map[string][]string {
		"windows": {
			"file": {"powershell.exe", "cmd.exe", "pwsh.exe"},
			"executor": {"psh", "cmd", "pwsh"},
		},
		"linux": {
			"file": {"sh", "pwsh"},
			"executor": {"sh", "pwsh"},
		},
		"darwin": {
			"file": {"sh", "pwsh", "osascript"},
			"executor": {"sh", "pwsh", "osa"},
		},
	}
	if executors == nil {
		for platformKey, platformValue := range platformExecutors {
			if platform == platformKey {
				for i := range platformValue["file"] {
					if checkIfExecutorAvailable(platformValue["file"][i]) {
						executors = append(executors, platformExecutors[platformKey]["executor"][i])
					}
				}
			}
		}
	}
	return executors
}

func checkIfExecutorAvailable(executor string) bool {
	_, err := exec.LookPath(executor)
	return err == nil
}

func GetFormattedTimestamp(timestamp time.Time, dateFormat string) (string) {
    return timestamp.Format(dateFormat)
}
