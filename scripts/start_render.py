"""Production entrypoint for Render (binds 0.0.0.0:$PORT)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.deploy.seed import (
    auto_seed_enabled,
    resolve_raw_dir,
    review_count,
    run_production_seed_if_empty,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_migrations() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        logger.info("Alembic migrations applied")
        return
    logger.warning(
        "Alembic upgrade failed (exit %s): %s",
        result.returncode,
        result.stderr.strip() or result.stdout.strip(),
    )
    init_database()


if __name__ == "__main__":
    configure_logging(settings.log_level)
    _run_migrations()
    port = int(os.environ.get("PORT", "10000"))
    scheme = settings.database_url.split(":", 1)[0]
    logger.info("Starting API on 0.0.0.0:%s (database=%s)", port, scheme)

    if auto_seed_enabled() and review_count() == 0:
        raw_dir = resolve_raw_dir()
        logger.info("Empty database detected; seeding from %s before serving traffic", raw_dir)
        if not run_production_seed_if_empty():
            logger.error("Production seed did not complete; API will start with empty data")

    uvicorn.run(
        "spotify_app_review_analyzer.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
    )
