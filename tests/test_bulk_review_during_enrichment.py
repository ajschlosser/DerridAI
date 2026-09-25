"""Review actions during metadata enrichment.

Why: enrichment of a book-length build takes a long time; reviewers must be able to
reject or accept records while it runs, and those human decisions must be marked so
the background workers never overwrite them.
How: `install` creates a running two-record build with queued enrichment stages.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules['chromadb']=types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app import corpus_review_actions as review_actions
from app.config import APP_VERSION


def install(tmp_path:Path):
    """Temp repository with two pending records whose metadata stages are still "queued"."""
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








def test_bulk_review_is_allowed_during_enrichment_and_marks_human_touch(tmp_path:Path):
    """Bulk-rejecting while enrichment is running works and records human ownership.

    What: rejecting r1 and r2 changes 2 records to disposition "rejected", and each
    record's human_touched_fields includes "__review__" so enrichment leaves them alone.
    """
    repo,build=install(tmp_path)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    result=manager.bulk_disposition(build['build_id'],'rejected',record_ids=['r1','r2'])
    assert result['changed']==2
    rows=repo.load_records(build['build_id'])
    assert all(row['review_disposition']=='rejected' for row in rows)
    assert all('__review__' in row.get('human_touched_fields',[]) for row in rows)


def test_bulk_accept_persists_promoted_metadata_memory(tmp_path:Path, monkeypatch):
    """Bulk acceptance is a human confirmation and must feed semantic-memory projection."""

    repo,build=install(tmp_path)
    rows=repo.load_records(build['build_id'])
    for row in rows:
        # Keep the acceptance fixture structurally valid. The behavior under test
        # is promotion of the model-inferred review field, not required-core blocking.
        row['region_type']='main_text'
        row['primary_text']=True
        row['discourse_role']='analysis'
        row['metadata_field_status']={
            'region_type':{'status':'deterministic','method':'source_structure','confidence':1.0},
            'primary_text':{'status':'deterministic','method':'source_structure','confidence':1.0},
            'discourse_role':{'status':'model_inferred','method':'llm','confidence':0.9},
        }
        row['metadata_incomplete_fields']=[]
        row['metadata_review_fields']=[]
        row['metadata_complete']=True
    repo.save_records(build['build_id'],rows)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    persisted=[]
    scheduled=[]
    monkeypatch.setattr(
        review_actions,
        'persist_record_decision',
        lambda **kwargs: persisted.append((kwargs['record']['record_id'],kwargs['field_name'],kwargs['value'])),
    )
    monkeypatch.setattr(
        manager,
        '_schedule_metadata_exemplar_projection',
        lambda build_id: scheduled.append(build_id),
    )

    result=manager.bulk_disposition(build['build_id'],'accepted',record_ids=['r1','r2'])

    assert result['changed']==2
    assert persisted==[
        ('r1','discourse_role','analysis'),
        ('r2','discourse_role','analysis'),
    ]
    assert scheduled==[build['build_id']]




