"""Read templates. The tree query here is the one the editor renders from, and the one import
verification reads back (rule R3), so what verification checks is what the user sees."""

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.db.records import (
    NodeIssue,
    StoredComment,
    StoredItem,
    StoredPhoto,
    StoredSection,
    StoredTemplate,
    TemplateSummary,
)
from app.spectora.workbook import HEADER_ROW

_COMMENT_COLUMNS = (
    "position",
    "name",
    "body_html",
    "comment_type",
    "category",
    "choices",
    "unit_options",
    "recommendation",
    "source_order",
    "answer_type",
    "default_value",
    "default_value_2",
    "default_unit_type",
    "default_location",
    "estimate_min",
    "estimate_max",
    "locked",
    "simple_format",
    "disable_photos",
    "uses",
    "source_last_modified",
    "body_edited_at",
    "import_run_id",
    "source_row_number",
)

_COMMENT_SELECT = ", ".join(f"c.{column} as comment_{column}" for column in _COMMENT_COLUMNS)

_TREE_QUERY = f"""
select s.id as section_id, s.position as section_position, s.name as section_name,
       s.source_first_row as section_first_row,
       i.id as item_id, i.position as item_position, i.name as item_name,
       i.source_first_row as item_first_row,
       c.id as comment_id, {_COMMENT_SELECT},
       p.id as photo_id, p.position as photo_position, p.source_url as photo_source_url,
       p.caption as photo_caption, p.stored_path as photo_stored_path
from section s
left join item i on i.section_id = s.id
left join comment c on c.item_id = i.id
left join comment_photo p on p.comment_id = c.id
where s.template_id = %s
order by s.position, s.id, i.position, i.id, c.position, c.id, p.position, p.id
"""


def read_tree(conn: psycopg.Connection, template_id: UUID) -> StoredTemplate | None:
    """The whole template, every level in position order. None if there is no such template."""
    with conn.cursor(row_factory=dict_row) as cursor:
        template = cursor.execute(
            "select id, name, origin, copied_from_id, created_at, updated_at"
            " from template where id = %s",
            [template_id],
        ).fetchone()
        if template is None:
            return None
        rows = cursor.execute(_TREE_QUERY, [template_id]).fetchall()
    return StoredTemplate(**template, sections=_sections(rows))


def read_comment(conn: psycopg.Connection, comment_id: UUID) -> StoredComment | None:
    with conn.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute(
            f"select {_COMMENT_SELECT},"
            " p.id as photo_id, p.position as photo_position, p.source_url as photo_source_url,"
            " p.caption as photo_caption, p.stored_path as photo_stored_path"
            " from comment c left join comment_photo p on p.comment_id = c.id"
            " where c.id = %s order by p.position, p.id",
            [comment_id],
        ).fetchall()
    if not rows:
        return None
    return _comment(comment_id, rows[0], [row for row in rows if row["photo_id"] is not None])


def _sections(rows: Iterable[dict[str, Any]]) -> tuple[StoredSection, ...]:
    """Fold the joined rows back into nested nodes. Rows arrive in tree order, so each node's
    children follow it; dicts keep that order."""
    sections: dict[UUID, dict] = {}
    for row in rows:
        section = sections.setdefault(row["section_id"], {"row": row, "items": {}})
        if row["item_id"] is None:
            continue
        item = section["items"].setdefault(row["item_id"], {"row": row, "comments": {}})
        if row["comment_id"] is None:
            continue
        comment = item["comments"].setdefault(row["comment_id"], {"row": row, "photos": []})
        if row["photo_id"] is not None:
            comment["photos"].append(row)
    return tuple(
        StoredSection(
            id=section_id,
            position=section["row"]["section_position"],
            name=section["row"]["section_name"],
            source_first_row=section["row"]["section_first_row"],
            items=tuple(
                StoredItem(
                    id=item_id,
                    position=item["row"]["item_position"],
                    name=item["row"]["item_name"],
                    source_first_row=item["row"]["item_first_row"],
                    comments=tuple(
                        _comment(comment_id, comment["row"], comment["photos"])
                        for comment_id, comment in item["comments"].items()
                    ),
                )
                for item_id, item in section["items"].items()
            ),
        )
        for section_id, section in sections.items()
    )


def _comment(comment_id: UUID, row: dict[str, Any], photo_rows: list[dict]) -> StoredComment:
    values = {column: row[f"comment_{column}"] for column in _COMMENT_COLUMNS}
    values["choices"] = tuple(values["choices"])
    values["unit_options"] = tuple(values["unit_options"])
    photos = tuple(
        StoredPhoto(
            id=photo["photo_id"],
            position=photo["photo_position"],
            source_url=photo["photo_source_url"],
            caption=photo["photo_caption"],
            stored_path=photo["photo_stored_path"],
        )
        for photo in photo_rows
    )
    return StoredComment(id=comment_id, **values, photos=photos)


def list_templates(conn: psycopg.Connection) -> list[TemplateSummary]:
    """Every template, most recently changed first, with its size and latest import."""
    with conn.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute(
            """
            select t.id, t.name, t.origin, t.updated_at,
                   (select count(*) from section s where s.template_id = t.id) as sections,
                   (select count(*) from item i join section s on s.id = i.section_id
                     where s.template_id = t.id) as items,
                   (select count(*) from comment c join item i on i.id = c.item_id
                     join section s on s.id = i.section_id
                     where s.template_id = t.id) as comments,
                   coalesce(
                     (select r.id from import_run r where r.template_id = t.id
                       order by r.started_at desc limit 1),
                     (select c.import_run_id from comment c join item i on i.id = c.item_id
                       join section s on s.id = i.section_id
                       where s.template_id = t.id and c.import_run_id is not null limit 1)
                   ) as latest_run_id
            from template t
            order by t.updated_at desc, t.name
            """
        ).fetchall()
    return [TemplateSummary(**row) for row in rows]


def issues_by_node(conn: psycopg.Connection, template_id: UUID) -> dict[UUID, list[NodeIssue]]:
    """Import issues keyed by every node they concern: an issue about a comment is listed under
    the comment, its item and its section."""
    rows = conn.execute(
        "select i.section_id, i.item_id, i.comment_id, i.kind, i.severity, i.detail,"
        " i.row_number, i.column_letter, i.scope"
        " from import_issue i join section s on s.id = i.section_id"
        " where s.template_id = %s order by i.import_run_id, i.position",
        [template_id],
    ).fetchall()
    by_node: dict[UUID, list[NodeIssue]] = {}
    for section_id, item_id, comment_id, *fields in rows:
        issue = NodeIssue(*fields)
        for node_id in (section_id, item_id, comment_id):
            if node_id is not None:
                by_node.setdefault(node_id, []).append(issue)
    return by_node


def latest_run_id(conn: psycopg.Connection, template_id: UUID) -> UUID | None:
    """The template's latest import or, for a copy, the import its comments came from."""
    row = conn.execute(
        "select coalesce("
        " (select id from import_run where template_id = %(t)s order by started_at desc limit 1),"
        " (select c.import_run_id from comment c join item i on i.id = c.item_id"
        "  join section s on s.id = i.section_id"
        "  where s.template_id = %(t)s and c.import_run_id is not null limit 1))",
        {"t": template_id},
    ).fetchone()
    return row[0] if row else None


def source_rows_for_item(
    conn: psycopg.Connection, item_id: UUID
) -> dict[UUID, tuple[dict[str, str | None], dict[str, str | None]]]:
    """For each imported comment of an item, the header and the cells of its source row."""
    rows = conn.execute(
        "select c.id, header.raw, source.raw from comment c"
        " join source_row source on source.import_run_id = c.import_run_id"
        "  and source.row_number = c.source_row_number"
        " join source_row header on header.import_run_id = c.import_run_id"
        "  and header.row_number = %s"
        " where c.item_id = %s",
        [HEADER_ROW, item_id],
    ).fetchall()
    return {comment_id: (header, cells) for comment_id, header, cells in rows}
