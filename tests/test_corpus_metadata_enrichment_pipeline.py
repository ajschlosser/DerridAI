# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus Builder metadata enrichment runs its model calls through the corpus_metadata_enrichment pipeline.

Why: which provider answers a metadata group, how many attempts it gets, and when it escalates
to the review provider used to be hard-coded in ``_chat_json``. The pipeline now owns that
choice; the schema still owns the task, and reconciliation still owns authority.
How: ``chat_complete`` is replaced by a scripted provider. Version 1 remains reproducible
with its historical two-plus-two retry budget, while version 2 spends one primary attempt and
escalates only after validation/provider failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.corpus_metadata_enrichment import (
    ENRICHMENT_FEATURE,
    compile_enrichment_pipeline,
)
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.manager import pipeline_manager
from app.pipelines.service import PipelineService, pipeline_hash
from pydantic import BaseModel

LEGACY_BUILT_IN = ("corpus.metadata_enrichment.current", 1)
BUILT_IN = ("corpus.metadata_enrichment.current", 2)
PROMPT = "Classify THIS record."
SCHEMA = "derridai_record_discourse"
VALID = '{"label": "ok"}'


class Answer(BaseModel):
    label: str


REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


@pytest.fixture
def manager(tmp_path: Path):
    return cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)


def _provider(monkeypatch, replies: dict[str, list[object]]):
    """Script each model's replies in order; an Exception instance is raised instead of returned."""
    calls: list[dict[str, object]] = []

    def fake_chat_complete(**kwargs):
        calls.append({"model": kwargs["model"], "prompt": kwargs["prompt"], "max_tokens": kwargs["max_tokens"]})
        reply = replies[kwargs["model"]].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    return calls


def _use(monkeypatch, stages):
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "corpus.metadata_enrichment.custom",
        "built_in": False,
        "stages": [stage.model_copy(update=changes) for stage, changes in zip(source.stages, stages)],
    })
    monkeypatch.setattr(
        manager_module.pipeline_manager,
        "resolve",
        lambda _feature: {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)},
    )
    return pipeline


def _enrich(manager, request):
    record: dict[str, object] = {"record_id": "r1", "text": "Text."}
    results = manager._execute_metadata_tasks(record, request, [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None)
    return record, results[0]


SCENARIOS = {
    "primary answers": {"primary-model": [VALID]},
    "review answers after primary validation failure": {"primary-model": ["no"], "review-model": [VALID]},
    "both fail": {"primary-model": ["no"], "review-model": ["no"]},
    "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [VALID]},
}


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_built_in_pipeline_uses_one_attempt_per_provider(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = SCENARIOS[scenario]
    calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    record, (_family, result, error) = _enrich(manager, request_)

    expected_models = ["primary-model"]
    if request_ is WITH_REVIEW and scenario != "primary answers":
        expected_models.append("review-model")
    assert [call["model"] for call in calls] == expected_models

    succeeds = scenario == "primary answers" or (
        request_ is WITH_REVIEW
        and scenario in {"review answers after primary validation failure", "primary times out"}
    )
    if succeeds:
        assert result == {"label": "ok"} and error is None
    else:
        assert result is None and error is not None

    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["pipeline"]["pipeline_id"] == BUILT_IN[0]
    assert ledger["pipeline"]["pipeline_version"] == 2
    assert ledger["attempts_allowed"] == 1


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert pipeline.status == "active"
    assert PipelineService().validate(pipeline).valid
    plan = compile_enrichment_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id) == ("primary", "review")
    assert plan.entry.config["attempts"] == 1
    assert plan.fallback.config["attempts"] == 1
    assignment = built_in_assignment(ENRICHMENT_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN
    assert pipeline_manager.runtime_support(pipeline) == {"supported": True, "adapter": ENRICHMENT_FEATURE}


def test_legacy_v1_remains_available_for_reproducibility() -> None:
    pipeline = built_in_pipeline(*LEGACY_BUILT_IN)
    assert pipeline.status == "disabled"
    plan = compile_enrichment_pipeline(pipeline)
    assert plan.entry.config["attempts"] == 2
    assert plan.fallback.config["attempts"] == 2


def test_escalation_is_traced_by_code_without_prompt_or_answer_text(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": ["leaked answer text"], "review-model": [VALID]})
    record, (_family, result, _error) = _enrich(manager, WITH_REVIEW)

    assert result == {"label": "ok"}
    identity = record["metadata_execution_ledger"]["discourse"]["pipeline"]
    assert identity["stages"] == [
        {"stage_id": "primary", "provider_role": "primary", "status": "failed"},
        {"stage_id": "review", "provider_role": "review", "status": "completed"},
    ]
    (trace,) = traces
    assert trace.run_id == identity["trace_id"] and trace.feature == ENRICHMENT_FEATURE
    primary, review = trace.stages
    assert (primary.status, primary.fallback_reason, primary.model) == ("failed", "structured_output_failed", "primary-model")
    assert (review.status, review.output_count, review.model) == ("completed", 1, "review-model")
    assert review.parameters == {"provider_role": "review", "attempts": 1, "response_contracts": [SCHEMA]}
    dumped = trace.model_dump_json()
    assert PROMPT not in dumped and "leaked answer text" not in dumped


def test_attempts_setting_can_restore_a_second_primary_attempt(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [{"config": {"provider_role": "primary", "attempts": 2}}, {}])
    calls = _provider(monkeypatch, {
        "primary-model": ["no", "still no"],
        "review-model": [VALID],
    })
    record, (_family, result, _error) = _enrich(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == [
        "primary-model",
        "primary-model",
        "review-model",
    ]
    assert result == {"label": "ok"}
    assert record["metadata_execution_ledger"]["discourse"]["attempts_allowed"] == 2


def test_review_provider_can_answer_first(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [
        {"config": {"provider_role": "review", "attempts": 2}, "on_error": None, "on_timeout": None},
        {"enabled": False},
    ])
    calls = _provider(monkeypatch, {"review-model": [VALID]})
    _record, (_family, result, _error) = _enrich(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in str(calls[0]["prompt"])
    assert result == {"label": "ok"}


def test_timeout_without_a_timeout_edge_does_not_escalate(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [{"on_timeout": None}, {}])
    calls = _provider(monkeypatch, {"primary-model": [TimeoutError("read timed out")], "review-model": [VALID]})
    record, (_family, result, error) = _enrich(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["primary-model"]
    assert result is None and "timed out" in str(error)
    assert record["metadata_stage_status"]["discourse"] == "failed"
    assert traces[0].stages[0].fallback_reason == "provider_timed_out"


def test_unconfigured_review_provider_is_reported_as_unavailable(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": ["no"]})
    record, (_family, _result, error) = _enrich(manager, REQUEST)

    assert str(error).startswith("LLM structured output failed after bounded retry: primary ollama/primary-model")
    assert [step["status"] for step in record["metadata_execution_ledger"]["discourse"]["pipeline"]["stages"]] == [
        "failed", "unavailable",
    ]
    assert traces[0].stages[1].fallback_reason == "provider_role_not_configured"


def test_unresolvable_assignment_fails_the_family_without_a_model_call(monkeypatch, manager, traces) -> None:
    def broken(_feature):
        raise KeyError("corpus.metadata_enrichment.missing@9")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", broken)
    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_family, result, error) = _enrich(manager, REQUEST)

    assert calls == [] and result is None
    assert "metadata enrichment pipeline is unavailable" in str(error)
    assert record["metadata_stage_status"]["discourse"] == "failed"
    assert "pipeline" not in record["metadata_execution_ledger"]["discourse"]
    assert traces == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ([{}, {"config": {"provider_role": "primary", "attempts": 2}}], "other provider role"),
        ([{"next": ["review"], "on_error": None, "on_timeout": None}, {}], "terminal"),
        ([{"on_empty": "review"}, {}], "terminal"),
        ([{"config": {"provider_role": "fallback"}}, {}], "provider_role"),
        ([{"config": {"attempts": 9}}, {}], "attempts"),
        ([{}, {"on_error": "primary"}], "escalation stage must be terminal"),
        ([{}, {"strategy": "select.top_k"}], "does not implement"),
    ],
)
def test_compiler_rejects_graphs_the_runtime_cannot_honour(changes, message) -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "stages": [stage.model_copy(update=update) for stage, update in zip(source.stages, changes)],
    })
    with pytest.raises(ValueError, match=message):
        compile_enrichment_pipeline(pipeline)
