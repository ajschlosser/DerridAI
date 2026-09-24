# Copyright 2026 Aaron John Schlosser, PhD.
"""Backend-neutral inspection of DerridAI's learned metadata precedents.

The product surface exposes *metadata memory*, not Chroma collections.  Today the
service reads the progressive evidence-bound projection and, when present, the
semantic reviewer-memory projection introduced by PR #145.  Both are derived
storage details: rows are normalized into one scholarly/audit contract and
duplicate decisions prefer the richer evidence-bound representation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .metadata_exemplar_retrieval import COLLECTION_NAME

PR145_COLLECTION_NAME = "derridai_metadata_memory"
SYSTEM_KINDS = {"metadata_exemplars", "metadata_memory"}
PAGE_SCAN_SIZE = 500


def _decode_json(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else value


def _text(value: Any) -> str:
    return str(value or "").strip()


def _memory_kind(collection: Any) -> str:
    metadata = dict(getattr(collection, "metadata", None) or {})
    declared = _text(metadata.get("derridai_system_collection"))
    if declared in SYSTEM_KINDS:
        return declared
    name = _text(getattr(collection, "name", ""))
    if name == COLLECTION_NAME:
        return "metadata_exemplars"
    if name == PR145_COLLECTION_NAME:
        return "metadata_memory"
    return ""


def _normalized_item(
    memory_kind: str,
    item_id: str,
    document: Any,
    metadata: Mapping[str, Any],
) -> dict[str, Any] | None:
    if memory_kind == "metadata_exemplars":
        field = _text(metadata.get("field_name"))
        record_id = _text(metadata.get("record_id"))
        if not field or not record_id:
            return None
        block_ids = _decode_json(metadata.get("evidence_block_ids_json"), [])
        if not isinstance(block_ids, list):
            block_ids = []
        return {
            "id": _text(metadata.get("metadata_exemplar_id")) or item_id,
            "memory_type": "evidence_bound",
            "kind": _text(metadata.get("kind")) or "positive",
            "field": field,
            "value": _decode_json(metadata.get("field_value_json")),
            "rejected_value": _decode_json(metadata.get("rejected_value_json")),
            "authority": _text(metadata.get("assertion_status")),
            "review_method": _text(metadata.get("assertion_method")),
            "record_id": record_id,
            "record_revision": metadata.get("record_revision"),
            "build_id": _text(metadata.get("scope_id")),
            "source_document_id": _text(metadata.get("source_document_id")),
            "schema_id": _text(metadata.get("schema_id")),
            "schema_version": _text(metadata.get("schema_version")),
            "language": _text(metadata.get("language")),
            "region_type": _text(metadata.get("region_type")),
            "page_start": metadata.get("page_start"),
            "page_end": metadata.get("page_end"),
            "reviewed_at": _text(metadata.get("reviewed_at")),
            "evidence_bound": True,
            "evidence_hash": _text(metadata.get("evidence_hash")),
            "evidence_block_ids": [str(value) for value in block_ids if str(value)],
            "evidence_text": "",
            "context_text": str(document or metadata.get("context_text") or ""),
        }

    if memory_kind == "metadata_memory":
        field = _text(metadata.get("memory_field") or metadata.get("field"))
        record_id = _text(metadata.get("source_record_id") or metadata.get("record_id"))
        if not field or not record_id:
            return None
        return {
            "id": item_id,
            "memory_type": "reviewer_memory",
            "kind": "positive",
            "field": field,
            "value": _decode_json(metadata.get("memory_value")),
            "rejected_value": None,
            "authority": _text(metadata.get("status")) or "human_confirmed",
            "review_method": "",
            "record_id": record_id,
            "record_revision": metadata.get("record_revision"),
            "build_id": _text(metadata.get("build_id")),
            "source_document_id": _text(metadata.get("source_document_id")),
            "schema_id": _text(metadata.get("schema_id")),
            "schema_version": _text(metadata.get("schema_version")),
            "language": _text(metadata.get("language")),
            "region_type": _text(metadata.get("region_type")),
            "page_start": metadata.get("page_start"),
            "page_end": metadata.get("page_end"),
            "reviewed_at": _text(metadata.get("reviewed_at")),
            "evidence_bound": False,
            "evidence_hash": "",
            "evidence_block_ids": [],
            "evidence_text": "",
            "context_text": str(document or metadata.get("text") or ""),
        }
    return None


def _dedupe_key(item: Mapping[str, Any]) -> tuple[str, str, str, str]:
    value = json.dumps(item.get("value"), ensure_ascii=False, sort_keys=True, default=str)
    return (
        _text(item.get("record_id")),
        _text(item.get("field")),
        value,
        _text(item.get("kind")) or "positive",
    )


class MetadataMemoryService:
    """Read-only audit view over whichever derived metadata-memory backends exist."""

    def __init__(self, store: Any, corpus_repository: Any | None = None) -> None:
        self.store = store
        self.corpus_repository = corpus_repository

    def _collections(self) -> list[tuple[Any, str]]:
        output: list[tuple[Any, str]] = []
        for listed in self.store.client.list_collections():
            name = listed.name if hasattr(listed, "name") else str(listed)
            collection = self.store.client.get_collection(name=name)
            kind = _memory_kind(collection)
            if kind:
                output.append((collection, kind))
        return output

    @staticmethod
    def _scan(collection: Any) -> list[tuple[str, Any, Mapping[str, Any]]]:
        total = int(collection.count())
        output: list[tuple[str, Any, Mapping[str, Any]]] = []
        for offset in range(0, total, PAGE_SCAN_SIZE):
            payload = collection.get(
                limit=PAGE_SCAN_SIZE,
                offset=offset,
                include=["documents", "metadatas"],
            )
            ids = list(payload.get("ids") or [])
            docs = list(payload.get("documents") or [])
            metas = list(payload.get("metadatas") or [])
            for index, value in enumerate(ids):
                metadata = metas[index] if index < len(metas) and isinstance(metas[index], dict) else {}
                document = docs[index] if index < len(docs) else ""
                output.append((str(value), document, metadata))
        return output

    def _resolve_evidence(self, item: dict[str, Any], caches: dict[str, Any]) -> None:
        if not item.get("evidence_bound") or not item.get("build_id") or not self.corpus_repository:
            return
        build_id = str(item["build_id"])
        try:
            build = caches.setdefault("builds", {}).get(build_id)
            if build is None:
                build = self.corpus_repository.get_build(build_id)
                caches["builds"][build_id] = build
            asset_id = _text(build.get("asset_id"))
            if not asset_id:
                return
            blocks = caches.setdefault("blocks", {}).get(asset_id)
            if blocks is None:
                blocks = {
                    _text(block.get("block_id")): block
                    for block in self.corpus_repository.load_blocks(asset_id)
                    if isinstance(block, dict) and _text(block.get("block_id"))
                }
                caches["blocks"][asset_id] = blocks
            texts = [
                _text(blocks.get(block_id, {}).get("text"))
                for block_id in item.get("evidence_block_ids") or []
                if _text(blocks.get(block_id, {}).get("text"))
            ]
            if texts:
                resolved_evidence = "\n\n".join(texts)
                item["evidence_text"] = resolved_evidence
                expected_hash = _text(item.get("evidence_hash"))
                item["evidence_current"] = (
                    not expected_hash
                    or hashlib.sha256(resolved_evidence.encode("utf-8")).hexdigest()
                    == expected_hash
                )
            elif item.get("evidence_block_ids"):
                item["evidence_current"] = False

            records = caches.setdefault("records", {}).get(build_id)
            if records is None:
                records = {
                    _text(record.get("record_id")): record
                    for record in self.corpus_repository.load_records(build_id)
                    if isinstance(record, dict) and _text(record.get("record_id"))
                }
                caches["records"][build_id] = records
            source_record = records.get(_text(item.get("record_id")))
            if source_record:
                current_revision = source_record.get("record_revision")
                expected_revision = item.get("record_revision")
                item["source_current"] = (
                    expected_revision in (None, "")
                    or current_revision in (None, "")
                    or str(current_revision) == str(expected_revision)
                )
            else:
                item["source_current"] = False
        except Exception:
            # The memory remains inspectable even if its canonical source has
            # moved or a build is unavailable.  The UI marks unresolved sources
            # instead of making an audit screen fail wholesale.
            item["source_current"] = False
            if item.get("evidence_bound"):
                item["evidence_current"] = False

    def list_entries(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        field: str = "",
        kind: str = "",
        build_id: str = "",
        language: str = "",
        query: str = "",
    ) -> dict[str, Any]:
        """Return normalized, deduplicated metadata memory without exposing storage names."""

        field = _text(field)
        kind = _text(kind)
        build_id = _text(build_id)
        language = _text(language)
        needle = _text(query).casefold()

        merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        backend_count = 0
        try:
            collections = self._collections()
        except Exception as exc:
            return {
                "items": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
                "summary": {
                    "entries": 0,
                    "evidence_bound": 0,
                    "corrections": 0,
                    "fields": 0,
                    "backends": 0,
                },
                "facets": {"fields": [], "kinds": [], "languages": [], "builds": []},
                "derived": True,
                "authoritative_source": "reviewed corpus metadata and evidence",
                "available": False,
                "error": str(exc),
            }

        for collection, memory_kind in collections:
            backend_count += 1
            for item_id, document, metadata in self._scan(collection):
                item = _normalized_item(memory_kind, item_id, document, metadata)
                if item is None:
                    continue
                key = _dedupe_key(item)
                prior = merged.get(key)
                # Evidence-bound exemplars win over older/general semantic
                # reviewer memory for the same reviewed decision.
                if prior is None or (
                    item.get("evidence_bound") and not prior.get("evidence_bound")
                ):
                    merged[key] = item

        items = list(merged.values())
        if field:
            items = [item for item in items if item.get("field") == field]
        if kind:
            items = [item for item in items if item.get("kind") == kind]
        if build_id:
            items = [item for item in items if item.get("build_id") == build_id]
        if language:
            items = [item for item in items if item.get("language") == language]
        if needle:
            def searchable(item: Mapping[str, Any]) -> str:
                return " ".join(
                    [
                        _text(item.get("field")),
                        _text(item.get("record_id")),
                        _text(item.get("build_id")),
                        _text(item.get("schema_id")),
                        _text(item.get("language")),
                        json.dumps(item.get("value"), ensure_ascii=False, default=str),
                        _text(item.get("context_text")),
                    ]
                ).casefold()
            items = [item for item in items if needle in searchable(item)]

        items.sort(
            key=lambda item: (
                _text(item.get("field")).casefold(),
                _text(item.get("record_id")).casefold(),
                _text(item.get("id")).casefold(),
            )
        )
        caches: dict[str, Any] = {}
        page = items[offset : offset + limit]
        for item in page:
            self._resolve_evidence(item, caches)

        all_items = list(merged.values())
        return {
            "items": page,
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "summary": {
                "entries": len(all_items),
                "evidence_bound": sum(1 for item in all_items if item.get("evidence_bound")),
                "corrections": sum(1 for item in all_items if item.get("kind") == "correction"),
                "fields": len({_text(item.get("field")) for item in all_items if _text(item.get("field"))}),
                "backends": backend_count,
            },
            "facets": {
                "fields": sorted({_text(item.get("field")) for item in all_items if _text(item.get("field"))}, key=str.casefold),
                "kinds": sorted({_text(item.get("kind")) for item in all_items if _text(item.get("kind"))}, key=str.casefold),
                "languages": sorted({_text(item.get("language")) for item in all_items if _text(item.get("language"))}, key=str.casefold),
                "builds": sorted({_text(item.get("build_id")) for item in all_items if _text(item.get("build_id"))}, key=str.casefold),
            },
            "derived": True,
            "authoritative_source": "reviewed corpus metadata and evidence",
            "available": True,
            "error": "",
        }
