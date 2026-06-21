from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from spotify_app_review_analyzer.db.models import AnalysisResult, Review, Source
from spotify_app_review_analyzer.taxonomy.loader import Taxonomy, load_taxonomy


@dataclass(frozen=True)
class AnalyzedReview:
    review_id: str
    text: str
    sentiment: str | None
    themes: tuple[str, ...]
    research_questions: tuple[str, ...]
    segment_tags: tuple[str, ...]
    confidence: float | None
    source_key: str
    published_at: datetime | None = None


def fetch_analyzed_reviews(session: Session) -> list[AnalyzedReview]:
    rows = session.scalars(
        select(Review)
        .options(joinedload(Review.source), joinedload(Review.analysis))
        .where(Review.processing_status == "processed")
        .order_by(Review.created_at)
    ).all()

    output: list[AnalyzedReview] = []
    for review in rows:
        if review.analysis is None or review.source is None:
            continue
        analysis = review.analysis
        output.append(
            AnalyzedReview(
                review_id=str(review.id),
                text=review.text,
                sentiment=analysis.sentiment,
                themes=tuple(analysis.themes or []),
                research_questions=tuple(analysis.research_questions or []),
                segment_tags=tuple(analysis.segment_tags or []),
                confidence=analysis.confidence,
                source_key=review.source.key,
                published_at=review.published_at,
            )
        )
    return output


def sql_processed_count(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(Review)
            .where(Review.processing_status == "processed")
        )
        or 0
    )


def sql_rq_review_count(session: Session, rq_id: str) -> int:
    """Count processed reviews mapped to an RQ via research_questions JSON."""
    reviews = fetch_analyzed_reviews(session)
    return len(filter_reviews_for_rq(reviews, rq_id))


def theme_belongs_to_rq(theme_id: str, rq_id: str) -> bool:
    return theme_id == rq_id or theme_id.startswith(f"{rq_id}.")


def filter_reviews_for_rq(reviews: list[AnalyzedReview], rq_id: str) -> list[AnalyzedReview]:
    return [
        review
        for review in reviews
        if rq_id in review.research_questions
        or any(theme_belongs_to_rq(theme, rq_id) for theme in review.themes)
    ]


def themes_for_rq(review: AnalyzedReview, rq_id: str) -> list[str]:
    return [theme for theme in review.themes if theme_belongs_to_rq(theme, rq_id)]


def count_themes(reviews: list[AnalyzedReview], rq_id: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for review in reviews:
        for theme in themes_for_rq(review, rq_id):
            counter[theme] += 1
    return counter


def sentiment_mix(reviews: list[AnalyzedReview]) -> dict[str, float]:
    if not reviews:
        return {}
    counts = Counter(review.sentiment or "unknown" for review in reviews)
    total = sum(counts.values())
    return {sentiment: round(count / total * 100, 1) for sentiment, count in counts.items()}


def source_breakdown(reviews: list[AnalyzedReview]) -> dict[str, float]:
    if not reviews:
        return {}
    counts = Counter(review.source_key for review in reviews)
    total = sum(counts.values())
    return {source: round(count / total * 100, 1) for source, count in counts.items()}


def average_confidence(reviews: list[AnalyzedReview]) -> float | None:
    values = [review.confidence for review in reviews if review.confidence is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def cross_source_themes(
    reviews: list[AnalyzedReview],
    rq_id: str,
    *,
    min_sources: int = 2,
) -> list[str]:
    theme_sources: dict[str, set[str]] = defaultdict(set)
    for review in reviews:
        for theme in themes_for_rq(review, rq_id):
            theme_sources[theme].add(review.source_key)

    qualifying = [
        theme
        for theme, sources in theme_sources.items()
        if len(sources) >= min_sources
    ]
    return sorted(qualifying, key=lambda theme: (-len(theme_sources[theme]), theme))


def segment_theme_counts(
    reviews: list[AnalyzedReview],
    rq_id: str,
    segment_prefix: str,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    for review in reviews:
        if not any(tag.startswith(segment_prefix) for tag in review.segment_tags):
            continue
        for theme in themes_for_rq(review, rq_id):
            counter[theme] += 1
    return counter


def compute_segment_signals(
    reviews: list[AnalyzedReview],
    rq_id: str,
    *,
    top_theme_ids: list[str],
    min_count: int = 3,
    ratio_threshold: float = 1.25,
) -> list[tuple[str, str]]:
    """Return (theme_id, description) pairs for directional segment contrasts."""
    signals: list[tuple[str, str]] = []
    comparisons = [
        ("segment.platform.ios", "segment.platform.android", "iOS", "Android"),
        (
            "segment.subscription.free",
            "segment.subscription.premium",
            "Free-tier",
            "Premium",
        ),
    ]

    for left_prefix, right_prefix, left_label, right_label in comparisons:
        left_counts = segment_theme_counts(reviews, rq_id, left_prefix)
        right_counts = segment_theme_counts(reviews, rq_id, right_prefix)
        for theme_id in top_theme_ids:
            left = left_counts.get(theme_id, 0)
            right = right_counts.get(theme_id, 0)
            if left >= min_count and left >= right * ratio_threshold and right > 0:
                signals.append(
                    (
                        theme_id,
                        f"{left_label} pain > {right_label} on {theme_id} (directional)",
                    )
                )
            elif right >= min_count and right >= left * ratio_threshold and left > 0:
                signals.append(
                    (
                        theme_id,
                        f"{right_label} pain > {left_label} on {theme_id} (directional)",
                    )
                )
    return signals


def readiness_label(
    review_count: int,
    avg_confidence: float | None,
    *,
    high_count: int = 50,
    medium_count: int = 20,
    high_confidence: float = 0.6,
) -> str:
    if review_count >= high_count and (avg_confidence or 0) >= high_confidence:
        return "high"
    if review_count >= medium_count:
        return "medium"
    return "low"


def theme_label_map(taxonomy: Taxonomy | None = None) -> dict[str, str]:
    taxonomy = taxonomy or load_taxonomy()
    return {theme.id: theme.label for theme in taxonomy.themes}


def filter_reviews_by_days(
    reviews: list[AnalyzedReview],
    *,
    since_days: int | None,
) -> list[AnalyzedReview]:
    if since_days is None:
        return reviews
    cutoff = datetime.now(UTC) - timedelta(days=since_days)
    filtered: list[AnalyzedReview] = []
    for review in reviews:
        if review.published_at is None:
            filtered.append(review)
            continue
        published = review.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        if published >= cutoff:
            filtered.append(review)
    return filtered


def compare_source_metrics(
    reviews: list[AnalyzedReview],
    source_a: str,
    source_b: str,
    *,
    rq_id: str | None = None,
) -> dict:
    """Side-by-side sentiment and theme counts for two sources."""
    scoped = reviews
    if rq_id:
        scoped = filter_reviews_for_rq(reviews, rq_id)

    def _subset(source_key: str) -> list[AnalyzedReview]:
        return [review for review in scoped if review.source_key == source_key]

    left = _subset(source_a)
    right = _subset(source_b)
    theme_counter_a: Counter[str] = Counter()
    theme_counter_b: Counter[str] = Counter()
    for review in left:
        themes = themes_for_rq(review, rq_id) if rq_id else list(review.themes)
        theme_counter_a.update(themes)
    for review in right:
        themes = themes_for_rq(review, rq_id) if rq_id else list(review.themes)
        theme_counter_b.update(themes)

    return {
        "source_a": source_a,
        "source_b": source_b,
        "rq_id": rq_id,
        "review_count_a": len(left),
        "review_count_b": len(right),
        "sentiment_a": sentiment_mix(left),
        "sentiment_b": sentiment_mix(right),
        "top_themes_a": theme_counter_a.most_common(5),
        "top_themes_b": theme_counter_b.most_common(5),
    }

