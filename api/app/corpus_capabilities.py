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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Dependency-light runtime diagnostics for the native Corpus Builder CLI.

The doctor surface is descriptive, not an installer. It never downloads models,
modifies provider configuration, or probes a network service unless the caller
explicitly asks for that separately. Keeping this module on the standard library
plus the existing pipeline contract lets a compiled CLI explain missing optional
capabilities even when those optional packages are not present.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .config import APP_VERSION, resolve_git_commit
from .corpus_binary_manifest import target_key
from .pipelines.capabilities import pipeline_contract_identity

_SOURCE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    # The shared Corpus Builder currently imports PyMuPDF and httpx as part of
    # its application-layer dependency closure, even for media whose extractor
    # itself is standard-library-only. Report that honestly instead of claiming
    # a text-only run is executable in a deliberately minimal binary.
    "pdf": ("fitz", "httpx"),
    "text": ("fitz", "httpx"),
    "html": ("fitz", "httpx"),
    "rtf": ("fitz", "httpx"),
    "doc": ("fitz", "httpx"),
    "docx": ("fitz", "httpx"),
    "gutenberg": ("fitz", "httpx"),
    "url": ("fitz", "httpx"),
    "image": ("fitz", "httpx", "PIL"),
    "audio": ("fitz", "httpx"),
}

_SOURCE_SUFFIXES: dict[str, str] = {
    ".pdf": "pdf",
    ".txt": "text",
    ".text": "text",
    ".md": "text",
    ".html": "html",
    ".htm": "html",
    ".rtf": "rtf",
    ".doc": "doc",
    ".docx": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".flac": "audio",
    ".webm": "audio",
    ".mp4": "audio",
    ".mpeg": "audio",
    ".mpga": "audio",
    ".aac": "audio",
}

_BUNDLED_NLP_PACKAGES: tuple[tuple[str, str], ...] = (
    ("en", "en_core_web_sm"),
    ("fr", "fr_core_news_sm"),
    ("la", "la_core_web_sm"),
)


def _module_available(name: str) -> bool:
    """Check a Python capability without importing it or triggering model loads."""

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _tool(name: str, version_args: tuple[str, ...]) -> dict[str, Any]:
    """Inspect one fixed helper executable without shell interpretation."""

    executable = shutil.which(name)
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        completed = subprocess.run(  # noqa: S603 - executable comes from fixed caller-owned allowlist
            [executable, *version_args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "path": executable, "version": None}

    output = (completed.stdout or completed.stderr or "").splitlines()
    return {
        "available": completed.returncode == 0,
        "path": executable,
        "version": output[0].strip() if output else None,
    }


def _writable_directory(path: Path) -> dict[str, Any]:
    """Prove a directory is writable using a cleaned-up file, not os.access()."""

    target = path.expanduser().resolve()
    try:
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".derridai-doctor-",
            dir=target,
            delete=True,
        ):
            pass
    except OSError as exc:
        return {
            "path": str(target),
            "writable": False,
            "error": str(exc),
        }
    return {"path": str(target), "writable": True, "error": None}


def _nlp_resources() -> dict[str, Any]:
    bundled = {
        language: {
            "package": package,
            "available": _module_available(package),
        }
        for language, package in _BUNDLED_NLP_PACKAGES
    }
    models_root = os.getenv("DOCUMENT_NLP_MODELS_DIR", "").strip()
    return {
        "spacy": {
            "available": _module_available("spacy"),
            "bundled_models": bundled,
        },
        "managed_models": {
            "configured_path": models_root or None,
            "path_exists": bool(models_root and Path(models_root).expanduser().is_dir()),
        },
        "booknlp": {
            "worker_configured": bool(os.getenv("DOCUMENT_NLP_BASE_URL", "").strip()),
            "local_package_available": _module_available("booknlp"),
        },
        "whisperx": {
            "available": _module_available("whisperx"),
        },
    }


def _source_kinds(
    *,
    tesseract: dict[str, Any],
    ffprobe: dict[str, Any],
) -> dict[str, Any]:
    module_status = {
        name: _module_available(name)
        for name in sorted({module for modules in _SOURCE_REQUIREMENTS.values() for module in modules})
    }
    result: dict[str, Any] = {}
    for kind, required_modules in _SOURCE_REQUIREMENTS.items():
        missing = [
            f"python:{module}"
            for module in required_modules
            if not module_status[module]
        ]
        if kind == "image" and not tesseract["available"]:
            missing.append("tool:tesseract")
        if kind == "audio" and not ffprobe["available"]:
            missing.append("tool:ffprobe")
        result[kind] = {
            "available": not missing,
            "missing": missing,
        }
    return result


def source_preflight(
    path: str | Path,
    *,
    ocr_mode: str = "auto",
) -> dict[str, Any]:
    """Return only capabilities relevant to one local source path.

    This is a cheap filename-level preflight. Content sniffing and safety limits
    remain authoritative in the ingestion layer after the file is read.
    """

    source = Path(path)
    kind = _SOURCE_SUFFIXES.get(source.suffix.casefold())

    # Helper probes are source-kind aware: an ordinary text/PDF run must not
    # depend on audio tooling, and native-text PDF processing does not require
    # Tesseract unless OCR is explicitly forced.
    tesseract = (
        _tool("tesseract", ("--version",))
        if kind == "image" or (kind == "pdf" and ocr_mode == "always")
        else {"available": False, "path": None, "version": None}
    )
    ffprobe = (
        _tool("ffprobe", ("-version",))
        if kind == "audio"
        else {"available": False, "path": None, "version": None}
    )

    # Unknown/no-extension files may still be supported plain text. The shared
    # engine dependencies are nevertheless required before any build can start.
    required_modules = (
        _SOURCE_REQUIREMENTS[kind]
        if kind is not None
        else ("fitz", "httpx")
    )
    missing = [
        f"python:{module}"
        for module in required_modules
        if not _module_available(module)
    ]
    if kind == "image" and not tesseract["available"]:
        missing.append("tool:tesseract")
    if kind == "pdf" and ocr_mode == "always" and not tesseract["available"]:
        missing.append("tool:tesseract")
    if kind == "audio" and not ffprobe["available"]:
        missing.append("tool:ffprobe")

    return {
        "kind": kind,
        "available": not missing,
        "missing": list(dict.fromkeys(missing)),
    }


def runtime_capabilities(
    *,
    workspace: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Return one machine-readable diagnostic snapshot without network access."""

    # Import lazily so capability inspection remains cheap and does not import the
    # Corpus Builder engine or any optional extractor package.
    from .headless_corpus_runner import default_cli_data_root

    workspace_path = (
        Path(workspace).expanduser()
        if workspace is not None
        else default_cli_data_root()
    )
    output_path = (
        Path(output_directory).expanduser()
        if output_directory is not None
        else Path.cwd()
    )

    tesseract = _tool("tesseract", ("--version",))
    ffmpeg = _tool("ffmpeg", ("-version",))
    ffprobe = _tool("ffprobe", ("-version",))

    try:
        native_target: str | None = target_key()
    except ValueError:
        native_target = None

    return {
        "application": {
            "version": APP_VERSION,
            "source_commit": resolve_git_commit() or None,
            "python": platform.python_version(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "target": native_target,
        },
        "filesystem": {
            "workspace": _writable_directory(workspace_path),
            "output": _writable_directory(output_path),
        },
        "helpers": {
            "tesseract": tesseract,
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
        },
        "nlp_resources": _nlp_resources(),
        "source_kinds": _source_kinds(
            tesseract=tesseract,
            ffprobe=ffprobe,
        ),
        "provider_reachability": {
            "checked": False,
            "reason": "Network providers are not probed by the default doctor command.",
        },
        "pipeline_contract": pipeline_contract_identity(),
    }
