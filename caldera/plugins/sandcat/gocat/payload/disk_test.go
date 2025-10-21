package payload

import (
	"bytes"
	"os"
	"reflect"
	"testing"
)

const (
	FILE_NAME = "dummyfile.txt"
)

var (
	PAYLOAD_BYTES = []byte("sample payload data")
)

func TestWriteToDisk(t *testing.T) {
	loc, err := WriteToDisk(FILE_NAME, PAYLOAD_BYTES)
	if err != nil {
		t.Errorf("Failed to write file to disk: %s", err.Error())
		return
	}
	if loc != FILE_NAME {
		t.Errorf("Got %s as returned file location; expected %s", loc, FILE_NAME)
	}
	contents, err := os.ReadFile(loc)
	if err != nil {
		t.Errorf("Failed to read file on disk: %s", err.Error())
	}
	if !bytes.Equal(contents, PAYLOAD_BYTES) {
		t.Errorf("Got %s as written file bytes; expected %s", string(contents[:]), string(PAYLOAD_BYTES[:]))
	}
	clearFile(t, FILE_NAME)
}

func TestWriteToDiskAlreadyExisting(t *testing.T) {
	err := touchFile(FILE_NAME)
	if err != nil {
		t.Errorf("Failed to touch file %s: %s",FILE_NAME, err.Error())
		return
	}
	loc, err := WriteToDisk(FILE_NAME, PAYLOAD_BYTES)
	if err != nil {
		t.Errorf("Unexpected error for already existing payload: %s", err.Error())
	}
	if loc != FILE_NAME {
		t.Errorf("Got %s as returned file location; expected %s", loc, FILE_NAME)
	}
	clearFile(t, FILE_NAME)
}

func TestCheckIfOnDisk(t *testing.T) {
	err := touchFile(FILE_NAME)
	if err != nil {
		t.Errorf("Failed to touch file %s: %s",FILE_NAME, err.Error())
		return
	}
	toCheck := []string{
		"payload1",
		"payload2",
		FILE_NAME,
		"payload3",
	}
	want := []string{
		"payload1",
		"payload2",
		"payload3",
	}
	missing := CheckIfOnDisk(toCheck)
	clearFile(t, FILE_NAME)
	if !reflect.DeepEqual(missing, want) {
		t.Errorf("Got %v, expected %v", missing, want)
	}
}

func TestFileExists(t *testing.T) {
	if FileExists(FILE_NAME) {
		t.Errorf("File %s should not exist", FILE_NAME)
	}
	err := touchFile(FILE_NAME)
	if err != nil {
		t.Errorf("Failed to touch file %s: %s",FILE_NAME, err.Error())
		return
	}
	if !FileExists(FILE_NAME) {
		t.Errorf("File %s should exist", FILE_NAME)
	}
	clearFile(t, FILE_NAME)
}

func clearFile(t *testing.T, path string) {
	if err := os.Remove(path); err != nil {
		t.Errorf("Failed to clear file after test: %s", err.Error())
	}
}

func touchFile(path string) error {
	file, err := os.OpenFile(path, os.O_CREATE, 0700)
	if err != nil {
		return err
	}
	return file.Close()
}
