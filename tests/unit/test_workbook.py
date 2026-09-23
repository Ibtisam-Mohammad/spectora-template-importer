import pytest

from app.spectora import workbook as workbook_module
from app.spectora.model import Refusal, Verdict
from app.spectora.workbook import column_index, column_letters, read_workbook
from tests.paths import ANALYSED, PROBE_HTML
from tests.xlsx_builder import VALUELESS, build_xlsx, zip_of


def probe():
    return read_workbook(PROBE_HTML.read_bytes())


# ---------------------------------------------------------------- F1 identify by content


@pytest.mark.rule("F1")
@pytest.mark.parametrize("path", ANALYSED, ids=lambda p: p.name)
def test_every_real_export_opens_although_named_xls(path):
    assert path.suffix == ".xls"
    workbook = read_workbook(path.read_bytes())
    assert len(workbook.header) == 42
    assert workbook.rows


@pytest.mark.rule("F1", "D1")
@pytest.mark.parametrize(
    "data",
    [
        b"%PDF-1.7 not a workbook",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 legacy OLE2 xls",
        b"Section Name,Item Name\nA,B\n",
        b"",
    ],
    ids=["pdf", "legacy-ole2-xls", "csv", "empty"],
)
def test_non_workbooks_are_refused(data):
    with pytest.raises(Refusal) as refused:
        read_workbook(data)
    assert refused.value.verdict is Verdict.NOT_A_SPREADSHEET


@pytest.mark.rule("F1", "D1")
def test_a_zip_that_is_not_a_workbook_is_refused():
    with pytest.raises(Refusal) as refused:
        read_workbook(zip_of({"notes.txt": "hello"}))
    assert refused.value.verdict is Verdict.NOT_A_SPREADSHEET


# ---------------------------------------------------------------- F2 hostile input


@pytest.mark.rule("F2")
def test_too_many_zip_entries_are_refused(monkeypatch):
    monkeypatch.setattr(workbook_module, "MAX_ENTRIES", 3)
    with pytest.raises(Refusal, match="parts"):
        read_workbook(build_xlsx([["Section Name"]]))


@pytest.mark.rule("F2")
def test_oversized_expansion_is_refused(monkeypatch):
    monkeypatch.setattr(workbook_module, "MAX_UNCOMPRESSED_BYTES", 100)
    with pytest.raises(Refusal, match="expands"):
        read_workbook(build_xlsx([["Section Name"]]))


@pytest.mark.rule("F2")
def test_xml_entity_expansion_is_refused():
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
        "<Relationships>&lol2;</Relationships>"
    )
    with pytest.raises(Refusal) as refused:
        read_workbook(zip_of({"_rels/.rels": bomb}))
    assert refused.value.verdict is Verdict.NOT_A_SPREADSHEET


# ---------------------------------------------------------------- F3 sheet via relationships


@pytest.mark.rule("F3")
def test_the_real_export_has_one_sheet():
    assert probe().sheet_names == ("Sheet1",)


@pytest.mark.rule("F3")
def test_first_sheet_is_read_and_every_sheet_is_named():
    data = build_xlsx(
        [["Section Name"], ["first"]], extra_sheets=(("Other", [["Section Name"], ["second"]]),)
    )
    workbook = read_workbook(data)
    assert workbook.sheet_names == ("Sheet1", "Other")
    assert workbook.rows[0].cells == {"A": "first"}


@pytest.mark.rule("F3")
def test_sheet_is_found_through_relationships_not_a_fixed_path():
    data = build_xlsx([["Section Name"], ["found"]], sheet_path="sheets/data.xml")
    assert read_workbook(data).rows[0].cells == {"A": "found"}


# ---------------------------------------------------------------- F4 cells by reference


@pytest.mark.rule("F4")
def test_photo_columns_have_no_cells_at_all_and_stay_absent():
    workbook = probe()
    column_ab = column_letters(27)
    assert column_ab == "AB"
    assert all(column_ab not in row.cells for row in workbook.rows)


@pytest.mark.rule("F4")
def test_valueless_cells_are_kept_distinct_from_absent_ones():
    workbook = probe()
    valueless = [row for row in workbook.rows if row.cells.get("L", "missing") is None]
    assert valueless, "the export writes valueless <c> elements in column L"
    assert all(row.text("L") == "" for row in valueless)


@pytest.mark.rule("F4")
def test_a_gap_in_the_cells_does_not_shift_later_columns():
    data = build_xlsx([["Section Name", "Item Name", "Comment Name"], ["S", None, "C"]])
    row = read_workbook(data).rows[0]
    assert row.cells == {"A": "S", "C": "C"}


@pytest.mark.rule("F4")
def test_valueless_cell_in_a_built_workbook():
    data = build_xlsx([["Section Name", "Item Name"], ["S", VALUELESS]])
    assert read_workbook(data).rows[0].cells == {"A": "S", "B": None}


# ---------------------------------------------------------------- F5 every string-cell form


@pytest.mark.rule("F5")
@pytest.mark.parametrize("style", ["str", "inline", "shared"])
def test_every_string_cell_form_reads_the_same(style):
    rows = [["Section Name", "Item Name"], ["Roof & Attic", "  spaced  "]]
    row = read_workbook(build_xlsx(rows, style=style)).rows[0]
    assert row.cells == {"A": "Roof & Attic", "B": "  spaced  "}


@pytest.mark.rule("F5")
def test_the_real_export_uses_formula_string_cells():
    raw = PROBE_HTML.read_bytes()
    assert b"xl/sharedStrings.xml" not in raw
    assert probe().header[0] == ("A", "Section Name")


# ---------------------------------------------------------------- F7 text never cast


@pytest.mark.rule("F7")
def test_every_value_is_text_or_none():
    for row in probe().rows:
        assert all(value is None or isinstance(value, str) for value in row.cells.values())


@pytest.mark.rule("F7")
def test_numbers_and_whitespace_survive_as_written():
    rows = [["Section Name", "Item Name", "Order (w/i item)"], ["S", " I ", "007"]]
    row = read_workbook(build_xlsx(rows)).rows[0]
    assert row.cells == {"A": "S", "B": " I ", "C": "007"}


def test_column_letters_round_trip():
    for index in (0, 25, 26, 41, 701, 702):
        assert column_index(column_letters(index)) == index
    assert column_letters(41) == "AP"
