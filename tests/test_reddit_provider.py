from __future__ import annotations

from spotify_app_review_analyzer.ingestion.sources.reddit import RedditProvider

SAMPLE_PAYLOAD = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc123",
                    "title": "Can't find new music",
                    "selftext": "Discover weekly feels stale lately",
                    "author": "reddit_user",
                    "created_utc": 1718611200,
                    "permalink": "/r/spotify/comments/abc123/test/",
                    "score": 10,
                    "num_comments": 2,
                }
            }
        ],
        "after": None,
    }
}


class FakeHttp:
    def get_json(self, url: str, params=None):
        return SAMPLE_PAYLOAD


def test_reddit_normalizes_posts() -> None:
    provider = RedditProvider(http_client=FakeHttp())
    reviews = provider.fetch(limit=5)
    assert len(reviews) == 3  # one per configured subreddit
    review = reviews[0]
    assert review.source_key == "reddit"
    assert review.title == "Can't find new music"
    assert review.published_at is not None
    assert "discover weekly" in review.text.lower()
