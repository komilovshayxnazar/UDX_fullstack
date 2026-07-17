// Index rebuild on startup. Walks every rotated chunk, decodes its lines,
// and re-inserts the (field, value) -> Ref entries. The cost is proportional
// to total stored data, so for a real production system you'd persist a
// serialized index and load that instead.

package index

import (
	"github.com/shayxnazar/logagg/internal/chunk"
)

// Rebuild clears the index and re-populates it from the given chunk store.
// All rotated chunk files are scanned. Active (mutable) buckets are not
// indexed here; they are empty after a clean restart because the WAL owns
// the most recent lines.
func (i *Index) Rebuild(store *chunk.Store) error {
	i.mu.Lock()
	i.idx = make(map[fieldKey][]chunk.Ref)
	i.mu.Unlock()

	for _, ref := range store.Rotated() {
		lines, err := chunk.ReadLines(ref.Path)
		if err != nil {
			return err
		}
		for _, l := range lines {
			for _, field := range []string{FieldService, FieldLevel, FieldTraceID} {
				if v := ExtractField(l, field); v != "" {
					i.Add(field, v, ref)
				}
			}
		}
	}
	return nil
}
