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

"""Record-local contributions shared by full validation and incremental queue projection."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .corpus_review_state import _metadata_enrichment_finished
from .corpus_reviewer_helpers import _metadata_issue_type_for_field
from .field_assertions import current_assertion_by_name


def record_review_aggregate(record: dict[str, Any], automation_running: bool) -> dict[str, Any]:
    issue_rows: list[dict[str, Any]] = []
    by_field: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    invalid_by_field: Counter[str] = Counter()
    incomplete: list[str] = []
    retryable_types = {"not_run", "llm_failed", "evidence_failed", "invalid_value", "unresolved"}
    contribution: Counter[str] = Counter()
    llm_elapsed_ms = 0
    llm_family_calls = 0
    rejected = str(record.get("review_disposition") or "") == "rejected" or bool(record.get("rejected"))
    if not rejected and not (automation_running and not _metadata_enrichment_finished(record)):
        incomplete = list(dict.fromkeys([
            str(value) for value in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])
        ]))
        statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        for field in incomplete:
            by_field[field] += 1
            status_info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
            assertion = current_assertion_by_name(record, field)
            if assertion is not None and assertion.value_status == "invalid":
                invalid_by_field[field] += 1
            issue_type = _metadata_issue_type_for_field(record, field)
            by_reason[issue_type] += 1
            issue_rows.append({
                "record_id": record.get("record_id"), "field": field,
                "issue_type": issue_type, "retryable": issue_type in retryable_types,
                "status": status_info.get("status") or "unresolved",
                "reason": status_info.get("reason") or "", "method": status_info.get("method") or "",
                "confidence": status_info.get("confidence"), "current_value": record.get(field),
                "page_start": record.get("page_start"), "page_end": record.get("page_end"),
            })
    status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
    for field, info in status_map.items():
        if not isinstance(info, dict):
            continue
        assertion = current_assertion_by_name(record, str(field))
        if assertion is None:
            continue
        if assertion.authority_status in {"human_confirmed", "human_override"}:
            contribution["human_fields"] += 1
        elif assertion.derivation_method == "inherited":
            contribution["inherited_fields"] += 1
        elif assertion.derivation_method == "deterministic":
            contribution["deterministic_fields"] += 1
        elif assertion.derivation_method == "model":
            if assertion.value_status == "present" and assertion.evaluation_status != "evaluation_failed":
                contribution["llm_fields_usable"] += 1
            if assertion.value_status in {"unresolved", "invalid"} or assertion.evaluation_status == "evaluation_failed":
                contribution["llm_fields_review"] += 1
                if info.get("proposed_value") not in (None, "", []):
                    contribution["llm_fields_proposed"] += 1
    ledger = record.get("metadata_execution_ledger") if isinstance(record.get("metadata_execution_ledger"), dict) else {}
    for family in ("discourse", "quotation", "indexing"):
        entry = ledger.get(family) if isinstance(ledger.get(family), dict) else {}
        state = str(entry.get("state") or "")
        if state in {"complete", "failed"}:
            llm_family_calls += 1
        try:
            llm_elapsed_ms += int(entry.get("elapsed_ms") or 0)
        except (TypeError, ValueError):
            pass
        contribution[f"tasks_{state or 'unknown'}"] += 1
    return {
        "incomplete": incomplete, "rows": issue_rows, "by_field": by_field, "by_reason": by_reason,
        "invalid_by_field": invalid_by_field, "contribution": contribution,
        "llm_elapsed_ms": llm_elapsed_ms, "llm_family_calls": llm_family_calls,
    }
