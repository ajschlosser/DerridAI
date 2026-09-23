"""Hybrid deterministic/LLM metadata, review state, and Unicode safety.

Why: required fields (region type, primary text, discourse role) combine
deterministic rules with a constrained LLM, and every field must record where its
value came from. Review actions must change state reliably.
How: `install_asset`/`make_build` create a small build; the LLM (`_chat_json`) is
replaced by canned responses so the reconciliation logic is what is being tested.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def install_asset(repo:cb.PdfCorpusRepository, count:int=2):
    """Write an asset and its blocks (with accented names) into the temp repository."""
    asset={"asset_id":"asset-aardvark","sha256":"sha","filename":"book.pdf","page_count":2,"block_count":count,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path(asset["asset_id"]),asset)
    lines=[]
    for i in range(count):
        lines.append(json.dumps({"block_id":f"b{i+1}","page":i+1,"bbox":[0,0,100,100],"type":"paragraph","text":f"Passage {i+1} — Édouard Glissant and différance.","extraction_method":"native","confidence":1.0},ensure_ascii=False))
    repo.asset_blocks_path(asset["asset_id"]).write_text("\n".join(lines)+"\n",encoding="utf-8")
    return asset


def make_build(repo:cb.PdfCorpusRepository,count:int=2):
    """Create the asset plus a build referring to it; returns (asset, build)."""
    asset=install_asset(repo,count)
    build=repo.create_build({"asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"book.pdf","source_page_count":2,"source_block_count":count,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":8,"app_version":"0.60.0","provider":"ollama","model":"test-model","request":{"provider_profile_id":"primary"},"manifest":{},"validation":{"valid":True}})
    return asset,build


def test_profile_requires_region_type_primary_text_and_discourse_role():
    """Pin profile/prompt ids and the required metadata fields.

    Required fields are region_type, primary_text and discourse_role; the profile must
    list main_text and analysis as allowed values. (Name says v8 for history; the ids now
    checked are the current ones.)
    """
    assert cb.PROFILE_VERSION=="derrida-scholarly-v12"
    assert cb.METADATA_PROMPT_VERSION=="derridai-record-metadata-v11"
    assert PdfCorpusBuildCreate(asset_id="a").profile_id=="derrida-scholarly-v12"
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["required_metadata_fields"]==["region_type","primary_text","discourse_role"]
    assert "main_text" in profile["region_types"]
    assert "analysis" in profile["discourse_roles"]
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}


def test_hybrid_metadata_uses_constrained_llm_and_tracks_field_provenance(tmp_path:Path,monkeypatch):
    """LLM output fills fields and provenance shows which value came from where.

    The prompt must tell the model to choose from closed vocabularies. With a confident
    reply: region_type and discourse_role are "model_inferred", primary_text is
    "deterministic" (derived from region type), and the record is metadata-complete.
    """
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
    assert record["metadata_field_status"]["region_type"]["status"]=="model_inferred"
    assert record["metadata_field_status"]["primary_text"]["status"]=="deterministic"
    assert record["metadata_field_status"]["primary_text"]["method"]=="region_type_consistency"
    assert record["metadata_field_status"]["discourse_role"]["status"]=="model_inferred"


def test_manifest_llm_disagreement_is_prefilled_for_review(tmp_path:Path,monkeypatch):
    """When the LLM contradicts reviewer-defined structure, the human value stays selected.

    The manifest says main text is page 1; the model says front matter. Expect
    region_type/primary_text keep their deterministic values, status "unresolved" with
    reason deterministic_llm_disagreement, both candidates retained, and llm_checked
    True. Why: reviewer-defined structure outranks a model opinion, but the disagreement
    must be visible.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo,1)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={"record_id":"r1","record_revision":1,"text":"Main text.","text_length":10,"pdf_pages":[1],"source_asset_id":"asset-aardvark","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1,"confidence":1.0}],"region_type":"main_text","primary_text":True,"metadata_field_status":{"region_type":{"status":"deterministic","method":"human_document_layout","confidence":.99,"reason":"Reviewer-defined document structure."},"primary_text":{"status":"deterministic","method":"human_document_layout","confidence":.99,"reason":"Reviewer-defined document structure."}}}
    def fake_chat(_request,prompt,*,response_model,max_tokens,schema_name,build_id=""):
        if schema_name=="derridai_record_discourse":
            return {"metadata":{"region_type":"front_matter","primary_text":False,"discourse_role":"assertion"},"field_evidence":{"region_type":{"block_ids":["b1"],"confidence":.99,"reason":"model"},"primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"model"},"discourse_role":{"block_ids":["b1"],"confidence":.99,"reason":"assertion"}},"field_assessments":{"region_type":{"confidence":.99,"needs_review":False,"reason":"model","outcome":"supported_value"},"primary_text":{"confidence":.99,"needs_review":False,"reason":"model","outcome":"supported_value"},"discourse_role":{"confidence":.99,"needs_review":False,"reason":"assertion","outcome":"supported_value"}},"review_reason":""}
        if schema_name=="derridai_record_quotation": return {"metadata":{},"field_evidence":{},"review_reason":""}
        return {"metadata":{},"review_reason":""}
    monkeypatch.setattr(manager,"_chat_json",fake_chat)
    manager._enrich_record(record,{"main_text_start_page":1,"main_text_end_page":1},{"provider":"ollama","model":"test-model"},build_id=build["build_id"])
    # The pipeline preserves reviewer-defined document structure as the selected
    # value while retaining the semantic reader's disagreement for explicit review.
    assert record["region_type"]=="main_text"
    assert record["primary_text"] is True
    assert record["metadata_field_status"]["primary_text"]["status"]=="unresolved"
    assert record["metadata_field_status"]["primary_text"]["reason_code"]=="deterministic_llm_disagreement"
    assert record["metadata_field_status"]["region_type"]["status"]=="unresolved"
    assert record["metadata_field_status"]["region_type"]["llm_corroborates"] is False
    assert record["metadata_field_status"]["region_type"]["deterministic_value"]=="main_text"
    assert record["metadata_field_status"]["region_type"]["llm_value"]=="front_matter"
    assert record["metadata_field_status"]["region_type"]["prefilled_candidate"]=="deterministic"
    assert record["metadata_field_status"]["region_type"]["llm_checked"] is True


def test_metadata_issue_summary_and_metadata_queue_are_derived_from_records(tmp_path:Path):
    """Issue counts and the metadata queue are computed from the records themselves.

    Two accepted records, one missing discourse_role: 1 of 2 complete, 1 incomplete, the
    by-field summary names discourse_role, and the metadata_incomplete filter returns r2.
    """
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
    """Accept, reject, and bulk-accept-the-rejected update the stored state."""
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








def test_unicode_is_preserved_in_normalization_and_json_serialization():
    """Accents, Polish, Greek, and CJK survive normalization and JSON encoding.

    Why: names like Cixous, Glissant, and Łódź must never be mangled or ASCII-escaped.
    """
    original="Hélène Cixous · Édouard Glissant · différance · Łódź · Ελληνικά · 東京"
    assert cb._normalize_text(original)==original
    encoded=json.dumps({"text":original},ensure_ascii=False)
    assert original in encoded
