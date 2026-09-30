# Copyright 2026 Aaron John Schlosser, PhD.
"""Build self-contained, read-mostly DerridAI research sites from selected Works."""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
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
from .system_store import system_store

SITE_FORMAT = "derridai-static-site-v1"
SITE_ASSET = Path(__file__).with_name("site_assets") / "derridai-site.js"
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


def _json_for_html(value: Any) -> str:
    """Serialize JSON without allowing documentary text to terminate the data script."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _runtime_strings() -> dict[str, dict[str, str]]:
    prefixes = ("site.runtime.",)
    return {
        "en-US": {key: value for key, value in EN_US.items() if key.startswith(prefixes)},
        "fr-CA": {key: value for key, value in FR_CA.items() if key.startswith(prefixes)},
    }


def _public_provider_profiles() -> list[dict[str, Any]]:
    """Only descriptors safe for a public bundle; the system store already removes secrets."""
    profiles = system_store.researcher_profiles()
    safe: list[dict[str, Any]] = []
    for raw in profiles:
        profile = {
            key: raw.get(key)
            for key in (
                "id",
                "name",
                "type",
                "model",
                "model_mode",
                "model_kind",
                "num_ctx",
                "num_predict",
                "temperature",
                "top_p",
            )
            if raw.get(key) not in (None, "")
        }
        if profile.get("id") and profile.get("type"):
            safe.append(profile)
    return safe


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


def build_site_bundle(
    *,
    store_name: str,
    works: Sequence[str],
    title: str,
    description: str = "",
    locale: str = "en-US",
) -> SiteBundle:
    """Create a static ZIP whose search/RAG runtime executes in the visitor's browser."""
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

    # Keep the vector projection structurally separate from authoritative Records.
    vector_contract = dict(projection.get("store") or {})
    vector_index = {
        "record_ids": [str(record["record_id"]) for record in public_records],
        "vectors": vectors,
        "dimension": dimension,
        "provider": vector_contract.get("embedding_provider"),
        "model": vector_contract.get("embedding_model"),
        "revision": vector_contract.get("embedding_revision"),
        "distance_metric": vector_contract.get("distance_metric") or "cosine",
        "text_field": vector_contract.get("text_field") or "text",
    }
    semantic_count = sum(1 for vector in vectors if vector)

    created_at = datetime.now(UTC).isoformat()
    publication_id = f"sitepub-{uuid.uuid4().hex}"
    csp_nonce = uuid.uuid4().hex
    normalized_locale = locale if locale in {"en-US", "fr-CA"} else "en-US"
    locale_dictionary = FR_CA if normalized_locale == "fr-CA" else EN_US
    title = str(title or "").strip() or locale_dictionary["site.runtime.site_title"]
    description = str(description or "").strip()

    digest_payload = json.dumps(
        {"records": public_records, "vector_index": vector_index},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    integrity = hashlib.sha256(digest_payload).hexdigest()

    publication = {
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
        "records": public_records,
        "vector_index": vector_index,
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
        "provider_profiles": _public_provider_profiles(),
        "features": {
            "browse": True,
            "lexical_search": True,
            "semantic_search": semantic_count > 0,
            "semantic_record_count": semantic_count,
            "local_annotations": True,
            "research": True,
            "shared_state": False,
        },
        "integrity": {
            "algorithm": "sha256",
            "records_and_vectors": integrity,
        },
        "strings": _runtime_strings(),
    }

    safe_data = _json_for_html(publication)
    index_html = f"""<!doctype html>
<html lang="{html.escape(normalized_locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self' data: blob:; connect-src 'self' http: https:; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'nonce-{csp_nonce}'">
  <title>{html.escape(title)}</title>
</head>
<body>
  <div id="app"></div>
  <script id="derridai-publication" type="application/json" nonce="{csp_nonce}">{safe_data}</script>
  <script src="./derridai-site.js" defer></script>
</body>
</html>
"""

    if not SITE_ASSET.exists():
        raise RuntimeError("The DerridAI static-site runtime is missing.")
    runtime_js = SITE_ASSET.read_bytes()

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr("index.html", index_html.encode("utf-8"))
        bundle.writestr("derridai-site.js", runtime_js)

    return SiteBundle(
        payload=archive.getvalue(),
        filename=f"{_slug(title)}.zip",
        publication_id=publication_id,
        record_count=len(public_records),
        work_count=len(selected_works),
    )
