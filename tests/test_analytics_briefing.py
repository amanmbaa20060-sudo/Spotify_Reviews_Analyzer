from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from spotify_app_review_analyzer.analytics.aggregations import (
    count_themes,
    cross_source_themes,
    filter_reviews_for_rq,
    sentiment_mix,
    source_breakdown,
)
from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing, verify_briefing_counts
from spotify_app_review_analyzer.analytics.evidence import select_exemplars_for_theme
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.analytics.service import RQAnalysisService
from spotify_app_review_analyzer.db.models import AnalysisResult, Review, Source
from spotify_app_review_analyzer.taxonomy.loader import Theme, load_taxonomy


def _add_review(
    session,
    *,
    source_key: str,
    text: str,
    themes: list[str],
    research_questions: list[str],
    segment_tags: list[str] | None = None,
    sentiment: str = "negative",
    confidence: float = 0.8,
) -> Review:
    source = session.scalar(select(Source).where(Source.key == source_key))
    if source is None:
        source = Source(
            id=uuid.uuid4(),
            key=source_key,
            name=source_key,
            created_at=datetime.now(UTC),
        )
        session.add(source)
        session.flush()

    review = Review(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id=f"ext-{uuid.uuid4().hex[:8]}",
        text=text,
        rating=2,
        content_hash=f"hash-{uuid.uuid4().hex}",
        processing_status="processed",
        created_at=datetime.now(UTC),
        extra_metadata={},
    )
    session.add(review)
    session.flush()
    session.add(
        AnalysisResult(
            review_id=review.id,
            sentiment=sentiment,
            sentiment_score=-0.5,
            themes=themes,
            research_questions=research_questions,
            listening_intent=[],
            segment_tags=segment_tags or [],
            confidence=confidence,
            model_version="rule-v1.0+tfidf-v1",
            created_at=datetime.now(UTC),
        )
    )
    session.flush()
    return review


@pytest.fixture
def seeded_rq_reviews(db_session):
    _add_review(
        db_session,
        source_key="app_store",
        text="I cannot find new music; discovery entry points are confusing on iOS.",
        themes=["rq1.entry_points.clarity"],
        research_questions=["rq1"],
        segment_tags=["segment.platform.ios"],
    )
    _add_review(
        db_session,
        source_key="play_store",
        text="Recommendations are stale and repetitive every day on Android.",
        themes=["rq2.repetition.stale", "rq4.repetition.habit"],
        research_questions=["rq2", "rq4"],
        segment_tags=["segment.platform.android"],
    )
    _add_review(
        db_session,
        source_key="reddit",
        text="Spotify keeps playing the same songs; recommendations feel irrelevant.",
        themes=["rq2.repetition.stale", "rq2.relevance.mismatch"],
        research_questions=["rq2"],
        segment_tags=["segment.platform.android"],
    )
    _add_review(
        db_session,
        source_key="app_store",
        text="I want to explore new genres but the app makes it hard to start.",
        themes=["rq1.entry_points.clarity", "rq3.intent.explore"],
        research_questions=["rq1", "rq3"],
        segment_tags=["segment.platform.ios", "segment.subscription.premium"],
    )
    db_session.commit()


def test_filter_reviews_for_rq_matches_themes_or_research_questions(db_session, seeded_rq_reviews):
    from spotify_app_review_analyzer.analytics.aggregations import fetch_analyzed_reviews

    reviews = fetch_analyzed_reviews(db_session)
    rq2_reviews = filter_reviews_for_rq(reviews, "rq2")
    assert len(rq2_reviews) == 2
    assert count_themes(rq2_reviews, "rq2")["rq2.repetition.stale"] == 2


def test_cross_source_themes_detects_shared_themes(db_session, seeded_rq_reviews):
    from spotify_app_review_analyzer.analytics.aggregations import fetch_analyzed_reviews

    reviews = fetch_analyzed_reviews(db_session)
    rq2_reviews = filter_reviews_for_rq(reviews, "rq2")
    shared = cross_source_themes(rq2_reviews, "rq2")
    assert "rq2.repetition.stale" in shared


def test_sentiment_and_source_breakdown(db_session, seeded_rq_reviews):
    from spotify_app_review_analyzer.analytics.aggregations import fetch_analyzed_reviews

    reviews = fetch_analyzed_reviews(db_session)
    mix = sentiment_mix(reviews)
    assert mix["negative"] == 100.0
    breakdown = source_breakdown(reviews)
    assert breakdown["app_store"] == 50.0
    assert breakdown["play_store"] == 25.0


def test_select_exemplars_prefers_source_diversity(db_session, seeded_rq_reviews):
    theme = Theme(
        id="rq2.repetition.stale",
        rq="rq2",
        label="Recommendations feel stale",
        description="Users hear the same songs repeatedly.",
    )
    from spotify_app_review_analyzer.analytics.aggregations import fetch_analyzed_reviews

    reviews = fetch_analyzed_reviews(db_session)
    rq2_reviews = filter_reviews_for_rq(reviews, "rq2")
    citations = select_exemplars_for_theme(theme, rq2_reviews, "rq2", per_theme=2)
    assert len(citations) == 2
    sources = {citation.source_key for citation in citations}
    assert len(sources) == 2


def test_build_rq_briefing_covers_all_rqs(db_session, seeded_rq_reviews):
    briefing = build_rq_briefing(db_session)
    assert len(briefing.sections) == len(RQ_IDS)
    rq2 = next(section for section in briefing.sections if section.rq_id == "rq2")
    assert rq2.review_count == 2
    assert len(rq2.exemplar_citations) >= 3
    assert briefing.verification["passed"] is True


def test_verify_briefing_counts_detects_mismatch(db_session, seeded_rq_reviews):
    briefing = build_rq_briefing(db_session)
    briefing.sections[0].review_count = 9999
    result = verify_briefing_counts(db_session, briefing)
    assert result["passed"] is False
    assert result["mismatches"]


def test_service_exports_briefing_files(db_session, seeded_rq_reviews, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "spotify_app_review_analyzer.analytics.service.settings.validation_export_dir",
        str(tmp_path),
    )
    service = RQAnalysisService(db_session)
    briefing = service.run(rq_ids=["rq2"], export=True)
    assert (tmp_path / "rq_briefing.md").exists()
    assert (tmp_path / "rq_briefing.json").exists()
    assert briefing.sections[0].rq_id == "rq2"


def test_taxonomy_loads_research_question_labels():
    taxonomy = load_taxonomy()
    assert "rq1" in taxonomy.research_questions
    assert "discover" in taxonomy.research_questions["rq1"].lower()
