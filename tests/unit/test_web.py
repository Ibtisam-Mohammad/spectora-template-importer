import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

LIMIT = config.MEGABYTE * 4


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config.get_settings.cache_clear()
    yield TestClient(app)
    config.get_settings.cache_clear()


def upload(client, data: bytes, filename: str = "export.xls"):
    return client.post("/import", files={"file": (filename, data, "application/vnd.ms-excel")})


@pytest.mark.rule("F9")
def test_an_upload_over_the_limit_gets_a_clear_message(client):
    response = upload(client, b"x" * (LIMIT + 1))
    assert response.status_code == 413
    assert "larger than 4 MB" in response.text


@pytest.mark.rule("F9")
def test_an_upload_at_the_limit_is_not_refused_for_size(client):
    response = upload(client, b"x" * LIMIT)
    assert response.status_code == 503
    assert "The database is not configured." in response.text


@pytest.mark.rule("F9")
def test_the_form_checks_the_size_before_sending(client):
    page = client.get("/").text
    assert f'data-max-bytes="{LIMIT}"' in page
    assert "app.js" in page


def test_an_upload_without_a_file_asks_for_one(client):
    response = client.post("/import", data={})
    assert response.status_code == 400
    assert "Choose a Spectora export" in response.text


def test_without_a_database_the_library_says_so(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "database is not configured" in response.text


def test_without_a_database_the_editor_says_so(client):
    response = client.get("/t/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 503
    assert "DATABASE_URL" in response.text
