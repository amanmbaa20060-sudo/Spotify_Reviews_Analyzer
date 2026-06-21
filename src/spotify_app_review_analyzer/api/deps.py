from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from spotify_app_review_analyzer.db.init_db import init_database
from spotify_app_review_analyzer.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    init_database()
    session = get_session()
    try:
        yield session
    finally:
        session.close()
