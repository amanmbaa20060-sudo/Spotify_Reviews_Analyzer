"""analysis_results list columns as jsonb

Revision ID: 0004_analysis_json
Revises: 0003_agent
Create Date: 2026-07-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_analysis_json"
down_revision = "0003_agent"
branch_labels = None
depends_on = None

_LIST_COLUMNS: tuple[tuple[str, int], ...] = (
    ("themes", 128),
    ("research_questions", 16),
    ("listening_intent", 64),
    ("segment_tags", 64),
)


def upgrade() -> None:
    for column, length in _LIST_COLUMNS:
        op.alter_column(
            "analysis_results",
            column,
            existing_type=postgresql.ARRAY(sa.String(length=length)),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            postgresql_using=f"to_jsonb({column})",
            existing_nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        )


def downgrade() -> None:
    for column, length in reversed(_LIST_COLUMNS):
        op.alter_column(
            "analysis_results",
            column,
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=postgresql.ARRAY(sa.String(length=length)),
            postgresql_using=(
                f"ARRAY(SELECT jsonb_array_elements_text({column}))"
                f"::varchar({length})[]"
            ),
            existing_nullable=False,
            server_default=sa.text("'{}'"),
        )
