from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # SQLite default works locally without Docker/Postgres (Windows-friendly).
    database_url: str = "sqlite:///data/spotify_reviews.db"

    # Ingestion
    spotify_app_store_id: str = "324684580"
    spotify_play_store_id: str = "com.spotify.music"
    app_store_max_pages: int = 10
    play_store_default_limit: int = 1000
    reddit_subreddits: str = "spotify,truespotify,spotifyplaylists"
    reddit_default_limit: int = 1000
    reddit_user_agent: str = "SpotifyAppReviewAnalyzer/0.1 (Growth Team)"
    ingest_max_retries: int = 3
    ingest_backoff_seconds: float = 1.0
    raw_data_export_dir: str = "data/raw"

    # Processing (Phase 3)
    classifier_backend: str = "rule"  # rule | openai (future)
    embedding_backend: str = "tfidf"  # tfidf | openai (future)
    model_version: str = "rule-v1.0+tfidf-v1"
    processing_batch_size: int = 100
    embedding_max_features: int = 256
    embedding_model_dir: str = "data/models"
    validation_export_dir: str = "data/exports"
    rq_briefing_exemplars_per_theme: int = 3
    rq_briefing_top_themes: int = 5
    min_review_text_length: int = 15
    openai_api_key: str | None = None

    # Agent / Groq (Phase 4B)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_prompt_version: str = "v1.0"
    groq_max_output_tokens: int = 2048
    groq_max_context_tokens: int = 8000
    groq_requests_per_minute: int = 30
    groq_requests_per_day: int = 1000
    groq_tokens_per_minute: int = 12000
    groq_tokens_per_day: int = 100000
    groq_temperature: float = 0.2
    agent_low_confidence_threshold: float = 0.5
    agent_session_history_limit: int = 6

    # Social ingestion (Phase 5)
    mastodon_instance_url: str = "https://mastodon.social"
    mastodon_hashtags: str = "spotify,music,Music,spotifyplaylist"
    mastodon_default_limit: int = 500
    bluesky_service_url: str = "https://bsky.social"
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    bluesky_search_queries: str = "spotify,spotify music,discover weekly,spotify playlist"
    bluesky_default_limit: int = 500
    social_viral_engagement_percentile: float = 0.9
    trend_window_days: int = 7
    trend_burst_multiplier: float = 2.0
    trend_top_n: int = 5

    @property
    def reddit_subreddit_list(self) -> list[str]:
        return [s.strip() for s in self.reddit_subreddits.split(",") if s.strip()]

    @property
    def mastodon_hashtag_list(self) -> list[str]:
        return [s.strip().lstrip("#") for s in self.mastodon_hashtags.split(",") if s.strip()]

    @property
    def bluesky_search_query_list(self) -> list[str]:
        return [s.strip() for s in self.bluesky_search_queries.split(",") if s.strip()]


settings = Settings()
