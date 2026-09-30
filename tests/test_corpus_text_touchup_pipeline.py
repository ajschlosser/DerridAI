# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus Builder text touch-up runs its model call through the corpus_text_touchup pipeline.

Why: which provider proposes a touch-up, how many attempts it gets, and when it escalates to the
review provider used to be hard-coded in ``_chat_json``. The pipeline now owns that choice; the
prompt, sanitizing against the source text and "a touch-up is only a proposal" stay touch-up code.
How: ``chat_complete`` is replaced by a scripted provider, so the tests compare the exact calls the
legacy chain and the pipeline make, and check the trace, the proposal's identity and failure handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.corpus_text_touchup import (
    TEXT_TOUCHUP_FEATURE,
    compile_text_touchup_pipeline,
)
from app.pipelines.defaults import built_in_assignment, built_in_pipeline
from app.pipelines.manager import pipeline_manager
from app.pipelines.service import PipelineService, pipeline_hash

BUILT_IN = ("corpus.text_touchup.current", 1)
REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}
SOURCE = "A stable philosophical para- graph continues its argument."
CLEAN = '{"text": "A stable philosophical paragraph continues its argument.", "changes": ["joined hyphenation"]}'


@pytest.fixture
def traces(monkeypatch):
    saved = []
    monkeypatch.setattr(store_module.pipeline_store, "put_run", lambda trace: saved.append(trace) or trace)
    return saved


@pytest.fixture
def manager(tmp_path: Path):
    return cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)


def _build(manager) -> str:
    build_id = manager.repo.create_build({
        "asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1,
        "source_block_count": 1, "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION,
        "profile_version": 7, "provider": "ollama", "model": "test", "request": {}, "warnings": [],
    })["build_id"]
    manager.repo.save_records(build_id, [{"record_id": "r1", "text": SOURCE, "source_block_ids": ["b1"]}])
    return build_id


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
        "primary answers": {"primary-model": [CLEAN]},
        "review answers after primary retries": {"primary-model": ["no", "still no"], "review-model": [CLEAN]},
        "both fail": {"primary-model": ["no", "no"], "review-model": ["no", "no"]},
        "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [CLEAN]},
    }


def _touchup(manager, build_id, request):
    try:
        return manager.touchup_record_text(build_id, "r1", request), None
    except ValueError as exc:
        return None, str(exc)


@pytest.mark.parametrize("scenario", sorted(_scenarios()))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_touchup_makes_the_legacy_chains_calls(monkeypatch, manager, traces, scenario, request_) -> None:
    replies = _scenarios()[scenario]
    pipeline_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    build_id = _build(manager)
    proposal, error = _touchup(manager, build_id, request_)

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    try:
        manager._chat_json(
            manager._interactive_llm_request(build_id, request_), pipeline_calls[0]["prompt"],
            response_model=cb.TextTouchupResponseModel, max_tokens=pipeline_calls[0]["max_tokens"],
            schema_name="record_text_touchup", attempts=2, build_id=build_id,
        )
        legacy_error = None
    except ValueError as exc:
        legacy_error = str(exc)

    assert pipeline_calls == legacy_calls
    assert pipeline_calls[0]["max_tokens"] == 2048
    assert error == legacy_error
    assert (proposal or {}).get("proposed_text") == (None if legacy_error else SOURCE.replace("para- graph", "paragraph"))
    # Every proposal, answered or failed, is one trace.
    assert [trace.feature for trace in traces] == [TEXT_TOUCHUP_FEATURE]


def test_built_in_compiles_and_is_assigned() -> None:
    pipeline = built_in_pipeline(*BUILT_IN)
    assert PipelineService().validate(pipeline).valid
    plan = compile_text_touchup_pipeline(pipeline)
    assert (plan.entry.id, plan.fallback.id) == ("primary", "review")
    assignment = built_in_assignment(TEXT_TOUCHUP_FEATURE)
    assert (assignment.pipeline_id, assignment.pipeline_version) == BUILT_IN
    assert pipeline_manager.runtime_support(pipeline) == {"supported": True, "adapter": TEXT_TOUCHUP_FEATURE}


def test_saved_proposal_names_its_pipeline_and_trace(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": [CLEAN]})
    build_id = _build(manager)
    proposal = manager.touchup_record_text(build_id, "r1", REQUEST)
    # Validation needs a full source asset; this test is about what the saved proposal carries.
    monkeypatch.setattr(manager, "_rewrite_and_validate", lambda bid, records, **_: manager.repo.save_records(bid, records))
    saved = manager.save_text_touchup_proposal(build_id, "r1", proposal)["text_touchup_proposal"]

    (trace,) = traces
    assert saved["pipeline"]["trace_id"] == trace.run_id
    assert saved["pipeline"]["pipeline_id"] == BUILT_IN[0]
    assert saved["pipeline"]["stages"] == [{"stage_id": "primary", "provider_role": "primary", "status": "completed"}]
    assert SOURCE not in trace.model_dump_json()
    # A proposal never changes the reviewed text.
    assert manager.repo.get_record(build_id, "r1")["text"] == SOURCE


def test_review_provider_can_propose_first(monkeypatch, manager, traces) -> None:
    source = built_in_pipeline(*BUILT_IN)
    pipeline = source.model_copy(update={
        "pipeline_id": "corpus.text_touchup.custom",
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
    calls = _provider(monkeypatch, {"review-model": [CLEAN]})
    proposal = manager.touchup_record_text(_build(manager), "r1", WITH_REVIEW)

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in str(calls[0]["prompt"])
    assert proposal["pipeline"]["pipeline_id"] == "corpus.text_touchup.custom"


def test_unresolvable_pipeline_fails_the_request_without_a_model_call(monkeypatch, manager, traces) -> None:
    def broken(_feature):
        raise KeyError("corpus.text_touchup.missing@9")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", broken)
    calls = _provider(monkeypatch, {"primary-model": [CLEAN]})
    build_id = _build(manager)
    proposal, error = _touchup(manager, build_id, REQUEST)

    assert calls == [] and traces == [] and proposal is None
    assert "text touch-up pipeline is unavailable" in str(error)
    assert "text_touchup_proposal" not in manager.repo.get_record(build_id, "r1")


def test_cancelled_touchup_records_a_cancelled_trace(monkeypatch, manager, traces) -> None:
    _provider(monkeypatch, {"primary-model": ["no", "no"], "review-model": [CLEAN]})
    # Checks: before each primary attempt, then before the review provider's first attempt.
    cancelled = iter([False, False, True])
    monkeypatch.setattr(manager, "_cancelled", lambda _build_id: next(cancelled, True))
    with pytest.raises(InterruptedError):
        manager.touchup_record_text(_build(manager), "r1", WITH_REVIEW)

    assert [trace.status for trace in traces] == ["cancelled"]
