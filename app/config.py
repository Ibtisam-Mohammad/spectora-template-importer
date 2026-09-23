"""Settings read from the environment. Nothing else in the app reads os.environ."""

import os
from dataclasses import dataclass
from functools import lru_cache

MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    supabase_url: str | None
    supabase_secret_key: str | None
    photo_bucket: str
    max_upload_bytes: int = 4 * MEGABYTE


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=_env("DATABASE_URL"),
        supabase_url=_env("SUPABASE_URL"),
        supabase_secret_key=_env("SUPABASE_SECRET_KEY"),
        photo_bucket=_env("PHOTO_BUCKET") or "template-photos",
    )
