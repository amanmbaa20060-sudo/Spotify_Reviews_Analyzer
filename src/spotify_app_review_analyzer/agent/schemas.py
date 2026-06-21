from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from spotify_app_review_analyzer.analytics.schemas import RQBriefing, RQSection


@dataclass
class ToolCallRecord:
    tool: str
    input: dict[str, Any]
    output_summary: str


@dataclass
class AgentAnswer:
    answer_text: str
    rq_id: str | None
    citations: list[str] = field(default_factory=list)
    confidence_flags: list[str] = field(default_factory=list)
    guardrail_passed: bool = True
    guardrail_notes: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    briefing_context: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    used_groq: bool = False


GOLDEN_QUESTIONS: dict[str, str] = {
    "rq1": "Why do users struggle to discover new music?",
    "rq2": "What are the most common frustrations with recommendations?",
    "rq3": "What listening behaviors are users trying to achieve?",
    "rq4": "What causes users to repeat the same content?",
    "rq5": "Which segments have different discovery challenges?",
    "rq6": "What unmet needs appear consistently?",
}

RQ_KEYWORDS: dict[str, list[str]] = {
    "rq1": ["discover", "discovery", "find new music", "struggle", "browse"],
    "rq2": ["recommendation", "frustrat", "stale", "repetitive", "discover weekly"],
    "rq3": ["listening behavior", "trying to achieve", "intent", "goal", "behavior"],
    "rq4": ["repeat", "repetition", "same content", "same songs", "comfort"],
    "rq5": ["segment", "ios", "android", "premium", "free tier", "different challenges"],
    "rq6": ["unmet need", "consistent", "missing feature", "wish", "need"],
}


def infer_rq_id(question: str) -> str | None:
    lowered = question.lower()
    for rq_id, keywords in RQ_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return rq_id
    match = re.search(r"\brq([1-6])\b", lowered)
    if match:
        return f"rq{match.group(1)}"
    return None


def compact_briefing_section(section: RQSection) -> dict[str, Any]:
    return {
        "rq_id": section.rq_id,
        "label": section.label,
        "review_count": section.review_count,
        "readiness": section.readiness,
        "avg_confidence": section.avg_confidence,
        "top_themes": [theme.to_dict() for theme in section.top_themes],
        "sentiment_mix": section.sentiment_mix,
        "source_breakdown": section.source_breakdown,
        "segment_signals": [signal.to_dict() for signal in section.segment_signals],
        "cross_source_themes": section.cross_source_themes,
        "exemplar_citations": [citation.to_dict() for citation in section.exemplar_citations],
    }


def briefing_to_context_text(briefing: RQBriefing, *, rq_id: str | None = None) -> str:
    sections = briefing.sections
    if rq_id:
        sections = [section for section in sections if section.rq_id == rq_id]
    payload = {
        "generated_at": briefing.generated_at,
        "taxonomy_version": briefing.taxonomy_version,
        "sections": [compact_briefing_section(section) for section in sections],
    }
    return json.dumps(payload, indent=2)


def collect_allowed_review_ids(briefing: RQBriefing, tool_results: list[dict[str, Any]]) -> set[str]:
    allowed: set[str] = set()
    for section in briefing.sections:
        for citation in section.exemplar_citations:
            allowed.add(citation.review_id)
    for result in tool_results:
        for hit in result.get("results", []):
            review_id = hit.get("review_id")
            if review_id:
                allowed.add(str(review_id))
    return allowed


def collect_citation_confidence(briefing: RQBriefing) -> dict[str, float | None]:
    confidence: dict[str, float | None] = {}
    for section in briefing.sections:
        for citation in section.exemplar_citations:
            confidence[citation.review_id] = citation.confidence
    return confidence
