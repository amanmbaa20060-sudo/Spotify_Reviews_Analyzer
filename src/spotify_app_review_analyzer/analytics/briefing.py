from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from spotify_app_review_analyzer.analytics.aggregations import (
    average_confidence,
    compute_segment_signals,
    count_themes,
    cross_source_themes,
    fetch_analyzed_reviews,
    filter_reviews_for_rq,
    readiness_label,
    sentiment_mix,
    source_breakdown,
    sql_processed_count,
    sql_rq_review_count,
    theme_label_map,
)
from spotify_app_review_analyzer.analytics.evidence import select_exemplars_for_rq
from spotify_app_review_analyzer.analytics.schemas import (
    RQ_IDS,
    RQBriefing,
    RQSection,
    SegmentSignal,
    ThemeCount,
)
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.models import AnalysisResult
from spotify_app_review_analyzer.processing.embeddings import EmbeddingStore
from spotify_app_review_analyzer.taxonomy.loader import load_taxonomy


def build_rq_briefing(
    session: Session,
    *,
    rq_ids: list[str] | None = None,
    top_themes: int | None = None,
    exemplars_per_theme: int | None = None,
    embedding_store: EmbeddingStore | None = None,
) -> RQBriefing:
    taxonomy = load_taxonomy()
    labels = taxonomy.research_questions
    theme_labels = theme_label_map(taxonomy)
    top_n = top_themes or settings.rq_briefing_top_themes
    per_theme = exemplars_per_theme or settings.rq_briefing_exemplars_per_theme
    target_rqs = tuple(rq_ids or RQ_IDS)

    all_reviews = fetch_analyzed_reviews(session)
    store = embedding_store or EmbeddingStore()
    if store.review_ids and not store.matrix:
        store._load()

    model_version = session.scalar(
        select(AnalysisResult.model_version)
        .where(AnalysisResult.model_version.is_not(None))
        .limit(1)
    )

    sections: list[RQSection] = []
    for rq_id in target_rqs:
        rq_reviews = filter_reviews_for_rq(all_reviews, rq_id)
        theme_counts = count_themes(rq_reviews, rq_id)
        top_theme_items = theme_counts.most_common(top_n)
        top_theme_ids = [theme_id for theme_id, _ in top_theme_items]

        segment_signal_pairs = compute_segment_signals(
            rq_reviews,
            rq_id,
            top_theme_ids=top_theme_ids,
        )
        avg_conf = average_confidence(rq_reviews)

        sections.append(
            RQSection(
                rq_id=rq_id,
                label=labels.get(rq_id, rq_id),
                review_count=len(rq_reviews),
                top_themes=[
                    ThemeCount(
                        theme_id=theme_id,
                        label=theme_labels.get(theme_id, theme_id),
                        count=count,
                    )
                    for theme_id, count in top_theme_items
                ],
                sentiment_mix=sentiment_mix(rq_reviews),
                source_breakdown=source_breakdown(rq_reviews),
                segment_signals=[
                    SegmentSignal(description=description, theme_id=theme_id)
                    for theme_id, description in segment_signal_pairs
                ],
                cross_source_themes=cross_source_themes(rq_reviews, rq_id),
                exemplar_citations=select_exemplars_for_rq(
                    rq_id,
                    rq_reviews,
                    top_theme_ids,
                    per_theme=per_theme,
                    embedding_store=store if store.review_ids else None,
                ),
                readiness=readiness_label(len(rq_reviews), avg_conf),
                avg_confidence=avg_conf,
            )
        )

    briefing = RQBriefing(
        generated_at=datetime.now(UTC).isoformat(),
        taxonomy_version=taxonomy.version,
        model_version=model_version,
        total_processed_reviews=len(all_reviews),
        sections=sections,
    )
    briefing.verification = verify_briefing_counts(session, briefing)
    return briefing


def verify_briefing_counts(session: Session, briefing: RQBriefing) -> dict:
    """Compare briefing counts against independent SQL/Python recounts."""
    sql_total = sql_processed_count(session)
    mismatches: list[dict] = []

    if sql_total != briefing.total_processed_reviews:
        mismatches.append(
            {
                "field": "total_processed_reviews",
                "briefing": briefing.total_processed_reviews,
                "sql": sql_total,
            }
        )

    for section in briefing.sections:
        sql_rq_count = sql_rq_review_count(session, section.rq_id)
        if sql_rq_count != section.review_count:
            mismatches.append(
                {
                    "field": f"{section.rq_id}.review_count",
                    "briefing": section.review_count,
                    "sql": sql_rq_count,
                }
            )

    return {
        "passed": not mismatches,
        "sql_processed_total": sql_total,
        "mismatches": mismatches,
    }
