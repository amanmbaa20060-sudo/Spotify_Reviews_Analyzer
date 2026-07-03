from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.agent.service import AgentService
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS
from spotify_app_review_analyzer.api.deps import get_db
from spotify_app_review_analyzer.api.services.dashboard_data import (
    get_overview_kpis,
    get_rating_distribution,
    get_recent_feedback,
    get_research_question,
    get_research_questions,
    get_reviews,
    get_rq_negative_evidence,
    get_rq_problem_analysis,
    get_sentiment_by_source,
    get_top_themes,
    get_unmet_needs,
    get_word_cloud_data,
)
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.deploy.seed import is_seeding, seed_completed

router = APIRouter(prefix="/api", tags=["dashboard"])


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    rq_id: str | None = None


@router.get("/status")
def api_status(session: Session = Depends(get_db)) -> dict:
    """Lightweight health + data counts for production debugging."""
    overview = get_overview_kpis(session)
    scheme = settings.database_url.split(":", 1)[0]
    warnings: list[str] = []
    if settings.app_env == "production" and scheme == "sqlite":
        warnings.append(
            "DATABASE_URL is not set to Postgres; SQLite data is ephemeral on Render."
        )
    return {
        "status": "ok",
        "env": settings.app_env,
        "database_url_scheme": scheme,
        "total_records": overview["total_records"],
        "processed_records": overview["processed_records"],
        "seeding_in_progress": is_seeding(),
        "seed_completed": seed_completed(),
        "warnings": warnings,
    }


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


@router.get("/research-questions/{rq_id}/problem-analysis")
def rq_problem_analysis(rq_id: str, session: Session = Depends(get_db)) -> dict:
    if rq_id not in RQ_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown research question: {rq_id}")
    analysis = get_rq_problem_analysis(session, rq_id)
    return {"rq_id": rq_id, "problem_analysis": analysis, "problem_summary": analysis["summary"]}


@router.get("/research-questions/{rq_id}/top-evidence")
def rq_top_evidence(rq_id: str, session: Session = Depends(get_db)) -> dict:
    if rq_id not in RQ_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown research question: {rq_id}")
    items = get_rq_negative_evidence(session, rq_id)
    return {"rq_id": rq_id, "items": items, "total": len(items)}


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
