# Copyright 2026 Aaron John Schlosser, PhD.
"""Pause, delete-build and delete-source operations for the Corpus Builder."""
import sys
import types
from pathlib import Path

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import corpus_builder as cb  # noqa: E402


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    mgr = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(mgr._executor, "submit", lambda *a, **k: None)
    return mgr


def _build(manager, name="essay.txt"):
    asset = manager.repo.save_asset(b"One paragraph of text.\n\nAnother paragraph.", filename=name)
    build = manager.create({"asset_id": asset["asset_id"], "provider": "ollama", "model": "m"})
    return asset, build


def test_pause_requires_running_build_and_marks_request(manager):
    _, build = _build(manager)
    build["status"] = "running"
    manager.repo.save_build(build)
    paused = manager.pause(build["build_id"])
    assert paused["pause_requested"] and manager._cancelled(build["build_id"])
    build["status"] = "cancelled"
    manager.repo.save_build(build)
    with pytest.raises(ValueError):
        manager.pause(build["build_id"])


def test_delete_build_removes_workspace_but_refuses_running(manager):
    _, build = _build(manager)
    build["status"] = "running"
    manager.repo.save_build(build)
    with pytest.raises(ValueError):
        manager.discard_build(build["build_id"])
    build["status"] = "cancelled"
    manager.repo.save_build(build)
    manager.discard_build(build["build_id"])
    with pytest.raises(KeyError):
        manager.repo.get_build(build["build_id"])


def test_delete_source_needs_cascade_when_builds_use_it(manager):
    asset, build = _build(manager)
    build = manager.repo.get_build(build["build_id"])
    build["status"] = "cancelled"
    manager.repo.save_build(build)
    with pytest.raises(ValueError):
        manager.discard_source(build["asset_id"])
    result = manager.discard_source(build["asset_id"], cascade=True)
    assert result["builds_deleted"] == 1
    with pytest.raises(KeyError):
        manager.repo.get_asset(asset["asset_id"])


def test_delete_source_without_builds(manager):
    asset = manager.repo.save_asset(b"Just text here.", filename="a.txt")
    manager.discard_source(asset["asset_id"])
    assert manager.repo.list_assets() == []
