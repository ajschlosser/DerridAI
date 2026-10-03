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

"""Deterministic cELF Core and Publication conformance projections."""

from __future__ import annotations

from typing import Any

from .corpus_publication import serialize_public_record, validate_publication_record
from .field_assertions import current_assertions

_SOURCE_INTEGRITY_KEYS = (
    "missing_block_ids",
    "duplicate_block_ids",
    "text_fidelity_errors",
    "source_order_errors",
)


def _status(blockers: list[dict[str, Any]]) -> str:
    return "conformant" if not blockers else "non_conformant"


def evaluate_celf_conformance(
    build: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the cELF profiles supported by the publication contract.

    Human review is deliberately absent from this evaluator. Review provenance is
    reported by publication metadata; cELF conformance is derived from identity,
    source, structural, and integrity requirements instead.
    """
    normalized_records = [serialize_public_record(record) for record in records]
    core: list[dict[str, Any]] = []
    validation = build.get("validation") if isinstance(build.get("validation"), dict) else {}
    for key in _SOURCE_INTEGRITY_KEYS:
        values = validation.get(key)
        if values:
            core.append({"code": f"source_{key}", "detail": values})
    for record in normalized_records:
        record_id = str(record.get("record_id") or "")
        if not record_id:
            core.append({"code": "missing_record_id", "record_id": record_id})
        if not str(record.get("source_document_id") or "").strip():
            core.append({"code": "missing_source_document_id", "record_id": record_id})
        spans = record.get("source_spans")
        if not isinstance(spans, list) or not spans:
            core.append({"code": "missing_source_spans", "record_id": record_id})
            continue
        source_id = str(record.get("source_document_id") or "")
        for span in spans:
            if not isinstance(span, dict) or str(span.get("source_document_id") or source_id) != source_id:
                core.append({"code": "source_span_document_mismatch", "record_id": record_id})
    # Repeatable scholarly values are conformant only when every projected member
    # has its own stable, independently recoverable assertion target.
    for source_record in records:
        record_id = str(source_record.get("record_id") or "")
        member_assertions = {
            (
                assertion.field_name,
                assertion.instance_id,
                assertion.member_name,
            )
            for assertion in current_assertions(source_record)
            if assertion.container_field_id
            and assertion.instance_id
            and assertion.member_field_id
            and assertion.member_name
            and assertion.value_status == "present"
        }
        for field_name, value in source_record.items():
            if not isinstance(value, list) or not value or not all(isinstance(row, dict) for row in value):
                continue
            if not all("instance_id" in row for row in value):
                continue
            instance_ids = [str(row.get("instance_id") or "") for row in value]
            if any(not instance_id for instance_id in instance_ids) or len(instance_ids) != len(set(instance_ids)):
                core.append({
                    "code": "repeatable_instance_identity_invalid",
                    "record_id": record_id,
                    "field": field_name,
                })
                continue
            for row in value:
                instance_id = str(row["instance_id"])
                for member_name, member_value in row.items():
                    if member_name == "instance_id" or member_value in (None, "", []):
                        continue
                    if (field_name, instance_id, member_name) not in member_assertions:
                        core.append({
                            "code": "repeatable_member_assertion_missing",
                            "record_id": record_id,
                            "field": field_name,
                            "instance_id": instance_id,
                            "member": member_name,
                        })
    publication: list[dict[str, Any]] = []
    for record in normalized_records:
        for error in validate_publication_record(record):
            publication.append({"code": "publication_record_invalid", "record_id": record.get("record_id"), "detail": error})
    if not normalized_records:
        publication.append({"code": "empty_publication"})
    core_status = _status(core)
    publication_status = _status(publication) if not core else "non_conformant"
    return {
        "spec_version": "1.0",
        "core": {"status": core_status, "blockers": core},
        "publication": {
            "status": publication_status,
            "blockers": publication,
        },
        "conformant": core_status == "conformant" and publication_status == "conformant",
    }
