from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from spotify_app_review_analyzer.analytics.aggregations import (
    AnalyzedReview,
    themes_for_rq,
)
from spotify_app_review_analyzer.analytics.schemas import RQSection
from spotify_app_review_analyzer.taxonomy.loader import Taxonomy, load_taxonomy


def _theme_meta(taxonomy: Taxonomy) -> dict[str, dict[str, str]]:
    return {
        theme.id: {"label": theme.label, "description": theme.description or theme.label}
        for theme in taxonomy.themes
    }


def _reviews_for_theme(reviews: list[AnalyzedReview], rq_id: str, theme_id: str) -> list[AnalyzedReview]:
    return [review for review in reviews if theme_id in themes_for_rq(review, rq_id)]


def _source_breakdown_for_theme(matching: list[AnalyzedReview]) -> dict[str, float]:
    if not matching:
        return {}
    counts = Counter(review.source_key for review in matching)
    total = sum(counts.values())
    return {source: round(count / total * 100, 1) for source, count in counts.most_common()}


def build_weighted_problem_analysis(
    section: RQSection,
    rq_reviews: list[AnalyzedReview],
    *,
    taxonomy: Taxonomy | None = None,
    max_factors: int = 6,
) -> dict[str, Any]:
    """Weighted root-cause breakdown for an RQ from theme + sentiment evidence."""
    taxonomy = taxonomy or load_taxonomy()
    meta = _theme_meta(taxonomy)

    if not section.top_themes or not rq_reviews:
        return {
            "summary": "Insufficient evidence for a detailed problem analysis.",
            "root_causes": [],
            "segment_factors": [],
            "negative_share": section.sentiment_mix.get("negative", 0.0),
            "review_count": section.review_count,
        }

    raw_scores: list[tuple[str, float, int, float, dict[str, float]]] = []
    for theme in section.top_themes:
        matching = _reviews_for_theme(rq_reviews, section.rq_id, theme.theme_id)
        mention_count = len(matching) or theme.count
        negative_count = sum(1 for review in matching if review.sentiment == "negative")
        negative_share = round(negative_count / mention_count * 100, 1) if mention_count else 0.0
        # Weight mentions and severity (negative share) together.
        raw_score = mention_count * (1.0 + negative_share / 100.0)
        sources = _source_breakdown_for_theme(matching)
        raw_scores.append((theme.theme_id, raw_score, mention_count, negative_share, sources))

    raw_scores.sort(key=lambda item: item[1], reverse=True)
    raw_scores = raw_scores[:max_factors]
    total_score = sum(score for _, score, _, _, _ in raw_scores) or 1.0

    root_causes: list[dict[str, Any]] = []
    for theme_id, score, mention_count, negative_share, sources in raw_scores:
        info = meta.get(theme_id, {"label": theme_id, "description": theme_id})
        root_causes.append(
            {
                "theme_id": theme_id,
                "label": info["label"],
                "description": info["description"],
                "weight": round(score / total_score * 100, 1),
                "mention_count": mention_count,
                "negative_share": negative_share,
                "top_sources": sources,
            }
        )

    segment_factors = [
        {
            "label": signal.description,
            "theme_id": signal.theme_id,
            "weight": round(100 / max(len(section.segment_signals), 1), 1)
            if section.segment_signals
            else 0.0,
        }
        for signal in section.segment_signals[:4]
    ]

    summary = _build_summary(section, root_causes, segment_factors)
    return {
        "summary": summary,
        "root_causes": root_causes,
        "segment_factors": segment_factors,
        "negative_share": section.sentiment_mix.get("negative", 0.0),
        "review_count": section.review_count,
        "cross_source_themes": len(section.cross_source_themes),
    }


def _build_summary(
    section: RQSection,
    root_causes: list[dict[str, Any]],
    segment_factors: list[dict[str, Any]],
) -> str:
    if not root_causes:
        return "Insufficient evidence for a consolidated problem statement."

    lead = root_causes[0]
    parts = [
        f"Analysis of {section.review_count} reviews shows that "
        f"{lead['label']} is the strongest driver ({lead['weight']}% weight, "
        f"{lead['mention_count']} mentions, {lead['negative_share']}% negative). "
        f"{lead['description']}"
    ]

    if len(root_causes) > 1:
        secondary = ", ".join(
            f"{factor['label']} ({factor['weight']}%)" for factor in root_causes[1:4]
        )
        parts.append(f"Secondary contributing factors include {secondary}.")

    negative = section.sentiment_mix.get("negative")
    if negative:
        parts.append(f"{negative}% of mapped feedback for this RQ is negative overall.")

    if section.cross_source_themes:
        parts.append(
            f"{len(section.cross_source_themes)} problem themes appear across multiple "
            "sources (App Store, Play Store, social), indicating systemic rather than "
            "platform-specific issues."
        )

    if segment_factors:
        parts.append(
            "Segment signals: "
            + "; ".join(factor["label"] for factor in segment_factors[:2])
            + "."
        )

    return " ".join(parts)
