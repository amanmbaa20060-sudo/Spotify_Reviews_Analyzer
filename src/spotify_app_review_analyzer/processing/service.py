from __future__ import annotations

import csv
import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.db.models import AnalysisResult, Review, ReviewEmbedding, Source
from spotify_app_review_analyzer.processing.embeddings import EmbeddingStore
from spotify_app_review_analyzer.processing.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    fetched: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    embedded: int = 0
    errors: list[str] = field(default_factory=list)

    def log_summary(self) -> None:
        logger.info(
            "Processing summary fetched=%s processed=%s skipped=%s failed=%s embedded=%s",
            self.fetched,
            self.processed,
            self.skipped,
            self.failed,
            self.embedded,
        )


class ProcessingService:
    def __init__(self, session: Session, pipeline: ProcessingPipeline | None = None) -> None:
        self.session = session
        self.pipeline = pipeline or ProcessingPipeline()
        self.embedding_store = EmbeddingStore()

    def fetch_pending(
        self,
        *,
        batch_size: int,
        force: bool = False,
        review_id: uuid.UUID | None = None,
    ) -> list[Review]:
        stmt = select(Review).options(joinedload(Review.source)).order_by(Review.created_at)
        if review_id:
            stmt = stmt.where(Review.id == review_id)
        elif not force:
            stmt = stmt.where(Review.processing_status == "pending")
        if batch_size:
            stmt = stmt.limit(batch_size)
        return list(self.session.scalars(stmt).all())

    def process_batch(
        self,
        *,
        batch_size: int = 100,
        force: bool = False,
    ) -> ProcessingMetrics:
        metrics = ProcessingMetrics()
        reviews = self.fetch_pending(batch_size=batch_size, force=force)
        metrics.fetched = len(reviews)

        for review in reviews:
            source_key = review.source.key if review.source else None
            result = self.pipeline.run(
                review.text,
                rating=review.rating,
                source_key=source_key,
                metadata=review.extra_metadata,
            )

            metadata = dict(review.extra_metadata or {})
            if result.quality:
                metadata["quality_score"] = result.quality.score

            if result.status == "skipped":
                review.processing_status = "skipped"
                metadata["skip_reason"] = result.skip_reason
                review.extra_metadata = metadata
                metrics.skipped += 1
                continue

            if result.status == "failed":
                review.processing_status = "failed"
                metadata["error"] = result.error
                review.extra_metadata = metadata
                metrics.failed += 1
                if result.error:
                    metrics.errors.append(result.error)
                continue

            classification = result.classification
            if classification is None:
                review.processing_status = "failed"
                metrics.failed += 1
                continue

            self._upsert_analysis(review.id, classification, result.segment_tags)
            review.processing_status = "processed"
            review.extra_metadata = metadata
            metrics.processed += 1

        self.session.flush()
        metrics.log_summary()
        return metrics

    def _upsert_analysis(
        self,
        review_id: uuid.UUID,
        classification,
        segment_tags: list[str],
    ) -> None:
        existing = self.session.get(AnalysisResult, review_id)
        if existing:
            existing.sentiment = classification.sentiment
            existing.sentiment_score = classification.sentiment_score
            existing.themes = classification.themes
            existing.research_questions = classification.research_questions
            existing.listening_intent = classification.listening_intent
            existing.segment_tags = segment_tags
            existing.confidence = classification.confidence
            existing.model_version = settings.model_version
            return

        self.session.add(
            AnalysisResult(
                review_id=review_id,
                sentiment=classification.sentiment,
                sentiment_score=classification.sentiment_score,
                themes=classification.themes,
                research_questions=classification.research_questions,
                listening_intent=classification.listening_intent,
                segment_tags=segment_tags,
                confidence=classification.confidence,
                model_version=settings.model_version,
                created_at=datetime.now(UTC),
            )
        )

    def _upsert_embeddings(self, review_ids: list[str], vectors: list[list[float]]) -> None:
        for review_id, vector in zip(review_ids, vectors, strict=True):
            rid = uuid.UUID(review_id)
            existing = self.session.get(ReviewEmbedding, rid)
            if existing:
                existing.embedding = vector
                existing.model_version = settings.model_version
            else:
                self.session.add(
                    ReviewEmbedding(
                        review_id=rid,
                        embedding=vector,
                        model_version=settings.model_version,
                        created_at=datetime.now(UTC),
                    )
                )

    def rebuild_all_embeddings(self) -> int:
        rows = self.session.execute(
            select(Review.id, Review.text)
            .where(Review.processing_status == "processed")
            .order_by(Review.created_at)
        ).all()
        if not rows:
            return 0
        ids = [str(row[0]) for row in rows]
        texts = [row[1] for row in rows]
        vectors = self.embedding_store.fit_transform(texts, ids)
        self._upsert_embeddings(ids, vectors)
        self.session.flush()
        return len(vectors)

    def semantic_search(self, query: str, *, top_k: int = 5) -> list[dict]:
        if not self.embedding_store.review_ids:
            self.rebuild_all_embeddings()
        hits = self.embedding_store.search(query, top_k=top_k)
        if not hits:
            return []

        review_ids = [uuid.UUID(hit.review_id) for hit in hits]
        reviews = {
            str(r.id): r
            for r in self.session.scalars(select(Review).where(Review.id.in_(review_ids)))
        }
        output: list[dict] = []
        for hit in hits:
            review = reviews.get(hit.review_id)
            if not review:
                continue
            output.append(
                {
                    "review_id": hit.review_id,
                    "score": hit.score,
                    "text": review.text[:300],
                    "source_id": str(review.source_id),
                }
            )
        return output

    def export_validation_sample(self, *, sample_size: int = 100, seed: int = 42) -> Path:
        export_dir = Path(settings.validation_export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / "validation_sample.csv"

        rows = self.session.execute(
            select(
                Review.id,
                Source.key,
                Review.text,
                Review.rating,
                AnalysisResult.sentiment,
                AnalysisResult.themes,
                AnalysisResult.research_questions,
                AnalysisResult.confidence,
            )
            .join(Source, Review.source_id == Source.id)
            .join(AnalysisResult, AnalysisResult.review_id == Review.id)
            .where(Review.processing_status == "processed")
        ).all()

        if not rows:
            path.write_text("", encoding="utf-8")
            return path

        rng = random.Random(seed)
        selected = rows if len(rows) <= sample_size else rng.sample(rows, sample_size)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "review_id",
                    "source",
                    "rating",
                    "sentiment",
                    "themes",
                    "research_questions",
                    "confidence",
                    "text",
                ]
            )
            for row in selected:
                writer.writerow(
                    [
                        str(row[0]),
                        row[1],
                        row[2] or "",
                        row[4] or "",
                        ";".join(row[5] or []),
                        ";".join(row[6] or []),
                        row[7] or "",
                        row[3],
                    ]
                )

        logger.info("Exported validation sample (%s rows) to %s", len(selected), path)
        return path

    def status_counts(self) -> dict[str, int]:
        rows = self.session.execute(
            select(Review.processing_status, func.count())
            .group_by(Review.processing_status)
        ).all()
        return {status: count for status, count in rows}
