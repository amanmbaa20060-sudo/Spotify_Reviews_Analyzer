from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NormalizedReview:
    source_key: str
    external_id: str | None
    text: str
    title: str | None = None
    rating: int | None = None
    author_hash: str | None = None
    published_at: datetime | None = None
    app_version: str | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


class IngestionProvider(ABC):
    source_key: str

    @abstractmethod
    def fetch(self, *, limit: int | None = None) -> list[NormalizedReview]:
        """Fetch and normalize reviews from the source."""
