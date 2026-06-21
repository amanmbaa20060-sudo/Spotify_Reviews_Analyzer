"""phase1 core schema

Revision ID: 0001_phase1
Revises:
Create Date: 2026-06-17
"""

# ruff: noqa: E501
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_key", "sources", ["key"], unique=True)

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=256), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("author_hash", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "processing_status in ('pending','processed','failed','skipped')",
            name="reviews_processing_status_check",
        ),
        sa.CheckConstraint("rating is null or (rating >= 1 and rating <= 5)", name="reviews_rating_check"),
    )
    op.create_index("ix_reviews_external_id", "reviews", ["external_id"], unique=False)
    op.create_index("ix_reviews_source_id", "reviews", ["source_id"], unique=False)
    op.create_index("ix_reviews_author_hash", "reviews", ["author_hash"], unique=False)
    op.create_index("ix_reviews_published_at", "reviews", ["published_at"], unique=False)
    op.create_index("ix_reviews_processing_status", "reviews", ["processing_status"], unique=False)
    op.create_index("ix_reviews_content_hash", "reviews", ["content_hash"], unique=True)
    op.create_index("ix_reviews_source_published_at", "reviews", ["source_id", "published_at"], unique=False)

    op.create_table(
        "analysis_results",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sentiment", sa.String(length=16), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("themes", postgresql.ARRAY(sa.String(length=128)), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "research_questions",
            postgresql.ARRAY(sa.String(length=16)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "listening_intent",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "segment_tags",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "theme_taxonomy",
        sa.Column("id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("parent_id", sa.String(length=128), nullable=True),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["theme_taxonomy.id"]),
    )


def downgrade() -> None:
    op.drop_table("theme_taxonomy")
    op.drop_table("analysis_results")

    op.drop_index("ix_reviews_source_published_at", table_name="reviews")
    op.drop_index("ix_reviews_content_hash", table_name="reviews")
    op.drop_index("ix_reviews_processing_status", table_name="reviews")
    op.drop_index("ix_reviews_published_at", table_name="reviews")
    op.drop_index("ix_reviews_author_hash", table_name="reviews")
    op.drop_index("ix_reviews_source_id", table_name="reviews")
    op.drop_index("ix_reviews_external_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_sources_key", table_name="sources")
    op.drop_table("sources")

