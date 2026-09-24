# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .auth import SESSION_COOKIE, auth_store
from .response_filters import hide_pending_second_opinions
from .reviewer_context import current_reviewer, reviewer_id
from .route_policy import is_public_language_route, non_admin_route_allowed

PUBLIC_AUTH_ROUTES = frozenset(
    {
        "/api/auth/status",
        "/api/auth/bootstrap",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
    }
)


async def authentication_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Authenticate API requests and apply cross-cutting response privacy rules."""
    path = request.url.path
    public_i18n = is_public_language_route(request.method, path)

    if (
        not path.startswith("/api/")
        or path == "/api/live"
        or path in PUBLIC_AUTH_ROUTES
        or public_i18n
    ):
        return await call_next(request)

    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required."},
        )

    request.state.user = user
    current_reviewer.set(reviewer_id(user.id))

    if user.role != "admin" and not non_admin_route_allowed(
        user.role,
        path,
        request.method,
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Your role does not have permission to use this API feature."},
        )

    response = await call_next(request)
    if path.startswith("/api/pdf/corpus-builds"):
        return await hide_pending_second_opinions(response)
    return response
