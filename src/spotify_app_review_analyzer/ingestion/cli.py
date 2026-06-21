from __future__ import annotations

import argparse
import logging
import sys

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.ingestion.service import IngestService
from spotify_app_review_analyzer.ingestion.sources import (
    AppStoreProvider,
    BlueskyProvider,
    MastodonProvider,
    PlayStoreProvider,
    RedditProvider,
)

logger = logging.getLogger(__name__)

PROVIDERS = {
    "app_store": AppStoreProvider,
    "play_store": PlayStoreProvider,
    "reddit": RedditProvider,
    "mastodon": MastodonProvider,
    "bluesky": BlueskyProvider,
}

SOCIAL_PROVIDERS = ("mastodon", "bluesky", "reddit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest Spotify app reviews from public sources.")
    parser.add_argument(
        "--source",
        choices=["all", "social", *PROVIDERS.keys()],
        default="all",
        help="Source to ingest: all, social (mastodon+bluesky+reddit), or a single source",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max records per source")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count without writing")
    parser.add_argument(
        "--export-json",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Export fetched reviews to data/raw/*.json (default: on)",
    )
    return parser


def run_ingest(
    *,
    source: str,
    limit: int | None,
    dry_run: bool,
    export_json: bool = True,
) -> int:
    configure_logging(settings.log_level)
    keys = list(PROVIDERS.keys()) if source == "all" else list(SOCIAL_PROVIDERS) if source == "social" else [source]
    session = get_session()
    exit_code = 0

    try:
        service = IngestService(session)
        for key in keys:
            provider = PROVIDERS[key]()
            metrics = service.ingest_provider(
                provider,
                limit=limit,
                dry_run=dry_run,
                export_json=export_json,
            )
            if metrics.failed:
                exit_code = 1
        if not dry_run:
            session.commit()
    finally:
        session.close()

    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_ingest(
        source=args.source,
        limit=args.limit,
        dry_run=args.dry_run,
        export_json=args.export_json,
    )


if __name__ == "__main__":
    sys.exit(main())
