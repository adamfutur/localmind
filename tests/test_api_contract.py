"""API contract smoke tests that do not load models or call providers."""

from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)


def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "LocalMind Backend is running"
    assert "data_dir" in body


def test_search_requires_query():
    assert client.get("/api/search").status_code == 422
    assert client.get("/api/search?q=").status_code == 422


def test_ask_rejects_invalid_questions():
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 2001}).status_code == 422
