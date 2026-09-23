import pytest

from app.db.imports import source_rows
from app.db.runs import StoredIssue, StoredLedgerEntry
from app.services.reporting import (
    MISSING_FROM_EXPORT,
    NOT_SUPPORTED_HERE,
    coverage,
    group_issues,
    markup_summary,
)
from app.spectora.workbook import workbook_from_rows
from tests.helpers import analysed
from tests.paths import ANALYSED, KITCHEN_SINK, PRIMARY


@pytest.mark.rule("F7")
@pytest.mark.parametrize("path", ANALYSED, ids=lambda p: p.name)
def test_the_stored_rows_rebuild_the_sheet_exactly(path):
    workbook = analysed(path).workbook
    rebuilt = workbook_from_rows(source_rows(analysed(path)))
    assert rebuilt.header == workbook.header
    assert rebuilt.rows == workbook.rows


@pytest.mark.rule("H6")
def test_the_markup_inventory_counts_what_the_editor_wrote():
    markup = markup_summary([KITCHEN_SINK.read_text("utf-8")])
    groups = {line.group: dict(line.entries) for line in markup.inventory}
    assert {"<table>", "<iframe>", "<a>", "<span>"} <= set(groups["Tags"])
    assert groups["Embedded frames"] == {"player.vimeo.com": 1}
    assert markup.comments_with_markup == 1
    assert markup.not_displayed == ()
    assert markup.editor_state_removed > 0


@pytest.mark.rule("H6")
def test_markup_that_will_not_display_is_listed():
    markup = markup_summary(
        ["<p>plain</p>", '<p onclick="x()">a</p><script>alert(1)</script>', "no markup"]
    )
    not_displayed = dict(markup.not_displayed)
    assert not_displayed["tag <script>"] == 1
    assert not_displayed["attribute onclick on <p>"] == 1
    assert markup.comments_with_markup == 2


@pytest.mark.rule("H6")
def test_the_stock_template_holds_back_only_one_css_property():
    bodies = [comment.body_html for comment in analysed(PRIMARY).template.comments()]
    assert markup_summary(bodies).not_displayed == (("style position", 1),)


@pytest.mark.rule("R4")
def test_the_three_coverage_numbers():
    ledger = [
        StoredLedgerEntry("A", "Section Name", "consumed", 10, "section_name"),
        StoredLedgerEntry("B", "Uses", "constant", 5, "uses"),
        StoredLedgerEntry("C", "Notes", "unrecognised", 5, None),
        StoredLedgerEntry("D", "Locked", "empty", 0, "locked"),
    ]
    captured, modelled, varying = coverage(ledger, analysed(PRIMARY).workbook)
    assert (modelled.part, modelled.whole, modelled.percent) == (15, 20, "75.0%")
    assert (varying.part, varying.whole, varying.percent) == (10, 15, "66.7%")
    assert captured.whole == 20


@pytest.mark.rule("R4")
def test_every_filled_cell_of_the_stock_template_is_captured_and_modelled():
    analysis = analysed(PRIMARY)
    ledger = [
        StoredLedgerEntry(e.column, e.header, e.outcome, e.cell_count, e.target_field)
        for e in analysis.ledger
    ]
    figures = coverage(ledger, analysis.workbook)
    assert [figure.percent for figure in figures] == ["100%", "100%", "100%"]


@pytest.mark.rule("R5")
def test_missing_from_the_export_and_not_supported_are_separate_lists():
    assert MISSING_FROM_EXPORT
    assert NOT_SUPPORTED_HERE
    assert not set(MISSING_FROM_EXPORT) & set(NOT_SUPPORTED_HERE)


def _issue(kind: str, severity: str) -> StoredIssue:
    return StoredIssue(kind, severity, "file", None, None, kind, None, None, None)


def test_issue_groups_put_warnings_before_information():
    groups = group_issues(
        [
            _issue("AMBIGUOUS_ORDER", "info"),
            _issue("MERGED_SECTIONS_SUSPECTED", "warning"),
            _issue("AMBIGUOUS_ORDER", "info"),
            _issue("SOMETHING_NEW", "warning"),
        ]
    )
    assert [(g.kind, len(g.issues)) for g in groups] == [
        ("MERGED_SECTIONS_SUSPECTED", 1),
        ("SOMETHING_NEW", 1),
        ("AMBIGUOUS_ORDER", 2),
    ]
    assert groups[1].label == "SOMETHING_NEW"
