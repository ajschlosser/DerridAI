# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..http_auth import require_admin
from ..site_publication import build_local_site_file, build_nginx_site_bundle, build_site_bundle
from ..system_store import system_store

router = APIRouter(tags=["sites"])


class SiteExportRequest(BaseModel):
    store: str = Field(min_length=1, max_length=300)
    works: list[str] = Field(min_length=1, max_length=500)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=4000)
    locale: str = Field(default="en-US", min_length=2, max_length=35)
    languages: list[str] = Field(default_factory=list, max_length=100)
    provider_profile_ids: list[str] = Field(default_factory=list, max_length=100)
    export_format: Literal["two-file", "local-single-file", "nginx-docker"] = "two-file"


@router.get("/api/sites/export-options")
def site_export_options(request: Request) -> dict[str, object]:
    """Return administrator-visible language and safe provider choices for site export."""
    require_admin(request)
    return {
        "languages": system_store.list_languages(),
        "provider_profiles": system_store.researcher_profiles(),
    }


@router.post("/api/sites/export")
def export_site(body: SiteExportRequest, request: Request) -> Response:
    """Create a two-file, local single-file, or nginx/Docker research-site export."""
    require_admin(request)
    try:
        if body.export_format == "two-file":
            builder = build_site_bundle
        elif body.export_format == "local-single-file":
            builder = build_local_site_file
        else:
            builder = build_nginx_site_bundle
        bundle = builder(
            store_name=body.store,
            works=body.works,
            title=body.title,
            description=body.description,
            locale=body.locale,
            languages=body.languages or [body.locale],
            provider_profile_ids=body.provider_profile_ids,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=bundle.payload,
        media_type=(
            "text/html; charset=utf-8"
            if body.export_format == "local-single-file"
            else "application/zip"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{bundle.filename}"',
            "X-DerridAI-Publication-ID": bundle.publication_id,
            "X-DerridAI-Record-Count": str(bundle.record_count),
            "X-DerridAI-Work-Count": str(bundle.work_count),
        },
    )
