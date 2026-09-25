# Copyright 2026 Aaron John Schlosser, PhD.
"""Materialize evidence-bound metadata exemplars from authoritative reviewed records.

Human review writes the corpus RecordRevision first and appends a durable audit
binding/outbox item in SQLite. This module consumes that outbox: it derives the
current complete exemplar set for an affected build, replaces that build's Chroma
scope, and acknowledges the outbox only after the derived projection succeeds.
"""

from __future__ import annotations

from typing import Any

from . import experiment
from .corpus_reviewer_helpers import _second_opinion_owed
from .field_assertions import current_assertions, migrate_record_assertions, project_record_assertions
from .metadata_exemplars import build_correction_exemplars, build_metadata_exemplar
from .system_store import system_store

PROJECTION = "metadata_exemplars"


def _field_contract(
    rows: list[dict[str, Any]],
    build: dict[str, Any],
) -> tuple[str, str, dict[str, str]]:
    schema_payload = build.get("schema") if isinstance(build.get("schema"), dict) else {}
    schema_id = str(schema_payload.get("id") or build.get("schema_id") or "")
    schema_version = str(
        schema_payload.get("schema_version")
        or build.get("metadata_schema_version")
        or ""
    )
    core = {
        "region_type": "core.region_type",
        "primary_text": "core.primary_text",
        "discourse_role": "core.discourse_role",
    }
    fields = {
        str(item.get("name") or ""): str(item.get("field_id") or "")
        for item in schema_payload.get("fields") or []
        if isinstance(item, dict) and str(item.get("name") or "")
    }
    fields.update(core)
    for row in rows:
        migrate_record_assertions(row)
        for assertion in current_assertions(row):
            name = str(assertion.field_name or "")
            if name and name not in fields:
                fields[name] = str(assertion.field_id or f"legacy.{name}")
    return schema_id, schema_version, fields


def derive_build_metadata_exemplars(
    repo: Any,
    build_id: str,
) -> list[dict[str, Any]]:
    """Derive the complete current evidence-bound exemplar set for one build."""

    build = repo.get_build(build_id)
    rows = repo.load_records(build_id)
    asset_id = str(build.get("asset_id") or "")
    blocks_by_id: dict[str, dict[str, Any]] = {}
    if asset_id:
        blocks_by_id = {
            str(block.get("block_id") or ""): block
            for block in repo.load_blocks(asset_id)
            if isinstance(block, dict) and str(block.get("block_id") or "")
        }

    schema_id, schema_version, field_ids = _field_contract(rows, build)
    source_document_id = str(build.get("source_document_id") or asset_id or "")
    reset_at = str(build.get("editorial_memory_reset_at") or "")
    exemplars: list[dict[str, Any]] = []
    trusted_rows: list[dict[str, Any]] = []

    for row in rows:
        record_id = str(row.get("record_id") or "")
        if reset_at and str(row.get("human_touched_at") or "") <= reset_at:
            continue
        if experiment.is_gold(record_id):
            continue
        migrate_record_assertions(row)
        project_record_assertions(row)
        row_is_trusted = False
        for assertion in current_assertions(row):
            field = str(assertion.field_name or "")
            trusted = (
                assertion.authority_status in {"human_confirmed", "human_override"}
                or assertion.value_status == "confirmed_absent"
            )
            if not field or not trusted or _second_opinion_owed(row, field):
                continue
            exemplar = build_metadata_exemplar(
                row,
                field,
                blocks_by_id,
                schema_id=schema_id,
                schema_version=schema_version,
                source_document_id=source_document_id,
                field_id=str(assertion.field_id or field_ids.get(field, "")),
            )
            if exemplar is not None:
                exemplars.append(exemplar)
                row_is_trusted = True
        if row_is_trusted:
            trusted_rows.append(row)

    for row in trusted_rows:
        for correction in build_correction_exemplars(
            row,
            blocks_by_id,
            schema_id=schema_id,
            schema_version=schema_version,
            source_document_id=source_document_id,
            field_ids=field_ids,
        ):
            field = str(correction.get("field_name") or "")
            if field and not _second_opinion_owed(row, field):
                exemplars.append(correction)

    return list(
        {
            str(item.get("metadata_exemplar_id") or ""): item
            for item in exemplars
            if str(item.get("metadata_exemplar_id") or "")
        }.values()
    )


def _dirty_items_for_build(repo: Any, build_id: str) -> list[dict[str, Any]]:
    rows = system_store.list_semantic_memory_dirty(PROJECTION, limit=1000)
    explicit = [row for row in rows if str(row.get("scope_id") or "") == build_id]
    legacy = [row for row in rows if not str(row.get("scope_id") or "")]
    if not legacy:
        return explicit
    record_ids = {
        str(row.get("record_id") or "")
        for row in repo.load_records(build_id)
        if str(row.get("record_id") or "")
    }
    explicit.extend(
        row for row in legacy
        if str(row.get("record_id") or "") in record_ids
    )
    return explicit


def dirty_metadata_exemplar_build_ids(repo: Any) -> list[str]:
    """Resolve dirty outbox rows to builds, including pre-scope legacy rows."""

    dirty = system_store.list_semantic_memory_dirty(PROJECTION, limit=1000)
    scopes = {
        str(row.get("scope_id") or "")
        for row in dirty
        if str(row.get("scope_id") or "")
    }
    unresolved = {
        str(row.get("record_id") or "")
        for row in dirty
        if not str(row.get("scope_id") or "") and str(row.get("record_id") or "")
    }
    if unresolved:
        listing = repo.list_builds(offset=0, limit=1000)
        for build in listing.get("items") or []:
            build_id = str(build.get("build_id") or "")
            if not build_id:
                continue
            ids = {
                str(row.get("record_id") or "")
                for row in repo.load_records(build_id)
                if str(row.get("record_id") or "")
            }
            if ids & unresolved:
                scopes.add(build_id)
                unresolved -= ids
            if not unresolved:
                break
    return sorted(scopes)


def project_build_metadata_exemplars(
    repo: Any,
    build_id: str,
    index: Any,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Make one build's Chroma scope match current authoritative reviewed state."""

    dirty = _dirty_items_for_build(repo, build_id)
    if not dirty and not force:
        return {"scope_id": build_id, "skipped": True, "desired": 0, "acknowledged": 0}

    exemplars = derive_build_metadata_exemplars(repo, build_id)
    stats = dict(index.rebuild_scope(build_id, exemplars))
    item_ids = [
        str(row.get("item_id") or "")
        for row in dirty
        if str(row.get("item_id") or "")
    ]
    acknowledged = system_store.complete_semantic_memory_dirty(item_ids)
    return {
        "scope_id": build_id,
        "skipped": False,
        **stats,
        "acknowledged": acknowledged,
    }
