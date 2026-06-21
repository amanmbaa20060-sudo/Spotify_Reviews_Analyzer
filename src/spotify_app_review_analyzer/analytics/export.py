from __future__ import annotations

import json
from pathlib import Path

from spotify_app_review_analyzer.analytics.schemas import RQBriefing, RQSection


def export_briefing_json(briefing: RQBriefing, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(briefing.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _format_pct(mix: dict[str, float]) -> str:
    if not mix:
        return "_No data_"
    parts = [f"{sentiment} {pct:g}%" for sentiment, pct in sorted(mix.items())]
    return ", ".join(parts)


def _format_breakdown(breakdown: dict[str, float]) -> str:
    if not breakdown:
        return "_No data_"
    parts = [f"{source} {pct:g}%" for source, pct in sorted(breakdown.items())]
    return ", ".join(parts)


def _section_markdown(section: RQSection) -> str:
    lines = [
        f"## {section.rq_id.upper()}: {section.label}",
        "",
        f"- **Reviews:** {section.review_count}",
        f"- **Readiness:** {section.readiness}",
        f"- **Avg confidence:** {section.avg_confidence if section.avg_confidence is not None else 'n/a'}",
        f"- **Sentiment mix:** {_format_pct(section.sentiment_mix)}",
        f"- **Source breakdown:** {_format_breakdown(section.source_breakdown)}",
        "",
        "### Top themes",
        "",
    ]

    if section.top_themes:
        for theme in section.top_themes:
            lines.append(f"- `{theme.theme_id}` — {theme.label} ({theme.count})")
    else:
        lines.append("_No themes tagged for this RQ._")

    lines.extend(["", "### Cross-source themes", ""])
    if section.cross_source_themes:
        for theme_id in section.cross_source_themes:
            lines.append(f"- `{theme_id}`")
    else:
        lines.append("_None detected across multiple sources._")

    lines.extend(["", "### Segment signals", ""])
    if section.segment_signals:
        for signal in section.segment_signals:
            lines.append(f"- {signal.description}")
    else:
        lines.append("_No directional segment contrasts detected._")

    lines.extend(["", "### Exemplar citations", ""])
    if section.exemplar_citations:
        by_theme: dict[str, list] = {}
        for citation in section.exemplar_citations:
            by_theme.setdefault(citation.theme_id, []).append(citation)
        for theme_id, citations in by_theme.items():
            lines.append(f"**{theme_id}**")
            for citation in citations:
                lines.append(
                    f"- `{citation.review_id}` ({citation.source_key}, "
                    f"{citation.sentiment or 'unknown'}): "
                    f"\"{citation.snippet}\""
                )
            lines.append("")
    else:
        lines.append("_No exemplars selected._")

    lines.append("")
    return "\n".join(lines)


def export_briefing_markdown(briefing: RQBriefing, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# RQ Briefing — Spotify App Review Analyzer",
        "",
        f"_Generated: {briefing.generated_at}_",
        f"_Taxonomy: v{briefing.taxonomy_version} | Model: {briefing.model_version or 'n/a'}_",
        f"_Processed reviews: {briefing.total_processed_reviews}_",
        "",
        "Deterministic pre-LLM briefing for RQ1–RQ6. Use before Groq synthesis (Phase 4B).",
        "",
    ]

    verification = briefing.verification
    if verification:
        status = "PASSED" if verification.get("passed") else "FAILED"
        lines.append(f"**Verification:** {status}")
        if verification.get("mismatches"):
            lines.append("")
            lines.append("Count mismatches:")
            for mismatch in verification["mismatches"]:
                lines.append(
                    f"- {mismatch['field']}: briefing={mismatch['briefing']}, "
                    f"sql={mismatch['sql']}"
                )
        lines.append("")

    for section in briefing.sections:
        lines.append(_section_markdown(section))

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
