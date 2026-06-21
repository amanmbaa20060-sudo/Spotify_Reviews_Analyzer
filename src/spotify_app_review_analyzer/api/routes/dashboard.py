from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.agent.service import AgentService
from spotify_app_review_analyzer.api.services.dashboard_data import (
    get_overview_kpis,
    get_rating_distribution,
    get_research_question,
    get_research_questions,
    get_recent_feedback,
    get_reviews,
    get_sentiment_by_source,
    get_top_themes,
    get_unmet_needs,
    get_word_cloud_data,
)
from spotify_app_review_analyzer.api.deps import get_db

router = APIRouter(prefix="/api", tags=["dashboard"])


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    rq_id: str | None = None


@router.get("/overview")
def overview(
    since_days: int | None = Query(None, ge=1, le=365),
    session: Session = Depends(get_db),
) -> dict:
    return get_overview_kpis(session, since_days=since_days)


@router.get("/reviews/recent")
def recent_reviews(
    source_key: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=50),
    session: Session = Depends(get_db),
) -> dict:
    items, total = get_recent_feedback(session, source_key=source_key, limit=limit)
    return {"items": items, "total": total, "limit": limit}


@router.get("/reviews")
def list_reviews(
    source_key: str | None = None,
    sentiment: str | None = None,
    min_rating: int | None = Query(None, ge=1, le=5),
    theme: str | None = None,
    since_days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
) -> dict:
    items, total = get_reviews(
        session,
        source_key=source_key,
        sentiment=sentiment,
        min_rating=min_rating,
        theme=theme,
        since_days=since_days,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/aggregates/sentiment")
def aggregates_sentiment(
    since_days: int | None = Query(None, ge=1, le=365),
    session: Session = Depends(get_db),
) -> dict:
    return {"items": get_sentiment_by_source(session, since_days=since_days)}


@router.get("/aggregates/themes")
def aggregates_themes(
    since_days: int | None = Query(None, ge=1, le=365),
    rq_id: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
) -> dict:
    return {
        "items": get_top_themes(session, since_days=since_days, rq_id=rq_id, limit=limit)
    }


@router.get("/aggregates/ratings")
def aggregates_ratings(
    source_key: str | None = None,
    since_days: int | None = Query(None, ge=1, le=365),
    session: Session = Depends(get_db),
) -> dict:
    return {
        "items": get_rating_distribution(session, source_key=source_key, since_days=since_days)
    }


@router.get("/research-questions")
def research_questions(session: Session = Depends(get_db)) -> dict:
    return {"items": get_research_questions(session)}


@router.get("/research-questions/{rq_id}")
def research_question(rq_id: str, session: Session = Depends(get_db)) -> dict:
    item = get_research_question(session, rq_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Unknown research question: {rq_id}")
    return item


@router.get("/unmet-needs")
def unmet_needs(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
) -> dict:
    return {"items": get_unmet_needs(session, limit=limit)}


@router.get("/word-cloud")
def word_cloud(
    rq_id: str | None = None,
    session: Session = Depends(get_db),
) -> dict:
    return {"items": get_word_cloud_data(session, rq_id=rq_id)}


@router.post("/agent/query")
def agent_query(
    body: AgentQueryRequest,
    session: Session = Depends(get_db),
) -> dict:
    service = AgentService(session)
    answer = service.ask(body.question, rq_id=body.rq_id, audit=True)
    session.commit()
    return {
        "answer": answer.answer_text,
        "rq_id": answer.rq_id,
        "citations": answer.citations,
        "guardrail_passed": answer.guardrail_passed,
        "latency_ms": answer.latency_ms,
    }
