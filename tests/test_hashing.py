from __future__ import annotations

from spotify_app_review_analyzer.ingestion.hashing import content_hash, normalize_text


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  Hello   World  ") == "hello world"


def test_content_hash_stable() -> None:
    h1 = content_hash("app_store", "Great app!", "Title")
    h2 = content_hash("app_store", "Great app!", "Title")
    assert h1 == h2


def test_content_hash_differs_by_source() -> None:
    h1 = content_hash("app_store", "Same text")
    h2 = content_hash("play_store", "Same text")
    assert h1 != h2


def test_fuzzy_dedup_same_text_different_case() -> None:
    h1 = content_hash("reddit", "Spotify recommendations are stale")
    h2 = content_hash("reddit", "  spotify RECOMMENDATIONS are stale  ")
    assert h1 == h2
