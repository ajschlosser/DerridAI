# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
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
        self.build_id = "build-123"
        self.embedding_revision = "rev-7"

    def list_stores(self):
        return [
            {
                "name": "corpus",
                "storage_name": "corpus",
                "count": 12,
                "manifest_version": 2,
                "embedding_provider": "ollama",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
                "embedding_revision": self.embedding_revision,
                "distance_metric": "cosine",
                "retrieval_mode": "hybrid",
                "status": "ready",
                "build_id": self.build_id,
                "source_snapshot_hash": "source-hash",
                "app_version": "0.80.7",
                "collection_role": "general",
                "language_codes": ["en"],
                "metadata": {"must_not_persist": "arbitrary metadata"},
            }
        ]


def _case(store: _BenchmarkStore | None = None):
    return build_research_benchmark_case(
        ResearchPipelineBenchmarkCaseCreate(
            case_id="trace-question",
            version=3,
            prompt="What is the trace?",
            instructions="Use only the fixed benchmark corpus.",
            source_collection="corpus",
            locales=["en"],
            search_types=["similarity", "lexical"],
            k=32,
            fetch_k=200,
            rerank_top_n=20,
            reranker="cross_encoder",
            cross_encoder_model="cross-encoder/test-model",
            query_decomposition=False,
            notes="Fixed retrieval case",
        ),
        store=store or _BenchmarkStore(),
        created_by="admin",
    )


def _raw_result(pipeline_id: str) -> dict:
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
                "stages": [],
            },
        },
        "stages": [
            {
                "name": "rerank",
                "detail": {
                    "requested_mode": "cross_encoder",
                    "mode": "cross_encoder",
                    "cross_encoder_model": "cross-encoder/test-model",
                    "reranker_telemetry": {
                        "provider": "sentence-transformers",
                        "model": "cross-encoder/test-model",
                        "model_revision": "model-rev-1",
                        "library_version": "5.0.0",
                    },
                },
            }
        ],
    }


def _comparison() -> dict:
    return {
        "non_persistent": True,
        "left": {
            "pipeline": {
                "pipeline_id": "research.current",
                "pipeline_version": 1,
                "pipeline_hash": "hash-research.current",
            }
        },
        "right": {
            "pipeline": {
                "pipeline_id": "research.balanced",
                "pipeline_version": 1,
                "pipeline_hash": "hash-research.balanced",
            }
        },
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


def _run(case):
    return build_research_benchmark_run(
        case,
        _comparison(),
        left_result=_raw_result("research.current"),
        right_result=_raw_result("research.balanced"),
        created_by="admin",
    )


def test_benchmark_case_freezes_corpus_identity_and_request_controls() -> None:
    case = _case()

    assert case.case_id == "trace-question"
    assert case.version == 3
    assert case.corpus_snapshot.collections[0].source_snapshot_hash == "source-hash"
    assert case.corpus_snapshot.collections[0].embedding_revision == "rev-7"
    assert case.k == 32
    assert case.cross_encoder_model == "cross-encoder/test-model"

    serialized = case.model_dump_json()
    assert "must_not_persist" not in serialized

    request = benchmark_request_for_case(
        case,
        pipeline_id="research.current",
        pipeline_version=1,
    )
    assert request.prompt == "What is the trace?"
    assert request.k == 32
    assert request.query_decomposition is False
    assert request.auto_grade is False
    assert request.use_prior_response_memory is False
    assert request.use_prior_claim_memory is False


def test_benchmark_run_captures_exact_pipeline_and_reranker_identity() -> None:
    run = _run(_case())

    assert run.case_id == "trace-question"
    assert run.case_version == 3
    assert run.fixed_input["prompt"] == "What is the trace?"
    assert run.retrieval_config["k"] == 32
    assert run.model_config["cross_encoder_model"] == "cross-encoder/test-model"
    assert run.model_config["left_reranker"]["model_revision"] == "model-rev-1"
    assert run.left_pipeline["pipeline_hash"] == "hash-research.current"
    assert run.right_pipeline["pipeline_hash"] == "hash-research.balanced"
    assert run.left_pipeline["resolved_pipeline"]["pipeline_id"] == "research.current"
    assert run.reproducibility_warnings == []


def test_benchmark_rejects_corpus_or_index_drift() -> None:
    store = _BenchmarkStore()
    case = _case(store)

    store.build_id = "build-456"
    with pytest.raises(BenchmarkCorpusDriftError, match="drift"):
        assert_benchmark_corpus_unchanged(case, store=store)


def test_pipeline_store_persists_cases_runs_and_backup(tmp_path) -> None:
    case = _case()
    run = _run(case)

    first = PipelineStore(tmp_path / "first.sqlite3")
    first.put_benchmark_case(case)
    first.put_benchmark(run)

    restored_case = first.get_benchmark_case("trace-question", 3)
    assert restored_case is not None
    assert restored_case.corpus_snapshot.fingerprint == case.corpus_snapshot.fingerprint

    restored_run = first.get_benchmark(run.benchmark_run_id)
    assert restored_run is not None
    assert restored_run.case_id == "trace-question"
    assert (
        first.list_benchmarks(case_id="trace-question")[0].benchmark_run_id
        == run.benchmark_run_id
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


def test_benchmark_surfaces_missing_revision_metadata() -> None:
    class _SparseStore:
        def list_stores(self):
            return [
                {
                    "name": "corpus",
                    "count": 12,
                    "collection_role": "general",
                    "language_codes": ["en"],
                }
            ]

    case = build_research_benchmark_case(
        ResearchPipelineBenchmarkCaseCreate(
            case_id="sparse",
            prompt="What is the trace?",
            source_collection="corpus",
            locales=["en"],
        ),
        store=_SparseStore(),
        created_by="admin",
    )

    assert len(case.corpus_snapshot.limitations) == 3
    assert any(
        "source snapshot hash" in item
        for item in case.corpus_snapshot.limitations
    )
    assert any("build ID" in item for item in case.corpus_snapshot.limitations)
    assert any(
        "embedding revision" in item
        for item in case.corpus_snapshot.limitations
    )
