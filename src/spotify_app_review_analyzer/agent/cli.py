from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

from spotify_app_review_analyzer.agent.schemas import GOLDEN_QUESTIONS
from spotify_app_review_analyzer.agent.service import AgentService
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.session import get_session

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Groq-backed research agent (Phase 4B).")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Ask a research question")
    ask.add_argument("question", type=str, help="Natural-language question")
    ask.add_argument("--rq", type=str, default=None, help="Force RQ id (rq1–rq6)")
    ask.add_argument("--session-id", type=str, default=None)
    ask.add_argument("--no-groq", action="store_true", help="Return briefing only (no LLM)")

    chat = sub.add_parser("chat", help="Interactive chat session")
    chat.add_argument("--session-id", type=str, default=None)

    golden = sub.add_parser("golden", help="Run golden research questions")
    golden.add_argument(
        "--output",
        type=str,
        default="data/exports/golden_questions_report.json",
    )
    golden.add_argument("--runs", type=int, default=1, help="Runs per question (eval uses 3)")
    golden.add_argument("--no-groq", action="store_true", help="Briefing-only dry run")

    summarize = sub.add_parser("summarize", help="Summarize a research question via RQ briefing + Groq")
    summarize.add_argument("rq_id", choices=list(RQ_IDS))

    return parser


def _print_answer(answer) -> None:
    print("\n" + "=" * 72)
    print(answer.answer_text)
    print("=" * 72)
    if answer.citations:
        print(f"\nCitations ({len(answer.citations)}): {', '.join(answer.citations)}")
    if answer.confidence_flags:
        print("\nConfidence flags:")
        for flag in answer.confidence_flags:
            print(f"  - {flag}")
    if answer.guardrail_notes:
        print("\nGuardrail notes:")
        for note in answer.guardrail_notes:
            print(f"  - {note}")
    print(
        f"\nRQ: {answer.rq_id or 'n/a'} | guardrail_passed={answer.guardrail_passed} | "
        f"latency_ms={answer.latency_ms} | groq={answer.used_groq}"
    )


def run_ask(question: str, *, rq_id: str | None, session_id: str | None, use_groq: bool) -> int:
    if use_groq and not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set. Use --no-groq for briefing-only mode.")
        return 1

    init_database()
    session = get_session()
    try:
        service = AgentService(session)
        answer = service.ask(
            question,
            rq_id=rq_id,
            session_id=session_id,
            use_groq=use_groq,
        )
        session.commit()
        _print_answer(answer)
        return 0 if answer.guardrail_passed or not use_groq else 1
    finally:
        session.close()


def run_chat(*, session_id: str | None) -> int:
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set.")
        return 1

    init_database()
    session = get_session()
    sid = session_id or uuid.uuid4().hex[:12]
    history: list[dict[str, str]] = []
    print(f"Agent chat session={sid}. Type 'exit' to quit.\n")

    try:
        service = AgentService(session)
        while True:
            try:
                question = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question:
                continue
            if question.lower() in {"exit", "quit"}:
                break

            answer = service.ask(
                question,
                session_id=sid,
                conversation_history=history,
            )
            session.commit()
            _print_answer(answer)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer.answer_text})
            if len(history) > settings.agent_session_history_limit * 2:
                history = history[-settings.agent_session_history_limit * 2 :]
    finally:
        session.close()
    return 0


def run_golden(*, output: str, runs: int, use_groq: bool) -> int:
    if use_groq and not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set. Use --no-groq for briefing-only mode.")
        return 1

    init_database()
    session = get_session()
    report: dict = {"runs_per_question": runs, "results": []}

    try:
        service = AgentService(session)
        for rq_id, question in GOLDEN_QUESTIONS.items():
            rq_result = {"rq_id": rq_id, "question": question, "runs": []}
            for run_idx in range(1, runs + 1):
                answer = service.ask(
                    question,
                    rq_id=rq_id,
                    session_id=f"golden-{rq_id}-{run_idx}",
                    use_groq=use_groq,
                )
                rq_result["runs"].append(
                    {
                        "run": run_idx,
                        "citations": len(answer.citations),
                        "guardrail_passed": answer.guardrail_passed,
                        "latency_ms": answer.latency_ms,
                        "used_groq": answer.used_groq,
                    }
                )
            report["results"].append(rq_result)
        session.commit()
    finally:
        session.close()

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Golden question report written to {out_path}")
    return 0


def run_summarize(rq_id: str) -> int:
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set.")
        return 1

    init_database()
    session = get_session()
    try:
        service = AgentService(session)
        answer = service.summarize_research_question(rq_id)
        session.commit()
        _print_answer(answer)
        return 0 if answer.guardrail_passed else 1
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    configure_logging(settings.log_level)
    args = build_parser().parse_args(argv)

    if args.command == "ask":
        return run_ask(
            args.question,
            rq_id=args.rq,
            session_id=args.session_id,
            use_groq=not args.no_groq,
        )
    if args.command == "chat":
        return run_chat(session_id=args.session_id)
    if args.command == "golden":
        return run_golden(output=args.output, runs=args.runs, use_groq=not args.no_groq)
    if args.command == "summarize":
        return run_summarize(args.rq_id)
    return 1


if __name__ == "__main__":
    sys.exit(main())
