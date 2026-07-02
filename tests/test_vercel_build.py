import os

from scripts.vercel_build import backend_url_configured


def test_backend_url_configured_false(monkeypatch) -> None:
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("RENDER_API_URL", raising=False)
    assert backend_url_configured() is False


def test_backend_url_configured_true(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "https://example.onrender.com")
    assert backend_url_configured() is True


def test_vercel_build_writes_same_origin_config(tmp_path, monkeypatch) -> None:
    import scripts.vercel_build as build

    config_path = tmp_path / "dashboard" / "static" / "js" / "config.js"
    monkeypatch.setattr(build, "CONFIG_PATH", config_path)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("API_BASE_URL", "https://api.example.com")
    build.main()
    text = config_path.read_text(encoding="utf-8")
    assert "apiBase: '/api'" in text


def test_vercel_build_warns_without_backend_on_vercel(tmp_path, monkeypatch, capsys) -> None:
    import scripts.vercel_build as build

    config_path = tmp_path / "dashboard" / "static" / "js" / "config.js"
    monkeypatch.setattr(build, "CONFIG_PATH", config_path)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("RENDER_API_URL", raising=False)
    build.main()
    assert "WARNING" in capsys.readouterr().err
