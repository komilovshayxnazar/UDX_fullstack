// Package compress wraps klauspost/compress's zstd codec. The agent compresses
// outgoing batches; the server decompresses inbound batches. Both sides share
// the same package so encoding settings stay in sync.
package compress

import (
	"errors"
	"fmt"

	"github.com/klauspost/compress/zstd"
)

// Encoder is safe for concurrent use.
var encoder, _ = zstd.NewWriter(
	nil,
	zstd.WithEncoderLevel(zstd.SpeedFastest),
)

// Decoder is safe for concurrent use.
var decoder, _ = zstd.NewReader(
	nil,
	zstd.WithDecoderConcurrency(4),
)

// Compress returns a zstd-compressed copy of src. The result is independent of
// the input buffer and may be retained.
func Compress(src []byte) ([]byte, error) {
	if len(src) == 0 {
		return nil, errors.New("compress: empty input")
	}
	out := encoder.EncodeAll(src, make([]byte, 0, len(src)/2))
	return out, nil
}

// Decompress reverses Compress. It returns an error if the input is not a
// valid zstd payload.
func Decompress(src []byte) ([]byte, error) {
	out, err := decoder.DecodeAll(src, nil)
	if err != nil {
		return nil, fmt.Errorf("compress: decompress: %w", err)
	}
	return out, nil
}
