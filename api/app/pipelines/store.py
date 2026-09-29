# Copyright 2026 Aaron John Schlosser, PhD.
"""Facade for durable Pipeline Studio configuration and execution history.

Storage responsibilities are split by domain so definition/version management
and high-volume run traces can evolve independently without growing a new
persistence monolith.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .definition_store import PipelineDefinitionStore
from .models import (
    PipelineAssignment,
    PipelineDefinition,
    PipelineRunTrace,
    PipelineStageTrace,
)
from .storage import PipelineDatabase
from .trace_store import PipelineTraceStore


class PipelineStore:
    """Stable application-facing facade over focused pipeline repositories."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.database = PipelineDatabase(path)
        self.definitions = PipelineDefinitionStore(self.database)
        self.traces = PipelineTraceStore(self.database)

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
        owner: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRunTrace]:
        return self.traces.list_runs(
            feature=feature,
            owner=owner,
            limit=limit,
            offset=offset,
        )

    def snapshot(self) -> dict[str, Any]:
        """Return configuration and trace history for full system backups."""

        return {
            **self.definitions.snapshot(),
            **self.traces.snapshot(),
        }

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Pipeline backup is invalid.")
        definitions = payload.get("definitions") or []
        assignments = payload.get("assignments") or []
        runs = payload.get("runs") or []
        stages = payload.get("stages") or []
        if not all(
            isinstance(items, list)
            for items in (definitions, assignments, runs, stages)
        ):
            raise ValueError("Pipeline backup is invalid.")

        # Trace rows reference their parent runs, and definitions/assignments are
        # restored before history so no half-restored operational state leaks
        # through if model validation rejects the backup.
        self.traces.clear()
        self.definitions.clear()

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
                self.put_stage(
                    run_id,
                    PipelineStageTrace.model_validate(raw["payload"]),
                )

    def clear_all(self) -> dict[str, int]:
        return {
            **self.traces.clear(),
            **self.definitions.clear(),
        }


pipeline_store = PipelineStore()
