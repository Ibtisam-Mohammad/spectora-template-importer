"""Editing rules that hold without a database."""

import pytest

from app.db.editing import EDITABLE_COMMENT_COLUMNS
from app.db.imports import COMMENT_SOURCE_FIELDS, source_rows
from app.services.editing import original_comment
from app.spectora.workbook import HEADER_ROW
from tests.helpers import analysed
from tests.paths import ANALYSED


@pytest.mark.rule("O5")
def test_nothing_an_edit_or_a_revert_writes_can_reorder():
    assert "position" not in EDITABLE_COMMENT_COLUMNS
    assert "position" not in COMMENT_SOURCE_FIELDS


@pytest.mark.rule("O5", "E3")
def test_provenance_columns_are_not_editable():
    assert not [column for column in EDITABLE_COMMENT_COLUMNS if column.startswith("source_")]
    assert {"body_html", "name", "choices", "default_location"} <= set(EDITABLE_COMMENT_COLUMNS)


@pytest.mark.rule("E3")
@pytest.mark.parametrize("path", ANALYSED, ids=lambda p: p.name)
def test_each_source_row_alone_parses_to_the_comment_it_was_imported_as(path):
    analysis = analysed(path)
    rows = source_rows(analysis)
    for comment in analysis.template.comments():
        assert original_comment(rows[HEADER_ROW], comment.row, rows[comment.row]) == comment
