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
from datetime import datetime
from typing import Any

from .field_assertions import current_assertions, migrate_record_assertions
from .enrichment_ledger import (
    ACCEPTED,
    AUTOFILLED,
    BLIND_LABEL,
    CALL,
    CORRECTED,
    PROPOSED,
    RECHECK,
    REJECTED,
    RESUMED,
    REVIEW_EVENTS,
    SUSPENDED,
)
from .experiment_stats import cohens_kappa, two_proportion, wilson

THRESHOLDS = (0.7, 0.8, 0.9, 0.95)
LEARNING_BUCKET = 10  # reviews per point on the learning curve
IDLE_CAP_SECONDS = 120  # a longer gap between two decisions is a break, not review time


def _rate(part: int | float, whole: int | float) -> float | None:
    return round(part / whole, 4) if whole else None


def _key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)


def _seconds(row: dict[str, Any]) -> float | None:
    try:
        return datetime.fromisoformat(str(row["at"])).timestamp()
    except (KeyError, ValueError):
        return None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return round(ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2, 2)


def review_seconds(reviews: list[dict[str, Any]]) -> float | None:
    """Median active time between consecutive decisions in one build.

    Reviewer time is not recorded directly, so this is the gap between one decision and the next in
    the same build, with gaps over IDLE_CAP_SECONDS dropped as breaks. It is an estimate of time
    per decision, and one decision often settles several fields at once, so read it as an upper bound.
    """
    gaps: list[float] = []
    by_build: dict[str, list[float]] = defaultdict(list)
    for r in reviews:
        t = _seconds(r)
        if t is not None:
            by_build[str(r.get("build_id") or "")].append(t)
    for times in by_build.values():
        times.sort()
        gaps += [b - a for a, b in zip(times, times[1:]) if 0 < b - a <= IDLE_CAP_SECONDS]
    return _median(gaps)


def repeat_rate(events: list[dict[str, Any]]) -> dict[str, Any]:
    """After a person rejected or corrected a value, how often the model proposed that same value again for the same record and field."""
    turned_down: dict[tuple[str, str, str], list[tuple[float, str]]] = defaultdict(list)
    for e in events:
        if e["kind"] in (CORRECTED, REJECTED) and _seconds(e) is not None:
            turned_down[(e.get("build_id", ""), e.get("record_id", ""), e.get("field", ""))].append((_seconds(e) or 0.0, _key(e.get("value"))))
    later = repeats = 0
    for e in events:
        if e["kind"] != PROPOSED or _seconds(e) is None:
            continue
        earlier = [v for t, v in turned_down.get((e.get("build_id", ""), e.get("record_id", ""), e.get("field", "")), []) if t < (_seconds(e) or 0.0)]
        if earlier:
            later += 1
            repeats += _key(e.get("value")) in earlier
    return {"proposals_after_a_rejection": later, "repeat_rate": _rate(repeats, later)}


def _ci(successes: int, n: int) -> dict[str, Any]:
    return wilson(successes, n)


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
            "precision_ci": _ci(sum(e["kind"] == ACCEPTED for e in kept), len(kept)),
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
    autofill_ok = sum(e["kind"] == ACCEPTED for e in audited_reviews)
    checkable = [e for e in proposals if e.get("supported") is not None]
    severities: dict[str, int] = defaultdict(int)
    for e in corrected + rejected:
        severities[str(e.get("severity") or ("cleared" if e["kind"] == REJECTED else "unknown"))] += 1
    firsts = [t for t in (_seconds(e) for e in calls) if t is not None]
    useful = [t for t in (_seconds(e) for e in events if e["kind"] in (AUTOFILLED, ACCEPTED)) if t is not None]
    blind = [e for e in events if e["kind"] == BLIND_LABEL]
    blind_agreed = sum(1 for e in blind if e.get("agreed"))
    return {
        # Anchoring: how much more often people agree with the model when they can see its value than when they cannot.
        "blind_labels": len(blind),
        "blind_agreement_ci": _ci(blind_agreed, len(blind)),
        "anchoring": two_proportion(len(accepted), len(reviews), blind_agreed, len(blind)),
        "acceptance_ci": _ci(len(accepted), len(reviews)),
        "correction_severity": dict(severities),
        "substantive_error_rate": _ci(severities.get("substantive", 0), len(reviews)),
        "autofill_precision_ci": _ci(autofill_ok, len(audited_reviews)),
        "spot_checks_still_needed": max(0, round(0.1 * len(autofilled)) - len(audited_reviews)),
        "grounded_ci": _ci(grounded, len(proposals)),
        "supported_rate": _rate(sum(1 for e in checkable if e["supported"]), len(checkable)),
        "supported_checked": len(checkable),
        **repeat_rate(events),
        "review_seconds_per_decision": review_seconds(reviews),
        "seconds_to_first_useful_value": round(min(useful) - min(firsts), 1) if useful and firsts and min(useful) >= min(firsts) else None,
        "autofill_suspensions": sum(1 for e in events if e["kind"] == SUSPENDED),
        "autofill_resumptions": sum(1 for e in events if e["kind"] == RESUMED),
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


def contested_outcomes(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Where models disagreed about a field, what the person then did.

    For each model: how often its value was kept when another model had proposed something else, and
    how often the person's correction matched what another model had proposed.
    """
    proposed: dict[tuple[str, str, str], dict[str, str]] = defaultdict(dict)
    for e in events:
        if e["kind"] == PROPOSED and e.get("model"):
            proposed[(e.get("build_id", ""), e.get("record_id", ""), e.get("field", ""))][e["model"]] = _key(e.get("value"))
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"contested_reviews": 0, "kept": 0, "person_chose_other_models_value": 0})
    for e in events:
        if e["kind"] not in REVIEW_EVENTS or not e.get("model"):
            continue
        rivals = {m: v for m, v in proposed.get((e.get("build_id", ""), e.get("record_id", ""), e.get("field", "")), {}).items() if m != e["model"]}
        if not rivals or all(v == _key(e.get("value")) for v in rivals.values()):
            continue  # nobody disagreed
        row = out[e["model"]]
        row["contested_reviews"] += 1
        row["kept"] += e["kind"] == ACCEPTED
        row["person_chose_other_models_value"] += e["kind"] == CORRECTED and _key(e.get("new_value")) in rivals.values()
    return {model: {**row, "kept_rate": _rate(row["kept"], row["contested_reviews"])} for model, row in out.items()}


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
    """10. Canonical assertions still waiting for a person."""
    total = 0
    for record in records:
        migrate_record_assertions(record)
        total += sum(
            1
            for assertion in current_assertions(record)
            if (
                assertion.value_status in {"unresolved", "invalid"}
                or assertion.evaluation_status == "evaluation_failed"
                or assertion.authority_status == "disputed"
            )
        )
    return total


def compute(
    events: list[dict[str, Any]], records: list[dict[str, Any]] | None = None, *,
    build_id: str = "", run_id: str = "", arm: str = "", gold: bool | None = None, group_by: str = "",
) -> dict[str, Any]:
    """Metrics per model (and per field within it) for whatever slice of the ledger is asked for.

    `group_by` names an event column (arm, run_id, build_id, model_version, prompt_version, gold, ...)
    and adds the same per-model measures within each of its values.
    """
    rows = [
        e for e in events
        if (not build_id or e.get("build_id") == build_id) and (not run_id or e.get("run_id") == run_id)
        and (not arm or e.get("arm") == arm) and (gold is None or bool(e.get("gold")) == gold)
    ]

    def per_model(subset: list[dict[str, Any]]) -> dict[str, Any]:
        models: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in subset:
            models[str(e.get("model") or "")].append(e)
        out: dict[str, Any] = {}
        for model, model_rows in sorted(models.items()):
            fields: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for e in model_rows:
                fields[str(e.get("field") or "")].append(e)
            out[model] = {**_model_metrics(model_rows), "by_field": {f: _model_metrics(r) for f, r in sorted(fields.items()) if f}}
        return out

    seconds = [e for e in rows if e["kind"] == "second_label"] + [e for e in rows if e["kind"] == RECHECK and not e.get("same_reviewer", True)]
    second_by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in seconds:
        second_by_field[str(e.get("field") or "")].append(e)
    rechecks = [e for e in rows if e["kind"] == RECHECK and e.get("same_reviewer", True)]
    by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in rechecks:
        by_field[str(e.get("field") or "")].append(e)
    result: dict[str, Any] = {
        # Reviewer self-consistency: how often the same person, asked again without seeing their earlier answer, gives it again.
        "self_consistency": {
            **_ci(sum(1 for e in rechecks if e.get("agreed")), len(rechecks)),
            "by_field": {f: _ci(sum(1 for e in v if e.get("agreed")), len(v)) for f, v in sorted(by_field.items()) if f},
        },
        # Inter-annotator agreement: two different reviewers labelling the same field, the second not seeing the first.
        "inter_annotator": {
            **_ci(sum(1 for e in seconds if e.get("agreed")), len(seconds)),
            "kappa": cohens_kappa([_key(e.get("value")) for e in seconds], [_key(e.get("new_value")) for e in seconds]),
            "by_field": {
                f: {**_ci(sum(1 for e in v if e.get("agreed")), len(v)), "kappa": cohens_kappa([_key(e.get("value")) for e in v], [_key(e.get("new_value")) for e in v])}
                for f, v in sorted(second_by_field.items()) if f
            },
        },
        "models": per_model(rows),
        "inter_model_agreement": inter_model_agreement(rows),
        "contested": contested_outcomes(rows),
        "unresolved_remaining": unresolved_remaining(records) if records is not None else None,
        "runs": sorted({str(e.get("run_id")) for e in rows if e.get("run_id")}),
    }
    if group_by:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in rows:
            groups[str(e.get(group_by, ""))].append(e)
        result["slices"] = {"by": group_by, "groups": {key: per_model(group) for key, group in sorted(groups.items())}}
    return result
