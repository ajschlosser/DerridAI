# Copyright 2026 Aaron John Schlosser, PhD.
"""The displayed app version can include the git commit that built this process."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.config import app_version_label, resolve_git_commit


def test_app_version_label_includes_commit_when_present():
    assert app_version_label("1.2.3", "abc1234") == "1.2.3 (abc1234)"
    assert app_version_label("1.2.3", "") == "1.2.3"
    assert app_version_label("1.2.3", "  ") == "1.2.3"


def test_git_commit_prefers_environment(monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "deadbeefcafebabe")
    assert resolve_git_commit() == "deadbeefcafebabe"
    monkeypatch.delenv("GIT_COMMIT")
    monkeypatch.setenv("SOURCE_COMMIT", "abc1234 extra")
    assert resolve_git_commit() == "abc1234"


def test_git_commit_reads_baked_docker_file(monkeypatch, tmp_path: Path):
    baked = tmp_path / "git-commit"
    baked.write_text("cafed00d\n", encoding="utf-8")
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    monkeypatch.setattr("app.config._GIT_COMMIT_FILE", baked)
    assert resolve_git_commit() == "cafed00d"


def test_empty_git_commit_env_does_not_override_baked_file(monkeypatch, tmp_path: Path):
    baked = tmp_path / "git-commit"
    baked.write_text("cafed00d\n", encoding="utf-8")
    monkeypatch.setenv("GIT_COMMIT", "")
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    monkeypatch.setattr("app.config._GIT_COMMIT_FILE", baked)
    assert resolve_git_commit() == "cafed00d"
