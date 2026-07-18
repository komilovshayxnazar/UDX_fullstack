// Output formatting for query results.

package query

import (
	"encoding/json"
	"fmt"
	"io"

	"github.com/shayxnazar/logagg/internal/logline"
)

// Print writes one JSON object per matching log line, followed by a
// summary on stderr (so piping JSON to jq is straightforward).
func Print(w io.Writer, lines []logline.LogLine) error {
	enc := json.NewEncoder(w)
	for _, l := range lines {
		if err := enc.Encode(l); err != nil {
			return err
		}
	}
	return nil
}

// Summarize prints a one-line human-readable summary to w.
func Summarize(w io.Writer, n int) {
	fmt.Fprintf(w, "-- %d match(es)\n", n)
}
