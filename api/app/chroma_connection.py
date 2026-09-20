# Copyright 2026 Aaron John Schlosser, PhD.
"""Chroma connection identity: embedded filesystem vs HTTP server.

Why: DerridAI historically opened chromadb.PersistentClient against a host-mounted
directory. Administrators also need to point the API at a running Chroma server
(the compose service, or one already on the host), the same way Ollama is either
the provided container or a local process. Vector stores remain derived data;
this module only names the backend.
How: pure parsing and identity helpers with no chromadb import, so tests and the
store can share one contract without a live database.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

EMBEDDED_ALIASES = {"embedded", "local", "persistent", "filesystem", "path"}
HTTP_ALIASES = {"http", "https", "server", "remote", "chroma"}
DEFAULT_TENANT = "default_tenant"
DEFAULT_DATABASE = "default_database"
DEFAULT_HTTP_URL = "http://chroma:8000"


def normalize_mode(value: str | None) -> str:
    """Return ``embedded`` or ``http``. Empty values default to embedded."""
    mode = str(value or "embedded").strip().lower()
    if mode in EMBEDDED_ALIASES:
        return "embedded"
    if mode in HTTP_ALIASES:
        return "http"
    raise ValueError("Chroma mode must be embedded or http.")


def parse_http_endpoint(url: str) -> dict[str, Any]:
    """Validate an absolute Chroma server URL and return a connection spec.

    chromadb.HttpClient takes a hostname and port, not a full origin. Token
    credentials belong in headers, not in the URL.
    """
    raw = str(url or "").strip()
    if not raw:
        raise ValueError(
            "A Chroma server URL is required. "
            "Example: http://chroma:8000 or http://host.docker.internal:8001."
        )
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Chroma server URL must be an absolute http(s) URL, "
            "for example http://chroma:8000 or http://host.docker.internal:8001."
        )
    if parsed.username or parsed.password:
        raise ValueError(
            "Do not put Chroma credentials in the URL. Use the token field."
        )
    path = parsed.path.rstrip("/")
    for suffix in ("/api/v2", "/api/v1", "/api"):
        if path.endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
            break
    display = urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return {
        "scheme": parsed.scheme,
        "ssl": parsed.scheme == "https",
        "hostname": parsed.hostname,
        "port": parsed.port,
        "host": display,
        "display": display,
    }


def http_client_kwargs(url: str) -> dict[str, Any]:
    """Map a validated origin onto chromadb.HttpClient host/port/ssl."""
    parsed = parse_http_endpoint(url)
    hostname = parsed.get("hostname")
    if not hostname:
        raise ValueError("Chroma server URL must include a hostname.")
    port = parsed.get("port")
    if port is None:
        port = 443 if parsed["ssl"] else 8000
    return {"host": str(hostname), "port": int(port), "ssl": bool(parsed["ssl"])}


def connection_identity(
    *,
    mode: str,
    path: str | None = None,
    host_path_hint: str | None = None,
    url: str | None = None,
    tenant: str | None = None,
    database: str | None = None,
) -> str:
    """Human-readable backend identity for health chips and backups. Never a secret."""
    normalized = normalize_mode(mode)
    if normalized == "http":
        endpoint = str(url or "").strip() or DEFAULT_HTTP_URL
        tenant_name = str(tenant or DEFAULT_TENANT).strip() or DEFAULT_TENANT
        database_name = str(database or DEFAULT_DATABASE).strip() or DEFAULT_DATABASE
        extra = ""
        if tenant_name != DEFAULT_TENANT or database_name != DEFAULT_DATABASE:
            extra = f" · {tenant_name}/{database_name}"
        return f"Chroma server · {endpoint}{extra}"
    hint = str(host_path_hint or path or "").strip()
    return f"Local Chroma · {hint}" if hint else "Local Chroma"


def public_http_config(http: dict[str, Any] | None) -> dict[str, Any]:
    """Return the HTTP identity that may be sent to the browser. Token omitted."""
    payload = dict(http or {})
    url = str(payload.get("url") or "").strip()
    display = ""
    if url:
        try:
            display = str(parse_http_endpoint(url)["display"])
        except ValueError:
            display = url
    return {
        "url": display,
        "tenant": str(payload.get("tenant") or DEFAULT_TENANT).strip() or DEFAULT_TENANT,
        "database": str(payload.get("database") or DEFAULT_DATABASE).strip()
        or DEFAULT_DATABASE,
        "token_configured": bool(str(payload.get("token") or "").strip()),
    }
