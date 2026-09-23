"""Edits to a stored template. Each runs in one transaction that also updates the template's
modified time.

Rules E1 (everything can be renamed, edited, added, deleted and reordered), E2 (a body that is
not sent, or is sent unchanged, is left alone), E3 (revert to the source row), E5 (the same
checks as import, reported and never blocking), E6 (an edited body is marked), O5 (positions
belong to the app).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import psycopg

from app.db import copying, editing
from app.db.editing import EDITABLE_COMMENT_COLUMNS, Direction, NodeKind, NodePath
from app.db.imports import COMMENT_SOURCE_FIELDS
from app.db.records import StoredComment
from app.db.templates import read_comment
from app.spectora.checks import comment_issues
from app.spectora.columns import COMMENT_TYPES, map_columns, split_list
from app.spectora.model import Issue, ParsedComment
from app.spectora.parse import parse
from app.spectora.workbook import HEADER_ROW, workbook_from_rows

LIST_COLUMNS = ("choices", "unit_options")


@dataclass(frozen=True)
class CommentResult:
    path: NodePath
    comment_id: UUID
    summary: str
    """What happened, in a few words, for the comment's card."""
    warnings: tuple[Issue, ...]


def _is_blank(name: str) -> bool:
    return not name.strip()


def _named(name: str, default: str) -> str:
    return default if _is_blank(name) else name


def rename_template(conn: psycopg.Connection, template_id: UUID, name: str) -> None:
    if _is_blank(name):
        return
    with conn.transaction():
        editing.rename(conn, "template", template_id, name)
        editing.touch_template(conn, template_id)


def rename_node(
    conn: psycopg.Connection, kind: Literal["section", "item"], node_id: UUID, name: str
) -> NodePath | None:
    with conn.transaction():
        path = editing.locate(conn, kind, node_id)
        if path is not None and not _is_blank(name):
            editing.rename(conn, kind, node_id, name)
            editing.touch_template(conn, path.template_id)
    return path


def add_section(conn: psycopg.Connection, template_id: UUID, name: str) -> NodePath:
    with conn.transaction():
        section_id = editing.insert_node(conn, "section", template_id, _named(name, "New section"))
        editing.touch_template(conn, template_id)
    return NodePath(template_id, section_id)


def add_item(conn: psycopg.Connection, section_id: UUID, name: str) -> NodePath | None:
    with conn.transaction():
        path = editing.locate(conn, "section", section_id)
        if path is None:
            return None
        item_id = editing.insert_node(conn, "item", section_id, _named(name, "New item"))
        editing.touch_template(conn, path.template_id)
    return NodePath(path.template_id, section_id, item_id)


def add_comment(
    conn: psycopg.Connection, item_id: UUID, name: str, comment_type: str
) -> CommentResult | None:
    """A new comment at the end of its type's group, checked like an imported one."""
    kind = comment_type if comment_type in COMMENT_TYPES else COMMENT_TYPES[0]
    with conn.transaction():
        path = editing.locate(conn, "item", item_id)
        if path is None:
            return None
        comment_id = editing.insert_node(
            conn, "comment", item_id, _named(name, "New comment"), comment_type=kind
        )
        editing.touch_template(conn, path.template_id)
        warnings = _checks(read_comment(conn, comment_id))
    return CommentResult(path, comment_id, "Added.", warnings)


def save_comment(
    conn: psycopg.Connection, comment_id: UUID, submitted: Mapping[str, str]
) -> CommentResult | None:
    """Write the submitted fields that differ from what is stored. A field that is not
    submitted is left alone, so a form without the body never touches the body (rule E2)."""
    with conn.transaction():
        stored = read_comment(conn, comment_id)
        path = editing.locate(conn, "comment", comment_id)
        if stored is None or path is None:
            return None
        changes = _changes(stored, submitted)
        editing.update_comment(
            conn, comment_id, changes, body_edited=True if "body_html" in changes else None
        )
        if changes:
            editing.touch_template(conn, path.template_id)
        warnings = _checks(read_comment(conn, comment_id))
    summary = (
        f"Saved {len(changes)} field{'s' if len(changes) != 1 else ''}."
        if changes
        else "No changes to save."
    )
    return CommentResult(path, comment_id, summary, warnings)


def _changes(stored: StoredComment, submitted: Mapping[str, str]) -> dict[str, object]:
    changes: dict[str, object] = {}
    for column in EDITABLE_COMMENT_COLUMNS:
        if column not in submitted:
            continue
        value: object = submitted[column]
        if column in LIST_COLUMNS:
            value = split_list(submitted[column])
        if column == "name" and _is_blank(submitted[column]):
            continue
        if value != getattr(stored, column):
            changes[column] = value
    return changes


def revert_comment(conn: psycopg.Connection, comment_id: UUID) -> CommentResult | None:
    """Every editable field back to what its source row says, read with today's parser.
    Position is not reverted: it belongs to the app (rule O5)."""
    with conn.transaction():
        found = editing.source_row_of(conn, comment_id)
        path = editing.locate(conn, "comment", comment_id)
        if found is None or path is None:
            return None
        original = original_comment(*found)
        values = {
            column: getattr(original, COMMENT_SOURCE_FIELDS[column])
            for column in EDITABLE_COMMENT_COLUMNS
        }
        editing.update_comment(conn, comment_id, values, body_edited=False)
        editing.touch_template(conn, path.template_id)
        warnings = _checks(read_comment(conn, comment_id))
    summary = f"Put back as imported from row {found[1]}."
    return CommentResult(path, comment_id, summary, warnings)


def original_comment(
    header: dict[str, str | None], row_number: int, cells: dict[str, str | None]
) -> ParsedComment:
    """The comment one source row describes, parsed exactly as at import."""
    workbook = workbook_from_rows({HEADER_ROW: header, row_number: cells})
    [comment] = parse(workbook, map_columns(workbook), "").template.comments()
    return comment


def move_node(
    conn: psycopg.Connection, kind: NodeKind, node_id: UUID, direction: Direction
) -> NodePath | None:
    with conn.transaction():
        path = editing.locate(conn, kind, node_id)
        if path is not None and editing.move(conn, kind, node_id, direction):
            editing.touch_template(conn, path.template_id)
    return path


def delete_node(conn: psycopg.Connection, kind: NodeKind, node_id: UUID) -> NodePath | None:
    """Delete a node and everything under it. Returns where it was."""
    with conn.transaction():
        path = editing.locate(conn, kind, node_id)
        if path is not None:
            editing.delete_node(conn, kind, node_id)
            editing.touch_template(conn, path.template_id)
    return path


def duplicate_template(conn: psycopg.Connection, template_id: UUID) -> UUID | None:
    """A deep copy, all in one transaction. Editing either one never changes the other."""
    with conn.transaction():
        name = copying.template_name(conn, template_id)
        if name is None:
            return None
        return copying.copy_template(conn, template_id, f"{name} (copy)")


def delete_template(conn: psycopg.Connection, template_id: UUID) -> None:
    with conn.transaction():
        editing.delete_template(conn, template_id)


def _checks(comment: StoredComment | None) -> tuple[Issue, ...]:
    """The import's checks on a stored comment (rule E5)."""
    if comment is None:
        return ()
    parsed = ParsedComment(
        **{
            attribute: getattr(comment, column)
            for column, attribute in COMMENT_SOURCE_FIELDS.items()
        }
    )
    return tuple(comment_issues(parsed))
