# Copyright 2026 Aaron John Schlosser, PhD.
"""Bound untrusted source parsing before invoking format-specific extractors."""

from __future__ import annotations

import io
import platform
import re
import subprocess
import warnings
import zipfile
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from xml.etree import ElementTree as ET

MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def check_size(data: bytes, maximum: int = MAX_SOURCE_BYTES) -> None:
    if not data or len(data) > maximum:
        raise ValueError("Source is empty or exceeds the ingestion size limit.")


def tool_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unavailable"


@lru_cache(maxsize=4)
def executable_version(name: str) -> str:
    """Query only fixed extractor executables, never commands from document bytes."""
    if name not in {"tesseract", "ffprobe"}:
        raise ValueError("Unknown extraction tool.")
    try:
        result = subprocess.run(  # noqa: S603 - fixed executable allowlist
            [name, "-version" if name == "ffprobe" else "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unavailable"


def extraction_provenance(extractor: str) -> dict:
    from .config import APP_VERSION

    return {
        "contract": "source-extraction-v2",
        "extractor": extractor,
        "app_version": APP_VERSION,
        "python": platform.python_version(),
        "tools": {
            name: tool_version(name)
            for name in ("PyMuPDF", "Pillow", "httpx", "whisperx")
        },
    }


def safe_xml(data: bytes) -> ET.Element:
    if (
        len(data) > MAX_XML_BYTES
        or b"<!DOCTYPE" in data.upper()
        or b"<!ENTITY" in data.upper()
        or b"\x00" in data
    ):
        raise ValueError("Unsupported or oversized document XML.")
    try:
        return ET.fromstring(data)  # noqa: S314 - byte limit and DTD/entity rejection precede parsing
    except ET.ParseError as exc:
        raise ValueError("Malformed document XML.") from exc


def validate_docx(package: zipfile.ZipFile) -> None:
    entries = package.infolist()
    if (
        len(entries) > 2048
        or sum(item.file_size for item in entries) > MAX_ARCHIVE_BYTES
    ):
        raise ValueError("Word archive exceeds decompression limits.")
    names = [item.filename for item in entries]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate Word archive entries.")
    for item in entries:
        name = item.filename.lower()
        if item.flag_bits & 1 or item.compress_type not in {
            zipfile.ZIP_STORED,
            zipfile.ZIP_DEFLATED,
        }:
            raise ValueError("Unsupported Word archive compression or encryption.")
        if (
            item.file_size > MAX_XML_BYTES
            or item.file_size > max(1, item.compress_size) * 200
        ):
            raise ValueError("Word archive exceeds decompression limits.")
        if any(part in name for part in ("vbaproject", "embeddings/", "activex/")):
            raise ValueError("Embedded active content is unsupported.")
        if name.endswith((".xml", ".rels")):
            root = safe_xml(package.read(item))
            for node in root.iter():
                local = node.tag.rsplit("}", 1)[-1]
                if local in {
                    "object",
                    "oleObject",
                    "altChunk",
                    "fldSimple",
                    "instrText",
                }:
                    raise ValueError("Embedded active content is unsupported.")
                if (
                    local == "Relationship"
                    and node.get("TargetMode", "").lower() == "external"
                ):
                    # Ordinary hyperlinks are inert; linked templates and OLE are not.
                    if not node.get("Type", "").endswith("/hyperlink"):
                        raise ValueError("External document content is unsupported.")


def validate_rtf(data: bytes) -> None:
    check_size(data, MAX_XML_BYTES)
    if not data.startswith(b"{\\rtf"):
        raise ValueError("Malformed RTF header.")
    depth = 0
    for token in re.finditer(rb"\\(?:[a-zA-Z]+-?\d* ?|[^a-zA-Z])|[{}]", data):
        value = token.group()
        if value == b"{":
            depth += 1
        elif value == b"}":
            depth -= 1
        elif re.match(
            rb"\\(?:object|objdata|field|filetbl|datastore|pict|bin)(?:\d|\s|$)",
            value,
            re.I,
        ):
            raise ValueError("Embedded RTF content is unsupported.")
        if depth < 0 or depth > 128:
            raise ValueError("RTF nesting exceeds safe limits.")
    if depth or not data.rstrip().endswith(b"}"):
        raise ValueError("Malformed RTF groups.")


def validate_image(data: bytes) -> None:
    from PIL import Image

    check_size(data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise ValueError("Unsupported image format; use PNG or JPEG.")
                if (
                    image.width * image.height > MAX_IMAGE_PIXELS
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError("Image exceeds pixel or frame limits.")
                image.verify()
    except Exception as exc:
        raise ValueError("Malformed, unsupported, or oversized image.") from exc
