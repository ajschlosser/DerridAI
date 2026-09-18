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
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":3,"source_block_count":n,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":7,"provider":"ollama","model":"test","request":{},"warnings":[]})
    return repo,build,cb.PdfCorpusBuildManager(repo,max_workers=1)


def test_current_release_keeps_v6_registered_and_uses_v8_contract():
    assert cb.PROFILE_VERSION=="derrida-scholarly-v11"
    assert cb.SEGMENTATION_PROMPT_VERSION=="derridai-local-boundaries-v7"
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["version"]==11
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
    assert not any(b.get("source")=="local_batch_classifier" for b in boundaries)
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


def test_record_sizing_normalizer_adds_retrieval_boundaries_without_review(monkeypatch,tmp_path):
    repo,build,manager=_build(tmp_path,16)
    blocks=_blocks(16,chars=260)
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[])
    boundaries=manager._segment(blocks,{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert any(b.get("boundary_kind")=="retrieval_size_optimized" for b in boundaries)
    assert all(b.get("semantic_boundary") is False for b in boundaries if b.get("boundary_kind")=="retrieval_size_optimized")
    assert refreshed["boundary_review_count"]==0
    assert refreshed["size_optimized_boundary_count"]>=1


def test_topology_sanity_catches_absolute_oversize_and_reports_distribution():
    policy={"preferred_record_chars":1750,"record_length_tolerance":200,"long_record_chars":3500,"absolute_record_chars":6000}
    ok=cb.PdfCorpusBuildManager._topology_sanity([{"record_id":"r1","text":"x"*1800,"text_length":1800,"source_block_ids":[]}],policy)
    bad=cb.PdfCorpusBuildManager._topology_sanity([{"record_id":"r1","text":"x"*6500,"text_length":6500,"source_block_ids":[]}],policy)
    assert ok["valid"] is True
    assert ok["median_record_chars"]==1800
    assert bad["valid"] is False
    assert "topology.over_absolute_limit" in bad["issues"]


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
    store=(ROOT/"api/app/locales/en_us.py").read_text(encoding="utf-8")+(ROOT/"api/app/locales/fr_ca.py").read_text(encoding="utf-8")
    assert '<dl>' in component and ':aria-labelledby="headingId"' in component and 'useId' in component
    assert "Segmentation Telemetry" in story
    assert 'pdf_corpus.segmentation_telemetry' in store
    assert 'pdf_corpus.boundary_failures_kept' in store


def test_new_build_default_and_ui_do_not_drift_from_v8_profile():
    models=(ROOT/"api/app/models.py").read_text(encoding="utf-8")
    builder=(ROOT/"web/src/components/PdfCorpusBuilder.vue").read_text(encoding="utf-8")
    assert 'default="derrida-scholarly-v11"' in models
    assert 'profile_id:"derrida-scholarly-v5"' not in builder
