package circuit

import (
	"testing"
	"time"
)

func TestBreakerOpensOnFailureRatio(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	b := New(Config{
		MinRequests:  4,
		FailureRatio: 0.5,
		Window:       time.Second,
		Cooldown:     time.Second,
		Clock:        func() time.Time { return now },
	})
	// 4 requests, 2 failures — exactly at threshold, should open.
	for i := 0; i < 4; i++ {
		_, err := b.Allow()
		if err != nil {
			t.Fatalf("closed breaker denied req %d", i)
		}
		b.Record(false, i%2 == 0)
	}
	if b.State() != Open {
		t.Fatalf("state=%s want open", b.State())
	}
}

func TestBreakerHalfOpenAllowsSingleProbe(t *testing.T) {
	current := time.Unix(1_700_000_000, 0)
	b := New(Config{
		MinRequests:  2, FailureRatio: 0.5,
		Window: time.Second, Cooldown: time.Second,
		Clock: func() time.Time { return current },
	})
	// Force open.
	b.Record(false, false)
	b.Record(false, false)
	if b.State() != Open {
		t.Fatalf("expected open, got %s", b.State())
	}
	// Still in cooldown.
	if _, err := b.Allow(); err != ErrOpen {
		t.Fatal("expected ErrOpen during cooldown")
	}
	// Cooldown elapses.
	current = current.Add(2 * time.Second)
	probe, err := b.Allow()
	if err != nil || !probe {
		t.Fatalf("expected probe allowance, got probe=%v err=%v", probe, err)
	}
	// A second concurrent caller is rejected.
	if _, err := b.Allow(); err != ErrOpen {
		t.Fatal("expected ErrOpen while a probe is in flight")
	}
	// Probe succeeds; breaker closes.
	b.Record(true, true)
	if b.State() != Closed {
		t.Fatalf("state=%s want closed after successful probe", b.State())
	}
}

func TestFailedProbeReopens(t *testing.T) {
	current := time.Unix(1_700_000_000, 0)
	b := New(Config{
		MinRequests:  2, FailureRatio: 0.5,
		Window: time.Second, Cooldown: time.Second,
		Clock: func() time.Time { return current },
	})
	b.Record(false, false)
	b.Record(false, false)
	current = current.Add(2 * time.Second)
	probe, _ := b.Allow()
	b.Record(probe, false) // probe fails
	if b.State() != Open {
		t.Fatalf("state=%s want open after failed probe", b.State())
	}
}
