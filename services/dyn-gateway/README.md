# Dynamic Rate Limiter & Reverse Proxy API Gateway

A stdlib-only Go implementation of the four-stage gateway pipeline described
in `Workflow.md`:

```
Client → [Reverse Proxy] → [Rate Limiter] → [Circuit Breaker] → [Upstream]
                                                             ↑
                                                     metrics captured
```

## Layout

```
cmd/gateway/          gateway binary
cmd/echo/             demo upstream used for smoke tests
internal/identify/    per-request key extraction (IP / API key / path)
internal/ratelimit/   sharded token-bucket limiter
internal/circuit/     closed/open/half-open state machine per upstream
internal/metrics/     RPS, latency, status-code counters + /metrics endpoint
internal/proxy/       httputil.ReverseProxy wired through the middleware chain
internal/config/      env / flag configuration
```

## Build

```sh
make build           # -> bin/gateway, bin/echo
```

## Demo

Terminal 1 — a dummy upstream that echoes and can be poked into failing:

```sh
./bin/echo --addr :9000
```

Terminal 2 — the gateway, pointed at the echo upstream:

```sh
./bin/gateway \
  --addr :8080 \
  --upstream http://127.0.0.1:9000 \
  --rate 5 --burst 5 \
  --cb-failures 3 --cb-window 5s --cb-cooldown 2s
```

Terminal 3 — hammer it:

```sh
for i in $(seq 1 10); do curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/hello; done
curl -s http://127.0.0.1:8080/_gw/metrics
```

Requests beyond `burst` in one second return `429 Too Many Requests` with a
`Retry-After` header. If the echo upstream is killed, the breaker trips
after `cb-failures` and returns `503 Service Unavailable` until the
cooldown elapses.

## Identity

The rate-limit key is chosen from the first non-empty of:

1. `Authorization` header (API key / bearer)
2. `X-Api-Key` header
3. `X-Forwarded-For` (first hop)
4. `RemoteAddr` host portion

Add `--key-by-path` to combine the identity with the URL path so that per-
route quotas apply.
