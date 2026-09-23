"""Write one import: the template tree, its source rows, column ledger and issues.

Rules F7 (every cell kept verbatim in the source rows) and R2 (the run records the file, its
hash, the verdict, the parser version and the counts). The caller owns the transaction.

Ids are generated here rather than by the database, so issues can be linked to the nodes they
are about without reading anything back.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.spectora.analysis import PARSER_VERSION, Analysis
from app.spectora.model import Issue, IssueKind, ParsedComment, Scope

# Comment columns filled from the parse, and the ParsedComment attribute each one takes.
# Verification reads the same mapping back, so a column left out here is never checked.
COMMENT_SOURCE_FIELDS: dict[str, str] = {
    "name": "name",
    "body_html": "body_html",
    "comment_type": "comment_type",
    "category": "category",
    "choices": "choices",
    "unit_options": "unit_options",
    "recommendation": "recommendation",
    "source_order": "order_raw",
    "answer_type": "answer_type",
    "default_value": "default_value",
    "default_value_2": "default_value_2",
    "default_unit_type": "default_unit_type",
    "default_location": "default_location",
    "estimate_min": "estimate_min",
    "estimate_max": "estimate_max",
    "locked": "locked",
    "simple_format": "simple_format",
    "disable_photos": "disable_photos",
    "uses": "uses",
    "source_last_modified": "last_modified",
    "source_row_number": "row",
}

HEADER_ROW = 1


@dataclass(frozen=True)
class NewImport:
    analysis: Analysis
    filename: str
    sha256: str
    started_at: datetime
    issues: tuple[Issue, ...]
    """Everything to record: the analysis's issues plus those found while importing."""
    photo_paths: Mapping[str, str | None]
    """Photo URL to its stored copy, or None when it was not copied."""


@dataclass(frozen=True)
class ImportIds:
    template_id: UUID
    run_id: UUID


@dataclass(frozen=True)
class _NodeIds:
    """The node an issue belongs to, and that node's ancestors."""

    section_id: UUID | None = None
    item_id: UUID | None = None
    comment_id: UUID | None = None


def source_rows(analysis: Analysis) -> dict[int, dict[str, str | None]]:
    """The sheet as read, keyed by row number, with the header as row 1."""
    rows = {HEADER_ROW: dict(analysis.workbook.header)}
    rows.update({row.number: row.cells for row in analysis.workbook.rows})
    return rows


def comment_values(comment: ParsedComment) -> list:
    values = [getattr(comment, attribute) for attribute in COMMENT_SOURCE_FIELDS.values()]
    return [list(value) if isinstance(value, tuple) else value for value in values]


def insert_import(conn: psycopg.Connection, new: NewImport) -> ImportIds:
    template = new.analysis.template
    ids = ImportIds(uuid4(), uuid4())
    conn.execute(
        "insert into template (id, name, origin) values (%s, %s, 'import')",
        [ids.template_id, template.name],
    )
    _insert_run(conn, ids, new)
    nodes = _insert_tree(conn, ids, new)
    with conn.cursor() as cursor:
        cursor.executemany(
            "insert into source_row (import_run_id, row_number, raw) values (%s, %s, %s)",
            [[ids.run_id, number, Jsonb(raw)] for number, raw in source_rows(new.analysis).items()],
        )
        cursor.executemany(
            "insert into cell_ledger (import_run_id, column_letter, header, outcome,"
            " cell_count, target_field) values (%s, %s, %s, %s, %s, %s)",
            [
                [ids.run_id, e.column, e.header, e.outcome, e.cell_count, e.target_field]
                for e in new.analysis.ledger
            ],
        )
        cursor.executemany(
            "insert into import_issue (import_run_id, position, kind, severity, scope,"
            " row_number, column_letter, detail, section_id, item_id, comment_id)"
            " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                _issue_values(ids.run_id, position, issue, nodes)
                for position, issue in enumerate(new.issues, start=1)
            ],
        )
    return ids


def _insert_run(conn: psycopg.Connection, ids: ImportIds, new: NewImport) -> None:
    analysis, template = new.analysis, new.analysis.template
    photos = [photo for comment in template.comments() for photo in comment.photos if photo.url]
    conn.execute(
        "insert into import_run (id, template_id, source_filename, source_sha256, verdict,"
        " parser_version, rows_total, empty_rows, rows_skipped, sections_created, items_created,"
        " comments_created, comment_types, photos_found, photos_stored, started_at)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            ids.run_id,
            ids.template_id,
            new.filename,
            new.sha256,
            analysis.detection.verdict.value,
            PARSER_VERSION,
            len(analysis.workbook.rows),
            template.empty_rows,
            sum(1 for issue in new.issues if issue.kind is IssueKind.ROW_SKIPPED),
            len(template.sections),
            len(template.items()),
            len(template.comments()),
            Jsonb(Counter(comment.comment_type for comment in template.comments())),
            len(photos),
            sum(1 for photo in photos if new.photo_paths.get(photo.url)),
            new.started_at,
        ],
    )


def _insert_tree(
    conn: psycopg.Connection, ids: ImportIds, new: NewImport
) -> dict[tuple[Scope, int], _NodeIds]:
    """Insert sections, items, comments and photos. Returns each node's ids keyed by the scope
    and source row an issue would name it by."""
    sections, items, comments, photos = [], [], [], []
    nodes: dict[tuple[Scope, int], _NodeIds] = {}
    for section_position, section in enumerate(new.analysis.template.sections, start=1):
        section_id = uuid4()
        sections.append(
            [section_id, ids.template_id, section.name, section_position, section.first_row]
        )
        nodes[(Scope.SECTION, section.first_row)] = _NodeIds(section_id)
        for item_position, item in enumerate(section.items, start=1):
            item_id = uuid4()
            items.append([item_id, section_id, item.name, item_position, item.first_row])
            nodes[(Scope.ITEM, item.first_row)] = _NodeIds(section_id, item_id)
            for comment_position, comment in enumerate(item.comments, start=1):
                comment_id = uuid4()
                comments.append(
                    [comment_id, item_id, comment_position, ids.run_id, *comment_values(comment)]
                )
                nodes[(Scope.COMMENT, comment.row)] = _NodeIds(section_id, item_id, comment_id)
                photos.extend(
                    [
                        comment_id,
                        photo.slot,
                        photo.url,
                        photo.caption,
                        new.photo_paths.get(photo.url),
                    ]
                    for photo in comment.photos
                )
    comment_columns = ", ".join(COMMENT_SOURCE_FIELDS)
    comment_slots = ", ".join(["%s"] * (4 + len(COMMENT_SOURCE_FIELDS)))
    with conn.cursor() as cursor:
        cursor.executemany(
            "insert into section (id, template_id, name, position, source_first_row)"
            " values (%s, %s, %s, %s, %s)",
            sections,
        )
        cursor.executemany(
            "insert into item (id, section_id, name, position, source_first_row)"
            " values (%s, %s, %s, %s, %s)",
            items,
        )
        cursor.executemany(
            f"insert into comment (id, item_id, position, import_run_id, {comment_columns})"
            f" values ({comment_slots})",
            comments,
        )
        cursor.executemany(
            "insert into comment_photo (comment_id, position, source_url, caption, stored_path)"
            " values (%s, %s, %s, %s, %s)",
            photos,
        )
    return nodes


def _issue_values(
    run_id: UUID, position: int, issue: Issue, nodes: dict[tuple[Scope, int], _NodeIds]
) -> list:
    node = _NodeIds()
    if issue.scope is not Scope.FILE and issue.row is not None:
        node = nodes.get((issue.scope, issue.row), node)
    return [
        run_id,
        position,
        issue.kind.value,
        issue.severity.value,
        issue.scope.value,
        issue.row,
        issue.column,
        issue.detail,
        node.section_id,
        node.item_id,
        node.comment_id,
    ]


def mark_verified(conn: psycopg.Connection, run_id: UUID) -> None:
    conn.execute("update import_run set verified_at = clock_timestamp() where id = %s", [run_id])


def read_source_rows(conn: psycopg.Connection, run_id: UUID) -> dict[int, dict[str, str | None]]:
    rows = conn.execute(
        "select row_number, raw from source_row where import_run_id = %s", [run_id]
    ).fetchall()
    return {number: raw for number, raw in rows}


def count_rows(conn: psycopg.Connection, table: str, run_id: UUID) -> int:
    """Rows a run owns in one of its own tables."""
    if table not in ("import_issue", "cell_ledger", "source_row"):
        raise ValueError(f"{table} is not a per-run table")
    row = conn.execute(
        f"select count(*) from {table} where import_run_id = %s", [run_id]
    ).fetchone()
    return row[0] if row else 0
