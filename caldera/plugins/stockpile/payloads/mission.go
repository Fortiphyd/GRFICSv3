package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

var modifiedFiles map[string]bool

func getFiles(searchpath string, extension string) []string {
	var files []string
	err := filepath.Walk(searchpath, func(path string, info os.FileInfo, err error) error {
		if filepath.Ext(path) == extension {
			files = append(files, path)
		}
		return nil
	})
	if err != nil {
		panic(err)
	}
	return files
}

func findNewFiles(files []string) []string {
	var filesToModify []string
	for _, file := range files {
		_, alreadyModified := modifiedFiles[file]
		if alreadyModified == false {
			modifiedFiles[file] = true
			filesToModify = append(filesToModify, file)
		}
	}
	return filesToModify
}

func modifyFiles(files []string, message string) []string {
	var successfulFiles []string
	for _, f := range files {
		file, err := os.OpenFile(f, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		defer file.Close()
		if err != nil {
			log.Println(err)
		}
		if _, err := file.WriteString(message); err != nil {
			log.Println(err)
		} else {
			successfulFiles = append(successfulFiles, f)
		}
	}
	return successfulFiles
}

func runMission(extension string, message string, rootDir string) {
	allFiles := getFiles(rootDir, extension)
	newFiles := findNewFiles(allFiles)
	successfulFiles := modifyFiles(newFiles, message)
	for _, f := range successfulFiles {
		fmt.Println(string(f))
	}
}

func main() {
	duration := flag.String("duration", "60", "How long the mission should run (seconds)")
	extension := flag.String("extension", ".caldera", "What extension are we searching for")
	message := flag.String("message", "caldera wuz here", "What message should be inserted into the files")
	dir := flag.String("dir", "/", "Where should Caldera start looking for files")
	flag.Parse()

	modifiedFiles = make(map[string]bool)
	fmt.Printf("Running mission for %s seconds\n", *duration)
	i, _ := strconv.Atoi(*duration)
	expires := time.Now().Add(time.Duration(i) * time.Second)
	for time.Now().Sub(expires) < 0 {
		runMission(*extension, *message, *dir)
		time.Sleep(time.Duration(3) * time.Second)
	}
	fmt.Println("Done with mission")
}

var key = "L26FTC4BJ8U0IMJ6SFLS0961ZGQJKA"
