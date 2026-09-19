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

def text(path:str)->str:return (ROOT/path).read_text(encoding='utf-8')

def install(tmp_path:Path):
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    asset={'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':2,'block_count':3,'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]}
    cb._json_write(repo.asset_meta_path('a'),asset)
    blocks=[
        {'block_id':'b1','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'Previous ending.','extraction_method':'native','confidence':1.0},
        {'block_id':'b2','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'Misplaced beginning. Proper current text.','extraction_method':'native','confidence':1.0},
        {'block_id':'b3','page':2,'bbox':[0,0,1,1],'type':'paragraph','text':'Next beginning.','extraction_method':'native','confidence':1.0},
    ]
    with repo.asset_blocks_path('a').open('w',encoding='utf-8') as h:
        for b in blocks:h.write(json.dumps(b)+'\n')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':2,'source_block_count':3,'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':11,'app_version':APP_VERSION,'provider':'ollama','model':'test','request':{},'manifest':{'title':'Book','document_author':'Derrida'}})
    build.update(status='running',stage='enriching',record_count=3);repo.save_build(build)
    rows=[]
    for i,(bid,txt) in enumerate([('b1','Previous ending.'),('b2','Misplaced beginning. Proper current text.'),('b3','Next beginning.')],1):
        rows.append({'record_id':f'r{i}','record_revision':1,'text':txt,'text_length':len(txt),'source_block_ids':[bid],'source_spans':[{'block_id':bid,'page':1 if i<3 else 2}],'pdf_pages':[1 if i<3 else 2],'metadata_field_status':{},'metadata_stage_status':{},'review_disposition':'pending','accepted':False,'rejected':False})
    repo.save_records(build['build_id'],rows)
    return repo,build


def test_boundary_suspect_detection_marks_both_sides():
    rows=[{'text':'This continues without punctuation'},{'text':'and clearly continues here.'}]
    assert cb.annotate_boundary_suspects(rows)==1
    assert rows[0]['boundary_quality_issues'][0]['edge']=='end'
    assert rows[1]['boundary_quality_issues'][0]['edge']=='start'

def test_slice_moves_prefix_to_previous_and_undo_redo_walk_history(tmp_path:Path):
    repo,build=install(tmp_path);manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    target=repo.load_records(build['build_id'])[1];cut=target['text'].index('Proper')
    result=manager.slice_to_neighbor(build['build_id'],'r2','previous',cut,1)
    assert result['record']['text'].startswith('Proper current text')
    assert repo.load_records(build['build_id'])[0]['text'].endswith('Misplaced beginning.')
    undo=manager.undo_last_review_edit(build['build_id']); assert undo['can_redo'] is True
    assert repo.load_records(build['build_id'])[1]['text'].startswith('Misplaced beginning')
    manager.redo_last_review_edit(build['build_id'])
    assert repo.load_records(build['build_id'])[1]['text'].startswith('Proper current text')

def test_review_ui_has_slice_select_from_text_focus_pdf_and_undo_redo():
    builder=text('web/src/components/PdfCorpusBuilder.vue');focus=text('web/src/components/CorpusRecordFocusReview.vue');field=text('web/src/components/CorpusMetadataFieldEditor.vue');api=text('web/src/api/pdfCorpus.ts')
    assert '<CorpusBoundarySliceDialog' in builder and 'sliceRecord:' in api
    assert 'redoReview:' in api and '@redo="redoReview"' in builder
    assert 'selectFromText' in field and "window.getSelection()" in field
    assert 'sourcePdfUrl' in focus and '<iframe' not in focus and 'openSourceViewer' in focus
    assert 'SourceTranscriptionDialog' in builder
    assert '<CorpusBoundarySliceDialog' in focus

def test_boundary_slice_storybook_component_is_accessible_and_reusable():
    comp=text('web/src/components/CorpusBoundarySliceDialog.vue');story=text('web/src/components/CorpusBoundarySliceDialog.stories.ts')
    assert '<UiDialog' in comp and "import UiDialog" in comp
    assert ':focus-visible' in comp
    assert 'Corpus Builder/Review/Boundary Slice Dialog' in story
