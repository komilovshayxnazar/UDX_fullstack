// Package tailer implements the OS-file-descriptor based log tail described in stage 2 of the workflow. We own the FD: open the file once, stat it periodically for size growth, and Read from the last offset. No external "tail" binary is invoked.
package tailer

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"sync/atomic"
	"time"

	"github.com/shayxnazar/logagg/internal/logline"
)

// Tailer reads newline-delimited JSON LogLine records from a file and pushes them on the out channel. It survives truncation/replacement (logrotate) by re-opening the file and resetting the read offset.
type Tailer struct {
	path   string
	out    chan<- logline.LogLine
	poll   time.Duration
	offset atomic.Int64
	skip   atomic.Int64
}

// New constructs a Tailer. poll sets how often we stat the file for new bytes; 250ms is a sensible default for production.
func New(path string, out chan<- logline.LogLine, poll time.Duration) *Tailer {
	if poll <= 0 {
		poll = 250 * time.Millisecond
	}
	return &Tailer{path: path, out: out, poll: poll}
}

// Skipped returns the count of lines that failed to parse.
func (t *Tailer) Skipped() int64 { return t.skip.Load() }

// Run blocks until ctx is done. Returns ctx.Err() on cancellation.
func (t *Tailer) Run(ctx context.Context) error {
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		if err := t.tailOnce(ctx); err != nil {
			if errors.Is(err, context.Canceled) {
				return err
			}
			// File not yet present (FastAPI not started). Sleep and retry.
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(t.poll):
			}
			continue
		}
		// tailOnce returns nil only when the file disappeared between read
		// passes (truncate/replace). Reset offset and reopen.
		t.offset.Store(0)
	}
}

// tailOnce opens the file (or uses the existing FD's last offset) and reads
// new bytes until either the file is gone or the context is cancelled. It
// returns io.EOF-like signals as nil so the outer loop reopens the file.
func (t *Tailer) tailOnce(ctx context.Context) error {
	f, err := os.Open(t.path)
	if err != nil {
		return fmt.Errorf("tailer: open: %w", err)
	}
	defer f.Close()

	// Seek to the offset we left off at. The offset survives across tailOnce
	// invocations through the atomic on the receiver.
	if off := t.offset.Load(); off > 0 {
		if _, err := f.Seek(off, io.SeekStart); err != nil {
			return fmt.Errorf("tailer: seek: %w", err)
		}
	} else {
		// First open: default to end-of-file so we don't re-ship history.
		end, err := f.Seek(0, io.SeekEnd)
		if err != nil {
			return fmt.Errorf("tailer: seek-end: %w", err)
		}
		t.offset.Store(end)
	}

	reader := bufio.NewReaderSize(f, 64*1024)

	for {
		if err := ctx.Err(); err != nil {
			return err
		}

		line, err := reader.ReadBytes('\n')
		if len(line) > 0 {
			t.offset.Add(int64(len(line)))
			t.handleLine(line)
			continue
		}
		if err != nil && !errors.Is(err, io.EOF) {
			return err
		}

		// Check whether the file was rotated (inode changed, size shrank).
		fi, statErr := f.Stat()
		if statErr != nil {
			return statErr
		}
		if cur := t.offset.Load(); fi.Size() < cur {
			// File was truncated or replaced. Reopen from scratch.
			return nil
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(t.poll):
		}
	}
}

func (t *Tailer) handleLine(raw []byte) {
	// Strip trailing newline (and optional \r) before parsing.
	trimmed := raw
	for len(trimmed) > 0 && (trimmed[len(trimmed)-1] == '\n' || trimmed[len(trimmed)-1] == '\r') {
		trimmed = trimmed[:len(trimmed)-1]
	}
	if len(trimmed) == 0 {
		return
	}
	ll, err := logline.DecodeJSONLine(trimmed)
	if err != nil {
		t.skip.Add(1)
		return
	}
	// Backpressure: out is unbuffered by the caller, so this naturally
	// throttles the file read.
	select {
	case t.out <- ll:
	case <-time.After(2 * time.Second):
		// Downstream stuck; drop the line rather than block forever.
		t.skip.Add(1)
	}
}
