from __future__ import annotations

import argparse
import logging
import sys

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.trends.service import TrendService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Social burst/trend report (Phase 5).")
    parser.add_argument("--days", type=int, default=settings.trend_window_days)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging(settings.log_level)
    args = build_parser().parse_args(argv)
    init_database()
    session = get_session()
    try:
        service = TrendService(session)
        md_path, json_path = service.export(days=args.days)
        report = service.build_report(days=args.days)
        print("\n=== Social trends ===")
        print(f"Processed social reviews: {report['social_processed_count']}")
        print(f"Burst signals: {len(report['burst_signals'])}")
        print(f"Rising themes: {len(report['rising_themes'])}")
        print(f"Exports: {md_path}, {json_path}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
