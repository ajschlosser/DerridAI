# Copyright 2026 Aaron John Schlosser, PhD.
"""Facade for durable Pipeline Studio configuration and execution history.

Storage responsibilities are split by domain so definition/version management
and high-volume run traces can evolve independently without growing a new
persistence monolith.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .benchmark import (
    ResearchPipelineBenchmarkCase,
    ResearchPipelineBenchmarkRun,
)
from .benchmark_store import PipelineBenchmarkStore
from .definition_store import PipelineDefinitionStore
from .models import (
    PipelineAssignment,
    PipelineDefinition,
    PipelineRunTrace,
    PipelineStageTrace,
)
from .storage import PipelineDatabase, dump_json
from .trace_store import PipelineTraceStore


class PipelineStore:
    """Stable application-facing facade over focused pipeline repositories."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.database = PipelineDatabase(path)
        self.definitions = PipelineDefinitionStore(self.database)
        self.traces = PipelineTraceStore(self.database)
        self.benchmarks = PipelineBenchmarkStore(self.database)

    @property
    def path(self) -> Path:
        return self.database.path

    def list_definitions(
        self,
        *,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[PipelineDefinition]:
        return self.definitions.list_definitions(purpose=purpose, status=status)

    def get_definition(
        self,
        pipeline_id: str,
        version: int | None = None,
    ) -> PipelineDefinition | None:
        return self.definitions.get_definition(pipeline_id, version)

    def put_definition(self, definition: PipelineDefinition) -> PipelineDefinition:
        return self.definitions.put_definition(definition)

    def list_assignments(self) -> list[PipelineAssignment]:
        return self.definitions.list_assignments()

    def get_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> PipelineAssignment | None:
        return self.definitions.get_assignment(feature, scope=scope, scope_id=scope_id)

    def put_assignment(
        self,
        assignment: PipelineAssignment,
        *,
        updated_at: str,
    ) -> PipelineAssignment:
        return self.definitions.put_assignment(assignment, updated_at=updated_at)

    def delete_assignment(
        self,
        feature: str,
        *,
        scope: str = "system",
        scope_id: str | None = None,
    ) -> bool:
        return self.definitions.delete_assignment(feature, scope=scope, scope_id=scope_id)

    def put_run(self, trace: PipelineRunTrace) -> PipelineRunTrace:
        return self.traces.put_run(trace)

    def put_stage(self, run_id: str, stage: PipelineStageTrace) -> PipelineStageTrace:
        return self.traces.put_stage(run_id, stage)

    def get_run(self, run_id: str) -> PipelineRunTrace | None:
        return self.traces.get_run(run_id)

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
        return self.traces.list_runs(
            feature=feature,
            features=features,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
            limit=limit,
            offset=offset,
        )

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
        return self.traces.count_runs(
            feature=feature,
            features=features,
            owner=owner,
            pipeline_id=pipeline_id,
            status=status,
            query=query,
        )

    def delete_run(self, run_id: str) -> bool:
        return self.traces.delete_run(run_id)

    def clear_runs(self) -> dict[str, int]:
        return self.traces.clear()

    def put_benchmark_case(
        self,
        case: ResearchPipelineBenchmarkCase,
    ) -> ResearchPipelineBenchmarkCase:
        return self.benchmarks.put_case(case)

    def get_benchmark_case(
        self,
        case_id: str,
        version: int | None = None,
    ) -> ResearchPipelineBenchmarkCase | None:
        return self.benchmarks.get_case(case_id, version)

    def list_benchmark_cases(
        self,
        *,
        case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResearchPipelineBenchmarkCase]:
        return self.benchmarks.list_cases(
            case_id=case_id,
            limit=limit,
            offset=offset,
        )

    def put_benchmark(
        self,
        run: ResearchPipelineBenchmarkRun,
    ) -> ResearchPipelineBenchmarkRun:
        return self.benchmarks.put(run)

    def get_benchmark(
        self,
        benchmark_run_id: str,
    ) -> ResearchPipelineBenchmarkRun | None:
        return self.benchmarks.get(benchmark_run_id)

    def list_benchmarks(
        self,
        *,
        case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResearchPipelineBenchmarkRun]:
        return self.benchmarks.list_benchmarks(
            case_id=case_id,
            limit=limit,
            offset=offset,
        )

    def snapshot(self) -> dict[str, Any]:
        """Return configuration, traces, and benchmark history for backups."""

        return {
            **self.definitions.snapshot(),
            **self.traces.snapshot(),
            **self.benchmarks.snapshot(),
        }

    @staticmethod
    def _validated_snapshot(
        payload: dict[str, Any],
    ) -> tuple[
        list[PipelineDefinition],
        list[PipelineAssignment],
        list[PipelineRunTrace],
        list[tuple[str, PipelineStageTrace]],
        list[ResearchPipelineBenchmarkCase],
        list[ResearchPipelineBenchmarkRun],
    ]:
        """Validate a complete backup before any persistent row is changed."""

        if not isinstance(payload, dict):
            raise ValueError("Pipeline backup is invalid.")
        definition_rows = payload.get("definitions") or []
        assignment_rows = payload.get("assignments") or []
        run_rows = payload.get("runs") or []
        stage_rows = payload.get("stages") or []
        benchmark_case_rows = payload.get("benchmark_cases") or []
        benchmark_rows = payload.get("benchmark_runs") or []
        if not all(
            isinstance(items, list)
            for items in (
                definition_rows,
                assignment_rows,
                run_rows,
                stage_rows,
                benchmark_case_rows,
                benchmark_rows,
            )
        ):
            raise ValueError("Pipeline backup is invalid.")

        definitions: list[PipelineDefinition] = []
        definition_keys: set[tuple[str, int]] = set()
        for raw in definition_rows:
            if not isinstance(raw, dict):
                raise ValueError("Pipeline backup contains an invalid definition row.")
            definition = PipelineDefinition.model_validate(raw)
            if definition.built_in:
                raise ValueError(
                    "Pipeline backup cannot persist code-owned built-in definitions."
                )
            if definition.created_at is None:
                raise ValueError(
                    f"Pipeline {definition.pipeline_id}@{definition.version} "
                    "is missing created_at."
                )
            key = (definition.pipeline_id, definition.version)
            if key in definition_keys:
                raise ValueError(
                    f"Pipeline backup contains duplicate definition {key[0]}@{key[1]}."
                )
            definition_keys.add(key)
            definitions.append(definition)

        assignments: list[PipelineAssignment] = []
        assignment_keys: set[tuple[str, str, str]] = set()
        for raw in assignment_rows:
            if not isinstance(raw, dict):
                raise ValueError("Pipeline backup contains an invalid assignment row.")
            assignment = PipelineAssignment.model_validate(raw)
            key = (
                assignment.feature,
                assignment.scope,
                str(assignment.scope_id or ""),
            )
            if key in assignment_keys:
                raise ValueError(
                    "Pipeline backup contains duplicate assignment "
                    f"{assignment.feature!r}/{assignment.scope!r}/{key[2]!r}."
                )
            assignment_keys.add(key)
            assignments.append(assignment)

        runs: list[PipelineRunTrace] = []
        run_ids: set[str] = set()
        for raw in run_rows:
            if not isinstance(raw, dict):
                raise ValueError("Pipeline backup contains an invalid run row.")
            trace = PipelineRunTrace.model_validate({**raw, "stages": []})
            if trace.run_id in run_ids:
                raise ValueError(
                    f"Pipeline backup contains duplicate run {trace.run_id!r}."
                )
            run_ids.add(trace.run_id)
            runs.append(trace)

        stages: list[tuple[str, PipelineStageTrace]] = []
        stage_keys: set[tuple[str, str]] = set()
        for raw in stage_rows:
            if not isinstance(raw, dict) or not isinstance(raw.get("payload"), dict):
                raise ValueError("Pipeline backup contains an invalid stage row.")
            run_id = str(raw.get("run_id") or "")
            if not run_id or run_id not in run_ids:
                raise ValueError(
                    f"Pipeline backup stage references unknown run {run_id!r}."
                )
            stage = PipelineStageTrace.model_validate(raw["payload"])
            key = (run_id, stage.stage_id)
            if key in stage_keys:
                raise ValueError(
                    "Pipeline backup contains duplicate stage "
                    f"{stage.stage_id!r} for run {run_id!r}."
                )
            stage_keys.add(key)
            stages.append((run_id, stage))

        benchmark_cases: list[ResearchPipelineBenchmarkCase] = []
        benchmark_case_keys: set[tuple[str, int]] = set()
        for raw in benchmark_case_rows:
            if not isinstance(raw, dict):
                raise ValueError("Pipeline backup contains an invalid benchmark case row.")
            case = ResearchPipelineBenchmarkCase.model_validate(raw)
            key = (case.case_id, case.version)
            if key in benchmark_case_keys:
                raise ValueError(
                    "Pipeline backup contains duplicate benchmark case "
                    f"{case.case_id}@{case.version}."
                )
            benchmark_case_keys.add(key)
            benchmark_cases.append(case)

        benchmarks: list[ResearchPipelineBenchmarkRun] = []
        benchmark_ids: set[str] = set()
        for raw in benchmark_rows:
            if not isinstance(raw, dict):
                raise ValueError("Pipeline backup contains an invalid benchmark row.")
            benchmark = ResearchPipelineBenchmarkRun.model_validate(raw)
            if benchmark.benchmark_run_id in benchmark_ids:
                raise ValueError(
                    "Pipeline backup contains duplicate benchmark "
                    f"{benchmark.benchmark_run_id!r}."
                )
            benchmark_ids.add(benchmark.benchmark_run_id)
            if (benchmark.case_id, benchmark.case_version) not in benchmark_case_keys:
                raise ValueError(
                    "Pipeline backup benchmark references unknown fixed case "
                    f"{benchmark.case_id}@{benchmark.case_version}."
                )
            benchmarks.append(benchmark)

        return definitions, assignments, runs, stages, benchmark_cases, benchmarks

    def validate_snapshot(self, payload: dict[str, Any]) -> None:
        """Validate a backup without mutating persistent state."""

        self._validated_snapshot(payload)

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        """Atomically replace pipeline state with a validated backup.

        Validation happens before the transaction starts. Definitions,
        assignments, runs, stage traces, benchmark cases, and benchmark results are then replaced
        through one SQLite connection so any insertion failure rolls the whole
        restore back.
        """

        (
            definitions,
            assignments,
            runs,
            stages,
            benchmark_cases,
            benchmarks,
        ) = self._validated_snapshot(payload)

        with self.database.lock, self.database.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM pipeline_stage_runs")
                conn.execute("DELETE FROM pipeline_runs")
                conn.execute("DELETE FROM pipeline_benchmark_runs")
                conn.execute("DELETE FROM pipeline_benchmark_cases")
                conn.execute("DELETE FROM pipeline_assignments")
                conn.execute("DELETE FROM pipeline_definitions")

                for definition in definitions:
                    data = definition.model_dump(mode="json")
                    conn.execute(
                        """
                        INSERT INTO pipeline_definitions
                            (pipeline_id,version,name,purpose,status,created_at,
                             created_by,payload_json)
                        VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            definition.pipeline_id,
                            definition.version,
                            definition.name,
                            definition.purpose,
                            definition.status,
                            str(data.get("created_at") or ""),
                            definition.created_by,
                            dump_json(data),
                        ),
                    )

                for assignment in assignments:
                    data = assignment.model_dump(mode="json")
                    conn.execute(
                        """
                        INSERT INTO pipeline_assignments
                            (feature,scope,scope_id,pipeline_id,pipeline_version,
                             override_allowed,source,updated_at,payload_json)
                        VALUES(?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            assignment.feature,
                            assignment.scope,
                            str(assignment.scope_id or ""),
                            assignment.pipeline_id,
                            assignment.pipeline_version,
                            int(assignment.override_allowed),
                            assignment.source,
                            "restored",
                            dump_json(data),
                        ),
                    )

                for trace in runs:
                    data = trace.model_copy(update={"stages": []}).model_dump(
                        mode="json"
                    )
                    conn.execute(
                        """
                        INSERT INTO pipeline_runs
                            (run_id,feature,pipeline_id,pipeline_version,owner,
                             status,resolved_hash,started_at,finished_at,payload_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
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
                            (
                                trace.finished_at.isoformat()
                                if trace.finished_at
                                else None
                            ),
                            dump_json(data),
                        ),
                    )

                for run_id, stage in stages:
                    data = stage.model_dump(mode="json")
                    conn.execute(
                        """
                        INSERT INTO pipeline_stage_runs
                            (run_id,stage_id,strategy_id,status,started_at,
                             finished_at,payload_json)
                        VALUES(?,?,?,?,?,?,?)
                        """,
                        (
                            run_id,
                            stage.stage_id,
                            stage.strategy_id,
                            stage.status,
                            (
                                stage.started_at.isoformat()
                                if stage.started_at
                                else None
                            ),
                            (
                                stage.finished_at.isoformat()
                                if stage.finished_at
                                else None
                            ),
                            dump_json(data),
                        ),
                    )

                for case in benchmark_cases:
                    data = case.model_dump(mode="json")
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
                            dump_json(data),
                        ),
                    )

                for benchmark in benchmarks:
                    data = benchmark.model_dump(mode="json")
                    conn.execute(
                        """
                        INSERT INTO pipeline_benchmark_runs
                            (benchmark_run_id,case_id,case_version,created_at,
                             created_by,left_pipeline_id,left_pipeline_version,
                             right_pipeline_id,right_pipeline_version,payload_json)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            benchmark.benchmark_run_id,
                            benchmark.case_id,
                            benchmark.case_version,
                            benchmark.created_at.isoformat(),
                            benchmark.created_by,
                            str(benchmark.left_pipeline.get("pipeline_id") or ""),
                            int(benchmark.left_pipeline.get("pipeline_version") or 0),
                            str(benchmark.right_pipeline.get("pipeline_id") or ""),
                            int(benchmark.right_pipeline.get("pipeline_version") or 0),
                            dump_json(data),
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def clear_all(self) -> dict[str, int]:
        return {
            **self.traces.clear(),
            **self.benchmarks.clear(),
            **self.definitions.clear(),
        }


pipeline_store = PipelineStore()
