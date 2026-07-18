# syntax=docker/dockerfile:1.7

# ── Stage 1 · builder ───────────────────────────────────────────────────
FROM golang:1.25-alpine AS builder
WORKDIR /build
COPY go.mod ./
RUN go mod download 2>/dev/null || true
COPY . .
RUN CGO_ENABLED=0 go build -o /out/gateway ./cmd/gateway


# ── Stage 2 · runtime ───────────────────────────────────────────────────
FROM alpine:3.20 AS runtime

RUN addgroup -S gateway && adduser -S gateway -G gateway
COPY --from=builder /out/gateway /usr/local/bin/gateway
USER gateway

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/gateway"]
