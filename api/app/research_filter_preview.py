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

"""Non-mutating diagnostics for a proposed Research filter plan.

The preview validates the same contract a Research run enforces
(`ResearchFilterPlan`), checks referenced fields against the selected
collection's declared filter fields, and returns a structured explanation.
It never reads source text, never scans the collection, and never changes state.
Diagnostics carry stable codes and parameters so the browser can localize them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from .models import ResearchFilterPlan
from .research_filters import metadata_filter_fields

_LOGICAL = {"$and": "and", "$or": "or"}


def _explain_metadata(node: Mapping[str, Any]) -> dict[str, Any]:
    key, operand = next(iter(node.items()))
    if key in _LOGICAL:
        return {
            "kind": "group",
            "operator": _LOGICAL[key],
            "children": [_explain_metadata(child) for child in operand],
        }
    if isinstance(operand, Mapping):
        operator, value = next(iter(operand.items()))
        return {"kind": "predicate", "field": key, "operator": operator, "value": value}
    return {"kind": "predicate", "field": key, "operator": "$eq", "value": operand}


def _explain_document(node: Mapping[str, Any]) -> dict[str, Any]:
    key, operand = next(iter(node.items()))
    if key in _LOGICAL:
        return {
            "kind": "group",
            "operator": _LOGICAL[key],
            "children": [_explain_document(child) for child in operand],
        }
    return {"kind": "document_predicate", "operator": key, "value": operand}


def _diagnostic(code: str, **params: Any) -> dict[str, Any]:
    return {"code": code, "params": params}


def preview_filter_plan(
    *,
    metadata_filter: Any,
    document_filter: Any,
    source: str,
    collection_filter_fields: list[str],
) -> dict[str, Any]:
    """Validate a proposed plan and describe it without executing retrieval."""

    declared = sorted({str(name) for name in collection_filter_fields})
    result: dict[str, Any] = {
        "valid": False,
        "plan": None,
        "fields_referenced": [],
        "collection_filter_fields": declared,
        "unsupported_fields": [],
        "errors": [],
        "warnings": [],
        "explanation": {"metadata": None, "document": None},
    }
    try:
        plan = ResearchFilterPlan(
            metadata_filter=metadata_filter,
            document_filter=document_filter,
            source=source,
        )
    except ValidationError as exc:
        for error in exc.errors():
            message = str(error.get("msg") or "").removeprefix("Value error, ")
            result["errors"].append(
                _diagnostic("invalid_filter", message=message, location=[str(p) for p in error.get("loc", ())])
            )
        return result

    referenced = sorted(metadata_filter_fields(plan.metadata_filter))
    result["fields_referenced"] = referenced
    if plan.metadata_filter is None and plan.document_filter is None:
        result["warnings"].append(_diagnostic("empty_filter"))
    if referenced and not declared:
        result["warnings"].append(_diagnostic("collection_declares_no_filter_fields"))
    elif declared:
        unsupported = [name for name in referenced if name not in declared]
        result["unsupported_fields"] = unsupported
        for name in unsupported:
            result["errors"].append(_diagnostic("unknown_field", field=name))

    if plan.metadata_filter:
        result["explanation"]["metadata"] = _explain_metadata(plan.metadata_filter)
    if plan.document_filter:
        result["explanation"]["document"] = _explain_document(plan.document_filter)
    result["plan"] = plan.model_dump(exclude={"original_text", "remaining_instructions"})
    result["valid"] = not result["errors"]
    return result
