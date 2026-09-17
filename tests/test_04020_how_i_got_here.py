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
    assert package["version"]=="0.40.20"
    assert "0.40.20 — You're Probably Wondering How I Got Here" in text("README.md")
    ui=text("web/src/components/PdfCorpusBuilder.vue")
    assert "recordTotal.value>0" in ui
    assert "recordsLoading" in ui
    assert "retry once instead of requiring a checkbox toggle" in ui

def test_focus_view_is_record_first_and_not_pdf_viewer():
    focus=text("web/src/components/CorpusRecordFocusReview.vue")
    assert "record.text" in focus
    assert "Interpretive data" in focus
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
    build=repo.create_build({"asset_id":"pdf-test","source_sha256":"source-sha","source_filename":"test.pdf","schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":7,"app_version":"0.40.20","document_prompt_version":cb.DOCUMENT_PROMPT_VERSION,"segmentation_prompt_version":cb.SEGMENTATION_PROMPT_VERSION,"metadata_prompt_version":cb.METADATA_PROMPT_VERSION,"provider":"ollama","model":"profile-model","request":{"provider_profile_id":"primary","record_sizing":{"preferred_record_chars":1750}},"manifest":{},"validation":{"valid":True}})
    record={"record_id":"r1","record_revision":1,"text":"Record text","text_length":11,"source_asset_id":"pdf-test","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"accepted":True,"review_disposition":"accepted","needs_review":False}
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
    assert refreshed["status"]=="published"
    assert refreshed["stage"]=="published"
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
