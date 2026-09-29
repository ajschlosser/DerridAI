# Copyright 2026 Aaron John Schlosser, PhD.
"""Shared relevance normalization and diversity selection primitives.

Retrieval scores are operational signals, not scholarly evidence. This module
keeps their semantics explicit so vector distance, reranker relevance, and MMR
objectives are not silently collapsed into one ambiguous score field.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

Candidate = TypeVar("Candidate", bound=Mapping[str, Any])


def cosine_similarity(left: Any, right: Any) -> float:
    """Return cosine similarity without relying on NumPy truthiness."""

    if left is None or right is None:
        return 0.0
    try:
        a = list(left)
        b = list(right)
    except TypeError:
        return 0.0
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(y) * float(y) for y in b))
    return dot / (na * nb) if na and nb else 0.0


def distance_to_relevance(distance: Any, metric: str | None = None) -> float:
    """Normalize a collection-native distance into a bounded relevance signal.

    Chroma collections can use cosine, L2, or inner-product distance. Treating
    all three as non-negative Euclidean distance erases meaningful negative
    inner-product values and makes thresholds incomparable.

    The returned value is in [0, 1] and is intended for ranking/fusion, not as
    a calibrated probability:

    - cosine: Chroma distance is 1 - cosine_similarity; map the theoretical
      [0, 2] range linearly onto [1, 0];
    - l2: use the monotone inverse-distance transform 1 / (1 + d);
    - ip: preserve signed ordering with a logistic transform of native distance,
      where lower/negative distances are more relevant;
    - unknown/legacy: retain the historical non-negative inverse-distance rule
      so old collections do not silently change behavior until their manifest
      declares a metric.
    """

    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0

    normalized_metric = str(metric or "").strip().casefold()
    if normalized_metric == "cosine":
        return max(0.0, min(1.0, 1.0 - (value / 2.0)))
    if normalized_metric in {"l2", "euclidean"}:
        return 1.0 / (1.0 + max(0.0, value))
    if normalized_metric in {"ip", "inner_product", "inner-product"}:
        # Numerically stable logistic(-distance). Chroma inner-product distance
        # is ordered "smaller is better" and may legitimately be negative.
        if value >= 0:
            z = math.exp(-value)
            return z / (1.0 + z)
        z = math.exp(value)
        return 1.0 / (1.0 + z)

    return 1.0 / (1.0 + max(0.0, value))


def mmr_select(
    candidates: Sequence[Candidate],
    *,
    limit: int,
    lambda_mult: float,
    relevance: Callable[[Candidate], float],
    vector: Callable[[Candidate], Any],
    score_key: str = "mmr_score",
) -> list[dict[str, Any]]:
    """Select candidates by maximum marginal relevance.

    Returned rows are copies and preserve their original relevance fields. The
    MMR objective is stored separately under score_key so downstream traces can
    distinguish "how relevant was this?" from "why was this subset chosen?".
    """

    bounded_limit = max(0, int(limit))
    if bounded_limit == 0 or not candidates:
        return []
    lam = max(0.0, min(1.0, float(lambda_mult)))
    remaining: list[Candidate] = list(candidates)
    selected: list[dict[str, Any]] = []

    while remaining and len(selected) < bounded_limit:
        best_index = 0
        best_score = -float("inf")
        for index, candidate in enumerate(remaining):
            rel = float(relevance(candidate))
            diversity = max(
                (
                    cosine_similarity(vector(candidate), chosen.get("_mmr_vector"))
                    for chosen in selected
                ),
                default=0.0,
            )
            objective = lam * rel - (1.0 - lam) * diversity
            if objective > best_score:
                best_index = index
                best_score = objective

        source = remaining.pop(best_index)
        chosen = dict(source)
        # Keep the vector only as an internal scratch value while selecting. It
        # is removed before the result escapes so API payloads do not balloon.
        chosen["_mmr_vector"] = vector(source)
        chosen[score_key] = best_score
        selected.append(chosen)

    for chosen in selected:
        chosen.pop("_mmr_vector", None)
    return selected
