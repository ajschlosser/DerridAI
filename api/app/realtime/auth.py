# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
