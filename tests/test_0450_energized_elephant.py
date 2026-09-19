from __future__ import annotations

import json
from pathlib import Path
import sys
import types

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))

from app import corpus_builder as cb
from app.config import APP_VERSION


def text(path:str)->str:
    return (ROOT/path).read_text(encoding='utf-8')


def test_metadata_enrichment_is_family_checkpointed_and_bounded():
    source=text('api/app/corpus_builder.py')
    rag=text('api/app/rag.py')
    for token in ('metadata_stage_results','metadata_execution_ledger','metadata_tasks_running','metadata_last_progress_at','metadata_active_tasks'):
        assert token in source
    assert 'stage_callback' in source
    assert 'attempts: int = 2' in source
    assert 'metadata_settle_requested' in source
    assert 'settle_metadata_unresolved' in source
    assert 'timeout_seconds' in rag
    assert 'LLM generation exceeded' in rag


def test_metadata_stage_timeouts_are_configurable_and_reasonable():
    limits=cb.PdfCorpusBuildManager._stage_timeouts({})
    assert limits['discourse'] <= 300
    assert limits['quotation'] <= 300
    assert limits['indexing'] <= 300
    custom=cb.PdfCorpusBuildManager._stage_timeouts({'stage_timeouts':{'discourse':90,'indexing':45}})
    assert custom['discourse']==90
    assert custom['indexing']==45


def test_live_status_component_is_storybooked_accessible_and_localized():
    component=text('web/src/components/CorpusMetadataLiveStatus.vue')
    stories=text('web/src/components/CorpusMetadataLiveStatus.stories.ts')
    store=text('api/app/locales/en_us.py')+text('api/app/locales/fr_ca.py')
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'role="progressbar"' in component
    assert 'aria-live="polite"' in component
    assert 'font-size:.8125rem' in component and 'font-size:13px' in component
    assert 'Continue with unresolved metadata' in component
    assert 'Stalled' in stories and 'FrenchLengthStress' in stories
    for key in ('"pdf_corpus.metadata_live_title"','"pdf_corpus.continue_unresolved"','"pdf_corpus.status_refresh_failed"'):
        assert store.count(key.strip('"')) >= 2
    assert '<CorpusMetadataLiveStatus' in builder
    assert 'transientNetworkError' in builder


def test_workflow_stepper_no_longer_uses_tiny_status_fonts():
    stepper=text('web/src/components/CorpusWorkflowStepper.vue')
    assert 'font-size:8px' not in stepper
    assert 'font-size:9px' not in stepper


def test_operations_surface_metadata_task_progress():
    operation=cb.PdfCorpusBuildManager._operation_from_build({
        'build_id':'build-test','status':'running','stage':'enriching','progress':0.5,
        'metadata_tasks_total':33,'metadata_tasks_completed':4,'metadata_tasks_failed':1,
        'metadata_tasks_skipped':1,'metadata_tasks_running':3,'metadata_tasks_queued':24,
    })
    assert operation['stage_detail']=='Metadata: 6/33 settled · 3 active · 24 queued · 2 review'
    assert operation['metadata_tasks_running']==3


def test_energized_elephant_i18n_and_review_controls_are_bilingual():
    store=text('api/app/locales/en_us.py')+text('api/app/locales/fr_ca.py')
    for key in (
        'pdf_corpus.stage_timeouts','pdf_corpus.timeout.discourse','pdf_corpus.timeout.quotation',
        'pdf_corpus.timeout.indexing','pdf_corpus.issue_filter','pdf_corpus.select_visible',
        'pdf_corpus.reject_selected_count','pdf_corpus.open_pdf_explorer','pdf_corpus.resume_safe',
    ):
        assert store.count(key.strip('"')) >= 2
    queue=text('web/src/components/CorpusReviewQueueTabs.vue')
    assert 'issue-filter' in queue
    assert 'primaryTabs' in queue
    builder=text('web/src/components/PdfCorpusBuilder.vue')
    assert 'selectedReviewIds' in builder
    assert 'openPdfExplorer' in builder
    assert 'Accessible type floor' in builder


def test_bulk_disposition_accepts_explicit_record_ids():
    models=text('api/app/models.py')
    manager=text('api/app/corpus_builder.py')
    api=text('web/src/api/pdfCorpus.ts')
    assert 'record_ids: list[str]' in models
    assert 'selected_ids = {' in manager
    assert 'record_ids:recordIds' in api


def _install_minimal_build(repo:cb.PdfCorpusRepository):
    asset={"asset_id":"asset-elephant","sha256":"sha","filename":"elephant.pdf","page_count":1,"block_count":1,"ocr_pages":0,"warnings":[],"metadata":{},"pages":[]}
    cb._json_write(repo.asset_meta_path(asset["asset_id"]),asset)
    repo.asset_blocks_path(asset["asset_id"]).write_text(json.dumps({"block_id":"b1","page":1,"bbox":[0,0,100,100],"type":"paragraph","text":"Derrida discusses hospitality.","extraction_method":"native","confidence":1.0})+'\n',encoding='utf-8')
    return repo.create_build({"asset_id":asset["asset_id"],"source_sha256":"sha","source_filename":"elephant.pdf","source_page_count":1,"source_block_count":1,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"provider":"ollama","model":"test-model","request":{},"manifest":{}})


def _metadata_result(schema_name:str):
    if schema_name=='derridai_record_discourse':
        return {"metadata":{"region_type":"main_text","primary_text":True,"discourse_role":"analysis"},"field_evidence":{"region_type":{"block_ids":["b1"],"confidence":.99,"reason":"body"},"primary_text":{"block_ids":["b1"],"confidence":.99,"reason":"body"},"discourse_role":{"block_ids":["b1"],"confidence":.99,"reason":"analysis"}},"review_reason":""}
    if schema_name=='derridai_record_quotation':
        return {"metadata":{},"field_evidence":{},"review_reason":""}
    return {"metadata":{"topics":["hospitality"]},"review_reason":""}


def test_metadata_families_checkpoint_independently_and_record_execution_ledger(tmp_path,monkeypatch):
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
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    build=_install_minimal_build(repo)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build['status']='running';build['stage']='enriching';repo.save_build(build)
    settled=manager.settle_metadata_unresolved(build['build_id'])
    assert settled['metadata_settle_requested'] is True
    assert settled['metadata_settle_requested_at']


def test_record_store_concurrent_writes_remain_valid_jsonl(tmp_path):
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


def test_progressive_review_mutations_are_serialized_with_metadata_checkpoints():

    for name in (
        "set_disposition", "review_decision", "bulk_disposition", "undo_last_review_edit",
        "patch_metadata", "metadata_decision", "patch_evidence", "merge", "split",
        "rerun_metadata", "settle_metadata_unresolved", "publish",
    ):
        method = getattr(cb.PdfCorpusBuildManager, name)
        assert method.__name__ == name
    source = (ROOT / "api/app/corpus_builder.py").read_text(encoding="utf-8")
    assert "def _serialize_record_mutation" in source
    assert "with self._lock:\n                            live_records = self.repo.load_records(build_id)" in source
    assert "tempfile.mkstemp(prefix=f\".{path.name}.\"" in source
