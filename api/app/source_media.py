# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus source detection and the public ingest API.

Text, audio, and Project Gutenberg implementations live in sibling modules.
This module keeps the names callers already import.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .source_audio import extract_audio, spans_from_transcript
from .source_gutenberg import (
    fetch_source_url,
    load_gutenberg_etext,
    search_project_gutenberg,
    search_wikisource,
)
from .source_kinds import AUDIO_SUFFIXES, IMAGE_SUFFIXES, TEXT_SUFFIXES
from .source_text import (
    _looks_like_text,
    apply_deterministic_ingest_metadata,
    decode_plain_text,
    document_from_text,
    docx_to_text,
    html_to_text,
    infer_initial_metadata,
    ole_doc_to_text,
    png_text_metadata,
    prepare_text,
    prose_to_blocks,
    rtf_to_text,
)

__all__ = [
    "AUDIO_SUFFIXES",
    "IMAGE_SUFFIXES",
    "TEXT_SUFFIXES",
    "apply_deterministic_ingest_metadata",
    "clamp_illegibility",
    "content_suffix_for",
    "decode_plain_text",
    "detect_media_kind",
    "document_from_text",
    "extract_non_pdf",
    "fetch_source_url",
    "html_to_text",
    "infer_initial_metadata",
    "load_gutenberg_etext",
    "media_type_for",
    "native_text_ocr_threshold",
    "png_text_metadata",
    "prepare_text",
    "prose_to_blocks",
    "search_project_gutenberg",
    "search_wikisource",
    "spans_from_transcript",
]


def clamp_illegibility(value: Any) -> float:
    """Source illegibility is a 0–100 reviewer setting. 100 forces OCR."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if number != number or number in {float("inf"), float("-inf")}:
        return 0.0
    return max(0.0, min(100.0, number))


def native_text_ocr_threshold(source_illegibility: Any) -> int:
    """How many native characters a page may contain before OCR is skipped.

    Zero preserves the historical PDF behavior (OCR below 24 characters).
    One hundred treats the source as illegible and always OCRs.
    """
    level = clamp_illegibility(source_illegibility) / 100.0
    if level >= 0.999:
        return 10**9
    return int(round(24 + level * 5000))


def detect_media_kind(filename: str, data: bytes, content_type: str = "") -> str:
    name = str(filename or "").lower()
    suffix = Path(name).suffix
    head = data[:16]
    kind = (content_type or "").split(";", 1)[0].strip().lower()
    if name.endswith(".pdf") or head.startswith(b"%PDF") or kind == "application/pdf":
        return "pdf"
    if name.endswith(".docx") or kind == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    if name.endswith(".rtf") or data[:5] == b"{\\rtf" or kind == "application/rtf":
        return "rtf"
    if name.endswith(".doc") or head.startswith(b"\xd0\xcf\x11\xe0") or kind == "application/msword":
        return "doc"
    if suffix in IMAGE_SUFFIXES or head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8") or kind.startswith("image/"):
        return "image"
    if suffix in AUDIO_SUFFIXES or kind.startswith("audio/") or kind.startswith("video/"):
        return "audio"
    if kind == "text/html" or suffix in {".html", ".htm"}:
        return "html"
    if suffix in TEXT_SUFFIXES or kind.startswith("text/"):
        return "text"
    if not suffix and _looks_like_text(data):
        return "text"
    raise ValueError("Unsupported source format.")


def content_suffix_for(kind: str, filename: str) -> str:
    suffix = Path(str(filename or "")).suffix.lower()
    if kind == "pdf":
        return ".pdf"
    if kind == "image" and suffix in IMAGE_SUFFIXES:
        return suffix
    if kind == "audio" and suffix in AUDIO_SUFFIXES:
        return suffix
    return {
        "docx": ".docx", "doc": ".doc", "rtf": ".rtf", "html": ".html",
        "text": ".txt", "gutenberg": ".txt", "url": ".html",
    }.get(kind, suffix or ".bin")


def media_type_for(kind: str, filename: str) -> str:
    suffix = content_suffix_for(kind, filename)
    return {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".rtf": "application/rtf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
        ".mp4": "video/mp4",
    }.get(suffix, "application/octet-stream")


def extract_non_pdf(
    data: bytes,
    *,
    filename: str,
    kind: str,
    catalog: dict[str, Any] | None = None,
    detect_page_numbers: bool = True,
) -> dict[str, Any]:
    from .source_safety import check_size

    check_size(data)
    if kind not in {"audio", "docx", "doc", "rtf", "html", "image", "text", "gutenberg", "url"}:
        raise ValueError("Unsupported source format.")
    if kind == "audio":
        return extract_audio(data, filename=filename, catalog=catalog)
    if kind == "docx":
        text, embedded = docx_to_text(data)
        method = "docx"
    elif kind == "doc":
        text, embedded = ole_doc_to_text(data)
        method = "doc"
    elif kind == "rtf":
        text, embedded = rtf_to_text(data)
        method = "rtf"
    elif kind == "html":
        text, embedded = html_to_text(data.decode("utf-8", errors="replace"))
        method = "html"
    elif kind == "image":
        raise ValueError("Images are extracted through the PDF OCR path.")
    else:
        text, embedded = decode_plain_text(data), {}
        method = "text"
        kind = "text" if kind not in {"gutenberg", "url"} else kind
    indexable, metadata_text = prepare_text(text)
    if not indexable.strip():
        raise ValueError("The source did not contain extractable text.")
    return document_from_text(
        indexable,
        filename=filename,
        extraction_method=method,
        embedded=embedded,
        media_kind=kind if kind != "text" else "text",
        metadata_text=metadata_text,
        catalog=catalog,
        detect_pages=detect_page_numbers,
    )
