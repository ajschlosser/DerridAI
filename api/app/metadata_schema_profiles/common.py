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

"""Shared helpers for built-in domain metadata schema profiles."""

from __future__ import annotations

from typing import Any

from ..metadata_schema import (
    SEMANTIC_COMPATIBILITY_IDS,
    FieldScope,
    FieldType,
    SchemaField,
    SchemaValue,
)

PROFILE_FOOTER = (
    "For every populated field in this group, include field_evidence using only "
    "current-record source block IDs, confidence 0..1, and a short reason. "
    "Use null or [] when the source does not support a value.\n"
    "Return one field_assessments entry for every one of {assessed_fields}, even "
    "when the corresponding metadata value is null or empty. Each assessment "
    "must contain confidence (0..1 or null), needs_review, reason, and outcome. "
    "Boolean assessments must also contain assessed_value exactly matching the metadata value. "
    "Use outcome=\"supported_value\" for a supported value, "
    "outcome=\"no_supported_value\" when the source supports that no value applies, "
    "and outcome=\"uncertain\" when the field cannot be determined. Preserve "
    "ambiguity rather than inventing specificity.\n"
    "Keep metadata and assessment structurally consistent: supported_value requires "
    "a non-empty metadata value (or false for a supported boolean); no_supported_value "
    "requires null or []; uncertain requires needs_review=true and may retain a tentative "
    "proposal. Linguistic and document-intelligence candidates are attention cues only, "
    "not candidate metadata values: inspect the source text and never copy a candidate "
    "list into metadata merely because it was provided as a hint."
)


def values(items: dict[str, str] | list[str]) -> list[SchemaValue]:
    """Turn a compact built-in vocabulary declaration into schema values."""

    if isinstance(items, dict):
        return [
            SchemaValue(value=value, definition=definition)
            for value, definition in items.items()
        ]
    return [SchemaValue(value=value) for value in items]


def profile_field(
    profile: str,
    name: str,
    label: str,
    type_: FieldType,
    group: str,
    instruction: str,
    *,
    allowed_values: dict[str, str] | list[str] | None = None,
    strict: bool = False,
    scope: FieldScope = "record",
    pos_tags: tuple[str, ...] = (),
    ner_tags: tuple[str, ...] = (),
    semantic_compatibility_id: str | None = None,
    review: bool = False,
    **extra: Any,
) -> SchemaField:
    """Create one evidence-bound, assessed built-in profile field.

    Profile fields deliberately use namespaced stable identities. Runtime code
    remains schema-driven: these names have no special behavior outside the
    metadata contract itself.
    """

    return SchemaField(
        field_id=f"derridai.profile.{profile}.{name}",
        name=name,
        label=label,
        type=type_,
        group=group,
        role="scholarly",
        review_visibility="primary",
        scope=scope,
        values=values(allowed_values or []),
        strict=strict,
        instruction=instruction,
        evidence=True,
        assess=True,
        review=review,
        pos_tags=list(pos_tags),
        ner_tags=list(ner_tags),
        semantic_compatibility_id=(
            semantic_compatibility_id
            if semantic_compatibility_id is not None
            else SEMANTIC_COMPATIBILITY_IDS.get(name)
        ),
        **extra,
    )
