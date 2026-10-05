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

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .config import app_version_label, settings
from .graphql.router import graphql_router
from .middleware import authentication_middleware
from .realtime.broker import broker as realtime_broker
from .realtime.events import RealtimeObserver
from .realtime.router import router as realtime_router
from .routers.admin import router as admin_router
from .routers.annotations import router as annotations_router
from .routers.auth import router as auth_router
from .routers.chroma import router as chroma_router
from .routers.corpus import router as corpus_router
from .routers.derridai import router as derridai_router
from .routers.document_nlp import router as document_nlp_router
from .routers.gutenberg import router as gutenberg_router
from .routers.health import router as health_router
from .routers.i18n import router as i18n_router
from .routers.jobs import router as jobs_router
from .routers.llm import router as llm_router
from .routers.pipelines import router as pipelines_router
from .routers.research_filters import router as research_filters_router
from .routers.research_threads import router as research_threads_router
from .routers.sites import router as sites_router
from .routers.sources import router as sources_router
from .routers.stores import router as stores_router
from .routers.system import router as system_router
from .routers.system_data import router as system_data_router
from .validation_handlers import request_validation_error_handler

ROUTERS = (
    auth_router,
    annotations_router,
    system_router,
    research_threads_router,
    research_filters_router,
    system_data_router,
    i18n_router,
    health_router,
    gutenberg_router,
    llm_router,
    pipelines_router,
    jobs_router,
    chroma_router,
    admin_router,
    corpus_router,
    sources_router,
    sites_router,
    derridai_router,
    document_nlp_router,
    stores_router,
    # Read-only cELF query façade and the realtime notification plane sit beside
    # the REST command API; neither replaces it (docs/GRAPHQL.md, docs/REALTIME.md).
    graphql_router,
    realtime_router,
)

realtime_observer = RealtimeObserver(realtime_broker)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from .services import retention_scheduler

    if settings.realtime_enabled:
        realtime_observer.start()
    retention_scheduler.start()
    try:
        yield
    finally:
        retention_scheduler.stop()
        realtime_observer.stop()


def create_app() -> FastAPI:
    """Create and compose the DerridAI FastAPI application."""
    app = FastAPI(title="DerridAI API", version=app_version_label(), lifespan=lifespan)

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
