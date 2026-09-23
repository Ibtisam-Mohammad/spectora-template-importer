"""Database tests. They run only when TEST_DATABASE_URL points at a database they may wipe."""

import os

import psycopg
import pytest

from app.db.migrations import apply_migrations
from app.db.pool import connect

# Every table the migrations create, children first.
APP_TABLES = (
    "cell_ledger",
    "import_issue",
    "source_row",
    "comment_photo",
    "comment",
    "item",
    "section",
    "import_run",
    "template",
    "schema_migrations",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.database)


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("set TEST_DATABASE_URL to run the database tests")
    with connect(url) as conn:
        conn.execute("drop table if exists " + ", ".join(APP_TABLES) + " cascade")
        apply_migrations(conn)
    return url


@pytest.fixture
def conn(database_url: str):
    with connect(database_url) as connection:
        connection.execute("truncate template, import_run cascade")
        yield connection


def table_counts(conn: psycopg.Connection) -> dict[str, int]:
    return {
        table: conn.execute(f"select count(*) from {table}").fetchone()[0]
        for table in APP_TABLES
        if table != "schema_migrations"
    }
