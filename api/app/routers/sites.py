# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..http_auth import require_admin
from ..site_publication import build_site_bundle

router = APIRouter(tags=["sites"])


class SiteExportRequest(BaseModel):
    store: str = Field(min_length=1, max_length=300)
    works: list[str] = Field(min_length=1, max_length=500)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=4000)
    locale: Literal["en-US", "fr-CA"] = "en-US"


@router.post("/api/sites/export")
def export_site(body: SiteExportRequest, request: Request) -> Response:
    """Create a static ZIP from selected Works in one corpus collection."""
    require_admin(request)
    bundle = build_site_bundle(
        store_name=body.store,
        works=body.works,
        title=body.title,
        description=body.description,
        locale=body.locale,
    )
    return Response(
        content=bundle.payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{bundle.filename}"',
            "X-DerridAI-Publication-ID": bundle.publication_id,
            "X-DerridAI-Record-Count": str(bundle.record_count),
            "X-DerridAI-Work-Count": str(bundle.work_count),
        },
    )
