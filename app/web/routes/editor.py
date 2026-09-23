"""The template editor: three panes, sections | items | comments, like Spectora's own.

Every request renders the whole page. Links in the panes carry htmx attributes that swap only
the panes to their right, so a click keeps the scroll position of the pane it was made in, and
the same URL loaded directly, or restored from history, renders the same page.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.db.records import StoredComment, StoredItem
from app.db.templates import issues_by_node, latest_run_id, read_tree
from app.spectora.columns import COMMENT_TYPE_LABELS, COMMENT_TYPES
from app.web.database import db
from app.web.templating import templates

router = APIRouter()


@dataclass(frozen=True)
class CommentGroup:
    key: str
    label: str
    comments: tuple[StoredComment, ...]


@router.get("/t/{template_id}", response_class=HTMLResponse)
def editor_page(
    request: Request,
    template_id: UUID,
    conn: Annotated[psycopg.Connection, Depends(db)],
    section: UUID | None = None,
    item: UUID | None = None,
) -> Response:
    tree = read_tree(conn, template_id)
    if tree is None:
        raise HTTPException(404, "There is no template at this address.")
    selected_section = _selected(tree.sections, section)
    selected_item = _selected(selected_section.items, item) if selected_section else None
    return templates.TemplateResponse(
        request,
        "editor.html",
        {
            "template": tree,
            "section": selected_section,
            "item": selected_item,
            "groups": comment_groups(selected_item) if selected_item else [],
            "issues": issues_by_node(conn, template_id),
            "run_id": latest_run_id(conn, template_id),
        },
    )


def _selected[Node](nodes: tuple[Node, ...], wanted: UUID | None) -> Node | None:
    """The requested node, or the first one when none was requested or it is not here."""
    return next((node for node in nodes if node.id == wanted), nodes[0] if nodes else None)


def comment_groups(item: StoredItem) -> list[CommentGroup]:
    """Comments under Spectora's three headings, then any type Spectora does not document."""
    groups = [
        CommentGroup(
            key,
            COMMENT_TYPE_LABELS[key],
            tuple(c for c in item.comments if c.comment_type == key),
        )
        for key in COMMENT_TYPES
    ]
    other = tuple(c for c in item.comments if c.comment_type not in COMMENT_TYPES)
    if other:
        groups.append(CommentGroup("other", "Other", other))
    return groups
