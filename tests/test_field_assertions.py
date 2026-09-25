# Copyright 2026 Aaron John Schlosser, PhD.
"""Regression coverage for canonical metadata assertions and legacy projection."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.corpus_record_quality import _metadata_source_quality_gate
from app.field_assertions import (
    FieldAssertion,
    confirm_absence,
    confirm_assertion,
    create_model_assertion,
    current_assertion_by_name,
    get_assertions,
    migrate_record_assertions,
    project_record_assertions,
    replace_assertion_evidence,
    reset_fields_for_evaluation,
    validate_projection,
)
from app.metadata_schema import default_schema


def test_model_confidence_and_human_confirmation_preserve_derivation() -> None:
    record = {"record_id": "r1", "record_revision": 1, "speaker": "Derrida"}
    assertion = create_model_assertion(
        record,
        "speaker",
        "Derrida",
        confidence=0.82,
        model="test-model",
        evidence=[{"block_id": "b1"}],
    )
    confirmed = confirm_assertion(record, assertion, actor="reviewer")
    project_record_assertions(record)

    assert confirmed.derivation_method == "model"
    assert confirmed.authority_status == "human_confirmed"
    assert confirmed.confidence == pytest.approx(0.82)
    assert record["metadata_field_status"]["speaker"]["status"] == "human_confirmed"
    assert record["metadata_field_status"]["speaker"]["assertion_id"] == confirmed.assertion_id
    assert not validate_projection(record)


def test_legacy_migration_is_idempotent_and_preserves_confirmed_absence() -> None:
    record = {
        "record_id": "r2",
        "record_revision": 1,
        "position_holder": None,
        "metadata_field_status": {
            "position_holder": {
                "status": "confirmed_absent",
                "method": "human_review",
                "reason": "No supported position holder.",
            }
        },
    }

    migrate_record_assertions(record)
    first = record["field_assertions"]
    migrate_record_assertions(record)

    assert record["field_assertions"] == first
    current = current_assertion_by_name(record, "position_holder")
    assert current is not None
    assert current.value_status == "confirmed_absent"
    assert record["position_holder"] is None
    assert not validate_projection(record)


def test_evaluated_unknown_confidence_is_serialized_as_null() -> None:
    assertion = FieldAssertion(
        record_id="r3",
        field_id="legacy.speaker",
        field_name="speaker",
        value="Derrida",
        derivation_method="model",
        evaluation_status="value_supported",
        confidence=None,
    )

    assert assertion.model_dump(mode="json")["confidence"] is None


def test_invalid_states_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FieldAssertion(
            record_id="r4",
            field_id="legacy.speaker",
            field_name="speaker",
            value="Derrida",
            derivation_method="model",
            evaluation_status="not_evaluated",
            confidence=0.5,
        )
    with pytest.raises(ValidationError):
        FieldAssertion(
            record_id="r5",
            field_id="legacy.speaker",
            field_name="speaker",
            value="Derrida",
            derivation_method="model",
            evaluation_status="evaluation_failed",
            value_status="confirmed_absent",
        )


def test_human_absence_supersedes_model_candidate_without_claiming_model_absence() -> None:
    record = {"record_id": "r6", "record_revision": 1}
    model = create_model_assertion(
        record,
        "position_holder",
        None,
        outcome="no_supported_value",
        confidence=0.73,
        model="test-model",
        evidence=[{"block_ids": ["b1"], "reason": "No supported holder in this passage."}],
    )
    absent = confirm_absence(record, "position_holder", prior=model, actor="reviewer")

    assert absent.derivation_method == "model"
    assert absent.authority_status == "human_confirmed"
    assert absent.value_status == "confirmed_absent"
    assert absent.supersedes_assertion_id == model.assertion_id
    assert absent.model == "test-model"
    assert absent.confidence == pytest.approx(0.73)
    assert absent.evidence == model.evidence




def test_confirmed_absence_preserves_model_provenance_and_evidence() -> None:
    record = {"record_id": "r8", "record_revision": 2}
    model = create_model_assertion(
        record,
        "position_holder",
        None,
        outcome="no_supported_value",
        confidence=0.64,
        model="model-x",
        run_id="run-1",
        evidence=[{"block_ids": ["b2"], "confidence": 0.9}],
    )
    absent = confirm_absence(record, "position_holder", prior=model, actor="reviewer")

    assert absent.derivation_method == "model"
    assert absent.authority_status == "human_confirmed"
    assert absent.value_status == "confirmed_absent"
    assert absent.confidence == pytest.approx(0.64)
    assert absent.model == "model-x"
    assert absent.run_id == "run-1"
    assert absent.evidence == [{"block_ids": ["b2"], "confidence": 0.9}]


def test_reset_fields_for_evaluation_preserves_durable_history() -> None:
    record = {"record_id": "r9", "record_revision": 1}
    original = create_model_assertion(
        record,
        "stance",
        "critical",
        confidence=0.8,
        model="model-x",
    )
    project_record_assertions(record)

    reset_fields_for_evaluation(record, ["stance"], method="metadata_rerun")
    current = current_assertion_by_name(record, "stance")

    assert current is not None
    assert current.assertion_id != original.assertion_id
    assert current.value_status == "unresolved"
    assert current.evaluation_status == "not_evaluated"
    assert "stance" not in record
    assert any(
        item.assertion_id == original.assertion_id
        for item in get_assertions(record, original.field_id)
    )


def test_worker_reset_discards_ephemeral_field_history() -> None:
    record = {"record_id": "r10", "record_revision": 1}
    create_model_assertion(record, "stance", "critical", confidence=0.8)
    create_model_assertion(record, "speaker", "Derrida", confidence=0.9)
    project_record_assertions(record)

    reset_fields_for_evaluation(
        record,
        ["stance"],
        discard_history=True,
        method="metadata_rerun_worker",
    )

    assert current_assertion_by_name(record, "stance") is None
    assert "stance" not in record
    assert current_assertion_by_name(record, "speaker") is not None


def test_replacing_evidence_supersedes_without_changing_authority() -> None:
    record = {"record_id": "r11", "record_revision": 3}
    model = create_model_assertion(
        record,
        "speaker",
        "Derrida",
        confidence=0.9,
        evidence=[{"block_ids": ["b1"]}],
    )
    confirmed = confirm_assertion(record, model)
    changed = replace_assertion_evidence(
        record,
        confirmed,
        [{"block_ids": ["b2"], "reviewed_by": "human"}],
        actor="reviewer",
    )

    assert changed.supersedes_assertion_id == confirmed.assertion_id
    assert changed.derivation_method == "model"
    assert changed.authority_status == "human_confirmed"
    assert changed.evidence == [{"block_ids": ["b2"], "reviewed_by": "human"}]


def test_schema_identity_survives_legacy_migration_and_custom_fields() -> None:
    schema = default_schema()
    schema.fields.append(
        schema.fields[0].model_copy(
            update={
                "name": "interlocutor_role",
                "label": "Interlocutor role",
                "field_id": "field-interlocutor-role",
                "semantic_compatibility_id": None,
            }
        )
    )
    record = {
        "record_id": "r7",
        "record_revision": 1,
        "interlocutor_role": "critic",
        "metadata_field_status": {
            "interlocutor_role": {"status": "model_inferred", "confidence": 0.7}
        },
    }

    migrate_record_assertions(record, schema)
    assertion = current_assertion_by_name(record, "interlocutor_role")

    assert assertion is not None
    assert assertion.field_id == "field-interlocutor-role"
    assert record["interlocutor_role"] == "critic"



def test_source_quality_failure_creates_unresolved_assertion_not_absence() -> None:
    schema = default_schema()
    record = {
        "record_id": "r-source-quality",
        "record_revision": 1,
        "text": "corrupted source",
        "source_quality_issues": [{"code": "fragmented_glyph_layout", "severity": "blocking"}],
        "metadata_field_status": {},
    }

    blocked = _metadata_source_quality_gate(
        record,
        ["speaker"],
        None,
        schema=schema,
    )

    assert blocked is True
    assertion = current_assertion_by_name(record, "speaker")
    assert assertion is not None
    assert assertion.evaluation_status == "not_evaluated"
    assert assertion.value_status == "unresolved"
    assert assertion.authority_status == "unreviewed"
    assert assertion.value_status != "confirmed_absent"
    assert "confidence" not in assertion.model_dump(mode="json", exclude_none=True)
