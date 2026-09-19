# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import settings


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | bytes | None, default: Any) -> Any:
    if value is None:
        return copy.deepcopy(default)
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return copy.deepcopy(default)
    return parsed


def _language_from_row(row: sqlite3.Row) -> dict[str, Any]:
    value: dict[str, Any] = {
        "name": str(row["name"]),
        "flag": str(row["flag"]),
        "dictionary": _json_loads(row["dictionary_json"], {}),
    }
    if row["translation_report_json"]:
        value["translation_report"] = _json_loads(row["translation_report_json"], {})
    keys = set(row.keys())
    if "content_policy_json" in keys and row["content_policy_json"]:
        policy = _json_loads(row["content_policy_json"], None)
        if isinstance(policy, dict):
            value["content_policy"] = policy
    return value


class SQLiteRepositoryBase:
    """Small SQLite repository foundation shared by durable application state.

    Authentication remains in its existing SQLite database while server-owned
    system metadata and operation state use a second durable SQLite database.
    This release assumes a fresh database and initializes only the current schema.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        raw = path or getattr(settings, "system_db_path", "/data/.home/derridai-system.sqlite3")
        self.path = Path(raw).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS researcher_provider_profiles (
                    id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_provider_profiles_position
                    ON researcher_provider_profiles(position, id);

                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_annotations_user_created
                    ON annotations(user_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS languages (
                    code TEXT PRIMARY KEY COLLATE NOCASE,
                    name TEXT NOT NULL,
                    flag TEXT NOT NULL,
                    dictionary_json TEXT NOT NULL,
                    translation_report_json TEXT,
                    content_policy_json TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_type_created
                    ON jobs(job_type, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                    ON jobs(status, updated_at DESC);
                """
            )
            self._ensure_column(conn, "languages", "content_policy_json", "TEXT")


    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
        names = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def describe(self) -> dict[str, Any]:
        with self._connect() as conn:
            page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
            page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
            journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
        return {
            "backend": "sqlite",
            "path": str(self.path),
            "journal_mode": journal_mode,
            "size_bytes": page_count * page_size,
        }


class SQLiteSystemRepository(SQLiteRepositoryBase):
    """Repository for provider profiles, annotations, and locale dictionaries."""

    def is_empty(self) -> bool:
        with self._connect() as conn:
            counts = [
                int(conn.execute("SELECT COUNT(*) FROM researcher_provider_profiles").fetchone()[0]),
                int(conn.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]),
                int(conn.execute("SELECT COUNT(*) FROM languages").fetchone()[0]),
            ]
        return not any(counts)

    def load(self) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            profiles = [
                _json_loads(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM researcher_provider_profiles ORDER BY position,id"
                )
            ]
            annotations = [
                _json_loads(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM annotations ORDER BY created_at DESC,id"
                )
            ]
            languages: dict[str, Any] = {}
            for row in conn.execute(
                "SELECT code,name,flag,dictionary_json,translation_report_json,content_policy_json FROM languages ORDER BY code"
            ):
                languages[str(row["code"])] = _language_from_row(row)

        return {
            "researcher_provider_profiles": profiles,
            "annotations": annotations,
            "languages": languages,
        }

    def replace(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("System repository payload must be an object.")
        profiles = data.get("researcher_provider_profiles") or []
        annotations = data.get("annotations") or []
        languages = data.get("languages") or {}
        if not isinstance(profiles, list) or not isinstance(annotations, list) or not isinstance(languages, dict):
            raise ValueError("System repository payload is invalid.")

        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM researcher_provider_profiles")
            conn.execute("DELETE FROM annotations")
            conn.execute("DELETE FROM languages")

            for position, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    continue
                profile_id = str(profile.get("id") or "").strip()
                if not profile_id:
                    continue
                conn.execute(
                    "INSERT INTO researcher_provider_profiles(id,position,payload_json,updated_at) VALUES(?,?,?,?)",
                    (profile_id, position, _json_dumps(profile), now),
                )

            for annotation in annotations:
                if not isinstance(annotation, dict):
                    continue
                annotation_id = str(annotation.get("id") or "").strip()
                if not annotation_id:
                    continue
                user_id = annotation.get("user_id")
                try:
                    user_id = int(user_id) if user_id is not None else None
                except (TypeError, ValueError):
                    user_id = None
                created_at = str(annotation.get("created_at") or now)
                conn.execute(
                    "INSERT INTO annotations(id,user_id,created_at,payload_json,updated_at) VALUES(?,?,?,?,?)",
                    (annotation_id, user_id, created_at, _json_dumps(annotation), now),
                )

            for code, language in languages.items():
                if not isinstance(language, dict):
                    continue
                clean_code = str(code).strip()
                if not clean_code:
                    continue
                report = language.get("translation_report")
                policy = language.get("content_policy")
                conn.execute(
                    "INSERT INTO languages(code,name,flag,dictionary_json,translation_report_json,content_policy_json,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (
                        clean_code,
                        str(language.get("name") or clean_code),
                        str(language.get("flag") or "🌐"),
                        _json_dumps(language.get("dictionary") or {}),
                        _json_dumps(report) if isinstance(report, dict) else None,
                        _json_dumps(policy) if isinstance(policy, dict) else None,
                        now,
                    ),
                )

            conn.commit()

    def list_provider_profiles(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM researcher_provider_profiles ORDER BY position,id"
            ).fetchall()
        return [
            item for item in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(item, dict)
        ]

    def replace_provider_profiles(self, profiles: list[dict[str, Any]]) -> None:
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM researcher_provider_profiles")
            for position, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    continue
                profile_id = str(profile.get("id") or "").strip()
                if not profile_id:
                    continue
                conn.execute(
                    "INSERT INTO researcher_provider_profiles(id,position,payload_json,updated_at) VALUES(?,?,?,?)",
                    (profile_id, position, _json_dumps(profile), now),
                )
            conn.commit()

    def list_annotations(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM annotations ORDER BY created_at DESC,id"
            ).fetchall()
        return [
            item for item in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(item, dict)
        ]

    def put_annotation(self, annotation: dict[str, Any]) -> None:
        annotation_id = str(annotation.get("id") or "").strip()
        if not annotation_id:
            raise ValueError("Annotation is missing an id.")
        user_id = annotation.get("user_id")
        try:
            user_id = int(user_id) if user_id is not None else None
        except (TypeError, ValueError):
            user_id = None
        created_at = str(annotation.get("created_at") or _iso_now())
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO annotations(id,user_id,created_at,payload_json,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    created_at=excluded.created_at,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (annotation_id, user_id, created_at, _json_dumps(annotation), now),
            )
            conn.commit()

    def delete_annotation(self, annotation_id: str, *, user_id: int | None = None, admin: bool = False) -> bool:
        with self._lock, self._connect() as conn:
            if admin or user_id is None:
                cursor = conn.execute("DELETE FROM annotations WHERE id=?", (str(annotation_id),))
            else:
                cursor = conn.execute(
                    "DELETE FROM annotations WHERE id=? AND user_id=?",
                    (str(annotation_id), int(user_id)),
                )
            conn.commit()
            return bool(cursor.rowcount)

    def list_languages(self) -> dict[str, dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT code,name,flag,dictionary_json,translation_report_json,content_policy_json FROM languages ORDER BY code"
            ).fetchall()
        return {str(row["code"]): _language_from_row(row) for row in rows}

    def get_language(self, code: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT code,name,flag,dictionary_json,translation_report_json,content_policy_json FROM languages WHERE code=?",
                (str(code),),
            ).fetchone()
        if row is None:
            return None
        return _language_from_row(row)

    def put_language(self, code: str, language: dict[str, Any]) -> None:
        now = _iso_now()
        report = language.get("translation_report")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO languages(code,name,flag,dictionary_json,translation_report_json,updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name,
                    flag=excluded.flag,
                    dictionary_json=excluded.dictionary_json,
                    translation_report_json=excluded.translation_report_json,
                    updated_at=excluded.updated_at
                """,
                (
                    str(code),
                    str(language.get("name") or code),
                    str(language.get("flag") or "🌐"),
                    _json_dumps(language.get("dictionary") or {}),
                    _json_dumps(report) if isinstance(report, dict) else None,
                    now,
                ),
            )
            conn.commit()

    def put_content_policy(self, code: str, policy: dict[str, Any] | None) -> bool:
        now = _iso_now()
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "UPDATE languages SET content_policy_json=?, updated_at=? WHERE code=?",
                (_json_dumps(policy) if isinstance(policy, dict) else None, now, str(code)),
            )
            conn.commit()
            return bool(cursor.rowcount)

    def delete_language(self, code: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM languages WHERE code=?", (str(code),))
            conn.commit()
            return bool(cursor.rowcount)



class SQLiteJobRepository(SQLiteRepositoryBase):
    """Durable operation ledger used by all background job managers."""

    ACTIVE_STATUSES = frozenset({"queued", "running", "cancelling"})

    def recover_interrupted(self) -> int:
        """Finalize jobs whose worker process disappeared during a restart.

        We intentionally do not auto-replay side-effecting work.  The durable
        record remains inspectable; resumable workflows (notably language
        translation) retain their checkpoints and can be explicitly resumed.
        """
        recovered = 0
        now = _iso_now()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id,payload_json FROM jobs WHERE status IN ('queued','running','cancelling')"
            ).fetchall()
            for row in rows:
                job = _json_loads(row["payload_json"], {})
                if not isinstance(job, dict):
                    continue
                previous = str(job.get("status") or "running")
                job["status"] = "failed"
                job["finished_at"] = job.get("finished_at") or now
                job["fatal_error"] = "Operation interrupted by a DerridAI restart."
                job["error_message"] = "Operation interrupted by a DerridAI restart."
                job["error_diagnostic"] = (
                    f"The process stopped while this operation was {previous}. "
                    "No side-effecting job is replayed automatically after restart."
                )
                events = job.setdefault("events", [])
                if isinstance(events, list):
                    events.append({
                        "timestamp": now,
                        "stage": "interrupted",
                        "detail": "Operation was interrupted by application restart; retained state can be inspected or explicitly resumed where supported.",
                    })
                self._upsert_conn(conn, job, now=now)
                recovered += 1
            conn.commit()
        return recovered

    @staticmethod
    def _job_type(job: dict[str, Any]) -> str:
        return str(job.get("type") or job.get("mode") or "operation")

    def _upsert_conn(self, conn: sqlite3.Connection, job: dict[str, Any], *, now: str | None = None) -> None:
        job_id = str(job.get("id") or "").strip()
        if not job_id:
            raise ValueError("Job payload is missing an id.")
        now = now or _iso_now()
        conn.execute(
            """
            INSERT INTO jobs(id,job_type,status,owner,created_at,updated_at,payload_json)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                job_type=excluded.job_type,
                status=excluded.status,
                owner=excluded.owner,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                payload_json=excluded.payload_json
            """,
            (
                job_id,
                self._job_type(job),
                str(job.get("status") or "unknown"),
                (str(job.get("owner")) if job.get("owner") is not None else None),
                str(job.get("created_at") or now),
                now,
                _json_dumps(job),
            ),
        )

    def upsert(self, job: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            self._upsert_conn(conn, copy.deepcopy(job))
            conn.commit()

    def upsert_many(self, jobs: Iterable[dict[str, Any]]) -> None:
        now = _iso_now()
        with self._lock, self._connect() as conn:
            for job in jobs:
                if isinstance(job, dict) and job.get("id"):
                    self._upsert_conn(conn, copy.deepcopy(job), now=now)
            conn.commit()

    def load(self, job_type: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM jobs WHERE job_type=? ORDER BY created_at DESC",
                (str(job_type),),
            ).fetchall()
        return [
            item for item in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(item, dict) and item.get("id")
        ]

    def delete(self, job_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id=?", (str(job_id),))
            conn.commit()
            return bool(cursor.rowcount)

    def clear_finished(self, job_type: str) -> int:
        placeholders = ",".join("?" for _ in self.ACTIVE_STATUSES)
        params: list[Any] = [str(job_type), *sorted(self.ACTIVE_STATUSES)]
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM jobs WHERE job_type=? AND status NOT IN ({placeholders})",
                params,
            )
            conn.commit()
            return int(cursor.rowcount or 0)

    def replace_finished(self, job_type: str, jobs: list[dict[str, Any]]) -> int:
        """Replace retained finished records for one manager during backup restore."""
        restored = 0
        now = _iso_now()
        placeholders = ",".join("?" for _ in self.ACTIVE_STATUSES)
        params: list[Any] = [str(job_type), *sorted(self.ACTIVE_STATUSES)]
        with self._lock, self._connect() as conn:
            conn.execute(
                f"DELETE FROM jobs WHERE job_type=? AND status NOT IN ({placeholders})",
                params,
            )
            for raw in jobs or []:
                if not isinstance(raw, dict):
                    continue
                job_id = str(raw.get("id") or "").strip()
                if not job_id or str(raw.get("status") or "") in self.ACTIVE_STATUSES:
                    continue
                job = copy.deepcopy(raw)
                job["type"] = job_type
                self._upsert_conn(conn, job, now=now)
                restored += 1
            conn.commit()
        return restored


system_repository = SQLiteSystemRepository()
job_repository = SQLiteJobRepository(system_repository.path)
# Recovery is deliberately process-wide and happens before manager instances
# hydrate their in-memory working sets.
job_repository.recover_interrupted()
