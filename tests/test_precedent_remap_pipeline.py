# Copyright 2026 Aaron John Schlosser, PhD.
"""Precedent evidence remapping runs through the precedent_evidence_remap pipeline."""

from __future__ import annotations

import pytest
from app.metadata_precedents_cache import build_precedents_cache, rank_candidates
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.precedent_remap import (
    REMAP_FEATURE,
    RemapSession,
    compile_remap_pipeline,
)
from app.pipelines.service import PipelineService, pipeline_hash

BUILT_IN = ("precedent.remap.current", 1)
EVIDENCE = "The face of the other precedes ontology."
BLOCKS = [
    {"block_id": "b1", "text": "Ontology comes first in this account."},
    {"block_id": "b2", "text": "The face of the other precedes every ontology."},
    {"block_id": "b3", "text": "An unrelated remark about the weather."},
]
VECTORS = {EVIDENCE: [1.0, 0.0], BLOCKS[0]["text"]: [0.5, 0.5], BLOCKS[1]["text"]: [0.95, 0.05], BLOCKS[2]["text"]: [0.1, 0.9]}


def embed(texts):
    return [VECTORS[text] for text in texts]


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


def _use(monkeypatch, stages=None, entry=None):
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "precedent.remap.custom",
        "built_in": False,
        **({"stages": stages(source.stages)} if stages else {}),
        **({"entry_stage_ids": entry} if entry else {}),
    })
    monkeypatch.setattr(
        manager_module.pipeline_manager,
        "resolve",
        lambda _feature: {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)},
    )
    return pipeline


def _ids(ranked):
    return [[item["block_id"] for item in picks] for picks in ranked]


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_remap_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id, plan.limit) == ("semantic", "lexical", 3)
    assignment = built_in_assignment(REMAP_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN


def test_semantic_ranking_is_traced_without_the_precedent_text(traces) -> None:
    session = RemapSession.open()
    ranked = session.rank([EVIDENCE], BLOCKS, embed=embed)
    identity = session.finish()

    assert _ids(ranked) == [["b2", "b1", "b3"]]
    assert {item["method"] for item in ranked[0]} == {"precedent-semantic-v1"}
    assert identity["trace_id"] == traces[0].run_id and identity["feature"] == REMAP_FEATURE
    assert [stage.stage_id for stage in traces[0].stages] == ["semantic", "provenance", "select"]
    assert EVIDENCE not in traces[0].model_dump_json()


def test_missing_embedder_follows_the_fallback_edge(traces) -> None:
    session = RemapSession.open()
    ranked = session.rank([EVIDENCE], BLOCKS, embed=None)
    session.finish()

    assert ranked[0][0]["block_id"] == "b2" and ranked[0][0]["method"] == "precedent-lexical-v1"
    stages = {stage.stage_id: stage for stage in traces[0].stages}
    assert stages["semantic"].status == "unavailable" and stages["semantic"].fallback_reason
    assert stages["lexical"].status == "completed"


def test_stage_config_is_authoritative(monkeypatch, traces) -> None:
    _use(monkeypatch, lambda stages: [
        stage.model_copy(update={"config": {"min_similarity": 0.8}}) if stage.id == "semantic"
        else stage.model_copy(update={"config": {"limit": 1}}) if stage.id == "select"
        else stage
        for stage in stages
    ])
    ranked = RemapSession.open().rank([EVIDENCE], BLOCKS, embed=embed)
    assert _ids(ranked) == [["b2"]]


def test_lexical_only_graph_never_calls_the_embedder(monkeypatch, traces) -> None:
    _use(
        monkeypatch,
        lambda stages: [stage for stage in stages if stage.id != "semantic"],
        entry=["lexical"],
    )
    ranked = RemapSession.open().rank([EVIDENCE], BLOCKS, embed=lambda _texts: pytest.fail("no semantic stage"))
    assert ranked[0][0]["method"] == "precedent-lexical-v1"


def test_without_a_fallback_edge_an_unavailable_embedder_yields_no_candidates(monkeypatch, traces) -> None:
    _use(monkeypatch, lambda stages: [
        stage.model_copy(update={"on_unavailable": None, "on_error": None}) if stage.id == "semantic" else stage
        for stage in stages if stage.id != "lexical"
    ])
    session = RemapSession.open()
    assert session.rank([EVIDENCE], BLOCKS, embed=None) == [[]]
    session.finish()
    assert traces[0].stages[0].status == "unavailable"


def test_unresolvable_assignment_means_no_candidates_not_a_failed_panel(monkeypatch, traces) -> None:
    def missing(_feature):
        raise KeyError(REMAP_FEATURE)

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", missing)
    assert RemapSession.open() is None
    record = {"source_block_ids": ["b2"], "source_spans": []}
    items = [{"exemplar_id": "e1", "evidence": EVIDENCE}]
    assert rank_candidates(items, record, {"b2": BLOCKS[1]}, embed=embed, session=None) == [[]]
    cache = build_precedents_cache(["topic"], {"topic": items}, {}, record, {"b2": BLOCKS[1]}, computed_at="now")
    assert cache["fields"]["topic"]["refs"][0]["candidate_source_units"] == []
    assert "candidate_pipeline" not in cache and traces == []


def test_enrichment_cache_records_one_trace_for_all_fields(traces) -> None:
    record = {"source_block_ids": ["b1", "b2"], "source_spans": []}
    items = [{"exemplar_id": "e1", "evidence": EVIDENCE}]
    cache = build_precedents_cache(
        ["topic", "position_holder"], {"topic": items, "position_holder": items}, {}, record,
        {block["block_id"]: block for block in BLOCKS}, computed_at="now", embed=embed,
    )
    assert len(traces) == 1 and cache["candidate_pipeline"]["trace_id"] == traces[0].run_id
    assert traces[0].stages[0].input_count == 2, "one query per field, both in the same trace"
    candidates = cache["fields"]["topic"]["refs"][0]["candidate_source_units"]
    assert {item["block_id"] for item in candidates} <= {"b1", "b2"}, "only this record's source units"


@pytest.mark.parametrize(
    ("stages", "match"),
    [
        (lambda stages: [s.model_copy(update={"enabled": False}) if s.id == "provenance" else s for s in stages],
         "provenance gate"),
        (lambda stages: [s.model_copy(update={"next": ["select"]}) if s.id == "semantic" else s for s in stages],
         "continues to the provenance gate"),
        (lambda stages: [s.model_copy(update={"config": {"fetch_k": 5}}) if s.id == "semantic" else s for s in stages],
         "does not apply fetch_k"),
    ],
)
def test_unsupported_graphs_are_rejected(stages, match) -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={"pipeline_id": "precedent.remap.bad", "built_in": False,
                                         "stages": stages(source.stages)})
    with pytest.raises(ValueError, match=match):
        compile_remap_pipeline(pipeline)
