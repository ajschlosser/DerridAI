"""Review actions during metadata enrichment (release 0.48.0, "Frightened Ferret").

Why: enrichment of a book-length build takes a long time; reviewers must be able to
reject or accept records while it runs, and those human decisions must be marked so
the background workers never overwrite them.
How: `install` creates a running two-record build with queued enrichment stages.
"""

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


def text(path:str)->str:
    """Read a repository file as UTF-8 text.

    Currently unused in this file: it is a leftover from earlier source-text checks that were
    removed (AGENTS.md: test behavior, not text). Safe to delete in a code-changing cleanup.
    """
    return (ROOT/path).read_text(encoding='utf-8')


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




