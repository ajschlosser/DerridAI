# Copyright 2026 Aaron John Schlosser, PhD.
"""Read-only System Data projection for progressive metadata exemplars.

The public contract is intentionally semantic rather than vector-oriented.
Chroma is only the current derived-storage implementation; callers see
reviewed metadata exemplars and their provenance/audit fields.
"""

from __future__ import annotations

import json
from typing import Any

from .chroma_store import ChromaStore, decode_metadata

_COLLECTION_NAME = "derridai_metadata_exemplars"


def _json(value: Any, fallback: Any) -> Any:
    if not isinstance(value, str):
        return value if value is not None else fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _where(
    *,
    field: str = "",
    kind: str = "",
    language: str = "",
    scope_id: str = "",
    schema_id: str = "",
    record_id: str = "",
) -> dict[str, Any] | None:
    terms = []
    for key, value in (
        ("field_name", field),
        ("kind", kind),
        ("language", language),
        ("scope_id", scope_id),
        ("schema_id", schema_id),
        ("record_id", record_id),
    ):
        if str(value or "").strip():
            terms.append({key: str(value).strip()})
    if not terms:
        return None
    return {"$and": terms} if len(terms) > 1 else terms[0]


class MetadataExemplarInspector:
    """Expose the derived exemplar projection as read-only system data."""

    def __init__(self, store: ChromaStore) -> None:
        self._store = store

    def rows(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        field: str = "",
        kind: str = "",
        language: str = "",
        scope_id: str = "",
        schema_id: str = "",
        record_id: str = "",
    ) -> dict[str, Any]:
        try:
            collection = self._store.client.get_collection(name=_COLLECTION_NAME)
        except Exception as exc:
            missing = getattr(self._store, "_is_missing_collection_error", None)
            if callable(missing) and missing(exc):
                return {
                    "exists": False,
                    "count": 0,
                    "limit": limit,
                    "offset": offset,
                    "rows": [],
                    "facets": self._empty_facets(),
                }
            if not callable(missing) and "not found" in str(exc).casefold():
                return {
                    "exists": False,
                    "count": 0,
                    "limit": limit,
                    "offset": offset,
                    "rows": [],
                    "facets": self._empty_facets(),
                }
            raise

        where = _where(
            field=field,
            kind=kind,
            language=language,
            scope_id=scope_id,
            schema_id=schema_id,
            record_id=record_id,
        )
        all_kwargs: dict[str, Any] = {"include": ["metadatas"]}
        if where:
            all_kwargs["where"] = where
        all_payload = collection.get(**all_kwargs)
        all_ids = [str(value) for value in (all_payload.get("ids") or [])]
        all_metadata = [
            decode_metadata(value if isinstance(value, dict) else {})
            for value in (all_payload.get("metadatas") or [])
        ]

        page_kwargs: dict[str, Any] = {
            "limit": max(1, int(limit)),
            "offset": max(0, int(offset)),
            "include": ["documents", "metadatas"],
        }
        if where:
            page_kwargs["where"] = where
        payload = collection.get(**page_kwargs)
        ids = [str(value) for value in (payload.get("ids") or [])]
        documents = list(payload.get("documents") or [])
        metadatas = list(payload.get("metadatas") or [])

        rows = []
        for index, exemplar_id in enumerate(ids):
            metadata = decode_metadata(
                metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            )
            rows.append(
                {
                    "exemplar_id": exemplar_id,
                    "scope_id": str(metadata.get("scope_id") or ""),
                    "record_id": str(metadata.get("record_id") or ""),
                    "record_revision": metadata.get("record_revision"),
                    "source_document_id": str(metadata.get("source_document_id") or ""),
                    "field_name": str(metadata.get("field_name") or ""),
                    "field_value": _json(metadata.get("field_value_json"), None),
                    "kind": str(metadata.get("kind") or "positive"),
                    "assertion_status": str(metadata.get("assertion_status") or ""),
                    "schema_id": str(metadata.get("schema_id") or ""),
                    "schema_version": str(metadata.get("schema_version") or ""),
                    "language": str(metadata.get("language") or ""),
                    "region_type": str(metadata.get("region_type") or ""),
                    "evidence_hash": str(metadata.get("evidence_hash") or ""),
                    "evidence_block_ids": _json(
                        metadata.get("evidence_block_ids_json"),
                        [],
                    ),
                    "context_text": str(
                        documents[index] if index < len(documents) else ""
                    ),
                }
            )

        return {
            "exists": True,
            "count": len(all_ids),
            "limit": max(1, int(limit)),
            "offset": max(0, int(offset)),
            "rows": rows,
            "facets": self._facets(all_metadata),
        }

    @staticmethod
    def _empty_facets() -> dict[str, list[str]]:
        return {
            "fields": [],
            "kinds": [],
            "languages": [],
            "scopes": [],
            "schemas": [],
        }

    @classmethod
    def _facets(cls, rows: list[dict[str, Any]]) -> dict[str, list[str]]:
        mapping = {
            "fields": "field_name",
            "kinds": "kind",
            "languages": "language",
            "scopes": "scope_id",
            "schemas": "schema_id",
        }
        return {
            name: sorted(
                {
                    str(row.get(field) or "").strip()
                    for row in rows
                    if str(row.get(field) or "").strip()
                },
                key=str.casefold,
            )
            for name, field in mapping.items()
        }
