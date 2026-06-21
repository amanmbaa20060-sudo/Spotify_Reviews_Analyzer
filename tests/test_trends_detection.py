from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from spotify_app_review_analyzer.db.models import AnalysisResult, Review, Source
from spotify_app_review_analyzer.trends.detection import (
    DailyThemeCount,
    compute_daily_theme_volumes,
    detect_bursts,
    top_rising_themes,
)


def _add_review(session, *, source_key: str, theme: str, day_offset: int, engagement: int):
    source = session.scalar(
        __import__("sqlalchemy").select(Source).where(Source.key == source_key)
    )
    if source is None:
        source = Source(
            id=uuid.uuid4(),
            key=source_key,
            name=source_key,
            created_at=datetime.now(UTC),
        )
        session.add(source)
        session.flush()

    published = datetime.now(UTC) - timedelta(days=day_offset)
    review = Review(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id=f"ext-{uuid.uuid4().hex[:8]}",
        text="Spotify recommendations are stale",
        content_hash=f"hash-{uuid.uuid4().hex}",
        processing_status="processed",
        published_at=published,
        created_at=published,
        extra_metadata={"engagement_score": engagement, "traffic_state": "steady_state"},
    )
    session.add(review)
    session.flush()
    session.add(
        AnalysisResult(
            review_id=review.id,
            sentiment="negative",
            themes=[theme],
            research_questions=["rq2"],
            listening_intent=[],
            segment_tags=[],
            confidence=0.8,
            model_version="test",
            created_at=published,
        )
    )
    session.flush()
    review.source = source
    review.analysis = session.get(AnalysisResult, review.id)
    return review


def test_detect_bursts_flags_spike(db_session) -> None:
    theme = "rq2.repetition.stale"
    reviews = []
    for offset in range(6, 1, -1):
        reviews.append(
            _add_review(db_session, source_key="mastodon", theme=theme, day_offset=offset, engagement=1)
        )
    for _ in range(6):
        reviews.append(
            _add_review(db_session, source_key="mastodon", theme=theme, day_offset=0, engagement=1)
        )
    volumes = compute_daily_theme_volumes(reviews, days=7)
    bursts = detect_bursts(volumes, threshold=2.0)
    assert bursts
    assert bursts[0].theme_id == theme
    assert bursts[0].multiplier >= 2.0


def test_top_rising_themes_orders_by_growth(db_session) -> None:
    theme = "rq2.relevance.mismatch"
    reviews = [
        _add_review(db_session, source_key="bluesky", theme=theme, day_offset=2, engagement=1),
        _add_review(db_session, source_key="bluesky", theme=theme, day_offset=1, engagement=1),
        _add_review(db_session, source_key="bluesky", theme=theme, day_offset=0, engagement=1),
        _add_review(db_session, source_key="bluesky", theme=theme, day_offset=0, engagement=1),
        _add_review(db_session, source_key="bluesky", theme=theme, day_offset=0, engagement=1),
    ]
    volumes = compute_daily_theme_volumes(reviews, days=7)
    rising = top_rising_themes(volumes, top_n=3)
    assert rising
    assert rising[0].theme_id == theme
    assert rising[0].growth_ratio >= 2.0
