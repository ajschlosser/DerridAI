"""Boundary-quality flags and review edits with undo/redo.

Why: segmentation can leave a sentence split across two records, or leave the start
of one record inside its neighbor. Reviewers need to spot those and to move text
between records safely, with full reversibility.
How: `install` builds a three-record build in a temporary repository whose middle
record starts with text that belongs to the record before it.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.config import APP_VERSION


def install(tmp_path:Path):
    """Create a temp repository with three records where r2 begins with misplaced text.

    Records: r1 "Previous ending.", r2 "Misplaced beginning. Proper current text.",
    r3 "Next beginning." The build is marked running/enriching so review-edit APIs
    are exercised in the same state a live build would be in.
    """
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
    """A sentence that continues across records flags both sides.

    What: a first record ending without punctuation and a second starting in lowercase
    mid-sentence. annotate_boundary_suspects reports 1 suspect boundary and marks the
    "end" edge of the first record and the "start" edge of the second.
    """
    rows=[{'text':'This continues without punctuation'},{'text':'and clearly continues here.'}]
    assert cb.annotate_boundary_suspects(rows)==1
    assert rows[0]['boundary_quality_issues'][0]['edge']=='end'
    assert rows[1]['boundary_quality_issues'][0]['edge']=='start'

def test_slice_moves_prefix_to_previous_and_undo_redo_walk_history(tmp_path:Path):
    """Slicing moves text to the previous record, and undo/redo restore it exactly.

    Steps: cut r2 before "Proper" so "Misplaced beginning." moves onto the end of r1;
    undo puts it back (and reports can_redo); redo applies it again.
    Why: review edits change scholarly text, so every one must be reversible.
    """
    repo,build=install(tmp_path);manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    target=repo.load_records(build['build_id'])[1];cut=target['text'].index('Proper')
    result=manager.create_from_selection(build['build_id'],'r2',cut,len(target['text']),'merge_prior',expected_revision=1)
    assert result['record']['text'].startswith('Proper current text')
    assert repo.load_records(build['build_id'])[0]['text'].endswith('Misplaced beginning.')
    undo=manager.undo_last_review_edit(build['build_id']); assert undo['can_redo'] is True
    assert repo.load_records(build['build_id'])[1]['text'].startswith('Misplaced beginning')
    manager.redo_last_review_edit(build['build_id'])
    assert repo.load_records(build['build_id'])[1]['text'].startswith('Proper current text')


def test_slice_moves_text_to_beginning_of_next_record_and_requeues_metadata(tmp_path:Path):
    repo,build=install(tmp_path); manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    target=repo.load_records(build['build_id'])[1]
    cut=target['text'].index('Proper')
    result=manager.create_from_selection(build['build_id'],'r2',0,cut,right='merge_next',expected_revision=1)
    rows=repo.load_records(build['build_id'])
    assert rows[2]['text'].startswith('Proper current text.')
    assert result['record']['text'].startswith('Misplaced beginning.')
    assert all(row['needs_review'] and row['metadata_needs_attention'] for row in rows[1:3])
