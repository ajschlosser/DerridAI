"""Deterministic-first segmentation: candidates, routing, budgets.

Why: asking an LLM about every block boundary is slow and unreliable. The builder
first finds candidate boundaries with cheap deterministic signals, routes the clear
ones itself, asks the LLM only about the ambiguous ones within a fixed budget, and
always defaults to KEEP (never split) when unsure.
How: `_blocks` makes uniform paragraph blocks; `_build` creates a temp repository and
manager; the LLM batch call is monkeypatched so no provider is needed.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb


def _blocks(n=20, chars=180):
    """Build n paragraph blocks of roughly `chars` characters each, eight per page."""
    unit="A stable philosophical paragraph continues its argument. "
    text=(unit * max(8,(chars//len(unit))+2))[:chars]
    return [{"block_id":f"b{i}","page":1+(i//8),"type":"paragraph","text":text,"bbox":[0,i,1,i+1]} for i in range(n)]


def _build(tmp_path, n=20):
    """Create a temp repository, an empty build, and a manager for segmentation tests."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":3,"source_block_count":n,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":7,"provider":"ollama","model":"test","request":{},"warnings":[]})
    return repo,build,cb.PdfCorpusBuildManager(repo,max_workers=1)


def test_segmentation_contract_has_one_current_profile():
    """Pin the segmentation contract: prompt version, single profile, and batching limits.

    Checks the active profile/prompt ids, that only one profile is registered, that
    boundary batches hold at least 2 candidates, and that LLM calls per 100 atoms stay
    under 100 (the budget that keeps builds fast). Update the ids when they are bumped.
    """
    assert cb.PROFILE_VERSION=="derrida-scholarly-v12"
    assert cb.SEGMENTATION_PROMPT_VERSION=="derridai-local-boundaries-v7"
    assert set(cb.CORPUS_PROFILES) == {cb.PROFILE_VERSION}
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["boundary_batch_size"]>=2
    assert profile["max_llm_boundary_calls_per_100_atoms"]<100


def test_soft_length_alone_never_creates_candidate():
    """Long text on its own is not a reason to look for a boundary.

    40 blocks of 900 characters yield no candidates at all; size is handled later by the
    topology normalizer, never by asking the LLM.
    """
    blocks=_blocks(40,chars=900)
    candidates=cb.PdfCorpusBuildManager._deterministic_boundary_candidates(blocks,cb.CORPUS_PROFILES[cb.PROFILE_VERSION])
    assert all("soft_length_candidate" not in c.get("signals",[]) for c in candidates)
    assert candidates==[]


def test_heading_start_is_deterministic_split_and_heading_body_is_protected():
    """A heading starts a new record without an LLM, and is never separated from its body.

    The boundary before "CHAPTER TWO" routes to "split"; the boundary right after the
    heading is protected and routes to "keep".
    """
    blocks=_blocks(4)
    blocks[1].update(type="heading",text="CHAPTER TWO")
    candidates=cb.PdfCorpusBuildManager._deterministic_boundary_candidates(blocks,cb.CORPUS_PROFILES[cb.PROFILE_VERSION])
    by_after={c["after_block_id"]:c for c in candidates}
    assert cb.PdfCorpusBuildManager._candidate_route(by_after["b0"],cb.CORPUS_PROFILES[cb.PROFILE_VERSION])=="split"
    assert by_after["b1"]["protected"] is True
    assert cb.PdfCorpusBuildManager._candidate_route(by_after["b1"],cb.CORPUS_PROFILES[cb.PROFILE_VERSION])=="keep"


def test_attribution_lead_to_quote_is_protected():
    """"Derrida writes:" followed by a quotation must never be split.

    Why: separating an attribution from its quote would misattribute the proposition.
    """
    left={"block_id":"a","type":"paragraph","text":"Derrida writes:"}
    right={"block_id":"b","type":"paragraph","text":"“The proposition begins here.”"}
    assert cb.PdfCorpusBuildManager._is_protected_transition(left,right) is True


def test_llm_batch_omission_and_failure_default_to_keep(monkeypatch,tmp_path):
    """If the classifier errors, keep the text together and count the failure.

    Expect no classifier-created boundaries, zero review items, one recorded classifier
    failure, and one "keep" decision counted.
    """
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
    """Only a bounded number of candidates is sent to the LLM.

    With 60 candidates over 100 atoms the budget allows 16 calls; the other 44 are
    counted as skipped (defaulting to keep) and produce no review items.
    """
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
    assert len(calls)==16
    assert refreshed["boundary_budget_skipped_count"]==44
    assert refreshed["boundary_llm_adjudication_count"]==16
    assert refreshed["boundary_review_count"]==0


def test_record_sizing_normalizer_adds_retrieval_boundaries_without_review(monkeypatch,tmp_path):
    """Oversize runs are split for retrieval without asking a human.

    With no semantic candidates, 16 blocks of ~260 chars get size-optimized boundaries
    marked as non-semantic ("retrieval_size_optimized") and no review count.
    """
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
    """A 1,800-char record is valid (median reported); a 6,500-char record is not."""
    policy={"preferred_record_chars":1750,"record_length_tolerance":200,"long_record_chars":3500,"absolute_record_chars":6000}
    ok=cb.PdfCorpusBuildManager._topology_sanity([{"record_id":"r1","text":"x"*1800,"text_length":1800,"source_block_ids":[]}],policy)
    bad=cb.PdfCorpusBuildManager._topology_sanity([{"record_id":"r1","text":"x"*6500,"text_length":6500,"source_block_ids":[]}],policy)
    assert ok["valid"] is True
    assert ok["median_record_chars"]==1800
    assert bad["valid"] is False
    assert "topology.over_absolute_limit" in bad["issues"]


def test_segmentation_cache_fingerprint_changes_with_prompt_or_text(tmp_path):
    """The boundary cache key changes when the text changes.

    Why: reusing a cached boundary verdict for edited text would give a stale decision.
    """
    repo,build,manager=_build(tmp_path,2)
    req={"provider":"ollama","model":"test"}
    a={"block_id":"a","text":"one"}; b={"block_id":"b","text":"two"}
    first=manager._boundary_cache_fingerprint(a,b,req)
    b["text"]="changed"
    second=manager._boundary_cache_fingerprint(a,b,req)
    assert first!=second




