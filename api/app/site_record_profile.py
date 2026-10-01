# Copyright 2026 Aaron John Schlosser, PhD.
"""Record metadata profiles for published research sites.

``complete`` publishes every public Record field, including FieldAssertions. ``reader`` publishes only what a
reading, searching and citing site uses, which makes the packaged corpus much smaller. Both are validated against
the cELF Core Record requirements; ``reader`` deliberately omits the Scholarly Assertion layer (FieldAssertions),
and the publication manifest says so.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from .corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS,
    HYBRID_REQUIRED_FIELDS,
    MANIFEST_INHERITED_FIELDS,
    METADATA_FAMILY_FIELDS,
)
from .field_assertions import current_assertions

SITE_RECORD_PROFILES = ("complete", "reader")
DEFAULT_SITE_RECORD_PROFILE = "complete"

# cELF Core: a conforming Record MUST contain these (SPECIFICATION.md, "Record").
CELF_REQUIRED_RECORD_FIELDS = ("record_id", "source_document_id", "text", "source_spans")

# Fields a reader needs to cite, locate and attribute a passage.
_LOCATION_FIELDS = {"page_start", "page_end", "printed_page", "page"}
_CITATION_FIELDS = {
    "citation",
    "editor",
    "container_title",
    "journal_title",
    "volume",
    "issue",
    "pages",
    "doi",
    "source_type",
    "language",
}
# Attribution is never flattened: speaker, quoted speaker and position holder stay separate fields.
_ATTRIBUTION_FIELDS = (
    set(ATTRIBUTION_EVIDENCE_FIELDS)
    | set(HYBRID_REQUIRED_FIELDS)
    | METADATA_FAMILY_FIELDS["discourse"]
    | METADATA_FAMILY_FIELDS["quotation"]
)
# Review state stays visible: a reader must be able to tell unreviewed values from confirmed ones.
_REVIEW_FIELDS = {"needs_review", "review_reason", "publication_review_status", "provenance_warnings"}

READER_RECORD_FIELDS = frozenset(
    set(CELF_REQUIRED_RECORD_FIELDS)
    | _LOCATION_FIELDS
    | _CITATION_FIELDS
    | set(MANIFEST_INHERITED_FIELDS)
    | _ATTRIBUTION_FIELDS
    | _REVIEW_FIELDS
)

# What the reader profile intentionally leaves out, by layer.
OMITTED_LAYERS = ("field_assertions",)


def normalize_site_record_profile(value: str | None) -> str:
    profile = str(value or DEFAULT_SITE_RECORD_PROFILE).strip().lower()
    if profile not in SITE_RECORD_PROFILES:
        raise ValueError(f"Unsupported record metadata profile: {value!r}")
    return profile


def _field_authority(record: dict[str, Any], kept: Iterable[str]) -> dict[str, dict[str, str]]:
    """The derivation and review state of each kept scholarly field, in place of the full assertions.

    A reader-profile site has no FieldAssertions, but an attribution value that a model proposed and nobody
    reviewed must not read as settled, so the state travels with the value in a few short strings.
    """
    kept_names = set(kept)
    summary: dict[str, dict[str, str]] = {}
    for assertion in current_assertions(record):
        name = assertion.field_name
        if not name or name not in kept_names or name not in _ATTRIBUTION_FIELDS:
            continue
        summary[name] = {
            "derivation": str(assertion.derivation_method),
            "evaluation": str(assertion.evaluation_status),
            "authority": str(assertion.authority_status),
        }
    return summary


def reader_record(record: dict[str, Any], extra_fields: Iterable[str] = ()) -> dict[str, Any]:
    """Reduce one public Record to the reader profile (plus any collection filter fields)."""
    allowed = READER_RECORD_FIELDS | set(extra_fields)
    slim = {key: value for key, value in record.items() if key in allowed}
    authority = _field_authority(record, slim)
    if authority:
        slim["field_authority"] = authority
    return slim


def apply_record_profile(
    records: Sequence[dict[str, Any]], profile: str, filter_fields: Iterable[str] = ()
) -> list[dict[str, Any]]:
    if normalize_site_record_profile(profile) == "complete":
        return [dict(record) for record in records]
    extra = [str(field) for field in filter_fields if str(field) and not str(field).startswith("_")]
    return [reader_record(record, extra) for record in records]


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
