from __future__ import annotations

import json
from pathlib import Path

from spotify_app_review_analyzer.processing.classifier.rule_based import RuleBasedClassifier
from spotify_app_review_analyzer.processing.cleaning import clean_text
from spotify_app_review_analyzer.processing.quality import score_quality


def test_clean_text_strips_html() -> None:
    assert clean_text("<b>Great</b>  app") == "Great app"


def test_quality_flags_spam() -> None:
    result = score_quality("click here for free money fast")
    assert result.skip_reason == "spam"


def test_quality_flags_short_text() -> None:
    result = score_quality("bad")
    assert result.skip_reason == "too_short"


def test_classifier_detects_repetition_theme() -> None:
    clf = RuleBasedClassifier()
    result = clf.classify(
        "Spotify recommendations are repetitive and I hear the same songs every day.",
        rating=2,
    )
    assert result.sentiment == "negative"
    assert "rq2.repetition.stale" in result.themes
    assert "rq2" in result.research_questions


def test_classifier_positive_sentiment() -> None:
    clf = RuleBasedClassifier()
    result = clf.classify("I love this app, amazing music discovery!", rating=5)
    assert result.sentiment == "positive"


def test_gold_set_accuracy_threshold() -> None:
    gold_path = Path(__file__).parent / "fixtures" / "gold_labels.json"
    samples = json.loads(gold_path.read_text(encoding="utf-8"))
    clf = RuleBasedClassifier()

    sentiment_hits = 0
    theme_hits = 0
    rq_hits = 0

    for sample in samples:
        result = clf.classify(sample["text"], rating=sample.get("rating"))
        if result.sentiment == sample["sentiment"]:
            sentiment_hits += 1
        if sample["primary_theme"] in result.themes:
            theme_hits += 1
        if sample["rq"] in result.research_questions:
            rq_hits += 1

    n = len(samples)
    assert sentiment_hits / n >= 0.75
    assert theme_hits / n >= 0.6
    assert rq_hits / n >= 0.6
