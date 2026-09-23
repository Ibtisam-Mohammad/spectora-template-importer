import pytest
from fastapi.testclient import TestClient

from app import config
from app.db.editing import EDITABLE_COMMENT_COLUMNS
from app.db.pool import close_pool
from app.db.templates import list_templates, read_comment, read_tree
from app.main import app
from app.services import editing
from app.services.importer import import_file
from tests.integration.conftest import fake_photo_copier
from tests.paths import PROBE_HTML, RICH_COMMENT

# Each table's rows in tree order, as JSON without the row's own id and its parent link.
# Comparing these between a template and its copy catches a column the copy forgot.
DRIFT_QUERIES = {
    "section": "select to_jsonb(s) - 'id' - 'template_id' from section s"
    " where s.template_id = %s order by s.position",
    "item": "select to_jsonb(i) - 'id' - 'section_id' from item i"
    " join section s on s.id = i.section_id where s.template_id = %s"
    " order by s.position, i.position",
    "comment": "select to_jsonb(c) - 'id' - 'item_id' from comment c"
    " join item i on i.id = c.item_id join section s on s.id = i.section_id"
    " where s.template_id = %s order by s.position, i.position, c.position",
    "comment_photo": "select to_jsonb(p) - 'id' - 'comment_id' from comment_photo p"
    " join comment c on c.id = p.comment_id join item i on i.id = c.item_id"
    " join section s on s.id = i.section_id where s.template_id = %s"
    " order by s.position, i.position, c.position, p.position",
}


def rows(conn, query, template_id):
    return [row[0] for row in conn.execute(query, [template_id]).fetchall()]


def all_ids(tree):
    return (
        {s.id for s in tree.sections}
        | {i.id for i in tree.items()}
        | {c.id for c in tree.comments()}
        | {p.id for c in tree.comments() for p in c.photos}
    )


@pytest.fixture
def original(conn):
    outcome = import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, fake_photo_copier())
    return read_tree(conn, outcome.template_id)


def columns_left_at_their_default(conn, table: str) -> list[str]:
    """Columns that hold only null, '' or an empty array in every row of a table. A copy that
    forgot one of these would still look identical, so the drift test must have none."""
    columns = conn.execute(
        "select column_name from information_schema.columns where table_name = %s", [table]
    ).fetchall()
    return [
        column
        for (column,) in columns
        if not conn.execute(
            f"select exists (select 1 from {table} where {column} is not null"
            f" and {column}::text not in ('', '{{}}'))"
        ).fetchone()[0]
    ]


@pytest.mark.rule("E4")
def test_a_copy_matches_its_original_in_every_column(conn, original):
    # Give one comment a value in every editable column, so no column is at its default
    # everywhere and a column the copy forgot cannot hide.
    editing.save_comment(
        conn,
        original.comments()[0].id,
        {column: f"set {column}" for column in EDITABLE_COMMENT_COLUMNS},
    )
    for table in DRIFT_QUERIES:
        assert columns_left_at_their_default(conn, table) == [], table
    copy_id = editing.duplicate_template(conn, original.id)
    for table, query in DRIFT_QUERIES.items():
        source, copied = rows(conn, query, original.id), rows(conn, query, copy_id)
        assert copied == source, f"{table} differs in the copy"


@pytest.mark.rule("E4")
def test_a_copy_has_new_ids_everywhere_and_points_at_its_original(conn, original):
    copy = read_tree(conn, editing.duplicate_template(conn, original.id))
    assert not all_ids(copy) & all_ids(original)
    assert len(all_ids(copy)) == len(all_ids(original))
    assert (copy.origin, copy.copied_from_id) == ("copy", original.id)
    assert copy.name == f"{original.name} (copy)"


@pytest.mark.rule("E4")
def test_editing_the_copy_leaves_the_original_alone(conn, original):
    copy = read_tree(conn, editing.duplicate_template(conn, original.id))
    comment = copy.comments()[5]
    editing.save_comment(conn, comment.id, {"name": "Changed in copy", "body_html": "<p>x</p>"})
    editing.rename_node(conn, "section", copy.sections[0].id, "Copy section")
    editing.delete_node(conn, "item", copy.sections[1].items[0].id)
    editing.move_node(conn, "section", copy.sections[3].id, "up")
    editing.add_section(conn, copy.id, "Only in the copy")
    assert read_tree(conn, original.id) == original


@pytest.mark.rule("E4")
def test_editing_the_original_leaves_the_copy_alone(conn, original):
    copy = read_tree(conn, editing.duplicate_template(conn, original.id))
    editing.save_comment(conn, original.comments()[0].id, {"name": "Changed in original"})
    editing.delete_node(conn, "section", original.sections[2].id)
    editing.rename_template(conn, original.id, "Original renamed")
    assert read_tree(conn, copy.id) == copy


@pytest.mark.rule("E4", "E3")
def test_a_copy_outlives_its_original_and_can_still_be_reverted(conn, original):
    copy = read_tree(conn, editing.duplicate_template(conn, original.id))
    editing.delete_template(conn, original.id)
    survivor = read_tree(conn, copy.id)
    assert survivor.sections == copy.sections
    assert survivor.copied_from_id is None, "the link to a deleted original is cleared"
    comment = copy.comments()[3]
    editing.save_comment(conn, comment.id, {"body_html": "<p>edited in the copy</p>"})
    editing.revert_comment(conn, comment.id)
    assert read_comment(conn, comment.id) == comment
    editing.delete_template(conn, copy.id)
    assert conn.execute("select count(*) from import_run").fetchone()[0] == 0


@pytest.mark.rule("E4")
def test_a_copy_of_a_copy_is_still_complete(conn):
    outcome = import_file(conn, RICH_COMMENT.read_bytes(), RICH_COMMENT.name, None)
    first = editing.duplicate_template(conn, outcome.template_id)
    second = editing.duplicate_template(conn, first)
    for query in DRIFT_QUERIES.values():
        assert rows(conn, query, second) == rows(conn, query, outcome.template_id)


@pytest.mark.rule("E4")
def test_a_failed_copy_leaves_nothing(conn, original, monkeypatch):
    from app.db import copying

    steps = copying._COPY_STEPS
    monkeypatch.setattr(copying, "_COPY_STEPS", (*steps[:-1], "select 1 / 0"))
    with pytest.raises(Exception, match="division by zero"):
        editing.duplicate_template(conn, original.id)
    assert [t.id for t in list_templates(conn)] == [original.id]


def test_duplicating_a_missing_template_is_none(conn):
    assert editing.duplicate_template(conn, "00000000-0000-0000-0000-000000000000") is None


# ---------------------------------------------------------------- through the web


@pytest.fixture
def client(conn, database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    config.get_settings.cache_clear()
    yield TestClient(app)
    close_pool()
    config.get_settings.cache_clear()


@pytest.mark.rule("E4")
def test_duplicate_opens_the_copy_and_the_library_lists_it(client, conn, original):
    response = client.post(f"/t/{original.id}/duplicate", follow_redirects=False)
    assert response.status_code == 303
    copy_id = response.headers["location"].removeprefix("/t/")
    page = client.get(response.headers["location"]).text
    assert f"{original.name} (copy)" in page
    run_id = conn.execute("select id from import_run").fetchone()[0]
    assert f'href="/runs/{run_id}"' in page, "a copy links to the import it came from"
    library = {str(entry.id): entry for entry in list_templates(conn)}
    assert library[copy_id].origin == "copy"
    assert ">Copy<" in client.get("/").text
