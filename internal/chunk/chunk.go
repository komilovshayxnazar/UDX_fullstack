// Package chunk implements the time-series chunk store. Logs are bucketed
// into 1-hour immutable blocks; the active block is mutable. On rotation we
// zstd-compress the block and write it to a file under data/chunks/.
//
// File layout (all times UTC):
//
//	data/chunks/YYYY/MM/DD/HH-<startNs>-<endNs>.jsonl.zst
//
// where startNs / endNs are Unix nanosecond timestamps. Nanos are used
// instead of RFC3339 so the filename splits cleanly on '-' (RFC3339 already
// contains dashes and would collide with the field separator).
package chunk

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/shayxnazar/logagg/internal/compress"
	"github.com/shayxnazar/logagg/internal/logline"
)

// Size is the time bucket width.
const Size = time.Hour

// Ref points at a contiguous range of one chunk file on disk. The query
// engine uses these to seek the underlying file.
type Ref struct {
	Path  string
	Start time.Time
	End   time.Time
}

// Overlaps reports whether the chunk's [Start, End) window intersects [s, e).
func (r Ref) Overlaps(s, e time.Time) bool {
	return r.Start.Before(e) && r.End.After(s)
}

// Store is a thread-safe append-only chunk store.
type Store struct {
	root string

	mu      sync.Mutex
	active  *activeBucket
	rotated []Ref // every chunk ever sealed, in append order
}

// NewStore prepares data/chunks under root, replaying any existing chunk
// files into the in-memory index of rotated chunks. (The mutable active
// bucket is empty after restart — durability of in-flight lines is owned
// by the WAL.)
func NewStore(root string) (*Store, error) {
	chunksDir := filepath.Join(root, "chunks")
	if err := os.MkdirAll(chunksDir, 0o755); err != nil {
		return nil, fmt.Errorf("chunk: mkdir: %w", err)
	}
	s := &Store{root: root}
	if err := s.scan(); err != nil {
		return nil, err
	}
	return s, nil
}

// scan walks the chunk directory and registers existing chunk files as
// rotated. We do not load their contents into memory.
func (s *Store) scan() error {
	walk := filepath.Join(s.root, "chunks")
	return filepath.Walk(walk, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			if errors.Is(err, os.ErrNotExist) {
				return nil
			}
			return err
		}
		if info.IsDir() {
			return nil
		}
		if !strings.HasSuffix(path, ".jsonl.zst") {
			return nil
		}
		start, end, ok := parseName(info.Name())
		if !ok {
			return nil
		}
		s.rotated = append(s.rotated, Ref{Path: path, Start: start, End: end})
		return nil
	})
}

// Rotated returns a snapshot of the rotated chunk index. Safe to call
// concurrently with Append.
func (s *Store) Rotated() []Ref {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Ref, len(s.rotated))
	copy(out, s.rotated)
	return out
}

// Append adds lines to the active bucket. If the lines cross a bucket
// boundary, the current bucket is rotated first.
func (s *Store) Append(lines []logline.LogLine) error {
	if len(lines) == 0 {
		return nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, l := range lines {
		if s.active == nil {
			s.active = newBucket(l.Timestamp.Truncate(Size))
		}
		if !l.Timestamp.Truncate(Size).Equal(s.active.Start) {
			if err := s.rotateLocked(); err != nil {
				return err
			}
			s.active = newBucket(l.Timestamp.Truncate(Size))
		}
		s.active.Append(l)
	}
	return nil
}

// Rotate seals the active bucket immediately, regardless of its size. Used
// at shutdown so that nothing lingers in memory.
func (s *Store) Rotate() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.active == nil {
		return nil
	}
	return s.rotateLocked()
}

func (s *Store) rotateLocked() error {
	if s.active == nil || len(s.active.lines) == 0 {
		s.active = nil
		return nil
	}
	start := s.active.Start
	end := start.Add(Size)
	path, err := s.writeChunk(start, end, s.active.lines)
	if err != nil {
		return err
	}
	s.rotated = append(s.rotated, Ref{Path: path, Start: start, End: end})
	s.active = nil
	return nil
}

func (s *Store) writeChunk(start, end time.Time, lines []logline.LogLine) (string, error) {
	startUTC := start.UTC()
	rel := filepath.Join(
		"chunks",
		fmt.Sprintf("%04d", startUTC.Year()),
		fmt.Sprintf("%02d", int(startUTC.Month())),
		fmt.Sprintf("%02d", startUTC.Day()),
		fmt.Sprintf("%02d-%d-%d.jsonl.zst", startUTC.Hour(), start.UnixNano(), end.UnixNano()),
	)
	abs := filepath.Join(s.root, rel)
	if err := os.MkdirAll(filepath.Dir(abs), 0o755); err != nil {
		return "", err
	}

	// Encode as JSON-lines, then compress the whole thing with zstd.
	encoded, err := encodeJSONLines(lines)
	if err != nil {
		return "", err
	}
	compressed, err := compress.Compress(encoded)
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(abs, compressed, 0o644); err != nil {
		return "", err
	}
	return abs, nil
}

// ReadLines decodes a chunk file back into LogLine records. Used by the
// query engine.
func ReadLines(path string) ([]logline.LogLine, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("chunk: read %s: %w", path, err)
	}
	decoded, err := compress.Decompress(raw)
	if err != nil {
		return nil, err
	}
	return decodeJSONLines(decoded)
}

// --- helpers ---

type activeBucket struct {
	Start time.Time
	lines []logline.LogLine
}

func newBucket(start time.Time) *activeBucket {
	return &activeBucket{Start: start}
}

func (b *activeBucket) Append(l logline.LogLine) {
	b.lines = append(b.lines, l)
}

func parseName(name string) (time.Time, time.Time, bool) {
	base := strings.TrimSuffix(name, ".jsonl.zst")
	// HH-<startNs>-<endNs>
	parts := strings.Split(base, "-")
	if len(parts) != 3 {
		return time.Time{}, time.Time{}, false
	}
	startNs, err := strconv.ParseInt(parts[1], 10, 64)
	if err != nil {
		return time.Time{}, time.Time{}, false
	}
	endNs, err := strconv.ParseInt(parts[2], 10, 64)
	if err != nil {
		return time.Time{}, time.Time{}, false
	}
	return time.Unix(0, startNs).UTC(), time.Unix(0, endNs).UTC(), true
}

func encodeJSONLines(lines []logline.LogLine) ([]byte, error) {
	var buf strings.Builder
	enc := json.NewEncoder(&buf)
	for _, l := range lines {
		if err := enc.Encode(l); err != nil {
			return nil, err
		}
	}
	return []byte(buf.String()), nil
}

func decodeJSONLines(raw []byte) ([]logline.LogLine, error) {
	var out []logline.LogLine
	dec := json.NewDecoder(strings.NewReader(string(raw)))
	for {
		var l logline.LogLine
		if err := dec.Decode(&l); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return nil, err
		}
		out = append(out, l)
	}
	return out, nil
}

