# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from ..auth import SESSION_COOKIE, auth_store
from ..config import settings
from ..http_auth import require_admin
from ..models import (
    AuthBootstrapRequest,
    AuthLoginRequest,
    RoleCreateRequest,
    RolePermissionsUpdate,
    UserCreateRequest,
    UserUpdateRequest,
)

router = APIRouter(tags=["authentication"])


def _session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, Any]:
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    return {
        "bootstrap_required": auth_store.bootstrap_required(),
        "authenticated": user is not None,
        "user": user.public() if user else None,
    }


@router.post("/api/auth/bootstrap")
def auth_bootstrap(body: AuthBootstrapRequest, response: Response) -> dict[str, Any]:
    try:
        user = auth_store.bootstrap_admin(body.username, body.password)
        user = auth_store.record_login(user.id)
        token = auth_store.create_session(user.id)
        _session_cookie(response, token)
        return {"user": user.public(), "bootstrap_required": False}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/auth/login")
def auth_login(body: AuthLoginRequest, response: Response) -> dict[str, Any]:
    retry_after = auth_store.login_lockout_remaining(body.username)
    if retry_after > 0:
        # Locked usernames are reported identically whether or not the account
        # exists, because unknown usernames are throttled with the same counter.
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Too many failed sign-in attempts. Try again later.",
                "code": "login_locked",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
    user = auth_store.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    try:
        token = auth_store.create_session(user.id, expected_updated_at=user.updated_at)
    except ValueError as exc:
        # Hide whether the account was disabled or changed during this login.
        raise HTTPException(status_code=401, detail="Invalid username or password.") from exc
    _session_cookie(response, token)
    return {"user": user.public()}


@router.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, Any]:
    auth_store.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return {"user": user.public()}


@router.get("/api/auth/users")
def auth_users(request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"users": [user.public() for user in auth_store.list_users()]}


@router.post("/api/auth/users")
def auth_create_user(body: UserCreateRequest, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return {"user": auth_store.create_user(body.username, body.password, body.role).public()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/auth/users/{user_id}")
def auth_update_user(user_id: int, body: UserUpdateRequest, request: Request) -> dict[str, Any]:
    current = require_admin(request)
    if current.id == user_id and body.active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your current session account.")
    if current.id == user_id and body.role is not None and body.role != current.role:
        raise HTTPException(status_code=400, detail="You cannot change the role of your current session account.")
    try:
        user = auth_store.update_user(user_id, role=body.role, active=body.active, password=body.password)
        return {"user": user.public()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/auth/users/{user_id}")
def auth_delete_user(user_id: int, request: Request) -> dict[str, Any]:
    current = require_admin(request)
    if current.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your current session account.")
    try:
        auth_store.delete_user(user_id)
        return {"deleted": user_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/auth/roles")
def auth_roles(request: Request) -> dict[str, Any]:
    require_admin(request)
    roles, capabilities = auth_store.role_definitions()
    return {"roles": roles, "capabilities": capabilities}


@router.post("/api/auth/roles")
def auth_create_role(body: RoleCreateRequest, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        role = auth_store.create_role(body.name, body.description, body.clone_from)
        roles, capabilities = auth_store.role_definitions()
        return {"role": role, "roles": roles, "capabilities": capabilities}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/auth/roles/{role}/permissions")
def auth_update_role_permissions(role: str, body: RolePermissionsUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        permissions = auth_store.set_role_permissions(role, body.permissions)
        roles, capabilities = auth_store.role_definitions()
        return {"role": role, "permissions": permissions, "roles": roles, "capabilities": capabilities}
    except ValueError as exc:
        if "Unknown role" in str(exc):
            raise HTTPException(status_code=404, detail="Role not found.") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/auth/roles/{role}")
def auth_delete_role(role: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        auth_store.delete_role(role)
        roles, capabilities = auth_store.role_definitions()
        return {"deleted": role, "roles": roles, "capabilities": capabilities}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Role not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

