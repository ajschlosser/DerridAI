# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import SESSION_COOKIE, auth_store, role_has_capability
from .config import app_version_label
from .corpus_reviewer_helpers import _present_for_reviewer
from .http_auth import request_user as _request_user
from .reviewer_context import current_reviewer, reviewer_id
from .routers.admin import router as admin_router
from .routers.annotations import router as annotations_router
from .routers.auth import router as auth_router
from .routers.chroma import router as chroma_router
from .routers.corpus import router as corpus_router
from .routers.health import health  # noqa: F401
from .routers.health import router as health_router
from .routers.i18n import router as i18n_router
from .routers.jobs import router as jobs_router
from .routers.llm import router as llm_router
from .routers.stores import router as stores_router
from .routers.system import router as system_router

logger = logging.getLogger(__name__)

app = FastAPI(title="DerridAI API", version=app_version_label())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(annotations_router)
app.include_router(system_router)
app.include_router(i18n_router)
app.include_router(health_router)
app.include_router(llm_router)
app.include_router(jobs_router)
app.include_router(chroma_router)
app.include_router(admin_router)
app.include_router(corpus_router)
app.include_router(stores_router)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep Pydantic internals out of the product UI. The client gets a stable
    # machine code and a concise field list; full details remain available to
    # server logs for diagnosis.
    errors = exc.errors()
    fields = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if str(part) not in {"body", "query", "path"}]
        label = ".".join(loc) if loc else "request"
        if label not in fields:
            fields.append(label)
    logger.warning("Request validation failed for %s: %s", getattr(_request, "url", "request"), errors)
    message = "Some submitted data is invalid. Review the highlighted fields and try again."
    if fields:
        message += " Fields: " + ", ".join(fields[:8]) + ("…" if len(fields) > 8 else "")
    return JSONResponse(status_code=422, content={"detail": message, "code": "request_validation_error", "fields": fields[:50]})


def _non_admin_route_allowed(role: str, path: str, method: str) -> bool:
    """Map non-admin HTTP routes to explicit capabilities.

    Admin is implicitly allowed everywhere. New API surfaces are therefore
    non-admin-denied until they are deliberately added here, matching the
    product rule that new functionality is admin-only by default.
    """
    method = method.upper()
    # Health is needed by the researcher workspace, but the full configuration
    # endpoint is an administrator surface. The health response itself is
    # projected for non-admins in health().
    if path == "/api/health" and method == "GET":
        return True
    if _is_public_language_route(method, path):
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
            # Keep this aligned with the read-only corpus routes. In particular,
            # don't let a future nested admin route inherit access from a prefix.
            if len(parts) == 3 and parts[2]:
                return True  # /api/stores/{store_name}
            if len(parts) == 4 and parts[2] and parts[3] in {"records", "works"}:
                return True
            if len(parts) >= 5 and parts[2] and parts[3] == "records" and parts[4]:
                return True  # record IDs use a path converter and may contain slashes
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
        # A user who may start Research must be able to read the one job they
        # just started so the workspace can surface completion. Ownership is
        # still enforced by _researcher_job_access; history/list, cancel and
        # delete remain independently controlled by rag.jobs.own.
        if len(parts) == 3 and method == "GET":
            return role_has_capability(role, "rag.run") or role_has_capability(role, "rag.jobs.own")
        if len(parts) == 3 and method == "DELETE":
            return role_has_capability(role, "rag.jobs.own")
        if len(parts) == 4 and parts[3] == "cancel" and method == "POST":
            return role_has_capability(role, "rag.jobs.own")
    return False


def _is_public_language_route(method: str, path: str) -> bool:
    """Match only public dictionary reads; keep neighboring API routes private."""
    return method.upper() == "GET" and (
        path == "/api/i18n/languages"
        or re.fullmatch(r"/api/i18n/languages/[^/]+", path) is not None
    )


@app.middleware("http")
async def authentication_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    public_auth = {"/api/auth/status", "/api/auth/bootstrap", "/api/auth/login", "/api/auth/logout", "/api/auth/me"}
    public_i18n = _is_public_language_route(request.method, path)
    if not path.startswith("/api/") or path == "/api/live" or path in public_auth or public_i18n:
        return await call_next(request)
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})
    request.state.user = user
    current_reviewer.set(reviewer_id(user.id))
    if user.role != "admin" and not _non_admin_route_allowed(user.role, path, request.method):
        return JSONResponse(status_code=403, content={"detail": "Your role does not have permission to use this API feature."})
    response = await call_next(request)
    if path.startswith("/api/pdf/corpus-builds"):
        return await _hide_pending_second_opinions(response)
    return response


def scrub_second_opinions(node: Any) -> bool:
    """Blank, in place, every answer the current reviewer is still owed an independent second opinion on.

    A record served by any corpus-build route (list, save, accept, split, touch-up, bulk edit…) passes through here, so a
    second reviewer cannot see the first reviewer's answer through whichever response happens to carry the record.
    Returns whether anything was hidden.
    """
    hidden = False
    if isinstance(node, dict):
        if "record_id" in node and isinstance(node.get("second_opinion"), dict):
            before = json.dumps(node, default=str)
            _present_for_reviewer(node)
            hidden = json.dumps(node, default=str) != before
        for value in node.values():
            hidden = scrub_second_opinions(value) or hidden
    elif isinstance(node, list):
        for item in node:
            hidden = scrub_second_opinions(item) or hidden
    return hidden


async def _hide_pending_second_opinions(response):
    """Apply scrub_second_opinions to a JSON response, reading it only when it mentions a second opinion at all."""
    if "application/json" not in str(response.headers.get("content-type", "")):
        return response
    body = b"".join([chunk async for chunk in response.body_iterator]) if hasattr(response, "body_iterator") else bytes(response.body)
    headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "content-type"}}
    if b"second_opinion" in body:
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        if payload is not None and current_reviewer.get() and scrub_second_opinions(payload):
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return Response(content=body, status_code=response.status_code, headers=headers, media_type="application/json")


