from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.db.models import AnalysisResult, Review, Source
from spotify_app_review_analyzer.processing.classifier.rule_based import RuleBasedClassifier
from spotify_app_review_analyzer.taxonomy.loader import load_taxonomy

_feedback_classifier: RuleBasedClassifier | None = None


def _parse_since(since_days: int | None) -> datetime | None:
    if since_days is None:
        return None
    return datetime.now(UTC) - timedelta(days=since_days)


def _review_timestamp():
    """Effective review date for filters (published_at, else ingest time)."""
    return func.coalesce(Review.published_at, Review.created_at)


def _feedback_classifier_instance() -> RuleBasedClassifier:
    global _feedback_classifier
    if _feedback_classifier is None:
        _feedback_classifier = RuleBasedClassifier()
    return _feedback_classifier


def _feedback_sentiment(review: Review, analysis: AnalysisResult | None) -> str:
    if analysis and analysis.sentiment:
        return analysis.sentiment
    return _feedback_classifier_instance().classify(review.text, rating=review.rating).sentiment


def get_overview_kpis(session: Session, *, since_days: int | None = None) -> dict[str, Any]:
    since = _parse_since(since_days)
    total = session.scalar(select(func.count()).select_from(Review)) or 0
    processed = session.scalar(
        select(func.count()).select_from(Review).where(Review.processing_status == "processed")
    ) or 0

    def _avg_rating(source_key: str) -> dict[str, Any]:
        stmt = (
            select(func.avg(Review.rating), func.count())
            .join(Source, Review.source_id == Source.id)
            .where(Source.key == source_key, Review.rating.is_not(None))
        )
        if since:
            stmt = stmt.where(_review_timestamp() >= since)
        avg, count = session.execute(stmt).one()
        return {
            "average": round(float(avg), 2) if avg is not None else None,
            "count": int(count or 0),
        }

    play_store = _avg_rating("play_store")
    app_store = _avg_rating("app_store")

    sentiment_stmt = (
        select(AnalysisResult.sentiment, func.count())
        .join(Review, Review.id == AnalysisResult.review_id)
        .where(Review.processing_status == "processed")
        .group_by(AnalysisResult.sentiment)
    )
    if since:
        sentiment_stmt = sentiment_stmt.where(_review_timestamp() >= since)
    sentiment_rows = dict(session.execute(sentiment_stmt).all())
    sentiment_total = sum(sentiment_rows.values()) or 1
    sentiment_mix = {
        key or "unknown": round(count / sentiment_total * 100, 1)
        for key, count in sentiment_rows.items()
    }

    return {
        "total_records": int(total),
        "processed_records": int(processed),
        "play_store": play_store,
        "app_store": app_store,
        "sentiment_mix": sentiment_mix,
    }


def get_sentiment_by_source(session: Session, *, since_days: int | None = None) -> list[dict]:
    since = _parse_since(since_days)
    stmt = (
        select(Source.key, AnalysisResult.sentiment, func.count())
        .join(Review, Review.source_id == Source.id)
        .join(AnalysisResult, AnalysisResult.review_id == Review.id)
        .where(Review.processing_status == "processed")
        .group_by(Source.key, AnalysisResult.sentiment)
    )
    if since:
        stmt = stmt.where(_review_timestamp() >= since)
    rows = session.execute(stmt).all()
    return [
        {"source_key": source, "sentiment": sentiment or "unknown", "count": int(count)}
        for source, sentiment, count in rows
    ]


def get_rating_distribution(
    session: Session,
    *,
    source_key: str | None = None,
    since_days: int | None = None,
) -> list[dict]:
    since = _parse_since(since_days)
    stmt = (
        select(Source.key, Review.rating, func.count())
        .join(Source, Review.source_id == Source.id)
        .where(Review.rating.is_not(None))
        .group_by(Source.key, Review.rating)
    )
    if source_key:
        stmt = stmt.where(Source.key == source_key)
    if since:
        stmt = stmt.where(_review_timestamp() >= since)
    return [
        {"source_key": sk, "rating": int(rating), "count": int(count)}
        for sk, rating, count in session.execute(stmt).all()
    ]


def get_top_themes(
    session: Session,
    *,
    since_days: int | None = None,
    rq_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    since = _parse_since(since_days)
    rows = session.scalars(
        select(Review)
        .options(joinedload(Review.source), joinedload(Review.analysis))
        .where(Review.processing_status == "processed")
    ).all()
    labels = {t.id: t.label for t in load_taxonomy().themes}
    counter: Counter[str] = Counter()
    for review in rows:
        if review.analysis is None:
            continue
        if since:
            effective = review.published_at or review.created_at
            if effective and effective.replace(tzinfo=UTC) < since:
                continue
        for theme in review.analysis.themes or []:
            if rq_id and not theme.startswith(f"{rq_id}."):
                continue
            counter[theme] += 1
    return [
        {
            "theme_id": theme_id,
            "label": labels.get(theme_id, theme_id),
            "count": count,
            "rq_id": theme_id.split(".")[0] if "." in theme_id else None,
        }
        for theme_id, count in counter.most_common(limit)
    ]


def get_reviews(
    session: Session,
    *,
    source_key: str | None = None,
    sentiment: str | None = None,
    min_rating: int | None = None,
    theme: str | None = None,
    since_days: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    since = _parse_since(since_days)
    stmt = (
        select(Review)
        .join(Source, Review.source_id == Source.id)
        .options(joinedload(Review.source), joinedload(Review.analysis))
        .where(Review.processing_status == "processed")
        .order_by(_review_timestamp().desc())
    )
    if source_key:
        stmt = stmt.where(Source.key == source_key)
    if since:
        stmt = stmt.where(_review_timestamp() >= since)
    if min_rating is not None:
        stmt = stmt.where(Review.rating >= min_rating)
    if sentiment:
        stmt = stmt.join(AnalysisResult, AnalysisResult.review_id == Review.id).where(
            AnalysisResult.sentiment == sentiment
        )
    elif theme:
        stmt = stmt.join(AnalysisResult, AnalysisResult.review_id == Review.id)

    all_rows = list(session.scalars(stmt).unique().all())
    if theme:
        all_rows = [r for r in all_rows if r.analysis and theme in (r.analysis.themes or [])]
    if sentiment and not theme:
        pass  # already filtered in SQL
    total = len(all_rows)
    page = all_rows[offset : offset + limit]
    items = []
    for review in page:
        analysis = review.analysis
        items.append(
            {
                "review_id": str(review.id),
                "source_key": review.source.key if review.source else None,
                "text": review.text[:500],
                "rating": review.rating,
                "sentiment": analysis.sentiment if analysis else None,
                "themes": analysis.themes if analysis else [],
                "published_at": review.published_at.isoformat() if review.published_at else None,
                "confidence": analysis.confidence if analysis else None,
            }
        )
    return items, total


def get_recent_feedback(
    session: Session,
    *,
    source_key: str,
    limit: int = 8,
) -> tuple[list[dict], int]:
    """Latest reviews for the feedback panel (includes pending; ignores date filters)."""
    stmt = (
        select(Review)
        .join(Source, Review.source_id == Source.id)
        .options(joinedload(Review.source), joinedload(Review.analysis))
        .where(
            Source.key == source_key,
            Review.processing_status.in_(("processed", "pending")),
        )
        .order_by(_review_timestamp().desc())
    )
    all_rows = list(session.scalars(stmt).unique().all())
    total = len(all_rows)
    page = all_rows[:limit]
    items = []
    for review in page:
        analysis = review.analysis
        effective = review.published_at or review.created_at
        sentiment = _feedback_sentiment(review, analysis)
        items.append(
            {
                "review_id": str(review.id),
                "source_key": review.source.key if review.source else None,
                "text": review.text[:500],
                "rating": review.rating,
                "sentiment": sentiment,
                "themes": analysis.themes if analysis else [],
                "published_at": effective.isoformat() if effective else None,
                "processing_status": review.processing_status,
                "confidence": analysis.confidence if analysis else None,
            }
        )
    return items, total


def get_research_questions(session: Session) -> list[dict]:
    briefing = build_rq_briefing(session)
    taxonomy = load_taxonomy()
    solutions = _rq_solutions()
    output: list[dict] = []
    for section in briefing.sections:
        rq_id = section.rq_id
        output.append(
            {
                "rq_id": rq_id,
                "label": section.label,
                "review_count": section.review_count,
                "readiness": section.readiness,
                "readiness_score": _readiness_score(section.review_count, section.avg_confidence),
                "sentiment_mix": section.sentiment_mix,
                "source_breakdown": section.source_breakdown,
                "top_themes": [t.to_dict() for t in section.top_themes],
                "segment_signals": [s.to_dict() for s in section.segment_signals],
                "cross_source_themes": section.cross_source_themes,
                "exemplar_citations": [e.to_dict() for e in section.exemplar_citations],
                "problem_summary": _problem_summary(section),
                "proposed_solutions": solutions.get(rq_id, []),
                "tags": _rq_tags(section),
            }
        )
    return output


def get_research_question(session: Session, rq_id: str) -> dict | None:
    for item in get_research_questions(session):
        if item["rq_id"] == rq_id:
            return item
    return None


def get_unmet_needs(session: Session, *, limit: int = 10) -> list[dict]:
    """Rank rq6 themes by frequency * negative sentiment weight."""
    rq6 = get_research_question(session, "rq6")
    if not rq6:
        return []
    themes = rq6.get("top_themes", [])
    scored = []
    for theme in themes:
        severity = 1.0
        if "unmet" in theme["theme_id"] or "missing" in theme["theme_id"]:
            severity = 1.2
        scored.append(
            {
                **theme,
                "severity_score": round(theme["count"] * severity, 1),
            }
        )
    scored.sort(key=lambda item: item["severity_score"], reverse=True)
    return scored[:limit]


def get_word_cloud_data(session: Session, *, rq_id: str | None = None) -> list[dict]:
    themes = get_top_themes(session, rq_id=rq_id, limit=50)
    if not themes:
        return []
    max_count = max(t["count"] for t in themes)
    return [
        {
            "text": t["label"].split("/")[0].strip()[:30],
            "theme_id": t["theme_id"],
            "weight": round(t["count"] / max_count, 2),
            "count": t["count"],
        }
        for t in themes
    ]


def _readiness_score(review_count: int, avg_confidence: float | None) -> int:
    base = min(review_count / 2, 50)
    conf = (avg_confidence or 0.5) * 50
    return min(100, int(base + conf))


def _problem_summary(section) -> str:
    if not section.top_themes:
        return "Insufficient evidence for a consolidated problem statement."
    top = section.top_themes[0]
    return (
        f"Users most frequently report '{top.label}' ({top.count} mentions). "
        f"Evidence spans {len(section.cross_source_themes)} cross-source themes with "
        f"{section.review_count} relevant reviews."
    )


def _rq_tags(section) -> list[str]:
    tags: list[str] = []
    for theme in section.top_themes[:3]:
        label = theme.label.split("/")[0].strip().replace(" ", "")
        tags.append(f"#{label[:20]}")
    return tags or ["#Discovery"]


def _rq_solutions() -> dict[str, list[str]]:
    return {
        "rq1": [
            "Improve discovery entry points with clearer Browse/Search hierarchy",
            "Add onboarding tooltips for Discover Weekly and Release Radar",
            "Reduce choice overload via guided 'Start here' playlists",
        ],
        "rq2": [
            "Introduce repetition controls and 'refresh my mix' actions",
            "Improve genre diversity in daily recommendations",
            "Surface transparency for why a track was recommended",
        ],
        "rq3": [
            "Support intentional exploration modes (mood, genre dive)",
            "Enable playlist co-creation and social discovery loops",
            "Highlight listening intent shortcuts on Home",
        ],
        "rq4": [
            "Distinguish comfort listening from algorithmic loops",
            "Offer 'break the loop' nudges after repeated plays",
            "Improve autoplay variety after playlist ends",
        ],
        "rq5": [
            "Address Android-specific browse friction",
            "Tailor discovery for free vs premium tiers",
            "Close iOS/Android parity gaps on discovery surfaces",
        ],
        "rq6": [
            "Improve search accuracy and offline reliability",
            "Reduce ad load impact on free-tier discovery",
            "Increase transparency on AI-driven features and stability",
        ],
    }
