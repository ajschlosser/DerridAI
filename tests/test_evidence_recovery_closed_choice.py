# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Evidence recovery's closed-choice stage decides which provider answers and how many attempts it gets.

Why: during metadata enrichment, the recovery graph's ``llm.closed_choice_evidence`` stage used to
run ``_chat_json``'s hard-coded chain (primary twice, then review twice) whatever the stage said.
The stage's ``provider_role`` and ``attempts`` settings are now authoritative. With neither set
(every built-in), the stage makes exactly the legacy calls; a clone can pick one provider, or
express the escalation as two stages joined by fallback edges.
How: ``chat_complete`` is replaced by a scripted provider, so the tests compare the exact calls of
the legacy chain and the stage, and check the trace, the fallback edges and the settings'
validation. The block-ID validation of the answer stays evidence code and is not re-tested here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.corpus_models import EvidenceChoiceModel
from app.evidence_suggestions import llm_prompt
from app.pipelines import manager as manager_module
from app.pipelines import store as store_module
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.evidence import compile_evidence_pipeline
from app.pipelines.evidence_recovery import (
    RECOVERY_FEATURE,
    compile_recovery_pipeline,
    execute_evidence_recovery,
)
from app.pipelines.service import PipelineService, pipeline_hash

CELF = ("evidence.recovery.celf", 1)
REQUEST = {"provider": "ollama", "model": "primary-model"}
WITH_REVIEW = {**REQUEST, "_review_provider": {"provider": "ollama", "model": "review-model"}}
FIELD = "topic"
VALUE = "welcoming the stranger"
BLOCKS = [{"block_id": "b1", "text": "Hospitality."}, {"block_id": "b2", "text": "Grammar."}]
CHOICE = '{"block_ids": ["b1", "invented"], "reason": "paraphrases the value"}'


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


def _use(monkeypatch, pipeline):
    monkeypatch.setattr(
        manager_module.pipeline_manager,
        "resolve",
        lambda feature: {"pipeline": pipeline.model_dump(mode="json"), "pipeline_hash": pipeline_hash(pipeline)},
    )


def _with_llm_stages(pipeline_id: str, *llm_stages: dict):
    """The cELF built-in with its closed-choice stage replaced by ``llm_stages`` (first one is reached)."""
    source = built_in_pipeline(*CELF)
    first = llm_stages[0]["id"]
    stages = []
    for stage in source.stages:
        if stage.id == "llm_choice":
            stages.extend(
                stage.model_copy(update={"id": spec["id"], "config": spec.get("config", {}), **spec.get("edges", {})})
                for spec in llm_stages
            )
        else:
            stages.append(stage.model_copy(update={"on_empty": first if stage.on_empty == "llm_choice" else stage.on_empty}))
    return source.model_copy(update={"pipeline_id": pipeline_id, "built_in": False, "stages": stages})


def _recover(manager, request):
    return execute_evidence_recovery(
        value=VALUE, blocks=BLOCKS, field=FIELD, field_metadata={"name": FIELD}, source_document_id="doc",
        projection=None,
        llm_choice=lambda prompt, role, attempts, escalated: manager._evidence_closed_choice(
            request, prompt, role, attempts, escalated=escalated,
        ),
    )


def _stages(trace):
    return {stage.stage_id: stage for stage in trace.stages}


def _scenarios() -> dict[str, dict[str, list[object]]]:
    return {
        "primary answers": {"primary-model": [CHOICE]},
        "review answers after primary retries": {"primary-model": ["no", "still no"], "review-model": [CHOICE]},
        "both fail": {"primary-model": ["no", "no"], "review-model": ["no", "no"]},
        "primary times out": {"primary-model": [TimeoutError("read timed out")], "review-model": [CHOICE]},
        "both time out": {"primary-model": [TimeoutError("read timed out")], "review-model": [TimeoutError("read timed out")]},
    }


# --- Built-ins keep the legacy chain -------------------------------------------------------


@pytest.mark.parametrize("scenario", sorted(_scenarios()))
@pytest.mark.parametrize("request_", [REQUEST, WITH_REVIEW], ids=["no-review", "review"])
def test_default_chain_makes_the_legacy_calls(monkeypatch, manager, scenario, request_) -> None:
    replies = _scenarios()[scenario]
    prompt = llm_prompt(FIELD, VALUE, BLOCKS)

    stage_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    try:
        choice = manager._evidence_closed_choice(request_, prompt, "chain", 2)
        stage_answer, stage_error, stage_timed_out = choice.answer, None, False
    except ValueError as exc:
        choice, stage_answer, stage_error, stage_timed_out = None, None, str(exc), exc.timed_out

    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    try:
        legacy_answer = manager._chat_json(
            request_, prompt, response_model=EvidenceChoiceModel, max_tokens=800,
            schema_name="evidence_choice", attempts=2,
        )
        legacy_error, legacy_timed_out = None, False
    except ValueError as exc:
        legacy_answer, legacy_error, legacy_timed_out = None, str(exc), exc.timed_out

    assert stage_calls == legacy_calls
    assert (stage_answer, stage_error, stage_timed_out) == (legacy_answer, legacy_error, legacy_timed_out)
    if choice is not None:
        # The trace names the provider that actually answered, not always the primary.
        assert choice.model == stage_calls[-1]["model"]


def test_built_ins_leave_the_stage_unconfigured_and_stay_celf_compliant() -> None:
    for key in (CELF, ("evidence.recovery.cascade", 1)):
        pipeline = built_in_pipeline(*key)
        assert PipelineService().validate(pipeline).valid
        (stage,) = [stage for stage in pipeline.stages if stage.strategy == "llm.closed_choice_evidence"]
        assert stage.config == {}
    assert compile_recovery_pipeline(built_in_pipeline(*CELF)).celf_compliant


def test_trace_records_the_stage_settings_and_the_answering_model(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, built_in_pipeline(*CELF))
    _provider(monkeypatch, {"primary-model": ["no", "no"], "review-model": [CHOICE]})

    result = _recover(manager, WITH_REVIEW)

    assert result.entry["block_ids"] == ["b1"], "invented IDs never survive validation"
    stage = _stages(traces[-1])["llm_choice"]
    assert stage.parameters == {"provider_role": "chain", "attempts": 2}
    assert (stage.provider, stage.model) == ("ollama", "review-model")


# --- Clones choose the provider and the escalation -----------------------------------------


def test_clone_can_ask_the_review_provider_first(monkeypatch, manager, traces) -> None:
    review_first = _with_llm_stages("evidence.recovery.review-first", {
        "id": "llm_review", "config": {"provider_role": "review", "attempts": 1}, "edges": {"next": ["provenance"]},
    })
    assert PipelineService().validate(review_first).valid
    _use(monkeypatch, review_first)
    calls = _provider(monkeypatch, {"review-model": [CHOICE]})

    result = _recover(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["review-model"]
    assert "ESCALATION REVIEW" not in calls[0]["prompt"], "a first stage is not an escalation"
    assert result.entry["block_ids"] == ["b1"]
    assert _stages(traces[-1])["llm_review"].model == "review-model"


def test_two_stage_escalation_follows_the_fallback_edges(monkeypatch, manager, traces) -> None:
    escalate = {"on_error": "llm_review", "on_timeout": "llm_review", "on_unavailable": "llm_review", "next": ["provenance"]}
    two_stage = _with_llm_stages(
        "evidence.recovery.escalating",
        {"id": "llm_primary", "config": {"provider_role": "primary", "attempts": 1}, "edges": escalate},
        {"id": "llm_review", "config": {"provider_role": "review", "attempts": 1}, "edges": {"next": ["provenance"]}},
    )
    assert PipelineService().validate(two_stage).valid
    assert compile_recovery_pipeline(two_stage).celf_compliant
    _use(monkeypatch, two_stage)

    calls = _provider(monkeypatch, {"primary-model": ["no"], "review-model": [CHOICE]})
    assert _recover(manager, WITH_REVIEW).entry["block_ids"] == ["b1"]
    assert [call["model"] for call in calls] == ["primary-model", "review-model"]
    ran = _stages(traces[-1])
    assert (ran["llm_primary"].status, ran["llm_review"].status) == ("failed", "completed")
    # The review stage is told, as _chat_json's own chain tells it, that a first pass failed.
    assert "ESCALATION REVIEW" not in calls[0]["prompt"]
    assert "ESCALATION REVIEW" in calls[1]["prompt"]
    assert ran["llm_review"].parameters == {"provider_role": "review", "attempts": 1, "escalated": True}

    calls = _provider(monkeypatch, {"primary-model": [TimeoutError("read timed out")], "review-model": [CHOICE]})
    _recover(manager, WITH_REVIEW)
    assert _stages(traces[-1])["llm_primary"].status == "timed_out"
    assert "ESCALATION REVIEW" in calls[1]["prompt"]


def test_escalated_review_stage_makes_the_legacy_chains_review_call(monkeypatch, manager) -> None:
    prompt = llm_prompt(FIELD, VALUE, BLOCKS)
    replies = {"primary-model": ["no", "no"], "review-model": ["no", CHOICE]}
    legacy_calls = _provider(monkeypatch, {model: list(items) for model, items in replies.items()})
    manager._chat_json(
        WITH_REVIEW, prompt, response_model=EvidenceChoiceModel, max_tokens=800,
        schema_name="evidence_choice", attempts=2,
    )

    stage_calls = _provider(monkeypatch, {"review-model": list(replies["review-model"])})
    manager._evidence_closed_choice(WITH_REVIEW, prompt, "review", 2, escalated=True)

    assert stage_calls == legacy_calls[2:]


def test_only_a_failed_model_stage_escalates(monkeypatch, manager, traces) -> None:
    # An unconfigured first provider asked no model, so the next stage is not an escalation.
    escalate = {"on_error": "llm_primary", "on_timeout": "llm_primary", "on_unavailable": "llm_primary", "next": ["provenance"]}
    review_then_primary = _with_llm_stages(
        "evidence.recovery.review-then-primary",
        {"id": "llm_review", "config": {"provider_role": "review"}, "edges": escalate},
        {"id": "llm_primary", "config": {"provider_role": "primary"}, "edges": {"next": ["provenance"]}},
    )
    _use(monkeypatch, review_then_primary)
    calls = _provider(monkeypatch, {"primary-model": [CHOICE]})

    assert _recover(manager, REQUEST).entry["block_ids"] == ["b1"]
    assert [call["model"] for call in calls] == ["primary-model"]
    assert "ESCALATION REVIEW" not in calls[0]["prompt"]
    ran = _stages(traces[-1])
    assert ran["llm_review"].status == "unavailable"
    assert "escalated" not in ran["llm_primary"].parameters


def test_missing_provider_role_is_unavailable_and_asks_no_model(monkeypatch, manager, traces) -> None:
    review_only = _with_llm_stages("evidence.recovery.review-only", {
        "id": "llm_review", "config": {"provider_role": "review"}, "edges": {"next": ["provenance"]},
    })
    _use(monkeypatch, review_only)
    calls = _provider(monkeypatch, {})

    result = _recover(manager, REQUEST)

    assert result.entry is None
    assert calls == []
    stage = _stages(traces[-1])["llm_review"]
    assert stage.status == "unavailable"
    assert "No review provider is configured" in stage.fallback_reason


def test_skipped_stage_still_reports_its_settings(monkeypatch, traces) -> None:
    # evidence_cascade_llm_enabled=false passes no callback: the stage is skipped, no model is asked.
    _use(monkeypatch, built_in_pipeline(*CELF))
    result = execute_evidence_recovery(
        value=VALUE, blocks=BLOCKS, field=FIELD, field_metadata={"name": FIELD}, source_document_id="doc",
        projection=None, llm_choice=None,
    )
    assert result.entry is None
    stage = _stages(traces[-1])["llm_choice"]
    assert (stage.status, stage.parameters) == ("skipped", {"provider_role": "chain", "attempts": 2})


# --- The settings exist only where a model is asked ----------------------------------------


def test_settings_are_validated() -> None:
    bad = _with_llm_stages("evidence.recovery.bad", {
        "id": "llm_choice", "config": {"provider_role": "tertiary", "attempts": 9}, "edges": {"next": ["provenance"]},
    })
    assert not PipelineService().validate(bad).valid


def test_reviewer_suggestion_graph_rejects_the_settings() -> None:
    reviewer = built_in_pipeline("evidence.conservative", 1)
    compile_evidence_pipeline(reviewer)
    configured = reviewer.model_copy(update={"stages": [
        stage.model_copy(
            update={
                "config": {
                    "provider_role": "review",
                    "candidate_scope": "input_or_all",
                    "candidate_limit": 4,
                }
            }
        )
        if stage.strategy == "llm.closed_choice_evidence" else stage
        for stage in reviewer.stages
    ]})
    with pytest.raises(ValueError, match="candidate_limit, candidate_scope, provider_role"):
        compile_evidence_pipeline(configured)


def test_feature_is_evidence_recovery(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, built_in_pipeline(*CELF))
    _provider(monkeypatch, {"primary-model": [CHOICE]})
    _recover(manager, REQUEST)
    assert [trace.feature for trace in traces] == [RECOVERY_FEATURE]
