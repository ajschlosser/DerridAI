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

"""Known semantic identities and their aliases, projected from canonical state.

The registry is authoritative only for *derived* identity resolution.  It never changes a
FieldAssertion value, a reviewer's value, source text or an evidence span, and it can be
rebuilt at any time from:

``reviewed_alias``
    An explicit reviewed statement that these surfaces name one identity.  Established: it
    can make two values equivalent or keep two similar-looking values apart.
``reviewed_metadata``
    Human-confirmed or human-overridden values.  Established, but each reviewed surface only
    names its own normalized identity; observing two reviewed values never asserts that
    they are different people or concepts.
``document_intelligence``
    Provider entity clusters (spaCy/BookNLP).  Advisory: a cluster can resolve an otherwise
    unknown comparison to equivalent, but it never overrides a deterministic difference and
    never outranks reviewed identity.  Provider, model and cluster ids stay as provenance.

Identities are scoped by kind (``person``, ``concept``, ...).  The Semantic Content Graph
consumes this registry; the registry never reads the graph.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .field_assertions import current_assertions, migrate_record_assertions
from .semantic_identity import (
    SEMANTIC_IDENTITY_VERSION,
    EquivalenceMode,
    EquivalenceProfile,
    SemanticIdentityRef,
    ValueEquivalenceResult,
    compare_values,
    entity_name_key,
    text_key,
)

REVIEWED_ALIAS = "reviewed_alias"
REVIEWED_METADATA = "reviewed_metadata"
DOCUMENT_INTELLIGENCE = "document_intelligence"
ESTABLISHED_SOURCES = frozenset({REVIEWED_ALIAS, REVIEWED_METADATA})
_REVIEWED_AUTHORITY = {"human_confirmed", "human_override"}
# Provider entity types that name identities a metadata field can hold.
_PROVIDER_KINDS = {"PERSON": "person", "PER": "person", "WORK_OF_ART": "work"}


def surface_key(value: str, mode: EquivalenceMode | str) -> str:
    """The key an alias is indexed under: names by name identity, everything else by surface."""
    return entity_name_key(value) if mode == "entity_name" else text_key(value)


def _identity_id(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join([kind, *parts]).encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{digest}"


class SemanticIdentityRegistry:
    """An in-memory index of identities by kind and normalized alias."""

    def __init__(self, parent: SemanticIdentityRegistry | None = None) -> None:
        # ``parent`` is a shared, read-only base layer (for example a build's reviewed
        # aliases) under a per-Record layer, so the base is not rebuilt for every Record.
        self._parent = parent
        self._identities: dict[str, SemanticIdentityRef] = {}
        self._modes: dict[str, str] = {}
        self._index: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    def __len__(self) -> int:
        return len(self._identities) + (len(self._parent) if self._parent is not None else 0)

    def identities(self) -> list[SemanticIdentityRef]:
        merged = {ref.identity_id: ref for ref in (self._parent.identities() if self._parent is not None else [])}
        merged.update(self._identities)
        return [merged[key] for key in sorted(merged)]

    def _lookup(self, index_key: tuple[str, str, str]) -> dict[str, SemanticIdentityRef]:
        found = self._parent._lookup(index_key) if self._parent is not None else {}
        for key in self._index.get(index_key, set()):
            found[key] = self._identities[key]
        return found

    def register_projection(self, identity: SemanticIdentityRef, *, mode: EquivalenceMode | str = "text") -> None:
        """Add an identity, merging aliases and source ids into one already registered."""
        existing = self._identities.get(identity.identity_id)
        if existing is not None:
            identity = existing.model_copy(update={
                "aliases": list(dict.fromkeys([*existing.aliases, *identity.aliases])),
                "source_ids": list(dict.fromkeys([*existing.source_ids, *identity.source_ids])),
            })
        self._identities[identity.identity_id] = identity
        self._modes[identity.identity_id] = str(mode)
        for alias in [identity.canonical_label, *identity.aliases]:
            if str(alias).strip():
                # The exact surface is indexed apart from the normalized key, so that two established
                # identities whose surfaces normalize alike stay distinguishable.
                self._index[(identity.kind, "=", text_key(str(alias)))].add(identity.identity_id)
                self._index[(identity.kind, str(mode), surface_key(str(alias), mode))].add(identity.identity_id)

    def _tier(self, value: str, kind: str, mode: str, sources: frozenset[str]) -> tuple[SemanticIdentityRef | None, bool]:
        """(the identity ``value`` names within ``sources``, whether the lookup was ambiguous)."""
        for index_key in ((kind, "=", text_key(value)), (kind, mode, surface_key(value, mode))):
            candidates = self._lookup(index_key)
            found = [candidates[key] for key in sorted(candidates) if candidates[key].source in sources]
            if len(found) == 1:
                return found[0], False
            if len(found) > 1:
                return None, True
        return None, False

    def resolve(
        self,
        *,
        value: str,
        kind: str,
        mode: EquivalenceMode | str = "text",
        language: str = "",
        established_only: bool = False,
    ) -> SemanticIdentityRef | None:
        """The single identity ``value`` names, or None when unknown or ambiguous.

        Explicit reviewed aliases win over reviewed metadata, which wins over advisory
        Document Intelligence clusters (ignored with ``established_only``).
        """
        tiers = [frozenset({REVIEWED_ALIAS}), frozenset({REVIEWED_METADATA})]
        if not established_only:
            tiers.append(frozenset({DOCUMENT_INTELLIGENCE}))
        for sources in tiers:
            ref, ambiguous = self._tier(value, kind, str(mode), sources)
            if ref is not None or ambiguous:
                return ref
        return None

    def ambiguous(self, *, value: str, kind: str, mode: EquivalenceMode | str = "text") -> bool:
        """Whether ``value`` could name more than one established identity."""
        return any(self._tier(value, kind, str(mode), frozenset({source}))[1] for source in (REVIEWED_ALIAS, REVIEWED_METADATA))

    def resolve_alias(self, *, value: str, kind: str, mode: EquivalenceMode | str = "text", language: str = "") -> SemanticIdentityRef | None:
        """The identity an explicit reviewed alias assigns to ``value``."""
        return self._tier(value, kind, str(mode), frozenset({REVIEWED_ALIAS}))[0]

    def identities_for_key(self, *, canonical_key: str, kind: str) -> list[SemanticIdentityRef]:
        ids = {key for (k, _mode, alias), found in self._index.items() if k == kind and alias == canonical_key for key in found}
        return [self._identities[key] for key in sorted(ids)]


def register_reviewed_alias(
    registry: SemanticIdentityRegistry,
    *,
    kind: str,
    canonical_label: str,
    aliases: Iterable[str],
    mode: EquivalenceMode | str = "text",
    source_ids: Iterable[str] = (),
) -> SemanticIdentityRef:
    """Register a human-reviewed alias set. Ambiguous surname-only forms must not be added automatically."""
    ref = SemanticIdentityRef(
        identity_id=_identity_id(kind, REVIEWED_ALIAS, text_key(canonical_label)),
        kind=kind,
        canonical_label=canonical_label,
        aliases=list(dict.fromkeys(str(alias) for alias in aliases if str(alias).strip())),
        source=REVIEWED_ALIAS,
        source_ids=list(source_ids),
        version=SEMANTIC_IDENTITY_VERSION,
    )
    registry.register_projection(ref, mode=mode)
    return ref


def project_reviewed_metadata(registry: SemanticIdentityRegistry, records: Iterable[dict[str, Any]], schema: Any) -> int:
    """Register the human-reviewed values of ``records`` as identities of their field's kind.

    Unreviewed model output is never an identity source. Returns the number of values seen.
    """
    seen = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        migrate_record_assertions(record, schema)
        for assertion in current_assertions(record):
            name = str(assertion.field_name or "")
            if assertion.value_status != "present" or assertion.authority_status not in _REVIEWED_AUTHORITY:
                continue
            try:
                profile = schema.equivalence_profile_for(name)
            except KeyError:
                continue
            if profile.mode not in {"entity_name", "text", "lexical_phrase", "controlled"}:
                continue
            kind = str(profile.identity_kind or "value")
            values = assertion.value if isinstance(assertion.value, list) else [assertion.value]
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    continue
                seen += 1
                key = surface_key(value, profile.mode)
                registry.register_projection(
                    SemanticIdentityRef(
                        identity_id=_identity_id(kind, REVIEWED_METADATA, str(profile.mode), key),
                        kind=kind,
                        canonical_label=value,
                        aliases=[value],
                        source=REVIEWED_METADATA,
                        source_ids=[str(assertion.assertion_id)],
                    ),
                    mode=profile.mode,
                )
    return seen


def _document_clusters(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Entity clusters from a whole-document analysis or from one Record's projection."""
    clusters = [item for item in (payload.get("entity_clusters") or []) if isinstance(item, dict)]
    if clusters:
        return clusters
    grouped: dict[str, dict[str, Any]] = {}
    for mention in payload.get("entities") or []:
        if not isinstance(mention, dict) or not mention.get("entity_id"):
            continue
        cluster = grouped.setdefault(str(mention["entity_id"]), {
            "cluster_id": str(mention["entity_id"]),
            "canonical": str(mention.get("label") or ""),
            "aliases": [],
            "entity_type": str(mention.get("entity_type") or ""),
        })
        if str(mention.get("text") or "").strip():
            cluster["aliases"].append(str(mention["text"]))
    return list(grouped.values())


def project_document_intelligence(
    registry: SemanticIdentityRegistry,
    payload: dict[str, Any] | None,
    *,
    kinds: dict[str, str] | None = None,
) -> int:
    """Register provider entity clusters as advisory identities; returns clusters registered.

    ``payload`` is a document analysis or a Record's ``document_intelligence`` projection. A
    Record projection bound to other text is stale and contributes nothing.
    """
    if not isinstance(payload, dict) or payload.get("status") not in (None, "ok", "complete"):
        return 0
    kind_map = kinds or _PROVIDER_KINDS
    provider = str(payload.get("provider") or "")
    model = str(payload.get("model") or "")
    registered = 0
    for cluster in _document_clusters(payload):
        kind = kind_map.get(str(cluster.get("entity_type") or "").upper())
        cluster_id = str(cluster.get("cluster_id") or "")
        aliases = [str(value) for value in (cluster.get("aliases") or []) if str(value).strip()]
        label = str(cluster.get("canonical") or (aliases[0] if aliases else ""))
        if not kind or not cluster_id or not label:
            continue
        mode = "entity_name" if kind == "person" else "text"
        registry.register_projection(
            SemanticIdentityRef(
                identity_id=_identity_id(kind, DOCUMENT_INTELLIGENCE, provider, model, cluster_id),
                kind=kind,
                canonical_label=label,
                aliases=list(dict.fromkeys([label, *aliases])),
                source=DOCUMENT_INTELLIGENCE,
                source_ids=[f"{provider or 'provider'}:{model}:{cluster_id}"],
            ),
            mode=mode,
        )
        registered += 1
    return registered


def registry_for_record(record: dict[str, Any], text_sha256: str | None = None, *, parent: SemanticIdentityRegistry | None = None) -> SemanticIdentityRegistry:
    """A registry from one Record's current Document Intelligence projection.

    ``text_sha256`` is the digest of the Record's current text; a projection bound to other
    text is ignored rather than trusted.
    """
    registry = SemanticIdentityRegistry(parent)
    projection = record.get("document_intelligence") if isinstance(record, dict) else None
    if isinstance(projection, dict):
        bound = projection.get("record_text_sha256")
        if text_sha256 is None:
            text_sha256 = hashlib.sha256(str(record.get("text") or "").encode("utf-8")).hexdigest()
        if not bound or bound == text_sha256:
            project_document_intelligence(registry, projection)
    return registry


def compare_field_values(
    schema: Any,
    field: str,
    left: Any,
    right: Any,
    *,
    record: dict[str, Any] | None = None,
    registry: SemanticIdentityRegistry | None = None,
) -> ValueEquivalenceResult:
    """Compare two values of one schema field under that field's equivalence policy.

    With a ``record`` and no ``registry``, the Record's own current Document Intelligence
    projection is consulted. A field the schema does not know compares exactly.
    """
    try:
        profile = schema.equivalence_profile_for(field) if schema is not None else EquivalenceProfile(mode="exact")
    except KeyError:
        profile = EquivalenceProfile(mode="exact", identity_kind="value")
    if registry is None and isinstance(record, dict):
        registry = registry_for_record(record)
    language = str((record or {}).get("language") or "")
    return compare_values(left, right, profile=profile, language=language, registry=registry)
