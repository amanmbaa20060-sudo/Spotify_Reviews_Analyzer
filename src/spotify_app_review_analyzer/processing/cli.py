from __future__ import annotations

import argparse
import logging
import sys

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.processing.service import ProcessingService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process pending reviews (Phase 3 pipeline).")
    parser.add_argument("--batch-size", type=int, default=settings.processing_batch_size)
    parser.add_argument("--force", action="store_true", help="Reprocess already-processed reviews")
    parser.add_argument(
        "--loop",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep processing pending reviews until none remain (default: on)",
    )
    parser.add_argument(
        "--export-validation",
        action="store_true",
        help="Export PM validation CSV after processing",
    )
    parser.add_argument("--search", type=str, default=None, help="Run semantic search query")
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def run_process(
    *,
    batch_size: int,
    force: bool,
    loop: bool,
    export_validation: bool,
    search: str | None,
    top_k: int,
) -> int:
    configure_logging(settings.log_level)
    init_database()
    session = get_session()
    exit_code = 0

    try:
        service = ProcessingService(session)

        if search:
            hits = service.semantic_search(search, top_k=top_k)
            print(f"\nSemantic search: {search!r}")
            for idx, hit in enumerate(hits, start=1):
                print(f"{idx}. score={hit['score']} id={hit['review_id']}")
                print(f"   {hit['text']}\n")
            return 0

        while True:
            metrics = service.process_batch(batch_size=batch_size, force=force)
            if metrics.failed:
                exit_code = 1
            if not loop or metrics.fetched == 0:
                break
            force = False

        if search is None:
            embedded = service.rebuild_all_embeddings()
            session.commit()
            logger.info("Rebuilt embeddings for %s reviews", embedded)

        counts = service.status_counts()
        print("\n=== Processing status ===")
        for status, count in sorted(counts.items()):
            print(f"  {status}: {count}")

        if export_validation:
            path = service.export_validation_sample()
            print(f"Validation export: {path}")

        session.commit()
    finally:
        session.close()

    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_process(
        batch_size=args.batch_size,
        force=args.force,
        loop=args.loop,
        export_validation=args.export_validation,
        search=args.search,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    sys.exit(main())
