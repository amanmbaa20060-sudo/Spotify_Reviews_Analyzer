from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.ingestion.base import IngestionProvider, NormalizedReview
from spotify_app_review_analyzer.ingestion.http import HttpClient

logger = logging.getLogger(__name__)


def _parse_updated(updated: str | None) -> datetime | None:
    """Parse App Store RSS `updated` labels (ISO 8601 or RFC 2822)."""
    if not updated or not isinstance(updated, str):
        return None
    try:
        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(updated).astimezone(UTC)
    except (TypeError, ValueError):
        return None


class AppStoreProvider(IngestionProvider):
    source_key = "app_store"

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or HttpClient(
            max_retries=settings.ingest_max_retries,
            backoff_seconds=settings.ingest_backoff_seconds,
        )

    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        results: list[NormalizedReview] = []
        page = 1
        max_pages = settings.app_store_max_pages

        while page <= max_pages:
            if limit is not None and len(results) >= limit:
                break

            url = (
                "https://itunes.apple.com/rss/customerreviews/"
                f"page={page}/id={settings.spotify_app_store_id}/sortby=mostrecent/json"
            )
            try:
                payload = self.http_client.get_json(url)
            except Exception as exc:
                logger.warning("App Store page %s failed: %s", page, exc)
                break

            entries = self._extract_entries(payload)
            if not entries:
                break

            for entry in entries:
                normalized = self._normalize_entry(entry)
                if normalized:
                    results.append(normalized)
                    if limit is not None and len(results) >= limit:
                        break
            page += 1

        return results

    def _extract_entries(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            logger.warning("App Store payload is not a dict")
            return []
        feed = payload.get("feed", {})
        if not isinstance(feed, dict):
            return []
        entries = feed.get("entry", [])
        if isinstance(entries, dict):
            return [entries]
        if isinstance(entries, list):
            return [e for e in entries if isinstance(e, dict)]
        return []

    def _normalize_entry(self, entry: dict[str, Any]) -> NormalizedReview | None:
        if "content" not in entry:
            return None

        content = entry.get("content", {})
        label = content.get("label") if isinstance(content, dict) else None
        text = label if isinstance(label, str) else str(content)
        if not text.strip():
            return None

        title_field = entry.get("title")
        title = title_field.get("label") if isinstance(title_field, dict) else None
        rating_raw = entry.get("im:rating", {}).get("label")
        rating = int(rating_raw) if rating_raw and str(rating_raw).isdigit() else None

        author_name = entry.get("author", {}).get("name", {}).get("label")
        author_hash = (
            hashlib.sha256(str(author_name).encode("utf-8")).hexdigest()[:32]
            if author_name
            else None
        )

        updated = entry.get("updated", {}).get("label")
        published_at = _parse_updated(updated)

        external_id = entry.get("id", {}).get("label")
        app_version = entry.get("im:version", {}).get("label")

        return NormalizedReview(
            source_key=self.source_key,
            external_id=str(external_id) if external_id else None,
            title=str(title) if title else None,
            text=text.strip(),
            rating=rating,
            author_hash=author_hash,
            published_at=published_at,
            app_version=str(app_version) if app_version else None,
            extra_metadata={"raw_entry_id": external_id},
        )
