# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import gc
import hashlib
import json
import logging
import math
import re
import shutil
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
import httpx

from .chroma_connection import (
    DEFAULT_DATABASE,
    DEFAULT_HTTP_URL,
    DEFAULT_TENANT,
    connection_identity,
    http_client_kwargs,
    normalize_mode,
    parse_http_endpoint,
    public_http_config,
)
from .config import APP_VERSION, settings

logger = logging.getLogger(__name__)

_JSON_PREFIX = "__json__:"


class StoreAlreadyExistsError(ValueError):
    """Raised when strict collection creation collides with an existing name."""


def encode_metadata(
    record: dict[str, Any],
    *,
    document_field: str,
    embedding_field: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key, value in record.items():
        if key in {document_field, embedding_field, "_chroma_id"} or key.startswith("_chroma_"):
            continue
        if value is None:
            continue
        if key == "updates" and isinstance(value, list):
            metadata["_updates_count"] = len(value)
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        else:
            metadata[key] = _JSON_PREFIX + json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )
    return metadata


def decode_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    out: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and value.startswith(_JSON_PREFIX):
            try:
                out[key] = json.loads(value[len(_JSON_PREFIX):])
            except json.JSONDecodeError:
                out[key] = value
        else:
            out[key] = value
    return out


def compact_record_payload(record: dict[str, Any], *, include_updates: bool = False) -> dict[str, Any]:
    """Return a record suitable for ordinary API/RAG transport.

    ``updates`` is intentionally omitted unless a caller explicitly asks for
    history.  A tiny count is retained so list/search UIs can still indicate
    that history exists without shipping the history itself.
    """
    out = dict(record)
    updates = out.get("updates")
    if not include_updates:
        out.pop("updates", None)
        if isinstance(updates, list) and updates:
            out["_updates_count"] = len(updates)
    return out


def compact_nested_record_payloads(value: Any) -> Any:
    """Compact record objects nested inside transport/cache payloads.

    RAG evidence and selected-evidence request entries wrap records under a
    ``record`` key.  Older response-cache rows can therefore still contain a
    historical ``updates`` array even after ordinary store reads became
    compact.  Walk only those explicit record wrappers rather than deleting an
    unrelated field named ``updates`` from arbitrary application data.
    """
    if isinstance(value, list):
        return [compact_nested_record_payloads(item) for item in value]
    if not isinstance(value, dict):
        return value
    out: dict[str, Any] = {}
    for key, item in value.items():
        if key == "record" and isinstance(item, dict):
            out[key] = compact_record_payload(item, include_updates=False)
        else:
            out[key] = compact_nested_record_payloads(item)
    return out


class Embeddings:
    def __init__(self) -> None:
        self._default: Any = None

    def embed(
        self,
        texts: list[str],
        records: list[dict[str, Any]],
        embedding_field: str,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[list[float]]:
        provider = (provider or settings.embedding_provider).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()

        if provider == "precomputed":
            vectors: list[list[float]] = []
            for index, record in enumerate(records):
                value = record.get(embedding_field)
                if not isinstance(value, list) or not value:
                    raise ValueError(
                        f"Record {index + 1} has no non-empty '{embedding_field}' array. "
                        "This collection uses precomputed vectors, so every record must carry "
                        "its own embedding. Use Ollama, Chroma's default, or a provider profile "
                        "to have DerridAI compute embeddings instead."
                    )
                vectors.append([float(x) for x in value])
            return vectors

        if provider == "ollama":
            return self._ollama(
                texts,
                model=(model or settings.ollama_embed_model).strip(),
            )

        if provider.startswith("profile:"):
            profile_id = provider.split(":", 1)[1].strip()
            if not profile_id:
                raise ValueError("The embedding provider profile ID is empty.")
            from .system_store import system_store

            profile = system_store.researcher_profile(profile_id)
            if not profile:
                raise ValueError(f"Embedding provider profile {profile_id!r} was not found.")
            profile_type = str(profile.get("type") or "").strip().lower()
            chosen_model = str(model or profile.get("model") or "").strip()
            base_url = str(profile.get("base_url") or "").strip()
            if profile_type == "ollama":
                return self._ollama(
                    texts,
                    model=chosen_model,
                    base_url=base_url or settings.ollama_base_url,
                )
            if profile_type == "openai":
                return self._openai_compatible(
                    texts,
                    model=chosen_model,
                    base_url=base_url,
                    api_key=str(profile.get("api_key") or ""),
                )
            raise ValueError(
                f"Provider profile {profile_id!r} has unsupported type {profile_type!r} for embeddings."
            )

        if provider != "chroma":
            raise ValueError(
                f"Unsupported embedding provider {provider!r}. "
                "Use chroma, precomputed, or profile:<provider-id>."
            )

        if self._default is None:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            self._default = DefaultEmbeddingFunction()

        result = self._default(texts)
        return [list(map(float, row)) for row in result]

    def embed_query(
        self,
        query: str,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[float]:
        provider = (provider or settings.embedding_provider).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()
        if provider == "precomputed":
            raise ValueError(
                "Semantic search cannot create a query embedding for a "
                "precomputed-vector collection. Use Chroma or a configured provider profile."
            )
        return self.embed(
            [query],
            [{}],
            "embedding",
            provider=provider,
            model=model,
        )[0]

    def _ollama(
        self,
        texts: list[str],
        *,
        model: str,
        base_url: str | None = None,
    ) -> list[list[float]]:
        if not model:
            raise ValueError("An Ollama embedding model is required.")
        root = str(base_url or settings.ollama_base_url).rstrip("/")
        modern_endpoint = f"{root}/api/embed"
        legacy_endpoint = f"{root}/api/embeddings"
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                modern_endpoint,
                json={"model": model, "input": texts},
            )
            if response.status_code == 404:
                vectors: list[list[float]] = []
                modern_detail = response.text.strip()
                for text in texts:
                    legacy = client.post(
                        legacy_endpoint,
                        json={"model": model, "prompt": text},
                    )
                    if legacy.status_code == 404:
                        legacy_detail = legacy.text.strip()
                        detail_parts = [
                            part
                            for part in (
                                f"modern response: {modern_detail}" if modern_detail else "",
                                f"legacy response: {legacy_detail}" if legacy_detail else "",
                            )
                            if part
                        ]
                        detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""
                        raise RuntimeError(
                            "Ollama embeddings are unavailable: both /api/embed and the "
                            "legacy /api/embeddings endpoint returned 404. Verify that the "
                            "configured base URL points to Ollama, the installed Ollama "
                            f"version supports embeddings, and embedding model '{model}' is installed"
                            f"{detail}."
                        )
                    legacy.raise_for_status()
                    embedding = legacy.json().get("embedding")
                    if not isinstance(embedding, list):
                        raise RuntimeError("Ollama returned an unexpected legacy embedding response.")
                    vectors.append(list(map(float, embedding)))
                return vectors
            response.raise_for_status()
            payload = response.json()

        vectors = payload.get("embeddings")
        if vectors is None and isinstance(payload.get("embedding"), list) and len(texts) == 1:
            vectors = [payload["embedding"]]
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise RuntimeError("Ollama returned an unexpected embedding response.")
        return [list(map(float, vector)) for vector in vectors]

    def _openai_compatible(
        self,
        texts: list[str],
        *,
        model: str,
        base_url: str,
        api_key: str = "",
    ) -> list[list[float]]:
        if not model:
            raise ValueError("An embedding model is required for this provider profile.")
        if not base_url:
            raise ValueError("The provider profile needs a base URL for embeddings.")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        endpoint = f"{base_url.rstrip('/')}/embeddings"
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                endpoint,
                headers=headers,
                json={"model": model, "input": texts},
            )
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError("The provider returned an unexpected embeddings response.")
        ordered = sorted(
            [item for item in data if isinstance(item, dict)],
            key=lambda item: int(item.get("index") or 0),
        )
        vectors = [item.get("embedding") for item in ordered]
        if len(vectors) != len(texts) or any(not isinstance(vector, list) for vector in vectors):
            raise RuntimeError("The provider returned an unexpected number of embeddings.")
        return [list(map(float, vector)) for vector in vectors]


class ChromaStore:
    _RESPONSE_CACHE_PUBLIC = "_response_cache"
    _RESPONSE_CACHE_STORAGE = "derridai_response_cache"
    _PROVIDER_KEY = "__derridai_embedding_provider"
    _MODEL_KEY = "__derridai_embedding_model"
    _LANG_KEY = "__derridai_language_codes"
    _ROLE_KEY = "__derridai_collection_role"
    _SOURCE_KEY = "__derridai_source_collection"
    _MANIFEST_VERSION_KEY = "__derridai_manifest_version"
    _DESCRIPTION_KEY = "__derridai_description"
    _DIMENSION_KEY = "__derridai_embedding_dimension"
    _REVISION_KEY = "__derridai_embedding_revision"
    _DISTANCE_KEY = "__derridai_distance_metric"
    _RETRIEVAL_KEY = "__derridai_retrieval_mode"
    _TEXT_FIELD_KEY = "__derridai_text_field"
    _FILTER_FIELDS_KEY = "__derridai_filter_fields"
    _RECORD_FINGERPRINT_KEY = "__derridai_source_fingerprint"
    _STATUS_KEY = "__derridai_status"
    _BUILD_ID_KEY = "__derridai_build_id"
    _BUILD_CREATED_KEY = "__derridai_build_created_at"
    _LAST_SYNCED_KEY = "__derridai_last_synced_at"
    _SOURCE_KIND_KEY = "__derridai_source_kind"
    _SOURCE_LABEL_KEY = "__derridai_source_label"
    _SOURCE_COUNT_KEY = "__derridai_source_record_count"
    _SOURCE_HASH_KEY = "__derridai_source_snapshot_hash"
    _SOURCE_WORKS_KEY = "__derridai_source_works"
    _PROTECTED_KEY = "__derridai_protected"
    _APP_VERSION_KEY = "__derridai_app_version"
    _BUILD_HISTORY_KEY = "__derridai_build_history"

    def __init__(self) -> None:
        self._client: Any = None
        self._data_root = Path(settings.chroma_data_root).expanduser().resolve()
        self._path = str(self._normalize_path(settings.chroma_path))
        self._mode = normalize_mode(settings.chroma_mode)
        self._http: dict[str, Any] = {
            "url": str(settings.chroma_base_url or DEFAULT_HTTP_URL).rstrip("/"),
            "token": str(settings.chroma_token or ""),
            "tenant": str(settings.chroma_tenant or DEFAULT_TENANT),
            "database": str(settings.chroma_database or DEFAULT_DATABASE),
        }
        self.embeddings = Embeddings()

    def default_embedding_spec(self) -> tuple[str, str | None]:
        """Resolve the server-owned default used when a collection omits a contract."""

        try:
            from .system_store import system_store

            defaults = system_store.embedding_defaults()
        except Exception:
            logger.warning(
                "Could not read persisted embedding defaults; using environment defaults.",
                exc_info=True,
            )
            defaults = {}

        provider = str(
            defaults.get("embedding_provider") or settings.embedding_provider
        ).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()
        model = str(defaults.get("embedding_model") or "").strip() or None
        if provider == "ollama" and not model:
            model = settings.ollama_embed_model
        return provider, model

    def _normalize_path(self, path: str) -> Path:
        root = self._data_root
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = root / target
        target = target.resolve()
        if not target.is_relative_to(root):
            raise ValueError(
                f"Chroma storage must be inside {root}. "
                "That directory is the host-mounted persistent data root."
            )
        return target

    def _host_path_hint(self, target: Path | None = None) -> str:
        target = (target or Path(self._path)).resolve()
        relative = target.relative_to(self._data_root)
        return "./data" if str(relative) == "." else f"./data/{relative.as_posix()}"

    @property
    def path(self) -> str:
        return self._path

    @property
    def mode(self) -> str:
        return getattr(self, "_mode", "embedded")

    def _http_display(self) -> str:
        http = getattr(self, "_http", {}) or {}
        try:
            return str(parse_http_endpoint(str(http.get("url") or DEFAULT_HTTP_URL))["display"])
        except ValueError:
            return str(http.get("url") or "")

    @property
    def client(self):
        if self._client is None:
            self._client = self._open_client()
        return self._client

    def _open_client(self):
        if self.mode == "http":
            return self._open_http_client(getattr(self, "_http", {}) or {})
        target = Path(self._path).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(target))

    def _open_http_client(self, http: dict[str, Any]):
        kwargs: dict[str, Any] = http_client_kwargs(str(http.get("url") or DEFAULT_HTTP_URL))
        token = str(http.get("token") or "").strip()
        if token:
            kwargs["headers"] = {"Authorization": f"Bearer {token}"}
        tenant = str(http.get("tenant") or "").strip()
        database = str(http.get("database") or "").strip()
        if tenant:
            kwargs["tenant"] = tenant
        if database:
            kwargs["database"] = database
        return chromadb.HttpClient(**kwargs)

    def _probe_client(self, client) -> dict[str, Any]:
        heartbeat_ok = False
        version = getattr(chromadb, "__version__", None)
        if hasattr(client, "heartbeat"):
            client.heartbeat()
            heartbeat_ok = True
        if hasattr(client, "get_version"):
            try:
                version = client.get_version() or version
            except Exception:
                logger.debug("Chroma get_version() failed; using package version", exc_info=True)
        collections = client.list_collections()
        if not heartbeat_ok:
            heartbeat_ok = True
        return {
            "heartbeat_ok": heartbeat_ok,
            "chroma_version": str(version) if version else None,
            "collection_count": len(collections),
        }

    def set_path(self, path: str) -> dict[str, Any]:
        if self.mode != "embedded":
            raise ValueError(
                "A filesystem path is only used in embedded mode. "
                "Switch the Chroma backend to embedded storage first."
            )
        return self.set_connection(mode="embedded", path=path)

    def probe_connection(
        self,
        *,
        mode: str,
        path: str | None = None,
        url: str | None = None,
        token: str | None = None,
        tenant: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Validate a backend without replacing the live client."""
        return self._connect(
            mode=mode,
            path=path,
            url=url,
            token=token,
            tenant=tenant,
            database=database,
            commit=False,
        )

    def set_connection(
        self,
        *,
        mode: str,
        path: str | None = None,
        url: str | None = None,
        token: str | None = None,
        tenant: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Probe then adopt a backend. Collections are not migrated."""
        return self._connect(
            mode=mode,
            path=path,
            url=url,
            token=token,
            tenant=tenant,
            database=database,
            commit=True,
        )

    def _connect(
        self,
        *,
        mode: str,
        path: str | None,
        url: str | None,
        token: str | None,
        tenant: str | None,
        database: str | None,
        commit: bool,
    ) -> dict[str, Any]:
        normalized = normalize_mode(mode)
        current_http = dict(getattr(self, "_http", {}) or {})
        if normalized == "embedded":
            target = self._normalize_path(path or self._path)
            if (
                not commit
                and self.mode == "embedded"
                and str(target) == self._path
                and self._client is not None
            ):
                probed = self._probe_client(self._client)
                return self._health_from(
                    mode="embedded",
                    path=str(target),
                    probed=probed,
                    error=None,
                )
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".derridai-write-test"
            try:
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            except OSError as exc:
                raise ValueError(f"Chroma path is not writable: {target}: {exc}") from exc
            client = chromadb.PersistentClient(path=str(target))
            probed = self._probe_client(client)
            if commit:
                self._mode = "embedded"
                self._path = str(target)
                self._client = client
            return self.health() if commit else self._health_from(
                mode="embedded",
                path=str(target),
                probed=probed,
                error=None,
            )

        next_http = {
            "url": str(url or current_http.get("url") or DEFAULT_HTTP_URL).rstrip("/"),
            "token": current_http.get("token") if token is None else str(token),
            "tenant": str(tenant or current_http.get("tenant") or DEFAULT_TENANT).strip()
            or DEFAULT_TENANT,
            "database": str(
                database or current_http.get("database") or DEFAULT_DATABASE
            ).strip()
            or DEFAULT_DATABASE,
        }
        client = self._open_http_client(next_http)
        probed = self._probe_client(client)
        if commit:
            self._mode = "http"
            self._http = next_http
            self._client = client
        return self.health() if commit else self._health_from(
            mode="http",
            path=None,
            http=next_http,
            probed=probed,
            error=None,
        )

    def _health_from(
        self,
        *,
        mode: str,
        path: str | None,
        probed: dict[str, Any] | None = None,
        http: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        probed = probed or {}
        http_public = public_http_config(http if mode == "http" else None)
        host_hint = self._host_path_hint(Path(path)) if mode == "embedded" and path else None
        identity = connection_identity(
            mode=mode,
            path=path,
            host_path_hint=host_hint,
            url=http_public.get("url"),
            tenant=http_public.get("tenant"),
            database=http_public.get("database"),
        )
        return {
            "available": error is None,
            "mode": mode,
            "path": path if mode == "embedded" else None,
            "host_path_hint": host_hint,
            "data_root": str(self._data_root),
            "url": http_public.get("url") if mode == "http" else None,
            "tenant": http_public.get("tenant") if mode == "http" else None,
            "database": http_public.get("database") if mode == "http" else None,
            "token_configured": bool(http_public.get("token_configured")) if mode == "http" else False,
            "writable": error is None,
            "heartbeat_ok": bool(probed.get("heartbeat_ok")) if error is None else False,
            "chroma_version": probed.get("chroma_version"),
            "collection_count": probed.get("collection_count"),
            "identity": identity,
            "error": error,
        }

    def health(self) -> dict[str, Any]:
        mode = self.mode
        try:
            probed = self._probe_client(self.client)
            return self._health_from(
                mode=mode,
                path=self._path if mode == "embedded" else None,
                http=getattr(self, "_http", None),
                probed=probed,
                error=None,
            )
        except Exception as exc:
            return self._health_from(
                mode=mode,
                path=self._path if mode == "embedded" else None,
                http=getattr(self, "_http", None),
                error=str(exc),
            )

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(UTC).isoformat()

    def preflight_embedding(
        self,
        *,
        provider: str,
        model: str | None = None,
        embedding_dimension: int | None = None,
        distance_metric: str = "cosine",
    ) -> dict[str, Any]:
        """Resolve the immutable embedding contract before collection creation.

        A one-item probe catches missing Ollama models and records the actual vector
        dimension so dimension mismatches fail before a collection is populated.
        """
        if provider:
            provider = str(provider).strip()
            if not provider.startswith("profile:"):
                provider = provider.lower()
        else:
            provider, default_model = self.default_embedding_spec()
            if not model:
                model = default_model
        if provider not in {"chroma", "ollama", "precomputed"} and not provider.startswith("profile:"):
            raise ValueError(
                "Embedding provider must be chroma, precomputed, or profile:<provider-id>."
            )
        metric = str(distance_metric or "cosine").strip().lower()
        if metric not in {"cosine", "l2", "ip"}:
            raise ValueError("Distance metric must be cosine, l2, or ip.")
        normalized_model = str(model or "").strip() or None
        if provider == "ollama" and not normalized_model:
            normalized_model = settings.ollama_embed_model
        if provider.startswith("profile:"):
            profile_id = provider.split(":", 1)[1].strip()
            from .system_store import system_store

            profile = system_store.researcher_profile(profile_id)
            if not profile:
                raise ValueError(f"Embedding provider profile {profile_id!r} was not found.")
            if not normalized_model:
                normalized_model = str(profile.get("model") or "").strip() or None
            if not normalized_model:
                raise ValueError("Select an embedding model for the provider profile.")

        revision: str | None = None
        if provider == "precomputed":
            return {
                "ok": True,
                "embedding_provider": provider,
                "embedding_model": normalized_model,
                "embedding_revision": revision,
                "embedding_dimension": int(embedding_dimension) if embedding_dimension else None,
                "distance_metric": metric,
                "query_supported": False,
                "probed": False,
                "message": (
                    "Precomputed vectors cannot be probed until records are supplied; "
                    "their first vector establishes the dimension unless one is provided."
                ),
            }

        vector = self.embeddings.embed_query(
            "DerridAI embedding compatibility probe",
            provider=provider,
            model=normalized_model,
        )
        dimension = len(vector)
        if provider == "ollama":
            # Ollama's tags endpoint exposes a content digest. Persisting it means
            # a mutable model tag (for example ``:latest``) remains auditable.
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{settings.ollama_base_url}/api/tags")
                    response.raise_for_status()
                    models = response.json().get("models") or []
                target = str(normalized_model or "").strip()
                target_base = target.removesuffix(":latest")
                for item in models:
                    item_name = str(item.get("name") or item.get("model") or "").strip()
                    if item_name == target or item_name.removesuffix(":latest") == target_base:
                        revision = str(item.get("digest") or "").strip() or None
                        break
            except Exception:
                # Revision discovery is provenance enrichment, not a prerequisite
                # for a successful embedding probe.
                revision = None
        elif provider.startswith("profile:"):
            revision = provider
        elif provider == "chroma":
            revision = f"chromadb-{getattr(chromadb, '__version__', 'unknown')}"

        if embedding_dimension is not None and int(embedding_dimension) != dimension:
            raise ValueError(
                f"Embedding preflight returned dimension {dimension}, not the requested "
                f"dimension {embedding_dimension}."
            )
        return {
            "ok": True,
            "embedding_provider": provider,
            "embedding_model": normalized_model,
            "embedding_revision": revision,
            "embedding_dimension": dimension,
            "distance_metric": metric,
            "query_supported": True,
            "probed": True,
            "message": f"Embedding probe succeeded with {dimension} dimensions.",
        }

    @staticmethod
    def _decode_json_metadata(value: Any, default: Any) -> Any:
        if not isinstance(value, str) or not value:
            return default
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default
        return parsed

    def _manifest_spec(self, collection) -> dict[str, Any]:
        metadata = dict(getattr(collection, "metadata", None) or {})
        count = collection.count()
        dimension = metadata.get(self._DIMENSION_KEY)
        try:
            dimension = int(dimension) if dimension not in (None, "") else None
        except (TypeError, ValueError):
            dimension = None
        status = str(metadata.get(self._STATUS_KEY) or ("ready" if count else "empty"))
        history = self._decode_json_metadata(metadata.get(self._BUILD_HISTORY_KEY), [])
        if not isinstance(history, list):
            history = []
        works = self._decode_json_metadata(metadata.get(self._SOURCE_WORKS_KEY), [])
        if not isinstance(works, list):
            works = []
        filter_fields = self._decode_json_metadata(metadata.get(self._FILTER_FIELDS_KEY), [])
        if not isinstance(filter_fields, list):
            filter_fields = []
        return {
            "manifest_version": int(metadata.get(self._MANIFEST_VERSION_KEY) or 1),
            "description": str(metadata.get(self._DESCRIPTION_KEY) or ""),
            "embedding_dimension": dimension,
            "embedding_revision": metadata.get(self._REVISION_KEY),
            "distance_metric": str(metadata.get(self._DISTANCE_KEY) or "l2"),
            "retrieval_mode": str(metadata.get(self._RETRIEVAL_KEY) or "semantic"),
            "text_field": str(metadata.get(self._TEXT_FIELD_KEY) or "text"),
            "filter_fields": [str(value) for value in filter_fields],
            "status": status,
            "build_id": str(metadata.get(self._BUILD_ID_KEY) or ""),
            "build_created_at": metadata.get(self._BUILD_CREATED_KEY),
            "last_synced_at": metadata.get(self._LAST_SYNCED_KEY),
            "source_kind": metadata.get(self._SOURCE_KIND_KEY),
            "source_label": metadata.get(self._SOURCE_LABEL_KEY),
            "source_record_count": int(metadata.get(self._SOURCE_COUNT_KEY) or 0),
            "source_snapshot_hash": metadata.get(self._SOURCE_HASH_KEY),
            "source_works": [str(value) for value in works],
            "protected": bool(metadata.get(self._PROTECTED_KEY) or False),
            "app_version": str(metadata.get(self._APP_VERSION_KEY) or ""),
            "build_history": history[-20:],
        }

    def set_protection(self, name: str, protected: bool) -> dict[str, Any]:
        collection = self._collection(name)
        metadata = dict(collection.metadata or {})
        metadata[self._PROTECTED_KEY] = bool(protected)
        collection.modify(metadata=metadata)
        return self._public_store(collection)

    def begin_sync(
        self,
        name: str,
        *,
        source_kind: str = "browser_workspace",
        source_label: str | None = None,
        source_record_count: int = 0,
        source_works: list[str] | None = None,
        source_snapshot_hash: str | None = None,
    ) -> dict[str, Any]:
        collection = self._collection(name)
        metadata = dict(collection.metadata or {})
        build_id = f"build-{self._iso_now().replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:8]}"
        metadata[self._STATUS_KEY] = "building"
        metadata[self._BUILD_ID_KEY] = build_id
        metadata[self._BUILD_CREATED_KEY] = self._iso_now()
        metadata.pop("__derridai_last_build_error", None)
        metadata[self._SOURCE_KIND_KEY] = str(source_kind or "browser_workspace")
        if source_label:
            metadata[self._SOURCE_LABEL_KEY] = str(source_label)
        metadata[self._SOURCE_COUNT_KEY] = int(max(0, source_record_count))
        metadata[self._SOURCE_WORKS_KEY] = json.dumps(list(dict.fromkeys(source_works or [])), ensure_ascii=False, separators=(",", ":"))
        if source_snapshot_hash:
            metadata[self._SOURCE_HASH_KEY] = str(source_snapshot_hash)
        collection.modify(metadata=metadata)
        return {"build_id": build_id, "store": self._public_store(collection)}

    def set_build_status(self, name: str, status: str) -> dict[str, Any]:
        allowed = {"empty", "queued", "building", "validating", "ready", "stale", "failed"}
        normalized = str(status or "").strip().lower()
        if normalized not in allowed:
            raise ValueError(f"Unsupported collection build status: {status!r}")
        collection = self._collection(name)
        metadata = dict(collection.metadata or {})
        metadata[self._STATUS_KEY] = normalized
        collection.modify(metadata=metadata)
        return self._public_store(collection)

    def finish_sync(self, name: str, *, status: str = "ready") -> dict[str, Any]:
        collection = self._collection(name)
        metadata = dict(collection.metadata or {})
        now = self._iso_now()
        metadata[self._STATUS_KEY] = status
        metadata[self._LAST_SYNCED_KEY] = now
        history = self._decode_json_metadata(metadata.get(self._BUILD_HISTORY_KEY), [])
        if not isinstance(history, list):
            history = []
        history.append({
            "build_id": metadata.get(self._BUILD_ID_KEY),
            "status": status,
            "created_at": metadata.get(self._BUILD_CREATED_KEY),
            "finished_at": now,
            "record_count": collection.count(),
            "source_record_count": int(metadata.get(self._SOURCE_COUNT_KEY) or 0),
            "source_snapshot_hash": metadata.get(self._SOURCE_HASH_KEY),
            "embedding_provider": metadata.get(self._PROVIDER_KEY),
            "embedding_model": metadata.get(self._MODEL_KEY),
            "embedding_dimension": metadata.get(self._DIMENSION_KEY),
            "embedding_revision": metadata.get(self._REVISION_KEY),
            "distance_metric": metadata.get(self._DISTANCE_KEY),
            "retrieval_mode": metadata.get(self._RETRIEVAL_KEY),
            "filter_fields": self._decode_json_metadata(metadata.get(self._FILTER_FIELDS_KEY), []),
            "source_kind": metadata.get(self._SOURCE_KIND_KEY),
            "source_label": metadata.get(self._SOURCE_LABEL_KEY),
            "source_works": self._decode_json_metadata(metadata.get(self._SOURCE_WORKS_KEY), []),
            "app_version": metadata.get(self._APP_VERSION_KEY),
        })
        metadata[self._BUILD_HISTORY_KEY] = json.dumps(history[-20:], ensure_ascii=False, separators=(",", ":"))
        collection.modify(metadata=metadata)
        return self._public_store(collection)

    def fail_sync(self, name: str, message: str | None = None) -> dict[str, Any]:
        collection = self._collection(name)
        metadata = dict(collection.metadata or {})
        metadata[self._STATUS_KEY] = "failed"
        if message:
            metadata["__derridai_last_build_error"] = str(message)[:2000]
        collection.modify(metadata=metadata)
        return self._public_store(collection)

    def _ensure_vector_dimension(self, collection, vectors: list[list[float]]) -> int | None:
        if not vectors:
            return None
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1:
            raise ValueError("A single upsert batch contains vectors with different dimensions.")
        dimension = next(iter(dimensions))
        metadata = dict(getattr(collection, "metadata", None) or {})
        expected = metadata.get(self._DIMENSION_KEY)
        if expected not in (None, "") and int(expected) != dimension:
            raise ValueError(
                f"Embedding dimension mismatch: collection expects {int(expected)}, "
                f"but this batch produced {dimension}. Rebuild into a new collection "
                "with the intended embedding model."
            )
        if expected in (None, "") and hasattr(collection, "modify"):
            metadata[self._DIMENSION_KEY] = dimension
            collection.modify(metadata=metadata)
        return dimension

    def _embedding_spec(self, collection) -> tuple[str, str | None]:
        metadata = dict(getattr(collection, "metadata", None) or {})
        default_provider, default_model = self.default_embedding_spec()
        provider = str(metadata.get(self._PROVIDER_KEY) or default_provider).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()
        model_value = metadata.get(self._MODEL_KEY)
        model = str(model_value).strip() if model_value else default_model
        if provider == "ollama" and not model:
            model = settings.ollama_embed_model
        return provider, model

    @staticmethod
    def _normalize_language_code(value: str) -> str | None:
        token = re.sub(
            r"[^\w]+",
            "_",
            str(value or "").strip().casefold(),
            flags=re.UNICODE,
        ).strip("_")
        english = {
            "en", "eng", "english", "anglais", "anglaise",
            "en_us", "enus", "english_us", "english_usa",
            "american_english", "us_english",
            "en_gb", "engb", "en_uk", "english_uk", "english_gb",
            "british_english", "uk_english",
        }
        french = {
            "fr", "fra", "fre", "french", "français", "francais",
            "fr_fr", "frfr", "french_france",
        }
        if token in english or token.startswith("en_"):
            return "en"
        if token in french or token.startswith("fr_"):
            return "fr"
        if token.startswith(("english_", "american_", "british_")):
            return "en"
        if token.startswith(("french_", "français_", "francais_")):
            return "fr"
        return None

    @classmethod
    def _infer_language_metadata(
        cls,
        name: str,
        language_codes: Sequence[str] | None,
        collection_role: str | None,
    ) -> tuple[list[str], str]:
        if language_codes is not None:
            codes: list[str] = []
            for value in language_codes:
                normalized = cls._normalize_language_code(value)
                if normalized and normalized not in codes:
                    codes.append(normalized)
        else:
            lowered = name.casefold()
            if lowered.endswith(("_en", "-en", "_en_us", "-en_us", "_en_gb", "-en_gb")):
                codes = ["en"]
            elif lowered.endswith(("_fr", "-fr", "_fr_fr", "-fr_fr")):
                codes = ["fr"]
            elif "primary" in lowered:
                codes = ["en", "fr"]
            else:
                codes = []

        if collection_role:
            role = collection_role
        else:
            lowered = name.casefold()
            if (
                lowered.endswith(("_en", "-en", "_fr", "-fr"))
                or any(
                    lowered.endswith(suffix)
                    for suffix in (
                        "_en_us", "-en_us", "_en-us", "-en-us",
                        "_en_gb", "-en_gb", "_en-gb", "-en-gb",
                        "_fr_fr", "-fr_fr", "_fr-fr", "-fr-fr",
                    )
                )
            ):
                role = "language"
            elif "primary" in lowered:
                role = "primary"
            else:
                role = "general"
        return codes, role

    def _language_spec(self, collection) -> tuple[list[str], str, str | None]:
        metadata = dict(getattr(collection, "metadata", None) or {})
        raw_codes = metadata.get(self._LANG_KEY)
        codes: list[str] = []
        if isinstance(raw_codes, str):
            try:
                parsed = json.loads(raw_codes)
                if isinstance(parsed, list):
                    codes = [
                        code
                        for code in (
                            self._normalize_language_code(value)
                            for value in parsed
                        )
                        if code
                    ]
            except json.JSONDecodeError:
                pass
        if not codes:
            codes, inferred_role = self._infer_language_metadata(
                collection.name,
                None,
                metadata.get(self._ROLE_KEY),
            )
        else:
            inferred_role = str(metadata.get(self._ROLE_KEY) or "general")
        source = metadata.get(self._SOURCE_KEY)
        return list(dict.fromkeys(codes)), inferred_role, str(source) if source else None

    def _storage_name(self, name: str) -> str:
        if name == self._RESPONSE_CACHE_PUBLIC:
            return self._RESPONSE_CACHE_STORAGE
        return name

    def _public_collection_name(self, collection) -> str:
        # The response cache has a stable public alias while using a reserved
        # internal storage name.
        if collection.name == self._RESPONSE_CACHE_STORAGE:
            return self._RESPONSE_CACHE_PUBLIC
        return collection.name

    def _public_store(self, collection) -> dict[str, Any]:
        metadata = dict(getattr(collection, "metadata", None) or {})
        provider, model = self._embedding_spec(collection)
        language_codes, role, source_collection = self._language_spec(collection)
        private = {
            self._PROVIDER_KEY,
            self._MODEL_KEY,
            self._LANG_KEY,
            self._ROLE_KEY,
            self._SOURCE_KEY,
            self._MANIFEST_VERSION_KEY,
            self._DESCRIPTION_KEY,
            self._DIMENSION_KEY,
            self._REVISION_KEY,
            self._DISTANCE_KEY,
            self._RETRIEVAL_KEY,
            self._TEXT_FIELD_KEY,
            self._FILTER_FIELDS_KEY,
            self._STATUS_KEY,
            self._BUILD_ID_KEY,
            self._BUILD_CREATED_KEY,
            self._LAST_SYNCED_KEY,
            self._SOURCE_KIND_KEY,
            self._SOURCE_LABEL_KEY,
            self._SOURCE_COUNT_KEY,
            self._SOURCE_HASH_KEY,
            self._SOURCE_WORKS_KEY,
            self._PROTECTED_KEY,
            self._APP_VERSION_KEY,
            self._BUILD_HISTORY_KEY,
            "__derridai_last_build_error",
        }
        public_metadata = {
            key: value
            for key, value in metadata.items()
            if key not in private
        }
        manifest = self._manifest_spec(collection)
        return {
            "name": self._public_collection_name(collection),
            "storage_name": collection.name,
            "count": collection.count(),
            "metadata": public_metadata,
            "embedding_provider": provider,
            "embedding_model": model,
            "language_codes": language_codes,
            "collection_role": role,
            "source_collection": source_collection,
            **manifest,
            "last_build_error": metadata.get("__derridai_last_build_error"),
        }

    def set_language_tags(
        self,
        name: str,
        *,
        language_codes: Sequence[str],
        collection_role: str | None = None,
    ) -> dict[str, Any]:
        collection = self._collection(name)
        codes, inferred_role = self._infer_language_metadata(
            name,
            language_codes,
            collection_role,
        )
        role = collection_role or inferred_role
        metadata = dict(collection.metadata or {})
        metadata[self._LANG_KEY] = json.dumps(
            codes,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        metadata[self._ROLE_KEY] = role
        collection.modify(metadata=metadata)
        return self._public_store(collection)


    def set_embedding(
        self,
        name: str,
        *,
        provider: str,
        model: str | None,
    ) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider not in {"chroma", "ollama", "precomputed"}:
            raise ValueError("Embedding provider must be chroma, ollama, or precomputed.")
        if provider == "ollama" and not (model or "").strip():
            raise ValueError("Choose an Ollama embedding model.")
        collection = self._collection(name)
        current_provider, current_model = self._embedding_spec(collection)
        normalized_model = (model or "").strip() or None
        metadata = dict(collection.metadata or {})
        changed = (
            current_provider != provider
            or (current_provider == "ollama" and current_model != normalized_model)
        )

        if changed and metadata.get(self._MANIFEST_VERSION_KEY):
            raise ValueError(
                "Embedding settings are immutable for manifest-backed collections. "
                "Create a new collection/build with the desired retrieval contract."
            )
        if collection.count() > 0 and changed:
            raise ValueError(
                "Embedding settings cannot be changed on a non-empty collection "
                "because existing vectors may have a different dimension. "
                "Create a new collection with the desired embedding model."
            )

        metadata[self._PROVIDER_KEY] = provider
        if normalized_model:
            metadata[self._MODEL_KEY] = normalized_model
        else:
            metadata.pop(self._MODEL_KEY, None)
        collection.modify(metadata=metadata)
        return self._public_store(collection)

    def list_stores(self) -> list[dict[str, Any]]:
        stores = []
        for collection in self.client.list_collections():
            name = collection.name if hasattr(collection, "name") else str(collection)
            col = self.client.get_collection(name)
            metadata = dict(getattr(col, "metadata", None) or {})
            if bool(metadata.get("derridai_hidden_system_collection")):
                continue
            stores.append(self._public_store(col))
        return sorted(stores, key=lambda item: item["name"].casefold())

    def get_store(self, name: str) -> dict[str, Any]:
        return self._public_store(
            self.client.get_collection(name=self._storage_name(name))
        )

    def create_store(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        *,
        description: str | None = None,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        embedding_dimension: int | None = None,
        distance_metric: str = "cosine",
        retrieval_mode: str = "hybrid",
        text_field: str = "text",
        filter_fields: list[str] | None = None,
        language_codes: Sequence[str] | None = None,
        collection_role: str | None = None,
        protected: bool = False,
    ) -> dict[str, Any]:
        requested_name = str(name or "").strip()
        # ``_response_cache`` is a stable logical alias exposed by DerridAI.
        # Chroma itself rejects leading underscores, so validate and create the
        # physical storage name instead. Public API models still reject arbitrary
        # user-created names that begin with underscores; this exception is only
        # reachable by the internal response-cache lifecycle.
        name = self._storage_name(requested_name)
        validation_name = (
            name
            if requested_name == self._RESPONSE_CACHE_PUBLIC
            else requested_name
        )
        if len(validation_name) < 3 or len(validation_name) > 128:
            raise ValueError("Collection names must contain 3 to 128 characters.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]", validation_name):
            raise ValueError(
                "Collection names must start and end with a letter or number and "
                "contain only letters, numbers, periods, underscores, or hyphens."
            )
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", validation_name):
            raise ValueError("Collection names cannot be IPv4 addresses.")

        existing = {
            item.name if hasattr(item, "name") else str(item)
            for item in self.client.list_collections()
        }
        if name in existing:
            raise StoreAlreadyExistsError(
                f"Collection {requested_name!r} already exists. Open the existing "
                "collection or choose a new name; Create never reuses an existing collection."
            )

        default_provider, default_model = self.default_embedding_spec()
        provider = str(embedding_provider or default_provider).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()
        model = (embedding_model or "").strip() or None
        if not model and provider == default_provider:
            model = default_model
        preflight = self.preflight_embedding(
            provider=provider,
            model=model,
            embedding_dimension=embedding_dimension,
            distance_metric=distance_metric,
        )
        provider = preflight["embedding_provider"]
        model = preflight.get("embedding_model")
        dimension = preflight.get("embedding_dimension")
        revision = preflight.get("embedding_revision")
        metric = preflight.get("distance_metric") or "cosine"
        retrieval_mode = str(retrieval_mode or "hybrid").strip().lower()
        if retrieval_mode not in {"semantic", "hybrid", "lexical"}:
            raise ValueError("Retrieval mode must be semantic, hybrid, or lexical.")

        codes, role = self._infer_language_metadata(
            requested_name,
            language_codes,
            collection_role,
        )

        now = self._iso_now()
        build_id = f"build-{now.replace(':', '').replace('-', '')[:15]}-{uuid.uuid4().hex[:8]}"
        collection_metadata = dict(metadata or {})
        collection_metadata.update({
            self._PROVIDER_KEY: provider,
            self._ROLE_KEY: role,
            self._LANG_KEY: json.dumps(codes, ensure_ascii=False, separators=(",", ":")),
            self._MANIFEST_VERSION_KEY: 1,
            self._DESCRIPTION_KEY: str(description or "").strip(),
            self._DISTANCE_KEY: metric,
            self._RETRIEVAL_KEY: retrieval_mode,
            self._TEXT_FIELD_KEY: str(text_field or "text").strip(),
            self._FILTER_FIELDS_KEY: json.dumps(list(dict.fromkeys(filter_fields or [])), ensure_ascii=False, separators=(",", ":")),
            self._STATUS_KEY: "empty",
            self._BUILD_ID_KEY: build_id,
            self._BUILD_CREATED_KEY: now,
            self._PROTECTED_KEY: bool(protected),
            self._APP_VERSION_KEY: APP_VERSION,
            self._BUILD_HISTORY_KEY: "[]",
        })
        if dimension:
            collection_metadata[self._DIMENSION_KEY] = int(dimension)
        if revision:
            collection_metadata[self._REVISION_KEY] = str(revision)
        if model:
            collection_metadata[self._MODEL_KEY] = model

        try:
            try:
                col = self.client.create_collection(
                    name=name,
                    metadata=collection_metadata,
                    configuration={"hnsw": {"space": metric}},
                )
            except TypeError:
                # Chroma 1.x releases do not all expose collection configuration
                # through the same constructor. The distance contract is already
                # retained in metadata, so creation remains deterministic on
                # clients that require the older constructor shape.
                col = self.client.create_collection(
                    name=name,
                    metadata=collection_metadata,
                )
        except Exception as exc:
            # Chroma's exception type differs across releases. Convert the race
            # between the explicit existence check and create into a 409-capable
            # domain error without weakening strict-create semantics.
            if "already exists" in str(exc).casefold() or "unique" in str(exc).casefold():
                raise StoreAlreadyExistsError(
                    f"Collection {requested_name!r} already exists."
                ) from exc
            raise
        return self._public_store(col)

    def delete_store(self, name: str, *, force: bool = False) -> None:
        collection = self._collection(name)
        if self._manifest_spec(collection).get("protected") and not force:
            raise PermissionError(
                "Deletion protection is enabled for this collection. Disable protection first."
            )
        self.client.delete_collection(name=self._storage_name(name))

    def _collection(self, name: str):
        return self.client.get_collection(name=self._storage_name(name))

    def upsert_many(
        self,
        store: str,
        records: list[dict[str, Any]],
        *,
        document_field: str = "text",
        id_field: str = "record_id",
        embedding_field: str = "embedding",
        id_prefix: str | None = None,
        audit_entries_by_id: dict[str, list[dict[str, Any]]] | None = None,
        replace_updates_by_id: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        col = self._collection(store)
        provider, model = self._embedding_spec(col)
        audit_entries_by_id = audit_entries_by_id or {}
        replace_updates_by_id = replace_updates_by_id or {}
        if not records:
            return {"upserted": 0, "count": col.count()}

        total = 0
        for start in range(0, len(records), settings.api_batch_size):
            batch = records[start:start + settings.api_batch_size]
            ids: list[str] = []
            docs: list[str] = []
            logical_ids: list[str] = []

            for row, record in enumerate(batch, start=start + 1):
                raw_id = record.get(id_field)
                if raw_id is None or str(raw_id).strip() == "":
                    raise ValueError(f"Record {row} is missing '{id_field}'.")

                logical_id = str(record.get("record_id") or raw_id)
                storage_id = str(raw_id)
                chroma_id = f"{id_prefix}::{storage_id}" if id_prefix else storage_id
                ids.append(chroma_id)
                docs.append(str(record.get(document_field) or ""))
                logical_ids.append(logical_id)

            # Chroma metadata upserts replace the whole metadata object. Preserve
            # an existing encoded audit trail server-side when the incoming
            # operation intentionally omits ``updates``. This avoids round-
            # tripping the history through the browser/API while retaining it.
            existing_updates: dict[str, Any] = {}
            existing_updates_count: dict[str, int] = {}
            existing_update_histories: dict[str, list[dict[str, Any]]] = {}
            if ids:
                existing_payload = col.get(ids=ids, include=["metadatas"])
                for existing_id, metadata in zip(
                    existing_payload.get("ids") or [],
                    existing_payload.get("metadatas") or [],
                ):
                    if not isinstance(metadata, dict):
                        continue
                    key = str(existing_id)
                    if "updates" in metadata:
                        existing_updates[key] = metadata["updates"]
                    raw_count = metadata.get("_updates_count")
                    if isinstance(raw_count, (int, float)):
                        existing_updates_count[key] = int(raw_count)
                    if key in audit_entries_by_id:
                        decoded = decode_metadata(metadata).get("updates")
                        if isinstance(decoded, list):
                            existing_update_histories[key] = list(decoded)

            metas: list[dict[str, Any]] = []
            for record, chroma_id, logical_id in zip(batch, ids, logical_ids):
                metadata = encode_metadata(
                    record,
                    document_field=document_field,
                    embedding_field=embedding_field,
                )
                if chroma_id in replace_updates_by_id:
                    replacement = list(replace_updates_by_id.get(chroma_id) or [])
                    metadata["updates"] = _JSON_PREFIX + json.dumps(
                        replacement, ensure_ascii=False, separators=(",", ":")
                    )
                    metadata["_updates_count"] = len(replacement)
                elif chroma_id in audit_entries_by_id:
                    history = list(existing_update_histories.get(chroma_id) or [])
                    history.extend(audit_entries_by_id.get(chroma_id) or [])
                    metadata["updates"] = _JSON_PREFIX + json.dumps(
                        history, ensure_ascii=False, separators=(",", ":")
                    )
                    metadata["_updates_count"] = len(history)
                elif "updates" not in record and chroma_id in existing_updates:
                    metadata["updates"] = existing_updates[chroma_id]
                    if chroma_id in existing_updates_count:
                        metadata["_updates_count"] = existing_updates_count[chroma_id]
                metadata["_record_id"] = logical_id
                metadata["_document_field"] = document_field
                metas.append(metadata)

            vectors = self.embeddings.embed(
                docs,
                batch,
                embedding_field,
                provider=provider,
                model=model,
            )
            self._ensure_vector_dimension(col, vectors)
            col.upsert(
                ids=ids,
                documents=docs,
                metadatas=metas,
                embeddings=vectors,
            )
            total += len(batch)

        return {"upserted": total, "count": col.count()}

    def _language_children(self, source_name: str) -> list[dict[str, Any]]:
        children: list[dict[str, Any]] = []
        for item in self.list_stores():
            if (
                item.get("collection_role") == "language"
                and item.get("source_collection") == source_name
                and item.get("language_codes")
            ):
                children.append(item)
        return children

    @staticmethod
    def _storage_id_for_record(
        record: dict[str, Any],
        *,
        id_field: str,
        id_prefix: str | None,
    ) -> str:
        raw_id = record.get(id_field)
        if raw_id is None or str(raw_id).strip() == "":
            raise ValueError(f"Record is missing '{id_field}'.")
        storage_id = str(raw_id)
        return f"{id_prefix}::{storage_id}" if id_prefix else storage_id

    def sync_language_children(
        self,
        source_name: str,
        records: list[dict[str, Any]],
        *,
        id_field: str = "record_id",
        id_prefix: str | None = None,
    ) -> dict[str, Any]:
        source = self._collection(source_name)
        _, source_role, _ = self._language_spec(source)
        if source_role != "primary":
            return {"source": source_name, "mirrored": {}, "record_routes": {}}

        children = self._language_children(source_name)
        if not children or not records:
            return {"source": source_name, "mirrored": {}, "record_routes": {}}

        ids = [
            self._storage_id_for_record(
                record,
                id_field=id_field,
                id_prefix=id_prefix,
            )
            for record in records
        ]
        payload = source.get(
            ids=ids,
            include=["documents", "metadatas", "embeddings"],
        )
        returned_ids = payload.get("ids") or []
        documents = payload.get("documents") or []
        metadatas = payload.get("metadatas") or []
        embeddings = payload.get("embeddings")
        embeddings_list = (
            embeddings.tolist()
            if hasattr(embeddings, "tolist")
            else embeddings
        ) or []

        source_rows: dict[str, dict[str, Any]] = {}
        for index, chroma_id in enumerate(returned_ids):
            source_rows[str(chroma_id)] = {
                "document": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
                "embedding": embeddings_list[index] if index < len(embeddings_list) else None,
            }

        record_by_id = {
            self._storage_id_for_record(record, id_field=id_field, id_prefix=id_prefix): record
            for record in records
        }
        record_routes: dict[str, list[str]] = {chroma_id: [] for chroma_id in ids}
        mirrored: dict[str, int] = {}

        for child in children:
            child_name = child["name"]
            child_codes = set(child.get("language_codes") or [])
            child_col = self._collection(child_name)
            matching_ids: list[str] = []

            for chroma_id in ids:
                record = record_by_id[chroma_id]
                language_value = record.get("document_language")
                if language_value is None:
                    language_value = record.get("document_languages")
                codes = self._record_language_codes(language_value)
                if codes & child_codes:
                    matching_ids.append(chroma_id)
                    record_routes[chroma_id].append(child_name)

            # Delete the current record versions from the child first. This keeps
            # language stores synchronized when a record's language metadata changes.
            child_col.delete(ids=ids)

            if matching_ids:
                child_col.upsert(
                    ids=matching_ids,
                    documents=[source_rows[chroma_id]["document"] for chroma_id in matching_ids],
                    metadatas=[source_rows[chroma_id]["metadata"] for chroma_id in matching_ids],
                    embeddings=[source_rows[chroma_id]["embedding"] for chroma_id in matching_ids],
                )
            mirrored[child_name] = len(matching_ids)

        return {
            "source": source_name,
            "mirrored": mirrored,
            "record_routes": record_routes,
        }

    def upsert_with_language_sync(
        self,
        store: str,
        records: list[dict[str, Any]],
        *,
        document_field: str = "text",
        id_field: str = "record_id",
        embedding_field: str = "embedding",
        id_prefix: str | None = None,
        mirror_languages: bool = True,
        audit_entries_by_id: dict[str, list[dict[str, Any]]] | None = None,
        replace_updates_by_id: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        result = self.upsert_many(
            store,
            records,
            document_field=document_field,
            id_field=id_field,
            embedding_field=embedding_field,
            id_prefix=id_prefix,
            audit_entries_by_id=audit_entries_by_id,
            replace_updates_by_id=replace_updates_by_id,
        )
        language_sync = (
            self.sync_language_children(
                store,
                records,
                id_field=id_field,
                id_prefix=id_prefix,
            )
            if mirror_languages
            else {"source": store, "mirrored": {}, "record_routes": {}}
        )
        return {**result, "language_sync": language_sync}

    def update_existing(
        self,
        store: str,
        chroma_id: str,
        record: dict[str, Any],
        *,
        document_field: str = "text",
        embedding_field: str = "embedding",
    ) -> dict[str, Any]:
        col = self._collection(store)
        provider, model = self._embedding_spec(col)
        existing = col.get(
            ids=[chroma_id],
            include=["documents", "metadatas", "embeddings"],
        )
        if not existing.get("ids"):
            raise KeyError(f"Record {chroma_id!r} was not found.")

        clean_record = {
            key: value
            for key, value in record.items()
            if key != "_chroma_id" and not key.startswith("_chroma_")
        }
        document = str(clean_record.get(document_field) or "")
        logical_id = clean_record.get("record_id")
        if logical_id is None:
            old_meta = decode_metadata((existing.get("metadatas") or [{}])[0])
            logical_id = old_meta.get("_record_id") or chroma_id

        metadata = encode_metadata(
            clean_record,
            document_field=document_field,
            embedding_field=embedding_field,
        )
        metadata["_record_id"] = str(logical_id)
        metadata["_document_field"] = document_field

        if provider == "precomputed" and not clean_record.get(embedding_field):
            existing_vectors = existing.get("embeddings")
            if existing_vectors is None or len(existing_vectors) == 0:
                raise ValueError(
                    "The existing record has no stored embedding and no "
                    f"'{embedding_field}' was supplied."
                )
            vector = [float(x) for x in existing_vectors[0]]
        else:
            vector = self.embeddings.embed(
                [document],
                [clean_record],
                embedding_field,
                provider=provider,
                model=model,
            )[0]

        col.upsert(
            ids=[chroma_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[vector],
        )
        return {
            "updated": chroma_id,
            "count": col.count(),
            "record": self.get_record(store, chroma_id, include_updates=False),
        }

    def get_records(
        self,
        store: str,
        *,
        limit: int = 100,
        offset: int = 0,
        work: str | None = None,
        sort_field: str | None = None,
        sort_dir: str = "asc",
        filters: dict[str, str] | None = None,
        include_updates: bool = False,
    ) -> dict[str, Any]:
        col = self._collection(store)
        filters = {
            str(key): str(value)
            for key, value in (filters or {}).items()
            if str(value).strip()
        }

        # Plain work-only browsing can stay fully delegated to Chroma. Column
        # text filters/sorting require decoded flat records, so those are
        # handled deterministically in Python and paginated afterward.
        if not filters and not sort_field:
            where = {"work": work} if work else None
            kwargs: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "include": ["documents", "metadatas"],
            }
            if where:
                kwargs["where"] = where
            payload = col.get(**kwargs)
            if where:
                count_payload = col.get(where=where, include=["metadatas"])
                count = len(count_payload.get("ids") or [])
            else:
                count = col.count()
            return {
                "records": self._decode_result(payload, include_updates=include_updates),
                "count": count,
                "limit": limit,
                "offset": offset,
                "work": work,
                "sort_field": sort_field,
                "sort_dir": sort_dir,
                "filters": filters,
            }

        scan_kwargs: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if work:
            scan_kwargs["where"] = {"work": work}
        payload = col.get(**scan_kwargs)
        records = self._decode_result(payload, include_updates=include_updates)

        def searchable(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, (list, tuple, set)):
                return " ".join(searchable(item) for item in value)
            if isinstance(value, dict):
                return " ".join(
                    f"{key} {searchable(item)}"
                    for key, item in value.items()
                )
            return str(value)

        for field, query in filters.items():
            needle = query.casefold().strip()
            records = [
                record
                for record in records
                if needle in searchable(record.get(field)).casefold()
            ]

        if sort_field:
            reverse = str(sort_dir).lower() == "desc"

            def sort_value(record: dict[str, Any]):
                value = record.get(sort_field)
                if value is None:
                    return (1, 2, "")
                if isinstance(value, bool):
                    return (0, 0, 1.0 if value else 0.0)
                if isinstance(value, (int, float)):
                    return (0, 0, float(value))
                return (0, 1, searchable(value).casefold())

            records.sort(key=sort_value, reverse=reverse)

        count = len(records)
        page = records[offset:offset + limit]
        return {
            "records": page,
            "count": count,
            "limit": limit,
            "offset": offset,
            "work": work,
            "sort_field": sort_field,
            "sort_dir": sort_dir,
            "filters": filters,
        }

    def list_works(self, store: str) -> list[str]:
        return [item["work"] for item in self.work_stats(store)]

    def work_stats(self, store: str) -> list[dict[str, Any]]:
        col = self._collection(store)
        payload = col.get(include=["metadatas", "documents"])
        fields = ("document_author", "year", "publication_year", "publisher", "publication_place", "translator", "edition", "isbn", "document_language", "original_language", "canonical_work_id", "full_citation", "cover_url")
        grouped: dict[str, dict[str, Any]] = {}
        metadatas = payload.get("metadatas") or []
        documents = payload.get("documents") or []
        for index, metadata in enumerate(metadatas):
            decoded = decode_metadata(metadata or {})
            value = decoded.get("work")
            if value is None or not str(value).strip():
                continue
            key = str(value)
            item = grouped.setdefault(key, {"work": key, "count": 0, "total_words": 0, "_values": {field: set() for field in fields}})
            item["count"] += 1
            document = documents[index] if index < len(documents) else ""
            item["total_words"] += len(str(document or "").split())
            for field in fields:
                field_value = decoded.get(field)
                if field_value is None or not str(field_value).strip():
                    continue
                try:
                    token = json.dumps(field_value, ensure_ascii=False, sort_keys=True)
                except TypeError:
                    token = json.dumps(str(field_value), ensure_ascii=False)
                item["_values"][field].add(token)
        output: list[dict[str, Any]] = []
        for work in sorted(grouped, key=str.casefold):
            item = grouped[work]
            result = {
                "work": work,
                "count": item["count"],
                "total_words": int(item.get("total_words") or 0),
                "average_record_length": round((item.get("total_words") or 0) / item["count"]) if item["count"] else 0,
            }
            for field, values in item["_values"].items():
                if len(values) == 1:
                    result[field] = json.loads(next(iter(values)))
                elif len(values) > 1:
                    result[f"{field}_mixed"] = True
            output.append(result)
        return output

    @staticmethod
    def _flatten_language_values(value: Any) -> list[str]:
        output: list[str] = []
        if value is None:
            return output
        if isinstance(value, list):
            for item in value:
                output.extend(ChromaStore._flatten_language_values(item))
            return output
        if isinstance(value, dict):
            for item in value.values():
                output.extend(ChromaStore._flatten_language_values(item))
            return output
        return [str(value)]

    @classmethod
    def _record_language_codes(cls, value: Any) -> set[str]:
        codes: set[str] = set()
        for raw in cls._flatten_language_values(value):
            normalized = cls._normalize_language_code(raw)
            if normalized:
                codes.add(normalized)
        return codes

    def derive_language_stores(
        self,
        source_name: str,
        *,
        en_name: str | None = None,
        fr_name: str | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        source = self._collection(source_name)
        _, source_role, _ = self._language_spec(source)
        lowered = source_name.casefold()
        looks_derived = any(
            lowered.endswith(suffix)
            for suffix in (
                "_en", "-en", "_fr", "-fr",
                "_en_us", "-en_us", "_en_gb", "-en_gb",
                "_fr_fr", "-fr_fr",
            )
        )
        if source_role == "language" or looks_derived:
            raise ValueError(
                "Language collections cannot be used to generate further "
                "language collections. Select a primary/general source collection."
            )

        names = {
            "en": (en_name or f"{source_name}_en").strip(),
            "fr": (fr_name or f"{source_name}_fr").strip(),
        }
        if any(not value for value in names.values()):
            raise ValueError("Derived collection names cannot be empty.")
        if len(set(names.values())) != 2:
            raise ValueError("English and French collection names must differ.")
        if source_name in set(names.values()):
            raise ValueError("Derived collection names must differ from the source.")

        existing = {
            item.name if hasattr(item, "name") else str(item)
            for item in self.client.list_collections()
        }

        for target in names.values():
            if target in existing:
                if not overwrite:
                    raise ValueError(
                        f"Collection {target!r} already exists. Enable overwrite "
                        "or choose another name."
                    )
                self.client.delete_collection(name=target)

        source_metadata = dict(source.metadata or {})
        targets: dict[str, Any] = {}
        for code, name in names.items():
            metadata = dict(source_metadata)
            metadata[self._ROLE_KEY] = "language"
            metadata[self._SOURCE_KEY] = source_name
            metadata[self._LANG_KEY] = json.dumps([code])
            targets[code] = self.client.get_or_create_collection(
                name=name,
                metadata=metadata,
            )

        totals = {"en": 0, "fr": 0, "skipped": 0}
        batch_size = max(1, settings.api_batch_size)
        source_count = source.count()

        for offset in range(0, source_count, batch_size):
            payload = source.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas", "embeddings"],
            )
            ids = payload.get("ids") or []
            documents = payload.get("documents") or []
            metadatas = payload.get("metadatas") or []
            embeddings = payload.get("embeddings")
            embeddings_list = (
                embeddings.tolist()
                if hasattr(embeddings, "tolist")
                else embeddings
            ) or []

            buckets: dict[str, dict[str, list[Any]]] = {
                code: {
                    "ids": [],
                    "documents": [],
                    "metadatas": [],
                    "embeddings": [],
                }
                for code in targets
            }

            for index, chroma_id in enumerate(ids):
                metadata = metadatas[index] if index < len(metadatas) else {}
                decoded = decode_metadata(metadata or {})
                language_value = decoded.get("document_language")
                if language_value is None:
                    language_value = decoded.get("document_languages")
                codes = self._record_language_codes(language_value)

                matched = False
                for code in ("en", "fr"):
                    if code not in codes:
                        continue
                    matched = True
                    bucket = buckets[code]
                    bucket["ids"].append(chroma_id)
                    bucket["documents"].append(
                        documents[index] if index < len(documents) else ""
                    )
                    bucket["metadatas"].append(metadata)
                    if index >= len(embeddings_list):
                        raise RuntimeError(
                            "Source collection did not return embeddings required "
                            "for language-store derivation."
                        )
                    bucket["embeddings"].append(embeddings_list[index])
                    totals[code] += 1

                if not matched:
                    totals["skipped"] += 1

            for code, target in targets.items():
                bucket = buckets[code]
                if not bucket["ids"]:
                    continue
                target.upsert(
                    ids=bucket["ids"],
                    documents=bucket["documents"],
                    metadatas=bucket["metadatas"],
                    embeddings=bucket["embeddings"],
                )

        return {
            "source": source_name,
            "source_count": source_count,
            "collections": {
                code: {
                    "name": names[code],
                    "count": totals[code],
                    "language_codes": [code],
                }
                for code in ("en", "fr")
            },
            "skipped": totals["skipped"],
        }

    @staticmethod
    def _response_cache_embedding(
        text: str,
        dimensions: int = 64,
    ) -> list[float]:
        """Deterministic local cache vector; no embedding service required."""
        vector = [0.0] * dimensions
        tokens = re.findall(r"\\w+", str(text or "").casefold())
        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"),
                digest_size=16,
            ).digest()
            bucket = int.from_bytes(
                digest[:4],
                "little",
            ) % dimensions
            sign = -1.0 if digest[4] & 1 else 1.0
            vector[bucket] += sign
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _is_missing_collection_error(exc: Exception) -> bool:
        """Recognize an absent collection without conflating it with storage failure."""
        name = exc.__class__.__name__.casefold()
        message = str(exc).casefold()
        return (
            name in {"notfounderror", "invalidcollectionexception"}
            or ("collection" in message and ("not found" in message or "does not exist" in message))
        )

    @staticmethod
    def _is_query_capability_error(exc: Exception) -> bool:
        """Return True only for query-shape/capability failures with a safe scan fallback."""
        if isinstance(exc, (TypeError, ValueError)):
            return True
        name = exc.__class__.__name__.casefold()
        message = str(exc).casefold()
        if name in {"invalidargumenterror", "invalidwhereerror"}:
            return True
        mentions_feature = any(token in message for token in ("where_document", "$contains", "limit"))
        mentions_capability = any(token in message for token in ("unsupported", "not supported", "invalid", "unexpected"))
        return mentions_feature and mentions_capability

    def get_response_cache_records(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        query: str | None = None,
    ) -> dict[str, Any]:
        """Read the current response-cache collection."""
        try:
            collection = self.client.get_collection(name=self._RESPONSE_CACHE_STORAGE)
        except Exception as exc:
            if self._is_missing_collection_error(exc):
                return {
                    "records": [],
                    "count": 0,
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "query": query or "",
                    "exists": False,
                }
            raise RuntimeError(f"Could not open response-cache collection: {exc}") from exc

        try:
            payload = collection.get(include=["documents", "metadatas"])
            records = [dict(record) for record in self._decode_result(payload)]
        except Exception as exc:
            raise RuntimeError(f"Could not read response-cache records: {exc}") from exc

        records.sort(
            key=lambda record: str(
                record.get("created_at")
                or record.get("updated_at")
                or ""
            ),
            reverse=True,
        )
        total = len(records)
        needle = str(query or "").strip().casefold()
        if needle:
            records = [
                record
                for record in records
                if needle in str(record.get("question") or "").casefold()
            ]
        count = len(records)
        page = [
            compact_nested_record_payloads(record)
            for record in records[offset:offset + limit]
        ]
        return {
            "records": page,
            "count": count,
            "total": total,
            "limit": limit,
            "offset": offset,
            "query": query or "",
            "exists": True,
        }

    def ensure_response_cache(self) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(name=self._RESPONSE_CACHE_STORAGE)
            return self._public_store(collection)
        except Exception as exc:
            if not self._is_missing_collection_error(exc):
                raise RuntimeError(f"Could not inspect response-cache collection: {exc}") from exc
            return self.create_store(
                self._RESPONSE_CACHE_PUBLIC,
                embedding_provider="precomputed",
                embedding_model="derridai-response-cache-hash-v1",
                embedding_dimension=64,
                distance_metric="cosine",
                language_codes=[],
                collection_role="general",
                metadata={
                    "derridai_system_collection": "response_cache",
                    "derridai_cache_embedding": "deterministic-hash-vector-v1",
                },
            )

    def cache_rag_response(
        self,
        *,
        job_id: str,
        request: dict[str, Any],
        result: dict[str, Any],
        created_at: str,
    ) -> dict[str, Any]:
        self.ensure_response_cache()
        record_id = f"rag-response::{job_id}"
        evidence = compact_nested_record_payloads(result.get("evidence") or [])
        compact_request = compact_nested_record_payloads(request)
        compact_evidence = [
            {
                "evidence_id": item.get("evidence_id"),
                "record_id": (item.get("record") or {}).get("record_id"),
                "work": (item.get("record") or {}).get("work"),
                "inline_citation": item.get("inline_citation"),
                "collection": item.get("collection"),
                "rerank_score": item.get("rerank_score"),
            }
            for item in evidence
        ]
        record = {
            "record_id": record_id,
            "response_id": job_id,
            "response_type": "rag",
            "question": result.get("prompt") or request.get("prompt") or "",
            "instructions": request.get("instructions") or "",
            "text": result.get("answer") or "",
            "raw_answer": result.get("raw_answer") or "",
            "provider": result.get("provider") or request.get("provider"),
            "model": result.get("model") or request.get("model"),
            "source_collection": request.get("source_collection"),
            "collections": result.get("collections") or [],
            "query_metadata": result.get("query_metadata") or {},
            "retrieval": result.get("retrieval") or {},
            "pipeline_stages": result.get("stages") or [],
            "warnings": result.get("warnings") or [],
            "evidence_summary": compact_evidence,
            "evidence": evidence,
            "evidence_count": len(evidence),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "rag_request": compact_request,
            "created_at": created_at,
            "updated_at": created_at,
            "grade": None,
            # Response-cache vectors are local/deterministic. The cache remains
            # writable even when the corpus embedding service is offline.
            "embedding": self._response_cache_embedding(
                result.get("answer") or ""
            ),
        }
        payload = self.upsert_many(
            "_response_cache",
            [record],
            document_field="text",
            id_field="record_id",
        )
        return {
            "store": "_response_cache",
            "record_id": record_id,
            "count": payload.get("count"),
        }

    def update_response_cache_grade(
        self,
        response_record_id: str,
        grade: dict[str, Any],
        *,
        provider: str | None = None,
        model: str | None = None,
        generation_provider: str | None = None,
        generation_model: str | None = None,
    ) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(name=self._RESPONSE_CACHE_STORAGE)
            payload = collection.get(
                ids=[response_record_id],
                include=["documents", "metadatas"],
            )
            decoded = self._decode_result(payload)
        except Exception as exc:
            raise ValueError("Cached RAG response was not found.") from exc
        if not decoded:
            raise ValueError("Cached RAG response was not found.")
        record = dict(decoded[0])
        clean = dict(record)
        chroma_id = str(clean.pop("_chroma_id", response_record_id))
        graded_at = datetime.now(UTC).isoformat()
        entry = {
            "graded_at": graded_at,
            "provider": provider,
            "model": model,
            "generation_provider": generation_provider or clean.get("provider"),
            "generation_model": generation_model or clean.get("model"),
            "same_model_as_generation": bool(
                model
                and (generation_model or clean.get("model"))
                and str(model) == str(generation_model or clean.get("model"))
            ),
            "result": grade,
        }
        history = list(clean.get("grades") or [])
        history.append(entry)
        clean["grades"] = history[-50:]
        clean["grade"] = grade
        clean["latest_grade"] = entry
        clean["updated_at"] = graded_at
        metadata = encode_metadata(
            clean,
            document_field="text",
            embedding_field="embedding",
        )
        metadata["_record_id"] = str(clean.get("record_id") or response_record_id)
        metadata["_document_field"] = "text"
        # Grade updates only change metadata. Supplying ``documents`` here makes
        # Chroma invoke the collection embedding function; the response cache uses
        # deterministic 64-D precomputed vectors, while Chroma's default embedding
        # function is 384-D. Metadata-only updates preserve the existing cache
        # vector and avoid dimension mismatch failures during RAG grading.
        collection.update(
            ids=[chroma_id],
            metadatas=[metadata],
        )
        return clean

    def export_records(
        self,
        store: str,
        *,
        work: str | None = None,
    ) -> list[dict[str, Any]]:
        total = self.get_records(
            store,
            limit=1,
            offset=0,
            work=work,
            include_updates=True,
        )["count"]
        output: list[dict[str, Any]] = []
        batch_size = min(1000, max(1, settings.api_batch_size * 4))
        for offset in range(0, total, batch_size):
            page = self.get_records(
                store,
                limit=batch_size,
                offset=offset,
                work=work,
                include_updates=True,
            )
            for record in page["records"]:
                clean = dict(record)
                clean.pop("_chroma_id", None)
                output.append(clean)
        return output

    @staticmethod
    def _backup_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(key): ChromaStore._backup_jsonable(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [ChromaStore._backup_jsonable(item) for item in value]
        if hasattr(value, "tolist"):
            return ChromaStore._backup_jsonable(value.tolist())
        return str(value)

    def write_logical_backup(self, root: Path) -> list[dict[str, Any]]:
        """Write a portable, embedding-preserving Chroma snapshot under root."""
        chroma_root = root / "chroma"
        chroma_root.mkdir(parents=True, exist_ok=True)
        inventory: list[dict[str, Any]] = []
        collections = sorted(
            self.client.list_collections(),
            key=lambda item: (item.name if hasattr(item, "name") else str(item)).casefold(),
        )
        for index, item in enumerate(collections, start=1):
            name = item.name if hasattr(item, "name") else str(item)
            collection = self.client.get_collection(name=name)
            count = collection.count()
            file_name = f"collection-{index:05d}.jsonl"
            file_path = chroma_root / file_name
            raw_metadata = self._backup_jsonable(dict(collection.metadata or {}))
            raw_configuration = self._backup_jsonable(
                getattr(collection, "configuration", None)
            )
            with file_path.open("w", encoding="utf-8") as handle:
                for offset in range(0, count, 1000):
                    payload = collection.get(
                        limit=min(1000, count - offset),
                        offset=offset,
                        include=["documents", "metadatas", "embeddings"],
                    )
                    ids = list(payload.get("ids") or [])
                    docs = list(payload.get("documents") or [])
                    metas = list(payload.get("metadatas") or [])
                    embeddings = payload.get("embeddings")
                    if embeddings is None:
                        embeddings = [None] * len(ids)
                    else:
                        embeddings = self._backup_jsonable(embeddings)
                    for row, chroma_id in enumerate(ids):
                        record = {
                            "id": str(chroma_id),
                            "document": docs[row] if row < len(docs) else None,
                            "metadata": metas[row] if row < len(metas) else None,
                            "embedding": embeddings[row] if row < len(embeddings) else None,
                        }
                        handle.write(json.dumps(
                            self._backup_jsonable(record),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ) + "\n")
            inventory.append({
                "name": self._public_collection_name(collection),
                "storage_name": name,
                "count": count,
                "metadata": raw_metadata,
                "configuration": raw_configuration,
                "file": f"chroma/{file_name}",
                "public": self._public_store(collection),
            })
        return inventory

    @staticmethod
    def _flush_logical_restore_batch(
        collection: Any,
        name: str,
        ids: list[str],
        docs: list[str | None],
        metas: list[dict[str, Any] | None],
        embeddings: list[list[float] | None],
    ) -> None:
        if not ids:
            return
        grouped: dict[tuple[bool, bool, bool], list[int]] = {}
        for row_index in range(len(ids)):
            key = (
                docs[row_index] is not None,
                metas[row_index] is not None,
                embeddings[row_index] is not None,
            )
            grouped.setdefault(key, []).append(row_index)
        for (has_doc, has_meta, has_embedding), indexes in grouped.items():
            kwargs: dict[str, Any] = {
                "ids": [ids[index] for index in indexes],
            }
            if has_doc:
                kwargs["documents"] = [docs[index] for index in indexes]
            if has_meta:
                kwargs["metadatas"] = [metas[index] for index in indexes]
            if has_embedding:
                kwargs["embeddings"] = [embeddings[index] for index in indexes]
            elif has_doc:
                raise ValueError(
                    f"Collection {name!r} backup row is missing its stored embedding; "
                    "restore refuses to silently re-embed it."
                )
            collection.add(**kwargs)
        ids.clear()
        docs.clear()
        metas.clear()
        embeddings.clear()

    def restore_logical_backup(
        self,
        root: Path,
        inventory: list[dict[str, Any]],
        *,
        replace: bool = True,
    ) -> dict[str, Any]:
        """Restore a logical Chroma snapshot, preserving stored embeddings exactly."""
        if replace:
            self.nuke()
        restored: list[dict[str, Any]] = []
        for entry in inventory:
            public_name = str(entry.get("name") or "").strip()
            name = str(entry.get("storage_name") or self._storage_name(public_name)).strip()
            relative_file = str(entry.get("file") or "").strip()
            if not name or not public_name or not relative_file:
                raise ValueError("Backup collection entry is missing name/file.")
            file_path = (root / relative_file).resolve()
            if not file_path.is_relative_to(root.resolve()) or not file_path.exists():
                raise ValueError(f"Backup collection payload is missing or unsafe: {relative_file}")
            metadata = entry.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError(f"Collection metadata for {name!r} is invalid.")
            create_kwargs: dict[str, Any] = {
                "name": name,
                "metadata": metadata or None,
            }
            configuration = entry.get("configuration")
            if isinstance(configuration, dict) and configuration:
                create_kwargs["configuration"] = configuration
            try:
                collection = self.client.create_collection(**create_kwargs)
            except TypeError:
                # Chroma versions within the supported 1.x range do not all
                # expose collection configuration through the same constructor.
                create_kwargs.pop("configuration", None)
                collection = self.client.create_collection(**create_kwargs)
            ids: list[str] = []
            docs: list[str | None] = []
            metas: list[dict[str, Any] | None] = []
            embeddings: list[list[float] | None] = []

            with file_path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Invalid JSON in {relative_file} line {line_number}."
                        ) from exc
                    chroma_id = str(row.get("id") or "").strip()
                    if not chroma_id:
                        raise ValueError(
                            f"Missing Chroma ID in {relative_file} line {line_number}."
                        )
                    embedding = row.get("embedding")
                    if embedding is not None:
                        embedding = [float(value) for value in embedding]
                    ids.append(chroma_id)
                    docs.append(row.get("document"))
                    metas.append(row.get("metadata"))
                    embeddings.append(embedding)
                    if len(ids) >= 500:
                        self._flush_logical_restore_batch(
                            collection, name, ids, docs, metas, embeddings
                        )
                self._flush_logical_restore_batch(collection, name, ids, docs, metas, embeddings)
            actual = collection.count()
            expected = int(entry.get("count") or 0)
            if expected != actual:
                raise ValueError(
                    f"Collection {name!r} restored {actual} records; expected {expected}."
                )
            restored.append(self._public_store(collection))
        return {"collections": restored, "count": len(restored)}

    def nuke(self) -> dict[str, Any]:
        names: list[str] = []
        mode = self.mode
        try:
            names = [
                collection.name if hasattr(collection, "name") else str(collection)
                for collection in self.client.list_collections()
            ]
            for name in names:
                self.client.delete_collection(name=name)
        except Exception as exc:
            # Embedded NUKE still has a filesystem wipe as the authority.
            # An HTTP server has no local catalog to delete; fail visibly.
            if mode != "embedded":
                raise RuntimeError(
                    f"Could not reset the Chroma server: {exc}"
                ) from exc
        self._client = None
        gc.collect()

        if mode != "embedded":
            return {
                "deleted_collections": len(names),
                "removed_paths": 0,
                "mode": mode,
                "path": None,
                "url": self._http_display(),
            }

        root = Path(self._path)
        removed_paths = 0
        for child in list(root.iterdir()) if root.exists() else []:
            if child.name == ".gitkeep":
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed_paths += 1
            except OSError:
                # Collection deletion is the authoritative reset; stale files are
                # non-fatal and can be removed after the API container stops.
                pass
        root.mkdir(parents=True, exist_ok=True)
        return {
            "deleted_collections": len(names),
            "removed_paths": removed_paths,
            "mode": "embedded",
            "path": self._path,
            "url": None,
        }

    def existing_ids(self, store: str, ids: list[str]) -> list[str]:
        col = self._collection(store)
        if not ids:
            return []
        found: list[str] = []
        for start in range(0, len(ids), 500):
            batch = ids[start:start + 500]
            payload = col.get(ids=batch, include=["metadatas"])
            found.extend(str(value) for value in (payload.get("ids") or []))
        return found

    def drift_report(
        self,
        store: str,
        items: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Compare a compact source fingerprint set with the indexed collection.

        The browser sends only stable storage ids plus content fingerprints. The
        server owns the comparison, including rows that disappeared from the
        source. Rows without fingerprints are classified as modified and rebuilt.
        """
        col = self._collection(store)
        requested: dict[str, str] = {}
        for item in items:
            item_id = str(item.get("id") or "").strip()
            fingerprint = str(item.get("fingerprint") or "").strip()
            if item_id and fingerprint:
                requested[item_id] = fingerprint
        if not requested:
            raise ValueError("At least one source id and fingerprint is required.")

        indexed: dict[str, str | None] = {}
        ids = list(requested)
        for start in range(0, len(ids), 500):
            payload = col.get(ids=ids[start:start + 500], include=["metadatas"])
            for chroma_id, metadata in zip(
                payload.get("ids") or [],
                payload.get("metadatas") or [],
            ):
                raw = (metadata or {}).get(self._RECORD_FINGERPRINT_KEY) if isinstance(metadata, dict) else None
                indexed[str(chroma_id)] = str(raw).strip() if raw else None

        added = [item_id for item_id in ids if item_id not in indexed]
        modified = [
            item_id for item_id in ids
            if item_id in indexed and indexed[item_id] != requested[item_id]
        ]
        unchanged = len(ids) - len(added) - len(modified)

        source_ids = set(ids)
        removed: list[str] = []
        # Chroma's get API is paged here so drift checks remain bounded in memory
        # to identifiers rather than full records or embeddings.
        total = col.count()
        for offset in range(0, total, 5000):
            payload = col.get(limit=min(5000, total - offset), offset=offset, include=[])
            for chroma_id in payload.get("ids") or []:
                value = str(chroma_id)
                if value not in source_ids:
                    removed.append(value)

        source_hasher = hashlib.sha256()
        for item_id in sorted(requested):
            source_hasher.update(item_id.encode("utf-8", errors="replace"))
            source_hasher.update(b"\0")
            source_hasher.update(requested[item_id].encode("utf-8", errors="replace"))
            source_hasher.update(b"\n")
        source_snapshot_hash = source_hasher.hexdigest()
        manifest = self._manifest_spec(col)
        stale_count = len(added) + len(modified) + len(removed)
        return {
            "store_name": store,
            "source_count": len(requested),
            "indexed_count": total,
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
            "unchanged": unchanged,
            "stale": bool(stale_count),
            "stale_count": stale_count,
            "source_snapshot_hash": source_snapshot_hash,
            "manifest_snapshot_hash": manifest.get("source_snapshot_hash"),
            "samples": {
                "added": added[:100],
                "modified": modified[:100],
                "removed": removed[:100],
            },
        }

    def get_record(
        self,
        store: str,
        chroma_id: str,
        *,
        include_updates: bool = False,
    ) -> dict[str, Any] | None:
        col = self._collection(store)
        payload = col.get(
            ids=[chroma_id],
            include=["documents", "metadatas"],
        )
        records = self._decode_result(payload, include_updates=include_updates)
        return records[0] if records else None

    def patch_existing(
        self,
        store: str,
        chroma_id: str,
        changes: dict[str, Any],
        *,
        audit_entries: list[dict[str, Any]] | None = None,
        document_field: str = "text",
        embedding_field: str = "embedding",
    ) -> dict[str, Any]:
        """Patch only changed record fields while preserving omitted data.

        The browser never needs to round-trip a complete record merely to edit
        one field. Audit history is appended server-side from small delta
        entries, avoiding the historical O(n) ``updates`` payload on every edit.
        """
        existing = self.get_record(store, chroma_id, include_updates=True)
        if existing is None:
            raise KeyError(f"Record {chroma_id!r} was not found.")
        merged = {
            key: value
            for key, value in existing.items()
            if key != "_chroma_id" and not key.startswith("_chroma_")
        }
        merged.update(changes or {})
        if audit_entries:
            history = list(merged.get("updates") or [])
            history.extend(audit_entries)
            merged["updates"] = history
        return self.update_existing(
            store,
            chroma_id,
            merged,
            document_field=document_field,
            embedding_field=embedding_field,
        )

    def delete_record(self, store: str, chroma_id: str) -> None:
        self._collection(store).delete(ids=[chroma_id])

    def delete_record_with_language_sync(self, store: str, chroma_id: str) -> dict[str, Any]:
        collection = self._collection(store)
        _, role, _ = self._language_spec(collection)
        self.delete_record(store, chroma_id)
        mirrored: list[str] = []
        if role == "primary":
            for child in self._language_children(store):
                self._collection(child["name"]).delete(ids=[chroma_id])
                mirrored.append(child["name"])
        return {"deleted": chroma_id, "mirrored_deletes": mirrored}

    def delete_work_with_language_sync(self, store: str, work: str) -> dict[str, Any]:
        """Delete every record whose decoded ``work`` metadata equals ``work``.

        Primary collections mirror the deletion into generated language children.
        Returning counts makes destructive UI feedback deterministic and allows the
        caller to distinguish an already-absent work from a successful removal.
        """
        collection = self._collection(store)
        _, role, _ = self._language_spec(collection)
        where = {"work": str(work)}
        payload = collection.get(where=where, include=["metadatas"])
        ids = [str(value) for value in (payload.get("ids") or [])]
        if ids:
            collection.delete(ids=ids)

        mirrored: dict[str, int] = {}
        if role == "primary":
            for child in self._language_children(store):
                child_collection = self._collection(child["name"])
                child_payload = child_collection.get(where=where, include=["metadatas"])
                child_ids = [str(value) for value in (child_payload.get("ids") or [])]
                if child_ids:
                    child_collection.delete(ids=child_ids)
                mirrored[child["name"]] = len(child_ids)
        return {
            "work": str(work),
            "deleted": len(ids),
            "mirrored_deletes": mirrored,
        }

    def semantic_candidates(
        self,
        store: str,
        query: str,
        n_results: int,
    ) -> list[dict[str, Any]]:
        col = self._collection(store)
        count = col.count()
        if count == 0:
            return []
        provider, model = self._embedding_spec(col)
        vector = self.embeddings.embed_query(
            query,
            provider=provider,
            model=model,
        )
        payload = col.query(
            query_embeddings=[vector],
            n_results=min(max(1, n_results), count),
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        ids = (payload.get("ids") or [[]])[0]
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        embedding_payload = payload.get("embeddings")
        if hasattr(embedding_payload, "tolist"):
            embedding_payload = embedding_payload.tolist()
        embeddings = (embedding_payload or [[]])[0]
        output: list[dict[str, Any]] = []
        for index, chroma_id in enumerate(ids):
            meta = decode_metadata(
                metadatas[index] if index < len(metadatas) else {}
            )
            document_field = meta.pop("_document_field", "text")
            logical_id = meta.pop("_record_id", None)
            meta.pop(self._RECORD_FINGERPRINT_KEY, None)
            record = dict(meta)
            if logical_id is not None and "record_id" not in record:
                record["record_id"] = logical_id
            record[document_field] = (
                documents[index] if index < len(documents) else ""
            )
            record["_chroma_id"] = chroma_id
            record = compact_record_payload(record, include_updates=False)
            embedding = (
                embeddings[index]
                if index < len(embeddings)
                else None
            )
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            output.append({
                "id": chroma_id,
                "record": record,
                "distance": (
                    float(distances[index])
                    if index < len(distances) and distances[index] is not None
                    else None
                ),
                "embedding": (
                    [float(x) for x in embedding]
                    if embedding is not None
                    else None
                ),
                "query_embedding": [float(x) for x in vector],
                "collection": store,
            })
        return output

    def search(
        self,
        store: str,
        query: str,
        n_results: int,
        where: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        col = self._collection(store)
        if col.count() == 0:
            return []
        provider, model = self._embedding_spec(col)
        vector = self.embeddings.embed_query(
            query,
            provider=provider,
            model=model,
        )
        payload = col.query(
            query_embeddings=[vector],
            n_results=min(n_results, col.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = (payload.get("ids") or [[]])[0]
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]

        out = []
        for index, chroma_id in enumerate(ids):
            meta = decode_metadata(
                metadatas[index] if index < len(metadatas) else {}
            )
            document_field = meta.pop("_document_field", "text")
            logical_id = meta.pop("_record_id", None)
            record = dict(meta)
            if logical_id is not None and "record_id" not in record:
                record["record_id"] = logical_id
            record[document_field] = (
                documents[index] if index < len(documents) else ""
            )
            record["_chroma_id"] = chroma_id
            record = compact_record_payload(record, include_updates=False)
            out.append({
                "id": chroma_id,
                "distance": (
                    distances[index] if index < len(distances) else None
                ),
                "record": record,
            })
        return out

    @staticmethod
    def _cosine(a: list[float] | None, b: list[float] | None) -> float:
        # Chroma may return embeddings as NumPy arrays. Never truth-test an
        # array: ``if not array`` raises the ambiguous truth-value error.
        if (
            a is None
            or b is None
            or len(a) == 0
            or len(b) == 0
            or len(a) != len(b)
        ):
            return 0.0
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        na = sum(float(x) * float(x) for x in a) ** 0.5
        nb = sum(float(y) * float(y) for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def mmr_search(self, store: str, query: str, n_results: int, where: dict[str, Any] | None = None, *, fetch_k: int = 100, lambda_mult: float = 0.7) -> list[dict[str, Any]]:
        col = self._collection(store)
        if col.count() == 0:
            return []
        provider, model = self._embedding_spec(col)
        query_vector = self.embeddings.embed_query(query, provider=provider, model=model)
        payload = col.query(query_embeddings=[query_vector], n_results=min(max(n_results, fetch_k), col.count()), where=where, include=["documents", "metadatas", "distances", "embeddings"])
        ids = (payload.get("ids") or [[]])[0]
        docs = (payload.get("documents") or [[]])[0]
        metas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        embedding_payload = payload.get("embeddings")
        # Chroma commonly returns embeddings as a NumPy ndarray. Convert it
        # before fallback/default handling so Python never evaluates the array
        # as a boolean.
        if hasattr(embedding_payload, "tolist"):
            embedding_payload = embedding_payload.tolist()
        embeddings = (embedding_payload or [[]])[0]
        candidates=[]
        for index,chroma_id in enumerate(ids):
            meta=decode_metadata(metas[index] if index < len(metas) else {})
            document_field=meta.pop("_document_field","text"); logical_id=meta.pop("_record_id",None); record=dict(meta)
            if logical_id is not None and "record_id" not in record: record["record_id"]=logical_id
            record[document_field]=docs[index] if index < len(docs) else ""; record["_chroma_id"]=chroma_id
            record=compact_record_payload(record,include_updates=False)
            candidates.append({"id":chroma_id,"distance":distances[index] if index < len(distances) else None,"record":record,"embedding":embeddings[index] if index < len(embeddings) else None})
        selected: list[dict[str, Any]] = []; remaining=list(candidates)
        while remaining and len(selected)<n_results:
            best_index=0; best_score=-float("inf")
            for index,candidate in enumerate(remaining):
                relevance=1.0/(1.0+max(0.0,float(candidate.get("distance") or 0.0)))
                diversity=max((self._cosine(candidate.get("embedding"),chosen.get("embedding")) for chosen in selected),default=0.0)
                score=lambda_mult*relevance-(1.0-lambda_mult)*diversity
                if score>best_score: best_score=score; best_index=index
            chosen=remaining.pop(best_index); chosen["mmr_score"]=best_score; chosen.pop("embedding",None); selected.append(chosen)
        return selected

    def filter_search(self, store: str, n_results: int, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        col = self._collection(store)
        where = where or {}
        contains_filters: dict[str, str] = {}
        native_where: dict[str, Any] = {}
        for field, value in where.items():
            if isinstance(value, dict) and "$contains" in value:
                contains_filters[field] = str(value.get("$contains") or "").casefold()
            else:
                native_where[field] = value
        args: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if native_where:
            args["where"] = native_where
        # A contains filter may target array-like metadata that Chroma persists
        # through DerridAI's metadata codec. Fetch the native-filtered set,
        # decode it, then perform membership/substring matching on the decoded
        # values. Exact-only filters retain Chroma's efficient limit path.
        if not contains_filters:
            args["limit"] = n_results
        rows = self._decode_result(col.get(**args))
        if contains_filters:
            def matches(record: dict[str, Any]) -> bool:
                for field, needle in contains_filters.items():
                    value = record.get(field)
                    if isinstance(value, (list, tuple, set)):
                        values = [str(item).casefold() for item in value]
                        if needle not in values and not any(needle in item for item in values):
                            return False
                    elif isinstance(value, dict):
                        if needle not in " ".join(f"{k} {v}" for k, v in value.items()).casefold():
                            return False
                    elif needle not in str(value or "").casefold():
                        return False
                return True
            rows = [row for row in rows if matches(row)]
        return [{"id": row.get("_chroma_id") or row.get("record_id"), "distance": None, "record": row} for row in rows[:n_results]]

    def keyword_search(self, store: str, query: str, n_results: int, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Case-insensitive record-text search with metadata filtering.

        Chroma's ``$contains`` document filter is case-sensitive on some
        versions/backends. Researcher "Record search" is expected to behave
        like ordinary text search, so use the native filter as a fast path and
        transparently fall back to a bounded case-folded scan when necessary.
        """
        col = self._collection(store)
        needle = str(query or "").strip()
        args: dict[str, Any] = {"include": ["documents", "metadatas"], "limit": n_results}
        if where:
            args["where"] = where
        if not needle:
            rows = self._decode_result(col.get(**args))
            return [{"id": row.get("_chroma_id") or row.get("record_id"), "distance": None, "record": row} for row in rows]

        fast_args = dict(args)
        fast_args["where_document"] = {"$contains": needle}
        try:
            rows = self._decode_result(col.get(**fast_args))
        except Exception as exc:
            if not self._is_query_capability_error(exc):
                raise
            rows = []
        if rows:
            return [{"id": row.get("_chroma_id") or row.get("record_id"), "distance": None, "record": row} for row in rows[:n_results]]

        scan_args: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if where:
            scan_args["where"] = where
        # Keep the fallback predictable on very large corpora while making the
        # common researcher search robust across capitalization differences.
        try:
            scan_args["limit"] = min(max(n_results * 50, 1000), 10000)
            candidates = self._decode_result(col.get(**scan_args))
        except Exception as exc:
            if not self._is_query_capability_error(exc):
                raise
            scan_args.pop("limit", None)
            candidates = self._decode_result(col.get(**scan_args))
        folded = needle.casefold()
        rows = [row for row in candidates if folded in str(row.get("text") or "").casefold()][:n_results]
        return [{"id": row.get("_chroma_id") or row.get("record_id"), "distance": None, "record": row} for row in rows]

    @staticmethod
    def _lexical_tokens(value: Any) -> list[str]:
        return [
            token
            for token in re.findall(r"[\w’'\-]+", str(value or "").casefold(), flags=re.UNICODE)
            if token
        ]

    def lexical_search(
        self,
        store: str,
        query: str,
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Bounded BM25-style lexical ranking over stored record text/metadata.

        Chroma does not expose a sparse/BM25 index in the local collection API,
        so DerridAI supplies a deterministic lexical leg for hybrid retrieval.
        The scorer is intentionally query-local: it computes document frequency
        only for terms in the current query and adds a modest exact-phrase boost.
        """
        query = str(query or "").strip()
        if not query:
            return self.keyword_search(store, query, n_results, where)
        col = self._collection(store)
        scan_args: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if where:
            scan_args["where"] = where
        try:
            scan_args["limit"] = min(max(n_results * 100, 2000), 20000)
            candidates = self._decode_result(col.get(**scan_args))
        except Exception as exc:
            if not self._is_query_capability_error(exc):
                raise
            scan_args.pop("limit", None)
            candidates = self._decode_result(col.get(**scan_args))
        if not candidates:
            return []

        query_tokens = self._lexical_tokens(query)
        if not query_tokens:
            return self.keyword_search(store, query, n_results, where)
        query_terms = list(dict.fromkeys(query_tokens))
        docs: list[tuple[dict[str, Any], list[str], str]] = []
        document_frequencies = {term: 0 for term in query_terms}
        total_length = 0
        for row in candidates:
            searchable = " ".join(
                str(row.get(field) or "")
                for field in (
                    "text",
                    "work",
                    "record_id",
                    "document_author",
                    "speaker",
                    "quoted_speaker",
                    "position_holder",
                    "target",
                )
            )
            folded = searchable.casefold()
            tokens = self._lexical_tokens(searchable)
            docs.append((row, tokens, folded))
            total_length += len(tokens)
            token_set = set(tokens)
            for term in query_terms:
                if term in token_set:
                    document_frequencies[term] += 1

        count = len(docs)
        avg_length = max(1.0, total_length / max(1, count))
        k1 = 1.2
        b = 0.75
        folded_phrase = query.casefold()
        scored: list[tuple[float, dict[str, Any]]] = []
        for row, tokens, folded in docs:
            if not tokens:
                continue
            frequencies: dict[str, int] = {}
            for token in tokens:
                if token in document_frequencies:
                    frequencies[token] = frequencies.get(token, 0) + 1
            score = 0.0
            length = len(tokens)
            for term in query_terms:
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                df = document_frequencies.get(term, 0)
                # Robertson/Sparck Jones BM25 IDF with a positive floor.
                idf = max(0.0, math.log(1.0 + (count - df + 0.5) / (df + 0.5)))
                denominator = tf + k1 * (1.0 - b + b * length / avg_length)
                score += idf * (tf * (k1 + 1.0)) / max(denominator, 1e-9)
            if folded_phrase and folded_phrase in folded:
                score += 2.5
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": row.get("_chroma_id") or row.get("record_id"),
                "distance": None,
                "lexical_score": score,
                "record": row,
            }
            for score, row in scored[:n_results]
        ]

    def hybrid_search(
        self,
        store: str,
        query: str,
        n_results: int,
        where: dict[str, Any] | None = None,
        *,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        """Fuse dense semantic and BM25-style lexical retrieval with reciprocal rank.

        This deliberately uses DerridAI's stored document text for the lexical leg
        rather than requiring a second infrastructure service. It gives exact names,
        quotations, neologisms, and multilingual terminology an independent path
        into the candidate set while preserving semantic recall.
        """
        query = str(query or "").strip()
        if not query:
            return self.filter_search(store, n_results, where)
        fetch_n = min(max(n_results * 4, 32), 400)
        semantic: list[dict[str, Any]] = []
        try:
            semantic = self.search(store, query, fetch_n, where)
        except ValueError:
            # Precomputed-vector collections do not have a query embedding function.
            semantic = []
        lexical = self.lexical_search(store, query, fetch_n, where)

        fused: dict[str, dict[str, Any]] = {}
        for search_type, rows in (("semantic", semantic), ("lexical", lexical)):
            for rank, row in enumerate(rows, start=1):
                item_id = str(row.get("id") or (row.get("record") or {}).get("record_id") or "")
                if not item_id:
                    continue
                score = 1.0 / (float(rrf_k) + float(rank))
                if item_id not in fused:
                    fused[item_id] = {
                        **row,
                        "hybrid_score": score,
                        "retrieval_hits": [{"type": search_type, "rank": rank}],
                    }
                else:
                    fused[item_id]["hybrid_score"] += score
                    fused[item_id]["retrieval_hits"].append({"type": search_type, "rank": rank})
                    if row.get("distance") is not None:
                        current = fused[item_id].get("distance")
                        if current is None or float(row["distance"]) < float(current):
                            fused[item_id]["distance"] = row["distance"]
        return sorted(
            fused.values(),
            key=lambda item: (float(item.get("hybrid_score") or 0.0), -float(item.get("distance") or 0.0)),
            reverse=True,
        )[:n_results]

    def _decode_result(
        self,
        payload: dict[str, Any],
        *,
        include_updates: bool = False,
    ) -> list[dict[str, Any]]:
        ids = payload.get("ids") or []
        docs = payload.get("documents") or []
        metas = payload.get("metadatas") or []
        out: list[dict[str, Any]] = []

        for index, chroma_id in enumerate(ids):
            meta = decode_metadata(
                metas[index] if index < len(metas) else {}
            )
            document_field = meta.pop("_document_field", "text")
            logical_id = meta.pop("_record_id", None)
            record = dict(meta)
            if logical_id is not None and "record_id" not in record:
                record["record_id"] = logical_id
            record[document_field] = (
                docs[index] if index < len(docs) else ""
            )
            record["_chroma_id"] = chroma_id
            out.append(compact_record_payload(record, include_updates=include_updates))
        return out
