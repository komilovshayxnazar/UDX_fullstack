package ratelimit

import (
	"testing"
	"time"
)

func TestAllowConsumesBurstThenBlocks(t *testing.T) {
	l := New(10, 5, 4)
	now := time.Unix(1_700_000_000, 0)
	for i := 0; i < 5; i++ {
		ok, _ := l.Allow("k", now)
		if !ok {
			t.Fatalf("burst token %d denied unexpectedly", i)
		}
	}
	ok, wait := l.Allow("k", now)
	if ok {
		t.Fatal("expected 6th call to be denied")
	}
	if wait <= 0 {
		t.Fatal("expected non-zero Retry-After")
	}
}

func TestRefillOverTime(t *testing.T) {
	l := New(10, 5, 4) // 10 tokens/sec
	now := time.Unix(1_700_000_000, 0)
	for i := 0; i < 5; i++ {
		l.Allow("k", now)
	}
	// After 200ms we should have refilled ~2 tokens.
	next := now.Add(200 * time.Millisecond)
	got := 0
	for i := 0; i < 3; i++ {
		if ok, _ := l.Allow("k", next); ok {
			got++
		}
	}
	if got < 2 {
		t.Fatalf("expected >=2 refilled tokens, got %d", got)
	}
}

func TestGCReclaimsIdle(t *testing.T) {
	l := New(1, 1, 4)
	now := time.Unix(1_700_000_000, 0)
	l.Allow("a", now)
	l.Allow("b", now)
	if got := l.Snapshot(); got != 2 {
		t.Fatalf("snapshot=%d want 2", got)
	}
	dropped := l.GC(now.Add(10 * time.Second))
	if dropped != 2 {
		t.Fatalf("gc dropped=%d want 2", dropped)
	}
	if got := l.Snapshot(); got != 0 {
		t.Fatalf("snapshot after gc=%d want 0", got)
	}
}
