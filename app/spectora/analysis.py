"""The one entry point to the format core: uploaded bytes to everything known about them."""

from dataclasses import dataclass

from app.spectora.checks import file_issues, tree_issues
from app.spectora.columns import column_ledger, map_columns
from app.spectora.detect import detect, refusal
from app.spectora.model import (
    ColumnMap,
    Detection,
    Issue,
    LedgerEntry,
    ParsedTemplate,
    Workbook,
)
from app.spectora.parse import name_from_filename, parse
from app.spectora.workbook import read_workbook

PARSER_VERSION = "1"


@dataclass(frozen=True)
class Analysis:
    workbook: Workbook
    columns: ColumnMap
    detection: Detection
    template: ParsedTemplate
    issues: tuple[Issue, ...]
    ledger: tuple[LedgerEntry, ...]


def analyse(data: bytes, filename: str) -> Analysis:
    """Read, identify and parse an upload. Raises Refusal when it cannot be imported."""
    workbook = read_workbook(data)
    columns = map_columns(workbook)
    detection = detect(workbook, columns)
    refused = refusal(detection)
    if refused is not None:
        raise refused
    parsed = parse(workbook, columns, name_from_filename(filename))
    issues = (
        *file_issues(workbook, columns, detection),
        *parsed.issues,
        *tree_issues(parsed.template, columns),
    )
    return Analysis(
        workbook=workbook,
        columns=columns,
        detection=detection,
        template=parsed.template,
        issues=tuple(issues),
        ledger=column_ledger(workbook, columns),
    )
