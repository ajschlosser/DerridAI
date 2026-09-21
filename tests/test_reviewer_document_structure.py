"""Reviewer-owned document structure, touch-up sanitizing, and confident stance.

Why: a reviewer can declare where the main text starts and where bibliography begins. That
structure is authoritative: an LLM or a page-range guess may disagree, but must not replace it.
Text touch-ups must not leak model-added separators. Confident closed-vocabulary values
(like "stance") must be normalized and filled in automatically.
How: `install_asset` / `make_build` create a 12-page build whose layout says main text starts on
PDF page 3; the LLM (`_chat_json`) is replaced with canned replies.
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


def install_asset(repo:cb.PdfCorpusRepository):
    """Write a 12-page asset whose human-confirmed layout puts main text at PDF page 3, with one block on page 9."""
    asset={
        "asset_id":"asset-testy-titmouse","sha256":"sha","filename":"book.pdf",
        "page_count":12,"block_count":1,"ocr_pages":0,"warnings":[],"metadata":{},
        "pages":[{"pdf_page":page,"width":600,"height":800} for page in range(1,13)],
        "document_layout":{
            "page_layout":"single","reading_order":"left_to_right",
            "main_text_pdf_start":3,"main_text_printed_start":1,
            "bibliography_pdf_start":None,"thread_mode":"continuous",
            "confirmed_by":"human",
        },
    }
    cb._json_write(repo.asset_meta_path(asset["asset_id"]),asset)
    repo.asset_blocks_path(asset["asset_id"]).write_text(json.dumps({
        "block_id":"b1","page":9,"bbox":[0,0,100,100],"type":"paragraph",
        "text":"Derrida explicitly affirms this proposition.","extraction_method":"native","confidence":1.0,
        "deterministic_region_type":"main_text",
    })+"\n",encoding="utf-8")
    return asset


def make_build(repo:cb.PdfCorpusRepository):
    """Create the asset and a build for it; returns (asset, build)."""
    asset=install_asset(repo)
    build=repo.create_build({
        "asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"book.pdf",
        "source_page_count":12,"source_block_count":1,"schema_version":cb.SCHEMA_VERSION,
        "profile_id":cb.PROFILE_VERSION,"profile_version":12,"app_version":"0.60.0",
        "provider":"ollama","model":"test-model","request":{"provider_profile_id":"primary"},
        "manifest":{},"validation":{"valid":True},
    })
    return asset,build


def test_profile_and_prompt_version_ids_are_pinned():
    """Pin the profile, metadata prompt, and document-manifest prompt version ids."""
    assert cb.PROFILE_VERSION=="derrida-scholarly-v12"
    assert cb.METADATA_PROMPT_VERSION=="derridai-record-metadata-v11"
    assert cb.DOCUMENT_PROMPT_VERSION=="derridai-document-manifest-v3"


def test_touchup_sanitizer_removes_only_model_added_outer_separators():
    """Strip "---", "~~~", or code fences a model wrapped around text, but nothing else.

    Separators inside the text stay, and a source that legitimately starts/ends with "---" is left
    alone. Why: touch-ups must not change the text apart from what the reviewer asked for.
    """
    source="A sentence — with a legitimate dash.\n\n---\n\nAn internal separator remains."
    proposed="---\n"+source+"\n---"
    assert cb._sanitize_touchup_output(proposed,source)==source
    wrapped_source="---\nDeliberately wrapped source\n---"
    assert cb._sanitize_touchup_output(wrapped_source,wrapped_source)==wrapped_source
    assert cb._sanitize_touchup_output("~~~\nText\n~~~","Text")=="Text"
    assert cb._sanitize_touchup_output("```text\nText\n```","Text")=="Text"


def test_human_document_layout_cannot_be_overwritten_by_manifest_range():
    """A manifest page range never overrides reviewer-defined layout.

    The record on PDF page 9 is main text by reviewer layout; a bad manifest range (main text starts on
    page 11) would call it front matter, but region_type/primary_text and their
    "human_document_layout" method must not change.
    """
    record={
        "record_id":"r1","pdf_pages":[9],"region_type":"main_text","primary_text":True,
        "metadata_field_status":{
            "region_type":{"status":"deterministic","method":"human_document_layout","confidence":.99},
            "primary_text":{"status":"deterministic","method":"human_document_layout","confidence":.99},
        },
    }
    # Deliberately bad manifest range would classify PDF 9 as front matter.
    cb.PdfCorpusBuildManager._apply_manifest_metadata(record,{"main_text_start_page":11})
    assert record["region_type"]=="main_text"
    assert record["primary_text"] is True
    assert record["metadata_field_status"]["region_type"]["method"]=="human_document_layout"
    assert record["metadata_field_status"]["primary_text"]["method"]=="human_document_layout"


def test_llm_disagreement_is_recorded_but_reviewer_structure_stays_selected(tmp_path:Path,monkeypatch):
    """The LLM may disagree with reviewer structure; the disagreement is kept, the value is not.

    The model says "front_matter / not primary text" at 96% confidence. The record stays main text, and
    the status keeps both values, marks llm_checked, prefills the deterministic candidate, and is
    not auto-populated with the LLM value.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={
        "record_id":"r1","record_revision":1,"text":"Substantive main text.",
        "text_length":22,"pdf_pages":[9],"source_asset_id":"asset-testy-titmouse",
        "source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":9,"confidence":1.0}],
        "region_type":"main_text","primary_text":True,
        "metadata_field_status":{
            "region_type":{"status":"deterministic","method":"human_document_layout","confidence":.99,"reason":"Reviewer structure."},
            "primary_text":{"status":"deterministic","method":"human_document_layout","confidence":.99,"reason":"Reviewer structure."},
        },
    }
    def fake_chat(_request,_prompt,*,response_model,max_tokens,schema_name,build_id=""):
        if schema_name=="derridai_record_discourse":
            return {
                "metadata":{"region_type":"front_matter","primary_text":False,"discourse_role":"analysis"},
                "field_evidence":{
                    "region_type":{"block_ids":["b1"],"confidence":.96,"reason":"Semantic reader disagrees."},
                    "primary_text":{"block_ids":["b1"],"confidence":.96,"reason":"Semantic reader disagrees."},
                    "discourse_role":{"block_ids":["b1"],"confidence":.9,"reason":"Analysis."},
                },
                "field_assessments":{
                    "region_type":{"confidence":.96,"needs_review":False,"reason":"Semantic reader disagrees."},
                    "primary_text":{"confidence":.96,"needs_review":False,"reason":"Semantic reader disagrees."},
                    "discourse_role":{"confidence":.9,"needs_review":False,"reason":"Analysis."},
                },
                "review_reason":"",
            }
        return {"metadata":{},"field_evidence":{},"field_assessments":{},"review_reason":""}
    monkeypatch.setattr(manager,"_chat_json",fake_chat)
    manager._enrich_record(record,{},{"provider":"ollama","model":"test-model","enrichment_mode":"fast","semantic_indexing":False},build_id=build["build_id"])
    status=record["metadata_field_status"]["region_type"]
    assert record["region_type"]=="main_text"
    assert record["primary_text"] is True
    assert status["reason_code"]=="deterministic_llm_disagreement"
    assert status["deterministic_value"]=="main_text"
    assert status["llm_value"]=="front_matter"
    assert status["llm_checked"] is True
    assert status["prefilled_candidate"]=="deterministic"
    assert status["auto_populated"] is False


def test_confident_stance_alias_is_normalized_and_auto_populated(tmp_path:Path,monkeypatch):
    """"affirmed" at 91% confidence becomes the vocabulary value "affirm" and is auto-filled.

    The raw model text is kept in raw_llm_value for audit, and the field records its confidence and
    proposed value. Why: the >65% rule should fill fields even when the model uses a near-synonym.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    _asset,build=make_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={
        "record_id":"r2","record_revision":1,"text":"Derrida explicitly affirms this proposition.",
        "text_length":43,"pdf_pages":[9],"source_asset_id":"asset-testy-titmouse",
        "source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":9,"confidence":1.0}],
        "region_type":"main_text","primary_text":True,
        "metadata_field_status":{
            "region_type":{"status":"deterministic","method":"human_document_layout","confidence":.99},
            "primary_text":{"status":"deterministic","method":"human_document_layout","confidence":.99},
        },
    }
    def fake_chat(_request,_prompt,*,response_model,max_tokens,schema_name,build_id=""):
        if schema_name=="derridai_record_discourse":
            return {
                "metadata":{"region_type":"main_text","primary_text":True,"discourse_role":"assertion","stance":"affirmed"},
                "field_evidence":{
                    "region_type":{"block_ids":["b1"],"confidence":.99,"reason":"Main text."},
                    "primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"Main text."},
                    "discourse_role":{"block_ids":["b1"],"confidence":.9,"reason":"Assertion."},
                    "stance":{"block_ids":["b1"],"confidence":.91,"reason":"Explicit endorsement."},
                },
                "field_assessments":{
                    "region_type":{"confidence":.99,"needs_review":False,"reason":"Main text."},
                    "primary_text":{"confidence":.99,"needs_review":False,"reason":"Main text."},
                    "discourse_role":{"confidence":.9,"needs_review":False,"reason":"Assertion."},
                    "stance":{"confidence":.91,"needs_review":False,"reason":"Explicit endorsement."},
                },
                "review_reason":"",
            }
        return {"metadata":{},"field_evidence":{},"field_assessments":{},"review_reason":""}
    monkeypatch.setattr(manager,"_chat_json",fake_chat)
    manager._enrich_record(record,{},{"provider":"ollama","model":"test-model","enrichment_mode":"fast","semantic_indexing":False},build_id=build["build_id"])
    assert record["stance"]=="affirm"
    status=record["metadata_field_status"]["stance"]
    assert status["auto_populated"] is True
    assert status["confidence"]==.91
    assert status["proposed_value"]=="affirm"
    assert status["raw_llm_value"]=="affirmed"
    assert status["llm_checked"] is True




