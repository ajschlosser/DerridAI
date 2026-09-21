"""Profile identity, manifest normalization, and metadata-gated acceptance.

Why: the profile and prompt version strings are part of a build's provenance; they
must change deliberately when semantics change. Acceptance must not bypass
unresolved metadata.
How: exercises PdfCorpusRepository / PdfCorpusBuildManager on a temporary directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'api'))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate


def test_profile_and_prompt_ids_are_pinned():
    """Pin the active corpus profile and prompt version identifiers.

    What: profile "derrida-scholarly-v12", metadata prompt "derridai-record-metadata-v11",
    exactly one registered profile, and review_metadata_fields matching the constant.
    Why: AGENTS.md requires bumping these when their semantics change; this test fails
    until the change is made on purpose (update the strings when you bump them).
    """
    assert cb.PROFILE_VERSION=='derrida-scholarly-v12'
    assert cb.METADATA_PROMPT_VERSION=='derridai-record-metadata-v11'
    assert PdfCorpusBuildCreate(asset_id='a').profile_id=='derrida-scholarly-v12'
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    assert cb.CORPUS_PROFILES[cb.PROFILE_VERSION]['review_metadata_fields']==list(cb.REVIEW_METADATA_FIELDS)

def test_manifest_nullable_notes_are_normalized_not_rejected():
    """A null "notes" value from an LLM becomes an empty string instead of failing validation.

    Why: models often emit null for empty optional fields; rejecting the whole manifest
    for that would waste a paid/slow LLM call.
    """
    manifest=cb.DocumentManifestModel.model_validate({'title':'Book','notes':None})
    assert manifest.notes==''

def test_accept_requires_uncertain_metadata_resolution_and_confirms_llm_fields(tmp_path:Path):
    """Accepting a record needs its unresolved metadata decided, then confirms LLM fields.

    What: r1 has an unresolved position_holder (52% confidence). Accepting must raise
    ValueError mentioning metadata. After a human patches position_holder, the review
    list is empty and acceptance succeeds.
    Also checks: the confident LLM-inferred discourse_role becomes "human_confirmed"
    on acceptance, so an accepted record has reviewer-owned provenance.
    """
    repo=cb.PdfCorpusRepository(tmp_path/'repo')
    cb._json_write(repo.asset_meta_path('a'), {'asset_id':'a','sha256':'x','filename':'x.pdf','page_count':1,'block_count':1,'ocr_pages':0,'warnings':[],'metadata':{},'pages':[]})
    repo.asset_blocks_path('a').write_text(json.dumps({'block_id':'b1','page':1,'bbox':[0,0,1,1],'type':'paragraph','text':'text','extraction_method':'native','confidence':1.0})+'\n',encoding='utf-8')
    build=repo.create_build({'asset_id':'a','source_sha256':'x','source_filename':'x.pdf','source_page_count':1,'source_block_count':1,'schema_version':cb.SCHEMA_VERSION,'profile_id':cb.PROFILE_VERSION,'profile_version':10,'provider':'ollama','model':'test','request':{},'manifest':{},'validation':{'valid':True}})
    record={'record_id':'r1','record_revision':1,'text':'text','text_length':4,'source_block_ids':['b1'],'source_spans':[{'block_id':'b1','page':1}], 'metadata_review_fields':['position_holder'],'metadata_field_status':{'position_holder':{'status':'unresolved','method':'llm','confidence':.52},'discourse_role':{'status':'llm_inferred','method':'llm','confidence':.95}}, 'region_type':'main_text','primary_text':True,'discourse_role':'analysis','review_disposition':'pending','accepted':False,'rejected':False,'needs_review':True}
    repo.save_records(build['build_id'],[record])
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    try:
        manager.set_disposition(build['build_id'],'r1','accepted',expected_revision=1)
        assert False, 'accept should require metadata resolution'
    except ValueError as exc:
        assert 'metadata' in str(exc).lower()
    updated=manager.patch_metadata(build['build_id'],'r1',{'position_holder':'Jacques Derrida'},expected_revision=1)
    assert updated['metadata_review_fields']==[]
    accepted=manager.set_disposition(build['build_id'],'r1','accepted',expected_revision=2)
    assert accepted['accepted'] is True
    assert accepted['metadata_field_status']['discourse_role']['status']=='human_confirmed'




