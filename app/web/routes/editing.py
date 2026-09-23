"""Form posts that change a template. Each one calls a service, then renders the editor at the
selection the change leaves behind. The forms say which part of the page to swap."""

from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, create_model

from app.db.editing import EDITABLE_COMMENT_COLUMNS, NodePath
from app.services import editing
from app.services.editing import CommentResult
from app.web.database import db
from app.web.routes.editor import render_editor

router = APIRouter()

Connection = Annotated[psycopg.Connection, Depends(db)]
Name = Annotated[str, Form()]
Direction = Annotated[Literal["up", "down"], Form()]

# Every editable comment column, each optional: a field the form leaves out stays as stored.
CommentForm: type[BaseModel] = create_model(
    "CommentForm", **{column: (str | None, None) for column in EDITABLE_COMMENT_COLUMNS}
)


def _found[T](value: T | None) -> T:
    if value is None:
        raise HTTPException(404, "That part of the template no longer exists.")
    return value


def _show(
    request: Request, conn: psycopg.Connection, path: NodePath, result: CommentResult | None = None
) -> Response:
    return render_editor(
        request,
        conn,
        path.template_id,
        path.section_id,
        path.item_id,
        result=result,
    )


# ---------------------------------------------------------------- template


@router.post("/t/{template_id}/rename")
def rename_template(request: Request, template_id: UUID, name: Name, conn: Connection):
    editing.rename_template(conn, template_id, name)
    return _show(request, conn, NodePath(template_id))


@router.post("/t/{template_id}/delete")
def delete_template(template_id: UUID, conn: Connection):
    editing.delete_template(conn, template_id)
    return RedirectResponse("/", status_code=303)


@router.post("/t/{template_id}/sections")
def add_section(request: Request, template_id: UUID, name: Name, conn: Connection):
    return _show(request, conn, editing.add_section(conn, template_id, name))


# ---------------------------------------------------------------- sections


@router.post("/sections/{section_id}/rename")
def rename_section(request: Request, section_id: UUID, name: Name, conn: Connection):
    return _show(request, conn, _found(editing.rename_node(conn, "section", section_id, name)))


@router.post("/sections/{section_id}/move")
def move_section(request: Request, section_id: UUID, direction: Direction, conn: Connection):
    return _show(request, conn, _found(editing.move_node(conn, "section", section_id, direction)))


@router.post("/sections/{section_id}/delete")
def delete_section(request: Request, section_id: UUID, conn: Connection):
    path = _found(editing.delete_node(conn, "section", section_id))
    return _show(request, conn, NodePath(path.template_id))


@router.post("/sections/{section_id}/items")
def add_item(request: Request, section_id: UUID, name: Name, conn: Connection):
    return _show(request, conn, _found(editing.add_item(conn, section_id, name)))


# ---------------------------------------------------------------- items


@router.post("/items/{item_id}/rename")
def rename_item(request: Request, item_id: UUID, name: Name, conn: Connection):
    return _show(request, conn, _found(editing.rename_node(conn, "item", item_id, name)))


@router.post("/items/{item_id}/move")
def move_item(request: Request, item_id: UUID, direction: Direction, conn: Connection):
    return _show(request, conn, _found(editing.move_node(conn, "item", item_id, direction)))


@router.post("/items/{item_id}/delete")
def delete_item(request: Request, item_id: UUID, conn: Connection):
    path = _found(editing.delete_node(conn, "item", item_id))
    return _show(request, conn, NodePath(path.template_id, path.section_id))


@router.post("/items/{item_id}/comments")
def add_comment(
    request: Request,
    item_id: UUID,
    name: Name,
    comment_type: Annotated[str, Form()],
    conn: Connection,
):
    result = _found(editing.add_comment(conn, item_id, name, comment_type))
    return _show(request, conn, result.path, result)


# ---------------------------------------------------------------- comments


@router.post("/comments/{comment_id}")
def save_comment(
    request: Request,
    comment_id: UUID,
    form: Annotated[CommentForm, Form()],  # type: ignore[valid-type]
    conn: Connection,
):
    submitted = {column: value for column, value in form.model_dump().items() if value is not None}
    result = _found(editing.save_comment(conn, comment_id, submitted))
    return _show(request, conn, result.path, result)


@router.post("/comments/{comment_id}/revert")
def revert_comment(request: Request, comment_id: UUID, conn: Connection):
    result = _found(editing.revert_comment(conn, comment_id))
    return _show(request, conn, result.path, result)


@router.post("/comments/{comment_id}/move")
def move_comment(request: Request, comment_id: UUID, direction: Direction, conn: Connection):
    path = _found(editing.move_node(conn, "comment", comment_id, direction))
    return render_editor(
        request, conn, path.template_id, path.section_id, path.item_id, open_comment=comment_id
    )


@router.post("/comments/{comment_id}/delete")
def delete_comment(request: Request, comment_id: UUID, conn: Connection):
    return _show(request, conn, _found(editing.delete_node(conn, "comment", comment_id)))
