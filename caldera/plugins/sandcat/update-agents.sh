#!/bin/bash
# generates payloads for each os

function build() {
GOOS=windows go build -o ../payloads/sandcat.go-windows -ldflags="-s -w" sandcat.go
GOOS=linux go build -o ../payloads/sandcat.go-linux -ldflags="-s -w" sandcat.go
GOOS=darwin go build -o ../payloads/sandcat.go-darwin -ldflags="-s -w" sandcat.go
GOOS=darwin GOARCH=arm64 go build -o ../payloads/sandcat.go-darwin-arm64 -ldflags="-s -w" sandcat.go
}
cd gocat && build
cd ..
