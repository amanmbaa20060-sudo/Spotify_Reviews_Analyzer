from __future__ import annotations

import re
from dataclasses import dataclass, field

from spotify_app_review_analyzer.core.settings import settings

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

OUT_OF_SCOPE_PATTERNS = [
    r"\brevenue\b",
    r"\bstock price\b",
    r"\bmarket cap\b",
    r"\bquarterly earnings\b",
    r"\bwho is the ceo\b",
    r"\bcompetitor revenue\b",
]

IN_SCOPE_HINTS = [
    "spotify",
    "discover",
    "discovery",
    "recommend",
    "playlist",
    "music",
    "review",
    "app store",
    "play store",
    "reddit",
    "mastodon",
    "bluesky",
    "social",
    "listening",
    "unmet",
    "need",
    "needs",
    "consistently",
    "behavior",
    "segment",
    "repeat",
    "frustrat",
    "rq1",
    "rq2",
    "rq3",
    "rq4",
    "rq5",
    "rq6",
]

OUT_OF_SCOPE_SOURCE_PATTERNS = [
    r"\btiktok\b",
    r"\btwitter\b",
    r"\bx\.com\b",
    r"\binstagram\b",
    r"\byoutube\b",
    r"\bfacebook\b",
]


@dataclass
class GuardrailResult:
    passed: bool
    notes: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence_flags: list[str] = field(default_factory=list)


def is_in_scope(question: str) -> tuple[bool, str | None]:
    lowered = question.lower()
    if any(re.search(pattern, lowered) for pattern in OUT_OF_SCOPE_PATTERNS):
        return False, "Question appears out of scope for the review corpus"
    if any(re.search(pattern, lowered) for pattern in OUT_OF_SCOPE_SOURCE_PATTERNS):
        return False, "Requested source is not in the ingested review corpus"
    if any(hint in lowered for hint in IN_SCOPE_HINTS):
        return True, None
    # Allow generic research phrasing
    if "user" in lowered or "users" in lowered:
        return True, None
    return False, "Question does not appear related to Spotify app review analysis"


def extract_citations(text: str) -> list[str]:
    return list(dict.fromkeys(UUID_PATTERN.findall(text)))


def validate_grounding(
    answer_text: str,
    *,
    allowed_review_ids: set[str],
    citation_confidence: dict[str, float | None],
) -> GuardrailResult:
    notes: list[str] = []
    confidence_flags: list[str] = []
    citations = extract_citations(answer_text)

    if not citations:
        notes.append("No review_id citations found in response")
        return GuardrailResult(passed=False, notes=notes, citations=citations)

    unknown = [cid for cid in citations if cid not in allowed_review_ids]
    if unknown:
        notes.append(f"Citations not in evidence pack: {', '.join(unknown[:5])}")

    threshold = settings.agent_low_confidence_threshold
    for review_id in citations:
        confidence = citation_confidence.get(review_id)
        if confidence is not None and confidence < threshold:
            confidence_flags.append(
                f"Low-confidence citation `{review_id}` (confidence={confidence:.2f})"
            )

    passed = not unknown
    return GuardrailResult(
        passed=passed,
        notes=notes,
        citations=citations,
        confidence_flags=confidence_flags,
    )


def truncate_context(text: str, *, max_tokens: int) -> str:
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n...[truncated]"


def insufficient_data_message(rq_id: str | None, review_count: int) -> str:
    target = rq_id or "this topic"
    return (
        f"Insufficient processed review evidence for {target} "
        f"(matched reviews: {review_count}). "
        "I cannot provide a grounded answer without more ingested data."
    )
