# Copyright 2026 Aaron John Schlosser, PhD.
"""Application service for saved pipeline configuration and resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .defaults import (
    BUILT_IN_ASSIGNMENTS,
    BUILT_IN_PIPELINES,
    built_in_assignment,
    built_in_pipeline,
)
from .models import PipelineAssignment, PipelineDefinition
from .research import compile_research_pipeline
from .service import PipelineService, pipeline_hash, pipeline_service
from .store import PipelineStore, pipeline_store


class PipelineManager:
    """Resolve built-in and administrator-defined pipeline configuration.

    Resolution is intentionally conservative in this first migration step:
    persisted system assignments override built-in assignments; callers may then
    add feature-specific/per-run layers without changing this durable contract.
    """

    def __init__(
        self,
        *,
        service: PipelineService = pipeline_service,
        store: PipelineStore = pipeline_store,
    ) -> None:
        self.service = service
        self.store = store

    def list_definitions(self, *, purpose: str | None = None) -> list[PipelineDefinition]:
        built_ins = [
            item
            for item in BUILT_IN_PIPELINES
            if purpose is None or item.purpose == purpose
        ]
        custom = self.store.list_definitions(purpose=purpose)
        return [*built_ins, *custom]

    def get_definition(
        self,
        pipeline_id: str,
        version: int | None = None,
    ) -> PipelineDefinition | None:
        built_in = built_in_pipeline(pipeline_id, version)
        custom = self.store.get_definition(pipeline_id, version)
        if custom is None:
            return built_in
        if built_in is None:
            return custom
        # A code-owned built-in wins any ID/version collision. The persistence
        # API rejects built_in=True, but this guard also protects old databases.
        if version is not None and built_in.version == custom.version:
            return built_in
        return custom if custom.version > built_in.version else built_in

    def list_assignments(self) -> list[PipelineAssignment]:
        custom = self.store.list_assignments()
        custom_keys = {
            (item.feature, item.scope, item.scope_id or "")
            for item in custom
        }
        defaults = [
            item
            for item in BUILT_IN_ASSIGNMENTS
            if (item.feature, item.scope, item.scope_id or "") not in custom_keys
        ]
        return [*defaults, *custom]

    def save_definition(
        self,
        definition: PipelineDefinition,
        *,
        actor: str,
    ) -> PipelineDefinition:
        now = datetime.now(UTC)
        normalized = definition.model_copy(
            update={
                "built_in": False,
                "created_at": now,
                "created_by": str(actor or "administrator"),
            }
        )
        if built_in_pipeline(normalized.pipeline_id, normalized.version) is not None:
            raise ValueError(
                f"Pipeline {normalized.pipeline_id}@{normalized.version} is code-owned; "
                "clone it under a different ID or create a new non-conflicting version."
            )
        validation = self.service.validate(normalized)
        if not validation.valid:
            messages = "; ".join(
                issue.message for issue in validation.issues if issue.level == "error"
            )
            raise ValueError(messages or "Pipeline definition is invalid.")
        return self.store.put_definition(normalized)

    def assign(
        self,
        assignment: PipelineAssignment,
        *,
        actor_source: str = "system",
    ) -> PipelineAssignment:
        pipeline = self.get_definition(
            assignment.pipeline_id,
            assignment.pipeline_version,
        )
        if pipeline is None:
            raise ValueError(
                f"Pipeline {assignment.pipeline_id}@{assignment.pipeline_version} was not found."
            )
        validation = self.service.validate(pipeline)
        if not validation.valid:
            raise ValueError("Cannot assign an invalid pipeline.")
        if pipeline.status != "active":
            raise ValueError(
                "Only active pipeline versions may be assigned system-wide. "
                "Draft versions remain available to administrators for explicit test runs."
            )

        if assignment.feature == "research":
            # Compiling is the runtime-support check: an administrator can save
            # experimental graphs, but only graphs the explicit Research adapter
            # understands may become active execution configuration.
            compile_research_pipeline(pipeline)
        elif assignment.feature not in {
            "evidence_suggestion.reviewer",
            "metadata_precedents",
            "claim_memory",
            "response_memory",
        }:
            raise ValueError(f"Pipeline feature {assignment.feature!r} is not supported.")
        else:
            current = built_in_assignment(assignment.feature)
            if current is None or (
                assignment.pipeline_id,
                assignment.pipeline_version,
            ) != (current.pipeline_id, current.pipeline_version):
                raise ValueError(
                    f"Custom {assignment.feature!r} execution is not wired yet; "
                    "the current built-in assignment remains authoritative."
                )

        normalized = assignment.model_copy(update={"source": actor_source})
        return self.store.put_assignment(
            normalized,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def resolve(self, feature: str) -> dict[str, Any]:
        custom = self.store.get_assignment(feature)
        assignment = custom or built_in_assignment(feature)
        if assignment is None:
            raise KeyError(feature)
        pipeline = self.get_definition(
            assignment.pipeline_id,
            assignment.pipeline_version,
        )
        if pipeline is None:
            raise KeyError(
                f"{assignment.pipeline_id}@{assignment.pipeline_version}"
            )
        validation = self.service.validate(pipeline)
        return {
            "assignment": assignment.model_dump(mode="json"),
            "pipeline": pipeline.model_dump(mode="json"),
            "pipeline_hash": pipeline_hash(pipeline),
            "validation": validation.model_dump(mode="json"),
        }

    def runtime_support(self, pipeline: PipelineDefinition) -> dict[str, Any]:
        """Describe whether a saved graph can currently drive production code."""

        try:
            if pipeline.purpose == "research":
                compile_research_pipeline(pipeline)
                return {"supported": True, "adapter": "research"}
            current_features = {
                "evidence_suggestion": "evidence_suggestion.reviewer",
                "metadata_precedents": "metadata_precedents",
                "claim_memory": "claim_memory",
                "response_memory": "response_memory",
            }
            feature = current_features.get(pipeline.purpose)
            assignment = built_in_assignment(feature) if feature else None
            if assignment and (
                pipeline.pipeline_id,
                pipeline.version,
            ) == (assignment.pipeline_id, assignment.pipeline_version):
                return {"supported": True, "adapter": pipeline.purpose}
            return {
                "supported": False,
                "adapter": None,
                "reason": (
                    "This purpose is inspectable but custom execution has not "
                    "yet been migrated to a configurable adapter."
                ),
            }
        except ValueError as exc:
            return {"supported": False, "adapter": None, "reason": str(exc)}

    def catalog(self) -> dict[str, Any]:
        return {
            "strategies": self.service.strategies(),
            "pipelines": [
                {
                    **item.model_dump(mode="json"),
                    "validation": self.service.validate(item).model_dump(mode="json"),
                    "runtime_support": self.runtime_support(item),
                }
                for item in self.list_definitions()
            ],
            "assignments": [
                item.model_dump(mode="json") for item in self.list_assignments()
            ],
        }


pipeline_manager = PipelineManager()
