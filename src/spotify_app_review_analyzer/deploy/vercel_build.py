"""Vercel build step: validate proxy config and write dashboard/static/js/config.js."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "dashboard" / "static" / "js" / "config.js"


def backend_url_configured() -> bool:
    return bool((os.getenv("API_BASE_URL") or os.getenv("RENDER_API_URL") or "").strip())


def resolve_api_base() -> str:
    """Use direct Render URL when set (CORS-enabled); otherwise same-origin /api + middleware."""
    raw = (os.getenv("API_BASE_URL") or os.getenv("RENDER_API_URL") or "").strip().rstrip("/")
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
    mode = "direct Render URL" if api_base.startswith("http") else "same-origin /api (middleware)"
    print(f"Wrote {CONFIG_PATH} with apiBase={api_base!r} ({mode})")

    if os.getenv("VERCEL") and not backend_url_configured():
        print(
            "WARNING: API_BASE_URL is not set on Vercel. "
            "Add it under Settings → Environment Variables, then redeploy.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
