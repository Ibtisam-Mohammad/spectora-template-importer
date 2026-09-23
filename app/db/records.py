"""What the database hands back: a template tree as stored, and the library's summary rows."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class StoredPhoto:
    id: UUID
    position: int
    source_url: str
    caption: str
    stored_path: str | None


@dataclass(frozen=True)
class StoredComment:
    id: UUID
    position: int
    name: str
    body_html: str
    comment_type: str
    category: str
    choices: tuple[str, ...]
    unit_options: tuple[str, ...]
    recommendation: str
    source_order: str
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
    source_last_modified: str
    body_edited_at: datetime | None
    import_run_id: UUID | None
    source_row_number: int | None
    photos: tuple[StoredPhoto, ...]


@dataclass(frozen=True)
class StoredItem:
    id: UUID
    position: int
    name: str
    source_first_row: int | None
    comments: tuple[StoredComment, ...]


@dataclass(frozen=True)
class StoredSection:
    id: UUID
    position: int
    name: str
    source_first_row: int | None
    items: tuple[StoredItem, ...]


@dataclass(frozen=True)
class StoredTemplate:
    id: UUID
    name: str
    origin: str
    copied_from_id: UUID | None
    created_at: datetime
    updated_at: datetime
    sections: tuple[StoredSection, ...]

    def items(self) -> list[StoredItem]:
        return [item for section in self.sections for item in section.items]

    def comments(self) -> list[StoredComment]:
        return [comment for item in self.items() for comment in item.comments]


@dataclass(frozen=True)
class TemplateSummary:
    id: UUID
    name: str
    origin: str
    updated_at: datetime
    sections: int
    items: int
    comments: int
    latest_run_id: UUID | None


@dataclass(frozen=True)
class NodeIssue:
    """An import issue as the editor shows it on the node it is about."""

    kind: str
    severity: str
    detail: str
    row_number: int | None
    column_letter: str | None
