from __future__ import annotations

# ruff: noqa: E501
import re
from abc import ABC, abstractmethod

from spotify_app_review_analyzer.processing.classifier.base import ClassificationResult
from spotify_app_review_analyzer.taxonomy.loader import Taxonomy, load_taxonomy

_POSITIVE = re.compile(
    r"\b(love|great|awesome|amazing|excellent|perfect|best|enjoy|helpful|good)\b", re.I
)
_NEGATIVE = re.compile(
    r"\b(hate|terrible|awful|worst|bad|frustrat|annoy|broken|useless|disappoint|stale|repeat)\b",
    re.I,
)

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "rq1.entry_points.clarity": ("find new", "where to", "how do i", "can't find", "hard to find"),
    "rq1.overwhelm.choice_overload": ("too many", "overwhelming", "overload", "so much music"),
    "rq1.onboarding.discovery_features": ("discover weekly", "don't understand", "how to use", "onboarding"),
    "rq1.search.browse_friction": ("search", "browse", "genre", "category", "navigate"),
    "rq2.relevance.mismatch": ("irrelevant", "doesn't match", "not my taste", "wrong music", "bad recommendations"),
    "rq2.repetition.stale": ("repetitive", "same songs", "same artist", "stale", "repeat", "again and again"),
    "rq2.diversity.genre_stagnation": ("same genre", "narrow", "stuck in", "only plays", "one genre"),
    "rq2.control.lack_of_controls": ("control", "reset algorithm", "tune", "steer", "customize"),
    "rq3.intent.background": ("background", "while working", "passive", "hands free"),
    "rq3.intent.focus_workout": ("workout", "gym", "focus", "study", "concentration", "mood"),
    "rq3.intent.active_discovery": ("discover", "new music", "new artist", "explore", "find new"),
    "rq3.intent.artist_deep_dive": ("discography", "deep dive", "all songs by", "artist catalog"),
    "rq4.habit.comfort_listening": ("comfort", "familiar", "favorite playlist", "same playlist"),
    "rq4.friction.defaulting_to_known": ("default", "go back to", "saved songs", "liked songs only"),
    "rq4.trust.algorithm_fatigue": ("algorithm", "don't trust", "fatigue", "spotify knows"),
    "rq4.risk.wasting_time": ("waste time", "skip", "not worth", "disappointing recommendations"),
    "rq5.platform.android": ("android", "samsung", "pixel"),
    "rq5.platform.ios": ("iphone", "ios", "ipad", "apple"),
    "rq5.tier.free_vs_premium": ("free tier", "ads", "premium", "paywall", "shuffle only", "subscription"),
    "rq6.unmet.freshness": ("fresh", "new releases", "more variety", "update recommendations"),
    "rq6.unmet.transparency": ("why recommend", "explain", "transparent", "understand why"),
    "rq6.unmet.effortless": ("effortless", "easy to discover", "without searching", "automatic"),
}

INTENT_THEMES = {
    "rq3.intent.background",
    "rq3.intent.focus_workout",
    "rq3.intent.active_discovery",
    "rq3.intent.artist_deep_dive",
}


class Classifier(ABC):
    @abstractmethod
    def classify(self, text: str, *, rating: int | None = None) -> ClassificationResult:
        pass


class RuleBasedClassifier(Classifier):
    def __init__(self, taxonomy: Taxonomy | None = None) -> None:
        self.taxonomy = taxonomy or load_taxonomy()
        self._valid_theme_ids = {theme.id for theme in self.taxonomy.themes}

    def classify(self, text: str, *, rating: int | None = None) -> ClassificationResult:
        lower = text.lower()
        sentiment, sentiment_score = self._sentiment(lower, rating)
        themes = self._match_themes(lower)
        research_questions = sorted({theme_id.split(".")[0] for theme_id in themes})
        listening_intent = [t for t in themes if t in INTENT_THEMES]
        confidence = self._confidence(themes, sentiment_score)
        return ClassificationResult(
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            themes=themes,
            research_questions=research_questions,
            listening_intent=listening_intent,
            confidence=confidence,
        )

    def _sentiment(self, lower: str, rating: int | None) -> tuple[str, float]:
        pos = len(_POSITIVE.findall(lower))
        neg = len(_NEGATIVE.findall(lower))
        if rating is not None:
            if rating >= 4:
                pos += 2
            elif rating <= 2:
                neg += 2

        if pos > neg:
            score = min(0.55 + 0.1 * pos, 0.95)
            return "positive", round(score, 3)
        if neg > pos:
            score = min(0.55 + 0.1 * neg, 0.95)
            return "negative", round(-score, 3)
        if rating is not None and rating == 3:
            return "neutral", 0.0
        return "neutral", 0.0

    def _match_themes(self, lower: str) -> list[str]:
        matched: list[str] = []
        for theme_id, keywords in THEME_KEYWORDS.items():
            if theme_id not in self._valid_theme_ids:
                continue
            if any(keyword in lower for keyword in keywords):
                matched.append(theme_id)
        if not matched and "discover" in lower:
            matched.append("rq3.intent.active_discovery")
        if not matched and ("recommend" in lower or "algorithm" in lower):
            matched.append("rq2.relevance.mismatch")
        return matched[:5]

    def _confidence(self, themes: list[str], sentiment_score: float) -> float:
        base = 0.45 + min(len(themes), 3) * 0.12
        if sentiment_score != 0:
            base += 0.1
        return round(min(base, 0.92), 3)


def get_classifier(backend: str | None = None) -> Classifier:
    selected = backend or "rule"
    if selected == "rule":
        return RuleBasedClassifier()
    raise ValueError(f"Unsupported classifier backend: {selected}")
