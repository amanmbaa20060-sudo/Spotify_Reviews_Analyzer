from __future__ import annotations

from fastapi.testclient import TestClient

from spotify_app_review_analyzer.api.app import app


def test_health() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"

