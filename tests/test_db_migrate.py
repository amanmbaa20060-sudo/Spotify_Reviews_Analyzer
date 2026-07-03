from __future__ import annotations

from unittest.mock import patch

from spotify_app_review_analyzer.db.migrate import resolve_project_root


def test_resolve_project_root_from_cwd(tmp_path, monkeypatch) -> None:
    (tmp_path / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert resolve_project_root() == tmp_path


def test_resolve_project_root_prefers_env(tmp_path, monkeypatch) -> None:
    other = tmp_path / "repo"
    other.mkdir()
    (other / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROJECT_ROOT", str(other))
    assert resolve_project_root() == other


def test_resolve_project_root_after_pip_install(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    with patch(
        "spotify_app_review_analyzer.db.migrate.__file__",
        str(tmp_path / "site-packages/spotify_app_review_analyzer/db/migrate.py"),
    ):
        assert resolve_project_root() == repo
