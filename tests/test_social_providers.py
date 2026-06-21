from __future__ import annotations

from spotify_app_review_analyzer.ingestion.sources.bluesky import BlueskyProvider
from spotify_app_review_analyzer.ingestion.sources.mastodon import MastodonProvider
from spotify_app_review_analyzer.ingestion.social_filter import is_spotify_relevant

MASTODON_TIMELINE_SAMPLE = [
    {
        "id": "12345",
        "content": "<p>Spotify Discover Weekly feels stale this week</p>",
        "created_at": "2026-06-18T12:00:00.000Z",
        "favourites_count": 12,
        "reblogs_count": 3,
        "replies_count": 1,
        "url": "https://mastodon.social/@user/12345",
        "visibility": "public",
        "account": {"acct": "musicfan", "username": "musicfan"},
    },
    {
        "id": "99999",
        "content": "<p>Random crypto giveaway not about music</p>",
        "created_at": "2026-06-18T12:01:00.000Z",
        "favourites_count": 0,
        "reblogs_count": 0,
        "replies_count": 0,
        "url": "https://mastodon.social/@spam/99999",
        "visibility": "public",
        "account": {"acct": "spam", "username": "spam"},
    },
]

BLUESKY_SAMPLE = {
    "posts": [
        {
            "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
            "cid": "bafytest",
            "indexedAt": "2026-06-18T12:00:00.000Z",
            "likeCount": 20,
            "repostCount": 5,
            "replyCount": 2,
            "author": {"handle": "listener.bsky.social"},
            "record": {
                "text": "Spotify recommendations keep repeating the same artists #spotify",
                "createdAt": "2026-06-18T12:00:00.000Z",
            },
        }
    ],
    "cursor": None,
}


class FakeHttp:
    def __init__(self, payload):
        self.payload = payload
        self.headers: dict[str, str] = {}
        self.calls = 0

    def get_json(self, url: str, params=None):
        self.calls += 1
        return self.payload


def test_social_filter_accepts_spotify_content() -> None:
    assert is_spotify_relevant("Love my Spotify Discover Weekly playlist")


def test_social_filter_accepts_hashtag_timeline_posts() -> None:
    assert is_spotify_relevant("Great track today", from_hashtag="spotify")


def test_social_filter_rejects_off_topic() -> None:
    assert not is_spotify_relevant("Crypto giveaway click here")


def test_mastodon_normalizes_posts() -> None:
    provider = MastodonProvider(http_client=FakeHttp(MASTODON_TIMELINE_SAMPLE))
    reviews = provider.fetch(limit=10)
    assert len(reviews) == 2
    review = reviews[0]
    assert review.source_key == "mastodon"
    assert "discover weekly" in review.text.lower()
    assert review.extra_metadata["likes"] == 12
    assert review.extra_metadata["channel_type"] == "social"


def test_bluesky_normalizes_posts(monkeypatch) -> None:
    monkeypatch.setattr(
        "spotify_app_review_analyzer.ingestion.sources.bluesky.settings.bluesky_handle",
        None,
    )
    monkeypatch.setattr(
        "spotify_app_review_analyzer.ingestion.sources.bluesky.settings.bluesky_app_password",
        None,
    )
    provider = BlueskyProvider(http_client=FakeHttp(BLUESKY_SAMPLE))
    provider._access_token = ""
    reviews = provider._search("spotify", limit=10, seen_uris=set())
    assert len(reviews) == 1
    review = reviews[0]
    assert review.source_key == "bluesky"
    assert review.extra_metadata["reposts"] == 5
