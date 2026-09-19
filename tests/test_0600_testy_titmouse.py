from __future__ import annotations

import json
from pathlib import Path
import sys
import types

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb


def text(path:str)->str:
    return (ROOT/path).read_text(encoding="utf-8")


def install_asset(repo:cb.PdfCorpusRepository):
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
    asset=install_asset(repo)
    build=repo.create_build({
        "asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"book.pdf",
        "source_page_count":12,"source_block_count":1,"schema_version":cb.SCHEMA_VERSION,
        "profile_id":cb.PROFILE_VERSION,"profile_version":12,"app_version":"0.60.0",
        "provider":"ollama","model":"test-model","request":{"provider_profile_id":"primary"},
        "manifest":{},"validation":{"valid":True},
    })
    return asset,build


def test_release_identity_and_profile_versions():
    assert cb.PROFILE_VERSION=="derrida-scholarly-v12"
    assert cb.METADATA_PROMPT_VERSION=="derridai-record-metadata-v9"
    assert cb.DOCUMENT_PROMPT_VERSION=="derridai-document-manifest-v3"
    assert 'APP_VERSION = "0.60.0"' in text("api/app/config.py")
    assert json.loads(text("web/package.json"))["version"]=="0.60.0"
    assert "0.60.0 — Testy Titmouse" in text("README.md")


def test_touchup_sanitizer_removes_only_model_added_outer_separators():
    source="A sentence — with a legitimate dash.\n\n---\n\nAn internal separator remains."
    proposed="---\n"+source+"\n---"
    assert cb._sanitize_touchup_output(proposed,source)==source
    wrapped_source="---\nDeliberately wrapped source\n---"
    assert cb._sanitize_touchup_output(wrapped_source,wrapped_source)==wrapped_source
    assert cb._sanitize_touchup_output("~~~\nText\n~~~","Text")=="Text"
    assert cb._sanitize_touchup_output("```text\nText\n```","Text")=="Text"


def test_human_document_layout_cannot_be_overwritten_by_manifest_range():
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


def test_frontend_surface_and_test_contracts_are_present():
    css=text("web/src/style.css")
    history=text("web/src/components/CorpusBuildHistoryMenu.vue")
    readiness=text("web/src/components/CorpusBuildReadiness.vue")
    package=json.loads(text("web/package.json"))
    assert "--surface-overlay:#fff" in css.replace(" ","")
    assert "--surface-glass:rgba(255,255,255,.96)" in css.replace(" ","")
    assert 'data-surface="overlay"' in history
    assert "var(--surface-overlay,#fff)" in history
    assert 'data-surface="glass"' in readiness
    assert "var(--surface-glass,rgba(255,255,255,.96))" in readiness.replace(" ","")
    for script in ("test:unit","test:e2e","test:frontend"):
        assert script in package["scripts"]
    for path in ("web/vitest.config.ts","web/playwright.config.ts","web/tests/frontend/metadata-field-editor.test.ts","web/tests/e2e/corpus-builder-surfaces.spec.ts",".github/workflows/frontend.yml"):
        assert (ROOT/path).exists()


def test_new_i18n_strings_have_en_us_fr_ca_parity():
    en=text("api/app/locales/en_us.py")
    fr=text("api/app/locales/fr_ca.py")
    for key in (
        "pdf_corpus.build_history_panel",
        "pdf_corpus.llm_field_checked",
        "pdf_corpus.llm_field_not_checked",
        "pdf_corpus.llm_value_normalized",
    ):
        assert key in en and key in fr
