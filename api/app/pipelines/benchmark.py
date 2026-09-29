# Copyright 2026 Aaron John Schlosser, PhD.
"""Fixed-case Research pipeline benchmarks built on retrieval dry runs.

Benchmark cases pin a normalized retrieval request and the available Chroma
collection revision metadata. Benchmark runs persist the descriptive comparison
result separately from ordinary Research jobs and pipeline execution traces.
They never create scholarly authority or a pipeline "winner".
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ..config import APP_GIT_COMMIT, APP_VERSION
from ..models import RAGRunRequest
from .comparison import PipelineVersionRef


class ResearchBenchmarkCaseCreate(BaseModel):
    benchmark_id: str = Field(
        min_length=2,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    name: str = Field(min_length=1, max_length=200)
    request: RAGRunRequest
    notes: str | None = Field(default=None, max_length=4000)


class ResearchBenchmarkCase(BaseModel):
    benchmark_id: str
    version: int = Field(ge=1)
    name: str
    request: dict[str, Any]
    collection_snapshot: dict[str, Any]
    reproducibility_warnings: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime
    created_by: str


class ResearchBenchmarkRunRequest(BaseModel):
    benchmark_id: str = Field(min_length=2, max_length=80)
    benchmark_version: int | None = Field(default=None, ge=1)
    left: PipelineVersionRef
    right: PipelineVersionRef


class ResearchBenchmarkRun(BaseModel):
    benchmark_run_id: str
    benchmark_id: str
    benchmark_version: int
    case: ResearchBenchmarkCase
    owner: str
    created_at: datetime
    app_version: str
    git_commit: str
    collection_snapshot: dict[str, Any]
    reproducibility_warnings: list[str] = Field(default_factory=list)
    comparison: dict[str, Any]


def normalize_benchmark_request(request: RAGRunRequest) -> RAGRunRequest:
    """Return a safe retrieval-only request suitable for durable benchmark cases."""

    if request.skip_retrieval:
        raise ValueError("Research benchmark cases require retrieval.")
    if not str(request.source_collection or "").strip():
        raise ValueError("Research benchmark cases require a source collection.")
    if request.selected_evidence:
        raise ValueError(
            "Retrieval benchmark cases cannot pin selected evidence; use the fixed corpus instead."
        )

    payload = request.model_dump(mode="python")
    payload.update(
        {
            "pipeline_id": None,
            "pipeline_version": None,
            "query_decomposition": False,
            "use_prior_response_memory": False,
            "use_prior_claim_memory": False,
            "memory_profile_id": None,
            "auto_grade": False,
            # Generation/provider values are irrelevant because benchmark
            # execution stops after context packing. Do not persist credentials
            # or endpoint/profile details in benchmark cases.
            "provider": "ollama",
            "model": None,
            "base_url": None,
            "api_key": None,
            "provider_profile_id": None,
            "generation": None,
            "auto_grade_provider": None,
            "auto_grade_model": None,
            "auto_grade_base_url": None,
            "auto_grade_api_key": None,
            "auto_grade_provider_profile_id": None,
            "auto_grade_generation": None,
        }
    )
    return RAGRunRequest.model_validate(payload)


_COLLECTION_SNAPSHOT_KEYS = (
    "name",
    "count",
    "embedding_provider",
    "embedding_model",
    "embedding_dimension",
    "embedding_revision",
    "distance_metric",
    "retrieval_mode",
    "text_field",
    "filter_fields",
    "build_id",
    "source_record_count",
    "source_snapshot_hash",
    "app_version",
)


def collection_snapshot(store: Any, collection_name: str) -> dict[str, Any]:
    """Capture the available immutable/search-contract identity of one collection."""

    info = store.get_store(collection_name)
    return {key: info.get(key) for key in _COLLECTION_SNAPSHOT_KEYS}


def reproducibility_warnings(snapshot: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not snapshot.get("source_snapshot_hash"):
        warnings.append(
            "This collection does not expose a source snapshot hash; source-content identity "
            "cannot be verified beyond the stored build/count metadata."
        )
    if not snapshot.get("embedding_revision"):
        warnings.append(
            "This collection does not expose an immutable embedding revision; the embedding "
            "provider/model contract is recorded, but exact vector revision cannot be verified."
        )
    return warnings


_DRIFT_KEYS = (
    "name",
    "count",
    "embedding_provider",
    "embedding_model",
    "embedding_dimension",
    "embedding_revision",
    "distance_metric",
    "retrieval_mode",
    "text_field",
    "filter_fields",
    "build_id",
    "source_record_count",
    "source_snapshot_hash",
)


def verify_collection_snapshot(
    expected: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Reject known collection drift and report unverifiable revision dimensions."""

    changed: list[str] = []
    for key in _DRIFT_KEYS:
        before = expected.get(key)
        after = current.get(key)
        if before in (None, "", []):
            continue
        if before != after:
            changed.append(key)
    if changed:
        raise ValueError(
            "The benchmark corpus/index has changed since this case was saved: "
            + ", ".join(changed)
            + ". Save a new benchmark-case version."
        )
    return reproducibility_warnings(expected)


def build_case(
    body: ResearchBenchmarkCaseCreate,
    *,
    version: int,
    created_by: str,
    store: Any,
) -> ResearchBenchmarkCase:
    request = normalize_benchmark_request(body.request)
    snapshot = collection_snapshot(store, request.source_collection)
    return ResearchBenchmarkCase(
        benchmark_id=body.benchmark_id,
        version=version,
        name=body.name,
        request=request.model_dump(mode="json"),
        collection_snapshot=snapshot,
        reproducibility_warnings=reproducibility_warnings(snapshot),
        notes=body.notes,
        created_at=datetime.now(UTC),
        created_by=created_by,
    )


def build_run(
    case: ResearchBenchmarkCase,
    *,
    owner: str,
    current_snapshot: dict[str, Any],
    comparison: dict[str, Any],
) -> ResearchBenchmarkRun:
    warnings = verify_collection_snapshot(case.collection_snapshot, current_snapshot)
    return ResearchBenchmarkRun(
        benchmark_run_id=f"benchmark-{uuid4().hex}",
        benchmark_id=case.benchmark_id,
        benchmark_version=case.version,
        case=case,
        owner=owner,
        created_at=datetime.now(UTC),
        app_version=APP_VERSION,
        git_commit=APP_GIT_COMMIT,
        collection_snapshot=current_snapshot,
        reproducibility_warnings=warnings,
        comparison=comparison,
    )
