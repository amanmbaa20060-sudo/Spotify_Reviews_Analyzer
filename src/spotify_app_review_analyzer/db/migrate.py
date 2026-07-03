from __future__ import annotations

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def resolve_project_root() -> Path:
    """Find the repo root that contains alembic.ini (works after pip install on Render)."""
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root)

    for candidate in (Path.cwd(), *Path(__file__).resolve().parents):
        if (candidate / "alembic.ini").is_file():
            return candidate

    return Path.cwd()


def run_migrations() -> bool:
    """Apply Alembic migrations using the repo alembic.ini.

    Returns True on success, False if alembic.ini cannot be found or upgrade fails.
    """
    project_root = resolve_project_root()
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.is_file():
        logger.error("alembic.ini not found under %s", project_root)
        return False

    try:
        config = Config(str(alembic_ini))
        command.upgrade(config, "head")
        logger.info("Alembic migrations applied from %s", alembic_ini)
        return True
    except Exception:
        logger.exception("Alembic upgrade failed")
        return False
