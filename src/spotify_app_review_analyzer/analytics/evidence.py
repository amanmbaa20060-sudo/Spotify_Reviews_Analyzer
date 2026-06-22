from __future__ import annotations

from collections import defaultdict

from spotify_app_review_analyzer.analytics.aggregations import AnalyzedReview, themes_for_rq
from spotify_app_review_analyzer.analytics.schemas import ExemplarCitation
from spotify_app_review_analyzer.processing.embeddings import EmbeddingStore
from spotify_app_review_analyzer.taxonomy.loader import Theme, load_taxonomy

SNIPPET_MAX_LEN = 250


def _snippet(text: str, *, max_len: int = SNIPPET_MAX_LEN) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def _candidate_score(review: AnalyzedReview, tfidf_score: float = 0.0) -> float:
    confidence = review.confidence or 0.0
    length_bonus = min(len(review.text) / 200.0, 1.0) * 0.1
    return confidence + tfidf_score + length_bonus


def _tfidf_scores_for_theme(
    theme: Theme,
    candidates: list[AnalyzedReview],
    embedding_store: EmbeddingStore | None,
) -> dict[str, float]:
    if embedding_store is None or not candidates:
        return {}

    query = f"{theme.label}. {theme.description or ''}".strip()
    hits = embedding_store.search(query, top_k=max(20, len(candidates) * 2))
    candidate_ids = {review.review_id for review in candidates}
    return {
        hit.review_id: hit.score
        for hit in hits
        if hit.review_id in candidate_ids
    }


def select_exemplars_for_theme(
    theme: Theme,
    reviews: list[AnalyzedReview],
    rq_id: str,
    *,
    per_theme: int,
    embedding_store: EmbeddingStore | None = None,
) -> list[ExemplarCitation]:
    candidates = [
        review
        for review in reviews
        if theme.id in themes_for_rq(review, rq_id)
    ]
    if not candidates:
        return []

    tfidf_scores = _tfidf_scores_for_theme(theme, candidates, embedding_store)
    ranked = sorted(
        candidates,
        key=lambda review: _candidate_score(review, tfidf_scores.get(review.review_id, 0.0)),
        reverse=True,
    )

    by_source: dict[str, list[AnalyzedReview]] = defaultdict(list)
    for review in ranked:
        by_source[review.source_key].append(review)

    selected: list[ExemplarCitation] = []
    seen_ids: set[str] = set()
    source_keys = sorted(by_source.keys())

    while len(selected) < per_theme and source_keys:
        progressed = False
        for source_key in list(source_keys):
            bucket = by_source[source_key]
            while bucket:
                review = bucket.pop(0)
                if review.review_id in seen_ids:
                    continue
                seen_ids.add(review.review_id)
                selected.append(
                    ExemplarCitation(
                        review_id=review.review_id,
                        source_key=review.source_key,
                        sentiment=review.sentiment,
                        confidence=review.confidence,
                        snippet=_snippet(review.text),
                        theme_id=theme.id,
                    )
                )
                progressed = True
                break
            if len(selected) >= per_theme:
                break
        if not progressed:
            break

    return selected


def select_exemplars_for_rq(
    rq_id: str,
    reviews: list[AnalyzedReview],
    top_theme_ids: list[str],
    *,
    per_theme: int,
    embedding_store: EmbeddingStore | None = None,
) -> list[ExemplarCitation]:
    taxonomy = load_taxonomy()
    theme_by_id = {theme.id: theme for theme in taxonomy.themes}
    citations: list[ExemplarCitation] = []

    for theme_id in top_theme_ids:
        theme = theme_by_id.get(theme_id)
        if theme is None:
            continue
        citations.extend(
            select_exemplars_for_theme(
                theme,
                reviews,
                rq_id,
                per_theme=per_theme,
                embedding_store=embedding_store,
            )
        )
    return citations


def select_negative_problem_evidence(
    rq_id: str,
    reviews: list[AnalyzedReview],
    top_theme_ids: list[str],
    *,
    limit: int = 5,
    embedding_store: EmbeddingStore | None = None,
) -> list[ExemplarCitation]:
    """Negative reviews tied to top problem themes for an RQ (dashboard Key Evidence)."""
    negative_reviews = [review for review in reviews if review.sentiment == "negative"]
    if not negative_reviews or not top_theme_ids:
        return []

    per_theme = max(1, (limit + len(top_theme_ids) - 1) // len(top_theme_ids))
    citations = select_exemplars_for_rq(
        rq_id,
        negative_reviews,
        top_theme_ids,
        per_theme=per_theme,
        embedding_store=embedding_store,
    )
    return [citation for citation in citations if citation.sentiment == "negative"][:limit]
