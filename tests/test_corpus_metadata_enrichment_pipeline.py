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

"""Corpus Builder metadata enrichment runs its model calls through the corpus_metadata_enrichment pipeline.

Why: which provider answers a metadata group, how many attempts it gets, and when it escalates
to the review provider used to be hard-coded in ``_chat_json``. The pipeline now owns that
choice; the schema still owns the task, and reconciliation still owns authority.
How: ``chat_complete`` is replaced by a scripted provider. Version 1 remains reproducible
with its historical two-plus-two retry budget, while version 2 spends one primary attempt and
escalates only after validation/provider failure.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app import corpus_builder as cb
from app.corpus_metadata_enrichment_execution import _materialized_family_fingerprint
from app.llm_failures import ProviderRequestError
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


class RepairAssessment(BaseModel):
    reason: str


class RepairAnswer(BaseModel):
    label: str
    field_assessments: dict[str, RepairAssessment]


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


def test_exact_family_checkpoint_reuses_validated_result(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_, first, error) = _enrich(manager, REQUEST)
    assert error is None
    result = manager._execute_metadata_tasks(
        record, {**REQUEST, "run_id": "another-run", "max_concurrent_requests": 4},
        [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None,
    )
    assert result == [("discourse", first, None)]
    assert len(calls) == 1
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["reuse_count"] == 1
    assert ledger["dependency_fingerprint"]
    assert ledger["reused_at"]
    assert ledger["model_invocations"] == 1


def _materialize_answer(record):
    record["label"] = record["metadata_stage_results"]["discourse"]["label"]
    record.pop("metadata_stage_results")
    ledger = record["metadata_execution_ledger"]["discourse"]
    ledger["requested_fields"] = ["label"]
    ledger["materialized_fingerprint"] = _materialized_family_fingerprint(record, ["label"])


def test_materialized_family_reuses_exact_dependencies_without_raw_response(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_, _, error) = _enrich(manager, REQUEST)
    assert error is None
    _materialize_answer(record)
    restored = json.loads(json.dumps(record))
    callbacks = []
    result = manager._execute_metadata_tasks(
        restored, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "",
        lambda snapshot, family, state, error: callbacks.append((family, state)),
    )
    assert result == [("discourse", {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None)]
    assert len(calls) == 1
    assert restored["label"] == "ok"
    assert restored["metadata_execution_ledger"]["discourse"]["materialized_reuse_count"] == 1
    assert callbacks == [("discourse", "complete")]
    assert not restored["metadata_stage_results"]


@pytest.mark.parametrize("change", [
    "prompt", "text", "revision", "spans", "model", "pipeline", "output",
    "evidence", "status", "unknown_output", "explicit_retry",
])
def test_materialized_family_invalidates_changed_inputs_or_outputs(
    monkeypatch, manager, traces, change,
):
    calls = _provider(monkeypatch, {"primary-model": [VALID, VALID], "changed-model": [VALID]})
    record, (_, _, error) = _enrich(manager, REQUEST)
    assert error is None
    _materialize_answer(record)
    request, prompt = dict(REQUEST), PROMPT
    if change == "prompt":
        prompt += " New guidance."
    elif change == "text":
        record["text"] = "Changed text."
    elif change == "revision":
        record["record_revision"] = 2
    elif change == "spans":
        record["source_spans"] = [{"block_id": "changed"}]
    elif change == "model":
        request["model"] = "changed-model"
    elif change == "pipeline":
        _use(monkeypatch, [{"settings": {"provider_role": "primary", "attempts": 2}}, {}])
    elif change == "output":
        record["label"] = "changed materialization"
    elif change == "evidence":
        record["metadata_evidence"] = {"label": {"block_ids": ["different"]}}
    elif change == "status":
        record["metadata_field_status"] = {"label": {"status": "unresolved"}}
    elif change == "unknown_output":
        record["metadata_execution_ledger"]["discourse"].pop("materialized_fingerprint")
    elif change == "explicit_retry":
        record["metadata_stage_status"]["discourse"] = "queued"
    results = manager._execute_metadata_tasks(
        record, request, [("discourse", prompt, Answer, 512, SCHEMA)], "", None,
    )
    assert len(calls) == 2
    assert results == [("discourse", {"label": "ok"}, None)]
    if change != "explicit_retry":
        assert record["metadata_execution_ledger"]["discourse"]["checkpoint_invalidation_reason"].startswith("materialized_")


def test_legacy_materialized_resume_is_not_reported_as_exact_reuse(monkeypatch, manager, traces):
    monkeypatch.setattr(manager, "_chat_json", lambda *args, **kwargs: pytest.fail("legacy resume called provider"))
    record = {"record_id": "r1", "text": "Text.", "label": "historical", "metadata_stage_status": {"discourse": "complete"}}
    results = manager._execute_metadata_tasks(
        record, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None,
    )
    assert results[0][2] is None
    assert record["label"] == "historical"
    assert not record["metadata_execution_ledger"].get("discourse")


def test_materialized_invalidation_is_family_local_and_citation_independent(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID, VALID, VALID]})
    record = {"record_id": "r1", "text": "Text."}
    tasks = [
        ("discourse", PROMPT, Answer, 512, SCHEMA),
        ("quotation", "Quote classification.", Answer, 512, "derridai_record_quotation"),
    ]
    manager._execute_metadata_tasks(record, REQUEST, tasks, "", None)
    record.pop("metadata_stage_results")
    for entry in record["metadata_execution_ledger"].values():
        entry["materialized_fingerprint"] = _materialized_family_fingerprint(record, entry["requested_fields"])
    record["inline_citation"] = "Different citation style"
    record["full_citation"] = "Different formatting of the same source facts"
    tasks[1] = ("quotation", "Updated quotation instructions.", Answer, 512, "derridai_record_quotation")
    results = manager._execute_metadata_tasks(record, REQUEST, tasks, "", None)
    assert len(calls) == 3
    assert all(error is None for _, _, error in results)
    assert record["metadata_execution_ledger"]["discourse"]["materialized_reuse_count"] == 1
    assert record["metadata_execution_ledger"]["quotation"]["checkpoint_invalidation_reason"] == "materialized_dependencies_changed"


def test_unavailable_pipeline_does_not_certify_materialized_reuse(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_, _, error) = _enrich(manager, REQUEST)
    assert error is None
    _materialize_answer(record)

    def unavailable(_feature):
        raise RuntimeError("Assignment unavailable.")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", unavailable)
    result = manager._execute_metadata_tasks(
        record, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None,
    )
    assert result[0][1] is None and "Assignment unavailable" in str(result[0][2])
    assert record["label"] == "ok"
    assert not record["metadata_execution_ledger"]["discourse"].get("materialized_reuse_count")
    assert len(calls) == 1


def test_materialized_fingerprint_binds_repeatable_member_assertions():
    from app.field_assertions import create_model_assertion, store_assertion

    record = {"record_id": "r1", "label": [{"name": "same value"}]}
    container = create_model_assertion(record, "label", record["label"], method="test")
    member = container.model_copy(update={
        "assertion_id": "member-one", "field_id": "label.instance.name",
        "container_field_id": container.field_id, "member_field_id": "name",
        "instance_id": "instance", "member_name": "name", "value": "same value",
    })
    store_assertion(record, member)
    before = _materialized_family_fingerprint(record, ["label"])
    revised = member.model_copy(update={
        "assertion_id": "member-two", "evidence": [{"block_ids": ["changed-source"]}],
    })
    store_assertion(record, revised)
    assert record["label"] == [{"name": "same value"}]
    assert _materialized_family_fingerprint(record, ["label"]) != before


@pytest.mark.parametrize("change", [
    "prompt", "text", "spans", "revision", "model", "generation",
    "model_version", "pipeline", "response_schema", "tokens", "legacy", "invalid",
    "endpoint", "review_provider", "schema_name", "explicit_retry", "malformed",
])
def test_family_checkpoint_invalidates_changed_dependencies(
    monkeypatch, manager, traces, change,
):
    calls = _provider(monkeypatch, {"primary-model": [VALID, VALID], "changed-model": [VALID]})
    record, (_, _, error) = _enrich(manager, REQUEST)
    assert error is None
    request = dict(REQUEST)
    prompt, model, tokens, schema_name = PROMPT, Answer, 512, SCHEMA
    if change == "prompt":
        prompt += " Revised attribution guidance."
    elif change == "text":
        record["text"] = "Changed source text."
    elif change == "spans":
        record["source_spans"] = [{"block_id": "new-block"}]
    elif change == "revision":
        record["record_revision"] = 2
    elif change == "model":
        request["model"] = "changed-model"
    elif change == "generation":
        request["generation"] = {"temperature": 0.2}
    elif change == "model_version":
        request["model_version"] = "new-digest"
    elif change == "pipeline":
        _use(monkeypatch, [{"settings": {"provider_role": "primary", "attempts": 2}}, {}])
    elif change == "response_schema":
        class RevisedAnswer(BaseModel):
            label: str
            qualifier: str = "unknown"
        model = RevisedAnswer
    elif change == "tokens":
        tokens = 1024
    elif change == "legacy":
        record["metadata_execution_ledger"]["discourse"].pop("dependency_fingerprint", None)
    elif change == "invalid":
        record["metadata_stage_results"]["discourse"] = {"unrecognised": "value"}
    elif change == "endpoint":
        request["base_url"] = "http://different-local-provider:11434"
    elif change == "review_provider":
        request["_review_provider"] = {"provider": "ollama", "model": "review-model"}
    elif change == "schema_name":
        schema_name += "_v2"
    elif change == "explicit_retry":
        record["metadata_stage_status"]["discourse"] = "queued"
    elif change == "malformed":
        record["metadata_stage_results"]["discourse"] = []
    result = manager._execute_metadata_tasks(
        record, request, [("discourse", prompt, model, tokens, schema_name)], "", None,
    )
    assert len(calls) == 2
    assert result[0][2] is None
    assert result[0][1]["label"] == "ok"


def test_failed_family_is_not_reused_as_success(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": ["invalid JSON"]})
    record, (_, first, error) = _enrich(manager, REQUEST)
    assert first is None and error is not None
    result = manager._execute_metadata_tasks(
        record, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None,
    )
    assert result[0][1] is None and result[0][2] is not None
    assert len(calls) == 1
    assert not record["metadata_execution_ledger"]["discourse"].get("dependency_fingerprint")


def test_checkpoint_reuse_survives_serialization_and_excludes_secrets(
    monkeypatch, manager, traces,
):
    import json

    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_, _, error) = _enrich(manager, {**REQUEST, "api_key": "never-retain-this-key"})
    assert error is None
    restored = json.loads(json.dumps(record))
    assert "never-retain-this-key" not in json.dumps(restored)
    callbacks = []
    result = manager._execute_metadata_tasks(
        restored, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "",
        lambda snapshot, task, state, error: callbacks.append((task, state, error)),
    )
    assert result == [("discourse", {"label": "ok"}, None)]
    assert len(calls) == 1
    assert callbacks == [("discourse", "complete", None)]


def test_checkpoint_invalidation_is_family_local(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID, VALID, VALID]})
    record = {"record_id": "r1", "text": "Text."}
    tasks = [
        ("discourse", PROMPT, Answer, 512, SCHEMA),
        ("quotation", "Identify quotations.", Answer, 512, "derridai_record_quotation"),
    ]
    manager._execute_metadata_tasks(record, REQUEST, tasks, "", None)
    tasks[1] = ("quotation", "Identify quotations with new guidance.", Answer, 512, "derridai_record_quotation")
    result = manager._execute_metadata_tasks(record, REQUEST, tasks, "", None)
    assert len(calls) == 3
    assert all(row[2] is None for row in result)
    assert record["metadata_execution_ledger"]["discourse"]["reuse_count"] == 1
    assert record["metadata_execution_ledger"]["quotation"]["checkpoint_invalidation_reason"]


def test_unavailable_pipeline_cannot_reuse_a_raw_checkpoint(monkeypatch, manager, traces):
    calls = _provider(monkeypatch, {"primary-model": [VALID]})
    record, (_, _, error) = _enrich(manager, REQUEST)
    assert error is None

    def unavailable(_feature):
        raise RuntimeError("Assignment unavailable.")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", unavailable)
    result = manager._execute_metadata_tasks(
        record, REQUEST, [("discourse", PROMPT, Answer, 512, SCHEMA)], "", None,
    )
    assert len(calls) == 1
    assert result[0][1] is None
    assert "Assignment unavailable" in str(result[0][2])
    assert "discourse" not in record["metadata_stage_results"]
    assert record["metadata_execution_ledger"]["discourse"]["state"] != "complete"


def test_concurrent_family_calls_share_provider_and_keep_separate_run_ledgers(
    monkeypatch, manager, traces,
):
    from test_metadata_stage_checkpoints import _install_minimal_build

    build = _install_minimal_build(manager.repo)
    bid = build["build_id"]
    record = {"record_id": "r1", "record_revision": 1, "text": "Text."}
    manager.repo.save_records(bid, [record])
    started, release, joined = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def provider(**kwargs):
        calls.append(kwargs["model"])
        started.set()
        assert release.wait(5)
        return VALID

    monkeypatch.setattr(cb, "chat_complete", provider)
    tasks = [("discourse", PROMPT, Answer, 512, SCHEMA)]

    def execute():
        snapshot = dict(record)
        result = manager._execute_metadata_tasks(snapshot, REQUEST, tasks, bid, None)
        return snapshot, result

    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(execute)
        assert started.wait(5)
        pending = next(iter(manager._metadata_request_coalescer._pending.values()))
        original = pending.result

        def waiting(*args, **kwargs):
            joined.set()
            return original(*args, **kwargs)

        monkeypatch.setattr(pending, "result", waiting)
        follower = pool.submit(execute)
        try:
            assert joined.wait(5)
        finally:
            release.set()
        first, first_results = leader.result()
        second, second_results = follower.result()
    assert first_results == second_results == [("discourse", {"label": "ok"}, None)]
    assert len(calls) == 1
    assert len(traces) == 2
    ledgers = [row["metadata_execution_ledger"]["discourse"] for row in (first, second)]
    assert sorted(row["model_invocations"] for row in ledgers) == [0, 1]
    assert sorted(row["inflight_coalesced_calls"] for row in ledgers) == [0, 1]
    assert not manager._metadata_request_coalescer._pending


@pytest.mark.parametrize("change", ["build", "fingerprint", "credential", "role", "prompt", "tokens", "run"])
def test_inflight_sharing_is_exact_and_scope_bound(monkeypatch, manager, change):
    request = {**WITH_REVIEW, "_metadata_dependency_fingerprint": "exact-snapshot"}
    started, release = threading.Event(), threading.Event()
    calls = []

    def generate(*args, **kwargs):
        calls.append(kwargs["build_id"])
        if len(calls) == 1:
            started.set()
            assert release.wait(5)
        return {"label": "ok"}

    monkeypatch.setattr(manager, "_chat_json", generate)
    leader = manager._structured_metadata_invoker(request, PROMPT, Answer, 512, SCHEMA, "one")
    revised = dict(request)
    bid, prompt, tokens, role = "one", PROMPT, 512, "primary"
    if change == "build":
        bid = "two"
    elif change == "fingerprint":
        revised["_metadata_dependency_fingerprint"] = "different-record-or-revision"
    elif change == "credential":
        revised["api_key"] = "separate-authorized-provider-account"
    elif change == "role":
        role = "review"
    elif change == "prompt":
        prompt += " Repair."
    elif change == "tokens":
        tokens = 1024
    elif change == "run":
        revised["run_id"] = "explicit-new-recomputation"
    different = manager._structured_metadata_invoker(revised, prompt, Answer, tokens, SCHEMA, bid)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(leader, "primary", 1, False)
        assert started.wait(5)
        try:
            assert different(role, 1, False) == {"label": "ok"}
            assert len(calls) == 2
        finally:
            release.set()
        assert first.result() == {"label": "ok"}
    assert not manager._metadata_request_coalescer._pending


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


def test_truncated_primary_output_gets_one_bounded_recovery_call(
    monkeypatch,
    manager,
    traces,
) -> None:
    calls = _provider(
        monkeypatch,
        {"primary-model": ['{"label":"unfinished', VALID]},
    )
    record, (_family, result, error) = _enrich(manager, REQUEST)

    assert error is None
    assert result == {"label": "ok"}
    assert [call["model"] for call in calls] == ["primary-model", "primary-model"]
    assert calls[1]["max_tokens"] > calls[0]["max_tokens"]
    assert "STRUCTURED OUTPUT RECOVERY" in str(calls[1]["prompt"])
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["recovery_kind"] == "truncated_output"
    assert ledger["recovery_calls"] == 1
    assert ledger["recovery_max_output_tokens"] > ledger["max_output_tokens"]
    assert ledger["model_invocations"] == 2


def test_runtime_provider_switch_preserves_server_owned_priority(manager) -> None:
    manager._runtime_requests["priority-build"] = {"provider": "openai", "model": "new-model"}
    resolved = manager._latest_runtime_request(
        "priority-build",
        {"provider": "ollama", "model": "old-model", "_capacity_priority": "foreground"},
    )
    assert resolved["model"] == "new-model"
    assert resolved["_capacity_priority"] == "foreground"
    assert "_capacity_priority" not in manager._runtime_requests["priority-build"]


def test_assessment_contradiction_gets_one_consistency_repair_call(
    monkeypatch,
    manager,
    traces,
) -> None:
    first = (
        '{"label":"ok","field_assessments":{"proposition_status":'
        '{"reason":"Structured-output contradiction: outcome=supported_value but the metadata value is empty. '
        'The text presents its claims as definitive truths."}}}'
    )
    second = '{"label":"ok","field_assessments":{"proposition_status":{"reason":"Consistent."}}}'
    calls = _provider(monkeypatch, {"primary-model": [first, second]})
    record: dict[str, object] = {"record_id": "r1", "text": "Such genesis is impossible."}
    results = manager._execute_metadata_tasks(
        record,
        REQUEST,
        [("discourse", PROMPT, RepairAnswer, 512, SCHEMA)],
        "",
        None,
    )
    _family, result, error = results[0]

    assert error is None
    assert result is not None
    assert [call["model"] for call in calls] == ["primary-model", "primary-model"]
    assert "STRUCTURED OUTPUT CONSISTENCY REPAIR" in str(calls[1]["prompt"])
    repair_data = json.loads(str(calls[1]["prompt"]).rsplit("\n", 1)[1])
    assert repair_data["proposition_status"]["metadata_value"] is None
    assert repair_data["proposition_status"]["assessment"] == json.loads(first)["field_assessments"]["proposition_status"]
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["recovery_kind"] == "assessment_contradiction"
    assert ledger["recovery_fields"] == ["proposition_status"]
    assert ledger["recovery_calls"] == 1
    assert ledger["residual_contradiction_fields"] == []
    assert ledger["model_invocations"] == 2


def test_residual_assessment_contradiction_gets_one_final_repair_call(
    monkeypatch,
    manager,
    traces,
) -> None:
    contradictory = (
        '{"label":"ok","field_assessments":{"proposition_status":'
        '{"reason":"Structured-output contradiction: outcome=supported_value but the metadata value is empty. '
        'The text presents its claims as definitive truths."}}}'
    )
    repaired = '{"label":"ok","field_assessments":{"proposition_status":{"reason":"Consistent."}}}'
    calls = _provider(
        monkeypatch,
        {"primary-model": [contradictory, contradictory, repaired]},
    )
    record: dict[str, object] = {
        "record_id": "r1",
        "text": "Such genesis is impossible.",
    }
    results = manager._execute_metadata_tasks(
        record,
        REQUEST,
        [("discourse", PROMPT, RepairAnswer, 512, SCHEMA)],
        "",
        None,
    )
    _family, result, error = results[0]

    assert error is None
    assert result is not None
    assert [call["model"] for call in calls] == [
        "primary-model",
        "primary-model",
        "primary-model",
    ]
    assert "STRUCTURED OUTPUT CONSISTENCY REPAIR" in str(calls[1]["prompt"])
    assert "FINAL STRUCTURED OUTPUT CONSISTENCY REPAIR" in str(calls[2]["prompt"])
    assert json.loads(str(calls[2]["prompt"]).rsplit("\n", 1)[1]) == json.loads(
        str(calls[1]["prompt"]).rsplit("\n", 1)[1]
    )
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["recovery_kind"] == "assessment_contradiction"
    assert ledger["recovery_calls"] == 2
    assert ledger["residual_contradiction_fields"] == []
    assert ledger["model_invocations"] == 3


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


def test_timeout_without_a_timeout_edge_defers_outer_recovery(monkeypatch, manager, traces) -> None:
    _use(monkeypatch, [{"on_timeout": None}, {}])
    calls = _provider(monkeypatch, {"primary-model": [TimeoutError("read timed out")], "review-model": [VALID]})
    record, (_family, result, error) = _enrich(manager, WITH_REVIEW)

    assert [call["model"] for call in calls] == ["primary-model"]
    assert result is None and "timed out" in str(error)
    assert record["metadata_stage_status"]["discourse"] == "retry_pending"
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["retryable"] is True
    assert ledger["next_automatic_recovery_attempt"] == 1
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


def test_enrichment_uses_generic_executor_without_legacy_provider_loop(monkeypatch, manager, traces):
    from app.pipelines.graph_execution import GraphExecutor
    from app.pipelines.structured_llm_stage import StructuredStageSession

    executed = []
    original = GraphExecutor.run

    def run_graph(executor, inputs):
        executed.append(executor.resolved_hash)
        return original(executor, inputs)

    monkeypatch.setattr(GraphExecutor, 'run', run_graph)
    monkeypatch.setattr(StructuredStageSession, 'run', lambda *args, **kwargs: pytest.fail('legacy provider loop must not execute'))
    calls = _provider(monkeypatch, {'primary-model': ['invalid'], 'review-model': [VALID]})
    record, (_, answer, error) = _enrich(manager, WITH_REVIEW)
    assert error is None and answer == {'label': 'ok'}
    assert len(executed) == 1
    assert executed[0] == record['metadata_execution_ledger']['discourse']['pipeline']['pipeline_hash']
    assert [call['model'] for call in calls] == ['primary-model', 'review-model']


def test_enrichment_session_compiles_once_and_keeps_call_local_context(monkeypatch):
    from app.pipelines.corpus_metadata_enrichment import EnrichmentSession
    from app.pipelines.graph_execution import GraphExecutor

    compiled = []
    original = GraphExecutor.__init__

    def compile_graph(executor, *args, **kwargs):
        compiled.append(args[0].pipeline_id)
        original(executor, *args, **kwargs)

    monkeypatch.setattr(GraphExecutor, '__init__', compile_graph)
    session = EnrichmentSession.open()
    calls = []

    def invoke(role, attempts, escalated):
        calls.append((role, attempts, escalated))
        return {'label': 'proposal'}

    for contract in ('first_contract', 'second_contract'):
        assert session.run(invoke, response_contract=contract, providers={'primary': ('fake', 'model')}) == {'label': 'proposal'}
        assert session.identity()['stages'] == [{'stage_id': 'primary', 'provider_role': 'primary', 'status': 'completed'}]
    assert len(compiled) == 1
    assert calls == [('primary', 1, False), ('primary', 1, False)]
    assert session.counts['primary']['contracts'] == {'first_contract', 'second_contract'}


def test_enrichment_cancellation_does_not_invoke_fallback_or_create_failed_observation():
    from app.pipelines.corpus_metadata_enrichment import EnrichmentSession

    session = EnrichmentSession.open()
    roles = []

    def invoke(role, attempts, escalated):
        roles.append(role)
        raise InterruptedError('cancelled')

    with pytest.raises(InterruptedError):
        session.run(invoke, response_contract='test', providers={})
    assert roles == ['primary']
    assert session.identity()['stages'] == []
    assert session.counts == {}



def test_transient_provider_failure_becomes_retry_pending_and_recovers(
    monkeypatch, manager, traces,
):
    calls = _provider(
        monkeypatch,
        {
            "primary-model": [
                ProviderRequestError(
                    "OpenAI-compatible endpoint returned HTTP 502: upstream failed",
                    status_code=502,
                    provider_code="upstream_failed",
                ),
                VALID,
            ]
        },
    )
    record: dict[str, object] = {"record_id": "r1", "text": "Text."}
    first = manager._execute_metadata_tasks(
        record,
        REQUEST,
        [("discourse", PROMPT, Answer, 512, SCHEMA)],
        "",
        None,
    )
    assert first[0][1] is None
    assert first[0][2] is not None
    assert record["metadata_stage_status"]["discourse"] == "retry_pending"
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["failure_code"] == "provider_upstream_failure"
    assert ledger["retryable"] is True
    assert ledger["next_automatic_recovery_attempt"] == 1

    record["metadata_stage_status"]["discourse"] = "queued"
    ledger["state"] = "queued"
    ledger["automatic_recovery_inflight_attempt"] = 1
    ledger.pop("next_automatic_recovery_attempt", None)

    second = manager._execute_metadata_tasks(
        record,
        REQUEST,
        [("discourse", PROMPT, Answer, 512, SCHEMA)],
        "",
        None,
    )
    assert second == [("discourse", {"label": "ok"}, None)]
    assert record["metadata_stage_status"]["discourse"] == "complete"
    assert record["metadata_execution_ledger"]["discourse"]["recovered_after_retry"] is True
    assert record["metadata_execution_ledger"]["discourse"]["automatic_recovery_attempts"] == 1
    assert len(calls) == 2


def test_provider_graph_preserves_retryability_after_both_roles_fail(
    monkeypatch, manager, traces,
):
    calls = _provider(
        monkeypatch,
        {
            "primary-model": [
                ProviderRequestError("primary upstream", status_code=502),
            ],
            "review-model": [
                ProviderRequestError("review upstream", status_code=503),
            ],
        },
    )
    record: dict[str, object] = {"record_id": "r1", "text": "Text."}
    result = manager._execute_metadata_tasks(
        record,
        WITH_REVIEW,
        [("discourse", PROMPT, Answer, 512, SCHEMA)],
        "",
        None,
    )
    assert result[0][1] is None
    assert result[0][2] is not None
    assert record["metadata_stage_status"]["discourse"] == "retry_pending"
    ledger = record["metadata_execution_ledger"]["discourse"]
    assert ledger["retryable"] is True
    assert ledger["failure_class"] == "transient_provider"
    assert ledger["next_automatic_recovery_attempt"] == 1
    assert [call["model"] for call in calls] == ["primary-model", "review-model"]


def test_request_bound_pipeline_executes_without_re_resolving_global_assignment(
    monkeypatch,
    manager,
    traces,
):
    source = built_in_pipeline(*BUILT_IN)
    assert source is not None
    exact = source.model_copy(
        update={
            "pipeline_id": "corpus.metadata_enrichment.request-bound",
            "built_in": False,
            "stages": [
                source.stages[0].model_copy(
                    update={"config": {"provider_role": "primary", "attempts": 2}}
                ),
                source.stages[1],
            ],
        }
    )

    monkeypatch.setattr(
        manager_module.pipeline_manager,
        "resolve",
        lambda _feature: (_ for _ in ()).throw(
            AssertionError("request-bound execution must not re-resolve assignment")
        ),
    )
    calls = _provider(
        monkeypatch,
        {"primary-model": ["invalid", VALID]},
    )
    request = {
        **REQUEST,
        "pipeline_definition": exact.model_dump(mode="json"),
        "pipeline_hash": pipeline_hash(exact),
    }

    record, (_family, result, error) = _enrich(manager, request)

    assert error is None
    assert result == {"label": "ok"}
    assert [call["model"] for call in calls] == ["primary-model", "primary-model"]
    identity = record["metadata_execution_ledger"]["discourse"]["pipeline"]
    assert identity["pipeline_id"] == exact.pipeline_id
    assert identity["pipeline_hash"] == pipeline_hash(exact)
