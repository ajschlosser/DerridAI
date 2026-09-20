# Copyright 2026 Aaron John Schlosser, PhD.
"""Interval and significance helpers, so a headline rate never travels without its uncertainty.

Standard library only. `wilson` is the interval for a proportion (well behaved at small n and at 0
or 1, unlike the normal approximation). `bootstrap_ci` is for anything else (means, differences).
`mcnemar` is the paired test for two models scored on the same items. `cohens_kappa` is agreement
between two labellers beyond chance.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Callable, Sequence

Z95 = 1.959963984540054


def wilson(successes: int, n: int, z: float = Z95) -> dict[str, float | int | None]:
    if n <= 0:
        return {"rate": None, "low": None, "high": None, "n": 0}
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"rate": round(p, 4), "low": round(max(0.0, centre - half), 4), "high": round(min(1.0, centre + half), 4), "n": n}


def bootstrap_ci(values: Sequence[float], stat: Callable[[Sequence[float]], float] = lambda v: sum(v) / len(v), *, rounds: int = 2000, seed: int = 0) -> dict[str, float | int | None]:
    if not values:
        return {"estimate": None, "low": None, "high": None, "n": 0}
    rng = random.Random(seed)  # fixed seed: the same data gives the same interval
    n = len(values)
    draws = sorted(stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(rounds))
    return {"estimate": round(stat(values), 4), "low": round(draws[int(0.025 * rounds)], 4), "high": round(draws[int(0.975 * rounds) - 1], 4), "n": n}


def mcnemar(a_correct: Sequence[bool], b_correct: Sequence[bool]) -> dict[str, float | int | None]:
    """Exact two-sided test on the items where exactly one of two models was right."""
    if len(a_correct) != len(b_correct):
        raise ValueError("Both models must be scored on the same items.")
    only_a = sum(1 for a, b in zip(a_correct, b_correct) if a and not b)
    only_b = sum(1 for a, b in zip(a_correct, b_correct) if b and not a)
    n = only_a + only_b
    if n == 0:
        return {"only_a": 0, "only_b": 0, "p_value": None}
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return {"only_a": only_a, "only_b": only_b, "p_value": round(min(1.0, 2 * tail), 6)}


def cohens_kappa(labels_a: Sequence[object], labels_b: Sequence[object]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        return None
    n = len(labels_a)
    observed = sum(x == y for x, y in zip(labels_a, labels_b)) / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    expected = sum(ca[k] * cb[k] for k in ca) / (n * n)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 4)
