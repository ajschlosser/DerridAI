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

"""Authoritative Research thread/turn persistence and domain service.

A thread is conversational continuity; every assistant answer stays the output
of its own independently auditable ResearchRun. Thread structure lives in the
system SQLite database, never in Chroma or the response cache, which only carry
completed answer artifacts. Deterministic code owns IDs, ownership, ordering and
idempotency here; thread text is advisory context and is never evidence.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .persistence import _iso_now
from .pipelines.storage import PipelineDatabase, dump_json, load_json

ACTIVE_STATUSES = frozenset({"queued", "running"})
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
TURN_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES
TITLE_MAX_CHARS = 80


class ThreadNotFound(LookupError):
    """Missing thread/turn, or one the caller does not own (indistinguishable)."""


class ThreadBusy(RuntimeError):
    """A turn is already queued or running in this linear thread."""


def derive_title(question: str) -> str:
    """Deterministic title from the first question; no model call."""
    text = " ".join(str(question or "").split())
    if len(text) <= TITLE_MAX_CHARS:
        return text or "Untitled"
    cut = text[:TITLE_MAX_CHARS].rsplit(" ", 1)[0] or text[:TITLE_MAX_CHARS]
    return cut.rstrip(" ,;:.-") + "…"


def _thread_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "thread_id": row["thread_id"],
        "owner": row["owner"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "archived_at": row["archived_at"],
        "originating_response_record_id": row["originating_response_record_id"],
    }


def _turn_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "turn_id": row["turn_id"],
        "thread_id": row["thread_id"],
        "ordinal": row["ordinal"],
        "user_question": row["user_question"],
        "user_instructions": row["user_instructions"],
        "status": row["status"],
        "job_id": row["job_id"],
        "research_run_id": row["research_run_id"],
        "response_record_id": row["response_record_id"],
        "parent_turn_id": row["parent_turn_id"],
        "contextualized_query": row["contextualized_query"],
        "context_selection": load_json(row["context_selection_json"], None),
        "error": row["error"],
        "attempt": row["attempt"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class ResearchThreadStore(PipelineDatabase):
    """Thread/turn tables plus owner-scoped operations on the system database."""

    def _init_schema(self) -> None:
        with self.lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_threads (
                    thread_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT,
                    deleted_at TEXT,
                    originating_response_record_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_research_threads_owner_updated
                    ON research_threads(owner, updated_at DESC);
                -- Idempotent legacy materialization; tombstones keep the key so
                -- a deleted singleton thread is never resurrected.
                CREATE UNIQUE INDEX IF NOT EXISTS idx_research_threads_legacy
                    ON research_threads(owner, originating_response_record_id)
                    WHERE originating_response_record_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS research_turns (
                    turn_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    user_question TEXT NOT NULL,
                    user_instructions TEXT,
                    idempotency_key TEXT,
                    status TEXT NOT NULL,
                    job_id TEXT,
                    research_run_id TEXT,
                    response_record_id TEXT,
                    parent_turn_id TEXT,
                    contextualized_query TEXT,
                    context_selection_json TEXT,
                    error TEXT,
                    attempt INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (thread_id, ordinal),
                    FOREIGN KEY (thread_id) REFERENCES research_threads(thread_id)
                        ON DELETE CASCADE
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_research_turns_idempotency
                    ON research_turns(thread_id, idempotency_key)
                    WHERE idempotency_key IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_research_turns_job
                    ON research_turns(job_id) WHERE job_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_research_turns_run
                    ON research_turns(research_run_id) WHERE research_run_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_research_turns_response
                    ON research_turns(response_record_id) WHERE response_record_id IS NOT NULL;
                """
            )

    # -- internals ---------------------------------------------------------

    def _owned_thread(self, conn: sqlite3.Connection, thread_id: str, owner: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM research_threads WHERE thread_id=? AND owner=? AND deleted_at IS NULL",
            (thread_id, owner),
        ).fetchone()
        if row is None:
            raise ThreadNotFound(thread_id)
        return row

    def _owned_turn(self, conn: sqlite3.Connection, turn_id: str, owner: str) -> sqlite3.Row:
        row = conn.execute(
            """SELECT t.* FROM research_turns t JOIN research_threads h USING (thread_id)
               WHERE t.turn_id=? AND h.owner=? AND h.deleted_at IS NULL""",
            (turn_id, owner),
        ).fetchone()
        if row is None:
            raise ThreadNotFound(turn_id)
        return row

    @staticmethod
    def _touch(conn: sqlite3.Connection, thread_id: str, now: str) -> None:
        conn.execute("UPDATE research_threads SET updated_at=? WHERE thread_id=?", (now, thread_id))

    # -- threads -----------------------------------------------------------

    def create_thread(self, owner: str, *, title: str | None = None) -> dict[str, Any]:
        now = _iso_now()
        thread_id = f"rt_{uuid.uuid4().hex}"
        with self.lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO research_threads (thread_id, owner, title, created_at, updated_at)"
                " VALUES (?,?,?,?,?)",
                (thread_id, owner, (title or "").strip() or "Untitled", now, now),
            )
            return _thread_row(self._owned_thread(conn, thread_id, owner))

    def list_threads(
        self,
        owner: str,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Bounded summaries only: no evidence packets or answer bodies."""
        limit = max(1, min(int(limit), 200))
        where = ["h.owner=?", "h.deleted_at IS NULL"]
        args: list[Any] = [owner]
        if not include_archived:
            where.append("h.archived_at IS NULL")
        term = (search or "").strip()
        if term:
            like = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            where.append(
                "(h.title LIKE ? ESCAPE '\\' OR EXISTS (SELECT 1 FROM research_turns s"
                " WHERE s.thread_id=h.thread_id AND s.user_question LIKE ? ESCAPE '\\'))"
            )
            args += [like, like]
        sql = f"""
            SELECT h.*,
              (SELECT COUNT(*) FROM research_turns t WHERE t.thread_id=h.thread_id) AS turn_count,
              (SELECT user_question FROM research_turns t WHERE t.thread_id=h.thread_id
                 ORDER BY ordinal ASC LIMIT 1) AS first_question,
              (SELECT user_question FROM research_turns t WHERE t.thread_id=h.thread_id
                 ORDER BY ordinal DESC LIMIT 1) AS last_question,
              (SELECT status FROM research_turns t WHERE t.thread_id=h.thread_id
                 ORDER BY ordinal DESC LIMIT 1) AS last_status
            FROM research_threads h WHERE {" AND ".join(where)}
            ORDER BY h.updated_at DESC, h.thread_id LIMIT ? OFFSET ?"""  # noqa: S608 - fixed fragments; values bound
        with self.lock, self.connect() as conn:
            rows = conn.execute(sql, (*args, limit, max(0, int(offset)))).fetchall()
        out = []
        for row in rows:
            item = _thread_row(row)
            item.update(
                turn_count=row["turn_count"],
                first_question=row["first_question"],
                last_question=row["last_question"],
                last_status=row["last_status"],
            )
            out.append(item)
        return out

    def get_thread(self, thread_id: str, owner: str) -> dict[str, Any]:
        """Thread metadata plus ordered turn shells (no evidence payloads)."""
        with self.lock, self.connect() as conn:
            thread = _thread_row(self._owned_thread(conn, thread_id, owner))
            turns = conn.execute(
                "SELECT * FROM research_turns WHERE thread_id=? ORDER BY ordinal", (thread_id,)
            ).fetchall()
        thread["turns"] = [_turn_row(row) for row in turns]
        return thread

    def rename_thread(self, thread_id: str, owner: str, title: str) -> dict[str, Any]:
        title = " ".join(str(title or "").split())
        if not title:
            raise ValueError("title must not be empty")
        with self.lock, self.connect() as conn:
            self._owned_thread(conn, thread_id, owner)
            conn.execute(
                "UPDATE research_threads SET title=?, updated_at=? WHERE thread_id=?",
                (title[:200], _iso_now(), thread_id),
            )
            return _thread_row(self._owned_thread(conn, thread_id, owner))

    def set_archived(self, thread_id: str, owner: str, archived: bool) -> dict[str, Any]:
        with self.lock, self.connect() as conn:
            self._owned_thread(conn, thread_id, owner)
            conn.execute(
                "UPDATE research_threads SET archived_at=? WHERE thread_id=?",
                (_iso_now() if archived else None, thread_id),
            )
            return _thread_row(self._owned_thread(conn, thread_id, owner))

    def delete_thread(self, thread_id: str, owner: str) -> None:
        """Tombstone the thread and drop its turn history.

        Canonical corpus data, claims, support bindings and the response cache
        are untouched; a surviving response simply loses its thread linkage.
        """
        with self.lock, self.connect() as conn:
            self._owned_thread(conn, thread_id, owner)
            now = _iso_now()
            conn.execute("DELETE FROM research_turns WHERE thread_id=?", (thread_id,))
            conn.execute(
                "UPDATE research_threads SET deleted_at=?, updated_at=?, title='' WHERE thread_id=?",
                (now, now, thread_id),
            )

    # -- turns -------------------------------------------------------------

    def append_turn(
        self,
        thread_id: str,
        owner: str,
        user_question: str,
        *,
        user_instructions: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Append a queued turn atomically; returns ``(turn, created)``.

        A repeated idempotency key returns the original turn (``created=False``).
        The default parent is the preceding turn; linear v1 allows one active
        turn per thread, otherwise parent/context semantics are ambiguous.
        """
        question = str(user_question or "").strip()
        if not question:
            raise ValueError("question must not be empty")
        key = (idempotency_key or "").strip() or None
        with self.lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            thread = self._owned_thread(conn, thread_id, owner)
            if key:
                existing = conn.execute(
                    "SELECT * FROM research_turns WHERE thread_id=? AND idempotency_key=?",
                    (thread_id, key),
                ).fetchone()
                if existing is not None:
                    return _turn_row(existing), False
            last = conn.execute(
                "SELECT turn_id, ordinal, status FROM research_turns WHERE thread_id=?"
                " ORDER BY ordinal DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
            if conn.execute(
                "SELECT 1 FROM research_turns WHERE thread_id=? AND status IN ('queued','running')",
                (thread_id,),
            ).fetchone():
                raise ThreadBusy(thread_id)
            now = _iso_now()
            turn_id = f"rtt_{uuid.uuid4().hex}"
            conn.execute(
                """INSERT INTO research_turns (turn_id, thread_id, ordinal, user_question,
                   user_instructions, idempotency_key, status, parent_turn_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    turn_id,
                    thread_id,
                    (last["ordinal"] + 1) if last else 1,
                    question,
                    user_instructions,
                    key,
                    "queued",
                    last["turn_id"] if last else None,
                    now,
                    now,
                ),
            )
            if not last and thread["title"] in ("", "Untitled"):
                conn.execute(
                    "UPDATE research_threads SET title=? WHERE thread_id=?",
                    (derive_title(question), thread_id),
                )
            self._touch(conn, thread_id, now)
            return _turn_row(self._owned_turn(conn, turn_id, owner)), True

    def get_turn(self, turn_id: str, owner: str) -> dict[str, Any]:
        with self.lock, self.connect() as conn:
            return _turn_row(self._owned_turn(conn, turn_id, owner))

    def turn_for_job(self, job_id: str) -> dict[str, Any] | None:
        with self.lock, self.connect() as conn:
            row = conn.execute(
                "SELECT t.* FROM research_turns t JOIN research_threads h USING (thread_id)"
                " WHERE t.job_id=? AND h.deleted_at IS NULL",
                (job_id,),
            ).fetchone()
        return _turn_row(row) if row else None

    def bind_job(
        self,
        turn_id: str,
        owner: str,
        *,
        job_id: str,
        research_run_id: str | None = None,
        contextualized_query: str | None = None,
        context_selection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach a Research job to a queued turn; also used for retry attempts."""
        with self.lock, self.connect() as conn:
            turn = self._owned_turn(conn, turn_id, owner)
            if turn["status"] in ("completed", "running") or (
                turn["status"] == "queued" and turn["job_id"] and turn["job_id"] != job_id
            ):
                raise ThreadBusy(turn_id)
            now = _iso_now()
            conn.execute(
                """UPDATE research_turns SET job_id=?, research_run_id=COALESCE(?, research_run_id),
                   contextualized_query=COALESCE(?, contextualized_query),
                   context_selection_json=COALESCE(?, context_selection_json),
                   status='running', error=NULL, updated_at=? WHERE turn_id=?""",
                (
                    job_id,
                    research_run_id,
                    contextualized_query,
                    dump_json(context_selection) if context_selection is not None else None,
                    now,
                    turn_id,
                ),
            )
            self._touch(conn, turn["thread_id"], now)
            return _turn_row(self._owned_turn(conn, turn_id, owner))

    def complete_turn(
        self,
        turn_id: str,
        owner: str,
        *,
        research_run_id: str | None,
        response_record_id: str | None,
    ) -> dict[str, Any]:
        with self.lock, self.connect() as conn:
            turn = self._owned_turn(conn, turn_id, owner)
            now = _iso_now()
            conn.execute(
                """UPDATE research_turns SET status='completed', error=NULL,
                   research_run_id=COALESCE(?, research_run_id), response_record_id=?, updated_at=?
                   WHERE turn_id=?""",
                (research_run_id, response_record_id, now, turn_id),
            )
            self._touch(conn, turn["thread_id"], now)
            return _turn_row(self._owned_turn(conn, turn_id, owner))

    def end_turn(
        self, turn_id: str, owner: str, *, status: str, error: str | None = None
    ) -> dict[str, Any]:
        """Mark a turn failed/cancelled, keeping the question and sequence intact."""
        if status not in ("failed", "cancelled"):
            raise ValueError("status must be failed or cancelled")
        with self.lock, self.connect() as conn:
            turn = self._owned_turn(conn, turn_id, owner)
            if turn["status"] == "completed":
                raise ThreadBusy(turn_id)
            now = _iso_now()
            conn.execute(
                "UPDATE research_turns SET status=?, error=?, updated_at=? WHERE turn_id=?",
                (status, (error or "")[:1000] or None, now, turn_id),
            )
            self._touch(conn, turn["thread_id"], now)
            return _turn_row(self._owned_turn(conn, turn_id, owner))

    def retry_turn(self, turn_id: str, owner: str) -> dict[str, Any]:
        """Re-queue a failed/cancelled turn in place: same visible question, new attempt."""
        with self.lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            turn = self._owned_turn(conn, turn_id, owner)
            if turn["status"] not in ("failed", "cancelled"):
                raise ThreadBusy(turn_id)
            if conn.execute(
                "SELECT 1 FROM research_turns WHERE thread_id=? AND status IN ('queued','running')",
                (turn["thread_id"],),
            ).fetchone():
                raise ThreadBusy(turn["thread_id"])
            now = _iso_now()
            conn.execute(
                """UPDATE research_turns SET status='queued', error=NULL, job_id=NULL,
                   attempt=attempt+1, updated_at=? WHERE turn_id=?""",
                (now, turn_id),
            )
            self._touch(conn, turn["thread_id"], now)
            return _turn_row(self._owned_turn(conn, turn_id, owner))

    # -- legacy singleton threads -----------------------------------------

    def materialize_legacy(
        self, owner: str, responses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Idempotently expose legacy one-off responses as one-turn threads.

        ``responses`` are completed legacy summaries (``record_id``, ``question``,
        ``created_at``, optional ``run_id``). The response record itself is not
        rewritten. Already materialized (or tombstoned) responses are skipped.
        """
        created: list[dict[str, Any]] = []
        with self.lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for item in responses:
                record_id = str(item.get("record_id") or "").strip()
                question = str(item.get("question") or "").strip()
                if not record_id or not question:
                    continue
                if conn.execute(
                    "SELECT 1 FROM research_threads WHERE owner=? AND originating_response_record_id=?",
                    (owner, record_id),
                ).fetchone():
                    continue
                stamp = str(item.get("created_at") or "") or _iso_now()
                thread_id = f"rt_{uuid.uuid4().hex}"
                conn.execute(
                    """INSERT INTO research_threads (thread_id, owner, title, created_at, updated_at,
                       originating_response_record_id) VALUES (?,?,?,?,?,?)""",
                    (thread_id, owner, derive_title(question), stamp, stamp, record_id),
                )
                conn.execute(
                    """INSERT INTO research_turns (turn_id, thread_id, ordinal, user_question, status,
                       research_run_id, response_record_id, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        f"rtt_{uuid.uuid4().hex}",
                        thread_id,
                        1,
                        question,
                        "completed",
                        item.get("run_id"),
                        record_id,
                        stamp,
                        stamp,
                    ),
                )
                created.append({"thread_id": thread_id, "response_record_id": record_id})
        return created


_store: ResearchThreadStore | None = None


def get_thread_store(path: str | Path | None = None) -> ResearchThreadStore:
    """Process-wide store on the system database (lazy; tests pass a path)."""
    global _store
    if path is not None:
        return ResearchThreadStore(path)
    if _store is None:
        _store = ResearchThreadStore()
    return _store
