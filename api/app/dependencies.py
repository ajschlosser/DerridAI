# Copyright 2026 Aaron John Schlosser, PhD.
"""FastAPI request dependencies shared by API routers."""

from __future__ import annotations

from typing import cast

from fastapi import HTTPException, Request

from .auth import AuthUser
from .chroma_store import ChromaStore


def request_user(request: Request) -> AuthUser:
    """Return the authenticated request user or fail with the API's standard 401."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return cast(AuthUser, user)


def require_admin(request: Request) -> AuthUser:
    """Require an authenticated administrator for an API operation."""
    user = request_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def get_store(request: Request) -> ChromaStore:
    """Resolve the application-owned vector store without importing ``main``.

    Routers depend on application state rather than module globals so they remain
    independently importable and testable. ``main.py`` owns service construction
    and places the configured store on ``app.state`` during application setup.
    """
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise RuntimeError("Application vector store is not initialized.")
    return cast(ChromaStore, store)
