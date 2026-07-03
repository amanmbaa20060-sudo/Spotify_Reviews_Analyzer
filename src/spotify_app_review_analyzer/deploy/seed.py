"""Production bootstrap: import snapshots, process, and analyze when the DB is empty."""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from sqlalchemy import func, select

from spotify_app_review_analyzer.analytics.service import RQAnalysisService
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.models import Review
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.ingestion.service import IngestService
from spotify_app_review_analyzer.ingestion.snapshot import SnapshotProvider, load_snapshot
from spotify_app_review_analyzer.processing.service import ProcessingService

logger = logging.getLogger(__name__)

_seed_lock = threading.Lock()
_seeding = False
_seed_complete = False
_last_seed_error: str | None = None


def resolve_raw_dir() -> Path:
    """Locate committed JSON snapshots in dev and on Render after pip install."""
    env_dir = os.getenv("RAW_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    for candidate in (Path.cwd(), *Path(__file__).resolve().parents):
        raw_dir = candidate / "data" / "raw"
        if raw_dir.is_dir() and any(raw_dir.glob("*.json")):
            return raw_dir

    return Path.cwd() / "data" / "raw"


def auto_seed_enabled() -> bool:
    explicit = os.getenv("AUTO_SEED_IF_EMPTY")
    if explicit is not None and explicit.strip():
        return explicit.lower() in {"1", "true", "yes"}
    return os.getenv("RENDER") == "true"


def last_seed_error() -> str | None:
    return _last_seed_error


def is_seeding() -> bool:
    return _seeding


def seed_completed() -> bool:
    if _seed_complete:
        return True
    return not bootstrap_needed()


def review_count() -> int:
    session = get_session()
    try:
        return session.scalar(select(func.count()).select_from(Review)) or 0
    finally:
        session.close()


def pending_review_count() -> int:
    session = get_session()
    try:
        return (
            session.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.processing_status == "pending")
            )
            or 0
        )
    finally:
        session.close()


def bootstrap_needed() -> bool:
    total = review_count()
    if total == 0:
        return True
    return pending_review_count() > 0


def import_snapshots(session) -> int:
    raw_dir = resolve_raw_dir()
    service = IngestService(session)
    service.ensure_sources(commit=True)
    inserted = 0

    for path in sorted(raw_dir.glob("*.json")):
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
    total_processed = 0
    while True:
        metrics = service.process_batch(batch_size=settings.processing_batch_size, force=False)
        if metrics.fetched == 0:
            break
        total_processed += metrics.processed
        session.commit()
        logger.info(
            "Committed processing batch: fetched=%s processed=%s (running total=%s)",
            metrics.fetched,
            metrics.processed,
            total_processed,
        )
    embedded = service.rebuild_all_embeddings()
    session.commit()
    logger.info("Processing complete; rebuilt embeddings for %s reviews", embedded)


def run_production_seed_if_empty() -> bool:
    """Import snapshots, process pending reviews, and build RQ briefings when needed.

    Returns True if bootstrap work ran, False if skipped.
    """
    global _seeding, _seed_complete, _last_seed_error

    if not auto_seed_enabled():
        logger.info("AUTO_SEED_IF_EMPTY is disabled; skipping seed.")
        return False

    with _seed_lock:
        if _seed_complete:
            return False

        raw_dir = resolve_raw_dir()
        session = get_session()
        try:
            init_database()
            existing = session.scalar(select(func.count()).select_from(Review)) or 0
            pending = (
                session.scalar(
                    select(func.count())
                    .select_from(Review)
                    .where(Review.processing_status == "pending")
                )
                or 0
            )

            if existing > 0 and pending == 0:
                logger.info("Database has %s processed reviews; skipping bootstrap.", existing)
                _seed_complete = True
                _last_seed_error = None
                return False

            _seeding = True
            _last_seed_error = None

            if existing == 0:
                if not raw_dir.is_dir() or not any(raw_dir.glob("*.json")):
                    _last_seed_error = f"Missing snapshot JSON files in {raw_dir}"
                    logger.error(_last_seed_error)
                    return False

                logger.info("Seeding empty database from %s", raw_dir)
                inserted = import_snapshots(session)
                logger.info("Imported %s new reviews from snapshots", inserted)
            else:
                logger.info(
                    "Resuming bootstrap for %s pending reviews (of %s total)",
                    pending,
                    existing,
                )

            process_all(session)

            pending_after = pending_review_count()
            if pending_after > 0:
                _last_seed_error = f"{pending_after} reviews still pending after processing"
                logger.error(_last_seed_error)
                return False

            try:
                RQAnalysisService(session).run(export=False)
                session.commit()
                logger.info("RQ briefing built in database context (exports skipped).")
                _last_seed_error = None
            except Exception as exc:
                session.rollback()
                _last_seed_error = f"RQ briefing failed: {exc}"
                logger.exception("RQ briefing failed after processing completed")
            _seed_complete = True
            return True
        except Exception as exc:
            session.rollback()
            _last_seed_error = str(exc)
            logger.exception("Production seed failed")
            return False
        finally:
            _seeding = False
            session.close()


def start_background_seed_if_empty() -> bool:
    """Kick off bootstrap in a daemon thread when the database needs work."""
    if not auto_seed_enabled() or _seeding:
        return False

    if not bootstrap_needed():
        return False

    def _run() -> None:
        attempts = 0
        while bootstrap_needed() and attempts < 5:
            run_production_seed_if_empty()
            if not bootstrap_needed():
                break
            attempts += 1
            time.sleep(5)

    threading.Thread(target=_run, name="production-seed", daemon=True).start()
    logger.warning("Bootstrap started in background from %s", resolve_raw_dir())
    return True
