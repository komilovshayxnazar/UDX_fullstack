// Command gateway wires the 4-stage pipeline behind a public listener.
package main

import (
	"context"
	"errors"
	"flag"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/komilovshayxnazar/dyn-gateway/internal/circuit"
	"github.com/komilovshayxnazar/dyn-gateway/internal/config"
	"github.com/komilovshayxnazar/dyn-gateway/internal/identify"
	"github.com/komilovshayxnazar/dyn-gateway/internal/metrics"
	"github.com/komilovshayxnazar/dyn-gateway/internal/proxy"
	"github.com/komilovshayxnazar/dyn-gateway/internal/ratelimit"
)

func main() {
	cfg := config.Parse()
	flag.Parse()
	if err := cfg.Validate(); err != nil {
		log.Fatalf("gateway: %v", err)
	}

	u, err := url.Parse(cfg.Upstream)
	if err != nil {
		log.Fatalf("gateway: parse --upstream: %v", err)
	}

	limiter := ratelimit.New(cfg.Rate, cfg.Burst, cfg.Shards)
	breaker := circuit.New(circuit.Config{
		MinRequests:  cfg.CBMinRequests,
		FailureRatio: cfg.CBFailureRatio,
		Window:       cfg.CBWindow,
		Cooldown:     cfg.CBCooldown,
	})
	reg := metrics.New()

	pipeline := proxy.New(proxy.Options{
		Upstream:        u,
		Extract:         identify.Default(cfg.KeyByPath),
		Limiter:         limiter,
		Breaker:         breaker,
		Metrics:         reg,
		UpstreamTimeout: cfg.UpstreamTimeout,
	})

	mux := http.NewServeMux()
	mux.HandleFunc(cfg.MetricsPath, func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		reg.WriteText(w)
	})
	mux.HandleFunc("/_gw/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.Handle("/", pipeline)

	srv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// Background housekeeping: sweep idle buckets so long-tail keys don't
	// leak memory.
	go func() {
		t := time.NewTicker(cfg.GCInterval)
		defer t.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case now := <-t.C:
				if n := limiter.GC(now); n > 0 {
					log.Printf("gateway: gc dropped %d idle buckets", n)
				}
			}
		}
	}()

	go func() {
		log.Printf("gateway: listen=%s upstream=%s rate=%.1f burst=%.1f",
			cfg.ListenAddr, cfg.Upstream, cfg.Rate, cfg.Burst)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("gateway: listen: %v", err)
		}
	}()

	<-ctx.Done()
	log.Printf("gateway: shutting down")
	shCtx, shCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shCancel()
	_ = srv.Shutdown(shCtx)
}
