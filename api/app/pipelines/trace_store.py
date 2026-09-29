# Copyright 2026 Aaron John Schlosser, PhD.
"""Persistence for pipeline run and stage execution traces."""

from __future__ import annotations

import sqlite3
from typing import Any

from .models import PipelineRunTrace, PipelineStageTrace
from .storage import PipelineDatabase, dump_json, load_json


def _like_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _run_filter_clause(
    *,
    feature: str | None,
    owner: str | None,
    pipeline_id: str | None,
    status: str | None,
    query: str | None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if feature:
        clauses.append("feature=?")
        params.append(feature)
    if owner:
        clauses.append("owner=?")
        params.append(owner)
    if pipeline_id:
        clauses.append("pipeline_id=?")
        params.append(pipeline_id)
    if status:
        clauses.append("status=?")
        params.append(status)
    text = str(query or "").strip()
    if text:
        like = _like_term(text)
        clauses.append(
            "("
            "run_id LIKE ? ESCAPE '\\' OR pipeline_id LIKE ? ESCAPE '\\' "
            "OR feature LIKE ? ESCAPE '\\' OR IFNULL(owner, '') LIKE ? ESCAPE '\\'"
            ")"
        )
        params.extend((like, like, like, like))
    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


class PipelineTraceStore:
    def __init__(self, database: PipelineDatabase) -> None:
        self.database = database

    def put_run(self, trace: PipelineRunTrace) -> PipelineRunTrace:
        payload = trace.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
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
                    dump_json(payload),
                ),
            )
            for stage in trace.stages:
                self._put_stage_with_connection(conn, trace.run_id, stage)
            conn.commit()
        return trace

    def put_stage(self, run_id: str, stage: PipelineStageTrace) -> PipelineStageTrace:
        with self.database.lock, self.database.connect() as conn:
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
                dump_json(payload),
            ),
        )

    def get_run(self, run_id: str) -> PipelineRunTrace | None:
        with self.database.lock, self.database.connect() as conn:
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

        payload = load_json(row["payload_json"], {})
        if not isinstance(payload, dict):
            return None
        payload["stages"] = [
            value
            for value in (load_json(item["payload_json"], {}) for item in stage_rows)
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
        pipeline_id: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRunTrace]:
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))
        where, params = _run_filter_clause(
            feature=feature,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
        )
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT run_id
                FROM pipeline_runs
                {where}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                (*params, page_limit, page_offset),
            ).fetchall()
        return [
            trace
            for trace in (self.get_run(str(row["run_id"])) for row in rows)
            if trace is not None
        ]

    def count_runs(
        self,
        *,
        feature: str | None = None,
        owner: str | None = None,
        pipeline_id: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> int:
        where, params = _run_filter_clause(
            feature=feature,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
        )
        with self.database.lock, self.database.connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM pipeline_runs {where}",
                params,
            ).fetchone()
        return int(row[0] if row is not None else 0)

    def delete_run(self, run_id: str) -> bool:
        with self.database.lock, self.database.connect() as conn:
            existed = conn.execute(
                "SELECT 1 FROM pipeline_runs WHERE run_id=?",
                (str(run_id),),
            ).fetchone()
            if existed is None:
                return False
            conn.execute("DELETE FROM pipeline_stage_runs WHERE run_id=?", (str(run_id),))
            conn.execute("DELETE FROM pipeline_runs WHERE run_id=?", (str(run_id),))
            conn.commit()
        return True

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self.database.lock, self.database.connect() as conn:
            runs = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM pipeline_runs ORDER BY started_at"
                )
            ]
            stages = [
                {
                    "run_id": str(row["run_id"]),
                    "payload": load_json(row["payload_json"], {}),
                }
                for row in conn.execute(
                    "SELECT run_id,payload_json FROM pipeline_stage_runs ORDER BY run_id,stage_id"
                )
            ]
        return {
            "runs": [item for item in runs if isinstance(item, dict)],
            "stages": [
                item for item in stages if isinstance(item.get("payload"), dict)
            ],
        }

    def clear(self) -> dict[str, int]:
        with self.database.lock, self.database.connect() as conn:
            counts = {
                "pipeline_stage_runs": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_stage_runs").fetchone()[0]
                ),
                "pipeline_runs": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
                ),
            }
            conn.execute("DELETE FROM pipeline_stage_runs")
            conn.execute("DELETE FROM pipeline_runs")
            conn.commit()
        return counts
