from spotify_app_review_analyzer.core.settings import normalize_database_url


def test_normalize_render_postgres_url() -> None:
    assert (
        normalize_database_url("postgres://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert normalize_database_url("sqlite:///data/spotify_reviews.db").startswith("sqlite:")
