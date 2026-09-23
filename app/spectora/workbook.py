"""Read an uploaded OOXML workbook into a header row and raw rows.

Rules: F1 (identify by content), F2 (hostile input), F3 (sheet via relationships),
F4 (cells by reference), F5 (every string-cell form), F7 (text kept as text).
"""

import io
import posixpath
import zipfile
from collections.abc import Mapping
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as SafeXML
from defusedxml.common import DefusedXmlException

from app.spectora.model import RawRow, Refusal, Verdict, Workbook

ZIP_SIGNATURE = b"PK\x03\x04"
MAX_ENTRIES = 500
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
HEADER_ROW = 1

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_PACKAGE_RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_DOC_RELS_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def read_workbook(data: bytes) -> Workbook:
    """Bytes of an uploaded file to its first worksheet, or a Refusal if it is not a workbook."""
    archive = _open_archive(data)
    with archive:
        workbook_part = _office_document_part(archive)
        relationships = _relationships(archive, workbook_part)
        sheets = _sheets(archive, workbook_part, relationships)
        shared = _shared_strings(archive, workbook_part, relationships)
        rows = _read_rows(_read_xml(archive, sheets[0][1]), shared)

    header_row = next((row for row in rows if row.number == HEADER_ROW), None)
    return Workbook(
        sheet_names=tuple(name for name, _ in sheets),
        header=_header(header_row),
        rows=tuple(row for row in rows if row.number > HEADER_ROW),
    )


def workbook_from_rows(rows: Mapping[int, dict[str, str | None]]) -> Workbook:
    """A workbook rebuilt from rows kept as {row number: {column letter: text}}, header
    included. The inverse of storing each RawRow's cells; the sheet names are not kept."""
    header = RawRow(HEADER_ROW, dict(rows[HEADER_ROW])) if HEADER_ROW in rows else None
    data = sorted((number, cells) for number, cells in rows.items() if number > HEADER_ROW)
    return Workbook(
        sheet_names=(),
        header=_header(header),
        rows=tuple(RawRow(number, dict(cells)) for number, cells in data),
    )


def column_index(letters: str) -> int:
    """'A' -> 0, 'Z' -> 25, 'AA' -> 26."""
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def column_letters(index: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA'."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


# ---------------------------------------------------------------- the zip package


def _refuse(reason: str) -> Refusal:
    return Refusal(Verdict.NOT_A_SPREADSHEET, reason)


def _open_archive(data: bytes) -> zipfile.ZipFile:
    if not data.startswith(ZIP_SIGNATURE):
        raise _refuse("This file is not a spreadsheet. A Spectora export is an Excel workbook.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise _refuse("This file looks like a zip archive but could not be opened.") from error
    entries = archive.infolist()
    if len(entries) > MAX_ENTRIES:
        raise _refuse(f"This file has {len(entries)} parts, more than a workbook would.")
    if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
        raise _refuse("This file expands to more data than a template export could contain.")
    return archive


def _read_xml(archive: zipfile.ZipFile, part: str) -> Element:
    try:
        return SafeXML.fromstring(archive.read(part))
    except KeyError as error:
        raise _refuse(f"This file has no '{part}', so it is not an Excel workbook.") from error
    except (SafeXML.ParseError, DefusedXmlException) as error:
        raise _refuse(f"The part '{part}' of this file could not be read as XML.") from error


def _resolve(source_part: str, target: str) -> str:
    """A relationship target, resolved relative to the part that declares it."""
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def _rels_part(part: str) -> str:
    directory, name = posixpath.split(part)
    return posixpath.join(directory, "_rels", f"{name}.rels")


def _office_document_part(archive: zipfile.ZipFile) -> str:
    for rel in _read_xml(archive, "_rels/.rels").iter(f"{_PACKAGE_RELS}Relationship"):
        if rel.get("Type", "").endswith("/officeDocument"):
            return _resolve("", rel.get("Target", ""))
    raise _refuse("This file does not declare a workbook, so it is not an Excel spreadsheet.")


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """Relationship id to (type, resolved target) for one part."""
    try:
        rels = _read_xml(archive, _rels_part(part))
    except Refusal:
        return {}
    return {
        rel.get("Id", ""): (rel.get("Type", ""), _resolve(part, rel.get("Target", "")))
        for rel in rels.iter(f"{_PACKAGE_RELS}Relationship")
    }


def _sheets(
    archive: zipfile.ZipFile, workbook_part: str, relationships: dict[str, tuple[str, str]]
) -> list[tuple[str, str]]:
    """(sheet name, part path) for every worksheet, in workbook order."""
    sheets = []
    for sheet in _read_xml(archive, workbook_part).iter(f"{_MAIN}sheet"):
        rel_type, target = relationships.get(sheet.get(_DOC_RELS_ID, ""), ("", ""))
        if rel_type.endswith("/worksheet"):
            sheets.append((sheet.get("name", ""), target))
    if not sheets:
        raise _refuse("This workbook has no worksheet.")
    return sheets


def _shared_strings(
    archive: zipfile.ZipFile, workbook_part: str, relationships: dict[str, tuple[str, str]]
) -> list[str]:
    for rel_type, target in relationships.values():
        if rel_type.endswith("/sharedStrings"):
            root = _read_xml(archive, target)
            return [_string_item_text(item) for item in root.iter(f"{_MAIN}si")]
    return []


# ---------------------------------------------------------------- the worksheet


def _string_item_text(element: Element) -> str:
    """Text of a shared-string item or inline string: plain `<t>`, or rich-text runs.

    Phonetic runs (`<rPh>`) are annotations, not text, and are skipped.
    """
    parts = []
    for child in element:
        if child.tag == f"{_MAIN}t":
            parts.append(child.text or "")
        elif child.tag == f"{_MAIN}r":
            parts.extend(t.text or "" for t in child.iter(f"{_MAIN}t"))
    return "".join(parts)


def _cell_text(cell: Element, shared: list[str]) -> str | None:
    """A cell's text, never cast. None when the `<c>` element carries no value."""
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(f"{_MAIN}is")
        return None if inline is None else _string_item_text(inline)
    value = cell.find(f"{_MAIN}v")
    if value is None:
        return None
    text = value.text or ""
    if cell_type == "s" and text.isdigit() and int(text) < len(shared):
        return shared[int(text)]
    return text


def _split_reference(reference: str) -> tuple[str, int | None]:
    letters = "".join(char for char in reference if char.isalpha()).upper()
    digits = "".join(char for char in reference if char.isdigit())
    return letters, int(digits) if digits else None


def _read_rows(sheet: Element, shared: list[str]) -> list[RawRow]:
    rows = []
    previous_number = 0
    for row in sheet.iter(f"{_MAIN}row"):
        number = int(row.get("r")) if row.get("r", "").isdigit() else previous_number + 1
        previous_number = number
        cells: dict[str, str | None] = {}
        next_column = 0
        for cell in row.iter(f"{_MAIN}c"):
            letters, _ = _split_reference(cell.get("r", ""))
            column = letters or column_letters(next_column)
            next_column = column_index(column) + 1
            cells[column] = _cell_text(cell, shared)
        rows.append(RawRow(number=number, cells=cells))
    return rows


def _header(row: RawRow | None) -> tuple[tuple[str, str], ...]:
    if row is None:
        return ()
    ordered = sorted(row.cells.items(), key=lambda pair: column_index(pair[0]))
    return tuple((column, text) for column, text in ordered if text)
