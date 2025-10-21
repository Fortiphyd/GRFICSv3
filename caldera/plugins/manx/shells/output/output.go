package output

import (
    "fmt"
)

var VerboseEnabled = false

func VerbosePrint(formatted string) {
    if VerboseEnabled {
        fmt.Println(formatted)
    }
}

func SetVerbose(v bool) {
    VerboseEnabled = v
}
