"""Human ownership of metadata during and after enrichment.

Why: reviewers edit while background workers enrich. Human decisions must win, be
marked as such, and never be overwritten by later model output; only repeated human
choices may become advisory conventions.
How: `install` creates a temporary build with the given records and status, and the
tests call PdfCorpusBuildManager methods directly.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.config import APP_VERSION


def install(tmp_path:Path, records:list[dict], *, status='running', stage='enriching'):
    """Create a temp repository with an asset, blocks, a build, and the given records.

    Fills defaults for each record (id, revision, text, block ids/spans, pending
    review). status/stage choose whether the build looks like it is enriching or in
    review.
    """
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    asset={'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':1,'block_count':len(records),'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]}
    cb._json_write(repo.asset_meta_path('a'),asset)
    with repo.asset_blocks_path('a').open('w',encoding='utf-8') as h:
        for i,r in enumerate(records,1):
            h.write(json.dumps({'block_id':f'b{i}','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':r.get('text','text'),'extraction_method':'native','confidence':1.0})+'\n')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':1,'source_block_count':len(records),'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':11,'app_version':APP_VERSION,'provider':'ollama','model':'test','request':{'enrichment_mode':'fast'},'manifest':{'title':'Book','document_author':'Derrida'}})
    build['status']=status; build['stage']=stage; build['record_count']=len(records); repo.save_build(build)
    for i,r in enumerate(records,1):
        r.setdefault('record_id',f'r{i}');r.setdefault('record_revision',1);r.setdefault('text','text');r.setdefault('text_length',len(r['text']));r.setdefault('source_block_ids',[f'b{i}']);r.setdefault('source_spans',[{'block_id':f'b{i}','page':1}]);r.setdefault('pdf_pages',[1]);r.setdefault('metadata_field_status',{});r.setdefault('review_disposition','pending');r.setdefault('accepted',False);r.setdefault('rejected',False);r.setdefault('metadata_stage_status',{'discourse':'queued','quotation':'queued','indexing':'queued'});r.setdefault('metadata_enrichment_state','queued')
    repo.save_records(build['build_id'],records)
    return repo,build


def test_human_metadata_edit_is_allowed_during_enrichment_and_establishes_field_ownership(tmp_path:Path):
    """Editing a field mid-enrichment saves it and marks it human-confirmed.

    Checks: the value is stored, status becomes "human_confirmed", and the field is added
    to human_touched_fields so workers will not replace it.
    """
    repo,build=install(tmp_path,[{'text':'Derrida writes about hospitality.'}])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    updated=manager.patch_metadata(build['build_id'],'r1',{'speaker':'Derrida'},expected_revision=1)
    assert updated['speaker']=='Derrida'
    assert updated['metadata_field_status']['speaker']['status']=='human_confirmed'
    assert 'speaker' in updated['human_touched_fields']


def test_bulk_metadata_patch_supports_selection_and_all_records(tmp_path:Path):
    """Bulk edit applies to selected records or to every record.

    First a patch targets r1 and r3 only (2 changed, r2 untouched, status
    "human_override"). Then apply_to_all sets language on all 3 records.
    """
    repo,build=install(tmp_path,[{'text':'one'},{'text':'two'},{'text':'three'}])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    result=manager.bulk_patch_metadata(build['build_id'],{'document_author':'Jacques Derrida'},record_ids=['r1','r3'])
    assert result['changed']==2
    rows=repo.load_records(build['build_id'])
    assert rows[0]['document_author']=='Jacques Derrida'
    assert 'document_author' not in rows[1]
    assert rows[2]['metadata_field_status']['document_author']['status']=='human_override'
    result=manager.bulk_patch_metadata(build['build_id'],{'language':'en'},apply_to_all=True)
    assert result['changed']==3
    assert all(row.get('language')=='en' for row in repo.load_records(build['build_id']))


def test_worker_merge_preserves_human_owned_fields_and_discards_frozen_record_results():
    """Merging a worker's snapshot into the live record never clobbers human edits.

    Case 1: the human set speaker="Human"; the worker proposes speaker="Model" and
    target="Kant". Result keeps "Human" and accepts the new target.
    Case 2: the record's text was hand-edited ("__text__" touched), so the whole worker
    result is discarded (its stage becomes "skipped") and the human target stays.
    """
    live={'record_id':'r1','text':'reviewed','speaker':'Human','human_touched_fields':['speaker'],'metadata_field_status':{'speaker':{'status':'human_confirmed'}},'metadata_stage_status':{},'metadata_execution_ledger':{}}
    worker={'record_id':'r1','text':'reviewed','speaker':'Model','target':'Kant','metadata_field_status':{'speaker':{'status':'model_inferred'},'target':{'status':'model_inferred'}},'metadata_stage_status':{'discourse':'complete'},'metadata_execution_ledger':{'discourse':{'state':'complete'}}}
    merged=cb.PdfCorpusBuildManager._merge_enrichment_snapshot(live,worker)
    assert merged['speaker']=='Human'
    assert merged['target']=='Kant'
    frozen={**live,'human_touched_fields':['__text__'],'target':'Human target'}
    merged2=cb.PdfCorpusBuildManager._merge_enrichment_snapshot(frozen,worker)
    assert merged2['target']=='Human target'
    assert merged2['metadata_stage_status']['discourse']=='skipped'


def test_editorial_context_only_generalizes_repeated_human_choices(tmp_path:Path):
    """A convention needs at least two matching human confirmations.

    Records confirmed as Derrida, Derrida, Levinas produce a speaker convention of
    "Derrida" supported by 2 records; the single Levinas choice is not generalized.
    """
    rows=[]
    for i,value in enumerate(['Derrida','Derrida','Levinas'],1):
        rows.append({'record_id':f'r{i}','text':str(i),'speaker':value,'metadata_field_status':{'speaker':{'status':'human_confirmed'}}})
    repo,build=install(tmp_path,rows,status='awaiting_review',stage='review')
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    context=manager._editorial_context(build['build_id'])
    assert context['speaker']['value']=='Derrida'
    assert context['speaker']['confirmed_records']==2


def test_resume_clears_cancel_marker(tmp_path:Path,monkeypatch):
    """Resuming a cancelled build clears the in-memory cancel flag and re-queues it.

    Why: a stale cancel marker would make the resumed build stop immediately.
    The executor is stubbed so no real work runs.
    """
    repo,build=install(tmp_path,[{'text':'x'}],status='cancelled',stage='cancelled')
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    manager._cancel.add(build['build_id'])
    monkeypatch.setattr(manager._executor,'submit',lambda *a,**k:None)
    manager.resume(build['build_id'],{'provider':'ollama','model':'test'})
    assert build['build_id'] not in manager._cancel
    assert repo.get_build(build['build_id'])['status']=='queued'




