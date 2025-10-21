// +build !windows

package privdetect

import (
	"os"
)

func Privlevel() string{
	uid := os.Geteuid()

	if uid ==0 {
		return "Elevated"
	} else {
		return "User"
	}
}
