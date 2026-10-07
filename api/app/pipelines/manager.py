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

"""Application service for saved pipeline configuration and resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .compatibility import pipeline_contract_identity
from .contracts import input_ports
from .defaults import (
    BUILT_IN_ASSIGNMENTS,
    BUILT_IN_PIPELINES,
    built_in_assignment,
    built_in_pipeline,
)
from .models import PipelineAssignment, PipelineDefinition
from .purposes import purpose_registry, workflow_vocabulary
from .service import PipelineService, pipeline_hash, pipeline_service
from .store import PipelineStore, pipeline_store
from .workflows import PURPOSE_ADAPTERS, compile_for_feature, purpose_catalog
from .workflows import runtime_support as adapter_runtime_support


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
        built_in_keys = {
            (item.pipeline_id, item.version)
            for item in built_ins
        }
        custom = [
            item
            for item in self.store.list_definitions(purpose=purpose)
            if (item.pipeline_id, item.version) not in built_in_keys
        ]
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

    def prepare_clone(
        self,
        pipeline_id: str,
        version: int,
    ) -> PipelineDefinition:
        """Return a safe editable draft derived from an immutable definition.

        Clone identity/version selection is server-owned rather than inferred
        from a possibly stale browser catalog. This avoids collisions with
        hidden legacy rows, built-ins, or versions created in another session.
        """

        source = self.get_definition(pipeline_id, version)
        if source is None:
            raise KeyError(f"{pipeline_id}@{version}")

        target_id = (
            f"{source.pipeline_id}.custom"
            if source.built_in
            else source.pipeline_id
        )
        # Do not generate an ID that is itself code-owned. This is uncommon,
        # but makes cloning deterministic even if a future built-in happens to
        # use the conventional ".custom" suffix.
        if source.built_in:
            stem = target_id
            suffix = 2
            while any(
                item.pipeline_id == target_id
                for item in BUILT_IN_PIPELINES
            ):
                target_id = f"{stem}.{suffix}"
                suffix += 1

        versions = [
            item.version
            for item in BUILT_IN_PIPELINES
            if item.pipeline_id == target_id
        ]
        versions.extend(
            item.version
            for item in self.store.list_definitions()
            if item.pipeline_id == target_id
        )
        next_version = max([0, *versions]) + 1

        return source.model_copy(
            deep=True,
            update={
                "pipeline_id": target_id,
                "version": next_version,
                "name": (
                    f"{source.name} — custom"
                    if source.built_in
                    else source.name
                ),
                "status": "draft",
                "built_in": False,
                "derived_from": f"{source.pipeline_id}@{source.version}",
                "created_at": None,
                "created_by": None,
            },
        )

    def prepare_blank(self, purpose_id: str) -> PipelineDefinition:
        """A minimal valid draft for a workflow, to build a pipeline from scratch.

        The first stage is the cheapest registered strategy the workflow's
        adapter runs that takes what the workflow supplies, so the draft
        validates before any edit. Identity is server-owned for the same reason
        clone identity is.
        """

        purpose = purpose_registry.get(purpose_id)
        adapter = PURPOSE_ADAPTERS.get(purpose_id)
        if purpose is None or adapter is None:
            raise KeyError(purpose_id)
        run_types = {item.data_type for item in purpose.run_inputs}
        family_rank = {
            "query_transform": 0,
            "candidate_generation": 1,
            "llm": 2,
        }

        def seedable(spec: Any) -> bool:
            ports = input_ports(spec)
            return all(
                port.data_type in run_types or port.data_type == "any" or not port.required
                for port in ports
            )

        candidates = sorted(
            (
                spec
                for spec in self.service.registry.list()
                if spec.strategy_id in adapter.supported_strategies and seedable(spec)
            ),
            key=lambda spec: (spec.invokes_llm, family_rank.get(spec.family, 9), spec.strategy_id),
        )
        if not candidates:
            raise ValueError(f"No starting stage is available for {purpose_id!r}.")
        seed = candidates[0]
        stage_id = seed.strategy_id.split(".")[-1].replace("-", "_") or "stage"

        taken = {item.pipeline_id for item in BUILT_IN_PIPELINES}
        taken.update(item.pipeline_id for item in self.store.list_definitions())
        stem = f"custom.{purpose_id}"
        pipeline_id = stem
        suffix = 2
        while pipeline_id in taken:
            pipeline_id = f"{stem}.{suffix}"
            suffix += 1
        return PipelineDefinition.model_validate(
            {
                "pipeline_id": pipeline_id,
                "version": 1,
                "name": "Untitled pipeline",
                "purpose": purpose_id,
                "status": "draft",
                "entry_stage_ids": [stage_id],
                "stages": [{"id": stage_id, "strategy": seed.strategy_id}],
            }
        )

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

        # Compiling is the runtime-support check: administrators can save
        # experimental graphs, but only graphs the purpose's adapter can run may
        # become active execution configuration.
        compile_for_feature(assignment.feature, pipeline)

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

        return adapter_runtime_support(pipeline)

    def catalog(self) -> dict[str, Any]:
        return {
            "compatibility": pipeline_contract_identity(self.service.registry),
            "purposes": purpose_catalog(self.service.registry),
            "vocabulary": workflow_vocabulary(),
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
