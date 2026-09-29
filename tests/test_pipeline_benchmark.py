# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.models import RAGRunRequest
from app.pipelines.benchmark import (
    ResearchPipelineBenchmarkRequest,
    build_research_benchmark_run,
)
from app.pipelines.store import PipelineStore


class _BenchmarkStore:
    def get_store(self, name: str):
        assert name == "corpus"
        return {
            "name": "corpus",
            "storage_name": "corpus",
            "count": 12,
            "manifest_version": 2,
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
            "embedding_dimension": 768,
            "embedding_revision": "rev-7",
            "distance_metric": "cosine",
            "retrieval_mode": "hybrid",
            "status": "ready",
            "build_id": "build-123",
            "source_snapshot_hash": "source-hash",
            "app_version": "0.80.7",
            "metadata": {"must_not_persist": "arbitrary metadata"},
        }


def _side(pipeline_id: str) -> dict:
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


def _comparison() -> dict:
    return {
        "non_persistent": True,
        "left": _side("research.current"),
        "right": _side("research.balanced"),
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


def _request() -> ResearchPipelineBenchmarkRequest:
    return ResearchPipelineBenchmarkRequest(
        case_id="trace-question",
        case_version=3,
        notes="Fixed retrieval case",
        request=RAGRunRequest(
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
            provider="openai",
            model="generation-model",
            base_url="https://private.example.test/v1",
            api_key="super-secret-key",
            provider_profile_id="profile-1",
        ),
        left={"pipeline_id": "research.current", "version": 1},
        right={"pipeline_id": "research.balanced", "version": 1},
    )


def test_benchmark_record_captures_reproducibility_without_secrets() -> None:
    run = build_research_benchmark_run(
        _request(),
        _comparison(),
        store=_BenchmarkStore(),
        created_by="admin",
    )

    assert run.case_id == "trace-question"
    assert run.case_version == 3
    assert run.fixed_input["prompt"] == "What is the trace?"
    assert run.corpus["source_snapshot_hash"] == "source-hash"
    assert run.corpus["embedding_revision"] == "rev-7"
    assert run.retrieval_config["k"] == 32
    assert run.model_config["cross_encoder_model"] == "cross-encoder/test-model"
    assert run.left_pipeline["pipeline_hash"] == "hash-research.current"
    assert run.right_pipeline["pipeline_hash"] == "hash-research.balanced"
    assert run.reproducibility_warnings == []

    serialized = run.model_dump_json()
    assert "super-secret-key" not in serialized
    assert "private.example.test" not in serialized
    assert "must_not_persist" not in serialized


def test_pipeline_store_persists_and_backs_up_benchmarks(tmp_path) -> None:
    run = build_research_benchmark_run(
        _request(),
        _comparison(),
        store=_BenchmarkStore(),
        created_by="admin",
    )
    first = PipelineStore(tmp_path / "first.sqlite3")
    first.put_benchmark(run)

    restored = first.get_benchmark(run.benchmark_run_id)
    assert restored is not None
    assert restored.case_id == "trace-question"
    assert first.list_benchmarks(case_id="trace-question")[0].benchmark_run_id == run.benchmark_run_id

    snapshot = first.snapshot()
    assert len(snapshot["benchmark_runs"]) == 1

    second = PipelineStore(tmp_path / "second.sqlite3")
    second.restore_snapshot(snapshot)
    copied = second.get_benchmark(run.benchmark_run_id)
    assert copied is not None
    assert copied.left_pipeline["pipeline_hash"] == "hash-research.current"


def test_benchmark_surfaces_missing_revision_metadata() -> None:
    class _SparseStore:
        def list_stores(self):
            return [{"name": "corpus", "count": 12}]

    run = build_research_benchmark_run(
        _request(),
        _comparison(),
        store=_SparseStore(),
        created_by="admin",
    )

    assert len(run.reproducibility_warnings) == 3
    assert any("source snapshot hash" in item for item in run.reproducibility_warnings)
    assert any("build ID" in item for item in run.reproducibility_warnings)
    assert any("embedding revision" in item for item in run.reproducibility_warnings)
