"""Bootstrap local database and ingest raw review data."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from sqlalchemy import func, select

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.models import Review, Source
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.ingestion.cli import run_ingest

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def ensure_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if env_path.exists():
        return
    if not example_path.exists():
        raise FileNotFoundError("Missing .env.example")
    shutil.copy(example_path, env_path)
    logger.info("Created %s from .env.example", env_path)


def print_summary() -> None:
    session = get_session()
    try:
        total = session.scalar(select(func.count()).select_from(Review)) or 0
        rows = session.execute(
            select(Source.key, func.count(Review.id))
            .join(Review, Review.source_id == Source.id, isouter=True)
            .group_by(Source.key)
            .order_by(Source.key)
        ).all()
        print("\n=== Raw data summary ===")
        print(f"Database: {settings.database_url}")
        print(f"Total reviews: {total}")
        for key, count in rows:
            print(f"  - {key}: {count}")
        raw_dir = Path(settings.raw_data_export_dir)
        if raw_dir.exists():
            exports = list(raw_dir.glob("*.json"))
            print(f"JSON exports: {len(exports)} files in {raw_dir}")
            for export in sorted(exports):
                print(f"  - {export.name}")
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap DB and ingest raw Spotify review data.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max records per source (default: source-specific limits)",
    )
    parser.add_argument("--skip-ingest", action="store_true", help="Only init DB and .env")
    args = parser.parse_args(argv)

    configure_logging(settings.log_level)

    ensure_env_file()
    init_database()

    if args.skip_ingest:
        print_summary()
        return 0

    print("Starting raw data ingestion (App Store, Play Store, Reddit)...")
    exit_code = run_ingest(source="all", limit=args.limit, dry_run=False, export_json=True)
    print_summary()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
