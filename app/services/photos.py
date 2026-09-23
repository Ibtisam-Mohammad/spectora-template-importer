"""Copy Spectora's default photos into our storage, so they outlive the Spectora account.

Rules PH2 and PH3. The URLs come from an uploaded file, so every fetch is a request the
uploader chose.
Only https URLs on Spectora's CDN are fetched, redirects are never followed, and each fetch is
capped in size and time, with one budget for the whole import.

Photos are copied before the import's database transaction opens, so no connection is held
while the network is slow. Stored objects are named by the SHA-256 of their bytes, so copying
the same photo twice, or copying for an import that later rolls back, stores nothing new.
"""

import hashlib
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import httpx

from app.config import MEGABYTE, Settings
from app.render import image_sources
from app.spectora.model import ColumnMap, Issue, IssueKind, ParsedTemplate, Scope, Severity

PHOTO_HOST = "cdn.spectora.com"
MAX_PHOTO_BYTES = 20 * MEGABYTE
FETCH_TIMEOUT_SECONDS = 10.0
IMPORT_BUDGET_SECONDS = 30.0
PARALLEL_FETCHES = 8

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
}


@dataclass(frozen=True)
class PhotoCopy:
    stored_path: str | None = None
    problem: str | None = None


class _Refused(Exception):
    """A photo that will not be copied, with the reason shown in the report."""


def is_fetchable(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.hostname == PHOTO_HOST
        and port in (None, 443)
        and parts.username is None
        and parts.password is None
    )


class SupabaseStorage:
    """The few Supabase Storage calls the importer needs, made with the server's secret key."""

    def __init__(self, client: httpx.Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def connect(cls, supabase_url: str, secret_key: str, bucket: str) -> "SupabaseStorage":
        client = httpx.Client(
            base_url=supabase_url.rstrip("/"), headers={"apikey": secret_key}, timeout=30.0
        )
        return cls(client, bucket)

    def close(self) -> None:
        self._client.close()

    def put(self, key: str, data: bytes, content_type: str) -> None:
        response = self._client.post(
            f"/storage/v1/object/{quote(self._bucket)}/{quote(key)}",
            content=data,
            headers={"content-type": content_type, "x-upsert": "true"},
        )
        response.raise_for_status()

    def ensure_bucket(self) -> bool:
        """Create the public photo bucket if it does not exist. True if it was created."""
        if self._client.get(f"/storage/v1/bucket/{quote(self._bucket)}").is_success:
            return False
        response = self._client.post(
            "/storage/v1/bucket", json={"id": self._bucket, "name": self._bucket, "public": True}
        )
        response.raise_for_status()
        return True


class PhotoCopier:
    def __init__(self, fetcher: httpx.Client, storage: SupabaseStorage) -> None:
        self._fetcher = fetcher
        self._storage = storage

    @classmethod
    def connect(cls, storage: SupabaseStorage) -> "PhotoCopier":
        fetcher = httpx.Client(follow_redirects=False, timeout=FETCH_TIMEOUT_SECONDS)
        return cls(fetcher, storage)

    def close(self) -> None:
        self._fetcher.close()
        self._storage.close()

    def copy_all(self, urls: Iterable[str]) -> dict[str, PhotoCopy]:
        """Copy each distinct URL once, in parallel, within the import's time budget."""
        unique = list(dict.fromkeys(url for url in urls if url))
        if not unique:
            return {}
        executor = ThreadPoolExecutor(max_workers=PARALLEL_FETCHES)
        futures = {executor.submit(self._copy, url): url for url in unique}
        done, _ = wait(futures, timeout=IMPORT_BUDGET_SECONDS)
        executor.shutdown(wait=False, cancel_futures=True)
        late = PhotoCopy(problem="it was not reached within the import's time limit")
        return {url: future.result() if future in done else late for future, url in futures.items()}

    def _copy(self, url: str) -> PhotoCopy:
        try:
            data, content_type = self._fetch(url)
            key = hashlib.sha256(data).hexdigest() + EXTENSIONS.get(content_type, "")
            self._storage.put(key, data, content_type)
            return PhotoCopy(stored_path=key)
        except _Refused as refused:
            return PhotoCopy(problem=str(refused))
        except httpx.HTTPStatusError as error:
            return PhotoCopy(problem=f"storage refused it (HTTP {error.response.status_code})")
        except httpx.HTTPError as error:
            return PhotoCopy(problem=f"the download failed ({type(error).__name__})")

    def _fetch(self, url: str) -> tuple[bytes, str]:
        if not is_fetchable(url):
            raise _Refused(f"only https addresses on {PHOTO_HOST} are fetched")
        with self._fetcher.stream("GET", url) as response:
            if response.is_redirect:
                raise _Refused(f"the server redirected it elsewhere (HTTP {response.status_code})")
            if response.status_code != 200:
                raise _Refused(f"the server answered HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if not content_type.startswith("image/"):
                raise _Refused(f"it is not an image ({content_type or 'no content type'})")
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > MAX_PHOTO_BYTES:
                raise _Refused(f"it is larger than {MAX_PHOTO_BYTES // MEGABYTE} MB")
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_PHOTO_BYTES:
                    raise _Refused(f"it is larger than {MAX_PHOTO_BYTES // MEGABYTE} MB")
                chunks.append(chunk)
        return b"".join(chunks), content_type


def configured_storage(settings: Settings) -> SupabaseStorage | None:
    """Storage from the environment, or None when it is not set up."""
    if settings.supabase_url is None or settings.supabase_secret_key is None:
        return None
    return SupabaseStorage.connect(
        settings.supabase_url, settings.supabase_secret_key, settings.photo_bucket
    )


def configured_copier(settings: Settings) -> PhotoCopier | None:
    storage = configured_storage(settings)
    return PhotoCopier.connect(storage) if storage else None


def public_url(settings: Settings, stored_path: str) -> str | None:
    """Where the browser loads a stored copy from. The bucket is public."""
    if settings.supabase_url is None:
        return None
    base = settings.supabase_url.rstrip("/")
    return f"{base}/storage/v1/object/public/{quote(settings.photo_bucket)}/{quote(stored_path)}"


def is_spectora_hosted(url: str) -> bool:
    try:
        return urlsplit(url).hostname == PHOTO_HOST
    except ValueError:
        return False


def inline_image_issues(template: ParsedTemplate, columns: ColumnMap) -> list[Issue]:
    """Images inside comment text that Spectora hosts (rule PH3). Only Default Photos are copied,
    because copying these would mean rewriting the stored text, which the importer never does."""
    issues = []
    for comment in template.comments():
        hosted = [url for url in image_sources(comment.body_html) if is_spectora_hosted(url)]
        if hosted:
            many = len(hosted) > 1
            what = f"{len(hosted)} images" if many else "an image"
            fate = (
                "They were not copied, so they stop" if many else "It was not copied, so it stops"
            )
            issues.append(
                Issue(
                    IssueKind.INLINE_IMAGE_NOT_COPIED,
                    Severity.WARNING,
                    f"'{comment.name}' shows {what} inside its text from Spectora's servers. "
                    f"{fate} working if the Spectora account closes.",
                    Scope.COMMENT,
                    comment.row,
                    columns.letter("comment_text"),
                )
            )
    return issues


def photo_urls(template: ParsedTemplate) -> list[str]:
    return [photo.url for comment in template.comments() for photo in comment.photos if photo.url]


def photo_issues(
    template: ParsedTemplate, columns: ColumnMap, copies: dict[str, PhotoCopy] | None
) -> list[Issue]:
    """One issue per photo that was not copied. `copies` is None when storage is not set up."""
    urls = photo_urls(template)
    if copies is None:
        if not urls:
            return []
        return [
            Issue(
                IssueKind.PHOTO_FETCH_FAILED,
                Severity.WARNING,
                f"Photo storage is not configured, so {len(urls)} default photos were not "
                "copied. Their Spectora addresses are kept, and stop working if the Spectora "
                "account closes.",
            )
        ]
    issues = []
    for comment in template.comments():
        for photo in comment.photos:
            copy = copies.get(photo.url)
            if not photo.url or copy is None or copy.problem is None:
                continue
            issues.append(
                Issue(
                    IssueKind.PHOTO_FETCH_FAILED,
                    Severity.WARNING,
                    f"Default Photo {photo.slot} on '{comment.name}' was not copied because "
                    f"{copy.problem}. Its Spectora address is kept.",
                    Scope.COMMENT,
                    comment.row,
                    columns.letter(f"photo_{photo.slot}"),
                )
            )
    return issues
