from __future__ import annotations

import json
from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app.config import APP_VERSION
from app.models import PdfCorpusBuildCreate


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def install_repo(tmp_path: Path, records: list[dict], *, status: str = "ready"):
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
    return {
        "record_id":rid,"record_revision":1,"text":"Édouard Glissant and différance","text_length":31,
        "source_block_ids":[bid],"source_spans":[{"block_id":bid,"page":1}],"pdf_pages":[1],
        "region_type":"main_text","primary_text":True,"discourse_role":"analysis",
        "metadata_field_status":{
            "region_type":{"status":"deterministic","method":"test"},
            "primary_text":{"status":"deterministic","method":"test"},
            "discourse_role":{"status":"llm_inferred","method":"llm","confidence":.96},
        },
        "metadata_incomplete_fields":[],"metadata_review_fields":[],"metadata_complete":True,
        "review_disposition":"pending","accepted":False,"rejected":False,"needs_review":False,"review_reason":"",
    }


def test_release_contract_has_one_current_profile():
    assert APP_VERSION == "0.44.0"
    assert cb.PROFILE_VERSION == "derrida-scholarly-v11"
    assert cb.METADATA_PROMPT_VERSION == "derridai-record-metadata-v7"
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    assert cb.CORPUS_PROFILES[cb.PROFILE_VERSION]["version"] == 11
    assert PdfCorpusBuildCreate(asset_id="a").profile_id == "derrida-scholarly-v11"


def test_false_primary_text_is_complete_and_human_decision_survives_manifest(tmp_path: Path):
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
    cb.PdfCorpusBuildManager._apply_manifest_metadata(updated, {"main_text_start_page":1,"main_text_end_page":2})
    assert updated["primary_text"] is False
    assert updated["metadata_field_status"]["primary_text"]["status"] == "human_confirmed"


def test_metadata_decision_is_durable_and_moves_record_out_of_metadata_queue(tmp_path: Path):
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

def test_human_review_is_read_only_while_automatic_enrichment_runs(tmp_path: Path):
    repo, build = install_repo(tmp_path, [ready_record("r1","b1")], status="running")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    running=repo.get_build(build["build_id"]); running["status"]="running"; running["stage"]="enriching"; repo.save_build(running)
    try:
        manager.review_decision(build["build_id"], "r1", "accepted", expected_revision=1)
        assert False, "review mutation must not race automatic enrichment"
    except ValueError as exc:
        assert "review unlocks" in str(exc).lower()
    try:
        manager.patch_metadata(build["build_id"], "r1", {"primary_text":False}, expected_revision=1)
        assert False, "metadata decisions must not race automatic enrichment"
    except ValueError as exc:
        assert "review unlocks" in str(exc).lower()



def test_authoritative_rewrite_reopens_impossibly_accepted_record_with_metadata_blocker(tmp_path: Path):
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


def test_review_ui_is_exception_oriented_and_read_only_during_enrichment():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    api=text("web/src/api/pdfCorpus.ts")
    panel=text("web/src/components/CorpusMetadataResolutionPanel.vue")
    assert "acceptCleanRecords" in ui
    assert "reviewQueueCounts" in ui
    assert "reviewLocked=computed(()=>buildRunning.value)" in ui
    assert "review-readonly-banner" in ui
    assert "metadataDecision" in ui and "reviewDecision" in api
    assert 'reviewQueue.value="ready"' not in ui[ui.index("async function resolveMetadataField"):ui.index("function showMetadataSource")]
    assert "acceptButtonEl.value?.focus({preventScroll:true})" in ui
    assert '@click="save(field)"' in panel
    assert ':value="false"' in panel
    assert "metadataSavingField" in ui and "metadataSavedField" in ui
    assert 'aria-controls="review-panel-metadata"' in ui
    assert 'aria-labelledby="review-tab-metadata"' in ui
    queue_tabs=text("web/src/components/CorpusReviewQueueTabs.vue")
    assert 'role="toolbar"' in queue_tabs and ':aria-pressed="modelValue===tab.id"' in queue_tabs


def test_dachshund_i18n_and_storybook_cover_exception_review():
    store=text("api/app/system_store.py")
    for key in (
        '"pdf_corpus.queue_ready"', '"pdf_corpus.accept_clean"',
        '"pdf_corpus.review_preparing_title"', '"pdf_corpus.decision_saved"', '"pdf_corpus.review_details"',
    ):
        assert store.count(key) >= 2
    stories=text("web/src/components/CorpusReviewQueueTabs.stories.ts")
    assert "ExceptionsRemain" in stories and "MetadataQueue" in stories and "LockedDuringEnrichment" in stories
    metadata_stories=text("web/src/components/CorpusMetadataResolutionPanel.stories.ts")
    assert "PrimaryTextHumanDecisionNo" in metadata_stories


def test_low_confidence_llm_review_metadata_is_forced_to_human_review():
    source = text("api/app/corpus_builder.py")
    assert 'elif confidence < minimum and value not in (None, "", []):' in source
    assert '"reason_code": "low_confidence"' in source
