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

"""Persistence for pipeline run and stage execution traces."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import Any

from .. import operation_events
from .models import PipelineRunTrace, PipelineStageTrace
from .storage import PipelineDatabase, dump_json, load_json


def _like_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _run_filter_params(
    *,
    feature: str | None,
    features: Sequence[str] | None,
    owner: str | None,
    pipeline_id: str | None,
    status: str | None,
    query: str | None,
) -> tuple[Any, ...]:
    like = _like_term(str(query).strip()) if str(query or "").strip() else None
    feature_list = json.dumps(sorted(features)) if features is not None else None
    return (
        feature,
        feature,
        feature_list,
        feature_list,
        owner,
        owner,
        pipeline_id,
        pipeline_id,
        status,
        status,
        like,
        like,
        like,
        like,
        like,
    )


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
            operation_events.note_resource_changed("pipeline_runs")
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
            operation_events.note_resource_changed("pipeline_runs")
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
        features: Sequence[str] | None = None,
        owner: str | None = None,
        pipeline_id: str | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRunTrace]:
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))
        params = _run_filter_params(
            feature=feature,
            features=features,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
        )
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id
                FROM pipeline_runs
                WHERE (? IS NULL OR feature=?)
                  AND (? IS NULL OR feature IN (SELECT value FROM json_each(?)))
                  AND (? IS NULL OR owner=?)
                  AND (? IS NULL OR pipeline_id=?)
                  AND (? IS NULL OR status=?)
                  AND (
                    ? IS NULL
                    OR run_id LIKE ? ESCAPE '\\'
                    OR pipeline_id LIKE ? ESCAPE '\\'
                    OR feature LIKE ? ESCAPE '\\'
                    OR IFNULL(owner, '') LIKE ? ESCAPE '\\'
                  )
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
        features: Sequence[str] | None = None,
        owner: str | None = None,
        pipeline_id: str | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> int:
        params = _run_filter_params(
            feature=feature,
            features=features,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
        )
        with self.database.lock, self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM pipeline_runs
                WHERE (? IS NULL OR feature=?)
                  AND (? IS NULL OR feature IN (SELECT value FROM json_each(?)))
                  AND (? IS NULL OR owner=?)
                  AND (? IS NULL OR pipeline_id=?)
                  AND (? IS NULL OR status=?)
                  AND (
                    ? IS NULL
                    OR run_id LIKE ? ESCAPE '\\'
                    OR pipeline_id LIKE ? ESCAPE '\\'
                    OR feature LIKE ? ESCAPE '\\'
                    OR IFNULL(owner, '') LIKE ? ESCAPE '\\'
                  )
                """,
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
            operation_events.note_resource_changed("pipeline_runs")
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
            operation_events.note_resource_changed("pipeline_runs")
        return counts
