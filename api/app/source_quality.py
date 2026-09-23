# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic source-extraction quality, scored when a PDF is ingested.

Page-level corruption, raster DPI, and word-shape noise belong to the SourceDocument,
not the later corpus build. An optional LLM second-read still runs only at kickoff.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any

from .text_noise import (
    DEFAULT_NOISE_THRESHOLD,
    fuse_record_noise,
    score_text_noise,
)


def page_source_quality_report(
    blocks: list[dict[str, Any]], pages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Sparse pages warn; replacement/control characters block enrichment."""
    by_page: dict[int, list[str]] = {}
    methods: dict[int, Counter[str]] = {}
    page_info = {int(item.get("pdf_page") or 0): item for item in (pages or []) if int(item.get("pdf_page") or 0) > 0}
    for block in blocks:
        try:
            page = int(block.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page < 1:
            continue
        text = unicodedata.normalize("NFC", str(block.get("text") or ""))
        by_page.setdefault(page, []).append(text)
        methods.setdefault(page, Counter())[str(block.get("extraction_method") or "unknown")] += 1
    issues: list[dict[str, Any]] = []
    blocking_pages: list[int] = []
    warning_pages: list[int] = []
    all_pages = sorted(set(by_page) | set(page_info))
    for page in all_pages:
        parts = by_page.get(page, [])
        text = "\n".join(parts)
        chars = len(text)
        replacement = text.count("\ufffd")
        controls = sum(1 for ch in text if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t")
        printable = sum(1 for ch in text if not ch.isspace())
        replacement_ratio = replacement / max(1, printable)
        severity = "ok"
        codes: list[str] = []
        if replacement >= 2 and replacement_ratio >= 0.005:
            severity = "blocking"
            codes.append("replacement_characters")
        if controls:
            severity = "blocking"
            codes.append("control_characters")
        if chars < 20:
            if severity != "blocking":
                severity = "warning"
            codes.append("very_low_text_density")
        if not parts and int((page_info.get(page) or {}).get("image_count") or 0) > 0:
            if severity != "blocking":
                severity = "warning"
            codes.append("image_only_page")
        if codes:
            issue = {
                "page": page, "severity": severity, "codes": codes,
                "characters": chars, "replacement_characters": replacement,
                "control_characters": controls, "extraction_methods": dict(methods.get(page) or {}),
            }
            issues.append(issue)
            (blocking_pages if severity == "blocking" else warning_pages).append(page)
    image_only_pages = {
        int(issue["page"])
        for issue in issues
        if "image_only_page" in (issue.get("codes") or [])
    }
    return {
        "valid_for_enrichment": not blocking_pages,
        "page_count": len(all_pages),
        "blocking_page_count": len(blocking_pages),
        "warning_page_count": len(warning_pages),
        "image_only_page_count": len(image_only_pages),
        "blocking_pages": blocking_pages,
        "warning_pages": warning_pages,
        "issues": issues,
    }


def assess_extracted_source(
    blocks: list[dict[str, Any]],
    pages: list[dict[str, Any]] | None = None,
    *,
    threshold: float = DEFAULT_NOISE_THRESHOLD,
) -> dict[str, Any]:
    """Score every extracted page as soon as the PDF is loaded."""
    pages = list(pages or [])
    source_quality = page_source_quality_report(blocks, pages)
    by_page: dict[int, list[str]] = {}
    for block in blocks:
        try:
            page = int(block.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page < 1:
            continue
        by_page.setdefault(page, []).append(str(block.get("text") or ""))
    page_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    unusable = 0
    page_ids = sorted({int(item.get("pdf_page") or 0) for item in pages if int(item.get("pdf_page") or 0) > 0} | set(by_page))
    page_meta = {int(item.get("pdf_page") or 0): item for item in pages if int(item.get("pdf_page") or 0) > 0}
    blocking = set(int(value) for value in (source_quality.get("blocking_pages") or []))
    for page in page_ids:
        text = "\n".join(by_page.get(page, []))
        raster = None
        info = page_meta.get(page) or {}
        raster_info = info.get("raster") if isinstance(info.get("raster"), dict) else None
        if raster_info and raster_info.get("noise") is not None:
            try:
                raster = float(raster_info.get("noise"))
            except (TypeError, ValueError):
                raster = None
        fused = fuse_record_noise(
            score_text_noise(text),
            raster,
            threshold=threshold,
        )
        if page in blocking:
            fused["score"] = max(float(fused.get("score") or 0), 90.0)
            fused["unusable"] = True
            reasons = list(fused.get("reasons") or [])
            if "corrupt_characters" not in reasons:
                reasons.append("corrupt_characters")
            fused["reasons"] = reasons
        if fused.get("unusable"):
            unusable += 1
        scores.append(float(fused.get("score") or 0))
        page_rows.append({
            "page": page,
            "score": fused.get("score"),
            "unusable": bool(fused.get("unusable")),
            "reasons": fused.get("reasons") or [],
            "effective_dpi": (raster_info or {}).get("effective_dpi") if raster_info else None,
        })
    total = len(page_ids)
    ratio = unusable / max(1, total)
    scores.sort()
    mid = len(scores) // 2
    if not scores:
        median = None
    elif len(scores) % 2:
        median = round(scores[mid], 1)
    else:
        median = round((scores[mid - 1] + scores[mid]) / 2, 1)
    image_only_ratio = int(source_quality.get("image_only_page_count") or 0) / max(1, int(source_quality.get("page_count") or total or 1))
    exceeds = bool((total and ratio > 0.10) or image_only_ratio > 0.10 or source_quality.get("blocking_page_count"))
    return {
        "source_quality": source_quality,
        "extraction_noise": {
            "page_count": total,
            "unusable_page_count": unusable,
            "unusable_page_ratio": round(ratio, 4),
            "median_noise": median,
            "threshold": float(threshold),
            "exceeds_threshold": exceeds,
            "deterministic": True,
            "pages": page_rows[:500],
        },
    }
