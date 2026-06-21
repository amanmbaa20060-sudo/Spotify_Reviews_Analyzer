from __future__ import annotations

import re
from dataclasses import dataclass

_SPAM_PATTERNS = (
    re.compile(r"(?i)click here"),
    re.compile(r"(?i)free\s+v-bucks"),
    re.compile(r"(?i)earn money fast"),
    re.compile(r"http[s]?://\S{60,}"),
)


@dataclass(frozen=True)
class QualityResult:
    score: float
    is_on_topic: bool
    skip_reason: str | None = None


def score_quality(text: str, *, min_length: int = 15) -> QualityResult:
    stripped = text.strip()
    if not stripped:
        return QualityResult(score=0.0, is_on_topic=False, skip_reason="empty_text")

    if len(stripped) < min_length:
        return QualityResult(score=0.1, is_on_topic=False, skip_reason="too_short")

    for pattern in _SPAM_PATTERNS:
        if pattern.search(stripped):
            return QualityResult(score=0.0, is_on_topic=False, skip_reason="spam")

    lower = stripped.lower()
    spotify_markers = ("spotify", "playlist", "discover", "recommend", "music", "song", "album")
    on_topic = any(marker in lower for marker in spotify_markers) or len(stripped) >= 40

    length_score = min(len(stripped) / 200.0, 1.0)
    topic_score = 1.0 if on_topic else 0.4
    score = round(0.6 * length_score + 0.4 * topic_score, 3)

    if not on_topic and len(stripped) < 80:
        return QualityResult(score=score, is_on_topic=False, skip_reason="off_topic")

    return QualityResult(score=score, is_on_topic=True)
