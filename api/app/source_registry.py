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

"""Compact, paginated source rows for the Sources workspace and the Corpus Builder selector.

Rows are derived from the canonical SourceDocument assets plus capture links and
build summaries. They never include source text or blocks. Parsed asset rows are
cached by file mtime so a page of 50 rows does not re-read hundreds of JSON files.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .source_identity import normalize_language, normalize_languages

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()
SORTS = {"title", "added", "provider", "language", "author"}
BUILD_STATE = {"completed": "built", "published": "built", "failed": "failed", "cancelled": "not_built"}


def _provider(meta: dict[str, Any]) -> str:
    catalog = meta.get("catalog_metadata") or {}
    if catalog.get("provider"):
        return str(catalog["provider"])
    if catalog.get("gutenberg_id") or meta.get("media_kind") == "gutenberg":
        return "gutenberg"
    url = str(meta.get("source_url") or "")
    if "wikisource.org" in url:
        return "wikisource"
    return "web" if url else "upload"


def asset_row(meta: dict[str, Any]) -> dict[str, Any]:
    catalog = meta.get("catalog_metadata") or {}
    initial = meta.get("initial_metadata") or {}
    languages = normalize_languages(catalog.get("document_languages") or []) or normalize_languages(
        [catalog.get("language") or initial.get("language") or ""]
    )
    captured = catalog.get("captured_by") or {}
    return {
        "source_document_id": str(meta.get("asset_id")),
        "title": str(catalog.get("title") or initial.get("title") or meta.get("filename") or ""),
        "filename": str(meta.get("filename") or ""),
        "provider": _provider(meta),
        "provider_item_id": str(catalog.get("provider_item_id") or catalog.get("gutenberg_id") or "") or None,
        "document_author": str(catalog.get("document_author") or initial.get("document_author") or "") or None,
        "document_languages": languages,
        "original_language": normalize_language(catalog.get("original_language")),
        "source_project_language": catalog.get("source_project_language"),
        "canonical_work_id": catalog.get("canonical_work_id"),
        "relationship_to_work": catalog.get("relationship_to_work"),
        "contribution_role": catalog.get("contribution_role"),
        "edition": catalog.get("edition") or initial.get("edition"),
        "translator": catalog.get("translator"),
        "media_kind": str(meta.get("media_kind") or "pdf"),
        "acquisition_status": "ready",
        "source_hash_short": str(meta.get("sha256") or "")[:12] or None,
        "created_at": meta.get("created_at"),
        "derived_from_asset_id": meta.get("derived_from_asset_id"),
        "block_count": meta.get("block_count"),
        "_capture_hint": captured.get("capture_id"),
    }


def _load_rows(asset_dir: Path) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    for path in asset_dir.glob("pdf-*.json"):
        key = str(path)
        seen.add(key)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        with _CACHE_LOCK:
            cached = _CACHE.get(key)
        if cached and cached[0] == mtime:
            rows.append(cached[1])
            continue
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict) or not meta.get("asset_id"):
            continue
        row = asset_row(meta)
        with _CACHE_LOCK:
            _CACHE[key] = (mtime, row)
        rows.append(row)
    with _CACHE_LOCK:
        for key in [k for k in _CACHE if k.startswith(str(asset_dir)) and k not in seen]:
            del _CACHE[key]
    return rows


def build_states(builds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Latest build per source: state (not_built|building|built|failed) and build count."""
    out: dict[str, dict[str, Any]] = {}
    for build in sorted(builds, key=lambda item: str(item.get("created_at") or "")):
        asset = str(build.get("asset_id") or "")
        if not asset:
            continue
        status = str(build.get("status") or "")
        state = BUILD_STATE.get(status, "building" if status in {"queued", "running", "extracting", "segmenting", "enriching", "paused", "cancelling"} else "built" if status else "not_built")
        previous = out.get(asset, {"builds": 0})
        out[asset] = {"state": state, "builds": previous["builds"] + 1, "latest_build_id": build.get("build_id") or build.get("id")}
    return out


def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    q = str(filters.get("q") or "").strip().casefold()
    if q and not any(q in str(row.get(k) or "").casefold() for k in ("title", "filename", "document_author", "translator")):
        return False
    for key, field in (("provider", "provider"), ("media_kind", "media_kind"), ("build_status", "build_status"), ("work", "canonical_work_id"), ("relationship", "relationship_to_work"), ("role", "contribution_role"), ("original_language", "original_language")):
        wanted = filters.get(key)
        if wanted and str(row.get(field) or "") not in wanted:
            return False
    if filters.get("document_language") and not set(row["document_languages"]) & set(filters["document_language"]):
        return False
    if filters.get("capture_id") and not set(row["capture_ids"]) & set(filters["capture_id"]):
        return False
    author = str(filters.get("author") or "").strip().casefold()
    return not (author and author not in str(row.get("document_author") or "").casefold())


def _sort_key(sort: str):
    if sort == "added":
        return lambda row: str(row.get("created_at") or "")
    if sort == "provider":
        return lambda row: (row["provider"], row["title"].casefold())
    if sort == "language":
        return lambda row: (",".join(row["document_languages"]) or "~", row["title"].casefold())
    if sort == "author":
        return lambda row: (str(row.get("document_author") or "~").casefold(), row["title"].casefold())
    return lambda row: row["title"].casefold()


def list_sources(
    asset_dir: Path,
    *,
    builds: list[dict[str, Any]],
    links: dict[str, list[dict[str, Any]]],
    filters: dict[str, Any],
    sort: str = "added",
    descending: bool = True,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    states = build_states(builds)
    rows = []
    for base in _load_rows(asset_dir):
        row = {k: v for k, v in base.items() if not k.startswith("_")}
        source_links = links.get(row["source_document_id"], [])
        row["capture_ids"] = sorted({link["capture_id"] for link in source_links} | ({base["_capture_hint"]} if base.get("_capture_hint") else set()))
        state = states.get(row["source_document_id"], {"state": "not_built", "builds": 0, "latest_build_id": None})
        row["build_status"] = state["state"]
        row["build_count"] = state["builds"]
        row["latest_build_id"] = state["latest_build_id"]
        rows.append(row)
    facets = {
        "provider": _count(rows, lambda r: [r["provider"]]),
        "document_language": _count(rows, lambda r: r["document_languages"] or ["und"]),
        "original_language": _count(rows, lambda r: [r["original_language"]] if r.get("original_language") else []),
        "capture_id": _count(rows, lambda r: r["capture_ids"]),
        "build_status": _count(rows, lambda r: [r["build_status"]]),
        "relationship": _count(rows, lambda r: [r["relationship_to_work"]] if r.get("relationship_to_work") else []),
        "role": _count(rows, lambda r: [r["contribution_role"]] if r.get("contribution_role") else []),
        "media_kind": _count(rows, lambda r: [r["media_kind"]]),
    }
    matching = [row for row in rows if _matches(row, filters)]
    matching.sort(key=_sort_key(sort if sort in SORTS else "added"), reverse=descending)
    return {"items": matching[offset : offset + limit], "total": len(matching), "offset": offset, "limit": limit, "facets": facets, "all_total": len(rows)}


def _count(rows: list[dict[str, Any]], values) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        for value in values(row):
            out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items(), key=lambda item: -item[1]))
