// Package identify extracts the rate-limit key from an incoming request.
// Stage 1 of the workflow: parse headers/IP and hand a stable string to the
// limiter and the metrics layer.
package identify

import (
	"net"
	"net/http"
	"strings"
)

// Extractor is the request-to-key function used by the limiter middleware.
type Extractor func(*http.Request) string

// Default returns an Extractor that tries, in order:
//  1. Authorization header (bearer / API key)
//  2. X-Api-Key header
//  3. First hop of X-Forwarded-For
//  4. host portion of RemoteAddr
//
// If keyByPath is true, the resulting key is joined with the request path
// so that per-route quotas apply.
func Default(keyByPath bool) Extractor {
	return func(r *http.Request) string {
		id := firstNonEmpty(
			bearer(r.Header.Get("Authorization")),
			strings.TrimSpace(r.Header.Get("X-Api-Key")),
			firstHop(r.Header.Get("X-Forwarded-For")),
			hostOnly(r.RemoteAddr),
		)
		if keyByPath {
			return id + "|" + r.URL.Path
		}
		return id
	}
}

func bearer(h string) string {
	h = strings.TrimSpace(h)
	if h == "" {
		return ""
	}
	// "Bearer XXX" or "ApiKey XXX" — take the token half; otherwise use the
	// whole header verbatim.
	if i := strings.IndexByte(h, ' '); i > 0 {
		return strings.TrimSpace(h[i+1:])
	}
	return h
}

func firstHop(xff string) string {
	if xff == "" {
		return ""
	}
	if i := strings.IndexByte(xff, ','); i >= 0 {
		return strings.TrimSpace(xff[:i])
	}
	return strings.TrimSpace(xff)
}

func hostOnly(remote string) string {
	if remote == "" {
		return ""
	}
	if host, _, err := net.SplitHostPort(remote); err == nil {
		return host
	}
	return remote
}

func firstNonEmpty(candidates ...string) string {
	for _, c := range candidates {
		if c != "" {
			return c
		}
	}
	return "unknown"
}
