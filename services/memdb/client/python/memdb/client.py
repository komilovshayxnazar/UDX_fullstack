"""Sync client + thread-safe connection pool for the Go memdb server.

The wire protocol matches the server's `proto` package:

    -> SET <key> <valueLen>\\r\\n<value bytes>\\r\\n
    <- +OK\\r\\n

    -> GET <key>\\r\\n
    <- $<n>\\r\\n<n bytes>\\r\\n     (hit)
       $-1\\r\\n                     (miss)

    -> DEL <key>\\r\\n
    <- :1\\r\\n or :0\\r\\n

    -> PING\\r\\n
    <- +PONG\\r\\n

    -> STATS\\r\\n
    <- :<n>\\r\\n

    -> SNAPSHOT\\r\\n
    <- +OK\\r\\n

Errors from the server come back as `-ERR <msg>\\r\\n`.
"""

from __future__ import annotations

import queue
import socket
import threading
from typing import Optional


class MemDBError(RuntimeError):
    """Raised when the server sends a -ERR frame or the wire is malformed."""


def _validate_key(key: str) -> bytes:
    if not key:
        raise ValueError("memdb: key must be non-empty")
    if any(c.isspace() for c in key):
        raise ValueError("memdb: key must not contain whitespace")
    return key.encode("utf-8")


class MemDB:
    """A single, non-thread-safe TCP client to the memdb server.

    For multi-threaded / FastAPI use, prefer :class:`PooledMemDB`.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5455,
        timeout: float = 5.0,
        connect_timeout: float = 2.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._connect_timeout = connect_timeout
        self._sock: Optional[socket.socket] = None
        self._buf = b""

    # -- connection lifecycle -------------------------------------------------

    def connect(self) -> None:
        if self._sock is not None:
            return
        s = socket.create_connection(
            (self._host, self._port), timeout=self._connect_timeout
        )
        s.settimeout(self._timeout)
        # TCP_NODELAY: this is a request/response protocol, don't wait for Nagle.
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock = s
        self._buf = b""

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._buf = b""

    def __enter__(self) -> "MemDB":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -- commands -------------------------------------------------------------

    def ping(self) -> None:
        self._send(b"PING\r\n")
        reply = self._read_line()
        if reply != b"+PONG":
            raise MemDBError(f"unexpected PING reply: {reply!r}")

    def stats(self) -> int:
        self._send(b"STATS\r\n")
        return self._read_int()

    def snapshot(self) -> None:
        self._send(b"SNAPSHOT\r\n")
        self._expect_ok()

    def set(self, key: str, value: bytes) -> None:
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise TypeError("memdb.set value must be bytes-like")
        value = bytes(value)
        k = _validate_key(key)
        frame = b"SET " + k + b" " + str(len(value)).encode("ascii") + b"\r\n" + value + b"\r\n"
        self._send(frame)
        self._expect_ok()

    def get(self, key: str) -> Optional[bytes]:
        k = _validate_key(key)
        self._send(b"GET " + k + b"\r\n")
        return self._read_bulk()

    def delete(self, key: str) -> bool:
        k = _validate_key(key)
        self._send(b"DEL " + k + b"\r\n")
        return self._read_int() == 1

    # -- IO helpers -----------------------------------------------------------

    def _send(self, data: bytes) -> None:
        if self._sock is None:
            self.connect()
        assert self._sock is not None
        self._sock.sendall(data)

    def _read_line(self) -> bytes:
        while b"\r\n" not in self._buf:
            chunk = self._recv_some()
            if not chunk:
                raise MemDBError("connection closed while reading line")
            self._buf += chunk
        line, _, rest = self._buf.partition(b"\r\n")
        self._buf = rest
        if line.startswith(b"-ERR "):
            raise MemDBError(line[5:].decode("utf-8", "replace"))
        return line

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self._recv_some()
            if not chunk:
                raise MemDBError("connection closed while reading body")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _recv_some(self) -> bytes:
        assert self._sock is not None
        return self._sock.recv(32 * 1024)

    def _expect_ok(self) -> None:
        line = self._read_line()
        if line != b"+OK":
            raise MemDBError(f"expected +OK, got {line!r}")

    def _read_int(self) -> int:
        line = self._read_line()
        if not line.startswith(b":"):
            raise MemDBError(f"expected integer, got {line!r}")
        try:
            return int(line[1:])
        except ValueError as e:
            raise MemDBError(f"bad integer frame: {line!r}") from e

    def _read_bulk(self) -> Optional[bytes]:
        line = self._read_line()
        if not line.startswith(b"$"):
            raise MemDBError(f"expected bulk, got {line!r}")
        n = int(line[1:])
        if n == -1:
            return None
        body = self._read_exact(n + 2)  # include trailing \r\n
        if body[-2:] != b"\r\n":
            raise MemDBError("bulk missing CRLF")
        return bytes(body[:-2])


# ---------------------------------------------------------------------------
# Thread-safe pool (recommended for FastAPI apps)
# ---------------------------------------------------------------------------


class PooledMemDB:
    """A thread-safe pool of :class:`MemDB` connections.

    Use one instance per FastAPI app; borrow via :meth:`connection`::

        pool = PooledMemDB(host="127.0.0.1", port=5455, size=16)

        @app.get("/kv/{key}")
        def read(key: str):
            with pool.connection() as db:
                val = db.get(key)
            return {"value": val}
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5455,
        size: int = 8,
        timeout: float = 5.0,
    ) -> None:
        if size <= 0:
            raise ValueError("size must be > 0")
        self._host, self._port, self._timeout = host, port, timeout
        self._pool: "queue.Queue[MemDB]" = queue.Queue(maxsize=size)
        for _ in range(size):
            self._pool.put(MemDB(host=host, port=port, timeout=timeout))
        self._closed = False
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            while True:
                try:
                    conn = self._pool.get_nowait()
                except queue.Empty:
                    break
                conn.close()

    def connection(self) -> "_PooledConn":
        return _PooledConn(self)

    # internal
    def _borrow(self) -> MemDB:
        if self._closed:
            raise MemDBError("pool: closed")
        conn = self._pool.get(timeout=self._timeout)
        try:
            conn.connect()
        except Exception:
            self._pool.put(conn)  # give it back so pool doesn't shrink
            raise
        return conn

    def _release(self, conn: MemDB, healthy: bool) -> None:
        if not healthy:
            conn.close()
        self._pool.put(conn)


class _PooledConn:
    def __init__(self, pool: PooledMemDB) -> None:
        self._pool = pool
        self._conn: Optional[MemDB] = None
        self._healthy = True

    def __enter__(self) -> MemDB:
        self._conn = self._pool._borrow()
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._conn is not None
        # If the exception is a connection-level error, mark unhealthy so we
        # reconnect on the next borrow.
        self._healthy = exc_type is None or not issubclass(
            exc_type, (OSError, MemDBError)
        )
        self._pool._release(self._conn, self._healthy)
        self._conn = None
