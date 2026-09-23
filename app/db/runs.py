"""Read what an import recorded: the run, its column ledger and its issues."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import class_row, dict_row


@dataclass(frozen=True)
class StoredRun:
    id: UUID
    template_id: UUID | None
    template_name: str | None
    source_filename: str
    source_sha256: str
    verdict: str
    parser_version: str
    rows_total: int
    empty_rows: int
    rows_skipped: int
    sections_created: int
    items_created: int
    comments_created: int
    comment_types: dict[str, int]
    photos_found: int
    photos_stored: int
    started_at: datetime
    verified_at: datetime | None


@dataclass(frozen=True)
class StoredLedgerEntry:
    column_letter: str
    header: str
    outcome: str
    cell_count: int
    target_field: str | None


@dataclass(frozen=True)
class StoredIssue:
    kind: str
    severity: str
    scope: str
    row_number: int | None
    column_letter: str | None
    detail: str
    section_id: UUID | None
    item_id: UUID | None
    comment_id: UUID | None


def read_run(conn: psycopg.Connection, run_id: UUID) -> StoredRun | None:
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            "select r.*, t.name as template_name from import_run r"
            " left join template t on t.id = r.template_id where r.id = %s",
            [run_id],
        ).fetchone()
    return StoredRun(**row) if row else None


def read_ledger(conn: psycopg.Connection, run_id: UUID) -> list[StoredLedgerEntry]:
    with conn.cursor(row_factory=class_row(StoredLedgerEntry)) as cursor:
        return cursor.execute(
            "select column_letter, header, outcome, cell_count, target_field"
            " from cell_ledger where import_run_id = %s"
            " order by length(column_letter), column_letter",
            [run_id],
        ).fetchall()


def read_issues(conn: psycopg.Connection, run_id: UUID) -> list[StoredIssue]:
    with conn.cursor(row_factory=class_row(StoredIssue)) as cursor:
        return cursor.execute(
            "select kind, severity, scope, row_number, column_letter, detail,"
            " section_id, item_id, comment_id"
            " from import_issue where import_run_id = %s order by position",
            [run_id],
        ).fetchall()
