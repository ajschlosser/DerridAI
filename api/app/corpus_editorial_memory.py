# Copyright 2026 Aaron John Schlosser, PhD.
"""Editorial memory: advisory conventions and few-shot examples drawn from human decisions.

Only human-confirmed/overridden fields become eligible conventions or examples; nothing
here is copied as truth into a record, only offered as advisory context for a later LLM
pass. Moved verbatim out of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's
module docstring for why a mixin, not free functions, and corpus_build_lifecycle.py's for
why every mixin's mypy stub block must be wrapped in `if TYPE_CHECKING:`).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from . import experiment
from .corpus_enrichment_helpers import _editorial_tokens
from .corpus_record_quality import iso_now
from .corpus_reviewer_helpers import _second_opinion_owed
from .enrichment_cycles import learn_from_pass


class EditorialMemoryMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _global_learning: Any

        def _append_warning(self, build_id: str, message: str) -> None: ...


    def _editorial_memory(self, build_id: str, current_record: dict[str, Any] | None = None, *, exclude_record_id: str = "", use_global: bool = True) -> dict[str, Any]:
        """Build advisory context from human decisions and the last enrichment pass.

        Only human-confirmed/overridden fields are eligible as conventions and few-shot
        examples. Repeated values become advisory conventions after two confirmations.
        ``pass_learning`` also includes last-pass LLM inferences on two or more records
        (working conventions, not confirmed) so a later pass can start before every
        record has been reviewed. Nothing here is copied as truth.
        """
        try:
            rows = self.repo.load_records(build_id)
            build = self.repo.get_build(build_id)
        except Exception as exc:
            # Editorial memory only supplies advisory few-shot context; records
            # are never altered by it. Proceed without it but say so on the build.
            self._append_warning(build_id, f"Editorial memory was unavailable; enrichment ran without reviewer examples ({exc}).")
            return {"conventions": {}, "examples": {}, "pass_learning": {}}
        reset_at = str(build.get("editorial_memory_reset_at") or "")
        counts: dict[str, dict[str, tuple[Any, int]]] = {}
        eligible: list[tuple[dict[str, Any], str, Any]] = []
        for row in rows:
            if exclude_record_id and str(row.get("record_id") or "") == exclude_record_id:
                continue
            if reset_at and str(row.get("human_touched_at") or "") <= reset_at:
                continue
            if experiment.is_gold(str(row.get("record_id") or "")):
                continue  # the frozen gold set is scored, never learned from
            statuses = row.get("metadata_field_status") if isinstance(row.get("metadata_field_status"), dict) else {}
            for field, info in statuses.items():
                if not isinstance(info, dict) or str(info.get("status") or "") not in {"human_confirmed", "human_override"}:
                    continue
                if _second_opinion_owed(row, field):
                    continue  # a conventions list or example must not tell a second reviewer what the first one answered
                value = row.get(field)
                if value in (None, "", []):
                    continue
                key = json.dumps(value, ensure_ascii=False, sort_keys=True)
                prior = counts.setdefault(str(field), {}).get(key)
                counts[str(field)][key] = (value, (prior[1] if prior else 0) + 1)
                if str(field) in {"discourse_role", "region_type", "primary_text", "speaker", "position_holder", "stance"}:
                    eligible.append((row, str(field), value))
        conventions: dict[str, Any] = {}
        for field, values in counts.items():
            ranked = sorted(values.values(), key=lambda item: item[1], reverse=True)
            if ranked and ranked[0][1] >= 2:
                conventions[field] = {"value": ranked[0][0], "confirmed_records": ranked[0][1]}

        current_text = str((current_record or {}).get("text") or "")
        current_tokens = _editorial_tokens(current_text)
        by_field: dict[str, list[dict[str, Any]]] = {}
        for row, field, value in eligible:
            row_tokens = _editorial_tokens(str(row.get("text") or ""))
            union = current_tokens | row_tokens
            similarity = (len(current_tokens & row_tokens) / len(union)) if union else 0.0
            # Region agreement is a useful but non-authoritative tie breaker.
            if current_record and row.get("region_type") and row.get("region_type") == current_record.get("region_type"):
                similarity += 0.08
            by_field.setdefault(field, []).append({
                "record_id": str(row.get("record_id") or ""),
                "value": value,
                "similarity": round(min(1.0, similarity), 4),
                "excerpt": re.sub(r"\s+", " ", str(row.get("text") or "")).strip()[:420],
            })
        examples: dict[str, list[dict[str, Any]]] = {}
        for field, items in by_field.items():
            ranked = sorted(items, key=lambda item: float(item.get("similarity") or 0), reverse=True)
            # Keep prompts compact. Include up to four field-specific examples;
            # zero-overlap examples are still useful only for discourse role when
            # a repeated build convention exists.
            kept = [item for item in ranked if float(item.get("similarity") or 0) > 0][:4]
            if not kept and field == "discourse_role" and conventions.get(field):
                kept = ranked[:2]
            if kept:
                examples[field] = kept
        # Conventions confirmed in other builds fill gaps only; this build's own
        # reviewers always take precedence over the shared ones.
        for field, convention in (self._global_learning.conventions(exclude_build_id=build_id).items() if use_global else []):
            conventions.setdefault(field, convention)
        return {"conventions": conventions, "examples": examples, "pass_learning": learn_from_pass([row for row in rows if str(row.get("record_id") or "") != exclude_record_id])}


    def _editorial_context(self, build_id: str, *, exclude_record_id: str = "") -> dict[str, Any]:
        # Retained as the small conventions-only API used by older internal tests;
        # new enrichment calls use _editorial_memory for retrieved examples too.
        return self._editorial_memory(build_id, None, exclude_record_id=exclude_record_id).get("conventions", {})


    def editorial_memory(self, build_id: str) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        memory = self._editorial_memory(build_id, None)
        return {
            **memory,
            "reset_at": build.get("editorial_memory_reset_at"),
            "convention_count": len(memory.get("conventions") or {}),
            "example_count": sum(len(items) for items in (memory.get("examples") or {}).values() if isinstance(items, list)),
        }


    def reset_editorial_memory(self, build_id: str) -> dict[str, Any]:
        with self._lock:
            build = self.repo.get_build(build_id)
            build["editorial_memory_reset_at"] = iso_now()
            self.repo.save_build(build)
        return self.editorial_memory(build_id)

