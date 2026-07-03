from __future__ import annotations

import os
from unittest.mock import patch

from spotify_app_review_analyzer.deploy.seed import auto_seed_enabled


def test_auto_seed_explicit_true() -> None:
    with patch.dict(os.environ, {"AUTO_SEED_IF_EMPTY": "true"}, clear=False):
        assert auto_seed_enabled() is True


def test_auto_seed_defaults_on_render() -> None:
    env = {k: v for k, v in os.environ.items() if k != "AUTO_SEED_IF_EMPTY"}
    env["RENDER"] = "true"
    with patch.dict(os.environ, env, clear=True):
        assert auto_seed_enabled() is True


def test_auto_seed_off_by_default_locally() -> None:
    env = {k: v for k, v in os.environ.items() if k not in {"AUTO_SEED_IF_EMPTY", "RENDER"}}
    with patch.dict(os.environ, env, clear=True):
        assert auto_seed_enabled() is False
