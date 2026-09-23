"""The template library, and uploading a Spectora export into it."""

from dataclasses import dataclass

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.config import MEGABYTE, get_settings
from app.db.pool import pooled_connection
from app.db.templates import list_templates
from app.services.importer import VerificationFailed, import_file
from app.services.photos import configured_copier
from app.spectora.model import Refusal
from app.web.templating import templates

router = APIRouter()


@dataclass(frozen=True)
class UploadProblem:
    title: str
    details: tuple[str, ...] = ()


@router.get("/", response_class=HTMLResponse)
def library_page(request: Request) -> Response:
    return _library(request)


@router.post("/import")
def import_upload(request: Request, file: UploadFile | None = None) -> Response:
    settings = get_settings()
    limit = settings.max_upload_bytes
    if file is None or not file.filename:
        return _library(request, UploadProblem("Choose a Spectora export to import."), 400)
    # Rule F9: read one byte past the limit, so a larger file is recognised without reading it all.
    data = file.file.read(limit + 1)
    if len(data) > limit:
        return _library(
            request,
            UploadProblem(
                f"{file.filename} is larger than {limit // MEGABYTE} MB, the most this app "
                "accepts in one upload.",
                (
                    "Spectora exports of even very large templates are well under this size, so "
                    "check that this is the export and not another file.",
                ),
            ),
            413,
        )
    if settings.database_url is None:
        return _library(request, UploadProblem("The database is not configured."), 503)
    photos = configured_copier(settings)
    try:
        with pooled_connection(settings.database_url) as conn:
            outcome = import_file(conn, data, file.filename, photos)
    except Refusal as refused:
        return _library(request, UploadProblem(refused.reason, refused.details), 422)
    except VerificationFailed as failed:
        return _library(
            request,
            UploadProblem(
                "The import was rolled back because what was stored did not match the file.",
                (str(failed),),
            ),
            500,
        )
    finally:
        if photos:
            photos.close()
    return RedirectResponse(f"/runs/{outcome.run_id}", status_code=303)


def _library(request: Request, problem: UploadProblem | None = None, status: int = 200) -> Response:
    settings = get_settings()
    library = None
    if settings.database_url is not None:
        with pooled_connection(settings.database_url) as conn:
            library = list_templates(conn)
    return templates.TemplateResponse(
        request,
        "library.html",
        {
            "library": library,
            "problem": problem,
            "max_upload_bytes": settings.max_upload_bytes,
            "max_upload_mb": settings.max_upload_bytes // MEGABYTE,
        },
        status_code=status,
    )
