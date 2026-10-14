# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Browser-compatible publication embeddings for static research sites.

The published site uses a pinned, quantized multilingual E5 model through
Transformers.js.  This module runs that same ONNX artifact on the API when an
administrator chooses the browser-ready publication strategy, so Record vectors
can ship with the site while query embeddings are produced by the browser.

The model is downloaded lazily into DerridAI's model cache.  It is never baked
into the API image and corpus processing never triggers the download.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .config import settings

BROWSER_EMBEDDING_PROFILE: dict[str, Any] = {
    "id": "Xenova/multilingual-e5-small",
    "upstream_id": "intfloat/multilingual-e5-small",
    "revision": "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
    "dimension": 384,
    "max_length": 512,
    "dtype": "q8",
    "pooling": "mean",
    "normalize": True,
    "query_prefix": "query: ",
    "document_prefix": "passage: ",
    "model_file": "onnx/model_quantized.onnx",
    "model_bytes": 135390915,
}

_EXPECTED_SHA256 = {
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    "onnx/model_quantized.onnx": "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
}
_ALLOWED_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "onnx/model_quantized.onnx",
)
_lock = threading.Lock()
_runtime: tuple[Any, Any] | None = None


class BrowserEmbeddingUnavailableError(RuntimeError):
    """The pinned browser-compatible model could not be loaded or downloaded."""


def browser_embedding_contract() -> dict[str, Any]:
    """Manifest-safe embedding contract shared with the published site."""
    profile = BROWSER_EMBEDDING_PROFILE
    variant = ";".join(
        (
            f"query-prefix={profile['query_prefix']}",
            f"document-prefix={profile['document_prefix']}",
            f"dtype={profile['dtype']}",
            f"pooling={profile['pooling']}",
            f"normalize={str(bool(profile['normalize'])).lower()}",
        )
    )
    return {
        "provider": "transformers",
        "model": profile["id"],
        "dimension": profile["dimension"],
        "revision": profile["revision"],
        "variant": variant,
        "distance_metric": "cosine",
        "text_field": "text",
    }


def browser_embedding_profile() -> dict[str, Any]:
    """Small public description used by the publication UI and manifest."""
    profile = BROWSER_EMBEDDING_PROFILE
    return {
        "model": profile["id"],
        "revision": profile["revision"],
        "dimension": profile["dimension"],
        "dtype": profile["dtype"],
        "pooling": profile["pooling"],
        "normalize": profile["normalize"],
        "query_prefix": profile["query_prefix"],
        "document_prefix": profile["document_prefix"],
        "download_bytes": profile["model_bytes"],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _model_cache_dir() -> Path:
    """Return the deterministic cache directory for the pinned browser model."""
    profile = BROWSER_EMBEDDING_PROFILE
    repository = str(profile["id"]).replace("/", "--")
    return (
        Path(settings.rag_model_cache)
        / "site-embeddings"
        / repository
        / str(profile["revision"])
    )


def _download_model_file(relative: str, target: Path) -> None:
    """Download one pinned public artifact without invoking Hugging Face Hub.

    DerridAI's publication model is a public, revision-pinned dependency. Using
    the Hub snapshot helper for it makes a normal anonymous download emit an
    authentication warning in API logs. A direct HTTPS transfer keeps anonymous
    operation quiet while still honoring HF_TOKEN when an administrator supplies
    one for higher Hub rate limits.
    """
    import httpx

    profile = BROWSER_EMBEDDING_PROFILE
    repository = quote(str(profile["id"]), safe="/")
    revision = quote(str(profile["revision"]), safe="")
    artifact = quote(relative, safe="/")
    url = f"https://huggingface.co/{repository}/resolve/{revision}/{artifact}"
    headers = {"User-Agent": "DerridAI/site-embeddings"}
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".part",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with httpx.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=True,
                timeout=httpx.Timeout(120.0, connect=20.0),
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    temporary.write(chunk)
        temporary_path.replace(target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _prepare_model_snapshot() -> Path:
    """Ensure the allowlisted model snapshot exists and verifies locally."""
    local_dir = _model_cache_dir()
    for relative in _ALLOWED_FILES:
        target = local_dir / relative
        expected = _EXPECTED_SHA256.get(relative)
        if target.is_file() and (expected is None or _sha256(target) == expected):
            continue
        target.unlink(missing_ok=True)
        _download_model_file(relative, target)

    for relative, expected in _EXPECTED_SHA256.items():
        path = local_dir / relative
        if not path.is_file() or _sha256(path) != expected:
            raise BrowserEmbeddingUnavailableError(
                f"The pinned browser embedding artifact {relative!r} failed integrity verification."
            )
    return local_dir

def _load_runtime() -> tuple[Any, Any]:
    global _runtime
    if _runtime is not None:
        return _runtime
    with _lock:
        if _runtime is not None:
            return _runtime
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer

            local_dir = _prepare_model_snapshot()
            tokenizer = AutoTokenizer.from_pretrained(local_dir, local_files_only=True)
            session = ort.InferenceSession(
                str(local_dir / str(BROWSER_EMBEDDING_PROFILE["model_file"])),
                providers=["CPUExecutionProvider"],
            )
            _runtime = (tokenizer, session)
            return _runtime
        except BrowserEmbeddingUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced as a publication dependency failure
            raise BrowserEmbeddingUnavailableError(
                "The browser-compatible multilingual embedding model could not be prepared. "
                "Check network access and the DerridAI model cache, then retry."
            ) from exc


def embed_browser_documents(texts: list[str], *, batch_size: int = 16) -> list[list[float]]:
    """Embed Record text with the exact browser publication model and passage prefix."""
    if not texts:
        return []
    import numpy as np

    tokenizer, session = _load_runtime()
    profile = BROWSER_EMBEDDING_PROFILE
    input_names = {item.name for item in session.get_inputs()}
    vectors: list[list[float]] = []
    for start in range(0, len(texts), max(1, batch_size)):
        batch = [
            f"{profile['document_prefix']}{str(text or '')}"
            for text in texts[start : start + max(1, batch_size)]
        ]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=int(profile["max_length"]),
            return_tensors="np",
        )
        if "token_type_ids" in input_names and "token_type_ids" not in encoded:
            encoded["token_type_ids"] = np.zeros_like(encoded["input_ids"])
        inputs = {
            key: np.asarray(value, dtype=np.int64)
            for key, value in encoded.items()
            if key in input_names
        }
        output = np.asarray(session.run(None, inputs)[0], dtype=np.float32)
        if output.ndim == 3:
            mask = np.asarray(encoded["attention_mask"], dtype=np.float32)[..., None]
            pooled = (output * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1.0, None)
        elif output.ndim == 2:
            pooled = output
        else:
            raise BrowserEmbeddingUnavailableError(
                f"Unexpected browser embedding model output shape {tuple(output.shape)}."
            )
        if bool(profile["normalize"]):
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            pooled = pooled / np.clip(norms, 1e-12, None)
        if pooled.shape[1] != int(profile["dimension"]):
            raise BrowserEmbeddingUnavailableError(
                "The browser embedding model returned an unexpected vector dimension."
            )
        vectors.extend([[float(value) for value in row] for row in pooled])
    return vectors
