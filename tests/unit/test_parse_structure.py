import inspect

import pytest

from app.spectora import parse as parse_module
from app.spectora.model import IssueKind, Scope
from app.spectora.parse import name_from_filename
from tests.helpers import analyse_rows, analysed, issues_of, parse_rows, section_named
from tests.paths import PRIMARY, PROBE_DUPLICATE, PROBE_HTML, PROBE_PLAIN


def row(section, item, name="c", **values):
    return {"section_name": section, "item_name": item, "comment_name": name, **values}


# ---------------------------------------------------------------- S1 a row is a comment


@pytest.mark.rule("S1")
@pytest.mark.parametrize(
    ("path", "comments"), [(PRIMARY, 392), (PROBE_HTML, 403), (PROBE_DUPLICATE, 423)]
)
def test_every_data_row_becomes_one_comment(path, comments):
    analysis = analysed(path)
    assert len(analysis.workbook.rows) == comments
    assert len(analysis.template.comments()) == comments


@pytest.mark.rule("S1")
def test_the_primary_fixture_matches_the_file():
    template = analysed(PRIMARY).template
    types = [c.comment_type for c in template.comments()]
    assert (len(template.sections), len(template.items()), len(types)) == (13, 69, 392)
    assert (types.count("defect"), types.count("info"), types.count("limit")) == (302, 78, 12)


# ---------------------------------------------------------------- S2 S3 identity is the block


@pytest.mark.rule("S2")
def test_a_section_name_that_returns_later_starts_a_new_section():
    template = parse_rows(row("A", "i"), row("B", "i"), row("A", "i")).template
    assert [s.name for s in template.sections] == ["A", "B", "A"]


@pytest.mark.rule("S2", "S3")
def test_adjacent_same_named_sections_arrive_as_one_block_with_repeated_items():
    zz_dup = section_named(analysed(PROBE_DUPLICATE), "ZZ Dup")
    assert [item.name for item in zz_dup.items] == ["General", "Same", "General", "Same"]
    assert [len(item.comments) for item in zz_dup.items] == [6, 4, 6, 4]


@pytest.mark.rule("S3")
def test_an_item_name_under_several_sections_is_several_items():
    template = analysed(PRIMARY).template
    general = [s.name for s in template.sections for i in s.items if i.name == "General"]
    assert len(general) == 8


@pytest.mark.rule("S3")
def test_an_item_name_that_returns_within_a_section_is_a_new_item():
    template = parse_rows(row("S", "a"), row("S", "b"), row("S", "a")).template
    assert [i.name for i in template.sections[0].items] == ["a", "b", "a"]


@pytest.mark.rule("S2", "S3")
def test_blocks_compare_the_exported_text_exactly():
    template = parse_rows(row("S", "Item"), row("S", "Item "), row("S ", "Item ")).template
    assert [s.name for s in template.sections] == ["S", "S "]
    assert [i.name for i in template.sections[0].items] == ["Item", "Item "]


# ---------------------------------------------------------------- S4 surrogate identity


@pytest.mark.rule("S4")
def test_same_named_comments_in_one_item_are_all_kept():
    fireplace = section_named(analysed(PRIMARY), "Fireplace")
    damper = next(i for i in fireplace.items if i.name == "Damper Doors")
    assert [c.name for c in damper.comments].count("Damper Inoperable") == 2


@pytest.mark.rule("S4")
def test_identical_rows_are_two_comments():
    template = parse_rows(row("S", "I", "same"), row("S", "I", "same")).template
    assert [c.row for c in template.comments()] == [2, 3]


# ---------------------------------------------------------------- S5 template name


@pytest.mark.rule("S5")
@pytest.mark.parametrize(
    ("filename", "name"),
    [
        ("InterNACHI Residential -2026-09-22.xls", "InterNACHI Residential -2026-09-22"),
        ("C:\\Users\\me\\Downloads\\Radon.xlsx", "Radon"),
        ("folder/probe-html.xls", "probe-html"),
        ("", "Imported template"),
    ],
)
def test_template_name_is_the_file_name_without_extension(filename, name):
    assert name_from_filename(filename) == name


# ---------------------------------------------------------------- S6 merged sections


@pytest.mark.rule("S6")
def test_merged_same_named_sections_are_reported_not_split():
    analysis = analysed(PROBE_DUPLICATE)
    merged = issues_of(analysis, IssueKind.MERGED_SECTIONS_SUSPECTED)
    assert len(merged) == 1
    assert "'ZZ Dup'" in merged[0].detail
    assert "'General' and 'Same'" in merged[0].detail
    assert merged[0].scope is Scope.SECTION
    assert [s.name for s in analysis.template.sections].count("ZZ Dup") == 1


@pytest.mark.rule("S6")
def test_templates_without_repeats_raise_no_merge_warning():
    assert not issues_of(analysed(PROBE_HTML), IssueKind.MERGED_SECTIONS_SUSPECTED)


# ---------------------------------------------------------------- F8 nothing dropped silently


@pytest.mark.rule("F8")
def test_rows_without_section_or_item_are_reported_and_empty_rows_counted():
    analysis = analyse_rows(
        row("S", "I", "kept"),
        row("", "I", "no section"),
        row("S", " ", "no item"),
        {},
        row("S", "I", "kept too"),
    )
    skipped = issues_of(analysis, IssueKind.ROW_SKIPPED)
    assert [(issue.row, issue.column) for issue in skipped] == [(3, "A"), (4, "B")]
    assert analysis.template.empty_rows == 1
    assert [c.name for c in analysis.template.comments()] == ["kept", "kept too"]
    placed = len(analysis.template.comments()) + len(skipped) + analysis.template.empty_rows
    assert placed == len(analysis.workbook.rows)


@pytest.mark.rule("F8")
def test_real_exports_skip_nothing():
    for path in (PRIMARY, PROBE_HTML, PROBE_DUPLICATE):
        assert not issues_of(analysed(path), IssueKind.ROW_SKIPPED)


# ---------------------------------------------------------------- O1 to O4 ordering


@pytest.mark.rule("O1")
def test_sections_and_items_keep_block_order():
    template = analysed(PROBE_HTML).template
    assert [s.name for s in template.sections][:3] == ["Inspection Details", "Exterior", "Roof"]
    exterior = section_named(analysed(PROBE_HTML), "Exterior")
    assert [i.name for i in exterior.items][-2:] == [
        "Walkways, Patios & Driveways",
        "Vegetation, Grading, Drainage & Retaining Walls",
    ]


@pytest.mark.rule("O2")
def test_comments_group_by_type_then_sort_by_order_within_the_group():
    probe = section_named(analysed(PROBE_HTML), "ZZ Probe & Test <x></x>").items[0]
    assert [(c.comment_type, c.order_raw) for c in probe.comments] == [
        ("info", "0"), ("info", "1"), ("info", "2"), ("info", "3"), ("info", "4"),
        ("info", "5"), ("info", "6"), ("limit", "0"),
        ("defect", "0"), ("defect", "1"), ("defect", "2"),
    ]  # fmt: skip


@pytest.mark.rule("O2")
def test_ties_and_non_numeric_order_keep_file_order_and_unknown_types_come_last():
    template = parse_rows(
        row("S", "I", "d1", comment_type="defect", order="0"),
        row("S", "I", "x1", comment_type="observation", order="0"),
        row("S", "I", "i-b", comment_type="info", order="1"),
        row("S", "I", "i-tie", comment_type="info", order="1"),
        row("S", "I", "i-none", comment_type="info", order=""),
        row("S", "I", "i-a", comment_type="info", order="0"),
        row("S", "I", "l1", comment_type="limit", order="x"),
    ).template
    names = [c.name for c in template.comments()]
    assert names == ["i-a", "i-b", "i-tie", "i-none", "l1", "d1", "x1"]


@pytest.mark.rule("O3")
def test_the_raw_order_value_is_kept():
    template = parse_rows(row("S", "I", order=" 07 ")).template
    assert template.comments()[0].order_raw == " 07 "


@pytest.mark.rule("O4")
def test_duplicate_order_values_are_reported_at_info_level():
    analysis = analysed(PRIMARY)
    ambiguous = issues_of(analysis, IssueKind.AMBIGUOUS_ORDER)
    assert len(ambiguous) == 1
    assert "Heating / General" in ambiguous[0].detail
    assert ambiguous[0].severity.value == "info"


# ---------------------------------------------------------------- D2 the verdict never parses


@pytest.mark.rule("D2")
def test_parse_never_receives_the_verdict():
    assert list(inspect.signature(parse_module.parse).parameters) == [
        "workbook", "columns", "template_name",
    ]  # fmt: skip
    assert "Verdict" not in inspect.getsource(parse_module)


@pytest.mark.rule("D2")
def test_plain_and_html_exports_of_one_template_parse_to_the_same_shape():
    html, plain = analysed(PROBE_HTML).template, analysed(PROBE_PLAIN).template
    assert [len(s.items) for s in html.sections] == [len(s.items) for s in plain.sections]
    assert [c.row for c in html.comments()] == [c.row for c in plain.comments()]


# ---------------------------------------------------------------- R6 issues locate themselves


@pytest.mark.rule("R6")
def test_row_level_issues_name_their_row_and_column():
    analysis = analyse_rows(
        row("S", "I", "bad type", comment_type="observation"),
        row("", "I", "skipped"),
        row("S", "I", "category on info", comment_type="info", category="1"),
    )
    located = [i for i in analysis.issues if i.scope is not Scope.FILE or i.row]
    assert located
    assert all(issue.row and issue.column for issue in located)
