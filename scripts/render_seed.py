"""Seed production Postgres from committed JSON snapshots when the DB is empty."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import func, select

from spotify_app_review_analyzer.analytics.service import RQAnalysisService
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.models import Review
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.ingestion.service import IngestService
from spotify_app_review_analyzer.ingestion.snapshot import SnapshotProvider, load_snapshot
from spotify_app_review_analyzer.processing.service import ProcessingService

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _auto_seed_enabled() -> bool:
    return os.getenv("AUTO_SEED_IF_EMPTY", "false").lower() in {"1", "true", "yes"}


def import_snapshots(session) -> int:
    service = IngestService(session)
    service.ensure_sources(commit=True)
    inserted = 0

    for path in sorted(RAW_DIR.glob("*.json")):
        reviews = load_snapshot(path)
        if not reviews:
            continue
        source_key = reviews[0].source_key
        metrics = service.ingest_provider(
            SnapshotProvider(source_key, reviews),
            dry_run=False,
            export_json=False,
        )
        inserted += metrics.inserted
        logger.info(
            "Snapshot %s: fetched=%s inserted=%s skipped=%s",
            path.name,
            metrics.fetched,
            metrics.inserted,
            metrics.skipped,
        )

    session.commit()
    return inserted


def process_all(session) -> None:
    service = ProcessingService(session)
    while True:
        metrics = service.process_batch(batch_size=settings.processing_batch_size, force=False)
        if metrics.fetched == 0:
            break
    embedded = service.rebuild_all_embeddings()
    session.commit()
    logger.info("Processing complete; rebuilt embeddings for %s reviews", embedded)


def main() -> int:
    configure_logging(settings.log_level)

    if not _auto_seed_enabled():
        logger.info("AUTO_SEED_IF_EMPTY is disabled; skipping seed.")
        return 0

    session = get_session()
    try:
        init_database()
        existing = session.scalar(select(func.count()).select_from(Review)) or 0
        if existing > 0:
            logger.info("Database already has %s reviews; skipping seed.", existing)
            return 0

        if not RAW_DIR.exists():
            logger.error("Missing snapshot directory: %s", RAW_DIR)
            return 1

        logger.info("Seeding empty database from %s", RAW_DIR)
        inserted = import_snapshots(session)
        logger.info("Imported %s new reviews from snapshots", inserted)

        process_all(session)

        RQAnalysisService(session).run(export=False)
        session.commit()
        logger.info("RQ briefing built in database context (exports skipped).")
        return 0
    except Exception:
        session.rollback()
        logger.exception("Production seed failed")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
