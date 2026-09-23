"""The template editor: three panes, sections | items | comments, like Spectora's own.

Every request renders the whole page. Links and forms in the panes carry htmx attributes that
swap only the parts that changed, so a click keeps the scroll position of the pane it was made
in, and the same URL loaded directly, or restored from history, renders the same page.
"""

from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.db.records import StoredComment, StoredItem, StoredTemplate
from app.db.templates import issues_by_node, latest_run_id, read_tree
from app.services.editing import CommentResult
from app.spectora.columns import (
    ANSWER_TYPE_LABELS,
    CATEGORY_LABELS,
    COMMENT_TYPE_LABELS,
    COMMENT_TYPES,
)
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
    return render_editor(request, conn, template_id, section, item)


def editor_url(
    template_id: UUID, section_id: UUID | None = None, item_id: UUID | None = None
) -> str:
    query = {key: value for key, value in (("section", section_id), ("item", item_id)) if value}
    return f"/t/{template_id}" + (f"?{urlencode(query)}" if query else "")


def render_editor(
    request: Request,
    conn: psycopg.Connection,
    template_id: UUID,
    section_id: UUID | None = None,
    item_id: UUID | None = None,
    open_comment: UUID | None = None,
    result: CommentResult | None = None,
) -> Response:
    """The editor for one selection. After an edit made with htmx, the browser's address is set
    to that selection; after an edit made without it, the browser is sent there."""
    tree = read_tree(conn, template_id)
    if tree is None:
        raise HTTPException(404, "There is no template at this address.")
    section = _selected(tree.sections, section_id)
    item = _selected(section.items, item_id) if section else None
    url = editor_url(tree.id, section.id if section else None, item.id if item else None)
    if result is not None:
        open_comment = result.comment_id
    if request.method != "GET" and "hx-request" not in request.headers:
        anchor = f"#comment-{open_comment}" if open_comment else ""
        return RedirectResponse(url + anchor, status_code=303)
    response = templates.TemplateResponse(
        request,
        "editor.html",
        {
            "template": tree,
            "section": section,
            "item": item,
            "groups": comment_groups(item) if item else [],
            "issues": issues_by_node(conn, template_id),
            "run_id": latest_run_id(conn, template_id),
            "open_comment": open_comment,
            "result": result,
            "suggestions": suggestions(tree),
            "comment_types": COMMENT_TYPE_LABELS,
            "answer_types": ANSWER_TYPE_LABELS,
            "categories": CATEGORY_LABELS,
        },
    )
    if request.method != "GET":
        response.headers["HX-Push-Url"] = url
    return response


# Fields whose values Spectora picks from account-wide lists that the export leaves out. The
# values this template already uses are offered as suggestions; anything can still be typed.
SUGGESTED_FIELDS = ("recommendation", "default_location", "default_unit_type")


def suggestions(tree: StoredTemplate) -> dict[str, list[str]]:
    """Each suggested field's distinct values in this template, for the form's pick lists."""
    return {
        field: sorted(
            {value for comment in tree.comments() if (value := getattr(comment, field)).strip()},
            key=lambda value: value.strip().casefold(),
        )
        for field in SUGGESTED_FIELDS
    }


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
