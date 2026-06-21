# ruff: noqa: I001
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from spotify_app_review_analyzer.core.settings import settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _sqlite_connect_args(url: str) -> dict:
    if url.startswith("sqlite:"):
        return {"check_same_thread": False}
    return {}


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        connect_args = _sqlite_connect_args(settings.database_url)
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=not settings.database_url.startswith("sqlite:"),
            connect_args=connect_args,
        )
        if settings.database_url.startswith("sqlite:"):

            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)
    return _session_factory


def get_session() -> Session:
    return get_session_factory()()
