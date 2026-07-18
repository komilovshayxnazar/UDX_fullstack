// Query engine: intersects chunk refs from the index, reads the surviving
// chunks, and applies a regex post-filter on the message field.

package query

import (
	"context"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/shayxnazar/logagg/internal/chunk"
	"github.com/shayxnazar/logagg/internal/index"
	"github.com/shayxnazar/logagg/internal/logline"
)

// normalizeIndexValue mirrors index.ExtractField's normalization so that a
// query like `level=error` still hits index entries stored as "ERROR".
func normalizeIndexValue(field, value string) string {
	if field == index.FieldLevel {
		return strings.ToUpper(value)
	}
	return value
}

// Engine runs parsed queries against the chunk store + index.
type Engine struct {
	Store *chunk.Store
	Index *index.Index
}

// Range restricts the time window of a query. Zero values mean "no bound".
type Range struct {
	Since time.Time
	Until time.Time
}

// Run executes the query and returns matching log lines.
func (e *Engine) Run(ctx context.Context, q Query, r Range, msgRegex *regexp.Regexp) ([]logline.LogLine, error) {
	refs := e.candidateChunks(q, r)
	// Deduplicate + sort by path so output is deterministic.
	uniq := uniqueRefs(refs)
	sort.Slice(uniq, func(i, j int) bool { return uniq[i].Path < uniq[j].Path })

	var out []logline.LogLine
	for _, ref := range uniq {
		if err := ctx.Err(); err != nil {
			return out, err
		}
		lines, err := chunk.ReadLines(ref.Path)
		if err != nil {
			return out, fmt.Errorf("query: read %s: %w", ref.Path, err)
		}
		for _, l := range lines {
			if !matchesConstraints(l, q) {
				continue
			}
			if !inRange(l.Timestamp, r) {
				continue
			}
			if msgRegex != nil && !msgRegex.MatchString(l.Message) {
				continue
			}
			out = append(out, l)
		}
	}
	return out, nil
}

func (e *Engine) candidateChunks(q Query, r Range) []chunk.Ref {
	if len(q.Constraints) == 0 {
		all := e.Store.Rotated()
		return filterByTime(all, r)
	}
	sets := make([]map[string]chunk.Ref, 0, len(q.Constraints))
	for _, c := range q.Constraints {
		refs := e.Index.Lookup(c.Field, normalizeIndexValue(c.Field, c.Value))
		set := make(map[string]chunk.Ref, len(refs))
		for _, ref := range refs {
			set[ref.Path] = ref
		}
		sets = append(sets, set)
	}
	intersect := sets[0]
	for _, s := range sets[1:] {
		intersect = intersectMaps(intersect, s)
	}
	refs := make([]chunk.Ref, 0, len(intersect))
	for _, ref := range intersect {
		refs = append(refs, ref)
	}
	return filterByTime(refs, r)
}

func filterByTime(refs []chunk.Ref, r Range) []chunk.Ref {
	if r.Since.IsZero() && r.Until.IsZero() {
		return refs
	}
	out := refs[:0]
	for _, ref := range refs {
		if ref.Overlaps(orZero(r.Since), orInf(r.Until)) {
			out = append(out, ref)
		}
	}
	return out
}

func orZero(t time.Time) time.Time {
	if t.IsZero() {
		return time.Unix(0, 0)
	}
	return t
}
func orInf(t time.Time) time.Time {
	if t.IsZero() {
		return time.Date(9999, 1, 1, 0, 0, 0, 0, time.UTC)
	}
	return t
}

func uniqueRefs(refs []chunk.Ref) []chunk.Ref {
	seen := make(map[string]struct{}, len(refs))
	out := make([]chunk.Ref, 0, len(refs))
	for _, r := range refs {
		if _, ok := seen[r.Path]; ok {
			continue
		}
		seen[r.Path] = struct{}{}
		out = append(out, r)
	}
	return out
}

func intersectMaps(a, b map[string]chunk.Ref) map[string]chunk.Ref {
	out := make(map[string]chunk.Ref, len(a))
	for k, v := range a {
		if _, ok := b[k]; ok {
			out[k] = v
		}
	}
	return out
}

func matchesConstraints(l logline.LogLine, q Query) bool {
	for _, c := range q.Constraints {
		switch c.Field {
		case index.FieldService:
			if l.Service != c.Value {
				return false
			}
		case index.FieldLevel:
			if l.Level != c.Value && !equalFold(l.Level, c.Value) {
				return false
			}
		case index.FieldTraceID:
			if l.TraceID != c.Value {
				return false
			}
		default:
			return false
		}
	}
	return true
}

func inRange(t time.Time, r Range) bool {
	if !r.Since.IsZero() && t.Before(r.Since) {
		return false
	}
	if !r.Until.IsZero() && !t.Before(r.Until) {
		return false
	}
	return true
}

func equalFold(a, b string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := 0; i < len(a); i++ {
		ca, cb := a[i], b[i]
		if 'a' <= ca && ca <= 'z' {
			ca -= 'a' - 'A'
		}
		if 'a' <= cb && cb <= 'z' {
			cb -= 'a' - 'A'
		}
		if ca != cb {
			return false
		}
	}
	return true
}
