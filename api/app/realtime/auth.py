# Copyright 2026 Aaron John Schlosser, PhD.
"""WebSocket authentication from the existing session cookie, plus origin checks.

HTTP middleware does not run for WebSocket scopes, so the socket authenticates
itself. The username/role always come from the server-side session; nothing a
client sends can choose an identity.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocket

from ..auth import SESSION_COOKIE, auth_store
from ..config import settings


async def session_user(websocket: WebSocket) -> Any | None:
    cookie = websocket.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    return await run_in_threadpool(auth_store.user_for_session, cookie)


async def revalidate(cookie: str | None) -> Any | None:
    if not cookie:
        return None
    return await run_in_threadpool(auth_store.user_for_session, cookie)


def origin_allowed(websocket: WebSocket) -> bool:
    """Same-origin browsers (plus configured origins) only; non-browser clients send no Origin."""
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    allowed = {item.strip().rstrip("/") for item in settings.realtime_allowed_origins.split(",") if item.strip()}
    if origin.rstrip("/") in allowed:
        return True
    origin_host = urlsplit(origin).netloc.lower()
    hosts = {
        (websocket.headers.get("host") or "").lower(),
        (websocket.headers.get("x-forwarded-host") or "").split(",")[0].strip().lower(),
    }
    return bool(origin_host) and origin_host in hosts


def capabilities_for(user: Any) -> frozenset[str]:
    if user.role == "admin":
        return frozenset()
    return frozenset(auth_store.capabilities_for_role(user.role))
