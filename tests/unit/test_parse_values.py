import dataclasses

import pytest

from app.spectora.columns import ANSWER_TYPE_LABELS, CATEGORY_LABELS, KNOWN_HEADERS
from app.spectora.model import IssueKind
from tests.helpers import analyse_rows, analysed, comment_named, issues_of, parse_rows
from tests.paths import PRIMARY, PROBE_HTML, RICH_COMMENT


def row(name="c", **values):
    return {"section_name": "S", "item_name": "I", "comment_name": name, **values}


# ---------------------------------------------------------------- T2 bodies byte-for-byte


@pytest.mark.rule("T2")
def test_every_body_equals_the_cell_text_exactly():
    analysis = analysed(PROBE_HTML)
    body = analysis.columns.letter("comment_text")
    by_row = {r.number: r.text(body) for r in analysis.workbook.rows}
    assert all(c.body_html == by_row[c.row] for c in analysis.template.comments())


@pytest.mark.rule("T2")
def test_bodies_keep_line_breaks_non_breaking_spaces_and_entities():
    bodies = [c.body_html for c in analysed(PROBE_HTML).template.comments()]
    joined = "".join(bodies)
    assert (joined.count("\r"), joined.count("\n")) == (43, 306)
    assert joined.count(chr(0xA0)) == 194
    assert joined.count("&amp;") == 31


@pytest.mark.rule("T2")
def test_the_rich_editor_comment_arrives_intact():
    rich = [c for c in analysed(RICH_COMMENT).template.comments() if "<iframe" in c.body_html]
    assert [c.name for c in rich] == ["Damper Inoperable"]
    rich = rich[0]
    assert 'src="https://player.vimeo.com/video/76073568"' in rich.body_html
    assert 'class="fr-dashed-borders fr-alternate-rows"' in rich.body_html


# ---------------------------------------------------------------- T4 T5 values as exported


@pytest.mark.rule("T4")
def test_values_are_never_trimmed():
    comment = parse_rows(row(default_location=" 1st Floor ", default_value=" 42 ")).template
    parsed = comment.comments()[0]
    assert parsed.default_location == " 1st Floor "
    assert parsed.default_value == " 42 "


@pytest.mark.rule("T4", "V7")
def test_the_composed_location_keeps_its_leading_space_and_is_one_string():
    locations = [c.default_location for c in analysed(PROBE_HTML).template.comments()]
    filled = [location for location in locations if location]
    assert len(filled) == 1
    assert filled[0].startswith(" 1st Floor 2nd Floor")
    assert filled[0].endswith("Garage,")


@pytest.mark.rule("T4", "T1")
def test_names_are_decoded_but_not_trimmed():
    names = [c.name for c in analysed(PRIMARY).template.comments()]
    assert sum(1 for name in names if name != name.strip()) == 11
    assert "Siding, Flashing & Trim" in {i.name for i in analysed(PRIMARY).template.items()}


@pytest.mark.rule("T5")
def test_closing_tags_the_export_appended_to_names_are_kept():
    template = analysed(PROBE_HTML).template
    assert "ZZ Probe & Test <x></x>" in [s.name for s in template.sections]
    assert 'Item & <angle> "quote"</angle>' in [i.name for i in template.items()]
    assert 'Smith & Sons <test> "quoted"</test>' in [c.name for c in template.comments()]


# ---------------------------------------------------------------- V1 V2 V3 known and unknown


@pytest.mark.rule("V1")
def test_unknown_comment_types_are_kept_and_reported():
    analysis = analyse_rows(
        row("odd", comment_type="observation"), row("spaced", comment_type=" defect")
    )
    by_row = sorted(analysis.template.comments(), key=lambda c: c.row)
    assert [c.comment_type for c in by_row] == ["observation", " defect"]
    unexpected = issues_of(analysis, IssueKind.UNEXPECTED_VALUE)
    assert sorted((issue.row, issue.column) for issue in unexpected) == [(2, "E"), (3, "E")]


@pytest.mark.rule("V1")
def test_known_comment_types_raise_nothing():
    assert not issues_of(analysed(PROBE_HTML), IssueKind.UNEXPECTED_VALUE)


@pytest.mark.rule("V2")
def test_all_seven_answer_types_are_stored_verbatim():
    answer_types = {c.answer_type for c in analysed(PROBE_HTML).template.comments()}
    assert answer_types == {"boolean", "checkbox", "date", "number", "range", "signature", "text"}
    assert set(ANSWER_TYPE_LABELS) == answer_types


@pytest.mark.rule("V2")
def test_the_ui_labels_for_boolean_and_checkbox_are_the_inverted_pair():
    assert ANSWER_TYPE_LABELS["boolean"].startswith("Checkbox")
    assert ANSWER_TYPE_LABELS["checkbox"].startswith("Multiple Choices")
    analysis = analyse_rows(row(answer_type="slider"))
    assert analysis.template.comments()[0].answer_type == "slider"
    assert issues_of(analysis, IssueKind.UNEXPECTED_VALUE)[0].column == "K"


@pytest.mark.rule("V3")
def test_category_is_stored_verbatim_with_low_med_high_labels():
    probe = analysed(PROBE_HTML)
    assert comment_named(probe, "Probe Photos").category == "-1"
    assert comment_named(probe, "Probe Deficiency Mid").category == "0"
    assert comment_named(probe, "Probe Deficiency High").category == "1"
    assert CATEGORY_LABELS == {"-1": "Low", "0": "Med", "1": "High"}
    odd = analyse_rows(row(comment_type="defect", category="2"))
    assert odd.template.comments()[0].category == "2"
    assert issues_of(odd, IssueKind.UNEXPECTED_VALUE)[0].column == "F"


# ---------------------------------------------------------------- V4 invariants


@pytest.mark.rule("V4")
def test_real_exports_satisfy_both_invariants():
    for path in (PRIMARY, PROBE_HTML):
        assert not issues_of(analysed(path), IssueKind.INVARIANT_VIOLATED)


@pytest.mark.rule("V4")
def test_violations_are_reported_and_the_data_kept():
    analysis = analyse_rows(
        row("category on info", comment_type="info", category="1", answer_type="boolean"),
        row("defect without category", comment_type="defect", answer_type="boolean"),
        row("choices on text", comment_type="info", answer_type="text", choices="a, b"),
        row("checkbox without choices", comment_type="info", answer_type="checkbox"),
    )
    violated = issues_of(analysis, IssueKind.INVARIANT_VIOLATED)
    assert sorted((issue.row, issue.column) for issue in violated) == [
        (2, "F"), (3, "F"), (4, "G"), (5, "G"),
    ]  # fmt: skip
    by_row = {c.row: c for c in analysis.template.comments()}
    assert by_row[2].category == "1"
    assert by_row[4].choices == ("a", "b")


# ---------------------------------------------------------------- V5 V6 V9 verbatim values


@pytest.mark.rule("V5")
def test_default_values_are_never_coerced():
    probe = analysed(PROBE_HTML)
    assert comment_named(probe, 'Smith & Sons <test> "quoted"</test>').default_value == "true"
    assert comment_named(probe, "Probe Range").default_value == "10"
    assert comment_named(probe, "Probe Range").default_value_2 == "20"
    assert comment_named(probe, "Probe Text").default_value == "hello"
    booleans = {c.default_value for c in probe.template.comments() if c.answer_type == "boolean"}
    assert {"true", "f"} <= booleans


@pytest.mark.rule("V6")
def test_recommendations_are_stored_as_exported():
    probe = analysed(PROBE_HTML)
    assert comment_named(probe, "Probe Photos").recommendation == "carpetcleaner"
    assert comment_named(probe, "Probe Deficiency Mid").recommendation == "appliance"
    assert comment_named(probe, "Probe Deficiency High").recommendation == ""
    assert comment_named(probe, "Probe Limitation").recommendation == "pro"


@pytest.mark.rule("V9")
def test_last_modified_is_the_exported_text():
    probe = analysed(PROBE_HTML)
    assert comment_named(probe, "Probe Photos").last_modified == "09/22/2026 23:38:37"


# ---------------------------------------------------------------- V8 every column has a field


@pytest.mark.rule("V8")
def test_every_one_of_the_42_columns_reaches_the_parsed_tree():
    values = {field: f"<{field}>" for field in KNOWN_HEADERS.values()}
    values["choices"] = "<choices>"
    values["unit_options"] = "<unit_options>"
    template = parse_rows(values).template
    comment = template.comments()[0]
    found = {template.sections[0].name, template.items()[0].name}
    for field in dataclasses.fields(comment):
        value = getattr(comment, field.name)
        if isinstance(value, str):
            found.add(value)
        elif field.name in ("choices", "unit_options"):
            found.update(value)
    for photo in comment.photos:
        found.update((photo.url, photo.caption))
    missing = [field for field, marker in values.items() if marker not in found]
    assert not missing, f"columns that never reach the tree: {missing}"


# ---------------------------------------------------------------- PH1 photos


@pytest.mark.rule("PH1")
def test_photos_keep_export_order_newest_first():
    photos = comment_named(analysed(PROBE_HTML), "Probe Photos").photos
    assert [(p.slot, p.caption) for p in photos] == [(1, "three"), (2, "two"), (3, "one")]
    assert all(p.url.startswith("https://cdn.spectora.com/") for p in photos)


@pytest.mark.rule("PH1")
def test_only_filled_photo_slots_become_photos():
    template = parse_rows(row(photo_2="https://cdn.spectora.com/a.png", photo_4_caption="x"))
    assert [(p.slot, p.url, p.caption) for p in template.template.comments()[0].photos] == [
        (2, "https://cdn.spectora.com/a.png", ""),
        (4, "", "x"),
    ]
