"""Production entrypoint for Render (binds 0.0.0.0:$PORT)."""

from __future__ import annotations

import os

import uvicorn

from spotify_app_review_analyzer.core.logging import configure_logging
from spotify_app_review_analyzer.core.settings import settings

if __name__ == "__main__":
    configure_logging(settings.log_level)
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(
        "spotify_app_review_analyzer.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
    )
