import pytest
from fastapi.testclient import TestClient

from app import config
from app.db.editing import EDITABLE_COMMENT_COLUMNS
from app.db.pool import close_pool, connect
from app.db.templates import read_comment, read_tree
from app.main import app
from app.services import editing
from app.services.importer import import_file
from app.services.reporting import build_report
from app.spectora.model import IssueKind
from app.web.routes.editor import editor_url
from tests.paths import PRIMARY, PROBE_HTML, RICH_COMMENT


@pytest.fixture
def tree(conn):
    outcome = import_file(conn, PRIMARY.read_bytes(), PRIMARY.name, None)
    return read_tree(conn, outcome.template_id)


def fresh(database_url, template_id):
    """The template as a new connection sees it, so an edit is known to be committed."""
    with connect(database_url) as other:
        return read_tree(other, template_id)


def updated_at(conn, template_id):
    row = conn.execute("select updated_at from template where id = %s", [template_id]).fetchone()
    return row[0]


def a_comment_with_everything(tree):
    """A deficiency with a body, a severity and a location, so every kind of field is set."""
    return next(
        c for c in tree.comments() if c.comment_type == "defect" and c.body_html and c.category
    )


def form_of(comment) -> dict[str, str]:
    """What the comment form submits when nothing is touched: every field but the body."""
    values = {}
    for column in EDITABLE_COMMENT_COLUMNS:
        value = getattr(comment, column)
        values[column] = ", ".join(value) if isinstance(value, tuple) else value
    del values["body_html"]
    return values


# ---------------------------------------------------------------- E1 rename, add, delete


@pytest.mark.rule("E1")
def test_renames_persist_and_touch_the_template(conn, database_url, tree):
    before = updated_at(conn, tree.id)
    section, item = tree.sections[2], tree.sections[2].items[1]
    editing.rename_template(conn, tree.id, "My template")
    editing.rename_node(conn, "section", section.id, "Roof & Gutters")
    editing.rename_node(conn, "item", item.id, "Flashing <new>")
    after = fresh(database_url, tree.id)
    assert after.name == "My template"
    assert after.sections[2].name == "Roof & Gutters"
    assert after.sections[2].items[1].name == "Flashing <new>"
    assert updated_at(conn, tree.id) > before


@pytest.mark.rule("E1")
def test_a_blank_name_keeps_the_old_one(conn, tree):
    editing.rename_node(conn, "section", tree.sections[0].id, "   ")
    assert read_tree(conn, tree.id).sections[0].name == tree.sections[0].name


@pytest.mark.rule("E1")
def test_added_nodes_go_last_and_persist(conn, database_url, tree):
    section_path = editing.add_section(conn, tree.id, "Pool")
    item_path = editing.add_item(conn, section_path.section_id, "Pump")
    result = editing.add_comment(conn, item_path.item_id, "Pump noisy", "defect")
    after = fresh(database_url, tree.id)
    assert after.sections[-1].name == "Pool"
    assert after.sections[-1].items[0].name == "Pump"
    [comment] = after.sections[-1].items[0].comments
    assert (comment.name, comment.comment_type) == ("Pump noisy", "defect")
    assert comment.source_row_number is None
    assert result.comment_id == comment.id


@pytest.mark.rule("E1")
def test_deleting_removes_the_node_and_everything_under_it(conn, database_url, tree):
    section = tree.sections[3]
    editing.delete_node(conn, "comment", tree.sections[0].items[0].comments[0].id)
    editing.delete_node(conn, "item", tree.sections[1].items[0].id)
    editing.delete_node(conn, "section", section.id)
    after = fresh(database_url, tree.id)
    assert len(after.sections) == len(tree.sections) - 1
    assert section.id not in {s.id for s in after.sections}
    assert len(after.sections[1].items) == len(tree.sections[1].items) - 1
    assert len(after.sections[0].items[0].comments) == len(tree.sections[0].items[0].comments) - 1
    orphans = conn.execute(
        "select count(*) from item where section_id = %s", [section.id]
    ).fetchone()[0]
    assert orphans == 0


@pytest.mark.rule("E1")
def test_deleting_a_template_removes_its_import_too(conn, tree):
    editing.delete_template(conn, tree.id)
    assert read_tree(conn, tree.id) is None
    for table in ("import_run", "source_row", "section", "comment"):
        assert conn.execute(f"select count(*) from {table}").fetchone()[0] == 0


# ---------------------------------------------------------------- O5 reordering


@pytest.mark.rule("O5", "E1")
def test_moving_sections_and_items_changes_their_order_and_it_stays(conn, database_url, tree):
    first, second = tree.sections[0], tree.sections[1]
    editing.move_node(conn, "section", second.id, "up")
    items = tree.sections[4].items
    editing.move_node(conn, "item", items[0].id, "down")
    after = fresh(database_url, tree.id)
    assert [s.id for s in after.sections[:2]] == [second.id, first.id]
    assert [i.id for i in after.sections[4].items[:2]] == [items[1].id, items[0].id]


@pytest.mark.rule("O5")
def test_moving_past_either_end_changes_nothing(conn, tree):
    editing.move_node(conn, "section", tree.sections[0].id, "up")
    editing.move_node(conn, "section", tree.sections[-1].id, "down")
    assert [s.id for s in read_tree(conn, tree.id).sections] == [s.id for s in tree.sections]


@pytest.mark.rule("O5")
def test_a_comment_moves_within_its_type_group(conn, tree):
    item = next(
        i
        for i in tree.items()
        if sum(c.comment_type == "defect" for c in i.comments) >= 2
        and any(c.comment_type != "defect" for c in i.comments)
    )
    defects = [c for c in item.comments if c.comment_type == "defect"]
    others = [c.id for c in item.comments if c.comment_type != "defect"]
    editing.move_node(conn, "comment", defects[0].id, "up")  # already first of its group
    editing.move_node(conn, "comment", defects[1].id, "up")
    moved = next(i for i in read_tree(conn, tree.id).items() if i.id == item.id)
    moved_defects = [c.id for c in moved.comments if c.comment_type == "defect"]
    assert moved_defects[:2] == [defects[1].id, defects[0].id]
    assert [c.id for c in moved.comments if c.comment_type != "defect"] == others


@pytest.mark.rule("O5")
def test_the_file_side_of_the_report_does_not_follow_edits(conn, tree):
    editing.move_node(conn, "section", tree.sections[1].id, "up")
    editing.delete_node(conn, "section", tree.sections[5].id)
    run_id = conn.execute("select id from import_run").fetchone()[0]
    report = build_report(conn, run_id)
    assert report.in_file.sections == 13
    assert report.rederived_matches


# ---------------------------------------------------------------- E2 and E6 the body


@pytest.mark.rule("E2")
def test_saving_the_untouched_form_changes_nothing(conn, database_url, tree):
    comment = a_comment_with_everything(tree)
    before = updated_at(conn, tree.id)
    result = editing.save_comment(conn, comment.id, form_of(comment))
    assert result.summary == "No changes to save."
    assert read_comment(conn, comment.id) == comment
    assert updated_at(conn, tree.id) == before


@pytest.mark.rule("E2")
def test_a_body_sent_unchanged_is_not_marked_edited(conn, tree):
    comment = a_comment_with_everything(tree)
    editing.save_comment(conn, comment.id, {"body_html": comment.body_html})
    assert read_comment(conn, comment.id).body_edited_at is None


@pytest.mark.rule("E2", "E1")
def test_other_fields_save_without_touching_the_body(conn, tree):
    comment = a_comment_with_everything(tree)
    form = form_of(comment) | {"name": "Renamed", "choices": "One, Two ,, Three", "category": "1"}
    result = editing.save_comment(conn, comment.id, form)
    saved = read_comment(conn, comment.id)
    assert (saved.name, saved.choices, saved.category) == ("Renamed", ("One", "Two", "Three"), "1")
    assert saved.body_html == comment.body_html
    assert saved.body_edited_at is None
    assert result.summary == "Saved 3 fields."


@pytest.mark.rule("E6", "E1")
def test_an_edited_body_is_saved_and_marked(conn, database_url, tree):
    comment = a_comment_with_everything(tree)
    editing.save_comment(conn, comment.id, {"body_html": "<p>New <strong>text</strong></p>"})
    saved = next(c for c in fresh(database_url, tree.id).comments() if c.id == comment.id)
    assert saved.body_html == "<p>New <strong>text</strong></p>"
    assert saved.body_edited_at is not None


# ---------------------------------------------------------------- E3 revert


@pytest.mark.rule("E3")
def test_revert_puts_every_field_back_as_imported(conn, tree):
    comment = a_comment_with_everything(tree)
    changes = {column: "changed" for column in EDITABLE_COMMENT_COLUMNS}
    editing.save_comment(conn, comment.id, changes)
    assert read_comment(conn, comment.id).body_edited_at is not None
    result = editing.revert_comment(conn, comment.id)
    assert read_comment(conn, comment.id) == comment
    assert result.summary == f"Put back as imported from row {comment.source_row_number}."


@pytest.mark.rule("E3")
def test_revert_restores_rich_html_and_photos_are_untouched(conn):
    outcome = import_file(conn, RICH_COMMENT.read_bytes(), RICH_COMMENT.name, None)
    rich = next(
        c for c in read_tree(conn, outcome.template_id).comments() if "<table" in c.body_html
    )
    editing.save_comment(conn, rich.id, {"body_html": "<p>flattened by an editor</p>"})
    editing.revert_comment(conn, rich.id)
    assert read_comment(conn, rich.id) == rich


@pytest.mark.rule("E3")
def test_a_comment_added_here_has_nothing_to_revert_to(conn, tree):
    result = editing.add_comment(conn, tree.items()[0].id, "Fresh", "info")
    assert editing.revert_comment(conn, result.comment_id) is None


# ---------------------------------------------------------------- E5 checks, never blocks


@pytest.mark.rule("E5")
def test_edits_get_the_import_checks_and_are_saved_anyway(conn, tree):
    comment = a_comment_with_everything(tree)
    result = editing.save_comment(
        conn, comment.id, {"comment_type": "note", "answer_type": "checkbox", "choices": ""}
    )
    kinds = sorted(issue.kind for issue in result.warnings)
    assert kinds == [
        IssueKind.INVARIANT_VIOLATED,
        IssueKind.INVARIANT_VIOLATED,
        IssueKind.UNEXPECTED_VALUE,
    ]
    saved = read_comment(conn, comment.id)
    assert (saved.comment_type, saved.answer_type) == ("note", "checkbox")


@pytest.mark.rule("E5")
def test_a_new_deficiency_is_told_it_has_no_severity(conn, tree):
    result = editing.add_comment(conn, tree.items()[0].id, "Leak", "defect")
    assert [issue.detail for issue in result.warnings] == ["Deficiency 'Leak' has no Category."]


# ---------------------------------------------------------------- through the web


@pytest.fixture
def client(conn, database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    config.get_settings.cache_clear()
    yield TestClient(app)
    close_pool()
    config.get_settings.cache_clear()


HTMX = {"HX-Request": "true"}


@pytest.mark.rule("E2")
def test_a_posted_form_without_the_body_leaves_it_byte_identical(client, conn, tree):
    comment = a_comment_with_everything(tree)
    response = client.post(f"/comments/{comment.id}", data=form_of(comment), headers=HTMX)
    assert response.status_code == 200
    assert "No changes to save." in response.text
    assert read_comment(conn, comment.id) == comment


@pytest.mark.rule("E6")
def test_the_editor_marks_an_edited_comment(client, conn, tree):
    comment = a_comment_with_everything(tree)
    response = client.post(
        f"/comments/{comment.id}", data={"body_html": "<p>changed</p>"}, headers=HTMX
    )
    card = response.text.split(f'id="comment-{comment.id}"', 1)[1].split("</summary>", 1)[0]
    assert ">Edited</span>" in card
    assert " open>" in response.text.split(f'id="comment-{comment.id}"', 1)[1][:10]


@pytest.mark.rule("E1")
def test_an_htmx_edit_sets_the_address_and_a_plain_post_redirects(client, tree):
    section = tree.sections[3]
    swapped = client.post(f"/sections/{section.id}/rename", data={"name": "Attic"}, headers=HTMX)
    assert swapped.status_code == 200
    address = editor_url(tree.id, section.id, section.items[0].id)
    assert swapped.headers["HX-Push-Url"] == address
    plain = client.post(
        f"/sections/{section.id}/rename", data={"name": "Attic 2"}, follow_redirects=False
    )
    assert plain.status_code == 303
    assert plain.headers["location"] == address


@pytest.mark.rule("E1")
def test_the_web_routes_cover_every_operation(client, conn, tree):
    section, item = tree.sections[0], tree.sections[0].items[0]
    comment = item.comments[0]
    for url, data in [
        (f"/t/{tree.id}/rename", {"name": "Renamed template"}),
        (f"/t/{tree.id}/sections", {"name": "New section"}),
        (f"/sections/{section.id}/items", {"name": "New item"}),
        (f"/items/{item.id}/comments", {"name": "New comment", "comment_type": "limit"}),
        (f"/items/{item.id}/rename", {"name": "Renamed item"}),
        (f"/items/{item.id}/move", {"direction": "down"}),
        (f"/sections/{section.id}/move", {"direction": "down"}),
        (f"/comments/{comment.id}/move", {"direction": "down"}),
        (f"/comments/{comment.id}/revert", {}),
        (f"/comments/{comment.id}/delete", {}),
    ]:
        assert client.post(url, data=data, headers=HTMX).status_code == 200, url
    after = read_tree(conn, tree.id)
    assert after.name == "Renamed template"
    assert after.sections[-1].name == "New section"
    assert comment.id not in {c.id for c in after.comments()}
    deleted = client.post(f"/t/{tree.id}/delete", follow_redirects=False)
    assert (deleted.status_code, deleted.headers["location"]) == (303, "/")
    assert client.get(f"/t/{tree.id}").status_code == 404


def test_editing_something_that_is_gone_is_not_found(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/sections/{missing}/rename", data={"name": "x"}).status_code == 404
    assert client.post(f"/comments/{missing}", data={"name": "x"}).status_code == 404


def test_photos_survive_a_comment_edit(conn):
    outcome = import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, None)
    with_photos = next(c for c in read_tree(conn, outcome.template_id).comments() if c.photos)
    editing.save_comment(conn, with_photos.id, {"name": "Photo comment"})
    assert read_comment(conn, with_photos.id).photos == with_photos.photos
