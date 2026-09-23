"""Apply the SQL files in supabase/migrations in name order, each exactly once."""

from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def pending_migrations(conn: psycopg.Connection) -> list[Path]:
    conn.execute(
        "create table if not exists schema_migrations ("
        " filename text primary key, applied_at timestamptz not null default now())"
    )
    conn.execute("alter table schema_migrations enable row level security")
    applied = {row[0] for row in conn.execute("select filename from schema_migrations")}
    return [path for path in sorted(MIGRATIONS_DIR.glob("*.sql")) if path.name not in applied]


def apply_migrations(conn: psycopg.Connection) -> list[str]:
    """Apply every pending migration, each in its own transaction. Returns the files applied."""
    applied = []
    for path in pending_migrations(conn):
        with conn.transaction():
            conn.execute(path.read_text("utf-8"))
            conn.execute("insert into schema_migrations (filename) values (%s)", [path.name])
        applied.append(path.name)
    return applied
