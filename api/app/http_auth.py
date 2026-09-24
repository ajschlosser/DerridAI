# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from fastapi import HTTPException, Request

from .auth import AuthUser


def request_user(request: Request) -> AuthUser:
    """Return the authenticated request user or fail with HTTP 401."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def require_admin(request: Request) -> AuthUser:
    """Require an authenticated administrator for an endpoint."""
    user = request_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user
