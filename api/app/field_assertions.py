# Copyright 2026 Aaron John Schlosser, PhD.
"""Canonical field assertions and the legacy record compatibility boundary.

Field names are presentation/storage labels.  A FieldAssertion is the durable
account of how a value entered the research model, what evaluation occurred,
what authority it has, and whether the value is present, absent, invalid, or
unresolved.  The top-level record value and metadata_field_status are derived
projections retained for old clients and human-readable JSONL.
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

DerivationMethod = Literal["deterministic", "model", "human", "inherited", "imported", "other"]
EvaluationStatus = Literal["not_evaluated", "value_supported", "no_supported_value", "evaluation_failed"]
AuthorityStatus = Literal["unreviewed", "human_confirmed", "human_override", "disputed"]
ValueStatus = Literal["present", "confirmed_absent", "invalid", "unresolved"]

_STATUS_TO_CANONICAL = {
    "model_inferred": ("model", "value_supported", "unreviewed", "present"),
    "llm_inferred": ("model", "value_supported", "unreviewed", "present"),
    "human_confirmed": ("model", "value_supported", "human_confirmed", "present"),
    "human_override": ("human", "value_supported", "human_override", "present"),
    "deterministic": ("deterministic", "value_supported", "unreviewed", "present"),
    "inherited": ("inherited", "not_evaluated", "unreviewed", "present"),
    "confirmed_absent": ("imported", "no_supported_value", "human_confirmed", "confirmed_absent"),
    "human_confirmed_absent": ("human", "no_supported_value", "human_confirmed", "confirmed_absent"),
    "unresolved": ("model", "no_supported_value", "unreviewed", "unresolved"),
    "invalid": ("model", "evaluation_failed", "unreviewed", "invalid"),
}

_NON_ASSERTION_FIELDS = {
    "record_id", "record_revision", "source_document_id", "source_asset_id",
    "source_spans", "source_units", "source_unit_ids", "source_block_ids",
    "source_extracted_text", "text", "text_length", "page_start", "page_end",
    "pdf_file", "pdf_page", "pdf_pages", "inline_citation", "full_citation",
    "accepted", "rejected", "review_disposition", "review_state", "needs_review",
    "review_reason", "metadata_complete", "metadata_incomplete_fields",
    "metadata_review_fields", "metadata_attention_reasons", "metadata_needs_attention",
    "metadata_stage_status", "metadata_execution_ledger", "metadata_decisions",
    "metadata_enrichment_state", "metadata_enrichment_history", "metadata_disputes",
    "human_touched_fields", "human_touched_at", "activity", "updates",
    "review_events", "source_quality_issues", "resolved_source_quality_issues",
    "text_noise", "can_accept", "build_id", "publication_id", "app_version",
    "schema_version", "profile_id", "profile_version", "provider_profile_id",
    "provider", "model", "document_prompt_version", "segmentation_prompt_version",
    "metadata_prompt_version", "record_sizing_policy", "topology_quality",
    "topology_index", "topology_count", "boundary_review", "boundary_suspicion",
    "corpus_build_details", "schema", "schema_id", "schema_hash", "schema_name",
    "human_touched_revision", "accepted_by", "autonomous_decision",
    "editorial_memory_used", "metadata_adjudication_prefills", "llm_rejections",
    "metadata_enrichment_finished", "metadata_requeue_requested",
    "metadata_requeue_reason", "metadata_reviewed_at", "review_issue_codes",
    "acceptance_blocking_fields", "slice_lineage", "boundary_quality_issues",
    "text_cleanup_status", "text_cleanup_report", "text_touchup_proposal",
    "field_assertion_errors",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def field_identity(field_name: str, schema: Any | None = None) -> str:
    """Resolve a stable field identity without requiring a mutable schema."""
    name = str(field_name or "").strip()
    if schema is not None:
        try:
            compatibility_id = schema.semantic_compatibility_id(name)
            if compatibility_id:
                return str(compatibility_id)
        except AttributeError:
            pass
        try:
            return str(schema.field_id(name))
        except (AttributeError, KeyError):
            pass
    if name in {"region_type", "primary_text", "discourse_role"}:
        return f"core.{name}"
    return f"legacy.{uuid.uuid5(uuid.NAMESPACE_URL, 'derridai:field:' + name)}"


class FieldAssertion(BaseModel):
    """One value assertion with independent derivation, evaluation and authority."""

    model_config = ConfigDict(extra="forbid")

    assertion_id: str = Field(default_factory=lambda: f"assertion-{uuid.uuid4().hex}")
    record_id: str
    record_revision: int | None = Field(default=None, ge=1)
    field_id: str
    field_name: str | None = None
    value: Any = None
    derivation_method: DerivationMethod
    evaluation_status: EvaluationStatus
    authority_status: AuthorityStatus = "unreviewed"
    value_status: ValueStatus = "present"
    method: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    calibration: dict[str, Any] | None = None
    reason: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    actor: str | None = None
    model: str | None = None
    run_id: str | None = None
    schema_id: str | None = None
    schema_version: str | None = None
    supersedes_assertion_id: str | None = None
    created_at: str = Field(default_factory=_now)

    @model_validator(mode="after")
    def _valid_state(self) -> FieldAssertion:
        if self.evaluation_status == "not_evaluated" and self.confidence is not None:
            raise ValueError("not_evaluated assertions must not carry confidence")
        if self.value_status == "confirmed_absent" and self.value not in (None, "", []):
            raise ValueError("confirmed_absent assertions cannot carry a value")
        if self.evaluation_status == "evaluation_failed" and self.value_status == "confirmed_absent":
            raise ValueError("evaluation_failed cannot establish confirmed absence")
        if self.value_status == "present" and self.value in (None, "", []):
            raise ValueError("present assertions require a value")
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        # Omission means the field was not evaluated; evaluated-but-unknown is
        # intentionally serialized as JSON null.
        if self.evaluation_status == "not_evaluated":
            data.pop("confidence", None)
        return data


def assertion_from_dict(value: Any) -> FieldAssertion:
    if isinstance(value, FieldAssertion):
        return value
    if not isinstance(value, dict):
        raise ValueError("A field assertion must be an object.")
    return FieldAssertion.model_validate(value)


def _assertions(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    value = record.get("field_assertions")
    if not isinstance(value, dict):
        value = {}
        record["field_assertions"] = value
    return value


def get_assertions(record: dict[str, Any], field_id: str) -> list[FieldAssertion]:
    result: list[FieldAssertion] = []
    for item in _assertions(record).get(field_id, []):
        try:
            result.append(assertion_from_dict(item))
        except ValueError:
            continue
    return result


def current_assertion(record: dict[str, Any], field_id: str) -> FieldAssertion | None:
    selected = record.get("current_field_assertions")
    selected_id = selected.get(field_id) if isinstance(selected, dict) else None
    values = get_assertions(record, field_id)
    if selected_id:
        for item in values:
            if item.assertion_id == selected_id:
                return item
    return values[-1] if values else None


def current_assertion_by_name(record: dict[str, Any], field_name: str) -> FieldAssertion | None:
    """Return the selected assertion for a field regardless of schema identity."""
    selected = record.get("current_field_assertions")
    if isinstance(selected, dict):
        for field_id, assertion_id in reversed(list(selected.items())):
            for assertion in get_assertions(record, field_id):
                if assertion.assertion_id == assertion_id and assertion.field_name == field_name:
                    return assertion
    for field_id, values in _assertions(record).items():
        current = current_assertion(record, field_id)
        if current is not None and current.field_name == field_name:
            return current
    return None


def _same_assertion(existing: FieldAssertion, candidate: FieldAssertion) -> bool:
    return (
        existing.record_id == candidate.record_id
        and existing.field_id == candidate.field_id
        and existing.value_status == candidate.value_status
        and existing.value == candidate.value
        and existing.derivation_method == candidate.derivation_method
        and existing.authority_status == candidate.authority_status
        and existing.evaluation_status == candidate.evaluation_status
        and existing.supersedes_assertion_id == candidate.supersedes_assertion_id
        and existing.confidence == candidate.confidence
        and existing.reason == candidate.reason
        and existing.evidence == candidate.evidence
    )


def store_assertion(record: dict[str, Any], assertion: FieldAssertion, *, select: bool = True) -> FieldAssertion:
    """Persist one assertion idempotently and optionally select it as current."""
    buckets = _assertions(record)
    values = buckets.setdefault(assertion.field_id, [])
    existing = [assertion_from_dict(item) for item in values if isinstance(item, dict)]
    for item in existing:
        if item.assertion_id == assertion.assertion_id or _same_assertion(item, assertion):
            assertion = item
            break
    else:
        values.append(assertion.model_dump(mode="json"))
    if select:
        current = record.setdefault("current_field_assertions", {})
        current[assertion.field_id] = assertion.assertion_id
    return assertion


def _new_assertion(
    record: dict[str, Any],
    *,
    field_name: str,
    schema: Any | None,
    value: Any,
    derivation_method: DerivationMethod,
    evaluation_status: EvaluationStatus,
    authority_status: AuthorityStatus = "unreviewed",
    value_status: ValueStatus = "present",
    select: bool = True,
    **kwargs: Any,
) -> FieldAssertion:
    return store_assertion(
        record,
        FieldAssertion(
            record_id=str(record.get("record_id") or ""),
            record_revision=int(record.get("record_revision") or 1),
            field_id=field_identity(field_name, schema),
            field_name=field_name,
            value=value,
            derivation_method=derivation_method,
            evaluation_status=evaluation_status,
            authority_status=authority_status,
            value_status=value_status,
            **kwargs,
        ),
        select=select,
    )


def create_deterministic_assertion(record: dict[str, Any], field_name: str, value: Any, *, schema: Any | None = None, method: str, reason: str = "", confidence: float | None = 1.0) -> FieldAssertion:
    present = value not in (None, "", [])
    return _new_assertion(
        record,
        field_name=field_name,
        schema=schema,
        value=value,
        derivation_method="deterministic",
        evaluation_status="value_supported" if present else "no_supported_value",
        value_status="present" if present else "unresolved",
        method=method,
        reason=reason,
        confidence=confidence if present else None,
    )


def create_inherited_assertion(record: dict[str, Any], field_name: str, value: Any, *, schema: Any | None = None, method: str = "manifest_inheritance", reason: str = "") -> FieldAssertion:
    present = value not in (None, "", [])
    return _new_assertion(
        record,
        field_name=field_name,
        schema=schema,
        value=value,
        derivation_method="inherited",
        evaluation_status="not_evaluated",
        value_status="present" if present else "unresolved",
        method=method,
        reason=reason,
        confidence=None,
    )


def create_model_assertion(
    record: dict[str, Any],
    field_name: str,
    value: Any,
    *,
    schema: Any | None = None,
    outcome: str = "supported_value",
    confidence: float | None = None,
    method: str = "llm",
    reason: str = "",
    evidence: list[dict[str, Any]] | None = None,
    model: str | None = None,
    run_id: str | None = None,
    schema_id: str | None = None,
    schema_version: str | None = None,
    select: bool = True,
) -> FieldAssertion:
    evaluation: EvaluationStatus = {
        "supported_value": "value_supported",
        "no_supported_value": "no_supported_value",
        "uncertain": "value_supported" if value not in (None, "", []) else "no_supported_value",
        "evaluation_failed": "evaluation_failed",
    }.get(str(outcome), "evaluation_failed")  # type: ignore[assignment]
    status: ValueStatus = "present" if value not in (None, "", []) else "unresolved"
    if evaluation == "evaluation_failed":
        status = "invalid" if value not in (None, "", []) else "unresolved"
    return _new_assertion(
        record, field_name=field_name, schema=schema, value=value,
        derivation_method="model", evaluation_status=evaluation,
        value_status=status, method=method, confidence=confidence, reason=reason,
        evidence=evidence or [], model=model, run_id=run_id, schema_id=schema_id,
        schema_version=schema_version, select=select,
    )


def confirm_assertion(record: dict[str, Any], assertion: FieldAssertion, *, actor: str | None = None, reason: str = "") -> FieldAssertion:
    return store_assertion(
        record,
        assertion.model_copy(update={
            "assertion_id": f"assertion-{uuid.uuid4().hex}",
            "authority_status": "human_confirmed",
            "actor": actor,
            "reason": reason or assertion.reason,
            "record_revision": int(record.get("record_revision") or assertion.record_revision or 1),
            "supersedes_assertion_id": assertion.assertion_id,
            "created_at": _now(),
        }),
    )


def override_assertion(record: dict[str, Any], field_name: str, value: Any, *, schema: Any | None = None, supersedes: FieldAssertion | None = None, actor: str | None = None, reason: str = "") -> FieldAssertion:
    return _new_assertion(
        record, field_name=field_name, schema=schema, value=value,
        derivation_method="human", evaluation_status="value_supported",
        authority_status="human_override", method="human_review", actor=actor,
        reason=reason or "Human record-level override.",
        supersedes_assertion_id=supersedes.assertion_id if supersedes else None,
    )


def confirm_absence(record: dict[str, Any], field_name: str, *, schema: Any | None = None, prior: FieldAssertion | None = None, actor: str | None = None, reason: str = "") -> FieldAssertion:
    derivation: DerivationMethod = prior.derivation_method if prior and prior.derivation_method == "model" else "human"
    return _new_assertion(
        record, field_name=field_name, schema=schema, value=None,
        derivation_method=derivation, evaluation_status="no_supported_value",
        authority_status="human_confirmed", value_status="confirmed_absent",
        method="human_review", actor=actor,
        reason=reason or "Reviewer confirmed that no supported value applies.",
        supersedes_assertion_id=prior.assertion_id if prior else None,
    )


def reopen_assertion(record: dict[str, Any], assertion: FieldAssertion, *, actor: str | None = None, reason: str = "") -> FieldAssertion:
    return store_assertion(record, assertion.model_copy(update={
        "assertion_id": f"assertion-{uuid.uuid4().hex}",
        "authority_status": "disputed",
        "value_status": "unresolved",
        "actor": actor,
        "reason": reason or "Reopened for review.",
        "supersedes_assertion_id": assertion.assertion_id,
        "created_at": _now(),
    }))


def invalidate_assertion(record: dict[str, Any], assertion: FieldAssertion, *, actor: str | None = None, reason: str = "") -> FieldAssertion:
    return store_assertion(record, assertion.model_copy(update={
        "assertion_id": f"assertion-{uuid.uuid4().hex}",
        "authority_status": "disputed",
        "value_status": "invalid",
        "actor": actor,
        "reason": reason or "Assertion failed validation.",
        "supersedes_assertion_id": assertion.assertion_id,
        "created_at": _now(),
    }))


def _compatibility_status(assertion: FieldAssertion) -> str:
    if assertion.value_status == "confirmed_absent":
        return "confirmed_absent"
    if assertion.value_status == "invalid":
        return "invalid"
    if assertion.value_status == "unresolved" or assertion.evaluation_status == "evaluation_failed":
        return "unresolved"
    if assertion.authority_status == "human_override":
        return "human_override"
    if assertion.authority_status == "human_confirmed":
        return "human_confirmed"
    if assertion.derivation_method == "model":
        return "model_inferred"
    if assertion.derivation_method == "deterministic":
        return "deterministic"
    if assertion.derivation_method == "inherited":
        return "inherited"
    return "unresolved"


def project_record_assertions(record: dict[str, Any]) -> dict[str, Any]:
    """Materialize current values and compatibility views from assertions."""
    status_map: dict[str, Any] = {}
    evidence_map: dict[str, Any] = {}
    for field_id, raw_values in _assertions(record).items():
        current = current_assertion(record, field_id)
        if current is None or not current.field_name:
            continue
        if current.value_status == "confirmed_absent":
            record[current.field_name] = None
        elif current.value_status == "present":
            record[current.field_name] = copy.deepcopy(current.value)
        status = {
            "status": _compatibility_status(current),
            "method": current.method or current.derivation_method,
            "reason": current.reason,
            "confidence": current.confidence,
            "assertion_id": current.assertion_id,
            "field_id": current.field_id,
            "derivation_method": current.derivation_method,
            "evaluation_status": current.evaluation_status,
            "authority_status": current.authority_status,
            "value_status": current.value_status,
        }
        if current.evaluation_status == "not_evaluated":
            status.pop("confidence", None)
        status_map[current.field_name] = status
        if current.evidence:
            evidence_map[current.field_name] = copy.deepcopy(current.evidence[0] if len(current.evidence) == 1 else {"spans": current.evidence})
    if status_map:
        prior_status = record.get("metadata_field_status")
        if isinstance(prior_status, dict):
            for field, status in status_map.items():
                prior = prior_status.get(field)
                if isinstance(prior, dict):
                    for key, value in prior.items():
                        if key not in status and key not in {"status", "method", "confidence", "reason"}:
                            status[key] = value
        record["metadata_field_status"] = status_map
    if evidence_map:
        record["metadata_evidence"] = evidence_map
    return record


def _legacy_assertion(
    record: dict[str, Any],
    field_name: str,
    value: Any,
    status: dict[str, Any],
    *,
    schema: Any | None,
    evidence: Any,
) -> FieldAssertion | None:
    token = str(status.get("status") or "").strip()
    if not token and value in (None, "", []):
        return None
    derivation, evaluation, authority, value_status = _STATUS_TO_CANONICAL.get(
        token,
        ("imported", "not_evaluated", "unreviewed", "present" if value not in (None, "", []) else "unresolved"),
    )
    if token == "unresolved":
        evaluation = "value_supported" if value not in (None, "", []) else "no_supported_value"
    if token == "invalid":
        evaluation = "evaluation_failed" if str(status.get("reason_code") or "") in {"invalid_value", "validation_failed"} else "value_supported"
    if token == "human_confirmed" and str(status.get("method") or "").casefold() not in {"llm", "human_review_of_llm_proposal", "human_adjudication_cache"}:
        derivation = "human" if str(status.get("method") or "").casefold().startswith("human") else "imported"
    if token == "confirmed_absent" and str(status.get("method") or "").casefold() in {"human", "human_review"}:
        derivation = "human"
    if value in (None, "", []) and value_status == "present":
        value_status = "unresolved"
        evaluation = "no_supported_value"
    if value_status == "confirmed_absent":
        value = None
    raw_evidence = evidence if isinstance(evidence, list) else [evidence] if isinstance(evidence, dict) else []
    candidate = FieldAssertion(
        assertion_id=f"assertion-{uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([record.get('record_id'), record.get('record_revision'), field_identity(field_name, schema), token, value, status, raw_evidence], default=str, sort_keys=True)).hex}",
        record_id=str(record.get("record_id") or ""),
        record_revision=int(record.get("record_revision") or 1),
        field_id=field_identity(field_name, schema),
        field_name=field_name,
        value=value,
        derivation_method=derivation,  # type: ignore[arg-type]
        evaluation_status=evaluation,  # type: ignore[arg-type]
        authority_status=authority,  # type: ignore[arg-type]
        value_status=value_status,  # type: ignore[arg-type]
        method=str(status.get("method") or "") or None,
        confidence=status.get("confidence") if isinstance(status.get("confidence"), (int, float)) else None,
        reason=str(status.get("reason") or status.get("reason_code") or "Migrated from legacy metadata state."),
        evidence=[item for item in raw_evidence if isinstance(item, dict)],
        actor=status.get("actor"),
        model=status.get("model"),
        run_id=status.get("run_id"),
        schema_id=str(getattr(schema, "id", "") or "") or None,
        schema_version=str(getattr(schema, "schema_version", "") or "") or None,
    )
    return candidate


def migrate_record_assertions(record: dict[str, Any], schema: Any | None = None) -> dict[str, Any]:
    """Idempotently convert legacy metadata fields/status/evidence into assertions."""
    assertions = _assertions(record)
    if assertions:
        # Normalize any hand-written assertion dictionaries and ensure a
        # current selector exists; do not duplicate already migrated state.
        normalized: dict[str, list[dict[str, Any]]] = {}
        for field_id, values in assertions.items():
            for value in values if isinstance(values, list) else []:
                try:
                    item = assertion_from_dict(value)
                except ValueError as exc:
                    errors = record.setdefault("field_assertion_errors", [])
                    if isinstance(errors, list):
                        errors.append(str(exc))
                    continue
                normalized.setdefault(field_id, []).append(item.model_dump(mode="json"))
        record["field_assertions"] = normalized
        current = record.setdefault("current_field_assertions", {})
        for field_id in normalized:
            if not current.get(field_id) or not any(item["assertion_id"] == current[field_id] for item in normalized[field_id]):
                current[field_id] = normalized[field_id][-1]["assertion_id"]
    statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
    evidence_map = record.get("metadata_evidence") if isinstance(record.get("metadata_evidence"), dict) else {}
    names = set(statuses) | {
        key for key in record
        if key not in _NON_ASSERTION_FIELDS and not key.startswith("_")
        and key not in {"field_assertions", "current_field_assertions", "metadata_field_status", "metadata_evidence"}
    }
    if schema is not None:
        try:
            names.update(schema.field_names())
        except AttributeError:
            pass
    for name in sorted(str(item) for item in names):
        if not name or name in _NON_ASSERTION_FIELDS:
            continue
        field_id = field_identity(name, schema)
        status = statuses.get(name) if isinstance(statuses.get(name), dict) else {}
        value = record.get(name)
        assertion = _legacy_assertion(record, name, value, status, schema=schema, evidence=evidence_map.get(name))
        current = current_assertion(record, field_id)
        if assertion is not None and (
            current is None
            or (
                current.record_revision != int(record.get("record_revision") or 1)
                or
                str(status.get("status") or "") not in {"", _compatibility_status(current)}
                or (current.value_status == "present" and current.value != value)
                or (current.value_status == "confirmed_absent" and value is not None)
                or (assertion.evidence != current.evidence)
            )
        ):
            if current is not None and (
                current.record_revision != int(record.get("record_revision") or 1)
                or str(status.get("status") or "") in {
                "human_confirmed", "human_override", "confirmed_absent", "human_confirmed_absent",
                }
            ):
                assertion = assertion.model_copy(update={"supersedes_assertion_id": current.assertion_id})
            store_assertion(record, assertion)
    return project_record_assertions(record)


def confirm_model_assertions(record: dict[str, Any], schema: Any | None = None, *, actor: str | None = None) -> int:
    """Confirm current model candidates without changing their derivation."""
    migrate_record_assertions(record, schema)
    changed = 0
    for field_id in list(record.get("current_field_assertions") or {}):
        assertion = current_assertion(record, field_id)
        if assertion and assertion.derivation_method == "model" and assertion.authority_status == "unreviewed":
            confirm_assertion(record, assertion, actor=actor, reason="Confirmed when the reviewer accepted the record.")
            changed += 1
    return changed


def validate_projection(record: dict[str, Any]) -> list[str]:
    """Detect drift between canonical assertions and compatibility projections."""
    errors: list[str] = []
    for field_id in _assertions(record):
        assertion = current_assertion(record, field_id)
        if assertion is None or not assertion.field_name:
            continue
        if assertion.value_status == "present":
            expected = assertion.value
        elif assertion.value_status == "confirmed_absent":
            expected = None
        else:
            expected = record.get(assertion.field_name)
        if record.get(assertion.field_name) != expected:
            errors.append(f"{assertion.field_name}: materialized value differs from current assertion")
        status = (record.get("metadata_field_status") or {}).get(assertion.field_name)
        if isinstance(status, dict) and status.get("assertion_id") not in {None, assertion.assertion_id}:
            errors.append(f"{assertion.field_name}: metadata_field_status points at another assertion")
    return errors


def migrate_records(records: list[dict[str, Any]], schema: Any | None = None) -> dict[str, Any]:
    """Migrate an in-memory corpus and return counts suitable for dry-run reports."""
    report = {"records": len(records), "migrated": 0, "assertions": 0, "ambiguous": 0, "errors": []}
    for record in records:
        before = bool(record.get("field_assertions"))
        migrate_record_assertions(record, schema)
        if not before:
            report["migrated"] += 1
        report["assertions"] += sum(len(values) for values in (record.get("field_assertions") or {}).values())
        report["ambiguous"] += sum(
            1 for status in (record.get("metadata_field_status") or {}).values()
            if isinstance(status, dict) and status.get("status") in {"unresolved", "invalid"}
        )
        report["errors"].extend(validate_projection(record))
    return report
