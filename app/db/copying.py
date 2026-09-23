"""Deep-copy a template: set-based SQL, new ids at every level, nothing shared (rule E4).

Each level first gets a mapping from old id to new id, so children can find their new parent.
Every column is copied except the row's own id and its parent link. Copied comments keep their
link to the import run and source row they came from, so a copy can be reverted too.
The caller owns the transaction; the mapping tables are dropped when it commits.
"""

from uuid import UUID, uuid4

import psycopg

from app.db.imports import COMMENT_SOURCE_FIELDS

# Every comment column but its id and item_id. The drift test in tests/integration fails if a
# column is added to the table and not here.
COMMENT_COPY_COLUMNS = ("position", *COMMENT_SOURCE_FIELDS, "body_edited_at", "import_run_id")

_COPY_STEPS = (
    "create temp table section_map on commit drop as"
    " select id as old_id, gen_random_uuid() as new_id from section where template_id = %(source)s",
    "create temp table item_map on commit drop as"
    " select i.id as old_id, gen_random_uuid() as new_id, m.new_id as parent_id"
    " from item i join section_map m on m.old_id = i.section_id",
    "create temp table comment_map on commit drop as"
    " select c.id as old_id, gen_random_uuid() as new_id, m.new_id as parent_id"
    " from comment c join item_map m on m.old_id = c.item_id",
    "insert into template (id, name, origin, copied_from_id)"
    " select %(copy)s, %(name)s, 'copy', id from template where id = %(source)s",
    "insert into section (id, template_id, name, position, source_first_row)"
    " select m.new_id, %(copy)s, s.name, s.position, s.source_first_row"
    " from section s join section_map m on m.old_id = s.id",
    "insert into item (id, section_id, name, position, source_first_row)"
    " select m.new_id, m.parent_id, i.name, i.position, i.source_first_row"
    " from item i join item_map m on m.old_id = i.id",
    f"insert into comment (id, item_id, {', '.join(COMMENT_COPY_COLUMNS)})"
    f" select m.new_id, m.parent_id, {', '.join(f'c.{c}' for c in COMMENT_COPY_COLUMNS)}"
    " from comment c join comment_map m on m.old_id = c.id",
    "insert into comment_photo (comment_id, position, source_url, caption, stored_path)"
    " select m.new_id, p.position, p.source_url, p.caption, p.stored_path"
    " from comment_photo p join comment_map m on m.old_id = p.comment_id",
)


def copy_template(conn: psycopg.Connection, source_id: UUID, name: str) -> UUID:
    copy_id = uuid4()
    for step in _COPY_STEPS:
        conn.execute(step, {"source": source_id, "copy": copy_id, "name": name})
    return copy_id


def template_name(conn: psycopg.Connection, template_id: UUID) -> str | None:
    row = conn.execute("select name from template where id = %s", [template_id]).fetchone()
    return row[0] if row else None
