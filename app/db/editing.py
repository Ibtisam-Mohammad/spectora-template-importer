"""Change a stored template: rename, edit, add, delete and reorder. The caller owns the
transaction, and touches the template's modified time through `touch_template`.

Rule O5: position belongs to the app once imported. Reordering swaps positions, and nothing
here or elsewhere re-derives them from the file.
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

import psycopg

from app.db.imports import COMMENT_SOURCE_FIELDS, HEADER_ROW

NodeKind = Literal["section", "item", "comment"]
Direction = Literal["up", "down"]

# Each node's table and the column naming its parent. Identifiers come only from here.
_PARENT = {"section": "template_id", "item": "section_id", "comment": "item_id"}

# Comment columns a user can change. The source columns record provenance and stay as imported.
EDITABLE_COMMENT_COLUMNS = tuple(
    column for column in COMMENT_SOURCE_FIELDS if not column.startswith("source_")
)


@dataclass(frozen=True)
class NodePath:
    """Where a node sits: its template and, below that, its section and item."""

    template_id: UUID
    section_id: UUID | None = None
    item_id: UUID | None = None


def locate(conn: psycopg.Connection, kind: NodeKind, node_id: UUID) -> NodePath | None:
    queries = {
        "section": "select s.template_id, s.id, null from section s where s.id = %s",
        "item": "select s.template_id, s.id, i.id from item i"
        " join section s on s.id = i.section_id where i.id = %s",
        "comment": "select s.template_id, s.id, i.id from comment c"
        " join item i on i.id = c.item_id join section s on s.id = i.section_id"
        " where c.id = %s",
    }
    row = conn.execute(queries[kind], [node_id]).fetchone()
    return NodePath(*row) if row else None


def touch_template(conn: psycopg.Connection, template_id: UUID) -> None:
    conn.execute("update template set updated_at = now() where id = %s", [template_id])


def rename(
    conn: psycopg.Connection, kind: Literal["template", "section", "item"], node_id: UUID, name: str
) -> None:
    table = {"template": "template", "section": "section", "item": "item"}[kind]
    conn.execute(f"update {table} set name = %s where id = %s", [name, node_id])


def insert_node(
    conn: psycopg.Connection, kind: NodeKind, parent_id: UUID, name: str, **values: str
) -> UUID:
    """A new node after its siblings. For a comment, `values` sets further columns."""
    parent = _PARENT[kind]
    node_id = uuid4()
    last = f"(select coalesce(max(position), 0) + 1 from {kind} where {parent} = %s)"
    columns = ["id", parent, "name", "position", *values]
    slots = ["%s", "%s", "%s", last, *(["%s"] * len(values))]
    conn.execute(
        f"insert into {kind} ({', '.join(columns)}) values ({', '.join(slots)})",
        [node_id, parent_id, name, parent_id, *values.values()],
    )
    return node_id


def delete_node(conn: psycopg.Connection, kind: NodeKind, node_id: UUID) -> None:
    conn.execute(f"delete from {kind} where id = %s", [node_id])


def delete_template(conn: psycopg.Connection, template_id: UUID) -> None:
    """Delete a template, then any import run that no remaining comment points at."""
    conn.execute("delete from template where id = %s", [template_id])
    conn.execute(
        "delete from import_run r where r.template_id is null"
        " and not exists (select 1 from comment c where c.import_run_id = r.id)"
    )


def move(conn: psycopg.Connection, kind: NodeKind, node_id: UUID, direction: Direction) -> bool:
    """Swap a node's position with its neighbour. Comments move within their type's group,
    because that is how they are shown. False when there is no neighbour that way."""
    parent = _PARENT[kind]
    group = ", comment_type" if kind == "comment" else ""
    row = conn.execute(
        f"select {parent}, position{group} from {kind} where id = %s", [node_id]
    ).fetchone()
    if row is None:
        return False
    parent_id, position, *rest = row
    same_group = " and comment_type = %s" if kind == "comment" else ""
    before = direction == "up"
    neighbour = conn.execute(
        f"select id, position from {kind} where {parent} = %s{same_group}"
        f" and (position, id) {'<' if before else '>'} (%s, %s)"
        f" order by position {'desc' if before else 'asc'}, id {'desc' if before else 'asc'}"
        " limit 1",
        [parent_id, *rest, position, node_id],
    ).fetchone()
    if neighbour is None:
        return False
    neighbour_id, neighbour_position = neighbour
    conn.execute(f"update {kind} set position = %s where id = %s", [neighbour_position, node_id])
    conn.execute(f"update {kind} set position = %s where id = %s", [position, neighbour_id])
    return True


def update_comment(
    conn: psycopg.Connection, comment_id: UUID, values: dict[str, object], body_edited: bool | None
) -> None:
    """Set the given columns. `body_edited` True marks the body edited now, False clears the
    mark (a revert), None leaves it."""
    unknown = set(values) - set(EDITABLE_COMMENT_COLUMNS)
    if unknown:
        raise ValueError(f"not editable: {sorted(unknown)}")
    assignments = [f"{column} = %s" for column in values]
    if body_edited is not None:
        assignments.append("body_edited_at = now()" if body_edited else "body_edited_at = null")
    if not assignments:
        return
    conn.execute(
        f"update comment set {', '.join(assignments)} where id = %s",
        [*(list(v) if isinstance(v, tuple) else v for v in values.values()), comment_id],
    )


def source_row_of(
    conn: psycopg.Connection, comment_id: UUID
) -> tuple[dict[str, str | None], int, dict[str, str | None]] | None:
    """The header, row number and cells of the row a comment was imported from."""
    row = conn.execute(
        "select header.raw, source.row_number, source.raw from comment c"
        " join source_row source on source.import_run_id = c.import_run_id"
        "  and source.row_number = c.source_row_number"
        " join source_row header on header.import_run_id = c.import_run_id"
        "  and header.row_number = %s"
        " where c.id = %s",
        [HEADER_ROW, comment_id],
    ).fetchone()
    return (row[0], row[1], row[2]) if row else None
