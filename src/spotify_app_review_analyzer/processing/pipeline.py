from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.processing.classifier import get_classifier
from spotify_app_review_analyzer.processing.classifier.base import ClassificationResult
from spotify_app_review_analyzer.processing.cleaning import clean_text
from spotify_app_review_analyzer.processing.quality import QualityResult, score_quality
from spotify_app_review_analyzer.processing.segments import infer_segments


@dataclass(frozen=True)
class PipelineResult:
    status: str  # processed | skipped | failed
    cleaned_text: str
    quality: QualityResult | None
    classification: ClassificationResult | None
    segment_tags: list[str]
    skip_reason: str | None = None
    error: str | None = None


class ProcessingPipeline:
    def __init__(self, classifier_backend: str | None = None) -> None:
        self.classifier = get_classifier(classifier_backend or settings.classifier_backend)

    def run(
        self,
        text: str,
        *,
        rating: int | None = None,
        source_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineResult:
        try:
            cleaned = clean_text(text)
            quality = score_quality(cleaned, min_length=settings.min_review_text_length)
            if quality.skip_reason:
                return PipelineResult(
                    status="skipped",
                    cleaned_text=cleaned,
                    quality=quality,
                    classification=None,
                    segment_tags=[],
                    skip_reason=quality.skip_reason,
                )

            classification = self.classifier.classify(cleaned, rating=rating)
            segments = infer_segments(cleaned, source_key=source_key)
            if metadata:
                if metadata.get("subreddit"):
                    segments.append("segment.channel.reddit")
            return PipelineResult(
                status="processed",
                cleaned_text=cleaned,
                quality=quality,
                classification=classification,
                segment_tags=segments,
            )
        except Exception as exc:
            return PipelineResult(
                status="failed",
                cleaned_text=text,
                quality=None,
                classification=None,
                segment_tags=[],
                error=str(exc),
            )
