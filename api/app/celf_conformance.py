# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic cELF Core and Publication conformance projections."""

from __future__ import annotations

from typing import Any

from .corpus_publication import validate_publication_record

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
    core: list[dict[str, Any]] = []
    validation = build.get("validation") if isinstance(build.get("validation"), dict) else {}
    for key in _SOURCE_INTEGRITY_KEYS:
        values = validation.get(key)
        if values:
            core.append({"code": f"source_{key}", "detail": values})
    for record in records:
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
    publication: list[dict[str, Any]] = []
    for record in records:
        for error in validate_publication_record(record):
            publication.append({"code": "publication_record_invalid", "record_id": record.get("record_id"), "detail": error})
    if not records:
        publication.append({"code": "empty_publication"})
    result = {
        "spec_version": "1.0",
        "core": {"status": _status(core), "blockers": core},
        "publication": {"status": _status(publication) if not core else "non_conformant", "blockers": publication + core},
    }
    result["conformant"] = result["core"]["status"] == "conformant" and result["publication"]["status"] == "conformant"
    return result
