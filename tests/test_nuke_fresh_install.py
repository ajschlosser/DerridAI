# Copyright 2026 Aaron John Schlosser, PhD.
"""NUKE returns DerridAI to the same empty first-run state as a fresh data directory.

Why: the previous reset only deleted Chroma collections and browser IndexedDB, leaving
users, provider profiles, PDF corpora, and job history in place. After NUKE the next
load must ask for a new administrator, with shipped locales and no corpus data.
How: drives AuthStore / SystemStore / ChromaStore.nuke against temporary paths, then
calls the admin nuke route with the live job managers stubbed idle.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from starlette.responses import Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import auth
from app import chroma_store as cs
from app import system_store as system_store_mod
from app.auth import DEFAULT_RESEARCHER_CAPABILITIES, AuthStore
from app.persistence import SQLiteJobRepository, SQLiteSystemRepository
from app.system_store import SystemStore


def configure_auth(monkeypatch, tmp_path: Path) -> None:
    """Point AuthStore at a temp database with cheap password hashing."""
    monkeypatch.setattr(auth, "PBKDF2_ITERATIONS", 1_000)
    monkeypatch.setattr(
        auth,
        "settings",
        SimpleNamespace(
            auth_db_path=str(tmp_path / "auth.sqlite3"),
            auth_login_max_failures=5,
            auth_login_lockout_seconds=300,
        ),
    )


def test_auth_reset_returns_to_bootstrap_and_builtin_roles(monkeypatch, tmp_path: Path):
    """Users, sessions, lockouts, and custom roles disappear; bootstrap works again."""
    configure_auth(monkeypatch, tmp_path)
    store = AuthStore()
    admin = store.bootstrap_admin("owner", "secret-password")
    token = store.create_session(admin.id)
    store.create_user("reader", "secret-password", "researcher")
    store.create_role("Reviewer", "Custom review role")
    store.authenticate("reader", "wrong-password")
    store.set_role_permissions("researcher", [])

    result = store.reset_to_fresh_install()

    assert result["deleted_users"] == 2
    assert result["deleted_custom_roles"] == 1
    assert store.bootstrap_required() is True
    assert store.user_for_session(token) is None
    assert store.role_ids() == {"admin", "researcher"}
    assert set(store.capabilities_for_role("researcher")) == set(DEFAULT_RESEARCHER_CAPABILITIES)

    created = store.bootstrap_admin("fresh-admin", "new-secret")
    assert created.username == "fresh-admin"
    assert created.role == "admin"
    assert created.id == 1
    assert store.bootstrap_required() is False


def test_system_reset_reseeds_locales_and_clears_jobs(tmp_path: Path, monkeypatch):
    """Provider profiles, annotations, and job rows are dropped; en-US/fr-CA return."""
    db_path = tmp_path / "system.sqlite3"
    repo = SQLiteSystemRepository(db_path)
    monkeypatch.setattr(system_store_mod, "system_repository", repo)
    store = SystemStore()
    store.set_researcher_profiles([
        {"id": "local", "name": "Local", "type": "ollama", "base_url": "http://ollama", "model": "x"},
    ])
    store.add_annotation({"note": "keep me", "user_id": 3})
    jobs = SQLiteJobRepository(db_path)
    jobs.upsert({
        "id": "job-1",
        "type": "llm",
        "status": "completed",
        "created_at": "2026-09-19T00:00:00+00:00",
        "owner": "owner",
    })

    result = store.reset_to_fresh_install()

    assert result["languages"] == ["en-US", "fr-CA"]
    assert result["profiles"] == 0
    assert result["annotations"] == 0
    assert store.researcher_profiles() == []
    assert store.list_annotations() == []
    languages = store.repository.load()["languages"]
    assert set(languages) == {"en-US", "fr-CA"}
    assert languages["en-US"]["name"] == "English"
    assert languages["fr-CA"]["name"] == "Français"
    assert "content_policy" not in languages["en-US"]
    assert jobs.load("llm") == []
    with sqlite3.connect(db_path) as conn:
        assert int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]) == 0


def test_chroma_nuke_removes_catalog_files(tmp_path: Path):
    """Collection directories and chroma.sqlite3 are removed; .gitkeep is kept."""
    root = tmp_path / "chroma"
    (root / "uuid-collection").mkdir(parents=True)
    (root / "chroma.sqlite3").write_text("catalog", encoding="utf-8")
    (root / ".gitkeep").write_text("", encoding="utf-8")

    class FakeCollection:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeClient:
        def __init__(self) -> None:
            self.names = ["works", "derridai_response_cache"]
            self.deleted: list[str] = []

        def list_collections(self):
            return [FakeCollection(name) for name in list(self.names)]

        def delete_collection(self, name: str) -> None:
            self.deleted.append(name)
            self.names.remove(name)

    store = cs.ChromaStore.__new__(cs.ChromaStore)
    client = FakeClient()
    store._client = client
    store._path = str(root)
    store._data_root = tmp_path

    result = store.nuke()

    assert result["deleted_collections"] == 2
    assert client.deleted == ["works", "derridai_response_cache"]
    assert store._client is None
    assert (root / ".gitkeep").exists()
    assert not (root / "chroma.sqlite3").exists()
    assert not (root / "uuid-collection").exists()


def test_nuke_route_blocked_when_jobs_are_active(monkeypatch):
    """Active background work still returns HTTP 409 and does not reset state."""
    from app.routers import admin as admin_routes

    monkeypatch.setattr(admin_routes.llm_jobs, "active_count", lambda: 1)
    try:
        admin_routes.nuke(Response())
        raise AssertionError("expected HTTP 409")
    except HTTPException as exc:
        assert exc.status_code == 409


def test_nuke_route_clears_session_and_reports_bootstrap(monkeypatch, tmp_path: Path):
    """The admin route wipes corpus trees, resets stores, and expires the session cookie."""
    from app.routers import admin as admin_routes

    data_root = tmp_path / "data"
    chroma_dir = data_root / "chroma"
    pdf_root = data_root / ".home" / "pdf-corpus"
    for part in ("assets", "builds", "publications"):
        (pdf_root / part).mkdir(parents=True, exist_ok=True)
    (pdf_root / "assets" / "keep.pdf").write_bytes(b"%PDF")
    (data_root / ".derridai_tmp" / "scratch").mkdir(parents=True)
    chroma_dir.mkdir(parents=True)

    class IdleJobs:
        def active_count(self) -> int:
            return 0

        def clear_all(self) -> int:
            return 2

    class FakeChroma:
        def nuke(self) -> dict[str, object]:
            return {"deleted_collections": 3, "removed_paths": 1, "path": str(chroma_dir)}

    class FakeCorpusRepo:
        root = pdf_root

    class FakeCorpusBuilds:
        def active_count(self) -> int:
            return 0

        def reset_in_memory_state(self) -> None:
            self.reset = True

    monkeypatch.setattr(admin_routes, "llm_jobs", IdleJobs())
    monkeypatch.setattr(admin_routes, "llm_tool_jobs", IdleJobs())
    monkeypatch.setattr(admin_routes, "rag_jobs", IdleJobs())
    monkeypatch.setattr(admin_routes, "upsert_jobs", IdleJobs())
    monkeypatch.setattr(admin_routes, "store", FakeChroma())
    monkeypatch.setattr(admin_routes, "pdf_corpus_repository", FakeCorpusRepo())
    builds = FakeCorpusBuilds()
    monkeypatch.setattr(admin_routes, "pdf_corpus_builds", builds)
    monkeypatch.setattr(admin_routes, "settings", replace(admin_routes.settings, chroma_data_root=str(data_root)))

    configure_auth(monkeypatch, tmp_path)
    auth_store = AuthStore()
    auth_store.bootstrap_admin("owner", "secret-password")
    monkeypatch.setattr(admin_routes, "auth_store", auth_store)

    repo = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    monkeypatch.setattr(system_store_mod, "system_repository", repo)
    system = SystemStore()
    system.set_researcher_profiles([
        {"id": "local", "name": "Local", "type": "ollama", "base_url": "http://ollama", "model": "x"},
    ])
    monkeypatch.setattr(admin_routes, "system_store", system)

    response = Response()
    payload = admin_routes.nuke(response)

    assert payload["ok"] is True
    assert payload["bootstrap_required"] is True
    assert payload["cleared_jobs"] == 8
    assert payload["auth"]["deleted_users"] == 1
    assert auth_store.bootstrap_required() is True
    assert system.researcher_profiles() == []
    assert not (pdf_root / "assets" / "keep.pdf").exists()
    assert (pdf_root / "assets").is_dir()
    assert not (data_root / ".derridai_tmp").exists()
    assert builds.reset is True
    cookie = response.headers.get("set-cookie", "")
    assert "derridai_session=" in cookie
    assert "Max-Age=0" in cookie or "max-age=0" in cookie.lower()
