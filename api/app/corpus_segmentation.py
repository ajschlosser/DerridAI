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

"""Pure segmentation logic: windowing, boundary detection, topology, and record construction.

Deterministic candidate detection, seam-quality scoring, topology normalization/sanity
checks, and record construction from confirmed boundaries. These functions are kept
separate from PdfCorpusBuildManager so the segmentation invariants can be read and
tested without the manager's orchestration state. LLM orchestration (prompt building,
_segment, boundary adjudication) remains on the manager.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .corpus_metadata import STRONG_STRUCTURAL_METHODS
from .field_assertions import (
    create_deterministic_assertion,
    create_human_assertion,
    create_inherited_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
)
from .language_segmentation import (
    ends_quote,
    ends_sentence_text,
    looks_like_speaker_start,
    looks_like_strong_heading,
    profile_metadata,
    starts_quote,
)


def _normalize_text(value: str) -> str:
    """Normalize whitespace without destroying non-ASCII scholarly text.

    NFC keeps composed diacritics stable across PDF-native and OCR extraction
    while retaining every Unicode letter/symbol in the source.
    """
    text = unicodedata.normalize("NFC", str(value or "").replace("\u00ad", ""))
    return re.sub(r"\s+", " ", text).strip()



def _manifest_main_text_blocks(
    blocks: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    bounds_confirmed: bool = False,
) -> list[dict[str, Any]]:
    """Apply physical-page bounds only after explicit human confirmation.

    The document-manifest LLM may *suggest* ``main_text_start_page`` and
    ``main_text_end_page``, but an unreviewed suggestion is not allowed to
    destructively narrow the source topology.  A plausible-looking bad range
    can still contain many layout blocks (for example, the final three pages
    of a dense PDF), so block-count heuristics are not a sufficient safety
    guard.  Until the manifest has been explicitly confirmed, preserve every
    extracted source block and let downstream region/discourse metadata mark
    front matter, notes, bibliography, and other non-primary material.

    Once a reviewer confirms the manifest, its page bounds become an explicit
    structural decision and are honored.  Even then, an empty selection falls
    back to the full source so a typo cannot erase the document.
    """
    if not bounds_confirmed:
        return blocks
    try:
        start = int(manifest.get("main_text_start_page")) if manifest.get("main_text_start_page") is not None else None
        end = int(manifest.get("main_text_end_page")) if manifest.get("main_text_end_page") is not None else None
    except (TypeError, ValueError):
        return blocks
    if start is None and end is None:
        return blocks
    if start is not None and end is not None and start > end:
        return blocks
    selected = [
        block for block in blocks
        if (start is None or int(block.get("page") or 0) >= start)
        and (end is None or int(block.get("page") or 0) <= end)
    ]
    return selected or blocks


def _segmentation_windows(blocks: list[dict[str, Any]], token_budget: int) -> list[list[dict[str, Any]]]:
    """Create overlapping semantic-analysis windows using an approximate token budget.

    Window size is only an execution constraint. It never becomes a record
    boundary. Two source blocks are overlapped so a transition at a window
    seam can be judged in both contexts.
    """
    if not blocks:
        return []
    char_budget = max(4096, int(token_budget) * 4)
    overlap = 2
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    index = 0
    while index < len(blocks):
        block = blocks[index]
        block_chars = len(str(block.get("text") or "")) + 120
        if current and current_chars + block_chars > char_budget and len(current) >= 4:
            windows.append(current)
            carry = current[-overlap:] if len(current) > overlap else list(current)
            current = list(carry)
            current_chars = sum(len(str(item.get("text") or "")) + 120 for item in current)
            # Do not advance index; the current block still needs to be added.
            continue
        current.append(block)
        current_chars += block_chars
        index += 1
    if current:
        if windows and current == windows[-1][-len(current) :]:
            return windows
        windows.append(current)
    return windows


def _block_language(block: dict[str, Any], fallback: str | None = None) -> str | None:
    """Prefer reviewer-confirmed document-thread language over document fallback."""
    value = str(block.get("thread_language") or "").strip()
    return value or fallback


def _is_protected_transition(
    left: dict[str, Any],
    right: dict[str, Any],
    language: str | None = None,
) -> bool:
    """Return True when splitting would likely detach attribution or syntax.

    The protection layer is Unicode-aware and deliberately conservative. It
    prevents source-unit sizing and semantic classification from treating
    Western capitalization or punctuation conventions as universal.
    """
    left_text = str(left.get("text") or "").strip()
    right_text = str(right.get("text") or "").strip()
    left_language = _block_language(left, language)
    left_type = str(left.get("type") or "body").casefold()
    right_type = str(right.get("type") or "body").casefold()
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    attribution_lead = re.compile(
        r"(?:writes?|says?|asks?|replies?|continues?|according to|as .*? puts it)\s*[:;,]?\s*$",
        re.I,
    )
    list_marker = re.compile(r"^\s*(?:\d+[.)]|[-•*])\s+")
    label_text = left_text[:-1].strip() if left_text.endswith((":","：")) else ""
    speaker_label_only = bool(
        label_text
        and len(label_text) <= 60
        and any(char.isalpha() for char in label_text)
        and not ends_sentence_text(label_text, left_language)
    )

    if left_type in heading_types and right_type not in heading_types:
        return True
    if speaker_label_only:
        return True
    if (
        (left_text.endswith((":","：")) or attribution_lead.search(left_text))
        and starts_quote(right_text)
    ):
        return True
    if list_marker.match(left_text) and right_text and not ends_sentence_text(left_text, left_language):
        return True
    return False


def _deterministic_boundary_candidates(
    blocks: list[dict[str, Any]],
    profile: dict[str, Any],
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Generate structural candidates without turning length into evidence.

    0.40.9 removes the former soft-length probe. Approaching a preferred
    record size is handled later by a local best-seam search; it never earns
    an LLM call on its own.
    """
    if len(blocks) < 2:
        return []
    candidates: list[dict[str, Any]] = []
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    heading_counts = Counter(
        _normalize_text(str(block.get("text") or "")).casefold()
        for block in blocks
        if str(block.get("type") or "body").casefold() in heading_types and len(_normalize_text(str(block.get("text") or ""))) < 180
    )

    for i, (left, right) in enumerate(zip(blocks, blocks[1:])):
        left_text = str(left.get("text") or "").strip()
        right_text = str(right.get("text") or "").strip()
        signals: list[str] = []
        score = 0.0
        if _layout_region_change(left, right):
            signals.append("layout_region_change")
            score += 1.0
        left_type = str(left.get("type") or "body").casefold()
        right_type = str(right.get("type") or "body").casefold()
        left_language = _block_language(left, language)
        right_language = _block_language(right, language)
        boundary_language = right_language or left_language or language

        if (
            left_language
            and right_language
            and left_language.casefold() != right_language.casefold()
        ):
            signals.append("language_context_change")
            score += 0.40
        if right_type in heading_types:
            normalized_heading = _normalize_text(right_text).casefold()
            if normalized_heading and heading_counts.get(normalized_heading, 0) >= 3:
                signals.append("repeated_running_heading")
                score += 0.08
            else:
                signals.append("heading_start")
                score += 0.62
                if looks_like_strong_heading(right_text, right_language):
                    signals.append("strong_heading_start")
                    score += 0.36
        if left_type in heading_types and right_type not in heading_types:
            signals.append("heading_to_body")
            score += 0.20
        if looks_like_speaker_start(right_text, right_language):
            signals.append("speaker_label")
            score += 0.90
        if starts_quote(right_text) != starts_quote(left_text):
            signals.append("quotation_frame_change")
            score += 0.34
        if ends_quote(left_text) and not starts_quote(right_text):
            signals.append("quotation_exit")
            score += 0.28
        if re.match(r"^\s*(?:\d+[.)]|[-•*])\s+", right_text):
            signals.append("list_or_numbered_move")
            score += 0.18
        if not signals:
            continue
        candidates.append({
            "after_block_id": str(left.get("block_id") or ""),
            "next_block_id": str(right.get("block_id") or ""),
            "candidate_score": min(1.0, score),
            "signals": signals,
            "source": "deterministic_candidate",
            "index": i,
            "protected": _is_protected_transition(left, right, language) or "repeated_running_heading" in signals,
            "language_profile": profile_metadata(
                boundary_language,
                f"{left_text}\n{right_text}",
            ),
        })
    return candidates


def _layout_region_change(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """A reviewer-confirmed thread or separate region is a hard record boundary."""
    left_thread = str(left.get("document_thread") or "")
    right_thread = str(right.get("document_thread") or "")
    if left_thread != right_thread and (left_thread or right_thread):
        return True
    if str(left.get("layout_flow") or "") == "separate" or str(right.get("layout_flow") or "") == "separate":
        return str(left.get("layout_region_id") or "") != str(right.get("layout_region_id") or "")
    return False


def _candidate_route(candidate: dict[str, Any], profile: dict[str, Any]) -> str:
    signals = set(candidate.get("signals") or [])
    if "layout_region_change" in signals:
        return "split"
    if bool(candidate.get("protected")):
        return "keep"
    score = float(candidate.get("candidate_score") or 0.0)
    deterministic_threshold = float(profile.get("deterministic_split_threshold") or 0.92)
    llm_threshold = float(profile.get("candidate_llm_threshold") or 0.30)
    # A genuine heading start is document structure, not an inference task.
    if "strong_heading_start" in signals and score >= deterministic_threshold:
        return "split"
    if score < llm_threshold:
        return "keep"
    return "llm"


def _boundary_audit_candidates(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_ids = [str(value) for value in (left.get("source_block_ids") or []) if value]
    right_ids = [str(value) for value in (right.get("source_block_ids") or []) if value]
    # Candidate seams stay close to the current boundary.  The LLM never
    # invents a free-text cut point; deterministic code validates one of
    # these exact source-block IDs before exposing a recommendation.
    candidates = left_ids[-3:] + right_ids[:2]
    return list(dict.fromkeys(candidates))


def _apply_boundary_adjudication_to_records(
    left: dict[str, Any], right: dict[str, Any], decision: dict[str, Any], *, threshold: float,
) -> None:
    left["boundary_llm_after"] = decision
    right["boundary_llm_before"] = decision
    choice = str(decision.get("decision") or "uncertain")
    confidence = float(decision.get("confidence") or 0.0)
    if choice == "keep" and confidence >= threshold:
        # The deterministic heuristic asked for a second reader and the LLM
        # corroborated the current seam.  Remove only that heuristic flag;
        # unrelated topology/source issues remain untouched.
        for row, edge in ((left, "end"), (right, "start")):
            row["boundary_quality_issues"] = [
                item for item in (row.get("boundary_quality_issues") or [])
                if not (str(item.get("code") or "") == "boundary_suspect" and str(item.get("edge") or "") == edge)
            ]
            if not row["boundary_quality_issues"]:
                row.pop("boundary_quality_issues", None)
            if str(row.get("review_reason") or "").startswith("Possible sentence/quotation continuation"):
                row["review_reason"] = "Pending human review."
        return
    reason = str(decision.get("reason") or "Boundary second-reader review is unresolved.")
    label = "LLM recommends moving this boundary" if choice in {"move_earlier", "move_later"} else "LLM could not confidently verify this boundary"
    for row in (left, right):
        row["needs_review"] = True
        row["review_reason"] = f"Boundary review required: {label}. {reason}".strip()
        flags = list(row.get("boundary_quality_issues") or [])
        flags.append({
            "code": "llm_boundary_review",
            "edge": "end" if row is left else "start",
            "reason": reason,
            "decision": choice,
            "confidence": confidence,
            "suggested_after_block_id": decision.get("suggested_after_block_id"),
        })
        row["boundary_quality_issues"] = flags


def _record_sizing_policy(request: dict[str, Any], profile: dict[str, Any]) -> dict[str, int]:
    supplied = request.get("record_sizing") or {}
    if hasattr(supplied, "model_dump"):
        supplied = supplied.model_dump()
    if not isinstance(supplied, dict):
        supplied = {}
    preferred = int(supplied.get("preferred_record_chars") or profile.get("preferred_record_chars") or 1750)
    tolerance = int(supplied.get("record_length_tolerance") or profile.get("record_length_tolerance") or 200)
    long_limit = int(supplied.get("long_record_chars") or 0)
    absolute = int(supplied.get("absolute_record_chars") or 0)
    if not long_limit or not absolute:
        # A reviewer-supplied target must scale the exception ceilings; a fixed 3500/6000
        # made a 500-char target accept 1,500-char records as "coherent exceptions".
        custom = bool(supplied.get("preferred_record_chars")) and preferred != int(profile.get("preferred_record_chars") or 1750)
        if custom:
            long_limit = long_limit or preferred * 2
            absolute = absolute or preferred * 3
        else:
            long_limit = long_limit or int(profile.get("long_record_chars") or 3500)
            absolute = absolute or int(profile.get("absolute_record_chars") or 6000)
    # Floors mirror PdfCorpusRecordSizing; a reviewer's small target must not be silently raised.
    preferred = max(100, min(12000, preferred))
    tolerance = max(10, min(2000, tolerance))
    long_limit = max(preferred + tolerance, min(24000, long_limit))
    absolute = max(long_limit, min(48000, absolute))
    return {
        "preferred_record_chars": preferred,
        "record_length_tolerance": tolerance,
        "long_record_chars": long_limit,
        "absolute_record_chars": absolute,
    }


def _seam_quality(
    left: dict[str, Any],
    right: dict[str, Any],
    language: str | None = None,
) -> tuple[float, bool, list[str]]:
    """Score a local retrieval seam without pretending length is semantic evidence."""
    if _is_protected_transition(left, right, language):
        return -10.0, True, ["protected_transition"]
    left_text = str(left.get("text") or "").strip()
    right_text = str(right.get("text") or "").strip()
    left_language = _block_language(left, language)
    right_language = _block_language(right, language)
    left_type = str(left.get("type") or "body").casefold()
    right_type = str(right.get("type") or "body").casefold()
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    score = 0.0
    signals: list[str] = []
    if right_type in heading_types:
        score += 1.2
        signals.append("heading_start")
    if ends_sentence_text(left_text, left_language):
        score += 0.45
        signals.append("sentence_end")
    elif left_text.endswith((":","：",";","；","؛")):
        score += 0.12
        signals.append("clause_end")
    if looks_like_speaker_start(right_text, right_language):
        score += 0.85
        signals.append("speaker_start")
    if ends_quote(left_text) and not starts_quote(right_text):
        score += 0.25
        signals.append("quotation_exit")
    if left_type != right_type and right_type not in {"body", "paragraph"}:
        score += 0.18
        signals.append("layout_role_change")
    # Paragraph/source-atom seams are inherently safer than arbitrary character cuts.
    score += 0.10
    return score, False, signals



def _best_record_sizing_boundary(
    span: list[dict[str, Any]],
    policy: dict[str, int],
    language: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Find the best safe source-atom seam for soft retrieval sizing.

    Prefer a seam in the target band. If no good seam exists there, permit a
    coherent exception up to long_record_chars. The absolute ceiling is a
    safety constraint, not an ordinary target.
    """
    if len(span) < 2:
        return None, {"reason": "single_atom", "forced": False}

    preferred_chars = policy["preferred_record_chars"]
    tolerance_chars = policy["record_length_tolerance"]
    long_record_limit = policy["long_record_chars"]
    absolute_limit = policy["absolute_record_chars"]

    candidate_seams: list[dict[str, Any]] = []
    chars_before_seam = 0
    for left_block, right_block in zip(span, span[1:]):
        chars_before_seam += len(str(left_block.get("text") or "")) + 2

        # Rules below never choose an ordinary seam past the absolute ceiling.
        # Stop scoring once later seams cannot possibly be selected. This keeps
        # repeated topology normalization linear in the number of source atoms.
        if candidate_seams and chars_before_seam > absolute_limit:
            break

        quality, protected, signals = _seam_quality(left_block, right_block, language)
        candidate_seams.append(
            {
                "left": left_block,
                "right": right_block,
                "chars": chars_before_seam,
                "quality": quality,
                "protected": protected,
                "signals": signals,
            }
        )

    target_min = preferred_chars - tolerance_chars
    target_max = preferred_chars + tolerance_chars
    span_chars = sum(len(str(block.get("text") or "")) + 2 for block in span)

    # Avoid creating a tiny trailing Record merely to hit the preferred size.
    # Keep all seams only when there is no roomier alternative.
    minimum_tail_chars = preferred_chars // 4
    seams_with_roomy_tail = [
        seam
        for seam in candidate_seams
        if span_chars - seam["chars"] >= minimum_tail_chars
    ]
    if seams_with_roomy_tail:
        candidate_seams = seams_with_roomy_tail

    preferred_band_seams = [
        seam
        for seam in candidate_seams
        if target_min <= seam["chars"] <= target_max and not seam["protected"]
    ]
    if preferred_band_seams:
        best_seam = max(
            preferred_band_seams,
            key=lambda seam: (
                seam["quality"],
                -abs(seam["chars"] - preferred_chars),
            ),
        )
        if best_seam["quality"] >= 0.10:
            return best_seam["left"], {
                "reason": "preferred_band",
                "forced": False,
                "chars": best_seam["chars"],
                "quality": best_seam["quality"],
                "signals": best_seam["signals"],
            }

    # No clean target seam: let a coherent thought run longer when a stronger
    # seam appears before the configured long-record limit.
    extended_seams = [
        seam
        for seam in candidate_seams
        if target_min <= seam["chars"] <= long_record_limit and not seam["protected"]
    ]
    if extended_seams:
        best_seam = max(
            extended_seams,
            key=lambda seam: (
                seam["quality"]
                - (
                    abs(seam["chars"] - preferred_chars)
                    / max(preferred_chars, 1)
                )
                * 0.18,
                seam["quality"],
            ),
        )
        if best_seam["quality"] >= 0.30:
            return best_seam["left"], {
                "reason": "coherent_exception",
                "forced": False,
                "chars": best_seam["chars"],
                "quality": best_seam["quality"],
                "signals": best_seam["signals"],
            }

    # Once a Record exceeds the soft long-record limit, choose the strongest
    # unprotected seam that still respects the absolute safety ceiling.
    seams_before_absolute_limit = [
        seam
        for seam in candidate_seams
        if seam["chars"] <= absolute_limit and not seam["protected"]
    ]
    if seams_before_absolute_limit and span_chars > long_record_limit:
        best_seam = max(
            seams_before_absolute_limit,
            key=lambda seam: (
                seam["quality"]
                - (
                    abs(seam["chars"] - preferred_chars)
                    / max(preferred_chars, 1)
                )
                * 0.08,
                seam["quality"],
            ),
        )
        return best_seam["left"], {
            "reason": "long_record_repair",
            "forced": False,
            "chars": best_seam["chars"],
            "quality": best_seam["quality"],
            "signals": best_seam["signals"],
        }

    # A protected transition may be crossed only to enforce the absolute
    # ceiling. Prefer an unprotected seam if one exists within the ceiling.
    if span_chars > absolute_limit and candidate_seams:
        best_seam = max(
            (
                seam
                for seam in candidate_seams
                if seam["chars"] <= absolute_limit
            ),
            key=lambda seam: (
                -seam["protected"],
                seam["quality"],
                -abs(seam["chars"] - preferred_chars),
            ),
            default=None,
        )
        oversized_source_unit = best_seam is None
        if oversized_source_unit:
            # The first source unit itself exceeds the ceiling. Source units
            # are indivisible, so isolate that unit instead of swallowing the
            # rest of the document into the same oversized Record.
            best_seam = candidate_seams[0]
        return best_seam["left"], {
            "reason": "absolute_safety",
            "forced": bool(best_seam["protected"]),
            "chars": best_seam["chars"],
            "quality": best_seam["quality"],
            "signals": best_seam["signals"],
            "oversize_unit": oversized_source_unit,
        }

    return None, {"reason": "coherent_exception", "forced": False}


def _normalize_topology(
    blocks: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    policy: dict[str, int],
    language: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Add retrieval-size boundaries without removing semantic boundaries.

    The work list contains only groups that can still need splitting. After a
    split, only its two children are reconsidered, which avoids rescanning the
    whole document after every new boundary.
    """
    block_index_by_id = {
        str(block.get("block_id") or ""): index
        for index, block in enumerate(blocks)
    }
    boundary_by_block_id: dict[str, dict[str, Any]] = {}
    for boundary in boundaries:
        normalized_boundary = dict(boundary)
        normalized_boundary.setdefault("semantic_boundary", True)
        normalized_boundary.setdefault("boundary_kind", "semantic")
        boundary_by_block_id[
            str(normalized_boundary.get("after_block_id") or "")
        ] = normalized_boundary

    review_findings: list[dict[str, Any]] = []
    metrics = {
        "size_optimized_splits": 0,
        "long_exception_records": 0,
        "absolute_safety_splits": 0,
    }
    language_profile = profile_metadata(
        language,
        "\n".join(str(block.get("text") or "") for block in blocks[:8]),
    )

    def current_groups() -> list[list[dict[str, Any]]]:
        """Materialize Records implied by the current boundary map."""
        groups: list[list[dict[str, Any]]] = []
        current_group: list[dict[str, Any]] = []
        for block in blocks:
            current_group.append(block)
            if str(block.get("block_id") or "") in boundary_by_block_id:
                groups.append(current_group)
                current_group = []
        if current_group:
            groups.append(current_group)
        return groups

    # A split cannot affect a different group. Requeue only the two children,
    # rather than restarting at the first group (the former quadratic path).
    pending_groups = list(reversed(current_groups()))
    remaining_split_budget = max(10, len(blocks) * 2)
    preferred_max = (
        policy["preferred_record_chars"] + policy["record_length_tolerance"]
    )

    while pending_groups and remaining_split_budget > 0:
        span = pending_groups.pop()
        span_chars = (
            sum(len(str(block.get("text") or "")) for block in span)
            + max(0, len(span) - 1) * 2
        )
        if span_chars <= preferred_max:
            continue

        boundary_block, decision = _best_record_sizing_boundary(
            span,
            policy,
            language,
        )
        if boundary_block is None:
            continue

        boundary_block_id = str(boundary_block.get("block_id") or "")
        if (
            not boundary_block_id
            or boundary_block_id in boundary_by_block_id
            or boundary_block_id == str(span[-1].get("block_id") or "")
        ):
            continue

        remaining_split_budget -= 1
        boundary_kind = "retrieval_size_optimized"
        if decision.get("reason") == "absolute_safety":
            boundary_kind = "absolute_size_safety"
            metrics["absolute_safety_splits"] += 1
        else:
            metrics["size_optimized_splits"] += 1

        boundary_by_block_id[boundary_block_id] = {
            "after_block_id": boundary_block_id,
            "decision": "split",
            "confidence": 1.0,
            "changes": [],
            "source": "deterministic_topology_normalizer",
            "boundary_kind": boundary_kind,
            "semantic_boundary": False,
            "size_policy": dict(policy),
            "size_decision": decision,
            "language_profile": language_profile,
        }

        if decision.get("forced"):
            block_index = block_index_by_id.get(boundary_block_id, -1)
            next_block_id = (
                str(blocks[block_index + 1].get("block_id") or "")
                if 0 <= block_index < len(blocks) - 1
                else ""
            )
            review_findings.append(
                {
                    "after_block_id": boundary_block_id,
                    "next_block_id": next_block_id,
                    "kind": "forced_protected_absolute_split",
                    "reason": (
                        "The absolute record-size safety ceiling required a split "
                        "through an attribution/syntax-protected transition."
                    ),
                }
            )

        split_index = next(
            index
            for index, block in enumerate(span)
            if str(block.get("block_id") or "") == boundary_block_id
        )
        pending_groups.append(span[split_index + 1 :])
        pending_groups.append(span[: split_index + 1])

    # Count final long exceptions once. Counting inside the work loop would
    # count the same surviving group again each time a sibling is split.
    metrics["long_exception_records"] = sum(
        1
        for span in current_groups()
        if (
            sum(len(str(block.get("text") or "")) for block in span)
            + max(0, len(span) - 1) * 2
        )
        > policy["long_record_chars"]
    )

    ordered_boundaries = sorted(
        boundary_by_block_id.values(),
        key=lambda boundary: block_index_by_id.get(
            str(boundary.get("after_block_id") or ""),
            10**9,
        ),
    )
    return ordered_boundaries, review_findings, metrics


def _percentile(values: list[int], percentile: float) -> int:
    """Return a linearly interpolated integer percentile for Record sizes."""
    if not values:
        return 0

    ordered_values = sorted(values)
    clamped_percentile = max(0.0, min(1.0, percentile))
    position = (len(ordered_values) - 1) * clamped_percentile
    lower_index = int(position)
    upper_index = min(len(ordered_values) - 1, lower_index + 1)

    if lower_index == upper_index:
        return ordered_values[lower_index]

    upper_fraction = position - lower_index
    lower_fraction = 1 - upper_fraction
    return int(
        round(
            ordered_values[lower_index] * lower_fraction
            + ordered_values[upper_index] * upper_fraction
        )
    )


def _topology_sanity(
    records: list[dict[str, Any]],
    policy: dict[str, int],
    source_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate Record sizing and source-block conservation invariants."""
    record_sizes = [
        int(record.get("text_length") or len(str(record.get("text") or "")))
        for record in records
    ]
    findings: list[dict[str, Any]] = []

    def add_finding(
        code: str,
        severity: str,
        *,
        record_id: str | None = None,
        auto_repairable: bool = False,
        **params: Any,
    ) -> None:
        findings.append(
            {
                "code": code,
                "severity": severity,
                "record_id": record_id,
                "auto_repairable": auto_repairable,
                "params": params,
            }
        )

    if not records:
        add_finding("topology.no_records", "error")

    preferred_max = (
        policy["preferred_record_chars"] + policy["record_length_tolerance"]
    )
    for record, size in zip(records, record_sizes):
        record_id = str(record.get("record_id") or "")
        if size <= 0:
            add_finding("topology.empty_record", "error", record_id=record_id)

        if size > policy["absolute_record_chars"]:
            add_finding(
                "topology.over_absolute_limit",
                "warning",
                record_id=record_id,
                chars=size,
                limit=policy["absolute_record_chars"],
            )
        elif size > policy["long_record_chars"]:
            add_finding(
                "topology.long_exception",
                "warning",
                record_id=record_id,
                chars=size,
                limit=policy["long_record_chars"],
            )
        elif size > preferred_max:
            add_finding(
                "topology.over_preferred_range",
                "info",
                record_id=record_id,
                chars=size,
                preferred=policy["preferred_record_chars"],
            )

        if 0 < size < 180:
            add_finding(
                "topology.micro_record",
                "warning",
                record_id=record_id,
                chars=size,
                auto_repairable=True,
            )

    # Source-block IDs are the deterministic conservation check: every source
    # atom in scope must appear once, and in the same order, across Records.
    source_block_ids = [
        str(block.get("block_id") or "")
        for block in (source_blocks or [])
    ]
    used_block_ids = [
        str(block_id)
        for record in records
        for block_id in (record.get("source_block_ids") or [])
    ]
    if source_block_ids:
        source_id_set = set(source_block_ids)
        used_id_set = set(used_block_ids)

        missing_block_ids = [
            block_id for block_id in source_block_ids if block_id not in used_id_set
        ]
        duplicate_block_ids = [
            block_id
            for block_id, count in Counter(used_block_ids).items()
            if count > 1
        ]
        if missing_block_ids:
            add_finding(
                "topology.source_gap",
                "error",
                count=len(missing_block_ids),
                block_ids=missing_block_ids[:50],
            )
        if duplicate_block_ids:
            add_finding(
                "topology.source_overlap",
                "error",
                count=len(duplicate_block_ids),
                block_ids=duplicate_block_ids[:50],
            )

        used_ids_in_source = [
            block_id for block_id in used_block_ids if block_id in source_id_set
        ]
        expected_used_order = [
            block_id for block_id in source_block_ids if block_id in used_id_set
        ]
        if used_ids_in_source != expected_used_order:
            add_finding("topology.source_order", "error")

    blocking_findings = [
        finding for finding in findings if finding["severity"] == "error"
    ]
    preferred_min = (
        policy["preferred_record_chars"] - policy["record_length_tolerance"]
    )

    return {
        "valid": not blocking_findings,
        "issues": [finding["code"] for finding in blocking_findings],
        "findings": findings,
        "record_count": len(records),
        "max_record_chars": max(record_sizes, default=0),
        "min_record_chars": min(record_sizes, default=0),
        "median_record_chars": _percentile(record_sizes, 0.5),
        "p10_record_chars": _percentile(record_sizes, 0.1),
        "p90_record_chars": _percentile(record_sizes, 0.9),
        "preferred_record_chars": policy["preferred_record_chars"],
        "record_length_tolerance": policy["record_length_tolerance"],
        "long_record_chars": policy["long_record_chars"],
        "absolute_record_chars": policy["absolute_record_chars"],
        "records_in_preferred_range": sum(
            1
            for size in record_sizes
            if preferred_min <= size <= preferred_max
        ),
        "records_over_preferred_range": sum(
            1 for size in record_sizes if size > preferred_max
        ),
        "records_over_long_limit": sum(
            1
            for size in record_sizes
            if size > policy["long_record_chars"]
        ),
        "micro_record_count": sum(
            1 for size in record_sizes if 0 < size < 180
        ),
    }

def _topology_quality_report(records:list[dict[str,Any]], source_blocks:list[dict[str,Any]], policy:dict[str,int], validation:dict[str,Any]) -> dict[str,Any]:
    source_ids=[str(b.get("block_id") or "") for b in source_blocks]
    used=[str(x) for r in records for x in (r.get("source_block_ids") or [])]
    covered=len(set(source_ids)&set(used))
    return {
        "source_block_count":len(source_ids),
        "used_source_block_count":len(set(used)),
        "source_coverage":covered/len(source_ids) if source_ids else 1.0,
        "source_order_valid":not any(f.get("code")=="topology.source_order" for f in validation.get("findings",[])),
        "source_conservation_valid":not any(f.get("code") in {"topology.source_gap","topology.source_overlap"} for f in validation.get("findings",[])),
        "record_count":len(records),
        "median_record_chars":validation.get("median_record_chars",0),
        "p10_record_chars":validation.get("p10_record_chars",0),
        "p90_record_chars":validation.get("p90_record_chars",0),
        "max_record_chars":validation.get("max_record_chars",0),
        "records_in_preferred_range":validation.get("records_in_preferred_range",0),
        "records_over_preferred_range":validation.get("records_over_preferred_range",0),
        "records_over_long_limit":validation.get("records_over_long_limit",0),
        "micro_record_count":validation.get("micro_record_count",0),
        "policy":dict(policy),
        "valid":bool(validation.get("valid")),
    }


def _best_safety_boundary(
    span: list[dict[str, Any]],
    hard_max: int,
    language: str | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    """Choose the strongest safe seam near the preferred size target."""
    target = hard_max * 0.72
    cumulative = 0
    scored = []
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    for left, right in zip(span, span[1:]):
        cumulative += len(str(left.get("text") or ""))
        distance = abs(cumulative - target) / max(target, 1)
        structural = 0.0
        if str(right.get("type") or "body").casefold() in heading_types:
            structural += 1.0
        right_language = _block_language(right, language)
        left_language = _block_language(left, language)
        if looks_like_speaker_start(str(right.get("text") or ""), right_language):
            structural += 0.8
        if ends_sentence_text(str(left.get("text") or "").strip(), left_language):
            structural += 0.25
        if ends_quote(str(left.get("text") or "").strip()):
            structural += 0.15
        protected = _is_protected_transition(left, right, language)
        score = structural - (distance * 0.55) - (3.0 if protected else 0.0)
        scored.append((score, not protected, left))
    if not scored:
        return None, False
    safe = [item for item in scored if item[1]]
    if safe:
        return max(safe, key=lambda x: x[0])[2], False
    # Extremely unusual: every seam is protected. Force the least-bad seam and
    # surface exactly this demonstrated provenance hazard for human review.
    return max(scored, key=lambda x: x[0])[2], True


def _scholarly_page_range(group: list[dict[str, Any]]) -> tuple[int | str | None, int | str | None]:
    printed_labels = [str(block.get("printed_page_label") or "").strip() for block in group]
    printed_labels = [label for label in printed_labels if label]
    numeric_labels = [int(label) for label in printed_labels if label.isdigit()]
    if numeric_labels:
        return min(numeric_labels), max(numeric_labels)
    if printed_labels:
        return printed_labels[0], printed_labels[-1]
    # Physical PDF pages are never silently substituted for scholarly page
    # labels. They remain available separately in `pdf_pages`.
    return None, None


def page_record_boundaries(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One split at each page change, so each page is one record."""
    boundaries: list[dict[str, Any]] = []
    for block, nxt in zip(blocks, blocks[1:]):
        if block.get("page") == nxt.get("page"):
            continue
        boundaries.append({
            "after_block_id": block["block_id"],
            "decision": "split",
            "confidence": 1.0,
            "changes": [],
            "source": "word_count_page",
            "boundary_kind": "page",
            "semantic_boundary": False,
        })
    return boundaries


def source_unit_record_boundaries(
    blocks: list[dict[str, Any]], source_units_per_record: int
) -> list[dict[str, Any]]:
    """Split deterministically after each fixed-size SourceUnit group."""
    group_size = max(1, int(source_units_per_record or 1))
    boundaries: list[dict[str, Any]] = []
    for index, block in enumerate(blocks[:-1], 1):
        if index % group_size:
            continue
        boundaries.append({
            "after_block_id": block["block_id"],
            "decision": "split",
            "confidence": 1.0,
            "changes": [],
            "source": "source_unit_policy",
            "boundary_kind": "source_unit_group",
            "semantic_boundary": False,
        })
    return boundaries


def _construct_records(asset: dict[str, Any], blocks: list[dict[str, Any]], boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_map = {item["after_block_id"]: item for item in boundaries}
    voice_assignments = asset.get("voice_assignments")
    voice_assignments = voice_assignments if isinstance(voice_assignments, dict) else {}
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for block in blocks:
        current.append(block)
        if block["block_id"] in boundary_map:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    records: list[dict[str, Any]] = []
    prefix = re.sub(r"[^a-z0-9]+", "-", Path(asset["filename"]).stem.casefold()).strip("-")[:28] or "pdf"
    for index, group in enumerate(groups, 1):
        text = "\n\n".join(block["text"].strip() for block in group if block.get("text", "").strip())
        audio = asset.get("media_kind") == "audio" or any(block.get("locator_kind") == "time" for block in group)
        pages = [] if audio else sorted({int(block["page"]) for block in group})
        page_start, page_end = (None, None) if audio else _scholarly_page_range(group)
        last_id = group[-1]["block_id"]
        boundary = boundary_map.get(last_id)
        layout_regions = [str(block.get("deterministic_region_type") or "") for block in group if block.get("deterministic_region_type")]
        layout_region = layout_regions[0] if layout_regions and len(set(layout_regions)) == 1 else None
        thread_languages = sorted({str(block.get("thread_language") or "").strip() for block in group if str(block.get("thread_language") or "").strip()})
        speakers = [str(block.get("speaker") or "").strip() for block in group if str(block.get("speaker") or "").strip()]
        uniform_voice = speakers[0] if speakers and len(set(speakers)) == 1 and (not audio or len(speakers) == len(group)) else None
        assigned = voice_assignments.get(uniform_voice) if uniform_voice else None
        assigned_name = str(assigned.get("display_name") or "").strip() if isinstance(assigned, dict) else ""
        assigned_reviewer = str(assigned.get("reviewer") or "").strip() if isinstance(assigned, dict) else ""
        uniform_speaker = assigned_name or uniform_voice
        source_spans = []
        for block in group:
            span = {"source_document_id": asset["asset_id"], "source_unit_id": block["block_id"], "block_id": block["block_id"], "page": block.get("page"), "printed_page_label": block.get("printed_page_label"), "bbox": block.get("bbox"), "extraction_method": block.get("extraction_method"), "confidence": block.get("confidence")}
            if block.get("speaker"):
                span["speaker"] = block.get("speaker")
                assignment = voice_assignments.get(str(block.get("speaker")))
                if isinstance(assignment, dict) and str(assignment.get("display_name") or "").strip():
                    span["resolved_speaker"] = str(assignment["display_name"]).strip()
            if block.get("start") is not None:
                span["start"] = block.get("start")
                span["end"] = block.get("end")
            if audio:
                for key in ("page", "printed_page_label", "bbox"):
                    span.pop(key, None)
                span["locator_kind"] = "time"
            source_spans.append(span)
        record = {
            "record_id": f"{prefix}-{index:05d}",
            "record_revision": 1,
            **({"media_kind": "audio", "source_extracted_text": text} if audio else {}),
            "text": text,
            "text_length": len(text),
            "page_start": page_start,
            "page_end": page_end,
            "pdf_file": asset["filename"],
            "pdf_pages": pages,
            "source_document_id": asset["asset_id"],
            "source_asset_id": asset["asset_id"],
            "source_unit_ids": [block["block_id"] for block in group],
            "source_block_ids": [block["block_id"] for block in group],
            "source_spans": source_spans,
            "boundary_evidence": boundary,
            "metadata_evidence": {},
            **({"region_language": thread_languages, "region_is_multilingual": len(thread_languages) > 1} if thread_languages else {}),
            "needs_review": False,
            "review_reason": "",
            "accepted": False,
            "updates": [],
        }
        if layout_region:
            create_deterministic_assertion(
                record,
                "region_type",
                layout_region,
                method="human_document_layout",
                reason="Derived from reviewer-confirmed document structure and pagination.",
                confidence=0.99,
            )
            create_deterministic_assertion(
                record,
                "primary_text",
                layout_region == "main_text",
                method="human_document_layout",
                reason="Derived from reviewer-confirmed document structure and pagination.",
                confidence=0.99,
            )
        if uniform_speaker:
            if assigned_name:
                # A reviewer naming a diarized voice is an authority event, not a
                # deterministic inference. Preserve the machine voice ID on the
                # SourceSpan while making the reviewed identity authoritative for
                # record-level metadata and later enrichment.
                create_human_assertion(
                    record,
                    "speaker",
                    uniform_speaker,
                    override=True,
                    actor=assigned_reviewer or None,
                    method="human_voice_assignment",
                    reason=f"Reviewer assigned the diarized voice {uniform_voice}.",
                )
            else:
                create_deterministic_assertion(
                    record,
                    "speaker",
                    uniform_speaker,
                    method="source_span_speaker",
                    reason="Speaker label assigned when the source was loaded.",
                    confidence=0.95,
                )
        project_record_assertions(record)
        records.append(record)
    return records


def _mark_segmentation_review(records: list[dict[str, Any]], unresolved: list[dict[str, Any]]) -> None:
    """Attach boundary-review context without turning records into failures.

    Segmentation uncertainty belongs to a transition, not to both neighboring
    records.  Records remain independently reviewable for metadata problems;
    boundary review is represented on the adjacent record edges only.
    """
    if not unresolved:
        return
    by_block: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for block_id in record.get("source_block_ids") or []:
            by_block.setdefault(str(block_id), []).append(record)
    for item in unresolved:
        left_records = by_block.get(str(item.get("after_block_id") or ""), [])
        right_records = by_block.get(str(item.get("next_block_id") or ""), [])
        for record in left_records:
            record.setdefault("boundary_review_after", []).append(item)
        for record in right_records:
            record.setdefault("boundary_review_before", []).append(item)


def _apply_manifest_metadata(record: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Apply reviewed manifest metadata without overriding canonical human decisions."""
    migrate_record_assertions(record)

    def assertion_for(field: str):
        return current_assertion_by_name(record, field)

    def human_owned(field: str) -> bool:
        assertion = assertion_for(field)
        return bool(assertion and assertion.authority_status in {"human_confirmed", "human_override"})

    origin_labels = {"nlp_derived": "NLP-derived", "computed": "computed from an exact pattern"}
    applied_at_ingest = (
        (manifest.get("deterministic_ingest") or {}).get("applied")
        if isinstance(manifest.get("deterministic_ingest"), dict) else None
    ) or {}

    reviewer_supplied = manifest.get("reviewer_supplied") if isinstance(manifest.get("reviewer_supplied"), dict) else {}

    def origin_note(key: str | None, value: Any) -> str:
        """Say where an inherited value first came from when a tagger or pattern proposed it.

        Only while the manifest still holds the value the ingest proposed: a value a reviewer
        edited is theirs and carries no automatic origin.
        """
        if key and key in reviewer_supplied and str(reviewer_supplied[key]) == str(value):
            return " Origin: supplied by the reviewer before segmentation because it was not detected in the source."
        info = applied_at_ingest.get(key or "") if key else None
        if not isinstance(info, dict) or str(info.get("value")) != str(value):
            return ""
        label = origin_labels.get(str(info.get("derivation") or ""))
        if not label:
            return ""
        return f" Origin: {label} ({info.get('method')}, {round(float(info.get('confidence') or 0) * 100)}% confidence)."

    def inherited(field: str, value: Any, manifest_key: str | None = None) -> None:
        if value in (None, "", []):
            return
        assertion = assertion_for(field)
        if human_owned(field):
            return
        if field == "speaker" and assertion is not None and assertion.method == "source_span_speaker":
            return
        create_inherited_assertion(
            record,
            field,
            value,
            method="document_manifest",
            reason="Inherited from the reviewed document manifest." + origin_note(manifest_key, value),
        )

    work_wide = manifest.get("work_metadata") if isinstance(manifest.get("work_metadata"), dict) else {}
    for name, value in work_wide.items():
        if value in (None, "", []):
            continue
        if human_owned(name):
            continue
        create_inherited_assertion(
            record,
            str(name),
            value,
            method="document_manifest",
            reason="Supplied by the reviewer for the work as a whole, before segmentation.",
        )

    title = manifest.get("title")
    author = manifest.get("document_author")
    translator = manifest.get("translator")
    edition = manifest.get("edition") or manifest.get("publisher")
    year = manifest.get("publication_year")
    language = manifest.get("language")
    original_language = manifest.get("original_language")
    if title:
        inherited("work", title, "title")
        inherited("document_title", title, "title")
        inherited(
            "canonical_work_id",
            re.sub(r"[^a-z0-9]+", "-", str(title).casefold()).strip("-")[:120],
        )
    inherited("short_title", manifest.get("short_title"))
    inherited("original_title", manifest.get("original_title"))
    inherited("document_author", author, "document_author")
    inherited("speaker", manifest.get("speaker"))
    inherited("translator", translator, "translator")
    inherited("edition", edition)
    inherited("publisher", manifest.get("publisher"), "publisher")
    inherited("publication_place", manifest.get("publication_place"), "publication_place")
    inherited("isbn", manifest.get("isbn"), "isbn")
    if year is not None:
        try:
            parsed_year = int(year)
            inherited("year", parsed_year, "publication_year")
            inherited("publication_year", parsed_year, "publication_year")
        except (TypeError, ValueError):
            inherited("publication_year", year)
    if language:
        inherited("document_language", [str(language)])
        inherited("language", str(language))
    if original_language:
        inherited("original_language", [str(original_language)])
    if manifest.get("document_is_translation") is not None:
        inherited("document_is_translation", bool(manifest.get("document_is_translation")))

    start_page = manifest.get("main_text_start_page")
    end_page = manifest.get("main_text_end_page")
    pdf_pages = [int(value) for value in record.get("pdf_pages") or [] if isinstance(value, int)]
    if pdf_pages and isinstance(start_page, int):
        inside = min(pdf_pages) >= start_page and (
            not isinstance(end_page, int) or max(pdf_pages) <= end_page
        )
        primary_assertion = assertion_for("primary_text")
        region_assertion = assertion_for("region_type")
        primary_structure_owned = bool(
            primary_assertion and primary_assertion.method in STRONG_STRUCTURAL_METHODS
        )
        region_structure_owned = bool(
            region_assertion and region_assertion.method in STRONG_STRUCTURAL_METHODS
        )

        if not human_owned("primary_text") and not primary_structure_owned:
            create_deterministic_assertion(
                record,
                "primary_text",
                inside,
                method="manifest_page_range",
                reason="Classified from the reviewed document main-text page range.",
            )
        if not human_owned("region_type") and not region_structure_owned:
            if inside:
                inferred_region = "main_text"
                region_reason = "Record lies entirely inside the reviewed main-text page range."
            elif max(pdf_pages) < start_page:
                inferred_region = "front_matter"
                region_reason = "Record lies before the reviewed main-text page range."
            elif isinstance(end_page, int) and min(pdf_pages) > end_page:
                inferred_region = "back_matter"
                region_reason = "Record lies after the reviewed main-text page range."
            else:
                inferred_region = None
                region_reason = ""
            if inferred_region:
                create_deterministic_assertion(
                    record,
                    "region_type",
                    inferred_region,
                    method="manifest_page_range",
                    reason=region_reason,
                )

        issues = [
            item
            for item in record.get("boundary_quality_issues") or []
            if not (isinstance(item, dict) and item.get("code") == "main_text_start_straddle")
        ]
        if min(pdf_pages) < start_page <= max(pdf_pages) and not human_owned("region_type"):
            reason = (
                f"This record starts before the main text (PDF page {start_page}) and continues into it. "
                "Choose main text, front matter, or split it."
            )
            issues.append({"code": "main_text_start_straddle", "edge": "record", "reason": reason})
            record["needs_review"] = True
            if not record.get("review_reason") or str(record.get("review_reason")).lower() == "pending human review.":
                record["review_reason"] = reason
        if (
            not any(
                isinstance(item, dict) and item.get("code") == "main_text_start_straddle"
                for item in issues
            )
            and str(record.get("review_reason") or "").endswith(
                "Choose main text, front matter, or split it."
            )
        ):
            record["review_reason"] = ""
            record["needs_review"] = bool(issues)
        if issues or record.get("boundary_quality_issues"):
            record["boundary_quality_issues"] = issues

        strong_main_text = (
            (region_structure_owned and record.get("region_type") == "main_text")
            or (primary_structure_owned and record.get("primary_text") is True)
        )
        if not inside and not strong_main_text and not human_owned("discourse_role"):
            create_deterministic_assertion(
                record,
                "discourse_role",
                "paratext",
                method="manifest_page_range",
                reason=(
                    "Non-primary material is deterministically classified as paratext "
                    "unless a reviewer overrides it."
                ),
            )

    confidences = [
        float(span.get("confidence"))
        for span in record.get("source_spans") or []
        if isinstance(span, dict) and isinstance(span.get("confidence"), (int, float))
    ]
    if confidences:
        record["extraction_quality"] = round(sum(confidences) / len(confidences), 4)
    project_record_assertions(record)
