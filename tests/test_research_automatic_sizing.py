# Copyright 2026 Aaron John Schlosser, PhD.
"""Record-size-aware Research retrieval policy tests."""

from __future__ import annotations

from app.research_sizing import (
    automatic_collection_sizing,
    collapse_adjacent_candidates,
    expand_context_neighbors,
)


def _record(index: int, *, chars: int = 600, source: str = "doc-1") -> dict:
    return {
        "record_id": f"doc-{index:05d}",
        "record_revision": 1,
        "source_document_id": source,
        "text": f"record {index} " + ("x" * max(0, chars - 12)),
        "text_length": chars,
        "work": "Test Work",
        "document_author": "Test Author",
        "page_start": index,
        "page_end": index,
    }


def _candidate(index: int, *, chars: int = 600, source: str = "doc-1") -> dict:
    return {
        "id": f"c{index}",
        "collection": "corpus",
        "record": _record(index, chars=chars, source=source),
        "rrf_score": 1.0 / index,
        "retrieval_hits": [],
    }


def test_automatic_sizing_scales_short_records_without_unbounding_rerank_inputs() -> None:
    short = automatic_collection_sizing(
        count=10000,
        median_record_chars=400,
        requested_k=64,
        semantic_fetch_k=500,
        lexical_fetch_k=500,
        mmr_limit=64,
    )
    assert short["scale"] == 4.0
    assert short["k"] == 256
    # The pool grows only as far as useful to the larger k instead of 4x to 2000.
    assert short["semantic_fetch_k"] == 512
    assert short["lexical_fetch_k"] == 512
    assert short["mmr_limit"] == 256

    long = automatic_collection_sizing(
        count=10000,
        median_record_chars=3500,
        requested_k=64,
        semantic_fetch_k=500,
        lexical_fetch_k=500,
        mmr_limit=64,
    )
    assert long["scale"] == 1.0
    assert long["k"] == 64
    assert long["semantic_fetch_k"] == 500
    assert long["mmr_limit"] == 64


def test_automatic_sizing_never_exceeds_collection_or_api_bounds() -> None:
    sized = automatic_collection_sizing(
        count=90,
        median_record_chars=10,
        requested_k=500,
        semantic_fetch_k=5000,
        lexical_fetch_k=5000,
        mmr_limit=500,
    )
    assert sized["k"] == 90
    assert sized["semantic_fetch_k"] == 90
    assert sized["lexical_fetch_k"] == 90
    assert sized["mmr_limit"] == 90


def test_region_collapse_only_groups_short_consecutive_same_document_records() -> None:
    candidates = [
        _candidate(1, chars=500),
        _candidate(2, chars=500),
        _candidate(3, chars=500),
        _candidate(4, chars=2500),
        _candidate(8, chars=500),
        _candidate(9, chars=500, source="doc-2"),
    ]

    collapsed, detail = collapse_adjacent_candidates(candidates)

    assert detail == {"input_count": 6, "output_count": 4, "collapsed_records": 2}
    first = collapsed[0]
    assert first["record"]["record_id"] == "doc-00001"
    assert first["automatic_region_size"] == 3
    assert len(first["_automatic_region_members"]) == 3
    assert "record 1" in first["_rerank_text"]
    assert "record 3" in first["_rerank_text"]
    assert any(item["record"]["record_id"] == "doc-00004" for item in collapsed)
    assert any(item["record"]["record_id"] == "doc-00008" for item in collapsed)


def test_region_collapse_never_absorbs_pinned_selected_evidence() -> None:
    first = _candidate(1, chars=500)
    first["selected_evidence"] = True
    collapsed, detail = collapse_adjacent_candidates([first, _candidate(2, chars=500)])

    assert detail["output_count"] == 2
    assert collapsed[0].get("selected_evidence") is True


def test_context_expansion_keeps_neighbors_as_distinct_traceable_records() -> None:
    anchor = _candidate(3, chars=600)
    document = [_record(index, chars=600) for index in range(1, 6)]
    calls: list[tuple[str, str]] = []

    def load(collection: str, source_id: str):
        calls.append((collection, source_id))
        return document

    expanded, detail = expand_context_neighbors(
        [anchor],
        load_document_records=load,
        total_char_limit=12000,
        target_context_chars=3000,
        max_radius=2,
        neighbor_budget_fraction=0.5,
    )

    assert expanded[0]["record"]["record_id"] == "doc-00003"
    assert expanded[0]["selection_role"] == "retrieved_anchor"
    neighbors = expanded[1:]
    assert {item["record"]["record_id"] for item in neighbors} == {
        "doc-00001",
        "doc-00002",
        "doc-00004",
        "doc-00005",
    }
    assert all(item["selection_role"] == "context_neighbor" for item in neighbors)
    assert all(item["neighbor_of"] == "doc-00003" for item in neighbors)
    assert all(item["neighbor_reason"] == "adjacent_record" for item in neighbors)
    assert detail["neighbor_count"] == 4
    assert calls == [("corpus", "doc-1")]


def test_context_expansion_restores_collapsed_region_members_before_storage_reads() -> None:
    collapsed, _ = collapse_adjacent_candidates(
        [_candidate(1, chars=500), _candidate(2, chars=500), _candidate(3, chars=500)]
    )
    assert len(collapsed) == 1

    def should_not_load(_collection: str, _source_id: str):
        raise AssertionError("collapsed members should satisfy the target without a document read")

    expanded, detail = expand_context_neighbors(
        collapsed,
        load_document_records=should_not_load,
        total_char_limit=12000,
        target_context_chars=1500,
        max_radius=2,
        neighbor_budget_fraction=0.5,
    )

    assert [item["record"]["record_id"] for item in expanded] == [
        "doc-00001",
        "doc-00002",
        "doc-00003",
    ]
    assert [item.get("neighbor_reason") for item in expanded[1:]] == [
        "collapsed_region",
        "collapsed_region",
    ]
    assert detail["document_reads"] == 0


def test_context_expansion_respects_neighbor_share_of_existing_evidence_budget() -> None:
    anchor = _candidate(3, chars=600)
    document = [_record(index, chars=600) for index in range(1, 6)]

    expanded, detail = expand_context_neighbors(
        [anchor],
        load_document_records=lambda _collection, _source_id: document,
        total_char_limit=5000,
        target_context_chars=5000,
        max_radius=2,
        neighbor_budget_fraction=0.25,
    )

    assert detail["neighbor_character_budget"] == 1250
    assert detail["neighbor_count"] == 2
    assert len(expanded) == 3
