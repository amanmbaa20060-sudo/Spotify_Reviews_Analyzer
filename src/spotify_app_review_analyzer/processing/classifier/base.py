from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassificationResult:
    sentiment: str
    sentiment_score: float
    themes: list[str] = field(default_factory=list)
    research_questions: list[str] = field(default_factory=list)
    listening_intent: list[str] = field(default_factory=list)
    confidence: float = 0.0
