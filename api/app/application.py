# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import app_version_label
from .middleware import authentication_middleware
from .routers.admin import router as admin_router
from .routers.annotations import router as annotations_router
from .routers.auth import router as auth_router
from .routers.chroma import router as chroma_router
from .routers.corpus import router as corpus_router
from .routers.derridai import router as derridai_router
from .routers.gutenberg import router as gutenberg_router
from .routers.health import router as health_router
from .routers.i18n import router as i18n_router
from .routers.jobs import router as jobs_router
from .routers.llm import router as llm_router
from .routers.stores import router as stores_router
from .routers.system import router as system_router
from .routers.system_data import router as system_data_router
from .validation_handlers import request_validation_error_handler

ROUTERS = (
    auth_router,
    annotations_router,
    system_router,
    system_data_router,
    i18n_router,
    health_router,
    gutenberg_router,
    llm_router,
    jobs_router,
    chroma_router,
    admin_router,
    corpus_router,
    derridai_router,
    stores_router,
)


def create_app() -> FastAPI:
    """Create and compose the DerridAI FastAPI application."""
    app = FastAPI(title="DerridAI API", version=app_version_label())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    app.exception_handler(RequestValidationError)(request_validation_error_handler)
    app.middleware("http")(authentication_middleware)
    return app
