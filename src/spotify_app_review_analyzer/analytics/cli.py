from __future__ import annotations

import argparse
import logging
import sys

from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.analytics.service import RQAnalysisService
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.session import get_session

logger = logging.getLogger(__name__)


def _parse_rq_list(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(RQ_IDS)
    rqs = [part.strip().lower() for part in value.split(",") if part.strip()]
    invalid = [rq for rq in rqs if rq not in RQ_IDS]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Unknown RQ ids: {', '.join(invalid)}. Use rq1–rq6 or 'all'."
        )
    return rqs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build deterministic RQ briefings from Phase 3 analysis (Phase 4A)."
    )
    parser.add_argument(
        "--rq",
        type=_parse_rq_list,
        default="all",
        help="Comma-separated RQ ids (rq1,rq2) or 'all' (default)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Build briefing in memory only; do not write export files",
    )
    return parser


def run_analyze(*, rq_ids: list[str], export: bool) -> int:
    configure_logging(settings.log_level)
    init_database()
    session = get_session()
    exit_code = 0

    try:
        service = RQAnalysisService(session)
        briefing = service.run(rq_ids=rq_ids, export=export)

        print("\n=== RQ Briefing ===")
        print(f"Processed reviews: {briefing.total_processed_reviews}")
        for section in briefing.sections:
            print(
                f"  {section.rq_id}: {section.review_count} reviews, "
                f"readiness={section.readiness}, "
                f"exemplars={len(section.exemplar_citations)}"
            )

        verification = briefing.verification
        if verification:
            if verification.get("passed"):
                print("\nVerification: PASSED (counts match SQL)")
            else:
                print("\nVerification: FAILED")
                for mismatch in verification.get("mismatches", []):
                    print(f"  {mismatch}")
                exit_code = 1

        if export:
            out_dir = settings.validation_export_dir
            print(f"\nExports: {out_dir}/rq_briefing.md, {out_dir}/rq_briefing.json")
    finally:
        session.close()

    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_analyze(rq_ids=args.rq, export=not args.no_export)


if __name__ == "__main__":
    sys.exit(main())
