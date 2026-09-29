# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.pipelines.defaults import BUILT_IN_PIPELINES
from app.pipelines.models import PipelineDefinition
from app.pipelines.service import PipelineService, pipeline_hash


def test_built_in_pipeline_catalog_is_graph_valid() -> None:
    service = PipelineService()

    results = {item.pipeline_id: service.validate(item) for item in BUILT_IN_PIPELINES}

    assert results
    for pipeline_id, result in results.items():
        assert result.valid, (pipeline_id, result.model_dump())
    reviewer = results["evidence.reviewer.current"]
    assert any(issue.code == "evidence_without_support_gate" for issue in reviewer.issues)


def test_pipeline_validator_rejects_unknown_strategy_and_cycles() -> None:
    service = PipelineService()
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "broken",
            "version": 1,
            "name": "Broken",
            "purpose": "test",
            "entry_stage_ids": ["a"],
            "stages": [
                {
                    "id": "a",
                    "strategy": "retrieve.lexical_bm25",
                    "next": ["b"],
                },
                {
                    "id": "b",
                    "strategy": "missing.strategy",
                    "next": ["a"],
                },
            ],
        }
    )

    result = service.validate(pipeline)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "unknown_strategy" in codes
    assert "cycle" in codes


def test_pipeline_validator_checks_stage_contract_types() -> None:
    service = PipelineService()
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "bad-types",
            "version": 1,
            "name": "Bad types",
            "purpose": "test",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.chroma_similarity",
                    "next": ["generate"],
                },
                {
                    "id": "generate",
                    "strategy": "llm.generate_answer",
                },
            ],
        }
    )

    result = service.validate(pipeline)

    assert result.valid is False
    assert any(issue.code == "incompatible_stage_types" for issue in result.issues)


def test_pipeline_hash_is_stable_for_equivalent_model_dumps() -> None:
    pipeline = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "research.current")
    reconstructed = PipelineDefinition.model_validate(pipeline.model_dump(mode="json"))

    assert pipeline_hash(pipeline) == pipeline_hash(reconstructed)


def test_builtin_resolution_exposes_assignment_pipeline_and_validation() -> None:
    result = PipelineService().resolve_builtin("research")

    assert result["assignment"]["pipeline_id"] == "research.current"
    assert result["pipeline"]["purpose"] == "research"
    assert result["validation"]["valid"] is True
    assert len(result["pipeline_hash"]) == 64
