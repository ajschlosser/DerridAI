# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright Â© 2026  Aaron John Schlosser, PhD
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

"""Indexed field inventory across every Record/schema in Research collections.

Read metadata in pages, never documents. Values are bounded; field discovery is
complete even when value suggestions are truncated. Composite values retain the
exact Chroma JSON encoding: equality means equality of the complete value.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from .chroma_store import decode_metadata
from .corpus_publication import serialize_public_record
from .field_assertions import current_assertions
from .metadata_schema import DOCUMENT_FIELDS

VALUE_LIMIT = 100
PAGE_SIZE = 500
_EXCLUDED = {"text", "source_extracted_text", "source_spans", "source_units", "field_assertions",
             "field_assertion_errors", "current_field_assertions", "annotations", "updates", "provenance_warnings", "password", "api_key", "session_token", "access_token", "credentials"}


def indexed_filter_inventory(collections: list[Any]) -> dict[str, Any]:
    fields: dict[str, dict[str, Any]] = {}
    works: dict[str, set[str]] = {}
    for collection in collections:
        offset = 0
        while True:
            page = collection.get(include=["metadatas"], limit=PAGE_SIZE, offset=offset)
            rows = page.get("metadatas") or []
            if not rows:
                break
            for raw in rows:
                raw = raw or {}
                record = decode_metadata(raw)
                public = serialize_public_record(copy.deepcopy(record))
                work = str(record.get("work") or "").strip()
                if work:
                    authors = works.setdefault(work, set())
                    author = str(record.get("document_author") or "").strip()
                    if author:
                        authors.add(author)
                identities: dict[str, list[Any]] = {}
                for assertion in current_assertions(record) or current_assertions(public):
                    if assertion.field_name:
                        identities.setdefault(assertion.field_name, []).append(assertion)
                for key in public.keys() & raw.keys() - _EXCLUDED:
                    value = raw[key]
                    if not isinstance(value, (str, int, float, bool)) or key.startswith("_"):
                        continue
                    value_type = "boolean" if isinstance(value, bool) else "number" if isinstance(value, (int, float)) else "string"
                    slot = fields.setdefault(key, {"key": key, "types": set(), "values": {},
                        "values_truncated": False, "schema_ids": set(), "field_ids": set(), "works": set(), "encoding": "scalar"})
                    slot["types"].add(value_type)
                    # Historical publication projections remain a compatibility boundary.
                    identity = DOCUMENT_FIELDS.get(key) or {"document_language": "derridai.document.language", "year": "derridai.document.publication_year"}.get(key)
                    if identity:
                        slot["field_ids"].add(identity)
                    if isinstance(record.get(key), (dict, list)):
                        slot["encoding"] = "json"
                    if work:
                        slot["works"].add(work)
                    for assertion in identities.get(key, []):
                        slot["field_ids"].add(assertion.field_id)
                        if assertion.schema_id:
                            slot["schema_ids"].add(assertion.schema_id)
                    token = json.dumps(value, ensure_ascii=False)
                    if token not in slot["values"]:
                        if len(slot["values"]) < VALUE_LIMIT and len(token) <= 512:
                            slot["values"][token] = value
                        else:
                            slot["values_truncated"] = True
            offset += len(rows)
            if len(rows) < PAGE_SIZE:
                break
    catalog = []
    for key, slot in sorted(fields.items()):
        kinds = slot.pop("types")
        slot["type"] = next(iter(kinds)) if len(kinds) == 1 else "any"
        slot["values"] = list(slot["values"].values())
        for name in ("schema_ids", "field_ids", "works"):
            slot[name] = sorted(slot[name])
        catalog.append(slot)
    return {"fields": catalog, "works": [{"work": key, "authors": sorted(value)} for key, value in sorted(works.items())], "truncated": False}


def validate_catalog_filter(node: Any, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = {field["key"]: field for field in catalog}
    errors = []
    def walk(part: Any) -> None:
        if not part:
            return
        key, operand = next(iter(part.items()))
        if key in {"$and", "$or"}:
            for child in operand:
                walk(child)
            return
        field = fields.get(key)
        if field is None:
            errors.append({"code": "unknown_field", "params": {"field": key}})
            return
        op, value = next(iter(operand.items())) if isinstance(operand, dict) else ("$eq", operand)
        values = value if isinstance(value, list) else [value]
        kind = field["type"]
        for scalar in values:
            actual = "boolean" if isinstance(scalar, bool) else "number" if isinstance(scalar, (int, float)) else "string"
            if kind != "any" and kind != actual:
                errors.append({"code": "invalid_filter", "params": {"message": f"{key} requires {kind} values"}})
                break
        if field.get("encoding") == "json" and op not in {"$eq", "$ne", "$in", "$nin"}:
            errors.append({"code": "invalid_filter", "params": {"message": f"{key} supports exact whole-value equality only"}})
    walk(node)
    return errors
