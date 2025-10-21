// +build !windows

package discovery

import (
	"strings"

	"golang.org/x/sys/unix"
)

const keyWidth = 25

var obtainedUnameInfo bool
var unameInfo unix.Utsname

func init() {
	unameInfo = unix.Utsname{}
	obtainedUnameInfo = false
}

func getSystemInfo() string {
	outputLines := []string{
		getHostnameLine(getHostname),
		getOsNameLine(getOsName),
		getOsVersionLine(getOsVersion),
		getInfoLine("OS Release", getOsRelease),
		getHardwareTypeLine(getHardwareType),
	}
	return strings.Join(outputLines[:], "\n")
}

// Reference: https://stackoverflow.com/a/53197771
func getOsVersion() (string, error) {
	if err := getUnameInfo(); err != nil {
		return "", err
	}
	return string(unameInfo.Version[:]), nil
}

func getOsRelease() (string, error) {
	if err := getUnameInfo(); err != nil {
		return "", err
	}
	return string(unameInfo.Release[:]), nil
}

func getUnameInfo() error {
	if !obtainedUnameInfo {
		if err := unix.Uname(&unameInfo); err != nil {
			return err
		}
		obtainedUnameInfo = true
	}
	return nil
}

func getOsName() (string, error) {
	if err := getUnameInfo(); err != nil {
		return "", err
	}
	return string(unameInfo.Sysname[:]), nil
}

func getHardwareType() (string, error) {
	if err := getUnameInfo(); err != nil {
		return "", err
	}
	return string(unameInfo.Machine[:]), nil
}
