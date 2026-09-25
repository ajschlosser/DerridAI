# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure record-quality assessment: source-quality gating and trash-record detection.

Deterministic checks that decide whether a record's source text is safe to hand to
a model for scholarly enrichment, and whether it is likely unusable at all. Moved
verbatim out of PdfCorpusBuildManager (extracted during the 0.70 decomposition); the stateful methods that
call these (_prepare_metadata_tasks, _run, regenerate_manifest, etc.) stay on the
manager.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .rag import _citation_strings
from .text_noise import DEFAULT_NOISE_THRESHOLD
from .text_noise import median_score as median_text_noise
from .text_noise import threshold_from_records as record_noise_threshold


def iso_now() -> str:
    return datetime.now(UTC).isoformat()



def _metadata_source_quality_gate(
    record: dict[str, Any], required_metadata_fields: list[str],
    stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
) -> bool:
    """Settle unsafe source records without asking a model to interpret corruption."""
    # Do not ask a model to interpret source text that deterministic extraction
    # quality checks have already identified as corrupted. Preserve any
    # deterministic classifications and route only the unresolved fields to
    # explicit human/source repair.
    blocking_source_issues = [
        item for item in (record.get("source_quality_issues") or [])
        if str(item.get("severity") or "blocking") == "blocking"
    ]
    if blocking_source_issues and record.get("text_review_status") != "human_corrected":
        field_status = record.setdefault("metadata_field_status", {})
        for field in required_metadata_fields:
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            if current.get("status") in {"deterministic", "human_confirmed"}:
                continue
            field_status[field] = {
                "status": "unresolved", "method": "source_quality_gate",
                "confidence": None, "reason_code": "source_quality",
                "reason": "Automatic enrichment was skipped because this record touches a source page with blocking extraction-quality findings.",
            }
        incomplete_fields = [field for field in required_metadata_fields if str((field_status.get(field) or {}).get("status") or "") in {"unresolved", "invalid"} or record.get(field) in (None, "", [])]
        record["metadata_incomplete_fields"] = incomplete_fields
        record["metadata_complete"] = not incomplete_fields
        record["metadata_stage_status"] = {"discourse": "skipped", "quotation": "skipped", "indexing": "skipped", "source_quality": "needs_review"}
        record["metadata_execution_ledger"] = {
            family: {"state": "skipped", "finished_at": iso_now(), "error": "Source quality gate"}
            for family in ("discourse", "quotation", "indexing")
        }
        if stage_callback:
            for family in ("discourse", "quotation", "indexing"):
                stage_callback(record, family, "skipped", "Source quality gate")
        record["metadata_needs_attention"] = True
        record["metadata_attention_reasons"] = ["Source extraction quality must be resolved before scholarly metadata enrichment."]
        inline, full = _citation_strings(record)
        record["inline_citation"] = inline; record["full_citation"] = full
        return True
    return False


def _record_extraction_quality_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect layout/glyph fragmentation that page-level corruption checks miss.

    PDF text layers sometimes emit one glyph per line/position. Those records may
    contain valid Unicode yet are still unusable as scholarly text. Route them to
    the Source problem queue instead of presenting them as ready for acceptance.
    """
    text = unicodedata.normalize("NFC", str(record.get("text") or ""))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 8:
        return []
    micro = sum(1 for line in lines if len(line) <= 2)
    punctuation_only = sum(1 for line in lines if line and all((not ch.isalnum()) for ch in line))
    alpha_chars = [ch for ch in text if ch.isalpha()]
    separated_alpha = sum(1 for line in lines if len(line) == 1 and line.isalpha())
    micro_ratio = micro / max(1, len(lines))
    separated_ratio = separated_alpha / max(1, len(alpha_chars))
    if micro_ratio >= 0.45 and (separated_alpha >= 5 or punctuation_only >= 5 or separated_ratio >= 0.12):
        pages = [int(v) for v in (record.get("pdf_pages") or []) if isinstance(v, int)]
        return [{
            "code": "fragmented_glyph_layout",
            "pages": sorted(set(pages)),
            "micro_line_ratio": round(micro_ratio, 3),
            "message": "Extracted text appears fragmented into individual glyphs or punctuation lines.",
        }]
    return []


def _trash_quality_report(records: list[dict[str, Any]], source_quality: dict[str, Any] | None = None) -> dict[str, Any]:
    """Measure records that are very likely unusable before semantic enrichment.

    This is deliberately deterministic and conservative. Strong extraction
    findings already live in ``source_quality_issues``; this ratio adds
    record-level signals for sparse, replacement-heavy, or glyph-fragmented
    text so a build can warn before spending model calls.
    """
    trash: list[dict[str, Any]] = []
    for record in records:
        text = unicodedata.normalize("NFC", str(record.get("text") or "")).strip()
        compact = "".join(ch for ch in text if not ch.isspace())
        alpha = sum(1 for ch in compact if ch.isalpha())
        replacement = compact.count("\ufffd")
        controls = sum(1 for ch in compact if unicodedata.category(ch) == "Cc")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        micro = sum(1 for line in lines if len(line) <= 2)
        fragmented = bool(_record_extraction_quality_issues(record))
        reasons: list[str] = []
        if len(compact) < 24:
            reasons.append("very_low_text_density")
        if replacement >= 2 or controls:
            reasons.append("corrupt_characters")
        if fragmented:
            reasons.append("fragmented_glyph_layout")
        if compact and alpha / max(1, len(compact)) < 0.25:
            reasons.append("low_alphabetic_density")
        if lines and micro / max(1, len(lines)) >= 0.65:
            reasons.append("micro_line_fragmentation")
        noise = record.get("text_noise") if isinstance(record.get("text_noise"), dict) else {}
        try:
            noise_score = float(noise.get("score"))
        except (TypeError, ValueError):
            noise_score = None
        threshold = float(noise.get("threshold") if noise.get("threshold") is not None else DEFAULT_NOISE_THRESHOLD)
        if noise_score is not None and noise_score >= threshold:
            reasons.append("high_text_noise")
        if reasons:
            trash.append({
                "record_id": str(record.get("record_id") or ""),
                "pages": list(record.get("pdf_pages") or []),
                "reasons": reasons,
                "characters": len(compact),
            })
    total = len(records)
    ratio = len(trash) / max(1, total)
    source_quality = source_quality or {}
    image_only_page_count = int(source_quality.get("image_only_page_count") or 0)
    source_page_count = int(source_quality.get("page_count") or 0)
    image_only_page_ratio = image_only_page_count / max(1, source_page_count)
    return {
        "record_count": total,
        "trash_record_count": len(trash),
        "trash_ratio": round(ratio, 4),
        "threshold": 0.10,
        "unusable_page_count": image_only_page_count,
        "unusable_page_ratio": round(image_only_page_ratio, 4),
        "exceeds_threshold": bool((total and ratio > 0.10) or image_only_page_ratio > 0.10),
        "deterministic": True,
        "records": trash[:500],
        "median_noise": median_text_noise(records),
        "noise_unusable_threshold": record_noise_threshold(records),
    }

