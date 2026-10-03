# Copyright 2026 Aaron John Schlosser, PhD.
"""Build self-contained, read-mostly DerridAI research sites from selected Works."""

from __future__ import annotations

import base64
import gzip
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
from urllib.parse import urlsplit, urlunsplit

from .corpus_publication import serialize_public_record, validate_publication_record
from .locales.en_us import EN_US
from .services import store
from .site_record_profile import (
    DEFAULT_SITE_RECORD_PROFILE,
    apply_record_profile,
    celf_conformance,
    normalize_site_record_profile,
)
from .system_store import normalize_locale_code, system_store
from .transformers_runtime_cache import ensure_runtime, notice_text

SITE_FORMAT = "derridai-static-site-v5"
_ASSET_DIR = Path(__file__).with_name("site_assets")
SITE_ASSET = _ASSET_DIR / "derridai-site.js"
SDK_ASSET = _ASSET_DIR / "derridai-sdk.js"
PACKAGE_GLOBAL = "__DERRIDAI_SITE_PACKAGE__"
SITE_ASSET_NAME = "derridai-site.js"
TRANSFORMERS_GLOBAL = "__DERRIDAI_TRANSFORMERS_RUNTIME__"
# Published paths of the Transformers.js runtime when a deployment serves it as separate files.
TRANSFORMERS_FILES_BASE = "vendor/transformers/"
_TRANSFORMERS_WASM_FACTORY = "ort-wasm-simd-threaded.mjs"
_TRANSFORMERS_WASM = "ort-wasm-simd-threaded.wasm"
_SAFE_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SiteBundle:
    """A generated site artifact and its stable publication identity."""

    payload: bytes
    filename: str
    publication_id: str
    record_count: int
    work_count: int
    record_profile: str = DEFAULT_SITE_RECORD_PROFILE
    include_vectors: bool = True


def _slug(value: str) -> str:
    slug = _SAFE_SLUG.sub("-", str(value or "").casefold()).strip("-")
    return slug[:72] or "derridai-research-site"


def _selected_languages(language_codes: Sequence[str] | None, locale: str) -> list[dict[str, str]]:
    """Resolve an explicit export selection against installed DerridAI languages."""
    installed = {str(item["code"]): item for item in system_store.list_languages()}
    requested = list(language_codes or [locale])
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in requested:
        try:
            code = normalize_locale_code(str(raw))
        except ValueError as exc:
            raise ValueError(f"Invalid site language {raw!r}.") from exc
        if code in seen:
            continue
        metadata = installed.get(code)
        if metadata is None:
            raise ValueError(f"Site language {code!r} is not installed in DerridAI.")
        selected.append(
            {
                "code": code,
                "name": str(metadata.get("name") or code),
                "flag": str(metadata.get("flag") or "🌐"),
            }
        )
        seen.add(code)
    if not selected:
        raise ValueError("Select at least one language for the published site.")
    return selected


def _runtime_strings(language_codes: Sequence[str]) -> dict[str, dict[str, str]]:
    """Export complete selected dictionaries; never hide missing translations with fallback."""
    required = {
        key: str(value)
        for key, value in EN_US.items()
        if key.startswith("site.runtime.")
    }
    result: dict[str, dict[str, str]] = {}
    for code in language_codes:
        language = system_store.get_language(code)
        if language is None:
            raise ValueError(f"Site language {code!r} is not installed in DerridAI.")
        installed = {
            key: str(value)
            for key, value in dict(language.get("dictionary") or {}).items()
            if key.startswith("site.runtime.")
        }
        if code == "en-US":
            installed = {**required, **installed}
        missing = sorted(set(required) - set(installed))
        if missing:
            preview = ", ".join(missing[:8])
            extra = len(missing) - min(8, len(missing))
            suffix = f" (+{extra} more)" if extra else ""
            raise ValueError(
                f"Site language {code!r} is missing {len(missing)} required static-site "
                f"translations: {preview}{suffix}"
            )
        result[code] = {key: installed[key] for key in required}
    return result


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


def _site_csp(*, standalone: bool = False) -> str:
    """Content-Security-Policy for a generated site.

    Model calls stay limited to http(s) origins. Every site includes Transformers.js, so WebAssembly
    compilation and blob: module/binary URLs are always allowed. ``standalone`` is the single-file form,
    which has no sibling files to allow.
    """
    if standalone:
        return (
            "default-src 'none'; connect-src http: https: blob: data:; img-src data: https:; "
            "style-src 'unsafe-inline'; script-src 'unsafe-inline' 'wasm-unsafe-eval' blob:; "
            "base-uri 'none'; form-action 'none'; worker-src blob:"
        )
    return (
        "default-src 'self' file: data: blob:; connect-src 'self' http: https: blob: data:; "
        "img-src 'self' file: data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' file: 'wasm-unsafe-eval' blob:"
    )


def _transformers_inline_source() -> str:
    """Script that exposes the runtime to the site as base64 strings; the browser inflates the WASM."""
    files = ensure_runtime()

    def encode(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    payload = {
        "engine_b64": encode(files["engine"]),
        "wasm_factory_b64": encode(files["wasm_factory"]),
        "wasm_gzip_b64": encode(gzip.compress(files["wasm"], compresslevel=9, mtime=0)),
        "notice": notice_text() + "\n" + files["license"].decode("utf-8"),
    }
    return f"globalThis.{TRANSFORMERS_GLOBAL}={_js_json(payload)};\n"


def build_site_bundle(
    *,
    store_name: str,
    works: Sequence[str],
    title: str,
    description: str = "",
    locale: str = "en-US",
    languages: Sequence[str] | None = None,
    record_profile: str = DEFAULT_SITE_RECORD_PROFILE,
    include_transformers: bool = True,
    include_vectors: bool = True,
    transformers_delivery: str = "inline",
) -> SiteBundle:
    """Create an SDK-backed static research site from one immutable publication snapshot.

    ``record_profile`` chooses how much Record metadata is packaged: ``complete`` keeps every public field,
    including FieldAssertions; ``reader`` keeps every metadata value but omits the FieldAssertion layer
    (see ``site_record_profile``). Every site includes Transformers.js. ``inline`` embeds it in the site
    script (two-file and single-file sites); ``files`` leaves it to the deployment to serve as separate
    files (nginx/Docker). ``include_transformers`` is accepted for older callers and is always treated as true.
    """
    del include_transformers
    if transformers_delivery not in {"inline", "files"}:
        raise ValueError("Unknown Transformers.js delivery mode.")
    record_profile = normalize_site_record_profile(record_profile)
    # Fetch (or verify the cached copy of) the runtime before any corpus work, so a failure is immediate.
    ensure_runtime()
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

    vector_contract = dict(projection.get("store") or {})
    full_records: list[dict[str, Any]] = []
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
        full_records.append(public_record)

        vector = item.get("embedding") if include_vectors else None
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
    if not full_records:
        raise ValueError("No publication-valid records remain after validating the selected works.")

    public_records = apply_record_profile(full_records, record_profile)
    # The profile must never remove what cELF Core requires; fail rather than publish a broken Record.
    profile_errors = [
        error for record in public_records for error in validate_publication_record(record)
    ]
    if profile_errors:
        raise ValueError(
            "The record metadata profile removed required fields: " + "; ".join(profile_errors[:8])
        )
    semantic_count = sum(1 for vector in vectors if vector)
    created_at = datetime.now(UTC).isoformat()
    publication_id = f"sitepub-{uuid.uuid4().hex}"
    selected_languages = _selected_languages(languages, locale)
    selected_language_codes = [item["code"] for item in selected_languages]
    try:
        requested_locale = normalize_locale_code(locale)
    except ValueError:
        requested_locale = selected_language_codes[0]
    normalized_locale = (
        requested_locale if requested_locale in selected_language_codes else selected_language_codes[0]
    )
    locale_dictionary = _runtime_strings([normalized_locale])[normalized_locale]
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
        "celf_conformance": celf_conformance(record_profile, full_records, public_records),
        "created_at": created_at,
        "title": title,
        "description": description,
        "locale": normalized_locale,
        "languages": selected_languages,
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
            "publication_vectors_included": semantic_count > 0,
            "local_annotations": True,
            "research": True,
            "shared_state": False,
            "browser_llm": False,
            "derridai_sdk": True,
            "host_supplied_generation": True,
            "browser_providers": True,
            "browser_vector_index": True,
            "transformers_runtime": transformers_delivery,
            "transformers_local_models": None,
            "progressive_work_loading": True,
        },
        "integrity": {
            "algorithm": "sha256",
            "records_and_vectors": integrity,
        },
        "strings": _runtime_strings(selected_language_codes),
    }
    package = {"manifest": manifest, "chunks": chunks}

    index_html = f"""<!doctype html>
<html lang="{html.escape(normalized_locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta http-equiv="Content-Security-Policy" content="{_site_csp()}">
  <title>{html.escape(title)}</title>
</head>
<body>
  <div id="app" role="status" aria-live="polite">{html.escape(locale_dictionary["site.runtime.loading_site"])}</div>
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
    site_interface_source = SITE_ASSET.read_text(encoding="utf-8")
    parts = [publication_source]
    if transformers_delivery == "inline":
        parts.append(_transformers_inline_source())
    published_site_bundle = "\n".join((*parts, sdk_source, site_interface_source))

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr("index.html", index_html.encode("utf-8"))
        bundle.writestr(SITE_ASSET_NAME, published_site_bundle.encode("utf-8"))

    return SiteBundle(
        payload=archive.getvalue(),
        filename=f"{_slug(title)}.zip",
        publication_id=publication_id,
        record_count=len(public_records),
        work_count=len(selected_works),
        record_profile=record_profile,
        include_vectors=include_vectors,
    )


def _inline_script_source(source: str) -> str:
    """Make standalone JavaScript safe to embed in an HTML script element."""
    return re.sub(r"</script", r"<\\/script", source, flags=re.IGNORECASE)


def _core_site_files(bundle: SiteBundle) -> dict[str, bytes]:
    """Read the two canonical publication files from a generated core bundle."""
    with zipfile.ZipFile(io.BytesIO(bundle.payload)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def build_local_site_file(
    *,
    store_name: str,
    works: Sequence[str],
    title: str,
    description: str = "",
    locale: str = "en-US",
    languages: Sequence[str] | None = None,
    record_profile: str = DEFAULT_SITE_RECORD_PROFILE,
    include_transformers: bool = True,
    include_vectors: bool = True,
) -> SiteBundle:
    """Create one self-contained HTML file for direct local use.

    Publication data, SDK, reference UI, and Transformers.js are embedded inline. External model
    calls are allowed only to http(s) origins and remain subject to browser CORS.
    ``include_transformers`` is accepted for older callers and is always treated as true.
    """
    del include_transformers
    core = build_site_bundle(
        store_name=store_name,
        works=works,
        title=title,
        description=description,
        locale=locale,
        languages=languages,
        record_profile=record_profile,
        include_vectors=include_vectors,
    )
    files = _core_site_files(core)
    index_html = files["index.html"].decode("utf-8")
    site_interface_source = _inline_script_source(files[SITE_ASSET_NAME].decode("utf-8"))

    external_csp = _site_csp()
    local_csp = _site_csp(standalone=True)
    if external_csp not in index_html:
        raise RuntimeError("The static-site CSP template changed unexpectedly.")
    index_html = index_html.replace(external_csp, local_csp)

    replacements = {
        f'<script src="./{SITE_ASSET_NAME}" defer></script>': (
            f"<script>{site_interface_source}</script>"
        ),
    }
    for external, inline in replacements.items():
        if external not in index_html:
            raise RuntimeError(f"Static-site template is missing {external}.")
        index_html = index_html.replace(external, inline)

    base_name = core.filename.removesuffix(".zip")
    return SiteBundle(
        payload=index_html.encode("utf-8"),
        filename=f"{base_name}.html",
        publication_id=core.publication_id,
        record_count=core.record_count,
        work_count=core.work_count,
        record_profile=core.record_profile,
        include_vectors=core.include_vectors,
    )


_NGINX_DOCKERFILE = """# Generated by DerridAI. One static nginx container; no application server.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html derridai-site.js /usr/share/nginx/html/
COPY vendor /usr/share/nginx/html/vendor
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=3s --retries=3 \\
  CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
"""

_NGINX_CONFIG_TEMPLATE = """server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location = /healthz {
        access_log off;
        default_type text/plain;
        return 200 "ok";
    }

    location = /index.html {
        add_header Cache-Control "no-cache";
        try_files $uri =404;
    }

    # Runtime files must 404 rather than fall back to index.html.
    location /vendor/ {
        try_files $uri =404;
        add_header X-Content-Type-Options "nosniff" always;
    }

__PROVIDER_PROXY__
    location / {
        try_files $uri $uri/ /index.html;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer" always;
    }
}
"""

_START_SCRIPT_TEMPLATE = """#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IMAGE=${DERRIDAI_SITE_IMAGE:-derridai-research-site}
CONTAINER=${DERRIDAI_SITE_CONTAINER:-derridai-research-site}
PORT=${DERRIDAI_SITE_PORT:-8080}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but was not found on PATH." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not available." >&2
  exit 1
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker build --tag "$IMAGE" "$SCRIPT_DIR"
docker run --detach \\
  --name "$CONTAINER" \\
  --restart unless-stopped \\
__HOST_GATEWAY_ARG__  --publish "${PORT}:80" \\
  "$IMAGE" >/dev/null

attempt=0
until docker exec "$CONTAINER" wget -q -O /dev/null http://127.0.0.1/healthz; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "nginx did not become healthy in time." >&2
    docker logs "$CONTAINER" >&2 || true
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    exit 1
  fi
  sleep 1
done

echo "DerridAI research site: http://localhost:${PORT}"
echo "Container: ${CONTAINER}"
"""

_STOP_SCRIPT = """#!/bin/sh
set -eu

CONTAINER=${DERRIDAI_SITE_CONTAINER:-derridai-research-site}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but was not found on PATH." >&2
  exit 1
fi

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  docker rm -f "$CONTAINER" >/dev/null
  echo "Stopped ${CONTAINER}."
else
  echo "Container ${CONTAINER} is not running."
fi
"""

_NGINX_README_TEMPLATE = """DerridAI research site — nginx Docker export

This directory is self-contained. It serves only static publication files and
does not require the DerridAI API, Node.js, Python, or Docker Compose.

Start:
  ./start.sh

Stop:
  ./stop.sh

The default URL is http://localhost:8080.

Optional environment variables:
  DERRIDAI_SITE_PORT       host port (default: 8080)
  DERRIDAI_SITE_IMAGE      Docker image name (default: derridai-research-site)
  DERRIDAI_SITE_CONTAINER  container name (default: derridai-research-site)

The site uses the same DerridAI SDK as custom Web applications. No API token or
model name is exported. Transformers.js is included so a visitor can run an
embedding model in the browser. The model itself is downloaded once by that
library and kept in the browser cache. A visitor may also save a named
OpenAI-compatible endpoint; its token stays in that browser.
__PROVIDER_PROXY_README__
"""


def _normalize_provider_proxy_upstream(value: str | None) -> tuple[str | None, bool]:
    """Validate an optional nginx provider upstream and map host loopback into Docker."""
    raw = str(value or "").strip()
    if not raw:
        return None, False
    if any(char in raw for char in "\r\n\t;{}"):
        raise ValueError("Provider proxy upstream contains characters that are unsafe in nginx.")

    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Provider proxy upstream must be a valid http:// or https:// URL.") from exc

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Provider proxy upstream must be a valid http:// or https:// URL.")
    if parsed.username or parsed.password:
        raise ValueError("Provider proxy upstream must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provider proxy upstream must not contain a query string or fragment.")

    path = parsed.path or "/"
    if any(char.isspace() for char in path) or any(char in path for char in ";{}\\$"):
        raise ValueError("Provider proxy upstream path contains characters that are unsafe in nginx.")

    hostname = parsed.hostname
    normalized_host = hostname
    host_gateway = hostname.lower() in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        normalized_host = "host.docker.internal"

    host_for_url = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    netloc = host_for_url if port is None else f"{host_for_url}:{port}"
    normalized_path = f"/{path.lstrip('/')}".rstrip("/") + "/"
    return urlunsplit((parsed.scheme, netloc, normalized_path, "", "")), host_gateway


def _nginx_config(provider_proxy_upstream: str | None) -> tuple[str, bool]:
    upstream, host_gateway = _normalize_provider_proxy_upstream(provider_proxy_upstream)
    proxy = ""
    if upstream:
        proxy = f"""    # Optional same-origin OpenAI-compatible provider bridge.
    # /provider/foo is forwarded to the configured upstream's /foo.
    location = /provider {{
        return 308 /provider/;
    }}

    location /provider/ {{
        limit_except GET POST {{
            deny all;
        }}

        proxy_pass {upstream};
        proxy_http_version 1.1;
        proxy_set_header Host $proxy_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_ssl_server_name on;
        client_max_body_size 20m;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }}

"""
    return _NGINX_CONFIG_TEMPLATE.replace("__PROVIDER_PROXY__\n", proxy), host_gateway


def _start_script(*, host_gateway: bool) -> str:
    gateway_arg = "  --add-host=host.docker.internal:host-gateway \\\n" if host_gateway else ""
    return _START_SCRIPT_TEMPLATE.replace("__HOST_GATEWAY_ARG__", gateway_arg)


def _nginx_readme(provider_proxy_upstream: str | None) -> str:
    upstream, _host_gateway = _normalize_provider_proxy_upstream(provider_proxy_upstream)
    proxy_help = ""
    if upstream:
        proxy_help = f"""
Same-origin provider proxy:
  Browser endpoint base: /provider
  Container upstream:    {upstream}

The browser may save /provider as its OpenAI-compatible endpoint. nginx forwards
/provider/... to the upstream server-side, so provider-side browser CORS settings
are not required. Only GET and POST are exposed through this route. If the
upstream was entered as localhost/127.0.0.1/::1, this bundle rewrites it to
host.docker.internal and start.sh adds Docker's host-gateway mapping.

SECURITY: anyone who can reach this site's /provider/ path can send allowed
requests to that model server. Before exposing the site beyond a trusted local
machine or network, put authentication or network access controls in front of
/provider/.
"""
    return _NGINX_README_TEMPLATE.replace("__PROVIDER_PROXY_README__", proxy_help)


def _zip_write(
    archive: zipfile.ZipFile,
    name: str,
    payload: bytes | str,
    *,
    executable: bool = False,
) -> None:
    """Write deployment files and preserve executable script bits."""
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o755 if executable else 0o644) << 16
    archive.writestr(info, data)


def build_nginx_site_bundle(
    *,
    store_name: str,
    works: Sequence[str],
    title: str,
    description: str = "",
    locale: str = "en-US",
    languages: Sequence[str] | None = None,
    record_profile: str = DEFAULT_SITE_RECORD_PROFILE,
    include_transformers: bool = True,
    include_vectors: bool = True,
    provider_proxy_upstream: str | None = None,
) -> SiteBundle:
    """Create a deployable multi-file site served by exactly one nginx container.

    Transformers.js is always copied under vendor/. ``include_transformers`` is accepted for older
    callers and is always treated as true.
    """
    del include_transformers
    nginx_config, host_gateway = _nginx_config(provider_proxy_upstream)
    core = build_site_bundle(
        store_name=store_name,
        works=works,
        title=title,
        description=description,
        locale=locale,
        languages=languages,
        record_profile=record_profile,
        include_vectors=include_vectors,
        transformers_delivery="files",
    )
    files = _core_site_files(core)
    archive = io.BytesIO()
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for name in ("index.html", SITE_ASSET_NAME):
            _zip_write(bundle, name, files[name])
        runtime = ensure_runtime()
        _zip_write(bundle, f"{TRANSFORMERS_FILES_BASE}transformers.min.js", runtime["engine"])
        _zip_write(
            bundle, f"{TRANSFORMERS_FILES_BASE}{_TRANSFORMERS_WASM_FACTORY}", runtime["wasm_factory"]
        )
        _zip_write(bundle, f"{TRANSFORMERS_FILES_BASE}{_TRANSFORMERS_WASM}", runtime["wasm"])
        _zip_write(bundle, f"{TRANSFORMERS_FILES_BASE}NOTICE.txt", notice_text())
        _zip_write(bundle, f"{TRANSFORMERS_FILES_BASE}LICENSE-transformers.js.txt", runtime["license"])
        _zip_write(bundle, "Dockerfile", _NGINX_DOCKERFILE)
        _zip_write(bundle, "nginx.conf", nginx_config)
        _zip_write(bundle, "start.sh", _start_script(host_gateway=host_gateway), executable=True)
        _zip_write(bundle, "stop.sh", _STOP_SCRIPT, executable=True)
        _zip_write(bundle, "README.txt", _nginx_readme(provider_proxy_upstream))

    base_name = core.filename.removesuffix(".zip")
    return SiteBundle(
        payload=archive.getvalue(),
        filename=f"{base_name}-nginx.zip",
        publication_id=core.publication_id,
        record_count=core.record_count,
        work_count=core.work_count,
        record_profile=core.record_profile,
        include_vectors=core.include_vectors,
    )
