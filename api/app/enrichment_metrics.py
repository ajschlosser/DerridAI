# Copyright 2026 Aaron John Schlosser, PhD.
"""Ten measures of how well a model's metadata enrichment is working, computed from the ledger.

Every figure is a query over enrichment_ledger.jsonl (see enrichment_ledger.py), so it can be
recomputed for any model, field, build or run, and never drifts from what actually happened. A
measure with too little data says so (None) instead of reporting a number that looks precise.
Reviewer time is not recorded, so "effort" is measured as how much of the model's output a person
still had to touch.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .enrichment_ledger import ACCEPTED, AUTOFILLED, CALL, CORRECTED, PROPOSED, REJECTED, REVIEW_EVENTS

THRESHOLDS = (0.7, 0.8, 0.9, 0.95)
LEARNING_BUCKET = 10  # reviews per point on the learning curve


def _rate(part: int | float, whole: int | float) -> float | None:
    return round(part / whole, 4) if whole else None


def _key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)


def _model_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    proposals = [e for e in events if e["kind"] == PROPOSED]
    reviews = [e for e in events if e["kind"] in REVIEW_EVENTS]
    calls = [e for e in events if e["kind"] == CALL]
    accepted = [e for e in reviews if e["kind"] == ACCEPTED]
    corrected = [e for e in reviews if e["kind"] == CORRECTED]
    rejected = [e for e in reviews if e["kind"] == REJECTED]
    scored = [e for e in reviews if isinstance(e.get("confidence"), (int, float))]

    # 2. Calibration: does "90% confident" turn out right about 90% of the time?
    brier = _rate(sum((float(e["confidence"]) - (e["kind"] == ACCEPTED)) ** 2 for e in scored), len(scored))
    bins: dict[int, list[Any]] = defaultdict(list)
    for e in scored:
        bins[min(4, int(float(e["confidence"]) * 5))].append(e["kind"] == ACCEPTED)
    reliability = [{"from": b / 5, "to": (b + 1) / 5, "reviews": len(v), "accuracy": _rate(sum(v), len(v))} for b, v in sorted(bins.items())]

    # 4. Precision against coverage as the bar rises.
    self_reports = [float(e["self_reported"]) for e in proposals if isinstance(e.get("self_reported"), (int, float))]
    at_threshold = []
    for t in THRESHOLDS:
        kept = [e for e in scored if float(e["confidence"]) >= t]
        at_threshold.append({
            "threshold": t, "reviews": len(kept), "precision": _rate(sum(e["kind"] == ACCEPTED for e in kept), len(kept)),
            "coverage": _rate(sum(r >= t for r in self_reports), len(self_reports)),
        })

    # 6. Stability: the same model asked again, in another run, about the same field.
    by_slot: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for e in proposals:
        by_slot[(e.get("build_id", ""), e.get("record_id", ""), e.get("field", ""))][e.get("run_id", "")].add(_key(e.get("value")))
    repeated = [runs for runs in by_slot.values() if len(runs) >= 2]
    stable = sum(1 for runs in repeated if len(set().union(*runs.values())) == 1)

    # 8. Grounding: did the value cite a source block that exists?
    grounded = sum(1 for e in proposals if e.get("grounded"))

    # 9. Cost of a value a person kept.
    elapsed = sum(int(e.get("elapsed_ms") or 0) for e in calls)

    # 10. Learning curve: acceptance in successive groups of reviews.
    curve = []
    for start in range(0, len(reviews), LEARNING_BUCKET):
        chunk = reviews[start : start + LEARNING_BUCKET]
        if len(chunk) == LEARNING_BUCKET:
            curve.append({"reviews_before": start, "acceptance": _rate(sum(e["kind"] == ACCEPTED for e in chunk), len(chunk))})

    autofilled = [e for e in events if e["kind"] == AUTOFILLED]
    audited_reviews = [e for e in reviews if e.get("autofilled")]
    return {
        "proposals": len(proposals),
        "reviews": len(reviews),
        "autofilled": len(autofilled),
        "acceptance_rate": _rate(len(accepted), len(reviews)),  # 1
        "brier_score": brier,  # 2 (0 is perfect; 0.25 is a coin toss)
        "reliability": reliability,  # 2
        "correction_rate": _rate(len(corrected), len(reviews)),  # 3
        "rejection_rate": _rate(len(rejected), len(reviews)),  # 3 (cleared, with no replacement)
        "autofill_precision": _rate(sum(e["kind"] == ACCEPTED for e in audited_reviews), len(audited_reviews)),
        "precision_at_threshold": at_threshold,  # 4
        "stability": _rate(stable, len(repeated)),  # 6 (None until a slot has been run twice)
        "touched_share": _rate(len(reviews), len(proposals)),  # 7 how much a person still had to look at
        "grounded_rate": _rate(grounded, len(proposals)),  # 8
        "ungrounded_rate": _rate(len(proposals) - grounded, len(proposals)),  # 8
        "calls": len(calls),
        "failed_calls": sum(1 for e in calls if not e.get("ok")),
        "ms_per_call": _rate(elapsed, len(calls)),  # 9
        "ms_per_accepted_field": _rate(elapsed, len(accepted)),  # 9
        "learning_curve": curve,  # 10
    }


def inter_model_agreement(events: list[dict[str, Any]]) -> dict[str, Any]:
    """5. Where two models proposed a value for the same field of the same record, how often they matched."""
    slots: dict[tuple[str, str, str], dict[str, str]] = defaultdict(dict)
    for e in events:
        if e["kind"] == PROPOSED and e.get("model"):
            slots[(e.get("build_id", ""), e.get("record_id", ""), e.get("field", ""))][e["model"]] = _key(e.get("value"))
    pairs = {slot: models for slot, models in slots.items() if len(models) >= 2}
    agreed = sum(1 for models in pairs.values() if len(set(models.values())) == 1)
    return {"compared": len(pairs), "agreement": _rate(agreed, len(pairs))}


def unresolved_remaining(records: list[dict[str, Any]]) -> int:
    """10. Fields still waiting for a person, across the records given."""
    return sum(
        1
        for record in records
        for info in (record.get("metadata_field_status") or {}).values()
        if isinstance(info, dict) and info.get("status") in {"unresolved", "invalid"}
    )


def compute(events: list[dict[str, Any]], records: list[dict[str, Any]] | None = None, *, build_id: str = "", run_id: str = "") -> dict[str, Any]:
    """Metrics per model (and per field within it) for whatever slice of the ledger is asked for."""
    rows = [e for e in events if (not build_id or e.get("build_id") == build_id) and (not run_id or e.get("run_id") == run_id)]
    models: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in rows:
        models[str(e.get("model") or "")].append(e)
    out: dict[str, Any] = {}
    for model, model_rows in sorted(models.items()):
        fields: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in model_rows:
            fields[str(e.get("field") or "")].append(e)
        out[model] = {**_model_metrics(model_rows), "by_field": {f: _model_metrics(r) for f, r in sorted(fields.items()) if f}}
    return {
        "models": out,
        "inter_model_agreement": inter_model_agreement(rows),
        "unresolved_remaining": unresolved_remaining(records) if records is not None else None,
        "runs": sorted({str(e.get("run_id")) for e in rows if e.get("run_id")}),
    }
