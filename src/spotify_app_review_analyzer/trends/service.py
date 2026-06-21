from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from spotify_app_review_analyzer.analytics.aggregations import (
    cross_source_themes,
    fetch_analyzed_reviews,
    filter_reviews_for_rq,
)
from spotify_app_review_analyzer.core.settings import settings
from spotify_app_review_analyzer.trends.detection import (
    SOCIAL_SOURCE_KEYS,
    compute_daily_theme_volumes,
    detect_bursts,
    fetch_social_reviews,
    top_rising_themes,
    viral_summary,
)

logger = logging.getLogger(__name__)


class TrendService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_report(self, *, days: int | None = None) -> dict:
        window = days or settings.trend_window_days
        social_reviews = fetch_social_reviews(self.session, days=window)
        volumes = compute_daily_theme_volumes(social_reviews, days=window)
        bursts = detect_bursts(volumes, threshold=settings.trend_burst_multiplier)
        rising = top_rising_themes(volumes, top_n=settings.trend_top_n)

        all_reviews = fetch_analyzed_reviews(self.session)
        social_only = [r for r in all_reviews if r.source_key in SOCIAL_SOURCE_KEYS]
        app_store = [r for r in all_reviews if r.source_key == "app_store"]

        cross_rq2_social = cross_source_themes(
            filter_reviews_for_rq(all_reviews, "rq2"),
            "rq2",
            min_sources=2,
        )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "window_days": window,
            "social_processed_count": len(social_reviews),
            "viral_summary": viral_summary(social_reviews),
            "burst_signals": [
                {
                    "theme_id": signal.theme_id,
                    "source_key": signal.source_key,
                    "day": signal.day.isoformat(),
                    "current_count": signal.current_count,
                    "baseline_avg": signal.baseline_avg,
                    "multiplier": signal.multiplier,
                }
                for signal in bursts
            ],
            "rising_themes": [
                {
                    "theme_id": item.theme_id,
                    "source_key": item.source_key,
                    "current_count": item.current_count,
                    "baseline_avg": item.baseline_avg,
                    "growth_ratio": item.growth_ratio,
                }
                for item in rising
            ],
            "cross_source_rq2_themes": cross_rq2_social,
            "source_counts": {
                "social": len(social_only),
                "app_store": len(app_store),
            },
        }

    def export(self, *, days: int | None = None) -> tuple[Path, Path]:
        report = self.build_report(days=days)
        export_dir = Path(settings.validation_export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_dir / "social_trends.json"
        md_path = export_dir / "social_trends.md"
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(self._to_markdown(report), encoding="utf-8")
        logger.info("Exported social trends to %s and %s", json_path, md_path)
        return md_path, json_path

    @staticmethod
    def _to_markdown(report: dict) -> str:
        lines = [
            "# Social Trends Report",
            "",
            f"_Generated: {report['generated_at']}_",
            f"_Window: {report['window_days']} days_",
            f"_Social processed reviews: {report['social_processed_count']}_",
            "",
            "## Viral vs steady-state",
            "",
            f"- Viral: {report['viral_summary'].get('viral', 0)}",
            f"- Steady-state: {report['viral_summary'].get('steady_state', 0)}",
            "",
            "## Burst signals (>2x 7-day avg)",
            "",
        ]
        if report["burst_signals"]:
            for signal in report["burst_signals"]:
                lines.append(
                    f"- `{signal['theme_id']}` on **{signal['source_key']}** "
                    f"({signal['current_count']} vs avg {signal['baseline_avg']}, "
                    f"{signal['multiplier']}x)"
                )
        else:
            lines.append("_No burst signals detected in the current window._")

        lines.extend(["", "## Top rising themes (social)", ""])
        if report["rising_themes"]:
            for item in report["rising_themes"]:
                lines.append(
                    f"- `{item['theme_id']}` ({item['source_key']}): "
                    f"{item['growth_ratio']}x growth"
                )
        else:
            lines.append("_No rising themes in the current window._")

        lines.extend(["", "## Cross-source RQ2 themes", ""])
        for theme in report.get("cross_source_rq2_themes", []):
            lines.append(f"- `{theme}`")
        lines.append("")
        return "\n".join(lines)
