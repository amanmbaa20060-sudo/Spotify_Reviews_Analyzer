from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.db.models import Review, Source
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview
from spotify_app_review_analyzer.ingestion.export import export_raw_snapshot
from spotify_app_review_analyzer.ingestion.hashing import content_hash
from spotify_app_review_analyzer.ingestion.metrics import IngestMetrics

logger = logging.getLogger(__name__)

SOURCE_DEFINITIONS: dict[str, str] = {
    "app_store": "Apple App Store",
    "play_store": "Google Play Store",
    "reddit": "Reddit",
    "mastodon": "Mastodon",
    "bluesky": "Bluesky",
}


class IngestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_sources(self, *, commit: bool = False) -> dict[str, uuid.UUID]:
        source_ids: dict[str, uuid.UUID] = {}
        for key, name in SOURCE_DEFINITIONS.items():
            existing = self.session.scalar(select(Source).where(Source.key == key))
            if existing:
                source_ids[key] = existing.id
                continue
            source = Source(id=uuid.uuid4(), key=key, name=name, created_at=datetime.now(UTC))
            self.session.add(source)
            source_ids[key] = source.id
        self.session.flush()
        if commit:
            self.session.commit()
        return source_ids

    def ingest_provider(
        self,
        provider: IngestionProvider,
        *,
        limit: int | None = None,
        dry_run: bool = False,
        commit: bool = False,
        export_json: bool = False,
    ) -> IngestMetrics:
        metrics = IngestMetrics(source_key=provider.source_key)
        source_ids = self.ensure_sources()
        source_id = source_ids[provider.source_key]

        try:
            reviews = provider.fetch(limit=limit)
        except Exception as exc:
            metrics.failed += 1
            metrics.errors.append(str(exc))
            logger.exception("Failed to fetch from source=%s", provider.source_key)
            return metrics

        metrics.fetched = len(reviews)
        if export_json and reviews:
            export_raw_snapshot(provider.source_key, reviews)
        seen_hashes: set[str] = set()

        for item in reviews:
            try:
                review_hash = content_hash(item.source_key, item.text, item.title)
                if review_hash in seen_hashes:
                    metrics.skipped += 1
                    continue
                seen_hashes.add(review_hash)

                if dry_run:
                    metrics.inserted += 1
                    continue

                existing = self.session.scalar(
                    select(Review).where(Review.content_hash == review_hash)
                )
                if existing:
                    if item.published_at and existing.published_at is None:
                        existing.published_at = item.published_at
                    metrics.skipped += 1
                    continue

                review = Review(
                    id=uuid.uuid4(),
                    source_id=source_id,
                    external_id=item.external_id,
                    title=item.title,
                    text=item.text,
                    rating=item.rating,
                    author_hash=item.author_hash,
                    published_at=item.published_at,
                    app_version=item.app_version,
                    extra_metadata=item.extra_metadata,
                    content_hash=review_hash,
                    processing_status="pending",
                    created_at=datetime.now(UTC),
                )
                self.session.add(review)
                metrics.inserted += 1
            except Exception as exc:
                metrics.failed += 1
                metrics.errors.append(str(exc))
                logger.exception("Failed to persist review source=%s", provider.source_key)

        if not dry_run:
            self.session.flush()
            if commit:
                self.session.commit()

        metrics.log_summary()
        return metrics

    @staticmethod
    def to_review_dict(item: NormalizedReview) -> dict:
        return {
            "source_key": item.source_key,
            "external_id": item.external_id,
            "title": item.title,
            "text": item.text,
            "rating": item.rating,
            "author_hash": item.author_hash,
            "published_at": item.published_at,
            "app_version": item.app_version,
            "extra_metadata": item.extra_metadata,
            "content_hash": content_hash(item.source_key, item.text, item.title),
        }
