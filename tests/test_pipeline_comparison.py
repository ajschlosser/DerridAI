# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.models import RAGRunRequest
from app.pipelines.comparison import compare_research_dry_runs
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
        "retrieval": {"raw_count": len(ids), "reranked_count": len(ids)},
        "stages": [{"name": "retrieval", "seconds": elapsed, "detail": {}}],
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
    assert [item["record"]["record_id"] for item in result["evidence"]] == ["r1"]
    assert all(stage["name"] != "generation" for stage in result["stages"])
