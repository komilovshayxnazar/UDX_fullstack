// Package metrics implements the stage-4 metric capture layer: lockless
// counters for RPS and per-status-code hits, and a lock-guarded latency
// histogram. Exposed as plaintext at /_gw/metrics.
package metrics

import (
	"fmt"
	"io"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// Registry is the process-wide metrics sink.
type Registry struct {
	// atomically-updated counters, no locks in the hot path.
	total       atomic.Uint64
	allowed     atomic.Uint64
	rateLimited atomic.Uint64
	circuitOpen atomic.Uint64
	upstreamErr atomic.Uint64

	statusMu sync.Mutex
	byStatus map[int]uint64

	histMu sync.Mutex
	// buckets are fixed millisecond upper bounds; anything larger goes into
	// the +Inf overflow.
	histBounds []float64
	histCount  []uint64
	histSum    float64
	histObs    uint64

	startedAt time.Time
}

// New returns a Registry with sane latency bucket bounds (ms).
func New() *Registry {
	return &Registry{
		byStatus:   make(map[int]uint64),
		histBounds: []float64{1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000},
		histCount:  make([]uint64, 13), // 12 bounds + 1 overflow
		startedAt:  time.Now(),
	}
}

// Allowed increments the allowed-request counter.
func (r *Registry) Allowed() { r.total.Add(1); r.allowed.Add(1) }

// RateLimited increments the 429 counter (and total).
func (r *Registry) RateLimited() { r.total.Add(1); r.rateLimited.Add(1) }

// CircuitOpen increments the 503 counter (and total).
func (r *Registry) CircuitOpen() { r.total.Add(1); r.circuitOpen.Add(1) }

// UpstreamErr increments the upstream error counter (transport failures
// before we even get a status code).
func (r *Registry) UpstreamErr() { r.upstreamErr.Add(1) }

// Observe records a completed upstream response: status code and latency.
// Safe to call from any goroutine.
func (r *Registry) Observe(status int, latency time.Duration) {
	r.statusMu.Lock()
	r.byStatus[status]++
	r.statusMu.Unlock()

	ms := float64(latency) / float64(time.Millisecond)
	r.histMu.Lock()
	bucket := len(r.histBounds) // overflow slot
	for i, b := range r.histBounds {
		if ms <= b {
			bucket = i
			break
		}
	}
	r.histCount[bucket]++
	r.histSum += ms
	r.histObs++
	r.histMu.Unlock()
}

// Snapshot is what the /metrics endpoint serializes.
type Snapshot struct {
	Uptime         time.Duration
	Total          uint64
	Allowed        uint64
	RateLimited    uint64
	CircuitOpen    uint64
	UpstreamErr    uint64
	RPS            float64
	ByStatus       map[int]uint64
	LatencyBuckets map[float64]uint64 // "le" -> cumulative count
	LatencyOverflow uint64
	LatencyMeanMs   float64
	LatencyObs      uint64
}

// Snapshot returns a coherent point-in-time view of the registry.
func (r *Registry) Snapshot() Snapshot {
	total := r.total.Load()
	up := time.Since(r.startedAt)
	rps := 0.0
	if up > 0 {
		rps = float64(total) / up.Seconds()
	}

	r.statusMu.Lock()
	status := make(map[int]uint64, len(r.byStatus))
	for k, v := range r.byStatus {
		status[k] = v
	}
	r.statusMu.Unlock()

	r.histMu.Lock()
	cumBuckets := make(map[float64]uint64, len(r.histBounds))
	var cum uint64
	for i, b := range r.histBounds {
		cum += r.histCount[i]
		cumBuckets[b] = cum
	}
	overflow := r.histCount[len(r.histBounds)]
	mean := 0.0
	if r.histObs > 0 {
		mean = r.histSum / float64(r.histObs)
	}
	obs := r.histObs
	r.histMu.Unlock()

	return Snapshot{
		Uptime:          up,
		Total:           total,
		Allowed:         r.allowed.Load(),
		RateLimited:     r.rateLimited.Load(),
		CircuitOpen:     r.circuitOpen.Load(),
		UpstreamErr:     r.upstreamErr.Load(),
		RPS:             rps,
		ByStatus:        status,
		LatencyBuckets:  cumBuckets,
		LatencyOverflow: overflow,
		LatencyMeanMs:   mean,
		LatencyObs:      obs,
	}
}

// WriteText writes a Prometheus-flavoured (but standalone-parseable) text
// dump of the current snapshot.
func (r *Registry) WriteText(w io.Writer) {
	s := r.Snapshot()
	fmt.Fprintf(w, "# uptime_seconds %.3f\n", s.Uptime.Seconds())
	fmt.Fprintf(w, "gateway_requests_total %d\n", s.Total)
	fmt.Fprintf(w, "gateway_requests_allowed %d\n", s.Allowed)
	fmt.Fprintf(w, "gateway_requests_rate_limited %d\n", s.RateLimited)
	fmt.Fprintf(w, "gateway_requests_circuit_open %d\n", s.CircuitOpen)
	fmt.Fprintf(w, "gateway_upstream_errors %d\n", s.UpstreamErr)
	fmt.Fprintf(w, "gateway_rps %.3f\n", s.RPS)

	codes := make([]int, 0, len(s.ByStatus))
	for c := range s.ByStatus {
		codes = append(codes, c)
	}
	sort.Ints(codes)
	for _, c := range codes {
		fmt.Fprintf(w, "gateway_upstream_status{code=\"%d\"} %d\n", c, s.ByStatus[c])
	}

	bounds := make([]float64, 0, len(s.LatencyBuckets))
	for b := range s.LatencyBuckets {
		bounds = append(bounds, b)
	}
	sort.Float64s(bounds)
	for _, b := range bounds {
		fmt.Fprintf(w, "gateway_latency_ms_bucket{le=\"%g\"} %d\n", b, s.LatencyBuckets[b])
	}
	fmt.Fprintf(w, "gateway_latency_ms_bucket{le=\"+Inf\"} %d\n",
		func() uint64 {
			var total uint64
			for _, v := range s.LatencyBuckets {
				if v > total {
					total = v
				}
			}
			return total + s.LatencyOverflow
		}(),
	)
	fmt.Fprintf(w, "gateway_latency_ms_mean %.3f\n", s.LatencyMeanMs)
	fmt.Fprintf(w, "gateway_latency_ms_observations %d\n", s.LatencyObs)
}
