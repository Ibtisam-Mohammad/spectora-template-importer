import hashlib

import httpx
import pytest

from app.services.photos import (
    MAX_PHOTO_BYTES,
    PhotoCopier,
    PhotoCopy,
    SupabaseStorage,
    is_fetchable,
    photo_issues,
)
from app.spectora.model import IssueKind, Scope
from tests.helpers import analysed
from tests.paths import PRIMARY, PROBE_HTML

PHOTO = "https://cdn.spectora.com/default_photos/images/1/original/a.jpg?1"
JPEG = b"\xff\xd8\xff\xe0 not really a jpeg"


class FakeCdn:
    """Answers photo requests from a table and records every request it receives."""

    def __init__(self, responses: dict[str, httpx.Response]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requested.append(str(request.url))
        return self.responses.get(str(request.url), httpx.Response(404))


class FakeStorage:
    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.objects: dict[str, tuple[bytes, str]] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        key = request.url.path.rsplit("/", 1)[-1]
        self.objects[key] = (request.content, request.headers["content-type"])
        return httpx.Response(self.status)


def copier(cdn: FakeCdn, storage: FakeStorage | None = None) -> PhotoCopier:
    storage = storage or FakeStorage()
    fetcher = httpx.Client(transport=httpx.MockTransport(cdn), follow_redirects=False)
    store = httpx.Client(transport=httpx.MockTransport(storage), base_url="https://x.supabase.co")
    return PhotoCopier(fetcher, SupabaseStorage(store, "template-photos"))


def image(data: bytes = JPEG, content_type: str = "image/jpeg") -> httpx.Response:
    return httpx.Response(200, content=data, headers={"content-type": content_type})


@pytest.mark.rule("PH2")
def test_a_photo_is_stored_under_the_hash_of_its_bytes():
    storage = FakeStorage()
    copies = copier(FakeCdn({PHOTO: image()}), storage).copy_all([PHOTO])
    key = hashlib.sha256(JPEG).hexdigest() + ".jpg"
    assert copies == {PHOTO: PhotoCopy(stored_path=key)}
    assert storage.objects[key] == (JPEG, "image/jpeg")


@pytest.mark.rule("PH2")
def test_the_same_url_is_fetched_once():
    cdn = FakeCdn({PHOTO: image()})
    copier(cdn).copy_all([PHOTO, PHOTO, ""])
    assert cdn.requested == [PHOTO]


@pytest.mark.rule("PH2")
@pytest.mark.parametrize(
    "url",
    [
        "http://cdn.spectora.com/a.jpg",
        "https://evil.example/a.jpg",
        "https://cdn.spectora.com.evil.example/a.jpg",
        "https://user@cdn.spectora.com/a.jpg",
        "https://cdn.spectora.com:8443/a.jpg",
        "https://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
    ],
)
def test_only_https_on_spectoras_cdn_is_requested(url):
    cdn = FakeCdn({})
    copies = copier(cdn).copy_all([url])
    assert not is_fetchable(url)
    assert cdn.requested == []
    assert copies[url].stored_path is None
    assert "cdn.spectora.com" in copies[url].problem


@pytest.mark.rule("PH2")
def test_redirects_are_not_followed():
    cdn = FakeCdn({PHOTO: httpx.Response(302, headers={"location": "https://evil.example/"})})
    copies = copier(cdn).copy_all([PHOTO])
    assert cdn.requested == [PHOTO]
    assert "redirected" in copies[PHOTO].problem


@pytest.mark.rule("PH2")
@pytest.mark.parametrize(
    ("response", "problem"),
    [
        (httpx.Response(404), "HTTP 404"),
        (image(content_type="text/html"), "not an image"),
        (image(data=b"x" * (MAX_PHOTO_BYTES + 1)), "larger than"),
    ],
)
def test_a_photo_that_cannot_be_copied_says_why(response, problem):
    copies = copier(FakeCdn({PHOTO: response})).copy_all([PHOTO])
    assert copies[PHOTO].stored_path is None
    assert problem in copies[PHOTO].problem


@pytest.mark.rule("PH2")
def test_a_storage_failure_is_a_problem_not_a_crash():
    copies = copier(FakeCdn({PHOTO: image()}), FakeStorage(status=403)).copy_all([PHOTO])
    assert copies[PHOTO] == PhotoCopy(problem="storage refused it (HTTP 403)")


@pytest.mark.rule("PH2", "R6")
def test_each_failed_photo_is_an_issue_naming_its_row_and_column():
    analysis = analysed(PROBE_HTML)
    urls = {p.url for c in analysis.template.comments() for p in c.photos}
    copies = {url: PhotoCopy(problem="the server answered HTTP 404") for url in urls}
    issues = photo_issues(analysis.template, analysis.columns, copies)
    photos = [(c, p) for c in analysis.template.comments() for p in c.photos]
    assert len(issues) == len(photos)
    for issue, (comment, photo) in zip(issues, photos, strict=True):
        assert issue.kind is IssueKind.PHOTO_FETCH_FAILED
        assert issue.scope is Scope.COMMENT
        assert issue.row == comment.row
        assert issue.column == analysis.columns.letter(f"photo_{photo.slot}")


@pytest.mark.rule("PH2")
def test_unconfigured_storage_is_one_warning_and_no_photos_means_none():
    probe = analysed(PROBE_HTML)
    [issue] = photo_issues(probe.template, probe.columns, None)
    assert issue.kind is IssueKind.PHOTO_FETCH_FAILED
    assert issue.scope is Scope.FILE
    primary = analysed(PRIMARY)
    assert photo_issues(primary.template, primary.columns, None) == []
