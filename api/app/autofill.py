# Copyright 2026 Aaron John Schlosser, PhD.
"""When an LLM-proposed metadata value may be filled in without a person deciding first.

Autofill needs the value to be supported by cited evidence (checked by the caller) and a blended
confidence of AUTOFILL_THRESHOLD or more. The blend anchors the model's own report with what
reviewers actually did with this model's earlier values on this field, weighted so that a few
reviews nudge it and many settle it:

    confidence = (accepted + PRIOR_REVIEWS * self_report) / (reviews + PRIOR_REVIEWS)

where `accepted` is the number of reviewed values people kept. With no history it equals the model's
own report; after PRIOR_REVIEWS reviews the two count equally. If measured precision falls below
SUSPEND_PRECISION after at least SUSPEND_MIN_REVIEWS reviews, autofill stops for that model and
field, and its values go to review again. A stable pseudo-random AUDIT_RATE share of autofilled
values is flagged for a spot check, so a wrong-but-confident model is still caught.
"""

from __future__ import annotations

import hashlib
from typing import TypedDict


class AutofillDecision(TypedDict):
    autofill: bool
    confidence: float | None
    suspended: bool

AUTOFILL_THRESHOLD = 0.9
PRIOR_REVIEWS = 20
SUSPEND_PRECISION = 0.8
SUSPEND_MIN_REVIEWS = 20
AUDIT_RATE = 0.10


def blended_confidence(self_report: float, reviews: int, accepted: int) -> float:
    self_report = max(0.0, min(1.0, float(self_report)))
    return (accepted + PRIOR_REVIEWS * self_report) / (reviews + PRIOR_REVIEWS)


def is_suspended(reviews: int, accepted: int) -> bool:
    return reviews >= SUSPEND_MIN_REVIEWS and accepted / reviews < SUSPEND_PRECISION


def in_audit_sample(record_id: str, field: str, rate: float = AUDIT_RATE) -> bool:
    """Stable per (record, field), so a re-run does not change which values are being audited."""
    digest = hashlib.sha256(f"{record_id}\0{field}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**32 < rate


def decide(self_report: float | None, reviews: int, accepted: int) -> AutofillDecision:
    """Whether the model's value may be autofilled, and the confidence that decided it."""
    if self_report is None:
        return {"autofill": False, "confidence": None, "suspended": False}
    confidence = round(blended_confidence(self_report, reviews, accepted), 4)
    suspended = is_suspended(reviews, accepted)
    return {"autofill": confidence >= AUTOFILL_THRESHOLD and not suspended, "confidence": confidence, "suspended": suspended}
