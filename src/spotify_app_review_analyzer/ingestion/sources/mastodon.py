from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview
from spotify_app_review_analyzer.ingestion.http import HttpClient
from spotify_app_review_analyzer.ingestion.social_filter import (
    build_engagement_metadata,
    is_spotify_relevant,
    mark_viral_outliers,
    strip_html,
)

logger = logging.getLogger(__name__)


class MastodonProvider(IngestionProvider):
    source_key = "mastodon"

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient(
            max_retries=settings.ingest_max_retries,
            backoff_seconds=settings.ingest_backoff_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": settings.reddit_user_agent,
            },
        )
        self.instance = settings.mastodon_instance_url.rstrip("/")

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        target = limit or settings.mastodon_default_limit
        hashtags = settings.mastodon_hashtag_list
        results: list[NormalizedReview] = []
        seen_ids: set[str] = set()

        for hashtag in hashtags:
            if len(results) >= target:
                break
            batch = self._fetch_hashtag(hashtag, limit=target - len(results), seen_ids=seen_ids)
            results.extend(batch)

        self._apply_viral_flags(results)
        logger.info("Mastodon fetched %s relevant posts (target=%s)", len(results), target)
        return results[:target]

    def _fetch_hashtag(
        self,
        hashtag: str,
        *,
        limit: int,
        seen_ids: set[str],
    ) -> list[NormalizedReview]:
        results: list[NormalizedReview] = []
        max_id: str | None = None
        tag = hashtag.lstrip("#")

        while len(results) < limit:
            batch_limit = min(40, limit - len(results))
            params: dict[str, Any] = {"limit": batch_limit}
            if max_id:
                params["max_id"] = max_id

            url = f"{self.instance}/api/v1/timelines/tag/{tag}"
            try:
                payload = self.http_client.get_json(url, params=params)
            except Exception as exc:
                logger.warning("Mastodon hashtag fetch failed for #%s: %s", tag, exc)
                break

            if not isinstance(payload, list) or not payload:
                break

            for status in payload:
                if not isinstance(status, dict):
                    continue
                status_id = str(status.get("id") or "")
                if status_id in seen_ids:
                    continue
                normalized = self._normalize_status(status, hashtag=tag)
                if normalized:
                    seen_ids.add(status_id)
                    results.append(normalized)
                    if len(results) >= limit:
                        break

            max_id = str(payload[-1].get("id")) if payload else None
            if len(payload) < batch_limit:
                break

        return results

    def _normalize_status(self, status: dict[str, Any], *, hashtag: str) -> NormalizedReview | None:
        content_html = str(status.get("content") or "")
        text = strip_html(content_html)
        if not text:
            return None
        if not is_spotify_relevant(text, from_hashtag=hashtag):
            return None

        account = status.get("account") if isinstance(status.get("account"), dict) else {}
        author = account.get("acct") or account.get("username")
        author_hash = (
            hashlib.sha256(str(author).encode("utf-8")).hexdigest()[:32] if author else None
        )

        published_at = None
        created_at = status.get("created_at")
        if isinstance(created_at, str):
            published_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)

        likes = int(status.get("favourites_count") or 0)
        reposts = int(status.get("reblogs_count") or 0)
        replies = int(status.get("replies_count") or 0)
        metadata = build_engagement_metadata(
            likes=likes,
            reposts=reposts,
            replies=replies,
            extra={
                "platform": "mastodon",
                "hashtag": hashtag,
                "url": status.get("url"),
                "instance": self.instance,
                "visibility": status.get("visibility"),
            },
        )

        return NormalizedReview(
            source_key=self.source_key,
            external_id=str(status.get("id")) if status.get("id") else None,
            title=None,
            text=text,
            rating=None,
            author_hash=author_hash,
            published_at=published_at,
            app_version=None,
            extra_metadata=metadata,
        )

    @staticmethod
    def _apply_viral_flags(reviews: list[NormalizedReview]) -> None:
        payloads = [review.extra_metadata for review in reviews]
        mark_viral_outliers(payloads, percentile=settings.social_viral_engagement_percentile)
        for review, metadata in zip(reviews, payloads, strict=True):
            review.extra_metadata.update(
                {
                    "viral": metadata.get("viral", False),
                    "traffic_state": metadata.get("traffic_state", "steady_state"),
                }
            )
