package discovery

import (
	"fmt"
	"os"
	"strings"

	"github.com/mitre/gocat/execute/native/util"
)

func init() {
	util.NativeMethods["SystemInfo"] = GetSystemInfo
	util.NativeMethods["systeminfo"] = GetSystemInfo
}

type infoGetterFunc func() (string, error)

// Returns information about the current system. Ignores any provided args
func GetSystemInfo(args []string) util.NativeCmdResult {
	return util.NativeCmdResult{
		Stdout: []byte(getSystemInfo()),
		Stderr: nil,
		Err: nil,
		ExitCode: util.SUCCESS_EXIT_CODE,
	}
}

func getHostnameLine(hostnameGetterFunc infoGetterFunc) string {
	return getInfoLine("Host Name", hostnameGetterFunc)
}

func getHostname() (string, error) {
	return os.Hostname()
}

func getOsNameLine(osNameGetterFunc infoGetterFunc) string {
	return getInfoLine("OS Name", osNameGetterFunc)
}

func getOsVersionLine(osVersionGetterFunc infoGetterFunc) string {
	return getInfoLine("OS Version", osVersionGetterFunc)
}

func getHardwareTypeLine(hardwareTypeGetterFunc infoGetterFunc) string {
	return getInfoLine("Hardware Type", hardwareTypeGetterFunc)
}

func getInfoLine(keyName string, getterFunc infoGetterFunc) string {
	infoValue, err := getterFunc()
	if err != nil {
		return formatInfoLine("ERROR GETTING " + strings.ToUpper(keyName), err.Error())
	}
	return formatInfoLine(keyName, infoValue)
}

func formatInfoLine(key, value string) string {
	return fmt.Sprintf("%-*s %s", keyWidth, key + ": ", value)
}
