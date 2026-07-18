// Package proxy wires all four stages into a single http.Handler chain:
// identify -> rate limit -> circuit breaker -> reverse proxy -> metrics.
package proxy

import (
	"fmt"
	"math"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/komilovshayxnazar/dyn-gateway/internal/circuit"
	"github.com/komilovshayxnazar/dyn-gateway/internal/identify"
	"github.com/komilovshayxnazar/dyn-gateway/internal/metrics"
	"github.com/komilovshayxnazar/dyn-gateway/internal/ratelimit"
)

// Options bundles the collaborators the gateway needs.
type Options struct {
	Upstream        *url.URL
	Extract         identify.Extractor
	Limiter         *ratelimit.Limiter
	Breaker         *circuit.Breaker
	Metrics         *metrics.Registry
	UpstreamTimeout time.Duration
	Now             func() time.Time
}

// New returns the composed handler that implements the full pipeline.
func New(opt Options) http.Handler {
	if opt.Now == nil {
		opt.Now = time.Now
	}

	rp := httputil.NewSingleHostReverseProxy(opt.Upstream)
	// Preserve original Director; add gateway headers before dispatch.
	baseDirector := rp.Director
	rp.Director = func(r *http.Request) {
		baseDirector(r)
		r.Host = opt.Upstream.Host
		r.Header.Set("X-Forwarded-Host", r.Header.Get("Host"))
		r.Header.Set("X-Gateway", "dyn-gateway")
	}

	// Custom error hook lets us count upstream transport failures and
	// register them with the breaker.
	rp.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, err error) {
		opt.Metrics.UpstreamErr()
		http.Error(w, "upstream error: "+err.Error(), http.StatusBadGateway)
	}

	// Capture status codes on the way out for metrics + breaker feedback.
	type ctxKey int
	const probeKey ctxKey = 1

	rp.ModifyResponse = func(resp *http.Response) error {
		// no-op here; the outer handler wraps the writer and observes on
		// completion. Keeping ModifyResponse assigned prevents httputil from
		// stripping hop-by-hop headers we might want in the future.
		return nil
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Metrics-only endpoints route around the pipeline. The gateway main
		// mounts them separately; if callers hit them through here we still
		// forward, but ordinarily the mux short-circuits first.

		key := opt.Extract(r)

		// Stage 2: rate limit.
		if ok, retry := opt.Limiter.Allow(key, opt.Now()); !ok {
			opt.Metrics.RateLimited()
			seconds := int(math.Ceil(retry.Seconds()))
			if seconds < 1 {
				seconds = 1
			}
			w.Header().Set("Retry-After", strconv.Itoa(seconds))
			w.Header().Set("X-RateLimit-Key", redact(key))
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}

		// Stage 3: circuit breaker.
		probe, err := opt.Breaker.Allow()
		if err != nil {
			opt.Metrics.CircuitOpen()
			w.Header().Set("X-Circuit-State", opt.Breaker.State().String())
			http.Error(w, "service unavailable", http.StatusServiceUnavailable)
			return
		}

		opt.Metrics.Allowed()

		// Stage 4: forward to upstream and observe.
		start := opt.Now()
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}

		// Enforce per-request timeout on the upstream call.
		if opt.UpstreamTimeout > 0 {
			ctx, cancel := timeoutCtx(r, opt.UpstreamTimeout)
			defer cancel()
			r = r.WithContext(ctx)
		}

		rp.ServeHTTP(sw, r)

		lat := opt.Now().Sub(start)
		opt.Metrics.Observe(sw.status, lat)

		// Any 5xx from the upstream (or the proxy's own 502) counts as a
		// failure for the breaker.
		success := sw.status < 500
		opt.Breaker.Record(probe, success)
	})
}

// redact keeps the /_gw/metrics endpoint safe to look at; we send back the
// key length + a short prefix rather than the raw token in error responses.
func redact(k string) string {
	if len(k) <= 4 {
		return strings.Repeat("*", len(k))
	}
	return k[:2] + "…" + fmt.Sprintf("(%d)", len(k))
}

type statusWriter struct {
	http.ResponseWriter
	status  int
	written bool
}

func (s *statusWriter) WriteHeader(code int) {
	if !s.written {
		s.status = code
		s.written = true
	}
	s.ResponseWriter.WriteHeader(code)
}

func (s *statusWriter) Write(b []byte) (int, error) {
	if !s.written {
		s.written = true
	}
	return s.ResponseWriter.Write(b)
}
