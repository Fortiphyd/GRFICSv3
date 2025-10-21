package aws

import (
	"context"
	"errors"
	"io"
	"os"
	"testing"

	"github.com/aws/aws-sdk-go/aws/awserr"
	"github.com/aws/aws-sdk-go/aws/request"

	"github.com/mitre/gocat/execute/native/testutil"
)

var (
	errMsg = "Dummy error msg"
	fileNotFoundMsg = "File not found"
)

func mockOpenFile(path string) (*os.File, error) {
	return nil, nil
}

func mockOpenFileNotFound(path string) (*os.File, error) {
	return nil, errors.New(fileNotFoundMsg)
}

func mockUploadDataNoErr(ctx context.Context, region, bucket, key string, fileReadSeeker io.ReadSeeker) error {
	return nil
}

func mockUploadDataTimeoutErr(ctx context.Context, region, bucket, key string, fileReadSeeker io.ReadSeeker) error {
	return awserr.New(request.CanceledErrorCode, errMsg, nil)
}

func mockUploadDataOtherErr(ctx context.Context, region, bucket, key string, fileReadSeeker io.ReadSeeker) error {
	return errors.New(errMsg)
}

func TestUploadToS3BucketBadArgs(t *testing.T) {
	funcWrappers = &funcWrapperStruct{
		openFileFn: mockOpenFileNotFound,
		uploadDataFn: mockUploadDataNoErr,
	}

	// Incorrect arg count - too few
	args := []string{
		"filePath",
		"regionName",
		"bucketPath",
	}
	result := UploadToS3Bucket(args)
	testutil.VerifyResult(t, result, "", argErrMsg, argErrMsg)

	// Incorrect arg count - too many
	args = []string{
		"filePath",
		"regionName",
		"bucketPath",
		"keyName",
		"10m",
		"extraArg",
	}
	result = UploadToS3Bucket(args)
	testutil.VerifyResult(t, result, "", argErrMsg, argErrMsg)

	// Invalid duration
	args = []string{
		"filePath",
		"regionName",
		"bucketPath",
		"keyName",
		"badduration",
	}
	wantErrMsg := "time: invalid duration \"badduration\""
	result = UploadToS3Bucket(args)
	testutil.VerifyResult(t, result, "", wantErrMsg, wantErrMsg)

	// Bad file path
	args = []string{
		"filePath",
		"regionName",
		"bucketPath",
		"keyName",
		"10m",
	}
	result = UploadToS3Bucket(args)
	testutil.VerifyResult(t, result, "", fileNotFoundMsg, fileNotFoundMsg)
}

func TestUploadToS3BucketNoErr(t *testing.T) {
	funcWrappers = &funcWrapperStruct{
		openFileFn: mockOpenFile,
		uploadDataFn: mockUploadDataNoErr,
	}
	args := []string{
		"dummyFile",
		"regionName",
		"bucketPath",
		"keyName",
		"10m",
	}
	result := UploadToS3Bucket(args)
	want := "Successfully uploaded file dummyFile to bucketPath/keyName"
	testutil.VerifyResult(t, result, want, "", "")
}

func TestUploadToS3BucketErrors(t *testing.T) {
	// timeout error
	funcWrappers = &funcWrapperStruct{
		openFileFn: mockOpenFile,
		uploadDataFn: mockUploadDataTimeoutErr,
	}
	args := []string{
		"dummyFile",
		"regionName",
		"bucketPath",
		"keyName",
		"10m",
	}
	result := UploadToS3Bucket(args)
	want := "Upload canceled due to timeout: RequestCanceled: Dummy error msg"
	testutil.VerifyResult(t, result, "", want, want)

	// other error
	funcWrappers = &funcWrapperStruct{
		openFileFn: mockOpenFile,
		uploadDataFn: mockUploadDataOtherErr,
	}
	result = UploadToS3Bucket(args)
	want = "Failed to upload object: Dummy error msg"
	testutil.VerifyResult(t, result, "", want, want)
}
