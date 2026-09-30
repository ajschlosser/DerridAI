# Copyright 2026 Aaron John Schlosser, PhD.
"""Pipeline adapter for Corpus Builder structured metadata enrichment.

Enrichment asks a chat model for one schema-derived metadata group at a time.
The pipeline controls only how that model call runs: which configured provider
role answers first, how many attempts it gets, and which failures escalate to
the other role. It never owns the task itself. The active metadata schema
supplies the prompt and response model, the backend validates every answer,
and reconciliation, evidence binding, FieldAssertion authority, and autofill
stay domain code downstream of this adapter.

Two rules are server policy rather than settings: a stage reached by a
fallback edge must use the other provider role (so a read timeout is never
simply retried on the same provider), and the structured-output stage is
terminal because its answer returns to schema validation and review.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash
from .trace_safety import trace_stage

logger = logging.getLogger(__name__)

ENRICHMENT_FEATURE = "corpus_metadata_enrichment"
ENRICHMENT_PURPOSE = "corpus_metadata_enrichment"
_STRUCTURED = "llm.structured_metadata"
PROVIDER_ROLES = ("primary", "review")
DEFAULT_ATTEMPTS = 2

# Trace reasons are codes, never exception text: validation errors can quote
# the model's answer, which may quote source text.
_REASONS = {
    "unavailable": "provider_role_not_configured",
    "timed_out": "provider_timed_out",
    "failed": "structured_output_failed",
}


def stage_role(stage: PipelineStageDefinition) -> str:
    return str(stage.config.get("provider_role", "primary"))


def stage_attempts(stage: PipelineStageDefinition) -> int:
    return int(stage.config.get("attempts", DEFAULT_ATTEMPTS))


@dataclass(frozen=True)
class EnrichmentPlan:
    pipeline: PipelineDefinition
    entry: PipelineStageDefinition
    fallback: PipelineStageDefinition | None


def compile_enrichment_pipeline(pipeline: PipelineDefinition) -> EnrichmentPlan:
    """Accept: one structured-metadata stage, optionally escalating to one other provider role."""

    if pipeline.purpose != ENRICHMENT_PURPOSE:
        raise ValueError("Metadata-enrichment adapter can only compile corpus_metadata_enrichment pipelines.")
    reject_unhonoured_config(pipeline, "metadata enrichment")
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    unsupported = sorted({stage.strategy for stage in stages.values()} - {_STRUCTURED})
    if unsupported:
        raise ValueError("Metadata-enrichment adapter does not implement strategy stage(s): " + ", ".join(unsupported))
    if len(pipeline.entry_stage_ids) != 1 or pipeline.entry_stage_ids[0] not in stages:
        raise ValueError("Metadata enrichment requires exactly one enabled entry stage.")
    entry = stages[pipeline.entry_stage_ids[0]]
    if entry.next or entry.on_empty:
        raise ValueError(
            "The structured metadata stage is terminal: its answer returns to schema validation and review."
        )
    fallback_ids = {entry.on_unavailable, entry.on_timeout, entry.on_error} - {None}
    if len(fallback_ids) > 1:
        raise ValueError("A metadata-enrichment stage may escalate to only one other stage.")
    fallback = stages.get(next(iter(fallback_ids))) if fallback_ids else None
    if fallback_ids and fallback is None:
        raise ValueError("The metadata-enrichment escalation stage is missing or disabled.")
    if fallback is not None and fallback.edge_targets():
        raise ValueError("The metadata-enrichment escalation stage must be terminal.")
    if len(stages) != 1 + (fallback is not None):
        raise ValueError("Metadata enrichment runs one structured stage and at most one escalation stage.")
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
    return EnrichmentPlan(pipeline=pipeline, entry=entry, fallback=fallback)


StageInvoker = Callable[[str, int, bool], dict[str, Any]]


@dataclass
class EnrichmentSession:
    """One resolved pipeline used for a Record's metadata groups, recorded as a single trace."""

    plan: EnrichmentPlan
    resolved_hash: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    last_path: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def open(cls) -> EnrichmentSession:
        """Resolve and compile the assignment; there is no hidden default outside it."""
        from .manager import pipeline_manager

        try:
            resolved = pipeline_manager.resolve(ENRICHMENT_FEATURE)
            pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
            plan = compile_enrichment_pipeline(pipeline)
        except Exception as exc:  # noqa: BLE001 - reported to the caller as a family failure
            raise RuntimeError(f"The metadata enrichment pipeline is unavailable: {exc}") from exc
        return cls(plan=plan, resolved_hash=str(resolved.get("pipeline_hash") or pipeline_hash(pipeline)))

    def identity(self) -> dict[str, Any]:
        """Point-of-use identity for one call: the pipeline, its trace, and the stages that ran."""
        return {
            "feature": ENRICHMENT_FEATURE,
            "pipeline_id": self.plan.pipeline.pipeline_id,
            "pipeline_version": self.plan.pipeline.version,
            "pipeline_hash": self.resolved_hash,
            "trace_id": self.run_id,
            "stages": [dict(step) for step in self.last_path],
        }

    def _observe(self, stage: PipelineStageDefinition, *, contract: str, seconds: float, status: str,
                 provider: tuple[str, str]) -> None:
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

        ``invoke(provider_role, attempts, escalated)`` performs the model call. It raises
        ``LookupError`` when the role has no configured provider, and an exception with a true
        ``timed_out`` attribute when the provider stopped on a read timeout.
        """
        stage: PipelineStageDefinition | None = self.plan.entry
        escalated = False
        failures: list[tuple[str, Exception]] = []
        self.last_path = []
        while stage is not None:
            role = stage_role(stage)
            begun = time.perf_counter()
            try:
                result = invoke(role, stage_attempts(stage), escalated)
            except InterruptedError:
                raise
            except Exception as exc:  # noqa: BLE001 - the graph's fallback edge decides what follows
                status = (
                    "unavailable" if isinstance(exc, LookupError)
                    else "timed_out" if getattr(exc, "timed_out", False)
                    else "failed"
                )
                self._observe(stage, contract=response_contract, seconds=time.perf_counter() - begun,
                              status=status, provider=providers.get(role, ("", "")))
                self.last_path.append({"stage_id": stage.id, "provider_role": role, "status": status})
                if status != "unavailable":
                    failures.append((role, exc))
                edge = {"unavailable": stage.on_unavailable, "timed_out": stage.on_timeout, "failed": stage.on_error}[status]
                stage = self.plan.fallback if edge else None  # the escalation stage has no edges
                escalated = True
                continue
            self._observe(stage, contract=response_contract, seconds=time.perf_counter() - begun,
                          status="completed", provider=providers.get(role, ("", "")))
            self.last_path.append({"stage_id": stage.id, "provider_role": role, "status": "completed"})
            return result
        if not failures:
            raise LookupError("No provider is configured for any stage of the metadata enrichment pipeline.")
        if len(failures) == 1:
            raise failures[0][1]
        pieces = [
            item for role, exc in failures
            for item in (getattr(exc, "failures", None) or [f"{role}: {exc}"])
        ]
        suffix = "review-provider escalation" if stage_role(self.plan.fallback or self.plan.entry) == "review" else "pipeline escalation"
        raise ValueError(f"LLM structured output failed after bounded retry and {suffix}: " + " | ".join(pieces))

    def finish(self, *, cancelled: bool = False) -> None:
        """Persist the trace when any stage ran. Telemetry failure never touches the Record."""
        if not self.order:
            return
        from .store import pipeline_store

        finished_at = datetime.now(UTC)
        trace = PipelineRunTrace(
            run_id=self.run_id,
            feature=ENRICHMENT_FEATURE,
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
                for stage_id in self.order
                for counts in [self.counts[stage_id]]
                for stage in [self.plan.entry if stage_id == self.plan.entry.id else self.plan.fallback]
                if stage is not None
            ],
        )
        try:
            pipeline_store.put_run(trace)
        except Exception as exc:  # noqa: BLE001 - telemetry must never block enrichment
            logger.warning("Could not persist metadata enrichment pipeline trace %s: %s", self.run_id, exc)
