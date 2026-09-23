# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic raster (scan) quality from embedded PDF images.

Pixelation is inferred from effective DPI: pixel size of the embedded image
versus the rectangle it occupies on the page (72 PDF points per inch). Native
vector/text pages with no image return None — they are not 'sharp scans'.
"""

from __future__ import annotations

from typing import Any

# Below ~150 DPI a full-page scan is too coarse for scholarly OCR; 72 DPI is
# typical of a screen-capture PDF and maps near the top of the noise scale.
_DPI_CLEAN = 250.0
_DPI_FLOOR = 50.0


def noise_from_effective_dpi(dpi: float) -> float:
    """Map effective DPI to 0–100 noise. Higher DPI is cleaner."""
    if dpi >= _DPI_CLEAN:
        return 0.0
    if dpi <= _DPI_FLOOR:
        return 95.0
    span = _DPI_CLEAN - _DPI_FLOOR
    return round(95.0 * (1.0 - (dpi - _DPI_FLOOR) / span), 1)


def assess_page_raster(page: Any) -> dict[str, Any] | None:
    """Inspect embedded images on one PyMuPDF page. Never raises into ingest."""
    try:
        images = page.get_images(full=True) or []
    except Exception:
        return None
    if not images:
        return None
    best_dpi = 0.0
    used = 0
    for item in images:
        try:
            xref = int(item[0])
            pix_w = int(item[2] or 0)
            pix_h = int(item[3] or 0)
        except (TypeError, ValueError, IndexError):
            continue
        if pix_w < 8 or pix_h < 8:
            continue
        try:
            rects = page.get_image_rects(xref) or []
        except Exception:
            rects = []
        if not rects:
            # Unknown placement: fall back to the page box so a full-page scan
            # still yields an effective DPI.
            rects = [page.rect]
        for rect in rects:
            width_in = float(rect.width or 0) / 72.0
            height_in = float(rect.height or 0) / 72.0
            if width_in < 0.1 or height_in < 0.1:
                continue
            dpi = min(pix_w / width_in, pix_h / height_in)
            best_dpi = max(best_dpi, dpi)
            used += 1
    if used == 0 or best_dpi <= 0:
        return None
    noise = noise_from_effective_dpi(best_dpi)
    return {
        "effective_dpi": round(best_dpi, 1),
        "noise": noise,
        "image_count": used,
        "method": "embedded_dpi",
    }
