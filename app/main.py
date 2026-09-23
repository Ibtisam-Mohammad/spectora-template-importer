"""FastAPI application. Vercel imports `app` from here (see [tool.vercel] in pyproject.toml)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.db.pool import close_pool
from app.web.database import DatabaseNotConfigured
from app.web.routes import editor, library
from app.web.templating import STATIC_DIR, templates


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    close_pool()


app = FastAPI(title="Spectora template importer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(library.router)
app.include_router(editor.router)


@app.exception_handler(HTTPException)
def http_error_page(request: Request, error: HTTPException) -> Response:
    return templates.TemplateResponse(
        request,
        "message.html",
        {
            "title": "Not found" if error.status_code == 404 else "Something went wrong",
            "message": error.detail,
        },
        status_code=error.status_code,
    )


@app.exception_handler(DatabaseNotConfigured)
def database_missing_page(request: Request, _: DatabaseNotConfigured) -> Response:
    return templates.TemplateResponse(
        request,
        "message.html",
        {
            "title": "Database not configured",
            "message": "Set DATABASE_URL to Supabase's transaction pooler address. "
            "See .env.example.",
        },
        status_code=503,
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
