"""Turn raw rows into the template tree, recording what it notices on the way.

Rules: S1 (a row is a comment), S2 and S3 (identity is the contiguous block, not the name),
S4 (every row kept), S5 (template name), F8 (no silent drops), T1, T2, T4, T5 (text as
exported), O1 to O4 (ordering), V1 to V3, V5 to V9 (values verbatim), PH1 (photos).

D2: nothing here receives the export verdict, so it cannot change how a file is parsed.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import PureWindowsPath

from app.spectora.columns import (
    ANSWER_TYPE_LABELS,
    CATEGORY_LABELS,
    COMMENT_TYPES,
    PHOTO_SLOTS,
    decode_name,
    split_list,
)
from app.spectora.model import (
    ColumnMap,
    Issue,
    IssueKind,
    ParsedComment,
    ParsedItem,
    ParsedPhoto,
    ParsedSection,
    ParsedTemplate,
    ParseResult,
    RawRow,
    Scope,
    Severity,
    Workbook,
)

# Display order of comment-type groups. Values not listed sort after these, in text order.
TYPE_GROUP_ORDER = {comment_type: rank for rank, comment_type in enumerate(COMMENT_TYPES)}


def name_from_filename(filename: str) -> str:
    """The template's name: the uploaded file's name without folders or extension."""
    stem = PureWindowsPath(filename).stem
    return stem or "Imported template"


def parse(workbook: Workbook, columns: ColumnMap, template_name: str) -> ParseResult:
    builder = _TreeBuilder(columns)
    for row in workbook.rows:
        builder.add(row)
    sections = tuple(
        _finish_section(section, builder.issues, columns) for section in builder.sections
    )
    template = ParsedTemplate(template_name, sections, empty_rows=builder.empty_rows)
    return ParseResult(template, tuple(builder.issues))


# ---------------------------------------------------------------- building blocks


@dataclass
class _ItemBlock:
    name: str
    first_row: int
    comments: list[ParsedComment] = field(default_factory=list)


@dataclass
class _SectionBlock:
    name: str
    first_row: int
    items: list[_ItemBlock] = field(default_factory=list)


class _TreeBuilder:
    """Walks rows in file order. A change of Section Name or Item Name starts a new block."""

    def __init__(self, columns: ColumnMap) -> None:
        self.columns = columns
        self.sections: list[_SectionBlock] = []
        self.issues: list[Issue] = []
        self.empty_rows = 0
        self._section_key: str | None = None
        self._item_key: str | None = None

    def add(self, row: RawRow) -> None:
        if row.is_empty():
            self.empty_rows += 1
            return
        section_text = row.text(self.columns.letter("section_name"))
        item_text = row.text(self.columns.letter("item_name"))
        if not section_text.strip() or not item_text.strip():
            self._skip(row, section_text)
            return
        if section_text != self._section_key:
            self.sections.append(_SectionBlock(decode_name(section_text), row.number))
            self._section_key, self._item_key = section_text, None
        section = self.sections[-1]
        if item_text != self._item_key:
            section.items.append(_ItemBlock(decode_name(item_text), row.number))
            self._item_key = item_text
        comment = _comment(row, self.columns)
        section.items[-1].comments.append(comment)
        self.issues.extend(_value_issues(comment, self.columns))

    def _skip(self, row: RawRow, section_text: str) -> None:
        missing = "Item Name" if section_text.strip() else "Section Name"
        column = self.columns.letter("item_name" if section_text.strip() else "section_name")
        self.issues.append(
            Issue(
                IssueKind.ROW_SKIPPED,
                Severity.WARNING,
                f"Row {row.number} has no {missing}, so it cannot be placed in the template. "
                "Its cells are kept in the source rows.",
                Scope.FILE,
                row.number,
                column,
            )
        )


def _comment(row: RawRow, columns: ColumnMap) -> ParsedComment:
    def text(field_name: str) -> str:
        return row.text(columns.letter(field_name))

    return ParsedComment(
        row=row.number,
        name=decode_name(text("comment_name")),
        body_html=text("comment_text"),
        comment_type=text("comment_type"),
        category=text("category"),
        choices=split_list(text("choices")),
        unit_options=split_list(text("unit_options")),
        recommendation=text("recommendation"),
        order_raw=text("order"),
        answer_type=text("answer_type"),
        default_value=text("default_value"),
        default_value_2=text("default_value_2"),
        default_unit_type=text("default_unit_type"),
        default_location=text("default_location"),
        estimate_min=text("estimate_min"),
        estimate_max=text("estimate_max"),
        locked=text("locked"),
        simple_format=text("simple_format"),
        disable_photos=text("disable_photos"),
        uses=text("uses"),
        last_modified=text("last_modified"),
        photos=_photos(row, columns),
    )


def _photos(row: RawRow, columns: ColumnMap) -> tuple[ParsedPhoto, ...]:
    photos = []
    for slot in PHOTO_SLOTS:
        url = row.text(columns.letter(f"photo_{slot}"))
        caption = row.text(columns.letter(f"photo_{slot}_caption"))
        if url or caption:
            photos.append(ParsedPhoto(slot, url, caption))
    return tuple(photos)


def _value_issues(comment: ParsedComment, columns: ColumnMap) -> list[Issue]:
    """Values outside what the header documents. They are kept exactly as they arrived."""
    checks = (
        ("comment_type", comment.comment_type, COMMENT_TYPES, "Comment Type"),
        ("answer_type", comment.answer_type, ANSWER_TYPE_LABELS, "Answer Type"),
        ("category", comment.category, CATEGORY_LABELS, "Category"),
    )
    issues = []
    for field_name, value, known, label in checks:
        if value and value not in known:
            issues.append(
                Issue(
                    IssueKind.UNEXPECTED_VALUE,
                    Severity.WARNING,
                    f"{label} '{value}' on comment '{comment.name}' is not one Spectora "
                    "documents. It was imported as written.",
                    Scope.COMMENT,
                    comment.row,
                    columns.letter(field_name),
                )
            )
    return issues


# ---------------------------------------------------------------- ordering


def _order_number(comment: ParsedComment) -> int | None:
    text = comment.order_raw.strip()
    return int(text) if text.lstrip("-").isdigit() else None


def _group_key(comment_type: str) -> tuple[int, str]:
    return (TYPE_GROUP_ORDER.get(comment_type, len(TYPE_GROUP_ORDER)), comment_type)


def _sort_key(comment: ParsedComment) -> tuple:
    number = _order_number(comment)
    return (*_group_key(comment.comment_type), number is None, number or 0, comment.row)


def _finish_section(
    section: _SectionBlock, issues: list[Issue], columns: ColumnMap
) -> ParsedSection:
    items = []
    for item in section.items:
        ordered = tuple(sorted(item.comments, key=_sort_key))
        issues.extend(_ambiguous_order(section.name, item, ordered, columns))
        items.append(ParsedItem(item.name, item.first_row, ordered))
    return ParsedSection(section.name, section.first_row, tuple(items))


def _ambiguous_order(
    section_name: str, item: _ItemBlock, comments: tuple[ParsedComment, ...], columns: ColumnMap
) -> list[Issue]:
    issues = []
    groups = Counter(
        (comment.comment_type, number)
        for comment in comments
        if (number := _order_number(comment)) is not None
    )
    shared = sorted({comment_type for (comment_type, _), count in groups.items() if count > 1})
    for comment_type in shared:
        issues.append(
            Issue(
                IssueKind.AMBIGUOUS_ORDER,
                Severity.INFO,
                f"In '{section_name} / {item.name}', some {comment_type or 'untyped'} comments "
                "share an Order value, so their order follows the file.",
                Scope.ITEM,
                item.first_row,
                columns.letter("order"),
            )
        )
    return issues
