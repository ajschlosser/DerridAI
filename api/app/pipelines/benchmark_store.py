# Copyright 2026 Aaron John Schlosser, PhD.
"""Persistence for fixed-case pipeline benchmark results."""

from __future__ import annotations

from .benchmark import ResearchPipelineBenchmarkRun
from .storage import PipelineDatabase, dump_json, load_json


class PipelineBenchmarkStore:
    """Durable benchmark results kept separate from ordinary pipeline traces."""

    def __init__(self, database: PipelineDatabase) -> None:
        self.database = database

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

    def list(
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
            rows = [
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
            "benchmark_runs": [
                item for item in rows if isinstance(item, dict)
            ]
        }

    def clear(self) -> dict[str, int]:
        with self.database.lock, self.database.connect() as conn:
            count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM pipeline_benchmark_runs"
                ).fetchone()[0]
            )
            conn.execute("DELETE FROM pipeline_benchmark_runs")
            conn.commit()
        return {"pipeline_benchmark_runs": count}
