from __future__ import annotations
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate

def text(path:str)->str:
    return (ROOT/path).read_text(encoding='utf-8')

def test_release_identity_and_profile():
    assert cb.PROFILE_VERSION=='derrida-scholarly-v10'
    assert cb.METADATA_PROMPT_VERSION=='derridai-record-metadata-v6'
    assert PdfCorpusBuildCreate(asset_id='a').profile_id=='derrida-scholarly-v10'
    assert cb.CORPUS_PROFILES['derrida-scholarly-v9']['version']==9
    assert cb.CORPUS_PROFILES[cb.PROFILE_VERSION]['review_metadata_fields']==list(cb.REVIEW_METADATA_FIELDS)
    assert json.loads(text('web/package.json'))['version']=='0.42.1'
    assert 'Bunny Rabbit - Again' in text('README.md')

def test_manifest_nullable_notes_are_normalized_not_rejected():
    manifest=cb.DocumentManifestModel.model_validate({'title':'Book','notes':None})
    assert manifest.notes==''

def test_accept_requires_uncertain_metadata_resolution_and_confirms_llm_fields(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    cb._json_write(repo.asset_meta_path('a'), {'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':1,'block_count':1,'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]})
    repo.asset_blocks_path('a').write_text(json.dumps({'block_id':'b1','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'text','extraction_method':'native','confidence':1.0})+'\n',encoding='utf-8')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':1,'source_block_count':1,'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':10,'provider':'ollama','model':'test','request':{},'manifest':{},'validation':{'valid':True}})
    record={'record_id':'r1','record_revision':1,'text':'text','text_length':4,'source_block_ids':['b1'],'source_spans':[{'block_id':'b1','page':1}], 'metadata_review_fields':['position_holder'],'metadata_field_status':{'position_holder':{'status':'unresolved','method':'llm','confidence':.52},'discourse_role':{'status':'llm_inferred','method':'llm','confidence':.95}}, 'discourse_role':'analysis','review_disposition':'pending','accepted':False,'rejected':False,'needs_review':True}
    repo.save_records(build['build_id'],[record])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    try:
        manager.set_disposition(build['build_id'],'r1','accepted',expected_revision=1)
        assert False, 'accept should require metadata resolution'
    except ValueError as exc:
        assert 'metadata' in str(exc).lower()
    updated=manager.patch_metadata(build['build_id'],'r1',{'position_holder':'Jacques Derrida'},expected_revision=1)
    assert updated['metadata_review_fields']==[]
    accepted=manager.set_disposition(build['build_id'],'r1','accepted',expected_revision=2)
    assert accepted['accepted'] is True
    assert accepted['metadata_field_status']['discourse_role']['status']=='human_confirmed'

def test_query_only_router_updates_preserve_scroll():
    router=text('web/src/router/index.ts')
    assert 'to.path===from.path?false' in router
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'scrollIntoView({block:"start"})' not in builder

def test_record_review_surfaces_metadata_panel_and_bulk_reports_blocked_metadata():
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'Object.keys(selectedRecord.metadata_field_status||{}).length>0' in builder
    assert 'bulk_done_metadata_blocked' in builder
    panel=text('web/src/components/CorpusMetadataResolutionPanel.vue')
    assert 'metadata_review_fields' in panel
    assert 'confirmed_on_accept' in panel


def test_request_validation_is_product_safe_and_optional_absence_is_reviewable():
    main=text('api/app/main.py')
    assert 'request_validation_error_handler' in main
    assert 'Pydantic' not in 'Some submitted data is invalid. Review the highlighted fields and try again.'
    panel=text('web/src/components/CorpusMetadataResolutionPanel.vue')
    assert 'confirm_no_value' in panel and 'confirmAbsent' in panel
