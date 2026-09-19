from __future__ import annotations

import json
from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.config import APP_VERSION
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA


def text(path:str)->str:
    return (ROOT/path).read_text(encoding='utf-8')


def install(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    asset={'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':2,'block_count':2,'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]}
    cb._json_write(repo.asset_meta_path('a'),asset)
    with repo.asset_blocks_path('a').open('w',encoding='utf-8') as h:
        for i in range(1,3):
            h.write(json.dumps({'block_id':f'b{i}','page':i,'bbox':[0,0,1,1],'type':'paragraph','text':f'text {i}','extraction_method':'native','confidence':1.0})+'\n')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':2,'source_block_count':2,'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':11,'app_version':APP_VERSION,'provider':'ollama','model':'test','request':{'enrichment_mode':'fast'},'manifest':{'title':'Book','document_author':'Derrida'}})
    build['status']='running';build['stage']='enriching';build['record_count']=2;repo.save_build(build)
    rows=[]
    for i in range(1,3):
        rows.append({'record_id':f'r{i}','record_revision':1,'text':f'text {i}','text_length':6,'source_asset_id':'a','source_block_ids':[f'b{i}'],'source_spans':[{'block_id':f'b{i}','page':i}],'pdf_pages':[i],'accepted':False,'rejected':False,'review_disposition':'pending','metadata_field_status':{},'metadata_stage_status':{'discourse':'queued','quotation':'queued','indexing':'queued'},'metadata_enrichment_state':'queued'})
    repo.save_records(build['build_id'],rows)
    return repo,build


def test_release_identity_and_quebec_i18n_parity():
    assert APP_VERSION=='0.57.0'
    assert '0.57.0 — Quiet Camel' in text('README.md')
    assert set(EN_US)==set(FR_CA)
    for key in ['pdf_corpus.initialization_title','pdf_corpus.source_issue_help_v48','pdf_corpus.confidence_not_reported','pdf_corpus.accept_clean_none_changed']:
        assert key in EN_US and key in FR_CA and FR_CA[key] != EN_US[key]


def test_source_issue_resolution_and_initialization_are_explicit_in_ui():
    source=text('web/src/components/CorpusSourceIssuePanel.vue')
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    init=text('web/src/components/CorpusInitializationDialog.vue')
    assert "emit('editText')" in source and "emit('openSource')" in source
    assert 'resolve_source_with_correction' in builder
    assert 'CorpusInitializationDialog' in builder
    assert 'role="dialog" aria-modal="true"' in init
    assert ':has-asset="Boolean(selectedAsset)"' in builder


def test_llm_suggestion_prefill_and_missing_confidence_are_not_fabricated_as_zero():
    panel=text('web/src/components/CorpusMetadataResolutionPanel.vue')
    backend=text('api/app/corpus_builder.py')
    field=text('web/src/components/CorpusMetadataFieldEditor.vue')
    assert 'llm_suggestion_prefilled' in field
    assert 'confidence_not_reported' in field
    assert 'confidence: float | None = Field(default=None' in backend
    assert 'region_type_consistency' in backend


def test_bulk_review_is_allowed_during_enrichment_and_marks_human_touch(tmp_path:Path):
    repo,build=install(tmp_path)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    result=manager.bulk_disposition(build['build_id'],'rejected',record_ids=['r1','r2'])
    assert result['changed']==2
    rows=repo.load_records(build['build_id'])
    assert all(row['review_disposition']=='rejected' for row in rows)
    assert all('__review__' in row.get('human_touched_fields',[]) for row in rows)


def test_new_dialogs_and_bulk_editor_have_accessible_modal_semantics_and_stories():
    manifest_dialog=text('web/src/components/DocumentManifestDialog.vue')
    shared_dialog=text('web/src/components/ui/UiDialog.vue')
    assert 'UiDialog' in manifest_dialog
    assert 'role="dialog"' in shared_dialog and 'aria-modal="true"' in shared_dialog
    source=text('web/src/components/CorpusBulkMetadataEditor.vue')
    assert 'role="dialog"' in source and 'aria-modal="true"' in source
    assert 'Initialization Dialog' in text('web/src/components/CorpusInitializationDialog.stories.ts')
    assert 'Document Metadata Dialog' in text('web/src/components/DocumentManifestDialog.stories.ts')


def test_auth_heading_regression_and_default_semantic_indexing():
    css=text('web/src/style.css')
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert '212px' not in css
    assert 'const semanticIndexing=ref(true);' in builder
