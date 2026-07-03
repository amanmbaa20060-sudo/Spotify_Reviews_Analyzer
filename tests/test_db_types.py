from __future__ import annotations

from sqlalchemy.dialects import postgresql, sqlite

from spotify_app_review_analyzer.db.models import AnalysisResult
from spotify_app_review_analyzer.db.types import StringList


def test_analysis_result_uses_string_list_type() -> None:
    table = AnalysisResult.__table__
    for name in ("themes", "research_questions", "listening_intent", "segment_tags"):
        assert isinstance(table.c[name].type, StringList)


def test_analysis_list_columns_use_json_on_sqlite() -> None:
    dialect = sqlite.dialect()
    column_type = StringList(128).load_dialect_impl(dialect)
    assert "JSON" in str(column_type.compile(dialect=dialect))


def test_analysis_list_columns_use_array_on_postgres() -> None:
    dialect = postgresql.dialect()
    column_type = StringList(128).load_dialect_impl(dialect)
    assert "VARCHAR" in str(column_type.compile(dialect=dialect))
