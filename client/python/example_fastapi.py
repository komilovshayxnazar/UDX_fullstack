"""Minimal FastAPI example integrating with the memdb server.

Run:

    # terminal 1 — start memdb
    ./bin/memdb --addr :5455 --data ./data

    # terminal 2 — install fastapi + start example
    pip install fastapi uvicorn
    uvicorn example_fastapi:app --reload

    # terminal 3 — poke it
    curl -X POST http://127.0.0.1:8000/kv/hello -d 'world'
    curl http://127.0.0.1:8000/kv/hello
    curl -X DELETE http://127.0.0.1:8000/kv/hello
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response

from memdb import MemDBError, PooledMemDB


POOL: PooledMemDB | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global POOL
    POOL = PooledMemDB(host="127.0.0.1", port=5455, size=16)
    try:
        yield
    finally:
        POOL.close()


app = FastAPI(lifespan=lifespan)


def db() -> PooledMemDB:
    if POOL is None:
        raise HTTPException(status_code=503, detail="database not ready")
    return POOL


@app.get("/kv/{key}")
def read(key: str):
    with db().connection() as conn:
        value = conn.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="not found")
    return Response(content=value, media_type="application/octet-stream")


@app.post("/kv/{key}")
async def write(key: str, request: Request):
    body = await request.body()
    try:
        with db().connection() as conn:
            conn.set(key, body)
    except MemDBError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "bytes": len(body)}


@app.delete("/kv/{key}")
def remove(key: str):
    with db().connection() as conn:
        deleted = conn.delete(key)
    return {"deleted": deleted}


@app.post("/admin/snapshot")
def snapshot():
    with db().connection() as conn:
        conn.snapshot()
    return {"ok": True}


@app.get("/admin/stats")
def stats():
    with db().connection() as conn:
        return {"keys": conn.stats()}
