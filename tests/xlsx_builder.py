"""Build small OOXML workbooks in memory, for tests that need shapes no real export has.

A cell value of None writes no `<c>` element; VALUELESS writes a `<c>` with no value.
"""

import io
import zipfile
from xml.sax.saxutils import escape

from app.spectora.columns import KNOWN_HEADERS
from app.spectora.workbook import column_letters

VALUELESS = object()
SPECTORA_HEADERS = list(KNOWN_HEADERS)

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
</Types>"""
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)


def _cell(column: str, row: int, value, style: str) -> str:
    ref = f'r="{column}{row}"'
    if value is VALUELESS:
        return f"<c {ref}/>"
    text = escape(str(value))
    if style == "inline":
        return f'<c {ref} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
    return f'<c {ref} t="str"><v>{text}</v></c>'


def _sheet_xml(rows: list[list], style: str, shared: list[str]) -> str:
    lines = []
    for row_index, values in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(values):
            if value is None:
                continue
            column = column_letters(column_index)
            if style == "shared" and value is not VALUELESS:
                shared.append(str(value))
                cells.append(f'<c r="{column}{row_index}" t="s"><v>{len(shared) - 1}</v></c>')
            else:
                cells.append(_cell(column, row_index, value, style))
        lines.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(lines)}</sheetData></worksheet>"
    )


def build_xlsx(
    rows: list[list],
    *,
    style: str = "str",
    extra_sheets: tuple[tuple[str, list[list]], ...] = (),
    sheet_path: str = "worksheets/sheet1.xml",
) -> bytes:
    """rows[0] is the header row. style is 'str', 'inline' or 'shared'."""
    shared: list[str] = []
    sheets = [("Sheet1", sheet_path, _sheet_xml(rows, style, shared))]
    for index, (name, extra_rows) in enumerate(extra_sheets, start=2):
        sheets.append((name, f"worksheets/sheet{index}.xml", _sheet_xml(extra_rows, style, shared)))

    workbook_sheets = "".join(
        f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _, _) in enumerate(sheets, 1)
    )
    workbook_rels = "".join(
        f'<Relationship Id="rId{i}" Type="{_REL}/worksheet" Target="{path}"/>'
        for i, (_, path, _) in enumerate(sheets, 1)
    )
    if shared:
        workbook_rels += (
            f'<Relationship Id="rId{len(sheets) + 1}" Type="{_REL}/sharedStrings" '
            'Target="sharedStrings.xml"/>'
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'xmlns:r="{_REL}"><sheets>{workbook_sheets}</sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{workbook_rels}</Relationships>",
        )
        for _, path, xml in sheets:
            archive.writestr(f"xl/{path}", xml)
        if shared:
            items = "".join(f'<si><t xml:space="preserve">{escape(s)}</t></si>' for s in shared)
            archive.writestr(
                "xl/sharedStrings.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"{items}</sst>",
            )
    return buffer.getvalue()


def spectora_row(**values: str) -> list:
    """One data row in Spectora's column order, from field names to values."""
    fields = list(KNOWN_HEADERS.values())
    return [values.get(field) for field in fields]


def zip_of(parts: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()
