# Copyright 2026 Aaron John Schlosser, PhD.
"""Reusable derived embeddings for immutable source units and source blocks.

Source text and its block identity remain authoritative in the corpus files.
This module owns only a rebuildable vector projection so callers such as
metadata-memory prefill can reuse source embeddings without embedding the same
text on every pass.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, cast

from .config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "derridai_source_unit_embeddings"
SOURCE_BLOCK_COLLECTION_NAME = COLLECTION_NAME
SYSTEM_KIND = "source_unit_embeddings"
PROJECTION_VERSION = 1
IDENTITY_VERSION = "source-unit-embedding-v1"
TEXT_FIELD = "text"
FILTER_FIELDS = ["source_document_id", "source_unit_id", "text_hash"]

_SCHEMA_KEY = "derridai_source_embedding_schema"
_FALLBACK_STATE_KEY = "_derridai_source_embedding_projection"


def _normalise(value: Any) -> str:
    return str(value or "").strip()


def text_hash(text: Any) -> str:
    """Return the content identity used to invalidate a changed source unit."""

    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def source_unit_identity(source_document_id: Any, source_unit_id: Any) -> str:
    """Return the stable identity of one source unit, independent of its text."""

    document = _normalise(source_document_id)
    unit = _normalise(source_unit_id)
    digest = hashlib.sha256(f"{document}\0{unit}".encode()).hexdigest()
    return f"su-{digest}"


def embedding_identity(
    source_document_id: Any,
    source_unit_id: Any,
    text: Any,
    *,
    provider: Any = "",
    model: Any = "",
) -> str:
    """Return the vector identity, including source content and model contract."""

    parts = (
        IDENTITY_VERSION,
        source_unit_identity(source_document_id, source_unit_id),
        text_hash(text),
        _normalise(provider),
        _normalise(model),
    )
    return "emb-" + hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _unit_id(block: dict[str, Any]) -> str:
    return _normalise(block.get("source_unit_id") or block.get("block_id"))


def _provider_model(store: Any, provider: str | None, model: str | None) -> tuple[str, str | None]:
    if provider:
        resolved_provider = _normalise(provider)
        resolved_model = _normalise(model) or None
    else:
        default_spec = getattr(store, "default_embedding_spec", None)
        resolved_provider, resolved_model = default_spec() if callable(default_spec) else ("", None)
        resolved_provider = _normalise(resolved_provider)
        resolved_model = _normalise(resolved_model) or None
    if not resolved_provider.startswith("profile:"):
        resolved_provider = resolved_provider.lower()
    return resolved_provider, resolved_model


class SourceEmbeddingProjection:
    """Persist and reuse embeddings for the current source-unit snapshot."""

    SYSTEM_KIND = SYSTEM_KIND
    SCHEMA_VERSION = PROJECTION_VERSION

    def __init__(self, store: Any | None = None, *, collection_name: str = COLLECTION_NAME) -> None:
        if store is None:
            from .chroma_store import ChromaStore

            store = ChromaStore()
        self.store = store
        self.collection_name = _normalise(collection_name) or COLLECTION_NAME

    def _has_vector_backend(self) -> bool:
        return hasattr(self.store, "client") and callable(getattr(self.store, "create_store", None))

    def _collection(self, provider: str, model: str | None) -> Any:
        if not self._has_vector_backend():
            return None
        expected_provider, expected_model = _provider_model(self.store, provider, model)
        try:
            collection = self.store.client.get_collection(name=self.collection_name)
            metadata = dict(getattr(collection, "metadata", None) or {})
            current_provider, current_model = expected_provider, expected_model
            embedding_spec = getattr(self.store, "_embedding_spec", None)
            if callable(embedding_spec):
                current_provider, current_model = embedding_spec(collection)
            valid = (
                int(metadata.get(_SCHEMA_KEY) or 0) == self.SCHEMA_VERSION
                and str(metadata.get("derridai_system_collection") or "") == SYSTEM_KIND
                and current_provider == expected_provider
                and (current_model or None) == (expected_model or None)
            )
            if valid:
                return collection
            self.store.client.delete_collection(name=self.collection_name)
        except Exception as exc:
            missing = getattr(self.store, "_is_missing_collection_error", None)
            if callable(missing) and not missing(exc):
                raise
            if not callable(missing) and not (
                isinstance(exc, KeyError)
                or "not found" in str(exc).casefold()
                or "does not exist" in str(exc).casefold()
            ):
                raise

        try:
            self.store.create_store(
                self.collection_name,
                description="Derived source-unit embeddings.",
                embedding_provider=expected_provider,
                embedding_model=expected_model,
                retrieval_mode="semantic",
                text_field=TEXT_FIELD,
                filter_fields=list(FILTER_FIELDS),
                collection_role="general",
                protected=True,
                metadata={
                    "derridai_system_collection": SYSTEM_KIND,
                    "derridai_hidden_system_collection": True,
                    "derridai_derived": True,
                    _SCHEMA_KEY: self.SCHEMA_VERSION,
                },
            )
        except Exception as exc:
            message = str(exc).casefold()
            if "already exists" not in message and "unique" not in message:
                raise
        return self.store.client.get_collection(name=self.collection_name)

    def _fallback_rows(self, provider: str, model: str | None) -> dict[str, dict[str, Any]]:
        """Keep lightweight fakes and non-Chroma adapters on the same contract."""

        state = getattr(self.store, _FALLBACK_STATE_KEY, None)
        contract = (provider, model or None)
        if not isinstance(state, dict) or state.get("contract") != contract:
            state = {"contract": contract, "rows": {}}
            setattr(self.store, _FALLBACK_STATE_KEY, state)
        return cast(dict[str, dict[str, Any]], state["rows"])

    @staticmethod
    def _rows(blocks: list[dict[str, Any]], source_document_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for block in blocks:
            if not isinstance(block, dict):
                continue
            unit_id = _unit_id(block)
            text = str(block.get("text") or "")
            if not unit_id or not text.strip() or unit_id in seen:
                continue
            seen.add(unit_id)
            rows.append({
                "source_document_id": source_document_id,
                "source_unit_id": unit_id,
                "block_id": _normalise(block.get("block_id") or unit_id),
                "text": text,
                "text_hash": text_hash(text),
            })
        return rows

    def _batch_size(self) -> int:
        """Return a safe ceiling for embedding requests and Chroma mutations.

        API_BATCH_SIZE remains the application-level resource bound. Chroma
        also exposes a backend-specific maximum that can vary with the storage
        implementation, so honor the smaller value when the client reports it.
        """

        configured = max(1, int(getattr(settings, "api_batch_size", 128) or 128))
        try:
            client = getattr(self.store, "client", None)
        except Exception:
            # Batch-size discovery is advisory. A provider/store adapter without
            # a readable client still receives the conservative application cap.
            client = None
        if client is None:
            return configured

        for attribute in ("get_max_batch_size", "max_batch_size"):
            try:
                value = getattr(client, attribute, None)
                value = value() if callable(value) else value
                maximum = int(value)
            except Exception:
                logger.debug(
                    "Could not resolve source embedding batch size from %s.",
                    attribute,
                    exc_info=True,
                )
                continue
            if maximum > 0:
                return min(configured, maximum)
        return configured

    def sync(
        self,
        source_document_id: str,
        blocks: list[dict[str, Any]],
        *,
        provider: str | None = None,
        model: str | None = None,
        prune: bool = True,
    ) -> dict[str, int]:
        """Synchronize one source snapshot, embedding only new or changed text.

        ``prune=False`` is for callers that provide a partial view (for example
        a record's reviewable blocks) rather than the complete source snapshot.
        """

        document_id = _normalise(source_document_id)
        if not document_id:
            raise ValueError("A source document ID is required for source embeddings.")
        resolved_provider, resolved_model = _provider_model(self.store, provider, model)
        collection = self._collection(resolved_provider, resolved_model)
        desired = self._rows(blocks, document_id)
        if collection is None:
            rows = self._fallback_rows(resolved_provider, resolved_model)
            existing = {
                key: value for key, value in rows.items()
                if str(value.get("source_document_id") or "") == document_id
            }
            stale = (
                set(existing) - {_unit_id(row) for row in desired}
                if prune
                else set()
            )
            fallback_pending: list[dict[str, Any]] = []
            reused = 0
            for row in desired:
                prior = existing.get(row["source_unit_id"])
                identity = embedding_identity(
                    document_id, row["source_unit_id"], row["text"],
                    provider=resolved_provider, model=resolved_model,
                )
                if prior and prior.get("embedding_identity") == identity:
                    reused += 1
                    continue
                fallback_pending.append(row)
            batch_size = self._batch_size()
            vectors, embedding_batches = self._embed_unique(
                fallback_pending,
                resolved_provider,
                resolved_model,
                batch_size=batch_size,
            )
            embedded = len({row["text_hash"] for row in fallback_pending})
            vector_by_hash = {
                row["text_hash"]: vector for row, vector in zip(fallback_pending, vectors)
            }
            for row in desired:
                prior = existing.get(row["source_unit_id"])
                identity = embedding_identity(
                    document_id, row["source_unit_id"], row["text"],
                    provider=resolved_provider, model=resolved_model,
                )
                if prior and prior.get("embedding_identity") == identity:
                    continue
                rows[row["source_unit_id"]] = {
                    **row,
                    "embedding_identity": identity,
                    "embedding": vector_by_hash[row["text_hash"]],
                }
            for unit_id in stale:
                rows.pop(unit_id, None)
            return {
                "desired": len(desired),
                "embedded": embedded,
                "reused": reused,
                "upserted": len(fallback_pending),
                "deleted": len(stale),
                "batch_size": batch_size,
                "embedding_batches": embedding_batches,
                "upsert_batches": 0,
                "delete_batches": 0,
                "batches": embedding_batches,
            }

        payload = collection.get(
            where={"source_document_id": document_id},
            include=["metadatas"],
        )
        current: dict[str, dict[str, Any]] = {}
        for metadata in payload.get("metadatas") or []:
            if isinstance(metadata, dict) and _normalise(metadata.get("source_unit_id")):
                current[_normalise(metadata["source_unit_id"])] = metadata
        desired_ids = {_unit_id(row) for row in desired}
        # Chroma returns IDs and metadata in matching order; use that relationship
        # directly instead of making source-unit IDs part of the storage contract.
        stale_ids = [
            str(storage_id)
            for storage_id, metadata in zip(payload.get("ids") or [], payload.get("metadatas") or [])
            if prune
            and isinstance(metadata, dict)
            and _normalise(metadata.get("source_unit_id")) not in desired_ids
        ]
        chroma_pending: list[dict[str, Any]] = []
        for row in desired:
            identity = embedding_identity(
                document_id, row["source_unit_id"], row["text"],
                provider=resolved_provider, model=resolved_model,
            )
            prior = current.get(row["source_unit_id"])
            if not prior or str(prior.get("embedding_identity") or "") != identity:
                chroma_pending.append({**row, "embedding_identity": identity})
        batch_size = self._batch_size()
        vectors, embedding_batches = self._embed_unique(
            chroma_pending,
            resolved_provider,
            resolved_model,
            batch_size=batch_size,
        )

        # Write current source units before pruning stale ones. If an embedding
        # provider or later upsert fails, the previous rebuildable projection is
        # left available instead of deleting known-good rows first.
        upsert_batches = 0
        for start in range(0, len(chroma_pending), batch_size):
            batch = chroma_pending[start : start + batch_size]
            batch_vectors = vectors[start : start + batch_size]
            collection.upsert(
                ids=[
                    source_unit_identity(document_id, row["source_unit_id"])
                    for row in batch
                ],
                documents=[row["text"] for row in batch],
                metadatas=batch,
                embeddings=batch_vectors,
            )
            upsert_batches += 1

        delete_batches = 0
        for start in range(0, len(stale_ids), batch_size):
            collection.delete(ids=stale_ids[start : start + batch_size])
            delete_batches += 1

        return {
            "desired": len(desired),
            "embedded": len({row["text_hash"] for row in chroma_pending}),
            "reused": len(desired) - len(chroma_pending),
            "upserted": len(chroma_pending),
            "deleted": len(stale_ids),
            "batch_size": batch_size,
            "embedding_batches": embedding_batches,
            "upsert_batches": upsert_batches,
            "delete_batches": delete_batches,
            "batches": embedding_batches + upsert_batches + delete_batches,
        }

    def _embed_unique(
        self,
        rows: list[dict[str, Any]],
        provider: str,
        model: str | None,
        *,
        batch_size: int | None = None,
    ) -> tuple[list[list[float]], int]:
        if not rows:
            return [], 0
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if row["text_hash"] not in seen:
                seen.add(row["text_hash"])
                unique.append(row)

        ceiling = max(1, int(batch_size or self._batch_size()))
        vectors: list[list[float]] = []
        batches = 0
        for start in range(0, len(unique), ceiling):
            batch = unique[start : start + ceiling]
            batch_vectors = self.store.embeddings.embed(
                [row["text"] for row in batch],
                [{} for _ in batch],
                "embedding",
                provider=provider,
                model=model,
            )
            if len(batch_vectors) != len(batch):
                raise RuntimeError(
                    "The embedding provider returned an unexpected number of source-unit vectors."
                )
            vectors.extend(batch_vectors)
            batches += 1

        vector_by_hash = {
            row["text_hash"]: vector for row, vector in zip(unique, vectors)
        }
        return [vector_by_hash[row["text_hash"]] for row in rows], batches

    def embeddings_for(
        self,
        source_document_id: str,
        unit_ids: list[str],
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, list[float]]:
        """Return already synchronized vectors keyed by source-unit ID."""

        resolved_provider, resolved_model = _provider_model(self.store, provider, model)
        collection = self._collection(resolved_provider, resolved_model)
        wanted = {_normalise(value) for value in unit_ids if _normalise(value)}
        if collection is None:
            rows = self._fallback_rows(resolved_provider, resolved_model)
            return {
                unit_id: list(row["embedding"])
                for unit_id, row in rows.items()
                if str(row.get("source_document_id") or "") == str(source_document_id)
                and unit_id in wanted and isinstance(row.get("embedding"), list)
            }
        payload = collection.get(
            where={"source_document_id": _normalise(source_document_id)},
            include=["metadatas", "embeddings"],
        )
        # Chroma may return `embeddings` as a numpy array, whose truth value with more than
        # one row is ambiguous; convert to a list before any `or` fallback.
        raw_embeddings = payload.get("embeddings")
        embeddings = (
            raw_embeddings.tolist() if hasattr(raw_embeddings, "tolist") else raw_embeddings
        ) or []
        vectors: dict[str, list[float]] = {}
        for metadata, vector in zip(payload.get("metadatas") or [], embeddings):
            if not isinstance(metadata, dict):
                continue
            unit_id = _normalise(metadata.get("source_unit_id"))
            if unit_id in wanted and isinstance(vector, (list, tuple)):
                vectors[unit_id] = [float(value) for value in vector]
        return vectors

    def embed_query(
        self,
        query: str,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[float]:
        """Embed one field-aware query under the same contract as source units."""

        resolved_provider, resolved_model = _provider_model(self.store, provider, model)
        embed_query = getattr(self.store.embeddings, "embed_query", None)
        if callable(embed_query):
            vector = embed_query(
                str(query or ""),
                provider=resolved_provider,
                model=resolved_model,
            )
        else:
            vectors = self.store.embeddings.embed(
                [str(query or "")],
                [{}],
                "embedding",
                provider=resolved_provider,
                model=resolved_model,
            )
            vector = vectors[0] if vectors else []
        return [float(value) for value in vector]




SourceBlockEmbeddingProjection = SourceEmbeddingProjection
source_block_embedding_identity = embedding_identity
