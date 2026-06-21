from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from spotify_app_review_analyzer.analytics.aggregations import (
    compare_source_metrics,
    compute_segment_signals,
    count_themes,
    cross_source_themes,
    fetch_analyzed_reviews,
    filter_reviews_by_days,
    filter_reviews_for_rq,
    segment_theme_counts,
    sentiment_mix,
    theme_label_map,
    themes_for_rq,
)
from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing
from spotify_app_review_analyzer.analytics.schemas import RQBriefing
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.models import Review
from spotify_app_review_analyzer.processing.embeddings import EmbeddingStore
from spotify_app_review_analyzer.processing.service import ProcessingService

logger = logging.getLogger(__name__)


class AgentTools:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.processing = ProcessingService(session)
        self.embedding_store = EmbeddingStore()

    def search_reviews(
        self,
        query: str,
        *,
        source_key: str | None = None,
        min_rating: int | None = None,
        max_rating: int | None = None,
        since_days: int | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        hits = self.processing.semantic_search(query, top_k=top_k * 3)
        if not hits:
            return {"query": query, "results": [], "count": 0}

        review_ids = [uuid.UUID(hit["review_id"]) for hit in hits]
        reviews = {
            str(review.id): review
            for review in self.session.scalars(
                select(Review)
                .options(joinedload(Review.source), joinedload(Review.analysis))
                .where(Review.id.in_(review_ids))
            )
        }

        results: list[dict[str, Any]] = []
        for hit in hits:
            review = reviews.get(hit["review_id"])
            if review is None or review.source is None:
                continue
            if source_key and review.source.key != source_key:
                continue
            if min_rating is not None and (review.rating or 0) < min_rating:
                continue
            if max_rating is not None and review.rating is not None and review.rating > max_rating:
                continue
            if since_days is not None and review.published_at is not None:
                from datetime import UTC, datetime, timedelta

                cutoff = datetime.now(UTC) - timedelta(days=since_days)
                published = review.published_at
                if published.tzinfo is None:
                    published = published.replace(tzinfo=UTC)
                if published < cutoff:
                    continue
            analysis = review.analysis
            results.append(
                {
                    "review_id": hit["review_id"],
                    "score": hit["score"],
                    "source_key": review.source.key,
                    "rating": review.rating,
                    "sentiment": analysis.sentiment if analysis else None,
                    "themes": analysis.themes if analysis else [],
                    "confidence": analysis.confidence if analysis else None,
                    "text": review.text[:300],
                }
            )
            if len(results) >= top_k:
                break

        return {"query": query, "results": results, "count": len(results)}

    def aggregate_themes(
        self,
        *,
        rq_id: str | None = None,
        since_days: int | None = 90,
        theme_id: str | None = None,
    ) -> dict[str, Any]:
        reviews = fetch_analyzed_reviews(self.session)
        reviews = filter_reviews_by_days(reviews, since_days=since_days)
        if rq_id:
            reviews = filter_reviews_for_rq(reviews, rq_id)
        if theme_id:
            reviews = [review for review in reviews if theme_id in review.themes]

        if rq_id:
            theme_counts = count_themes(reviews, rq_id)
        else:
            from collections import Counter

            theme_counts = Counter()
            for review in reviews:
                theme_counts.update(review.themes)

        labels = theme_label_map()
        return {
            "rq_id": rq_id,
            "since_days": since_days,
            "review_count": len(reviews),
            "sentiment_mix": sentiment_mix(reviews),
            "themes": [
                {"theme_id": theme, "label": labels.get(theme, theme), "count": count}
                for theme, count in theme_counts.most_common(10)
            ],
        }

    def compare_segments(
        self,
        segment_a: str,
        segment_b: str,
        *,
        rq_id: str | None = None,
        theme_id: str | None = None,
    ) -> dict[str, Any]:
        reviews = fetch_analyzed_reviews(self.session)
        if rq_id:
            reviews = filter_reviews_for_rq(reviews, rq_id)

        effective_rq = rq_id or "rq1"
        if rq_id:
            left_counts = segment_theme_counts(reviews, rq_id, segment_a)
            right_counts = segment_theme_counts(reviews, rq_id, segment_b)
        else:
            from collections import Counter

            def _all_theme_counts(segment_prefix: str) -> Counter[str]:
                counter: Counter[str] = Counter()
                for review in reviews:
                    if not any(tag.startswith(segment_prefix) for tag in review.segment_tags):
                        continue
                    counter.update(review.themes)
                return counter

            left_counts = _all_theme_counts(segment_a)
            right_counts = _all_theme_counts(segment_b)
        if theme_id:
            return {
                "segment_a": segment_a,
                "segment_b": segment_b,
                "rq_id": rq_id,
                "theme_id": theme_id,
                "count_a": left_counts.get(theme_id, 0),
                "count_b": right_counts.get(theme_id, 0),
            }

        if rq_id:
            top_theme_ids = [tid for tid, _ in count_themes(reviews, rq_id).most_common(5)]
        else:
            from collections import Counter

            counter: Counter[str] = Counter()
            for review in reviews:
                counter.update(review.themes)
            top_theme_ids = [tid for tid, _ in counter.most_common(5)]

        signals = compute_segment_signals(
            reviews,
            effective_rq,
            top_theme_ids=top_theme_ids,
        )
        return {
            "segment_a": segment_a,
            "segment_b": segment_b,
            "rq_id": rq_id,
            "signals": [{"theme_id": theme, "description": desc} for theme, desc in signals],
            "theme_counts_a": left_counts.most_common(5),
            "theme_counts_b": right_counts.most_common(5),
        }

    def compare_sources(
        self,
        source_a: str,
        source_b: str,
        *,
        rq_id: str | None = None,
    ) -> dict[str, Any]:
        reviews = fetch_analyzed_reviews(self.session)
        return compare_source_metrics(reviews, source_a, source_b, rq_id=rq_id)

    def detect_cross_source_themes(
        self,
        *,
        rq_id: str | None = None,
        min_sources: int = 2,
    ) -> dict[str, Any]:
        reviews = fetch_analyzed_reviews(self.session)
        if rq_id:
            reviews = filter_reviews_for_rq(reviews, rq_id)
            themes = cross_source_themes(reviews, rq_id, min_sources=min_sources)
        else:
            from collections import defaultdict

            theme_sources: dict[str, set[str]] = defaultdict(set)
            for review in reviews:
                for theme in review.themes:
                    theme_sources[theme].add(review.source_key)
            themes = sorted(
                theme
                for theme, sources in theme_sources.items()
                if len(sources) >= min_sources
            )
        return {"rq_id": rq_id, "themes": themes, "min_sources": min_sources}

    def build_rq_briefing_tool(self, *, rq_ids: list[str] | None = None) -> RQBriefing:
        return build_rq_briefing(
            self.session,
            rq_ids=rq_ids,
            embedding_store=self.embedding_store,
        )

    def tool_context_text(self, tool_results: list[dict[str, Any]]) -> str:
        return json.dumps(tool_results, indent=2)

    def themes_for_review_text(self, review_id: str, rq_id: str | None) -> list[str]:
        review = self.session.get(Review, uuid.UUID(review_id))
        if review is None or review.analysis is None:
            return []
        from spotify_app_review_analyzer.analytics.aggregations import AnalyzedReview

        analyzed = AnalyzedReview(
            review_id=str(review.id),
            text=review.text,
            sentiment=review.analysis.sentiment,
            themes=tuple(review.analysis.themes or []),
            research_questions=tuple(review.analysis.research_questions or []),
            segment_tags=tuple(review.analysis.segment_tags or []),
            confidence=review.analysis.confidence,
            source_key=review.source.key if review.source else "unknown",
            published_at=review.published_at,
        )
        if rq_id:
            return themes_for_rq(analyzed, rq_id)
        return list(analyzed.themes)
