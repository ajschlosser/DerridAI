# Copyright 2026 Aaron John Schlosser, PhD.
"""Materialize evidence-bound metadata exemplars from authoritative reviewed records.

Human review writes canonical state before derived indexing. Ordinary projection
reconciles complete exemplar sets for dirty Records; full scope recovery remains
available. Only captured dirty events are acknowledged after successful writes.
"""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import experiment
from .corpus_reviewer_helpers import _second_opinion_owed
from .field_assertions import (
    current_assertions,
    migrate_record_assertions,
    project_record_assertions,
)
from .metadata_exemplars import build_correction_exemplars, build_metadata_exemplar
from .metadata_schema import MetadataSchema, default_schema
from .semantic_identity_store import registry_factory
from .system_store import system_store

PROJECTION = "metadata_exemplars"
PROJECTION_BATCH_SIZE = 100
DERIVATION_VERSION = 1

# Last projection failure per build (process-local). The outbox stays dirty until a
# projection succeeds, so an unreachable embedding provider would otherwise leave
# the Metadata examples page silently empty.
_last_errors: dict[str, str] = {}


def record_projection_result(build_id: str, error: str = "") -> None:
    if error:
        _last_errors[build_id] = error[:500]
    else:
        _last_errors.pop(build_id, None)


def projection_backlog(repo: Any = None) -> dict[str, Any]:
    """Unprojected reviewed-metadata work, with the most recent failure per build."""
    dirty = system_store.list_semantic_memory_dirty(PROJECTION, limit=1000)
    scopes = sorted({str(row.get("scope_id") or "") for row in dirty if str(row.get("scope_id") or "")})
    count = len(dirty)
    if repo is not None:
        summary = system_store.semantic_memory_dirty_summary(PROJECTION)
        count = sum(int(row["dirty"]) for row in summary)
        scope_ids = {str(row["scope_id"]) for row in summary if row["scope_id"]}
        offset = 0
        while True:
            listing = repo.list_builds(offset=offset, limit=100)
            for build in listing["items"]:
                build_id = str(build["build_id"])
                pending = repo.metadata_exemplar_dirty_count(build_id)
                if pending:
                    count += pending
                    scope_ids.add(build_id)
            offset += len(listing["items"])
            if offset >= listing["total"]:
                break
        scopes = sorted(scope_ids)
    return {
        "dirty": count,
        "scopes": scopes,
        "errors": {scope: _last_errors[scope] for scope in [*scopes, "recovery"] if scope in _last_errors},
    }


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
        "region_type": "derridai.region_type",
        "primary_text": "derridai.primary_text",
        "discourse_role": "derridai.discourse_role",
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


def _build_schema(build: dict[str, Any]) -> MetadataSchema | None:
    """The metadata schema copied onto a build; None (exact comparison) if it cannot be read."""
    raw = build.get("schema")
    try:
        return MetadataSchema.model_validate(raw) if isinstance(raw, dict) and raw else default_schema()
    except ValidationError:
        return None


def derive_build_metadata_exemplars(
    repo: Any,
    build_id: str,
) -> list[dict[str, Any]]:
    """Derive the complete current evidence-bound exemplar set for one build."""

    return _derive_metadata_exemplars(repo, build_id, repo.load_records(build_id))


def derive_record_metadata_exemplars(
    repo: Any, build_id: str, record_ids: list[str],
) -> list[dict[str, Any]]:
    """Derive complete exemplar sets for selected current Records, not the corpus."""
    rows = [row for row in repo.get_records(build_id, record_ids) if row is not None]
    return _derive_metadata_exemplars(repo, build_id, rows)


def _derive_metadata_exemplars(
    repo: Any, build_id: str, rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    build = repo.get_build(build_id)
    asset_id = str(build.get("asset_id") or "")
    blocks_by_id: dict[str, dict[str, Any]] = {}
    if asset_id:
        blocks_by_id = {
            str(block.get("block_id") or ""): block
            for block in repo.load_blocks(asset_id)
            if isinstance(block, dict) and str(block.get("block_id") or "")
        }

    schema_id, schema_version, field_ids = _field_contract(rows, build)
    schema = _build_schema(build)
    registry_for = registry_factory(repo, build_id, schema)
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
                schema=schema,
                registry=registry_for(row),
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
            schema=schema,
            registry_for=registry_for,
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
    after = None
    while True:
        legacy = system_store.list_semantic_memory_dirty(
            PROJECTION, unscoped=True, limit=PROJECTION_BATCH_SIZE, after=after,
        )
        if not legacy:
            break
        record_ids = {
            str(row["record_id"]) for row in repo.get_records(
                build_id, [str(item.get("record_id") or "") for item in legacy],
            ) if row is not None
        }
        matched = [str(row["item_id"]) for row in legacy if str(row.get("record_id") or "") in record_ids]
        if matched:
            system_store.resolve_semantic_memory_scope(matched, build_id)
        if len(legacy) < PROJECTION_BATCH_SIZE:
            break
        after = str(legacy[-1]["created_at"]), str(legacy[-1]["item_id"])
    return system_store.list_semantic_memory_dirty(
        PROJECTION, scope_id=build_id, limit=PROJECTION_BATCH_SIZE,
    )


def dirty_metadata_exemplar_build_ids(repo: Any) -> list[str]:
    """Resolve dirty outbox rows to builds, including pre-scope legacy rows."""

    dirty = system_store.semantic_memory_dirty_summary(PROJECTION)
    scopes = {
        str(row.get("scope_id") or "")
        for row in dirty
        if str(row.get("scope_id") or "")
    }
    offset = 0
    existing = set()
    while True:
        listing = repo.list_builds(offset=offset, limit=100)
        for build in listing.get("items") or []:
            build_id = str(build.get("build_id") or "")
            if not build_id:
                continue
            existing.add(build_id)
            journal = getattr(repo, "metadata_exemplar_dirty", None)
            state = getattr(repo, "metadata_exemplar_state", None)
            if callable(journal) and (journal(build_id, limit=1) or (
                callable(state) and (
                    state(build_id)[0] or state(build_id)[1] != _build_context(repo, build_id)
                )
            )):
                scopes.add(build_id)
            if _dirty_items_for_build(repo, build_id):
                scopes.add(build_id)
        offset += len(listing.get("items") or [])
        if not listing.get("items") or offset >= int(listing.get("total") or offset):
            break
    return sorted(scopes & existing)


def _build_context(repo: Any, build_id: str) -> str:
    build = repo.get_build(build_id)
    dependencies: dict[str, Any] = {
        key: build.get(key) for key in (
            "schema", "asset_id", "source_document_id", "editorial_memory_reset_at", "manifest",
        )
    }
    dependencies["derivation_version"] = DERIVATION_VERSION
    root = getattr(repo, "root", None)
    if root is not None:
        paths = [Path(root) / "builds" / build_id / "semantic_aliases.json"]
        asset_id = str(build.get("asset_id") or "")
        if asset_id:
            paths.append(repo.asset_blocks_path(asset_id))
        for path in paths:
            try:
                stat = path.stat()
                dependencies[str(path.name)] = (stat.st_mtime_ns, stat.st_size)
            except FileNotFoundError:
                dependencies[str(path.name)] = None
    return hashlib.sha256(json.dumps(dependencies, sort_keys=True, default=str).encode()).hexdigest()


def project_build_metadata_exemplars(
    repo: Any,
    build_id: str,
    index: Any,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Make one build's Chroma scope match current authoritative reviewed state."""

    writer = getattr(index, "projection_writer", None)
    with writer() if callable(writer) else nullcontext():
        dirty = _dirty_items_for_build(repo, build_id)
        journal_reader = getattr(repo, "metadata_exemplar_dirty", None)
        journal = journal_reader(build_id, limit=PROJECTION_BATCH_SIZE) if callable(journal_reader) else []
        context = _build_context(repo, build_id)
        state_reader = getattr(repo, "metadata_exemplar_state", None)
        previous = state_reader(build_id) if callable(state_reader) else ("", "")
        full = force or any(not item.get("record_id") for item in [*dirty, *journal])
        full = full or (callable(state_reader) and previous[1] != context)
        # Do not contact an unavailable vector service for a clean worker checkpoint.
        if not dirty and not journal and not full and not previous[0]:
            return {"scope_id": build_id, "skipped": True, "desired": 0, "acknowledged": 0, "pending": False}
        epoch_reader = getattr(index, "collection_epoch", None)
        try:
            epoch = epoch_reader() if callable(epoch_reader) else ""
        except Exception:
            if callable(journal_reader) and not dirty and not journal:
                repo.invalidate_metadata_exemplars(build_id, schedule=False)
            raise
        full = full or (callable(state_reader) and previous[0] != epoch)
        if not dirty and not journal and not full:
            return {"scope_id": build_id, "skipped": True, "desired": 0, "acknowledged": 0, "pending": False}
        record_ids = sorted({str(item["record_id"]) for item in [*dirty, *journal] if item.get("record_id")})
        started = time.monotonic()
        exemplars = (
            derive_build_metadata_exemplars(repo, build_id) if full
            else derive_record_metadata_exemplars(repo, build_id, record_ids)
        )
        derived_ms = round((time.monotonic() - started) * 1000, 3)
        stats = dict(
            index.rebuild_scope(build_id, exemplars) if full
            else index.reconcile_records(build_id, record_ids, exemplars)
        )
        item_ids = [str(row["item_id"]) for row in dirty if row.get("item_id")]
        acknowledged = system_store.complete_semantic_memory_dirty(item_ids)
        if callable(journal_reader):
            repo.complete_metadata_exemplar_dirty(build_id, journal)
            repo.save_metadata_exemplar_state(build_id, epoch, context)
        return {
            "scope_id": build_id, "skipped": False, **stats,
            "mode": "rebuild" if full else "incremental",
            "records": None if full else len(record_ids), "derivation_ms": derived_ms,
            "acknowledged": acknowledged,
            "pending": bool(_dirty_items_for_build(repo, build_id)) or bool(
                journal_reader(build_id, limit=1) if callable(journal_reader) else []
            ),
        }


def diagnose_build_metadata_exemplars(repo: Any, build_id: str) -> dict[str, Any]:
    """Explain, per current assertion, why a precedent was or was not derived.

    Reviewed bindings and the semantic outbox can exist while no exemplar does:
    an exemplar needs a human-owned value *and* reviewer-bound evidence blocks that
    belong to the record. This reports the count of each outcome so a reviewer can
    see what is missing instead of an empty Metadata examples page.
    """

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
    outcomes: dict[str, int] = {}
    samples: dict[str, list[dict[str, str]]] = {}

    def note(code: str, record_id: str, field: str) -> None:
        outcomes[code] = outcomes.get(code, 0) + 1
        bucket = samples.setdefault(code, [])
        if len(bucket) < 3:
            bucket.append({"record_id": record_id, "field": field})

    for row in rows:
        record_id = str(row.get("record_id") or "")
        if reset_at and str(row.get("human_touched_at") or "") <= reset_at:
            note("before_editorial_memory_reset", record_id, "")
            continue
        if experiment.is_gold(record_id):
            note("gold_record", record_id, "")
            continue
        migrate_record_assertions(row)
        project_record_assertions(row)
        for assertion in current_assertions(row):
            field = str(assertion.field_name or "")
            if not field:
                continue
            trusted = (
                assertion.authority_status in {"human_confirmed", "human_override"}
                or assertion.value_status == "confirmed_absent"
            )
            if not trusted:
                note("not_human_confirmed", record_id, field)
                continue
            if _second_opinion_owed(row, field):
                note("second_opinion_owed", record_id, field)
                continue
            why: list[str] = []
            exemplar = build_metadata_exemplar(
                row, field, blocks_by_id,
                schema_id=schema_id, schema_version=schema_version,
                source_document_id=source_document_id,
                field_id=str(assertion.field_id or field_ids.get(field, "")),
                why=why,
            )
            note("exemplar" if exemplar is not None else (why[-1] if why else "unknown"), record_id, field)
    dirty = system_store.list_semantic_memory_dirty(PROJECTION, scope_id=build_id, limit=1000)
    return {
        "build_id": build_id,
        "records": len(rows),
        "outcomes": outcomes,
        "examples": samples,
        "outbox_dirty": len(dirty),
    }
