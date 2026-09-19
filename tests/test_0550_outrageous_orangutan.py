from __future__ import annotations
import json, sys, types
from pathlib import Path
try:
    import chromadb  # type: ignore  # noqa
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.config import APP_VERSION
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA

def text(path:str)->str:return (ROOT/path).read_text(encoding='utf-8')

def install(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    asset={'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':2,'block_count':4,'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]}
    cb._json_write(repo.asset_meta_path('a'),asset)
    blocks=[
        {'block_id':'b1','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'A complete opening sentence.','extraction_method':'native','confidence':1.0},
        {'block_id':'b2','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'A thought that continues','extraction_method':'native','confidence':1.0},
        {'block_id':'b3','page':2,'bbox':[0,0,1,1],'type':'paragraph','text':'into the next block and then ends.','extraction_method':'native','confidence':1.0},
        {'block_id':'b4','page':2,'bbox':[0,0,1,1],'type':'paragraph','text':'A new unit begins here.','extraction_method':'native','confidence':1.0},
    ]
    with repo.asset_blocks_path('a').open('w',encoding='utf-8') as h:
        for b in blocks:h.write(json.dumps(b)+'\n')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':2,'source_block_count':4,'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':11,'app_version':APP_VERSION,'provider':'ollama','model':'test','request':{'provider':'ollama','model':'test'},'manifest':{'title':'Book','document_author':'Derrida'}})
    build.update(status='running',stage='enriching',record_count=2);repo.save_build(build)
    rows=[
        {'record_id':'r1','record_revision':1,'text':'A complete opening sentence.\n\nA thought that continues','text_length':54,'source_block_ids':['b1','b2'],'source_spans':[{'block_id':'b1','page':1},{'block_id':'b2','page':1}],'metadata_field_status':{},'metadata_stage_status':{},'review_disposition':'pending','accepted':False,'rejected':False,'boundary_quality_issues':[{'code':'boundary_suspect','edge':'end','reason':'Possible sentence/quotation continuation across this record boundary.'}],'needs_review':True,'review_reason':'Possible sentence/quotation continuation across this record boundary.'},
        {'record_id':'r2','record_revision':1,'text':'into the next block and then ends.\n\nA new unit begins here.','text_length':57,'source_block_ids':['b3','b4'],'source_spans':[{'block_id':'b3','page':2},{'block_id':'b4','page':2}],'metadata_field_status':{},'metadata_stage_status':{},'review_disposition':'pending','accepted':False,'rejected':False,'boundary_quality_issues':[{'code':'boundary_suspect','edge':'start','reason':'Possible sentence/quotation continuation across this record boundary.'}],'needs_review':True,'review_reason':'Possible sentence/quotation continuation across this record boundary.'},
    ]
    repo.save_records(build['build_id'],rows)
    return repo,build

def test_release_identity_and_quebec_i18n():
    assert APP_VERSION=='0.58.0'
    assert json.loads(text('web/package.json'))['version']=='0.58.0'
    assert '0.58.0 — Righteous Rhinoceros' in text('README.md')
    assert set(EN_US)==set(FR_CA)
    for key in ['pdf_corpus.boundary_second_reader','pdf_corpus.check_with_llm','pdf_corpus.boundary_llm.move_later']:
        assert key in EN_US and key in FR_CA and EN_US[key]!=FR_CA[key]

def test_second_reader_keep_corroboration_clears_only_heuristic_boundary_warning():
    left={'boundary_quality_issues':[{'code':'boundary_suspect','edge':'end','reason':'x'}],'needs_review':True,'review_reason':'Possible sentence/quotation continuation across this record boundary.'}
    right={'boundary_quality_issues':[{'code':'boundary_suspect','edge':'start','reason':'x'}],'needs_review':True,'review_reason':'Possible sentence/quotation continuation across this record boundary.'}
    decision={'decision':'keep','confidence':.91,'reason':'Coherent boundary','suggested_after_block_id':'b2'}
    cb.PdfCorpusBuildManager._apply_boundary_adjudication_to_records(left,right,decision,threshold=.72)
    assert left.get('boundary_quality_issues') is None
    assert right.get('boundary_quality_issues') is None
    assert left['boundary_llm_after']['decision']=='keep'
    assert right['boundary_llm_before']['confidence']==.91
    assert left['review_reason']=='Pending human review.'

def test_second_reader_move_is_a_review_recommendation_not_an_automatic_rewrite():
    left={'text':'left','source_block_ids':['b1','b2'],'review_disposition':'pending'}
    right={'text':'right','source_block_ids':['b3','b4'],'review_disposition':'pending'}
    before=(left['text'],right['text'])
    decision={'decision':'move_later','confidence':.84,'reason':'Quotation continues.','suggested_after_block_id':'b3'}
    cb.PdfCorpusBuildManager._apply_boundary_adjudication_to_records(left,right,decision,threshold=.72)
    assert (left['text'],right['text'])==before
    assert 'Boundary review required' in left['review_reason']
    assert left['boundary_quality_issues'][-1]['suggested_after_block_id']=='b3'

def test_on_demand_boundary_check_persists_provenance_without_moving_text(tmp_path:Path,monkeypatch):
    repo,build=install(tmp_path);manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    manager._runtime_requests[build['build_id']]={'provider':'ollama','model':'test'}
    monkeypatch.setattr(manager,'_adjudicate_record_boundary_pair',lambda left,right,manifest,request,build_id:{'boundary_id':'r1->r2','decision':'move_later','suggested_after_block_id':'b3','current_after_block_id':'b2','confidence':.88,'signals':['sentence_continuation'],'reason':'The sentence continues.','source':'llm_boundary_audit','adjudicated_at':cb.iso_now()})
    result=manager.adjudicate_record_boundary(build['build_id'],'r1','next')
    rows=repo.load_records(build['build_id'])
    assert result['decision']['decision']=='move_later'
    assert rows[0]['text'].startswith('A complete opening')
    assert rows[1]['text'].startswith('into the next')
    assert rows[0]['boundary_llm_after']['suggested_after_block_id']=='b3'

def test_human_slice_becomes_boundary_editorial_memory(tmp_path:Path):
    repo,build=install(tmp_path);manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    row=repo.load_records(build['build_id'])[1]
    cut=row['text'].index('A new unit')
    manager.slice_to_neighbor(build['build_id'],'r2','previous',cut,1)
    memory=repo.load_checkpoint(build['build_id'],'boundary_editorial_memory',{})
    assert memory['examples']
    assert memory['examples'][-1]['source']=='human_confirmed_boundary'

def test_storybook_and_focus_view_share_boundary_second_reader_component():
    comp=text('web/src/components/CorpusBoundaryAdjudication.vue')
    story=text('web/src/components/CorpusBoundaryAdjudication.stories.ts')
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    focus=text('web/src/components/CorpusRecordFocusReview.vue')
    api=text('web/src/api/pdfCorpus.ts')
    assert 'Check with LLM' in comp and 'Corpus Builder/Boundary Adjudication' in story
    assert '<CorpusBoundaryAdjudication' in builder and '<CorpusBoundaryAdjudication' in focus
    assert 'adjudicateBoundary:' in api
    assert ':focus-visible' in comp or 'UiButton' in comp
