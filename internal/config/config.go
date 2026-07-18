// Package config centralizes the gateway's tunables so cmd/gateway stays
// small.
package config

import (
	"errors"
	"flag"
	"net/url"
	"time"
)

// Config is populated from CLI flags.
type Config struct {
	ListenAddr string
	Upstream   string
	KeyByPath  bool

	Rate       float64
	Burst      float64
	Shards     int
	GCInterval time.Duration

	CBMinRequests  int
	CBFailureRatio float64
	CBWindow       time.Duration
	CBCooldown     time.Duration

	UpstreamTimeout time.Duration
	MetricsPath     string
}

// Parse binds flags to the returned Config. Call flag.Parse afterwards.
func Parse() *Config {
	c := &Config{}
	flag.StringVar(&c.ListenAddr, "addr", ":8080", "gateway listen address")
	flag.StringVar(&c.Upstream, "upstream", "", "upstream URL, e.g. http://127.0.0.1:9000")
	flag.BoolVar(&c.KeyByPath, "key-by-path", false, "combine identity with URL path when rate-limiting")

	flag.Float64Var(&c.Rate, "rate", 20, "tokens replenished per second")
	flag.Float64Var(&c.Burst, "burst", 40, "maximum tokens in the bucket")
	flag.IntVar(&c.Shards, "shards", 32, "limiter shard count")
	flag.DurationVar(&c.GCInterval, "gc", 30*time.Second, "how often to sweep idle buckets")

	flag.IntVar(&c.CBMinRequests, "cb-min", 5, "minimum requests before breaker evaluates ratio")
	flag.Float64Var(&c.CBFailureRatio, "cb-ratio", 0.5, "failure ratio that trips the breaker")
	flag.DurationVar(&c.CBWindow, "cb-window", 10*time.Second, "breaker sliding window")
	flag.DurationVar(&c.CBCooldown, "cb-cooldown", 5*time.Second, "how long the breaker stays open")

	flag.DurationVar(&c.UpstreamTimeout, "upstream-timeout", 10*time.Second, "per-request upstream timeout")
	flag.StringVar(&c.MetricsPath, "metrics-path", "/_gw/metrics", "path on which /metrics is served")
	return c
}

// Validate returns nil if the config is usable.
func (c *Config) Validate() error {
	if c.Upstream == "" {
		return errors.New("config: --upstream is required")
	}
	if _, err := url.Parse(c.Upstream); err != nil {
		return errors.New("config: --upstream is not a valid URL")
	}
	if c.Rate <= 0 || c.Burst <= 0 {
		return errors.New("config: --rate and --burst must be > 0")
	}
	return nil
}
