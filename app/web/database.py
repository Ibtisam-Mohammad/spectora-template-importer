"""The request's database connection."""

from collections.abc import Iterator

import psycopg

from app.config import get_settings
from app.db.pool import pooled_connection


class DatabaseNotConfigured(Exception):
    pass


def db() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: one pooled connection for the request."""
    url = get_settings().database_url
    if url is None:
        raise DatabaseNotConfigured
    with pooled_connection(url) as conn:
        yield conn
