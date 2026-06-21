from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IngestMetrics:
    source_key: str
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def log_summary(self) -> None:
        logger.info(
            "Ingest summary source=%s fetched=%s inserted=%s skipped=%s failed=%s",
            self.source_key,
            self.fetched,
            self.inserted,
            self.skipped,
            self.failed,
        )
