package contact

import (
	"fmt"
	"math/rand"
	"strconv"
	"time"
)

var seededRand *rand.Rand = rand.New(rand.NewSource(time.Now().UnixNano()))

func getRandomIdentifier() string {
	rand.Seed(time.Now().UnixNano())
	return strconv.Itoa(rand.Int())
}

func checkValidSleepInterval(profile map[string]interface{}, timeout, resetInterval int) {
	if profile["sleep"] == timeout{
		time.Sleep(time.Duration(float64(resetInterval)) * time.Second)
	}
}

func getDescriptor(descriptorType string, uniqueId string) string {
	return fmt.Sprintf("%s-%s", descriptorType, uniqueId)
}

