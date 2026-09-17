from __future__ import annotations

import json
from pathlib import Path
import sys, types

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def text(path:str)->str:
    return (ROOT/path).read_text(encoding="utf-8")


def install_asset(repo:cb.PdfCorpusRepository, count:int=2):
    asset={"asset_id":"asset-aardvark","sha256":"sha","filename":"book.pdf","page_count":2,"block_count":count,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path(asset["asset_id"]),asset)
    lines=[]
    for i in range(count):
        lines.append(json.dumps({"block_id":f"b{i+1}","page":i+1,"bbox":[0,0,100,100],"type":"paragraph","text":f"Passage {i+1} — Édouard Glissant and différance.","extraction_method":"native","confidence":1.0},ensure_ascii=False))
    repo.asset_blocks_path(asset["asset_id"]).write_text("\n".join(lines)+"\n",encoding="utf-8")
    return asset


def make_build(repo:cb.PdfCorpusRepository,count:int=2):
    asset=install_asset(repo,count)
    build=repo.create_build({"asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"book.pdf","source_page_count":2,"source_block_count":count,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":8,"app_version":"0.42.1","provider":"ollama","model":"test-model","request":{"provider_profile_id":"primary"},"manifest":{},"validation":{"valid":True}})
    return asset,build


def test_release_contract_is_v8_with_field_aware_metadata():
    assert cb.PROFILE_VERSION=="derrida-scholarly-v10"
    assert cb.METADATA_PROMPT_VERSION=="derridai-record-metadata-v6"
    assert PdfCorpusBuildCreate(asset_id="a").profile_id=="derrida-scholarly-v10"
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["version"]==10
    assert profile["required_metadata_fields"]==["region_type","primary_text","discourse_role"]
    assert "main_text" in profile["region_types"]
    assert "analysis" in profile["discourse_roles"]
    assert cb.CORPUS_PROFILES["derrida-scholarly-v7"]["version"]==7


def test_hybrid_metadata_uses_constrained_llm_and_tracks_field_provenance(tmp_path:Path,monkeypatch):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo,1)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={"record_id":"r1","record_revision":1,"text":"Derrida analyzes hospitality.","text_length":30,"source_asset_id":"asset-aardvark","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1,"confidence":1.0}]}
    def fake_chat(_request,prompt,*,response_model,max_tokens,schema_name,build_id=""):
        if schema_name=="derridai_record_discourse":
            assert "region_type MUST be one of" in prompt
            assert "primary_text MUST be true or false" in prompt
            return {"metadata":{"region_type":"main_text","primary_text":True,"discourse_role":"analysis","speaker":"Jacques Derrida"},"field_evidence":{"region_type":{"block_ids":["b1"],"confidence":.98,"reason":"Substantive essay body."},"primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"Substantive argument."},"discourse_role":{"block_ids":["b1"],"confidence":.94,"reason":"Analytical exposition."},"speaker":{"block_ids":["b1"],"confidence":.95,"reason":"Document voice."}},"review_reason":""}
        if schema_name=="derridai_record_quotation":
            return {"metadata":{},"field_evidence":{},"review_reason":""}
        return {"metadata":{"topics":["hospitality"]},"review_reason":""}
    monkeypatch.setattr(manager,"_chat_json",fake_chat)
    manager._enrich_record(record,{}, {"provider":"ollama","model":"test-model"},build_id=build["build_id"])
    assert record["region_type"]=="main_text"
    assert record["primary_text"] is True
    assert record["discourse_role"]=="analysis"
    assert record["metadata_complete"] is True
    assert record["metadata_incomplete_fields"]==[]
    assert record["metadata_field_status"]["region_type"]["status"]=="llm_inferred"
    assert record["metadata_field_status"]["primary_text"]["status"]=="llm_inferred"
    assert record["metadata_field_status"]["discourse_role"]["status"]=="llm_inferred"


def test_manifest_determinism_outranks_model_for_primary_text(tmp_path:Path,monkeypatch):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo,1)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={"record_id":"r1","record_revision":1,"text":"Main text.","text_length":10,"pdf_pages":[1],"source_asset_id":"asset-aardvark","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1,"confidence":1.0}]}
    def fake_chat(_request,prompt,*,response_model,max_tokens,schema_name,build_id=""):
        if schema_name=="derridai_record_discourse":
            return {"metadata":{"region_type":"front_matter","primary_text":False,"discourse_role":"assertion"},"field_evidence":{"region_type":{"block_ids":["b1"],"confidence":.99,"reason":"model"},"primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"model"},"discourse_role":{"block_ids":["b1"],"confidence":.99,"reason":"assertion"}},"review_reason":""}
        if schema_name=="derridai_record_quotation": return {"metadata":{},"field_evidence":{},"review_reason":""}
        return {"metadata":{},"review_reason":""}
    monkeypatch.setattr(manager,"_chat_json",fake_chat)
    manager._enrich_record(record,{"main_text_start_page":1,"main_text_end_page":1},{"provider":"ollama","model":"test-model"},build_id=build["build_id"])
    assert record["primary_text"] is True
    assert record["region_type"]=="main_text"
    assert record["metadata_field_status"]["primary_text"]["status"]=="deterministic"
    assert record["metadata_field_status"]["region_type"]["status"]=="deterministic"


def test_metadata_issue_summary_and_metadata_queue_are_derived_from_records(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo,2)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    records=[
        {"record_id":"r1","record_revision":1,"text":"Passage 1 — Édouard Glissant and différance.","text_length":44,"source_asset_id":"asset-aardvark","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1}],"accepted":True,"review_disposition":"accepted","needs_review":False,"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_complete":True,"metadata_incomplete_fields":[]},
        {"record_id":"r2","record_revision":1,"text":"Passage 2 — Édouard Glissant and différance.","text_length":44,"source_asset_id":"asset-aardvark","source_block_ids":["b2"],"source_spans":[{"block_id":"b2","page":2}],"accepted":True,"review_disposition":"accepted","needs_review":False,"region_type":"main_text","primary_text":True,"metadata_complete":False,"metadata_incomplete_fields":["discourse_role"],"metadata_field_status":{"discourse_role":{"status":"unresolved"}}},
    ]
    manager._rewrite_and_validate(build["build_id"],records)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["metadata_completed"]==1
    assert refreshed["metadata_total"]==2
    assert refreshed["metadata_issue_summary"]["records_incomplete"]==1
    assert refreshed["metadata_issue_summary"]["by_field"]=={"discourse_role":1}
    page=repo.page_records(build["build_id"],metadata_incomplete=True)
    assert page["total"]==1 and page["items"][0]["record_id"]=="r2"


def test_accept_reject_and_bulk_disposition_mutate_review_state_reliably(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo,2)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    base=lambda rid,bid,page:{"record_id":rid,"record_revision":1,"text":f"Passage {page} — Édouard Glissant and différance.","text_length":44,"source_asset_id":"asset-aardvark","source_block_ids":[bid],"source_spans":[{"block_id":bid,"page":page}],"accepted":False,"rejected":False,"review_disposition":"pending","needs_review":False,"region_type":"main_text","primary_text":True,"discourse_role":"analysis","metadata_complete":True,"metadata_incomplete_fields":[]}
    repo.save_records(build["build_id"],[base("r1","b1",1),base("r2","b2",2)])
    accepted=manager.set_disposition(build["build_id"],"r1","accepted",expected_revision=1)
    assert accepted["accepted"] is True and accepted["review_disposition"]=="accepted"
    rejected=manager.set_disposition(build["build_id"],"r2","rejected",expected_revision=1)
    assert rejected["rejected"] is True and rejected["review_disposition"]=="rejected"
    result=manager.bulk_disposition(build["build_id"],"accepted",filter_disposition="rejected")
    assert result["changed"]==1
    rows=repo.load_records(build["build_id"])
    assert all(row["review_disposition"]=="accepted" for row in rows)


def test_focus_review_is_full_screen_portaled_record_first_and_accessible():
    builder=text("web/src/components/PdfCorpusBuilder.vue")
    focus=text("web/src/components/CorpusRecordFocusReview.vue")
    assert '<Teleport to="body">' in builder
    assert 'position:fixed;inset:0;z-index:10000' in focus
    assert 'role="dialog" aria-modal="true"' in focus
    assert 'focus-record-text' in focus
    assert 'metadata_field_status' in focus
    assert 'role="tablist"' in focus
    assert 'Escape' in focus and 'event.key!=="Tab"' in focus


def test_pipeline_hydration_and_completion_are_explicit_without_form_interaction():
    builder=text("web/src/components/PdfCorpusBuilder.vue")
    lifecycle=text("web/src/components/CorpusBuildLifecycleCard.vue")
    assert "ensureReviewHydrated" in builder
    assert "window.setTimeout" in builder
    assert 'flush:"post"' in builder
    assert "CorpusFinishWorkspace" in builder and "CorpusMetadataResolutionPanel" in builder
    assert "CorpusMetadataIssues" in builder
    assert "metadataIncompleteOnly" in builder
    for label in ["Extract source","Construct records","Enrich metadata","Validate corpus","Publish snapshot"]:
        assert label in lifecycle


def test_storybook_covers_aardvark_workflow_surfaces():
    for name in ["CorpusMetadataIssues.stories.ts","CorpusFinishWorkspace.stories.ts","CorpusMetadataResolutionPanel.stories.ts","CorpusBuildTimeline.stories.ts","CorpusRecordFocusReview.stories.ts"]:
        assert (ROOT/"web/src/components"/name).exists()


def test_unicode_is_preserved_in_normalization_and_json_serialization():
    original="Hélène Cixous · Édouard Glissant · différance · Łódź · Ελληνικά · 東京"
    assert cb._normalize_text(original)==original
    encoded=json.dumps({"text":original},ensure_ascii=False)
    assert original in encoded
