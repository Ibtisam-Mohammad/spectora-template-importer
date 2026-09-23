"""Checks on the whole file, the whole tree, or one comment. They report; they never change.

Rules: F3 (more than one sheet), F6 (header issues), D1 (Plain Text warning), V1 to V3 (values
Spectora does not document), V4 (invariants reported, never enforced), S6 (merged same-named
sections), E5 (edits get the same comment checks as import).
"""

from app.spectora.columns import ANSWER_TYPE_LABELS, CATEGORY_LABELS, COMMENT_TYPES
from app.spectora.model import (
    ColumnMap,
    Detection,
    Issue,
    IssueKind,
    ParsedComment,
    ParsedTemplate,
    Scope,
    Severity,
    Verdict,
    Workbook,
)

# For checking a comment that did not come from a file, such as one being edited.
NO_COLUMNS = ColumnMap(fields={})


def file_issues(workbook: Workbook, columns: ColumnMap, detection: Detection) -> list[Issue]:
    issues = []
    if len(workbook.sheet_names) > 1:
        others = ", ".join(f"'{name}'" for name in workbook.sheet_names[1:])
        issues.append(
            Issue(
                IssueKind.MULTIPLE_SHEETS,
                Severity.WARNING,
                f"The workbook has {len(workbook.sheet_names)} sheets. Only the first, "
                f"'{workbook.sheet_names[0]}', was read; {others} were not.",
            )
        )
    for column, header in columns.unknown:
        issues.append(
            Issue(
                IssueKind.UNKNOWN_HEADER,
                Severity.WARNING,
                f"Column {column}, '{header}', is not a Spectora column. Its values are kept in "
                "the source rows but not shown in the editor.",
                column=column,
            )
        )
    for column, header in columns.duplicates:
        issues.append(
            Issue(
                IssueKind.UNKNOWN_HEADER,
                Severity.WARNING,
                f"Column {column} repeats the header '{header}'. The first one was used.",
                column=column,
            )
        )
    if columns.missing:
        issues.append(
            Issue(
                IssueKind.MISSING_HEADER,
                Severity.WARNING,
                f"{len(columns.missing)} Spectora columns are missing: "
                + ", ".join(f"'{header}'" for header in columns.missing)
                + ". Those fields were left empty.",
            )
        )
    if detection.verdict is Verdict.SPECTORA_PLAIN:
        issues.append(
            Issue(IssueKind.PLAIN_TEXT_EXPORT, Severity.WARNING, " ".join(detection.reasons))
        )
    return issues


def tree_issues(template: ParsedTemplate, columns: ColumnMap) -> list[Issue]:
    return [*_invariant_issues(template, columns), *_merged_section_issues(template, columns)]


def comment_issues(comment: ParsedComment, columns: ColumnMap = NO_COLUMNS) -> list[Issue]:
    """Everything the import checks on a single comment."""
    return [*value_issues(comment, columns), *invariant_issues(comment, columns)]


def value_issues(comment: ParsedComment, columns: ColumnMap = NO_COLUMNS) -> list[Issue]:
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


def invariant_issues(comment: ParsedComment, columns: ColumnMap = NO_COLUMNS) -> list[Issue]:
    """Two relationships held on every row of every export examined. Reported, never enforced."""
    issues = []
    is_defect = comment.comment_type == "defect"
    if bool(comment.category) != is_defect:
        detail = (
            f"Deficiency '{comment.name}' has no Category."
            if is_defect
            else f"'{comment.name}' has a Category, which Spectora sets only on deficiencies."
        )
        issues.append(
            Issue(
                IssueKind.INVARIANT_VIOLATED,
                Severity.WARNING,
                detail,
                Scope.COMMENT,
                comment.row,
                columns.letter("category"),
            )
        )
    is_multiple_choice = comment.answer_type == "checkbox"
    if bool(comment.choices) != is_multiple_choice:
        detail = (
            f"Multiple-choice comment '{comment.name}' has no answer choices."
            if is_multiple_choice
            else f"'{comment.name}' has answer choices but is not a multiple-choice comment."
        )
        issues.append(
            Issue(
                IssueKind.INVARIANT_VIOLATED,
                Severity.WARNING,
                detail,
                Scope.COMMENT,
                comment.row,
                columns.letter("choices"),
            )
        )
    return issues


def _invariant_issues(template: ParsedTemplate, columns: ColumnMap) -> list[Issue]:
    return [issue for c in template.comments() for issue in invariant_issues(c, columns)]


def _merged_section_issues(template: ParsedTemplate, columns: ColumnMap) -> list[Issue]:
    """An item name appearing as two separate blocks in one section is the trace Spectora leaves
    when two neighbouring sections share a name. The section is not split: the file cannot say
    where one ends, and a section may genuinely list an item name twice."""
    issues = []
    for section in template.sections:
        seen: set[str] = set()
        repeated: list[str] = []
        for item in section.items:
            if item.name in seen and item.name not in repeated:
                repeated.append(item.name)
            seen.add(item.name)
        if repeated:
            names = " and ".join(f"'{name}'" for name in repeated)
            issues.append(
                Issue(
                    IssueKind.MERGED_SECTIONS_SUSPECTED,
                    Severity.WARNING,
                    f"In section '{section.name}', {names} each appear more than once. Spectora "
                    "exports two neighbouring sections with the same name as one section. If "
                    "you had two, the items of both are in this one.",
                    Scope.SECTION,
                    section.first_row,
                    columns.letter("item_name"),
                )
            )
    return issues
