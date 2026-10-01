# Copyright 2026 Aaron John Schlosser, PhD.
"""Automatic evidence recovery runs only as a resolved evidence_recovery cascade."""

from __future__ import annotations

import dataclasses

import pytest
from app import config
from app import cross_encoder as cross_encoder_module
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.evidence import compile_evidence_pipeline
from app.pipelines.evidence_recovery import (
    MISSING_SOURCE_DOCUMENT,
    RECOVERY_FEATURE,
    ClosedChoiceAnswer,
    compile_recovery_pipeline,
    execute_evidence_recovery,
)
from app.pipelines.manager import PipelineManager
from app.pipelines.models import InputBinding
from app.pipelines.service import PipelineService, pipeline_hash
from app.pipelines.store import PipelineStore

CASCADE = ("evidence.recovery.cascade", 1)
CELF = ("evidence.recovery.celf", 1)


class Projection:
    def __init__(self, vectors=None, query_vector=None, error=None):
        self.vectors = vectors or {}
        self.query_vector = query_vector or [1.0, 0.0]
        self.error = error
        self.sync_calls = 0

    def sync(self, *args, **kwargs):
        self.sync_calls += 1
        if self.error:
            raise self.error

    def embeddings_for(self, _document_id, _unit_ids, **_kwargs):
        return self.vectors

    def embed_query(self, _query, **_kwargs):
        return self.query_vector


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


@pytest.fixture(autouse=True)
def cross_encoder_enabled(monkeypatch):
    monkeypatch.setattr(
        config, "settings", dataclasses.replace(config.settings, metadata_cross_encoder_enabled=True)
    )


def _use(monkeypatch, pipeline):
    def resolve(feature):
        assert feature == RECOVERY_FEATURE
        return {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)}

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", resolve)


def _built_in(monkeypatch, key):
    pipeline = built_in_pipeline(*key)
    assert pipeline is not None
    _use(monkeypatch, pipeline)
    return pipeline


def _variant(key, pipeline_id, stages):
    source = built_in_pipeline(*key)
    return source.model_copy(update={"pipeline_id": pipeline_id, "built_in": False, "stages": stages(source)})


def _recover(value, blocks, *, field="topic", projection=None, llm_choice=None, source_document_id="doc"):
    return execute_evidence_recovery(
        value=value, blocks=blocks, field=field, field_metadata={"name": field, "label": field.title()},
        source_document_id=source_document_id, projection=projection or Projection(), llm_choice=llm_choice,
    )


def _ran(traces):
    return {stage.stage_id: stage.status for stage in traces[-1].stages}


# --- Built-in definitions ---------------------------------------------------------------


def test_both_built_ins_execute_and_report_their_compliance() -> None:
    service = PipelineService()
    celf = compile_recovery_pipeline(built_in_pipeline(*CELF))
    cascade = compile_recovery_pipeline(built_in_pipeline(*CASCADE))

    assert celf.celf_compliant is True
    assert cascade.celf_compliant is False and "'mmr'" in cascade.compliance_reason
    celf_validation = service.validate(built_in_pipeline(*CELF))
    cascade_validation = service.validate(built_in_pipeline(*CASCADE))
    assert celf_validation.valid and not celf_validation.issues
    assert cascade_validation.valid
    assert [issue.code for issue in cascade_validation.issues] == ["evidence_recovery_not_celf_compliant"]
    assignment = built_in_assignment(RECOVERY_FEATURE)
    assert assignment is not None
    assert (assignment.pipeline_id, assignment.pipeline_version) == CELF


def test_existing_built_ins_still_validate_under_fallback_type_rule() -> None:
    service = PipelineService()
    for key in (("research.current", 1), ("evidence.reviewer.current", 2), ("metadata.precedents.current", 1)):
        assert service.validate(built_in_pipeline(*key)).valid, key


# --- Parity with the legacy first-hit cascade ------------------------------------------


def test_cascade_stops_at_strong_lexical_match_without_touching_embeddings(monkeypatch, traces):
    _built_in(monkeypatch, CASCADE)
    projection = Projection()
    result = _recover("calm", [{"block_id": "b1", "text": "calm calm calm"}], field="mood", projection=projection)

    assert result.entry["block_ids"] == ["b1"]
    assert result.entry["method"] == "deterministic-lexical-v1"
    assert result.entry["confidence"] is None and result.entry["backfilled"] is True
    assert projection.sync_calls == 0
    assert [stage.stage_id for stage in traces[-1].stages] == ["query", "lexical", "provenance", "select"]


def test_cascade_falls_to_cross_encoder_rerank_when_lexical_is_weak(monkeypatch, traces):
    _built_in(monkeypatch, CASCADE)
    blocks = [
        {"block_id": "b1", "text": "A passage about something else entirely."},
        {"block_id": "b2", "text": "A passage about hospitality and the stranger."},
    ]

    def fake_predict_scores(pairs, *, model_name, timeout_seconds):
        return [0.8 if "hospitality" in text else -0.5 for _query, text in pairs], {}

    monkeypatch.setattr(cross_encoder_module, "predict_scores", fake_predict_scores)
    result = _recover(
        "welcoming the stranger", blocks,
        projection=Projection({"b1": [1.0, 0.0], "b2": [0.9, 0.1]}, query_vector=[1.0, 0.0]),
    )

    assert result.entry["method"] == "cross-encoder-rerank-v1"
    assert result.entry["block_ids"] == ["b2"]
    assert result.entry["pipeline"]["celf_compliant"] is False
    ran = _ran(traces)
    assert "mmr" not in ran and "llm_choice" not in ran
    stages = {stage.stage_id: stage for stage in traces[-1].stages}
    assert stages["lexical"].fallback_reason and stages["rerank"].fallback_reason is None


def test_cascade_falls_to_mmr_similarity_when_cross_encoder_is_unavailable(monkeypatch, traces):
    _built_in(monkeypatch, CASCADE)
    blocks = [
        {"block_id": "b1", "text": "A passage about hospitality and the stranger."},
        {"block_id": "b2", "text": "A passage about something else entirely."},
    ]
    monkeypatch.setattr(
        cross_encoder_module, "predict_scores", lambda *a, **k: (None, {"fallback_reason": "missing_dependency"})
    )
    result = _recover(
        "welcoming the stranger", blocks,
        projection=Projection({"b1": [1.0, 0.0], "b2": [0.0, 1.0]}, query_vector=[1.0, 0.0]),
    )

    assert result.entry["method"] == "mmr-similarity-v1"
    assert result.entry["block_ids"][0] == "b1" and len(result.entry["block_ids"]) <= 2
    assert _ran(traces)["rerank"] == "unavailable"


def test_cascade_falls_to_llm_as_last_resort_and_accepts_unsupported_choice(monkeypatch, traces):
    _built_in(monkeypatch, CASCADE)

    def llm_choice(prompt: str, role: str, attempts: int, escalated: bool):
        assert "topic" in prompt
        assert (role, attempts, escalated) == ("chain", 2, False), "built-ins keep the primary-then-review chain"
        return ClosedChoiceAnswer({"block_ids": ["b1", "invented"], "reason": "The model's own judgment."})

    result = _recover(
        "an unrelated value", [{"block_id": "b1", "text": "Nothing relevant here."}],
        projection=Projection(error=RuntimeError("no embedding backend")), llm_choice=llm_choice,
    )

    assert result.entry["method"] == "llm-evidence-choice-v1"
    assert result.entry["block_ids"] == ["b1"], "invented IDs never survive validation"
    assert result.entry["score_details"][0]["lexical_support"] is False
    assert _ran(traces)["semantic"] == "failed"


def test_cascade_returns_none_when_the_llm_stage_raises(monkeypatch, traces):
    _built_in(monkeypatch, CASCADE)

    def failing(_prompt: str, _role: str, _attempts: int, _escalated: bool):
        raise RuntimeError("provider unreachable")

    result = _recover(
        "an unrelated value", [{"block_id": "b1", "text": "Nothing relevant here."}],
        projection=Projection(error=RuntimeError("no embedding backend")), llm_choice=failing,
    )

    assert result.entry is None
    assert _ran(traces)["llm_choice"] == "failed"


def test_empty_value_or_blocks_do_not_resolve_or_embed(monkeypatch):
    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", lambda _f: pytest.fail("nothing to recover"))
    projection = Projection()
    assert _recover("x", [], projection=projection).entry is None
    assert _recover(None, [{"block_id": "b1", "text": "anything"}], projection=projection).entry is None
    assert projection.sync_calls == 0


# --- cELF-compliant chain ------------------------------------------------------------------


def test_celf_chain_never_embeds_or_reranks(monkeypatch, traces):
    _built_in(monkeypatch, CELF)
    monkeypatch.setattr(cross_encoder_module, "predict_scores", lambda *a, **k: pytest.fail("no rerank"))
    projection = Projection({"b1": [1.0, 0.0]})
    prompts = []

    def llm_choice(prompt, _role, _attempts, _escalated):
        prompts.append(prompt)
        return ClosedChoiceAnswer({"block_ids": ["b1"], "reason": "Paraphrases the value."})

    supported = _recover("hospitality", [{"block_id": "b1", "text": "Hospitality."}],
                         projection=projection, llm_choice=llm_choice)
    assert supported.entry["method"] == "deterministic-lexical-v1"
    assert supported.entry["score_details"][0]["support_score"] == 1.0
    assert prompts == [], "the model runs only when nothing is directly supported"

    paraphrase = _recover("welcoming the stranger", [{"block_id": "b1", "text": "Hospitality."}],
                          projection=projection, llm_choice=llm_choice)
    assert paraphrase.entry["method"] == "llm-evidence-choice-v1"
    assert paraphrase.entry["pipeline"]["celf_compliant"] is True
    assert projection.sync_calls == 0


def test_celf_chain_without_model_callback_suggests_nothing_for_unsupported_values(monkeypatch, traces):
    _built_in(monkeypatch, CELF)
    result = _recover("welcoming the stranger", [{"block_id": "b1", "text": "Hospitality."}])
    assert result.entry is None
    assert _ran(traces)["llm_choice"] == "skipped"


# --- The resolved graph is authoritative --------------------------------------------------


def test_stage_config_changes_runtime_behavior(monkeypatch, traces):
    blocks = [{"block_id": "b1", "text": "The calm, quiet tone."}]
    _built_in(monkeypatch, CELF)
    assert _recover("calm tone", blocks).entry is not None  # all terms, not verbatim: 0.85

    strict = _variant(CELF, "evidence.recovery.strict", lambda source: [
        stage.model_copy(update={"config": {"min_score": 1.0}}) if stage.id in {"lexical", "support"} else stage
        for stage in source.stages
    ])
    _use(monkeypatch, strict)
    assert _recover("calm tone", blocks).entry is None
    assert traces[-1].pipeline_id == "evidence.recovery.strict"


def test_removed_stages_never_run(monkeypatch, traces):
    no_rerank = _variant(CASCADE, "evidence.recovery.no-rerank", lambda source: [
        stage.model_copy(update={"next": ["mmr"]}) if stage.id == "semantic" else stage
        for stage in source.stages if stage.id != "rerank"
    ])
    _use(monkeypatch, no_rerank)
    monkeypatch.setattr(cross_encoder_module, "predict_scores", lambda *a, **k: pytest.fail("no rerank stage"))
    result = _recover(
        "welcoming the stranger", [{"block_id": "b1", "text": "Hospitality and the stranger."}],
        projection=Projection({"b1": [1.0, 0.0]}),
    )
    assert result.entry["method"] == "mmr-similarity-v1"

    no_model = _variant(CASCADE, "evidence.recovery.no-model", lambda source: [
        stage.model_copy(update={
            "on_empty": None if stage.on_empty == "llm_choice" else stage.on_empty,
            "on_unavailable": None if stage.on_unavailable == "llm_choice" else stage.on_unavailable,
            "on_error": None if stage.on_error == "llm_choice" else stage.on_error,
        })
        for stage in source.stages if stage.id != "llm_choice"
    ])
    _use(monkeypatch, no_model)
    result = _recover(
        "an unrelated value", [{"block_id": "b1", "text": "Nothing lexical here."}],
        projection=Projection(error=RuntimeError("offline")),
        llm_choice=lambda *_args: pytest.fail("no model call outside the resolved graph"),
    )
    assert result.entry is None


# --- Mandatory gates and runtime contract ----------------------------------------------


def test_graphs_cannot_bypass_provenance_or_branch() -> None:
    def rejects(match, stages):
        with pytest.raises(ValueError, match=match):
            compile_recovery_pipeline(_variant(CELF, "evidence.recovery.bad", stages))

    rejects("Only the provenance gate", lambda source: [
        stage.model_copy(update={"next": ["select"]}) if stage.id == "support" else stage
        for stage in source.stages
    ])
    rejects("one next stage", lambda source: [
        stage.model_copy(update={"next": ["support", "llm_choice"], "on_empty": None})
        if stage.id == "lexical" else stage
        for stage in source.stages
    ])
    rejects("disabled stage", lambda source: [
        stage.model_copy(update={"enabled": False}) if stage.id == "provenance" else stage
        for stage in source.stages
    ])


def test_loosened_support_gate_is_reported_not_forbidden() -> None:
    weak = _variant(CELF, "evidence.recovery.weak", lambda source: [
        stage.model_copy(update={"config": {"min_score": 0.2}}) if stage.id == "support" else stage
        for stage in source.stages
    ])
    plan = compile_recovery_pipeline(weak)
    assert plan.celf_compliant is False and "below 0.50" in plan.compliance_reason


def test_active_recovery_graph_cannot_omit_provenance(tmp_path) -> None:
    manager = PipelineManager(service=PipelineService(), store=PipelineStore(tmp_path / "system.sqlite3"))
    no_provenance = _variant(CELF, "evidence.recovery.no-provenance", lambda source: [
        stage.model_copy(update={"enabled": False}) if stage.id == "provenance" else stage
        for stage in source.stages
    ])
    with pytest.raises(ValueError, match="real source unit"):
        manager.save_definition(no_provenance, actor="admin")


def test_other_adapters_reject_recovery_only_settings() -> None:
    reviewer = built_in_pipeline("evidence.reviewer.current", 2)
    with_min = reviewer.model_copy(update={"stages": [
        stage.model_copy(update={"config": {"min_score": 0.5}}) if stage.id == "lexical" else stage
        for stage in reviewer.stages
    ]})
    with pytest.raises(ValueError, match="does not apply min_score"):
        compile_evidence_pipeline(with_min)


def test_missing_source_document_identity_is_reported_before_any_work(monkeypatch):
    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", lambda _f: pytest.fail("guarded"))
    projection = Projection()
    result = _recover("calm", [{"block_id": "b1", "text": "calm"}], field="mood",
                      projection=projection, source_document_id="  ")
    assert result.entry is None
    assert result.status["skipped"] == MISSING_SOURCE_DOCUMENT
    assert "mood" in result.status["reason"]
    assert projection.sync_calls == 0


def test_trace_lists_only_stages_that_ran_and_binds_the_exact_pipeline(monkeypatch, traces):
    pipeline = _built_in(monkeypatch, CASCADE)
    result = _recover("calm", [{"block_id": "b1", "text": "calm calm calm"}], field="mood")
    trace = traces[-1]
    assert trace.feature == RECOVERY_FEATURE
    assert trace.resolved_hash == pipeline_hash(pipeline) == result.entry["pipeline"]["pipeline_hash"]
    assert result.entry["pipeline"]["trace_id"] == trace.run_id
    assert {stage.stage_id for stage in trace.stages}.isdisjoint({"semantic", "rerank", "mmr", "llm_choice"})


# --- Explicit input bindings -------------------------------------------------------------


def _bound(stage_id, producer, key=CELF):
    binding = InputBinding(source="stage", stage=producer, output="candidates")
    return _variant(key, "evidence.recovery.bound", lambda source: [
        stage.model_copy(update={"inputs": {"candidates": [binding]}}) if stage.id == stage_id else stage
        for stage in source.stages
    ])


def test_binding_the_provenance_gate_past_support_is_reported_non_celf() -> None:
    plan = compile_recovery_pipeline(_bound("provenance", "lexical"))
    assert plan.bound_sources == {"provenance": ["lexical"]}
    assert plan.celf_compliant is False and "'lexical'" in plan.compliance_reason
    # Restating the support gate keeps the guarantee.
    assert compile_recovery_pipeline(_bound("provenance", "support")).celf_compliant is True


def test_selection_cannot_be_bound_around_the_provenance_gate() -> None:
    with pytest.raises(ValueError, match="Only the provenance gate may feed"):
        compile_recovery_pipeline(_bound("select", "support"))


def test_bound_recovery_pipeline_runs_and_is_supported(monkeypatch, traces) -> None:
    from app.pipelines.workflows import runtime_support

    pipeline = _bound("provenance", "lexical")
    assert runtime_support(pipeline)["supported"] is True
    _use(monkeypatch, pipeline)
    result = _recover("calm", [{"block_id": "b1", "text": "calm calm calm"}], field="mood")
    assert result.entry["block_ids"] == ["b1"]
    assert result.status["celf_compliant"] is False
    assert _ran(traces)["provenance"] == "completed"


def test_rewired_recovery_run_is_flagged_in_its_trace(monkeypatch, traces) -> None:
    _use(monkeypatch, _bound("provenance", "lexical"))
    _recover("calm", [{"block_id": "b1", "text": "calm calm calm"}], field="mood")
    assert traces[-1].warnings == ["rewired_inputs: provenance.candidates"]


def test_unbound_recovery_run_carries_no_rewired_warning(monkeypatch, traces) -> None:
    _use(monkeypatch, built_in_pipeline(*CELF))
    _recover("calm", [{"block_id": "b1", "text": "calm calm calm"}], field="mood")
    assert traces[-1].warnings == []
