"""Production entrypoint for Render (binds 0.0.0.0:$PORT)."""

from __future__ import annotations

import logging
import os

import uvicorn

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.migrate import run_migrations

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    configure_logging(settings.log_level)
    if not run_migrations():
        logger.warning("Continuing without Alembic upgrade; preDeploy may have already applied it")

    port = int(os.environ.get("PORT", "10000"))
    scheme = settings.database_url.split(":", 1)[0]
    logger.info("Starting API on 0.0.0.0:%s (database=%s)", port, scheme)
    logger.info("Bootstrap runs in the background after the API starts when reviews are pending")

    uvicorn.run(
        "spotify_app_review_analyzer.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
    )
