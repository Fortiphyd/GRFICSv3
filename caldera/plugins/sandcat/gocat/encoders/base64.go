package encoders

import (
	"encoding/base64"
)

//Base64Encoder encodes and decodes data using base64
type Base64Encoder struct {
	name string
}

func init() {
	DataEncoders["base64"] = &Base64Encoder{ name: "base64" }
}

func (b *Base64Encoder) GetName() string {
	return b.name
}

func (b *Base64Encoder) EncodeData(data []byte, config map[string]interface{}) ([]byte, error) {
	encodedStr := base64.StdEncoding.EncodeToString(data)
	return []byte(encodedStr), nil
}

func (b *Base64Encoder) DecodeData(data []byte, config map[string]interface{}) ([]byte, error) {
	encodedStr := string(data)
	return base64.StdEncoding.DecodeString(encodedStr)
}
