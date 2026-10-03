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

"""Shared runtime for Corpus Builder features whose model call is one structured-output task.

Metadata enrichment and boundary segmentation each ask a chat model for one schema-validated
answer at a time. Their pipelines control only how that call runs: which configured provider
role answers first, how many attempts it gets, and which failures escalate to the other role.
The feature's own code keeps the task: it builds the prompt, validates the answer, and applies
its domain rules downstream of this runtime.

Two rules are server policy rather than settings: a stage reached by a fallback edge must use
the other provider role (so a read timeout is never simply retried on the same provider), and
the structured-output stage is terminal because its answer returns to backend validation.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self

from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash
from .trace_safety import trace_stage

logger = logging.getLogger(__name__)

PROVIDER_ROLES = ("primary", "review")
DEFAULT_ATTEMPTS = 2

# Trace reasons are codes, never exception text: validation errors can quote
# the model's answer, which may quote source text.
_REASONS = {
    "unavailable": "provider_role_not_configured",
    "timed_out": "provider_timed_out",
    "failed": "structured_output_failed",
}


@dataclass(frozen=True)
class StructuredStageFeature:
    """The feature a structured-stage pipeline drives: its assignment key, purpose, and stage strategy."""

    feature: str
    purpose: str
    strategy: str
    label: str  # lower-case noun phrase for messages, e.g. "metadata enrichment"


def stage_role(stage: PipelineStageDefinition) -> str:
    return str(stage.config.get("provider_role", "primary"))


def stage_attempts(stage: PipelineStageDefinition) -> int:
    return int(stage.config.get("attempts", DEFAULT_ATTEMPTS))


@dataclass(frozen=True)
class StructuredStagePlan:
    pipeline: PipelineDefinition
    entry: PipelineStageDefinition
    fallback: PipelineStageDefinition | None


def compile_structured_stage_pipeline(
    pipeline: PipelineDefinition, spec: StructuredStageFeature
) -> StructuredStagePlan:
    """Accept: one structured stage, optionally escalating to one stage on the other provider role."""

    label = spec.label
    if pipeline.purpose != spec.purpose:
        raise ValueError(f"The {label} adapter can only compile {spec.purpose} pipelines.")
    reject_unhonoured_config(pipeline, label)
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    unsupported = sorted({stage.strategy for stage in stages.values()} - {spec.strategy})
    if unsupported:
        raise ValueError(f"The {label} adapter does not implement strategy stage(s): " + ", ".join(unsupported))
    if len(pipeline.entry_stage_ids) != 1 or pipeline.entry_stage_ids[0] not in stages:
        raise ValueError(f"The {label} pipeline requires exactly one enabled entry stage.")
    entry = stages[pipeline.entry_stage_ids[0]]
    if entry.next or entry.on_empty:
        raise ValueError(
            f"The {label} stage is terminal: its answer returns to backend validation and review."
        )
    fallback_ids = {entry.on_unavailable, entry.on_timeout, entry.on_error} - {None}
    if len(fallback_ids) > 1:
        raise ValueError(f"A {label} stage may escalate to only one other stage.")
    fallback = stages.get(next(iter(fallback_ids))) if fallback_ids else None
    if fallback_ids and fallback is None:
        raise ValueError(f"The {label} escalation stage is missing or disabled.")
    if fallback is not None and fallback.edge_targets():
        raise ValueError(f"The {label} escalation stage must be terminal.")
    if len(stages) != 1 + (fallback is not None):
        raise ValueError(f"The {label} pipeline runs one structured stage and at most one escalation stage.")
    for stage in (entry, fallback):
        if stage is None:
            continue
        if stage_role(stage) not in PROVIDER_ROLES:
            raise ValueError(f"Stage {stage.id!r} provider_role must be one of: {', '.join(PROVIDER_ROLES)}.")
        if not 1 <= stage_attempts(stage) <= 4:
            raise ValueError(f"Stage {stage.id!r} attempts must be between 1 and 4.")
    if fallback is not None and stage_role(fallback) == stage_role(entry):
        raise ValueError(
            "The escalation stage must use the other provider role; a timed-out provider is not retried."
        )
    return StructuredStagePlan(pipeline=pipeline, entry=entry, fallback=fallback)


StageInvoker = Callable[[str, int, bool], dict[str, Any]]


@dataclass
class StructuredStageSession:
    """One resolved pipeline used for a unit of work's model calls, recorded as a single trace."""

    spec: StructuredStageFeature
    plan: StructuredStagePlan
    resolved_hash: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    last_path: list[dict[str, Any]] = field(default_factory=list)
    _state_lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _local: threading.local = field(default_factory=threading.local, repr=False)

    @classmethod
    def open_for(cls, spec: StructuredStageFeature) -> Self:
        """Resolve and compile the assignment; there is no hidden default outside it."""
        from .manager import pipeline_manager

        try:
            resolved = pipeline_manager.resolve(spec.feature)
            pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
            plan = compile_structured_stage_pipeline(pipeline, spec)
        except Exception as exc:  # noqa: BLE001 - reported to the caller as a task failure
            raise RuntimeError(f"The {spec.label} pipeline is unavailable: {exc}") from exc
        return cls(spec=spec, plan=plan, resolved_hash=str(resolved.get("pipeline_hash") or pipeline_hash(pipeline)))

    def identity(self) -> dict[str, Any]:
        """Point-of-use identity for one call, including that caller's stage path."""
        local_path = getattr(self._local, "last_path", None)
        if local_path is None:
            with self._state_lock:
                local_path = list(self.last_path)
        return {
            "feature": self.spec.feature,
            "pipeline_id": self.plan.pipeline.pipeline_id,
            "pipeline_version": self.plan.pipeline.version,
            "pipeline_hash": self.resolved_hash,
            "trace_id": self.run_id,
            "stages": [dict(step) for step in local_path],
        }

    def _remember_path(self, path: list[dict[str, Any]]) -> None:
        copied = [dict(step) for step in path]
        self._local.last_path = copied
        with self._state_lock:
            self.last_path = copied

    def _observe(self, stage: PipelineStageDefinition, *, contract: str, seconds: float, status: str,
                 provider: tuple[str, str]) -> None:
        with self._state_lock:
            if stage.id not in self.counts:
                self.order.append(stage.id)
                self.counts[stage.id] = {
                    "strategy": stage.strategy, "input_count": 0, "output_count": 0, "elapsed_seconds": 0.0,
                    "status": "completed", "contracts": set(), "provider": "", "model": "",
                }
            entry = self.counts[stage.id]
            entry["input_count"] += 1
            entry["output_count"] += int(status == "completed")
            entry["elapsed_seconds"] += seconds
            entry["contracts"].add(contract)
            if status != "unavailable":
                entry["provider"], entry["model"] = provider
            if status != "completed":
                entry["status"], entry["fallback_reason"] = status, _REASONS[status]

    def run(
        self,
        invoke: StageInvoker,
        *,
        response_contract: str,
        providers: dict[str, tuple[str, str]],
    ) -> dict[str, Any]:
        """Run one structured task through the graph.

        Independent callers may share one session. Provider/model work executes outside
        the session lock; only trace aggregation is synchronized. Each thread keeps its
        own last path so identity() remains call-local even when sibling tasks overlap.
        """
        stage: PipelineStageDefinition | None = self.plan.entry
        escalated = False
        failures: list[tuple[str, Exception]] = []
        path: list[dict[str, Any]] = []
        try:
            while stage is not None:
                role = stage_role(stage)
                begun = time.perf_counter()
                try:
                    result = invoke(role, stage_attempts(stage), escalated)
                except InterruptedError:
                    raise
                except Exception as exc:  # noqa: BLE001 - graph fallback decides what follows
                    status = (
                        "unavailable" if isinstance(exc, LookupError)
                        else "timed_out" if getattr(exc, "timed_out", False)
                        else "failed"
                    )
                    self._observe(
                        stage,
                        contract=response_contract,
                        seconds=time.perf_counter() - begun,
                        status=status,
                        provider=providers.get(role, ("", "")),
                    )
                    path.append({"stage_id": stage.id, "provider_role": role, "status": status})
                    if status != "unavailable":
                        failures.append((role, exc))
                    edge = {
                        "unavailable": stage.on_unavailable,
                        "timed_out": stage.on_timeout,
                        "failed": stage.on_error,
                    }[status]
                    stage = self.plan.fallback if edge else None
                    escalated = True
                    continue
                self._observe(
                    stage,
                    contract=response_contract,
                    seconds=time.perf_counter() - begun,
                    status="completed",
                    provider=providers.get(role, ("", "")),
                )
                path.append({"stage_id": stage.id, "provider_role": role, "status": "completed"})
                return result
            if not failures:
                raise LookupError(
                    f"No provider is configured for any stage of the {self.spec.label} pipeline."
                )
            if len(failures) == 1:
                raise failures[0][1]
            pieces = [
                item
                for role, exc in failures
                for item in (getattr(exc, "failures", None) or [f"{role}: {exc}"])
            ]
            suffix = (
                "review-provider escalation"
                if stage_role(self.plan.fallback or self.plan.entry) == "review"
                else "pipeline escalation"
            )
            raise ValueError(
                f"LLM structured output failed after bounded retry and {suffix}: "
                + " | ".join(pieces)
            )
        finally:
            self._remember_path(path)

    def finish(self, *, cancelled: bool = False) -> None:
        """Persist the trace when any stage ran. Telemetry failure never touches the task's result."""
        with self._state_lock:
            order = list(self.order)
            counts_snapshot = {
                stage_id: {
                    **self.counts[stage_id],
                    "contracts": set(self.counts[stage_id]["contracts"]),
                }
                for stage_id in order
            }
        if not order and not cancelled:
            return
        from .store import pipeline_store

        finished_at = datetime.now(UTC)
        trace = PipelineRunTrace(
            run_id=self.run_id,
            feature=self.spec.feature,
            pipeline_id=self.plan.pipeline.pipeline_id,
            pipeline_version=self.plan.pipeline.version,
            resolved_pipeline=self.plan.pipeline.model_dump(mode="json"),
            resolved_hash=self.resolved_hash,
            status="cancelled" if cancelled else "completed",
            started_at=self.started_at,
            finished_at=finished_at,
            total_elapsed_ms=max(0, int((finished_at - self.started_at).total_seconds() * 1000)),
            stages=[
                trace_stage(
                    stage_id,
                    counts["strategy"],
                    elapsed_seconds=counts["elapsed_seconds"],
                    input_count=counts["input_count"],
                    output_count=counts["output_count"],
                    parameters={
                        "provider_role": stage_role(stage),
                        "attempts": stage_attempts(stage),
                        "response_contracts": sorted(counts["contracts"]),
                    },
                    provider=counts["provider"] or None,
                    model=counts["model"] or None,
                    fallback_reason=counts.get("fallback_reason"),
                    status=counts["status"],
                )
                for stage_id in order
                for counts in [counts_snapshot[stage_id]]
                for stage in [self.plan.entry if stage_id == self.plan.entry.id else self.plan.fallback]
                if stage is not None
            ],
        )
        try:
            pipeline_store.put_run(trace)
        except Exception as exc:  # noqa: BLE001 - telemetry must never block the feature
            logger.warning("Could not persist %s pipeline trace %s: %s", self.spec.label, self.run_id, exc)
