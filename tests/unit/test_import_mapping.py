"""The column mapping the importer writes with and verifies against must not drift."""

from dataclasses import fields

from app.db.imports import COMMENT_SOURCE_FIELDS
from app.db.records import StoredComment
from app.spectora.model import ParsedComment


def test_every_parsed_comment_field_is_stored():
    parsed = {f.name for f in fields(ParsedComment)} - {"photos"}
    assert set(COMMENT_SOURCE_FIELDS.values()) == parsed


def test_every_stored_column_is_read_back():
    stored = {f.name for f in fields(StoredComment)}
    assert set(COMMENT_SOURCE_FIELDS) <= stored
