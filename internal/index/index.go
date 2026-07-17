// Package index implements the in-memory inverted index. Three fields are
// catalogued: service_name (component), log_level, and trace_id. The index
// maps a (field, value) pair to the set of chunk Refs whose file contains
// at least one matching log line.
//
// The index is rebuilt at startup from the chunk store. A real production
// system would persist it as a sidecar file to avoid rescanning; for the
// skeleton we keep it simple and rebuild on boot.
package index

import (
	"strings"
	"sync"

	"github.com/shayxnazar/logagg/internal/chunk"
	"github.com/shayxnazar/logagg/internal/logline"
)

// Field names we index. The constants match the JSON keys used by the
// logline package.
const (
	FieldService = "service_name"
	FieldLevel   = "level"
	FieldTraceID = "trace_id"
)

// Index is a goroutine-safe in-memory inverted index.
type Index struct {
	mu    sync.RWMutex
	idx   map[fieldKey][]chunk.Ref
}

type fieldKey struct {
	field string
	value string
}

// New returns an empty index.
func New() *Index {
	return &Index{idx: make(map[fieldKey][]chunk.Ref)}
}

// Add records that one LogLine matching (field, value) lives in r.
func (i *Index) Add(field, value string, r chunk.Ref) {
	if value == "" {
		return
	}
	k := fieldKey{field: field, value: value}
	i.mu.Lock()
	i.idx[k] = append(i.idx[k], r)
	i.mu.Unlock()
}

// Lookup returns the chunk refs that contain a matching value. The caller
// is responsible for intersecting multiple Lookup results.
func (i *Index) Lookup(field, value string) []chunk.Ref {
	i.mu.RLock()
	defer i.mu.RUnlock()
	out := make([]chunk.Ref, len(i.idx[fieldKey{field: field, value: value}]))
	copy(out, i.idx[fieldKey{field: field, value: value}])
	return out
}

// ExtractField returns the indexed value of `field` for a LogLine. The
// returned string is normalized (lowercased for level/trace_id) to keep
// lookups predictable.
func ExtractField(l logline.LogLine, field string) string {
	switch field {
	case FieldService:
		return l.Service
	case FieldLevel:
		return strings.ToUpper(l.Level)
	case FieldTraceID:
		return l.TraceID
	}
	return ""
}
