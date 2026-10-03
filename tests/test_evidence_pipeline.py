# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import dataclasses

import pytest
from app import config
from app import cross_encoder as cross_encoder_module
from app.pipelines.comparison import (
    compare_evidence_runs,
    summarize_evidence_suggestion_run,
)
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.evidence import (
    compile_evidence_pipeline,
    execute_reviewer_evidence_pipeline,
)


class LocalProjection:
    def __init__(self, vectors, query_vector=None, error=None):
        self.vectors = vectors
        self.query_vector = query_vector or [1.0, 0.0]
        self.error = error
        self.queries = []

    def sync(self, *args, **kwargs):
        if self.error:
            raise self.error

    def embeddings_for(self, _document_id, _unit_ids, **_kwargs):
        return self.vectors

    def embed_query(self, query, **_kwargs):
        self.queries.append(query)
        return self.query_vector


def test_current_evidence_pipeline_requires_support_and_provenance() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 2)
    assert pipeline is not None

    plan = compile_evidence_pipeline(pipeline)

    assert plan.query_stage_id == "query"
    assert plan.semantic_stage_id == "semantic"
    assert plan.lexical_stage_id == "lexical"
    assert plan.rerank_stage_id is None
    assert plan.support_stage_id == "support"
    assert plan.provenance_stage_id == "provenance"
    assert plan.select_stage_id == "select"


def test_legacy_reviewer_pipeline_remains_inspectable_but_not_executable() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 1)
    assert pipeline is not None
    assert pipeline.status == "disabled"

    with pytest.raises(ValueError, match="validate.evidence_support"):
        compile_evidence_pipeline(pipeline)


def test_conservative_evidence_pipeline_compiles_support_gate_and_fallback() -> None:
    pipeline = built_in_pipeline("evidence.conservative", 1)
    assert pipeline is not None

    plan = compile_evidence_pipeline(pipeline)

    assert plan.rerank_stage_id == "rerank"
    assert plan.support_stage_id == "support"
    assert plan.provenance_stage_id == "provenance"
    assert plan.llm_stage_id == "llm_choice"


def test_current_evidence_execution_preserves_separate_lexical_semantic_signals() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 2)
    assert pipeline is not None
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    projection = LocalProjection({"b1": [1.0, 0.0]})

    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=projection,
    )

    assert result.items[0]["block_id"] == "b1"
    assert result.items[0]["lexical_score"] == 1.0
    assert result.items[0]["semantic_score"] == 1.0
    assert result.status["pipeline_id"] == "evidence.reviewer.current"
    assert result.status["trace_id"] == result.trace.run_id
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["lexical"].output_count == 1
    assert trace["semantic"].output_count == 1
    assert trace["lexical"].elapsed_ms is not None
    assert trace["semantic"].elapsed_ms is not None
    for stage_id in ("lexical", "semantic"):
        assert trace[stage_id].parameters["scope_size"] == len(blocks)


def test_semantic_failure_is_visible_in_evidence_trace_without_losing_lexical_result() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 2)
    assert pipeline is not None
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    projection = LocalProjection({}, error=RuntimeError("embedding backend unavailable"))

    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=projection,
    )

    assert result.items[0]["block_id"] == "b1"
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["semantic"].status == "unavailable"
    assert "embedding backend unavailable" in str(trace["semantic"].fallback_reason)
    assert trace["lexical"].status == "completed"


def test_conservative_pipeline_keeps_relevance_and_support_scores_distinct(monkeypatch) -> None:
    pipeline = built_in_pipeline("evidence.conservative", 1)
    assert pipeline is not None
    blocks = [
        {"block_id": "b1", "text": "Hospitality is named directly in this passage."},
        {"block_id": "b2", "text": "A semantically related passage about welcoming strangers."},
    ]
    projection = LocalProjection(
        {"b1": [1.0, 0.0], "b2": [0.95, 0.05]},
        query_vector=[1.0, 0.0],
    )
    monkeypatch.setattr(
        config,
        "settings",
        dataclasses.replace(config.settings, metadata_cross_encoder_enabled=True),
    )

    def fake_predict_scores(pairs, *, model_name, timeout_seconds):
        assert len(pairs) == 2
        return [0.2, 0.9], {"requested_reranker": "cross_encoder"}

    monkeypatch.setattr(cross_encoder_module, "predict_scores", fake_predict_scores)

    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=projection,
        limit=2,
    )

    assert [item["block_id"] for item in result.items] == ["b1"]
    item = result.items[0]
    assert item["cross_encoder_score"] == 0.2
    assert item["support_score"] == 1.0
    assert item["support_status"] == "supported"
    decisions = {
        row["block_id"]: row
        for row in result.status["candidate_decisions"]
    }
    assert decisions["b1"]["decision"] == "selected"
    assert decisions["b2"]["decision"] == "rejected_support"
    assert decisions["b2"]["cross_encoder_score"] == 0.9
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["rerank"].score_summary["max"] == 0.9
    assert trace["support"].input_count == 2
    assert trace["support"].output_count == 1
    assert trace["llm_choice"].status == "skipped"
    assert trace["provenance"].input_count == 1
    assert trace["provenance"].output_count == 1



def test_provenance_gate_rejects_candidates_without_source_document_identity() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 2)
    assert pipeline is not None
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    projection = LocalProjection({"b1": [1.0, 0.0]})

    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="",
        projection=projection,
    )

    assert result.items == []
    decisions = {
        row["block_id"]: row
        for row in result.status["candidate_decisions"]
    }
    assert decisions["b1"]["decision"] == "rejected_provenance"
    assert decisions["b1"]["provenance_status"] == "rejected"
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["support"].output_count == 1
    assert trace["provenance"].input_count == 1
    assert trace["provenance"].output_count == 0



def test_support_and_provenance_gates_cannot_expose_bypass_edges() -> None:
    source = built_in_pipeline("evidence.reviewer.current", 2)
    assert source is not None

    support_bypass = source.model_copy(
        update={
            "pipeline_id": "evidence.support-bypass",
            "built_in": False,
            "stages": [
                stage.model_copy(update={"on_error": "select"})
                if stage.id == "support"
                else stage
                for stage in source.stages
            ],
        }
    )
    with pytest.raises(ValueError, match="support stage may not use on_error"):
        compile_evidence_pipeline(support_bypass)

    provenance_bypass = source.model_copy(
        update={
            "pipeline_id": "evidence.provenance-bypass",
            "built_in": False,
            "stages": [
                stage.model_copy(update={"on_error": "select"})
                if stage.id == "provenance"
                else stage
                for stage in source.stages
            ],
        }
    )
    with pytest.raises(ValueError, match="cannot expose a bypass edge"):
        compile_evidence_pipeline(provenance_bypass)


def _drop_retriever(source, *, keep: str):
    drop = "semantic" if keep == "lexical" else "lexical"
    stages = []
    for stage in source.stages:
        if stage.id == drop:
            continue
        if stage.id == "query":
            stages.append(stage.model_copy(update={"next": [keep]}))
        else:
            stages.append(stage)
    return source.model_copy(
        update={"pipeline_id": f"evidence.{keep}-only", "built_in": False, "stages": stages}
    )


def test_single_retriever_suggestion_pipeline_runs_only_that_search() -> None:
    source = built_in_pipeline("evidence.reviewer.current", 2)
    pipeline = _drop_retriever(source, keep="lexical")
    plan = compile_evidence_pipeline(pipeline)
    assert plan.lexical_stage_id == "lexical"
    assert plan.semantic_stage_id is None

    blocks = [
        {"block_id": "b1", "text": "Hospitality welcomes the stranger."},
        {"block_id": "b2", "text": "Unrelated meteorological notes."},
    ]
    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=LocalProjection({"b1": [1.0, 0.0], "b2": [0.0, 1.0]}),
    )
    assert [item["block_id"] for item in result.items] == ["b1"]
    assert result.items[0]["lexical_score"] == 1.0
    assert result.items[0]["semantic_score"] is None
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert "semantic" not in trace
    assert trace["lexical"].output_count == 1


def test_retriever_fetch_k_and_min_score_bound_the_search() -> None:
    source = built_in_pipeline("evidence.reviewer.current", 2)
    stages = []
    for stage in source.stages:
        if stage.id == "semantic":
            continue
        if stage.id == "query":
            stages.append(stage.model_copy(update={"next": ["lexical"]}))
        elif stage.id == "lexical":
            stages.append(stage.model_copy(update={"config": {"fetch_k": 1, "min_score": 0.9}}))
        else:
            stages.append(stage)
    pipeline = source.model_copy(
        update={"pipeline_id": "evidence.lexical-bounded", "built_in": False, "stages": stages}
    )
    blocks = [
        {"block_id": "b1", "text": "Hospitality is named here."},
        {"block_id": "b2", "text": "A weaker hospitality mention later."},
    ]
    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=LocalProjection({}),
        limit=5,
    )
    assert len(result.items) == 1
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["lexical"].parameters["fetch_k"] == 1
    assert trace["lexical"].parameters["min_score"] == 0.9
    assert trace["lexical"].output_count == 1


def test_optional_mmr_stage_compiles_and_runs_before_support() -> None:
    source = built_in_pipeline("evidence.reviewer.current", 2)
    stages = []
    for stage in source.stages:
        if stage.id in {"semantic", "lexical"}:
            stages.append(stage.model_copy(update={"next": ["mmr"]}))
        elif stage.id == "support":
            stages.append(stage)
        else:
            stages.append(stage)
    stages.insert(
        3,
        source.stages[0].model_copy(
            update={
                "id": "mmr",
                "strategy": "select.mmr",
                "config": {"limit": 1, "lambda_mult": 1.0},
                "next": ["support"],
                "on_empty": None,
                "on_error": None,
                "on_timeout": None,
                "on_unavailable": None,
            }
        ),
    )
    pipeline = source.model_copy(
        update={"pipeline_id": "evidence.with-mmr", "built_in": False, "stages": stages}
    )
    plan = compile_evidence_pipeline(pipeline)
    assert plan.mmr_stage_id == "mmr"
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    result = execute_reviewer_evidence_pipeline(
        pipeline=pipeline,
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=LocalProjection({"b1": [1.0, 0.0]}),
    )
    assert result.items[0]["block_id"] == "b1"
    assert "mmr" in {stage.stage_id for stage in result.trace.stages}


def test_suggestion_comparison_keeps_hashes_and_omits_source_text() -> None:
    source = built_in_pipeline("evidence.reviewer.current", 2)
    lexical = _drop_retriever(source, keep="lexical")
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger. private source text"}]
    kwargs = dict(
        resolved_hash=None,
        value="hospitality",
        blocks=blocks,
        field_metadata={"name": "topic", "label": "Topic"},
        source_document_id="doc",
        projection=LocalProjection({"b1": [1.0, 0.0]}),
    )
    left = execute_reviewer_evidence_pipeline(pipeline=source, **kwargs)
    right = execute_reviewer_evidence_pipeline(pipeline=lexical, **kwargs)
    compared = compare_evidence_runs(
        summarize_evidence_suggestion_run(left),
        summarize_evidence_suggestion_run(right),
    )
    assert compared["non_persistent"] is True
    assert compared["left"]["pipeline"]["pipeline_id"] == "evidence.reviewer.current"
    assert compared["right"]["pipeline"]["pipeline_id"] == "evidence.lexical-only"
    assert compared["comparison"]["shared_block_ids"] == ["b1"]
    assert "private source text" not in str(compared)


def test_comparison_source_projection_uses_chroma_store(monkeypatch) -> None:
    from app.pipelines import comparison as comparison_module

    captured = {}

    class DummyStore:
        pass

    class DummyProjection:
        def __init__(self, store):
            captured["store"] = store

    monkeypatch.setattr(comparison_module, "store", DummyStore(), raising=False)
    monkeypatch.setattr("app.services.store", DummyStore())
    monkeypatch.setattr("app.source_embeddings.SourceEmbeddingProjection", DummyProjection)
    projection = comparison_module.comparison_source_projection()
    assert isinstance(projection, DummyProjection)
    assert captured["store"] is not None
