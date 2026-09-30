# Copyright 2026 Aaron John Schlosser, PhD.
"""Pipeline purposes, strategy scholarly effects, and their catalog contract."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import get_args

import pytest
from app.pipelines.defaults import BUILT_IN_ASSIGNMENTS, BUILT_IN_PIPELINES
from app.pipelines.manager import PipelineManager
from app.pipelines.models import PipelineAssignment, PipelineRunTrace, ScholarlyEffect
from app.pipelines.purposes import (
    FAMILY_PHASES,
    PIPELINE_PURPOSES,
    WORKFLOW_CATEGORIES,
    WORKFLOW_GUARANTEES,
    PurposeRegistry,
    effect_note,
    purpose_registry,
    workflow_vocabulary,
)
from app.pipelines.registry import strategy_registry
from app.pipelines.service import PipelineService
from app.pipelines.store import PipelineStore
from app.pipelines.workflows import (
    PURPOSE_ADAPTERS,
    compile_for_feature,
    purpose_catalog,
    runtime_support,
    strategy_compatibility,
)


def _manager(tmp_path) -> PipelineManager:
    return PipelineManager(store=PipelineStore(tmp_path / "system.sqlite3"))


def test_purpose_ids_and_consuming_features_are_unique() -> None:
    ids = [spec.purpose_id for spec in PIPELINE_PURPOSES]
    features = [spec.consuming_feature for spec in PIPELINE_PURPOSES]
    assert len(ids) == len(set(ids))
    assert len(features) == len(set(features))
    with pytest.raises(ValueError, match="Duplicate pipeline purpose"):
        PurposeRegistry((PIPELINE_PURPOSES[0], PIPELINE_PURPOSES[0]))


def test_every_purpose_has_an_adapter_and_a_known_category() -> None:
    categories = {term.id for term in WORKFLOW_CATEGORIES}
    assert set(PURPOSE_ADAPTERS) == {spec.purpose_id for spec in PIPELINE_PURPOSES}
    assert {spec.category for spec in PIPELINE_PURPOSES} == categories
    guarantees = {term.id for term in WORKFLOW_GUARANTEES}
    for spec in PIPELINE_PURPOSES:
        assert set(spec.required_guarantees) <= guarantees


def test_every_built_in_pipeline_names_a_registered_purpose_and_runs() -> None:
    for pipeline in BUILT_IN_PIPELINES:
        assert purpose_registry.get(pipeline.purpose) is not None, pipeline.pipeline_id
        enabled = {stage.strategy for stage in pipeline.stages if stage.enabled}
        supported = PURPOSE_ADAPTERS[pipeline.purpose].supported_strategies
        support = runtime_support(pipeline)
        if support["supported"]:
            assert enabled <= supported, pipeline.pipeline_id


def test_built_in_assignments_route_to_the_purpose_that_consumes_them() -> None:
    for assignment in BUILT_IN_ASSIGNMENTS:
        spec = purpose_registry.for_feature(assignment.feature)
        assert spec is not None, assignment.feature
        pipeline = next(
            item
            for item in BUILT_IN_PIPELINES
            if item.pipeline_id == assignment.pipeline_id
            and item.version == assignment.pipeline_version
        )
        assert pipeline.purpose == spec.purpose_id
        assert assignment.override_allowed == spec.override_allowed
        compile_for_feature(assignment.feature, pipeline)
    assert {item.feature for item in BUILT_IN_ASSIGNMENTS} == {
        spec.consuming_feature for spec in PIPELINE_PURPOSES
    }


def test_evidence_purposes_are_distinct_but_share_the_evidence_category() -> None:
    evidence = [spec for spec in PIPELINE_PURPOSES if spec.category == "evidence"]
    assert {"evidence_suggestion", "evidence_recovery"} <= {spec.purpose_id for spec in evidence}
    suggestion = purpose_registry.get("evidence_suggestion")
    assert suggestion is not None
    assert suggestion.consuming_feature == "evidence_suggestion.reviewer"
    assert {"direct_support", "source_provenance"} <= set(suggestion.required_guarantees)
    search = purpose_registry.get("vector_store_search")
    assert search is not None and search.category == "search"


def test_assignment_rejects_a_pipeline_of_another_purpose(tmp_path) -> None:
    manager = _manager(tmp_path)
    research = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "research.current")
    with pytest.raises(ValueError, match="runs evidence_suggestion pipelines"):
        manager.assign(
            PipelineAssignment(
                feature="evidence_suggestion.reviewer",
                pipeline_id=research.pipeline_id,
                pipeline_version=research.version,
            )
        )
    with pytest.raises(ValueError, match="not supported"):
        compile_for_feature("unknown.feature", research)


def test_assignment_resolution_still_prefers_saved_assignments(tmp_path) -> None:
    manager = _manager(tmp_path)
    mmr = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "store_search.mmr")
    manager.assign(
        PipelineAssignment(
            feature="vector_store_search", pipeline_id=mmr.pipeline_id, pipeline_version=mmr.version
        )
    )
    assert manager.resolve("vector_store_search")["pipeline"]["pipeline_id"] == "store_search.mmr"
    assert manager.resolve("research")["assignment"]["source"] == "built_in"


def test_unregistered_purpose_is_a_validation_error() -> None:
    pipeline = BUILT_IN_PIPELINES[0].model_copy(update={"purpose": "made_up"})
    result = PipelineService().validate(pipeline)
    assert result.valid is False
    assert "unknown_purpose" in {issue.code for issue in result.issues}
    assert runtime_support(pipeline)["supported"] is False


def test_every_strategy_declares_a_valid_scholarly_effect() -> None:
    allowed = set(get_args(ScholarlyEffect))
    for spec in strategy_registry.list():
        assert spec.scholarly_effect in allowed
        assert spec.family in FAMILY_PHASES


@pytest.mark.parametrize(
    ("strategy_id", "effect", "note"),
    [
        ("retrieve.chroma_similarity", "advisory", "candidates_not_evidence"),
        ("rerank.cross_encoder", "advisory", "ranking_only"),
        ("select.mmr", "advisory", "diversity_only"),
        ("validate.evidence_support", "eligibility_gate", "eligibility_gate"),
        ("validate.provenance", "provenance_gate", "provenance_gate"),
        ("llm.generate_answer", "generation", "generation"),
        ("llm.grade_rag", "evaluation", "evaluation"),
    ],
)
def test_retrieval_and_ranking_never_claim_support(strategy_id, effect, note) -> None:
    spec = strategy_registry.require(strategy_id)
    assert spec.scholarly_effect == effect
    assert effect_note(spec.family, spec.scholarly_effect) == note


def test_strategy_serialization_carries_effect_phase_and_keys() -> None:
    rows = {row["strategy_id"]: row for row in PipelineService().strategies()}
    chroma = rows["retrieve.chroma_similarity"]
    assert chroma["scholarly_effect"] == "advisory"
    assert chroma["effect_note"] == "candidates_not_evidence"
    assert chroma["phase"] == "find"
    assert chroma["family"] == "candidate_generation"
    json.dumps(rows)


def test_purpose_compatibility_is_deterministic_and_explains_output_contracts() -> None:
    spec = purpose_registry.get("evidence_suggestion")
    assert spec is not None
    first = strategy_compatibility(spec)
    assert first == strategy_compatibility(spec)
    assert set(first) == {item.strategy_id for item in strategy_registry.list()}
    assert first["validate.evidence_support"] == "supported"
    assert first["llm.generate_answer"] == "output_contract"
    assert first["select.mmr"] == "inspect_only"
    for strategy_id in PURPOSE_ADAPTERS["evidence_suggestion"].supported_strategies:
        assert first[strategy_id] == "supported"


def test_catalog_serves_purposes_vocabulary_and_strategies(tmp_path) -> None:
    catalog = _manager(tmp_path).catalog()
    encoded = json.loads(json.dumps(catalog))
    purposes = {row["purpose_id"]: row for row in encoded["purposes"]}
    assert purposes["research"]["category"] == "research"
    assert purposes["research"]["label_key"] == "pipelines.purpose.research.label"
    assert purposes["research"]["authority_key"] == "pipelines.purpose.research.authority"
    assert purposes["evidence_suggestion"]["strategy_fit"]["validate.provenance"] == "supported"
    vocabulary = encoded["vocabulary"]
    assert [term["id"] for term in vocabulary["categories"]] == [
        term.id for term in WORKFLOW_CATEGORIES
    ]
    assert {term["id"] for term in vocabulary["scholarly_effects"]} == set(get_args(ScholarlyEffect))
    for group in vocabulary.values():
        for term in group:
            assert term["label_key"].startswith("pipelines.")
    assert purpose_catalog() == encoded["purposes"]
    assert workflow_vocabulary() == vocabulary


def test_evidence_gates_remain_mandatory_for_active_chains() -> None:
    reviewer = next(
        item
        for item in BUILT_IN_PIPELINES
        if item.pipeline_id == "evidence.conservative"
    )
    ungated = reviewer.model_copy(
        update={
            "status": "active",
            "stages": [
                stage.model_copy(update={"enabled": stage.strategy != "validate.evidence_support"})
                for stage in reviewer.stages
            ],
        }
    )
    codes = {issue.code for issue in PipelineService().validate(ungated).issues}
    assert "evidence_without_support_gate" in codes


def _trace(run_id: str, feature: str) -> PipelineRunTrace:
    now = datetime.now(UTC)
    return PipelineRunTrace(
        run_id=run_id,
        feature=feature,
        pipeline_id="p",
        pipeline_version=1,
        resolved_pipeline={},
        resolved_hash="c" * 64,
        status="completed",
        started_at=now,
        finished_at=now,
    )


def test_execution_history_filters_by_workflow_features(tmp_path) -> None:
    store = PipelineStore(tmp_path / "system.sqlite3")
    store.put_run(_trace("r1", "evidence_suggestion.reviewer"))
    store.put_run(_trace("r2", "evidence_recovery"))
    store.put_run(_trace("r3", "research"))
    evidence = [
        spec.consuming_feature for spec in PIPELINE_PURPOSES if spec.category == "evidence"
    ]
    assert {item.run_id for item in store.list_runs(features=evidence)} == {"r1", "r2"}
    assert store.count_runs(features=evidence) == 2
    assert store.count_runs(features=[]) == 0
    assert store.count_runs() == 3


def test_frontend_catalog_fixture_matches_the_served_contract() -> None:
    """Stories and Vitest read this fixture; it must be what the API serves."""

    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / (
        "web/src/components/pipelines/fixtures/pipelineCatalogContract.json"
    )
    served = json.loads(
        json.dumps(
            {
                "purposes": purpose_catalog(),
                "vocabulary": workflow_vocabulary(),
                "strategies": PipelineService().strategies(),
            }
        )
    )
    assert json.loads(fixture.read_text(encoding="utf-8")) == served
