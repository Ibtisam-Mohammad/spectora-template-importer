"""The export's column contract: the 42 known headers and how each column's text is read.

Rules: F6 (exact header mapping), T1 (strict name decoding), T3 (list splitting),
V2 and V3 (display labels), V8 (every column has a field), R4 (column ledger).
"""

import re
from collections import Counter
from html.entities import html5

from app.spectora.model import ColumnMap, LedgerEntry, Workbook
from app.spectora.workbook import column_index

# Header text exactly as Spectora writes it, to the field it fills. Order is Spectora's column
# order, A to AP. Matching is exact: `Default Value` is a prefix of `Default Value 2`.
_NAMED_HEADERS: tuple[tuple[str, str], ...] = (
    ("Section Name", "section_name"),
    ("Item Name", "item_name"),
    ("Comment Name", "comment_name"),
    ("Comment Text", "comment_text"),
    ("Comment Type (info, limit, defect)", "comment_type"),
    ("Category (-1: Low, 0: Med, 1: High)", "category"),
    ("Multiple Choice Options (comma-separated)", "choices"),
    ("Unit Type Options (numeric answers only, comma-separated)", "unit_options"),
    ("Recommendation (from list)", "recommendation"),
    ("Order (w/i item)", "order"),
    ("Answer Type (boolean, checkbox, date, number, range, text)", "answer_type"),
    ("Default Value", "default_value"),
    ('Default Value 2 (for "range" types)', "default_value_2"),
    ('Default Unit Type (for "number" and "range" types)', "default_unit_type"),
    ("Default Location", "default_location"),
    ("Default Estimate Min", "estimate_min"),
    ("Default Estimate Max", "estimate_max"),
    ("Locked", "locked"),
    ("Simple Format", "simple_format"),
    ("Disable Photos", "disable_photos"),
    ("Uses", "uses"),
)
PHOTO_SLOTS = range(1, 11)
_PHOTO_HEADERS = tuple(
    pair
    for slot in PHOTO_SLOTS
    for pair in (
        (f"Default Photo {slot}", f"photo_{slot}"),
        (f"Default Photo {slot} Caption", f"photo_{slot}_caption"),
    )
)
KNOWN_HEADERS: dict[str, str] = dict(
    (*_NAMED_HEADERS, *_PHOTO_HEADERS, ("Last Modified", "last_modified"))
)
FIELD_HEADERS: dict[str, str] = {field: header for header, field in KNOWN_HEADERS.items()}

REQUIRED_FIELDS = ("section_name", "item_name")
NAME_FIELDS = ("section_name", "item_name", "comment_name")

COMMENT_TYPES = ("info", "limit", "defect")
COMMENT_TYPE_LABELS = {"info": "Informational", "limit": "Limitations", "defect": "Deficiencies"}

# Spectora's editor labels, keyed by the value the export writes. Two are inverted: the UI's
# "Checkbox" is the export's `boolean`, and its "Multiple Choices" is the export's `checkbox`.
ANSWER_TYPE_LABELS = {
    "boolean": "Checkbox (i.e. Yes/No, Present/Not Present)",
    "checkbox": "Multiple Choices (i.e. checkboxes)",
    "date": "Date",
    "number": "Number",
    "range": "Numeric Range",
    "signature": "Signature",
    "text": "Text",
}
CATEGORY_LABELS = {"-1": "Low", "0": "Med", "1": "High"}


def map_columns(workbook: Workbook) -> ColumnMap:
    """Match header text exactly against the known headers."""
    fields: dict[str, str] = {}
    unknown, duplicates = [], []
    for column, header in workbook.header:
        field = KNOWN_HEADERS.get(header)
        if field is None:
            unknown.append((column, header))
        elif field in fields:
            duplicates.append((column, header))
        else:
            fields[field] = column
    missing = tuple(header for header, field in KNOWN_HEADERS.items() if field not in fields)
    return ColumnMap(fields, tuple(unknown), missing, tuple(duplicates))


# ---------------------------------------------------------------- reading cell text

# The entity grammar, not a rule about content: a name or a number, closed by a semicolon.
_ENTITY = re.compile(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")


def _decode_entity(match: re.Match[str]) -> str:
    body = match.group(1)
    if body.startswith("#"):
        code = int(body[2:], 16) if body[1:2] in "xX" else int(body[1:])
        is_valid = 0 < code <= 0x10FFFF and not 0xD800 <= code <= 0xDFFF
        return chr(code) if is_valid else match.group(0)
    return html5.get(f"{body};", match.group(0))


def decode_name(text: str) -> str:
    """Decode a name's entities once. Only semicolon-terminated entities count, so text such
    as `Heat &not working`, which a lenient decoder turns into `Heat ¬ working`, survives."""
    return _ENTITY.sub(_decode_entity, text)


def has_entity(text: str) -> bool:
    return _ENTITY.search(text) is not None


def has_bare_ampersand(text: str) -> bool:
    """True when some `&` does not start a semicolon-terminated entity."""
    return text.count("&") > len(_ENTITY.findall(text))


def split_list(text: str) -> tuple[str, ...]:
    """A comma-separated list to its items, each trimmed. No choice can contain a comma,
    because Spectora splits on every comma as it is typed."""
    return tuple(item.strip() for item in text.split(",") if item.strip())


# ---------------------------------------------------------------- the column ledger


def column_ledger(workbook: Workbook, columns: ColumnMap) -> tuple[LedgerEntry, ...]:
    """Where every column's cells go: consumed, empty, constant or unrecognised."""
    headers = dict(workbook.header)
    fields_by_column = {column: field for field, column in columns.fields.items()}
    seen = set(headers) | {column for row in workbook.rows for column in row.cells}
    entries = []
    for column in sorted(seen, key=column_index):
        values = [row.cells.get(column) or "" for row in workbook.rows]
        filled = [value for value in values if value]
        field = fields_by_column.get(column)
        if field is None:
            outcome = "unrecognised"
        elif not filled:
            outcome = "empty"
        elif len(filled) == len(values) and len(Counter(filled)) == 1:
            outcome = "constant"
        else:
            outcome = "consumed"
        entries.append(LedgerEntry(column, headers.get(column, ""), outcome, len(filled), field))
    return tuple(entries)
