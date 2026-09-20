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

# Importing app.main pulls in ChromaDB; stub it and put api/ on the path so this file works
# on its own (pytest collects files alphabetically, so it cannot rely on an earlier test).
sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.main import _non_admin_route_allowed  # noqa: E402


def test_researcher_can_load_hashed_content_policy_mirror():
    """A researcher may GET the hashed policy mirror at /api/i18n/content-policy."""
    assert _non_admin_route_allowed("researcher", "/api/i18n/content-policy", "GET") is True


def test_researcher_cannot_read_or_write_plaintext_locale_policies():
    """Reading or writing a locale's plaintext policy is refused for researchers.

    GET and PUT on /api/i18n/languages/en-US/content-policy are denied, while the ordinary language list and
    a single language dictionary stay readable, so the UI can still load.
    """
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "GET") is False
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "PUT") is False
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages", "GET") is True
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US", "GET") is True
