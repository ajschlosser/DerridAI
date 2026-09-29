# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.models import RAGRunRequest
from app.pipelines.comparison import (
    ResearchPipelineBenchmarkCase,
    ResearchPipelineBenchmarkRequest,
    PipelineVersionRef,
    aggregate_research_benchmark,
    benchmark_case_result,
    compare_research_dry_runs,
    expected_record_coverage,
)
from app.rag import run_rag_pipeline


def _result(pipeline_id: str, ids: list[str], *, elapsed: float = 0.1):
    return {
        "pipeline": {
            "pipeline_id": pipeline_id,
            "pipeline_version": 1,
            "pipeline_hash": f"hash-{pipeline_id}",
            "name": pipeline_id,
            "purpose": "research",
        },
        "elapsed_seconds": elapsed,
        "warnings": [],
        "retrieval": {
            "raw_count": len(ids),
            "reranked_count": len(ids),
            "query_decomposition": False,
        },
        "diagnostics": {
            "candidate_retention": "complete_for_comparison",
            "pre_rerank": [
                {
                    "record_id": record_id,
                    "rank": rank,
                    "relevance": 1.0 - (rank / 20),
                    "rrf_score": 1 / (60 + rank),
                    "rerank_score": None,
                    "retrieval_hits": [{"search_type": "lexical", "rank": rank}],
                }
                for rank, record_id in enumerate(ids, start=1)
            ],
            "post_rerank": [
                {
                    "record_id": record_id,
                    "rank": rank,
                    "relevance": 1.0 - (rank / 20),
                    "rrf_score": 1 / (60 + rank),
                    "rerank_score": 1.0 - (rank / 10),
                    "retrieval_hits": [{"search_type": "lexical", "rank": rank}],
                }
                for rank, record_id in enumerate(ids, start=1)
            ],
            "post_selection": [
                {"record_id": record_id, "rank": rank}
                for rank, record_id in enumerate(ids, start=1)
            ],
            "context_characters": 500 + len(ids),
        },
        "stages": [
            {"name": "retrieval", "seconds": elapsed, "detail": {}},
            {
                "name": "rerank",
                "seconds": elapsed / 2,
                "detail": {
                    "requested_mode": "none",
                    "cross_encoder_model": None,
                },
            },
        ],
        "evidence": [
            {
                "record": {
                    "record_id": record_id,
                    "work": f"Work {record_id}",
                    "text": "private source text that comparison must not copy",
                },
                "inline_citation": f"Author: {rank}",
                "collection": "corpus",
                "distance": 0.1 * rank,
                "rrf_score": 1 / (60 + rank),
                "rerank_score": 1.0 - (rank / 10),
                "retrieval_hits": [{"search_type": "lexical", "rank": rank}],
            }
            for rank, record_id in enumerate(ids, start=1)
        ],
    }


def test_research_comparison_reports_overlap_and_rank_changes_without_source_text() -> None:
    compared = compare_research_dry_runs(
        _result("research.a", ["r1", "r2", "r3"]),
        _result("research.b", ["r2", "r1", "r4"]),
    )

    summary = compared["comparison"]
    assert compared["non_persistent"] is True
    assert summary["shared_record_ids"] == ["r1", "r2"]
    assert summary["left_only_record_ids"] == ["r3"]
    assert summary["right_only_record_ids"] == ["r4"]
    assert summary["shared_count"] == 2
    assert summary["union_count"] == 4
    assert summary["jaccard_overlap"] == pytest.approx(0.5)
    assert summary["candidate_overlap"]["jaccard_overlap"] == pytest.approx(0.5)
    assert compared["left"]["candidate_retention"] == "complete_for_comparison"
    assert compared["left"]["candidates"]["pre_rerank"]["count"] == 3
    assert compared["left"]["candidates"]["pre_rerank"]["scores"]["rrf_score"]["count"] == 3
    assert compared["left"]["context_characters"] == 503
    assert summary["rank_changes"] == [
        {"record_id": "r1", "left_rank": 1, "right_rank": 2, "rank_delta": 1},
        {"record_id": "r2", "left_rank": 2, "right_rank": 1, "rank_delta": -1},
    ]
    assert "private source text" not in str(compared)


class _LexicalOnlyStore:
    def list_stores(self):
        return [
            {
                "name": "corpus",
                "count": 1,
                "collection_role": "general",
                "language_codes": ["en"],
            }
        ]

    def lexical_search(self, name, query, limit):
        assert name == "corpus"
        assert query == "What is the trace?"
        assert limit >= 1
        return [
            {
                "id": "row-1",
                "record": {
                    "record_id": "r1",
                    "work": "Of Grammatology",
                    "document_author": "Jacques Derrida",
                    "year": 1976,
                    "page_start": 65,
                    "text": "The trace is not a presence.",
                },
                "distance": None,
                "relevance": 0.8,
            }
        ]


def test_research_dry_run_stops_before_generation(monkeypatch) -> None:
    def forbidden_chat(**kwargs):
        raise AssertionError("dry-run comparison must not generate an answer")

    monkeypatch.setattr("app.rag.chat_complete", forbidden_chat)
    request = RAGRunRequest(
        prompt="What is the trace?",
        pipeline_id="research.current",
        pipeline_version=1,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=1,
        fetch_k=1,
        reranker="none",
        query_decomposition=False,
        model=None,
    )

    result = run_rag_pipeline(
        request,
        _LexicalOnlyStore(),
        stop_after_context=True,
    )

    assert result["dry_run"] is True
    assert result["answer"] == ""
    assert result["memory"]["mode"] == "skipped_for_non_persistent_dry_run"
    assert result["diagnostics"]["candidate_retention"] == "complete_for_comparison"
    assert result["diagnostics"]["pre_rerank"][0]["record_id"] == "r1"
    assert "text" not in result["diagnostics"]["pre_rerank"][0]
    assert [item["record"]["record_id"] for item in result["evidence"]] == ["r1"]
    assert all(stage["name"] != "generation" for stage in result["stages"])



def test_expected_record_coverage_is_review_grounded_and_ordered() -> None:
    coverage = expected_record_coverage(
        ["r2", "r4", "r1"],
        ["r1", "r2", "r3", "r2"],
    )

    assert coverage == {
        "expected_count": 3,
        "matched_count": 2,
        "matched_record_ids": ["r1", "r2"],
        "coverage": pytest.approx(2 / 3),
    }


def test_benchmark_case_and_aggregate_remain_descriptive() -> None:
    case = ResearchPipelineBenchmarkCase(
        case_id="trace",
        label="Trace benchmark",
        request=RAGRunRequest(
            prompt="What is the trace?",
            source_collection="corpus",
            query_decomposition=False,
        ),
        expected_record_ids=["r1", "r3"],
    )
    first = benchmark_case_result(
        case,
        _result("research.a", ["r1", "r2"], elapsed=0.2),
        _result("research.b", ["r2", "r3"], elapsed=0.4),
    )
    failed = {
        "case_id": "failed",
        "label": "Unavailable corpus",
        "status": "failed",
        "expected_record_ids": [],
        "left_error": "missing corpus",
        "right_error": "missing corpus",
    }

    aggregate = aggregate_research_benchmark([first, failed])

    assert first["status"] == "completed"
    assert first["expected_coverage"]["left"]["final_evidence"]["coverage"] == pytest.approx(0.5)
    assert first["expected_coverage"]["right"]["final_evidence"]["coverage"] == pytest.approx(0.5)
    assert aggregate["case_count"] == 2
    assert aggregate["completed_case_count"] == 1
    assert aggregate["failed_case_count"] == 1
    assert aggregate["mean_candidate_overlap"] == pytest.approx(1 / 3)
    assert aggregate["mean_final_evidence_overlap"] == pytest.approx(1 / 3)
    assert aggregate["left"]["mean_elapsed_seconds"] == pytest.approx(0.2)
    assert aggregate["right"]["mean_elapsed_seconds"] == pytest.approx(0.4)
    assert "winner" not in aggregate
    assert "better" not in aggregate


def test_benchmark_request_requires_unique_case_ids() -> None:
    case = ResearchPipelineBenchmarkCase(
        case_id="same",
        request=RAGRunRequest(
            prompt="What is the trace?",
            source_collection="corpus",
            query_decomposition=False,
        ),
    )

    with pytest.raises(ValueError, match="case IDs must be unique"):
        ResearchPipelineBenchmarkRequest(
            cases=[case, case.model_copy(deep=True)],
            left=PipelineVersionRef(pipeline_id="research.a", version=1),
            right=PipelineVersionRef(pipeline_id="research.b", version=1),
        )
