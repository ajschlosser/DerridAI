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

from __future__ import annotations

import pytest
from app.models import RAGRunRequest
from app.pipelines.comparison import compare_research_dry_runs
from app.rag import _cross_encoder_rerank, _lexical_rerank, run_rag_pipeline


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


class _SystemCollectionStore:
    def list_stores(self):
        return [
            {
                "name": "_response_cache",
                "count": 1,
                "collection_role": "general",
                "language_codes": [],
                "metadata": {"derridai_system_collection": "response_cache"},
            }
        ]

    def lexical_search(self, name, query, limit):
        raise AssertionError("System collections must be rejected before retrieval starts.")


def test_research_dry_run_rejects_system_collection_before_retrieval() -> None:
    request = RAGRunRequest(
        prompt="What is the trace?",
        pipeline_id="research.current",
        pipeline_version=1,
        source_collection="_response_cache",
        locales=["en"],
        search_types=["lexical"],
        k=1,
        fetch_k=1,
        reranker="none",
        query_decomposition=False,
        model=None,
    )

    with pytest.raises(
        ValueError,
        match=r"system collection \(response_cache\).*cannot be used as a Research source collection",
    ):
        run_rag_pipeline(
            request,
            _SystemCollectionStore(),
            stop_after_context=True,
        )


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


class _ExplicitScopeStore:
    def list_stores(self):
        return [
            {
                "name": "corpus",
                "count": 3,
                "collection_role": "general",
                "language_codes": ["en"],
            }
        ]

    def work_stats(self, name):
        assert name == "corpus"
        return [
            {"work": "Of Grammatology", "document_author": "Jacques Derrida", "count": 2},
            {"work": "Totality and Infinity", "document_author": "Emmanuel Levinas", "count": 1},
        ]

    def lexical_search(self, name, query, limit, where=None, where_document=None):
        assert name == "corpus"
        assert where_document is None

        def matches(record, predicate):
            if not predicate:
                return True
            key, value = next(iter(predicate.items()))
            if key == "$and":
                return all(matches(record, child) for child in value)
            if key == "$or":
                return any(matches(record, child) for child in value)
            actual = record.get(key)
            if not isinstance(value, dict):
                return actual == value
            operator, expected = next(iter(value.items()))
            if operator == "$eq":
                return actual == expected
            if operator == "$ne":
                return actual != expected
            if operator == "$in":
                return actual in expected
            if operator == "$nin":
                return actual not in expected
            raise AssertionError(f"unsupported fake filter operator: {operator}")

        derrida = {
            "id": "derrida-1",
            "record": {
                "record_id": "d1",
                "work": "Of Grammatology",
                "document_author": "Jacques Derrida",
                "year": 1976,
                "page_start": 65,
                "text": "The trace is not a presence.",
            },
            "distance": None,
            "relevance": 0.95,
        }
        levinas = {
            "id": "levinas-1",
            "record": {
                "record_id": "l1",
                "work": "Totality and Infinity",
                "document_author": "Emmanuel Levinas",
                "year": 1969,
                "page_start": 43,
                "text": "The face resists possession and thematic reduction.",
            },
            "distance": None,
            "relevance": 0.70,
        }
        if where:
            return [
                row
                for row in (derrida, levinas)
                if matches(row["record"], where)
            ][:limit]
        # Reproduce the regression: broad retrieval is monopolized by the
        # largest author/work before explicit scope targeting runs.
        return [derrida][:limit]


def test_single_named_author_closes_retrieval_scope() -> None:
    request = RAGRunRequest(
        prompt="Describe the major themes and stakes of Levinas's philosophy.",
        pipeline_id="research.balanced",
        pipeline_version=3,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=2,
        fetch_k=2,
        rerank_top_n=2,
        reranker="none",
        query_decomposition=False,
        model=None,
    )

    result = run_rag_pipeline(
        request,
        _ExplicitScopeStore(),
        stop_after_context=True,
    )

    assert [item["record"]["record_id"] for item in result["evidence"]] == ["l1"]
    assert result["retrieval"]["inferred_exclusive_scope_works"] == ["Totality and Infinity"]
    assert result["retrieval"]["filter_plan"]["inferred_exclusive_works"] == [
        "Totality and Infinity"
    ]
    scope_stage = next(stage for stage in result["stages"] if stage["name"] == "research_scope")
    assert scope_stage["detail"]["active"] is True
    assert scope_stage["detail"]["inferred_exclusive_works"] == ["Totality and Infinity"]


def test_single_citation_directive_remains_open_but_reserves_source() -> None:
    request = RAGRunRequest(
        prompt="Explain the relation between alterity and trace. Cite Levinas explicitly.",
        pipeline_id="research.balanced",
        pipeline_version=1,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=1,
        fetch_k=1,
        rerank_top_n=2,
        reranker="none",
        query_decomposition=False,
        model=None,
    )

    result = run_rag_pipeline(
        request,
        _ExplicitScopeStore(),
        stop_after_context=True,
    )

    assert result["retrieval"]["inferred_exclusive_scope_works"] == []
    assert {item["record"]["record_id"] for item in result["evidence"]} == {"d1", "l1"}


def test_balanced_research_reserves_explicitly_named_author_scope() -> None:
    request = RAGRunRequest(
        prompt=(
            "Explain the relation between alterity and trace. "
            "Cite Derrida and Levinas explicitly."
        ),
        pipeline_id="research.balanced",
        pipeline_version=1,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=1,
        fetch_k=1,
        rerank_top_n=1,
        reranker="none",
        query_decomposition=False,
        model=None,
    )

    result = run_rag_pipeline(
        request,
        _ExplicitScopeStore(),
        stop_after_context=True,
    )

    authors = {
        item["record"]["document_author"]
        for item in result["evidence"]
    }
    assert authors == {"Jacques Derrida", "Emmanuel Levinas"}
    assert result["retrieval"]["explicit_scope_seed_count"] == 2
    assert {
        item["source_document_author"]
        for item in result["retrieval"]["explicit_scope_groups"]
        if item["matched"]
    } == {"Jacques Derrida", "Emmanuel Levinas"}


@pytest.mark.parametrize("version", [1, 2, 3])
def test_research_filter_wins_over_explicit_named_work_seed(version) -> None:
    request = RAGRunRequest(
        prompt=(
            "Explain the relation between alterity and trace. "
            "Cite Derrida and Levinas explicitly."
        ),
        pipeline_id="research.balanced",
        pipeline_version=version,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=2,
        fetch_k=2,
        rerank_top_n=2,
        reranker="none",
        query_decomposition=False,
        model=None,
        filter_plan={
            "metadata_filter": {
                "work": {"$ne": "Totality and Infinity"}
            },
            "source": "explicit",
        },
    )

    result = run_rag_pipeline(
        request,
        _ExplicitScopeStore(),
        stop_after_context=True,
    )

    assert [item["record"]["record_id"] for item in result["evidence"]] == ["d1"]
    scope_stages = [stage for stage in result["stages"] if stage["name"] == "research_scope"]
    assert bool(scope_stages) == (version == 3)
    if scope_stages:
        assert scope_stages[0]["detail"]["active"] is True
        assert scope_stages[0]["detail"]["metadata_fields"] == ["work"]

    assert result["retrieval"]["filter_plan"]["metadata_filter"] == {
        "work": {"$ne": "Totality and Infinity"}
    }
    levinas_scope = next(
        item
        for item in result["retrieval"]["explicit_scope_groups"]
        if "Totality and Infinity" in item["works"]
    )
    assert levinas_scope["matched"] is False


@pytest.mark.parametrize("version", [1, 3])
def test_filtered_run_labels_pinned_evidence_exemption(version) -> None:
    base = dict(
        prompt="Explain the trace.",
        pipeline_id="research.balanced",
        pipeline_version=version,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=2,
        fetch_k=2,
        rerank_top_n=2,
        reranker="none",
        query_decomposition=False,
        model=None,
        selected_evidence=[
            {
                "record": {
                    "record_id": "l1",
                    "work": "Totality and Infinity",
                    "text": "The face resists possession.",
                }
            }
        ],
    )
    plan = {"metadata_filter": {"work": {"$ne": "Totality and Infinity"}}}
    filtered = run_rag_pipeline(
        RAGRunRequest(**base, filter_plan=plan),
        _ExplicitScopeStore(),
        stop_after_context=True,
    )
    assert filtered["retrieval"]["filter_plan"]["selected_evidence_exempt_count"] == 1

    unfiltered = run_rag_pipeline(
        RAGRunRequest(**base),
        _ExplicitScopeStore(),
        stop_after_context=True,
    )
    assert "selected_evidence_exempt_count" not in unfiltered["retrieval"]["filter_plan"]



def test_lexical_rerank_distinguishes_source_author_from_mentioned_author() -> None:
    docs = [
        {
            "record": {
                "record_id": "d1",
                "document_author": "Jacques Derrida",
                "work": "Adieu to Emmanuel Levinas",
                "quoted_author": "Emmanuel Levinas",
                "text": "Levinas is discussed throughout this passage.",
            },
            "relevance": 0.5,
        },
        {
            "record": {
                "record_id": "l1",
                "document_author": "Emmanuel Levinas",
                "work": "Totality and Infinity",
                "text": "The face resists possession.",
            },
            "relevance": 0.5,
        },
    ]

    ranked = _lexical_rerank("cite Emmanuel Levinas", docs, 2)

    assert ranked[0]["record"]["record_id"] == "l1"


def test_cross_encoder_receives_source_identity_separately_from_mentions(monkeypatch) -> None:
    captured = {}

    def fake_predict(pairs, **kwargs):
        captured["pairs"] = pairs
        return [0.5], {"model": kwargs.get("model_name")}

    monkeypatch.setattr("app.rag.predict_scores", fake_predict)
    docs = [
        {
            "record": {
                "record_id": "d1",
                "document_author": "Jacques Derrida",
                "work": "Adieu to Emmanuel Levinas",
                "quoted_author": "Emmanuel Levinas",
                "text": "A passage mentioning Levinas.",
            }
        }
    ]

    ranked, warning, _telemetry = _cross_encoder_rerank(
        "cite Levinas",
        docs,
        1,
        "test-model",
        timeout_seconds=1,
    )

    assert warning is None
    assert ranked is not None
    candidate_text = captured["pairs"][0][1]
    assert "Source document author: Jacques Derrida" in candidate_text
    assert "Quoted author: Emmanuel Levinas" in candidate_text



def test_prose_research_retries_json_shaped_generation_once(monkeypatch) -> None:
    drafts = [
        '```json\n{"title":"Bad \\*structured answer","major_themes":[]}\n```',
        "The trace is not a presence [[E0]].",
    ]
    prompts: list[str] = []

    def generate(**kwargs):
        prompts.append(kwargs["prompt"])
        return drafts[len(prompts) - 1]

    monkeypatch.setattr("app.rag.chat_complete", generate)
    request = RAGRunRequest(
        prompt="What is the trace?",
        model="test-model",
        pipeline_id="research.current",
        pipeline_version=1,
        source_collection="corpus",
        locales=["en"],
        search_types=["lexical"],
        k=1,
        fetch_k=1,
        reranker="none",
        query_decomposition=False,
        use_prior_response_memory=False,
        use_prior_claim_memory=False,
    )

    result = run_rag_pipeline(request, _LexicalOnlyStore())

    assert len(prompts) == 2
    assert "OUTPUT_CONTRACT_CORRECTION" in prompts[1]
    assert result["raw_answer"] == "The trace is not a presence [[E0]]."
    assert any("structured JSON" in warning for warning in result["warnings"])
    generation_stage = next(stage for stage in result["stages"] if stage["name"] == "generation")
    assert generation_stage["detail"]["attempts"] == 2
    assert generation_stage["detail"]["prose_contract_retry"] is True


@pytest.mark.parametrize("decompose", [False, True])
def test_first_turn_characterization_preserves_query_generation_and_citation_contract(monkeypatch, decompose):
    captured = []
    def query(**kwargs):
        captured.append(("query", kwargs["prompt"]))
        return {"prompt_query": "What is the trace?", "prompt_query_fr": "Qu’est-ce que la trace?"}
    def generate(**kwargs):
        captured.append(("generation", kwargs["prompt"]))
        return "The trace is not a presence [[E0]]."
    monkeypatch.setattr("app.rag.structured_chat_complete", query)
    monkeypatch.setattr("app.rag.chat_complete", generate)
    request = RAGRunRequest(prompt="What is the trace?", instructions="Preserve negation", model="test-model",
        pipeline_id="research.current", pipeline_version=1, source_collection="corpus", locales=["en"],
        search_types=["lexical"], k=1, fetch_k=1, reranker="none", query_decomposition=decompose,
        use_prior_response_memory=False, use_prior_claim_memory=False)
    before = request.model_dump()
    result = run_rag_pipeline(request, _LexicalOnlyStore())
    assert request.model_dump() == before
    assert result["prompt"] == "What is the trace?"
    assert [kind for kind, _ in captured] == (["query", "generation"] if decompose else ["generation"])
    assert "<EVIDENCE>" in captured[-1][1] and "The trace is not a presence." in captured[-1][1]
    assert "THREAD_CONTEXT" not in captured[-1][1]
    assert len(result["evidence"]) == 1 and result["evidence"][0]["record"]["record_id"] == "r1"
    assert "[[E0]]" not in result["answer"] and "1976" in result["answer"]
    assert result["raw_answer"] == "The trace is not a presence [[E0]]."
