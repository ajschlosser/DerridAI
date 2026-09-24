# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import re

from .auth import role_has_capability


def is_public_language_route(method: str, path: str) -> bool:
    """Return whether a language-dictionary route is intentionally public."""
    return method.upper() == "GET" and (
        path == "/api/i18n/languages"
        or re.fullmatch(r"/api/i18n/languages/[^/]+", path) is not None
    )


def non_admin_route_allowed(role: str, path: str, method: str) -> bool:
    """Map non-admin HTTP routes to explicit capabilities.

    Administrator accounts are allowed by the authentication middleware before
    this policy is consulted. New API surfaces therefore remain denied to
    non-admin roles until they are deliberately added here.
    """
    method = method.upper()

    # Research needs availability and collection counts from health, while the
    # route itself redacts infrastructure details for non-admin callers.
    if path == "/api/health" and method == "GET":
        return True

    if is_public_language_route(method, path):
        return role_has_capability(role, "i18n.read")
    if path == "/api/i18n/content-policy" and method == "GET":
        return role_has_capability(role, "i18n.read")
    if path == "/api/system/researcher-providers" and method == "GET":
        return role_has_capability(role, "providers.researcher.use")

    if path == "/api/annotations" and method == "GET":
        return role_has_capability(role, "annotations.read")
    if path == "/api/annotations" and method == "POST":
        return role_has_capability(role, "annotations.write")
    if method == "DELETE" and re.fullmatch(r"/api/annotations/\d+", path):
        return role_has_capability(role, "annotations.write")

    if path == "/api/stores" and method == "GET":
        return role_has_capability(role, "corpus.read")
    if path.startswith("/api/stores/"):
        parts = path.strip("/").split("/")
        if method == "GET" and role_has_capability(role, "corpus.read"):
            # Keep this whitelist shape-specific. A future nested administrative
            # endpoint must not inherit access merely because it shares /stores/.
            if len(parts) == 3 and parts[2]:
                return True
            if len(parts) == 4 and parts[2] and parts[3] in {"records", "works"}:
                return True
            if len(parts) >= 5 and parts[2] and parts[3] == "records" and parts[4]:
                # Record IDs use a path converter and may themselves contain "/".
                return True
        if method == "POST" and len(parts) == 4 and parts[2] and parts[3] == "search":
            return role_has_capability(role, "corpus.search")

    if path == "/api/jobs" and method == "GET":
        return role_has_capability(role, "rag.jobs.own")
    if path == "/api/jobs/rag" and method == "POST":
        return role_has_capability(role, "rag.run")
    if path == "/api/jobs/rag/concurrency" and method == "GET":
        return role_has_capability(role, "rag.run")
    if path.startswith("/api/jobs/"):
        parts = [part for part in path.split("/") if part]
        # A user who starts Research must be able to read that job's completion.
        # Ownership is enforced in the jobs router; history, cancel, and delete
        # remain independently capability-gated here.
        if len(parts) == 3 and method == "GET":
            return role_has_capability(role, "rag.run") or role_has_capability(
                role,
                "rag.jobs.own",
            )
        if len(parts) == 3 and method == "DELETE":
            return role_has_capability(role, "rag.jobs.own")
        if len(parts) == 4 and parts[3] == "cancel" and method == "POST":
            return role_has_capability(role, "rag.jobs.own")

    return False
