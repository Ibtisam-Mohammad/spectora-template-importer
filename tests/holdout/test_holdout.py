"""The held-out templates, run once after the parser was finished (rule Z2).

Nothing here names a section, item, comment or value. Every assertion is a property any
Spectora export must have, so a failure points at a general rule, never at a template.
Run with `pytest --holdout`; results are recorded in fixtures/holdout/README.md.
"""

import os

import pytest

from app.db.imports import source_rows
from app.db.migrations import apply_migrations
from app.db.pool import connect
from app.render import render_comment_html
from app.services.editing import original_comment
from app.services.importer import import_file
from app.spectora.analysis import analyse
from app.spectora.columns import map_columns
from app.spectora.model import IssueKind, Verdict
from app.spectora.parse import parse
from app.spectora.workbook import HEADER_ROW, workbook_from_rows
from tests.paths import HOLDOUT

pytestmark = pytest.mark.holdout

FILES = sorted(HOLDOUT.glob("*.xls"))


@pytest.fixture(scope="module", params=FILES, ids=lambda p: p.name)
def holdout(request):
    return request.param, analyse(request.param.read_bytes(), request.param.name)


@pytest.mark.rule("Z2")
def test_each_file_is_a_spectora_html_export(holdout):
    _, analysis = holdout
    assert analysis.detection.verdict is Verdict.SPECTORA_HTML
    assert not analysis.columns.missing
    assert not analysis.columns.unknown


@pytest.mark.rule("Z2")
def test_every_row_is_a_comment_an_empty_row_or_a_reported_skip(holdout):
    _, analysis = holdout
    skipped = sum(1 for issue in analysis.issues if issue.kind is IssueKind.ROW_SKIPPED)
    template = analysis.template
    assert len(template.comments()) + template.empty_rows + skipped == len(analysis.workbook.rows)


@pytest.mark.rule("Z2")
def test_the_stored_rows_alone_reproduce_the_template(holdout):
    _, analysis = holdout
    rows = source_rows(analysis)
    workbook = workbook_from_rows(rows)
    assert parse(workbook, map_columns(workbook), analysis.template.name).template == (
        analysis.template
    )
    for comment in analysis.template.comments():
        assert original_comment(rows[HEADER_ROW], comment.row, rows[comment.row]) == comment


@pytest.mark.rule("Z2")
def test_every_comment_renders(holdout):
    _, analysis = holdout
    for comment in analysis.template.comments():
        render_comment_html(comment.body_html)


@pytest.mark.rule("Z2")
def test_each_file_imports_and_verifies(holdout):
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("set TEST_DATABASE_URL to import the held-out templates")
    path, analysis = holdout
    with connect(url) as conn:
        apply_migrations(conn)
        outcome = import_file(conn, path.read_bytes(), path.name, None)
        assert len(outcome.analysis.template.comments()) == len(analysis.template.comments())
        conn.execute("delete from template where id = %s", [outcome.template_id])
        conn.execute("delete from import_run where id = %s", [outcome.run_id])
