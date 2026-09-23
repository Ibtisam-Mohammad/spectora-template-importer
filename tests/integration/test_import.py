import hashlib

import pytest

from app.db import imports
from app.db.migrations import apply_migrations
from app.db.templates import list_templates, read_tree
from app.services import importer
from app.services.importer import VerificationFailed, import_file
from app.spectora.analysis import PARSER_VERSION
from app.spectora.model import IssueKind, Refusal, Scope
from tests.helpers import analysed
from tests.integration.conftest import fake_photo_copier, table_counts
from tests.paths import ANALYSED, PRIMARY, PROBE_DUPLICATE, PROBE_HTML, PROBE_PLAIN, RICH_COMMENT
from tests.xlsx_builder import build_xlsx


def run_row(conn, run_id) -> dict:
    cursor = conn.execute("select * from import_run where id = %s", [run_id])
    names = [column.name for column in cursor.description]
    return dict(zip(names, cursor.fetchone(), strict=True))


def test_migrations_apply_once(conn):
    assert apply_migrations(conn) == []


# ---------------------------------------------------------------- R2 the run record


@pytest.mark.rule("R2")
def test_the_run_records_the_file_the_verdict_and_the_counts(conn):
    data = PRIMARY.read_bytes()
    outcome = import_file(conn, data, "InterNACHI Residential -2026-09-22.xls", None)
    run = run_row(conn, outcome.run_id)
    assert run["template_id"] == outcome.template_id
    assert run["source_filename"] == "InterNACHI Residential -2026-09-22.xls"
    assert run["source_sha256"] == hashlib.sha256(data).hexdigest()
    assert run["verdict"] == "SPECTORA_HTML"
    assert run["parser_version"] == PARSER_VERSION
    assert (run["rows_total"], run["empty_rows"], run["rows_skipped"]) == (392, 0, 0)
    assert (run["sections_created"], run["items_created"], run["comments_created"]) == (13, 69, 392)
    assert (run["photos_found"], run["photos_stored"]) == (0, 0)
    assert run["verified_at"] is not None
    tree = read_tree(conn, outcome.template_id)
    assert tree.name == "InterNACHI Residential -2026-09-22"


@pytest.mark.rule("R2")
def test_the_plain_text_export_is_recorded_with_its_verdict_and_warning(conn):
    outcome = import_file(conn, PROBE_PLAIN.read_bytes(), PROBE_PLAIN.name, None)
    assert run_row(conn, outcome.run_id)["verdict"] == "SPECTORA_PLAIN"
    kinds = {row[0] for row in conn.execute("select kind from import_issue").fetchall()}
    assert IssueKind.PLAIN_TEXT_EXPORT.value in kinds


# ---------------------------------------------------------------- R1 and R3 all or nothing


@pytest.mark.rule("R3")
@pytest.mark.parametrize("path", ANALYSED, ids=lambda p: p.name)
def test_every_fixture_reads_back_as_parsed(conn, path):
    outcome = import_file(conn, path.read_bytes(), path.name, None)
    parsed, tree = analysed(path).template, read_tree(conn, outcome.template_id)
    assert [s.name for s in tree.sections] == [s.name for s in parsed.sections]
    assert [i.name for i in tree.items()] == [i.name for i in parsed.items()]
    assert [c.source_row_number for c in tree.comments()] == [c.row for c in parsed.comments()]
    assert [c.body_html for c in tree.comments()] == [c.body_html for c in parsed.comments()]
    assert importer.verification_problems(conn, _ids(outcome), _new(outcome, path)) == []


def _ids(outcome) -> imports.ImportIds:
    return imports.ImportIds(outcome.template_id, outcome.run_id)


def _new(outcome, path) -> imports.NewImport:
    return imports.NewImport(
        analysis=outcome.analysis,
        filename=path.name,
        sha256="",
        started_at=None,
        issues=outcome.issues,
        photo_paths={},
    )


TAMPERING = {
    "comment body": "update comment set body_html = body_html || ' '"
    " where id = (select id from comment order by source_row_number limit 1)",
    "section order": "update section set position = position + 1000"
    " where id = (select id from section order by position limit 1)",
    "source row": 'update source_row set raw = raw || \'{"A": "changed"}\' where row_number = 2',
    "photo": "delete from comment_photo where id = (select id from comment_photo limit 1)",
    "issue": "delete from import_issue where id = (select id from import_issue limit 1)",
}


@pytest.mark.rule("R1", "R3")
@pytest.mark.parametrize("tampering", TAMPERING, ids=str)
def test_a_storage_mismatch_rolls_everything_back(conn, monkeypatch, tampering):
    def insert_then_tamper(connection, new):
        ids = imports.insert_import(connection, new)
        connection.execute(TAMPERING[tampering])
        return ids

    monkeypatch.setattr(importer, "insert_import", insert_then_tamper)
    with pytest.raises(VerificationFailed):
        import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, None)
    assert set(table_counts(conn).values()) == {0}


@pytest.mark.rule("R1")
@pytest.mark.parametrize(
    "data", [b"not a spreadsheet", build_xlsx([["Room", "Finding"], ["Kitchen", "Leak"]])]
)
def test_a_refused_file_leaves_nothing(conn, data):
    with pytest.raises(Refusal):
        import_file(conn, data, "upload.xls", None)
    assert set(table_counts(conn).values()) == {0}


@pytest.mark.rule("R1")
def test_a_database_error_mid_import_leaves_nothing(conn, monkeypatch):
    def insert_then_fail(connection, new):
        imports.insert_import(connection, new)
        connection.execute("select 1 / 0")

    monkeypatch.setattr(importer, "insert_import", insert_then_fail)
    with pytest.raises(Exception, match="division by zero"):
        import_file(conn, PRIMARY.read_bytes(), PRIMARY.name, None)
    assert set(table_counts(conn).values()) == {0}


# ---------------------------------------------------------------- F7 the source rows


@pytest.mark.rule("F7")
def test_source_rows_keep_every_cell_as_read(conn):
    analysis = analysed(PROBE_HTML)
    outcome = import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, None)
    stored = imports.read_source_rows(conn, outcome.run_id)
    assert stored[imports.HEADER_ROW] == dict(analysis.workbook.header)
    for row in analysis.workbook.rows:
        assert stored[row.number] == row.cells
    assert len(stored) == len(analysis.workbook.rows) + 1


# ---------------------------------------------------------------- issues and ledger


@pytest.mark.rule("R4")
def test_the_column_ledger_is_stored(conn):
    outcome = import_file(conn, PRIMARY.read_bytes(), PRIMARY.name, None)
    rows = conn.execute(
        "select column_letter, outcome, cell_count from cell_ledger where import_run_id = %s",
        [outcome.run_id],
    ).fetchall()
    expected = {(e.column, e.outcome, e.cell_count) for e in analysed(PRIMARY).ledger}
    assert set(rows) == expected
    assert len(rows) == 42


@pytest.mark.rule("R6")
def test_issues_are_linked_to_the_nodes_they_are_about(conn):
    outcome = import_file(conn, PROBE_DUPLICATE.read_bytes(), PROBE_DUPLICATE.name, None)
    tree = read_tree(conn, outcome.template_id)
    parents = {
        comment.id: (item.id, section.id)
        for section in tree.sections
        for item in section.items
        for comment in item.comments
    }
    items = {item.id: section.id for section in tree.sections for item in section.items}
    names = {section.id: section.name for section in tree.sections}
    rows = conn.execute(
        "select kind, scope, section_id, item_id, comment_id from import_issue"
        " where import_run_id = %s order by position",
        [outcome.run_id],
    ).fetchall()
    assert len(rows) == len(outcome.issues)
    for _, scope, section_id, item_id, comment_id in rows:
        if scope == Scope.COMMENT:
            assert parents[comment_id] == (item_id, section_id)
        elif scope == Scope.ITEM:
            assert comment_id is None and items[item_id] == section_id
        elif scope == Scope.SECTION:
            assert comment_id is None and item_id is None and section_id in names
        else:
            assert (section_id, item_id, comment_id) == (None, None, None)
    merged = [row for row in rows if row[0] == IssueKind.MERGED_SECTIONS_SUSPECTED]
    assert merged
    assert all(names[row[2]] == "ZZ Dup" for row in merged)


def test_markup_the_renderer_drops_is_reported_on_its_comment(conn):
    outcome = import_file(conn, RICH_COMMENT.read_bytes(), RICH_COMMENT.name, None)
    neutralised = [i for i in outcome.issues if i.kind is IssueKind.RENDER_NEUTRALISED]
    assert neutralised
    assert all(issue.scope is Scope.COMMENT for issue in neutralised)
    assert all("contenteditable" not in issue.detail for issue in neutralised)


# ---------------------------------------------------------------- photos and the library


@pytest.mark.rule("PH2")
def test_copied_photos_are_stored_with_their_original_url(conn):
    outcome = import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, fake_photo_copier())
    tree = read_tree(conn, outcome.template_id)
    stored = [photo for comment in tree.comments() for photo in comment.photos]
    assert len(stored) == 4
    for photo in stored:
        assert photo.source_url.startswith("https://cdn.spectora.com/")
        assert photo.stored_path == hashlib.sha256(photo.source_url.encode()).hexdigest() + ".jpg"
    run = run_row(conn, outcome.run_id)
    assert (run["photos_found"], run["photos_stored"]) == (4, 4)
    assert not [i for i in outcome.issues if i.kind is IssueKind.PHOTO_FETCH_FAILED]


def test_the_library_lists_each_template_with_its_size(conn):
    first = import_file(conn, PRIMARY.read_bytes(), PRIMARY.name, None)
    second = import_file(conn, PROBE_HTML.read_bytes(), PROBE_HTML.name, None)
    library = {summary.id: summary for summary in list_templates(conn)}
    assert (library[first.template_id].sections, library[first.template_id].items) == (13, 69)
    assert library[first.template_id].comments == 392
    assert library[second.template_id].latest_run_id == second.run_id
    assert all(summary.origin == "import" for summary in library.values())
