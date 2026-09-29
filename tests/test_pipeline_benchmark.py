# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.pipelines.benchmark import (
    BenchmarkCorpusDriftError,
    ResearchPipelineBenchmarkCaseCreate,
    assert_benchmark_corpus_unchanged,
    benchmark_request_for_case,
    build_research_benchmark_case,
    build_research_benchmark_run,
)
from app.pipelines.store import PipelineStore


class _BenchmarkStore:
    def __init__(self) -> None:
        self.source_hash = "source-hash"
        self.source_count = 12

    def list_stores(self):
        return [
            {
                "name": "corpus",
                "storage_name": "corpus",
                "count": self.source_count,
                "manifest_version": 2,
                "embedding_provider": "ollama",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
                "embedding_revision": "embed-rev-7",
                "distance_metric": "cosine",
                "retrieval_mode": "hybrid",
                "status": "ready",
                "build_id": "build-123",
                "source_snapshot_hash": self.source_hash,
                "app_version": "0.80.7",
                "collection_role": "primary",
                "metadata": {"must_not_persist": "arbitrary metadata"},
            },
            {
                "name": "corpus_fr",
                "storage_name": "corpus_fr",
                "count": 8,
                "manifest_version": 2,
                "embedding_provider": "ollama",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
                "embedding_revision": "embed-rev-7",
                "distance_metric": "cosine",
                "retrieval_mode": "semantic",
                "status": "ready",
                "build_id": "build-fr",
                "source_snapshot_hash": "source-fr-hash",
                "app_version": "0.80.7",
                "collection_role": "language",
                "source_collection": "corpus",
                "language_codes": ["fr"],
            },
            {
                "name": "other",
                "count": 3,
                "collection_role": "general",
            },
        ]


def _case_create() -> ResearchPipelineBenchmarkCaseCreate:
    return ResearchPipelineBenchmarkCaseCreate(
        case_id="trace-question",
        version=3,
        prompt="What is the trace?",
        instructions="Use only the fixed benchmark corpus.",
        source_collection="corpus",
        locales=["en", "fr"],
        search_types=["similarity", "lexical"],
        k=32,
        fetch_k=200,
        rerank_top_n=20,
        reranker="cross_encoder",
        cross_encoder_model="cross-encoder/test-model",
        notes="Fixed retrieval case",
    )


def _raw_side(pipeline_id: str) -> dict:
    return {
        "pipeline": {
            "pipeline_id": pipeline_id,
            "pipeline_version": 1,
            "pipeline_hash": f"hash-{pipeline_id}",
            "name": pipeline_id,
            "purpose": "research",
            "resolved_pipeline": {
                "pipeline_id": pipeline_id,
                "version": 1,
                "stages": [{"id": "retrieve", "strategy": "retrieve.lexical_bm25"}],
            },
        },
        "elapsed_seconds": 0.2,
        "warnings": [],
        "retrieval": {"cross_encoder_calls": 1},
        "diagnostics": {
            "candidate_retention": "complete_for_comparison",
            "pre_rerank": [],
            "post_rerank": [],
            "post_selection": [],
            "context_characters": 1000,
        },
        "evidence": [
            {
                "record": {
                    "record_id": "r1",
                    "text": "source text must not enter the benchmark record",
                },
                "collection": "corpus",
            }
        ],
        "stages": [
            {
                "name": "rerank",
                "seconds": 0.1,
                "detail": {
                    "mode": "cross_encoder",
                    "requested_mode": "cross_encoder",
                    "cross_encoder_model": "cross-encoder/test-model",
                    "reranker_telemetry": {
                        "provider": "sentence-transformers",
                        "model": "cross-encoder/test-model",
                        "library_version": "5.0.0",
                    },
                },
            }
        ],
    }


def _comparison() -> dict:
    def side(pipeline_id: str) -> dict:
        return {
            "pipeline": {
                "pipeline_id": pipeline_id,
                "pipeline_version": 1,
                "pipeline_hash": f"hash-{pipeline_id}",
                "name": pipeline_id,
                "purpose": "research",
            },
            "elapsed_seconds": 0.2,
            "warnings": [],
            "retrieval": {"cross_encoder_calls": 1},
            "candidate_retention": "complete_for_comparison",
            "candidates": {},
            "context_characters": 1000,
            "resource_use": {
                "query_transform_model_calls": 0,
                "cross_encoder_calls": 1,
            },
            "evidence": [{"record_id": "r1", "rank": 1}],
            "stages": [],
        }

    return {
        "non_persistent": True,
        "left": side("research.current"),
        "right": side("research.balanced"),
        "comparison": {
            "shared_record_ids": ["r1"],
            "left_only_record_ids": [],
            "right_only_record_ids": [],
            "shared_count": 1,
            "union_count": 1,
            "jaccard_overlap": 1.0,
            "candidate_overlap": {"jaccard_overlap": 1.0},
            "post_rerank_overlap": {"jaccard_overlap": 1.0},
            "rank_changes": [],
        },
    }


def test_fixed_case_captures_source_and_relevant_language_indexes() -> None:
    case = build_research_benchmark_case(
        _case_create(),
        store=_BenchmarkStore(),
        created_by="admin",
    )

    assert case.case_id == "trace-question"
    assert case.version == 3
    assert case.query_decomposition is False
    assert len(case.corpus_snapshot.fingerprint) == 64
    assert [item.name for item in case.corpus_snapshot.collections] == [
        "corpus",
        "corpus_fr",
    ]
    assert case.corpus_snapshot.collections[0].embedding_revision == "embed-rev-7"
    assert "must_not_persist" not in case.model_dump_json()


def test_fixed_case_rejects_query_decomposition() -> None:
    payload = _case_create().model_dump(mode="python")
    payload["query_decomposition"] = True
    with pytest.raises(ValidationError):
        ResearchPipelineBenchmarkCaseCreate.model_validate(payload)


def test_fixed_case_detects_corpus_or_index_drift() -> None:
    store = _BenchmarkStore()
    case = build_research_benchmark_case(
        _case_create(),
        store=store,
        created_by="admin",
    )
    assert_benchmark_corpus_unchanged(case, store=store)

    store.source_hash = "changed-source"
    with pytest.raises(BenchmarkCorpusDriftError, match="drift detected"):
        assert_benchmark_corpus_unchanged(case, store=store)


def test_case_compiles_to_non_generating_non_memory_request() -> None:
    case = build_research_benchmark_case(
        _case_create(),
        store=_BenchmarkStore(),
        created_by="admin",
    )
    request = benchmark_request_for_case(
        case,
        pipeline_id="research.current",
        pipeline_version=1,
    )

    assert request.prompt == "What is the trace?"
    assert request.query_decomposition is False
    assert request.auto_grade is False
    assert request.use_prior_response_memory is False
    assert request.use_prior_claim_memory is False
    assert request.pipeline_id == "research.current"
    assert request.pipeline_version == 1


def test_benchmark_record_retains_exact_pipeline_snapshot_without_source_text() -> None:
    case = build_research_benchmark_case(
        _case_create(),
        store=_BenchmarkStore(),
        created_by="admin",
    )
    run = build_research_benchmark_run(
        case,
        _comparison(),
        left_result=_raw_side("research.current"),
        right_result=_raw_side("research.balanced"),
        created_by="admin",
    )

    assert run.case_snapshot["corpus_snapshot"]["fingerprint"] == (
        case.corpus_snapshot.fingerprint
    )
    assert run.left_pipeline["pipeline_hash"] == "hash-research.current"
    assert run.left_pipeline["resolved_pipeline"]["pipeline_id"] == "research.current"
    assert run.right_pipeline["pipeline_hash"] == "hash-research.balanced"
    assert run.model_config["generation_model"] is None
    assert run.model_config["grader_model"] is None
    assert run.model_config["left_reranker"]["library_version"] == "5.0.0"
    assert any(
        "CrossEncoder model revision is unavailable" in item
        for item in run.reproducibility_warnings
    )
    serialized = run.model_dump_json()
    assert "source text must not enter" not in serialized
    assert "must_not_persist" not in serialized


def test_pipeline_store_versions_cases_immutably_and_backs_up_runs(tmp_path) -> None:
    case = build_research_benchmark_case(
        _case_create(),
        store=_BenchmarkStore(),
        created_by="admin",
    )
    first = PipelineStore(tmp_path / "first.sqlite3")
    first.put_benchmark_case(case)

    with pytest.raises(ValueError, match="already exists"):
        first.put_benchmark_case(case)

    restored_case = first.get_benchmark_case("trace-question", 3)
    assert restored_case is not None
    assert restored_case.corpus_snapshot.fingerprint == case.corpus_snapshot.fingerprint

    run = build_research_benchmark_run(
        case,
        _comparison(),
        left_result=_raw_side("research.current"),
        right_result=_raw_side("research.balanced"),
        created_by="admin",
    )
    first.put_benchmark(run)
    assert first.list_benchmarks(case_id="trace-question")[0].benchmark_run_id == (
        run.benchmark_run_id
    )

    snapshot = first.snapshot()
    assert len(snapshot["benchmark_cases"]) == 1
    assert len(snapshot["benchmark_runs"]) == 1

    second = PipelineStore(tmp_path / "second.sqlite3")
    second.restore_snapshot(snapshot)
    copied_case = second.get_benchmark_case("trace-question", 3)
    copied_run = second.get_benchmark(run.benchmark_run_id)
    assert copied_case is not None
    assert copied_run is not None
    assert copied_run.left_pipeline["pipeline_hash"] == "hash-research.current"


def test_backup_rejects_benchmark_run_without_case(tmp_path) -> None:
    case = build_research_benchmark_case(
        _case_create(),
        store=_BenchmarkStore(),
        created_by="admin",
    )
    run = build_research_benchmark_run(
        case,
        _comparison(),
        left_result=_raw_side("research.current"),
        right_result=_raw_side("research.balanced"),
        created_by="admin",
    )
    store = PipelineStore(tmp_path / "system.sqlite3")
    payload = store.snapshot()
    payload["benchmark_runs"] = [run.model_dump(mode="json")]

    with pytest.raises(ValueError, match="unknown fixed case"):
        store.restore_snapshot(payload)
