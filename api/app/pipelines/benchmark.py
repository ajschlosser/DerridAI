# Copyright 2026 Aaron John Schlosser, PhD.
"""Persisted fixed-case benchmarks for immutable Research pipeline variants.

Benchmark persistence is deliberately separate from ordinary Research jobs and
operational pipeline traces. A benchmark captures the fixed scholarly input,
corpus/index identity, immutable pipeline identities, retrieval configuration,
and bounded comparison diagnostics needed to reproduce an A/B run.

Prompt bodies belong here because a benchmark case is explicitly a fixed test
fixture. They do not belong in generic operational traces. Credentials, API
keys, provider endpoints, source text, and arbitrary Record metadata are never
persisted in this payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ..models import RAGRunRequest
from .comparison import PipelineVersionRef


class ResearchPipelineBenchmarkRequest(BaseModel):
    """One versioned fixed-case benchmark comparing two Research pipelines."""

    case_id: str = Field(min_length=1, max_length=160)
    case_version: int = Field(default=1, ge=1)
    request: RAGRunRequest
    left: PipelineVersionRef
    right: PipelineVersionRef
    notes: str | None = Field(default=None, max_length=4000)


class ResearchPipelineBenchmarkRun(BaseModel):
    """Durable result of one retrieval-only benchmark execution."""

    benchmark_run_id: str = Field(min_length=1, max_length=200)
    case_id: str = Field(min_length=1, max_length=160)
    case_version: int = Field(ge=1)
    mode: Literal["retrieval_only"] = "retrieval_only"
    created_at: datetime
    created_by: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    fixed_input: dict[str, Any]
    corpus: dict[str, Any]
    retrieval_config: dict[str, Any]
    model_config: dict[str, Any]
    left_pipeline: dict[str, Any]
    right_pipeline: dict[str, Any]
    comparison: dict[str, Any]
    reproducibility_warnings: list[str] = Field(default_factory=list)


_RETRIEVAL_REQUEST_FIELDS = (
    "locales",
    "search_types",
    "k",
    "fetch_k",
    "lambda_mult",
    "rrf_k",
    "rerank_top_n",
    "reranker",
    "query_decomposition",
    "query_decomposition_num_predict",
    "response_language",
    "evidence_record_char_limit",
    "evidence_total_char_limit",
    "skip_retrieval",
)

_MODEL_REQUEST_FIELDS = (
    "provider",
    "model",
    "provider_profile_id",
    "cross_encoder_model",
)


def _request_snapshot(
    request: RAGRunRequest,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    return {field: payload.get(field) for field in fields}


def benchmark_corpus_snapshot(
    store: Any,
    source_collection: str,
) -> dict[str, Any]:
    """Return bounded collection/index identity without arbitrary metadata."""

    row: dict[str, Any] | None = None
    getter = getattr(store, "get_store", None)
    if callable(getter):
        try:
            candidate = getter(source_collection)
            if isinstance(candidate, dict):
                row = candidate
        except Exception:
            row = None
    if row is None:
        lister = getattr(store, "list_stores", None)
        if callable(lister):
            rows = lister()
            row = next(
                (
                    item
                    for item in rows
                    if isinstance(item, dict)
                    and str(item.get("name") or "") == source_collection
                ),
                None,
            )
    if row is None:
        return {"name": source_collection}

    allowed = (
        "name",
        "storage_name",
        "count",
        "manifest_version",
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "embedding_revision",
        "distance_metric",
        "retrieval_mode",
        "status",
        "build_id",
        "build_created_at",
        "last_synced_at",
        "source_kind",
        "source_label",
        "source_record_count",
        "source_snapshot_hash",
        "app_version",
    )
    return {key: row.get(key) for key in allowed if key in row}


def _pipeline_identity(
    side: dict[str, Any],
) -> dict[str, Any]:
    pipeline = side.get("pipeline") if isinstance(side.get("pipeline"), dict) else {}
    return {
        key: pipeline.get(key)
        for key in (
            "pipeline_id",
            "pipeline_version",
            "pipeline_hash",
            "name",
            "purpose",
        )
    }


def _reproducibility_warnings(
    corpus: dict[str, Any],
    left_pipeline: dict[str, Any],
    right_pipeline: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not corpus.get("source_snapshot_hash"):
        warnings.append(
            "The corpus collection does not expose a source snapshot hash; "
            "the exact source snapshot cannot be independently verified."
        )
    if not corpus.get("build_id"):
        warnings.append(
            "The corpus collection does not expose a build ID; the exact index "
            "build cannot be identified."
        )
    if not corpus.get("embedding_revision"):
        warnings.append(
            "The corpus collection does not expose an embedding revision; "
            "embedding reproducibility is limited to provider/model metadata."
        )
    for label, pipeline in (("Pipeline A", left_pipeline), ("Pipeline B", right_pipeline)):
        if not pipeline.get("pipeline_hash"):
            warnings.append(
                f"{label} did not report an immutable pipeline hash."
            )
    return warnings


def build_research_benchmark_run(
    body: ResearchPipelineBenchmarkRequest,
    comparison: dict[str, Any],
    *,
    store: Any,
    created_by: str | None,
) -> ResearchPipelineBenchmarkRun:
    """Construct a safe durable benchmark record from one completed comparison."""

    left = comparison.get("left") if isinstance(comparison.get("left"), dict) else {}
    right = comparison.get("right") if isinstance(comparison.get("right"), dict) else {}
    left_pipeline = _pipeline_identity(left)
    right_pipeline = _pipeline_identity(right)
    corpus = benchmark_corpus_snapshot(store, body.request.source_collection)

    return ResearchPipelineBenchmarkRun(
        benchmark_run_id=f"benchmark-{uuid4().hex}",
        case_id=body.case_id,
        case_version=body.case_version,
        created_at=datetime.now(timezone.utc),
        created_by=created_by,
        notes=body.notes,
        fixed_input={
            "prompt": body.request.prompt,
            "instructions": body.request.instructions,
            "source_collection": body.request.source_collection,
        },
        corpus=corpus,
        retrieval_config=_request_snapshot(
            body.request,
            _RETRIEVAL_REQUEST_FIELDS,
        ),
        model_config=_request_snapshot(
            body.request,
            _MODEL_REQUEST_FIELDS,
        ),
        left_pipeline=left_pipeline,
        right_pipeline=right_pipeline,
        comparison=comparison,
        reproducibility_warnings=_reproducibility_warnings(
            corpus,
            left_pipeline,
            right_pipeline,
        ),
    )
