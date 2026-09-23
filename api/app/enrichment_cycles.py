# Copyright 2026 Aaron John Schlosser, PhD.
"""Multi-pass metadata enrichment: conflict resolution and cross-pass learning.

Why: a later enrichment pass may disagree with what an earlier pass (or the
reviewer) already settled. The rules here decide, without an LLM, whether to
replace, keep, or keep both values, and distill both reviewer decisions and
unreviewed last-pass inferences into advisory context for the next pass.
How: pure functions plus a small JSON-backed store for learning that is
generalizable across builds. Nothing here touches provider calls or records on
disk, so the rules are unit-testable in isolation.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Literal

from .experiment import is_gold

HUMAN_OWNED_STATUSES = frozenset({"human_confirmed", "human_override", "confirmed_absent"})
MAX_PASSES = 10
# A proposal at or above this confidence may replace a weaker value. It mirrors
# the profile's ``min_metadata_confidence`` auto-fill floor.
REPLACE_CONFIDENCE = 0.75
# The winner must also lead by this much, otherwise the model is too unsure to
# adjudicate between the two values and both are kept for the reviewer.
DECISION_MARGIN = 0.10
# Only fields whose values are corpus-independent conventions are shared across
# builds. Names (speaker, position holder, target) are specific to one corpus.
GENERALIZABLE_FIELDS = ("discourse_role", "region_type")
# Within one build, the next pass may also see last-pass inferences on these
# fields (including names). They stay advisory and never enter the global store.
PASS_LEARNING_FIELDS = (
    "discourse_role",
    "region_type",
    "primary_text",
    "speaker",
    "position_holder",
    "stance",
    "proposition_status",
)
PRIOR_PASS_MIN_RECORDS = 2
PRIOR_PASS_MIN_CONFIDENCE = 0.65
MAX_INFERRED_FIELDS = 8
MAX_DISPUTED_FIELDS = 8
GLOBAL_PROMOTION_MIN_BUILDS = 2
GLOBAL_PROMOTION_MIN_CONFIRMATIONS = 2

# The model's self-reported certainty about a classification. It is telemetry about
# the value, not a scholarly value, so a pass never disputes or replaces it.
CONFIDENCE_FIELDS = frozenset({"attribution_confidence", "semantic_classification_confidence"})
NUMBER_TOLERANCE = 0.05
LIST_OVERLAP = 0.6

Resolution = Literal["keep_existing", "replace", "keep_both"]


def _normalized(item: Any) -> str:
    text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
    return " ".join(text.casefold().split())


def same_value(old: Any, new: Any) -> bool:
    """True when a proposal restates the existing value closely enough that it is not a disagreement.

    Wording, case and spacing differences, a numeric wobble, and a list that shares
    most of its items are agreement. Reviewers should only see real disagreements.
    """
    if old == new:
        return True
    if isinstance(old, (int, float)) and isinstance(new, (int, float)) and not isinstance(old, bool) and not isinstance(new, bool):
        return abs(float(old) - float(new)) <= NUMBER_TOLERANCE
    if isinstance(old, str) and isinstance(new, str):
        return _normalized(old) == _normalized(new)
    if isinstance(old, list) and isinstance(new, list):
        left, right = {_normalized(item) for item in old}, {_normalized(item) for item in new}
        return bool(left | right) and len(left & right) / len(left | right) >= LIST_OVERLAP
    return False


def _confidence(info: dict[str, Any]) -> float | None:
    value = info.get("confidence")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def resolve_conflict(existing_info: dict[str, Any], new_info: dict[str, Any]) -> Resolution:
    """Decide what to do when a pass proposes a different value than the current one.

    Human-owned values always win. Otherwise the pass decides only when the
    confidences clearly separate; anything closer is left to the reviewer with
    both values retained.
    """
    if str(existing_info.get("status") or "") in HUMAN_OWNED_STATUSES:
        return "keep_existing"
    new_conf = _confidence(new_info)
    old_conf = _confidence(existing_info)
    # A value left "unresolved" only because an earlier pass disputed it still
    # carries its original confidence and must be judged against it.
    existing_settled = str(existing_info.get("status") or "") not in {"unresolved", "invalid", ""} or existing_info.get("reason_code") == "llm_disagreement"
    if new_conf is None:
        return "keep_both"
    if new_conf >= REPLACE_CONFIDENCE and (not existing_settled or old_conf is None or new_conf - old_conf >= DECISION_MARGIN):
        return "replace"
    if old_conf is not None and existing_settled and old_conf - new_conf >= DECISION_MARGIN:
        return "keep_existing"
    return "keep_both"


def learn_from_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize how reviewers treated values proposed by enrichment passes.

    Returns per-field accepted/rejected tallies and a few rejected proposals to
    show the next pass as things not to repeat. Only reviewer decisions count;
    a value nobody has looked at teaches nothing.
    """
    stats: dict[str, dict[str, int]] = {}
    rejected: dict[str, list[dict[str, Any]]] = {}

    def tally(field: str, accepted: bool, record: dict[str, Any], proposed: Any) -> None:
        bucket = stats.setdefault(field, {"accepted": 0, "rejected": 0})
        bucket["accepted" if accepted else "rejected"] += 1
        if not accepted and proposed not in (None, "", []):
            examples = rejected.setdefault(field, [])
            if len(examples) < 4:
                examples.append({
                    "record_id": str(record.get("record_id") or ""),
                    "rejected_value": proposed,
                    "chosen_value": record.get(field),
                })

    for record in records:
        if is_gold(str(record.get("record_id") or "")):
            continue  # the frozen gold set is scored, never learned from
        statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        decided: set[str] = set()
        # Values a person turned down after a model filled them in, whichever pass or build step did it.
        for turned_down in record.get("llm_rejections") or []:
            if isinstance(turned_down, dict) and turned_down.get("field"):
                field = str(turned_down["field"])
                decided.add(field)
                tally(field, False, {**record, field: turned_down.get("chosen_value")}, turned_down.get("rejected_value"))
        for dispute in record.get("metadata_disputes") or []:
            if not isinstance(dispute, dict):
                continue
            field = str(dispute.get("field") or "")
            info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
            if not field or str(info.get("status") or "") not in {"human_confirmed", "human_override"}:
                continue
            decided.add(field)
            tally(field, record.get(field) == dispute.get("proposed"), record, dispute.get("proposed"))
        for entry in record.get("metadata_enrichment_history") or []:
            for field in (entry.get("added_fields") or []) if isinstance(entry, dict) else []:
                info = statuses.get(str(field)) if isinstance(statuses.get(str(field)), dict) else {}
                status = str(info.get("status") or "")
                if field in decided or status not in {"human_confirmed", "human_override"}:
                    continue
                decided.add(field)
                tally(str(field), status == "human_confirmed", record, info.get("llm_value"))
    return {"field_stats": stats, "rejected_examples": rejected}


def learn_from_pass(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize the last enrichment pass for the next one, including unreviewed inferences.

    Reviewer decisions still win: they occupy ``field_stats`` / ``rejected_examples``.
    Values the previous pass wrote as ``model_inferred`` on two or more records, at or
    above the 65% auto-fill floor, become ``prior_pass.inferred_conventions``. Those
    are working conventions for this build only; they are not treated as confirmed
    and are omitted for any field a reviewer has already judged on any record.
    """
    learned = learn_from_review(records)
    judged = set((learned.get("field_stats") or {}).keys())
    for record in records:
        statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        for field, info in statuses.items():
            if isinstance(info, dict) and str(info.get("status") or "") in HUMAN_OWNED_STATUSES:
                judged.add(str(field))
    counts: dict[str, dict[str, dict[str, Any]]] = {}
    disputed: dict[str, int] = {}
    for record in records:
        statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        for field in PASS_LEARNING_FIELDS:
            if field in judged:
                continue
            info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
            if str(info.get("status") or "") != "model_inferred":
                continue
            confidence = info.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or float(confidence) < PRIOR_PASS_MIN_CONFIDENCE:
                continue
            value = record.get(field)
            if value in (None, "", []):
                continue
            key = json.dumps(value, ensure_ascii=False, sort_keys=True)
            bucket = counts.setdefault(field, {}).setdefault(
                key, {"value": value, "records": 0, "confidence_sum": 0.0},
            )
            bucket["records"] += 1
            bucket["confidence_sum"] += float(confidence)
        for dispute in record.get("metadata_disputes") or []:
            if not isinstance(dispute, dict):
                continue
            field = str(dispute.get("field") or "")
            if field:
                disputed[field] = disputed.get(field, 0) + 1
    inferred: list[tuple[int, str, dict[str, Any]]] = []
    for field, values in counts.items():
        best = max(values.values(), key=lambda item: (int(item["records"]), float(item["confidence_sum"])))
        if int(best["records"]) >= PRIOR_PASS_MIN_RECORDS:
            inferred.append((int(best["records"]), field, {
                "value": best["value"],
                "records": int(best["records"]),
                "mean_confidence": round(float(best["confidence_sum"]) / int(best["records"]), 3),
            }))
    inferred.sort(key=lambda item: item[0], reverse=True)
    learned["prior_pass"] = {
        "inferred_conventions": {field: payload for _, field, payload in inferred[:MAX_INFERRED_FIELDS]},
        "disputed_fields": dict(sorted(disputed.items(), key=lambda item: item[1], reverse=True)[:MAX_DISPUTED_FIELDS]),
    }
    return learned


class GlobalLearningStore:
    """Conventions confirmed independently in several builds, shared with new ones."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": 1, "observations": {}}
        return data if isinstance(data, dict) and isinstance(data.get("observations"), dict) else {"version": 1, "observations": {}}

    def observe(self, build_id: str, conventions: dict[str, Any]) -> None:
        """Record a build's local conventions; only generalizable fields are kept."""
        with self._lock:
            data = self._read()
            for field, convention in conventions.items():
                if field not in GENERALIZABLE_FIELDS or not isinstance(convention, dict):
                    continue
                key = json.dumps(convention.get("value"), ensure_ascii=False, sort_keys=True)
                entry = data["observations"].setdefault(field, {}).setdefault(key, {"value": convention.get("value"), "builds": {}})
                entry["builds"][build_id] = int(convention.get("confirmed_records") or 0)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                os.replace(tmp_name, self.path)
            finally:
                Path(tmp_name).unlink(missing_ok=True)

    def conventions(self, *, exclude_build_id: str = "") -> dict[str, Any]:
        """Return the top promoted convention per field, judged on other builds only."""
        with self._lock:
            data = self._read()
        promoted: dict[str, Any] = {}
        for field, values in data["observations"].items():
            best: tuple[int, Any] | None = None
            for entry in values.values():
                builds = {bid: n for bid, n in (entry.get("builds") or {}).items() if bid != exclude_build_id and n >= GLOBAL_PROMOTION_MIN_CONFIRMATIONS}
                if len(builds) >= GLOBAL_PROMOTION_MIN_BUILDS:
                    total = sum(builds.values())
                    if best is None or total > best[0]:
                        best = (total, entry.get("value"))
            if best is not None:
                promoted[field] = {"value": best[1], "confirmed_records": best[0], "scope": "global"}
        return promoted
