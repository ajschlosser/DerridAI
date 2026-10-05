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

"""Shared relevance normalization and diversity selection primitives.

Retrieval scores are operational signals, not scholarly evidence. This module
keeps their semantics explicit so vector distance, reranker relevance, and MMR
objectives are not silently collapsed into one ambiguous score field.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .research_semantics import source_author


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


def mmr_select[Candidate: Mapping[str, Any]](
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
    relevances = [float(relevance(candidate)) for candidate in remaining]
    vectors = [vector(candidate) for candidate in remaining]
    diversities = [0.0] * len(remaining)
    selected: list[dict[str, Any]] = []

    while remaining and len(selected) < bounded_limit:
        best_index = 0
        best_score = -float("inf")
        for index in range(len(remaining)):
            if selected:
                similarity = cosine_similarity(vectors[index], selected[-1].get("_mmr_vector"))
                # Extend the previous maximum with only the newest selection.
                # The first comparison must retain negative cosine similarity.
                diversities[index] = similarity if len(selected) == 1 else max(diversities[index], similarity)
            objective = lam * relevances[index] - (1.0 - lam) * diversities[index]
            if objective > best_score:
                best_index = index
                best_score = objective

        source = remaining.pop(best_index)
        chosen = dict(source)
        # Keep the vector only as an internal scratch value while selecting. It
        # is removed before the result escapes so API payloads do not balloon.
        chosen["_mmr_vector"] = vectors.pop(best_index)
        relevances.pop(best_index)
        diversities.pop(best_index)
        chosen[score_key] = best_score
        selected.append(chosen)

    for chosen in selected:
        chosen.pop("_mmr_vector", None)
    return selected


def source_aware_select[Candidate: Mapping[str, Any]](
    candidates: Sequence[Candidate],
    *,
    limit: int,
    relevance: Callable[[Candidate], float],
) -> list[dict[str, Any]]:
    """Greedily pack relevant candidates while penalizing redundant source context.

    This selector is intentionally metadata-aware rather than another embedding
    similarity heuristic. It favors different source documents/works and avoids
    filling a context packet with adjacent or text-duplicate Records from the
    same passage. User-selected evidence remains pinned by callers before this
    selector is applied.
    """

    bounded_limit = max(0, int(limit))
    if bounded_limit == 0 or not candidates:
        return []

    remaining: list[Candidate] = list(candidates)
    raw_relevance = [float(relevance(item)) for item in remaining]
    minimum = min(raw_relevance)
    maximum = max(raw_relevance)

    def normalized(value: float) -> float:
        if maximum <= minimum:
            return 1.0
        return (value - minimum) / (maximum - minimum)

    def record_of(item: Mapping[str, Any]) -> Mapping[str, Any]:
        record = item.get("record")
        return record if isinstance(record, Mapping) else item

    def text_terms(item: Mapping[str, Any]) -> set[str]:
        record = record_of(item)
        text = str(record.get("text") or "").casefold()
        return {token for token in text.split() if len(token) > 3}

    def redundancy(
        candidate: Mapping[str, Any], selected: Mapping[str, Any],
        left_terms: set[str], right_terms: set[str],
    ) -> float:
        left = record_of(candidate)
        right = record_of(selected)
        penalty = 0.0

        left_source = str(
            left.get("source_document_id")
            or left.get("source_asset_id")
            or ""
        )
        right_source = str(
            right.get("source_document_id")
            or right.get("source_asset_id")
            or ""
        )
        if left_source and left_source == right_source:
            penalty += 0.28

        left_work = str(left.get("work") or "")
        right_work = str(right.get("work") or "")
        if left_work and left_work == right_work:
            penalty += 0.12

        left_author = source_author(left).casefold()
        right_author = source_author(right).casefold()
        if left_author and left_author == right_author:
            # Work/source diversity alone can still collapse onto a prolific
            # author represented by many distinct documents. Penalize repeated
            # document authors so cross-author alternatives remain competitive.
            # A different-author candidate should remain viable even when the
            # prolific author's second-best passage is only modestly less
            # relevant. This penalty applies only after the first selection and
            # only when both records identify the same source author.
            penalty += 0.75

        try:
            left_page = int(left.get("page_start"))
            right_page = int(right.get("page_start"))
        except (TypeError, ValueError):
            left_page = right_page = -10000
        if left_source and left_source == right_source and abs(left_page - right_page) <= 1:
            penalty += 0.30

        if left_terms and right_terms:
            overlap = len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms)))
            penalty += min(0.30, overlap * 0.30)

        # Same-source adjacent near-duplicates should lose to a reasonably
        # relevant alternative source. Keep a small floor for exceptional cases
        # where every candidate is redundant, but allow the combined penalty to
        # outweigh a near-tied relevance score.
        return min(0.95, penalty)

    relevances = [normalized(value) for value in raw_relevance]
    # Tokenize each passage once, rather than once per pair per round.
    terms = [text_terms(candidate) for candidate in remaining]
    penalties = [0.0] * len(remaining)
    selected_terms: set[str] = set()
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < bounded_limit:
        best_index = 0
        best_score = -float("inf")
        for index, candidate in enumerate(remaining):
            if selected:
                penalties[index] = max(
                    penalties[index],
                    redundancy(candidate, selected[-1], terms[index], selected_terms),
                )
            objective = relevances[index] - penalties[index]
            if objective > best_score:
                best_score = objective
                best_index = index
        chosen = dict(remaining.pop(best_index))
        selected_terms = terms.pop(best_index)
        relevances.pop(best_index)
        penalties.pop(best_index)
        chosen["diversity_score"] = best_score
        selected.append(chosen)

    return selected
