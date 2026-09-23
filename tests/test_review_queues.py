"""Review queues, metadata decisions, and progressive unlocking.

Why: reviewers work through queues (ready, metadata, source, topology). A record is
"ready" only when nothing else is outstanding, decisions must persist and update
queue counts, and reviewers may start reviewing finished records while enrichment
continues (with automatic changes to reviewed records frozen).
How: `install_repo` builds a temp repository; `ready_record` makes a clean, accepted-able
record that tests then degrade with specific problems.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def install_repo(tmp_path: Path, records: list[dict], *, status: str = "ready"):
    """Create a temp repository and build with the given records and build status."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    cb._json_write(repo.asset_meta_path("a"), {
        "asset_id":"a","sha256":"x","filename":"x.pdf","page_count":2,
        "block_count":len(records),"ocr_pages":0,"warnings":[],"metadata":{},"pages":[],
    })
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as handle:
        for i, _ in enumerate(records, 1):
            handle.write(json.dumps({"block_id":f"b{i}","page":1,"bbox":[0,0,1,1],"type":"paragraph","text":f"text {i}","extraction_method":"native","confidence":1.0})+"\n")
    build = repo.create_build({
        "asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":2,
        "source_block_count":len(records),"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,
        "profile_version":int(cb.CORPUS_PROFILES[cb.PROFILE_VERSION]["version"]),"provider":"ollama","model":"test",
        "request":{},"manifest":{"main_text_start_page":1,"main_text_end_page":2},"validation":{"valid":True},
    })
    build["status"] = status
    build["stage"] = "ready" if status == "ready" else "enriching"
    repo.save_build(build)
    repo.save_records(build["build_id"], records)
    return repo, build


def ready_record(rid: str, bid: str) -> dict:
    """Make a complete, clean record (all required metadata resolved) ready to accept."""
    return {
        "record_id":rid,"record_revision":1,"text":"Édouard Glissant and différance","text_length":31,
        "source_block_ids":[bid],"source_spans":[{"block_id":bid,"page":1}],"pdf_pages":[1],
        "region_type":"main_text","primary_text":True,"discourse_role":"analysis",
        "metadata_field_status":{
            "region_type":{"status":"deterministic","method":"test"},
            "primary_text":{"status":"deterministic","method":"test"},
            "discourse_role":{"status":"model_inferred","method":"llm","confidence":.96},
        },
        "metadata_incomplete_fields":[],"metadata_review_fields":[],"metadata_complete":True,"metadata_enrichment_state":"complete",
        "review_disposition":"pending","accepted":False,"rejected":False,"needs_review":False,"review_reason":"",
    }


def test_one_current_profile_is_registered():
    """Pin profile and prompt ids, and that a single profile is registered."""
    assert cb.PROFILE_VERSION == "derrida-scholarly-v12"
    assert cb.METADATA_PROMPT_VERSION == "derridai-record-metadata-v11"
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    assert PdfCorpusBuildCreate(asset_id="a").profile_id == "derrida-scholarly-v12"


def test_false_primary_text_is_complete_and_human_decision_survives_manifest(tmp_path: Path):
    """A human "not primary text" answer counts as resolved and survives manifest re-application.

    primary_text=False is saved as human_confirmed with a decision-history entry, leaves
    the incomplete/review lists, and is not overwritten when the document manifest is
    applied again (main text pages 1-2).
    """
    record = ready_record("r1", "b1")
    record.update({"primary_text":None,"metadata_incomplete_fields":["primary_text"],"metadata_review_fields":["primary_text"]})
    record["metadata_field_status"]["primary_text"]={"status":"unresolved","method":"llm"}
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    updated = manager.patch_metadata(build["build_id"], "r1", {"primary_text":False}, expected_revision=1)
    assert updated["primary_text"] is False
    assert updated["metadata_field_status"]["primary_text"]["status"] == "human_confirmed"
    assert updated["metadata_incomplete_fields"] == []
    assert updated["metadata_review_fields"] == []
    assert updated["metadata_decisions"][-1]["value"] is False
    cb._apply_manifest_metadata(updated, {"main_text_start_page":1,"main_text_end_page":2})
    assert updated["primary_text"] is False
    assert updated["metadata_field_status"]["primary_text"]["status"] == "human_confirmed"


def test_metadata_decision_is_durable_and_moves_record_out_of_metadata_queue(tmp_path: Path):
    """Resolving the last unresolved field moves the record from the metadata queue to ready.

    Checks the decision result (nothing remaining, ready for acceptance), the persisted
    status "human_confirmed", and the queue totals (metadata 0, ready 1).
    """
    record = ready_record("r1", "b1")
    record.update({"position_holder":"Derrida","metadata_review_fields":["position_holder"],"metadata_complete":False})
    record["metadata_field_status"]["position_holder"]={"status":"unresolved","method":"llm","confidence":.61}
    repo, build = install_repo(tmp_path, [record])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.metadata_decision(build["build_id"], "r1", "position_holder", "Derrida", expected_revision=1)
    assert result["remaining_fields"] == []
    assert result["ready_for_acceptance"] is True
    assert result["review_state"] == "ready"
    persisted = repo.load_records(build["build_id"])[0]
    assert persisted["metadata_field_status"]["position_holder"]["status"] == "human_confirmed"
    assert persisted["metadata_review_fields"] == []
    assert persisted["review_state"] == "ready"
    assert repo.page_records(build["build_id"], review_queue="metadata")["total"] == 0
    assert repo.page_records(build["build_id"], review_queue="ready")["total"] == 1


def test_review_decision_returns_next_record_and_authoritative_queue_counts(tmp_path: Path):
    """Accepting r1 returns r2 as next, refreshed queue counts, and confirms LLM-inferred fields."""
    repo, build = install_repo(tmp_path, [ready_record("r1","b1"), ready_record("r2","b2")])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    result = manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1, review_queue="ready")
    assert result["applied"] is True
    assert result["record"]["accepted"] is True
    assert result["next_record"]["record_id"] == "r2"
    assert result["queue_counts"]["accepted"] == 1
    assert result["queue_counts"]["ready"] == 1
    assert result["record"]["metadata_field_status"]["discourse_role"]["status"] == "human_confirmed"


def test_accept_next_from_all_queue_skips_already_reviewed_records(tmp_path: Path):
    """From the "all" queue, "next" skips records that are already accepted.

    r1 is accepted; r2 was already accepted; the next record returned must be r3, and the
    counts must show 2 accepted and 1 pending.
    """
    first=ready_record("r1","b1")
    already=ready_record("r2","b2")
    already.update({"review_disposition":"accepted","accepted":True,"record_revision":2})
    pending=ready_record("r3","b3")
    repo, build = install_repo(tmp_path, [first, already, pending])
    # install_repo only creates matching source blocks for the record count.
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    result=manager.review_decision(build["build_id"],"r1","accepted",expected_revision=1,review_queue="all")
    assert result["applied"] is True
    assert result["next_record"]["record_id"] == "r3"
    assert result["queue_counts"]["accepted"] == 2
    assert result["queue_counts"]["pending"] == 1

def test_completed_records_unlock_progressively_while_book_enrichment_runs(tmp_path: Path):
    """Records can be reviewed and boundaries edited while enrichment runs.

    Both a finished (r1) and a still-queued (r2) record can be accepted mid-build, and a
    review marks the record "__review__" human-touched so background work will not alter
    it. Merging is allowed once topology exists and the merged Record is requeued
    because one of its inputs had already been enriched.
    """
    complete=ready_record("r1","b1")
    complete["metadata_enrichment_state"]="complete"
    queued=ready_record("r2","b2")
    queued.update({"metadata_enrichment_state":"queued","metadata_complete":False})
    repo, build = install_repo(tmp_path, [complete, queued], status="running")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    running=repo.get_build(build["build_id"]); running["status"]="running"; running["stage"]="enriching"; repo.save_build(running)

    result=manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
    assert result["applied"] is True
    assert repo.load_records(build["build_id"])[0]["accepted"] is True

    # Once segmentation exists, reviewers may work on
    # records while metadata enrichment continues. Human review freezes later
    # automatic changes to that record.
    result2=manager.review_decision(build["build_id"], "r2", "accepted", expected_revision=1)
    assert result2["applied"] is True
    assert "__review__" in repo.load_records(build["build_id"])[1].get("human_touched_fields", [])

    merged = manager.merge(build["build_id"], "r1", "next", expected_revision=2)
    assert merged["metadata_requeue_requested"] is True
    assert merged["metadata_enrichment_state"] == "stale"
    assert repo.get_build(build["build_id"])["metadata_priority_record_ids"] == ["r1"]


def test_authoritative_rewrite_reopens_impossibly_accepted_record_with_metadata_blocker(tmp_path: Path):
    """A record accepted while metadata was unresolved is reopened on the next validation.

    The authoritative rewrite sets disposition back to "pending", moves it to the
    "metadata" review state, zeroes accepted_count, and logs an "acceptance_reopened"
    event. Why: state must never claim a record is publishable when it is not.
    """
    record=ready_record("r1","b1")
    record.update({"review_disposition":"accepted","accepted":True,"position_holder":"Derrida","metadata_review_fields":["position_holder"]})
    record["metadata_field_status"]["position_holder"]={"status":"unresolved","method":"llm","confidence":.5}
    repo, build=install_repo(tmp_path,[record])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    rewritten=manager._rewrite_and_validate(build["build_id"],repo.load_records(build["build_id"]))
    persisted=repo.load_records(build["build_id"])[0]
    assert persisted["review_disposition"] == "pending"
    assert persisted["accepted"] is False
    assert persisted["review_state"] == "metadata"
    assert rewritten["accepted_count"] == 0
    assert rewritten["review_queue_counts"]["metadata"] == 1
    assert "acceptance_reopened" == persisted["review_events"][-1]["event"]

def test_ready_queue_excludes_source_metadata_and_concrete_review_exceptions(tmp_path: Path):
    """"Ready" contains only clean records.

    Four records: clean, unresolved metadata, source-quality issue, and a topology
    (boundary) exception. Each lands in exactly one queue; bulk-accept on "ready" changes
    only the clean record and leaves 3 issues.
    """
    clean=ready_record("clean","b1")
    metadata=ready_record("metadata","b2")
    metadata["metadata_review_fields"]=["position_holder"]
    metadata["metadata_field_status"]["position_holder"]={"status":"unresolved","method":"llm"}
    source=ready_record("source","b3")
    source["source_quality_issues"]=[{"code":"fragmented_glyph_layout"}]
    topology=ready_record("topology","b4")
    topology.update({"needs_review":True,"review_reason":"Forced protected boundary split requires topology review."})
    # Extra source blocks for the four records.
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    cb._json_write(repo.asset_meta_path("a"), {"asset_id":"a","sha256":"x","filename":"x.pdf","page_count":1,"block_count":4,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]})
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as h:
        for i in range(1,5): h.write(json.dumps({"block_id":f"b{i}","page":1,"bbox":[0,0,1,1],"type":"paragraph","text":f"text {i}","extraction_method":"native","confidence":1.0})+"\n")
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":1,"source_block_count":4,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":11,"provider":"ollama","model":"test","request":{},"manifest":{},"validation":{"valid":True}})
    build["status"]="ready"; build["stage"]="ready"; repo.save_build(build); repo.save_records(build["build_id"],[clean,metadata,source,topology])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    manager._rewrite_and_validate(build["build_id"],repo.load_records(build["build_id"]))
    assert repo.page_records(build["build_id"], review_queue="ready")["total"] == 1
    assert repo.page_records(build["build_id"], review_queue="metadata")["total"] == 1
    assert repo.page_records(build["build_id"], review_queue="source")["total"] == 1
    assert repo.page_records(build["build_id"], review_queue="topology")["total"] == 1
    result=manager.bulk_disposition(build["build_id"],"accepted",review_queue="ready")
    assert result["changed"] == 1
    assert result["queue_counts"]["issues"] == 3




