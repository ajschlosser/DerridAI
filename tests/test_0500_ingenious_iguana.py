from __future__ import annotations

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


def make_build(tmp_path:Path, rows:list[dict]|None=None):
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    build=repo.create_build({
        'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':1,
        'source_block_count':len(rows or []),'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,
        'profile_version':11,'app_version':APP_VERSION,'provider':'ollama','model':'old-model',
        'request':{'provider':'ollama','model':'old-model','provider_profile_id':'old','enrichment_mode':'fast'},
        'manifest':{'title':'Book','document_author':'Jacques Derrida'},
    })
    build['status']='running';build['stage']='enriching';repo.save_build(build)
    if rows is not None:
        for i,row in enumerate(rows,1):
            row.setdefault('record_id',f'r{i}')
            row.setdefault('text',f'record {i}')
            row.setdefault('metadata_field_status',{})
        repo.save_records(build['build_id'],rows)
    return repo,build






def test_deterministic_constraints_include_discourse_role_for_apparatus():
    bibliography={'region_type':'bibliography','primary_text':True,'discourse_role':'analysis','metadata_field_status':{}}
    changes=cb.apply_metadata_constraints(bibliography)
    assert bibliography['primary_text'] is False
    assert bibliography['discourse_role']=='bibliographic'
    assert {item['field'] for item in changes}=={'primary_text','discourse_role'}
    front={'region_type':'front_matter','metadata_field_status':{}}
    cb.apply_metadata_constraints(front)
    assert front['primary_text'] is False
    assert front['discourse_role']=='paratext'


def test_editorial_memory_retrieves_only_human_confirmed_examples(tmp_path:Path):
    rows=[
        {'record_id':'r1','text':'Derrida reports Heidegger argues that sovereignty precedes law.','discourse_role':'reported_position','metadata_field_status':{'discourse_role':{'status':'human_confirmed'}}},
        {'record_id':'r2','text':'Here Derrida reports another proposition held by Heidegger concerning sovereignty.','discourse_role':'reported_position','metadata_field_status':{'discourse_role':{'status':'human_override'}}},
        {'record_id':'r3','text':'The model guessed analysis here.','discourse_role':'analysis','metadata_field_status':{'discourse_role':{'status':'llm_inferred'}}},
        {'record_id':'r4','text':'Heidegger is presented as holding a proposition concerning sovereignty and law.','metadata_field_status':{}},
    ]
    repo,build=make_build(tmp_path,rows)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    memory=manager._editorial_memory(build['build_id'],rows[3],exclude_record_id='r4')
    assert memory['conventions']['discourse_role']['value']=='reported_position'
    assert memory['conventions']['discourse_role']['confirmed_records']==2
    examples=memory['examples']['discourse_role']
    assert {item['record_id'] for item in examples}<={'r1','r2'}
    assert examples and examples[0]['value']=='reported_position'


def test_provider_profile_switch_is_secret_safe_and_audited(tmp_path:Path):
    repo,build=make_build(tmp_path,[])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    manager._runtime_requests[build['build_id']]={
        'provider':'ollama','model':'old-model','provider_profile_id':'old','api_key':'old-secret',
        'enrichment_mode':'fast','stage_limits':{'discourse_num_predict':1200},
    }
    updated=manager.switch_provider_profile(build['build_id'],{
        'provider':'openai','model':'new-model','provider_profile_id':'new','base_url':'http://provider','api_key':'new-secret',
        'generation':{'temperature':0.0},
    })
    assert updated['request']['provider_profile_id']=='new'
    assert updated['model']=='new-model'
    assert 'api_key' not in updated['request']
    runtime=manager._latest_runtime_request(build['build_id'],{})
    assert runtime['api_key']=='new-secret'
    assert runtime['stage_limits']['discourse_num_predict']==1200
    assert updated['provider_profile_history'][-1]['provider_profile_id']=='new'



