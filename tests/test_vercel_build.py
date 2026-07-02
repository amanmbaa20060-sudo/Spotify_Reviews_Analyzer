import os
from pathlib import Path

from scripts.vercel_build import resolve_api_base


def test_resolve_api_base_default() -> None:
    os.environ.pop("API_BASE_URL", None)
    assert resolve_api_base() == "/api"


def test_resolve_api_base_render_url(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "https://example.onrender.com/")
    assert resolve_api_base() == "https://example.onrender.com/api"


def test_vercel_build_writes_config(tmp_path, monkeypatch) -> None:
    import scripts.vercel_build as build

    config_path = tmp_path / "dashboard" / "static" / "js" / "config.js"
    monkeypatch.setattr(build, "CONFIG_PATH", config_path)
    monkeypatch.setenv("API_BASE_URL", "https://api.example.com")
    build.main()
    text = config_path.read_text(encoding="utf-8")
    assert "https://api.example.com/api" in text
