"""CLI entry for Vercel build (no pip install required on Vercel)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spotify_app_review_analyzer.deploy.vercel_build import main  # noqa: E402

if __name__ == "__main__":
    main()
