# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Browser-compatible publication embeddings for static research sites.

The published site uses a pinned, quantized multilingual E5 model through
Transformers.js. This module runs the same tokenizer and ONNX artifact on the API
when an administrator chooses the browser-ready publication strategy, so Record
vectors can ship with the site while query embeddings are produced by the browser.

Only the tokenizer and model files required for inference are downloaded. They are
size-bounded, SHA-256 verified, cached under DerridAI's model cache, and never baked
into the API image. Corpus processing never triggers this download.
"""

from __future__ import annotations

import hashlib
import os
import threading
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
    "model_bytes": 118308185,
    "download_bytes": 135390915,
}

_REPO_URL = "https://huggingface.co/Xenova/multilingual-e5-small/resolve"
_ARTIFACTS = {
    "tokenizer.json": {
        "path": "tokenizer.json",
        "size": 17082730,
        "sha256": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    },
    "model_quantized.onnx": {
        "path": "onnx/model_quantized.onnx",
        "size": 118308185,
        "sha256": "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
    },
}
_CHUNK_BYTES = 1024 * 1024
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
        "download_bytes": profile["download_bytes"],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_cached_artifact(path: Path, *, size: int, sha256: str) -> bool:
    return path.is_file() and path.stat().st_size == size and _sha256(path) == sha256


def _download_artifact(name: str, target: Path) -> Path:
    artifact = _ARTIFACTS[name]
    size = int(artifact["size"])
    digest_expected = str(artifact["sha256"])
    if _valid_cached_artifact(target, size=size, sha256=digest_expected):
        return target

    revision = str(BROWSER_EMBEDDING_PROFILE["revision"])
    url = f"{_REPO_URL}/{revision}/{artifact['path']}"
    part = target.with_suffix(target.suffix + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    digest = hashlib.sha256()
    total = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "DerridAI static-site publisher"})
        with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as handle:  # noqa: S310
            final_url = response.geturl()
            parsed = urlparse(final_url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise BrowserEmbeddingUnavailableError(
                    f"The pinned browser embedding artifact {name!r} redirected away from HTTPS."
                )
            while True:
                chunk = response.read(_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > size:
                    raise BrowserEmbeddingUnavailableError(
                        f"The pinned browser embedding artifact {name!r} exceeded its declared size."
                    )
                digest.update(chunk)
                handle.write(chunk)
        if total != size or digest.hexdigest() != digest_expected:
            raise BrowserEmbeddingUnavailableError(
                f"The pinned browser embedding artifact {name!r} failed integrity verification."
            )
        os.replace(part, target)
        return target
    finally:
        part.unlink(missing_ok=True)


def _load_runtime() -> tuple[Any, Any]:
    global _runtime
    if _runtime is not None:
        return _runtime
    with _lock:
        if _runtime is not None:
            return _runtime
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            cache_dir = (
                Path(settings.rag_model_cache)
                / "site-embeddings"
                / str(BROWSER_EMBEDDING_PROFILE["revision"])
            )
            tokenizer_path = _download_artifact("tokenizer.json", cache_dir / "tokenizer.json")
            model_path = _download_artifact(
                "model_quantized.onnx",
                cache_dir / "model_quantized.onnx",
            )

            tokenizer = Tokenizer.from_file(str(tokenizer_path))
            tokenizer.enable_truncation(max_length=int(BROWSER_EMBEDDING_PROFILE["max_length"]))
            pad_token = "<pad>" if tokenizer.token_to_id("<pad>") is not None else "[PAD]"
            pad_id = tokenizer.token_to_id(pad_token)
            tokenizer.enable_padding(pad_id=pad_id or 0, pad_token=pad_token)
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
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
    effective_batch_size = max(1, batch_size)
    for start in range(0, len(texts), effective_batch_size):
        batch = [
            f"{profile['document_prefix']}{str(text or '')}"
            for text in texts[start : start + effective_batch_size]
        ]
        encodings = tokenizer.encode_batch(batch)
        input_ids = np.asarray([encoding.ids for encoding in encodings], dtype=np.int64)
        attention_mask = np.asarray(
            [encoding.attention_mask for encoding in encodings],
            dtype=np.int64,
        )
        token_type_ids = np.asarray(
            [encoding.type_ids for encoding in encodings],
            dtype=np.int64,
        )
        available_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }
        inputs = {key: value for key, value in available_inputs.items() if key in input_names}
        output = np.asarray(session.run(None, inputs)[0], dtype=np.float32)
        if output.ndim == 3:
            mask = attention_mask.astype(np.float32)[..., None]
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
