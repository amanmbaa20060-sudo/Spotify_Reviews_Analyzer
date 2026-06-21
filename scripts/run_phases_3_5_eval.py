"""Automated eval for Phases 3–5."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.models import AnalysisResult, Review, ReviewEmbedding, Source
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.ingestion.social_filter import is_spotify_relevant
from spotify_app_review_analyzer.trends.detection import SOCIAL_SOURCE_KEYS, detect_bursts
from spotify_app_review_analyzer.trends.detection import (
    compute_daily_theme_volumes,
    fetch_social_reviews,
)

EXPORT_DIR = Path(settings.validation_export_dir)
SOCIAL_KEYS = frozenset(SOCIAL_SOURCE_KEYS)


@dataclass
class Check:
    phase: str
    id: str
    name: str
    passed: bool
    detail: str = ""


@dataclass
class EvalReport:
    started_at: str
    checks: list[Check] = field(default_factory=list)
    finished_at: str = ""

    def add(self, check: Check) -> None:
        self.checks.append(check)

    def summary(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for check in self.checks:
            bucket = out.setdefault(check.phase, {"passed": 0, "failed": 0, "total": 0})
            bucket["total"] += 1
            if check.passed:
                bucket["passed"] += 1
            else:
                bucket["failed"] += 1
        return out

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "summary": self.summary(),
            "checks": [check.__dict__ for check in self.checks],
        }


def run_pytest() -> Check:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    passed = result.returncode == 0
    tail = (result.stdout or result.stderr).strip().splitlines()[-1] if result.returncode else ""
    return Check(
        "ALL",
        "pytest",
        "Unit/regression test suite",
        passed,
        tail or f"exit_code={result.returncode}",
    )


def eval_phase3(session) -> list[Check]:
    checks: list[Check] = []

    status_rows = dict(
        session.execute(select(Review.processing_status, func.count()).group_by(Review.processing_status)).all()
    )
    pending = status_rows.get("pending", 0)
    processed = status_rows.get("processed", 0)
    skipped = status_rows.get("skipped", 0)
    failed = status_rows.get("failed", 0)

    checks.append(
        Check(
            "3",
            "3.1",
            "No pending reviews (pipeline caught up)",
            pending == 0,
            f"pending={pending}, processed={processed}, skipped={skipped}, failed={failed}",
        )
    )

    missing_sentiment = session.scalar(
        select(func.count())
        .select_from(AnalysisResult)
        .where(AnalysisResult.sentiment.is_(None))
    ) or 0
    checks.append(
        Check(
            "3",
            "3.5",
            "100% processed records have sentiment",
            processed > 0 and missing_sentiment == 0,
            f"missing_sentiment={missing_sentiment}/{processed}",
        )
    )

    with_themes = session.scalar(
        select(func.count()).select_from(AnalysisResult).where(func.json_array_length(AnalysisResult.themes) > 0)
    )
    # SQLite may not support json_array_length — fallback in Python
    if with_themes is None:
        rows = session.scalars(select(AnalysisResult.themes)).all()
        with_themes = sum(1 for themes in rows if themes)

    theme_pct = (with_themes / processed * 100) if processed else 0
    checks.append(
        Check(
            "3",
            "3.6",
            ">=90% processed reviews have >=1 theme",
            theme_pct >= 90,
            f"{with_themes}/{processed} ({theme_pct:.1f}%)",
        )
    )

    with_rq = session.scalars(select(AnalysisResult.research_questions)).all()
    rq_count = sum(1 for rqs in with_rq if rqs)
    rq_pct = (rq_count / processed * 100) if processed else 0
    checks.append(
        Check(
            "3",
            "3.7",
            ">=70% processed reviews map to >=1 RQ",
            rq_pct >= 70,
            f"{rq_count}/{processed} ({rq_pct:.1f}%)",
        )
    )

    missing_conf = session.scalar(
        select(func.count()).select_from(AnalysisResult).where(AnalysisResult.confidence.is_(None))
    ) or 0
    checks.append(
        Check(
            "3",
            "3.8",
            "All analysis_results have confidence",
            missing_conf == 0,
            f"missing={missing_conf}",
        )
    )

    missing_model = session.scalar(
        select(func.count()).select_from(AnalysisResult).where(AnalysisResult.model_version.is_(None))
    ) or 0
    checks.append(
        Check(
            "3",
            "3.9",
            "model_version recorded on all analysis_results",
            missing_model == 0,
            f"version={settings.model_version}, missing={missing_model}",
        )
    )

    embedding_count = session.scalar(select(func.count()).select_from(ReviewEmbedding)) or 0
    checks.append(
        Check(
            "3",
            "3.14",
            "Embeddings stored for processed reviews",
            embedding_count >= processed and processed > 0,
            f"embeddings={embedding_count}, processed={processed}",
        )
    )

    tfidf_exists = Path(settings.embedding_model_dir, "tfidf_vectorizer.pkl").exists()
    checks.append(
        Check(
            "3",
            "3.15",
            "TF-IDF model persisted to disk",
            tfidf_exists,
            str(Path(settings.embedding_model_dir)),
        )
    )

    return checks


def eval_phase4(session) -> list[Check]:
    checks: list[Check] = []

    md_path = EXPORT_DIR / "rq_briefing.md"
    json_path = EXPORT_DIR / "rq_briefing.json"

    # Regenerate briefing
    result = subprocess.run(
        [sys.executable, "-m", "analyze", "--rq", "all"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    checks.append(
        Check(
            "4A",
            "EC-4A.1",
            "python -m analyze --rq all exports briefing",
            result.returncode == 0 and md_path.exists() and json_path.exists(),
            (result.stdout or "").strip()[-200:] or result.stderr[-200:],
        )
    )

    if json_path.exists():
        briefing = json.loads(json_path.read_text(encoding="utf-8"))
        sections_ok = True
        notes: list[str] = []
        for rq_id in RQ_IDS:
            section = next((s for s in briefing.get("sections", []) if s["rq_id"] == rq_id), None)
            if not section:
                sections_ok = False
                notes.append(f"{rq_id}: missing")
                continue
            ok = (
                len(section.get("top_themes", [])) > 0
                and bool(section.get("sentiment_mix"))
                and len(section.get("exemplar_citations", [])) >= 3
            )
            if not ok:
                sections_ok = False
            notes.append(
                f"{rq_id}: themes={len(section.get('top_themes', []))}, "
                f"exemplars={len(section.get('exemplar_citations', []))}"
            )
        checks.append(
            Check("4A", "EC-4A.2", "All 6 RQs have themes, sentiment, >=3 exemplars", sections_ok, "; ".join(notes))
        )
        verification = briefing.get("verification", {})
        checks.append(
            Check(
                "4A",
                "EC-4A.3",
                "Briefing counts match SQL verification",
                bool(verification.get("passed")),
                str(verification.get("mismatches", [])),
            )
        )

    audit_tables = session.scalar(
        select(func.count()).select_from(
            __import__("spotify_app_review_analyzer.db.models", fromlist=["AgentQuery"]).AgentQuery
        )
    )
    checks.append(
        Check(
            "4B",
            "4.12",
            "agent_queries audit log has records",
            (audit_tables or 0) > 0,
            f"rows={audit_tables or 0}",
        )
    )

    prompt_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "spotify_app_review_analyzer"
        / "agent"
        / "prompts"
        / "v1.0"
        / "system.md"
    )
    checks.append(
        Check("4B", "EC-4.6", "Versioned Groq prompt templates exist", prompt_path.exists(), str(prompt_path))
    )

    cli_exists = (Path(__file__).resolve().parent.parent / "src" / "agent" / "__main__.py").exists()
    checks.append(
        Check("4B", "EC-4.4", "Agent CLI available (python -m agent)", cli_exists, "ask|chat|golden|summarize")
    )

    if settings.groq_api_key:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "agent",
                "ask",
                "What are the most common frustrations with recommendations?",
                "--rq",
                "rq2",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
            timeout=120,
        )
        checks.append(
            Check(
                "4B",
                "4.4",
                "Groq agent answers RQ2 with citations",
                result.returncode == 0 and "Citations" in (result.stdout or ""),
                (result.stdout or result.stderr)[-300:],
            )
        )
    else:
        checks.append(
            Check(
                "4B",
                "4.4",
                "Groq agent answers RQ2 (skipped — no GROQ_API_KEY)",
                True,
                "Set GROQ_API_KEY to run live Groq check",
            )
        )

    return checks


def eval_phase5(session) -> list[Check]:
    checks: list[Check] = []

    by_source = dict(
        session.execute(
            select(Source.key, func.count(Review.id))
            .join(Review, Review.source_id == Source.id)
            .group_by(Source.key)
        ).all()
    )

    mastodon_count = by_source.get("mastodon", 0)
    reddit_count = by_source.get("reddit", 0)
    bluesky_count = by_source.get("bluesky", 0)

    checks.append(
        Check(
            "5",
            "5.1",
            "Mastodon ingests >=300 records",
            mastodon_count >= 300,
            f"mastodon={mastodon_count}",
        )
    )
    checks.append(
        Check(
            "5",
            "5.2",
            "Second social source >=300 records (Reddit fallback)",
            reddit_count >= 300 or bluesky_count >= 300,
            f"reddit={reddit_count}, bluesky={bluesky_count}",
        )
    )

    social_reviews = session.scalars(
        select(Review)
        .join(Source, Review.source_id == Source.id)
        .where(Source.key.in_(tuple(SOCIAL_KEYS)))
        .limit(5)
    ).all()
    has_engagement = all(
        (review.extra_metadata or {}).get("likes") is not None
        or (review.extra_metadata or {}).get("engagement_score") is not None
        or (review.extra_metadata or {}).get("score") is not None
        for review in social_reviews
    )
    checks.append(
        Check(
            "5",
            "5.4",
            "Social metadata includes engagement fields",
            bool(social_reviews) and has_engagement,
            f"sampled={len(social_reviews)}",
        )
    )

    # On-topic audit sample (mastodon)
    mastodon_sample = session.scalars(
        select(Review)
        .join(Source, Review.source_id == Source.id)
        .where(Source.key == "mastodon")
        .limit(200)
    ).all()
    if mastodon_sample:
        rng = random.Random(42)
        sample = mastodon_sample if len(mastodon_sample) <= 50 else rng.sample(mastodon_sample, 50)
        off_topic = sum(1 for r in sample if not is_spotify_relevant(r.text, from_hashtag="spotify"))
        off_rate = off_topic / len(sample) * 100
        checks.append(
            Check(
                "5",
                "5.5",
                "Mastodon sample off-topic rate <=30%",
                off_rate <= 30,
                f"off_topic={off_topic}/{len(sample)} ({off_rate:.1f}%)",
            )
        )

    social_processed = session.scalar(
        select(func.count())
        .select_from(Review)
        .join(Source, Review.source_id == Source.id)
        .where(Source.key.in_(tuple(SOCIAL_KEYS)), Review.processing_status == "processed")
    ) or 0
    social_with_analysis = session.scalar(
        select(func.count())
        .select_from(AnalysisResult)
        .join(Review, Review.id == AnalysisResult.review_id)
        .join(Source, Review.source_id == Source.id)
        .where(Source.key.in_(tuple(SOCIAL_KEYS)))
    ) or 0
    checks.append(
        Check(
            "5",
            "5.8",
            "Social records processed by Phase 3 pipeline",
            social_processed > 0 and social_with_analysis == social_processed,
            f"processed={social_processed}, analyzed={social_with_analysis}",
        )
    )

    viral_tagged = session.scalar(
        select(func.count())
        .select_from(Review)
        .join(Source, Review.source_id == Source.id)
        .where(
            Source.key == "mastodon",
            Review.extra_metadata.contains('"traffic_state"'),
        )
    )
    # SQLite JSON contains may not work — Python fallback
    if viral_tagged is None or viral_tagged == 0:
        mastodon_all = session.scalars(
            select(Review).join(Source, Review.source_id == Source.id).where(Source.key == "mastodon").limit(100)
        ).all()
        viral_tagged = sum(1 for r in mastodon_all if (r.extra_metadata or {}).get("traffic_state"))

    checks.append(
        Check(
            "5",
            "5.11",
            "Viral vs steady-state flags on social posts",
            viral_tagged > 0,
            f"tagged_sample={viral_tagged}",
        )
    )

    result = subprocess.run(
        [sys.executable, "-m", "trends", "--days", "7"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    trends_json = EXPORT_DIR / "social_trends.json"
    rising_ok = False
    if trends_json.exists():
        report = json.loads(trends_json.read_text(encoding="utf-8"))
        rising_ok = len(report.get("rising_themes", [])) > 0
    checks.append(
        Check(
            "5",
            "5.12",
            "Trend report lists rising themes",
            result.returncode == 0 and rising_ok,
            f"rising={len(json.loads(trends_json.read_text()).get('rising_themes', [])) if trends_json.exists() else 0}",
        )
    )

    # Burst detection logic (unit-level sanity on live data)
    social = fetch_social_reviews(session, days=7)
    volumes = compute_daily_theme_volumes(social, days=7)
    bursts = detect_bursts(volumes, threshold=2.0)
    checks.append(
        Check(
            "5",
            "5.10",
            "Burst detection module runs (spikes optional in window)",
            len(volumes) > 0,
            f"daily_volume_rows={len(volumes)}, bursts={len(bursts)}",
        )
    )

    total_social = sum(by_source.get(k, 0) for k in SOCIAL_KEYS)
    checks.append(
        Check(
            "5",
            "EC-5.2",
            ">=600 total social records ingested",
            total_social >= 600,
            f"total_social={total_social} (mastodon={mastodon_count}, reddit={reddit_count}, bluesky={bluesky_count})",
        )
    )

    dec_path = Path(__file__).resolve().parent.parent / "docs" / "decision.md"
    dec_ok = dec_path.exists() and "DEC-006" in dec_path.read_text(encoding="utf-8") and "Accepted" in dec_path.read_text(encoding="utf-8")
    checks.append(
        Check("5", "EC-5.6", "DEC-006 finalized in decision.md", dec_ok, "Mastodon + Bluesky priority"),
    )

    return checks


def main() -> int:
    configure_logging(settings.log_level)
    init_database()
    session = get_session()
    report = EvalReport(started_at=datetime.now(UTC).isoformat())

    print("=== Phases 3-5 Eval ===\n")

    print("[pytest] Running test suite...")
    report.add(run_pytest())

    print("[Phase 3] Checking processing pipeline...")
    for check in eval_phase3(session):
        report.add(check)

    print("[Phase 4] Checking RQ briefing + agent...")
    for check in eval_phase4(session):
        report.add(check)

    print("[Phase 5] Checking social sources + trends...")
    for check in eval_phase5(session):
        report.add(check)

    report.finished_at = datetime.now(UTC).isoformat()
    out_path = EXPORT_DIR / "phases_3_5_eval_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

    print("\n=== Results ===\n")
    for phase in ["ALL", "3", "4A", "4B", "5"]:
        phase_checks = [c for c in report.checks if c.phase == phase]
        if not phase_checks:
            continue
        passed = sum(1 for c in phase_checks if c.passed)
        print(f"## Phase {phase}: {passed}/{len(phase_checks)} passed")
        for check in phase_checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"  [{status}] {check.id}: {check.name}")
            if check.detail:
                print(f"          {check.detail[:160]}")
        print()

    summary = report.summary()
    total_passed = sum(s["passed"] for s in summary.values())
    total_checks = sum(s["total"] for s in summary.values())
    print(f"Overall: {total_passed}/{total_checks} checks passed")
    print(f"Report: {out_path}")

    session.close()
    return 0 if all(c.passed for c in report.checks) else 1


if __name__ == "__main__":
    sys.exit(main())
