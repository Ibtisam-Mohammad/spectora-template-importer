"""Database connections.

Supabase's transaction pooler (port 6543) cannot use prepared statements, so psycopg is told
never to prepare. A NullConnectionPool keeps no idle connections, which suits short-lived
serverless instances; the pooler does the pooling. Connections are in autocommit mode, and
every multi-statement change runs inside an explicit `conn.transaction()` in the services.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import NullConnectionPool

CONNECTION_OPTIONS = {"autocommit": True, "prepare_threshold": None}

_pool: NullConnectionPool | None = None


def connect(url: str) -> psycopg.Connection:
    """One connection, for the command line and tests."""
    return psycopg.connect(url, **CONNECTION_OPTIONS)


def open_pool(url: str) -> None:
    global _pool
    if _pool is None:
        _pool = NullConnectionPool(url, max_size=4, kwargs=CONNECTION_OPTIONS, open=True)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def pooled_connection() -> Iterator[psycopg.Connection]:
    if _pool is None:
        raise RuntimeError("The database is not configured. Set DATABASE_URL.")
    with _pool.connection() as conn:
        yield conn
