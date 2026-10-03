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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Shared optional CrossEncoder inference boundary for bounded reranking."""

from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .config import settings

_MODEL_CACHE: dict[str, Any] = {}


def predict_scores(
    pairs: list[tuple[str, str]],
    *,
    model_name: str,
    timeout_seconds: float | None = None,
) -> tuple[list[float] | None, dict[str, Any]]:
    """Predict a bounded batch of pair scores, failing open with diagnostics."""

    started = time.monotonic()
    model_name = str(model_name or "").strip()
    telemetry: dict[str, Any] = {
        "provider": "sentence-transformers",
        "model": model_name,
        "candidate_count": len(pairs),
        "reranked_count": 0,
        "mode": "cross_encoder",
    }
    if not pairs:
        telemetry["timing_ms"] = 0
        return [], telemetry
    if not model_name:
        telemetry["fallback_reason"] = "cross_encoder_model_not_configured"
        telemetry["timing_ms"] = _elapsed_ms(started)
        return None, telemetry

    try:
        import sentence_transformers
        from sentence_transformers import CrossEncoder

        telemetry["library_version"] = str(
            getattr(sentence_transformers, "__version__", "") or ""
        ) or None
    except Exception as exc:
        telemetry["fallback_reason"] = f"missing_dependency: {exc}"
        telemetry["timing_ms"] = _elapsed_ms(started)
        return None, telemetry

    try:
        model = _MODEL_CACHE.get(model_name)
        if model is None:
            cache_dir = Path(settings.rag_model_cache)
            cache_dir.mkdir(parents=True, exist_ok=True)
            model = CrossEncoder(model_name, cache_dir=str(cache_dir))
            _MODEL_CACHE[model_name] = model
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cross-encoder")
        future = executor.submit(model.predict, [[query, text] for query, text in pairs])
        try:
            scores = future.result(timeout=timeout_seconds)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        values = list(scores.tolist() if hasattr(scores, "tolist") else scores)
        if len(values) != len(pairs):
            raise ValueError(
                f"cross-encoder returned {len(values)} scores for {len(pairs)} candidates"
            )
        normalized = [float(value) for value in values]
        if not all(math.isfinite(value) for value in normalized):
            raise ValueError("cross-encoder returned non-finite scores")
        telemetry["reranked_count"] = len(normalized)
        telemetry["timing_ms"] = _elapsed_ms(started)
        return normalized, telemetry
    except TimeoutError:
        telemetry["fallback_reason"] = "inference_timeout"
    except Exception as exc:
        telemetry["fallback_reason"] = f"inference_failed: {exc}"
    telemetry["timing_ms"] = _elapsed_ms(started)
    return None, telemetry


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))
