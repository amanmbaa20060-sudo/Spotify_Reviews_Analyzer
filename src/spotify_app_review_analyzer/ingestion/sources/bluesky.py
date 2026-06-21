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
)

logger = logging.getLogger(__name__)


class BlueskyProvider(IngestionProvider):
    source_key = "bluesky"

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient(
            max_retries=settings.ingest_max_retries,
            backoff_seconds=settings.ingest_backoff_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": settings.reddit_user_agent,
            },
        )
        self.service_url = settings.bluesky_service_url.rstrip("/")
        self._access_token: str | None = None

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        target = limit or settings.bluesky_default_limit
        queries = settings.bluesky_search_query_list
        results: list[NormalizedReview] = []
        seen_uris: set[str] = set()

        if not self._ensure_session():
            logger.warning(
                "Bluesky ingest skipped: set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD "
                "or fix public API access (public.api.bsky.app may block some networks)."
            )
            return []

        for query in queries:
            if len(results) >= target:
                break
            batch = self._search(query, limit=target - len(results), seen_uris=seen_uris)
            results.extend(batch)

        self._apply_viral_flags(results)
        logger.info("Bluesky fetched %s relevant posts (target=%s)", len(results), target)
        return results[:target]

    def _ensure_session(self) -> bool:
        if self._access_token:
            return True
        if settings.bluesky_handle and settings.bluesky_app_password:
            return self._login()
        # Fallback: unauthenticated public API (may work on some networks).
        self._access_token = ""
        return True

    def _login(self) -> bool:
        try:
            import httpx

            with httpx.Client(
                headers=self.http_client.headers,
                timeout=self.http_client.timeout_seconds,
            ) as client:
                response = client.post(
                    f"{self.service_url}/xrpc/com.atproto.server.createSession",
                    json={
                        "identifier": settings.bluesky_handle,
                        "password": settings.bluesky_app_password,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("Bluesky login failed: %s", exc)
            return False

        token = payload.get("accessJwt") if isinstance(payload, dict) else None
        if not token:
            logger.warning("Bluesky login returned no access token")
            return False
        self._access_token = str(token)
        self.http_client.headers["Authorization"] = f"Bearer {self._access_token}"
        return True

    def _search_api_base(self) -> str:
        if settings.bluesky_handle and settings.bluesky_app_password:
            return self.service_url
        return "https://public.api.bsky.app"

    def _search(
        self,
        query: str,
        *,
        limit: int,
        seen_uris: set[str],
    ) -> list[NormalizedReview]:
        results: list[NormalizedReview] = []
        cursor: str | None = None
        api_base = self._search_api_base()

        while len(results) < limit:
            batch_limit = min(100, limit - len(results))
            params: dict[str, Any] = {"q": query, "limit": batch_limit}
            if cursor:
                params["cursor"] = cursor

            url = f"{api_base}/xrpc/app.bsky.feed.searchPosts"
            try:
                payload = self.http_client.get_json(url, params=params)
            except Exception as exc:
                logger.warning("Bluesky search failed for query=%r: %s", query, exc)
                break

            posts = payload.get("posts", []) if isinstance(payload, dict) else []
            if not posts:
                break

            for post in posts:
                if not isinstance(post, dict):
                    continue
                uri = str(post.get("uri") or "")
                if uri and uri in seen_uris:
                    continue
                normalized = self._normalize_post(post, query=query)
                if normalized:
                    if uri:
                        seen_uris.add(uri)
                    results.append(normalized)
                    if len(results) >= limit:
                        break

            cursor = payload.get("cursor") if isinstance(payload, dict) else None
            if not cursor:
                break

        return results

    def _normalize_post(self, post: dict[str, Any], *, query: str) -> NormalizedReview | None:
        record = post.get("record") if isinstance(post.get("record"), dict) else {}
        text = str(record.get("text") or "").strip()
        if not text or not is_spotify_relevant(text):
            return None

        author = post.get("author") if isinstance(post.get("author"), dict) else {}
        handle = author.get("handle")
        author_hash = (
            hashlib.sha256(str(handle).encode("utf-8")).hexdigest()[:32] if handle else None
        )

        published_at = None
        for ts_field in (record.get("createdAt"), post.get("indexedAt")):
            if isinstance(ts_field, str):
                published_at = datetime.fromisoformat(ts_field.replace("Z", "+00:00"))
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=UTC)
                break

        likes = int(post.get("likeCount") or 0)
        reposts = int(post.get("repostCount") or 0)
        replies = int(post.get("replyCount") or 0)
        metadata = build_engagement_metadata(
            likes=likes,
            reposts=reposts,
            replies=replies,
            extra={
                "platform": "bluesky",
                "search_query": query,
                "uri": post.get("uri"),
                "cid": post.get("cid"),
                "author_handle": handle,
            },
        )

        return NormalizedReview(
            source_key=self.source_key,
            external_id=str(post.get("uri") or post.get("cid") or ""),
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
