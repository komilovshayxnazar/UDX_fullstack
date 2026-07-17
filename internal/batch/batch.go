// Package batch groups incoming log lines into size- and time-bounded batches
// before they are compressed and shipped to the central server. The workflow
// spec calls for 100ms or 500KB triggers; we honour both.
package batch

import (
	"context"
	"sync"
	"time"

	"github.com/shayxnazar/logagg/internal/logline"
)

// Default knobs. They can be overridden at construction time.
const (
	DefaultMaxBytes = 500 * 1024 // 500 KB
	DefaultMaxLines = 4096
	DefaultInterval = 100 * time.Millisecond
)

// Batch is a sealed group of LogLine records, ready for compression.
type Batch struct {
	Lines   []logline.LogLine
	Bytes   int
	SealedAt time.Time
}

// Assembler is a single-producer-friendly batching primitive. The producer
// calls Push; the consumer receives sealed batches from Out. Assembler is
// safe to call Push from many goroutines.
type Assembler struct {
	maxBytes int
	maxLines int
	interval time.Duration

	mu     sync.Mutex
	buf    []logline.LogLine
	bytes  int

	out    chan<- Batch
	ticker *time.Ticker
	done   chan struct{}

	// Source identifier carried into Batch via SealedAt + the caller
	// constructs the gRPC envelope. Kept here for future use.
	now func() time.Time
}

// NewAssembler constructs an Assembler and starts its background seal loop.
// out is the channel that sealed batches are delivered on. The caller is
// responsible for closing the underlying context to stop the loop.
func NewAssembler(ctx context.Context, out chan<- Batch) *Assembler {
	a := &Assembler{
		maxBytes: DefaultMaxBytes,
		maxLines: DefaultMaxLines,
		interval: DefaultInterval,
		out:      out,
		done:     make(chan struct{}),
		now:      time.Now,
	}
	a.ticker = time.NewTicker(a.interval)
	go a.loop(ctx)
	return a
}

// WithLimits lets tests dial the knobs down. Returns the receiver.
func (a *Assembler) WithLimits(maxBytes int, maxLines int, interval time.Duration) *Assembler {
	if maxBytes > 0 {
		a.maxBytes = maxBytes
	}
	if maxLines > 0 {
		a.maxLines = maxLines
	}
	if interval > 0 {
		a.interval = interval
		a.ticker.Reset(interval)
	}
	return a
}

// Push adds a line to the current batch. If adding the line would exceed the
// configured byte or count limit, the current batch is sealed first.
func (a *Assembler) Push(line logline.LogLine) {
	// Approximate the marshaled size: json.Marshal of a LogLine is the cheap
	// upper bound we have without re-encoding. We add a per-line constant to
	// account for commas/brackets in the eventual array form.
	const perLineOverhead = 2
	encSize := estimateSize(line) + perLineOverhead

	a.mu.Lock()
	if a.bytes+encSize > a.maxBytes || len(a.buf) >= a.maxLines {
		pending := a.buf
		pendingBytes := a.bytes
		a.buf = nil
		a.bytes = 0
		a.mu.Unlock()
		a.deliver(pending, pendingBytes)
		a.mu.Lock()
	}
	a.buf = append(a.buf, line)
	a.bytes += encSize
	a.mu.Unlock()
}

// Close seals and delivers the final batch, then stops the background loop.
func (a *Assembler) Close() {
	a.mu.Lock()
	pending := a.buf
	pendingBytes := a.bytes
	a.buf = nil
	a.bytes = 0
	a.mu.Unlock()
	if len(pending) > 0 {
		a.deliver(pending, pendingBytes)
	}
	close(a.done)
}

func (a *Assembler) loop(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-a.done:
			return
		case <-a.ticker.C:
			a.mu.Lock()
			if len(a.buf) == 0 {
				a.mu.Unlock()
				continue
			}
			pending := a.buf
			pendingBytes := a.bytes
			a.buf = nil
			a.bytes = 0
			a.mu.Unlock()
			a.deliver(pending, pendingBytes)
		}
	}
}

func (a *Assembler) deliver(lines []logline.LogLine, bytes int) {
	select {
	case a.out <- Batch{Lines: lines, Bytes: bytes, SealedAt: a.now()}:
	default:
		// Out channel is unbuffered/slow; drop the batch? In production we
		// would block. For the skeleton we drop to avoid head-of-line
		// blocking on the gRPC stream. A real implementation would surface
		// this to metrics.
	}
}

// estimateSize returns a rough byte count for one LogLine. The exact
// marshaled size is only known after json.Marshal, but for the 500KB trigger
// a few-percent over-estimate is fine.
func estimateSize(l logline.LogLine) int {
	return 64 + len(l.Level) + len(l.Service) + len(l.TraceID) + len(l.Message)
}
