# Copyright 2026 Aaron John Schlosser, PhD.
"""Cascade runtime for automatic evidence-recovery pipelines.

Evidence recovery attaches advisory, confidence-free evidence to values that
reached enrichment or acceptance without bound evidence. Its pipelines are
cascades: each stage runs only when the graph routes to it, a stage that
produces candidates continues along ``next``, and a stage that produces nothing
(or is unavailable, times out, or fails) follows the matching fallback edge
with the input it was given. Expensive stages therefore run only when cheaper
ones come back empty.

The runtime executes a closed set of registered strategies; graphs cannot name
arbitrary code. The provenance gate and bounded selection are mandatory. The
direct-support gate is what makes a graph cELF-compliant: a graph that lets
candidates reach provenance without it is executable (for experimentation or
by choice) but is reported as non-cELF-guaranteed at the pipeline output boundary.
Those advisory suggestions may still be retained and later turned into compliant
corpus evidence when a reviewer binds and validates direct support.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..evidence_suggestions import (
    BACKFILL_MIN_SCORE,
    CASCADE_MAX_BLOCKS,
    CASCADE_MMR_LAMBDA,
    CROSS_ENCODER_METHOD,
    LLM_METHOD,
    METHOD,
    MMR_METHOD,
    SEMANTIC_METHOD,
    SEMANTIC_MIN_SCORE,
    _cosine,
    _flatten,
    advisory_evidence_entry,
    llm_prompt,
    select_evidence_mmr,
    semantic_query,
    suggest_evidence_blocks,
    validate_llm_choice,
)
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .service import pipeline_hash
from .trace_safety import trace_stage

RECOVERY_FEATURE = "evidence_recovery"
RECOVERY_PURPOSE = "evidence_recovery"

_QUERY = "query.evidence_field"
_LEXICAL = "retrieve.lexical_bm25"
_SEMANTIC = "retrieve.source_cosine"
_RERANK = "rerank.cross_encoder"
_MMR = "select.mmr"
_SUPPORT = "validate.evidence_support"
_LLM = "llm.closed_choice_evidence"
_PROVENANCE = "validate.provenance"
_SELECT = "select.top_k"
SUPPORTED_STRATEGIES = frozenset(
    {_QUERY, _LEXICAL, _SEMANTIC, _RERANK, _MMR, _SUPPORT, _LLM, _PROVENANCE, _SELECT}
)
# Stages whose own output names a winning method; gates and selection do not.
_METHODS = {
    _LEXICAL: METHOD,
    _SEMANTIC: SEMANTIC_METHOD,
    _RERANK: CROSS_ENCODER_METHOD,
    _MMR: MMR_METHOD,
    _LLM: LLM_METHOD,
}
_FALLBACK_EDGE = {"unavailable": "on_unavailable", "timed_out": "on_timeout", "failed": "on_error"}
MISSING_SOURCE_DOCUMENT = "missing_source_document_identity"


@dataclass(frozen=True)
class RecoveryPlan:
    pipeline: PipelineDefinition
    stages: dict[str, PipelineStageDefinition]
    entry_stage_id: str
    celf_compliant: bool
    compliance_reason: str

    @property
    def selection_limit(self) -> int:
        select = next(stage for stage in self.stages.values() if stage.strategy == _SELECT)
        return max(1, int(select.config.get("limit", CASCADE_MAX_BLOCKS)))


@dataclass(frozen=True)
class EvidenceRecovery:
    """Advisory evidence entry (or ``None``) plus the status that produced it."""

    entry: dict[str, Any] | None
    status: dict[str, Any]


def compile_recovery_pipeline(pipeline: PipelineDefinition) -> RecoveryPlan:
    """Check that a graph is an executable recovery cascade and assess cELF compliance."""

    if pipeline.purpose != RECOVERY_PURPOSE:
        raise ValueError("Evidence-recovery runtime can only compile evidence_recovery pipelines.")
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    unsupported = sorted({stage.strategy for stage in stages.values()} - SUPPORTED_STRATEGIES)
    if unsupported:
        raise ValueError(
            "Evidence-recovery runtime does not implement strategy stage(s): " + ", ".join(unsupported)
        )
    for stage in stages.values():
        disabled = [target for target in stage.edge_targets() if target not in stages]
        if disabled:
            raise ValueError(f"Stage {stage.id!r} routes to disabled stage(s): {', '.join(disabled)}.")
        if len(stage.next) > 1:
            raise ValueError(
                f"Evidence recovery is a cascade: stage {stage.id!r} may continue to only one next stage."
            )
    if len(pipeline.entry_stage_ids) != 1 or pipeline.entry_stage_ids[0] not in stages:
        raise ValueError("Evidence recovery requires exactly one enabled entry stage.")

    def single(strategy: str) -> PipelineStageDefinition:
        matches = [stage for stage in stages.values() if stage.strategy == strategy]
        if len(matches) != 1:
            raise ValueError(f"Evidence recovery requires exactly one {strategy!r} stage.")
        return matches[0]

    provenance = single(_PROVENANCE)
    select = single(_SELECT)
    if provenance.edge_targets() != [select.id] or provenance.next != [select.id]:
        raise ValueError(
            "The provenance gate must continue only to top-K selection; it cannot expose a bypass edge."
        )
    if select.edge_targets():
        raise ValueError("Top-K selection must be the terminal stage.")
    for stage in stages.values():
        if stage.id != provenance.id and select.id in stage.edge_targets():
            raise ValueError("Only the provenance gate may route candidates to selection.")
        if stage.id != select.id and not stage.next:
            raise ValueError(
                f"Stage {stage.id!r} has no next stage, so its candidates could never reach "
                "the provenance gate."
            )
    needs_query = any(stage.strategy in {_SEMANTIC, _RERANK} for stage in stages.values())
    if needs_query and stages[pipeline.entry_stage_ids[0]].strategy != _QUERY:
        raise ValueError(
            "Semantic and cross-encoder stages need the field-aware query stage as the entry stage."
        )

    feeders = [stage for stage in stages.values() if provenance.id in stage.edge_targets()]
    loose = sorted(stage.id for stage in feeders if stage.strategy not in {_SUPPORT, _LLM})
    weak = sorted(
        stage.id
        for stage in feeders
        if stage.strategy == _SUPPORT
        and float(stage.config.get("min_score", BACKFILL_MIN_SCORE)) < BACKFILL_MIN_SCORE
    )
    if loose:
        compliant, reason = False, (
            "Non-cELF-guaranteed: candidates from "
            + ", ".join(repr(item) for item in loose)
            + " reach the provenance gate without direct-support validation. Results remain "
            "advisory and pending review, and each carries this compliance status."
        )
    elif weak:
        compliant, reason = False, (
            "Non-cELF-guaranteed: support stage(s) "
            + ", ".join(repr(item) for item in weak)
            + f" accept direct support below {BACKFILL_MIN_SCORE:.2f}."
        )
    else:
        compliant, reason = True, (
            "cELF-guaranteed: every candidate passes direct-support validation, or is a flagged "
            "closed-choice model selection, before the provenance gate."
        )
    return RecoveryPlan(
        pipeline=pipeline,
        stages=stages,
        entry_stage_id=pipeline.entry_stage_ids[0],
        celf_compliant=compliant,
        compliance_reason=reason,
    )


@dataclass
class _Outcome:
    status: str
    rows: list[dict[str, Any]]
    reason: str | None = None
    observation: dict[str, Any] | None = None


class _Run:
    def __init__(
        self,
        plan: RecoveryPlan,
        *,
        value: Any,
        blocks: list[dict[str, Any]],
        field: str,
        field_metadata: Any,
        source_document_id: str,
        projection: Any,
        llm_choice: Callable[[str], dict[str, Any]] | None,
        llm_skip_reason: str,
        provider: str | None,
        model: str | None,
    ) -> None:
        self.plan = plan
        self.value = value
        self.blocks = blocks
        self.field = field
        self.field_metadata = field_metadata
        self.source_document_id = source_document_id
        self.projection = projection
        self.llm_choice = llm_choice
        self.llm_skip_reason = llm_skip_reason
        self.provider = provider
        self.model = model
        self.query_text: str | None = None
        self.block_text = {
            str(block.get("block_id") or ""): str(block.get("text") or "") for block in blocks
        }

    def run(self, stage: PipelineStageDefinition, rows: list[dict[str, Any]]) -> _Outcome:
        handler = {
            _QUERY: self._query,
            _LEXICAL: self._lexical,
            _SEMANTIC: self._semantic,
            _RERANK: self._rerank,
            _MMR: self._mmr,
            _SUPPORT: self._support,
            _LLM: self._llm,
            _PROVENANCE: self._provenance,
            _SELECT: self._select,
        }[stage.strategy]
        return handler(stage.config, rows)

    def _query(self, _config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        self.query_text = semantic_query(self.field_metadata, self.value)
        return _Outcome("completed", rows)

    def _lexical(self, config: dict[str, Any], _rows: list[dict[str, Any]]) -> _Outcome:
        min_score = float(config.get("min_score", BACKFILL_MIN_SCORE))
        limit = int(config.get("fetch_k", len(self.blocks)))
        rows = suggest_evidence_blocks(self.value, self.blocks, limit=limit, min_score=min_score)
        return _Outcome(
            "completed",
            rows,
            None if rows else f"No block reached lexical score {min_score:.2f}.",
            {"parameters": {"min_score": min_score, "fetch_k": limit}},
        )

    def _semantic(self, config: dict[str, Any], _rows: list[dict[str, Any]]) -> _Outcome:
        if self.projection is None:
            return _Outcome("unavailable", [], "No source embedding projection is available.")
        query = self.query_text or semantic_query(self.field_metadata, self.value)
        try:
            self.projection.sync(
                self.source_document_id, self.blocks, provider=self.provider, model=self.model, prune=False
            )
            unit_ids = [str(b.get("source_unit_id") or b.get("block_id") or "") for b in self.blocks]
            vectors = self.projection.embeddings_for(
                self.source_document_id, unit_ids, provider=self.provider, model=self.model
            )
            query_vector = self.projection.embed_query(query, provider=self.provider, model=self.model)
        except Exception as exc:  # noqa: BLE001 - the graph's on_error edge decides what follows
            return _Outcome("failed", [], f"Semantic retrieval failed: {str(exc)[:300]}")
        min_similarity = config.get("min_similarity")
        rows = []
        for block in self.blocks:
            block_id = str(block.get("block_id") or "")
            vector = vectors.get(str(block.get("source_unit_id") or block_id))
            if not block_id or not vector:
                continue
            score = _cosine(query_vector, vector)
            if min_similarity is not None and score < float(min_similarity):
                continue
            rows.append({"block_id": block_id, "vector": vector, "score": score})
        rows.sort(key=lambda row: -row["score"])
        if "fetch_k" in config:
            rows = rows[: int(config["fetch_k"])]
        return _Outcome(
            "completed",
            rows,
            None if rows else "No source unit had a comparable embedding.",
            {"provider": self.provider, "model": self.model},
        )

    def _rerank(self, config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        from ..config import settings

        if not settings.metadata_cross_encoder_enabled:
            return _Outcome("unavailable", [], "Metadata cross-encoder is disabled by deployment settings.")
        if not rows:
            return _Outcome("completed", [], "No candidates to rerank.")
        from ..cross_encoder import predict_scores

        top_k = max(1, int(config.get("top_k", settings.metadata_cross_encoder_top_k)))
        model_name = str(config.get("model") or settings.rag_cross_encoder_model)
        timeout = float(config.get("timeout_seconds", settings.metadata_cross_encoder_timeout_seconds))
        min_score = float(config.get("min_score", 0.0))
        head = rows[:top_k]
        query = self.query_text or semantic_query(self.field_metadata, self.value)
        scores, telemetry = predict_scores(
            [(query, self.block_text.get(str(row.get("block_id") or ""), "")) for row in head],
            model_name=model_name,
            timeout_seconds=timeout,
        )
        observation = {"model": model_name, "parameters": {"top_k": top_k, "min_score": min_score}}
        if not scores:
            reason = str((telemetry or {}).get("fallback_reason") or "Cross-encoder produced no usable scores.")
            status = (
                "timed_out"
                if reason == "inference_timeout"
                else "failed"
                if reason.startswith("inference_failed")
                else "unavailable"
            )
            return _Outcome(status, [], reason, observation)
        ranked = sorted(zip(head, scores), key=lambda pair: -pair[1])
        picks = [
            {
                **row,
                "score": round(float(score), 4),
                "semantic_score": round(float(row.get("score") or 0.0), 4),
                "cross_encoder_score": round(float(score), 4),
            }
            for row, score in ranked
            if score > min_score
        ]
        reason = None if picks else f"No cross-encoder score exceeded {min_score:g}."
        return _Outcome("completed", picks, reason, observation)

    def _mmr(self, config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        min_relevance = float(config.get("min_relevance", SEMANTIC_MIN_SCORE))
        limit = max(1, int(config.get("limit", self.plan.selection_limit)))
        lambda_mult = float(config.get("lambda_mult", CASCADE_MMR_LAMBDA))
        parameters = {"min_relevance": min_relevance, "limit": limit, "lambda_mult": lambda_mult}
        if not rows or float(rows[0].get("score") or 0.0) < min_relevance:
            return _Outcome(
                "completed", [], f"Top relevance did not reach {min_relevance:.2f}.", {"parameters": parameters}
            )
        selected = select_evidence_mmr(rows, limit=limit, lambda_mult=lambda_mult)
        picks = [
            {
                "block_id": row["block_id"],
                "score": round(float(row["score"]), 4),
                "semantic_score": round(float(row["score"]), 4),
                "mmr_score": round(float(row.get("mmr_score") or 0.0), 4),
            }
            for row in selected
        ]
        return _Outcome("completed", picks, None, {"parameters": parameters})

    def _support(self, config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        min_score = float(config.get("min_score", BACKFILL_MIN_SCORE))
        supported = {
            item["block_id"]: item["score"]
            for item in suggest_evidence_blocks(
                self.value, self.blocks, limit=max(1, len(self.blocks)), min_score=min_score
            )
        }
        kept = [
            {**row, "support_score": supported[str(row.get("block_id") or "")]}
            for row in rows
            if str(row.get("block_id") or "") in supported
        ]
        reason = None if kept else f"No candidate reached direct-support score {min_score:.2f}."
        return _Outcome("completed", kept, reason, {"parameters": {"min_score": min_score, "validator": METHOD}})

    def _llm(self, _config: dict[str, Any], _rows: list[dict[str, Any]]) -> _Outcome:
        if self.llm_choice is None:
            return _Outcome("skipped", [], self.llm_skip_reason)
        try:
            picks = validate_llm_choice(
                self.llm_choice(llm_prompt(self.field, self.value, self.blocks)),
                self.blocks,
                self.value,
                limit=self.plan.selection_limit,
            )
        except Exception as exc:  # noqa: BLE001 - the graph's on_error edge decides what follows
            return _Outcome("failed", [], f"Closed-choice model selection failed: {str(exc)[:300]}")
        observation = {"provider": self.provider, "model": self.model}
        return _Outcome("completed", picks, None if picks else "The model chose no source unit.", observation)

    def _provenance(self, _config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        known = set(self.block_text)
        kept = [
            row
            for row in rows
            if self.source_document_id and str(row.get("block_id") or "") in known
        ]
        reason = None if kept else "No candidate bound to a source unit of the current source document."
        return _Outcome("completed", kept, reason, {"parameters": {"validator": "current_source_unit_membership"}})

    def _select(self, config: dict[str, Any], rows: list[dict[str, Any]]) -> _Outcome:
        limit = max(1, int(config.get("limit", CASCADE_MAX_BLOCKS)))
        return _Outcome("completed", rows[:limit], None, {"parameters": {"limit": limit}})


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row["score"]) for row in rows if isinstance(row.get("score"), (int, float))]
    if not values:
        return {}
    return {"count": len(values), "min": round(min(values), 4), "max": round(max(values), 4)}


def execute_recovery_pipeline(
    plan: RecoveryPlan,
    *,
    resolved_hash: str,
    value: Any,
    blocks: list[dict[str, Any]],
    field: str,
    field_metadata: Any,
    source_document_id: str,
    projection: Any,
    llm_choice: Callable[[str], dict[str, Any]] | None,
    llm_skip_reason: str,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[list[dict[str, Any]], str | None, PipelineRunTrace]:
    """Walk the cascade. Returns selected rows, the winning strategy, and the trace.

    The trace lists only stages that actually ran, in execution order; a stage
    that left along a fallback edge records why in ``fallback_reason``.
    """

    run = _Run(
        plan,
        value=value,
        blocks=blocks,
        field=field,
        field_metadata=field_metadata,
        source_document_id=source_document_id,
        projection=projection,
        llm_choice=llm_choice,
        llm_skip_reason=llm_skip_reason,
        provider=provider,
        model=model,
    )
    started_at = datetime.now(UTC)
    traces = []
    rows: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    winner: str | None = None
    stage_id: str | None = plan.entry_stage_id
    for _ in range(len(plan.stages)):  # acyclic: each stage runs at most once
        if stage_id is None:
            break
        stage = plan.stages[stage_id]
        begun = time.perf_counter()
        # Stages that read the record's source units report those; the rest
        # report the candidate set they were handed.
        input_count = len(blocks) if stage.strategy in {_LEXICAL, _SEMANTIC, _LLM} else len(rows)
        outcome = run.run(stage, rows)
        produced = outcome.status == "completed" and (bool(outcome.rows) or stage.strategy == _QUERY)
        if produced:
            following = stage.next[0] if stage.next else None
            if stage.strategy in _METHODS:
                winner = stage.strategy
            rows = outcome.rows
            if stage.strategy == _SELECT:
                selected = outcome.rows
        elif outcome.status == "completed":
            following = stage.on_empty
        else:
            edge = _FALLBACK_EDGE.get(outcome.status)
            following = getattr(stage, edge) if edge else None
        observation = outcome.observation or {}
        traces.append(
            trace_stage(
                stage.id,
                stage.strategy,
                elapsed_seconds=time.perf_counter() - begun,
                input_count=input_count,
                output_count=len(outcome.rows),
                parameters=observation.get("parameters"),
                provider=observation.get("provider"),
                model=observation.get("model"),
                fallback_reason=None if produced else outcome.reason,
                score_summary=_summary(outcome.rows),
                status=outcome.status,
            )
        )
        stage_id = following
    finished_at = datetime.now(UTC)
    trace = PipelineRunTrace(
        run_id=str(uuid.uuid4()),
        feature=RECOVERY_FEATURE,
        pipeline_id=plan.pipeline.pipeline_id,
        pipeline_version=plan.pipeline.version,
        resolved_pipeline=plan.pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        status="completed",
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        stages=traces,
    )
    return selected, (winner if selected else None), trace


def _entry(items: list[dict[str, Any]], winner: str) -> dict[str, Any]:
    top = items[0]
    if winner == _LLM:
        reason = f"Suggested by the evidence cascade's model choice ({top.get('reason') or 'no reason given'})."
    elif winner == _RERANK:
        reason = f"Suggested by the evidence cascade's cross-encoder rerank (top score {top['score']:.3f})."
    elif winner == _MMR:
        reason = (
            "Suggested by the evidence cascade's maximum marginal relevance "
            f"selection (top semantic score {top['score']:.3f}; "
            f"MMR objective {top['mmr_score']:.3f})."
        )
    elif winner == _SEMANTIC:
        reason = f"Suggested by the evidence cascade's semantic similarity (top score {top['score']:.3f})."
    else:
        reason = f"Suggested by the evidence cascade's deterministic match ({top.get('reason') or 'direct support'})."
    return advisory_evidence_entry(items, _METHODS[winner], reason)


def execute_evidence_recovery(
    *,
    value: Any,
    blocks: list[dict[str, Any]],
    field: str,
    field_metadata: Any,
    source_document_id: str,
    projection: Any,
    llm_choice: Callable[[str], dict[str, Any]] | None = None,
    llm_skip_reason: str = "Closed-choice evidence selection is disabled for this request.",
    provider: str | None = None,
    model: str | None = None,
) -> EvidenceRecovery:
    """Recover advisory evidence through the assigned ``evidence_recovery`` pipeline.

    This is the only production orchestration for automatic evidence recovery.
    Resolution or compilation failures raise; callers decide how to surface them.
    """

    from .manager import pipeline_manager
    from .store import pipeline_store

    if not blocks or not _flatten(value):
        return EvidenceRecovery(entry=None, status={"skipped": "no_value_or_blocks"})
    if not str(source_document_id or "").strip():
        # Evidence must bind to a source unit of an identified source document.
        # Without that identity nothing could pass the provenance gate, so say
        # so explicitly instead of spending retrieval or model calls first.
        return EvidenceRecovery(
            entry=None,
            status={
                "skipped": MISSING_SOURCE_DOCUMENT,
                "reason": (
                    f"{field} evidence was not recovered: the record has no source document "
                    "identity, so no source unit can be bound as provenance."
                ),
            },
        )
    resolved = pipeline_manager.resolve(RECOVERY_FEATURE)
    pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
    plan = compile_recovery_pipeline(pipeline)
    resolved_hash = str(resolved.get("pipeline_hash") or pipeline_hash(pipeline))
    items, winner, trace = execute_recovery_pipeline(
        plan,
        resolved_hash=resolved_hash,
        value=value,
        blocks=blocks,
        field=field,
        field_metadata=field_metadata,
        source_document_id=source_document_id,
        projection=projection,
        llm_choice=llm_choice,
        llm_skip_reason=llm_skip_reason,
        provider=provider,
        model=model,
    )
    identity = {
        "feature": RECOVERY_FEATURE,
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_version": pipeline.version,
        "pipeline_hash": resolved_hash,
        "trace_id": trace.run_id,
        "celf_compliant": plan.celf_compliant,
    }
    status: dict[str, Any] = {**identity, "stages_run": [stage.stage_id for stage in trace.stages]}
    try:
        pipeline_store.put_run(trace)
    except Exception:  # noqa: BLE001 - telemetry must never block advisory evidence
        status["trace_warning"] = "Pipeline trace persistence failed."
    entry = None
    if items and winner:
        entry = _entry(items, winner)
        entry["pipeline"] = identity
    return EvidenceRecovery(entry=entry, status=status)
