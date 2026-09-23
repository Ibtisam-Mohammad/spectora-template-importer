"""Data types for the Spectora format core. Every type is immutable.

Nothing in this package touches a database, the network or the file system. It turns bytes into
these types, and those types are all the rest of the app knows about the export.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    SPECTORA_HTML = "SPECTORA_HTML"
    SPECTORA_PLAIN = "SPECTORA_PLAIN"
    UNKNOWN_SPREADSHEET = "UNKNOWN_SPREADSHEET"
    NOT_A_SPREADSHEET = "NOT_A_SPREADSHEET"


class IssueKind(StrEnum):
    MISSING_HEADER = "MISSING_HEADER"
    UNKNOWN_HEADER = "UNKNOWN_HEADER"
    DUPLICATE_HEADER = "DUPLICATE_HEADER"
    MULTIPLE_SHEETS = "MULTIPLE_SHEETS"
    ROW_SKIPPED = "ROW_SKIPPED"
    UNEXPECTED_VALUE = "UNEXPECTED_VALUE"
    INVARIANT_VIOLATED = "INVARIANT_VIOLATED"
    MERGED_SECTIONS_SUSPECTED = "MERGED_SECTIONS_SUSPECTED"
    AMBIGUOUS_ORDER = "AMBIGUOUS_ORDER"
    PHOTO_FETCH_FAILED = "PHOTO_FETCH_FAILED"
    PLAIN_TEXT_EXPORT = "PLAIN_TEXT_EXPORT"
    RENDER_NEUTRALISED = "RENDER_NEUTRALISED"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Scope(StrEnum):
    """Which node an issue is about. The importer links the issue to that node by its row."""

    FILE = "file"
    SECTION = "section"
    ITEM = "item"
    COMMENT = "comment"


@dataclass(frozen=True)
class Issue:
    kind: IssueKind
    severity: Severity
    detail: str
    scope: Scope = Scope.FILE
    row: int | None = None
    column: str | None = None


class Refusal(Exception):
    """The upload cannot be imported. Carries the verdict and what the user should know."""

    def __init__(self, verdict: Verdict, reason: str, details: tuple[str, ...] = ()) -> None:
        super().__init__(reason)
        self.verdict = verdict
        self.reason = reason
        self.details = details


# ---------------------------------------------------------------- the workbook as read


@dataclass(frozen=True)
class RawRow:
    """One spreadsheet row, cell text exactly as the XML parser produced it.

    `cells` maps a column letter to its text. A key with value None is a `<c>` element with no
    value; a missing key means the row has no `<c>` for that column at all.
    """

    number: int
    cells: dict[str, str | None]

    def text(self, column: str | None) -> str:
        if column is None:
            return ""
        return self.cells.get(column) or ""

    def is_empty(self) -> bool:
        return not any(self.cells.values())


@dataclass(frozen=True)
class Workbook:
    sheet_names: tuple[str, ...]
    header: tuple[tuple[str, str], ...]
    """(column letter, header text) for every non-empty cell of row 1, left to right."""
    rows: tuple[RawRow, ...]
    """Every row after row 1, in sheet order."""


@dataclass(frozen=True)
class ColumnMap:
    fields: dict[str, str]
    """Field name to column letter, for each known header found."""
    unknown: tuple[tuple[str, str], ...] = ()
    """(column letter, header text) for headers outside the known 42."""
    missing: tuple[str, ...] = ()
    """Known header texts that are absent."""
    duplicates: tuple[tuple[str, str], ...] = ()
    """(column letter, header text) for repeats of a known header; the first one is used."""

    def letter(self, field_name: str) -> str | None:
        return self.fields.get(field_name)


@dataclass(frozen=True)
class LedgerEntry:
    column: str
    header: str
    outcome: str
    """consumed, empty, constant or unrecognised."""
    cell_count: int
    target_field: str | None


@dataclass(frozen=True)
class Detection:
    verdict: Verdict
    reasons: tuple[str, ...] = ()


# ---------------------------------------------------------------- the parsed tree


@dataclass(frozen=True)
class ParsedPhoto:
    slot: int
    """1 to 10, the export's Default Photo number. Spectora writes the newest photo first."""
    url: str
    caption: str


@dataclass(frozen=True)
class ParsedComment:
    row: int
    name: str
    body_html: str
    comment_type: str
    category: str
    choices: tuple[str, ...]
    unit_options: tuple[str, ...]
    recommendation: str
    order_raw: str
    answer_type: str
    default_value: str
    default_value_2: str
    default_unit_type: str
    default_location: str
    estimate_min: str
    estimate_max: str
    locked: str
    simple_format: str
    disable_photos: str
    uses: str
    last_modified: str
    photos: tuple[ParsedPhoto, ...] = ()


@dataclass(frozen=True)
class ParsedItem:
    name: str
    first_row: int
    comments: tuple[ParsedComment, ...]


@dataclass(frozen=True)
class ParsedSection:
    name: str
    first_row: int
    items: tuple[ParsedItem, ...]


@dataclass(frozen=True)
class ParsedTemplate:
    name: str
    sections: tuple[ParsedSection, ...]
    empty_rows: int = 0

    def items(self) -> list[ParsedItem]:
        return [item for section in self.sections for item in section.items]

    def comments(self) -> list[ParsedComment]:
        return [comment for item in self.items() for comment in item.comments]


@dataclass(frozen=True)
class ParseResult:
    template: ParsedTemplate
    issues: tuple[Issue, ...] = field(default_factory=tuple)
