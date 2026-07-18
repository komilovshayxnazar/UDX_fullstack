# syntax=docker/dockerfile:1.7

# ── Stage 1 · builder ───────────────────────────────────────────────────
FROM golang:1.25-alpine AS builder
WORKDIR /build
COPY go.mod ./
RUN go mod download 2>/dev/null || true
COPY . .
RUN CGO_ENABLED=0 go build -o /out/memdb ./


# ── Stage 2 · runtime ───────────────────────────────────────────────────
FROM alpine:3.20 AS runtime

# netcat-openbsd gives the compose healthcheck a reliable `nc -z`.
RUN apk add --no-cache netcat-openbsd \
 && addgroup -S memdb && adduser -S memdb -G memdb
WORKDIR /app
COPY --from=builder /out/memdb /usr/local/bin/memdb

RUN mkdir -p /app/data && chown -R memdb:memdb /app
USER memdb

EXPOSE 5455

ENTRYPOINT ["/usr/local/bin/memdb"]
CMD ["--addr", ":5455", "--data", "/app/data", "--sync", "interval", "--auto-snapshot", "5m"]
