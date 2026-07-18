package proxy

import (
	"context"
	"net/http"
	"time"
)

// timeoutCtx returns a context that inherits from r and cancels after d.
// Extracted so proxy.go stays focused on the pipeline stages.
func timeoutCtx(r *http.Request, d time.Duration) (context.Context, context.CancelFunc) {
	return context.WithTimeout(r.Context(), d)
}
