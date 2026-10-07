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

"""Pipeline adapter for Corpus Builder structured metadata enrichment.

Enrichment asks a chat model for one schema-derived metadata group at a time.
The pipeline controls only how that model call runs (see ``structured_llm_stage``).
It never owns the task itself. The active metadata schema supplies the prompt and
response model, the backend validates every answer, and reconciliation, evidence
binding, FieldAssertion authority, and autofill stay domain code downstream of
this adapter.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from .graph_execution import (
    GraphExecutionError,
    GraphExecutor,
    StageFailure,
    StageResult,
)
from .models import PipelineDefinition, PipelineStageDefinition
from .purposes import purpose_registry
from .registry import strategy_registry
from .service import pipeline_hash
from .structured_llm_stage import (
    DEFAULT_ATTEMPTS,
    PROVIDER_ROLES,
    StageInvoker,
    StructuredStageFeature,
    StructuredStagePlan,
    StructuredStageSession,
    compile_structured_stage_pipeline,
    stage_attempts,
    stage_role,
)

__all__ = [
    "DEFAULT_ATTEMPTS",
    "ENRICHMENT",
    "ENRICHMENT_FEATURE",
    "ENRICHMENT_PURPOSE",
    "PROVIDER_ROLES",
    "EnrichmentPlan",
    "EnrichmentSession",
    "StageInvoker",
    "compile_enrichment_pipeline",
    "stage_attempts",
    "stage_role",
]

ENRICHMENT_FEATURE = "corpus_metadata_enrichment"
ENRICHMENT_PURPOSE = "corpus_metadata_enrichment"
ENRICHMENT = StructuredStageFeature(
    feature=ENRICHMENT_FEATURE,
    purpose=ENRICHMENT_PURPOSE,
    strategy="llm.structured_metadata",
    label="metadata enrichment",
)

EnrichmentPlan = StructuredStagePlan


def compile_enrichment_pipeline(pipeline: PipelineDefinition) -> StructuredStagePlan:
    """Accept: one structured-metadata stage, optionally escalating to one other provider role."""
    return compile_structured_stage_pipeline(pipeline, ENRICHMENT)


@dataclass
class _MetadataTask:
    """Server-owned call context; never serialized into a pipeline trace."""

    invoke: StageInvoker
    response_contract: str
    providers: dict[str, tuple[str, str]]
    failures: list[tuple[str, Exception]] = field(default_factory=list)
    path: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EnrichmentSession(StructuredStageSession):
    """Historical provider contracts executed by the generic named-port engine.

    Task state is call-local. The inherited lock protects aggregate telemetry,
    and inherited identity/finish retain historical ledger and trace shapes.
    """

    _executor: GraphExecutor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        purpose = purpose_registry.get(self.spec.purpose)
        if purpose is None:
            raise ValueError("Metadata enrichment requires a registered purpose.")
        self._executor = GraphExecutor(
            self.plan.pipeline,
            registry=strategy_registry,
            purpose=purpose,
            handlers={self.spec.strategy: self._invoke_task},
        )

    @classmethod
    def open(
        cls,
        pipeline: PipelineDefinition | None = None,
    ) -> EnrichmentSession:
        """Open the assigned pipeline, or one exact per-run definition when supplied."""

        if pipeline is None:
            return cls.open_for(ENRICHMENT)
        plan = compile_enrichment_pipeline(pipeline)
        return cls(
            spec=ENRICHMENT,
            plan=plan,
            resolved_hash=pipeline_hash(pipeline),
        )

    def _invoke_task(
        self, stage: PipelineStageDefinition, inputs: Mapping[str, Any]
    ) -> StageResult:
        task: _MetadataTask = inputs["context"]
        role = stage_role(stage)
        begun = time.perf_counter()
        try:
            answer = task.invoke(role, stage_attempts(stage), bool(task.path))
        except InterruptedError:
            raise
        except Exception as exc:  # noqa: BLE001 - retain historical structured failure classification
            status = (
                "unavailable"
                if isinstance(exc, LookupError)
                else "timed_out"
                if getattr(exc, "timed_out", False)
                else "failed"
            )
            self._observe(
                stage,
                contract=task.response_contract,
                seconds=time.perf_counter() - begun,
                status=status,
                provider=task.providers.get(role, ("", "")),
            )
            task.path.append(
                {"stage_id": stage.id, "provider_role": role, "status": status}
            )
            if status != "unavailable":
                task.failures.append((role, exc))
            edge: Literal["on_unavailable", "on_timeout", "on_error"] = (
                "on_unavailable"
                if status == "unavailable"
                else "on_timeout"
                if status == "timed_out"
                else "on_error"
            )
            raise StageFailure(edge) from None
        self._observe(
            stage,
            contract=task.response_contract,
            seconds=time.perf_counter() - begun,
            status="completed",
            provider=task.providers.get(role, ("", "")),
        )
        task.path.append(
            {"stage_id": stage.id, "provider_role": role, "status": "completed"}
        )
        provider, model = task.providers.get(role, ("", ""))
        return StageResult({"answer": answer}, provider=provider, model=model)

    def run(
        self,
        invoke: StageInvoker,
        *,
        response_contract: str,
        providers: dict[str, tuple[str, str]],
    ) -> dict[str, Any]:
        task = _MetadataTask(invoke, response_contract, providers)
        try:
            result = self._executor.run({"context": task})
            return next(iter(result.terminal_outputs.values()))["answer"]
        except GraphExecutionError:
            if task.path and all(step["status"] != "completed" for step in task.path):
                self._raise_failures(task.failures)
            raise
        finally:
            self._remember_path(task.path)
