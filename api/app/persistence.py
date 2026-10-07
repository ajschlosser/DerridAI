# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Durable server-owned application repositories.

The system SQLite database stores application/provenance/operation state; auth
uses its separate SQLite database, while canonical corpus files and derived
Chroma projections keep their own lifecycles. Keeping these boundaries explicit
prevents a repository helper from accidentally turning a cache or projection
into the authoritative scholarly record.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import settings


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


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

                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

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

                CREATE TABLE IF NOT EXISTS metadata_adjudication_cache (
                    cache_key TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    field TEXT NOT NULL,
                    cardinality TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_metadata_adjudication_cache_record
                    ON metadata_adjudication_cache(record_id, field, updated_at DESC);

                CREATE TABLE IF NOT EXISTS metadata_memory_bindings (
                    binding_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    record_revision INTEGER,
                    source_document_id TEXT,
                    field_id TEXT NOT NULL,
                    field_name TEXT,
                    schema_id TEXT,
                    schema_version TEXT,
                    decision_kind TEXT NOT NULL,
                    value_json TEXT,
                    evidence_json TEXT NOT NULL,
                    visibility TEXT NOT NULL DEFAULT 'corpus',
                    owner TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_metadata_memory_field
                    ON metadata_memory_bindings(field_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_metadata_memory_record
                    ON metadata_memory_bindings(record_id, field_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS semantic_memory_outbox (
                    item_id TEXT PRIMARY KEY,
                    projection TEXT NOT NULL,
                    scope_id TEXT,
                    record_id TEXT,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'dirty',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_semantic_memory_outbox_status
                    ON semantic_memory_outbox(status, created_at);

                CREATE TABLE IF NOT EXISTS generated_claims (
                    claim_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    response_record_id TEXT,
                    owner TEXT,
                    claim_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_generated_claims_owner
                    ON generated_claims(owner, created_at DESC);

                CREATE TABLE IF NOT EXISTS response_memory (
                    response_id TEXT PRIMARY KEY,
                    owner TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_response_memory_owner
                    ON response_memory(owner, created_at DESC);

                CREATE TABLE IF NOT EXISTS claim_support_bindings (
                    support_binding_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    owner TEXT,
                    record_id TEXT,
                    record_revision INTEGER,
                    relation TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_claim_support_claim
                    ON claim_support_bindings(claim_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_claim_support_record
                    ON claim_support_bindings(record_id, created_at);

                CREATE TABLE IF NOT EXISTS record_build_provenance (
                    record_id TEXT PRIMARY KEY,
                    build_id TEXT NOT NULL,
                    work TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_record_build_provenance_work
                    ON record_build_provenance(work, updated_at DESC);

                CREATE TABLE IF NOT EXISTS semantic_map_build_state (
                    build_id TEXT PRIMARY KEY,
                    generation INTEGER NOT NULL DEFAULT 1,
                    dirty INTEGER NOT NULL DEFAULT 1,
                    reason TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS semantic_map_projections (
                    scope_type TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    build_id TEXT NOT NULL,
                    audience TEXT NOT NULL DEFAULT '',
                    work TEXT,
                    generation INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(scope_type, scope_id, build_id, audience)
                );
                CREATE INDEX IF NOT EXISTS idx_semantic_map_projection_build
                    ON semantic_map_projections(build_id, generation);
                CREATE INDEX IF NOT EXISTS idx_semantic_map_projection_work
                    ON semantic_map_projections(work, scope_type, updated_at DESC);
                """
            )
            self._ensure_column(conn, "languages", "content_policy_json", "TEXT")
            self._ensure_column(conn, "semantic_memory_outbox", "scope_id", "TEXT")


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
                int(conn.execute("SELECT COUNT(*) FROM system_settings").fetchone()[0]),
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
            settings_rows = conn.execute(
                "SELECT key,payload_json FROM system_settings ORDER BY key"
            ).fetchall()
            system_settings = {
                str(row["key"]): _json_loads(row["payload_json"], None)
                for row in settings_rows
            }
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
            "settings": system_settings,
            "annotations": annotations,
            "languages": languages,
        }

    def replace(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("System repository payload must be an object.")
        profiles = data.get("researcher_provider_profiles") or []
        system_settings = data.get("settings") or {}
        annotations = data.get("annotations") or []
        languages = data.get("languages") or {}
        if (
            not isinstance(profiles, list)
            or not isinstance(system_settings, dict)
            or not isinstance(annotations, list)
            or not isinstance(languages, dict)
        ):
            raise ValueError("System repository payload is invalid.")

        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM researcher_provider_profiles")
            conn.execute("DELETE FROM system_settings")
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

            for key, value in system_settings.items():
                clean_key = str(key or "").strip()
                if not clean_key:
                    continue
                conn.execute(
                    "INSERT INTO system_settings(key,payload_json,updated_at) VALUES(?,?,?)",
                    (clean_key, _json_dumps(value), now),
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

    def get_setting(self, key: str) -> Any:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM system_settings WHERE key=?",
                (str(key),),
            ).fetchone()
        return _json_loads(row["payload_json"], None) if row else None

    def put_setting(self, key: str, value: Any) -> None:
        clean_key = str(key or "").strip()
        if not clean_key:
            raise ValueError("System setting key cannot be empty.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO system_settings(key,payload_json,updated_at)
                VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (clean_key, _json_dumps(value), now),
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

    def get_adjudication_cache(self, cache_key: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM metadata_adjudication_cache WHERE cache_key=?",
                (str(cache_key),),
            ).fetchone()
        value = _json_loads(row["payload_json"], None) if row else None
        return value if isinstance(value, dict) else None

    def put_adjudication_cache(
        self,
        cache_key: str,
        record_id: str,
        field: str,
        cardinality: str,
        text_hash: str,
        payload: dict[str, Any],
    ) -> None:
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata_adjudication_cache
                    (cache_key,record_id,field,cardinality,text_hash,payload_json,updated_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    str(cache_key),
                    str(record_id),
                    str(field),
                    str(cardinality),
                    str(text_hash),
                    _json_dumps(payload),
                    now,
                ),
            )
            conn.commit()

    def clear_adjudication_cache(
        self,
        *,
        record_id: str | None = None,
        field: str | None = None,
    ) -> int:
        clauses: list[str] = []
        params: list[Any] = []
        if record_id:
            clauses.append("record_id=?")
            params.append(str(record_id))
        if field:
            clauses.append("field=?")
            params.append(str(field))
        statement = "DELETE FROM metadata_adjudication_cache"
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        with self._lock, self._connect() as conn:
            cursor = conn.execute(statement, params)
            conn.commit()
            return int(cursor.rowcount)

    def prune_adjudication_cache(self, max_entries: int = 5000) -> int:
        limit = max(100, int(max_entries))
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM metadata_adjudication_cache
                WHERE cache_key NOT IN (
                    SELECT cache_key FROM metadata_adjudication_cache
                    ORDER BY updated_at DESC LIMIT ?
                )
                """,
                (limit,),
            )
            conn.commit()
            return int(cursor.rowcount)

    def put_memory_binding(self, payload: dict[str, Any], *, enqueue_projection: bool = False) -> None:
        binding_id = str(payload.get("binding_id") or "").strip()
        record_id = str(payload.get("record_id") or "").strip()
        field_id = str(payload.get("field_id") or "").strip()
        if not binding_id or not record_id or not field_id:
            raise ValueError("Metadata memory binding needs binding_id, record_id, and field_id.")
        now = _iso_now()
        value = payload.get("value")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata_memory_bindings
                    (binding_id,record_id,record_revision,source_document_id,field_id,field_name,
                     schema_id,schema_version,decision_kind,value_json,evidence_json,visibility,owner,
                     payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(binding_id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    value_json=excluded.value_json,
                    evidence_json=excluded.evidence_json,
                    updated_at=excluded.updated_at
                """,
                (
                    binding_id, record_id, payload.get("record_revision"),
                    payload.get("source_document_id"), field_id, payload.get("field_name"),
                    payload.get("schema_id"), payload.get("schema_version"),
                    str(payload.get("decision_kind") or "value"),
                    _json_dumps(value) if value is not None else None,
                    _json_dumps(payload.get("evidence") or []),
                    str(payload.get("visibility") or "corpus"),
                    payload.get("owner"), _json_dumps(payload),
                    str(payload.get("created_at") or now), now,
                ),
            )
            if enqueue_projection:
                import uuid

                conn.execute(
                    "INSERT INTO semantic_memory_outbox "
                    "(item_id,projection,scope_id,record_id,reason,status,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), "metadata_exemplars", payload.get("scope_id"),
                     record_id, "reviewed_metadata_decision", "dirty", now, now),
                )
            conn.commit()

    def list_memory_bindings(
        self, *, field_id: str | None = None, record_id: str | None = None,
        owner: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]:
        field_filter = str(field_id) if field_id else None
        record_filter = str(record_id) if record_id else None
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM metadata_memory_bindings
                WHERE (? IS NULL OR field_id=?)
                  AND (? IS NULL OR record_id=?)
                  AND (? IS NULL OR visibility='corpus' OR owner=?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    field_filter, field_filter, record_filter, record_filter,
                    owner_filter, owner_filter, max(1, min(1000, int(limit))),
                ),
            ).fetchall()
        return [value for value in (_json_loads(row["payload_json"], {}) for row in rows) if isinstance(value, dict)]

    def mark_semantic_memory_dirty(
        self,
        projection: str,
        *,
        scope_id: str | None = None,
        record_id: str | None = None,
        reason: str = "changed",
    ) -> str:
        import uuid
        item_id = str(uuid.uuid4())
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_memory_outbox
                    (item_id,projection,scope_id,record_id,reason,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (item_id, str(projection), scope_id, record_id, str(reason), "dirty", now, now),
            )
            conn.commit()
        return item_id

    def list_semantic_memory_dirty(
        self,
        projection: str | None = None,
        *,
        scope_id: str | None = None,
        unscoped: bool = False,
        after: tuple[str, str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        projection_filter = str(projection) if projection else None
        scope_filter = str(scope_id) if scope_id else None
        after_time, after_id = after if after is not None else ("", "")
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT item_id,projection,scope_id,record_id,reason,status,created_at,updated_at
                FROM semantic_memory_outbox
                WHERE status='dirty'
                  AND (? IS NULL OR projection=?)
                  AND (? IS NULL OR scope_id=?)
                  AND (?=0 OR scope_id IS NULL OR scope_id='')
                  AND (created_at>? OR (created_at=? AND item_id>?))
                ORDER BY created_at,item_id
                LIMIT ?
                """,
                (
                    projection_filter,
                    projection_filter,
                    scope_filter,
                    scope_filter,
                    int(unscoped),
                    after_time, after_time, after_id,
                    max(1, min(1000, int(limit))),
                ),
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve_semantic_memory_scope(self, item_ids: list[str], scope_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.executemany(
                "UPDATE semantic_memory_outbox SET scope_id=? WHERE item_id=? "
                "AND status='dirty' AND (scope_id IS NULL OR scope_id='')",
                [(scope_id, item_id) for item_id in item_ids],
            )

    def semantic_memory_dirty_summary(self, projection: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT COALESCE(scope_id,'') AS scope_id,COUNT(*) AS dirty "
                "FROM semantic_memory_outbox WHERE status='dirty' AND projection=? GROUP BY scope_id",
                (projection,),
            ).fetchall()
        return [dict(row) for row in rows]

    def complete_semantic_memory_dirty(self, item_ids: Iterable[str]) -> int:
        ids = [str(item_id) for item_id in item_ids if str(item_id).strip()]
        if not ids:
            return 0
        now = _iso_now()
        with self._lock, self._connect() as conn:
            cursor = conn.executemany(
                "UPDATE semantic_memory_outbox "
                "SET status='projected', updated_at=? "
                "WHERE item_id=? AND status='dirty'",
                [(now, item_id) for item_id in ids],
            )
            conn.commit()
            return int(cursor.rowcount or 0)

    def put_generated_claim(self, payload: dict[str, Any]) -> None:
        claim_id = str(payload.get("claim_id") or "").strip()
        claim_text = str(payload.get("claim_text") or "").strip()
        if not claim_id or not claim_text:
            raise ValueError("A generated claim needs claim_id and claim_text.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO generated_claims
                    (claim_id,run_id,response_record_id,owner,claim_text,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (
                    claim_id, payload.get("run_id"), payload.get("response_record_id"),
                    payload.get("owner"), claim_text, _json_dumps(payload),
                    str(payload.get("created_at") or now), now,
                ),
            )
            conn.commit()

    def put_response_memory(self, payload: dict[str, Any]) -> None:
        response_id = str(payload.get("response_id") or "").strip()
        question = str(payload.get("question") or "").strip()
        answer = str(payload.get("answer") or "").strip()
        if not response_id or not question or not answer:
            raise ValueError("A response memory item needs response_id, question, and answer.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO response_memory
                    (response_id,owner,question,answer,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(response_id) DO UPDATE SET
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (
                    response_id, payload.get("owner"), question, answer,
                    _json_dumps(payload), str(payload.get("created_at") or now), now,
                ),
            )
            conn.commit()

    def get_response_memory(self, response_id: str, *, owner: str | None = None) -> dict[str, Any] | None:
        """Resolve one durable Research response while enforcing owner visibility."""
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM response_memory
                WHERE response_id=?
                  AND (? IS NULL OR owner IS NULL OR owner=?)
                LIMIT 1
                """,
                (str(response_id), owner_filter, owner_filter),
            ).fetchone()
        value = _json_loads(row["payload_json"], {}) if row is not None else {}
        return value if isinstance(value, dict) and value else None

    def record_response_memory_grade(self, response_id: str, grade: dict[str, Any]) -> bool:
        """Attach the latest grade summary to a durable response; False when it is unknown."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM response_memory WHERE response_id=?", (str(response_id),)
            ).fetchone()
            if row is None:
                return False
            payload = _json_loads(row["payload_json"], {})
            if not isinstance(payload, dict):
                payload = {}
            payload["latest_grade"] = dict(grade)
            conn.execute(
                "UPDATE response_memory SET payload_json=?, updated_at=? WHERE response_id=?",
                (_json_dumps(payload), _iso_now(), str(response_id)),
            )
            conn.commit()
        return True

    def list_response_memory(self, *, owner: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM response_memory
                WHERE (? IS NULL OR owner IS NULL OR owner=?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_filter, owner_filter, max(1, min(1000, int(limit)))),
            ).fetchall()
        return [value for value in (_json_loads(row["payload_json"], {}) for row in rows) if isinstance(value, dict)]

    def list_generated_claims(
        self,
        *,
        owner: str | None = None,
        run_id: str | None = None,
        validation_status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        owner_filter = str(owner) if owner is not None else None
        run_filter = str(run_id) if run_id is not None else None
        status_filter = str(validation_status) if validation_status is not None else None
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM generated_claims
                WHERE (? IS NULL OR owner IS NULL OR owner=?)
                  AND (? IS NULL OR run_id=?)
                  AND (? IS NULL OR COALESCE(json_extract(payload_json, '$.validation_status'), 'unvalidated')=?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    owner_filter, owner_filter, run_filter, run_filter,
                    status_filter, status_filter, max(1, min(1000, int(limit))),
                ),
            ).fetchall()
        return [value for value in (_json_loads(row["payload_json"], {}) for row in rows) if isinstance(value, dict)]

    def put_claim_support_binding(self, payload: dict[str, Any]) -> None:
        support_id = str(payload.get("support_binding_id") or "").strip()
        claim_id = str(payload.get("claim_id") or "").strip()
        relation = str(payload.get("relation") or "").strip()
        if not support_id or not claim_id or not relation:
            raise ValueError("A support binding needs support_binding_id, claim_id, and relation.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO claim_support_bindings
                    (support_binding_id,claim_id,owner,record_id,record_revision,relation,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(support_binding_id) DO UPDATE SET
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (
                    support_id, claim_id, payload.get("owner"), payload.get("record_id"),
                    payload.get("record_revision"), relation, _json_dumps(payload),
                    str(payload.get("created_at") or now), now,
                ),
            )
            conn.commit()

    def list_claim_support_bindings(self, claim_id: str, *, owner: str | None = None) -> list[dict[str, Any]]:
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM claim_support_bindings
                WHERE claim_id=?
                  AND (? IS NULL OR owner IS NULL OR owner=?)
                ORDER BY created_at
                """,
                (str(claim_id), owner_filter, owner_filter),
            ).fetchall()
        return [value for value in (_json_loads(row["payload_json"], {}) for row in rows) if isinstance(value, dict)]

    def list_claim_support_bindings_for_record(
        self,
        record_id: str,
        *,
        owner: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return support relations that point at one logical Record."""
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM claim_support_bindings
                WHERE record_id=?
                  AND (? IS NULL OR owner IS NULL OR owner=?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (
                    str(record_id),
                    owner_filter,
                    owner_filter,
                    max(1, min(1000, int(limit))),
                ),
            ).fetchall()
        return [
            value
            for value in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(value, dict)
        ]

    def get_generated_claim(
        self,
        claim_id: str,
        *,
        owner: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve one durable generated claim while enforcing owner visibility."""
        owner_filter = str(owner) if owner is not None else None
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM generated_claims
                WHERE claim_id=?
                  AND (? IS NULL OR owner IS NULL OR owner=?)
                LIMIT 1
                """,
                (str(claim_id), owner_filter, owner_filter),
            ).fetchone()
        value = _json_loads(row["payload_json"], {}) if row is not None else {}
        return value if isinstance(value, dict) and value else None

    def get_generated_claims(
        self,
        claim_ids: list[str],
        *,
        owner: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Batch form of ``get_generated_claim`` with the same owner visibility rule."""
        ids = sorted({str(value) for value in claim_ids if str(value or "").strip()})
        if not ids:
            return {}
        owner_filter = str(owner) if owner is not None else None
        # Only "?" placeholders are interpolated; every value is bound.
        placeholders = ",".join("?" for _ in ids)
        sql = f"SELECT claim_id, payload_json FROM generated_claims WHERE claim_id IN ({placeholders}) AND (? IS NULL OR owner IS NULL OR owner=?)"  # noqa: S608
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                sql,
                (*ids, owner_filter, owner_filter),
            ).fetchall()
        found: dict[str, dict[str, Any]] = {}
        for row in rows:
            value = _json_loads(row["payload_json"], {})
            if isinstance(value, dict) and value:
                found[str(row["claim_id"])] = value
        return found

    def list_claim_support_bindings_for_claims(
        self,
        claim_ids: list[str],
        *,
        owner: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Batch form of ``list_claim_support_bindings`` keyed by claim id."""
        ids = sorted({str(value) for value in claim_ids if str(value or "").strip()})
        grouped: dict[str, list[dict[str, Any]]] = {claim_id: [] for claim_id in ids}
        if not ids:
            return grouped
        owner_filter = str(owner) if owner is not None else None
        # Only "?" placeholders are interpolated; every value is bound.
        placeholders = ",".join("?" for _ in ids)
        sql = f"SELECT claim_id, payload_json FROM claim_support_bindings WHERE claim_id IN ({placeholders}) AND (? IS NULL OR owner IS NULL OR owner=?) ORDER BY created_at"  # noqa: S608
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                sql,
                (*ids, owner_filter, owner_filter),
            ).fetchall()
        for row in rows:
            value = _json_loads(row["payload_json"], {})
            if isinstance(value, dict):
                grouped.setdefault(str(row["claim_id"]), []).append(value)
        return grouped

    def set_record_build_provenance(
        self, record_id: str, build_id: str, *, work: str | None = None
    ) -> None:
        """Remember which build a published Record's Document Intelligence lives in.

        This is derived provenance, not the canonical record: the published Record
        itself never carries `build_id` (see corpus_publication.serialize_public_record).
        Republishing the same record_id from a newer build overwrites the mapping.
        """
        record_id = str(record_id or "").strip()
        build_id = str(build_id or "").strip()
        if not record_id or not build_id:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO record_build_provenance(record_id, build_id, work, updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(record_id) DO UPDATE SET
                    build_id=excluded.build_id, work=excluded.work, updated_at=excluded.updated_at
                """,
                (record_id, build_id, str(work or "").strip() or None, _iso_now()),
            )

    def get_record_build_id(self, record_id: str) -> str | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT build_id FROM record_build_provenance WHERE record_id=?",
                (str(record_id or "").strip(),),
            ).fetchone()
        return str(row["build_id"]) if row else None

    def list_build_ids_for_work(self, work: str) -> list[str]:
        work = str(work or "").strip()
        if not work:
            return []
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT build_id FROM record_build_provenance WHERE work=? ORDER BY build_id",
                (work,),
            ).fetchall()
        return [str(row["build_id"]) for row in rows]

    def list_records_for_work(self, work: str, limit: int = 200) -> list[dict[str, str]]:
        work = str(work or "").strip()
        if not work:
            return []
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT record_id, build_id FROM record_build_provenance WHERE work=? "
                "ORDER BY updated_at DESC, record_id LIMIT ?",
                (work, max(1, min(int(limit), 500))),
            ).fetchall()
        return [{"record_id": str(row["record_id"]), "build_id": str(row["build_id"])} for row in rows]

    def semantic_map_state(self, build_id: str) -> dict[str, Any]:
        """Return the O(1) invalidation state for a build's derived semantic maps.

        Older builds have no row until first use. Treat them as generation 1 and
        dirty so the first semantic-map request materializes System Data once.
        """
        build_id = str(build_id or "").strip()
        if not build_id:
            raise ValueError("A build ID is required.")
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_map_build_state(build_id,generation,dirty,reason,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(build_id) DO NOTHING
                """,
                (build_id, 1, 1, "initial_projection", now),
            )
            row = conn.execute(
                "SELECT build_id,generation,dirty,reason,updated_at "
                "FROM semantic_map_build_state WHERE build_id=?",
                (build_id,),
            ).fetchone()
            conn.commit()
        return {
            "build_id": str(row["build_id"]),
            "generation": int(row["generation"]),
            "dirty": bool(row["dirty"]),
            "reason": str(row["reason"] or ""),
            "updated_at": str(row["updated_at"]),
        }

    def mark_semantic_map_dirty(self, build_id: str, *, reason: str = "changed") -> int:
        """Advance a build's semantic generation without walking its Records."""
        build_id = str(build_id or "").strip()
        if not build_id:
            return 0
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_map_build_state(build_id,generation,dirty,reason,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(build_id) DO UPDATE SET
                    generation=semantic_map_build_state.generation + 1,
                    dirty=1,
                    reason=excluded.reason,
                    updated_at=excluded.updated_at
                """,
                (build_id, 1, 1, str(reason or "changed"), now),
            )
            row = conn.execute(
                "SELECT generation FROM semantic_map_build_state WHERE build_id=?",
                (build_id,),
            ).fetchone()
            conn.commit()
        return int(row["generation"]) if row else 0

    def mark_semantic_map_clean(self, build_id: str, generation: int) -> bool:
        """Mark exactly the generation that was materialized as current.

        If another writer invalidated the build while projection was running, the
        generation no longer matches and the dirty bit remains set.
        """
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE semantic_map_build_state
                SET dirty=0, reason='', updated_at=?
                WHERE build_id=? AND generation=?
                """,
                (_iso_now(), str(build_id), int(generation)),
            )
            conn.commit()
        return bool(cursor.rowcount)

    def put_semantic_map_projection(
        self,
        scope_type: str,
        scope_id: str,
        build_id: str,
        generation: int,
        payload: dict[str, Any],
        *,
        work: str | None = None,
        audience: str = "",
    ) -> None:
        """Persist one rebuildable semantic-map projection in System Data.

        Audience isolates reviewer-presented projections so blind second-opinion
        values cannot leak through a projection built for another reviewer.
        """
        now = _iso_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_map_projections
                    (scope_type,scope_id,build_id,audience,work,generation,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scope_type,scope_id,build_id,audience) DO UPDATE SET
                    work=excluded.work,
                    generation=excluded.generation,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    str(scope_type),
                    str(scope_id),
                    str(build_id),
                    str(audience or ""),
                    str(work or "").strip() or None,
                    int(generation),
                    _json_dumps(payload),
                    now,
                    now,
                ),
            )
            conn.commit()

    def put_semantic_map_projections(self, rows: Iterable[dict[str, Any]]) -> int:
        """Bulk-upsert one generation in a single SQLite transaction."""
        now = _iso_now()
        values: list[tuple[Any, ...]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            scope_type = str(row.get("scope_type") or "").strip()
            scope_id = str(row.get("scope_id") or "").strip()
            build_id = str(row.get("build_id") or "").strip()
            payload = row.get("payload")
            if not scope_type or not scope_id or not build_id or not isinstance(payload, dict):
                continue
            values.append(
                (
                    scope_type,
                    scope_id,
                    build_id,
                    str(row.get("audience") or ""),
                    str(row.get("work") or "").strip() or None,
                    int(row.get("generation") or 0),
                    _json_dumps(payload),
                    now,
                    now,
                )
            )
        if not values:
            return 0
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO semantic_map_projections
                    (scope_type,scope_id,build_id,audience,work,generation,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scope_type,scope_id,build_id,audience) DO UPDATE SET
                    work=excluded.work,
                    generation=excluded.generation,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                values,
            )
            conn.commit()
        return len(values)

    def get_semantic_map_projection(
        self,
        scope_type: str,
        scope_id: str,
        build_id: str,
        *,
        audience: str = "",
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT scope_type,scope_id,build_id,audience,work,generation,payload_json,created_at,updated_at
                FROM semantic_map_projections
                WHERE scope_type=? AND scope_id=? AND build_id=? AND audience=?
                """,
                (str(scope_type), str(scope_id), str(build_id), str(audience or "")),
            ).fetchone()
        if row is None:
            return None
        payload = _json_loads(row["payload_json"], {})
        if not isinstance(payload, dict):
            return None
        return {
            "scope_type": str(row["scope_type"]),
            "scope_id": str(row["scope_id"]),
            "build_id": str(row["build_id"]),
            "audience": str(row["audience"] or ""),
            "work": str(row["work"] or ""),
            "generation": int(row["generation"]),
            "payload": payload,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def list_semantic_map_projections_for_work(
        self,
        work: str,
        *,
        scope_type: str = "work",
        audience: str = "",
    ) -> list[dict[str, Any]]:
        work = str(work or "").strip()
        if not work:
            return []
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT scope_type,scope_id,build_id,audience,work,generation,payload_json,created_at,updated_at
                FROM semantic_map_projections
                WHERE work=? AND scope_type=? AND audience=?
                ORDER BY updated_at DESC, build_id
                """,
                (work, str(scope_type), str(audience or "")),
            ).fetchall()
        values: list[dict[str, Any]] = []
        for row in rows:
            payload = _json_loads(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            values.append({
                "scope_type": str(row["scope_type"]),
                "scope_id": str(row["scope_id"]),
                "build_id": str(row["build_id"]),
                "audience": str(row["audience"] or ""),
                "work": str(row["work"] or ""),
                "generation": int(row["generation"]),
                "payload": payload,
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            })
        return values

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
    # Vector upserts are deliberately restart-resumable because their full
    # request body is spooled separately before execution. Other side-effecting
    # operations remain fail-closed after a process restart.
    RESTART_RESUMABLE_TYPES = frozenset({"upsert"})

    def recover_interrupted(self) -> int:
        """Finalize non-resumable jobs whose worker process disappeared."""
        recovered = 0
        now = _iso_now()
        placeholders = ",".join("?" for _ in self.RESTART_RESUMABLE_TYPES)
        exclusion = (
            f" AND job_type NOT IN ({placeholders})"
            if self.RESTART_RESUMABLE_TYPES
            else ""
        )
        params = tuple(sorted(self.RESTART_RESUMABLE_TYPES))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id,payload_json FROM jobs "
                "WHERE status IN ('queued','running','cancelling')" + exclusion,
                params,
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
                        "detail": (
                            "Operation was interrupted by application restart; "
                            "retained state can be inspected or explicitly resumed "
                            "where supported."
                        ),
                    })
                self._upsert_conn(conn, job, now=now)
                recovered += 1
            conn.commit()
        return recovered

    @staticmethod
    def _job_type(job: dict[str, Any]) -> str:
        return str(job.get("type") or job.get("mode") or "operation")

    def _upsert_conn(
        self,
        conn: sqlite3.Connection,
        job: dict[str, Any],
        *,
        now: str | None = None,
    ) -> None:
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
        """Persist one caller-owned snapshot without making another full copy."""
        with self._lock, self._connect() as conn:
            self._upsert_conn(conn, job)
            conn.commit()

    def upsert_many(self, jobs: Iterable[dict[str, Any]]) -> None:
        """Persist caller-owned snapshots without duplicating their object graphs."""
        now = _iso_now()
        with self._lock, self._connect() as conn:
            for job in jobs:
                if isinstance(job, dict) and job.get("id"):
                    self._upsert_conn(conn, job, now=now)
            conn.commit()

    def load(self, job_type: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM jobs WHERE job_type=? ORDER BY created_at DESC",
                (str(job_type),),
            ).fetchall()
        return [
            item
            for item in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(item, dict) and item.get("id")
        ]

    def load_active(self, job_type: str) -> list[dict[str, Any]]:
        """Load only work that must remain resident for live worker coordination."""
        placeholders = ",".join("?" for _ in self.ACTIVE_STATUSES)
        params: list[Any] = [str(job_type), *sorted(self.ACTIVE_STATUSES)]
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM jobs "
                f"WHERE job_type=? AND status IN ({placeholders}) "
                f"ORDER BY created_at DESC",  # noqa: S608
                params,
            ).fetchall()
        return [
            item
            for item in (_json_loads(row["payload_json"], {}) for row in rows)
            if isinstance(item, dict) and item.get("id")
        ]

    def get(self, job_id: str, *, job_type: str | None = None) -> dict[str, Any] | None:
        query = "SELECT payload_json FROM jobs WHERE id=?"
        params: list[Any] = [str(job_id)]
        if job_type is not None:
            query += " AND job_type=?"
            params.append(str(job_type))
        with self._lock, self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        value = _json_loads(row["payload_json"], {}) if row is not None else {}
        return value if isinstance(value, dict) and value.get("id") else None

    def footprints(self, job_type: str) -> list[tuple[str, str, int, bool]]:
        """Return retention metadata without deserializing historical payloads."""
        placeholders = ",".join("?" for _ in self.ACTIVE_STATUSES)
        params: list[Any] = [*sorted(self.ACTIVE_STATUSES), str(job_type)]
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, created_at, LENGTH(CAST(payload_json AS BLOB)) AS stored_bytes,
                       CASE WHEN status IN ({placeholders}) THEN 1 ELSE 0 END AS active
                FROM jobs
                WHERE job_type=?
                """,  # noqa: S608
                params,
            ).fetchall()
        return [
            (
                str(row["id"]),
                str(row["created_at"] or ""),
                int(row["stored_bytes"] or 0),
                bool(row["active"]),
            )
            for row in rows
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
                f"DELETE FROM jobs WHERE job_type=? "
                f"AND status NOT IN ({placeholders})",  # noqa: S608
                params,
            )
            conn.commit()
            return int(cursor.rowcount or 0)

    def clear_type(self, job_type: str) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE job_type=?", (str(job_type),))
            conn.commit()
            return int(cursor.rowcount or 0)

    def clear_all(self) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM jobs")
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
                f"DELETE FROM jobs WHERE job_type=? "
                f"AND status NOT IN ({placeholders})",  # noqa: S608
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
