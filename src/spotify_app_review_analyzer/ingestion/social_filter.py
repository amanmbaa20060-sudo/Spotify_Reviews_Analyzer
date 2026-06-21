from __future__ import annotations

import re
from typing import Any

# Spotify-relevant keywords and hashtags for social noise reduction (Phase 5).
SPOTIFY_KEYWORDS: tuple[str, ...] = (
    "spotify",
    "#spotify",
    "discover weekly",
    "release radar",
    "spotify wrapped",
    "spotify playlist",
    "spotify premium",
    "spotify free",
    "spotify app",
    "daylist",
    "blend",
    "dj ",
    "music discovery",
    "recommendation",
)

SPOTIFY_HASHTAGS: tuple[str, ...] = (
    "#spotify",
    "#spotifyplaylist",
    "#spotifyplaylists",
    "#musicdiscovery",
    "#newmusic",
)

_OFF_TOPIC_MARKERS: tuple[str, ...] = (
    "apple music only",
    "youtube music",
    "tidal is better",
    "amazon music",
    "crypto",
    "nft",
    "giveaway",
)


def strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def is_spotify_relevant(text: str, *, from_hashtag: str | None = None) -> bool:
    tag = (from_hashtag or "").lower().lstrip("#")
    if tag in {"spotify", "spotifyplaylist", "spotifyplaylists", "musicdiscovery", "newmusic"}:
        return True
    lowered = strip_html(text).lower()
    if any(marker in lowered for marker in _OFF_TOPIC_MARKERS):
        return False
    if any(keyword in lowered for keyword in SPOTIFY_KEYWORDS):
        return True
    if any(tag in lowered for tag in SPOTIFY_HASHTAGS):
        return True
    # Music-context fallback when post is substantive.
    music_terms = ("playlist", "album", "song", "artist", "listen", "stream")
    return any(term in lowered for term in music_terms) and "spotify" in lowered


def engagement_score(*, likes: int = 0, reposts: int = 0, replies: int = 0, views: int = 0) -> float:
    return float(likes + reposts * 2 + replies + views * 0.01)


def build_engagement_metadata(
    *,
    likes: int = 0,
    reposts: int = 0,
    replies: int = 0,
    views: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = engagement_score(likes=likes, reposts=reposts, replies=replies, views=views or 0)
    metadata: dict[str, Any] = {
        "channel_type": "social",
        "likes": likes,
        "reposts": reposts,
        "shares": reposts,
        "replies": replies,
        "engagement_score": round(score, 2),
    }
    if views is not None:
        metadata["views"] = views
    if extra:
        metadata.update(extra)
    return metadata


def mark_viral_outliers(items: list[dict[str, Any]], *, percentile: float = 0.9) -> None:
    """Tag items in-place with viral=True when engagement is a high outlier."""
    scores = [float(item.get("engagement_score", 0)) for item in items]
    if not scores:
        return
    sorted_scores = sorted(scores)
    idx = min(len(sorted_scores) - 1, int(len(sorted_scores) * percentile))
    threshold = sorted_scores[idx]
    if threshold <= 0:
        threshold = max(scores)
    for item in items:
        item["viral"] = float(item.get("engagement_score", 0)) >= threshold and threshold > 0
        item["traffic_state"] = "viral" if item["viral"] else "steady_state"
