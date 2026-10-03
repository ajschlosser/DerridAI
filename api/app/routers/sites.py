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

import json
import queue
import threading
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from ..http_auth import require_admin
from ..site_embeddings import (
    BrowserEmbeddingUnavailableError,
    browser_embedding_profile,
)
from ..site_publication import (
    build_local_site_file,
    build_nginx_site_bundle,
    build_site_bundle,
)
from ..system_store import system_store
from ..transformers_runtime_cache import (
    RuntimeUnavailableError,
    delete_runtime,
    ensure_runtime,
    runtime_info,
)

router = APIRouter(tags=["sites"])


class SiteExportRequest(BaseModel):
    store: str = Field(min_length=1, max_length=300)
    works: list[str] = Field(min_length=1, max_length=500)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=4000)
    locale: str = Field(default="en-US", min_length=2, max_length=35)
    languages: list[str] = Field(default_factory=list, max_length=100)
    export_format: Literal["two-file", "local-single-file", "nginx-docker"] = "two-file"
    # "reader" packages only the Record metadata a site reads and cites; it omits FieldAssertions.
    record_profile: Literal["complete", "reader"] = "complete"
    # Accepted for older clients. Every export includes Transformers.js; model weights are never packaged.
    include_transformers: bool = True
    # Backward compatibility for clients that predate vector_strategy. True maps to source; false maps to browser.
    include_vectors: bool | None = None
    # browser-default publishes vectors generated with the site's pinned multilingual browser model;
    # source copies the active collection vectors; browser omits vectors for per-browser indexing.
    vector_strategy: Literal["browser-default", "source", "browser"] | None = None
    # nginx/Docker only: expose a same-origin /provider/ bridge to this OpenAI-compatible base URL.
    provider_proxy_upstream: str | None = Field(default=None, max_length=2048)


@router.get("/api/sites/export-options")
def site_export_options(request: Request) -> dict[str, object]:
    """Return administrator-visible export choices. Provider profiles are never exported."""
    require_admin(request)
    return {
        "languages": system_store.list_languages(),
        "transformers_runtime": runtime_info(),
        "browser_embedding_profile": browser_embedding_profile(),
    }


@router.post("/api/sites/transformers-runtime")
def download_transformers_runtime(request: Request) -> StreamingResponse:
    """Download the pinned Transformers.js runtime, reporting byte progress as newline-delimited JSON."""
    require_admin(request)

    def generate():
        events: queue.Queue[dict[str, object] | None] = queue.Queue()

        def worker() -> None:
            try:
                ensure_runtime(on_progress=events.put)
            except Exception as exc:  # noqa: BLE001 - surfaced to the administrator as a download failure
                events.put({"status": "error", "detail": str(exc)})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = events.get()
            if item is None:
                break
            yield (json.dumps(item) + "\n").encode("utf-8")

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.delete("/api/sites/transformers-runtime")
def delete_transformers_runtime(request: Request) -> dict[str, object]:
    """Delete the cached Transformers.js runtime so the next export downloads it again."""
    require_admin(request)
    delete_runtime()
    return {"transformers_runtime": runtime_info()}


@router.post("/api/sites/export")
def export_site(body: SiteExportRequest, request: Request) -> Response:
    """Create a two-file, local single-file, or nginx/Docker research-site export."""
    require_admin(request)
    try:
        provider_proxy_upstream = str(body.provider_proxy_upstream or "").strip() or None
        if provider_proxy_upstream and body.export_format != "nginx-docker":
            raise ValueError("Provider proxy upstream is available only for the nginx Docker export.")

        if body.export_format == "two-file":
            bundle = build_site_bundle(
                store_name=body.store,
                works=body.works,
                title=body.title,
                description=body.description,
                locale=body.locale,
                languages=body.languages or [body.locale],
                include_transformers=body.include_transformers,
                include_vectors=body.include_vectors,
                vector_strategy=body.vector_strategy,
                record_profile=body.record_profile,
            )
        elif body.export_format == "local-single-file":
            bundle = build_local_site_file(
                store_name=body.store,
                works=body.works,
                title=body.title,
                description=body.description,
                locale=body.locale,
                languages=body.languages or [body.locale],
                include_transformers=body.include_transformers,
                include_vectors=body.include_vectors,
                vector_strategy=body.vector_strategy,
                record_profile=body.record_profile,
            )
        else:
            bundle = build_nginx_site_bundle(
                store_name=body.store,
                works=body.works,
                title=body.title,
                description=body.description,
                locale=body.locale,
                languages=body.languages or [body.locale],
                include_transformers=body.include_transformers,
                include_vectors=body.include_vectors,
                vector_strategy=body.vector_strategy,
                record_profile=body.record_profile,
                provider_proxy_upstream=provider_proxy_upstream,
            )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeUnavailableError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The Transformers.js runtime could not be downloaded. Retry the download, then create the site. {exc}",
        ) from exc
    except BrowserEmbeddingUnavailableError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The browser-ready semantic vectors could not be built. {exc}",
        ) from exc
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
            "X-DerridAI-Record-Profile": bundle.record_profile,
            "X-DerridAI-Transformers-Runtime": "included",
            "X-DerridAI-Publication-Vectors": "included" if bundle.include_vectors else "omitted",
            "X-DerridAI-Vector-Strategy": bundle.vector_strategy,
        },
    )
