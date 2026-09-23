"""FastAPI application. Vercel imports `app` from here (see [tool.vercel] in pyproject.toml)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.routes import library
from app.web.templating import STATIC_DIR


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Spectora template importer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(library.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
