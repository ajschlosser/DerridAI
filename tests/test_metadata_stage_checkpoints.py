"""Metadata stage timeouts, progress, checkpoints, and concurrent writes.

Why: enrichment runs three LLM "families" per record (discourse, quotation, indexing).
Each has its own timeout, checkpoint, and ledger entry so a slow or failed family does
not lose the others, and progress is visible in the operations list. Record files are
written by several threads and must never be corrupted.
How: `_install_minimal_build` makes a one-block build; `_metadata_result` returns a canned
LLM reply per family. Other helpers in this module are reused by later test files.
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


def test_metadata_stage_timeouts_are_configurable_and_reasonable():
    """Default family timeouts are at most 300 seconds and can be overridden per family."""
    limits=cb._stage_timeouts({})
    assert limits['discourse'] <= 300
    assert limits['quotation'] <= 300
    assert limits['indexing'] <= 300
    custom=cb._stage_timeouts({'stage_timeouts':{'discourse':90,'indexing':45}})
    assert custom['discourse']==90
    assert custom['indexing']==45






def test_operations_surface_metadata_task_progress():
    """The operations list shows task-level metadata progress.

    4 done + 1 failed + 1 skipped = 6 of 33 settled, 3 active, 24 queued, 2 needing
    review; the stage detail string and running count must reflect that.
    """
    operation=cb.PdfCorpusBuildManager._operation_from_build({
        'build_id':'build-test','status':'running','stage':'enriching','progress':0.5,
        'metadata_tasks_total':33,'metadata_tasks_completed':4,'metadata_tasks_failed':1,
        'metadata_tasks_skipped':1,'metadata_tasks_running':3,'metadata_tasks_queued':24,
    })
    assert operation['stage_detail']=='Metadata: 6/33 settled · 3 active · 24 queued · 2 review'
    assert operation['metadata_tasks_running']==3






def _install_minimal_build(repo:cb.PdfCorpusRepository):
    """Create a one-page, one-block asset and a build for it (reused by other test files)."""
    asset={"asset_id":"asset-elephant","sha256":"sha","filename":"elephant.pdf","page_count":1,"block_count":1,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path(asset["asset_id"]),asset)
    repo.asset_blocks_path(asset["asset_id"]).write_text(json.dumps({"block_id":"b1","page":1,"bbox":[0,0,100,100],"type":"paragraph","text":"Derrida discusses hospitality.","extraction_method":"native","confidence":1.0})+'\n',encoding='utf-8')
    return repo.create_build({"asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"elephant.pdf","source_page_count":1,"source_block_count":1,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"provider":"ollama","model":"test-model","request":{},"manifest":{}})


def _metadata_result(schema_name:str):
    """Canned LLM reply for a family: discourse gives region/role, quotation is empty, indexing gives a topic."""
    if schema_name=='derridai_record_discourse':
        return {"metadata":{"region_type":"main_text","primary_text":True,"discourse_role":"analysis"},"field_evidence":{"region_type":{"block_ids":["b1"],"confidence":.99,"reason":"body"},"primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"body"},"discourse_role":{"block_ids":["b1"],"confidence":.99,"reason":"analysis"}},"review_reason":""}
    if schema_name=='derridai_record_quotation':
        return {"metadata":{},"field_evidence":{},"review_reason":""}
    return {"metadata":{"topics":["hospitality"]},"review_reason":""}


def test_metadata_families_checkpoint_independently_and_record_execution_ledger(tmp_path,monkeypatch):
    """Each family runs in order, reports events, and leaves an execution ledger.

    Events must be running/complete for discourse, quotation, indexing in order. Afterwards
    all stages are "complete", the ledger records provider, model, timeout (90 s override)
    and input size, and the raw stage results are dropped from the record.
    """
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    build=_install_minimal_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={"record_id":"r1","record_revision":1,"text":"Derrida discusses hospitality.","text_length":30,"source_asset_id":"asset-elephant","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1,"confidence":1.0}]}
    events=[]
    monkeypatch.setattr(manager,'_chat_json',lambda _request,prompt,*,response_model,max_tokens,schema_name,build_id='':_metadata_result(schema_name))
    manager._enrich_record(record,{}, {"provider":"ollama","model":"test-model","stage_timeouts":{"discourse":90}},build_id=build['build_id'],stage_callback=lambda snapshot,task,state,error:events.append((task,state,dict(snapshot.get('metadata_stage_status') or {}))))
    assert [(task,state) for task,state,_ in events]==[("discourse","running"),("discourse","complete"),("quotation","running"),("quotation","complete"),("indexing","running"),("indexing","complete")]
    assert record['metadata_stage_status']=={'discourse':'complete','quotation':'complete','indexing':'complete'}
    assert record['metadata_execution_ledger']['discourse']['provider']=='ollama'
    assert record['metadata_execution_ledger']['discourse']['model']=='test-model'
    assert record['metadata_execution_ledger']['discourse']['timeout_seconds']==90
    assert record['metadata_execution_ledger']['discourse']['input_chars']>0
    assert 'metadata_stage_results' not in record


def test_metadata_resume_reuses_completed_family_checkpoint(tmp_path,monkeypatch):
    """A family with a saved checkpoint is not sent to the LLM again.

    With the discourse result already stored, only quotation and indexing are called and
    the record ends metadata-complete. Why: resuming a long build must not repeat paid work.
    """
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    build=_install_minimal_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    record={"record_id":"r1","record_revision":1,"text":"Derrida discusses hospitality.","text_length":30,"source_asset_id":"asset-elephant","source_block_ids":["b1"],"source_spans":[{"block_id":"b1","page":1,"confidence":1.0}],"metadata_stage_results":{"discourse":_metadata_result('derridai_record_discourse')},"metadata_stage_status":{"discourse":"complete"}}
    called=[]
    def fake(_request,prompt,*,response_model,max_tokens,schema_name,build_id=''):
        called.append(schema_name)
        return _metadata_result(schema_name)
    monkeypatch.setattr(manager,'_chat_json',fake)
    manager._enrich_record(record,{}, {"provider":"ollama","model":"test-model"},build_id=build['build_id'])
    assert called==['derridai_record_quotation','derridai_record_indexing']
    assert record['metadata_complete'] is True


def test_settle_metadata_unresolved_is_explicit_build_state(tmp_path):
    """"Continue with unresolved metadata" is recorded on the build with a timestamp."""
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    build=_install_minimal_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build['status']='running';build['stage']='enriching';repo.save_build(build)
    settled=manager.settle_metadata_unresolved(build['build_id'])
    assert settled['metadata_settle_requested'] is True
    assert settled['metadata_settle_requested_at']


def test_record_store_concurrent_writes_remain_valid_jsonl(tmp_path):
    """Two threads saving different large record sets never produce a mixed or torn file.

    Each thread saves and immediately reloads 20 times; every load must equal one of the
    two complete sets. Why: writes use a temp file and atomic replace under a lock.
    """
    import threading

    from app.corpus_builder import PdfCorpusRepository

    repo = PdfCorpusRepository(root=tmp_path / "pdf-corpus")
    build_id = "build-race"
    (repo.root / "builds" / build_id).mkdir(parents=True, exist_ok=True)
    (repo.root / "builds" / build_id / "build.json").write_text('{"build_id":"build-race"}', encoding="utf-8")
    rows_a = [{"record_id": f"a-{i}", "text": "A" * 7000} for i in range(8)]
    rows_b = [{"record_id": f"b-{i}", "text": "B" * 7000} for i in range(8)]
    failures = []

    def writer(rows):
        try:
            for _ in range(20):
                repo.save_records(build_id, rows)
                loaded = repo.load_records(build_id)
                assert loaded in (rows_a, rows_b)
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [threading.Thread(target=writer, args=(rows_a,)), threading.Thread(target=writer, args=(rows_b,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not failures
    assert repo.load_records(build_id) in (rows_a, rows_b)


