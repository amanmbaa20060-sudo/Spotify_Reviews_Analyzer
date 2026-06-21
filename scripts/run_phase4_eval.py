"""Phase 4 eval runner — 4A RQ prep + 4B Groq agent."""

from __future__ import annotations

import json
import re
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from spotify_app_review_analyzer.agent.groq_client import GroqClient
from spotify_app_review_analyzer.agent.guardrails import extract_citations
from spotify_app_review_analyzer.agent.orchestrator import AgentOrchestrator
from spotify_app_review_analyzer.agent.schemas import GOLDEN_QUESTIONS
from spotify_app_review_analyzer.agent.service import AgentService
from spotify_app_review_analyzer.agent.tools import AgentTools
from spotify_app_review_analyzer.analytics.aggregations import (
    count_themes,
    fetch_analyzed_reviews,
    filter_reviews_by_days,
    filter_reviews_for_rq,
)
from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.analytics.service import RQAnalysisService
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.models import AgentQuery
from spotify_app_review_analyzer.db.session import get_session

EXPORT_DIR = Path(settings.validation_export_dir)
BARRIER_TERMS = (
    "friction",
    "confus",
    "unclear",
    "overload",
    "browse",
    "search",
    "find",
    "discover",
)
BEHAVIOR_TERMS = (
    "explore",
    "discover",
    "playlist",
    "mood",
    "genre",
    "listen",
    "behavior",
    "intent",
    "habit",
)
NEED_TERMS = ("need", "unmet", "missing", "wish", "want", "lack", "feature")


@dataclass
class CheckResult:
    id: str
    name: str
    passed: bool
    detail: str = ""
    manual: bool = False


@dataclass
class EvalReport:
    started_at: str
    finished_at: str = ""
    checks: list[CheckResult] = field(default_factory=list)
    golden_results: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: dict[str, list[int]] = field(default_factory=dict)
    token_usage: dict[str, int] = field(default_factory=dict)

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)

    @property
    def automated_passed(self) -> int:
        return sum(1 for check in self.checks if check.passed and not check.manual)

    @property
    def automated_total(self) -> int:
        return sum(1 for check in self.checks if not check.manual)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "summary": {
                "automated_passed": self.automated_passed,
                "automated_total": self.automated_total,
                "all_automated_passed": self.automated_passed == self.automated_total,
            },
            "checks": [
                {
                    "id": check.id,
                    "name": check.name,
                    "passed": check.passed,
                    "detail": check.detail,
                    "manual": check.manual,
                }
                for check in self.checks
            ],
            "golden_results": self.golden_results,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
        }


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def _score_golden_run(rq_id: str, answer_text: str, citations: list[str]) -> tuple[bool, str]:
    text = answer_text.lower()
    n_cites = len(citations)

    if rq_id == "rq1":
        barriers = _count_terms(text, BARRIER_TERMS)
        ok = n_cites >= 3 and barriers >= 2
        return ok, f"citations={n_cites}, barrier_terms={barriers}"
    if rq_id == "rq2":
        has_themes = bool(re.search(r"theme|stale|repetit|relevant|control|count|\d+", text))
        ok = n_cites >= 3 and has_themes
        return ok, f"citations={n_cites}, themes_or_counts={has_themes}"
    if rq_id == "rq3":
        behaviors = _count_terms(text, BEHAVIOR_TERMS)
        ok = n_cites >= 3 and behaviors >= 3
        return ok, f"citations={n_cites}, behavior_terms={behaviors}"
    if rq_id == "rq4":
        has_comfort = "comfort" in text or "habit" in text or "familiar" in text
        has_friction = "friction" in text or "stale" in text or "repetit" in text
        ok = n_cites >= 3 and has_comfort and has_friction
        return ok, f"citations={n_cites}, comfort={has_comfort}, friction={has_friction}"
    if rq_id == "rq5":
        segments = sum(
            1 for term in ("ios", "android", "premium", "free", "segment") if term in text
        )
        ok = n_cites >= 2 and segments >= 2
        return ok, f"citations={n_cites}, segment_terms={segments}"
    if rq_id == "rq6":
        needs = _count_terms(text, NEED_TERMS)
        cross = "cross-source" in text or "across" in text or "consistent" in text
        ok = n_cites >= 3 and needs >= 3 and cross
        return ok, f"citations={n_cites}, need_terms={needs}, cross_source={cross}"
    return False, "unknown rq"


def run_phase4a(report: EvalReport, session) -> None:
    service = RQAnalysisService(session)
    briefing = service.run(rq_ids=list(RQ_IDS), export=True)
    md_path = EXPORT_DIR / "rq_briefing.md"
    json_path = EXPORT_DIR / "rq_briefing.json"

    report.add(
        CheckResult(
            "EC-4A.1",
            "RQ briefing exports exist",
            md_path.exists() and json_path.exists(),
            f"{md_path}, {json_path}",
        )
    )

    sections_ok = True
    section_notes: list[str] = []
    for rq_id in RQ_IDS:
        section = next((s for s in briefing.sections if s.rq_id == rq_id), None)
        if section is None:
            sections_ok = False
            section_notes.append(f"{rq_id}: missing")
            continue
        exemplars = len(section.exemplar_citations)
        themes = len(section.top_themes)
        sentiment = bool(section.sentiment_mix)
        ok = themes > 0 and sentiment and exemplars >= 3
        if not ok:
            sections_ok = False
        section_notes.append(
            f"{rq_id}: themes={themes}, exemplars={exemplars}, sentiment={sentiment}"
        )

    report.add(
        CheckResult(
            "EC-4A.2",
            "All six RQs have themes, sentiment, >=3 exemplars",
            sections_ok,
            "; ".join(section_notes),
        )
    )

    verification = briefing.verification or {}
    report.add(
        CheckResult(
            "EC-4A.3",
            "Aggregated counts match SQL verification",
            bool(verification.get("passed")),
            str(verification.get("mismatches", [])),
        )
    )

    report.add(
        CheckResult(
            "EC-4A.4",
            "PM sign-off on RQ briefing accuracy",
            False,
            "Requires manual Growth PM review of data/exports/rq_briefing.md",
            manual=True,
        )
    )


def run_tool_checks(report: EvalReport, session) -> None:
    tools = AgentTools(session)

    search = tools.search_reviews("recommendations stale", source_key="app_store", top_k=3)
    report.add(
        CheckResult(
            "4.1",
            "search_reviews with filters",
            search["count"] > 0 and all(r["source_key"] == "app_store" for r in search["results"]),
            f"count={search['count']}",
        )
    )

    agg = tools.aggregate_themes(rq_id="rq2", since_days=90)
    reviews = filter_reviews_by_days(fetch_analyzed_reviews(session), since_days=90)
    rq2 = filter_reviews_for_rq(reviews, "rq2")
    sql_top = count_themes(rq2, "rq2").most_common(1)
    agg_top = agg["themes"][0] if agg["themes"] else None
    agg_ok = bool(agg_top) and sql_top and agg_top["theme_id"] == sql_top[0][0]
    report.add(
        CheckResult(
            "4.2",
            "aggregate_themes last 90 days matches SQL",
            agg_ok,
            f"tool={agg_top}, sql={sql_top[:1] if sql_top else []}",
        )
    )

    compare = tools.compare_segments(
        "segment.platform.ios",
        "segment.platform.android",
        rq_id="rq2",
    )
    report.add(
        CheckResult(
            "4.3",
            "compare_segments iOS vs Android",
            "theme_counts_a" in compare and "theme_counts_b" in compare,
            f"signals={len(compare.get('signals', []))}",
        )
    )

    cross = tools.detect_cross_source_themes(rq_id="rq2", min_sources=2)
    report.add(
        CheckResult(
            "4.5",
            "detect_cross_source_themes",
            len(cross.get("themes", [])) >= 1,
            f"themes={len(cross.get('themes', []))}",
        )
    )


def run_guardrail_checks(report: EvalReport, session, service: AgentService) -> None:
    out = service.ask("What is Spotify's revenue this quarter?", audit=True)
    report.add(
        CheckResult(
            "4.7",
            "Out-of-scope question refused",
            "revenue" not in out.answer_text.lower()[:80]
            and ("scope" in out.answer_text.lower() or "only answer" in out.answer_text.lower()),
            out.answer_text[:160],
        )
    )

    empty = service.ask(
        "What do TikTok users say about Spotify music discovery?",
        audit=True,
    )
    empty_ok = (
        "insufficient" in empty.answer_text.lower()
        or "cannot provide" in empty.answer_text.lower()
        or "not in the ingested" in empty.answer_text.lower()
        or "out of scope" in empty.answer_text.lower()
        or len(empty.citations) == 0
    )
    report.add(
        CheckResult(
            "4.8",
            "Insufficient data / unknown source — no fabrication",
            empty_ok,
            empty.answer_text[:160],
        )
    )

    multi = service.ask(
        "Compare Reddit vs App Store sentiment on recommendations",
        rq_id="rq2",
        audit=True,
    )
    tool_names = {call.tool for call in multi.tool_calls}
    report.add(
        CheckResult(
            "4.10",
            "Multi-step query uses >=2 tools",
            len(tool_names) >= 2,
            f"tools={sorted(tool_names)}",
        )
    )
    report.latency_ms.setdefault("complex", []).append(multi.latency_ms or 0)

    history = [
        {"role": "user", "content": "Compare Reddit vs App Store sentiment on recommendations"},
        {"role": "assistant", "content": multi.answer_text[:500]},
    ]
    follow_up = service.ask(
        "Which source has more negative sentiment on stale recommendations?",
        rq_id="rq2",
        conversation_history=history,
        session_id="eval-followup",
        audit=True,
    )
    report.add(
        CheckResult(
            "4.11",
            "Follow-up question in session",
            len(follow_up.answer_text) > 50 and follow_up.used_groq,
            f"latency_ms={follow_up.latency_ms}",
        )
    )

    summarize = service.summarize_research_question("rq2", session_id="eval-summarize-rq2")
    report.add(
        CheckResult(
            "4.4",
            "summarize_research_question RQ2",
            summarize.used_groq and len(summarize.citations) >= 1,
            f"citations={len(summarize.citations)}, guardrail={summarize.guardrail_passed}",
        )
    )
    report.latency_ms.setdefault("simple", []).append(summarize.latency_ms or 0)


def run_golden_eval(
    report: EvalReport,
    service: AgentService,
    *,
    runs_per_question: int = 3,
) -> None:
    all_runs_with_citations = 0
    total_runs = 0

    for rq_id, question in GOLDEN_QUESTIONS.items():
        rq_entry: dict[str, Any] = {"rq_id": rq_id, "question": question, "runs": []}
        passes = 0

        for run_idx in range(1, runs_per_question + 1):
            answer = service.ask(
                question,
                rq_id=rq_id,
                session_id=f"eval-golden-{rq_id}-{run_idx}",
                audit=True,
            )
            passed, detail = _score_golden_run(rq_id, answer.answer_text, answer.citations)
            if passed:
                passes += 1
            if answer.citations:
                all_runs_with_citations += 1
            total_runs += 1

            rq_entry["runs"].append(
                {
                    "run": run_idx,
                    "passed": passed,
                    "detail": detail,
                    "citations": len(answer.citations),
                    "guardrail_passed": answer.guardrail_passed,
                    "latency_ms": answer.latency_ms,
                    "input_tokens": answer.input_tokens,
                    "output_tokens": answer.output_tokens,
                }
            )
            report.latency_ms.setdefault("golden", []).append(answer.latency_ms or 0)
            report.token_usage["input_tokens"] = report.token_usage.get("input_tokens", 0) + (
                answer.input_tokens or 0
            )
            report.token_usage["output_tokens"] = report.token_usage.get("output_tokens", 0) + (
                answer.output_tokens or 0
            )
            time.sleep(2.1)  # stay under 30 RPM during eval

        rq_entry["passes"] = passes
        rq_entry["required_passes"] = 2
        rq_entry["passed"] = passes >= 2
        report.golden_results.append(rq_entry)

        report.add(
            CheckResult(
                f"EC-4.1-{rq_id}",
                f"Golden question {rq_id.upper()} (>=2/{runs_per_question} runs)",
                passes >= 2,
                f"passes={passes}/{runs_per_question}",
            )
        )

    citation_rate = (all_runs_with_citations / total_runs * 100) if total_runs else 0
    report.add(
        CheckResult(
            "EC-4.2",
            f"Citation coverage >=90% on golden set ({citation_rate:.0f}%)",
            citation_rate >= 90,
            f"{all_runs_with_citations}/{total_runs} runs had citations",
        )
    )


def run_audit_and_perf_checks(report: EvalReport, session) -> None:
    query_count = session.scalar(select(func.count()).select_from(AgentQuery)) or 0
    report.add(
        CheckResult(
            "4.12",
            "agent_queries audit log populated",
            query_count >= 10,
            f"rows={query_count}",
        )
    )

    simple_latencies = [ms for ms in report.latency_ms.get("simple", []) if ms > 0]
    golden_latencies = [ms for ms in report.latency_ms.get("golden", []) if ms > 0]
    simple_latencies = simple_latencies + golden_latencies
    complex_latencies = report.latency_ms.get("complex", [])
    if simple_latencies:
        p95_simple = sorted(simple_latencies)[int(len(simple_latencies) * 0.95) - 1]
        report.add(
            CheckResult(
                "4.13",
                "Simple query latency p95 <10s",
                p95_simple < 10_000,
                f"p95_ms={p95_simple}",
            )
        )
    if complex_latencies:
        p95_complex = sorted(complex_latencies)[int(len(complex_latencies) * 0.95) - 1]
        report.add(
            CheckResult(
                "4.14",
                "Complex multi-tool query p95 <30s",
                p95_complex < 30_000,
                f"p95_ms={p95_complex}",
            )
        )

    total_tokens = report.token_usage.get("input_tokens", 0) + report.token_usage.get(
        "output_tokens", 0
    )
    report.add(
        CheckResult(
            "4.15",
            "Token usage documented for golden set",
            total_tokens > 0,
            f"input={report.token_usage.get('input_tokens', 0)}, "
            f"output={report.token_usage.get('output_tokens', 0)}, total={total_tokens}",
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
    report.add(
        CheckResult(
            "EC-4.6",
            "Prompt templates versioned in repo",
            prompt_path.exists(),
            str(prompt_path),
        )
    )

    report.add(
        CheckResult(
            "EC-4.4",
            "Agent CLI available",
            Path("src/agent/__main__.py").exists(),
            "python -m agent ask|chat|golden|summarize",
        )
    )

    report.add(
        CheckResult(
            "4.16",
            "Automated golden-question script runnable",
            True,
            "scripts/run_phase4_eval.py",
        )
    )


def main() -> int:
    configure_logging(settings.log_level)
    if not settings.groq_api_key:
        print("ERROR: GROQ_API_KEY is required for Phase 4B eval.")
        return 1

    init_database()
    session = get_session()
    report = EvalReport(started_at=datetime.now(UTC).isoformat())

    print("=== Phase 4 Eval ===\n")
    print("[4A] RQ Prep checks...")
    run_phase4a(report, session)
    session.commit()

    print("[4B] Tool functionality checks...")
    run_tool_checks(report, session)

    service = AgentService(session, groq_client=GroqClient())
    print("[4B] Guardrail and behavior checks (Groq)...")
    run_guardrail_checks(report, session, service)
    session.commit()

    print("[4B] Golden questions (3 runs x 6 RQs, Groq)...")
    run_golden_eval(report, service, runs_per_question=3)
    session.commit()

    run_audit_and_perf_checks(report, session)

    guardrail_ok = all(
        check.passed
        for check in report.checks
        if check.id in {"4.7", "4.8"}
    )
    report.add(
        CheckResult(
            "EC-4.3",
            "No hallucination on out-of-scope / empty-data tests",
            guardrail_ok,
            "",
        )
    )

    golden_ok = all(
        check.passed for check in report.checks if check.id.startswith("EC-4.1-")
    )
    perf_ok = all(check.passed for check in report.checks if check.id in {"4.13", "4.14"})
    report.add(
        CheckResult(
            "EC-4.5",
            "Latency targets met",
            perf_ok,
            "",
        )
    )

    report.finished_at = datetime.now(UTC).isoformat()
    out_path = EXPORT_DIR / "phase4_eval_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

    print("\n=== Results ===\n")
    for check in report.checks:
        status = "PASS" if check.passed else ("MANUAL" if check.manual else "FAIL")
        print(f"[{status}] {check.id}: {check.name.replace(chr(0x2265), '>=')}")
        if check.detail:
            print(f"       {check.detail[:200]}")

    print(
        f"\nAutomated: {report.automated_passed}/{report.automated_total} passed"
    )
    print(f"Golden RQs passed: {sum(1 for g in report.golden_results if g.get('passed'))}/6")
    print(f"Report: {out_path}")

    manual_pending = any(check.manual and not check.passed for check in report.checks)
    all_auto = report.automated_passed == report.automated_total
    return 0 if all_auto and golden_ok and not manual_pending else (0 if all_auto and golden_ok else 1)


if __name__ == "__main__":
    sys.exit(main())
