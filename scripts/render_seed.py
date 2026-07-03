"""Seed production Postgres from committed JSON snapshots when the DB is empty."""

from __future__ import annotations

import logging

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.deploy.seed import (
    RAW_DIR,
    auto_seed_enabled,
    review_count,
    run_production_seed_if_empty,
)

logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging(settings.log_level)

    if not auto_seed_enabled():
        logger.info("AUTO_SEED_IF_EMPTY is disabled; skipping seed.")
        return 0

    if review_count() > 0:
        logger.info("Database already has %s reviews; skipping seed.", review_count())
        return 0

    if not RAW_DIR.exists():
        logger.error("Missing snapshot directory: %s", RAW_DIR)
        return 1

    if run_production_seed_if_empty():
        return 0

    logger.error("Production seed failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
