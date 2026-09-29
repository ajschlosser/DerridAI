# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.models import RAGRunRequest
from app.pipelines.benchmark import (
    ResearchBenchmarkCaseCreate,
    build_case,
    build_run,
    collection_snapshot,
    verify_collection_snapshot,
)
from app.pipelines.store import PipelineStore


class _CollectionStore:
    def __init__(self, *, source_hash: str | None = "source-sha", revision: str | None = "emb-v1"):
        self.source_hash = source_hash
        self.revision = revision

    def get_store(self, name: str):
        assert name == "corpus"
        return {
            "name": "corpus",
            "count": 12,
            "embedding_provider": "ollama",
            "embedding_model": "bge-m3",
            "embedding_dimension": 1024,
            "embedding_revision": self.revision,
            "distance_metric": "cosine",
            "retrieval_mode": "hybrid",
            "text_field": "text",
            "filter_fields": ["work", "language"],
            "build_id": "build-1",
            "source_record_count": 12,
            "source_snapshot_hash": self.source_hash,
            "app_version": "0.80.7",
        }


def _create_body() -> ResearchBenchmarkCaseCreate:
    return ResearchBenchmarkCaseCreate(
        benchmark_id="trace-fixed",
        name="Trace retrieval fixture",
        request=RAGRunRequest(
            prompt="What is the trace?",
            source_collection="corpus",
            query_decomposition=True,
            provider="openai",
            model="generation-model",
            base_url="https://provider.example/v1",
            api_key="must-not-persist",
            provider_profile_id="profile-1",
            use_prior_response_memory=True,
            use_prior_claim_memory=True,
            auto_grade=True,
            auto_grade_api_key="must-not-persist-either",
        ),
        notes="Fixed retrieval case.",
    )


def test_benchmark_case_normalizes_to_retrieval_only_and_captures_revision() -> None:
    case = build_case(
        _create_body(),
        version=1,
        created_by="admin",
        store=_CollectionStore(),
    )

    assert case.benchmark_id == "trace-fixed"
    assert case.version == 1
    assert case.request["source_collection"] == "corpus"
    assert case.request["query_decomposition"] is False
    assert case.request["use_prior_response_memory"] is False
    assert case.request["use_prior_claim_memory"] is False
    assert case.request["auto_grade"] is False
    assert case.request["api_key"] is None
    assert case.request["base_url"] is None
    assert case.request["provider_profile_id"] is None
    assert case.collection_snapshot["source_snapshot_hash"] == "source-sha"
    assert case.collection_snapshot["embedding_revision"] == "emb-v1"
    assert case.reproducibility_warnings == []


def test_benchmark_case_rejects_selected_evidence() -> None:
    body = _create_body()
    body.request.selected_evidence = [
        {
            "collection": "corpus",
            "chroma_id": "row-1",
            "record_id": "r1",
        }
    ]

    with pytest.raises(ValueError, match="cannot pin selected evidence"):
        build_case(
            body,
            version=1,
            created_by="admin",
            store=_CollectionStore(),
        )


def test_benchmark_store_versions_cases_and_persists_runs(tmp_path) -> None:
    store = PipelineStore(tmp_path / "pipeline.sqlite3")
    source = _CollectionStore()

    assert store.next_benchmark_case_version("trace-fixed") == 1
    case = build_case(
        _create_body(),
        version=1,
        created_by="admin",
        store=source,
    )
    store.put_benchmark_case(case)
    assert store.next_benchmark_case_version("trace-fixed") == 2
    assert store.get_benchmark_case("trace-fixed", 1) == case

    comparison = {
        "non_persistent": True,
        "left": {"pipeline": {"pipeline_id": "research.current", "pipeline_hash": "a"}},
        "right": {"pipeline": {"pipeline_id": "research.balanced", "pipeline_hash": "b"}},
        "comparison": {"jaccard_overlap": 0.5},
    }
    snapshot = collection_snapshot(source, "corpus")
    run = build_run(
        case,
        owner="admin",
        current_snapshot=snapshot,
        comparison=comparison,
    )
    store.put_benchmark_run(run)

    saved = store.get_benchmark_run(run.benchmark_run_id)
    assert saved is not None
    assert saved.benchmark_id == "trace-fixed"
    assert saved.comparison["comparison"]["jaccard_overlap"] == 0.5
    assert store.list_benchmark_runs(benchmark_id="trace-fixed")[0].benchmark_run_id == run.benchmark_run_id
    assert store.list_runs() == []


def test_benchmark_rejects_known_collection_drift_and_discloses_missing_revisions() -> None:
    expected = collection_snapshot(_CollectionStore(), "corpus")
    changed = dict(expected)
    changed["source_snapshot_hash"] = "different"

    with pytest.raises(ValueError, match="source_snapshot_hash"):
        verify_collection_snapshot(expected, changed)

    missing = collection_snapshot(
        _CollectionStore(source_hash=None, revision=None),
        "corpus",
    )
    warnings = verify_collection_snapshot(missing, missing)
    assert len(warnings) == 2
    assert "source snapshot hash" in warnings[0]
    assert "embedding revision" in warnings[1]


def test_pipeline_backup_round_trips_benchmark_state(tmp_path) -> None:
    store = PipelineStore(tmp_path / "pipeline.sqlite3")
    case = build_case(
        _create_body(),
        version=1,
        created_by="admin",
        store=_CollectionStore(),
    )
    store.put_benchmark_case(case)
    run = build_run(
        case,
        owner="admin",
        current_snapshot=case.collection_snapshot,
        comparison={"non_persistent": True, "left": {}, "right": {}, "comparison": {}},
    )
    store.put_benchmark_run(run)

    snapshot = store.snapshot()
    restored = PipelineStore(tmp_path / "restored.sqlite3")
    restored.restore_snapshot(snapshot)

    assert restored.get_benchmark_case(case.benchmark_id, case.version) == case
    saved_run = restored.get_benchmark_run(run.benchmark_run_id)
    assert saved_run is not None
    assert saved_run.case == case
