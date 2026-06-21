from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.ingestion.base import NormalizedReview
from spotify_app_review_analyzer.ingestion.hashing import content_hash

logger = logging.getLogger(__name__)


def _serialize_review(item: NormalizedReview) -> dict:
    published_at = item.published_at.isoformat() if item.published_at else None
    return {
        "source_key": item.source_key,
        "external_id": item.external_id,
        "title": item.title,
        "text": item.text,
        "rating": item.rating,
        "author_hash": item.author_hash,
        "published_at": published_at,
        "app_version": item.app_version,
        "extra_metadata": item.extra_metadata,
        "content_hash": content_hash(item.source_key, item.text, item.title),
    }


def export_raw_snapshot(source_key: str, reviews: list[NormalizedReview]) -> Path:
    export_dir = Path(settings.raw_data_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"{source_key}.json"
    payload = {
        "source": source_key,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "count": len(reviews),
        "reviews": [_serialize_review(r) for r in reviews],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Exported %s raw reviews to %s", len(reviews), path)
    return path
