"""phase4 agent audit log

Revision ID: 0003_agent
Revises: 0002_embeddings
Create Date: 2026-06-19
"""

# ruff: noqa: E501
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_agent"
down_revision = "0002_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("rq_id", sa.String(length=16), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("briefing_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("groq_model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_queries_session_id", "agent_queries", ["session_id"])
    op.create_index("ix_agent_queries_rq_id", "agent_queries", ["rq_id"])

    op.create_table(
        "agent_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("guardrail_passed", sa.Boolean(), nullable=False),
        sa.Column("guardrail_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["agent_queries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("query_id"),
    )
    op.create_index("ix_agent_responses_query_id", "agent_responses", ["query_id"])


def downgrade() -> None:
    op.drop_table("agent_responses")
    op.drop_table("agent_queries")
