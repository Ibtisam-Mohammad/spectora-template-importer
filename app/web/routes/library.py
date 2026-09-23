"""Template library: the landing page."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def library_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "library.html", {"templates": []})
