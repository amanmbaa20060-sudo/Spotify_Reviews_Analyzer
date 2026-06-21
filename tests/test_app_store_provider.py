from __future__ import annotations

from spotify_app_review_analyzer.ingestion.sources.app_store import AppStoreProvider

SAMPLE_PAYLOAD = {
    "feed": {
        "entry": [
            {
                "author": {"name": {"label": "user1"}},
                "content": {"label": "Love discovering new music on Spotify"},
                "id": {"label": "review-1"},
                "im:rating": {"label": "5"},
                "im:version": {"label": "8.9.0"},
                "title": {"label": "Great"},
                "updated": {"label": "Tue, 17 Jun 2025 12:00:00 GMT"},
            },
            {"title": {"label": "Spotify"}, "id": {"label": "app-info"}},
        ]
    }
}


class FakeHttp:
    def __init__(self) -> None:
        self.calls = 0

    def get_json(self, url: str, params=None):
        self.calls += 1
        if self.calls > 1:
            return {"feed": {"entry": []}}
        return SAMPLE_PAYLOAD


def test_app_store_normalizes_reviews() -> None:
    provider = AppStoreProvider(http_client=FakeHttp())
    reviews = provider.fetch(limit=10)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source_key == "app_store"
    assert review.rating == 5
    assert review.published_at is not None
    assert "discovering" in review.text.lower()


def test_app_store_handles_malformed_payload() -> None:
    class BadHttp:
        def get_json(self, url: str, params=None):
            return "not-json-structure"

    provider = AppStoreProvider(http_client=BadHttp())
    reviews = provider.fetch(limit=10)
    assert reviews == []


def test_app_store_parses_iso8601_updated() -> None:
    payload = {
        "feed": {
            "entry": [
                {
                    "author": {"name": {"label": "user2"}},
                    "content": {"label": "Great discovery features"},
                    "id": {"label": "review-iso"},
                    "im:rating": {"label": "4"},
                    "im:version": {"label": "9.0.0"},
                    "title": {"label": "Nice"},
                    "updated": {"label": "2026-06-20T00:25:12-07:00"},
                }
            ]
        }
    }

    class IsoHttp:
        def __init__(self) -> None:
            self.calls = 0

        def get_json(self, url: str, params=None):
            self.calls += 1
            if self.calls > 1:
                return {"feed": {"entry": []}}
            return payload

    provider = AppStoreProvider(http_client=IsoHttp())
    reviews = provider.fetch(limit=10)
    assert len(reviews) == 1
    assert reviews[0].published_at is not None
    assert reviews[0].published_at.year == 2026
