from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview

logger = logging.getLogger(__name__)


class SnapshotProvider(IngestionProvider):
    """In-memory provider backed by a JSON export snapshot."""

    def __init__(self, source_key: str, reviews: list[NormalizedReview]) -> None:
        self.source_key = source_key
        self._reviews = reviews

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        if limit is None:
            return self._reviews
        return self._reviews[:limit]


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.warning("Could not parse published_at=%r", value)
        return None


def load_snapshot(path: Path) -> list[NormalizedReview]:
    """Load reviews from a data/raw/*.json export snapshot."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    reviews: list[NormalizedReview] = []
    for row in payload.get("reviews", []):
        reviews.append(
            NormalizedReview(
                source_key=row["source_key"],
                external_id=row.get("external_id"),
                title=row.get("title"),
                text=row["text"],
                rating=row.get("rating"),
                author_hash=row.get("author_hash"),
                published_at=_parse_published_at(row.get("published_at")),
                app_version=row.get("app_version"),
                extra_metadata=row.get("extra_metadata") or {},
            )
        )
    return reviews
