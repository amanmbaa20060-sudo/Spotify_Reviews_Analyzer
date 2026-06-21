from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from spotify_app_review_analyzer.agent.groq_client import GroqClient, GroqClientProtocol
from spotify_app_review_analyzer.agent.guardrails import (
    insufficient_data_message,
    is_in_scope,
    truncate_context,
    validate_grounding,
)
from spotify_app_review_analyzer.agent.prompts import (
    PROMPT_VERSION,
    build_synthesis_user_prompt,
    load_prompt,
)
from spotify_app_review_analyzer.agent.schemas import (
    AgentAnswer,
    ToolCallRecord,
    briefing_to_context_text,
    collect_allowed_review_ids,
    collect_citation_confidence,
    compact_briefing_section,
    infer_rq_id,
)
from spotify_app_review_analyzer.agent.tools import AgentTools
from spotify_app_review_analyzer.analytics.schemas import RQBriefing
from spotify_app_review_analyzer.core.settings import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(
        self,
        session: Session,
        *,
        groq_client: GroqClientProtocol | None = None,
        tools: AgentTools | None = None,
    ) -> None:
        self.session = session
        self.tools = tools or AgentTools(session)
        self.groq = groq_client or GroqClient()

    def ask(
        self,
        question: str,
        *,
        rq_id: str | None = None,
        session_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        use_groq: bool = True,
    ) -> AgentAnswer:
        started = time.perf_counter()
        tool_calls: list[ToolCallRecord] = []
        tool_results: list[dict[str, Any]] = []

        in_scope, scope_reason = is_in_scope(question)
        if not in_scope:
            return AgentAnswer(
                answer_text=(
                    f"I can only answer questions grounded in Spotify app review and Reddit "
                    f"discovery feedback. {scope_reason}"
                ),
                rq_id=rq_id,
                guardrail_passed=True,
                guardrail_notes=[scope_reason or "out_of_scope"],
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        resolved_rq = rq_id or infer_rq_id(question)
        briefing = self.tools.build_rq_briefing_tool(
            rq_ids=[resolved_rq] if resolved_rq else None,
        )
        tool_calls.append(
            ToolCallRecord(
                tool="build_rq_briefing",
                input={"rq_ids": [resolved_rq] if resolved_rq else "all"},
                output_summary=f"{len(briefing.sections)} RQ sections",
            )
        )

        section = self._section_for_rq(briefing, resolved_rq)
        review_count = section.review_count if section else briefing.total_processed_reviews
        if review_count == 0:
            return AgentAnswer(
                answer_text=insufficient_data_message(resolved_rq, review_count),
                rq_id=resolved_rq,
                guardrail_passed=True,
                tool_calls=tool_calls,
                briefing_context=self._briefing_payload(briefing, resolved_rq),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        if self._needs_source_comparison(question):
            result = self.tools.compare_sources("reddit", "app_store", rq_id=resolved_rq or "rq2")
            tool_results.append({"tool": "compare_sources", "result": result})
            tool_calls.append(
                ToolCallRecord(
                    tool="compare_sources",
                    input={"source_a": "reddit", "source_b": "app_store", "rq_id": resolved_rq},
                    output_summary=(
                        f"counts {result['review_count_a']}/{result['review_count_b']}"
                    ),
                )
            )

        if self._needs_segment_comparison(question):
            result = self.tools.compare_segments(
                "segment.platform.ios",
                "segment.platform.android",
                rq_id=resolved_rq,
            )
            tool_results.append({"tool": "compare_segments", "result": result})
            tool_calls.append(
                ToolCallRecord(
                    tool="compare_segments",
                    input={
                        "segment_a": "segment.platform.ios",
                        "segment_b": "segment.platform.android",
                        "rq_id": resolved_rq,
                    },
                    output_summary=f"{len(result.get('signals', []))} signals",
                )
            )

        cross_source = self.tools.detect_cross_source_themes(rq_id=resolved_rq)
        tool_results.append({"tool": "detect_cross_source_themes", "result": cross_source})
        tool_calls.append(
            ToolCallRecord(
                tool="detect_cross_source_themes",
                input={"rq_id": resolved_rq},
                output_summary=f"{len(cross_source['themes'])} themes",
            )
        )

        if self._needs_search(question):
            search_query = resolved_rq or question
            search_result = self.tools.search_reviews(search_query, top_k=5)
            tool_results.append({"tool": "search_reviews", "result": search_result})
            tool_calls.append(
                ToolCallRecord(
                    tool="search_reviews",
                    input={"query": search_query},
                    output_summary=f"{search_result['count']} hits",
                )
            )

        briefing_context = truncate_context(
            briefing_to_context_text(briefing, rq_id=resolved_rq),
            max_tokens=settings.groq_max_context_tokens - 500,
        )
        tool_context = truncate_context(
            self.tools.tool_context_text(tool_results),
            max_tokens=1500,
        )
        history_text = self._format_history(conversation_history or [])

        if not use_groq:
            return AgentAnswer(
                answer_text=briefing_context,
                rq_id=resolved_rq,
                tool_calls=tool_calls,
                briefing_context=self._briefing_payload(briefing, resolved_rq),
                latency_ms=int((time.perf_counter() - started) * 1000),
                used_groq=False,
            )

        system_prompt = load_prompt("system")
        user_prompt = build_synthesis_user_prompt(
            question=question,
            briefing_context=briefing_context,
            tool_context=tool_context,
            conversation_history=history_text,
        )
        completion = self.groq.complete(system_prompt=system_prompt, user_prompt=user_prompt)

        allowed_ids = collect_allowed_review_ids(briefing, tool_results)
        confidence_map = collect_citation_confidence(briefing)
        guardrail = validate_grounding(
            completion.content,
            allowed_review_ids=allowed_ids,
            citation_confidence=confidence_map,
        )

        return AgentAnswer(
            answer_text=completion.content,
            rq_id=resolved_rq,
            citations=guardrail.citations,
            confidence_flags=guardrail.confidence_flags,
            guardrail_passed=guardrail.passed,
            guardrail_notes=guardrail.notes,
            tool_calls=tool_calls,
            briefing_context=self._briefing_payload(briefing, resolved_rq),
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            used_groq=True,
        )

    def summarize_research_question(
        self,
        rq_id: str,
        *,
        session_id: str | None = None,
    ) -> AgentAnswer:
        from spotify_app_review_analyzer.agent.schemas import GOLDEN_QUESTIONS

        question = GOLDEN_QUESTIONS.get(rq_id, f"Summarize research question {rq_id}")
        return self.ask(question, rq_id=rq_id, session_id=session_id)

    def _section_for_rq(self, briefing: RQBriefing, rq_id: str | None):
        if not rq_id:
            return briefing.sections[0] if briefing.sections else None
        return next((section for section in briefing.sections if section.rq_id == rq_id), None)

    def _briefing_payload(self, briefing: RQBriefing, rq_id: str | None) -> dict[str, Any]:
        sections = briefing.sections
        if rq_id:
            sections = [section for section in sections if section.rq_id == rq_id]
        return {
            "generated_at": briefing.generated_at,
            "sections": [compact_briefing_section(section) for section in sections],
        }

    @staticmethod
    def _needs_source_comparison(question: str) -> bool:
        lowered = question.lower()
        return "reddit" in lowered and ("app store" in lowered or "compare" in lowered)

    @staticmethod
    def _needs_segment_comparison(question: str) -> bool:
        lowered = question.lower()
        return "segment" in lowered or "ios" in lowered or "android" in lowered

    @staticmethod
    def _needs_search(question: str) -> bool:
        lowered = question.lower()
        return "search" in lowered or "find reviews" in lowered

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return ""
        lines: list[str] = []
        for turn in history[-settings.agent_session_history_limit :]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines)
