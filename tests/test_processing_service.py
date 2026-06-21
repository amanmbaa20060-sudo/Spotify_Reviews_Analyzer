from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from spotify_app_review_analyzer.db.models import AnalysisResult, Review, ReviewEmbedding, Source
from spotify_app_review_analyzer.processing.service import ProcessingService


@pytest.fixture
def seeded_review(db_session):
    source = Source(
        id=uuid.uuid4(),
        key="app_store",
        name="Apple App Store",
        created_at=datetime.now(UTC),
    )
    db_session.add(source)
    db_session.flush()

    review = Review(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id="t1",
        title="Discovery",
        text="Spotify recommendations are repetitive and I cannot find new music easily.",
        rating=2,
        content_hash="hash-processing-1",
        processing_status="pending",
        created_at=datetime.now(UTC),
        extra_metadata={},
    )
    db_session.add(review)
    db_session.flush()
    return review


def test_process_batch_marks_review_processed(db_session, seeded_review) -> None:
    service = ProcessingService(db_session)
    metrics = service.process_batch(batch_size=10)
    db_session.commit()

    assert metrics.processed == 1
    refreshed = db_session.get(Review, seeded_review.id)
    assert refreshed is not None
    assert refreshed.processing_status == "processed"

    analysis = db_session.get(AnalysisResult, seeded_review.id)
    assert analysis is not None
    assert analysis.sentiment in {"negative", "neutral"}
    assert analysis.themes
    assert analysis.model_version


def test_process_batch_skips_empty_text(db_session) -> None:
    source = Source(id=uuid.uuid4(), key="reddit", name="Reddit", created_at=datetime.now(UTC))
    db_session.add(source)
    db_session.flush()
    review = Review(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id="empty",
        text="   ",
        content_hash="hash-empty",
        processing_status="pending",
        created_at=datetime.now(UTC),
        extra_metadata={},
    )
    db_session.add(review)
    db_session.flush()

    service = ProcessingService(db_session)
    metrics = service.process_batch(batch_size=10)
    assert metrics.skipped == 1
    assert db_session.get(Review, review.id).processing_status == "skipped"


def test_rebuild_embeddings_persists_vectors(db_session, seeded_review) -> None:
    service = ProcessingService(db_session)
    service.process_batch(batch_size=10)
    count = service.rebuild_all_embeddings()
    db_session.commit()

    assert count == 1
    embedding = db_session.get(ReviewEmbedding, seeded_review.id)
    assert embedding is not None
    assert len(embedding.embedding) > 0

    hits = service.semantic_search("repetitive recommendations", top_k=1)
    assert hits
    assert hits[0]["review_id"] == str(seeded_review.id)


def test_idempotent_without_force(db_session, seeded_review) -> None:
    service = ProcessingService(db_session)
    first = service.process_batch(batch_size=10)
    db_session.commit()
    second = service.process_batch(batch_size=10)

    assert first.processed == 1
    assert second.fetched == 0
