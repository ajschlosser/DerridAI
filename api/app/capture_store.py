# Copyright 2026 Aaron John Schlosser, PhD.
"""Durable Corpus Capture state in the system SQLite database.

Captures, their candidates and provider snapshots are acquisition bookkeeping,
not corpus content. Registered sources remain ordinary SourceDocument assets;
``source_capture_links`` is a many-to-many association so one source can be
reached by several captures without a one-to-one ``capture_id`` on the source.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import settings

ACTIVE_CAPTURE_STATUSES = frozenset({"discovering", "acquiring"})
# Metadata fields compared on refresh to report "provider source changed metadata".
TRACKED_FIELDS = ("title", "document_author", "document_languages", "translators", "editors", "contribution_role", "provider_revision_id", "wikidata_work_id")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def candidate_id_for(capture_id: str, provider_key: str) -> str:
    return "cand-" + hashlib.sha256(f"{capture_id}|{provider_key}".encode()).hexdigest()[:20]


class CaptureStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or settings.system_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init()
        self.recover_interrupted()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._lock, self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS corpus_captures (
                capture_id TEXT PRIMARY KEY, author_qid TEXT, author_name TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS corpus_capture_candidates (
                candidate_id TEXT PRIMARY KEY, capture_id TEXT NOT NULL, provider_key TEXT NOT NULL,
                provider TEXT NOT NULL, title TEXT NOT NULL, canonical_work_id TEXT,
                selection_status TEXT NOT NULL, acquisition_status TEXT NOT NULL,
                source_document_id TEXT, sort_index INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL, UNIQUE(capture_id, provider_key))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_capture_candidates_capture ON corpus_capture_candidates(capture_id, sort_index)")
            db.execute("""CREATE TABLE IF NOT EXISTS source_capture_links (
                source_document_id TEXT NOT NULL, capture_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
                provider TEXT NOT NULL, provider_item_id TEXT NOT NULL, discovery_method TEXT NOT NULL,
                discovered_at TEXT, acquired_at TEXT NOT NULL,
                PRIMARY KEY(source_document_id, capture_id, candidate_id))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_source_capture_links_capture ON source_capture_links(capture_id)")

    def recover_interrupted(self) -> int:
        """A capture whose worker died with the process is marked interrupted, never completed or replayed."""
        count = 0
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT capture_id,payload_json FROM corpus_captures WHERE status IN ('discovering','acquiring')").fetchall()
            for row in rows:
                capture = json.loads(row["payload_json"])
                capture["status"] = "interrupted"
                capture.setdefault("warnings", []).append("interrupted_by_restart")
                self._write_capture(db, capture)
                count += 1
            for row in db.execute("SELECT candidate_id,payload_json FROM corpus_capture_candidates WHERE acquisition_status IN ('fetching','acquired')").fetchall():
                payload = json.loads(row["payload_json"])
                payload.update({"acquisition_status": "failed", "error": {"code": "cancelled", "message": "Interrupted by a DerridAI restart; retry to acquire it."}})
                self._write_candidate(db, payload)
        return count

    # --- captures -------------------------------------------------------------

    @staticmethod
    def _write_capture(db: sqlite3.Connection, capture: dict[str, Any]) -> None:
        capture["updated_at"] = now_iso()
        author = capture.get("author") or {}
        db.execute(
            """INSERT INTO corpus_captures(capture_id,author_qid,author_name,status,created_at,updated_at,payload_json)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(capture_id) DO UPDATE SET author_qid=excluded.author_qid,
            author_name=excluded.author_name,status=excluded.status,updated_at=excluded.updated_at,payload_json=excluded.payload_json""",
            (capture["capture_id"], author.get("wikidata_qid"), str(author.get("canonical_name") or ""), capture["status"], capture["created_at"], capture["updated_at"], json.dumps(capture, ensure_ascii=False)),
        )

    def save_capture(self, capture: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connect() as db:
            self._write_capture(db, capture)
        return capture

    def get_capture(self, capture_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT payload_json FROM corpus_captures WHERE capture_id=?", (capture_id,)).fetchone()
        if row is None:
            raise KeyError(capture_id)
        return json.loads(row["payload_json"])

    def update_capture(self, capture_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            capture = self.get_capture(capture_id)
            capture.update(fields)
            return self.save_capture(capture)

    def list_captures(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload_json FROM corpus_captures ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def delete_capture(self, capture_id: str) -> None:
        """Forget a capture and its candidates. Registered sources and their link rows are kept."""
        with self._lock, self._connect() as db:
            db.execute("DELETE FROM corpus_capture_candidates WHERE capture_id=?", (capture_id,))
            db.execute("DELETE FROM corpus_captures WHERE capture_id=?", (capture_id,))

    # --- candidates -----------------------------------------------------------

    @staticmethod
    def _write_candidate(db: sqlite3.Connection, row: dict[str, Any]) -> None:
        db.execute(
            """INSERT INTO corpus_capture_candidates(candidate_id,capture_id,provider_key,provider,title,canonical_work_id,
            selection_status,acquisition_status,source_document_id,sort_index,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(candidate_id) DO UPDATE SET title=excluded.title,canonical_work_id=excluded.canonical_work_id,
            selection_status=excluded.selection_status,acquisition_status=excluded.acquisition_status,
            source_document_id=excluded.source_document_id,sort_index=excluded.sort_index,payload_json=excluded.payload_json""",
            (row["candidate_id"], row["capture_id"], row["provider_key"], row["provider"], row["title"], row.get("canonical_work_id"),
             row["selection_status"], row["acquisition_status"], row.get("source_document_id"), int(row.get("sort_index") or 0),
             json.dumps(row, ensure_ascii=False)),
        )

    def merge_candidates(self, capture_id: str, discovered: list[dict[str, Any]], *, discovered_at: str) -> dict[str, Any]:
        """Insert new candidates and refresh provider metadata of known ones; report the diff.

        Selection, acquisition state and registered sources of known candidates are preserved.
        Candidates the provider no longer lists are marked ``upstream_status=missing`` — never deleted.
        """
        diff: dict[str, Any] = {"new": [], "changed": [], "unchanged": 0, "missing": []}
        with self._lock, self._connect() as db:
            existing = {
                row["provider_key"]: json.loads(row["payload_json"])
                for row in db.execute("SELECT provider_key,payload_json FROM corpus_capture_candidates WHERE capture_id=?", (capture_id,))
            }
            seen: set[str] = set()
            for index, fresh in enumerate(discovered):
                key = fresh["provider_key"]
                seen.add(key)
                previous = existing.get(key)
                if previous is None:
                    row = {
                        **fresh,
                        "candidate_id": candidate_id_for(capture_id, key),
                        "capture_id": capture_id,
                        "discovered_at": discovered_at,
                        "acquisition_status": "pending",
                        "upstream_status": "present",
                        "sort_index": index,
                    }
                    diff["new"].append(row["candidate_id"])
                else:
                    changed = [field for field in TRACKED_FIELDS if previous.get(field) != fresh.get(field)]
                    keep = {k: previous[k] for k in ("candidate_id", "capture_id", "discovered_at", "selection_status", "acquisition_status", "source_document_id", "error", "acquired_at", "digital_duplicate_of", "attempts") if k in previous}
                    row = {**previous, **fresh, **keep, "upstream_status": "present", "sort_index": index}
                    if changed:
                        row["metadata_changed_fields"] = changed
                        row["metadata_changed_at"] = discovered_at
                        diff["changed"].append(row["candidate_id"])
                    else:
                        diff["unchanged"] += 1
                self._write_candidate(db, row)
            for key, previous in existing.items():
                if key not in seen:
                    previous["upstream_status"] = "missing"
                    self._write_candidate(db, previous)
                    diff["missing"].append(previous["candidate_id"])
        return diff

    def candidates(self, capture_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload_json FROM corpus_capture_candidates WHERE capture_id=? ORDER BY sort_index", (capture_id,)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT payload_json FROM corpus_capture_candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
        if row is None:
            raise KeyError(candidate_id)
        return json.loads(row["payload_json"])

    def update_candidate(self, candidate_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT payload_json FROM corpus_capture_candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
            if row is None:
                raise KeyError(candidate_id)
            payload = json.loads(row["payload_json"])
            payload.update(fields)
            self._write_candidate(db, payload)
            return payload

    def update_candidates(self, rows: Iterable[dict[str, Any]]) -> None:
        with self._lock, self._connect() as db:
            for row in rows:
                self._write_candidate(db, row)

    # --- source links -----------------------------------------------------------

    def link_source(self, source_document_id: str, candidate: dict[str, Any], acquired_at: str) -> None:
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO source_capture_links VALUES(?,?,?,?,?,?,?,?)",
                (source_document_id, candidate["capture_id"], candidate["candidate_id"], candidate["provider"], candidate["provider_item_id"], str(candidate.get("discovery_method") or ""), candidate.get("discovered_at"), acquired_at),
            )

    def links_for_sources(self, source_ids: Iterable[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        with self._connect() as db:
            rows = db.execute("SELECT l.*, c.author_name FROM source_capture_links l LEFT JOIN corpus_captures c ON c.capture_id=l.capture_id").fetchall()
        wanted = set(source_ids) if source_ids is not None else None
        out: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if wanted is None or row["source_document_id"] in wanted:
                out.setdefault(row["source_document_id"], []).append(dict(row))
        return out
