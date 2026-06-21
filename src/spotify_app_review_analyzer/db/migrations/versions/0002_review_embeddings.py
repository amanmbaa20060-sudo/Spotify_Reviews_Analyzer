"""phase2 review embeddings

Revision ID: 0002_embeddings
Revises: 0001_phase1
Create Date: 2026-06-18
"""

# ruff: noqa: E501
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_embeddings"
down_revision = "0001_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_embeddings",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("review_embeddings")
