# Copyright 2026 Aaron John Schlosser, PhD.
"""Durable SQLite storage for pipeline definitions, assignments, and traces.

Pipeline state lives in the system database because it is operational
configuration/history, never corpus authority. The store deliberately owns its
schema in this focused module instead of growing the already-large generic
persistence module.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..persistence import system_repository
from .models import (
    PipelineAssignment,
    PipelineDefinition,
    PipelineRunTrace,
    PipelineStageTrace,
)


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: str | bytes | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


class PipelineStore:
    """Versioned operational storage on DerridAI's system SQLite database."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or system_repository.path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pipeline_definitions (
                    pipeline_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (pipeline_id, version)
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_definitions_purpose
                    ON pipeline_definitions(purpose, status, pipeline_id, version DESC);

                CREATE TABLE IF NOT EXISTS pipeline_assignments (
                    feature TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL DEFAULT '',
                    pipeline_id TEXT NOT NULL,
                    pipeline_version INTEGER NOT NULL,
                    override_allowed INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (feature, scope, scope_id)
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_assignments_pipeline
                    ON pipeline_assignments(pipeline_id, pipeline_version);

                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    feature TEXT NOT NULL,
                    pipeline_id TEXT NOT NULL,
                    pipeline_version INTEGER NOT NULL,
                    owner TEXT,
                    status TEXT NOT NULL,
                    resolved_hash TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_feature_started
                    ON pipeline_runs(feature, started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_owner_started
                    ON pipeline_runs(owner, started_at DESC);

                CREATE TABLE IF NOT EXISTS pipeline_stage_runs (
                    run_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, stage_id),
                    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_stage_strategy
                    ON pipeline_stage_runs(strategy_id, started_at DESC);
                """
            )

    def list_definitions(
        self,
        *,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[PipelineDefinition]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_definitions
                WHERE (? IS NULL OR purpose=?)
                  AND (? IS NULL OR status=?)
                ORDER BY purpose, pipeline_id, version DESC
                """,
                (purpose, purpose, status, status),
            ).fetchall()
        result: list[PipelineDefinition] = []
        for row in rows:
            payload = _load(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(PipelineDefinition.model_validate(payload))
            except ValueError:
                continue
        return result

    def get_definition(
        self,
        pipeline_id: str,
        version: int | None = None,
    ) -> PipelineDefinition | None:
        with self._lock, self._connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_definitions
                    WHERE pipeline_id=?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (str(pipeline_id),),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_definitions
                    WHERE pipeline_id=? AND version=?
                    """,
                    (str(pipeline_id), int(version)),
                ).fetchone()
        if row is None:
            return None
        payload = _load(row["payload_json"], {})
        try:
            return PipelineDefinition.model_validate(payload)
        except ValueError:
            return None

    def put_definition(self, definition: PipelineDefinition) -> PipelineDefinition:
        """Persist one immutable custom pipeline version.

        Editing an existing version is intentionally unsupported. Callers clone
        and increment the version so historical runs never change meaning.
        """

        if definition.built_in:
            raise ValueError("Built-in pipeline definitions are code-owned and cannot be persisted.")
        payload = definition.model_dump(mode="json")
        created_at = str(payload.get("created_at") or "")
        if not created_at:
            raise ValueError("Custom pipeline definitions require created_at.")
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO pipeline_definitions
                        (pipeline_id,version,name,purpose,status,created_at,created_by,payload_json)
                    VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        definition.pipeline_id,
                        definition.version,
                        definition.name,
                        definition.purpose,
                        definition.status,
                        created_at,
                        definition.created_by,
                        _dump(payload),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Pipeline {definition.pipeline_id}@{definition.version} already exists; create a new version."
                ) from exc
        return definition

    def list_assignments(self) -> list[PipelineAssignment]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_assignments
                ORDER BY feature, scope, scope_id
                """
            ).fetchall()
        result: list[PipelineAssignment] = []
        for row in rows:
            payload = _load(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(PipelineAssignment.model_validate(payload))
            except ValueError:
                continue
        return result

    def get_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> PipelineAssignment | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_assignments
                WHERE feature=? AND scope=? AND scope_id=?
                """,
                (str(feature), str(scope), str(scope_id or "")),
            ).fetchone()
        if row is None:
            return None
        payload = _load(row["payload_json"], {})
        try:
            return PipelineAssignment.model_validate(payload)
        except ValueError:
            return None

    def put_assignment(
        self,
        assignment: PipelineAssignment,
        *,
        updated_at: str,
    ) -> PipelineAssignment:
        payload = assignment.model_dump(mode="json")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_assignments
                    (feature,scope,scope_id,pipeline_id,pipeline_version,
                     override_allowed,source,updated_at,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(feature,scope,scope_id) DO UPDATE SET
                    pipeline_id=excluded.pipeline_id,
                    pipeline_version=excluded.pipeline_version,
                    override_allowed=excluded.override_allowed,
                    source=excluded.source,
                    updated_at=excluded.updated_at,
                    payload_json=excluded.payload_json
                """,
                (
                    assignment.feature,
                    assignment.scope,
                    str(assignment.scope_id or ""),
                    assignment.pipeline_id,
                    assignment.pipeline_version,
                    int(assignment.override_allowed),
                    assignment.source,
                    str(updated_at),
                    _dump(payload),
                ),
            )
            conn.commit()
        return assignment

    def delete_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM pipeline_assignments WHERE feature=? AND scope=? AND scope_id=?",
                (str(feature), str(scope), str(scope_id or "")),
            )
            conn.commit()
            return bool(cursor.rowcount)

    def put_run(self, trace: PipelineRunTrace) -> PipelineRunTrace:
        payload = trace.model_dump(mode="json")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs
                    (run_id,feature,pipeline_id,pipeline_version,owner,status,
                     resolved_hash,started_at,finished_at,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    finished_at=excluded.finished_at,
                    payload_json=excluded.payload_json
                """,
                (
                    trace.run_id,
                    trace.feature,
                    trace.pipeline_id,
                    trace.pipeline_version,
                    trace.owner,
                    trace.status,
                    trace.resolved_hash,
                    trace.started_at.isoformat(),
                    trace.finished_at.isoformat() if trace.finished_at else None,
                    _dump(payload),
                ),
            )
            for stage in trace.stages:
                self._put_stage_with_connection(conn, trace.run_id, stage)
            conn.commit()
        return trace

    def put_stage(self, run_id: str, stage: PipelineStageTrace) -> PipelineStageTrace:
        with self._lock, self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM pipeline_runs WHERE run_id=?",
                (str(run_id),),
            ).fetchone()
            if exists is None:
                raise KeyError(run_id)
            self._put_stage_with_connection(conn, run_id, stage)
            conn.commit()
        return stage

    @staticmethod
    def _put_stage_with_connection(
        conn: sqlite3.Connection,
        run_id: str,
        stage: PipelineStageTrace,
    ) -> None:
        payload = stage.model_dump(mode="json")
        conn.execute(
            """
            INSERT INTO pipeline_stage_runs
                (run_id,stage_id,strategy_id,status,started_at,finished_at,payload_json)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(run_id,stage_id) DO UPDATE SET
                strategy_id=excluded.strategy_id,
                status=excluded.status,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                payload_json=excluded.payload_json
            """,
            (
                str(run_id),
                stage.stage_id,
                stage.strategy_id,
                stage.status,
                stage.started_at.isoformat() if stage.started_at else None,
                stage.finished_at.isoformat() if stage.finished_at else None,
                _dump(payload),
            ),
        )

    def get_run(self, run_id: str) -> PipelineRunTrace | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM pipeline_runs WHERE run_id=?",
                (str(run_id),),
            ).fetchone()
            stage_rows = conn.execute(
                """
                SELECT payload_json FROM pipeline_stage_runs
                WHERE run_id=?
                ORDER BY COALESCE(started_at, ''), stage_id
                """,
                (str(run_id),),
            ).fetchall()
        if row is None:
            return None
        payload = _load(row["payload_json"], {})
        if not isinstance(payload, dict):
            return None
        payload["stages"] = [
            value
            for value in (_load(item["payload_json"], {}) for item in stage_rows)
            if isinstance(value, dict)
        ]
        try:
            return PipelineRunTrace.model_validate(payload)
        except ValueError:
            return None

    def list_runs(
        self,
        *,
        feature: str | None = None,
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRunTrace]:
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id
                FROM pipeline_runs
                WHERE (? IS NULL OR feature=?)
                  AND (? IS NULL OR owner=?)
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                (feature, feature, owner, owner, page_limit, page_offset),
            ).fetchall()
        return [
            trace
            for trace in (self.get_run(str(row["run_id"])) for row in rows)
            if trace is not None
        ]

    def snapshot(self) -> dict[str, Any]:
        """Return pipeline configuration and trace history for full backups."""

        with self._lock, self._connect() as conn:
            definitions = [
                _load(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_definitions ORDER BY pipeline_id,version"
                )
            ]
            assignments = [
                _load(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_assignments ORDER BY feature,scope,scope_id"
                )
            ]
            runs = [
                _load(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_runs ORDER BY started_at"
                )
            ]
            stages = [
                {
                    "run_id": str(row["run_id"]),
                    "payload": _load(row["payload_json"], {}),
                }
                for row in conn.execute(
                    "SELECT run_id,payload_json FROM pipeline_stage_runs ORDER BY run_id,stage_id"
                )
            ]
        return {
            "definitions": [item for item in definitions if isinstance(item, dict)],
            "assignments": [item for item in assignments if isinstance(item, dict)],
            "runs": [item for item in runs if isinstance(item, dict)],
            "stages": [
                item
                for item in stages
                if isinstance(item.get("payload"), dict)
            ],
        }

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Pipeline backup is invalid.")
        definitions = payload.get("definitions") or []
        assignments = payload.get("assignments") or []
        runs = payload.get("runs") or []
        stages = payload.get("stages") or []
        if not all(isinstance(items, list) for items in (definitions, assignments, runs, stages)):
            raise ValueError("Pipeline backup is invalid.")

        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM pipeline_stage_runs")
            conn.execute("DELETE FROM pipeline_runs")
            conn.execute("DELETE FROM pipeline_assignments")
            conn.execute("DELETE FROM pipeline_definitions")
            conn.commit()

        # Reuse validation-aware public methods rather than duplicating the
        # serialization contract in restore code.
        for raw in definitions:
            if isinstance(raw, dict):
                self.put_definition(PipelineDefinition.model_validate(raw))
        for raw in assignments:
            if isinstance(raw, dict):
                self.put_assignment(
                    PipelineAssignment.model_validate(raw),
                    updated_at="restored",
                )
        for raw in runs:
            if isinstance(raw, dict):
                trace = PipelineRunTrace.model_validate({**raw, "stages": []})
                self.put_run(trace)
        for raw in stages:
            if not isinstance(raw, dict) or not isinstance(raw.get("payload"), dict):
                continue
            run_id = str(raw.get("run_id") or "")
            if run_id:
                self.put_stage(run_id, PipelineStageTrace.model_validate(raw["payload"]))

    def clear_all(self) -> dict[str, int]:
        with self._lock, self._connect() as conn:
            counts = {
                "pipeline_stage_runs": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_stage_runs").fetchone()[0]
                ),
                "pipeline_runs": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
                ),
                "pipeline_assignments": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_assignments").fetchone()[0]
                ),
                "pipeline_definitions": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_definitions").fetchone()[0]
                ),
            }
            conn.execute("DELETE FROM pipeline_stage_runs")
            conn.execute("DELETE FROM pipeline_runs")
            conn.execute("DELETE FROM pipeline_assignments")
            conn.execute("DELETE FROM pipeline_definitions")
            conn.commit()
        return counts


pipeline_store = PipelineStore()
