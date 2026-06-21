from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from spotify_app_review_analyzer.agent.groq_client import GroqClientProtocol
from spotify_app_review_analyzer.agent.orchestrator import AgentOrchestrator
from spotify_app_review_analyzer.agent.schemas import AgentAnswer, ToolCallRecord
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.models import AgentQuery, AgentResponse

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        session: Session,
        *,
        groq_client: GroqClientProtocol | None = None,
    ) -> None:
        self.session = session
        self.orchestrator = AgentOrchestrator(session, groq_client=groq_client)

    def ask(
        self,
        question: str,
        *,
        rq_id: str | None = None,
        session_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        audit: bool = True,
        use_groq: bool = True,
    ) -> AgentAnswer:
        answer = self.orchestrator.ask(
            question,
            rq_id=rq_id,
            session_id=session_id,
            conversation_history=conversation_history,
            use_groq=use_groq,
        )
        if audit:
            self._persist_audit(question, answer, session_id=session_id)
        return answer

    def summarize_research_question(
        self,
        rq_id: str,
        *,
        session_id: str | None = None,
        audit: bool = True,
    ) -> AgentAnswer:
        from spotify_app_review_analyzer.agent.schemas import GOLDEN_QUESTIONS

        question = GOLDEN_QUESTIONS.get(rq_id, f"Summarize research question {rq_id}")
        answer = self.orchestrator.summarize_research_question(rq_id, session_id=session_id)
        if audit:
            self._persist_audit(question, answer, session_id=session_id)
        return answer

    def _persist_audit(
        self,
        question: str,
        answer: AgentAnswer,
        *,
        session_id: str | None,
    ) -> AgentQuery:
        query = AgentQuery(
            id=uuid.uuid4(),
            session_id=session_id,
            user_query=question,
            rq_id=answer.rq_id,
            tool_calls=[
                {
                    "tool": call.tool,
                    "input": call.input,
                    "output_summary": call.output_summary,
                }
                for call in answer.tool_calls
            ],
            briefing_context=answer.briefing_context,
            groq_model=settings.groq_model if answer.used_groq else None,
            prompt_version=settings.groq_prompt_version if answer.used_groq else None,
            input_tokens=answer.input_tokens,
            output_tokens=answer.output_tokens,
            latency_ms=answer.latency_ms,
            created_at=datetime.now(UTC),
        )
        response = AgentResponse(
            id=uuid.uuid4(),
            query_id=query.id,
            answer_text=answer.answer_text,
            citations=answer.citations,
            confidence_flags=answer.confidence_flags,
            guardrail_passed=answer.guardrail_passed,
            guardrail_notes=answer.guardrail_notes,
            created_at=datetime.now(UTC),
        )
        self.session.add(query)
        self.session.add(response)
        self.session.flush()
        logger.info(
            "Logged agent query id=%s rq=%s guardrail_passed=%s",
            query.id,
            answer.rq_id,
            answer.guardrail_passed,
        )
        return query
