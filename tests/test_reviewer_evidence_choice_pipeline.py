# Copyright 2026 Aaron John Schlosser, PhD.
"""A reviewer's request for model-chosen evidence runs through the corpus_reviewer_evidence_choice pipeline.

Why: which provider answers the closed-choice evidence question, how many attempts it gets, and when
it escalates to the review provider used to be hard-coded in ``_chat_json``. The pipeline now owns
that choice; the closed-choice prompt and the deterministic validation of every returned block ID
stay evidence code, and a suggestion stays advisory until the reviewer binds it.
How: ``chat_complete`` is replaced by a scripted provider, so the tests compare the exact calls the
legacy chain and the pipeline make, and check the trace, the suggestions' identity and failure handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.corpus_models import EvidenceChoiceModel
from app.evidence_suggestions import llm_prompt
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.corpus_reviewer_evidence_choice import (
    REVIEWER_EVIDENCE_CHOICE_FEATURE,
    compile_reviewer_evidence_choice_pipeline,
)
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.manager import pipeline_manager
from app.pipelines.service import PipelineService, pipeline_hash

BUILT_IN = ("corpus.reviewer_evidence_choice.current", 1)
REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}
VALUE = "Jacques Derrida"
BLOCKS = [
    {"block_id": "b1", "text": "Jacques Derrida wrote this preface."},
    {"block_id": "b2", "text": "An unrelated passage about grammar."},
]
CHOICE = '{"block_ids": ["b1", "invented"], "reason": "names the author"}'


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


@pytest.fixture
def manager(tmp_path: Path, monkeypatch):
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)
    monkeypatch.setattr(manager, "_evidence_candidates", lambda *_: (VALUE, [dict(b) for b in BLOCKS]))
    return manager


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


def _scenarios() -> dict[str, dict[str, list[object]]]:
    return {
        "primary answers": {"primary-model": [CHOICE]},
        "review answers after primary retries": {"primary-model": ["no", "still no"], "review-model": [CHOICE]},
        "both fail": {"primary-model": ["no", "no"], "review-model": ["no", "no"]},
        "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [CHOICE]},
    }


def _suggest(manager, request):
    try:
        return manager.suggest_evidence_llm("", "r1", "document_author", request), None
    except ValueError as exc:
        return None, str(exc)


@pytest.mark.parametrize("scenario", sorted(_scenarios()))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_evidence_choice_makes_the_legacy_chains_calls(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = _scenarios()[scenario]
    pipeline_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    items, error = _suggest(manager, request_)

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    try:
        manager._chat_json(
            request_, llm_prompt("document_author", VALUE, BLOCKS), response_model=EvidenceChoiceModel,
            max_tokens=800, schema_name="evidence_choice", attempts=2,
        )
        legacy_error = None
    except ValueError as exc:
        legacy_error = str(exc)

    assert pipeline_calls == legacy_calls
    assert error == legacy_error
    # Only real candidate blocks survive; the invented ID never reaches the reviewer.
    assert [item["block_id"] for item in items or []] == ([] if legacy_error else ["b1"])
    assert [trace.feature for trace in traces] == [REVIEWER_EVIDENCE_CHOICE_FEATURE]


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_reviewer_evidence_choice_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id) == ("primary", "review")
    assignment = built_in_assignment(REVIEWER_EVIDENCE_CHOICE_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN
    assert pipeline_manager.runtime_support(pipeline) == {
        "supported": True, "adapter": REVIEWER_EVIDENCE_CHOICE_FEATURE,
    }


def test_compiler_rejects_the_evidence_graphs_closed_choice_stage() -> None:
    # The reviewer evidence and recovery graphs keep their own closed-choice strategy.
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "stages": [stage.model_copy(update={"strategy": "llm.closed_choice_evidence", "config": {}})
                   for stage in source.stages],
    })
    with pytest.raises(ValueError, match="does not implement"):
        compile_reviewer_evidence_choice_pipeline(pipeline)


def test_each_suggestion_names_its_pipeline_and_trace(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": [CHOICE]})
    items, _ = _suggest(manager, REQUEST)

    (trace,) = traces
    assert [item["pipeline"]["trace_id"] for item in items] == [trace.run_id]
    assert items[0]["pipeline"]["stages"] == [{"stage_id": "primary", "provider_role": "primary", "status": "completed"}]
    assert BLOCKS[0]["text"] not in trace.model_dump_json()


def test_review_provider_can_choose_first(monkeypatch, manager, traces) -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "corpus.reviewer_evidence_choice.custom",
        "built_in": False,
        "stages": [
            source.stages[0].model_copy(update={
                "config": {"provider_role": "review", "attempts": 1}, "on_error": None, "on_timeout": None,
            }),
            source.stages[1].model_copy(update={"enabled": False}),
        ],
    })
    monkeypatch.setattr(
        manager_module.pipeline_manager, "resolve",
        lambda _feature: {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)},
    )
    calls = _provider(monkeypatch, {"review-model": [CHOICE]})
    items, _ = _suggest(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in str(calls[0]["prompt"])
    assert [item["block_id"] for item in items] == ["b1"]


def test_unresolvable_pipeline_fails_the_request_without_a_model_call(monkeypatch, manager, traces) -> None:
    def broken(_feature):
        raise KeyError("corpus.reviewer_evidence_choice.missing@9")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", broken)
    calls = _provider(monkeypatch, {"primary-model": [CHOICE]})
    items, error = _suggest(manager, REQUEST)

    assert calls == [] and traces == [] and items is None
    assert "reviewer evidence choice pipeline is unavailable" in str(error)
