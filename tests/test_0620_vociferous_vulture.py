# Copyright 2026 Aaron John Schlosser, PhD.
"""Researchers may load hashed policies; plaintext locale lists stay admin-only."""
from __future__ import annotations

from app.main import _non_admin_route_allowed


def test_researcher_can_load_hashed_content_policy_mirror():
    assert _non_admin_route_allowed("researcher", "/api/i18n/content-policy", "GET") is True


def test_researcher_cannot_read_or_write_plaintext_locale_policies():
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "GET") is False
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US/content-policy", "PUT") is False
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages", "GET") is True
    assert _non_admin_route_allowed("researcher", "/api/i18n/languages/en-US", "GET") is True
