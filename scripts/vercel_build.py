"""Vercel build step: inject API_BASE_URL into dashboard/static/js/config.js."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "dashboard" / "static" / "js" / "config.js"


def resolve_api_base() -> str:
    raw = os.getenv("API_BASE_URL", "").strip().rstrip("/")
    if raw:
        return f"{raw}/api"
    return "/api"


def main() -> None:
    api_base = resolve_api_base()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        f"window.APP_CONFIG = {{\n  apiBase: {api_base!r},\n}};\n",
        encoding="utf-8",
    )
    print(f"Wrote {CONFIG_PATH} with apiBase={api_base!r}")


if __name__ == "__main__":
    main()
