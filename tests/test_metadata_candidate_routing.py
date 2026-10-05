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

"""Experimental routing contracts, current evidence and canonical authority."""

from copy import deepcopy

import pytest
from app.pipelines.graph_execution import GraphExecutionError, GraphExecutor
from app.pipelines.metadata_candidate_collection import candidate_collection_strategies
from app.pipelines.metadata_candidate_routing import (
    CandidateRouting,
    CurrentEvidence,
    FieldEvaluation,
    candidate_routing_strategies,
)
from app.pipelines.models import PipelineDefinition
from app.pipelines.purposes import PipelinePurposeSpec, RunInputSpec
from app.pipelines.registry import StrategyRegistry
from test_metadata_candidate_collection import collector, record


def unsupported(task):
    return FieldEvaluation(
        field_name=task.field_name,
        outcome="uncertain",
        confidence=None,
        reason="No supported value.",
    )


def supported(task, value=None):
    return FieldEvaluation(
        field_name=task.field_name,
        outcome="supported_value",
        value=["Rousseau"] if value is None else value,
        confidence=None,
        reason="Supported by current text.",
        evidence=(
            CurrentEvidence(
                record_id=task.binding.record_id,
                record_revision=task.binding.record_revision,
                source_document_id=task.source_document_id,
                start=0,
                end=8,
                quote="Rousseau",
            ),
        ),
    )


def graph(owner, *, verify=unsupported, infer=unsupported):
    adapter = CandidateRouting(owner, verify=verify, infer=infer)
    handlers = owner.handlers() | adapter.handlers()
    specs = candidate_collection_strategies() + candidate_routing_strategies()
    bind = lambda stage, output: {"source": "stage", "stage": stage, "output": output}
    stages = [
        {"id": "collect", "strategy": "metadata.collect_nlp", "next": ["route"]},
        {
            "id": "route",
            "strategy": "metadata.route_candidates",
            "next": ["resolve", "verify", "infer", "merge"],
        },
        {
            "id": "resolve",
            "strategy": "metadata.resolve_candidates",
            "next": ["merge"],
            "inputs": {"tasks": [bind("route", "resolve")]},
        },
        {
            "id": "verify",
            "strategy": "metadata.verify_candidates",
            "next": ["infer", "merge"],
            "inputs": {"tasks": [bind("route", "verify")]},
        },
        {
            "id": "infer",
            "strategy": "metadata.infer_scoped",
            "next": ["merge"],
            "inputs": {"tasks": [bind("route", "infer"), bind("verify", "unresolved")]},
        },
        {
            "id": "merge",
            "strategy": "metadata.aggregate_proposals",
            "inputs": {
                "proposals": [
                    bind("route", "preserved"),
                    *[
                        bind(stage, "proposals")
                        for stage in ("resolve", "verify", "infer")
                    ],
                ]
            },
        },
    ]
    purpose = PipelinePurposeSpec(
        purpose_id="test_routing",
        category="metadata",
        label="Test",
        description="Test",
        consuming_feature="test",
        consumer="test",
        input_semantics="test",
        output_semantics="advisory",
        authority_semantics="advisory",
        output_type="metadata_proposal_set",
        run_inputs=[RunInputSpec(name="context", data_type="any")],
    )
    pipeline = PipelineDefinition(
        pipeline_id="test.routing",
        name="Test",
        purpose="test_routing",
        entry_stage_ids=["collect"],
        stages=stages,
    )
    return adapter, GraphExecutor(
        pipeline, registry=StrategyRegistry(specs), purpose=purpose, handlers=handlers
    )


def test_exact_resolve_skips_providers_and_keeps_canonical_record():
    owner = collector()
    before = deepcopy(owner.record)

    def forbidden(task):
        pytest.fail("Resolved exact mentions must not invoke providers")

    adapter, executor = graph(owner, verify=forbidden, infer=forbidden)
    result = executor.run({"context": owner.binding})
    proposal = result.terminal_outputs["merge"]["proposals"].proposals[0]
    assert proposal.evaluation.value == ["Rousseau"]
    assert proposal.derivation == "deterministic_mention" and proposal.needs_review
    assert proposal.evaluation.confidence is None and proposal.authority == "advisory"
    assert owner.record == before
    assert [t.status for t in result.stages] == [
        "completed",
        "completed",
        "completed",
        "skipped",
        "skipped",
        "completed",
    ]
    assert "Rousseau" not in str([t.model_dump() for t in result.stages])
    assert adapter.aggregate(
        [result.terminal_outputs["merge"]["proposals"]]
    ).proposals == (proposal,)


def test_scoped_infer_only_unresolved_field_and_terminal_order():
    owner = collector(fields=["persons", "stance"])
    calls = []

    def infer(task):
        calls.append(task)
        return unsupported(task)

    _, executor = graph(owner, infer=infer)
    packet = executor.run({"context": owner.binding}).terminal_outputs["merge"][
        "proposals"
    ]
    assert [p.field_name for p in packet.proposals] == ["persons", "stance"]
    assert [t.field_name for t in calls] == ["stance"]
    assert calls[0].candidates == () and calls[0].field_definition["name"] == "stance"
    assert packet.proposals[1].evaluation.outcome == "uncertain"


@pytest.mark.parametrize(
    "status",
    ["human_confirmed", "human_override", "human_confirmed_absent", "confirmed_absent"],
)
def test_owned_fields_have_no_provider_calls(status):
    row = record()
    row["metadata_field_status"] = {"persons": {"status": status}}
    owner = collector(row)
    _, executor = graph(
        owner,
        verify=lambda task: pytest.fail("owned"),
        infer=lambda task: pytest.fail("owned"),
    )
    packet = executor.run({"context": owner.binding}).terminal_outputs["merge"][
        "proposals"
    ]
    assert packet.proposals == () and packet.diagnostics == ("owned_field_preserved",)


def verify_task():
    owner = collector()
    packet = owner.collect_nlp()
    candidate = packet.candidates[0].model_copy(update={"candidate_id": "second"})
    packet = packet.model_copy(update={"candidates": (*packet.candidates, candidate)})
    adapter = CandidateRouting(owner, verify=supported, infer=unsupported)
    return owner, adapter, adapter.route(packet)["VERIFY"][0]


def test_verify_is_model_inferred_and_failed_support_becomes_scoped_infer():
    _, adapter, task = verify_task()
    packet, pending = adapter.execute([task], "VERIFY")
    assert not pending and packet.proposals[0].derivation == "model_inferred"
    adapter.verify = unsupported
    packet, pending = adapter.execute([task], "VERIFY")
    assert (
        not packet.proposals
        and pending[0].route == "INFER"
        and pending[0].candidates == ()
    )
    assert packet.diagnostics == ("verify_uncertain_scoped_infer",)
    final, _ = adapter.execute(pending, "INFER")
    assert (
        adapter.aggregate([packet, final]).proposals[0].evaluation.outcome
        == "uncertain"
    )


@pytest.mark.parametrize(
    "change",
    [
        "field",
        "revision",
        "source",
        "quote",
        "offset",
        "value",
        "confidence",
        "empty_support",
    ],
)
def test_provider_contract_rejects_scope_schema_and_evidence_failures(change):
    _, adapter, task = verify_task()
    answer = supported(task).model_dump()
    if change == "field":
        answer["field_name"] = "stance"
    elif change in {"revision", "source", "quote", "offset"}:
        key, value = {
            "revision": ("record_revision", 9),
            "source": ("source_document_id", "other"),
            "quote": ("quote", "wrong"),
            "offset": ("start", False),
        }[change]
        answer["evidence"][0][key] = value
    elif change == "value":
        answer["value"] = "Rousseau"
    elif change == "confidence":
        del answer["confidence"]
    else:
        answer["evidence"] = ()
    with pytest.raises(ValueError):
        adapter.verify = lambda _: FieldEvaluation.model_validate(answer)
        adapter.execute([task], "VERIFY")


def test_verify_cannot_invent_candidate_value_or_absence_authority():
    _, adapter, task = verify_task()
    adapter.verify = lambda task: supported(task, ["Levinas"])
    with pytest.raises(ValueError, match="outside its candidates"):
        adapter.execute([task], "VERIFY")
    adapter.infer = lambda task: FieldEvaluation(
        field_name=task.field_name,
        outcome="no_supported_value",
        confidence=None,
        reason="No value",
    )
    packet, _ = adapter.execute(
        [task.model_copy(update={"route": "INFER", "candidates": ()})], "INFER"
    )
    assert (
        packet.proposals[0].authority == "advisory" and packet.proposals[0].needs_review
    )


def test_changed_ownership_invalidates_tasks_before_provider_call():
    owner, adapter, task = verify_task()
    owner.record["human_touched_fields"] = ["persons"]
    adapter.verify = lambda task: pytest.fail("stale ownership")
    with pytest.raises(ValueError, match="context changed"):
        adapter.execute([task], "VERIFY")


def test_fanin_rejects_duplicate_missing_and_stale_proposals():
    owner = collector()
    adapter = CandidateRouting(owner, verify=unsupported, infer=unsupported)
    tasks = adapter.route(owner.collect_nlp())["RESOLVE"]
    packet, _ = adapter.execute(tasks, "RESOLVE")
    for packets in (
        [packet, packet],
        [],
        [
            packet.model_copy(
                update={
                    "binding": packet.binding.model_copy(
                        update={"context_hash": "stale"}
                    )
                }
            )
        ],
    ):
        with pytest.raises(ValueError):
            adapter.aggregate(packets)


def test_shared_structured_completion_validates_domain_and_preserves_null_confidence():
    _, adapter, task = verify_task()
    prompts = []

    def factory(task):
        def request(context):
            prompts.append(context.prompt)
            return supported(task).model_dump_json()

        return request

    adapter.verify = adapter.structured_evaluator(factory)
    packet, _ = adapter.execute([task], "VERIFY")
    assert packet.proposals[0].evaluation.confidence is None
    assert "metadata-candidate-routing-v1" in prompts[0] and "inert data" in prompts[0]


def test_provider_failure_is_visible_and_never_silently_infers():
    owner = collector(fields=["stance"])

    def fail(task):
        raise TimeoutError("private provider payload")

    _, executor = graph(owner, infer=fail)
    with pytest.raises(GraphExecutionError) as error:
        executor.run({"context": owner.binding})
    assert "private provider payload" not in str(error.value)
    assert not error.value.result.terminal_outputs


def test_graph_verify_fallback_joins_direct_inference_without_extra_fields():
    from app import nlp_annotations

    row = record()
    row["text"] = "Rousseau and Levinas."
    row["nlp_candidates"]["text_sha256"] = nlp_annotations.text_digest(row["text"])
    row["nlp_candidates"]["fields"]["persons"].append(
        {"text": "Levinas", "start": 13, "end": 20, "tag": "PERSON", "source": "ner"}
    )
    owner = collector(row, fields=["persons", "stance"])
    calls = []

    def infer(task):
        calls.append(task.field_name)
        return unsupported(task)

    _, executor = graph(owner, verify=unsupported, infer=infer)
    result = executor.run({"context": owner.binding})
    packet = result.terminal_outputs["merge"]["proposals"]
    assert calls == ["stance", "persons"]
    assert [p.field_name for p in packet.proposals] == ["persons", "stance"]
    assert "verify_uncertain_scoped_infer" in packet.diagnostics
    assert all(p.route == "INFER" and p.needs_review for p in packet.proposals)


@pytest.mark.parametrize("value", ["PERSON", "supported_value", "null"])
def test_inference_rejects_control_vocabulary_and_placeholders(value):
    _, adapter, task = verify_task()
    task = task.model_copy(update={"route": "INFER", "candidates": ()})
    adapter.infer = lambda task: supported(task, [value])
    with pytest.raises(ValueError):
        adapter.execute([task], "INFER")


@pytest.mark.parametrize("method", ["human", "deterministic", "inherited"])
def test_selected_assertion_ownership_is_preserved(method):
    from app.field_assertions import (
        create_deterministic_assertion,
        create_human_assertion,
        create_inherited_assertion,
    )
    from app.metadata_schema import default_schema

    row = record()
    schema = default_schema()
    if method == "human":
        create_human_assertion(row, "persons", ["Reviewer"], schema=schema)
    elif method == "deterministic":
        create_deterministic_assertion(
            row, "persons", ["Source"], schema=schema, method="test"
        )
    else:
        create_inherited_assertion(row, "persons", ["Manifest"], schema=schema)
    owner = collector(row, schema=schema)
    _, executor = graph(owner)
    packet = executor.run({"context": owner.binding}).terminal_outputs["merge"][
        "proposals"
    ]
    assert packet.proposals == ()
    assert owner.record == row
