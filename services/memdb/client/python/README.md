# memdb Python client

Sync client + thread-safe connection pool for the Go memdb server.

## Install

The package is stdlib-only. Just copy the `memdb/` folder into your
FastAPI project (or install it as a wheel):

```sh
cp -r client/python/memdb <your-fastapi-project>/
```

## Quick start

```python
from memdb import MemDB

with MemDB("127.0.0.1", 5455) as db:
    db.set("greeting", b"hello")
    print(db.get("greeting"))   # b"hello"
    db.delete("greeting")
```

## FastAPI

Use `PooledMemDB` for concurrent request handling. See
[`example_fastapi.py`](./example_fastapi.py) for a full app.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from memdb import PooledMemDB

POOL = None

@asynccontextmanager
async def lifespan(app):
    global POOL
    POOL = PooledMemDB("127.0.0.1", 5455, size=16)
    try:
        yield
    finally:
        POOL.close()

app = FastAPI(lifespan=lifespan)

@app.get("/kv/{k}")
def read(k):
    with POOL.connection() as db:
        return {"value": db.get(k)}
```

## API

| Method              | Returns          | Notes                                     |
| ------------------- | ---------------- | ----------------------------------------- |
| `db.set(k, v)`      | `None`           | `v` must be bytes-like                    |
| `db.get(k)`         | `bytes \| None`  | `None` on miss                            |
| `db.delete(k)`      | `bool`           | `True` if key existed                     |
| `db.ping()`         | `None`           | Raises `MemDBError` on unexpected reply   |
| `db.stats()`        | `int`            | Number of keys resident in the server     |
| `db.snapshot()`     | `None`           | Triggers WAL compaction (async server-side) |

All calls raise `MemDBError` on server-side `-ERR` frames or protocol
violations, and `OSError` on socket failures.
