from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from spotify_app_review_analyzer.agent.groq_client import MockGroqClient
from spotify_app_review_analyzer.agent.guardrails import is_in_scope, validate_grounding
from spotify_app_review_analyzer.agent.orchestrator import AgentOrchestrator
from spotify_app_review_analyzer.agent.schemas import GOLDEN_QUESTIONS, infer_rq_id
from spotify_app_review_analyzer.agent.service import AgentService
from spotify_app_review_analyzer.agent.tools import AgentTools
from spotify_app_review_analyzer.db.models import AgentQuery, AnalysisResult, Review, Source


def _seed_processed_review(session, *, source_key: str, text: str, themes: list[str], rqs: list[str]):
    source = Source(
        id=uuid.uuid4(),
        key=source_key,
        name=source_key,
        created_at=datetime.now(UTC),
    )
    session.add(source)
    session.flush()
    review = Review(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id="x1",
        text=text,
        rating=2,
        content_hash=f"hash-agent-{uuid.uuid4().hex[:8]}",
        processing_status="processed",
        created_at=datetime.now(UTC),
        extra_metadata={},
    )
    session.add(review)
    session.flush()
    session.add(
        AnalysisResult(
            review_id=review.id,
            sentiment="negative",
            sentiment_score=-0.6,
            themes=themes,
            research_questions=rqs,
            listening_intent=[],
            segment_tags=["segment.platform.ios"],
            confidence=0.82,
            model_version="rule-v1.0+tfidf-v1",
            created_at=datetime.now(UTC),
        )
    )
    session.flush()
    return review


@pytest.fixture
def seeded_agent_data(db_session):
    review = _seed_processed_review(
        db_session,
        source_key="app_store",
        text="I cannot discover new music; recommendations are stale and repetitive.",
        themes=["rq1.search.browse_friction", "rq2.repetition.stale"],
        rqs=["rq1", "rq2"],
    )
    db_session.commit()
    return review


def test_infer_rq_id_from_question() -> None:
    assert infer_rq_id("Why do users struggle to discover new music?") == "rq1"
    assert infer_rq_id("What are frustrations with recommendations?") == "rq2"


def test_out_of_scope_question() -> None:
    allowed, reason = is_in_scope("What is Spotify's revenue this quarter?")
    assert allowed is False
    assert reason


def test_rq6_golden_question_in_scope() -> None:
    allowed, _ = is_in_scope(GOLDEN_QUESTIONS["rq6"])
    assert allowed is True


def test_unknown_source_out_of_scope() -> None:
    allowed, reason = is_in_scope("What do TikTok users say about Spotify music discovery?")
    assert allowed is False
    assert "corpus" in (reason or "").lower()


def test_validate_grounding_flags_unknown_citations() -> None:
    allowed_ids = {"00000000-0000-4000-8000-000000000001"}
    result = validate_grounding(
        "Users struggle `00000000-0000-4000-8000-000000000099`",
        allowed_review_ids=allowed_ids,
        citation_confidence={},
    )
    assert result.passed is False


def test_agent_tools_aggregate_themes(db_session, seeded_agent_data) -> None:
    tools = AgentTools(db_session)
    result = tools.aggregate_themes(rq_id="rq2", since_days=None)
    assert result["review_count"] >= 1
    theme_ids = [item["theme_id"] for item in result["themes"]]
    assert "rq2.repetition.stale" in theme_ids


def test_agent_tools_detect_cross_source_themes(db_session, seeded_agent_data) -> None:
    _seed_processed_review(
        db_session,
        source_key="reddit",
        text="Same songs every day on discover weekly.",
        themes=["rq2.repetition.stale"],
        rqs=["rq2"],
    )
    db_session.commit()
    tools = AgentTools(db_session)
    result = tools.detect_cross_source_themes(rq_id="rq2")
    assert "rq2.repetition.stale" in result["themes"]


def test_orchestrator_ask_without_groq(db_session, seeded_agent_data) -> None:
    orchestrator = AgentOrchestrator(db_session, groq_client=MockGroqClient())
    answer = orchestrator.ask(
        GOLDEN_QUESTIONS["rq1"],
        rq_id="rq1",
        use_groq=False,
    )
    assert "rq1" in answer.answer_text
    assert any(call.tool == "build_rq_briefing" for call in answer.tool_calls)


def test_orchestrator_ask_with_mock_groq(db_session, seeded_agent_data) -> None:
    review_id = str(seeded_agent_data.id)
    mock = MockGroqClient(
        response_text=f"Users struggle with discovery. See `{review_id}` for evidence."
    )
    orchestrator = AgentOrchestrator(db_session, groq_client=mock)
    answer = orchestrator.ask(GOLDEN_QUESTIONS["rq1"], rq_id="rq1", use_groq=True)
    assert answer.used_groq is True
    assert review_id in answer.citations
    assert answer.guardrail_passed is True


def test_agent_service_persists_audit_log(db_session, seeded_agent_data) -> None:
    review_id = str(seeded_agent_data.id)
    mock = MockGroqClient(
        response_text=f"Discovery friction is common. Citation `{review_id}`."
    )
    service = AgentService(db_session, groq_client=mock)
    service.ask(GOLDEN_QUESTIONS["rq1"], rq_id="rq1")
    db_session.commit()
    queries = list(db_session.scalars(select(AgentQuery)).all())
    assert len(queries) == 1
    assert queries[0].tool_calls
    assert queries[0].response is not None


def test_orchestrator_refuses_out_of_scope(db_session, seeded_agent_data) -> None:
    orchestrator = AgentOrchestrator(db_session, groq_client=MockGroqClient())
    answer = orchestrator.ask("What is Spotify's revenue?", use_groq=True)
    assert "out of scope" in answer.answer_text.lower() or "only answer" in answer.answer_text.lower()
    assert answer.used_groq is False
