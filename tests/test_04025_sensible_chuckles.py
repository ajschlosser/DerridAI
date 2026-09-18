from pathlib import Path
import json
import sys, types
sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb

def text(path): return (ROOT/path).read_text(encoding="utf-8")

def test_release_contract_and_review_refresh_fix():
    package=json.loads(text("web/package.json"))
    assert package["version"]=="0.44.0"
    assert "0.44.0 — Dachshund" in text("README.md")
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    assert "reviewHydrated" in ui
    assert "for(let attempt=0;attempt<5;attempt++)" in ui
    assert "CorpusReviewQueueTabs" in ui
    assert "reviewQueue" in ui

def test_focus_view_is_record_first_and_not_pdf_viewer():
    focus=text("web/src/components/CorpusRecordFocusReview.vue")
    assert "record.text" in focus
    assert "focus-record-text" in focus
    assert "metadata_field_status" in focus
    assert 'role="tablist"' in focus
    assert "metadata_evidence" in focus
    assert "PdfEvidenceViewer" not in focus
    assert "pdfUrl" not in focus

def test_provider_defaults_do_not_restore_stale_profile_selection():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    restore=ui[ui.index("function restoreBuilderDraft"):ui.index("function persistBuilderDraft")]
    assert "selectedProviderId" not in restore
    assert "selectedReviewProviderId" not in restore
    assert "selectedProfileModel" in ui
    assert 'for(const key of ["provider","base_url","api_key"])' in ui

def _install_publishable(repo: cb.PdfCorpusRepository):
    asset={"asset_id":"pdf-test","sha256":"source-sha","filename":"test.pdf","page_count":1,"block_count":1,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path("pdf-test"),asset)
    repo.asset_blocks_path("pdf-test").write_text(json.dumps({"block_id":"b1","page":1,"bbox":[0,0,1,1],"type":"paragraph","text":"Record text","extraction_method":"native","confidence":1.0})+"\n")
    build=repo.create_build({"asset_id":"pdf-test","source_sha256":"source-sha","source_filename":"test.pdf","schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":8,"app_version":"0.44.0","document_prompt_version":cb.DOCUMENT_PROMPT_VERSION,"segmentation_prompt_version":cb.SEGMENTATION_PROMPT_VERSION,"metadata_prompt_version":cb.METADATA_PROMPT_VERSION,"provider":"ollama","model":"profile-model","request":{"provider_profile_id":"primary","record_sizing":{"preferred_record_chars":1750}},"manifest":{},"validation":{"valid":True}})
    record={"record_id":"r1","record_revision":1,"text":"Record text","text_length":11,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"accepted":True,"review_disposition":"accepted","needs_review":False,"region_type":"main_text","primary_text":True,"discourse_role":"assertion","metadata_complete":True,"metadata_incomplete_fields":[],"metadata_field_status":{"region_type":{"status":"human_confirmed"},"primary_text":{"status":"human_confirmed"},"discourse_role":{"status":"human_confirmed"}}}
    repo.save_records(build["build_id"],[record])
    build.update({"record_count":1,"accepted_count":1,"rejected_count":0,"needs_review_count":0,"validation":{"valid":True},"status":"ready","stage":"ready","progress":.98})
    repo.save_build(build)
    return build

def test_publication_namespaces_build_details_and_finishes_progress(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    publication=manager.publish(build["build_id"])
    row=json.loads(repo.publication_path(publication["publication_id"]).read_text().splitlines()[0])
    assert row["corpus_build_details"]["build_id"]==build["build_id"]
    assert row["corpus_build_details"]["provider_profile_id"]=="primary"
    assert row["corpus_build_details"]["model"]=="profile-model"
    assert row["corpus_build_details"]["record_sizing_policy"]["preferred_record_chars"]==1750
    assert "review_disposition" not in row and "accepted" not in row
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="ready"
    assert refreshed["stage"]=="ready"
    assert refreshed["publication_status"]=="published"
    assert refreshed["progress"]==1.0

def test_review_status_progress_tracks_complete_pipeline(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    records=repo.load_records(build["build_id"])
    records[0].update({"accepted":False,"review_disposition":"pending","needs_review":False})
    manager._rewrite_and_validate(build["build_id"],records)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="awaiting_review"
    assert refreshed["stage"]=="review"
    assert .90 <= refreshed["progress"] < 1.0


def test_unicode_text_normalization_preserves_foreign_names():
    assert cb._normalize_text("  Édouard   Glissant — différance; Łódź; 東京  ") == "Édouard Glissant — différance; Łódź; 東京"
    assert cb._normalize_text("Cafe\u0301") == "Café"

def test_review_queue_filter_and_bulk_disposition_are_consistent(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    records=[
        {"record_id":"r1","record_revision":1,"text":"Édouard Glissant","text_length":15,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_field_status":{"region_type":{"status":"deterministic"},"primary_text":{"status":"deterministic"},"discourse_role":{"status":"deterministic"}},"accepted":False,"rejected":False,"review_disposition":"pending","needs_review":False},
        {"record_id":"r2","record_revision":1,"text":"Jacques Derrida","text_length":15,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_field_status":{"region_type":{"status":"deterministic"},"primary_text":{"status":"deterministic"},"discourse_role":{"status":"deterministic"}},"accepted":True,"rejected":False,"review_disposition":"accepted","needs_review":False},
    ]
    repo.save_records(build["build_id"],records)
    page=repo.page_records(build["build_id"],disposition="pending")
    assert page["total"]==1 and page["items"][0]["record_id"]=="r1"
    result=manager.bulk_disposition(build["build_id"],"accepted",filter_disposition="pending")
    assert result["changed"]==1
    refreshed=repo.load_records(build["build_id"])
    assert all(row["review_disposition"]=="accepted" for row in refreshed)

def test_record_review_actions_are_not_auto_publish_side_effects():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    assert "finalizeIfReady" not in ui
    assert "await pdfCorpusApi.disposition" in ui
    assert "await pdfCorpusApi.bulkDisposition" in ui
    assert "Accept & next" in ui
    assert "Technical build details" in text("api/app/system_store.py")

def test_storybook_covers_queue_and_lifecycle():
    assert (ROOT/"web/src/components/CorpusReviewQueueTabs.stories.ts").exists()
    assert (ROOT/"web/src/components/CorpusBuildLifecycleCard.stories.ts").exists()

def test_metadata_incomplete_creates_explicit_attention_state_and_blocks_publish(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    build=repo.get_build(build["build_id"])
    rows=repo.load_records(build["build_id"])
    rows[0]["metadata_complete"]=False
    rows[0]["metadata_incomplete_fields"]=["discourse_role"]
    rows[0].pop("discourse_role",None)
    manager._rewrite_and_validate(build["build_id"],rows)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="awaiting_review"
    assert refreshed["stage"]=="review"
    assert refreshed["metadata_issue_summary"]["fields_unresolved"] == 1
    try:
        manager.publish(build["build_id"])
    except ValueError as exc:
        assert "metadata is complete for 0 of 1" in str(exc)
    else:
        raise AssertionError("publication should be blocked by incomplete metadata")

def test_publication_is_snapshot_state_not_build_processing_state(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_install_publishable(repo)
    manager.publish(build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="ready"
    assert refreshed["stage"]=="ready"
    assert refreshed["publication_status"]=="published"
    assert refreshed["publication"]


def test_running_build_hydrates_intermediate_records_without_form_interaction():
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    assert "hydratedTopologyCount" in ui
    assert "Number(currentBuild.value?.record_count||0)>hydratedTopologyCount.value" in ui
    assert "await refreshRecords(true)" in ui
    assert "ensureReviewHydrated" in ui
    assert 'flush:"post"' in ui
    assert 'reviewQueue=ref<ReviewQueue>("all")' in ui
    assert 'reviewQueue.value="metadata"' in ui

def test_pdf_worker_lifecycle_uses_worker_src_and_awaited_single_teardown_path():
    viewer=text("web/src/components/PdfEvidenceViewer.vue")
    assert "GlobalWorkerOptions.workerSrc = PdfWorkerUrl" in viewer
    assert "workerPort" not in viewer
    assert "await task.destroy?.()" in viewer
    assert "await doc.destroy?.()" in viewer

def test_new_builds_start_unpublished_and_storybook_uses_snapshot_semantics(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"s","source_filename":"x.pdf"})
    assert build["publication_status"]=="unpublished"
    lifecycle=text("web/src/components/CorpusBuildLifecycleCard.stories.ts")
    stepper=text("web/src/components/CorpusWorkflowStepper.stories.ts")
    assert 'status:"ready",stage:"ready",progress:1' in lifecycle
    assert 'publication_status:"published"' in lifecycle
    assert 'stage:"ready",status:"ready",acceptedCount:84,published:true' in stepper
