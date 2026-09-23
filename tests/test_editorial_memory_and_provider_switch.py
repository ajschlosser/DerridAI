"""Apparatus constraints, editorial memory, and provider switching.

Why: three behaviors keep long builds correct: apparatus regions imply certain
metadata, only reviewer-confirmed values may teach the model, and switching LLM
provider mid-build must never persist secrets.
How: `make_build` creates a running build (optionally with records) on a
temporary repository.
"""

from __future__ import annotations

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


def make_build(tmp_path:Path, rows:list[dict]|None=None):
    """Create a temp repository and running "enriching" build, saving any given records.

    Missing record_id/text/metadata_field_status fields are filled with defaults.
    """
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
    """Bibliography and front matter force primary_text=False and a matching role.

    Bibliography -> discourse_role "bibliographic"; front_matter -> "paratext". Both
    changes are reported (primary_text and discourse_role) for the review trail.
    """
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
    """Few-shot memory uses only human-confirmed or human-overridden values.

    Setup: r1 confirmed and r2 overridden as "reported_position", r3 an unreviewed LLM
    guess ("analysis"), r4 the record being enriched.
    Expect: a convention for discourse_role = reported_position seen on 2 records, and
    examples drawn only from r1/r2.
    Why: LLM guesses must not train future LLM calls (no self-reinforcing errors).
    """
    rows=[
        {'record_id':'r1','text':'Derrida reports Heidegger argues that sovereignty precedes law.','discourse_role':'reported_position','metadata_field_status':{'discourse_role':{'status':'human_confirmed'}}},
        {'record_id':'r2','text':'Here Derrida reports another proposition held by Heidegger concerning sovereignty.','discourse_role':'reported_position','metadata_field_status':{'discourse_role':{'status':'human_override'}}},
        {'record_id':'r3','text':'The model guessed analysis here.','discourse_role':'analysis','metadata_field_status':{'discourse_role':{'status':'model_inferred'}}},
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
    assert 'discourse_role' not in (memory.get('pass_learning') or {}).get('prior_pass', {}).get('inferred_conventions', {})


def test_provider_profile_switch_is_secret_safe_and_audited(tmp_path:Path):
    """Changing provider mid-build updates the model, hides the key, and logs the change.

    Checks: the saved build request has the new profile and model but no api_key; the
    in-memory runtime request has the new key while keeping stage limits; and
    provider_profile_history records the switch.
    Why: build files are stored on disk and included in backups, so secrets stay in memory.
    """
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



