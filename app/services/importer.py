"""Import an upload: analyse it, copy its photos, write it, verify it, all or nothing.

Rules R1 (one transaction; a failure leaves nothing behind) and R3 (verify before commit).

Verification proves storage, not parsing. It checks that what the database now holds is what
the parser produced: every source row cell for cell, and the tree read back through the
editor's own query field for field. Whether the parser read the file correctly is checked by
the unit tests against hand-verified facts about the fixtures.
"""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import psycopg

from app.db.imports import (
    COMMENT_SOURCE_FIELDS,
    ImportIds,
    NewImport,
    count_rows,
    insert_import,
    mark_verified,
    read_source_rows,
    source_rows,
)
from app.db.records import StoredTemplate
from app.db.templates import read_tree
from app.render import neutralised_content
from app.services.photos import PhotoCopier, photo_issues, photo_urls
from app.spectora.analysis import Analysis, analyse
from app.spectora.model import (
    ColumnMap,
    Issue,
    IssueKind,
    ParsedTemplate,
    Scope,
    Severity,
)


class VerificationFailed(Exception):
    """What was stored differs from what was parsed. The import has been rolled back."""


@dataclass(frozen=True)
class ImportOutcome:
    template_id: UUID
    run_id: UUID
    analysis: Analysis
    issues: tuple[Issue, ...]


def import_file(
    conn: psycopg.Connection, data: bytes, filename: str, photos: PhotoCopier | None
) -> ImportOutcome:
    """Raises Refusal when the file cannot be imported, VerificationFailed on a storage
    mismatch. Either way nothing is stored."""
    started_at = datetime.now(UTC)
    analysis = analyse(data, filename)
    template, columns = analysis.template, analysis.columns
    copies = photos.copy_all(photo_urls(template)) if photos else None
    issues = (
        *analysis.issues,
        *render_issues(template, columns),
        *photo_issues(template, columns, copies),
    )
    new = NewImport(
        analysis=analysis,
        filename=filename,
        sha256=hashlib.sha256(data).hexdigest(),
        started_at=started_at,
        issues=issues,
        photo_paths={url: copy.stored_path for url, copy in (copies or {}).items()},
    )
    with conn.transaction():
        ids = insert_import(conn, new)
        problems = verification_problems(conn, ids, new)
        if problems:
            raise VerificationFailed("; ".join(problems))
        mark_verified(conn, ids.run_id)
    return ImportOutcome(ids.template_id, ids.run_id, analysis, issues)


def render_issues(template: ParsedTemplate, columns: ColumnMap) -> list[Issue]:
    """Comments holding markup that is stored but will not be displayed (rule H3)."""
    issues = []
    for comment in template.comments():
        lost = neutralised_content(comment.body_html)
        if lost:
            issues.append(
                Issue(
                    IssueKind.RENDER_NEUTRALISED,
                    Severity.INFO,
                    f"'{comment.name}' contains markup that is kept but not displayed: "
                    + ", ".join(sorted(lost))
                    + ".",
                    Scope.COMMENT,
                    comment.row,
                    columns.letter("comment_text"),
                )
            )
    return issues


# ---------------------------------------------------------------- verification


def verification_problems(conn: psycopg.Connection, ids: ImportIds, new: NewImport) -> list[str]:
    analysis = new.analysis
    problems = []
    stored_rows = read_source_rows(conn, ids.run_id)
    expected_rows = source_rows(analysis)
    if stored_rows != expected_rows:
        different = sorted(
            number
            for number in stored_rows.keys() | expected_rows.keys()
            if stored_rows.get(number) != expected_rows.get(number)
        )
        problems.append(f"source rows differ from the file at rows {different[:10]}")
    tree = read_tree(conn, ids.template_id)
    if tree is None:
        return [*problems, "the template was not stored"]
    difference = _first_difference(_parsed_nodes(analysis.template), _stored_nodes(tree))
    if difference:
        problems.append(difference)
    for table, expected in (
        ("import_issue", len(new.issues)),
        ("cell_ledger", len(analysis.ledger)),
    ):
        stored = count_rows(conn, table, ids.run_id)
        if stored != expected:
            problems.append(f"{table} holds {stored} rows, expected {expected}")
    problems.extend(_unaccounted_rows(new))
    return problems


def _unaccounted_rows(new: NewImport) -> list[str]:
    """Every data row is a comment, an empty row or a reported skip (rule F8)."""
    analysis = new.analysis
    skipped = sum(1 for issue in new.issues if issue.kind is IssueKind.ROW_SKIPPED)
    accounted = len(analysis.template.comments()) + analysis.template.empty_rows + skipped
    if accounted == len(analysis.workbook.rows):
        return []
    return [f"{len(analysis.workbook.rows)} rows were read but {accounted} are accounted for"]


def _parsed_nodes(template: ParsedTemplate) -> Iterator[tuple]:
    yield ("template", template.name)
    for section in template.sections:
        yield ("section", section.name, section.first_row)
        for item in section.items:
            yield ("item", item.name, item.first_row)
            for comment in item.comments:
                yield ("comment", *(getattr(comment, a) for a in COMMENT_SOURCE_FIELDS.values()))
                for photo in comment.photos:
                    yield ("photo", photo.slot, photo.url, photo.caption)


def _stored_nodes(tree: StoredTemplate) -> Iterator[tuple]:
    yield ("template", tree.name)
    for section in tree.sections:
        yield ("section", section.name, section.source_first_row)
        for item in section.items:
            yield ("item", item.name, item.source_first_row)
            for comment in item.comments:
                yield ("comment", *(getattr(comment, c) for c in COMMENT_SOURCE_FIELDS))
                for photo in comment.photos:
                    yield ("photo", photo.position, photo.source_url, photo.caption)


def _first_difference(expected: Iterator[tuple], stored: Iterator[tuple]) -> str | None:
    expected_nodes, stored_nodes = list(expected), list(stored)
    for index, (want, got) in enumerate(zip(expected_nodes, stored_nodes, strict=False)):
        if want != got:
            return f"stored node {index} is {got[:2]} where the parse has {want[:2]}"
    if len(expected_nodes) != len(stored_nodes):
        return f"stored tree has {len(stored_nodes)} nodes, the parse has {len(expected_nodes)}"
    return None
