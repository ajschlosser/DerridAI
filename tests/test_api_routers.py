"""Regression coverage for the first API-router extraction."""

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.requests import Request

from app.dependencies import get_store
from app.routers import (
    annotations_router,
    auth_router,
    i18n_router,
    llm_router,
    stores_router,
    system_router,
)


def _routes(router) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }


def test_auth_router_preserves_existing_http_contract():
    assert _routes(auth_router) == {
        ("GET", "/api/auth/status"),
        ("POST", "/api/auth/bootstrap"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/auth/users"),
        ("POST", "/api/auth/users"),
        ("PUT", "/api/auth/users/{user_id}"),
        ("DELETE", "/api/auth/users/{user_id}"),
        ("GET", "/api/auth/roles"),
        ("POST", "/api/auth/roles"),
        ("PUT", "/api/auth/roles/{role}/permissions"),
        ("DELETE", "/api/auth/roles/{role}"),
    }


def test_annotation_and_i18n_routers_preserve_existing_http_contract():
    assert _routes(annotations_router) == {
        ("GET", "/api/annotations"),
        ("POST", "/api/annotations"),
        ("DELETE", "/api/annotations/{annotation_id}"),
    }
    assert _routes(i18n_router) == {
        ("GET", "/api/i18n/languages"),
        ("GET", "/api/i18n/languages/{code}"),
        ("PUT", "/api/i18n/languages/{code}"),
        ("DELETE", "/api/i18n/languages/{code}"),
        ("POST", "/api/i18n/languages/install"),
        ("GET", "/api/i18n/content-policy"),
        ("GET", "/api/i18n/languages/{code}/content-policy"),
        ("PUT", "/api/i18n/languages/{code}/content-policy"),
    }


def test_system_and_llm_routers_preserve_existing_http_contract():
    assert _routes(system_router) == {
        ("GET", "/api/system/researcher-providers"),
        ("PUT", "/api/system/researcher-providers"),
        ("GET", "/api/system/storage"),
        ("POST", "/api/system/researcher-providers/status"),
        ("POST", "/api/system/researcher-providers/availability"),
        ("GET", "/api/live"),
        ("GET", "/api/health"),
        ("GET", "/api/config"),
    }
    assert _routes(llm_router) == {
        ("GET", "/api/llm/status"),
        ("POST", "/api/llm/status"),
        ("POST", "/api/llm/warmup"),
        ("POST", "/api/rag/grade"),
        ("POST", "/api/pdf/llm"),
        ("POST", "/api/llm/touchup"),
    }


def test_store_router_preserves_existing_http_contract():
    assert _routes(stores_router) == {
        ("GET", "/api/stores"),
        ("POST", "/api/stores"),
        ("POST", "/api/stores/preflight/embedding"),
        ("GET", "/api/stores/{store_name}"),
        ("PUT", "/api/stores/{store_name}/embedding"),
        ("PUT", "/api/stores/{store_name}/languages"),
        ("PUT", "/api/stores/{store_name}/protection"),
        ("POST", "/api/stores/{store_name}/derive-languages"),
        ("DELETE", "/api/stores/{store_name}"),
        ("DELETE", "/api/stores/{store_name}/works/{work:path}"),
        ("GET", "/api/response-cache/records"),
        ("GET", "/api/stores/{store_name}/records"),
        ("GET", "/api/stores/{store_name}/works"),
        ("POST", "/api/stores/{store_name}/records/status"),
        ("POST", "/api/stores/{store_name}/drift"),
        ("GET", "/api/stores/{store_name}/export"),
        ("GET", "/api/stores/{store_name}/records/{chroma_id:path}"),
        ("POST", "/api/stores/{store_name}/records"),
        ("PATCH", "/api/stores/{store_name}/records/{chroma_id:path}"),
        ("DELETE", "/api/stores/{store_name}/records/{chroma_id:path}"),
        ("POST", "/api/stores/{store_name}/records/bulk"),
        ("POST", "/api/stores/{store_name}/search"),
    }


def test_store_dependency_resolves_application_owned_store():
    app = FastAPI()
    store = object()
    app.state.store = store
    request = Request({"type": "http", "app": app, "headers": []})

    assert get_store(request) is store
