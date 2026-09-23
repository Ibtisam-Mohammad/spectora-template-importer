from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_answers():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_library_page_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Templates" in response.text
