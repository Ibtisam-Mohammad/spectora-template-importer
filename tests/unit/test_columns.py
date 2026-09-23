import ast
import inspect

import pytest

from app.spectora import columns as columns_module
from app.spectora.columns import (
    KNOWN_HEADERS,
    column_ledger,
    decode_name,
    has_bare_ampersand,
    map_columns,
    split_list,
)
from app.spectora.workbook import read_workbook
from tests.paths import PROBE_HTML
from tests.xlsx_builder import SPECTORA_HEADERS, build_xlsx


def probe_workbook():
    return read_workbook(PROBE_HTML.read_bytes())


# ---------------------------------------------------------------- F6 exact header mapping


@pytest.mark.rule("F6")
def test_real_export_maps_all_42_headers_exactly():
    columns = map_columns(probe_workbook())
    assert len(columns.fields) == 42
    assert columns.unknown == ()
    assert columns.missing == ()
    assert columns.letter("section_name") == "A"
    assert columns.letter("last_modified") == "AP"


@pytest.mark.rule("F6")
def test_default_value_and_default_value_2_are_different_columns():
    columns = map_columns(probe_workbook())
    assert columns.letter("default_value") == "L"
    assert columns.letter("default_value_2") == "M"


@pytest.mark.rule("F6")
def test_unknown_missing_and_duplicate_headers_are_reported():
    header = ["Section Name", "Item Name", "Inspector Notes", "Item Name"]
    columns = map_columns(read_workbook(build_xlsx([header])))
    assert columns.unknown == (("C", "Inspector Notes"),)
    assert columns.duplicates == (("D", "Item Name"),)
    assert "Comment Text" in columns.missing
    assert columns.letter("item_name") == "B"


@pytest.mark.rule("F6")
def test_a_near_miss_header_is_unknown_not_guessed():
    columns = map_columns(read_workbook(build_xlsx([["Section Name", "Comment Type"]])))
    assert columns.unknown == (("B", "Comment Type"),)
    assert columns.letter("comment_type") is None


# ---------------------------------------------------------------- T1 strict name decoding


@pytest.mark.rule("T1")
@pytest.mark.parametrize(
    ("exported", "expected"),
    [
        ("Siding, Flashing &amp; Trim", "Siding, Flashing & Trim"),
        ("Siding, Flashing & Trim", "Siding, Flashing & Trim"),
        ("ZZ Probe &amp; Test &lt;x&gt;&lt;/x&gt;", "ZZ Probe & Test <x></x>"),
        ("Homeowner&#39;s Responsibility", "Homeowner's Responsibility"),
        ("Homeowner&#x27;s Responsibility", "Homeowner's Responsibility"),
        ("Heat &not working", "Heat &not working"),
        ("Smith&copy Co", "Smith&copy Co"),
        ("R&D Wing", "R&D Wing"),
        ("&bogus; entity", "&bogus; entity"),
        ("&#0; nul", "&#0; nul"),
        ("&amp;amp;", "&amp;"),
    ],
)
def test_names_are_decoded_once_and_strictly(exported, expected):
    assert decode_name(exported) == expected


@pytest.mark.rule("T1")
def test_html_unescape_is_never_called():
    tree = ast.parse(inspect.getsource(columns_module))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "unescape"
    ]
    assert not calls


def test_bare_ampersand_detection():
    assert has_bare_ampersand("R&D")
    assert not has_bare_ampersand("R&amp;D")
    assert has_bare_ampersand("A &amp; B & C")


# ---------------------------------------------------------------- T3 list splitting


@pytest.mark.rule("T3")
def test_choices_split_on_every_comma_and_trim():
    assert split_list('Smith, John, 1, 000 sq ft, He said "no", Plain') == (
        "Smith", "John", "1", "000 sq ft", 'He said "no"', "Plain",
    )  # fmt: skip


@pytest.mark.rule("T3")
def test_choices_are_not_entity_decoded():
    assert split_list("Conduit, Knob & Tube") == ("Conduit", "Knob & Tube")
    assert split_list("Knob &amp; Tube") == ("Knob &amp; Tube",)


@pytest.mark.rule("T3")
def test_empty_list_items_are_dropped():
    assert split_list("") == ()
    assert split_list("a,, b ,") == ("a", "b")


# ---------------------------------------------------------------- R4 column ledger


@pytest.mark.rule("R4")
def test_ledger_covers_every_column_of_the_real_export():
    workbook = probe_workbook()
    ledger = {entry.column: entry for entry in column_ledger(workbook, map_columns(workbook))}
    assert len(ledger) == 42
    assert ledger["A"].outcome == "consumed"
    assert {ledger[c].outcome for c in ("P", "Q", "U")} == {"constant"}
    assert ledger["AB"].outcome == "empty"
    assert ledger["AB"].cell_count == 0
    assert ledger["A"].cell_count == len(workbook.rows)


@pytest.mark.rule("R4")
def test_ledger_marks_unknown_columns_unrecognised():
    workbook = read_workbook(build_xlsx([["Section Name", "Notes"], ["S1", "n"], ["S2", "m"]]))
    ledger = column_ledger(workbook, map_columns(workbook))
    assert [(e.column, e.outcome, e.target_field) for e in ledger] == [
        ("A", "consumed", "section_name"),
        ("B", "unrecognised", None),
    ]


@pytest.mark.rule("R4")
def test_a_column_identical_on_every_row_is_constant():
    workbook = read_workbook(build_xlsx([["Section Name"], ["same"], ["same"]]))
    assert column_ledger(workbook, map_columns(workbook))[0].outcome == "constant"


def test_the_contract_has_42_distinct_headers_and_fields():
    assert len(KNOWN_HEADERS) == 42
    assert len(set(KNOWN_HEADERS.values())) == 42
    assert list(KNOWN_HEADERS) == SPECTORA_HEADERS
