# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.memory import (
    classify_memory_failure,
    compile_memory_pipeline,
)


@pytest.mark.parametrize(
    ("pipeline_id", "purpose", "fetch_k", "limit"),
    [
        ("memory.claim.current", "claim_memory", 6, 6),
        ("memory.response.current", "response_memory", 4, 4),
    ],
)
def test_builtin_memory_pipelines_compile(
    pipeline_id: str,
    purpose: str,
    fetch_k: int,
    limit: int,
) -> None:
    pipeline = built_in_pipeline(pipeline_id, 1)
    assert pipeline is not None

    plan = compile_memory_pipeline(pipeline)

    assert plan.purpose == purpose
    assert plan.retrieve_stage_id == "retrieve"
    assert plan.lexical_fallback_stage_id == "lexical"
    assert plan.select_stage_id == "select"
    assert plan.fetch_k == fetch_k
    assert plan.fallback_fetch_k == fetch_k
    assert plan.selection_limit == limit
    assert plan.min_similarity == pytest.approx(0.5)
    assert plan.fallback_unavailable == "lexical"
    assert plan.fallback_timeout == "lexical"
    assert plan.fallback_error == "lexical"


def test_memory_pipeline_can_explicitly_disable_lexical_fallback() -> None:
    source = built_in_pipeline("memory.response.current", 1)
    assert source is not None
    stages = []
    for stage in source.stages:
        if stage.id == "retrieve":
            stage = stage.model_copy(
                update={
                    "on_unavailable": None,
                    "on_timeout": None,
                    "on_error": None,
                    "config": {"fetch_k": 9, "min_similarity": 0.72},
                }
            )
        if stage.id == "select":
            stage = stage.model_copy(update={"config": {"limit": 3}})
        if stage.id != "lexical":
            stages.append(stage)

    custom = source.model_copy(
        update={
            "pipeline_id": "memory.response.no-fallback",
            "built_in": False,
            "stages": stages,
        }
    )
    plan = compile_memory_pipeline(custom)

    assert plan.lexical_fallback_stage_id is None
    assert plan.fetch_k == 9
    assert plan.selection_limit == 3
    assert plan.min_similarity == pytest.approx(0.72)
    assert plan.fallback_for("error") is None


def test_memory_pipeline_rejects_fallback_that_does_not_rejoin_selection() -> None:
    source = built_in_pipeline("memory.claim.current", 1)
    assert source is not None
    stages = [
        stage.model_copy(update={"next": []})
        if stage.id == "lexical"
        else stage
        for stage in source.stages
    ]
    custom = source.model_copy(
        update={
            "pipeline_id": "memory.claim.bad-fallback",
            "built_in": False,
            "stages": stages,
        }
    )

    with pytest.raises(ValueError, match="must rejoin"):
        compile_memory_pipeline(custom)


def test_memory_failure_classification_matches_graph_edges() -> None:
    assert classify_memory_failure(TimeoutError("slow")) == "timeout"
    assert classify_memory_failure(ImportError("missing")) == "unavailable"
    assert classify_memory_failure(RuntimeError("offline")) == "error"
