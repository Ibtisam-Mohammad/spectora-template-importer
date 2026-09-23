import re
from html import escape
from html import unescape as html_unescape

import pytest
from fastapi.testclient import TestClient

from app import config
from app.db.pool import close_pool
from app.db.templates import read_tree
from app.main import app
from tests.paths import PRIMARY, PROBE_DUPLICATE, PROBE_PLAIN, RICH_COMMENT


@pytest.fixture
def client(conn, database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    config.get_settings.cache_clear()
    yield TestClient(app)
    close_pool()
    config.get_settings.cache_clear()


def upload(client, path, filename=None):
    return client.post(
        "/import",
        files={"file": (filename or path.name, path.read_bytes(), "application/vnd.ms-excel")},
        follow_redirects=False,
    )


def imported(client, conn, path):
    response = upload(client, path)
    assert response.status_code == 303
    run_id = response.headers["location"].removeprefix("/runs/")
    [template_id] = conn.execute(
        "select template_id from import_run where id = %s", [run_id]
    ).fetchone()
    return read_tree(conn, template_id)


def current(page: str) -> list[str]:
    """Names of the selected section and item, in pane order."""
    found = re.findall(r'aria-current="page">\s*<span class="node-name">([^<]*)</span>', page)
    return [html_unescape(name) for name in found]


def test_an_upload_opens_the_template_on_its_first_section_and_item(client, conn):
    tree = imported(client, conn, PRIMARY)
    page = client.get(f"/t/{tree.id}").text
    first_section = tree.sections[0]
    assert current(page) == [first_section.name, first_section.items[0].name]
    for section in tree.sections:
        assert f">{escape(section.name)}</span>" in page
    assert page.count('class="comment"') == len(first_section.items[0].comments)


def test_the_library_lists_the_import(client, conn):
    tree = imported(client, conn, PRIMARY)
    page = client.get("/").text
    assert f'href="/t/{tree.id}"' in page
    assert ">392<" in page


def test_choosing_a_section_and_an_item_shows_their_panes(client, conn):
    tree = imported(client, conn, PRIMARY)
    section = tree.sections[4]
    item = section.items[-1]
    page = client.get(f"/t/{tree.id}?section={section.id}&item={item.id}").text
    assert current(page) == [section.name, item.name]
    assert page.count('class="comment"') == len(item.comments)
    for comment in item.comments:
        assert f"comment-{comment.id}" in page


def test_an_item_from_another_section_falls_back_to_the_first_item(client, conn):
    tree = imported(client, conn, PRIMARY)
    section, elsewhere = tree.sections[1], tree.sections[2].items[0]
    page = client.get(f"/t/{tree.id}?section={section.id}&item={elsewhere.id}").text
    assert current(page) == [section.name, section.items[0].name]


def test_comment_bodies_render_sanitised_with_their_formatting(client, conn):
    tree = imported(client, conn, RICH_COMMENT)
    rich = next(c for c in tree.comments() if "<table" in c.body_html)
    section, item = next((s, i) for s in tree.sections for i in s.items if rich in i.comments)
    page = client.get(f"/t/{tree.id}?section={section.id}&item={item.id}").text
    assert 'class="comment-body" hx-disable' in page
    assert "player.vimeo.com" in page
    assert "fr-dashed-borders" in page or "<table" in page
    assert "contenteditable" not in page


def test_import_notes_are_shown_on_the_nodes_they_concern(client, conn):
    tree = imported(client, conn, PROBE_DUPLICATE)
    merged = next(s for s in tree.sections if s.name == "ZZ Dup")
    page = client.get(f"/t/{tree.id}?section={merged.id}").text
    section_link = page.split(f'?section={merged.id}"', 1)[1].split("</a>", 1)[0]
    assert 'class="dot"' in section_link


def test_a_refused_upload_explains_why_and_stores_nothing(client, conn):
    response = client.post(
        "/import",
        files={"file": ("notes.xls", b"just some text", "application/vnd.ms-excel")},
    )
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert conn.execute("select count(*) from template").fetchone()[0] == 0


def test_an_unknown_template_is_not_found(client):
    response = client.get("/t/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "no template at this address" in response.text


# ---------------------------------------------------------------- the import report


def report_of(client, path) -> str:
    response = upload(client, path)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/runs/")
    return client.get(response.headers["location"]).text


def numbers(page: str, label: str) -> list[str]:
    row = page.split(f"<th>{label}</th>", 1)[1].split("</tr>", 1)[0]
    return re.findall(r'class="num">([^<]*)<', row)


@pytest.mark.rule("R3")
def test_an_upload_lands_on_its_report_with_the_verification_result(client):
    page = report_of(client, PRIMARY)
    assert "Verified before saving." in page
    assert "Re-derived just now." in page
    assert numbers(page, "Sections") == ["13", "13"]
    assert numbers(page, "Items") == ["69", "69"]
    assert numbers(page, "Comments") == ["392", "392"]
    assert numbers(page, "Deficiencies") == ["302", "302"]
    assert numbers(page, "Informational") == ["78", "78"]
    assert numbers(page, "Limitations") == ["12", "12"]


@pytest.mark.rule("R4")
def test_the_report_shows_coverage_and_the_column_ledger(client):
    page = report_of(client, PRIMARY)
    assert page.count('class="figure-value">100%<') == 3
    assert "Where each of the 42 columns went" in page


@pytest.mark.rule("R5")
def test_every_report_separates_missing_from_the_export_and_not_supported(client):
    page = report_of(client, PRIMARY)
    missing = page.index("Missing from Spectora's export")
    unsupported = page.index("Not supported by this importer")
    assert missing < unsupported
    assert "Sections and items that hold no comments" in page[missing:unsupported]
    assert "other inspection software" in page[unsupported:]


@pytest.mark.rule("R6")
def test_each_note_names_its_row_and_column_and_links_to_its_node(client):
    page = report_of(client, PROBE_DUPLICATE)
    assert "row 126, column J" in page
    links = re.findall(r'<a href="(/t/[^"]+)">Show</a>', page)
    assert links
    editor = client.get(html_unescape(links[0]).split("#")[0])
    assert editor.status_code == 200


@pytest.mark.rule("H6")
def test_the_report_lists_markup_that_will_not_display(client):
    page = report_of(client, PRIMARY)
    assert "Kept but not displayed:" in page
    assert "style position 1" in page


def test_the_plain_text_export_is_flagged_first(client):
    notes = report_of(client, PROBE_PLAIN).split("<h2>Import notes</h2>", 1)[1]
    assert notes.index("Plain Text export") < notes.index("Comments sharing an order number")


def test_an_unknown_report_is_not_found(client):
    response = client.get("/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
