# memdb — in-memory KV store with WAL + custom TCP protocol

Stdlib-only Go implementation of the four-component design in `Agent.md`:

| Component              | Package              |
| ---------------------- | -------------------- |
| Sharded map + RWMutex  | `storage/`           |
| Binary WAL + fsync     | `wal/`               |
| RESP-lite TCP server   | `server/` + `proto/` |
| Snapshot compaction    | `wal/` (`Snapshot`)  |
| Wire-up + shutdown     | `main.go`            |
| Python client for FastAPI | `client/python/`  |

## Build & run

```sh
make build      # bin/memdb
./bin/memdb --addr :5455 --data ./data --sync interval --auto-snapshot 5m
```

Flags:

| Flag              | Default                | Description                                    |
| ----------------- | ---------------------- | ---------------------------------------------- |
| `--addr`          | `:5455`                | TCP listen address                             |
| `--data`          | `./data`               | Data directory (WAL + snapshot)                |
| `--sync`          | `interval`             | `always` \| `interval` \| `never`              |
| `--sync-every`    | `200ms`                | Background fsync interval when `interval`      |
| `--idle`          | `5m`                   | Per-connection idle timeout                    |
| `--auto-snapshot` | `0` (off)              | Auto-compact WAL every N (e.g. `5m`)           |

## Wire protocol

Text, line-oriented, binary-safe (values carry a length prefix).

```
-> SET foo 5\r\nhello\r\n
<- +OK\r\n

-> GET foo\r\n
<- $5\r\nhello\r\n         # hit
<- $-1\r\n                 # miss

-> DEL foo\r\n
<- :1\r\n                  # existed
<- :0\r\n                  # missing

-> PING\r\n            <- +PONG\r\n
-> STATS\r\n           <- :<n>\r\n
-> SNAPSHOT\r\n        <- +OK\r\n
```

## FastAPI integration

The `client/python/` folder ships a thread-safe pooled client. Drop the
`memdb/` package into your FastAPI project (or `pip install .`):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from memdb import PooledMemDB

@asynccontextmanager
async def lifespan(app):
    app.state.db = PooledMemDB("127.0.0.1", 5455, size=16)
    try:
        yield
    finally:
        app.state.db.close()

app = FastAPI(lifespan=lifespan)

@app.get("/kv/{key}")
def read(key: str):
    with app.state.db.connection() as db:
        return {"value": db.get(key)}
```

A complete example lives at
[`client/python/example_fastapi.py`](client/python/example_fastapi.py).

## Durability model

1. Every `SET`/`DEL` is written to `data/wal.log` **before** the map is
   updated.
2. On restart, the engine replays `snapshot.bin` (if any) then
   `wal.log`; a stale `wal.old` from a mid-snapshot crash is replayed
   first so no writes are lost.
3. `SNAPSHOT` (or `--auto-snapshot`) rotates the log, serializes the
   current point-in-time state, atomic-renames to `snapshot.bin`, and
   deletes the old WAL. Reads never block; writers are only briefly
   serialized during the log rotation itself.

The `--sync` flag lets you trade throughput for durability:

* `always` — `fsync` after each record (durable, slow)
* `interval` — background fsync every `--sync-every` (default 200ms)
* `never` — rely on the OS page cache (fastest, riskiest)
