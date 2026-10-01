# Copyright 2026 Aaron John Schlosser, PhD.
"""In-browser embedding runtime packaged into every published site, fetched on first use and cached.

DerridAI does not ship Transformers.js in the application image. The first site export downloads the pinned
files below once from a fixed HTTPS source, verifies each file's size and SHA-256, and keeps them in the
data directory. Later exports reuse that cache. An administrator can delete it; the next export downloads
it again. Model weights are never downloaded here.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import settings

TRANSFORMERS_VERSION = "4.3.0"
ONNXRUNTIME_WEB_VERSION = "1.31.0-dev.20260914-8d85527a0"
_CDN = "https://cdn.jsdelivr.net/npm"
_CHUNK_BYTES = 1024 * 256

# Pinned artifacts: nothing is accepted unless its size and SHA-256 match exactly.
ARTIFACTS: tuple[dict[str, Any], ...] = (
    {
        "role": "engine",
        "filename": "transformers.min.js",
        "url": f"{_CDN}/@huggingface/transformers@{TRANSFORMERS_VERSION}/dist/transformers.min.js",
        "size": 581935,
        "sha256": "1475fd440e9932ab206682ee42cb18f6097403e9ee77ea62084c592d0f83597d",
    },
    {
        "role": "license",
        "filename": "LICENSE-transformers.js.txt",
        "url": f"{_CDN}/@huggingface/transformers@{TRANSFORMERS_VERSION}/LICENSE",
        "size": 11358,
        "sha256": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    },
    {
        "role": "wasm_factory",
        "filename": "ort-wasm-simd-threaded.mjs",
        "url": f"{_CDN}/onnxruntime-web@{ONNXRUNTIME_WEB_VERSION}/dist/ort-wasm-simd-threaded.mjs",
        "size": 24381,
        "sha256": "c57ca56328877353a575e51bbca6f18450027d6c9bf2307a2cb2c41363b4de9f",
    },
    {
        "role": "wasm",
        "filename": "ort-wasm-simd-threaded.wasm",
        "url": f"{_CDN}/onnxruntime-web@{ONNXRUNTIME_WEB_VERSION}/dist/ort-wasm-simd-threaded.wasm",
        "size": 14264838,
        "sha256": "06ba057753da3847e4c24f02d91ab133455b0817c69a44993a9a53a2146df9e3",
    },
)

DOWNLOAD_BYTES = sum(int(item["size"]) for item in ARTIFACTS)
# Embedded in a single-file or two-file site: base64 of the engine, the WASM factory, and the gzipped WASM
# (about 3.7 MB). The gzip size is measured once and recorded here so the export dialog can state it before
# anything is downloaded.
_GZIPPED_WASM_BYTES = 3_667_671
INLINE_BYTES_ESTIMATE = -(
    -4
    * (int(ARTIFACTS[0]["size"]) + int(ARTIFACTS[2]["size"]) + _GZIPPED_WASM_BYTES)
    // 3
)

_lock = threading.Lock()


class RuntimeUnavailableError(RuntimeError):
    """The runtime could not be downloaded or verified; nothing partial is kept."""


def runtime_dir() -> Path:
    return Path(settings.chroma_data_root) / "site_runtime" / f"transformers-{TRANSFORMERS_VERSION}"


def _verified(path: Path, item: dict[str, Any]) -> bool:
    try:
        if path.stat().st_size != int(item["size"]):
            return False
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
                digest.update(chunk)
        return digest.hexdigest() == item["sha256"]
    except OSError:
        return False


def is_cached() -> bool:
    """True when every pinned file is present with the right size (cheap; digests are checked on use)."""
    directory = runtime_dir()
    for item in ARTIFACTS:
        try:
            if (directory / item["filename"]).stat().st_size != int(item["size"]):
                return False
        except OSError:
            return False
    return True


def delete_runtime() -> None:
    """Remove the cached runtime so the next export downloads it again."""
    directory = runtime_dir()
    with _lock:
        if directory.exists():
            shutil.rmtree(directory)


def _download(
    item: dict[str, Any],
    target: Path,
    opener: Callable[..., Any],
    on_progress: Callable[[dict[str, Any]], None] | None,
    received_before: int,
    total_bytes: int,
) -> None:
    """Stream one artifact to ``target`` with size and digest checks; nothing partial survives."""
    if not str(item["url"]).startswith("https://"):
        raise RuntimeUnavailableError(f"{item['filename']} must be downloaded over HTTPS.")
    limit = int(item["size"])
    part = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        with opener(item["url"], timeout=60) as response, part.open("wb") as handle:  # noqa: S310 - https only
            final_url = response.geturl() if hasattr(response, "geturl") else item["url"]
            if not str(final_url).startswith("https://"):
                raise RuntimeUnavailableError(f"{item['filename']} redirected to a non-HTTPS URL.")
            while True:
                chunk = response.read(_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise RuntimeUnavailableError(
                        f"{item['filename']} is larger than its expected {limit} bytes."
                    )
                digest.update(chunk)
                handle.write(chunk)
                if on_progress:
                    on_progress(
                        {
                            "status": "progress",
                            "file": item["filename"],
                            "received": total,
                            "file_total": limit,
                            "received_total": received_before + total,
                            "total": total_bytes,
                        }
                    )
        if total != limit:
            raise RuntimeUnavailableError(f"{item['filename']} is {total} bytes, expected {limit}.")
        if digest.hexdigest() != item["sha256"]:
            raise RuntimeUnavailableError(f"{item['filename']} failed SHA-256 verification.")
        os.replace(part, target)
    except RuntimeUnavailableError:
        raise
    except Exception as exc:  # network, DNS, TLS, and filesystem failures all mean "not available"
        raise RuntimeUnavailableError(f"Could not download {item['filename']}: {exc}") from exc
    finally:
        part.unlink(missing_ok=True)


def ensure_runtime(
    opener: Callable[..., Any] = urllib.request.urlopen,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, bytes]:
    """Return the pinned runtime files by role, downloading any that are missing or fail verification."""
    directory = runtime_dir()
    total_bytes = sum(int(item["size"]) for item in ARTIFACTS)
    with _lock:
        directory.mkdir(parents=True, exist_ok=True)
        received_before = 0
        for item in ARTIFACTS:
            target = directory / item["filename"]
            if not _verified(target, item):
                target.unlink(missing_ok=True)
                _download(item, target, opener, on_progress, received_before, total_bytes)
            received_before += int(item["size"])
        if on_progress:
            on_progress({"status": "complete", "received_total": total_bytes, "total": total_bytes})
        return {str(item["role"]): (directory / item["filename"]).read_bytes() for item in ARTIFACTS}


def notice_text() -> str:
    lines = [
        "Third-party runtime packaged into this site at the exporting administrator's request.",
        "It was downloaded unmodified from the pinned sources below and verified by SHA-256.",
        "",
    ]
    for item in ARTIFACTS:
        if item["role"] == "license":
            continue
        lines += [item["filename"], f"  source {item['url']}", f"  sha256 {item['sha256']}"]
    lines += [
        "",
        f"@huggingface/transformers {TRANSFORMERS_VERSION} is Apache-2.0 (see LICENSE-transformers.js.txt) and",
        "bundles onnxruntime-web (MIT, Copyright (c) Microsoft Corporation).",
        "No model weights are included.",
    ]
    return "\n".join(lines) + "\n"


def runtime_info() -> dict[str, Any]:
    """Describe the cached runtime for the export dialog without downloading anything."""
    return {
        "version": TRANSFORMERS_VERSION,
        "cached": is_cached(),
        "download_bytes": DOWNLOAD_BYTES,
        "inline_bytes": INLINE_BYTES_ESTIMATE,
    }
