// Package storage implements the sharded in-memory key/value engine
// described in Component 1. The engine is agnostic to durability — the WAL
// layer decides when a write is safe to apply — so this package only owns
// the map + per-shard RWMutex machinery and the point-in-time snapshot
// iterator used by the compaction path.
package storage

import (
	"hash/fnv"
	"sync"
)

// ShardCount is the fixed shard fanout. 32 shards keep the per-shard lock
// contention low without pushing the map count into cache-thrash territory.
const ShardCount = 32

// Engine is the sharded map. Safe for concurrent use.
type Engine struct {
	shards [ShardCount]*shard
}

type shard struct {
	mu sync.RWMutex
	m  map[string][]byte
}

// New returns an empty Engine with all shards pre-allocated.
func New() *Engine {
	e := &Engine{}
	for i := 0; i < ShardCount; i++ {
		e.shards[i] = &shard{m: make(map[string][]byte)}
	}
	return e
}

// Get returns a defensive copy of the stored value plus a hit boolean. The
// caller may mutate the returned slice freely.
func (e *Engine) Get(key string) ([]byte, bool) {
	sh := e.pick(key)
	sh.mu.RLock()
	v, ok := sh.m[key]
	if !ok {
		sh.mu.RUnlock()
		return nil, false
	}
	out := make([]byte, len(v))
	copy(out, v)
	sh.mu.RUnlock()
	return out, true
}

// Set stores a copy of value under key. Existing values are overwritten.
// The engine owns its internal copy; the caller may reuse the input buffer.
func (e *Engine) Set(key string, value []byte) {
	stored := make([]byte, len(value))
	copy(stored, value)

	sh := e.pick(key)
	sh.mu.Lock()
	sh.m[key] = stored
	sh.mu.Unlock()
}

// Delete removes key. The returned bool reports whether the key existed.
func (e *Engine) Delete(key string) bool {
	sh := e.pick(key)
	sh.mu.Lock()
	_, ok := sh.m[key]
	if ok {
		delete(sh.m, key)
	}
	sh.mu.Unlock()
	return ok
}

// Len is the total number of stored keys. It scans every shard under
// RLock; O(ShardCount) locks.
func (e *Engine) Len() int {
	n := 0
	for _, sh := range e.shards {
		sh.mu.RLock()
		n += len(sh.m)
		sh.mu.RUnlock()
	}
	return n
}

// Entry is a single (key, value) pair returned by Snapshot.
type Entry struct {
	Key   string
	Value []byte
}

// Snapshot returns a point-in-time copy of every entry. Each shard is
// locked with an RLock for the duration of its own copy — reads and other
// shards remain unblocked. Values are deep-copied so downstream callers
// (e.g. the WAL snapshotter) can write them to disk without racing new
// mutations.
func (e *Engine) Snapshot() []Entry {
	total := e.Len()
	out := make([]Entry, 0, total)

	for _, sh := range e.shards {
		sh.mu.RLock()
		for k, v := range sh.m {
			cp := make([]byte, len(v))
			copy(cp, v)
			out = append(out, Entry{Key: k, Value: cp})
		}
		sh.mu.RUnlock()
	}
	return out
}

// pick maps a key to its owning shard via 32-bit FNV.
func (e *Engine) pick(key string) *shard {
	h := fnv.New32a()
	_, _ = h.Write([]byte(key))
	return e.shards[h.Sum32()%ShardCount]
}
