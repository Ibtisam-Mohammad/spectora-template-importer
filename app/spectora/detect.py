"""Decide what kind of file was uploaded.

Rule D1: every upload gets exactly one verdict. Rule D2: the verdict only decides whether to
import and what to warn about; parse.py never reads it.

The Plain Text test uses how each export variant encodes text, which is a property of the
format rather than of any template: the HTML Text export keeps markup in Comment Text and
writes every `&` in names as an entity, while the Plain Text export strips all markup and
writes `&` bare.
"""

import re

from app.spectora.columns import (
    FIELD_HEADERS,
    NAME_FIELDS,
    REQUIRED_FIELDS,
    has_bare_ampersand,
    has_entity,
)
from app.spectora.model import ColumnMap, Detection, Refusal, Verdict, Workbook

_MARKUP = re.compile(r"<[A-Za-z/!]")


def detect(workbook: Workbook, columns: ColumnMap) -> Detection:
    missing = [FIELD_HEADERS[field] for field in REQUIRED_FIELDS if columns.letter(field) is None]
    if missing:
        return Detection(Verdict.UNKNOWN_SPREADSHEET, _header_differences(columns, missing))
    if _looks_like_plain_text_export(workbook, columns):
        return Detection(
            Verdict.SPECTORA_PLAIN,
            (
                "No Comment Text in this file contains any HTML, and ampersands are not encoded, "
                "which is how Spectora's Plain Text export writes a template.",
                "Spectora removes every link address, table and piece of formatting from that "
                "export before you download it. To keep them, export again with Export HTML Text.",
            ),
        )
    return Detection(Verdict.SPECTORA_HTML)


def refusal(detection: Detection) -> Refusal | None:
    """The Refusal for a verdict that cannot be imported, or None if it can."""
    if detection.verdict is Verdict.UNKNOWN_SPREADSHEET:
        return Refusal(
            detection.verdict,
            "This spreadsheet is not a Spectora template export.",
            detection.reasons,
        )
    return None


def _header_differences(columns: ColumnMap, missing_required: list[str]) -> tuple[str, ...]:
    reasons = [
        f"Missing the column '{header}', which every Spectora export has."
        for header in missing_required
    ]
    if columns.unknown:
        found = ", ".join(f"'{header}'" for _, header in columns.unknown[:12])
        reasons.append(f"Its columns include {found}, which a Spectora export does not have.")
    return tuple(reasons)


def _looks_like_plain_text_export(workbook: Workbook, columns: ColumnMap) -> bool:
    name_columns = [columns.letter(field) for field in NAME_FIELDS]
    body_column = columns.letter("comment_text")
    names = [row.text(column) for row in workbook.rows for column in name_columns]
    bodies = [text for text in (row.text(body_column) for row in workbook.rows) if text]

    html_signal = any(_MARKUP.search(body) for body in bodies) or any(
        has_entity(text) for text in (*names, *bodies)
    )
    if html_signal:
        return False
    plain_signal = any(has_bare_ampersand(name) for name in names)
    return plain_signal or bool(bodies)
