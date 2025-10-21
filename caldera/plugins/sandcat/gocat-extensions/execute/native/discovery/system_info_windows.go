// +build windows

package discovery

import (
	"fmt"
	"runtime"
	"strings"

	"golang.org/x/sys/windows"
)

const keyWidth = 26

var versionInfo *windows.OsVersionInfoEx

func getSystemInfo() string {
	outputLines := []string{
		getHostnameLine(getHostname),
		getOsNameLine(getOsName),
		getOsVersionLine(getOsVersion),
		getInfoLine("OS Service Pack", getOsServicePack),
		getHardwareTypeLine(getHardwareType),
	}
	return strings.Join(outputLines[:], "\n")
}

func getOsVersion() (string, error) {
	getVersionInfo()
	verMajor := versionInfo.MajorVersion
	verMinor := versionInfo.MinorVersion
	buildNumber := versionInfo.BuildNumber

	return fmt.Sprintf("%d.%d, Build %d", verMajor, verMinor, buildNumber), nil
}

func getOsName() (string, error) {
	return "Windows", nil
}

func getOsServicePack() (string, error) {
	getVersionInfo()
	servicePackStr := intArrayToStr(versionInfo.CsdVersion[:])
	if len(servicePackStr) > 0 {
		return servicePackStr, nil
	}
	return "No service pack detected.", nil
}

func getVersionInfo() {
	if versionInfo == nil {
		versionInfo = windows.RtlGetVersion()
	}
}

func getHardwareType() (string, error) {
	return runtime.GOARCH, nil
}

func intArrayToStr(intArr []uint16) string {
	var byteSlice []byte
	for _, v := range intArr {
		if v > 0 {
			byteSlice = append(byteSlice, byte(v))
		}
	}
	return string(byteSlice)
}
