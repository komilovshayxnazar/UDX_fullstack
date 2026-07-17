// Package wal implements the Write-Ahead Log used by the central server for
// crash-safe durability. Each record is a length-prefixed, zstd-compressed
// batch of LogLine records:
//
//	[u32 LE length][zstd(json_array_of_logline)]
//
// On startup the server replays the WAL into the storage engine, then opens
// it for append. Every Append is followed by an fsync, so a power loss can
// lose at most a single in-flight batch.
package wal

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"

	"github.com/shayxnazar/logagg/internal/compress"
	"github.com/shayxnazar/logagg/internal/logline"
)

// MaxRecordSize caps a single WAL record at 16 MiB. Anything bigger is
// almost certainly a bug or a corrupt log; we refuse rather than allocate.
const MaxRecordSize = 16 * 1024 * 1024

// WAL is a single-writer, multi-reader append log. The central server
// serializes writes through its worker pool, so the lock is mostly defensive.
type WAL struct {
	mu   sync.Mutex
	path string
	f    *os.File
	bw   *bufio.Writer
}

// Open opens (or creates) the WAL at path, replaying existing records to
// the consumer. If the file is empty, an empty WAL is returned and replay
// is a no-op.
func Open(path string, replay func([]logline.LogLine) error) (*WAL, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, fmt.Errorf("wal: mkdir: %w", err)
	}
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o644)
	if err != nil {
		return nil, fmt.Errorf("wal: open: %w", err)
	}
	w := &WAL{path: path, f: f, bw: bufio.NewWriterSize(f, 64*1024)}
	if replay != nil {
		if err := w.replay(replay); err != nil {
			f.Close()
			return nil, err
		}
	}
	return w, nil
}

func (w *WAL) replay(consume func([]logline.LogLine) error) error {
	if _, err := w.f.Seek(0, io.SeekStart); err != nil {
		return fmt.Errorf("wal: replay seek: %w", err)
	}
	br := bufio.NewReaderSize(w.f, 64*1024)
	for {
		var lenBuf [4]byte
		if _, err := io.ReadFull(br, lenBuf[:]); err != nil {
			if err == io.EOF {
				break
			}
			return fmt.Errorf("wal: replay len: %w", err)
		}
		recLen := binary.LittleEndian.Uint32(lenBuf[:])
		if recLen == 0 || recLen > MaxRecordSize {
			return fmt.Errorf("wal: replay bad length %d", recLen)
		}
		compressed := make([]byte, recLen)
		if _, err := io.ReadFull(br, compressed); err != nil {
			return fmt.Errorf("wal: replay body: %w", err)
		}
		raw, err := compress.Decompress(compressed)
		if err != nil {
			return fmt.Errorf("wal: replay decompress: %w", err)
		}
		lines, err := logline.DecodeBatch(raw)
		if err != nil {
			return fmt.Errorf("wal: replay decode: %w", err)
		}
		if err := consume(lines); err != nil {
			return fmt.Errorf("wal: replay consumer: %w", err)
		}
	}
	// Re-seek to end so subsequent appends continue from current EOF.
	if _, err := w.f.Seek(0, io.SeekEnd); err != nil {
		return fmt.Errorf("wal: replay end seek: %w", err)
	}
	w.bw.Reset(w.f)
	return nil
}

// Append serializes the batch as a single WAL record and fsyncs.
func (w *WAL) Append(lines []logline.LogLine) error {
	if len(lines) == 0 {
		return nil
	}
	raw, err := logline.EncodeBatch(lines)
	if err != nil {
		return fmt.Errorf("wal: encode: %w", err)
	}
	compressed, err := compress.Compress(raw)
	if err != nil {
		return fmt.Errorf("wal: compress: %w", err)
	}
	if len(compressed) > MaxRecordSize {
		return fmt.Errorf("wal: record too large (%d > %d)", len(compressed), MaxRecordSize)
	}

	w.mu.Lock()
	defer w.mu.Unlock()

	var lenBuf [4]byte
	binary.LittleEndian.PutUint32(lenBuf[:], uint32(len(compressed)))
	if _, err := w.bw.Write(lenBuf[:]); err != nil {
		return fmt.Errorf("wal: write len: %w", err)
	}
	if _, err := w.bw.Write(compressed); err != nil {
		return fmt.Errorf("wal: write body: %w", err)
	}
	if err := w.bw.Flush(); err != nil {
		return fmt.Errorf("wal: flush: %w", err)
	}
	if err := w.f.Sync(); err != nil {
		return fmt.Errorf("wal: fsync: %w", err)
	}
	return nil
}

// Close flushes and closes the underlying file.
func (w *WAL) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.bw != nil {
		_ = w.bw.Flush()
	}
	if w.f != nil {
		return w.f.Close()
	}
	return nil
}
