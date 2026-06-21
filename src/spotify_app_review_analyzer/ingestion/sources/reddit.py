from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview
from spotify_app_review_analyzer.ingestion.http import HttpClient

logger = logging.getLogger(__name__)


class RedditProvider(IngestionProvider):
    source_key = "reddit"

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient(
            max_retries=settings.ingest_max_retries,
            backoff_seconds=settings.ingest_backoff_seconds,
            headers={
                "User-Agent": settings.reddit_user_agent,
                "Accept": "application/json",
            },
        )

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        target = limit or settings.reddit_default_limit
        results: list[NormalizedReview] = []
        subreddits = settings.reddit_subreddit_list

        for subreddit in subreddits:
            if len(results) >= target:
                break
            remaining = target - len(results)
            sub_results = self._fetch_subreddit(subreddit, limit=remaining)
            results.extend(sub_results)

        return results[:target]

    def _fetch_subreddit(self, subreddit: str, *, limit: int) -> list[NormalizedReview]:
        results = self._fetch_subreddit_reddit(subreddit, limit=limit)
        if results:
            return results
        logger.info("Reddit direct API blocked for r/%s; using PullPush fallback", subreddit)
        return self._fetch_subreddit_pullpush(subreddit, limit=limit)

    def _fetch_subreddit_reddit(self, subreddit: str, *, limit: int) -> list[NormalizedReview]:
        results: list[NormalizedReview] = []
        after: str | None = None

        for base_url in (
            f"https://old.reddit.com/r/{subreddit}/new.json",
            f"https://www.reddit.com/r/{subreddit}/new.json",
        ):
            results = []
            after = None
            while len(results) < limit:
                batch_limit = min(100, limit - len(results))
                params: dict[str, Any] = {"limit": batch_limit, "raw_json": 1}
                if after:
                    params["after"] = after

                try:
                    payload = self.http_client.get_json(base_url, params=params)
                except Exception as exc:
                    logger.warning("Reddit fetch failed for r/%s via %s: %s", subreddit, base_url, exc)
                    results = []
                    break

                listing = payload.get("data", {}) if isinstance(payload, dict) else {}
                children = listing.get("children", []) if isinstance(listing, dict) else []
                if not children:
                    break

                for child in children:
                    data = child.get("data", {}) if isinstance(child, dict) else {}
                    normalized = self._normalize_post(subreddit, data)
                    if normalized:
                        results.append(normalized)
                        if len(results) >= limit:
                            break

                after = listing.get("after")
                if not after:
                    break

            if results:
                return results

        return []

    def _fetch_subreddit_pullpush(self, subreddit: str, *, limit: int) -> list[NormalizedReview]:
        results: list[NormalizedReview] = []
        before: int | None = None

        while len(results) < limit:
            batch_limit = min(100, limit - len(results))
            params: dict[str, Any] = {
                "subreddit": subreddit,
                "size": batch_limit,
                "sort": "desc",
                "sort_type": "created_utc",
            }
            if before is not None:
                params["before"] = before

            try:
                payload = self.http_client.get_json(
                    "https://api.pullpush.io/reddit/search/submission/",
                    params=params,
                )
            except Exception as exc:
                logger.warning("PullPush fetch failed for r/%s: %s", subreddit, exc)
                break

            items = payload.get("data", []) if isinstance(payload, dict) else []
            if not items:
                break

            for item in items:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_post(subreddit, item)
                if normalized:
                    results.append(normalized)
                    if len(results) >= limit:
                        break

            last_created = items[-1].get("created_utc") if items else None
            if not isinstance(last_created, (int, float)):
                break
            before = int(last_created)
            if len(items) < batch_limit:
                break

        return results

    def _normalize_post(self, subreddit: str, data: dict[str, Any]) -> NormalizedReview | None:
        title = data.get("title")
        selftext = data.get("selftext") or ""
        body = str(selftext).strip()
        text = f"{title}\n\n{body}".strip() if title else body
        if not text:
            return None

        author = data.get("author")
        author_hash = (
            hashlib.sha256(str(author).encode("utf-8")).hexdigest()[:32] if author else None
        )

        created_utc = data.get("created_utc")
        published_at = None
        if isinstance(created_utc, (int, float)):
            published_at = datetime.fromtimestamp(created_utc, tz=UTC)

        permalink = data.get("permalink")
        if permalink and not str(permalink).startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"

        return NormalizedReview(
            source_key=self.source_key,
            external_id=str(data.get("id")) if data.get("id") else None,
            title=str(title) if title else None,
            text=text,
            rating=None,
            author_hash=author_hash,
            published_at=published_at,
            app_version=None,
            extra_metadata={
                "subreddit": subreddit,
                "permalink": permalink,
                "score": data.get("score"),
                "num_comments": data.get("num_comments"),
                "fetch_method": data.get("fetch_method", "reddit"),
            },
        )
