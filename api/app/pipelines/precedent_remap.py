# Copyright 2026 Aaron John Schlosser, PhD.
"""Pipeline adapter for mapping precedent evidence onto the current Record's source units.

A reviewed precedent's evidence belongs to another Record. Remapping asks which
source units of *this* Record read like it, so a reviewer adopting the
precedent's value has a shortlist of where this Record may support it. The
result is an advisory correspondence: it binds nothing, never carries the
precedent's text or source identity, and every candidate must be a source unit
of the current Record (the provenance gate cannot be removed).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..evidence_suggestions import (
    PRECEDENT_LEXICAL_METHOD,
    PRECEDENT_SEMANTIC_METHOD,
    lexical_block_scores,
    ranked_block_candidates,
    semantic_block_scores,
)
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash
from .trace_safety import trace_stage

logger = logging.getLogger(__name__)

REMAP_FEATURE = "precedent_evidence_remap"
REMAP_PURPOSE = "precedent_evidence_remap"
_SEMANTIC = "retrieve.source_cosine"
_LEXICAL = "retrieve.token_overlap"
_PROVENANCE = "validate.provenance"
_SELECT = "select.top_k"
_METHODS = {_SEMANTIC: PRECEDENT_SEMANTIC_METHOD, _LEXICAL: PRECEDENT_LEXICAL_METHOD}


@dataclass(frozen=True)
class RemapPlan:
    pipeline: PipelineDefinition
    entry: PipelineStageDefinition
    fallback: PipelineStageDefinition | None
    provenance: PipelineStageDefinition
    select: PipelineStageDefinition
    limit: int


def compile_remap_pipeline(pipeline: PipelineDefinition) -> RemapPlan:
    """Accept: a retrieval stage (optionally falling back to another) → provenance → top-K."""

    if pipeline.purpose != REMAP_PURPOSE:
        raise ValueError("Precedent-remap adapter can only compile precedent_evidence_remap pipelines.")
    reject_unhonoured_config(pipeline, "precedent remap")
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    unsupported = sorted({stage.strategy for stage in stages.values()} - {_SEMANTIC, _LEXICAL, _PROVENANCE, _SELECT})
    if unsupported:
        raise ValueError("Precedent-remap adapter does not implement strategy stage(s): " + ", ".join(unsupported))
    provenance = [stage for stage in stages.values() if stage.strategy == _PROVENANCE]
    select = [stage for stage in stages.values() if stage.strategy == _SELECT]
    if len(provenance) != 1 or len(select) != 1:
        raise ValueError("Precedent remap requires exactly one provenance gate and one top-K selection.")
    if provenance[0].edge_targets() != [select[0].id] or select[0].edge_targets():
        raise ValueError("The provenance gate must continue only to a terminal top-K selection.")
    if len(pipeline.entry_stage_ids) != 1 or pipeline.entry_stage_ids[0] not in stages:
        raise ValueError("Precedent remap requires exactly one enabled entry stage.")
    entry = stages[pipeline.entry_stage_ids[0]]
    if entry.strategy not in _METHODS or entry.next != [provenance[0].id]:
        raise ValueError("Precedent remap starts with a retrieval stage that continues to the provenance gate.")
    fallback_ids = {entry.on_unavailable, entry.on_error} - {None}
    if entry.on_empty or entry.on_timeout or len(fallback_ids) > 1:
        raise ValueError("A remap retrieval stage may fall back to one other stage when unavailable or failing.")
    fallback = stages.get(next(iter(fallback_ids))) if fallback_ids else None
    if fallback_ids and fallback is None:
        raise ValueError("The remap fallback stage is missing or disabled.")
    if fallback is not None and (
        fallback.strategy not in _METHODS
        or fallback.next != [provenance[0].id]
        or fallback.edge_targets() != [provenance[0].id]
    ):
        raise ValueError("The remap fallback must be a retrieval stage that continues only to the provenance gate.")
    for stage in (entry, fallback):
        if stage is not None and "fetch_k" in stage.config:
            raise ValueError(f"Precedent remap does not apply fetch_k on stage {stage.id!r}; use top-K selection.")
    return RemapPlan(
        pipeline=pipeline,
        entry=entry,
        fallback=fallback,
        provenance=provenance[0],
        select=select[0],
        limit=int(select[0].config.get("limit", 3)),
    )


def _min_score(stage: PipelineStageDefinition) -> float:
    key = "min_similarity" if stage.strategy == _SEMANTIC else "min_score"
    return float(stage.config.get(key, 0.0))


@dataclass
class RemapSession:
    """One resolved pipeline used for one or more rankings, recorded as a single trace."""

    plan: RemapPlan
    resolved_hash: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    @classmethod
    def open(cls) -> RemapSession | None:
        """Resolve the assignment, or log why candidates cannot be ranked and return None."""
        from .manager import pipeline_manager

        try:
            resolved = pipeline_manager.resolve(REMAP_FEATURE)
            pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
            plan = compile_remap_pipeline(pipeline)
        except Exception as exc:  # noqa: BLE001 - candidates are advisory; precedents still show
            logger.warning("Precedent evidence remapping is unavailable: %s", exc)
            return None
        return cls(plan=plan, resolved_hash=str(resolved.get("pipeline_hash") or pipeline_hash(pipeline)))

    def _observe(self, stage: PipelineStageDefinition, *, inputs: int, outputs: int, seconds: float,
                 status: str = "completed", reason: str | None = None, parameters: dict[str, Any] | None = None) -> None:
        if stage.id not in self.counts:
            self.order.append(stage.id)
            self.counts[stage.id] = {"strategy": stage.strategy, "input_count": 0, "output_count": 0,
                                     "elapsed_seconds": 0.0, "status": status, "parameters": parameters or {}}
        entry = self.counts[stage.id]
        entry["input_count"] += inputs
        entry["output_count"] += outputs
        entry["elapsed_seconds"] += seconds
        if status != "completed":
            entry["status"], entry["fallback_reason"] = status, reason

    def rank(
        self,
        queries: list[str],
        blocks: list[dict[str, Any]],
        *,
        embed: Callable[[list[str]], list[list[float]]] | None,
    ) -> list[list[dict[str, Any]]]:
        """Candidate source units of ``blocks`` for each query, best first."""
        if not queries or not blocks:
            return [[] for _ in queries]
        stage: PipelineStageDefinition | None = self.plan.entry
        ranked: list[list[dict[str, Any]]] | None = None
        while stage is not None and ranked is None:
            begun = time.perf_counter()
            try:
                if stage.strategy == _SEMANTIC:
                    if embed is None:
                        raise LookupError("No embedding service is available for source-unit ranking.")
                    scores = semantic_block_scores(queries, blocks, embed)
                else:
                    scores = lexical_block_scores(queries, blocks)
            except Exception as exc:  # noqa: BLE001 - the graph's fallback edge decides what follows
                status = "unavailable" if isinstance(exc, LookupError) else "failed"
                self._observe(stage, inputs=len(queries), outputs=0, seconds=time.perf_counter() - begun,
                              status=status, reason=str(exc)[:300])
                edge = stage.on_unavailable if status == "unavailable" else stage.on_error
                stage = self.plan.fallback if edge else None
                continue
            ranked = ranked_block_candidates(scores, blocks, method=_METHODS[stage.strategy], min_score=_min_score(stage))
            self._observe(stage, inputs=len(queries), outputs=sum(map(len, ranked)),
                          seconds=time.perf_counter() - begun, parameters={"min_score": _min_score(stage)})
        if ranked is None:
            return [[] for _ in queries]
        members = {str(block.get("block_id") or "") for block in blocks}
        kept = [[pick for pick in picks if str(pick.get("block_id") or "") in members] for picks in ranked]
        self._observe(self.plan.provenance, inputs=sum(map(len, ranked)), outputs=sum(map(len, kept)), seconds=0.0,
                      parameters={"validator": "current_record_source_unit_membership"})
        selected = [picks[: self.plan.limit] for picks in kept]
        self._observe(self.plan.select, inputs=sum(map(len, kept)), outputs=sum(map(len, selected)), seconds=0.0,
                      parameters={"limit": self.plan.limit})
        return selected

    def finish(self) -> dict[str, Any] | None:
        """Persist the trace (when anything was ranked) and return the pipeline identity."""
        if not self.order:
            return None
        from .store import pipeline_store

        finished_at = datetime.now(UTC)
        trace = PipelineRunTrace(
            run_id=str(uuid.uuid4()),
            feature=REMAP_FEATURE,
            pipeline_id=self.plan.pipeline.pipeline_id,
            pipeline_version=self.plan.pipeline.version,
            resolved_pipeline=self.plan.pipeline.model_dump(mode="json"),
            resolved_hash=self.resolved_hash,
            status="completed",
            started_at=self.started_at,
            finished_at=finished_at,
            total_elapsed_ms=max(0, int((finished_at - self.started_at).total_seconds() * 1000)),
            stages=[
                trace_stage(
                    stage_id,
                    self.counts[stage_id]["strategy"],
                    elapsed_seconds=self.counts[stage_id]["elapsed_seconds"],
                    input_count=self.counts[stage_id]["input_count"],
                    output_count=self.counts[stage_id]["output_count"],
                    parameters=self.counts[stage_id]["parameters"],
                    fallback_reason=self.counts[stage_id].get("fallback_reason"),
                    status=self.counts[stage_id]["status"],
                )
                for stage_id in self.order
            ],
        )
        identity: dict[str, Any] = {
            "feature": REMAP_FEATURE,
            "pipeline_id": self.plan.pipeline.pipeline_id,
            "pipeline_version": self.plan.pipeline.version,
            "pipeline_hash": self.resolved_hash,
            "trace_id": trace.run_id,
        }
        try:
            pipeline_store.put_run(trace)
        except Exception:  # noqa: BLE001 - telemetry must never block advisory candidates
            identity["trace_warning"] = "Pipeline trace persistence failed."
        return identity
