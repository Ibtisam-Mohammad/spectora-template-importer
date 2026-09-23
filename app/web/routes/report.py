"""The import report, shown after every upload and linked from the library and the editor."""

from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.db.runs import StoredIssue
from app.services.reporting import build_report
from app.web.database import db
from app.web.templating import templates

router = APIRouter()


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def report_page(
    request: Request, run_id: UUID, conn: Annotated[psycopg.Connection, Depends(db)]
) -> Response:
    report = build_report(conn, run_id)
    if report is None:
        raise HTTPException(404, "There are no import results at this address.")
    return templates.TemplateResponse(
        request, "report.html", {"report": report, "node_url": _node_url(report.run.template_id)}
    )


def _node_url(template_id: UUID | None):
    """Where the editor shows the node an issue is about, or None when there is none."""

    def url(issue: StoredIssue) -> str | None:
        if template_id is None or issue.section_id is None:
            return None
        address = f"/t/{template_id}?section={issue.section_id}"
        if issue.item_id:
            address += f"&item={issue.item_id}"
        if issue.comment_id:
            address += f"#comment-{issue.comment_id}"
        return address

    return url
