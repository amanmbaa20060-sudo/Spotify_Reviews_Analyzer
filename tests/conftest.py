from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.base import Base


@pytest.fixture(scope="session")
def db_url() -> str:
    if settings.database_url.startswith("sqlite:"):
        return "sqlite:///:memory:"
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return settings.database_url
    except Exception:
        return "sqlite:///data/test_spotify_reviews.db"


@pytest.fixture
def db_session(db_url: str) -> Session:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite:") else {},
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
