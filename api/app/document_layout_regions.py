# Copyright 2026 Aaron John Schlosser, PhD.
"""Reviewer-owned layout regions for PDFs whose text is not one column.

A region is a rectangle in normalized page coordinates, a role, a thread, and a
scope (every page, odd, even, a range, or one page). Extracted blocks are
assigned by where their center falls. A smaller region wins over a full-page
main region, and a page-only region wins over a repeating one.

That is the scalable alternative to drawing a polygon around every passage.
Columns, margins, infoboxes, and inset quotations repeat; one rectangle covers
the book. A page that wraps around a figure gets its own page-only rectangle.
Polygons are rejected: they do not stay aligned across hundreds of pages, and
record boundaries are not something a reviewer should trace by hand.

Separate-flow regions are lifted out of the main reading sequence and appended
in page order. The main argument stays contiguous. Each block keeps its page.
"""

from __future__ import annotations

import re
from typing import Any

MAX_LAYOUT_REGIONS = 24
MIN_SPAN = 0.02
ROLES = (
    "main",
    "margin_parallel",
    "margin_apparatus",
    "infobox",
    "block_quote",
    "running_matter",
)
THREADS = ("thread_a", "thread_b", "thread_c", "thread_d")
SCOPES = ("all", "odd", "even", "range", "page")
FLOWS = ("with_main", "separate")
DEFAULT_FLOW = {
    "main": "with_main",
    "block_quote": "with_main",
    "margin_parallel": "separate",
    "margin_apparatus": "separate",
    "infobox": "separate",
    "running_matter": "separate",
}
# Closed region_type values. Parallel text and a separated quotation stay
# primary text. Apparatus, boxes, and running matter do not.
SEPARATE_REGION_TYPE = {
    "margin_parallel": "main_text",
    "margin_apparatus": "notes",
    "infobox": "paratext",
    "running_matter": "paratext",
    "block_quote": "main_text",
}
KEEP_PAGE_REGION_ROLES = {"margin_parallel", "block_quote"}
_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_LANGUAGE = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
_ALLOWED = {
    "id",
    "role",
    "thread",
    "language",
    "flow",
    "x0",
    "y0",
    "x1",
    "y1",
    "applies_to",
    "page_start",
    "page_end",
    "page",
    "label",
}


def _unit(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number between 0 and 1") from exc
    if number < 0 or number > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return round(number, 4)


def _optional_page(value: Any, name: str, page_count: int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a PDF page number") from exc
    if number < 1:
        raise ValueError(f"{name} must be a PDF page number")
    if page_count and number > page_count:
        raise ValueError(f"{name} must be within the PDF page range")
    return number


def normalize_regions(raw: Any, page_count: int | None = None) -> list[dict[str, Any]]:
    """Return a clean region list or raise ValueError."""
    if raw in (None, ""):
        return []
    if not isinstance(raw, list):
        raise ValueError("layout_regions must be a list")
    if len(raw) > MAX_LAYOUT_REGIONS:
        raise ValueError(f"A document can have at most {MAX_LAYOUT_REGIONS} layout regions")
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each layout region must be an object")
        unknown = set(item) - _ALLOWED
        if unknown:
            if "polygon" in unknown:
                raise ValueError(
                    "Layout regions are rectangles. Apply one rectangle to many pages, "
                    "or add a page-only rectangle when a single page is irregular."
                )
            raise ValueError("Unsupported layout region field")
        region_id = str(item.get("id") or "").strip()
        if not _ID.fullmatch(region_id):
            raise ValueError("Each layout region needs a stable id")
        if region_id in seen:
            raise ValueError("Layout region ids must be unique")
        seen.add(region_id)
        role = str(item.get("role") or "")
        if role not in ROLES:
            raise ValueError("Unsupported layout region role")
        thread = str(item.get("thread") or "thread_a")
        if thread not in THREADS:
            raise ValueError("Unsupported layout region thread")
        language = str(item.get("language") or "").strip()
        if language and not _LANGUAGE.fullmatch(language):
            raise ValueError("Region language must be a short code such as en_us or fr_fr")
        flow = str(item.get("flow") or DEFAULT_FLOW[role])
        if flow not in FLOWS:
            raise ValueError("Layout region flow must be with_main or separate")
        if role == "main":
            flow = "with_main"
        x0, y0 = _unit(item.get("x0"), "x0"), _unit(item.get("y0"), "y0")
        x1, y1 = _unit(item.get("x1"), "x1"), _unit(item.get("y1"), "y1")
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        if x1 - x0 < MIN_SPAN or y1 - y0 < MIN_SPAN:
            raise ValueError("A layout region is too small to capture text")
        scope = str(item.get("applies_to") or "all")
        if scope not in SCOPES:
            raise ValueError("Unsupported layout region scope")
        page = _optional_page(item.get("page"), "page", page_count)
        page_start = _optional_page(item.get("page_start"), "page_start", page_count)
        page_end = _optional_page(item.get("page_end"), "page_end", page_count)
        if scope == "page" and page is None:
            raise ValueError("A page-only region needs a PDF page")
        if scope == "range":
            if page_start is None or page_end is None:
                raise ValueError("A page-range region needs a start and end page")
            if page_end < page_start:
                raise ValueError("A page-range region cannot end before it starts")
        label = str(item.get("label") or "").strip()
        if len(label) > 80:
            raise ValueError("A layout region label must be 80 characters or fewer")
        cleaned.append({
            "id": region_id,
            "role": role,
            "thread": thread,
            "language": language or None,
            "flow": flow,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "applies_to": scope,
            "page_start": page_start if scope == "range" else None,
            "page_end": page_end if scope == "range" else None,
            "page": page if scope == "page" else None,
            "label": label or None,
        })
    return cleaned


def _applies(region: dict[str, Any], page: int) -> bool:
    scope = region.get("applies_to") or "all"
    if scope == "all":
        return True
    if scope == "odd":
        return page % 2 == 1
    if scope == "even":
        return page % 2 == 0
    if scope == "page":
        return int(region.get("page") or 0) == page
    if scope == "range":
        start = int(region.get("page_start") or 0)
        end = int(region.get("page_end") or 0)
        return start <= page <= end
    return False


def _specificity(region: dict[str, Any]) -> int:
    return {"page": 3, "range": 2, "odd": 1, "even": 1, "all": 0}.get(str(region.get("applies_to") or "all"), 0)


def _area(region: dict[str, Any]) -> float:
    return max(0.0, float(region["x1"]) - float(region["x0"])) * max(0.0, float(region["y1"]) - float(region["y0"]))


def _contains(region: dict[str, Any], x: float, y: float) -> bool:
    return float(region["x0"]) <= x <= float(region["x1"]) and float(region["y0"]) <= y <= float(region["y1"])


def match_region(
    regions: list[dict[str, Any]],
    page: int,
    bbox: Any,
    width: float,
    height: float,
) -> dict[str, Any] | None:
    """Return the region that owns a block center, if any."""
    if not regions or width <= 0 or height <= 0 or not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
        return None
    try:
        x = (float(bbox[0]) + float(bbox[2])) / 2 / width
        y = (float(bbox[1]) + float(bbox[3])) / 2 / height
    except (TypeError, ValueError):
        return None
    candidates = [
        (index, region)
        for index, region in enumerate(regions)
        if _applies(region, page) and _contains(region, x, y)
    ]
    if not candidates:
        return None
    # Page-only beats a repeating template. Within one specificity, the smaller
    # rectangle wins so a margin or box beats the full-page main region.
    # A later region wins a remaining tie.
    _index, region = min(candidates, key=lambda item: (-_specificity(item[1]), _area(item[1]), -item[0]))
    return region


def apply_layout_regions(
    blocks: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    regions: list[dict[str, Any]],
) -> None:
    """Tag blocks from reviewer regions. Separate regions take their own thread."""
    page_by_number = {int(page.get("pdf_page") or 0): page for page in pages}
    threads_by_page: dict[int, set[str]] = {}
    for block in blocks:
        page_no = int(block.get("page") or 0)
        page = page_by_number.get(page_no) or {}
        for key in ("layout_region_id", "layout_region_role", "layout_flow"):
            block.pop(key, None)
        region = match_region(
            regions,
            page_no,
            block.get("bbox"),
            float(page.get("width") or 0),
            float(page.get("height") or 0),
        )
        if region is not None:
            block["layout_region_id"] = region["id"]
            block["layout_region_role"] = region["role"]
            block["layout_flow"] = region["flow"]
            if region["flow"] == "separate":
                block["document_thread"] = region["thread"]
                if region.get("language"):
                    block["thread_language"] = region["language"]
                else:
                    block.pop("thread_language", None)
                mapped = SEPARATE_REGION_TYPE.get(str(region["role"]))
                page_region = str(block.get("deterministic_region_type") or "")
                if mapped and not (
                    region["role"] in KEEP_PAGE_REGION_ROLES and page_region not in {"", "main_text", "unknown"}
                ):
                    block["deterministic_region_type"] = mapped
        threads_by_page.setdefault(page_no, set()).add(str(block.get("document_thread") or "thread_a"))
    for page in pages:
        found = threads_by_page.get(int(page.get("pdf_page") or 0))
        if found:
            page["thread_ids"] = sorted(found)


def _sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, float, float, int]:
    index, block = item
    bbox = block.get("bbox") or [0, 0, 0, 0]
    try:
        y = (float(bbox[1]) + float(bbox[3])) / 2 if len(bbox) >= 4 else 0.0
        x = (float(bbox[0]) + float(bbox[2])) / 2 if len(bbox) >= 4 else 0.0
    except (TypeError, ValueError):
        y, x = 0.0, 0.0
    return (int(block.get("page") or 0), y, x, index)


def reading_sequence(blocks: list[dict[str, Any]], region_ids: list[str]) -> list[dict[str, Any]]:
    """Keep the main text in extraction order and append each separate region.

    Every block is returned once. Separate regions are ordered by page, then
    by position on the page, so a margin commentary is its own sequence instead
    of breaking the main argument on every sheet.
    """
    buckets: dict[str, list[tuple[int, dict[str, Any]]]] = {region_id: [] for region_id in region_ids}
    extras: list[tuple[int, dict[str, Any]]] = []
    main: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        region_id = str(block.get("layout_region_id") or "")
        if block.get("layout_flow") == "separate" and region_id:
            if region_id in buckets:
                buckets[region_id].append((index, block))
            else:
                extras.append((index, block))
        else:
            main.append(block)
    ordered = list(main)
    for region_id in region_ids:
        ordered.extend(block for _index, block in sorted(buckets[region_id], key=_sort_key))
    ordered.extend(block for _index, block in sorted(extras, key=_sort_key))
    return ordered
