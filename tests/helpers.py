from functools import lru_cache
from pathlib import Path

from app.spectora.analysis import Analysis, analyse
from app.spectora.columns import map_columns
from app.spectora.model import IssueKind, ParsedComment, ParsedSection
from app.spectora.parse import parse
from app.spectora.workbook import read_workbook
from tests.xlsx_builder import SPECTORA_HEADERS, build_xlsx, spectora_row


@lru_cache
def analysed(path: Path) -> Analysis:
    return analyse(path.read_bytes(), path.name)


def parse_rows(*rows: dict[str, str]):
    """Parse synthetic rows, each a mapping of field name to value, under Spectora's headers."""
    workbook = read_workbook(build_xlsx([SPECTORA_HEADERS, *(spectora_row(**r) for r in rows)]))
    return parse(workbook, map_columns(workbook), "synthetic")


def analyse_rows(*rows: dict[str, str]) -> Analysis:
    data = build_xlsx([SPECTORA_HEADERS, *(spectora_row(**r) for r in rows)])
    return analyse(data, "synthetic.xls")


def comment_named(analysis: Analysis, name: str) -> ParsedComment:
    matches = [c for c in analysis.template.comments() if c.name == name]
    assert matches, f"no comment named {name!r}"
    return matches[0]


def section_named(analysis: Analysis, name: str) -> ParsedSection:
    matches = [s for s in analysis.template.sections if s.name == name]
    assert matches, f"no section named {name!r}"
    return matches[0]


def issues_of(analysis, kind: IssueKind):
    return [issue for issue in analysis.issues if issue.kind is kind]
