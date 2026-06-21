from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from spotify_app_review_analyzer.analytics.briefing import build_rq_briefing
from spotify_app_review_analyzer.analytics.export import export_briefing_json, export_briefing_markdown
from spotify_app_review_analyzer.analytics.schemas import RQ_IDS, RQBriefing
from spotify_app_review_analyzer.core.settings import settings

logger = logging.getLogger(__name__)


class RQAnalysisService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_briefing(self, rq_ids: list[str] | None = None) -> RQBriefing:
        return build_rq_briefing(self.session, rq_ids=rq_ids)

    def export_briefing(
        self,
        briefing: RQBriefing,
        *,
        export_dir: Path | None = None,
    ) -> tuple[Path, Path]:
        out_dir = export_dir or Path(settings.validation_export_dir)
        md_path = export_briefing_markdown(briefing, out_dir / "rq_briefing.md")
        json_path = export_briefing_json(briefing, out_dir / "rq_briefing.json")
        logger.info("Exported RQ briefing to %s and %s", md_path, json_path)
        return md_path, json_path

    def run(
        self,
        *,
        rq_ids: list[str] | None = None,
        export: bool = True,
    ) -> RQBriefing:
        targets = rq_ids or list(RQ_IDS)
        briefing = self.build_briefing(rq_ids=targets)
        if export:
            self.export_briefing(briefing)
        return briefing
