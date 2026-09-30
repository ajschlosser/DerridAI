# Copyright 2026 Aaron John Schlosser, PhD.
"""Reviewed alias sets and the per-build semantic identity registry.

A reviewed alias set is a reviewer's explicit statement that several surfaces name one
identity of a kind ("Jacques Derrida", "J. Derrida", "Derrida, Jacques" are one person).
It is canonical reviewer state for a build, kept beside its records: never inferred from
model output, never created from Document Intelligence clusters, and never rewritten.
Changing a set retires it and records a new one, so the history stays auditable.

Two active sets of the same kind may not share a surface: a surface that could name two
reviewed identities is ambiguous by construction, and ambiguity must be visible rather
than resolved by whichever set happened to load first. Two sets whose surfaces merely
normalize alike ("J. P. Dingus", "JP Dingus") are allowed: that is how a reviewer says
two similar names belong to different people.

The registry assembled here is derived and rebuildable from these sets, the build's
reviewed metadata, and its Document Intelligence analysis.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .semantic_identity import SemanticIdentityRef, text_key
from .semantic_identity_registry import (
    REVIEWED_ALIAS,
    SemanticIdentityRegistry,
    project_document_intelligence,
    project_reviewed_metadata,
)

ALIAS_FILE = "semantic_aliases.json"
MAX_ALIAS_SETS = 2000
MAX_ALIASES = 50
MAX_ALIAS_CHARS = 200
KIND_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,119}$")
_lock = threading.Lock()


class AliasConflict(ValueError):
    """An alias is already claimed by another active set of the same kind."""


def _path(repo: Any, build_id: str) -> Path | None:
    """Where a build's alias sets live; None for a repository that stores none."""
    repo.get_build(build_id)  # KeyError for an unknown build
    root = getattr(repo, "root", None)
    return Path(root) / "builds" / build_id / ALIAS_FILE if root is not None else None


_cache: dict[str, tuple[tuple[int, int], list[dict[str, Any]]]] = {}


def _read(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    try:
        stat = path.stat()
    except FileNotFoundError:
        return []
    stamp = (stat.st_mtime_ns, stat.st_size)
    cached = _cache.get(str(path))
    if cached and cached[0] == stamp:
        return json.loads(json.dumps(cached[1]))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        # Canonical reviewer state that cannot be read is an error, not an empty list.
        raise RuntimeError(f"The reviewed alias file for this build cannot be read: {exc}") from exc
    items = payload.get("alias_sets") if isinstance(payload, dict) else None
    rows = [item for item in items or [] if isinstance(item, dict)]
    _cache[str(path)] = (stamp, json.loads(json.dumps(rows)))
    return rows


def _write(path: Path | None, items: list[dict[str, Any]]) -> None:
    if path is None:
        raise ValueError("This repository cannot store reviewed alias sets.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "alias_sets": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def list_alias_sets(repo: Any, build_id: str, *, include_retired: bool = False) -> list[dict[str, Any]]:
    items = _read(_path(repo, build_id))
    return [item for item in items if include_retired or not item.get("retired_at")]


def _clean_surfaces(canonical_label: Any, aliases: Any) -> tuple[str, list[str]]:
    label = " ".join(str(canonical_label or "").split())
    if not label or len(label) > MAX_ALIAS_CHARS:
        raise ValueError(f"A canonical label is required (at most {MAX_ALIAS_CHARS} characters).")
    if not isinstance(aliases, list) or len(aliases) > MAX_ALIASES:
        raise ValueError(f"Aliases must be a list of at most {MAX_ALIASES} values.")
    cleaned: list[str] = []
    seen = {text_key(label)}
    for alias in aliases:
        value = " ".join(str(alias or "").split())
        if not value:
            continue
        if len(value) > MAX_ALIAS_CHARS:
            raise ValueError(f"An alias may be at most {MAX_ALIAS_CHARS} characters.")
        if text_key(value) not in seen:
            seen.add(text_key(value))
            cleaned.append(value)
    return label, cleaned


def create_alias_set(
    repo: Any,
    build_id: str,
    *,
    kind: str,
    canonical_label: str,
    aliases: list[str],
    reason: str = "",
    reviewer: str = "",
    replaces: str | None = None,
) -> dict[str, Any]:
    """Record a reviewed alias set; with ``replaces``, retire that set in the same write."""
    kind = str(kind or "").strip()
    if not KIND_RE.match(kind):
        raise ValueError("An identity kind is lower-case letters, digits, '.', '_' or '-', starting with a letter.")
    label, cleaned = _clean_surfaces(canonical_label, aliases)
    path = _path(repo, build_id)
    now = datetime.now(UTC).isoformat()
    with _lock:
        items = _read(path)
        if replaces and not any(item.get("alias_set_id") == replaces and not item.get("retired_at") for item in items):
            raise KeyError(replaces)
        active = [item for item in items if not item.get("retired_at") and item.get("alias_set_id") != replaces]
        if len(active) >= MAX_ALIAS_SETS:
            raise ValueError(f"A build may hold at most {MAX_ALIAS_SETS} reviewed alias sets.")
        claimed = {
            text_key(surface): item
            for item in active
            if item.get("kind") == kind
            for surface in [item.get("canonical_label"), *(item.get("aliases") or [])]
            if str(surface or "").strip()
        }
        clashes = sorted({surface for surface in [label, *cleaned] if text_key(surface) in claimed})
        if clashes:
            raise AliasConflict("Already part of another reviewed identity of this kind: " + ", ".join(clashes))
        entry = {
            "alias_set_id": f"alias-{uuid.uuid4().hex[:16]}",
            "kind": kind,
            "canonical_label": label,
            "aliases": cleaned,
            "reason": str(reason or "")[:1000],
            "reviewer": reviewer,
            "created_at": now,
            "retired_at": None,
            "replaces": replaces,
        }
        for item in items:
            if replaces and item.get("alias_set_id") == replaces:
                item["retired_at"] = now
                item["retired_by"] = reviewer
                item["replaced_by"] = entry["alias_set_id"]
        items.append(entry)
        _write(path, items)
    return entry


def retire_alias_set(repo: Any, build_id: str, alias_set_id: str, *, reviewer: str = "") -> dict[str, Any]:
    path = _path(repo, build_id)
    with _lock:
        items = _read(path)
        for item in items:
            if item.get("alias_set_id") == alias_set_id and not item.get("retired_at"):
                item["retired_at"] = datetime.now(UTC).isoformat()
                item["retired_by"] = reviewer
                _write(path, items)
                return item
    raise KeyError(alias_set_id)


def alias_digest(repo: Any, build_id: str) -> str:
    """Changes whenever the active reviewed alias sets change (for derived-projection freshness)."""
    try:
        active = list_alias_sets(repo, build_id)
    except (KeyError, RuntimeError):
        return ""
    body = [(item.get("alias_set_id"), item.get("kind"), item.get("canonical_label"), item.get("aliases")) for item in active]
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _kind_modes(schema: Any) -> dict[str, str]:
    """The equivalence mode each identity kind is compared under by this schema's fields."""
    modes: dict[str, str] = {}
    for name in [*getattr(schema, "field_names", lambda: [])()]:
        try:
            profile = schema.equivalence_profile_for(name)
        except KeyError:
            continue
        if profile.identity_kind:
            modes.setdefault(profile.identity_kind, profile.mode)
    return modes


def register_alias_sets(registry: SemanticIdentityRegistry, alias_sets: list[dict[str, Any]], schema: Any = None) -> int:
    modes = _kind_modes(schema) if schema is not None else {}
    for item in alias_sets:
        kind = str(item.get("kind") or "")
        registry.register_projection(
            SemanticIdentityRef(
                identity_id=f"{kind}:{hashlib.sha256((kind + chr(31) + str(item.get('alias_set_id'))).encode('utf-8')).hexdigest()[:16]}",
                kind=kind,
                canonical_label=str(item.get("canonical_label") or ""),
                aliases=[str(value) for value in item.get("aliases") or []],
                source=REVIEWED_ALIAS,
                source_ids=[str(item.get("alias_set_id") or "")],
            ),
            mode=modes.get(kind, "entity_name" if kind in {"person", "character"} else "text"),
        )
    return len(alias_sets)


def build_registry(
    repo: Any,
    build_id: str,
    *,
    schema: Any,
    records: list[dict[str, Any]] | None = None,
    analysis: dict[str, Any] | None = None,
) -> SemanticIdentityRegistry:
    """The build's registry: reviewed aliases, reviewed metadata, then advisory Document Intelligence."""
    registry = SemanticIdentityRegistry()
    try:
        register_alias_sets(registry, list_alias_sets(repo, build_id), schema)
    except KeyError:
        pass
    if records:
        project_reviewed_metadata(registry, [json.loads(json.dumps(row, default=str)) for row in records], schema)
    if analysis:
        project_document_intelligence(registry, analysis)
    return registry


def registry_factory(repo: Any, build_id: str, schema: Any) -> Callable[[dict[str, Any]], SemanticIdentityRegistry]:
    """Per-Record registries for code that compares many records' values (exemplars, learning)."""
    try:
        alias_sets = list_alias_sets(repo, build_id)
    except (KeyError, RuntimeError):
        alias_sets = []

    base = SemanticIdentityRegistry()
    register_alias_sets(base, alias_sets, schema)

    def make(record: dict[str, Any]) -> SemanticIdentityRegistry:
        from .semantic_identity_registry import registry_for_record

        return registry_for_record(record, parent=base)

    return make


def review_registry(repo: Any, build_id: str, record: dict[str, Any], schema: Any) -> SemanticIdentityRegistry:
    """What a review comparison consults: the build's reviewed aliases and the Record's own analysis.

    Reviewed metadata values are not included: they never add equivalence beyond the
    field's normalization, and a review must not depend on every other record.
    """
    from .semantic_identity_registry import registry_for_record

    registry = registry_for_record(record)
    try:
        register_alias_sets(registry, list_alias_sets(repo, build_id), schema)
    except KeyError:
        pass
    return registry


def reviewed_value_relation(repo: Any, build_id: str, schema: Any, language: str = "") -> Callable[[str, str, str], str]:
    """Compare two JSON-encoded reviewed values of one field under the schema's policy.

    Used by precedent retrieval's analogy conditions (``match_field_ids``): equivalent
    reviewed values agree, different ones contradict, unknown ones are not compared.
    """
    from .semantic_identity_registry import compare_field_values

    registry = SemanticIdentityRegistry()
    try:
        register_alias_sets(registry, list_alias_sets(repo, build_id), schema)
    except (KeyError, RuntimeError):
        pass
    context = {"language": language}

    def relation(field: str, left: str, right: str) -> str:
        try:
            left_value, right_value = json.loads(left), json.loads(right)
        except (TypeError, ValueError):
            return "exact" if left == right else "different"
        if schema is None:
            return "exact" if left_value == right_value else "different"
        return compare_field_values(schema, field, left_value, right_value, record=context, registry=registry).relation

    return relation
