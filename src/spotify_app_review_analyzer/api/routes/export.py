from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.analytics.export import export_briefing_markdown
from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing
from spotify_app_review_analyzer.api.services.dashboard_data import get_reviews
from spotify_app_review_analyzer.api.deps import get_db

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def export_csv(
    source_key: str | None = None,
    theme: str | None = None,
    since_days: int | None = Query(None, ge=1, le=365),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    items, _ = get_reviews(
        session,
        source_key=source_key,
        theme=theme,
        since_days=since_days,
        limit=5000,
        offset=0,
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "review_id",
            "source_key",
            "rating",
            "sentiment",
            "themes",
            "published_at",
            "text",
        ],
    )
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "review_id": item["review_id"],
                "source_key": item["source_key"],
                "rating": item["rating"],
                "sentiment": item["sentiment"],
                "themes": ";".join(item.get("themes") or []),
                "published_at": item["published_at"],
                "text": item["text"],
            }
        )
    buffer.seek(0)
    filename = f"reviews_export_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/markdown")
def export_markdown(session: Session = Depends(get_db)) -> PlainTextResponse:
    briefing = build_rq_briefing(session)
    from pathlib import Path
    from spotify_app_review_analyzer.core.settings import settings

    path = Path(settings.validation_export_dir) / "rq_briefing_export.md"
    export_briefing_markdown(briefing, path)
    content = path.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="text/markdown")
