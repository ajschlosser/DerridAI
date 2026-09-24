# Copyright 2026 Aaron John Schlosser, PhD.
"""Which content-policy routes researcher accounts may reach.

Why: the researcher text filter needs a policy in the browser, but the readable word lists must stay
administrator-only. Researchers may fetch a hashed mirror (digests, no terms) and nothing that shows or
changes the plain terms.
How: calls the route allow-list function directly with a role, path, and method; no server is started.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

# Importing app.main pulls in ChromaDB; stub it and put api/ on the path so this file works
# on its own (pytest collects files alphabetically, so it cannot rely on an earlier test).
sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import route_policy  # noqa: E402
from app.route_policy import (  # noqa: E402
    is_public_language_route,
    non_admin_route_allowed,
)
from app.routers import health as health_routes  # noqa: E402


def test_researcher_can_load_hashed_content_policy_mirror():
    """A researcher may GET the hashed policy mirror at /api/i18n/content-policy."""
    assert non_admin_route_allowed("researcher", "/api/i18n/content-policy", "GET") is True


def test_researcher_cannot_read_or_write_plaintext_locale_policies():
    """Reading or writing a locale's plaintext policy is refused for researchers.

    GET and PUT on /api/i18n/languages/en-US/content-policy are denied, while the ordinary language list and
    a single language dictionary stay readable, so the UI can still load.
    """
    assert non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "GET") is False
    assert non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "PUT") is False
    assert non_admin_route_allowed("researcher", "/api/i18n/languages", "GET") is True
    assert non_admin_route_allowed("researcher", "/api/i18n/languages/en-US", "GET") is True


def test_researcher_route_allowlist_matches_only_intended_resource_shapes(monkeypatch):
    """A permitted route prefix cannot make a neighboring future route public."""
    monkeypatch.setattr(route_policy, "role_has_capability", lambda _role, _capability: True)

    assert non_admin_route_allowed("researcher", "/api/config", "GET") is False
    assert is_public_language_route("GET", "/api/i18n/languages/en-US") is True
    assert (
        is_public_language_route(
            "GET", "/api/i18n/languages/en-US/content-policy/extra"
        )
        is False
    )
    assert is_public_language_route("PUT", "/api/i18n/languages/en-US") is False
    assert non_admin_route_allowed("researcher", "/api/i18n/languages-extra", "GET") is False
    assert (
        non_admin_route_allowed(
            "researcher", "/api/i18n/languages/en-US/content-policy/extra", "GET"
        )
        is False
    )
    assert (
        non_admin_route_allowed("researcher", "/api/annotations/12/restore", "DELETE")
        is False
    )
    assert (
        non_admin_route_allowed("researcher", "/api/stores/Corpus/admin/secret", "GET")
        is False
    )
    assert (
        non_admin_route_allowed("researcher", "/api/stores/Corpus/export", "GET")
        is False
    )
    assert (
        non_admin_route_allowed(
            "researcher", "/api/stores/Corpus/records/id/extra", "GET"
        )
        is True
    )


def test_researcher_health_response_omits_internal_diagnostics(monkeypatch):
    """Researcher health retains workspace availability without revealing infra config."""
    monkeypatch.setattr(
        health_routes.store,
        "health",
        lambda: {
            "available": True,
            "mode": "http",
            "heartbeat_ok": True,
            "collection_count": 3,
            "url": "https://internal.example",
            "tenant": "private-tenant",
            "database": "private-db",
            "error": "internal diagnostic",
            "identity": "private-identity",
        },
    )

    def unexpected_llm_status(*_args, **_kwargs):
        raise AssertionError("admin diagnostics queried")

    monkeypatch.setattr(health_routes, "llm_status", unexpected_llm_status)
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(role="researcher")))

    response = health_routes.health(request)

    assert response["chroma"] == {
        "available": True,
        "mode": "http",
        "heartbeat_ok": True,
        "collection_count": 3,
    }
    assert "ollama" not in response
    assert "chroma_path" not in response
