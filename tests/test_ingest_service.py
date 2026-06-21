from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.db.models import Source
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview
from spotify_app_review_analyzer.ingestion.service import IngestService


class StubProvider(IngestionProvider):
    source_key = "app_store"

    def __init__(self, items: list[NormalizedReview]) -> None:
        self._items = items

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        return self._items[:limit] if limit else self._items


@pytest.fixture
def sample_review() -> NormalizedReview:
    return NormalizedReview(
        source_key="app_store",
        external_id="ext-1",
        title="Discovery",
        text="Hard to discover new artists",
        rating=4,
        published_at=datetime.now(UTC),
    )


def test_ingest_dry_run_counts_without_db_write(sample_review: NormalizedReview) -> None:
    session = MagicMock(spec=Session)
    service = IngestService(session)
    provider = StubProvider([sample_review])

    metrics = service.ingest_provider(provider, dry_run=True)

    assert metrics.fetched == 1
    assert metrics.inserted == 1
    assert metrics.skipped == 0
    session.add.assert_not_called()


def test_ingest_skips_duplicate_content_hash(
    db_session: Session, sample_review: NormalizedReview
) -> None:
    service = IngestService(db_session)
    provider = StubProvider([sample_review, sample_review])

    metrics = service.ingest_provider(provider)

    assert metrics.fetched == 2
    assert metrics.inserted == 1
    assert metrics.skipped == 1


def test_ingest_idempotent_rerun(db_session: Session, sample_review: NormalizedReview) -> None:
    service = IngestService(db_session)
    provider = StubProvider([sample_review])

    first = service.ingest_provider(provider)
    second = service.ingest_provider(provider)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped == 1


def test_ensure_sources_creates_records(db_session: Session) -> None:
    service = IngestService(db_session)
    source_ids = service.ensure_sources()
    assert set(source_ids.keys()) == {"app_store", "play_store", "reddit", "mastodon", "bluesky"}
    count = db_session.scalar(select(func.count()).select_from(Source))
    assert count == 5
