# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import dataclasses

from app import config
from app import cross_encoder as cross_encoder_module
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


def test_current_evidence_pipeline_compiles_to_legacy_reviewer_chain() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 1)
    assert pipeline is not None

    plan = compile_evidence_pipeline(pipeline)

    assert plan.query_stage_id == "query"
    assert plan.semantic_stage_id == "semantic"
    assert plan.lexical_stage_id == "lexical"
    assert plan.rerank_stage_id is None
    assert plan.support_stage_id is None
    assert plan.select_stage_id == "select"


def test_conservative_evidence_pipeline_compiles_support_gate_and_fallback() -> None:
    pipeline = built_in_pipeline("evidence.conservative", 1)
    assert pipeline is not None

    plan = compile_evidence_pipeline(pipeline)

    assert plan.rerank_stage_id == "rerank"
    assert plan.support_stage_id == "support"
    assert plan.llm_stage_id == "llm_choice"


def test_current_evidence_execution_preserves_separate_lexical_semantic_signals() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 1)
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
    assert trace["lexical"].elapsed_ms is None
    assert trace["semantic"].elapsed_ms is None


def test_semantic_failure_is_visible_in_evidence_trace_without_losing_lexical_result() -> None:
    pipeline = built_in_pipeline("evidence.reviewer.current", 1)
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
    trace = {stage.stage_id: stage for stage in result.trace.stages}
    assert trace["rerank"].score_summary["max"] == 0.9
    assert trace["support"].input_count == 2
    assert trace["support"].output_count == 1
    assert trace["llm_choice"].status == "skipped"
