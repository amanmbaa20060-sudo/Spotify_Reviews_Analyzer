from __future__ import annotations

from spotify_app_review_analyzer.analytics.aggregations import AnalyzedReview
from spotify_app_review_analyzer.analytics.problem_analysis import build_weighted_problem_analysis
from spotify_app_review_analyzer.analytics.schemas import RQSection, SegmentSignal, ThemeCount


def _section() -> RQSection:
    return RQSection(
        rq_id="rq1",
        label="Why do users struggle to discover new music?",
        review_count=100,
        top_themes=[
            ThemeCount("rq1.search.browse_friction", "Search/browse friction", 40),
            ThemeCount("rq1.overwhelm.choice_overload", "Choice overload", 20),
        ],
        sentiment_mix={"negative": 35.0, "neutral": 40.0, "positive": 25.0},
        source_breakdown={"app_store": 55.0, "play_store": 45.0},
        segment_signals=[
            SegmentSignal("iOS pain > Android on rq1.search.browse_friction", "rq1.search.browse_friction")
        ],
        cross_source_themes=["rq1.search.browse_friction"],
        exemplar_citations=[],
        readiness="high",
        avg_confidence=0.7,
    )


def _reviews() -> list[AnalyzedReview]:
    items: list[AnalyzedReview] = []
    for i in range(40):
        items.append(
            AnalyzedReview(
                review_id=f"browse-{i}",
                text="Hard to browse genres",
                sentiment="negative" if i < 25 else "neutral",
                themes=("rq1.search.browse_friction",),
                research_questions=("rq1",),
                segment_tags=("segment.platform.ios",),
                confidence=0.8,
                source_key="app_store",
            )
        )
    for i in range(20):
        items.append(
            AnalyzedReview(
                review_id=f"overload-{i}",
                text="Too many options",
                sentiment="negative" if i < 8 else "positive",
                themes=("rq1.overwhelm.choice_overload",),
                research_questions=("rq1",),
                segment_tags=(),
                confidence=0.75,
                source_key="play_store",
            )
        )
    return items


def test_weighted_problem_analysis_orders_by_weight() -> None:
    analysis = build_weighted_problem_analysis(_section(), _reviews())
    causes = analysis["root_causes"]
    assert len(causes) == 2
    assert causes[0]["theme_id"] == "rq1.search.browse_friction"
    assert causes[0]["weight"] > causes[1]["weight"]
    assert abs(sum(c["weight"] for c in causes) - 100.0) < 0.2
    assert "browse friction" in analysis["summary"].lower() or "Search" in analysis["summary"]
    assert analysis["segment_factors"]


def test_weights_reflect_negative_share() -> None:
    analysis = build_weighted_problem_analysis(_section(), _reviews())
    browse = next(c for c in analysis["root_causes"] if c["theme_id"] == "rq1.search.browse_friction")
    assert browse["negative_share"] > 50
