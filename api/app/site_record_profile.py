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

"""Record metadata profiles for published research sites.

``complete`` publishes every public Record field, including FieldAssertions. ``reader`` publishes the same Record
values, with all semantic, attribution, quotation and indexing metadata, and leaves out only the FieldAssertion
layer (the per-field assertions with their evidence, reasoning and history), which is the bulk of a Record's size
and which a reading site does not use. Both are validated against the cELF Core Record requirements; ``reader``
deliberately omits the Scholarly Assertion layer, and the publication manifest says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .field_assertions import current_assertions

SITE_RECORD_PROFILES = ("complete", "reader")
DEFAULT_SITE_RECORD_PROFILE = "complete"

# cELF Core: a conforming Record MUST contain these (SPECIFICATION.md, "Record").
CELF_REQUIRED_RECORD_FIELDS = ("record_id", "source_document_id", "text", "source_spans")

# The FieldAssertion layer and its bookkeeping. This is all the reader profile removes; metadata values
# (semantic, attribution, quotation, indexing, bibliographic, and any project-defined fields) always stay.
ASSERTION_LAYER_FIELDS = frozenset(
    {"field_assertions", "current_field_assertions", "field_assertion_errors"}
)


def normalize_site_record_profile(value: str | None) -> str:
    profile = str(value or DEFAULT_SITE_RECORD_PROFILE).strip().lower()
    if profile not in SITE_RECORD_PROFILES:
        raise ValueError(f"Unsupported record metadata profile: {value!r}")
    return profile


def _field_authority(record: dict[str, Any], kept: Sequence[str]) -> dict[str, dict[str, str]]:
    """The derivation and review state of each kept field, in place of the full assertions.

    A reader-profile site has no FieldAssertions, but a value that a model proposed and nobody reviewed must not
    read as settled, so the state travels with the value in a few short strings.
    """
    kept_names = set(kept)
    summary: dict[str, dict[str, str]] = {}
    for assertion in current_assertions(record):
        name = assertion.field_name
        if not name or name not in kept_names:
            continue
        summary[name] = {
            "derivation": str(assertion.derivation_method),
            "evaluation": str(assertion.evaluation_status),
            "authority": str(assertion.authority_status),
        }
    return summary


def reader_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove the FieldAssertion layer from one public Record, keeping every metadata value."""
    slim = {key: value for key, value in record.items() if key not in ASSERTION_LAYER_FIELDS}
    authority = _field_authority(record, list(slim))
    if authority:
        slim["field_authority"] = authority
    return slim


def apply_record_profile(records: Sequence[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    if normalize_site_record_profile(profile) == "complete":
        return [dict(record) for record in records]
    return [reader_record(record) for record in records]


def celf_conformance(
    profile: str, original: Sequence[dict[str, Any]], published: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    """Describe, from the records actually published, what cELF layers the site carries.

    ``core_record`` is computed, not assumed: every published Record must still hold the required Core fields.
    """
    profile = normalize_site_record_profile(profile)
    core = all(
        all(record.get(field) not in (None, "", []) for field in CELF_REQUIRED_RECORD_FIELDS)
        for record in published
    )
    kept_assertions = any(record.get("field_assertions") for record in published)
    original_keys = set().union(*(set(record) for record in original)) if original else set()
    published_keys = set().union(*(set(record) for record in published)) if published else set()
    omitted = sorted(original_keys - published_keys)
    return {
        "specification": "cELF 1.0",
        "record_profile": profile,
        "core_record": bool(core),
        "required_record_fields": list(CELF_REQUIRED_RECORD_FIELDS),
        "field_assertions": "retained" if kept_assertions else "omitted",
        "omitted_fields": omitted,
    }
