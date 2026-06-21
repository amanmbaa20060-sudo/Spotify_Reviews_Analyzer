from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Theme:
    id: str
    rq: str
    label: str
    description: str | None = None


@dataclass(frozen=True)
class Taxonomy:
    version: str
    themes: tuple[Theme, ...]
    research_questions: dict[str, str]


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    if path is None:
        path = Path(__file__).with_name("taxonomy_v1.yml")

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    themes = tuple(Theme(**t) for t in data.get("themes", []))
    rq_raw = data.get("research_questions", {})
    research_questions = {
        key: str(value.get("label", key)) if isinstance(value, dict) else str(value)
        for key, value in rq_raw.items()
    }
    return Taxonomy(
        version=str(data.get("version", "unknown")),
        themes=themes,
        research_questions=research_questions,
    )

