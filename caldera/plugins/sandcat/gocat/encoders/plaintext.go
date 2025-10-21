package encoders

//Base64Encoder encodes and decodes data using base64
type PlaintextEncoder struct {
	name string
}

func init() {
	DataEncoders["plain-text"] = &PlaintextEncoder{ name: "plain-text" }
}

func (p *PlaintextEncoder) GetName() string {
	return p.name
}

func (p *PlaintextEncoder) EncodeData(data []byte, config map[string]interface{}) ([]byte, error) {
	return data, nil
}

func (p *PlaintextEncoder) DecodeData(data []byte, config map[string]interface{}) ([]byte, error) {
	return data, nil
}
