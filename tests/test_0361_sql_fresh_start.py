from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.persistence import SQLiteJobRepository, SQLiteSystemRepository




def test_system_repository_round_trip_is_transactional_sqlite(tmp_path: Path):
    db_path = tmp_path / "derridai-system.sqlite3"
    repo = SQLiteSystemRepository(db_path)
    payload = {
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
    assert repo.load() == payload

    info = repo.describe()
    assert info["backend"] == "sqlite"
    assert info["journal_mode"].lower() == "wal"
    assert info["size_bytes"] > 0
    assert "schema_version" not in info

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "schema_migrations" not in tables
    assert "system_meta" not in tables
    assert {"researcher_provider_profiles", "annotations", "languages", "jobs"} <= tables


def test_system_store_bootstraps_current_defaults_and_ignores_old_json(tmp_path: Path, monkeypatch):
    import app.system_store as module

    db_path = tmp_path / "derridai-system.sqlite3"
    old_json = tmp_path / "derridai-system.json"
    old_json.write_text(json.dumps({
        "languages": {
            "en-US": {"name": "Old English", "flag": "X", "dictionary": {"app.name": "OLD"}},
        }
    }), encoding="utf-8")

    repository = SQLiteSystemRepository(db_path)
    monkeypatch.setattr(module, "system_repository", repository)
    store = module.SystemStore()

    assert store.get_language("en-US")["name"] == "English"
    assert store.get_language("en-US")["dictionary"]["app.name"] == "DerridAI"
    assert store.get_language("fr-CA")["name"] == "Français (Québec)"
    assert old_json.exists()
    assert old_json.read_text(encoding="utf-8").find("OLD") >= 0






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
    recovered = restarted.load("llm_tool")[0]

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
