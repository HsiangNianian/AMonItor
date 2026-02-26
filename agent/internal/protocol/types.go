package protocol

import "encoding/json"

type Envelope struct {
	MsgID     string          `json:"msg_id"`
	TraceID   string          `json:"trace_id,omitempty"`
	Type      string          `json:"type"`
	TargetID  string          `json:"target_id,omitempty"`
	Timestamp int64           `json:"timestamp"`
	Payload   json.RawMessage `json:"payload,omitempty"`
}

type ActionPayload struct {
	Action    string          `json:"action"`
	Params    json.RawMessage `json:"params,omitempty"`
	TargetURL string          `json:"target_url,omitempty"`
}

type ActionAckPayload struct {
	ActionMsgID string `json:"action_msg_id"`
	Success     bool   `json:"success"`
	Message     string `json:"message,omitempty"`
}

type RegisterPayload struct {
	TargetID string            `json:"target_id"`
	SDKURL   string            `json:"sdk_url"`
	Metadata map[string]string `json:"metadata,omitempty"`
}
