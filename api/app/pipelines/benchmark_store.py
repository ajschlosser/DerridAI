# Copyright 2026 Aaron John Schlosser, PhD.
"""Durable fixed-case pipeline benchmark definitions and results."""

from __future__ import annotations

import sqlite3

from .benchmark import ResearchBenchmarkCase, ResearchBenchmarkRun
from .storage import PipelineDatabase, dump_json, load_json


class PipelineBenchmarkStore:
    def __init__(self, database: PipelineDatabase) -> None:
        self.database = database

    def next_case_version(self, benchmark_id: str) -> int:
        with self.database.lock, self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT MAX(version) AS version
                FROM pipeline_benchmark_cases
                WHERE benchmark_id=?
                """,
                (str(benchmark_id),),
            ).fetchone()
        return int(row["version"] or 0) + 1 if row is not None else 1

    def put_case(self, case: ResearchBenchmarkCase) -> ResearchBenchmarkCase:
        payload = case.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO pipeline_benchmark_cases
                        (benchmark_id,version,name,created_at,created_by,payload_json)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        case.benchmark_id,
                        case.version,
                        case.name,
                        case.created_at.isoformat(),
                        case.created_by,
                        dump_json(payload),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    f"Benchmark case {case.benchmark_id}@{case.version} already exists."
                ) from exc
        return case

    def get_case(
        self,
        benchmark_id: str,
        version: int | None = None,
    ) -> ResearchBenchmarkCase | None:
        with self.database.lock, self.database.connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_cases
                    WHERE benchmark_id=?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (str(benchmark_id),),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_cases
                    WHERE benchmark_id=? AND version=?
                    """,
                    (str(benchmark_id), int(version)),
                ).fetchone()
        if row is None:
            return None
        payload = load_json(row["payload_json"], {})
        try:
            return ResearchBenchmarkCase.model_validate(payload)
        except ValueError:
            return None

    def list_cases(self, *, limit: int = 100, offset: int = 0) -> list[ResearchBenchmarkCase]:
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_benchmark_cases
                ORDER BY created_at DESC, benchmark_id, version DESC
                LIMIT ? OFFSET ?
                """,
                (int(limit), int(offset)),
            ).fetchall()
        result: list[ResearchBenchmarkCase] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(ResearchBenchmarkCase.model_validate(payload))
            except ValueError:
                continue
        return result

    def put_run(self, run: ResearchBenchmarkRun) -> ResearchBenchmarkRun:
        payload = run.model_dump(mode="json")
        with self.database.lock, self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_benchmark_runs
                    (benchmark_run_id,benchmark_id,benchmark_version,owner,created_at,payload_json)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    run.benchmark_run_id,
                    run.benchmark_id,
                    run.benchmark_version,
                    run.owner,
                    run.created_at.isoformat(),
                    dump_json(payload),
                ),
            )
            conn.commit()
        return run

    def get_run(self, benchmark_run_id: str) -> ResearchBenchmarkRun | None:
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
        try:
            return ResearchBenchmarkRun.model_validate(payload)
        except ValueError:
            return None

    def list_runs(
        self,
        *,
        benchmark_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResearchBenchmarkRun]:
        with self.database.lock, self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM pipeline_benchmark_runs
                WHERE (? IS NULL OR benchmark_id=?)
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (benchmark_id, benchmark_id, int(limit), int(offset)),
            ).fetchall()
        result: list[ResearchBenchmarkRun] = []
        for row in rows:
            payload = load_json(row["payload_json"], {})
            if not isinstance(payload, dict):
                continue
            try:
                result.append(ResearchBenchmarkRun.model_validate(payload))
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
                    ORDER BY benchmark_id,version
                    """
                )
            ]
            runs = [
                load_json(row["payload_json"], {})
                for row in conn.execute(
                    """
                    SELECT payload_json
                    FROM pipeline_benchmark_runs
                    ORDER BY created_at,benchmark_run_id
                    """
                )
            ]
        return {
            "benchmark_cases": [item for item in cases if isinstance(item, dict)],
            "benchmark_runs": [item for item in runs if isinstance(item, dict)],
        }

    def clear(self) -> dict[str, int]:
        with self.database.lock, self.database.connect() as conn:
            counts = {
                "pipeline_benchmark_runs": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_benchmark_runs").fetchone()[0]
                ),
                "pipeline_benchmark_cases": int(
                    conn.execute("SELECT COUNT(*) FROM pipeline_benchmark_cases").fetchone()[0]
                ),
            }
            conn.execute("DELETE FROM pipeline_benchmark_runs")
            conn.execute("DELETE FROM pipeline_benchmark_cases")
            conn.commit()
        return counts
