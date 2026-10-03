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

"""Translate metadata-precedent retrieval telemetry into common pipeline traces."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .metadata_precedents import compile_metadata_precedent_pipeline
from .models import PipelineDefinition, PipelineRunTrace
from .trace_safety import trace_stage


def _ms(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value)) / 1000.0
    return None


def _rerank_status(reason: str) -> str:
    value = str(reason or "").casefold()
    if "timeout" in value:
        return "timed_out"
    if "missing_dependency" in value or "not_configured" in value or "disabled" in value:
        return "unavailable"
    return "failed"


def build_metadata_precedent_trace(
    *,
    run_id: str,
    pipeline: PipelineDefinition,
    resolved_hash: str,
    telemetry: dict[str, Any],
    owner: str | None = None,
    finished_at: datetime | None = None,
) -> PipelineRunTrace:
    """Build an auditable trace without inventing measurements we do not have."""

    plan = compile_metadata_precedent_pipeline(pipeline)
    total_ms = int(telemetry.get("total_ms") or 0)
    finished = finished_at or datetime.now(UTC)
    started = finished - timedelta(milliseconds=max(0, total_ms))
    by_id = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    stages = []

    fallback_reason = str(telemetry.get("fallback_reason") or "")
    fallback_kind = str(telemetry.get("fallback_kind") or "")
    retrieval_failed = bool(fallback_reason)
    retrieval_fell_back = bool(
        fallback_reason and telemetry.get("fallback_mode") == "lexical"
    )

    retrieve_status = "completed"
    if retrieval_failed:
        retrieve_status = {
            "timeout": "timed_out",
            "unavailable": "unavailable",
            "error": "failed",
        }.get(fallback_kind, "failed")
    retrieve = by_id[plan.retrieve_stage_id]
    stages.append(
        trace_stage(
            retrieve.id,
            retrieve.strategy,
            elapsed_seconds=_ms(
                sum(
                    int(telemetry.get(key) or 0)
                    for key in ("sync_ms", "query_ms", "search_ms")
                )
            ),
            input_count=1,
            output_count=(
                0
                if retrieval_fell_back
                else int(telemetry.get("examples_considered") or 0)
            ),
            parameters={
                "fetch_k": telemetry.get("fetch_k"),
                "embedding_provider": telemetry.get("embedding_provider"),
                "embedding_model": telemetry.get("embedding_model"),
            },
            provider=(
                str(telemetry.get("embedding_provider"))
                if telemetry.get("embedding_provider")
                else None
            ),
            model=(
                str(telemetry.get("embedding_model"))
                if telemetry.get("embedding_model")
                else None
            ),
            collection="derridai_metadata_exemplars",
            fallback_reason=fallback_reason or None,
            status=retrieve_status,
        )
    )

    if retrieval_failed:
        if retrieval_fell_back and plan.lexical_fallback_stage_id is not None:
            fallback = by_id[plan.lexical_fallback_stage_id]
            stages.append(
                trace_stage(
                    fallback.id,
                    fallback.strategy,
                    elapsed_seconds=_ms(telemetry.get("total_ms")),
                    input_count=int(telemetry.get("candidates_considered") or 0),
                    output_count=int(telemetry.get("examples_used") or 0),
                    parameters={
                        "ranking": telemetry.get("ranking"),
                        "packet_char_budget": plan.packet_char_budget,
                    },
                    score_summary={
                        "packet_chars": telemetry.get("packet_chars"),
                        "fields_served": telemetry.get("fields_served") or [],
                    },
                    status="completed",
                )
            )
        for stage_id in (
            plan.scope_stage_id,
            plan.hybrid_stage_id,
            plan.rerank_stage_id,
            plan.quotas_stage_id,
            plan.mmr_stage_id,
            plan.pack_stage_id,
        ):
            if stage_id is None:
                continue
            stage = by_id[stage_id]
            stages.append(
                trace_stage(
                    stage.id,
                    stage.strategy,
                    fallback_reason=(
                        "semantic retrieval used lexical fallback path"
                        if retrieval_fell_back
                        else "semantic retrieval failed and no fallback path was configured"
                    ),
                    status="skipped",
                )
            )
    else:
        scope = by_id[plan.scope_stage_id]
        stages.append(
            trace_stage(
                scope.id,
                scope.strategy,
                input_count=int(telemetry.get("examples_considered") or 0),
                parameters={"fields_served": telemetry.get("fields_served") or []},
                status="completed",
            )
        )

        hybrid = by_id[plan.hybrid_stage_id]
        stages.append(
            trace_stage(
                hybrid.id,
                hybrid.strategy,
                parameters={
                    "semantic_weight": telemetry.get(
                        "semantic_weight",
                        plan.semantic_weight,
                    ),
                    "lexical_weight": telemetry.get(
                        "lexical_weight",
                        plan.lexical_weight,
                    ),
                },
                status="completed",
            )
        )

        if plan.rerank_stage_id is not None:
            rerank = by_id[plan.rerank_stage_id]
            reranking = (
                telemetry.get("reranking")
                if isinstance(telemetry.get("reranking"), dict)
                else {}
            )
            reason = str(reranking.get("fallback_reason") or "")
            mode = str(reranking.get("mode") or "")
            rerank_status = (
                "completed"
                if mode == "cross_encoder" and not reason
                else "skipped"
                if mode == "not_needed"
                else _rerank_status(reason)
                if reason
                else "completed"
            )
            stages.append(
                trace_stage(
                    rerank.id,
                    rerank.strategy,
                    elapsed_seconds=_ms(
                        telemetry.get("rerank_ms")
                        or reranking.get("timing_ms")
                    ),
                    input_count=int(reranking.get("candidate_count") or 0),
                    output_count=int(reranking.get("reranked_count") or 0),
                    parameters={
                        "top_k": plan.cross_encoder_top_k,
                        "timeout_seconds": plan.cross_encoder_timeout_seconds,
                    },
                    provider=(
                        str(reranking.get("provider"))
                        if reranking.get("provider")
                        else None
                    ),
                    model=(
                        str(reranking.get("model"))
                        if reranking.get("model")
                        else plan.cross_encoder_model
                    ),
                    fallback_reason=reason or None,
                    status=rerank_status,
                )
            )

        quotas = by_id[plan.quotas_stage_id]
        stages.append(
            trace_stage(
                quotas.id,
                quotas.strategy,
                output_count=int(telemetry.get("examples_used") or 0),
                status="completed",
            )
        )

        mmr = by_id[plan.mmr_stage_id]
        stages.append(
            trace_stage(
                mmr.id,
                mmr.strategy,
                parameters={
                    "lambda_mult": telemetry.get("mmr_lambda", plan.mmr_lambda)
                },
                output_count=int(telemetry.get("examples_used") or 0),
                status="completed",
            )
        )

        pack = by_id[plan.pack_stage_id]
        stages.append(
            trace_stage(
                pack.id,
                pack.strategy,
                elapsed_seconds=_ms(telemetry.get("select_ms")),
                input_count=int(telemetry.get("examples_used") or 0),
                output_count=int(telemetry.get("examples_used") or 0),
                parameters={
                    "char_budget": telemetry.get(
                        "packet_char_budget",
                        plan.packet_char_budget,
                    )
                },
                score_summary={
                    "packet_chars": telemetry.get("packet_chars"),
                    "fields_served": telemetry.get("fields_served") or [],
                },
                status="completed",
            )
        )

        if plan.lexical_fallback_stage_id is not None:
            fallback = by_id[plan.lexical_fallback_stage_id]
            stages.append(
                trace_stage(
                    fallback.id,
                    fallback.strategy,
                    status="skipped",
                )
            )

    warnings = [fallback_reason] if fallback_reason else []
    return PipelineRunTrace(
        run_id=run_id,
        feature="metadata_precedents",
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        resolved_pipeline=pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        owner=owner,
        status="completed",
        started_at=started,
        finished_at=finished,
        total_elapsed_ms=max(0, total_ms),
        warnings=warnings,
        stages=stages,
    )
