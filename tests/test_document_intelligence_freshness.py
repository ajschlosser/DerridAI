# Copyright 2026 Aaron John Schlosser, PhD.
"""Whole-document context stays exact without corpus reads on each hint lookup."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest
from app import corpus_builder as cb
from app import corpus_document_context as context
from app import corpus_metadata_enrichment_execution as execution
from app import document_intelligence as di
from app.record_semantic_map import record_semantic_map
from app.semantic_content_graph import build_semantic_content_graph
from test_review_queues import install_repo, ready_record


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1"), ready_record("r2", "b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(cb, "analyze_document", fake_analysis)
    yield repo, build["build_id"], manager
    manager._executor.shutdown(wait=True)


def fake_analysis(records, **kwargs):
    text, spans = di.document_text_for_records(records)
    return {
        "version": di.DOCUMENT_INTELLIGENCE_VERSION,
        "status": "ok", "provider": "test", "profile": "scholarly",
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "record_spans": spans,
        "entity_clusters": [
            {"cluster_id": "c1", "canonical": "Advisory person", "entity_type": "PERSON"}
        ],
        "entities": [
            {"cluster_id": "c1", "start_char": 8, "end_char": 16, "text": text[8:16], "entity_type": "PERSON"}
        ],
        "quotations": [
            {"start_char": 8, "end_char": 16, "text": text[8:16], "speaker_cluster_id": "c1"}
        ],
    }


def run_analysis(repo, bid, manager):
    records = repo.load_records(bid)
    base = copy.deepcopy(records)
    analysis = manager._run_document_intelligence(bid, records, {}, {})
    manager._persist_preparation_records(bid, base, records)
    return analysis


@pytest.mark.parametrize("change", ["text", "source", "units", "source_identity", "extraction"])
def test_document_context_changes_only_for_consumed_documentary_inputs(prepared, change):
    repo, bid, _manager = prepared
    before = repo.document_context(bid)
    current = repo.get_record(bid, "r1")
    if change == "text":
        current["text"] += " Edited."
    elif change == "source":
        current["source_spans"] = [{"block_id": "b1", "page": 2}]
    elif change == "units":
        current["source_unit_ids"] = ["replacement"]
    elif change == "source_identity":
        current["source_document_id"] = "other-document"
    else:
        current["source_extracted_text"] = "Revised extraction"
    repo.update_record(bid, current)
    assert repo.document_context(bid) != before
    assert cb.PdfCorpusRepository(repo.root).document_context(bid) == repo.document_context(bid)


def test_metadata_only_revision_and_equivalent_replacement_preserve_context(prepared):
    repo, bid, _manager = prepared
    before = repo.document_context(bid)
    current = repo.get_record(bid, "r1")
    current.update(record_revision=current["record_revision"] + 1, reviewer_note="Reviewed", speaker="Reviewed speaker")
    repo.update_record(bid, current)
    assert repo.document_context(bid) == before
    repo.save_records(bid, repo.load_records(bid))
    assert repo.document_context(bid) == before
    assert repo.document_context(bid, repo.load_records(bid)) == before


def test_context_lookup_and_metadata_writes_do_not_decode_unchanged_records(prepared, monkeypatch):
    repo, bid, _manager = prepared
    before = repo.document_context(bid)
    fingerprints = []
    fingerprint = context.record_fingerprint

    def counted(record):
        fingerprints.append(record["record_id"])
        return fingerprint(record)

    monkeypatch.setattr(context, "record_fingerprint", counted)
    for _ in range(5):
        assert repo.document_context(bid) == before
    assert not fingerprints
    current = repo.get_record(bid, "r1")
    current["reviewer_note"] = "New note"
    repo.update_record(bid, current)
    assert fingerprints == ["r1"]
    assert repo.document_context(bid) == before


@pytest.mark.parametrize("change", ["identity", "reorder", "retirement", "source"])
def test_checkpoint_goes_stale_for_topology_or_binding_even_without_changed_text(prepared, change):
    repo, bid, manager = prepared
    run_analysis(repo, bid, manager)
    assert not manager.document_intelligence(bid)["stale"]
    rows = repo.load_records(bid)
    before_text, _ = di.document_text_for_records(rows)
    if change == "identity":
        rows[0]["record_id"] = "replacement"
    elif change == "reorder":
        rows.reverse()  # Both fixture texts are identical.
    elif change == "retirement":
        rows.pop()
    else:
        rows[0]["source_spans"] = [{"block_id": "b1", "page": 2}]
    repo.save_records(bid, rows)
    if change != "retirement":
        assert di.document_text_for_records(rows)[0] == before_text
    assert manager.document_intelligence(bid)["stale"]
    graph = manager.semantic_content_graph(bid)
    assert all(node["label"] != "Advisory person" for node in graph["nodes"])
    local_map = manager.record_semantic_map(bid, rows[0]["record_id"])
    assert local_map["layers"]["document_intelligence"]["status"] == "stale"
    assert not any(item["layer"] in {"entity", "quotation"} for item in local_map["mentions"])


def test_external_canonical_write_is_detected_before_queue_repairs_dirty_rows(prepared):
    repo, bid, manager = prepared
    run_analysis(repo, bid, manager)
    before = repo.document_context(bid)
    external = cb.PdfCorpusRepository(repo.root)
    current = external.get_record(bid, "r2")
    current["text"] += " Changed by external repository."
    with external._records_db(bid) as connection:
        connection.execute("UPDATE corpus_records SET payload=? WHERE record_id='r2'", (json.dumps(current),))
    repo.projected_review_page(bid, cb.QueueFilter(), offset=0, limit=1)
    assert repo.document_context(bid) != before
    assert manager.document_intelligence(bid)["stale"]


def test_context_repair_invalidates_old_bindings_without_changing_canonical_rows(prepared):
    repo, bid, manager = prepared
    run_analysis(repo, bid, manager)
    before = repo.load_records(bid)
    epoch = repo.document_context(bid)
    with repo._records_db(bid) as connection:
        connection.execute("DROP TABLE document_context_records")
    assert repo.document_context(bid) != epoch
    assert repo.load_records(bid) == before
    assert manager.document_intelligence(bid)["stale"]


def test_change_during_analysis_never_installs_a_current_annotation_projection(prepared, monkeypatch):
    repo, bid, manager = prepared

    def racing(records, **kwargs):
        current = repo.get_record(bid, "r2")
        current["text"] += " Reviewed after analysis started."
        repo.update_record(bid, current)
        return fake_analysis(records)

    monkeypatch.setattr(cb, "analyze_document", racing)
    analysis = run_analysis(repo, bid, manager)
    assert analysis["stale"]
    assert analysis["warnings"]
    assert manager.document_intelligence(bid)["stale"]
    assert all("document_intelligence" not in row for row in repo.load_records(bid))
    assert repo.get_record(bid, "r2")["text"].endswith("started.")


def test_failed_rerun_cannot_reuse_a_previous_successful_checkpoint_or_graph(prepared, monkeypatch):
    repo, bid, manager = prepared
    run_analysis(repo, bid, manager)
    before = manager.semantic_content_graph(bid)
    assert any(node["label"] == "Advisory person" for node in before["nodes"])
    retained = repo.get_record(bid, "r1")

    def fail(*args, **kwargs):
        raise RuntimeError("Analyzer failed")

    monkeypatch.setattr(cb, "analyze_document", fail)
    result = run_analysis(repo, bid, manager)
    assert result["status"] == "unavailable"
    assert manager.document_intelligence(bid)["status"] == "unavailable"
    assert not any(node["label"] == "Advisory person" for node in manager.semantic_content_graph(bid)["nodes"])
    assert manager.record_semantic_map(bid, "r1")["layers"]["document_intelligence"]["status"] == "unavailable"
    assert retained["document_intelligence"]["analysis_id"] != result["analysis_id"]


@pytest.mark.parametrize("change", ["none", "metadata", "neighbor", "legacy"])
def test_metadata_routing_checks_document_context_without_loading_the_corpus(prepared, monkeypatch, change):
    repo, bid, manager = prepared
    run_analysis(repo, bid, manager)
    snapshot = repo.get_record(bid, "r1")
    if change == "metadata":
        current = repo.get_record(bid, "r2")
        current["reviewer_note"] = "Does not invalidate NLP"
        repo.update_record(bid, current)
    elif change == "neighbor":
        current = repo.get_record(bid, "r2")
        current["text"] += " Changed context."
        repo.update_record(bid, current)
    elif change == "legacy":
        snapshot["document_intelligence"].pop("document_context_epoch")
    monkeypatch.setattr(repo, "load_records", lambda *args: pytest.fail("hint routing loaded all Records"))

    class ObservedRouting(Exception):
        pass

    def inspect(record, text):
        if change in {"none", "metadata"}:
            assert di.current_quotations(record)
            assert di.prompt_hints(record, ["quoted_speaker"])
        else:
            assert di.current_quotations(record) is None
            assert di.prompt_hints(record, ["quoted_speaker"]) == {}
        raise ObservedRouting

    monkeypatch.setattr(execution, "_has_quotation_signal", inspect)
    with pytest.raises(ObservedRouting):
        manager._enrich_record(snapshot, {}, {}, build_id=bid)


def test_local_projection_rejects_source_rebinding_and_mismatched_analysis_scopes():
    records = [ready_record("r1", "b1")]
    analysis = fake_analysis(records)
    di.project_annotations_to_records(records, analysis)
    assert di.current_quotations(records[0])
    records[0]["source_spans"] = [{"block_id": "replacement", "page": 1}]
    assert di.current_quotations(records[0]) is None
    assert di.prompt_hints(records[0], ["quoted_speaker"]) == {}
    di.project_annotations_to_records(records, analysis)
    assert analysis["stale"]
    assert "document_intelligence" not in records[0]
    graph = build_semantic_content_graph(records, analysis)
    assert not any(node["label"] == "Advisory person" for node in graph["nodes"])
    assert record_semantic_map(graph, records, "r1", analysis=analysis)["mentions"] == []


def test_legacy_checkpoint_without_current_binding_is_visible_but_not_current(prepared):
    repo, bid, manager = prepared
    legacy = fake_analysis(repo.load_records(bid))
    legacy["version"] = 1
    repo.save_checkpoint(bid, "document_intelligence", legacy)
    result = manager.document_intelligence(bid)
    assert result["stale"]
    assert result["entity_clusters"] == legacy["entity_clusters"]


def test_provider_cannot_replace_server_owned_documentary_bindings(monkeypatch):
    records = [ready_record("r1", "b1")]
    provider = {
        **fake_analysis(records), "version": 1, "source_document_id": "invented",
        "text_sha256": "invented", "text_length": 1, "record_spans": [],
        "profile": "fiction", "selected_provider": "invented",
        "document_context_epoch": "invented", "analysis_id": "invented", "stale": False,
    }
    monkeypatch.setattr(di, "_spacy_document_annotations", lambda *args: provider)
    analysis = di.analyze_document(
        records, source_document_id="source", language="English",
        request={"document_nlp_provider": "spacy", "document_intelligence_profile": "scholarly"},
    )
    assert analysis["version"] == di.DOCUMENT_INTELLIGENCE_VERSION
    assert analysis["source_document_id"] == "source"
    assert analysis["text_sha256"] == hashlib.sha256(records[0]["text"].encode("utf-8")).hexdigest()
    assert analysis["record_spans"] == di.document_text_for_records(records)[1]
    assert (analysis["profile"], analysis["selected_provider"]) == ("scholarly", "spacy")
    assert "document_context_epoch" not in analysis
    assert "analysis_id" not in analysis


def test_failed_record_transaction_rolls_back_document_context(prepared, monkeypatch):
    repo, bid, _manager = prepared
    before = repo.document_context(bid)
    original = repo.get_record(bid, "r1")
    changed = copy.deepcopy(original)
    changed["text"] += " Must roll back."

    def fail(*args, **kwargs):
        raise RuntimeError("Projection write failed")

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", fail)
    with pytest.raises(RuntimeError, match="Projection write failed"):
        repo.update_record(bid, changed)
    assert repo.get_record(bid, "r1") == original
    assert repo.document_context(bid) == before
