from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from google_play_scraper import Sort
from google_play_scraper import reviews as gp_reviews

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview

logger = logging.getLogger(__name__)


class PlayStoreProvider(IngestionProvider):
    source_key = "play_store"

    def __init__(self, fetch_fn: Any | None = None) -> None:
        self._fetch_fn = fetch_fn or gp_reviews

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        target = limit or settings.play_store_default_limit
        results: list[NormalizedReview] = []
        token = None

        while len(results) < target:
            batch_size = min(200, target - len(results))
            try:
                batch, token = self._fetch_fn(
                    settings.spotify_play_store_id,
                    lang="en",
                    country="us",
                    sort=Sort.NEWEST,
                    count=batch_size,
                    continuation_token=token,
                )
            except Exception as exc:
                logger.warning("Play Store fetch failed: %s", exc)
                break

            if not batch:
                break

            for item in batch:
                normalized = self._normalize_item(item)
                if normalized:
                    results.append(normalized)

            if token is None:
                break

        return results[:target]

    def _normalize_item(self, item: dict[str, Any]) -> NormalizedReview | None:
        text = item.get("content")
        if not text or not str(text).strip():
            return None

        user_name = item.get("userName")
        author_hash = (
            hashlib.sha256(str(user_name).encode("utf-8")).hexdigest()[:32] if user_name else None
        )

        published_at = item.get("at")
        if isinstance(published_at, datetime) and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        elif not isinstance(published_at, datetime):
            published_at = None

        rating = item.get("score")
        rating_int = int(rating) if rating is not None else None

        return NormalizedReview(
            source_key=self.source_key,
            external_id=str(item.get("reviewId")) if item.get("reviewId") else None,
            title=None,
            text=str(text).strip(),
            rating=rating_int,
            author_hash=author_hash,
            published_at=published_at,
            app_version=item.get("appVersion"),
            extra_metadata={
                "thumbs_up": item.get("thumbsUpCount"),
                "reply_content": item.get("replyContent"),
            },
        )
