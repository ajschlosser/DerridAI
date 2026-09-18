from __future__ import annotations

import json
from pathlib import Path
import sys
import types

sys.modules.setdefault("chromadb", types.SimpleNamespace())

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"api"))
from app import corpus_builder as cb
from app.models import PdfCorpusBuildCreate

POLICY={"preferred_record_chars":1750,"record_length_tolerance":200,"long_record_chars":3500,"absolute_record_chars":6000}

def block(i:int,chars:int=320,kind:str="paragraph",text:str|None=None):
    base=("A philosophical sentence develops one coherent point and closes cleanly. "*20)[:chars]
    return {"block_id":f"b{i}","page":1+i//8,"type":kind,"text":text or base,"bbox":[0,i,1,i+1],"extraction_method":"text","confidence":1.0}

def test_release_profile_and_default_record_sizing():
    assert cb.PROFILE_VERSION=="derrida-scholarly-v11"
    profile=cb.CORPUS_PROFILES[cb.PROFILE_VERSION]
    assert profile["preferred_record_chars"]==1750
    assert profile["record_length_tolerance"]==200
    assert profile["long_record_chars"]==3500
    assert profile["absolute_record_chars"]==6000
    body=PdfCorpusBuildCreate(asset_id="asset")
    assert body.profile_id=="derrida-scholarly-v11"
    assert body.record_sizing.preferred_record_chars==1750
    assert body.record_sizing.absolute_record_chars==6000


def test_normalizer_targets_preferred_range_without_removing_semantic_boundary():
    blocks=[block(i,330) for i in range(18)]
    semantic={"after_block_id":"b8","decision":"split","confidence":1.0,"source":"semantic","semantic_boundary":True}
    boundaries,reviews,metrics=cb.PdfCorpusBuildManager._normalize_topology(blocks,[semantic],POLICY)
    ids={b["after_block_id"] for b in boundaries}
    assert "b8" in ids
    assert reviews==[]
    assert metrics["size_optimized_splits"]>=1
    records=cb.PdfCorpusBuildManager._construct_records({"filename":"fixture.pdf","asset_id":"a"},blocks,boundaries)
    assert max(r["text_length"] for r in records)<=POLICY["long_record_chars"]
    assert all(sum(1 for r in records if bid in r["source_block_ids"])==1 for bid in [b["block_id"] for b in blocks])


def test_coherent_exception_is_allowed_when_no_good_target_seam():
    blocks=[
        block(0,1700,text="Derrida writes:"),
        block(1,1450,text="“"+(("The quoted thought remains attached to its attribution. "*40)[:1448])+"”"),
    ]
    # The only target seam is attribution-protected, so the unit may remain a
    # coherent exception below the long-record limit rather than forcing a cut.
    boundaries,reviews,metrics=cb.PdfCorpusBuildManager._normalize_topology(blocks,[],POLICY)
    assert boundaries==[]
    assert reviews==[]
    assert metrics["absolute_safety_splits"]==0


def test_topology_validator_detects_gap_overlap_order_and_size():
    blocks=[block(i,300) for i in range(4)]
    records=[
        {"record_id":"r1","text":"x"*1700,"text_length":1700,"source_block_ids":["b0","b1"]},
        {"record_id":"r2","text":"x"*6200,"text_length":6200,"source_block_ids":["b1","b3"]},
    ]
    report=cb.PdfCorpusBuildManager._topology_sanity(records,POLICY,blocks)
    codes={f["code"] for f in report["findings"]}
    assert report["valid"] is False
    assert "topology.over_absolute_limit" in codes
    assert "topology.source_gap" in codes
    assert "topology.source_overlap" in codes


def test_quality_report_exposes_distribution_and_conservation():
    blocks=[block(i,300) for i in range(6)]
    boundaries=[{"after_block_id":"b2"}]
    records=cb.PdfCorpusBuildManager._construct_records({"filename":"fixture.pdf","asset_id":"a"},blocks,boundaries)
    validation=cb.PdfCorpusBuildManager._topology_sanity(records,POLICY,blocks)
    quality=cb.PdfCorpusBuildManager._topology_quality_report(records,blocks,POLICY,validation)
    assert quality["source_coverage"]==1.0
    assert quality["source_conservation_valid"] is True
    assert quality["p10_record_chars"]>0
    assert quality["p90_record_chars"]>=quality["p10_record_chars"]


def test_storybook_i18n_and_accessibility_surfaces_exist():
    sizing=(ROOT/"web/src/components/CorpusRecordSizingSettings.vue").read_text(encoding="utf-8")
    stories=(ROOT/"web/src/components/CorpusRecordSizingSettings.stories.ts").read_text(encoding="utf-8")
    quality=(ROOT/"web/src/components/CorpusQualitySummary.vue").read_text(encoding="utf-8")
    store=(ROOT/"api/app/system_store.py").read_text(encoding="utf-8")
    assert "<fieldset" in sizing and "<legend>" in sizing and "aria-describedby" in sizing
    assert "Record Sizing Settings" in stories
    assert "source_conservation_valid" in quality
    assert '"pdf_corpus.record_sizing.preferred"' in store
    assert '"pdf_corpus.quality.size_detail"' in store


def test_acceptance_fixture_invariants():
    fixture=json.loads((ROOT/"tests/fixtures/corpus_builder/topology_cases.json").read_text(encoding="utf-8"))
    for case in fixture["cases"]:
        blocks=case["blocks"]
        boundaries,reviews,_=cb.PdfCorpusBuildManager._normalize_topology(blocks,case.get("semantic_boundaries",[]),POLICY)
        records=cb.PdfCorpusBuildManager._construct_records({"filename":f"{case['id']}.pdf","asset_id":case["id"]},blocks,boundaries)
        validation=cb.PdfCorpusBuildManager._topology_sanity(records,POLICY,blocks)
        assert validation["valid"],case["id"]
        assert not reviews,case["id"]
        assert len({bid for r in records for bid in r["source_block_ids"]})==len(blocks)
        assert validation["max_record_chars"]<=case.get("max_expected_chars",6000)
