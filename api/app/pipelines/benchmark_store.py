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

"""Persistence for immutable benchmark cases and their fixed-case results."""

from __future__ import annotations

import sqlite3

from .. import operation_events
from .benchmark import (
    ResearchPipelineBenchmarkCase,
    ResearchPipelineBenchmarkRun,
)
from .storage import PipelineDatabase, dump_json, load_json


class PipelineBenchmarkStore:
    """Keep benchmark fixtures/results separate from ordinary pipeline traces."""

    def __init__(self, database: PipelineDatabase) -> None:
        self.database = database

    def put_case(
        self,
        case: ResearchPipelineBenchmarkCase,
    ) -> ResearchPipelineBenchmarkCase:
        payload = case.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO pipeline_benchmark_cases
                        (case_id,version,created_at,created_by,source_collection,
                         corpus_fingerprint,payload_json)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        case.case_id,
                        case.version,
                        case.created_at.isoformat(),
                        case.created_by,
                        case.source_collection,
                        case.corpus_snapshot.fingerprint,
                        dump_json(payload),
                    ),
                )
                conn.commit()
                operation_events.note_resource_changed("pipeline_benchmarks")
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Benchmark case {case.case_id}@{case.version} already exists; "
                    "create a new case version instead of mutating it."
                ) from exc
        return case

    def get_case(
        self,
        case_id: str,
        version: int | None = None,
    ) -> ResearchPipelineBenchmarkCase | None:
        with self.database.lock, self.database.connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_cases
                    WHERE case_id=?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (str(case_id),),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_cases
                    WHERE case_id=? AND version=?
                    """,
                    (str(case_id), int(version)),
                ).fetchone()
        if row is None:
            return None
        payload = load_json(row["payload_json"], {})
        try:
            return ResearchPipelineBenchmarkCase.model_validate(payload)
        except ValueError:
            return None

    def list_cases(
        self,
        *,
        case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResearchPipelineBenchmarkCase]:
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_benchmark_cases
                WHERE (? IS NULL OR case_id=?)
                ORDER BY case_id, version DESC
                LIMIT ? OFFSET ?
                """,
                (case_id, case_id, page_limit, page_offset),
            ).fetchall()
        result: list[ResearchPipelineBenchmarkCase] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(ResearchPipelineBenchmarkCase.model_validate(payload))
            except ValueError:
                continue
        return result

    def put(self, run: ResearchPipelineBenchmarkRun) -> ResearchPipelineBenchmarkRun:
        payload = run.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_benchmark_runs
                    (benchmark_run_id,case_id,case_version,created_at,created_by,
                     left_pipeline_id,left_pipeline_version,right_pipeline_id,
                     right_pipeline_version,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run.benchmark_run_id,
                    run.case_id,
                    run.case_version,
                    run.created_at.isoformat(),
                    run.created_by,
                    str(run.left_pipeline.get("pipeline_id") or ""),
                    int(run.left_pipeline.get("pipeline_version") or 0),
                    str(run.right_pipeline.get("pipeline_id") or ""),
                    int(run.right_pipeline.get("pipeline_version") or 0),
                    dump_json(payload),
                ),
            )
            conn.commit()
        operation_events.note_resource_changed("pipeline_benchmarks")
        return run

    def get(self, benchmark_run_id: str) -> ResearchPipelineBenchmarkRun | None:
        with self.database.lock, self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_benchmark_runs
                WHERE benchmark_run_id=?
                """,
                (str(benchmark_run_id),),
            ).fetchone()
        if row is None:
            return None
        payload = load_json(row["payload_json"], {})
        if not isinstance(payload, dict):
            return None
        try:
            return ResearchPipelineBenchmarkRun.model_validate(payload)
        except ValueError:
            return None

    def list_benchmarks(
        self,
        *,
        case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResearchPipelineBenchmarkRun]:
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_benchmark_runs
                WHERE (? IS NULL OR case_id=?)
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (case_id, case_id, page_limit, page_offset),
            ).fetchall()
        result: list[ResearchPipelineBenchmarkRun] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(ResearchPipelineBenchmarkRun.model_validate(payload))
            except ValueError:
                continue
        return result

    def snapshot(self) -> dict[str, list[dict]]:
        with self.database.lock, self.database.connect() as conn:
            cases = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_cases
                    ORDER BY case_id, version
                    """
                )
            ]
            runs = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_runs
                    ORDER BY created_at, benchmark_run_id
                    """
                )
            ]
        return {
            "benchmark_cases": [item for item in cases if isinstance(item, dict)],
            "benchmark_runs": [item for item in runs if isinstance(item, dict)],
        }

    def clear(self) -> dict[str, int]:
        with self.database.lock, self.database.connect() as conn:
            run_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pipeline_benchmark_runs"
                ).fetchone()[0]
            )
            case_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pipeline_benchmark_cases"
                ).fetchone()[0]
            )
            conn.execute("DELETE FROM pipeline_benchmark_runs")
            conn.execute("DELETE FROM pipeline_benchmark_cases")
            conn.commit()
        operation_events.note_resource_changed("pipeline_benchmarks")
        return {
            "pipeline_benchmark_runs": run_count,
            "pipeline_benchmark_cases": case_count,
        }
