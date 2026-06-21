from __future__ import annotations

import httpx
import pytest

from spotify_app_review_analyzer.ingestion.http import HttpClient


def test_http_client_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict | None = None) -> None:
            self.status_code = status_code
            self._payload = payload or {"ok": True}
            self.request = httpx.Request("GET", "https://example.com")

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("error", request=self.request, response=self)

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url: str, params=None) -> FakeResponse:
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeResponse(429)
            return FakeResponse(200, {"ok": True})

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr("spotify_app_review_analyzer.ingestion.http.time.sleep", lambda _: None)

    client = HttpClient(max_retries=2, backoff_seconds=0.01)
    result = client.get_json("https://example.com")
    assert result == {"ok": True}
    assert calls["count"] == 2
