# Copyright 2026 Aaron John Schlosser, PhD.
"""Build self-contained, read-mostly DerridAI research sites from selected Works."""

from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import re
import struct
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .corpus_publication import serialize_public_record, validate_publication_record
from .locales.en_us import EN_US
from .locales.fr_ca import FR_CA
from .services import store
SITE_FORMAT = "derridai-static-site-v3"
_ASSET_DIR = Path(__file__).with_name("site_assets")
SITE_ASSET = _ASSET_DIR / "derridai-site.js"
SDK_ASSET = _ASSET_DIR / "derridai-sdk.js"
PACKAGE_GLOBAL = "__DERRIDAI_SITE_PACKAGE__"
PUBLICATION_ASSET_NAME = "derridai-publication.js"
SDK_ASSET_NAME = "derridai-sdk.js"
SITE_ASSET_NAME = "derridai-site.js"
_SAFE_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SiteBundle:
    """A generated static site archive and its stable publication identity."""

    payload: bytes
    filename: str
    publication_id: str
    record_count: int
    work_count: int


def _slug(value: str) -> str:
    slug = _SAFE_SLUG.sub("-", str(value or "").casefold()).strip("-")
    return slug[:72] or "derridai-research-site"


def _runtime_strings() -> dict[str, dict[str, str]]:
    prefixes = ("site.runtime.",)
    return {
        "en-US": {key: value for key, value in EN_US.items() if key.startswith(prefixes)},
        "fr-CA": {key: value for key, value in FR_CA.items() if key.startswith(prefixes)},
    }


def _work_summary(records: Sequence[dict[str, Any]], work: str) -> dict[str, Any]:
    rows = [record for record in records if str(record.get("work") or "") == work]
    authors = sorted(
        {
            str(record.get("document_author") or "").strip()
            for record in rows
            if str(record.get("document_author") or "").strip()
        }
    )
    years = sorted(
        {
            str(record.get("publication_year") or record.get("year") or "").strip()
            for record in rows
            if str(record.get("publication_year") or record.get("year") or "").strip()
        }
    )
    citation = next(
        (
            str(record.get("full_citation") or record.get("citation") or "").strip()
            for record in rows
            if str(record.get("full_citation") or record.get("citation") or "").strip()
        ),
        "",
    )
    return {
        "work": work,
        "record_count": len(rows),
        "authors": authors,
        "years": years,
        "citation": citation,
    }


def _base64_json(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _base64_float32(vectors: Sequence[Sequence[float]]) -> str:
    payload = bytearray()
    for vector in vectors:
        payload.extend(struct.pack(f"<{len(vector)}f", *vector))
    return base64.b64encode(payload).decode("ascii")


def _js_json(value: Any) -> str:
    """Serialize a safe JavaScript object literal for an external script file."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _chunk_publication(
    *,
    selected_works: Sequence[str],
    records: Sequence[dict[str, Any]],
    vectors: Sequence[list[float] | None],
    dimension: int | None,
) -> list[dict[str, Any]]:
    """Package Records and vectors by Work so the browser can materialize them on demand."""
    chunks: list[dict[str, Any]] = []
    for ordinal, work in enumerate(selected_works):
        indexes = [
            index
            for index, record in enumerate(records)
            if str(record.get("work") or "") == work
        ]
        work_records = [records[index] for index in indexes]
        vector_ids: list[str] = []
        work_vectors: list[list[float]] = []
        if dimension:
            for index in indexes:
                vector = vectors[index]
                if not vector:
                    continue
                vector_ids.append(str(records[index]["record_id"]))
                work_vectors.append(vector)
        chunks.append(
            {
                "id": f"work-{ordinal + 1}",
                "work": work,
                "record_count": len(work_records),
                "records_b64": _base64_json(work_records),
                "vector_ids": vector_ids,
                "vectors_b64": _base64_float32(work_vectors) if work_vectors else "",
            }
        )
    return chunks


def build_site_bundle(
    *,
    store_name: str,
    works: Sequence[str],
    title: str,
    description: str = "",
    locale: str = "en-US",
) -> SiteBundle:
    """Create an SDK-backed static research site from one immutable publication snapshot."""
    selected_works = list(dict.fromkeys(str(item).strip() for item in works if str(item).strip()))
    if not selected_works:
        raise ValueError("Select at least one work.")
    if len(selected_works) > 500:
        raise ValueError("A site can include at most 500 works.")
    if not str(store_name or "").strip():
        raise ValueError("Choose a corpus database before creating a site.")

    projection = store.export_site_projection(str(store_name).strip(), selected_works)
    raw_records = list(projection.get("records") or [])
    if not raw_records:
        raise ValueError("The selected works have no records in the active corpus database.")

    indexed_works = {
        str(item.get("record", {}).get("work") or "").strip()
        for item in raw_records
        if isinstance(item, dict) and isinstance(item.get("record"), dict)
    }
    missing_works = [work for work in selected_works if work not in indexed_works]
    if missing_works:
        preview = ", ".join(missing_works[:8])
        extra = len(missing_works) - min(8, len(missing_works))
        suffix = f" (+{extra} more)" if extra else ""
        raise ValueError(
            "Site creation requires every selected work to be indexed in the active corpus "
            f"database. Missing: {preview}{suffix}"
        )

    public_records: list[dict[str, Any]] = []
    vectors: list[list[float] | None] = []
    ids: set[str] = set()
    dimension: int | None = None
    validation_errors: list[str] = []

    for item in raw_records:
        if not isinstance(item, dict) or not isinstance(item.get("record"), dict):
            continue
        source_record = dict(item["record"])
        public_record = serialize_public_record(source_record)
        errors = validate_publication_record(public_record)
        if errors:
            validation_errors.extend(errors)
            continue
        record_id = str(public_record.get("record_id") or "")
        if record_id in ids:
            raise ValueError(f"Duplicate record_id in site publication: {record_id}")
        ids.add(record_id)
        public_records.append(public_record)

        vector = item.get("embedding")
        if vector is None:
            vectors.append(None)
            continue
        numeric = [float(value) for value in vector]
        if not numeric:
            vectors.append(None)
            continue
        if dimension is None:
            dimension = len(numeric)
        elif len(numeric) != dimension:
            raise ValueError("The active corpus database contains incompatible embedding dimensions.")
        vectors.append(numeric)

    if validation_errors:
        preview = "; ".join(validation_errors[:8])
        extra = len(validation_errors) - min(8, len(validation_errors))
        suffix = f" (+{extra} more)" if extra else ""
        raise ValueError(
            "Site creation is blocked because selected records are not publication-valid: "
            f"{preview}{suffix}"
        )
    if not public_records:
        raise ValueError("No publication-valid records remain after validating the selected works.")

    vector_contract = dict(projection.get("store") or {})
    semantic_count = sum(1 for vector in vectors if vector)
    created_at = datetime.now(UTC).isoformat()
    publication_id = f"sitepub-{uuid.uuid4().hex}"
    normalized_locale = locale if locale in {"en-US", "fr-CA"} else "en-US"
    locale_dictionary = FR_CA if normalized_locale == "fr-CA" else EN_US
    title = str(title or "").strip() or locale_dictionary["site.runtime.site_title"]
    description = str(description or "").strip()

    digest_payload = json.dumps(
        {
            "records": public_records,
            "record_ids": [str(record["record_id"]) for record in public_records],
            "vectors": vectors,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    integrity = hashlib.sha256(digest_payload).hexdigest()

    chunks = _chunk_publication(
        selected_works=selected_works,
        records=public_records,
        vectors=vectors,
        dimension=dimension,
    )
    manifest = {
        "format": SITE_FORMAT,
        "publication_id": publication_id,
        "corpus_id": str(store_name).strip(),
        "publication_version": 1,
        "celf_version": "1.0",
        "created_at": created_at,
        "title": title,
        "description": description,
        "locale": normalized_locale,
        "works": [_work_summary(public_records, work) for work in selected_works],
        "vector_index": {
            "dimension": dimension,
            "provider": vector_contract.get("embedding_provider"),
            "model": vector_contract.get("embedding_model"),
            "revision": vector_contract.get("embedding_revision"),
            "distance_metric": vector_contract.get("distance_metric") or "cosine",
            "text_field": vector_contract.get("text_field") or "text",
        },
        "source_collection": {
            key: vector_contract.get(key)
            for key in (
                "name",
                "embedding_provider",
                "embedding_model",
                "embedding_dimension",
                "embedding_revision",
                "distance_metric",
                "retrieval_mode",
                "text_field",
                "filter_fields",
                "language_codes",
                "schema_id",
            )
            if vector_contract.get(key) not in (None, "")
        },
        "features": {
            "browse": True,
            "lexical_search": True,
            "semantic_search": semantic_count > 0,
            "semantic_record_count": semantic_count,
            "local_annotations": True,
            "research": True,
            "shared_state": False,
            "browser_llm": False,
            "derridai_sdk": True,
            "host_supplied_generation": True,
            "direct_provider_endpoints": False,
            "progressive_work_loading": True,
        },
        "integrity": {
            "algorithm": "sha256",
            "records_and_vectors": integrity,
        },
        "strings": _runtime_strings(),
    }
    package = {"manifest": manifest, "chunks": chunks}

    index_html = f"""<!doctype html>
<html lang="{html.escape(normalized_locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self' file: data: blob:; connect-src 'self'; img-src 'self' file: data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' file:">
  <title>{html.escape(title)}</title>
</head>
<body>
  <div id="app" role="status" aria-live="polite">Loading DerridAI research site…</div>
  <script src="./{PUBLICATION_ASSET_NAME}" defer></script>
  <script src="./{SDK_ASSET_NAME}" defer></script>
  <script src="./{SITE_ASSET_NAME}" defer></script>
</body>
</html>
"""

    if not SITE_ASSET.exists():
        raise RuntimeError("The DerridAI static-site reference UI is missing.")
    if not SDK_ASSET.exists():
        raise RuntimeError(
            "The DerridAI SDK distribution is missing. Run `cd web && npm run build:sdk`."
        )

    publication_source = f"globalThis.{PACKAGE_GLOBAL}={_js_json(package)};\n"
    sdk_source = SDK_ASSET.read_text(encoding="utf-8")
    runtime_source = SITE_ASSET.read_text(encoding="utf-8")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr("index.html", index_html.encode("utf-8"))
        bundle.writestr(PUBLICATION_ASSET_NAME, publication_source.encode("utf-8"))
        bundle.writestr(SDK_ASSET_NAME, sdk_source.encode("utf-8"))
        bundle.writestr(SITE_ASSET_NAME, runtime_source.encode("utf-8"))

    return SiteBundle(
        payload=archive.getvalue(),
        filename=f"{_slug(title)}.zip",
        publication_id=publication_id,
        record_count=len(public_records),
        work_count=len(selected_works),
    )
