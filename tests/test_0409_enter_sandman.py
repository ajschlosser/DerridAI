from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb


def _blocks(n=20, chars=180):
    unit="A stable philosophical paragraph continues its argument. "
    text=(unit * max(8,(chars//len(unit))+2))[:chars]
    return [{"block_id":f"b{i}","page":1+(i//8),"type":"paragraph","text":text,"bbox":[0,i,1,i+1]} for i in range(n)]


def _build(tmp_path, n=20):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":3,"source_block_count":n,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":6,"provider":"ollama","model":"test","request":{},"warnings":[]})
    return repo,build,cb.PdfCorpusBuildManager(repo,max_workers=1)


def test_release_uses_v6_segmentation_contract():
    assert cb.PROFILE_VERSION=="derrida-scholarly-v6"
    assert cb.SEGMENTATION_PROMPT_VERSION=="derridai-local-boundaries-v6"
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["version"]==6
    assert profile["boundary_batch_size"]>=2
    assert profile["max_llm_boundary_calls_per_100_atoms"]<100


def test_soft_length_alone_never_creates_candidate():
    blocks=_blocks(40,chars=900)
    candidates=cb.PdfCorpusBuildManager._deterministic_boundary_candidates(blocks,cb.CORPUS_PROFILES[cb.PROFILE_VERSION])
    assert all("soft_length_candidate" not in c.get("signals",[]) for c in candidates)
    assert candidates==[]


def test_heading_start_is_deterministic_split_and_heading_body_is_protected():
    blocks=_blocks(4)
    blocks[1].update(type="heading",text="CHAPTER TWO")
    candidates=cb.PdfCorpusBuildManager._deterministic_boundary_candidates(blocks,cb.CORPUS_PROFILES[cb.PROFILE_VERSION])
    by_after={c["after_block_id"]:c for c in candidates}
    assert cb.PdfCorpusBuildManager._candidate_route(by_after["b0"],cb.CORPUS_PROFILES[cb.PROFILE_VERSION])=="split"
    assert by_after["b1"]["protected"] is True
    assert cb.PdfCorpusBuildManager._candidate_route(by_after["b1"],cb.CORPUS_PROFILES[cb.PROFILE_VERSION])=="keep"


def test_attribution_lead_to_quote_is_protected():
    left={"block_id":"a","type":"paragraph","text":"Derrida writes:"}
    right={"block_id":"b","type":"paragraph","text":"“The proposition begins here.”"}
    assert cb.PdfCorpusBuildManager._is_protected_transition(left,right) is True


def test_llm_batch_omission_and_failure_default_to_keep(monkeypatch,tmp_path):
    repo,build,manager=_build(tmp_path,12)
    candidate={"after_block_id":"b5","next_block_id":"b6","signals":["quotation_frame_change"],"candidate_score":.6,"source":"test","index":5,"protected":False}
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[candidate])
    monkeypatch.setattr(manager,"_segment_candidate_batch",lambda *args,**kwargs:({},"malformed"))
    boundaries=manager._segment(_blocks(12),{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert boundaries==[]
    assert refreshed["boundary_review_count"]==0
    assert refreshed["boundary_classifier_failure_count"]==1
    assert refreshed["boundary_llm_keep_count"]==1


def test_llm_adjudication_budget_limits_work(monkeypatch,tmp_path):
    repo,build,manager=_build(tmp_path,100)
    candidates=[{"after_block_id":f"b{i}","next_block_id":f"b{i+1}","signals":["quotation_frame_change"],"candidate_score":.5,"source":"test","index":i,"protected":False} for i in range(60)]
    calls=[]
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:candidates)
    def batch(batch,*args,**kwargs):
        calls.extend(c["after_block_id"] for c in batch)
        return {},None
    monkeypatch.setattr(manager,"_segment_candidate_batch",batch)
    manager._segment(_blocks(100),{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert len(calls)==18
    assert refreshed["boundary_budget_skipped_count"]==42
    assert refreshed["boundary_llm_adjudication_count"]==18
    assert refreshed["boundary_review_count"]==0


def test_safe_hard_size_split_is_provisional_not_review(monkeypatch,tmp_path):
    repo,build,manager=_build(tmp_path,6)
    blocks=_blocks(6,chars=3000)
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[])
    boundaries=manager._segment(blocks,{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert any(b.get("provisional") for b in boundaries)
    assert refreshed["boundary_review_count"]==0
    assert refreshed["provisional_boundary_count"]>=1


def test_forced_protected_size_split_is_only_review_case(monkeypatch,tmp_path):
    repo,build,manager=_build(tmp_path,5)
    blocks=_blocks(5,chars=3200)
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[])
    monkeypatch.setattr(manager,"_best_safety_boundary",lambda span,hard_max:(span[1],True))
    manager._segment(blocks,{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["boundary_review_count"]>=1
    assert refreshed["segmentation_boundary_reviews"][0]["kind"]=="forced_protected_size_split"


def test_topology_sanity_catches_oversized_records():
    ok=cb.PdfCorpusBuildManager._topology_sanity([{"text":"x"*1000,"text_length":1000}],12000)
    bad=cb.PdfCorpusBuildManager._topology_sanity([{"text":"x"*15000,"text_length":15000}],12000)
    assert ok["valid"] is True
    assert bad["valid"] is False
    assert "oversized_record" in bad["issues"]


def test_segmentation_cache_fingerprint_changes_with_prompt_or_text(tmp_path):
    repo,build,manager=_build(tmp_path,2)
    req={"provider":"ollama","model":"test"}
    a={"block_id":"a","text":"one"}; b={"block_id":"b","text":"two"}
    first=manager._boundary_cache_fingerprint(a,b,req)
    b["text"]="changed"
    second=manager._boundary_cache_fingerprint(a,b,req)
    assert first!=second


def test_storybook_and_i18n_expose_segmentation_telemetry():
    component=(ROOT/"web/src/components/CorpusSegmentationTelemetry.vue").read_text(encoding="utf-8")
    story=(ROOT/"web/src/components/CorpusSegmentationTelemetry.stories.ts").read_text(encoding="utf-8")
    store=(ROOT/"api/app/system_store.py").read_text(encoding="utf-8")
    assert '<dl>' in component and ':aria-labelledby="headingId"' in component and 'useId' in component
    assert "Segmentation Telemetry" in story
    assert '"pdf_corpus.segmentation_telemetry"' in store
    assert '"pdf_corpus.boundary_failures_kept"' in store


def test_v5_profile_remains_registered_for_0408_build_compatibility():
    assert "derrida-scholarly-v5" in cb.CORPUS_PROFILES
    assert cb.CORPUS_PROFILES["derrida-scholarly-v5"]["version"] == 5


def test_new_build_default_and_ui_do_not_drift_from_v6_profile():
    models=(ROOT/"api/app/models.py").read_text(encoding="utf-8")
    builder=(ROOT/"web/src/components/PdfCorpusBuilder.vue").read_text(encoding="utf-8")
    assert 'default="derrida-scholarly-v6"' in models
    assert 'profile_id:"derrida-scholarly-v5"' not in builder
