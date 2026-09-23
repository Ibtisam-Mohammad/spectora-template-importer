"""The import report: what the file held, what was imported, and what was not.

Rules R3 (the verification result), R4 (the column ledger), R5 (missing from the export versus
not supported here), R6 (every issue names its row and column), H6 (the markup inventory and
what rendering will not display).

The file side of the report is re-derived from the stored source rows by the same parser, not
from the upload, which is gone. Agreement with the counts recorded at import shows the stored
rows alone reproduce the template.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.db.imports import read_source_rows
from app.db.runs import (
    StoredIssue,
    StoredLedgerEntry,
    StoredRun,
    read_issues,
    read_ledger,
    read_run,
)
from app.render import is_editor_state, markup_inventory, neutralised
from app.spectora.analysis import PARSER_VERSION
from app.spectora.columns import COMMENT_TYPE_LABELS, COMMENT_TYPES, map_columns
from app.spectora.model import IssueKind, Workbook
from app.spectora.parse import parse
from app.spectora.workbook import workbook_from_rows

VERDICT_LABELS = {
    "SPECTORA_HTML": "Spectora export, HTML Text",
    "SPECTORA_PLAIN": "Spectora export, Plain Text",
}

ISSUE_LABELS = {
    IssueKind.PLAIN_TEXT_EXPORT: "Plain Text export",
    IssueKind.MISSING_HEADER: "Missing columns",
    IssueKind.UNKNOWN_HEADER: "Columns Spectora does not write",
    IssueKind.MULTIPLE_SHEETS: "Sheets not read",
    IssueKind.ROW_SKIPPED: "Rows that could not be placed",
    IssueKind.UNEXPECTED_VALUE: "Values Spectora does not document",
    IssueKind.INVARIANT_VIOLATED: "Unusual combinations of values",
    IssueKind.MERGED_SECTIONS_SUSPECTED: "Sections that may have been merged",
    IssueKind.PHOTO_FETCH_FAILED: "Photos not copied",
    IssueKind.INLINE_IMAGE_NOT_COPIED: "Images in comment text not copied",
    IssueKind.RENDER_NEUTRALISED: "Markup kept but not displayed",
    IssueKind.AMBIGUOUS_ORDER: "Comments sharing an order number",
}

# Fixed properties of Spectora's export, the same for every import (rule R5).
MISSING_FROM_EXPORT = (
    "Sections and items that hold no comments. Spectora leaves them out of the export.",
    "Section and item settings: icons, Standards of Practice, reminders, optional and "
    "information-only flags, and the overview grid.",
    "The template's name and settings. The name here comes from the file name.",
    "An order for sections and items. Both follow the order of rows in the file. Section "
    "order matched Spectora's editor in every export examined and item order in two of "
    "three, so treat item order as best-effort and check it.",
    "The photos themselves. The export carries links to Spectora's servers, which is why "
    "the importer copies them.",
    "The account's Location Tags and Recommendation lists. Each comment's defaults arrive "
    "as text, so they are shown as text.",
    "Where one of two neighbouring sections with the same name ends. Spectora writes them "
    "as one section.",
    "Name text that looks like an HTML tag, such as <x>. Spectora adds a closing tag, and "
    "the name is kept as exported.",
)

# Fixed limits of this importer, the same for every import (rule R5).
NOT_SUPPORTED_HERE = (
    "Exports from other inspection software, such as HomeGauge, Palm-Tech or Home "
    "Inspector Pro. They are refused with the reason, and nothing is stored.",
    "Restoring what Spectora's Plain Text export removed. It is imported with a warning; "
    "export HTML Text instead.",
    "Sheets after the first one in a workbook.",
    "Copying images placed inside comment text. Only Default Photos are copied; an image in "
    "the text is shown from where it is hosted, and flagged when Spectora hosts it.",
    "Displaying scripts, event handlers, forms, embedded frames from anywhere but YouTube "
    "or Vimeo, and CSS such as position. They are kept in the stored text, not shown.",
    "Splitting a section that Spectora merged. The report points to it so you can check.",
    "Merging an upload into an existing template. Every upload becomes a new template.",
    "Exporting back to Spectora's format.",
)


@dataclass(frozen=True)
class Structure:
    rows: int
    empty_rows: int
    rows_skipped: int
    sections: int
    items: int
    comments: int
    comment_types: dict[str, int]


@dataclass(frozen=True)
class TypeCount:
    label: str
    in_file: int
    imported: int


@dataclass(frozen=True)
class CoverageFigure:
    label: str
    part: int
    whole: int
    meaning: str

    @property
    def percent(self) -> str:
        if self.whole == 0:
            return "n/a"
        value = 100 * self.part / self.whole
        return f"{value:.0f}%" if value in (0, 100) else f"{value:.1f}%"


@dataclass(frozen=True)
class IssueGroup:
    kind: str
    label: str
    severity: str
    issues: tuple[StoredIssue, ...]


@dataclass(frozen=True)
class MarkupLine:
    group: str
    entries: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Markup:
    comments_with_markup: int
    inventory: tuple[MarkupLine, ...]
    not_displayed: tuple[tuple[str, int], ...]
    editor_state_removed: int


@dataclass(frozen=True)
class Report:
    run: StoredRun
    verdict_label: str
    in_file: Structure
    imported: Structure
    rederived_matches: bool
    parser_changed: bool
    types: tuple[TypeCount, ...]
    coverage: tuple[CoverageFigure, ...]
    ledger: tuple[StoredLedgerEntry, ...]
    issue_groups: tuple[IssueGroup, ...]
    markup: Markup
    missing_from_export: tuple[str, ...] = MISSING_FROM_EXPORT
    not_supported: tuple[str, ...] = NOT_SUPPORTED_HERE


def build_report(conn: psycopg.Connection, run_id: UUID) -> Report | None:
    run = read_run(conn, run_id)
    if run is None:
        return None
    rows = read_source_rows(conn, run_id)
    workbook = workbook_from_rows(rows)
    in_file, bodies = _rederive(workbook)
    imported = Structure(
        rows=run.rows_total,
        empty_rows=run.empty_rows,
        rows_skipped=run.rows_skipped,
        sections=run.sections_created,
        items=run.items_created,
        comments=run.comments_created,
        comment_types=run.comment_types,
    )
    ledger = tuple(read_ledger(conn, run_id))
    return Report(
        run=run,
        verdict_label=VERDICT_LABELS.get(run.verdict, run.verdict),
        in_file=in_file,
        imported=imported,
        rederived_matches=in_file == imported,
        parser_changed=run.parser_version != PARSER_VERSION,
        types=_type_counts(in_file, imported),
        coverage=coverage(ledger, workbook),
        ledger=ledger,
        issue_groups=group_issues(read_issues(conn, run_id)),
        markup=markup_summary(bodies),
    )


def _rederive(workbook: Workbook) -> tuple[Structure, list[str]]:
    columns = map_columns(workbook)
    template = parse(workbook, columns, "").template
    comments = template.comments()
    structure = Structure(
        rows=len(workbook.rows),
        empty_rows=template.empty_rows,
        rows_skipped=len(workbook.rows) - template.empty_rows - len(comments),
        sections=len(template.sections),
        items=len(template.items()),
        comments=len(comments),
        comment_types=dict(Counter(comment.comment_type for comment in comments)),
    )
    return structure, [comment.body_html for comment in comments]


def _type_counts(in_file: Structure, imported: Structure) -> tuple[TypeCount, ...]:
    kinds = list(COMMENT_TYPES)
    kinds += sorted((set(in_file.comment_types) | set(imported.comment_types)) - set(kinds))
    return tuple(
        TypeCount(
            COMMENT_TYPE_LABELS.get(kind, f"Other: {kind or '(blank)'}"),
            in_file.comment_types.get(kind, 0),
            imported.comment_types.get(kind, 0),
        )
        for kind in kinds
    )


def coverage(ledger: Iterable[StoredLedgerEntry], workbook: Workbook) -> tuple[CoverageFigure, ...]:
    """The three coverage numbers from docs/design/preservation.md, section 1."""
    cells = Counter()
    for entry in ledger:
        cells[entry.outcome] += entry.cell_count
    in_file = sum(cells.values())
    stored = sum(1 for row in workbook.rows for value in row.cells.values() if value)
    modelled = in_file - cells["unrecognised"]
    varying = cells["consumed"] + cells["unrecognised"]
    return (
        CoverageFigure(
            "Captured",
            stored,
            in_file,
            "Filled cells kept word for word in the stored source rows.",
        ),
        CoverageFigure(
            "Modelled",
            modelled,
            in_file,
            "Filled cells that landed in a named field of the template.",
        ),
        CoverageFigure(
            "Varying data modelled",
            cells["consumed"],
            varying,
            "The same, leaving out columns holding one value on every row. This is the "
            "number that would fall first if a column were ever left out.",
        ),
    )


def group_issues(issues: Iterable[StoredIssue]) -> tuple[IssueGroup, ...]:
    """Issues grouped by kind: most severe first, then in the order ISSUE_LABELS lists."""
    by_kind: dict[str, list[StoredIssue]] = {}
    for issue in issues:
        by_kind.setdefault(issue.kind, []).append(issue)
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    kind_rank = {kind.value: rank for rank, kind in enumerate(ISSUE_LABELS)}

    def rank(kind: str) -> tuple[int, int, str]:
        worst = min(severity_rank.get(issue.severity, 3) for issue in by_kind[kind])
        return worst, kind_rank.get(kind, len(kind_rank)), kind

    return tuple(
        IssueGroup(
            kind,
            ISSUE_LABELS.get(kind, kind),
            min((i.severity for i in by_kind[kind]), key=lambda s: severity_rank.get(s, 3)),
            tuple(by_kind[kind]),
        )
        for kind in sorted(by_kind, key=rank)
    )


_MARKUP_GROUPS = (
    ("tag ", "Tags"),
    ("attribute ", "Attributes"),
    ("style ", "CSS properties"),
    ("iframe from ", "Embedded frames"),
    ("html comment", "HTML comments"),
)


def markup_summary(bodies: Iterable[str]) -> Markup:
    """Every tag, attribute, CSS property and frame host in the comment text, and what the
    render policy will not display (rule H6)."""
    inventory: Counter[str] = Counter()
    lost: Counter[str] = Counter()
    with_markup = 0
    for body in bodies:
        found = markup_inventory(body)
        if found:
            with_markup += 1
        inventory += found
        lost += neutralised(body)
    editor_state = sum(count for entry, count in lost.items() if is_editor_state(entry))
    not_displayed = tuple(
        (entry, count) for entry, count in lost.most_common() if not is_editor_state(entry)
    )
    return Markup(
        comments_with_markup=with_markup,
        inventory=_grouped(inventory),
        not_displayed=not_displayed,
        editor_state_removed=editor_state,
    )


def _grouped(inventory: Counter[str]) -> tuple[MarkupLine, ...]:
    lines = []
    for prefix, label in _MARKUP_GROUPS:
        entries = tuple(
            (entry.removeprefix(prefix) or label.lower(), count)
            for entry, count in inventory.most_common()
            if entry.startswith(prefix)
        )
        if entries:
            lines.append(MarkupLine(label, entries))
    return tuple(lines)
