# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure segmentation logic: windowing, boundary detection, topology, and record construction.

Deterministic candidate detection, seam-quality scoring, topology normalization/sanity
checks, and record construction from confirmed boundaries. Moved verbatim out of
PdfCorpusBuildManager (see PROGRESS.md); the LLM-orchestrating methods that call these
(prompt building, _segment, boundary adjudication via the model) stay on the manager.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .corpus_metadata import STRONG_STRUCTURAL_METHODS


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
        if windows and current == windows[-1][-len(current):]:
            return windows
        windows.append(current)
    return windows


def _is_protected_transition(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Return True when splitting would likely detach attribution or syntax.

    These guards are deliberately cheap and deterministic. They prevent the
    classifier and hard-size fallback from creating common provenance errors
    such as separating a speaker label or quotation lead-in from its speech.
    """
    left_text = str(left.get("text") or "").strip()
    right_text = str(right.get("text") or "").strip()
    left_type = str(left.get("type") or "body").casefold()
    right_type = str(right.get("type") or "body").casefold()
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    speaker_label_only = re.compile(r"^\s*(?:[A-Z][A-Z .'-]{1,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*:\s*$")
    quote_start = re.compile(r'^\s*[“\"]')
    attribution_lead = re.compile(r"(?:writes?|says?|asks?|replies?|continues?|according to|as .*? puts it)\s*[:;,]?\s*$", re.I)
    list_marker = re.compile(r"^\s*(?:\d+[.)]|[-•*])\s+")

    if left_type in heading_types and right_type not in heading_types:
        return True
    if speaker_label_only.match(left_text):
        return True
    if (left_text.endswith(":") or attribution_lead.search(left_text)) and quote_start.search(right_text):
        return True
    if list_marker.match(left_text) and right_text and not re.search(r"[.!?][”\"]?$", left_text):
        return True
    return False


def _deterministic_boundary_candidates(blocks: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate structural candidates without turning length into evidence.

    0.40.9 removes the former soft-length probe. Approaching a preferred
    record size is handled later by a local best-seam search; it never earns
    an LLM call on its own.
    """
    if len(blocks) < 2:
        return []
    candidates: list[dict[str, Any]] = []
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    speaker_re = re.compile(r"^\s*(?:[A-Z][A-Z .'-]{1,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*:\s+")
    quote_start_re = re.compile(r'^\s*[“\"]')
    quote_end_re = re.compile(r'[”\"]\s*$')
    strong_heading_re = re.compile(r"^\s*(?:§|chapter|part|session|section|book|introduction|preface|foreword|conclusion|epilogue|notes|bibliography|works cited)\b|^\s*(?:[IVXLCDM]+|\d+)\s*[.:—-]\s+", re.I)
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
        left_type = str(left.get("type") or "body").casefold()
        right_type = str(right.get("type") or "body").casefold()

        if right_type in heading_types:
            normalized_heading = _normalize_text(right_text).casefold()
            if normalized_heading and heading_counts.get(normalized_heading, 0) >= 3:
                signals.append("repeated_running_heading")
                score += 0.08
            else:
                signals.append("heading_start")
                score += 0.62
                if strong_heading_re.search(right_text):
                    signals.append("strong_heading_start")
                    score += 0.36
        if left_type in heading_types and right_type not in heading_types:
            signals.append("heading_to_body")
            score += 0.20
        if speaker_re.match(right_text):
            signals.append("speaker_label")
            score += 0.90
        if bool(quote_start_re.search(right_text)) != bool(quote_start_re.search(left_text)):
            signals.append("quotation_frame_change")
            score += 0.34
        if quote_end_re.search(left_text) and not quote_start_re.search(right_text):
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
            "protected": _is_protected_transition(left, right) or "repeated_running_heading" in signals,
        })
    return candidates


def _candidate_route(candidate: dict[str, Any], profile: dict[str, Any]) -> str:
    if bool(candidate.get("protected")):
        return "keep"
    signals = set(candidate.get("signals") or [])
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
    long_limit = int(supplied.get("long_record_chars") or profile.get("long_record_chars") or 3500)
    absolute = int(supplied.get("absolute_record_chars") or profile.get("absolute_record_chars") or 6000)
    preferred = max(600, min(12000, preferred))
    tolerance = max(50, min(2000, tolerance))
    long_limit = max(preferred + tolerance, min(24000, long_limit))
    absolute = max(long_limit, min(48000, absolute))
    return {
        "preferred_record_chars": preferred,
        "record_length_tolerance": tolerance,
        "long_record_chars": long_limit,
        "absolute_record_chars": absolute,
    }


def _seam_quality(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, bool, list[str]]:
    """Score a local retrieval seam without pretending length is semantic evidence."""
    if _is_protected_transition(left, right):
        return -10.0, True, ["protected_transition"]
    left_text = str(left.get("text") or "").strip()
    _ = str(right.get("text") or "").strip()
    left_type = str(left.get("type") or "body").casefold()
    right_type = str(right.get("type") or "body").casefold()
    heading_types = {"heading", "title", "subtitle", "section", "chapter"}
    score = 0.0
    signals: list[str] = []
    if right_type in heading_types:
        score += 1.2; signals.append("heading_start")
    if re.search(r'[.!?][”"]?$', left_text):
        score += 0.45; signals.append("sentence_end")
    elif re.search(r'[:;][”"]?$', left_text):
        score += 0.12; signals.append("clause_end")
    if re.match(r"^\s*(?:[A-Z][A-Z .'-]{1,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*:\s+", str(right.get("text") or "")):
        score += 0.85; signals.append("speaker_start")
    if re.search(r'[”"]\s*$', left_text) and not re.match(r'^\s*[“"]', str(right.get("text") or "")):
        score += 0.25; signals.append("quotation_exit")
    if left_type != right_type and right_type not in {"body", "paragraph"}:
        score += 0.18; signals.append("layout_role_change")
    # Paragraph/source-atom seams are inherently safer than arbitrary character cuts.
    score += 0.10
    return score, False, signals


def _best_record_sizing_boundary(
    span: list[dict[str, Any]],
    policy: dict[str, int],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Find the best safe source-atom seam for soft retrieval sizing.

    Prefer a seam in the target band. If no good seam exists there, permit a
    coherent exception up to long_record_chars. The absolute ceiling is a
    safety constraint, not an ordinary target.
    """
    if len(span) < 2:
        return None, {"reason": "single_atom", "forced": False}
    preferred = policy["preferred_record_chars"]
    tolerance = policy["record_length_tolerance"]
    long_limit = policy["long_record_chars"]
    absolute = policy["absolute_record_chars"]
    cumulative = 0
    seams: list[dict[str, Any]] = []
    for left, right in zip(span, span[1:]):
        cumulative += len(str(left.get("text") or "")) + 2
        quality, protected, signals = _seam_quality(left, right)
        seams.append({
            "left": left, "right": right, "chars": cumulative,
            "quality": quality, "protected": protected, "signals": signals,
        })
    target_low, target_high = preferred - tolerance, preferred + tolerance
    target = [x for x in seams if target_low <= x["chars"] <= target_high and not x["protected"]]
    if target:
        best=max(target,key=lambda x:(x["quality"],-abs(x["chars"]-preferred)))
        if best["quality"] >= 0.10:
            return best["left"], {"reason":"preferred_band","forced":False,"chars":best["chars"],"quality":best["quality"],"signals":best["signals"]}
    # No clean target seam: allow the thought to run longer if a stronger seam appears.
    extended=[x for x in seams if target_low <= x["chars"] <= long_limit and not x["protected"]]
    if extended:
        best=max(extended,key=lambda x:(x["quality"]-(abs(x["chars"]-preferred)/max(preferred,1))*0.18,x["quality"]))
        if best["quality"] >= 0.30:
            return best["left"], {"reason":"coherent_exception","forced":False,"chars":best["chars"],"quality":best["quality"],"signals":best["signals"]}
    # Above the long limit, prefer any safe seam before the absolute ceiling.
    before_absolute=[x for x in seams if x["chars"] <= absolute and not x["protected"]]
    if before_absolute and sum(len(str(b.get("text") or ""))+2 for b in span) > long_limit:
        best=max(before_absolute,key=lambda x:(x["quality"]-(abs(x["chars"]-preferred)/max(preferred,1))*0.08,x["quality"]))
        return best["left"], {"reason":"long_record_repair","forced":False,"chars":best["chars"],"quality":best["quality"],"signals":best["signals"]}
    # Only when the absolute ceiling is exceeded may a protected seam be forced.
    total=sum(len(str(b.get("text") or ""))+2 for b in span)
    if total > absolute and seams:
        best=max((x for x in seams if x["chars"] <= absolute),key=lambda x:(-x["protected"],x["quality"],-abs(x["chars"]-preferred)),default=None)
        if best:
            return best["left"], {"reason":"absolute_safety","forced":bool(best["protected"]),"chars":best["chars"],"quality":best["quality"],"signals":best["signals"]}
    return None, {"reason":"coherent_exception","forced":False}


def _normalize_topology(
    blocks: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    policy: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Deterministically optimize semantic topology for retrieval-sized records."""
    block_index={str(b.get("block_id") or ""):i for i,b in enumerate(blocks)}
    boundary_map={}
    for boundary in boundaries:
        item=dict(boundary)
        item.setdefault("semantic_boundary", True)
        item.setdefault("boundary_kind", "semantic")
        boundary_map[str(item.get("after_block_id") or "")]=item
    reviews: list[dict[str, Any]]=[]
    metrics={"size_optimized_splits":0,"long_exception_records":0,"absolute_safety_splits":0}

    def groups() -> list[list[dict[str, Any]]]:
        out=[]; current=[]
        for block in blocks:
            current.append(block)
            if str(block.get("block_id") or "") in boundary_map:
                out.append(current); current=[]
        if current: out.append(current)
        return out

    # Split one oversized group at a time so every new boundary immediately
    # participates in the next pass. Existing semantic boundaries are never removed.
    guard=0
    while guard < max(10,len(blocks)*2):
        guard+=1
        changed=False
        for span in groups():
            size=sum(len(str(b.get("text") or "")) for b in span)+max(0,len(span)-1)*2
            if size <= policy["preferred_record_chars"] + policy["record_length_tolerance"]:
                continue
            choice,info=_best_record_sizing_boundary(span,policy)
            if choice is None:
                if size > policy["long_record_chars"]:
                    metrics["long_exception_records"]+=1
                continue
            bid=str(choice.get("block_id") or "")
            if not bid or bid in boundary_map or bid==str(span[-1].get("block_id") or ""):
                continue
            kind="retrieval_size_optimized"
            if info.get("reason")=="absolute_safety":
                kind="absolute_size_safety"; metrics["absolute_safety_splits"]+=1
            else:
                metrics["size_optimized_splits"]+=1
            boundary_map[bid]={
                "after_block_id":bid,"decision":"split","confidence":1.0,
                "changes":[],"source":"deterministic_topology_normalizer",
                "boundary_kind":kind,"semantic_boundary":False,
                "size_policy":dict(policy),"size_decision":info,
            }
            if info.get("forced"):
                idx=block_index.get(bid,-1)
                reviews.append({
                    "after_block_id":bid,
                    "next_block_id":str(blocks[idx+1].get("block_id") or "") if 0<=idx<len(blocks)-1 else "",
                    "kind":"forced_protected_absolute_split",
                    "reason":"The absolute record-size safety ceiling required a split through an attribution/syntax-protected transition.",
                })
            changed=True
            break
        if not changed:
            break
    ordered=sorted(boundary_map.values(),key=lambda item:block_index.get(str(item.get("after_block_id") or ""),10**9))
    return ordered,reviews,metrics


def _percentile(values: list[int], percentile: float) -> int:
    if not values: return 0
    ordered=sorted(values)
    position=(len(ordered)-1)*max(0.0,min(1.0,percentile))
    lo=int(position); hi=min(len(ordered)-1,lo+1)
    if lo==hi: return ordered[lo]
    fraction=position-lo
    return int(round(ordered[lo]*(1-fraction)+ordered[hi]*fraction))


def _topology_sanity(records: list[dict[str, Any]], policy: dict[str, int], source_blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    sizes=[int(r.get("text_length") or len(str(r.get("text") or ""))) for r in records]
    findings=[]
    def add(code:str,severity:str,*,record_id:str|None=None,auto_repairable:bool=False,**params:Any)->None:
        findings.append({"code":code,"severity":severity,"record_id":record_id,"auto_repairable":auto_repairable,"params":params})
    if not records: add("topology.no_records","error")
    for record,size in zip(records,sizes):
        rid=str(record.get("record_id") or "")
        if size<=0: add("topology.empty_record","error",record_id=rid)
        if size>policy["absolute_record_chars"]: add("topology.over_absolute_limit","error",record_id=rid,chars=size,limit=policy["absolute_record_chars"])
        elif size>policy["long_record_chars"]: add("topology.long_exception","warning",record_id=rid,chars=size,limit=policy["long_record_chars"])
        elif size>policy["preferred_record_chars"]+policy["record_length_tolerance"]: add("topology.over_preferred_range","info",record_id=rid,chars=size,preferred=policy["preferred_record_chars"])
        if 0<size<180: add("topology.micro_record","warning",record_id=rid,chars=size,auto_repairable=True)
    source_ids=[str(b.get("block_id") or "") for b in (source_blocks or [])]
    used_ids=[str(x) for r in records for x in (r.get("source_block_ids") or [])]
    if source_ids:
        missing=[x for x in source_ids if x not in set(used_ids)]
        duplicates=[x for x,count in Counter(used_ids).items() if count>1]
        if missing: add("topology.source_gap","error",count=len(missing),block_ids=missing[:50])
        if duplicates: add("topology.source_overlap","error",count=len(duplicates),block_ids=duplicates[:50])
        ordered_used=[x for x in used_ids if x in set(source_ids)]
        expected=[x for x in source_ids if x in set(used_ids)]
        if ordered_used!=expected: add("topology.source_order","error")
    blocking=[f for f in findings if f["severity"]=="error"]
    return {
        "valid":not blocking,
        "issues":[f["code"] for f in blocking],
        "findings":findings,
        "record_count":len(records),
        "max_record_chars":max(sizes,default=0),
        "min_record_chars":min(sizes,default=0),
        "median_record_chars":_percentile(sizes,0.5),
        "p10_record_chars":_percentile(sizes,0.1),
        "p90_record_chars":_percentile(sizes,0.9),
        "preferred_record_chars":policy["preferred_record_chars"],
        "record_length_tolerance":policy["record_length_tolerance"],
        "long_record_chars":policy["long_record_chars"],
        "absolute_record_chars":policy["absolute_record_chars"],
        "records_in_preferred_range":sum(1 for x in sizes if policy["preferred_record_chars"]-policy["record_length_tolerance"] <= x <= policy["preferred_record_chars"]+policy["record_length_tolerance"]),
        "records_over_preferred_range":sum(1 for x in sizes if x>policy["preferred_record_chars"]+policy["record_length_tolerance"]),
        "records_over_long_limit":sum(1 for x in sizes if x>policy["long_record_chars"]),
        "micro_record_count":sum(1 for x in sizes if 0<x<180),
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


def _best_safety_boundary(span: list[dict[str, Any]], hard_max: int) -> tuple[dict[str, Any] | None, bool]:
    """Choose the strongest safe seam near the preferred size target."""
    target=hard_max*0.72
    cumulative=0
    _=max(1,sum(len(str(b.get("text") or "")) for b in span))
    scored=[]
    heading_types={"heading","title","subtitle","section","chapter"}
    speaker_re=re.compile(r"^\s*(?:[A-Z][A-Z .'-]{1,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*:\s+")
    for left, right in zip(span, span[1:]):
        cumulative+=len(str(left.get("text") or ""))
        distance=abs(cumulative-target)/max(target,1)
        structural=0.0
        if str(right.get("type") or "body").casefold() in heading_types: structural+=1.0
        if speaker_re.match(str(right.get("text") or "")): structural+=0.8
        if re.search(r'[.!?][”\"]?$',str(left.get("text") or "").strip()): structural+=0.25
        if re.search(r'[”\"]\s*$',str(left.get("text") or "").strip()): structural+=0.15
        protected=_is_protected_transition(left,right)
        score=structural-(distance*0.55)-(3.0 if protected else 0.0)
        scored.append((score,not protected,left))
    if not scored:
        return None, False
    safe=[item for item in scored if item[1]]
    if safe:
        return max(safe,key=lambda x:x[0])[2],False
    # Extremely unusual: every seam is protected. Force the least-bad seam and
    # surface exactly this demonstrated provenance hazard for human review.
    return max(scored,key=lambda x:x[0])[2],True


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


def _construct_records(asset: dict[str, Any], blocks: list[dict[str, Any]], boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_map = {item["after_block_id"]: item for item in boundaries}
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
        pages = sorted({int(block["page"]) for block in group})
        page_start, page_end = _scholarly_page_range(group)
        last_id = group[-1]["block_id"]
        boundary = boundary_map.get(last_id)
        layout_regions = [str(block.get("deterministic_region_type") or "") for block in group if block.get("deterministic_region_type")]
        layout_region = layout_regions[0] if layout_regions and len(set(layout_regions)) == 1 else None
        thread_languages = sorted({str(block.get("thread_language") or "").strip() for block in group if str(block.get("thread_language") or "").strip()})
        records.append({
            "record_id": f"{prefix}-{index:05d}",
            "record_revision": 1,
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
            "source_spans": [{"source_document_id": asset["asset_id"], "source_unit_id": block["block_id"], "block_id": block["block_id"], "page": block["page"], "printed_page_label": block.get("printed_page_label"), "bbox": block.get("bbox"), "extraction_method": block.get("extraction_method"), "confidence": block.get("confidence")} for block in group],
            "boundary_evidence": boundary,
            "metadata_evidence": {},
            **({"region_type": layout_region, "primary_text": layout_region == "main_text", "metadata_field_status": {
                "region_type": {"status": "deterministic", "method": "human_document_layout", "confidence": 0.99, "reason": "Derived from reviewer-confirmed document structure and pagination."},
                "primary_text": {"status": "deterministic", "method": "human_document_layout", "confidence": 0.99, "reason": "Derived from reviewer-confirmed document structure and pagination."},
            }} if layout_region else {}),
            **({"region_language": thread_languages, "region_is_multilingual": len(thread_languages) > 1} if thread_languages else {}),
            "needs_review": False,
            "review_reason": "",
            "accepted": False,
            "updates": [],
        })
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
    field_status = record.setdefault("metadata_field_status", {})

    def inherited(field: str, value: Any) -> None:
        if value in (None, "", []):
            return
        status = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
        if status.get("status") in {"human_confirmed", "human_override"}:
            return
        record[field] = value
        field_status[field] = {
            "status": "inherited", "method": "document_manifest", "confidence": 1.0,
            "reason": "Inherited from the reviewed document manifest.",
        }

    title = manifest.get("title")
    author = manifest.get("document_author")
    translator = manifest.get("translator")
    edition = manifest.get("edition") or manifest.get("publisher")
    year = manifest.get("publication_year")
    language = manifest.get("language")
    original_language = manifest.get("original_language")
    if title:
        inherited("work", title)
        inherited("document_title", title)
        inherited("canonical_work_id", re.sub(r"[^a-z0-9]+", "-", str(title).casefold()).strip("-")[:120])
    inherited("short_title", manifest.get("short_title"))
    inherited("original_title", manifest.get("original_title"))
    inherited("document_author", author)
    inherited("translator", translator)
    inherited("edition", edition)
    inherited("publisher", manifest.get("publisher"))
    inherited("publication_place", manifest.get("publication_place"))
    inherited("isbn", manifest.get("isbn"))
    if year is not None:
        try:
            parsed_year = int(year)
            inherited("year", parsed_year)
            inherited("publication_year", parsed_year)
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
        inside = min(pdf_pages) >= start_page and (not isinstance(end_page, int) or max(pdf_pages) <= end_page)
        primary_status = field_status.get("primary_text") if isinstance(field_status.get("primary_text"), dict) else {}
        region_status = field_status.get("region_type") if isinstance(field_status.get("region_type"), dict) else {}
        primary_method = str(primary_status.get("method") or "")
        region_method = str(region_status.get("method") or "")
        primary_structure_owned = primary_method in STRONG_STRUCTURAL_METHODS
        region_structure_owned = region_method in STRONG_STRUCTURAL_METHODS
        if primary_status.get("status") not in {"human_confirmed", "human_override"} and not primary_structure_owned:
            record["primary_text"] = inside
            field_status["primary_text"] = {
                "status": "deterministic", "method": "manifest_page_range", "confidence": 1.0,
                "reason": "Classified from the reviewed document main-text page range.",
            }
        if region_status.get("status") not in {"human_confirmed", "human_override"} and not region_structure_owned:
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
                record["region_type"] = inferred_region
                field_status["region_type"] = {
                    "status": "deterministic", "method": "manifest_page_range", "confidence": 1.0,
                    "reason": region_reason,
                }
        # A record that begins before the main text and runs into it cannot be labelled by
        # page alone: the reviewer chooses main text, front matter, or splits it.
        issues = [i for i in record.get("boundary_quality_issues") or [] if not (isinstance(i, dict) and i.get("code") == "main_text_start_straddle")]
        if min(pdf_pages) < start_page <= max(pdf_pages) and region_status.get("status") not in {"human_confirmed", "human_override"}:
            reason = f"This record starts before the main text (PDF page {start_page}) and continues into it. Choose main text, front matter, or split it."
            issues.append({"code": "main_text_start_straddle", "edge": "record", "reason": reason})
            record["needs_review"] = True
            if not record.get("review_reason") or str(record.get("review_reason")).lower() == "pending human review.":
                record["review_reason"] = reason
        if not any(isinstance(i, dict) and i.get("code") == "main_text_start_straddle" for i in issues) and str(record.get("review_reason") or "").endswith("Choose main text, front matter, or split it."):
            record["review_reason"] = ""
            record["needs_review"] = bool(issues)
        if issues or record.get("boundary_quality_issues"):
            record["boundary_quality_issues"] = issues
        role_status = field_status.get("discourse_role") if isinstance(field_status.get("discourse_role"), dict) else {}
        # A stale/inferred manifest range must not make a reviewer-defined
        # main-text record paratext. Region/primary structural ownership is
        # the higher-order document fact; discourse role remains available
        # for semantic classification.
        strong_main_text = (
            (region_structure_owned and record.get("region_type") == "main_text")
            or (primary_structure_owned and record.get("primary_text") is True)
        )
        if not inside and not strong_main_text and role_status.get("status") not in {"human_confirmed", "human_override"}:
            record["discourse_role"] = "paratext"
            field_status["discourse_role"] = {
                "status": "deterministic", "method": "manifest_page_range", "confidence": 1.0,
                "reason": "Non-primary material is deterministically classified as paratext unless a reviewer overrides it.",
            }
    confidences = [
        float(span.get("confidence"))
        for span in record.get("source_spans") or []
        if isinstance(span, dict) and isinstance(span.get("confidence"), (int, float))
    ]
    if confidences:
        record["extraction_quality"] = round(sum(confidences) / len(confidences), 4)
