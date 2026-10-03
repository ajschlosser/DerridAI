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

"""Preparation deltas preserve current authority and never replace Record topology."""

from __future__ import annotations

import copy

import pytest
from app import corpus_builder as cb
from app.corpus_enrichment_helpers import _merge_preparation_snapshot
from app.field_assertions import (
    create_human_assertion,
    create_model_assertion,
    current_assertion_by_name,
    get_assertions,
    project_record_assertions,
    reset_fields_for_evaluation,
)
from app.metadata_schema import MetadataSchema, SchemaField, SchemaGroup, SchemaMember
from test_review_queues import install_repo, ready_record


@pytest.fixture
def prepared(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1"), ready_record("r2", "b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    yield repo, build["build_id"], manager
    manager._executor.shutdown(wait=True)


def annotate(rows):
    workers = copy.deepcopy(rows)
    for row in workers:
        row["document_intelligence"] = {"record_text_sha256": "bound-test-digest", "status": "ready"}
        row["memory_hints"] = {"speaker": [{"value": "Advisory speaker"}]}
    return workers


def test_unchanged_preparation_is_noop_without_full_store_write(prepared, monkeypatch):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    monkeypatch.setattr(repo, "save_records", lambda *args: pytest.fail("preparation replaced topology"))
    monkeypatch.setattr(repo, "update_record", lambda *args, **kwargs: pytest.fail("no-op wrote a Record"))
    assert manager._persist_preparation_records(bid, base, copy.deepcopy(base)) == base


def test_preparation_persists_only_changed_rows_and_survives_restart(prepared, monkeypatch):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = copy.deepcopy(base)
    workers[0]["nlp_candidates"] = {"status": "ready", "text_sha256": "test-digest"}
    calls = []
    update = repo.update_record

    def counted(build_id, record, **kwargs):
        calls.append((record["record_id"], kwargs["expected_queue_version"]))
        return update(build_id, record, **kwargs)

    monkeypatch.setattr(repo, "save_records", lambda *args: pytest.fail("preparation replaced topology"))
    monkeypatch.setattr(repo, "update_record", counted)
    result = manager._persist_preparation_records(bid, base, workers)
    assert len(calls) == 1 and calls[0][0] == "r1"
    restarted = cb.PdfCorpusRepository(repo.root)
    assert restarted.load_records(bid) == result
    assert result[0]["nlp_candidates"] == workers[0]["nlp_candidates"]
    assert result[1] == base[1]
    assert repo.records_projection_dirty(bid)


def test_sparse_preparation_distinguishes_missing_from_explicit_null(prepared):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = copy.deepcopy(base)
    workers[0]["memory_hints"] = None
    result = manager._persist_preparation_records(bid, base, workers)
    assert "memory_hints" in result[0] and result[0]["memory_hints"] is None
    next_workers = copy.deepcopy(result)
    next_workers[0].pop("memory_hints")
    result = manager._persist_preparation_records(bid, result, next_workers)
    assert "memory_hints" not in result[0]


def test_merge_does_not_mutate_its_input_snapshots():
    base = {"record_id": "r1", "record_revision": 1, "text": "Source", "speaker": "Original"}
    live = copy.deepcopy(base)
    worker = {**base, "document_intelligence": {"status": "ready"}}
    snapshots = copy.deepcopy((base, live, worker))
    merged = _merge_preparation_snapshot(base, live, worker, allowed_fields={"speaker"})
    assert (base, live, worker) == snapshots
    assert merged["document_intelligence"] == {"status": "ready"}


def test_repeatable_proposals_retire_old_members_without_erasing_their_history():
    schema = MetadataSchema(
        name="Relations",
        groups=[
            SchemaGroup(key="discourse", label="Discourse", intro="Classify."),
            SchemaGroup(key="quotation", label="Quotation", intro="Extract."),
        ],
        fields=[SchemaField(
            field_id="field-relations", name="quotation_relations", label="Relations",
            type="repeatable", group="quotation", max_items=4,
            members=[SchemaMember(field_id="member-speaker", name="quoted_speaker", label="Speaker")],
        )],
    )
    base = {"record_id": "r1", "record_revision": 1, "text": "Source"}
    create_model_assertion(
        base, "quotation_relations", [{"instance_id": "old", "quoted_speaker": "Original"}],
        schema=schema, evidence=[{"block_id": "b1"}],
    )
    project_record_assertions(base)
    worker = copy.deepcopy(base)
    reset_fields_for_evaluation(worker, {"quotation_relations"}, schema=schema, discard_history=True)
    create_model_assertion(
        worker, "quotation_relations", [{"instance_id": "new", "quoted_speaker": "Replacement"}],
        schema=schema, evidence=[{"block_id": "b1"}],
    )
    project_record_assertions(worker)
    merged = _merge_preparation_snapshot(base, copy.deepcopy(base), worker, {"quotation_relations"})
    assert merged["quotation_relations"] == [{"instance_id": "new", "quoted_speaker": "Replacement"}]
    assert any(
        item.instance_id == "old"
        for field_id in base["field_assertions"]
        for item in get_assertions(merged, field_id)
    )
    assert set(merged["current_field_assertions"].values()) == set(worker["current_field_assertions"].values())


@pytest.mark.parametrize("change", ["text", "revision", "source", "review"])
def test_intervening_documentary_or_review_change_rejects_stale_annotations(prepared, change):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = annotate(base)
    current = copy.deepcopy(base[0])
    if change == "text":
        current["text"] = "Human-corrected source text"
    elif change == "revision":
        current["record_revision"] += 1
    elif change == "source":
        current["source_block_ids"] = ["new-source"]
    elif change == "review":
        current["human_touched_fields"] = ["__review__"]
    repo.update_record(bid, current)
    expected = repo.get_record(bid, "r1")
    result = manager._persist_preparation_records(bid, base, workers)
    assert result[0] == expected
    assert "document_intelligence" not in result[0]
    assert result[1]["document_intelligence"] == workers[1]["document_intelligence"]


def test_human_field_without_revision_bump_survives_late_model_proposal(prepared):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = annotate(base)
    create_model_assertion(workers[0], "speaker", "Model speaker", method="test")
    project_record_assertions(workers[0])
    current = copy.deepcopy(base[0])
    create_human_assertion(current, "speaker", "Reviewed speaker", method="human")
    project_record_assertions(current)
    repo.update_record(bid, current)
    result = manager._persist_preparation_records(bid, base, workers)
    assert result[0]["speaker"] == "Reviewed speaker"
    assert current_assertion_by_name(result[0], "speaker").authority_status == "human_confirmed"
    assert result[0]["document_intelligence"] == workers[0]["document_intelligence"]


def test_rerun_can_refresh_derived_annotations_of_already_reviewed_text(prepared, monkeypatch):
    repo, bid, manager = prepared
    current = repo.get_record(bid, "r1")
    current["human_touched_fields"] = ["__text__", "__review__"]
    create_human_assertion(current, "speaker", "Reviewed speaker", method="human")
    project_record_assertions(current)
    repo.update_record(bid, current)
    graph = {"summary": {"records": 2}}

    def annotate_reviewed(build_id, records, manifest, request):
        for record in records:
            record["document_intelligence"] = {"status": "ready", "record_text_sha256": "test-digest"}
        create_model_assertion(records[0], "speaker", "Late model speaker", method="test")
        project_record_assertions(records[0])
        return {"status": "ready"}

    monkeypatch.setattr(manager, "_run_document_intelligence", annotate_reviewed)
    monkeypatch.setattr(manager, "semantic_content_graph", lambda build_id: graph)
    monkeypatch.setattr(manager, "document_intelligence", lambda build_id: {"status": "ready"})
    monkeypatch.setattr(repo, "save_records", lambda *args: pytest.fail("rerun replaced topology"))
    result = manager.rerun_document_intelligence(bid)
    record = repo.get_record(bid, "r1")
    assert record["document_intelligence"]["status"] == "ready"
    assert record["speaker"] == "Reviewed speaker"
    assert record["record_revision"] == current["record_revision"]
    assert result["semantic_content_graph"] == graph


def test_source_illegibility_preserves_a_review_during_scoring(prepared, monkeypatch):
    repo, bid, manager = prepared
    records = repo.load_records(bid)

    def scoring(workers, request, pages, threshold):
        for worker in workers:
            worker["text_noise"] = {"score": 99.0, "unusable": True}
        current = repo.get_record(bid, "r1")
        current["text"] = "Reviewed correction"
        current["record_revision"] += 1
        current["human_touched_fields"] = ["__text__"]
        repo.update_record(bid, current)

    monkeypatch.setattr(manager, "_attach_ingest_noise", scoring)
    monkeypatch.setattr(repo, "save_records", lambda *args: pytest.fail("scoring replaced topology"))
    report = manager._apply_source_illegibility(bid, records, {}, {}, None)
    assert records == repo.load_records(bid)
    assert records[0]["text"] == "Reviewed correction"
    assert "text_noise" not in records[0]
    assert records[1]["text_noise"]["unusable"]
    assert records[1]["source_quality_issues"][0]["code"] == "illegible_text"
    assert report["record_count"] == 2


def test_unchanged_source_can_receive_independently_grounded_model_prefill(prepared):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = copy.deepcopy(base)
    create_model_assertion(
        workers[0], "speaker", "Model speaker", method="prefill-test",
        evidence=[{"block_ids": ["b1"]}], confidence=0.9,
    )
    project_record_assertions(workers[0])
    result = manager._persist_preparation_records(bid, base, workers)
    assertion = current_assertion_by_name(result[0], "speaker")
    assert assertion.value == "Model speaker"
    assert assertion.authority_status == "unreviewed"
    assert assertion.evidence == [{"block_ids": ["b1"]}]
    assert result[0]["record_revision"] == base[0]["record_revision"]


def test_retired_record_is_not_restored_and_new_topology_is_preserved(prepared):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = annotate(base)
    replacement = ready_record("replacement", "b1")
    repo.save_records(bid, [replacement, base[1]])
    result = manager._persist_preparation_records(bid, base, workers)
    assert [row["record_id"] for row in result] == ["replacement", "r2"]
    assert "document_intelligence" not in result[0]
    assert result[1]["document_intelligence"] == workers[1]["document_intelligence"]
    with pytest.raises(KeyError):
        repo.get_record(bid, "r1")


def test_conditional_write_rejects_external_repository_change(prepared):
    repo, bid, _manager = prepared
    snapshot = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    external = cb.PdfCorpusRepository(repo.root)
    current = external.get_record(bid, "r1")
    current["review_reason"] = "External reviewer decision"
    external.update_record(bid, current)
    snapshot["review_reason"] = "Stale replacement"
    with pytest.raises(cb.RecordStateConflict, match="changed during preparation"):
        repo.update_record(bid, snapshot, expected_queue_version=snapshot["queue_state_version"])
    assert external.get_record(bid, "r1")["review_reason"] == "External reviewer decision"


def test_preparation_retries_external_race_against_current_row(prepared, monkeypatch):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = annotate(base)
    external = cb.PdfCorpusRepository(repo.root)
    update = repo.update_record
    calls = []

    def racing(build_id, record, **kwargs):
        calls.append(record["record_id"])
        if len(calls) == 1:
            changed = external.get_record(bid, "r1")
            changed["review_reason"] = "External reviewer decision"
            external.update_record(bid, changed)
        return update(build_id, record, **kwargs)

    monkeypatch.setattr(repo, "update_record", racing)
    result = manager._persist_preparation_records(bid, base, workers)
    assert calls == ["r1", "r1", "r2"]
    assert result[0]["review_reason"] == "External reviewer decision"
    assert result[0]["document_intelligence"] == workers[0]["document_intelligence"]


def test_retirement_between_read_and_conditional_write_is_not_restored(prepared, monkeypatch):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    external = cb.PdfCorpusRepository(repo.root)
    update = repo.update_record

    def retiring(build_id, record, **kwargs):
        if record["record_id"] == "r1":
            external.save_records(bid, [base[1]])
        return update(build_id, record, **kwargs)

    monkeypatch.setattr(repo, "update_record", retiring)
    result = manager._persist_preparation_records(bid, base, annotate(base))
    assert [row["record_id"] for row in result] == ["r2"]
    assert result[0]["document_intelligence"]["status"] == "ready"


def test_repeated_conflicts_fail_visibly_without_partial_row_write(prepared, monkeypatch):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    calls = []

    def conflict(*args, **kwargs):
        calls.append(1)
        raise cb.RecordStateConflict("Concurrent writer still active")

    monkeypatch.setattr(repo, "update_record", conflict)
    with pytest.raises(cb.RecordStateConflict, match="still active"):
        manager._persist_preparation_records(bid, base, annotate(base))
    assert len(calls) == 3
    assert repo.load_records(bid) == base


@pytest.mark.parametrize("change", ["text", "revision", "source", "identity"])
def test_preparation_cannot_mutate_documentary_contract(prepared, change):
    repo, bid, manager = prepared
    base = repo.load_records(bid)
    workers = copy.deepcopy(base)
    if change == "text":
        workers[0]["text"] = "Unauthorized transformation"
    elif change == "revision":
        workers[0]["record_revision"] += 1
    elif change == "source":
        workers[0]["source_spans"] = [{"block_id": "invented"}]
    else:
        workers[0]["record_id"] = "invented"
    with pytest.raises(ValueError, match="Preparation cannot"):
        manager._persist_preparation_records(bid, base, workers)
    assert repo.load_records(bid) == base
