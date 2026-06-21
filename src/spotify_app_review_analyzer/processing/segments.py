from __future__ import annotations

import re

_PLATFORM_FROM_SOURCE = {
    "app_store": "segment.platform.ios",
    "play_store": "segment.platform.android",
}

_TIER_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bfree\b.*\b(ads|shuffle|skip)\b", re.I), "segment.tier.free"),
    (re.compile(r"\bpremium\b", re.I), "segment.tier.premium"),
    (re.compile(r"\bads?\b", re.I), "segment.tier.free"),
)

_TENURE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(years?|long time|since launch)\b", re.I), "segment.tenure.long_time"),
    (re.compile(r"\bnew user\b|\bjust (started|joined)\b", re.I), "segment.tenure.new"),
)


def infer_segments(text: str, *, source_key: str | None = None) -> list[str]:
    segments: list[str] = []
    if source_key and source_key in _PLATFORM_FROM_SOURCE:
        segments.append(_PLATFORM_FROM_SOURCE[source_key])

    for pattern, tag in _TIER_PATTERNS:
        if pattern.search(text):
            segments.append(tag)

    for pattern, tag in _TENURE_PATTERNS:
        if pattern.search(text):
            segments.append(tag)

    # dedupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for tag in segments:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique
