"""Python client for the Go memdb server.

Usage:

    from memdb import MemDB

    db = MemDB("127.0.0.1", 5455)
    db.set("greeting", b"hello")
    db.get("greeting")   # -> b"hello"
    db.delete("greeting")
"""

from .client import MemDB, MemDBError, PooledMemDB

__all__ = ["MemDB", "MemDBError", "PooledMemDB"]
