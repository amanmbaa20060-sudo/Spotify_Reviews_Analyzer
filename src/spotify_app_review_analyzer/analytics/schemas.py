from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RQ_IDS: tuple[str, ...] = ("rq1", "rq2", "rq3", "rq4", "rq5", "rq6")


@dataclass(frozen=True)
class ExemplarCitation:
    review_id: str
    source_key: str
    sentiment: str | None
    confidence: float | None
    snippet: str
    theme_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeCount:
    theme_id: str
    label: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SegmentSignal:
    description: str
    theme_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RQSection:
    rq_id: str
    label: str
    review_count: int
    top_themes: list[ThemeCount]
    sentiment_mix: dict[str, float]
    source_breakdown: dict[str, float]
    segment_signals: list[SegmentSignal]
    cross_source_themes: list[str]
    exemplar_citations: list[ExemplarCitation]
    readiness: str
    avg_confidence: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rq_id": self.rq_id,
            "label": self.label,
            "review_count": self.review_count,
            "top_themes": [t.to_dict() for t in self.top_themes],
            "sentiment_mix": self.sentiment_mix,
            "source_breakdown": self.source_breakdown,
            "segment_signals": [s.to_dict() for s in self.segment_signals],
            "cross_source_themes": self.cross_source_themes,
            "exemplar_citations": [e.to_dict() for e in self.exemplar_citations],
            "readiness": self.readiness,
            "avg_confidence": self.avg_confidence,
        }


@dataclass
class RQBriefing:
    generated_at: str
    taxonomy_version: str
    model_version: str | None
    total_processed_reviews: int
    sections: list[RQSection] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "taxonomy_version": self.taxonomy_version,
            "model_version": self.model_version,
            "total_processed_reviews": self.total_processed_reviews,
            "sections": [section.to_dict() for section in self.sections],
            "verification": self.verification,
        }
