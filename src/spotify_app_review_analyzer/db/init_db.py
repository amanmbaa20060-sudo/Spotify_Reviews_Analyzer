from __future__ import annotations

import logging
from pathlib import Path

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db import models  # noqa: F401
from spotify_app_review_analyzer.db.base import Base
from spotify_app_review_analyzer.db.session import get_engine

logger = logging.getLogger(__name__)


def ensure_data_dir() -> Path:
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "", 1)
        data_dir = Path(db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path("data")


def init_database() -> None:
    ensure_data_dir()
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database initialized at %s", settings.database_url)
