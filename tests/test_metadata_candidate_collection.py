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

"""Advisory collection, dependency invalidation and generic graph integration."""

from copy import deepcopy

import pytest
from app import (
    document_intelligence,
    metadata_adjudication_cache,
    metadata_schema,
    nlp_annotations,
)
from app.corpus_document_context import record_fingerprint
from app.pipelines.graph_execution import GraphExecutor
from app.pipelines.metadata_candidate_collection import (
    CandidateCollector,
    MetadataCandidate,
    candidate_collection_strategies,
)
from app.pipelines.models import (
    PipelineDefinition,
)
from app.pipelines.purposes import PipelinePurposeSpec, RunInputSpec
from app.pipelines.registry import StrategyRegistry

TEXT = "Rousseau questions certainty."


def record():
    return {
        "record_id": "r1", "record_revision": 1, "source_document_id": "d1",
        "source_spans": [{"block_id": "b1"}], "text": TEXT,
        "nlp_candidates": {
            "status": "ok", "engine": "spacy", "model": "test",
            "text_sha256": nlp_annotations.text_digest(TEXT),
            "fields": {"persons": [{"text": "Rousseau", "start": 0, "end": 8, "tag": "PERSON", "source": "ner"}]},
        },
    }


def exemplar(schema, *, value=None, kind="positive"):
    return {
        "metadata_exemplar_id": "mex-1", "field_id": schema.field_id("persons"),
        "record_id": "r2", "record_revision": 4, "source_document_id": "d2",
        "assertion_status": "human_confirmed", "kind": kind,
        "field_value": ["Rousseau"] if value is None and kind != "absence" else value,
        "evidence_ref": {
            "record_id": "r2", "record_revision": 4, "source_document_id": "d2",
            "block_ids": ["b2"], "source_spans": [{"block_id": "b2"}],
        },
    }


def collector(row=None, schema=None, **options):
    return CandidateCollector(
        row or record(), schema or metadata_schema.default_schema(), fields=options.pop("fields", ["persons"]),
        context=options.pop("context", {"reviewer_scope": "reviewer-A", "memory_epoch": "1"}),
        exact_lookup=options.pop("exact_lookup", lambda **kw: None), **options,
    )


def test_nlp_matches_existing_current_span_contract_without_mutation():
    row = record()
    before = deepcopy(row)
    packet = collector(row).collect_nlp()
    assert row == before
    assert packet.candidates[0].value == nlp_annotations.current_field_candidates(row)["persons"][0]["text"]
    assert packet.candidates[0].origin_ref == {
        "record_id": "r1", "record_revision": 1, "source_document_id": "d1", "start": 0, "end": 8,
    }
    assert packet.candidates[0].authority == "advisory"
    assert packet.candidates[0].current_record_support == "unchecked"
    with pytest.raises(ValueError):
        MetadataCandidate.model_validate(packet.candidates[0].model_dump() | {"authority": "human_confirmed"})


@pytest.mark.parametrize("change", ["stale", "wrong_quote", "negative_offset", "boolean_offset"])
def test_invalid_nlp_never_becomes_candidate(change):
    row = record()
    span = row["nlp_candidates"]["fields"]["persons"][0]
    if change == "stale":
        row["text"] += " revised"
    elif change == "wrong_quote":
        span["text"] = "Derrida"
    else:
        span["start"] = -1 if change == "negative_offset" else False
    packet = collector(row).collect_nlp()
    assert not packet.candidates
    assert packet.diagnostics


def test_document_hints_reuse_existing_digest_and_source_gates():
    row = record()
    row["document_intelligence"] = {
        "version": 2, "status": "ok", "record_text_sha256": document_intelligence._sha256(TEXT),
        "record_source_fingerprint": record_fingerprint(row),
        "entities": [{"label": "Rousseau", "entity_type": "PERSON"}],
    }
    packet = collector(row).collect_document_intelligence()
    assert packet.candidates[0].value == document_intelligence.prompt_hints(row, ["persons"])["person_candidates"][0]
    assert "start" not in packet.candidates[0].origin_ref
    row["source_spans"] = [{"block_id": "changed"}]
    assert not collector(row).collect_document_intelligence().candidates


def test_exact_memory_uses_existing_key_and_never_confers_authority():
    schema = metadata_schema.default_schema()
    metadata_adjudication_cache.remember(
        record_id="r1", text=TEXT, field="persons", value=["Rousseau"],
        schema_version=schema.schema_version, field_id=schema.field_id("persons"),
    )
    try:
        subject = collector(schema=schema, exact_lookup=metadata_adjudication_cache.suggestions)
        packet = subject.collect_exact_memory()
        assert packet.candidates[0].value == ["Rousseau"]
        assert packet.candidates[0].origin == "exact_memory"
        assert packet.candidates[0].current_record_support == "unchecked"
        changed = record() | {"text": TEXT + " changed"}
        assert not collector(changed, schema, exact_lookup=metadata_adjudication_cache.suggestions).collect_exact_memory().candidates
    finally:
        metadata_adjudication_cache.clear(record_id="r1")


@pytest.mark.parametrize("decision,value,kind", [("value", ["Rousseau"], "value"), ("absence", [], "absence"), ("correction", ["Levinas"], "correction")])
def test_exact_decisions_are_distinct_snapshots(decision, value, kind):
    schema = metadata_schema.default_schema()
    cached = {"field_id": schema.field_id("persons"), "schema_version": schema.schema_version, "decision": decision, "latest_value": value}
    calls = []

    def lookup(**kwargs):
        calls.append(kwargs)
        return cached

    subject = collector(schema=schema, exact_lookup=lookup)
    cached["latest_value"] = ["changed later"]
    assert subject.collect_exact_memory().candidates[0].value == value
    assert subject.collect_exact_memory().candidates[0].kind == kind
    assert len(calls) == 1
    assert calls[0]["cardinality"] == "list"


def test_legacy_exact_memory_is_diagnosed_without_guessing_field_identity():
    packet = collector(exact_lookup=lambda **kw: {"latest_value": ["Rousseau"]}).collect_exact_memory()
    assert not packet.candidates
    assert packet.diagnostics == ("incompatible_exact_memory",)


@pytest.mark.parametrize("change", ["field", "authority", "revision", "source", "missing_evidence"])
def test_ineligible_precedents_are_visible(change):
    schema = metadata_schema.default_schema()
    item = exemplar(schema)
    if change == "field":
        item["field_id"] = "unrelated"
    elif change == "authority":
        item["assertion_status"] = "unreviewed"
    elif change == "revision":
        item["evidence_ref"]["record_revision"] = 5
    elif change == "source":
        item["evidence_ref"]["source_document_id"] = ""
    else:
        item["evidence_ref"]["block_ids"] = []
    packet = collector(schema=schema, exemplars={"persons": [item]}).collect_reviewed_precedents()
    assert not packet.candidates
    assert packet.diagnostics == ("ineligible_reviewed_precedent",)


def test_aggregation_preserves_rivals_origins_absence_and_historical_evidence():
    schema = metadata_schema.default_schema()
    rows = [exemplar(schema), exemplar(schema, value=["Levinas"]), exemplar(schema, kind="absence")]
    subject = collector(schema=schema, exemplars={"persons": rows})
    nlp = subject.collect_nlp()
    historical = subject.collect_reviewed_precedents()
    result = subject.aggregate([nlp, historical, nlp])
    assert len(result.candidates) == 4
    assert result.candidates[-1].kind == "absence"
    assert result.candidates[1].origin_ref["record_id"] == "r2"
    assert result.candidates[1].origin_ref["record_revision"] == 4
    assert result.candidates[1].current_record_support == "unchecked"
    assert [item.value for item in result.candidates[1:3]] == [["Rousseau"], ["Levinas"]]


@pytest.mark.parametrize("dependency", ["text", "revision", "source", "schema", "reviewer", "memory", "projection", "human_value", "selection", "field_scope", "precedents", "exact_memory"])
def test_dependency_change_rejects_old_packet(dependency):
    row, schema = record(), metadata_schema.default_schema()
    old = collector(row, schema).collect_nlp()
    options = {}
    if dependency == "text":
        row["text"] += " changed"
    elif dependency == "revision":
        row["record_revision"] = 2
    elif dependency == "source":
        row["source_spans"] = [{"block_id": "other"}]
    elif dependency == "schema":
        schema.fields[0].instruction += " changed"
    elif dependency in {"reviewer", "memory"}:
        options["context"] = {"reviewer_scope": "B" if dependency == "reviewer" else "reviewer-A", "memory_epoch": "2"}
    elif dependency == "projection":
        row["nlp_candidates"]["model"] = "different"
    elif dependency == "human_value":
        row["persons"] = ["Human decision"]
    elif dependency == "selection":
        row["current_field_assertions"] = {"persons": "assertion-new"}
    elif dependency == "field_scope":
        options["fields"] = ["persons", "speaker"]
    elif dependency == "precedents":
        options["exemplars"] = {"persons": [exemplar(schema)]}
    else:
        options["exact_lookup"] = lambda **kw: {"latest_value": ["new"]}
    with pytest.raises(ValueError, match="Stale or incompatible"):
        collector(row, schema, **options).aggregate([old])


def test_snapshot_and_bounds_and_unknown_fields():
    row = record()
    span = row["nlp_candidates"]["fields"]["persons"][0]
    row["nlp_candidates"]["fields"]["persons"] = [span | {"tag": f"tag-{i}"} for i in range(40)]
    subject = collector(row)
    row["text"] = "changed externally"
    packet = subject.collect_nlp()
    assert len(packet.candidates) == 32
    assert packet.diagnostics == ("candidate_limit_reached",)
    assert len(subject.aggregate([packet, packet]).candidates) == 32
    with pytest.raises(ValueError, match="unknown schema"):
        collector(fields=["not_a_field"])
    with pytest.raises(ValueError, match="reviewer scope"):
        collector(context={})


def test_renamed_field_reuses_semantic_identity_without_redefining_it():
    schema = metadata_schema.default_schema()
    field = next(item for item in schema.fields if item.name == "persons")
    stable_id = field.field_id
    field.name = "mentioned_people"
    subject = collector(schema=schema, fields=["mentioned_people"])
    candidate = subject.collect_nlp().candidates[0]
    assert candidate.field_name == "mentioned_people"
    assert candidate.field_id == stable_id
    assert candidate.semantic_compatibility_id == "derridai.indexing.persons"
    assert candidate.value == "Rousseau"


def test_failed_projection_and_explicit_empty_remain_distinct():
    row = record()
    row["nlp_candidates"]["fields"] = {}
    assert collector(row).collect_nlp().diagnostics == ("nlp_empty",)
    row["nlp_candidates"]["status"] = "failed"
    assert collector(row).collect_nlp().diagnostics == ("nlp_failed",)


def test_precedent_semantic_field_identity_reuses_assertion_contract():
    schema = metadata_schema.default_schema()
    item = exemplar(schema)
    item["field_id"] = schema.semantic_compatibility_id("persons")
    packet = collector(schema=schema, exemplars={"persons": [item]}).collect_reviewed_precedents()
    assert len(packet.candidates) == 1


def test_changed_graph_context_fails_without_leaking_private_value():
    subject = collector()
    handler = subject.handlers()["metadata.collect_nlp"]
    with pytest.raises(ValueError, match="incompatible context") as failure:
        handler(None, {"context": {"private": TEXT}})
    assert TEXT not in str(failure.value)


def test_generic_graph_collection_fan_in_keeps_trace_free_of_values():
    subject = collector()
    handlers = subject.handlers()
    specs = candidate_collection_strategies()
    stages = []
    entries = []
    for index, name in enumerate(handlers):
        aggregate = name == "metadata.aggregate_candidates"
        stage_id = "aggregate" if aggregate else f"collect-{index}"
        stages.append({"id": stage_id, "strategy": name, **({} if aggregate else {"next": ["aggregate"]})})
        if not aggregate:
            entries.append(stage_id)
    purpose = PipelinePurposeSpec(
        purpose_id="test_collection", category="metadata", label="Test", description="Test",
        consuming_feature="test", consumer="test", input_semantics="test", output_semantics="advisory",
        authority_semantics="advisory", output_type="metadata_candidate_set",
        run_inputs=[RunInputSpec(name="context", data_type="any")],
    )
    pipeline = PipelineDefinition(pipeline_id="test.collection", name="Test", purpose="test_collection", entry_stage_ids=entries, stages=stages)
    executor = GraphExecutor(pipeline, registry=StrategyRegistry(specs), purpose=purpose, handlers=handlers)
    result = executor.run({"context": subject.binding})
    packet = result.terminal_outputs["aggregate"]["candidates"]
    assert len(packet.candidates) == 1
    assert all(trace.status == "completed" for trace in result.stages)
    traces = str([trace.model_dump() for trace in result.stages])
    assert "Rousseau" not in traces and TEXT not in traces
