# Copyright 2026 Aaron John Schlosser, PhD.
"""PDF-to-SourceDocument extraction for Corpus Builder.

This module owns the document boundary: native PDF text, OCR fallback,
SourceUnit construction, page labels, image-only diagnostics, and extraction
metadata. Corpus Builder consumes the resulting SourceDocument projection and
does not need to know how PyMuPDF assembled it.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import fitz

from .main_text_start import infer_main_text_start
from .raster_quality import assess_page_raster


def safe_filename(value: str) -> str:
    """Return a stable, filesystem-safe display filename."""
    name = Path(str(value or "source.pdf")).name
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name)[:240] or "source.pdf"


def normalize_text(value: Any) -> str:
    """Normalize extracted text without changing scholarly content."""
    text = unicodedata.normalize("NFC", str(value or "").replace("\u00ad", ""))
    return re.sub(r"\s+", " ", text).strip()


def block_text(block: dict[str, Any]) -> str:
    """Flatten one PyMuPDF text block while preserving line boundaries."""
    if "lines" in block:
        chunks: list[str] = []
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            text = unicodedata.normalize("NFC", "".join(str(span.get("text") or "") for span in spans))
            if text.strip():
                chunks.append(text.rstrip())
        return unicodedata.normalize("NFC", "\n".join(chunks).strip())
    return unicodedata.normalize("NFC", str(block.get("text") or "").strip())


def page_source_units(
    page: fitz.Page, *, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu",
) -> tuple[list[dict[str, Any]], str, str | None, int]:
    """Extract SourceUnits from one page and report the page extraction mode."""
    source = "native"
    warning: str | None = None
    data = page.get_text("dict", sort=True)
    raw_units = data.get("blocks") or []
    native_chars = sum(len(block_text(unit)) for unit in raw_units if unit.get("type") == 0)
    should_ocr = ocr_mode == "always" or (ocr_mode == "auto" and native_chars < 24)
    if should_ocr:
        try:
            textpage = page.get_textpage_ocr(language=ocr_languages, dpi=200, full=True)
            data = page.get_text("dict", textpage=textpage, sort=True)
            raw_units = data.get("blocks") or []
            source = "ocr"
        except Exception as exc:
            warning = f"OCR unavailable for page {page.number + 1}: {exc}"
            if ocr_mode == "always" and native_chars < 1:
                source = "ocr_failed"

    sizes: list[float] = []
    for unit in raw_units:
        for line in unit.get("lines") or []:
            for span in line.get("spans") or []:
                if str(span.get("text") or "").strip():
                    try:
                        sizes.append(float(span.get("size") or 0))
                    except (TypeError, ValueError):
                        pass
    median_size = sorted(sizes)[len(sizes) // 2] if sizes else 0.0
    height = float(page.rect.height or 1)
    width = float(page.rect.width or 1)
    units: list[dict[str, Any]] = []
    text_index = 0
    for raw in raw_units:
        if raw.get("type") != 0:
            continue
        value = block_text(raw)
        if not value.strip():
            continue
        text_index += 1
        bbox = [round(float(x), 2) for x in (raw.get("bbox") or [0, 0, 0, 0])]
        span_sizes: list[float] = []
        for line in raw.get("lines") or []:
            for span in line.get("spans") or []:
                if str(span.get("text") or "").strip():
                    try:
                        span_sizes.append(float(span.get("size") or 0))
                    except (TypeError, ValueError):
                        pass
        max_size = max(span_sizes) if span_sizes else median_size
        top, bottom = (bbox[1] if len(bbox) > 1 else 0), (bbox[3] if len(bbox) > 3 else 0)
        kind = "paragraph"
        stripped = value.lstrip()
        if median_size and max_size >= median_size * 1.35 and len(value) < 240:
            kind = "heading"
        elif top < height * 0.055 or bottom > height * 0.955:
            kind = "header_footer"
        elif median_size and bottom > height * 0.72 and max_size <= median_size * 0.82:
            kind = "footnote"
        elif re.match(r"^(?:[•▪◦‣–—-]|\d+[.)])\s+", stripped):
            kind = "list_item"
        elif len(bbox) >= 4 and bbox[0] > width * 0.13 and bbox[2] < width * 0.87 and len(value) > 80:
            kind = "block_quote"
        units.append({
            "block_id": f"p{page.number + 1:05d}-b{text_index:04d}",
            "page": page.number + 1,
            "bbox": bbox,
            "type": kind,
            "text": value,
            "extraction_method": source,
            "confidence": 1.0 if source == "native" else 0.88 if source == "ocr" else 0.35,
        })
    image_count = sum(1 for unit in raw_units if unit.get("type") == 1)
    return units, source, warning, image_count


def extract_source_document(
    data: bytes, *, filename: str, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu",
) -> dict[str, Any]:
    """Extract a stable SourceDocument projection from PDF bytes."""
    if not data:
        raise ValueError("The uploaded PDF was empty.")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF: {exc}") from exc
    try:
        metadata = {key: value for key, value in (doc.metadata or {}).items() if value}
        pages: list[dict[str, Any]] = []
        units: list[dict[str, Any]] = []
        warnings: list[str] = []
        ocr_pages = 0
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            try:
                pdf_label = page.get_label() or None
            except Exception as exc:
                pdf_label = None
                warnings.append(
                    f"PDF page-label lookup failed for physical page {page_index + 1}; "
                    f"continuing with visible-folio detection ({exc})."
                )
            page_units, source, warning, image_count = page_source_units(
                page, ocr_mode=ocr_mode, ocr_languages=ocr_languages,
            )
            visible_page_labels = [
                normalize_text(unit.get("text") or "")
                for unit in page_units
                if unit.get("type") == "header_footer"
                and re.fullmatch(r"(?:[ivxlcdm]+|\d+)", normalize_text(unit.get("text") or ""), re.I)
            ]
            printed_label = visible_page_labels[-1] if visible_page_labels else pdf_label
            label_source = "visible_folio" if visible_page_labels else "pdf_label" if pdf_label else None
            for unit in page_units:
                unit["printed_page_label"] = printed_label
                unit["printed_page_label_source"] = label_source
            if source == "ocr":
                ocr_pages += 1
            if warning:
                warnings.append(warning)
            page_meta = {
                "pdf_page": page_index + 1,
                "printed_page_label": printed_label,
                "printed_page_label_source": label_source,
                "width": round(float(page.rect.width), 2),
                "height": round(float(page.rect.height), 2),
                "block_ids": [unit["block_id"] for unit in page_units],
                "extraction_method": source,
                "image_count": image_count,
            }
            raster = assess_page_raster(page)
            if raster:
                page_meta["raster"] = raster
            pages.append(page_meta)
            units.extend(page_units)

        offsets: Counter[int] = Counter()
        for page_info in pages:
            if page_info.get("printed_page_label_source") != "visible_folio":
                continue
            label = str(page_info.get("printed_page_label") or "").strip()
            if label.isdigit():
                offsets[int(label) - int(page_info["pdf_page"])] += 1
        inferred_offset = None
        if offsets:
            candidate_offset, count = offsets.most_common(1)[0]
            if count >= 2:
                inferred_offset = int(candidate_offset)
        if inferred_offset is not None:
            anchor_pages = [
                int(item["pdf_page"]) for item in pages
                if item.get("printed_page_label_source") == "visible_folio"
                and str(item.get("printed_page_label") or "").isdigit()
            ]
            for page_info in pages:
                page_number = int(page_info["pdf_page"])
                if page_info.get("printed_page_label_source") == "visible_folio" or page_number < min(anchor_pages):
                    continue
                inferred = page_number + inferred_offset
                if inferred < 1:
                    continue
                page_info["printed_page_label"] = str(inferred)
                page_info["printed_page_label_source"] = "inferred_from_folios"
                for unit in units:
                    if int(unit.get("page") or 0) == page_number:
                        unit["printed_page_label"] = str(inferred)
                        unit["printed_page_label_source"] = "inferred_from_folios"

        header_pages: dict[str, set[int]] = {}
        for unit in units:
            if unit.get("type") != "header_footer":
                continue
            normalized = normalize_text(unit.get("text") or "").casefold()
            if normalized:
                header_pages.setdefault(normalized, set()).add(int(unit.get("page") or 0))
        repeat_threshold = max(3, int(max(1, doc.page_count) * 0.20))
        excluded_count = 0
        for unit in units:
            if unit.get("type") != "header_footer":
                continue
            normalized = normalize_text(unit.get("text") or "").casefold()
            is_page_number = bool(re.fullmatch(r"(?:[ivxlcdm]+|\d+)", normalized, re.I))
            if is_page_number or len(header_pages.get(normalized, set())) >= repeat_threshold:
                unit["excluded_reason"] = "page_number" if is_page_number else "repeated_header_footer"
                excluded_count += 1
        try:
            outline = [(int(page), str(title)) for _level, title, page in doc.get_toc(simple=True)]
        except Exception:  # noqa: BLE001 - a broken outline removes one clue
            outline = []
        return {
            "main_text_start_inference": infer_main_text_start(units, pages, outline),
            "outline": [{"page": page, "title": title} for page, title in outline[:400]],
            "filename": safe_filename(filename),
            "page_count": doc.page_count,
            "metadata": metadata,
            "pages": pages,
            "blocks": units,
            "block_count": len(units),
            "included_block_count": len(units) - excluded_count,
            "excluded_block_count": excluded_count,
            "ocr_pages": ocr_pages,
            "warnings": warnings,
            "extractor": "pymupdf-layout-v2",
        }
    finally:
        doc.close()
