// Package logline defines the canonical LogLine record produced by the
// FastAPI generator (stage 1) and consumed by the Go agent. The record is
// encoded on the wire as one JSON object per line, matching the workflow
// spec's "rigid JSON format".
package logline

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

// Field name constants. The generator (FastAPI side) must use these.
const (
	FieldTimestamp  = "timestamp"
	FieldLevel      = "log_level"
	FieldService    = "component"
	FieldTraceID    = "trace_id"
	FieldMessage    = "message"
)

// LogLine is the in-memory representation of a single log record.
//
// The field names below map to the JSON keys defined by the constants above;
// they are kept as struct tags so the encoder/decoder stays symmetric.
type LogLine struct {
	Timestamp  time.Time `json:"timestamp"`
	Level      string    `json:"log_level"`
	Service    string    `json:"component"`
	TraceID    string    `json:"trace_id,omitempty"`
	Message    string    `json:"message"`
}

// MarshalJSONLine encodes the log line as a single JSON object without a
// trailing newline. Newline framing is handled by the tailer.
func (l LogLine) MarshalJSONLine() ([]byte, error) {
	return json.Marshal(l)
}

// DecodeJSONLine parses a single JSON object. The caller is expected to have
// stripped the trailing newline already.
func DecodeJSONLine(b []byte) (LogLine, error) {
	var l LogLine
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&l); err != nil {
		return LogLine{}, fmt.Errorf("logline: decode: %w", err)
	}
	if l.Timestamp.IsZero() {
		return LogLine{}, errors.New("logline: missing timestamp")
	}
	return l, nil
}

// EncodeBatch encodes a slice of LogLine as a JSON array suitable for zstd
// compression before it goes onto the gRPC wire.
func EncodeBatch(lines []LogLine) ([]byte, error) {
	return json.Marshal(lines)
}

// DecodeBatch parses a JSON array payload.
func DecodeBatch(payload []byte) ([]LogLine, error) {
	var lines []LogLine
	if err := json.Unmarshal(payload, &lines); err != nil {
		return nil, fmt.Errorf("logline: decode batch: %w", err)
	}
	return lines, nil
}
