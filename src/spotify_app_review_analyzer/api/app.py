# ruff: noqa: I001
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from spotify_app_review_analyzer.api.routes.dashboard import router as dashboard_router
from spotify_app_review_analyzer.api.routes.export import router as export_router
from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.session import get_session
from spotify_app_review_analyzer.processing.embeddings import EmbeddingStore
from spotify_app_review_analyzer.processing.service import ProcessingService

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"


def _ensure_embedding_index() -> None:
    """Rebuild TF-IDF index from DB when pickle files are missing (e.g. after redeploy)."""
    store = EmbeddingStore()
    if store.vectorizer_path.exists():
        return
    session = get_session()
    try:
        count = ProcessingService(session).rebuild_all_embeddings()
        if count:
            session.commit()
            logger.info("Rebuilt TF-IDF embedding index for %s reviews on startup", count)
    except Exception:
        session.rollback()
        logger.exception("Failed to rebuild embedding index on startup")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_embedding_index()
    yield


app = FastAPI(title="Spotify App Review Analyzer", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(export_router)

if DASHBOARD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DASHBOARD_DIR / "assets"), name="dashboard-assets")
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="dashboard-static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/")
def dashboard_index() -> Response:
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        return FileResponse(__file__)
    return Response(
        content=index.read_text(encoding="utf-8"),
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )
