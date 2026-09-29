# Copyright 2026 Aaron John Schlosser, PhD.
"""Immutable fixed-case benchmarks for Research pipeline variants.

Benchmark cases freeze a scholarly question, bounded retrieval controls, and the
observable corpus/index manifest before any A/B execution. Benchmark runs use the
real non-persistent Research dry-run path and persist only benchmark-specific
inputs, immutable pipeline snapshots, bounded diagnostics, and reproducibility
metadata. They never become ordinary Research jobs or operational pipeline traces.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ..models import LanguageCode, RAGRunRequest, SearchType
from .comparison import PipelineVersionRef


class BenchmarkCollectionSnapshot(BaseModel):
    """Bounded identity for one collection that may serve the fixed case."""

    name: str = Field(min_length=1, max_length=128)
    storage_name: str | None = None
    count: int = Field(default=0, ge=0)
    manifest_version: int | None = Field(default=None, ge=1)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = Field(default=None, ge=1)
    embedding_revision: str | None = None
    distance_metric: str | None = None
    retrieval_mode: str | None = None
    status: str | None = None
    build_id: str | None = None
    build_created_at: str | None = None
    last_synced_at: str | None = None
    source_kind: str | None = None
    source_label: str | None = None
    source_record_count: int | None = Field(default=None, ge=0)
    source_snapshot_hash: str | None = None
    app_version: str | None = None


class BenchmarkCorpusSnapshot(BaseModel):
    """Canonical manifest for the source and relevant language indexes."""

    fingerprint: str = Field(min_length=64, max_length=64)
    collections: list[BenchmarkCollectionSnapshot] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class ResearchPipelineBenchmarkCaseCreate(BaseModel):
    """Immutable retrieval-only benchmark case supplied by an administrator."""

    case_id: str = Field(min_length=1, max_length=160)
    version: int = Field(default=1, ge=1)
    prompt: str = Field(min_length=1, max_length=20000)
    instructions: str | None = Field(default=None, max_length=20000)
    source_collection: str = Field(min_length=1, max_length=128)
    locales: list[LanguageCode] = Field(default_factory=lambda: ["en", "fr"])
    search_types: list[SearchType] = Field(
        default_factory=lambda: ["similarity", "lexical", "mmr"]
    )
    k: int = Field(default=64, ge=1, le=500)
    fetch_k: int = Field(default=500, ge=1, le=5000)
    lambda_mult: float = Field(default=0.7, ge=0.0, le=1.0)
    rrf_k: int = Field(default=60, ge=1, le=10000)
    rerank_top_n: int = Field(default=24, ge=1, le=500)
    reranker: Literal["cross_encoder", "lexical", "none"] = "cross_encoder"
    cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        min_length=1,
        max_length=500,
    )
    # Initial benchmark integration is retrieval-only. Keeping this a Literal
    # prevents a case from silently acquiring an LLM query-transform dependency.
    query_decomposition: Literal[False] = False
    evidence_record_char_limit: int = Field(default=12000, ge=500, le=100000)
    evidence_total_char_limit: int = Field(default=120000, ge=5000, le=1000000)
    notes: str | None = Field(default=None, max_length=4000)


class ResearchPipelineBenchmarkCase(ResearchPipelineBenchmarkCaseCreate):
    corpus_snapshot: BenchmarkCorpusSnapshot
    created_at: datetime
    created_by: str | None = Field(default=None, max_length=200)


class ResearchPipelineBenchmarkRequest(BaseModel):
    """Execute two immutable pipeline versions against one saved fixed case."""

    case_id: str = Field(min_length=1, max_length=160)
    case_version: int = Field(ge=1)
    left: PipelineVersionRef
    right: PipelineVersionRef


class ResearchPipelineBenchmarkRun(BaseModel):
    """Durable result of one retrieval-only fixed-case benchmark execution."""

    benchmark_run_id: str = Field(min_length=1, max_length=200)
    case_id: str = Field(min_length=1, max_length=160)
    case_version: int = Field(ge=1)
    mode: Literal["retrieval_only"] = "retrieval_only"
    created_at: datetime
    created_by: str | None = Field(default=None, max_length=200)
    case_snapshot: dict[str, Any]
    fixed_input: dict[str, Any]
    corpus: dict[str, Any]
    retrieval_config: dict[str, Any]
    model_config: dict[str, Any]
    left_pipeline: dict[str, Any]
    right_pipeline: dict[str, Any]
    comparison: dict[str, Any]
    reproducibility_warnings: list[str] = Field(default_factory=list)


_COLLECTION_FIELDS = (
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


def _collection_snapshot(row: dict[str, Any]) -> BenchmarkCollectionSnapshot:
    payload = {key: row.get(key) for key in _COLLECTION_FIELDS if key in row}
    return BenchmarkCollectionSnapshot.model_validate(payload)


def benchmark_corpus_snapshot(
    store: Any,
    source_collection: str,
    *,
    locales: list[str] | None = None,
) -> BenchmarkCorpusSnapshot:
    """Capture the source plus relevant derived-language collection manifests."""

    lister = getattr(store, "list_stores", None)
    if not callable(lister):
        raise ValueError("The configured corpus store cannot enumerate collections.")
    rows = [item for item in lister() if isinstance(item, dict)]
    source = next(
        (
            item
            for item in rows
            if str(item.get("name") or "") == str(source_collection)
        ),
        None,
    )
    if source is None:
        # Some lightweight/test stores expose only direct get_store access.
        getter = getattr(store, "get_store", None)
        if callable(getter):
            try:
                candidate = getter(source_collection)
            except Exception:
                candidate = None
            if isinstance(candidate, dict):
                source = candidate
                rows.append(candidate)
    if source is None:
        raise ValueError(f"Collection {source_collection!r} does not exist.")

    requested = {str(value) for value in (locales or ["en", "fr"])}
    selected: dict[str, dict[str, Any]] = {str(source.get("name")): source}
    expected_names = {f"{source_collection}_{locale}" for locale in requested}
    for item in rows:
        name = str(item.get("name") or "")
        if not name or item.get("collection_role") != "language":
            continue
        language_codes = {str(value) for value in item.get("language_codes") or []}
        if requested and language_codes and not (requested & language_codes):
            continue
        if (
            str(item.get("source_collection") or "") == source_collection
            or name in expected_names
        ):
            selected[name] = item

    snapshots = [
        _collection_snapshot(selected[name])
        for name in sorted(selected, key=str.casefold)
    ]
    canonical = json.dumps(
        [row.model_dump(mode="json") for row in snapshots],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    limitations: list[str] = []
    for row in snapshots:
        if not row.source_snapshot_hash:
            limitations.append(
                f"{row.name}: source snapshot hash is unavailable; exact source "
                "content identity cannot be independently verified."
            )
        if not row.build_id:
            limitations.append(
                f"{row.name}: collection build ID is unavailable."
            )
        if not row.embedding_revision:
            limitations.append(
                f"{row.name}: embedding revision is unavailable; reproducibility "
                "is limited to the retained embedding provider/model metadata."
            )

    return BenchmarkCorpusSnapshot(
        fingerprint=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        collections=snapshots,
        limitations=limitations,
    )


def build_research_benchmark_case(
    body: ResearchPipelineBenchmarkCaseCreate,
    *,
    store: Any,
    created_by: str | None,
) -> ResearchPipelineBenchmarkCase:
    """Freeze one benchmark fixture and the collection manifests it depends on."""

    snapshot = benchmark_corpus_snapshot(
        store,
        body.source_collection,
        locales=[str(value) for value in body.locales],
    )
    return ResearchPipelineBenchmarkCase(
        **body.model_dump(mode="python"),
        corpus_snapshot=snapshot,
        created_at=datetime.now(UTC),
        created_by=created_by,
    )


def assert_benchmark_corpus_unchanged(
    case: ResearchPipelineBenchmarkCase,
    *,
    store: Any,
) -> BenchmarkCorpusSnapshot:
    """Reject execution when the fixed case's collection/index identity drifted."""

    current = benchmark_corpus_snapshot(
        store,
        case.source_collection,
        locales=[str(value) for value in case.locales],
    )
    if current.fingerprint != case.corpus_snapshot.fingerprint:
        raise ValueError(
            "Benchmark corpus/index drift detected. "
            f"Case {case.case_id}@{case.version} expects "
            f"{case.corpus_snapshot.fingerprint[:12]}, but the current manifest is "
            f"{current.fingerprint[:12]}. Create a new benchmark case version for "
            "the changed corpus/index."
        )
    return current


def benchmark_request_for_case(
    case: ResearchPipelineBenchmarkCase,
    *,
    pipeline_id: str,
    pipeline_version: int,
) -> RAGRunRequest:
    """Compile a saved fixed case into the ordinary non-persistent RAG request."""

    return RAGRunRequest(
        prompt=case.prompt,
        instructions=case.instructions,
        pipeline_id=pipeline_id,
        pipeline_version=pipeline_version,
        source_collection=case.source_collection,
        locales=case.locales,
        search_types=case.search_types,
        k=case.k,
        fetch_k=case.fetch_k,
        lambda_mult=case.lambda_mult,
        rrf_k=case.rrf_k,
        rerank_top_n=case.rerank_top_n,
        reranker=case.reranker,
        cross_encoder_model=case.cross_encoder_model,
        query_decomposition=False,
        evidence_record_char_limit=case.evidence_record_char_limit,
        evidence_total_char_limit=case.evidence_total_char_limit,
        auto_grade=False,
        use_prior_response_memory=False,
        use_prior_claim_memory=False,
    )


def _pipeline_identity(raw_result: dict[str, Any]) -> dict[str, Any]:
    pipeline = (
        raw_result.get("pipeline")
        if isinstance(raw_result.get("pipeline"), dict)
        else {}
    )
    return {
        key: pipeline.get(key)
        for key in (
            "pipeline_id",
            "pipeline_version",
            "pipeline_hash",
            "name",
            "purpose",
            "resolved_pipeline",
        )
    }


def _reranker_environment(raw_result: dict[str, Any]) -> dict[str, Any]:
    for stage in raw_result.get("stages") or []:
        if not isinstance(stage, dict) or stage.get("name") != "rerank":
            continue
        detail = (
            stage.get("detail")
            if isinstance(stage.get("detail"), dict)
            else {}
        )
        telemetry = (
            detail.get("reranker_telemetry")
            if isinstance(detail.get("reranker_telemetry"), dict)
            else {}
        )
        return {
            "requested_mode": detail.get("requested_mode"),
            "effective_mode": detail.get("mode"),
            "provider": telemetry.get("provider"),
            "model": detail.get("cross_encoder_model") or telemetry.get("model"),
            "model_revision": telemetry.get("model_revision"),
            "library_version": telemetry.get("library_version"),
            "fallback_reason": telemetry.get("fallback_reason"),
        }
    return {}


def build_research_benchmark_run(
    case: ResearchPipelineBenchmarkCase,
    comparison: dict[str, Any],
    *,
    left_result: dict[str, Any],
    right_result: dict[str, Any],
    created_by: str | None,
) -> ResearchPipelineBenchmarkRun:
    """Construct the bounded durable record for a completed fixed-case comparison."""

    left_pipeline = _pipeline_identity(left_result)
    right_pipeline = _pipeline_identity(right_result)
    left_reranker = _reranker_environment(left_result)
    right_reranker = _reranker_environment(right_result)

    warnings = list(case.corpus_snapshot.limitations)
    for label, pipeline in (
        ("Pipeline A", left_pipeline),
        ("Pipeline B", right_pipeline),
    ):
        if not pipeline.get("pipeline_hash"):
            warnings.append(f"{label} did not report an immutable pipeline hash.")
        if not pipeline.get("resolved_pipeline"):
            warnings.append(
                f"{label} did not report its resolved immutable pipeline snapshot."
            )
    for label, reranker in (
        ("Pipeline A", left_reranker),
        ("Pipeline B", right_reranker),
    ):
        if reranker.get("model") and not reranker.get("model_revision"):
            warnings.append(
                f"{label}: CrossEncoder model revision is unavailable; the "
                "configured model identifier and library version are retained."
            )

    return ResearchPipelineBenchmarkRun(
        benchmark_run_id=f"benchmark-{uuid4().hex}",
        case_id=case.case_id,
        case_version=case.version,
        created_at=datetime.now(UTC),
        created_by=created_by,
        case_snapshot=case.model_dump(mode="json"),
        fixed_input={
            "prompt": case.prompt,
            "instructions": case.instructions,
            "source_collection": case.source_collection,
        },
        corpus=case.corpus_snapshot.model_dump(mode="json"),
        retrieval_config={
            "locales": case.locales,
            "search_types": case.search_types,
            "k": case.k,
            "fetch_k": case.fetch_k,
            "lambda_mult": case.lambda_mult,
            "rrf_k": case.rrf_k,
            "rerank_top_n": case.rerank_top_n,
            "reranker": case.reranker,
            "query_decomposition": False,
            "evidence_record_char_limit": case.evidence_record_char_limit,
            "evidence_total_char_limit": case.evidence_total_char_limit,
        },
        model_config={
            "query_transform_model": None,
            "generation_model": None,
            "grader_model": None,
            "cross_encoder_model": case.cross_encoder_model,
            "left_reranker": left_reranker,
            "right_reranker": right_reranker,
        },
        left_pipeline=left_pipeline,
        right_pipeline=right_pipeline,
        comparison=comparison,
        reproducibility_warnings=list(dict.fromkeys(warnings)),
    )
