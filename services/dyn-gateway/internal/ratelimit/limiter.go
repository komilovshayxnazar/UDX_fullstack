// Package ratelimit implements the stage-2 dynamic rate-limiting engine:
// a token bucket kept per identity key, sharded across N maps so the
// per-shard mutex only serializes ~1/N of the traffic. The bucket itself
// uses time-based lazy refill (no ticker goroutine) so idle keys pay
// nothing.
package ratelimit

import (
	"hash/fnv"
	"sync"
	"time"
)

// Limiter is safe for concurrent use.
type Limiter struct {
	rate   float64 // tokens added per second
	burst  float64 // maximum tokens the bucket can hold
	shards []*shard
}

type shard struct {
	mu      sync.Mutex
	buckets map[string]*bucket
}

type bucket struct {
	tokens float64
	last   time.Time
}

// New returns a Limiter with `rate` tokens/sec, capacity `burst`, split
// across `shardCount` shards. If shardCount <= 0 it defaults to 32.
func New(rate, burst float64, shardCount int) *Limiter {
	if shardCount <= 0 {
		shardCount = 32
	}
	if rate <= 0 {
		rate = 1
	}
	if burst <= 0 {
		burst = rate
	}
	shards := make([]*shard, shardCount)
	for i := range shards {
		shards[i] = &shard{buckets: make(map[string]*bucket)}
	}
	return &Limiter{rate: rate, burst: burst, shards: shards}
}

// Allow reports whether a single token could be taken for key at time now.
// If not, the returned duration is the caller-visible Retry-After hint —
// how long to wait before at least one token is available.
func (l *Limiter) Allow(key string, now time.Time) (bool, time.Duration) {
	sh := l.pickShard(key)
	sh.mu.Lock()
	defer sh.mu.Unlock()

	b, ok := sh.buckets[key]
	if !ok {
		// New identities start with a full bucket so a first-time visitor
		// gets the full burst.
		b = &bucket{tokens: l.burst, last: now}
		sh.buckets[key] = b
	} else {
		elapsed := now.Sub(b.last).Seconds()
		if elapsed > 0 {
			b.tokens += elapsed * l.rate
			if b.tokens > l.burst {
				b.tokens = l.burst
			}
			b.last = now
		}
	}

	if b.tokens >= 1 {
		b.tokens -= 1
		return true, 0
	}
	deficit := 1 - b.tokens
	wait := time.Duration(deficit / l.rate * float64(time.Second))
	if wait < time.Millisecond {
		wait = time.Millisecond
	}
	return false, wait
}

// Snapshot returns the current bucket count. Only intended for tests and
// the /metrics endpoint.
func (l *Limiter) Snapshot() int {
	n := 0
	for _, sh := range l.shards {
		sh.mu.Lock()
		n += len(sh.buckets)
		sh.mu.Unlock()
	}
	return n
}

// GC drops buckets that have been idle long enough to have refilled to
// capacity — they're indistinguishable from a fresh bucket, so keeping
// them wastes memory. Call periodically from the gateway supervisor.
func (l *Limiter) GC(now time.Time) int {
	// A bucket is fully refilled after burst/rate seconds of idleness.
	idle := time.Duration(l.burst/l.rate*float64(time.Second)) + time.Second
	dropped := 0
	for _, sh := range l.shards {
		sh.mu.Lock()
		for k, b := range sh.buckets {
			if now.Sub(b.last) >= idle {
				delete(sh.buckets, k)
				dropped++
			}
		}
		sh.mu.Unlock()
	}
	return dropped
}

func (l *Limiter) pickShard(key string) *shard {
	h := fnv.New32a()
	_, _ = h.Write([]byte(key))
	return l.shards[h.Sum32()%uint32(len(l.shards))]
}
