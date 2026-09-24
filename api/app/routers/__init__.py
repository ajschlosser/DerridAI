# Copyright 2026 Aaron John Schlosser, PhD.
"""HTTP router exports for application composition."""

from .annotations import router as annotations_router
from .auth import router as auth_router
from .i18n import router as i18n_router
from .jobs import router as jobs_router
from .llm import router as llm_router
from .records import router as records_router
from .source_assets import router as source_assets_router
from .stores import router as stores_router
from .system import router as system_router

__all__ = [
    "annotations_router",
    "auth_router",
    "i18n_router",
    "jobs_router",
    "llm_router",
    "records_router",
    "source_assets_router",
    "stores_router",
    "system_router",
]
