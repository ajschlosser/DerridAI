# Copyright 2026 Aaron John Schlosser, PhD.
"""Precedent retrieval kept from enrichment, and this record's own evidence candidates.

Why: Record Review repeated the precedent search enrichment had already run, and a reviewer
adopting a precedent's value had no pointer to where *this* record might support it. The kept
retrieval must stay references only (another record's value and evidence never land on this
record), must be re-verified for the current reviewer when read (a changed precedent or a
pending blind second opinion is never shown from a stale copy), and every candidate block must
belong to the record under review.
How: a small real repository and manager, the lexical path (no embedding service), a fake
embedder for the semantic ranking, and enrichment with a stubbed model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import corpus_builder as cb  # noqa: E402
from app.corpus_publication import serialize_public_record  # noqa: E402
from app.evidence_suggestions import (  # noqa: E402
    PRECEDENT_LEXICAL_METHOD,
    PRECEDENT_SEMANTIC_METHOD,
    record_source_blocks,
)
from app.metadata_precedents_cache import CACHE_KEY  # noqa: E402
from app.reviewer_context import current_reviewer  # noqa: E402

PRECEDENT_EVIDENCE = "For Levinas, responsibility precedes the freedom of the subject."
BLOCKS = {
    "pb1": PRECEDENT_EVIDENCE,
    "pb2": "The precedent record continues with something else entirely.",
    "tb1": "Unrelated remarks about the printing of this edition.",
    "tb2": "Here, for Levinas, responsibility precedes the freedom of any subject.",
}


def _precedent(**over):
    record = {
        "record_id": "p1", "record_revision": 2, "text": f"{BLOCKS['pb1']}\n\n{BLOCKS['pb2']}",
        "source_block_ids": ["pb1", "pb2"], "source_spans": [{"block_id": "pb1", "page": 3}, {"block_id": "pb2", "page": 3}],
        "region_type": "main_text", "primary_text": True, "discourse_role": "reported_position",
        "metadata_field_status": {"discourse_role": {"status": "human_confirmed", "method": "human"}},
        "metadata_evidence": {"discourse_role": {"block_ids": ["pb1"], "reviewed_by": "human", "confidence": 1.0}},
        "review_disposition": "pending", "metadata_complete": True,
    }
    record.update(over)
    return record


def _target():
    return {
        "record_id": "t", "record_revision": 1, "text": f"{BLOCKS['tb1']}\n\n{BLOCKS['tb2']}", "text_length": 120,
        "source_asset_id": "a", "source_block_ids": ["tb1", "tb2"],
        "source_spans": [{"block_id": "tb1", "page": 9}, {"block_id": "tb2", "page": 10}],
        "region_type": "main_text", "review_disposition": "pending",
    }


def _install(tmp_path: Path, records: list[dict]):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    cb._json_write(repo.asset_meta_path("a"), {
        "asset_id": "a", "sha256": "x", "filename": "x.pdf", "page_count": 1, "block_count": len(BLOCKS),
        "ocr_pages": 0, "warnings": [], "metadata": {}, "pages": [],
    })
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as handle:
        for block_id, text in BLOCKS.items():
            handle.write(json.dumps({"block_id": block_id, "page": 1, "type": "paragraph", "text": text}) + "\n")
    build = repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1,
        "source_block_count": len(BLOCKS), "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
        "profile_version": int(cb.CORPUS_PROFILES[cb.PROFILE_VERSION]["version"]), "app_version": cb.APP_VERSION,
        "provider": "ollama", "model": "test", "request": {}, "manifest": {}, "validation": {"valid": True},
    })
    repo.save_records(build["build_id"], records)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    manager._progressive_metadata_index = None  # lexical path: no embedding service in tests
    return repo, build["build_id"], manager


def _enrich(repo, build_id, manager, monkeypatch):
    def fake(_request, _prompt, *, response_model, max_tokens, schema_name, build_id="", attempts=1, **_kwargs):
        return {"metadata": {}, "field_evidence": {}, "field_assessments": {}, "review_reason": ""}

    monkeypatch.setattr(manager, "_chat_json", fake)
    record = repo.get_record(build_id, "t")
    manager._enrich_record(record, {}, {"provider": "ollama", "model": "test"}, build_id=build_id)
    repo.save_records(build_id, [repo.get_record(build_id, "p1"), record])
    return record


def _rank(queries, blocks, embed=None):
    """Rank through the assigned precedent_evidence_remap pipeline, as production does."""
    from app.pipelines.precedent_remap import RemapSession

    ranked = RemapSession.open().rank(queries, blocks, embed=embed)
    methods = {item["method"] for picks in ranked for item in picks}
    return ranked, (methods.pop() if len(methods) == 1 else None)


def test_ranking_uses_only_this_records_blocks_and_never_copies_the_query():
    record = _target()
    blocks = record_source_blocks(record, {key: {"block_id": key, "text": text} for key, text in BLOCKS.items()})
    ranked, method = _rank([PRECEDENT_EVIDENCE], blocks)

    assert method == PRECEDENT_LEXICAL_METHOD
    assert [item["block_id"] for item in ranked[0]][0] == "tb2"
    assert {item["block_id"] for item in ranked[0]} <= {"tb1", "tb2"}
    assert PRECEDENT_EVIDENCE not in json.dumps(ranked)
    assert ranked[0][0]["page"] == 10  # the record's own span location, not the block store's


def test_semantic_ranking_uses_the_embedder_and_falls_back_to_lexical_when_it_fails():
    blocks = [{"block_id": "x", "text": "alpha"}, {"block_id": "y", "text": "beta"}]
    vectors = {"query": [1.0, 0.0], "alpha": [0.3, 1.0], "beta": [0.9, 0.1]}
    ranked, method = _rank(["query"], blocks, embed=lambda texts: [vectors[t] for t in texts])
    assert method == PRECEDENT_SEMANTIC_METHOD
    assert [item["block_id"] for item in ranked[0]] == ["y", "x"]

    def broken(_texts):
        raise RuntimeError("embedding service down")

    ranked, method = _rank(["beta"], blocks, embed=broken)
    assert method == PRECEDENT_LEXICAL_METHOD
    assert [item["block_id"] for item in ranked[0]] == ["y"]


def test_non_pdf_units_keep_their_own_coordinates_and_gain_no_page():
    record = {"source_block_ids": ["s1"], "source_spans": [{"block_id": "s1", "start": 12.5, "end": 19.0, "speaker": "A"}]}
    units = record_source_blocks(record, {"s1": {"block_id": "s1", "text": "spoken words"}})
    assert units == [{"block_id": "s1", "text": "spoken words", "start": 12.5, "end": 19.0, "speaker": "A"}]


def test_enrichment_keeps_references_only_and_review_reads_them_back(tmp_path, monkeypatch):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    record = _enrich(repo, build_id, manager, monkeypatch)

    cache = record[CACHE_KEY]
    refs = cache["fields"]["discourse_role"]["refs"]
    assert len(refs) == 1 and refs[0]["exemplar_id"].startswith("mex-")
    stored = json.dumps(cache)
    assert PRECEDENT_EVIDENCE not in stored and "reported_position" not in stored
    assert "candidate_source_units" not in stored
    assert cache["fields"]["speaker"] == {"mode": "none", "refs": []}

    result = manager.metadata_precedents(build_id, "t", "discourse_role")
    assert result["source"] == "enrichment" and result["stale_count"] == 0
    [item] = result["items"]
    assert item["record_id"] == "p1" and item["value"] == "reported_position"
    assert item["evidence"] == PRECEDENT_EVIDENCE  # shown as the precedent's evidence, never as this record's
    assert item["candidate_source_units"][0]["block_id"] == "tb2"
    assert all(unit["block_id"] in {"tb1", "tb2"} for unit in item["candidate_source_units"])


def test_a_precedent_changed_after_enrichment_is_reported_stale_not_shown(tmp_path, monkeypatch):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    _enrich(repo, build_id, manager, monkeypatch)
    repo.save_records(build_id, [_precedent(record_revision=3, discourse_role="commentary"), repo.get_record(build_id, "t")])

    cached = manager.metadata_precedents(build_id, "t", "discourse_role")
    assert cached["items"] == [] and cached["stale_count"] == 1

    live = manager.metadata_precedents(build_id, "t", "discourse_role", refresh=True)
    assert live["source"] == "live" and [item["value"] for item in live["items"]] == ["commentary"]


def test_a_cached_precedent_is_hidden_from_a_reviewer_who_owes_a_second_opinion(tmp_path, monkeypatch):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    _enrich(repo, build_id, manager, monkeypatch)
    owed = _precedent(second_opinion={"discourse_role": {"first_reviewer": "user-1"}})
    repo.save_records(build_id, [owed, repo.get_record(build_id, "t")])

    token = current_reviewer.set("user-2")
    try:
        theirs = manager.metadata_precedents(build_id, "t", "discourse_role")
    finally:
        current_reviewer.reset(token)
    assert "reported_position" not in json.dumps(theirs) and theirs["stale_count"] == 1


def test_records_enriched_before_the_cache_search_live(tmp_path):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    result = manager.metadata_precedents(build_id, "t", "discourse_role")
    assert result["source"] == "live"
    assert result["items"][0]["candidate_source_units"][0]["block_id"] == "tb2"


def test_lazy_candidates_use_only_blocks_still_in_the_record(tmp_path, monkeypatch):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    record = _enrich(repo, build_id, manager, monkeypatch)
    ref = record[CACHE_KEY]["fields"]["discourse_role"]["refs"][0]
    assert "candidate_source_units" not in ref, "enrichment must not perform review-only remapping"

    record["source_block_ids"] = ["tb1"]  # re-segmented after enrichment
    repo.save_records(build_id, [repo.get_record(build_id, "p1"), record])

    result = manager.metadata_precedents(build_id, "t", "discourse_role")
    [item] = result["items"]
    assert all(unit["block_id"] == "tb1" for unit in item["candidate_source_units"])
    assert result["candidate_pipeline"]["feature"] == "precedent_evidence_remap"


def test_the_kept_retrieval_is_not_published():
    assert CACHE_KEY not in serialize_public_record({"record_id": "t", "text": "x", CACHE_KEY: {"version": 1}})


def test_one_call_returns_every_kept_field(tmp_path, monkeypatch):
    repo, build_id, manager = _install(tmp_path, [_precedent(), _target()])
    assert manager.record_precedents(build_id, "t")["fields"] == {}  # nothing kept yet
    _enrich(repo, build_id, manager, monkeypatch)

    fields = manager.record_precedents(build_id, "t")["fields"]
    assert fields["discourse_role"]["items"][0]["value"] == "reported_position"
    assert fields["speaker"]["items"] == [] and fields["speaker"]["mode"] == "none"
    assert fields["discourse_role"] == manager.metadata_precedents(build_id, "t", "discourse_role")
