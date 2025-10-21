package contact_test

import (
	"strconv"
	"testing"

	"github.com/mitre/gocat/contact"
)

var continuousContacts []string = make([]string, 0)

func TestSupportsContinuous(t *testing.T) {
	for contactName, contactImpl := range contact.CommunicationChannels {
		t.Log(contactName)
		var want bool
		if contains(continuousContacts, contactName) {
			want = true
		} else {
			want = false
		}
		result := contactImpl.SupportsContinuous()
		if want != result {
			t.Errorf("%s SupportsContinuous() should return %s, but returned %s", contactName, strconv.FormatBool(want), strconv.FormatBool(result))
		}
	}

}

func contains(s []string, str string) bool {
	for _, v := range s {
		if v == str {
			return true
		}
	}

	return false
}
