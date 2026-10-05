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

"""All-source shadow routing, live context gates and sealed review projection."""

from copy import deepcopy

import pytest
from app import document_intelligence
from app.corpus_document_context import record_fingerprint
from app.metadata_schema import default_schema
from app.pipelines.graph_execution import GraphExecutionError
from app.pipelines.metadata_candidate_collection import candidate_binding
from app.pipelines.metadata_candidate_session import CandidateRoutingSession
from test_metadata_candidate_collection import collector, exemplar
from test_metadata_candidate_routing import supported, unsupported


def session(owner, **options):
    return CandidateRoutingSession(
        owner, read_current=options.pop("read_current", lambda: owner.binding),
        candidate_visible=options.pop("candidate_visible", lambda candidate: True),
        verify=options.pop("verify", unsupported), infer=options.pop("infer", unsupported),
        **options,
    )


def test_all_sources_fan_in_preserves_rivals_and_model_review_state():
    schema = default_schema()
    owner = collector(schema=schema, exemplars={"persons": [exemplar(schema)]})
    before = deepcopy(owner.record)
    seen = []

    def verify(task):
        seen.extend(candidate.origin for candidate in task.candidates)
        return supported(task)

    result = session(owner, verify=verify).run()
    assert seen == ["nlp", "reviewed_precedent"]
    assert result.reviewer_packet.proposals[0].support == "model_inferred"
    assert result.server_proposals.proposals[0].needs_review
    assert owner.record == before
    assert sum(stage.stage_id.startswith("collect_") for stage in result.stages) == 4
    assert "Rousseau" not in str([stage.model_dump() for stage in result.stages])


def test_hidden_precedent_does_not_force_verification_or_leak_values():
    schema = default_schema()
    hidden = exemplar(schema, value=["PRIVATE_VALUE"])
    owner = collector(schema=schema, exemplars={"persons": [hidden]})

    def forbidden(task):
        pytest.fail("Hidden rivals must not force a provider call")

    result = session(
        owner, candidate_visible=lambda c: c.origin != "reviewed_precedent",
        verify=forbidden, infer=forbidden,
    ).run()
    assert result.reviewer_packet.proposals[0].support == "mention_only"
    assert "candidate_not_visible" in result.reviewer_packet.diagnostics
    assert "PRIVATE_VALUE" not in result.reviewer_packet.model_dump_json()


def test_blind_memory_is_withheld_from_provider_and_review_projection():
    schema = default_schema()
    owner = collector(
        schema=schema, fields=["persons", "stance"],
        context={"reviewer_scope": "reviewer-A", "memory_epoch": "1", "blind_fields": ["persons"]},
        exemplars={"persons": [exemplar(schema, value=["PRIVATE_VALUE"])]},
        exact_lookup=lambda **kw: {"field_id": schema.field_id(kw["field"]),
                                  "schema_version": schema.schema_version, "decision": "value",
                                  "latest_value": ["PRIVATE_EXACT"]} if kw["field"] == "persons" else None,
    )
    calls = []

    def infer(task):
        calls.append(task)
        return unsupported(task)

    result = session(owner, blind_fields=["persons"], infer=infer).run()
    assert [task.field_name for task in calls] == ["stance"]
    assert [p.proposal.field_name for p in result.reviewer_packet.proposals] == ["stance"]
    assert result.reviewer_packet.proposals[0].support == "unresolved"
    assert result.reviewer_packet.withheld_fields == ("persons",)
    serialized = result.reviewer_packet.model_dump_json()
    assert all(value not in serialized for value in ("Rousseau", "PRIVATE_VALUE", "PRIVATE_EXACT"))
    assert "blind_memory_withheld" in result.reviewer_packet.diagnostics
    assert len(result.server_proposals.proposals) == 2


def test_blind_policy_must_be_bound_to_current_reviewer_context():
    with pytest.raises(ValueError, match="context binding"):
        session(collector(), blind_fields=["persons"])
    with pytest.raises(ValueError, match="requested scope"):
        session(collector(), blind_fields=["stance"])


@pytest.mark.parametrize("change", ["text", "revision", "ownership", "scope", "blind"])
def test_live_canonical_changes_stop_work_before_providers(change):
    owner = collector(fields=["stance"])
    live = deepcopy(owner.record)
    context = deepcopy(owner.context)
    if change == "text":
        live["text"] += " changed"
    elif change == "revision":
        live["record_revision"] += 1
    elif change == "ownership":
        live["human_touched_fields"] = ["stance"]
    elif change == "scope":
        context["reviewer_scope"] = "reviewer-B"
    else:
        context["blind_fields"] = ["stance"]
    with pytest.raises(ValueError, match="canonical context changed"):
        session(owner, read_current=lambda: candidate_binding(live, owner.schema, context=context)).run()


def test_access_denial_is_sanitized_and_does_not_start_collection():
    owner = collector()

    def denied():
        raise PermissionError("PRIVATE_ACCESS_DETAILS")

    def forbidden():
        pytest.fail("No collection after access denial")

    owner.collect_nlp = forbidden
    with pytest.raises(ValueError, match="access/context check failed") as error:
        session(owner, read_current=denied).run()
    assert "PRIVATE_ACCESS_DETAILS" not in str(error.value)


def test_provider_response_is_discarded_after_concurrent_canonical_edit():
    owner = collector(fields=["persons", "stance"])
    live = deepcopy(owner.record)
    calls = []

    def infer(task):
        calls.append(task.field_name)
        live["human_touched_fields"] = [task.field_name]
        return unsupported(task)

    with pytest.raises(GraphExecutionError) as error:
        session(owner, infer=infer, read_current=lambda: candidate_binding(
            live, owner.schema, context=owner.context,
        )).run()
    assert calls == ["stance"]
    assert error.value.stage_id == "infer"
    assert not error.value.result.terminal_outputs
    assert "Rousseau" not in str([stage.model_dump() for stage in error.value.result.stages])


def test_access_is_rechecked_between_fields_and_before_delivery():
    owner = collector(fields=["stance", "target"])
    calls = []
    access = True

    def read():
        if not access:
            raise PermissionError("PRIVATE_REVOKED")
        return owner.binding

    def infer(task):
        nonlocal access
        calls.append(task.field_name)
        access = False
        return unsupported(task)

    with pytest.raises(GraphExecutionError) as error:
        session(owner, read_current=read, infer=infer).run()
    assert calls == ["stance"]
    assert not error.value.result.terminal_outputs
    assert "PRIVATE_REVOKED" not in str(error.value)


def test_visibility_failure_and_unknown_decision_are_visible_failures():
    def failed(candidate):
        raise RuntimeError("PRIVATE_VISIBILITY_ERROR")

    for predicate in (failed, lambda candidate: None):
        with pytest.raises(GraphExecutionError) as error:
            session(collector(), candidate_visible=predicate).run()
        assert error.value.stage_id == "aggregate"
        assert not error.value.result.terminal_outputs
        assert "PRIVATE_VISIBILITY_ERROR" not in str(error.value)


def test_all_owned_graph_returns_explicit_empty_review_packet_without_provider():
    owner = collector()
    owner.record["human_touched_fields"] = ["persons"]
    owner.binding = candidate_binding(owner.record, owner.schema, context=owner.context)

    def forbidden(task):
        pytest.fail("No provider for owned fields")

    result = session(owner, infer=forbidden, verify=forbidden).run()
    assert not result.server_proposals.proposals
    assert not result.reviewer_packet.proposals
    assert "owned_field_preserved" in result.reviewer_packet.diagnostics


def test_four_sources_retain_each_origin_and_do_not_transfer_historical_support():
    schema = default_schema()
    owner = collector(schema=schema, exemplars={"persons": [exemplar(schema)]},
                      exact_lookup=lambda **kw: {"field_id": schema.field_id(kw["field"]),
                                                "schema_version": schema.schema_version,
                                                "decision": "value", "latest_value": ["Rousseau"]})
    owner.record["document_intelligence"] = {
        "version": 2, "status": "ok",
        "record_text_sha256": document_intelligence._sha256(owner.record["text"]),
        "record_source_fingerprint": record_fingerprint(owner.record),
        "entities": [{"label": "Rousseau", "entity_type": "PERSON"}],
    }
    owner.binding = candidate_binding(owner.record, schema, context=owner.context)
    origins = []

    def verify(task):
        origins.extend(c.origin for c in task.candidates)
        return supported(task)

    result = session(owner, verify=verify).run()
    assert origins == ["nlp", "document_intelligence", "exact_memory", "reviewed_precedent"]
    proposal = result.server_proposals.proposals[0]
    assert proposal.route == "VERIFY" and proposal.derivation == "model_inferred"
    assert proposal.evaluation.evidence[0].record_id == owner.record["record_id"]


def test_cancellation_from_live_loader_prevents_fallback_and_delivery():
    owner = collector(fields=["stance", "target"])
    cancelled = False
    calls = []

    def read():
        if cancelled:
            raise InterruptedError("PRIVATE_CANCEL_DETAILS")
        return owner.binding

    def infer(task):
        nonlocal cancelled
        calls.append(task.field_name)
        cancelled = True
        return unsupported(task)

    with pytest.raises(InterruptedError, match="Routing cancelled") as error:
        session(owner, read_current=read, infer=infer).run()
    assert calls == ["stance"]
    assert "PRIVATE_CANCEL_DETAILS" not in str(error.value)
