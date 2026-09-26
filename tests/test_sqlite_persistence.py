"""SQLite persistence layer for system state and jobs.

Why: since 0.36 provider profiles, annotations, languages, and background-job
history live in SQLite. The schema is created directly (no migrations), state must
survive restarts, and jobs interrupted by a restart must be marked failed, never
silently replayed.
How: uses SQLiteSystemRepository / SQLiteJobRepository on temp database files.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.persistence import SQLiteJobRepository, SQLiteSystemRepository


def test_system_repository_round_trip_is_transactional_sqlite(tmp_path: Path):
    """Saved system state loads back identically, with WAL mode and no migration tables.

    Also checks describe() reports the sqlite backend and file size, and that only the
    current tables exist (researcher_provider_profiles, annotations, languages, jobs).
    """
    db_path = tmp_path / "derridai-system.sqlite3"
    repo = SQLiteSystemRepository(db_path)
    payload = {
        "researcher_provider_profiles": [
            {"id": "local", "name": "Local", "type": "ollama", "api_key": "write-only-secret"}
        ],
        "settings": {
            "embedding_defaults": {
                "embedding_provider": "profile:local",
                "embedding_model": "nomic-embed-text",
            }
        },
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
    assert {
        "researcher_provider_profiles",
        "system_settings",
        "annotations",
        "languages",
        "jobs",
    } <= tables


def test_system_store_bootstraps_current_defaults_and_ignores_old_json(tmp_path: Path, monkeypatch):
    """A legacy derridai-system.json next to the database is ignored (and left untouched).

    The store seeds English and Français from the built-ins rather than reading
    the old file.
    """
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
    assert store.get_language("fr-CA")["name"] == "Français"
    assert old_json.exists()
    assert old_json.read_text(encoding="utf-8").find("OLD") >= 0






def test_unpersisted_ollama_default_uses_configured_ollama_profile(
    tmp_path: Path,
    monkeypatch,
):
    import app.system_store as module

    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(module, "system_repository", repository)
    monkeypatch.setattr(module.app_settings, "embedding_provider", "ollama")
    monkeypatch.setattr(module.app_settings, "ollama_embed_model", "legacy-env-model")
    store = module.SystemStore()
    store.set_researcher_profiles(
        [
            {
                "id": "local-embeddings",
                "name": "Local embeddings",
                "type": "ollama",
                "base_url": "http://configured-ollama:11434",
                "model": "nomic-embed-text",
            }
        ]
    )

    defaults = store.embedding_defaults()

    assert defaults["embedding_provider"] == "profile:local-embeddings"
    assert defaults["embedding_model"] == "nomic-embed-text"
    assert defaults["persisted"] is False


def test_embedding_defaults_are_server_owned_and_can_reference_provider_profiles(
    tmp_path: Path,
    monkeypatch,
):
    import app.system_store as module

    repository = SQLiteSystemRepository(tmp_path / "derridai-system.sqlite3")
    monkeypatch.setattr(module, "system_repository", repository)
    store = module.SystemStore()
    store.set_researcher_profiles(
        [
            {
                "id": "embedding-lab",
                "name": "Embedding Lab",
                "type": "openai",
                "base_url": "https://embeddings.example/v1",
                "model": "text-embedding-model",
                "api_key": "secret",
            }
        ]
    )

    saved = store.set_embedding_defaults("profile:embedding-lab", None)

    assert saved["embedding_provider"] == "profile:embedding-lab"
    assert saved["embedding_model"] == "text-embedding-model"
    assert saved["persisted"] is True

    restarted = module.SystemStore()
    loaded = restarted.embedding_defaults()
    assert loaded["embedding_provider"] == "profile:embedding-lab"
    assert loaded["embedding_model"] == "text-embedding-model"
    assert loaded["persisted"] is True


def test_job_repository_survives_restart_and_marks_active_job_interrupted(tmp_path: Path):
    """After a restart a running job becomes "failed/interrupted" but keeps resume data.

    The job's resume dictionary, failed keys and resumable flag are preserved, the error
    mentions the restart, and the last event stage is "interrupted".
    Why: side-effecting work must never be replayed automatically.
    """
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
    """System state and job history coexist in one database file and load independently."""
    path = tmp_path / "derridai-system.sqlite3"
    system = SQLiteSystemRepository(path)
    jobs = SQLiteJobRepository(path)

    system.replace({
        "researcher_provider_profiles": [],
        "settings": {},
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
    """Translation reports partial progress through a checkpoint callback.

    The final checkpoint holds the translated pair, letting a job persist partial work
    so an interrupted translation can be resumed.
    """
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
