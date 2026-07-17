# Distributed Log Aggregator

A 5-stage log aggregation pipeline written in Go. This project implements
stages **2 → 5** of the workflow described in `workflow.md`:

```
[ FastAPI app ] → (writes JSON-line log) → [ Go log agent ] → (gRPC + zstd)
   → [ Go central server ] → (WAL + worker pool) → [ chunk store + index ]
   → [ query CLI ]
```

## Layout

```
proto/logagg.proto              gRPC service + LogBatch message
gen/logagg/v1/                  generated protobuf + gRPC stubs
cmd/server/                     central ingestion server
cmd/agent/                      tail + batch + stream
cmd/query/                      offline query CLI
internal/logline                canonical LogLine struct
internal/tailer                 file-descriptor based tail
internal/batch                  100ms / 500KB batcher
internal/compress               zstd helpers
internal/transport              gRPC dial/listen helpers
internal/server                 IngestService + worker pool + sync.Pool
internal/wal                    append-only WAL with fsync + replay
internal/chunk                  1-hour time-bucketed chunk store
internal/index                  in-memory inverted index
internal/query                  query DSL parser + engine
```

## Build

```sh
make build
```

Produces `bin/server`, `bin/agent`, `bin/query`.

## Demo (no FastAPI needed)

In three terminals:

```sh
# Terminal 1: server
./bin/server --data ./data

# Terminal 2: agent
# First, write a few sample lines
cat > /tmp/app.log <<'EOF'
{"timestamp":"2026-07-17T00:00:01Z","log_level":"INFO","component":"fastapi","trace_id":"a1","message":"hello"}
{"timestamp":"2026-07-17T00:00:02Z","log_level":"ERROR","component":"fastapi","trace_id":"a2","message":"panic: nil pointer"}
{"timestamp":"2026-07-17T00:00:03Z","log_level":"INFO","component":"worker","trace_id":"b1","message":"done"}
EOF
./bin/agent --file /tmp/app.log --server localhost:50051
# Append more lines to /tmp/app.log; the agent will pick them up.
echo '{"timestamp":"2026-07-17T00:00:04Z","log_level":"ERROR","component":"fastapi","trace_id":"a3","message":"panic again"}' >> /tmp/app.log

# Terminal 3: query
./bin/query "service_name=fastapi AND level=ERROR" --regex "panic" --data ./data
```

## Query DSL

`key=value [AND key=value ...]`

Recognised keys (matching `logline.Field*` and `index.Field*`):

- `service_name` — value of the `component` field in JSON
- `level` — value of `log_level`, compared case-insensitively
- `trace_id` — value of `trace_id`

Flags:

- `--regex <re>` — extra filter on the `message` field
- `--since <rfc3339>` / `--until <rfc3339>` — time bounds
- `--data <dir>` — same data directory the server uses

## Durability

Every batch is appended to `data/wal/active.wal` (length-prefixed,
zstd-compressed) and `fsync`'d before the agent is told the batch is
acknowledged. On restart the server replays the WAL into the chunk store
and rebuilds the inverted index from the on-disk chunks.

## Limits

- Single-host: the agent and server are designed for one machine pair.
  Multi-host would need a service registry for gRPC discovery.
- No mTLS: `transport.Dial` uses insecure for the skeleton. Add
  credentials before exposing the server on a hostile network.
- Active chunk is rotated every 5 minutes by the server. A crash inside
  that window loses at most 5 minutes of buffered lines (the WAL keeps
  them durable; the chunk file is rebuilt on replay).
