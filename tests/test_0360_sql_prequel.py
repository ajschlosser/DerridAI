from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.persistence import SQLiteJobRepository, SQLiteSystemRepository


def test_0360_release_identity_and_storage_configuration():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    main = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
    config = (ROOT / "api/app/config.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert package["version"] == "0.36.0"
    assert 'version="0.36.0"' in main
    assert '"app_version": "0.36.0"' in main
    assert "SYSTEM_DB_PATH" in config
    assert "SYSTEM_DB_PATH" in compose
    assert "0.36.0 — The SQL Prequel" in readme


def test_system_repository_round_trip_is_transactional_sqlite(tmp_path: Path):
    repo = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    payload = {
        "language_dictionary_revision": "test.1",
        "researcher_provider_profiles": [
            {"id": "local", "name": "Local", "type": "ollama", "api_key": "write-only-secret"}
        ],
        "annotations": [
            {"id": "a1", "user_id": 7, "created_at": "2026-09-15T10:00:00+00:00", "note": "note"}
        ],
        "languages": {
            "en-US": {"name": "English", "flag": "🇺🇸", "dictionary": {"hello": "Hello"}},
            "fr-CA": {
                "name": "Français",
                "flag": "🇨🇦",
                "dictionary": {"hello": "Bonjour"},
                "translation_report": {"status": "complete"},
            },
        },
    }

    repo.replace(payload)
    restored = repo.load()

    assert restored == payload
    info = repo.describe()
    assert info["backend"] == "sqlite"
    assert info["journal_mode"].lower() == "wal"
    assert info["schema_version"] >= 1
    assert info["size_bytes"] > 0


def test_legacy_system_json_migrates_non_destructively(tmp_path: Path):
    db_path = tmp_path / "derridai-system.sqlite3"
    legacy = tmp_path / "derridai-system.json"
    payload = {
        "language_dictionary_revision": "legacy",
        "researcher_provider_profiles": [],
        "annotations": [],
        "languages": {"en-US": {"name": "English", "flag": "🇺🇸", "dictionary": {"x": "X"}}},
    }
    legacy.write_text(json.dumps(payload), encoding="utf-8")

    repo = SQLiteSystemRepository(db_path)
    assert repo.migrate_legacy_json(legacy) is True
    assert repo.load() == payload
    assert not legacy.exists()
    assert (tmp_path / "derridai-system.migrated-v0.36.0.json").exists()


def test_job_repository_survives_restart_and_marks_active_job_interrupted(tmp_path: Path):
    db_path = tmp_path / "derridai-system.sqlite3"
    repo = SQLiteJobRepository(db_path)
    job = {
        "id": "job-1",
        "type": "llm_tool",
        "mode": "language_dictionary",
        "owner": "admin",
        "status": "running",
        "created_at": "2026-09-15T10:00:00+00:00",
        "started_at": "2026-09-15T10:00:01+00:00",
        "events": [],
        "_resume_dictionary": {"a": "A traduit"},
        "_resume_failed_keys": ["b"],
        "result": {"resumable": True, "partial_key_count": 1},
    }
    repo.upsert(job)

    restarted = SQLiteJobRepository(db_path)
    assert restarted.recover_interrupted() == 1
    loaded = restarted.load("llm_tool")

    assert len(loaded) == 1
    recovered = loaded[0]
    assert recovered["status"] == "failed"
    assert recovered["_resume_dictionary"] == {"a": "A traduit"}
    assert recovered["_resume_failed_keys"] == ["b"]
    assert recovered["result"]["resumable"] is True
    assert "restart" in recovered["error_message"].lower()
    assert recovered["events"][-1]["stage"] == "interrupted"


def test_jobs_and_system_state_share_one_durable_database(tmp_path: Path):
    path = tmp_path / "derridai-system.sqlite3"
    system = SQLiteSystemRepository(path)
    jobs = SQLiteJobRepository(path)

    system.replace({
        "researcher_provider_profiles": [],
        "annotations": [],
        "languages": {"en-US": {"name": "English", "flag": "🇺🇸", "dictionary": {}}},
    })
    jobs.upsert({
        "id": "rag-1",
        "type": "rag",
        "status": "completed",
        "owner": "researcher",
        "created_at": "2026-09-15T11:00:00+00:00",
        "events": [],
        "result": {"answer": "answer"},
    })

    assert system.load()["languages"]["en-US"]["name"] == "English"
    assert jobs.load("rag")[0]["result"]["answer"] == "answer"


def test_language_translation_emits_durable_checkpoint(monkeypatch):
    import app.i18n_translation as module

    def fake_chat_complete(**kwargs):
        assert kwargs["json_mode"] is True
        return json.dumps({"hello": "Bonjour"})

    monkeypatch.setattr(module, "chat_complete", fake_chat_complete)
    checkpoints = []
    translated, stats = module.translate_english_dictionary(
        code="fr-CA",
        dictionary={"hello": "Hello there"},
        provider="ollama",
        model="translator",
        base_url=None,
        api_key=None,
        checkpoint=lambda partial, failed, failures, current: checkpoints.append(
            (dict(partial), list(failed), list(failures), dict(current))
        ),
    )

    assert translated == {"hello": "Bonjour"}
    assert stats["failed_count"] == 0
    assert checkpoints
    assert checkpoints[-1][0] == {"hello": "Bonjour"}


def test_system_store_finds_legacy_json_beside_custom_auth_db(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import app.system_store as module

    legacy_home = tmp_path / "legacy-home"
    sqlite_home = tmp_path / "sqlite-home"
    legacy_home.mkdir()
    sqlite_home.mkdir()
    legacy = legacy_home / "derridai-system.json"
    legacy.write_text(json.dumps({
        "researcher_provider_profiles": [],
        "annotations": [],
        "languages": {
            "en-US": {"name": "English", "flag": "🇺🇸", "dictionary": {"app.name": "legacy"}},
            "fr-CA": {"name": "Français", "flag": "🇨🇦", "dictionary": {"app.name": "ancien"}},
        },
    }), encoding="utf-8")

    repository = SQLiteSystemRepository(sqlite_home / "derridai-system.sqlite3")
    monkeypatch.setattr(module, "system_repository", repository)
    monkeypatch.setattr(module, "settings", SimpleNamespace(auth_db_path=str(legacy_home / "auth.sqlite3")))

    store = module.SystemStore()
    assert store.get_language("en-US")["dictionary"]["app.name"] == "DerridAI"
    assert (legacy_home / "derridai-system.migrated-v0.36.0.json").exists()
