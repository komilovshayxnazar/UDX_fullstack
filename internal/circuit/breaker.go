// Package circuit implements the stage-3 circuit breaker state machine.
// It tracks failures inside a sliding window; if the failure ratio crosses
// a threshold, the breaker opens and fast-fails requests for a cooldown
// period. After the cooldown, a single probe is allowed (Half-Open); if
// that probe succeeds the breaker closes again.
package circuit

import (
	"errors"
	"sync"
	"time"
)

// State is the current breaker state.
type State int

const (
	Closed State = iota
	Open
	HalfOpen
)

func (s State) String() string {
	switch s {
	case Closed:
		return "closed"
	case Open:
		return "open"
	case HalfOpen:
		return "half-open"
	}
	return "unknown"
}

// ErrOpen is returned by Allow when the breaker is open (or half-open and
// a probe is already in flight).
var ErrOpen = errors.New("circuit: open")

// Config tunes the state machine.
type Config struct {
	// Minimum requests inside Window before the ratio is evaluated. Prevents
	// tripping on tiny sample sizes.
	MinRequests int
	// Failure ratio [0,1]. If ratio > threshold and MinRequests is reached
	// the breaker opens.
	FailureRatio float64
	// Sliding window duration.
	Window time.Duration
	// How long the breaker stays open before allowing a Half-Open probe.
	Cooldown time.Duration
	// Clock returns the current time; overridable in tests.
	Clock func() time.Time
}

// Breaker is safe for concurrent use.
type Breaker struct {
	cfg   Config
	mu    sync.Mutex
	state State

	events    []event // ring-ish, trimmed lazily by prune()
	openedAt  time.Time
	probing   bool
}

type event struct {
	at time.Time
	ok bool
}

// New returns a Breaker in the Closed state. Zero-valued Config fields
// receive reasonable defaults.
func New(cfg Config) *Breaker {
	if cfg.MinRequests <= 0 {
		cfg.MinRequests = 5
	}
	if cfg.FailureRatio <= 0 || cfg.FailureRatio > 1 {
		cfg.FailureRatio = 0.5
	}
	if cfg.Window <= 0 {
		cfg.Window = 10 * time.Second
	}
	if cfg.Cooldown <= 0 {
		cfg.Cooldown = 5 * time.Second
	}
	if cfg.Clock == nil {
		cfg.Clock = time.Now
	}
	return &Breaker{cfg: cfg, state: Closed}
}

// State returns the current state.
func (b *Breaker) State() State {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.state
}

// Allow is called before the downstream request. It returns ErrOpen if the
// caller should short-circuit. The returned bool indicates whether this
// call is the Half-Open probe (true) — probes are exclusive.
func (b *Breaker) Allow() (probe bool, err error) {
	now := b.cfg.Clock()
	b.mu.Lock()
	defer b.mu.Unlock()

	switch b.state {
	case Closed:
		return false, nil
	case Open:
		if now.Sub(b.openedAt) < b.cfg.Cooldown {
			return false, ErrOpen
		}
		// Cooldown elapsed; move to Half-Open and let this caller probe.
		b.state = HalfOpen
		b.probing = true
		return true, nil
	case HalfOpen:
		if b.probing {
			return false, ErrOpen
		}
		b.probing = true
		return true, nil
	}
	return false, nil
}

// Record reports the outcome of an attempt. If probe was true, success
// closes the breaker; failure re-opens it and starts a new cooldown.
func (b *Breaker) Record(probe bool, success bool) {
	now := b.cfg.Clock()
	b.mu.Lock()
	defer b.mu.Unlock()

	if probe {
		b.probing = false
		if success {
			b.state = Closed
			b.events = b.events[:0]
			return
		}
		b.state = Open
		b.openedAt = now
		return
	}

	b.events = append(b.events, event{at: now, ok: success})
	b.prune(now)

	if b.state == Closed && len(b.events) >= b.cfg.MinRequests {
		fails := 0
		for _, e := range b.events {
			if !e.ok {
				fails++
			}
		}
		ratio := float64(fails) / float64(len(b.events))
		if ratio >= b.cfg.FailureRatio {
			b.state = Open
			b.openedAt = now
			b.events = b.events[:0]
		}
	}
}

func (b *Breaker) prune(now time.Time) {
	cutoff := now.Add(-b.cfg.Window)
	drop := 0
	for _, e := range b.events {
		if e.at.Before(cutoff) {
			drop++
		} else {
			break
		}
	}
	if drop > 0 {
		b.events = append(b.events[:0], b.events[drop:]...)
	}
}
