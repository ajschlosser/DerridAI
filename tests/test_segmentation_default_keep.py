"""Segmentation review bookkeeping and "default to KEEP" behavior.

Why: the builder asks an LLM whether adjacent blocks belong in the same record. A
failed or non-committal answer must never split text or flood reviewers with
false "unresolved region" items: uncertainty defaults to keeping blocks together.
How: builds a temporary repository and monkeypatches the candidate finder and the
LLM batch call, then runs PdfCorpusBuildManager._segment.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb


def _blocks(n=12):
    """Build n simple paragraph blocks (b0..b{n-1}) on one page for segmentation tests."""
    return [{"block_id":f"b{i}","page":1,"type":"paragraph","text":f"Paragraph {i}. This argument continues in a stable way.","bbox":[0,i,1,i+1]} for i in range(n)]


def test_boundary_review_does_not_mark_neighbor_records_needs_review():
    """A reviewed boundary annotates both neighbors without flagging them.

    What: one uncertain boundary between r1 and r2 is recorded as boundary_review_after
    on r1 and boundary_review_before on r2.
    Why: the boundary is a note for the reviewer; it must not flip needs_review on
    otherwise-fine records.
    """
    records=[{"record_id":"r1","source_block_ids":["b0","b1"],"needs_review":False},{"record_id":"r2","source_block_ids":["b2","b3"],"needs_review":False}]
    review={"after_block_id":"b1","next_block_id":"b2","kind":"semantic_boundary_uncertain","reason":"test"}
    cb.PdfCorpusBuildManager._mark_segmentation_review(records,[review])
    assert records[0]["needs_review"] is False
    assert records[1]["needs_review"] is False
    assert records[0]["boundary_review_after"][0]["kind"]=="semantic_boundary_uncertain"
    assert records[1]["boundary_review_before"][0]["kind"]=="semantic_boundary_uncertain"


def test_failed_local_classifier_defaults_to_keep_without_unresolved_region(monkeypatch,tmp_path):
    """If the boundary classifier fails, keep the blocks together and raise no review.

    How: the candidate finder returns one candidate and the batch call returns an
    error ("bad json"). Expect no boundaries, zero boundary_review_count, and an empty
    segmentation_boundary_reviews list on the saved build.
    Why: text must be conserved; a provider failure is not evidence of a boundary.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":1,"source_block_count":12,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":6,"provider":"ollama","model":"test","request":{},"warnings":[]})
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[{"after_block_id":"b5","next_block_id":"b6","signals":["quotation_frame_change"],"candidate_score":.5,"source":"test","index":5,"protected":False}])
    monkeypatch.setattr(manager,"_segment_candidate_batch",lambda *args,**kwargs:({},"bad json"))
    boundaries=manager._segment(_blocks(),{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert boundaries==[]
    assert refreshed.get("segmentation_boundary_reviews")==[]
    assert refreshed.get("boundary_review_count")==0


def test_explicit_uncertain_defaults_to_keep_without_boundary_review(monkeypatch,tmp_path):
    """An omitted or uncertain adjudication is treated as KEEP.

    How: same setup, but the batch call returns no decision and no error.
    Why: the v6 adjudication is binary and cannot express uncertainty; omission is its
    operational equivalent, so it must not create boundaries or review items.
    """
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    build=repo.create_build({"asset_id":"a","source_sha256":"x","source_filename":"x.pdf","source_page_count":1,"source_block_count":12,"schema_version":cb.SCHEMA_VERSION,"profile_id":cb.PROFILE_VERSION,"profile_version":6,"provider":"ollama","model":"test","request":{},"warnings":[]})
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    monkeypatch.setattr(manager,"_deterministic_boundary_candidates",lambda blocks,profile:[{"after_block_id":"b5","next_block_id":"b6","signals":["quotation_frame_change"],"candidate_score":.5,"source":"test","index":5,"protected":False}])
    # Binary v6 adjudication cannot return uncertainty; omission is its operational equivalent and defaults to KEEP.
    monkeypatch.setattr(manager,"_segment_candidate_batch",lambda *args,**kwargs:({},None))
    boundaries=manager._segment(_blocks(),{}, {"provider":"ollama","model":"test"}, build["build_id"])
    refreshed=repo.get_build(build["build_id"])
    assert boundaries==[]
    assert refreshed["boundary_review_count"]==0
    assert refreshed["segmentation_boundary_reviews"]==[]
