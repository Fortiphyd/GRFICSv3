#!/bin/bash
cwd=$(pwd)
cd shells
GOOS=windows go build -o ../payloads/manx.go-windows -ldflags="-s -w" manx.go
GOOS=linux go build -o ../payloads/manx.go-linux -ldflags="-s -w" manx.go
GOOS=darwin go build -o ../payloads/manx.go-darwin -ldflags="-s -w" manx.go
cd $cwd
