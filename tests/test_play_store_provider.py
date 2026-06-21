from __future__ import annotations

from datetime import datetime

from spotify_app_review_analyzer.ingestion.sources.play_store import PlayStoreProvider


def fake_fetch(app_id, lang, country, sort, count, continuation_token=None):
    if continuation_token is not None:
        return [], None
    return (
        [
            {
                "reviewId": "gp-1",
                "userName": "android_user",
                "content": "Recommendations repeat too often",
                "score": 3,
                "at": datetime(2025, 6, 17, 10, 0, 0),
                "appVersion": "8.9.0",
                "thumbsUpCount": 2,
            }
        ],
        None,
    )


def test_play_store_normalizes_reviews() -> None:
    provider = PlayStoreProvider(fetch_fn=fake_fetch)
    reviews = provider.fetch(limit=5)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source_key == "play_store"
    assert review.rating == 3
    assert review.published_at is not None
    assert review.external_id == "gp-1"
