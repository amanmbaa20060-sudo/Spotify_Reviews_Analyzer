from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spotify_app_review_analyzer.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(256), index=True)

    title: Mapped[str | None] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)

    rating: Mapped[int | None] = mapped_column(Integer)
    author_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    app_version: Mapped[str | None] = mapped_column(String(64))

    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    processing_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source: Mapped[Source] = relationship()
    analysis: Mapped[AnalysisResult | None] = relationship(back_populates="review", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "processing_status in ('pending','processed','failed','skipped')",
            name="reviews_processing_status_check",
        ),
        CheckConstraint(
            "rating is null or (rating >= 1 and rating <= 5)", name="reviews_rating_check"
        ),
        Index("ix_reviews_source_published_at", "source_id", "published_at"),
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )

    sentiment: Mapped[str | None] = mapped_column(String(16))
    sentiment_score: Mapped[float | None] = mapped_column()

    themes: Mapped[list[str]] = mapped_column(JSON, default=list)
    research_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    listening_intent: Mapped[list[str]] = mapped_column(JSON, default=list)
    segment_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    confidence: Mapped[float | None] = mapped_column()
    model_version: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    review: Mapped[Review] = relationship(back_populates="analysis")


class ReviewEmbedding(Base):
    __tablename__ = "review_embeddings"

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    review: Mapped[Review] = relationship()


class ThemeTaxonomy(Base):
    __tablename__ = "theme_taxonomy"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("theme_taxonomy.id"))
    label: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AgentQuery(Base):
    __tablename__ = "agent_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    user_query: Mapped[str] = mapped_column(Text)
    rq_id: Mapped[str | None] = mapped_column(String(16), index=True)

    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    briefing_context: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    groq_model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    response: Mapped[AgentResponse | None] = relationship(back_populates="query", uselist=False)


class AgentResponse(Base):
    __tablename__ = "agent_responses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_queries.id", ondelete="CASCADE"), unique=True, index=True
    )

    answer_text: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    guardrail_passed: Mapped[bool] = mapped_column(default=True)
    guardrail_notes: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    query: Mapped[AgentQuery] = relationship(back_populates="response")
