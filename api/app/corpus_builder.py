# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
import threading
import time
import unicodedata
import uuid
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import fitz
from pydantic import BaseModel, ValidationError

from . import experiment
from .autofill import decide as decide_autofill
from .autofill import in_audit_sample
from .autonomous import Policy as AutonomousPolicy
from .config import APP_VERSION, settings
from .corpus_build_lifecycle import BuildLifecycleMixin
from .corpus_editorial_memory import EditorialMemoryMixin
from .corpus_enrichment_helpers import (
    _enrichment_pass_indices as _enrichment_pass_indices,
)
from .corpus_enrichment_helpers import (
    _initial_enrichment_operation as _initial_enrichment_operation,
)
from .corpus_enrichment_helpers import (
    _merge_enrichment_snapshot as _merge_enrichment_snapshot,
)
from .corpus_enrichment_helpers import (
    _metadata_family_states,
)
from .corpus_enrichment_helpers import (
    _semantic_atoms as _semantic_atoms,
)
from .corpus_enrichment_reruns import EnrichmentRerunsMixin
from .corpus_extraction import (
    extract_source_document as _extract_source_document,
)
from .corpus_llm_helpers import (
    _context_window,
    _generation_options,
    _llm_config,
    _parse_json_robust,
    _stage_limits,
    _stage_timeouts,
    _validate_execution_budget,
)

# Compatibility exports: existing callers and integrations retain this interface.
from .corpus_metadata import (
    ALLOWED_METADATA_FIELDS as ALLOWED_METADATA_FIELDS,
)
from .corpus_metadata import (
    ATTRIBUTION_EVIDENCE_FIELDS as ATTRIBUTION_EVIDENCE_FIELDS,
)
from .corpus_metadata import (
    DISCOURSE_ROLE_DEFINITIONS as DISCOURSE_ROLE_DEFINITIONS,
)
from .corpus_metadata import (
    DISCOURSE_ROLES as DISCOURSE_ROLES,
)
from .corpus_metadata import (
    EVIDENCE_REQUIRED_FIELDS as EVIDENCE_REQUIRED_FIELDS,
)
from .corpus_metadata import (
    HUMAN_EDITABLE_METADATA_FIELDS as HUMAN_EDITABLE_METADATA_FIELDS,
)
from .corpus_metadata import (
    HYBRID_REQUIRED_FIELDS as HYBRID_REQUIRED_FIELDS,
)
from .corpus_metadata import (
    MANIFEST_INHERITED_FIELDS as MANIFEST_INHERITED_FIELDS,
)
from .corpus_metadata import (
    METADATA_FAMILY_FIELDS as METADATA_FAMILY_FIELDS,
)
from .corpus_metadata import (
    NON_PRIMARY_REGION_TYPES as NON_PRIMARY_REGION_TYPES,
)
from .corpus_metadata import (
    PROPOSITION_STATUS_VALUES as PROPOSITION_STATUS_VALUES,
)
from .corpus_metadata import (
    REGION_TYPES as REGION_TYPES,
)
from .corpus_metadata import (
    REVIEW_METADATA_FIELDS as REVIEW_METADATA_FIELDS,
)
from .corpus_metadata import (
    SOURCE_BOUND_FIELDS as SOURCE_BOUND_FIELDS,
)
from .corpus_metadata import (
    STANCE_ALIASES as STANCE_ALIASES,
)
from .corpus_metadata import (
    STANCE_VALUES as STANCE_VALUES,
)
from .corpus_metadata import (
    STRONG_STRUCTURAL_METHODS as STRONG_STRUCTURAL_METHODS,
)
from .corpus_metadata import (
    _normalize_semantic_value as _normalize_semantic_value,
)
from .corpus_metadata import (
    apply_metadata_constraints as apply_metadata_constraints,
)
from .corpus_models import (
    CORPUS_PROFILES,
    DOCUMENT_PROMPT_VERSION,
    METADATA_PROMPT_VERSION,
    PROFILE_VERSION,
    SCHEMA_VERSION,
    SEGMENTATION_PROMPT_VERSION,
    BoundaryAuditResponseModel,
    BoundaryBatchResponseModel,
    CompactSegmentationResponseModel,
    DocumentManifestModel,
    PairBoundaryResponseModel,
    RecordMetadataModel,
    TextTouchupResponseModel,
)
from .corpus_models import (
    DiscourseMetadataModel as DiscourseMetadataModel,
)
from .corpus_models import (
    DiscourseMetadataResponseModel as DiscourseMetadataResponseModel,
)
from .corpus_models import (
    IndexMetadataResponseModel as IndexMetadataResponseModel,
)
from .corpus_models import (
    QuotationMetadataResponseModel as QuotationMetadataResponseModel,
)
from .corpus_models import (
    SegmentationResponseModel as SegmentationResponseModel,
)
from .corpus_operations import OperationsMixin
from .corpus_pipeline import BuildScope
from .corpus_publication import (
    build_text_touchup_prompt,
    publication_blocker,
    publishable_records,
    serialize_public_record,
    validate_publication_record,
)
from .corpus_record_quality import (
    _metadata_source_quality_gate,
    _record_extraction_quality_issues,
    _trash_quality_report,
    iso_now,
)
from .corpus_review_actions import ReviewActionsMixin, _serialize_record_mutation
from .corpus_review_state import (
    _decorate_review_state,
    _enforce_review_invariants,
    _matches_review_queue,
    _metadata_enrichment_finished,
    _queue_counts,
    _sync_record_metadata_state,
)
from .corpus_review_state import (
    _review_issue_codes as _review_issue_codes,
)
from .corpus_review_state import (
    _settle_enrichment_review_reason as _settle_enrichment_review_reason,
)
from .corpus_reviewer_helpers import (
    _allowed_for,
    _metadata_issue_type,
    _present_for_reviewer,
    _scrub_sealed_field,
)
from .corpus_reviewer_helpers import (
    _operation_from_build as _operation_from_build,
)
from .corpus_schema_profile import SchemaProfileMixin
from .corpus_segmentation import (
    _apply_boundary_adjudication_to_records,
    _apply_manifest_metadata,
    _boundary_audit_candidates,
    _candidate_route,
    _construct_records,
    _deterministic_boundary_candidates,
    _manifest_main_text_blocks,
    _mark_segmentation_review,
    _normalize_text,
    _normalize_topology,
    _record_sizing_policy,
    _scholarly_page_range,
    _topology_quality_report,
    _topology_sanity,
)
from .corpus_segmentation import (
    _is_protected_transition as _is_protected_transition,
)
from .enrichment_cycles import (
    GlobalLearningStore,
)
from .enrichment_ledger import (
    ACCEPTED,
    AUTOFILLED,
    BLIND_LABEL,
    CALL,
    CORRECTED,
    PROPOSED,
    REJECTED,
    EnrichmentLedger,
)
from .error_severity import severity as error_severity
from .main_text_start import infer_main_text_start
from .metadata_schema import (
    CORE_FIELDS,
    CORE_GROUP,
    DEFAULT_SCHEMA_ID,
    MetadataSchema,
    build_group_prompt,
    default_schema,
    edit_model,
    response_model_for,
)
from .metadata_schema_store import SchemaNotFound, SchemaStore
from .metadata_values import is_placeholder
from .models import WorkMetadataRequest, WorkMetadataSeed
from .rag import _citation_strings, chat_complete
from .run_guidance import find_guidance_matches, format_group_guidance
from .sentence_boundaries import snap_boundaries_to_sentences
from .source_quality import assess_extracted_source, page_source_quality_report
from .text_noise import (
    DEFAULT_NOISE_THRESHOLD,
    TEXT_NOISE_LLM_PROMPT,
    TEXT_NOISE_PROMPT_VERSION,
    TextNoiseLlmResult,
    fuse_record_noise,
    should_ask_llm,
)
from .text_noise import (
    annotate_records as annotate_text_noise,
)

PUBLICATION_SCHEMA_VERSION = "derridai-corpus-jsonl-v1"


_PROMPT_TAG_RE = re.compile(r"</?\s*SOURCE[_ ]?TEXT\s*/?\s*>", re.I)
_EDGE_TAG_RE = re.compile(r"^\s*(</?\s*[A-Za-z_][\w-]{0,30}\s*/?\s*>)\s*|\s*(</?\s*[A-Za-z_][\w-]{0,30}\s*/?\s*>)\s*$")
_EDGE_LABEL_RE = re.compile(r"^\s*(?:\[?\s*(?:SOURCE[_ ]TEXT|TOUCHED[- _]?UP(?: TEXT)?|CORRECTED(?: TEXT)?|OUTPUT|RESULT)\s*\]?\s*:)\s*", re.I)


def _strip_added_markup(proposed: str, source: str) -> str:
    """Trim tags and labels a model echoed from the prompt around its answer.

    The test is the one a person would use: material at the very start or end of the answer that is not at the
    start or end of the source was added by the model. So a tag or label is removed only when the source does not
    itself begin or end with it; a real "<b>" in the text is kept.
    """
    value = proposed
    # The prompt's own delimiter is never text, wherever the model put it (a small model may even write it self-closing).
    if not _PROMPT_TAG_RE.search(source):
        value = _PROMPT_TAG_RE.sub("", value)
    for _ in range(6):  # a tag, then a label, then another tag: peel until nothing more is added
        before = value
        label = _EDGE_LABEL_RE.match(value)
        if label and not source.lstrip().lower().startswith(label.group(0).strip().lower()):
            value = value[label.end():]
        for match in (_EDGE_TAG_RE.search(value),):
            if not match:
                continue
            tag = (match.group(1) or match.group(2) or "").strip()
            at_start = bool(match.group(1))
            if tag and not (source.lstrip().startswith(tag) if at_start else source.rstrip().endswith(tag)):
                value = value[match.end():] if at_start else value[: match.start()]
        value = value.strip()
        if value == before:
            break
    return value


def _sanitize_touchup_output(proposed: str, source: str) -> str:
    """Remove model-added outer wrappers without touching source punctuation."""
    value = _strip_added_markup(str(proposed or "").strip(), str(source or "").strip())
    source_value = str(source or "").strip()
    lines = value.splitlines()
    source_lines = source_value.splitlines()
    if len(lines) >= 3:
        first, last = lines[0].strip(), lines[-1].strip()
        source_first = source_lines[0].strip() if source_lines else ""
        source_last = source_lines[-1].strip() if source_lines else ""
        if first == "---" and last == "---" and not (source_first == "---" and source_last == "---"):
            value = "\n".join(lines[1:-1]).strip()
            lines = value.splitlines()
        if len(lines) >= 3 and lines[0].strip().startswith("~~~") and lines[-1].strip() == "~~~":
            if not (source_first.startswith("~~~") and source_last == "~~~"):
                value = "\n".join(lines[1:-1]).strip()
        if len(lines) >= 3 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
            if not (source_first.startswith("```") and source_last == "```"):
                value = "\n".join(lines[1:-1]).strip()
    return value


TEXT_CLEANUP_RULES = {
    "page_numbers", "repeated_short_lines", "line_hyphenation",
    "paragraph_lines", "empty_lines", "ocr_artifacts", "whitespace",
}
_PAGE_NUMBER_LINE_RE = re.compile(r"^\s*(?:page\s+)?(?:[ivxlcdm]+|\d{1,4})\s*$", re.I)
_QUOTE_OR_LIST_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-z][.)]|[ivxlcdm]+[.)]|[>»«“”\"'])\s*", re.I)
_SENTENCE_END_LINE_RE = re.compile(r"[.!?…:;][\]\)\}\"'»”’]*\s*$")
_HEADINGISH_LINE_RE = re.compile(r"^\s*(?:[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 '\u2019\-–—:;,.]{3,}|.{0,80}:)\s*$")
_OCR_GARBAGE_RE = re.compile(r"(?:\ufffd|[|¦]{3,}|[_~^]{4,}|(?:[^\w\s.,;:!?()'\"–—-]){5,})")


_OCR_BOILERPLATE_RE = re.compile(r"(?:downloaded\s+from|all\s+use\s+subject\s+to|digitized\s+by\s+the\s+internet\s+archive|created\s+from\s+.+ebooks|ebook\s+central|jstor\.org|proquest\s+ebook)", re.I)

def _looks_like_poetry_or_quotation(lines: list[str]) -> bool:
    meaningful = [line.strip() for line in lines if line.strip()]
    if len(meaningful) < 4:
        return False
    short = sum(1 for line in meaningful if len(line) <= 52)
    quoted = sum(1 for line in meaningful if line.startswith(("\"", "“", "‘", "'", ">", "«")))
    # Poetry tends to be consistently short-lined; block quotations often keep
    # an explicit quotation marker. Preserve both rather than flattening them.
    return (short / len(meaningful) >= 0.72) or (quoted / len(meaningful) >= 0.5)


def _clean_wrapped_lines(text: str) -> tuple[str, int]:
    """Repair layout line wraps conservatively without flattening poetry/quotes."""
    paragraphs = re.split(r"(\n\s*\n)", text)
    out: list[str] = []
    changes = 0
    for part in paragraphs:
        if not part or re.fullmatch(r"\n\s*\n", part):
            out.append(part)
            continue
        lines = part.splitlines()
        if _looks_like_poetry_or_quotation(lines):
            out.append(part)
            continue
        joined: list[str] = []
        i = 0
        while i < len(lines):
            current = lines[i].rstrip()
            if i + 1 >= len(lines):
                joined.append(current)
                break
            nxt = lines[i + 1].lstrip()
            can_join = bool(
                current.strip() and nxt.strip()
                and not _SENTENCE_END_LINE_RE.search(current)
                and not _QUOTE_OR_LIST_LINE_RE.match(current)
                and not _QUOTE_OR_LIST_LINE_RE.match(nxt)
                and not _HEADINGISH_LINE_RE.match(current)
                and not _HEADINGISH_LINE_RE.match(nxt)
                and (re.match(r"^[a-zà-öø-ÿ]", nxt) or len(current) >= 45)
            )
            if can_join:
                # Preserve hyphenated lexical compounds, but repair obvious
                # PDF line-break hyphenation when the next line starts lowercase.
                if current.endswith("-") and re.match(r"^[a-zà-öø-ÿ]", nxt):
                    joined.append(current[:-1] + nxt)
                else:
                    joined.append(current + " " + nxt)
                changes += 1
                i += 2
            else:
                joined.append(current)
                i += 1
        out.append("\n".join(joined))
    return "".join(out), changes


def _clean_text_value(text: str, rules: set[str], recurring_lines: set[str], document_terms: set[str] | None = None) -> tuple[str, dict[str, Any]]:
    original = str(text or "")
    value = original
    document_terms = {term.casefold().strip() for term in (document_terms or set()) if term and len(term.strip()) >= 3}
    removed: list[str] = []
    changes = 0
    if "ocr_artifacts" in rules:
        # Repair only extraction artefacts with unambiguous typographic meaning.
        # Do not guess at lexical errata here; uncertain corrections belong in
        # the opt-in LLM touch-up workflow.
        translation = str.maketrans({
            "\u00ad": "", "\u200b": "", "\u200c": "", "\u200d": "", "\ufeff": "",
            "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
        })
        updated = value.translate(translation).replace("\f", "\n")
        if updated != value:
            changes += 1
            value = updated
    if "line_hyphenation" in rules:
        updated = re.sub(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])-\s*\n\s*(?=[A-Za-zÀ-ÖØ-öø-ÿ])", "", value)
        if updated != value:
            changes += 1
            value = updated
    if rules & {"page_numbers", "repeated_short_lines", "ocr_artifacts"}:
        kept: list[str] = []
        raw_lines = value.splitlines()
        meaningful_indexes = [index for index, line in enumerate(raw_lines) if line.strip()]
        boundary_indexes = set(meaningful_indexes[:3] + meaningful_indexes[-3:])
        for index, line in enumerate(raw_lines):
            stripped = line.strip()
            normalized = stripped.casefold()
            remove = False
            if "page_numbers" in rules and index in boundary_indexes and _PAGE_NUMBER_LINE_RE.match(stripped):
                remove = True
            elif "repeated_short_lines" in rules and index in boundary_indexes and normalized and len(normalized) <= 120 and (normalized in recurring_lines or normalized in document_terms):
                remove = True
            elif "ocr_artifacts" in rules:
                control_count = sum(1 for ch in stripped if unicodedata.category(ch) == "Cc" and ch not in "\t\n\r")
                printable = sum(1 for ch in stripped if ch.isalnum() or ch.isspace() or ch in ".,;:!?()[]{}'\"-–—")
                ratio = printable / max(1, len(stripped))
                if stripped and (_OCR_GARBAGE_RE.search(stripped) or _OCR_BOILERPLATE_RE.search(stripped) or "\ufffd" in stripped or control_count or (len(stripped) >= 5 and ratio < 0.55)):
                    remove = True
            if remove:
                if stripped:
                    removed.append(stripped)
                changes += 1
            else:
                kept.append(line)
        value = "\n".join(kept)
    if "paragraph_lines" in rules:
        # A wrapped paragraph can span many physical PDF lines. Iterate a few
        # conservative passes so joining line 1→2 does not leave 2→3 behind.
        for _ in range(4):
            value, count = _clean_wrapped_lines(value)
            changes += count
            if not count:
                break
    if "empty_lines" in rules:
        updated = re.sub(r"^[ \t]+$", "", value, flags=re.M)
        updated = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", updated)
        if updated != value:
            changes += 1
            value = updated
    if "whitespace" in rules:
        updated = re.sub(r"[ \t]+\n", "\n", value)
        updated = re.sub(r"[ \t]{2,}", " ", updated).strip()
        if updated != value:
            changes += 1
            value = updated
    return value, {"changed": value != original, "changes": changes, "removed_lines": removed[:200]}


def _recurring_cleanup_lines(records: list[dict[str, Any]], minimum_occurrences: int = 2) -> set[str]:
    """Detect running headers/footers only at record boundaries.

    Restricting detection to the first/last meaningful lines prevents recurring
    philosophical phrases inside the body from being mistaken for page furniture.
    """
    counts: Counter[str] = Counter()
    for record in records:
        meaningful = [line.strip() for line in str(record.get("text") or "").splitlines() if line.strip()]
        seen: set[str] = set()
        for stripped in meaningful[:3] + meaningful[-3:]:
            key = stripped.casefold()
            if not key or len(key) > 120 or _PAGE_NUMBER_LINE_RE.match(stripped) or key in seen:
                continue
            seen.add(key)
            counts[key] += 1
    return {key for key, count in counts.items() if count >= minimum_occurrences}


def apply_automatic_text_cleanup(records: list[dict[str, Any]], rules: list[str] | tuple[str, ...] | set[str], document_terms: list[str] | tuple[str, ...] | set[str] | None = None) -> dict[str, Any]:
    """Clean reviewed corpus text before LLM enrichment while preserving source truth."""
    enabled = {str(rule) for rule in rules if str(rule) in TEXT_CLEANUP_RULES}
    recurring = _recurring_cleanup_lines(records)
    document_term_set = {str(term).strip() for term in (document_terms or []) if str(term).strip()}
    changed_records = 0
    total_changes = 0
    removed_lines = 0
    for record in records:
        original = str(record.get("text") or "")
        cleaned, report = _clean_text_value(original, enabled, recurring, document_term_set)
        if not report["changed"]:
            continue
        record.setdefault("source_extracted_text", original)
        record["text"] = cleaned
        record["text_length"] = len(cleaned)
        record["text_cleanup_status"] = "automatic"
        record["text_cleanup_report"] = {
            "source": "automatic_pre_enrichment",
            "rules": sorted(enabled),
            "changes": int(report["changes"]),
            "removed_lines": list(report["removed_lines"]),
            "at": iso_now(),
        }
        history = list(record.get("text_revision_history") or [])
        history.append({
            "at": iso_now(), "source": "automatic_cleanup",
            "previous_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "text_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            "previous_length": len(original), "text_length": len(cleaned),
            "diff": "".join(difflib.unified_diff(original.splitlines(True), cleaned.splitlines(True), fromfile="source_extracted_text", tofile="cleaned_text"))[:20000],
            "resolved_source_issues": False,
        })
        record["text_revision_history"] = history[-50:]
        changed_records += 1
        total_changes += int(report["changes"])
        removed_lines += len(report["removed_lines"])
    return {
        "enabled": True,
        "rules": sorted(enabled),
        "records_changed": changed_records,
        "changes": total_changes,
        "removed_lines": removed_lines,
        "recurring_line_patterns": len(recurring),
    }
























































def metric_stage_of(schema_name: str) -> str:
    """Which part of a build a model call belongs to, for words in the UI."""
    return (
        "manifest" if "manifest" in schema_name else
        "segmentation" if ("boundar" in schema_name or "segment" in schema_name or "reconciliation" in schema_name) else
        "metadata" if "record_" in schema_name else
        "other"
    )


def annotate_boundary_suspects(records: list[dict[str, Any]]) -> int:
    # Flag likely sentence/paragraph cuts between adjacent records without
    # automatically rewriting scholarly boundaries on weak heuristics.
    count = 0
    continuation_re = re.compile(r"^(?:[a-zà-öø-ÿ]|[,;:)\]])")
    for left, right in zip(records, records[1:]):
        lt = str(left.get("text") or "").rstrip()
        rt = str(right.get("text") or "").lstrip()
        if not lt or not rt:
            continue
        incomplete_left = not bool(re.search(r"[.!?…][\"'’”)]?$", lt))
        continuation_right = bool(continuation_re.search(rt))
        open_quote = (lt.count('"') % 2 == 1) or (lt.count('“') > lt.count('”'))
        if incomplete_left and (continuation_right or open_quote):
            reason = "Possible sentence/quotation continuation across this record boundary."
            for row, edge in ((left, "end"), (right, "start")):
                flags = list(row.get("boundary_quality_issues") or [])
                flags.append({"code": "boundary_suspect", "edge": edge, "reason": reason})
                row["boundary_quality_issues"] = flags
                row["needs_review"] = True
                if not row.get("review_reason") or str(row.get("review_reason")).lower() == "pending human review.":
                    row["review_reason"] = reason
            count += 1
    return count


def corpus_root() -> Path:
    root = Path(settings.chroma_data_root).expanduser().resolve() / ".home" / "pdf-corpus"
    for part in ("assets", "builds", "publications"):
        (root / part).mkdir(parents=True, exist_ok=True)
    return root


def _json_write(path: Path, payload: Any) -> None:
    """Write JSON atomically without a shared temporary filename.

    Multiple Corpus Builder workers can persist telemetry while a reviewer is
    active. A fixed ``*.tmp`` path lets concurrent writers truncate/interleave
    one another before ``os.replace``. Use a unique sibling tempfile instead.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            # Safe: best-effort removal of a leftover temp file after the
            # atomic replace succeeded or the original error is propagating.
            pass


def _json_read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# 2026: renamed to match the DERRIDAI Core Specification's assertion-status vocabulary
# (llm_inferred -> model_inferred, human_confirmed_absent -> confirmed_absent). Builds and
# records written before the rename still have the old values on disk; normalize them the
# first time they are read, in place, the same way _with_start_inference backfills a field
# that did not exist yet.
_STATUS_VOCABULARY_MIGRATIONS = {"llm_inferred": "model_inferred", "human_confirmed_absent": "confirmed_absent"}
_STATUS_BEARING_KEYS = {"status", "source"}


def _migrate_status_vocabulary(value: Any) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _STATUS_BEARING_KEYS and isinstance(item, str) and item in _STATUS_VOCABULARY_MIGRATIONS:
                value[key] = _STATUS_VOCABULARY_MIGRATIONS[item]
            else:
                _migrate_status_vocabulary(item)
    elif isinstance(value, list):
        for item in value:
            _migrate_status_vocabulary(item)
    return value


def extract_source_document(data: bytes, *, filename: str, ocr_mode: str = 'auto', ocr_languages: str = 'eng+fra+deu', source_illegibility: float = 0) -> dict[str, Any]:
    """Compatibility facade for the dedicated PDF SourceDocument extractor."""
    return _extract_source_document(data, filename=filename, ocr_mode=ocr_mode, ocr_languages=ocr_languages, source_illegibility=source_illegibility)


def _image_bytes_to_pdf(data: bytes, filename: str) -> bytes:
    filetype = "png" if data.startswith(b"\x89PNG") or str(filename).lower().endswith(".png") else "jpeg"
    try:
        image = fitz.open(stream=data, filetype=filetype)
    except Exception as exc:
        raise ValueError(f"Could not read image: {exc}") from exc
    try:
        return image.convert_to_pdf()
    except Exception as exc:
        raise ValueError(f"Could not prepare image for OCR: {exc}") from exc
    finally:
        image.close()

class PdfCorpusRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or corpus_root()
        for part in ("assets", "builds", "publications"):
            (self.root / part).mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def asset_meta_path(self, asset_id: str) -> Path:
        return self.root / "assets" / f"{asset_id}.json"

    def asset_pdf_path(self, asset_id: str) -> Path:
        return self.root / "assets" / f"{asset_id}.pdf"

    def asset_blocks_path(self, asset_id: str) -> Path:
        return self.root / "assets" / f"{asset_id}.blocks.jsonl"

    def asset_content_path(self, asset_id: str, suffix: str = ".pdf") -> Path:
        suffix = suffix if str(suffix).startswith(".") else f".{suffix}"
        return self.root / "assets" / f"{asset_id}{suffix}"

    def save_asset(
        self, data: bytes, *, filename: str, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu",
        source_illegibility: float = 0, content_type: str = "", catalog_metadata: dict[str, Any] | None = None,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        if not data:
            raise ValueError("The uploaded source was empty.")
        from .source_media import (
            clamp_illegibility,
            content_suffix_for,
            detect_media_kind,
            infer_initial_metadata,
            media_type_for,
        )
        from .source_quality import page_source_quality_report

        illegibility = clamp_illegibility(source_illegibility)
        kind = detect_media_kind(filename, data, content_type)
        digest = hashlib.sha256(data).hexdigest()
        # Default PDF uploads keep the historical content-addressed id.
        identity = digest
        if kind != "pdf" or ocr_mode != "auto" or illegibility:
            identity = hashlib.sha256(f"{digest}|{kind}|{ocr_mode}|{illegibility:.2f}".encode()).hexdigest()
        asset_id = f"pdf-{identity[:24]}"
        suffix = ".pdf" if kind == "pdf" else content_suffix_for(kind, filename)
        meta_path = self.asset_meta_path(asset_id)
        with self._lock:
            existing = _json_read(meta_path)
            existing_suffix = str(existing.get("content_suffix") or ".pdf") if isinstance(existing, dict) else suffix
            if isinstance(existing, dict) and self.asset_content_path(asset_id, existing_suffix).exists():
                return existing
            extracted = self._extract_for_ingest(
                data, filename=filename, kind=kind, ocr_mode=ocr_mode, ocr_languages=ocr_languages,
                source_illegibility=illegibility, catalog_metadata=catalog_metadata,
            )
            if catalog_metadata and catalog_metadata.get("gutenberg_id"):
                extracted["media_kind"] = "gutenberg"
            blocks = list(extracted.pop("blocks"))
            if not isinstance(extracted.get("initial_metadata"), dict):
                extracted["initial_metadata"] = infer_initial_metadata(
                    "\n\n".join(str(block.get("text") or "") for block in blocks),
                    embedded=extracted.get("metadata") if isinstance(extracted.get("metadata"), dict) else {},
                    blocks=blocks, catalog=catalog_metadata,
                )
            checked_at = iso_now()
            meta = {
                "asset_id": asset_id,
                "sha256": digest,
                "filename": extracted["filename"],
                "created_at": checked_at,
                "content_suffix": suffix,
                "media_type": media_type_for(str(extracted.get("media_kind") or kind), extracted["filename"]),
                "source_illegibility": illegibility,
                "source_quality": page_source_quality_report(blocks, extracted.get("pages") or []),
                "deterministic_checked_at": checked_at,
                **({} if not source_url else {"source_url": source_url}),
                **extracted,
            }
            self.asset_content_path(asset_id, suffix).write_bytes(data)
            with self.asset_blocks_path(asset_id).open("w", encoding="utf-8") as handle:
                for block in blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            _json_write(meta_path, meta)
            return meta

    def _extract_for_ingest(
        self, data: bytes, *, filename: str, kind: str, ocr_mode: str, ocr_languages: str,
        source_illegibility: float, catalog_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        from .source_media import (
            extract_non_pdf,
            infer_initial_metadata,
            png_text_metadata,
        )

        if kind == "image":
            pdf_bytes = _image_bytes_to_pdf(data, filename)
            extracted = extract_source_document(
                pdf_bytes, filename=filename,
                ocr_mode="always" if source_illegibility >= 99.9 else ocr_mode,
                ocr_languages=ocr_languages, source_illegibility=source_illegibility,
            )
            extracted["media_kind"] = "image"
            metadata = dict(extracted.get("metadata") or {})
            metadata.update(png_text_metadata(data))
            extracted["metadata"] = metadata
            extracted["initial_metadata"] = infer_initial_metadata(
                "\n\n".join(str(block.get("text") or "") for block in extracted.get("blocks") or []),
                embedded=metadata, blocks=list(extracted.get("blocks") or []), catalog=catalog_metadata,
            )
            return extracted
        if kind == "pdf":
            extracted = extract_source_document(
                data, filename=filename, ocr_mode=ocr_mode, ocr_languages=ocr_languages,
                source_illegibility=source_illegibility,
            )
            extracted["media_kind"] = "pdf"
            extracted["initial_metadata"] = infer_initial_metadata(
                "\n\n".join(str(block.get("text") or "") for block in extracted.get("blocks") or []),
                embedded=extracted.get("metadata") if isinstance(extracted.get("metadata"), dict) else {},
                blocks=list(extracted.get("blocks") or []), catalog=catalog_metadata,
            )
            return extracted
        return extract_non_pdf(data, filename=filename, kind=kind, catalog=catalog_metadata)

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        meta = _json_read(self.asset_meta_path(asset_id))
        if not isinstance(meta, dict):
            raise KeyError(asset_id)
        return self._with_extraction_quality(self._with_start_inference(meta))

    def _with_start_inference(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Assets extracted before the inference existed get it the first time they are read, and keep it."""
        if "main_text_start_inference" in meta or not meta.get("asset_id"):
            return meta
        asset_id = str(meta["asset_id"])
        try:
            outline: list[tuple[int, str]] = []
            pdf_path = self.asset_pdf_path(asset_id)
            if pdf_path.exists():
                with fitz.open(pdf_path) as doc:
                    outline = [(int(page), str(title)) for _level, title, page in doc.get_toc(simple=True)]
            meta["outline"] = [{"page": page, "title": title} for page, title in outline[:400]]
            meta["main_text_start_inference"] = infer_main_text_start(self.load_blocks(asset_id), meta.get("pages") or [], outline)
            with self._lock:
                _json_write(self.asset_meta_path(asset_id), meta)
        except Exception:  # noqa: BLE001 - a failed inference must never make an asset unreadable
            meta["main_text_start_inference"] = {"page": None, "confidence": 0.0, "clues": [], "offered": False}
        return meta

    def list_assets(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted((self.root / "assets").glob("pdf-*.json"), reverse=True):
            item = _json_read(path)
            if isinstance(item, dict):
                items.append(self._with_extraction_quality(self._with_start_inference(item)))
        return items

    def _load_block_rows(self, asset_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        path = self.asset_blocks_path(asset_id)
        if not path.exists():
            return blocks
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    blocks.append(json.loads(line))
        return blocks

    def _with_extraction_quality(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Score extraction quality when the PDF is first loaded, including older assets."""
        if (isinstance(meta.get("extraction_noise"), dict) and isinstance(meta.get("source_quality"), dict)) or not meta.get("asset_id"):
            return meta
        asset_id = str(meta["asset_id"])
        try:
            quality = assess_extracted_source(self._load_block_rows(asset_id), meta.get("pages") or [])
            meta.update(quality)
            with self._lock:
                _json_write(self.asset_meta_path(asset_id), meta)
        except Exception:  # noqa: BLE001,S110 - quality must never make an asset unreadable
            return meta
        return meta

    def load_blocks(self, asset_id: str) -> list[dict[str, Any]]:
        self.get_asset(asset_id)
        return self._load_block_rows(asset_id)

    def update_page_labels(self, asset_id: str, labels: dict[int, str | None]) -> dict[str, Any]:
        """Apply explicit scholarly page-label overrides to a source asset.

        Physical PDF page identity never changes. Overrides update the auditable
        source metadata and block labels used for subsequently generated records.
        """
        with self._lock:
            asset = self.get_asset(asset_id)
            normalized = {int(page): (str(label).strip() if label is not None else None) for page, label in labels.items()}
            valid_pages = {int(item.get("pdf_page") or 0) for item in asset.get("pages") or []}
            invalid = sorted(page for page in normalized if page not in valid_pages)
            if invalid:
                raise ValueError(f"Unknown physical PDF page(s): {', '.join(map(str, invalid[:12]))}")
            for page_info in asset.get("pages") or []:
                page_number = int(page_info.get("pdf_page") or 0)
                if page_number not in normalized:
                    continue
                if "original_printed_page_label" not in page_info:
                    page_info["original_printed_page_label"] = page_info.get("printed_page_label")
                page_info["printed_page_label"] = normalized[page_number]
                page_info["printed_page_label_source"] = "human_override"
            blocks = self.load_blocks(asset_id)
            for block in blocks:
                page_number = int(block.get("page") or 0)
                if page_number not in normalized:
                    continue
                if "original_printed_page_label" not in block:
                    block["original_printed_page_label"] = block.get("printed_page_label")
                block["printed_page_label"] = normalized[page_number]
                block["printed_page_label_source"] = "human_override"
            tmp = self.asset_blocks_path(asset_id).with_suffix(".blocks.jsonl.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                for block in blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            os.replace(tmp, self.asset_blocks_path(asset_id))
            asset["page_label_revision"] = int(asset.get("page_label_revision") or 0) + 1
            asset["page_labels_updated_at"] = iso_now()
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def update_document_layout(self, asset_id: str, plan: dict[str, Any]) -> dict[str, Any]:
        """Persist reviewer-owned document structure and derive page metadata deterministically.

        The immutable physical PDF page remains the source coordinate. The layout plan may
        derive scholarly folios, main-text/bibliography regions, logical left/right pages,
        and alternating thread hints. These reviewer-owned facts outrank later LLM guesses.
        """
        with self._lock:
            asset = self.get_asset(asset_id)
            page_count = int(asset.get("page_count") or 0)
            layout = str(plan.get("page_layout") or "single")
            if layout not in {"single", "two_up"}:
                raise ValueError("page_layout must be single or two_up")
            order = str(plan.get("reading_order") or "left_to_right")
            if order not in {"left_to_right", "right_to_left"}:
                raise ValueError("reading_order must be left_to_right or right_to_left")
            main_pdf = int(plan["main_text_pdf_start"]) if plan.get("main_text_pdf_start") else None
            main_printed = int(plan["main_text_printed_start"]) if plan.get("main_text_printed_start") else None
            bib_pdf = int(plan["bibliography_pdf_start"]) if plan.get("bibliography_pdf_start") else None
            for value, name in ((main_pdf, "main_text_pdf_start"), (bib_pdf, "bibliography_pdf_start")):
                if value is not None and not 1 <= value <= max(1, page_count):
                    raise ValueError(f"{name} must be within the PDF page range")
            if main_pdf and bib_pdf and bib_pdf < main_pdf:
                raise ValueError("bibliography_pdf_start cannot precede main_text_pdf_start")
            slots = ["left", "right"] if order == "left_to_right" else ["right", "left"]
            first_slot = str(plan.get("main_text_slot") or slots[0])
            if first_slot not in {"left", "right"}:
                first_slot = slots[0]
            thread_mode = str(plan.get("thread_mode") or "continuous")
            valid_thread_modes = {"continuous", "odd_even", "even_odd", "left_right", "right_left"}
            if thread_mode not in valid_thread_modes:
                raise ValueError("Unsupported thread_mode")
            clean_plan = {
                "page_layout": layout, "reading_order": order,
                "main_text_pdf_start": main_pdf, "main_text_printed_start": main_printed,
                "main_text_slot": first_slot if layout == "two_up" else None,
                "bibliography_pdf_start": bib_pdf, "thread_mode": thread_mode,
                "thread_a_language": str(plan.get("thread_a_language") or "").strip() or None,
                "thread_b_language": str(plan.get("thread_b_language") or "").strip() or None,
                "confirmed_by": "human", "updated_at": iso_now(),
            }
            pages = asset.get("pages") or []
            blocks = self.load_blocks(asset_id)
            page_lookup = {int(p.get("pdf_page") or 0): p for p in pages}
            # Reset prior derived structural fields while preserving extraction facts and manual labels.
            for page in pages:
                for key in ("logical_pages", "deterministic_region_type", "thread_ids"):
                    page.pop(key, None)
            for block in blocks:
                for key in ("logical_page_slot", "logical_printed_page_label", "deterministic_region_type", "document_thread", "thread_language"):
                    block.pop(key, None)
            def printed_for(pdf_page: int, slot: str | None = None) -> int | None:
                if not (main_pdf and main_printed) or pdf_page < main_pdf:
                    return None
                if layout == "single":
                    return main_printed + (pdf_page-main_pdf)
                ordered = slots
                start_index = ordered.index(first_slot)
                absolute = (pdf_page-main_pdf)*2 + ordered.index(slot or ordered[0]) - start_index
                if absolute < 0:
                    return None
                return main_printed + absolute
            for pdf_page in range(1, page_count+1):
                page = page_lookup.get(pdf_page)
                if not page:
                    continue
                if bib_pdf and pdf_page >= bib_pdf:
                    region = "bibliography"
                elif main_pdf and pdf_page >= main_pdf:
                    region = "main_text"
                elif main_pdf:
                    region = "front_matter"
                else:
                    region = None
                if region:
                    page["deterministic_region_type"] = region
                logical = []
                for slot in (slots if layout == "two_up" else [None]):
                    number = printed_for(pdf_page, slot)
                    logical.append({"slot": slot or "full", "printed_page_label": str(number) if number else None})
                page["logical_pages"] = logical
                thread_ids = []
                if thread_mode in {"odd_even", "even_odd"}:
                    a_is_odd = thread_mode == "odd_even"
                    thread_ids = ["thread_a" if (pdf_page % 2 == 1) == a_is_odd else "thread_b"]
                elif thread_mode in {"left_right", "right_left"}:
                    a_slot = "left" if thread_mode == "left_right" else "right"
                    thread_ids = ["thread_a" if (slot or "full") == a_slot else "thread_b" for slot in (slots if layout == "two_up" else [None])]
                elif thread_mode == "continuous":
                    thread_ids = ["thread_a"]
                page["thread_ids"] = thread_ids
                # A deterministic generated label is intentionally lower priority than a human override.
                generated = logical[0].get("printed_page_label") if len(logical) == 1 else None
                if generated and page.get("printed_page_label_source") != "human_override":
                    page["printed_page_label"] = generated
                    page["printed_page_label_source"] = "document_layout_rule"
            # Bind block-side/thread metadata by physical geometry for two-up documents.
            for block in blocks:
                pdf_page = int(block.get("page") or 0)
                page = page_lookup.get(pdf_page) or {}
                region = page.get("deterministic_region_type")
                if region:
                    block["deterministic_region_type"] = region
                slot = None
                if layout == "two_up":
                    bbox = block.get("bbox") or [0,0,0,0]
                    width = float(page.get("width") or 0)
                    center = (float(bbox[0])+float(bbox[2]))/2 if len(bbox) >= 4 else 0
                    slot = "left" if not width or center < width/2 else "right"
                    block["logical_page_slot"] = slot
                    logical_label = printed_for(pdf_page, slot)
                    if logical_label:
                        block["logical_printed_page_label"] = str(logical_label)
                        block["printed_page_label"] = str(logical_label)
                        block["printed_page_label_source"] = "document_layout_rule"
                elif page.get("printed_page_label_source") == "document_layout_rule":
                    block["printed_page_label"] = page.get("printed_page_label")
                    block["printed_page_label_source"] = "document_layout_rule"
                thread = "thread_a"
                if thread_mode in {"odd_even", "even_odd"}:
                    a_is_odd = thread_mode == "odd_even"
                    thread = "thread_a" if (pdf_page % 2 == 1) == a_is_odd else "thread_b"
                elif thread_mode in {"left_right", "right_left"}:
                    a_slot = "left" if thread_mode == "left_right" else "right"
                    thread = "thread_a" if (slot or "full") == a_slot else "thread_b"
                block["document_thread"] = thread
                language = clean_plan.get("thread_a_language" if thread == "thread_a" else "thread_b_language")
                if language:
                    block["thread_language"] = language
            tmp = self.asset_blocks_path(asset_id).with_suffix(".blocks.jsonl.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                for block in blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            os.replace(tmp, self.asset_blocks_path(asset_id))
            asset["pages"] = pages
            asset["document_layout"] = clean_plan
            asset["document_layout_revision"] = int(asset.get("document_layout_revision") or 0) + 1
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def build_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "build.json"

    def build_records_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "records.jsonl"

    def build_checkpoint_path(self, build_id: str, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or "checkpoint"))
        return self.root / "builds" / build_id / "checkpoints" / f"{safe}.json"

    def save_checkpoint(self, build_id: str, name: str, payload: Any) -> None:
        self.get_build(build_id)
        _json_write(self.build_checkpoint_path(build_id, name), payload)

    def load_checkpoint(self, build_id: str, name: str, default: Any = None) -> Any:
        self.get_build(build_id)
        payload = _json_read(self.build_checkpoint_path(build_id, name), default)
        return _migrate_status_vocabulary(payload) if payload is not default else payload

    def create_build(self, payload: dict[str, Any]) -> dict[str, Any]:
        build_id = f"build-{uuid.uuid4().hex[:16]}"
        now = iso_now()
        build = {
            "build_id": build_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "record_count": 0,
            "needs_review_count": 0,
            "accepted_count": 0,
            "validation": None,
            "publication": None,
            "publication_status": "unpublished",
            "error": None,
            **payload,
        }
        _json_write(self.build_path(build_id), build)
        return build

    def save_build(self, build: dict[str, Any]) -> None:
        _json_write(self.build_path(str(build["build_id"])), build)

    def get_build(self, build_id: str) -> dict[str, Any]:
        build = _json_read(self.build_path(build_id))
        if not isinstance(build, dict):
            raise KeyError(build_id)
        return _migrate_status_vocabulary(build)

    def list_builds(self, *, offset: int = 0, limit: int = 50, asset_id: str | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for path in (self.root / "builds").glob("build-*/build.json"):
            build = _json_read(path)
            if isinstance(build, dict) and (not asset_id or build.get("asset_id") == asset_id):
                items.append(_migrate_status_vocabulary(build))
        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        total = len(items)
        return {"items": items[offset:offset + limit], "total": total, "offset": offset, "limit": limit}

    def save_records(self, build_id: str, records: list[dict[str, Any]]) -> None:
        """Atomically persist the record store.

        The repository lock serializes writers in this process; the unique temp
        file prevents two writers from ever sharing/truncating the same staging
        file. This is critical while progressive review and metadata checkpoints
        are both active.
        """
        path = self.build_records_path(build_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    for record in records:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    # Safe: best-effort temp-file cleanup; see _json_write.
                    pass

    def load_records(self, build_id: str) -> list[dict[str, Any]]:
        self.get_build(build_id)
        path = self.build_records_path(build_id)
        if not path.exists():
            return []
        with self._lock:
            with path.open("r", encoding="utf-8") as handle:
                return [_migrate_status_vocabulary(json.loads(line)) for line in handle if line.strip()]

    def page_records(self, build_id: str, *, offset: int = 0, limit: int = 50, needs_review: bool | None = None, disposition: str | None = None, metadata_incomplete: bool | None = None, source_problem: bool | None = None, review_queue: str | None = None, query: str = "") -> dict[str, Any]:
        # Stream the JSONL rather than loading the entire generated corpus for a
        # browse request. Structural edits intentionally use load_records(); read
        # pagination remains bounded no matter how large the generated record set.
        self.get_build(build_id)
        path = self.build_records_path(build_id)
        if not path.exists():
            return {
                "items": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
                "queue_counts": _queue_counts([]),
                "metadata_values": {},
            }
        q = query.casefold().strip()
        items: list[dict[str, Any]] = []
        queue_records: list[dict[str, Any]] = []
        metadata_values: dict[str, set[str]] = {field: set() for field in ALLOWED_METADATA_FIELDS}
        total = 0
        topology_count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = _migrate_status_vocabulary(json.loads(line))
                for field, value in record.items():
                    if field not in metadata_values and not isinstance(value, (str, list, tuple)):
                        continue
                    metadata_values.setdefault(field, set())
                    value = record.get(field)
                    values = value if isinstance(value, list) else [value]
                    for item in values:
                        if isinstance(item, str) and item.strip() and not is_placeholder(item):
                            metadata_values[field].add(item.strip())
                topology_index = topology_count
                topology_count += 1
                if needs_review is not None and bool(record.get("needs_review")) is not needs_review:
                    continue
                record_disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
                if disposition is not None and record_disposition != disposition:
                    continue
                if metadata_incomplete is not None and (not bool(record.get("metadata_complete"))) is not metadata_incomplete:
                    continue
                if source_problem is not None and bool(record.get("source_quality_issues")) is not source_problem:
                    continue
                if q and q not in line.casefold():
                    continue
                queue_records.append(record)
                if review_queue and not _matches_review_queue(record, review_queue):
                    continue
                if total >= offset and len(items) < limit:
                    record["topology_index"] = topology_index
                    _decorate_review_state(record)
                    _present_for_reviewer(record)
                    items.append(record)
                total += 1
        for record in items:
            record["topology_count"] = topology_count
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
            "queue_counts": _queue_counts(queue_records),
            "metadata_values": {
                field: sorted(values, key=str.casefold)
                for field, values in metadata_values.items()
                if values
            },
        }

    def publication_path(self, publication_id: str) -> Path:
        return self.root / "publications" / f"{publication_id}.jsonl"




class PdfCorpusBuildManager(BuildLifecycleMixin, EditorialMemoryMixin, OperationsMixin, ReviewActionsMixin, EnrichmentRerunsMixin, SchemaProfileMixin):
    def __init__(self, repository: PdfCorpusRepository | None = None, max_workers: int = 2) -> None:
        self.repo = repository or PdfCorpusRepository()
        self._lock = threading.RLock()
        self._cancel: set[str] = set()
        # Resolved provider requests may contain server-owned credentials and must
        # never be serialized into build.json. Keep the current execution contract
        # in memory so a reviewer can hot-swap profiles for subsequently scheduled
        # metadata work while the public build manifest remains secret-free.
        self._runtime_requests: dict[str, dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="derridai-pdf-corpus")
        # Conventions confirmed independently in several builds; see enrichment_cycles.
        self._global_learning = GlobalLearningStore(self.repo.root / "global_learning.json")
        self._ledger = EnrichmentLedger(self.repo.root / "enrichment_ledger.jsonl")
        self._suspended: set[tuple[str, str]] = set()
        self._schemas = SchemaStore(self.repo.root)
        self._schema_cache: dict[str, MetadataSchema] = {}  # a build's schema never changes, so it is parsed once
        # Model calls in flight per build, so the UI can say what it is waiting for instead of showing a frozen bar.
        self._llm_inflight: dict[str, dict[int, dict[str, Any]]] = {}
        self._llm_call_sequence = 0
        self._loaded_models_cache: tuple[float, str, set[str]] = (0.0, "", set())
        self._provider_epoch: dict[str, int] = {}  # bumped whenever a build's provider is switched, so a running pass can notice
        self._mark_interrupted()


    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
        _validate_execution_budget(request)
        try:
            schema = self._schemas.get(str(request.get("schema_id") or DEFAULT_SCHEMA_ID))
        except SchemaNotFound as exc:
            raise ValueError(f"Unknown metadata schema: {request.get('schema_id')}") from exc
        guidance = request.get("run_guidance") or {}
        if not isinstance(guidance, dict):
            raise ValueError("Run guidance must be a field-to-guidance object")
        unknown_guidance_fields = sorted(set(guidance) - set(schema.field_names()))
        if unknown_guidance_fields:
            raise ValueError("Run guidance references fields outside the selected schema: " + ", ".join(unknown_guidance_fields))
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build = self.repo.create_build({
            "schema": schema.model_dump(mode="json"), "schema_id": schema.id, "schema_hash": schema.content_hash(), "schema_name": schema.name,
            "asset_id": asset["asset_id"],
            "source_sha256": asset["sha256"],
            "source_filename": asset["filename"],
            "source_page_count": asset["page_count"],
            "source_block_count": asset["block_count"],
            "schema_version": SCHEMA_VERSION,
            "metadata_schema_version": schema.schema_version,
            "profile_id": profile_id,
            "profile_version": CORPUS_PROFILES[profile_id]["version"],
            "app_version": APP_VERSION,
            "document_prompt_version": DOCUMENT_PROMPT_VERSION,
            "segmentation_prompt_version": SEGMENTATION_PROMPT_VERSION,
            "metadata_prompt_version": METADATA_PROMPT_VERSION,
            "provider": request.get("provider") or "ollama",
            "model": request.get("model"),
            "request": public_request,
            "manifest": {},
        })
        with self._lock:
            self._runtime_requests[build["build_id"]] = dict(request)
        self._executor.submit(self._run, build["build_id"], request, False)
        return build


    def preview_schema_group(self, schema: MetadataSchema, group: str, text: str, request: dict[str, Any], run: bool) -> dict[str, Any]:
        """Show, and optionally run, the prompt one group of a schema produces for a passage.

        This is for trying a schema without a build. It has none of a build's context (no document manifest, editorial
        memory or neighbouring records), so a real build's prompt is this one plus that context.
        """
        if group not in {g.key for g in schema.groups}:
            raise ValueError(f"The schema has no group '{group}'.")
        # Keep the preview's context envelope identical to the enrichment
        # prompt. A preview has no build-local values, but it must not use a
        # second, simplified prompt contract.
        context = f"""Document manifest: {json.dumps({}, ensure_ascii=False)}
Build-local editorial conventions confirmed on at least two other records (advisory context only; do not copy unless supported here): {json.dumps({}, ensure_ascii=False)}
Relevant human-confirmed examples retrieved from this build (few-shot guidance only; source evidence in THIS record remains authoritative): {json.dumps({}, ensure_ascii=False)}
How earlier enrichment in this build went (advisory only; evidence in THIS record remains authoritative). Includes reviewer accepted/rejected counts when present, plus values the previous pass inferred on two or more other records (working conventions, not confirmed). Do not copy these; use them only when THIS record's evidence supports the same reading: {json.dumps({}, ensure_ascii=False)}
Human-owned fields on this record (authoritative; DO NOT propose replacements): {json.dumps({}, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps({"previous_record_tail": "", "next_record_head": ""}, ensure_ascii=False)}
Current source block IDs: ["preview-1"]
CURRENT REVIEWED RECORD TEXT:
{text}
"""
        profile = CORPUS_PROFILES[PROFILE_VERSION]
        prompt = build_group_prompt(schema, group, base_context=context, allowed_region_types=list(profile.get("region_types") or []), allowed_discourse_roles=list(profile.get("discourse_roles") or []))
        model_cls = response_model_for(schema, group, region_types=list(profile.get("region_types") or []) or None, roles=list(profile.get("discourse_roles") or []) or None)
        out: dict[str, Any] = {"prompt": prompt, "answer_schema": model_cls.model_json_schema(), "ran": False}
        if not run:
            return out
        started = time.monotonic()
        active = self._interactive_llm_request("", request or None)
        result = self._chat_json(active, prompt, response_model=model_cls, max_tokens=int(_stage_limits(active).get("indexing_num_predict", 1200)), schema_name=f"derridai_record_{group}", build_id="")
        return {**out, "ran": True, "answer": result, "seconds": round(time.monotonic() - started, 1)}


    def _edit_model(self, build_id: str) -> type[BaseModel]:
        return edit_model(self._schema_for(build_id), RecordMetadataModel)


    def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]:
        """The build's profile, with the fields a person must review taken from its schema."""
        base = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
        schema = self._schema_of_build(build)
        return {**base, "review_metadata_fields": schema.review_fields(), "attribution_evidence_fields": sorted(schema.attribution_fields()), "schema_field_names": schema.field_names()}

    def _profile_for(self, build_id: str) -> dict[str, Any]:
        return self._profile_of_build(self.repo.get_build(build_id))


    def _adaptive_family_should_skip(self, build_id: str | None, family: str, request: dict[str, Any]) -> tuple[bool, str]:
        # A selective user-requested rerun is an explicit instruction and must
        # bypass the build's automatic low-yield routing policy.
        if not build_id or request.get("families") or str(request.get("enrichment_mode") or "fast") != "fast":
            return False, ""
        try:
            build = self.repo.get_build(build_id)
        except Exception:
            # Adaptive routing is a performance optimization only. If its metrics
            # cannot be read, run the metadata family rather than suppressing
            # scholarly analysis on the basis of unavailable telemetry.
            return False, ""
        stats = build.get("llm_family_effectiveness") if isinstance(build.get("llm_family_effectiveness"), dict) else {}
        family_stats = stats.get(family) if isinstance(stats.get(family), dict) else {}
        calls = int(family_stats.get("calls") or 0)
        proposed = int(family_stats.get("proposed_fields") or 0)
        human_accepted = int(family_stats.get("human_accepted_fields") or 0)
        human_corrected = int(family_stats.get("human_corrected_fields") or 0)
        # Do not learn from tiny samples. Once a family has repeatedly produced
        # almost no usable material, Fast mode defers it instead of continuing
        # to spend provider time. A human can always explicitly rerun that family.
        if calls >= 5 and proposed / max(1, calls) < 0.25:
            return True, f"Adaptive Fast-mode routing paused {family}: only {proposed} proposed field(s) across {calls} completed call(s)."
        reviewed = human_accepted + human_corrected
        if calls >= 8 and reviewed >= 4 and human_accepted / max(1, reviewed) < 0.20:
            return True, f"Adaptive Fast-mode routing paused {family}: reviewers usually corrected or rejected its suggestions."
        return False, ""

    def _record_family_effectiveness(self, build_id: str | None, family: str, result: dict[str, Any] | None, *, elapsed_ms: int = 0, provider_profile_id: str = "", provider: str = "", model: str = "") -> None:
        if not build_id:
            return
        metadata = result.get("metadata") if isinstance(result, dict) and isinstance(result.get("metadata"), dict) else {}
        proposed = sum(1 for value in metadata.values() if value not in (None, "", []))
        with self._lock:
            try:
                build = self.repo.get_build(build_id)
            except Exception:
                # Effectiveness telemetry never determines record truth. Losing
                # this optional metric must not fail otherwise valid enrichment.
                return
            stats = build.get("llm_family_effectiveness") if isinstance(build.get("llm_family_effectiveness"), dict) else {}
            family_stats = stats.get(family) if isinstance(stats.get(family), dict) else {}
            family_stats["calls"] = int(family_stats.get("calls") or 0) + 1
            family_stats["proposed_fields"] = int(family_stats.get("proposed_fields") or 0) + proposed
            family_stats["elapsed_ms"] = int(family_stats.get("elapsed_ms") or 0) + int(elapsed_ms or 0)
            family_stats["last_updated_at"] = iso_now()
            stats[family] = family_stats
            build["llm_family_effectiveness"] = stats
            model_stats = build.get("llm_model_effectiveness") if isinstance(build.get("llm_model_effectiveness"), dict) else {}
            model_key = "::".join(value for value in (str(provider_profile_id or ""), str(provider or ""), str(model or "")) if value) or "unknown"
            model_row = model_stats.get(model_key) if isinstance(model_stats.get(model_key), dict) else {}
            model_row["provider_profile_id"] = provider_profile_id or None
            model_row["provider"] = provider or None
            model_row["model"] = model or None
            model_row["calls"] = int(model_row.get("calls") or 0) + 1
            model_row["proposed_fields"] = int(model_row.get("proposed_fields") or 0) + proposed
            model_row["elapsed_ms"] = int(model_row.get("elapsed_ms") or 0) + int(elapsed_ms or 0)
            model_stats[model_key] = model_row
            build["llm_model_effectiveness"] = model_stats
            self.repo.save_build(build)

    def _record_human_llm_feedback(self, build_id: str, field: str, prior_value: Any, new_value: Any, prior_status: dict[str, Any] | None, record: dict[str, Any] | None = None) -> None:
        info = prior_status or {}
        method = str(info.get("method") or "")
        state = str(info.get("status") or "")
        if "llm" not in method and state != "model_inferred":
            return
        if info.get("blind") and info.get("model") and record is not None:
            sealed = self._ledger.sealed_value(build_id, str(record.get("record_id") or ""), field)
            self._ledger.append(BLIND_LABEL, model=str(info["model"]), field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=sealed, new_value=new_value, agreed=sealed == new_value, severity=None if sealed == new_value else error_severity(sealed, new_value), **(info.get("conditions") or {}))
            record.setdefault("blind_reveals", {})[field] = sealed  # now that they have decided, the reviewer may see it
            return
        kept = prior_value == new_value
        if info.get("model"):
            kind = ACCEPTED if kept else (REJECTED if new_value in (None, "", []) else CORRECTED)
            self._ledger.append(kind, model=str(info["model"]), field=field, build_id=build_id, record_id=str((record or {}).get("record_id") or ""), confidence=info.get("confidence"), autofilled=bool(info.get("autofilled")), value=prior_value, new_value=new_value, severity=None if kept else error_severity(prior_value, new_value), **(info.get("conditions") or {}))
        if record is not None and not kept and prior_value not in (None, "", []):
            # Remembered: the next pass is shown this as a value people turned down, and it lowers the
            # model's blended confidence on this field through the ledger.
            rejections = [r for r in record.get("llm_rejections") or [] if isinstance(r, dict)]
            rejections.append({"field": field, "rejected_value": prior_value, "chosen_value": new_value, "model": info.get("model"), "at": iso_now()})
            record["llm_rejections"] = rejections[-40:]
        family = next((name for name, fields in self._schema_for(build_id).family_fields().items() if field in fields), None)
        if not family:
            return
        key = "human_accepted_fields" if kept else "human_corrected_fields"
        with self._lock:
            try:
                build = self.repo.get_build(build_id)
            except Exception:
                # Calibration telemetry is advisory analytics only; reviewer-owned
                # metadata has already been committed before this bookkeeping runs.
                return
            stats = build.get("llm_family_effectiveness") if isinstance(build.get("llm_family_effectiveness"), dict) else {}
            family_stats = stats.get(family) if isinstance(stats.get(family), dict) else {}
            family_stats[key] = int(family_stats.get(key) or 0) + 1
            family_stats["last_human_feedback_at"] = iso_now()
            stats[family] = family_stats
            build["llm_family_effectiveness"] = stats
            confidence = info.get("confidence") if isinstance(info.get("confidence"), (int, float)) else None
            calibration = build.get("llm_confidence_calibration") if isinstance(build.get("llm_confidence_calibration"), dict) else {}
            field_stats = calibration.get(field) if isinstance(calibration.get(field), dict) else {}
            if confidence is not None:
                pct = max(0.0, min(1.0, float(confidence)))
                band = "high" if pct >= 0.85 else "medium" if pct >= 0.65 else "low"
                band_stats = field_stats.get(band) if isinstance(field_stats.get(band), dict) else {}
                band_stats["reviewed"] = int(band_stats.get("reviewed") or 0) + 1
                if prior_value == new_value:
                    band_stats["accepted"] = int(band_stats.get("accepted") or 0) + 1
                else:
                    band_stats["corrected"] = int(band_stats.get("corrected") or 0) + 1
                band_stats["acceptance_rate"] = round(int(band_stats.get("accepted") or 0) / max(1, int(band_stats.get("reviewed") or 0)), 4)
                field_stats[band] = band_stats
                calibration[field] = field_stats
                build["llm_confidence_calibration"] = calibration
            self.repo.save_build(build)


    @classmethod
    def _refresh_workflow_fields(cls, build: dict[str, Any]) -> dict[str, Any]:
        """Persist one coherent, machine-readable corpus workflow/readiness model.

        UI stages are derived from independent facts rather than one overloaded
        status string. This keeps refreshes, retries, review completion and
        publication snapshots consistent.
        """
        record_count = int(build.get("record_count") or 0)
        accepted = int(build.get("accepted_count") or 0)
        rejected = int(build.get("rejected_count") or 0)
        reviewed = min(record_count, accepted + rejected)
        pending = max(0, record_count - reviewed)
        metadata_total = int(build.get("metadata_total") or record_count or 0)
        metadata_completed = int(build.get("metadata_completed") or 0)
        issue_summary_present = isinstance(build.get("metadata_issue_summary"), dict)
        issue_summary = build.get("metadata_issue_summary") if issue_summary_present else {}
        unresolved_fields = int(issue_summary.get("fields_unresolved") or 0)
        # Once the issue summary exists it is the authoritative publication-facing
        # metadata state. A stale worker counter must never manufacture blockers.
        metadata_remaining = int(issue_summary.get("records_incomplete") or 0) if issue_summary_present else max(0, metadata_total - metadata_completed)
        validation = build.get("validation") if isinstance(build.get("validation"), dict) else {}
        _ = build.get("source_quality") if isinstance(build.get("source_quality"), dict) else {}
        publication = build.get("publication") if isinstance(build.get("publication"), dict) else None
        running = str(build.get("status") or "") in {"queued", "running"}
        stage = str(build.get("stage") or "")
        profile = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES.get(PROFILE_VERSION, {}))
        required_fields = list(profile.get("publication_required_metadata_fields") or profile.get("required_metadata_fields") or [])
        required_document_fields = list(profile.get("publication_required_document_fields") or [])
        manifest = build.get("manifest") if isinstance(build.get("manifest"), dict) else {}
        missing_document_fields = [field for field in required_document_fields if manifest.get(field) in (None, "", [])]

        blockers: list[dict[str, Any]] = []
        no_publishable_records = bool(record_count and rejected == record_count and accepted == 0 and pending == 0)
        if no_publishable_records:
            blockers.append({"code": "no_publishable_records", "count": rejected})
        if pending:
            blockers.append({"code": "review_pending", "count": pending})
        # Rejected records are intentionally excluded from the publishable corpus.
        # They remain recoverable in review, but do not block publication of
        # accepted records. An all-rejected build is handled as a terminal
        # "no publishable records" outcome above.
        if int(build.get("needs_review_count") or 0):
            blockers.append({"code": "record_attention", "count": int(build.get("needs_review_count") or 0)})
        if int(build.get("boundary_review_count") or 0):
            blockers.append({"code": "boundary_attention", "count": int(build.get("boundary_review_count") or 0)})
        if (metadata_remaining or unresolved_fields) and not no_publishable_records:
            blockers.append({"code": "required_metadata", "count": max(metadata_remaining, int(issue_summary.get("records_incomplete") or 0)), "fields": required_fields})
        if missing_document_fields:
            blockers.append({"code": "required_document_metadata", "count": len(missing_document_fields), "fields": missing_document_fields})
        if validation and not bool(validation.get("source_valid", validation.get("valid", True))):
            blockers.append({"code": "source_validation", "count": len(validation.get("missing_block_ids") or []) + len(validation.get("text_fidelity_errors") or []) + len(validation.get("source_order_errors") or [])})
        if validation and not bool(validation.get("metadata_valid", validation.get("valid", True))):
            blockers.append({"code": "metadata_validation", "count": sum(len(validation.get(key) or []) for key in ("metadata_evidence_errors", "metadata_schema_errors", "citation_errors", "relationship_errors", "human_ownership_errors", "record_content_errors"))})
        # Raw PDF extraction findings remain in build.source_quality for audit,
        # but a reviewer may resolve a record-level extraction problem by
        # correcting the reviewed text while preserving source_extracted_text.
        # Publication is therefore gated by unresolved record source issues, not
        # forever by the immutable raw-page diagnostic.
        if int(build.get("source_problem_count") or 0):
            blockers.append({"code": "source_quality", "count": int(build.get("source_problem_count") or 0)})

        can_publish = bool(accepted > 0 and pending == 0 and not blockers and bool(validation.get("valid", True)) and accepted + rejected == record_count)
        if publication:
            next_action = "download_publication"
        elif no_publishable_records:
            next_action = "no_publishable_records"
        elif running:
            next_action = "wait"
        elif pending or int(build.get("needs_review_count") or 0) or int(build.get("boundary_review_count") or 0) or metadata_remaining or unresolved_fields:
            next_action = "review_records"
        elif missing_document_fields:
            next_action = "resolve_document_metadata"
        elif blockers:
            next_action = "resolve_validation"
        elif can_publish:
            next_action = "publish"
        else:
            next_action = "inspect"

        extraction_state = "complete" if int(build.get("source_block_count") or 0) else ("active" if running and stage in {"structure", "document_review"} else "waiting")
        construction_state = "complete" if record_count else ("active" if running and stage in {"segmenting", "reconciling"} else "waiting")
        enrichment_state = "complete" if metadata_total and metadata_remaining == 0 else ("active" if running and stage in {"enriching", "metadata_retry"} else "attention" if record_count else "waiting")
        review_state = "complete" if record_count and pending == 0 else ("attention" if record_count else "waiting")
        validation_state = "complete" if validation.get("valid") else ("blocked" if validation else "waiting")
        publication_state = "complete" if publication else ("active" if can_publish else "blocked" if record_count else "waiting")
        build["pipeline_state"] = {
            "current": next_action,
            "stages": {
                "extraction": {"state": extraction_state},
                "construction": {"state": construction_state},
                "enrichment": {"state": enrichment_state, "remaining_records": metadata_remaining, "unresolved_fields": unresolved_fields},
                "review": {"state": review_state, "reviewed": reviewed, "pending": pending, "accepted": accepted, "rejected": rejected},
                "validation": {"state": validation_state},
                "publication": {"state": publication_state},
            },
        }
        build["publication_readiness"] = {
            "can_publish": can_publish,
            "next_action": next_action,
            "blockers": blockers,
            "required_metadata_fields": required_fields,
            "required_document_fields": required_document_fields,
            "missing_document_fields": missing_document_fields,
            "records_total": record_count,
            "records_reviewed": reviewed,
            "records_accepted": accepted,
            "records_rejected": rejected,
            "records_pending": pending,
            "metadata_records_remaining": metadata_remaining,
            "metadata_fields_unresolved": unresolved_fields,
            "source_valid": bool(validation.get("source_valid", validation.get("valid", False))) if validation else False,
            "metadata_valid": bool(validation.get("metadata_valid", validation.get("valid", False))) if validation else False,
            "published": bool(publication),
            "no_publishable_records": no_publishable_records,
        }
        return build

    def _update(self, build_id: str, **changes: Any) -> dict[str, Any]:
        # Metadata workers update telemetry and warnings concurrently. Serialize
        # read/modify/write of build.json so one worker cannot erase another
        # worker's metric, progress, or recovery flag.
        with self._lock:
            build = self.repo.get_build(build_id)
            prior_stage = str(build.get("stage") or "")
            prior_status = str(build.get("status") or "")
            stage = changes.get("stage")
            progress = changes.get("progress")
            if stage is not None:
                build["stage"] = stage
            if progress is not None:
                build["progress"] = max(0.0, min(1.0, float(progress)))
            build.update(changes)
            current_stage = str(build.get("stage") or "")
            current_status = str(build.get("status") or "")
            if current_stage != prior_stage or current_status != prior_status:
                events = list(build.get("build_events") or [])
                events.append({
                    "at": iso_now(),
                    "stage": current_stage,
                    "status": current_status,
                    "progress": round(float(build.get("progress") or 0.0), 4),
                })
                build["build_events"] = events[-120:]
            self._refresh_workflow_fields(build)
            self.repo.save_build(build)
            return build


    def _append_warning(self, build_id: str, message: str) -> None:
        with self._lock:
            build = self.repo.get_build(build_id)
            warnings = list(build.get("warnings") or [])
            if message not in warnings:
                warnings.append(message)
            build["warnings"] = warnings[-100:]
            self.repo.save_build(build)

    def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None:
        if not build_id:
            return
        with self._lock:
            build = self.repo.get_build(build_id)
            metrics = dict(build.get("llm_metrics") or {})
            metrics[key] = int(metrics.get(key) or 0) + int(amount)
            build["llm_metrics"] = metrics
            self.repo.save_build(build)

    def _chat_json(
        self,
        request: dict[str, Any],
        prompt: str,
        *,
        response_model: type[BaseModel],
        max_tokens: int = 4096,
        schema_name: str = "derridai_corpus",
        attempts: int = 2,
        build_id: str = "",
    ) -> dict[str, Any]:
        """Generate and validate typed structured output with bounded retry/escalation.

        A malformed or transient model turn must not destroy a book-length build.
        Provider-native JSON Schema is requested when supported, every response is
        Pydantic-validated, and an optional separately configured review provider
        receives the same source-bound task only after the primary provider has
        exhausted its attempts.
        """
        schema = response_model.model_json_schema()
        request_chain: list[tuple[str, dict[str, Any]]] = [("primary", request)]
        reviewer = request.get("_review_provider")
        if isinstance(reviewer, dict) and reviewer:
            request_chain.append(("review", reviewer))
        all_failures: list[str] = []
        for chain_index, (role, active_request) in enumerate(request_chain):
            provider, model, base_url, api_key, generation = _llm_config(active_request)
            if chain_index > 0 and build_id:
                self._increment_metric(build_id, "escalations")
            failure: Exception | None = None
            diagnostic = ""
            for attempt in range(1, max(1, attempts) + 1):
                if build_id and self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")
                retry_note = ""
                if chain_index > 0 and attempt == 1:
                    retry_note = (
                        "\n\nESCALATION REVIEW: a first-pass model could not produce a valid structured "
                        "answer. Independently perform the task from the supplied source evidence and "
                        "return ONLY one complete JSON object matching the schema."
                    )
                elif attempt > 1:
                    retry_note = (
                        "\n\nIMPORTANT CORRECTION: the previous response could not be validated. "
                        f"Validation error: {failure}. Return ONLY one complete JSON object that exactly "
                        "matches the supplied schema. Do not include Markdown, commentary, or trailing text."
                    )
                    if "field_evidence" in str(failure):
                        retry_note += (
                            "\nThe validation error concerns evidence, not the metadata value. For every "
                            "field whose assessment outcome is supported_value and whose schema requires "
                            "evidence, include a field_evidence object with at least one valid current-record "
                            "block_id. Use the block IDs shown in the source context; never invent IDs and "
                            "never omit the evidence object for a supported value."
                        )
                    if diagnostic:
                        retry_note += f"\nPrevious response excerpt: {diagnostic[:1200]}"
                try:
                    if build_id:
                        self._increment_metric(build_id, "calls")
                        metric_stage = (
                            "manifest" if "manifest" in schema_name else
                            "segmentation" if ("boundar" in schema_name or "segment" in schema_name or "reconciliation" in schema_name) else
                            "metadata" if "record_" in schema_name else
                            "other"
                        )
                        self._increment_metric(build_id, f"{metric_stage}_calls")
                        if "record_discourse" in schema_name:
                            self._increment_metric(build_id, "discourse_calls")
                        elif "record_quotation" in schema_name:
                            self._increment_metric(build_id, "quotation_calls")
                        elif "record_indexing" in schema_name:
                            self._increment_metric(build_id, "indexing_calls")
                        if attempt > 1:
                            self._increment_metric(build_id, "retries")
                    timeout_key = (
                        "manifest" if "manifest" in schema_name else
                        "reconciliation" if "reconciliation" in schema_name else
                        "segmentation" if ("boundar" in schema_name or "segment" in schema_name) else
                        "discourse" if "record_discourse" in schema_name else
                        "quotation" if "record_quotation" in schema_name else
                        "indexing" if "record_indexing" in schema_name else "indexing"
                    )
                    call_token = self._note_llm_call_start(build_id, metric_stage_of(schema_name), provider, model, base_url)
                    try:
                        raw = self._with_transport_retry(build_id, chat_complete, 
                            provider=provider,
                            model=model,
                            base_url=base_url,
                            api_key=api_key,
                            prompt=prompt + retry_note,
                            options=generation,
                            json_mode=True,
                            json_schema=schema,
                            schema_name=schema_name,
                            max_tokens=min(8192, max_tokens + ((attempt - 1) * 1024)),
                            cancelled=(lambda: self._cancelled(build_id)) if build_id else None,
                            timeout_seconds=float(_stage_timeouts(request).get(timeout_key, 240)),
                        )
                    finally:
                        self._note_llm_call_end(build_id, call_token)
                except InterruptedError:
                    raise
                except Exception as exc:
                    failure = exc
                    diagnostic = ""
                    # A hard read timeout already consumed the stage budget. Repeating
                    # the same expensive request obscures stalls rather than improving
                    # resilience; settle it for human review instead.
                    if "timeout" in type(exc).__name__.casefold() or "timed out" in str(exc).casefold():
                        if build_id:
                            self._increment_metric(build_id, "timeouts")
                        break
                    if attempt < max(1, attempts):
                        time.sleep(min(2.0, 0.35 * attempt))
                        continue
                    break
                diagnostic = str(raw or "")
                try:
                    value = _parse_json_robust(raw)
                    parsed = response_model.model_validate(value)
                    return parsed.model_dump(mode="json")
                except (ValueError, ValidationError) as exc:
                    failure = exc
                    if build_id:
                        self._increment_metric(build_id, "structured_output_failures")
            all_failures.append(f"{role} {provider}/{model}: {failure}")
        raise ValueError(
            "LLM structured output failed after bounded retry"
            + (" and review-provider escalation" if len(request_chain) > 1 else "")
            + ": " + " | ".join(all_failures)
        )

    def _document_manifest(self, asset: dict[str, Any], blocks: list[dict[str, Any]], request: dict[str, Any], build_id: str) -> dict[str, Any]:
        metadata = asset.get("metadata") or {}
        reviewed_layout = asset.get("document_layout") if isinstance(asset.get("document_layout"), dict) and asset.get("document_layout", {}).get("confirmed_by") == "human" else {}
        # Sample the whole document rather than assuming the front matter is
        # representative. Headings plus front/middle/end blocks reveal later
        # section transitions, notes and bibliographic regions without sending a
        # book-sized prompt.
        chosen: list[dict[str, Any]] = []
        seen: set[str] = set()
        def add_many(items: list[dict[str, Any]]) -> None:
            for block in items:
                block_id = str(block.get("block_id") or "")
                if block_id and block_id not in seen:
                    chosen.append(block)
                    seen.add(block_id)
        add_many(blocks[:40])
        add_many([block for block in blocks if block.get("type") == "heading"][:50])
        midpoint = max(0, len(blocks) // 2 - 15)
        add_many(blocks[midpoint:midpoint + 30])
        add_many(blocks[-40:])
        chosen = sorted(chosen[:140], key=lambda b: (int(b.get("page") or 0), str(b.get("block_id") or "")))
        limits = _stage_limits(request)
        context = _context_window(request)
        # Keep manifest analysis representative across the whole book even on
        # smaller local contexts. We reduce the number/size of excerpts rather
        # than truncating the end of a front-loaded prompt.
        manifest_input_tokens = 12000 if not context else max(2200, min(12000, context - limits["manifest_num_predict"] - 1800))
        sample_char_budget = max(8000, manifest_input_tokens * 4)
        if chosen:
            max_samples = max(12, min(len(chosen), sample_char_budget // 720))
            if len(chosen) > max_samples:
                indices = sorted({round(i * (len(chosen) - 1) / max(1, max_samples - 1)) for i in range(max_samples)})
                chosen = [chosen[index] for index in indices]
        per_excerpt = max(280, min(900, sample_char_budget // max(1, len(chosen)) - 100))
        sample_text = "\n".join(
            f"[{b['block_id']} PDF p.{b['page']} label={b.get('printed_page_label')!r} {b['type']}] {str(b.get('text') or '')[:per_excerpt]}"
            for b in chosen
        )[:sample_char_budget]
        prompt = f"""You are establishing a source-bound document manifest for an auditable scholarly corpus build.
Use only evidence in the supplied PDF metadata and source blocks. Use null when unsupported. Never fill bibliographic facts from general knowledge. Distinguish the PDF page index from a printed page label. The manifest will be inherited deterministically by generated records, so be conservative.

PDF metadata: {json.dumps(metadata, ensure_ascii=False)}
Filename: {asset.get('filename')}
Reviewer-confirmed document structure (authoritative where present): {json.dumps(reviewed_layout, ensure_ascii=False)}
Strategic whole-document sample:
{sample_text}

Return one JSON object matching the schema. `main_text_start_page` and `main_text_end_page` are physical PDF pages when supported. `document_is_translation` should be null unless the source itself supports that conclusion.
"""
        try:
            result = self._chat_json(
                request,
                prompt,
                response_model=DocumentManifestModel,
                max_tokens=limits["manifest_num_predict"],
                schema_name="derridai_document_manifest",
                build_id=build_id,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            self._append_warning(build_id, f"Document manifest used PDF-metadata fallback: {exc}")
            result = DocumentManifestModel(
                title=metadata.get("title") or None,
                document_author=metadata.get("author") or None,
                notes="LLM manifest unavailable; values are limited to embedded PDF metadata.",
            ).model_dump(mode="json")
        # Embedded PDF metadata is a deterministic source assertion. A model
        # may enrich missing bibliography, but must not replace an author
        # explicitly declared by the source file.
        if metadata.get("author"):
            result["document_author"] = str(metadata["author"]).strip()
            result["document_author_source"] = "pdf_metadata"
            result["document_author_confidence"] = 1.0
            result["document_author_assertion"] = {
                "field": "document_author",
                "value": result["document_author"],
                "status": "deterministic",
                "method": "pdf_metadata",
                "checked": True,
                "confidence": 1.0,
                "reason": "Author value was read from embedded PDF metadata.",
            }
        # A deterministic start-page inference (only present when it is more than 90% sure) outranks
        # the model's guess; the clues travel with the value so the reviewer can check them.
        inferred = asset.get("main_text_start_inference")
        if isinstance(inferred, dict) and inferred.get("offered") and isinstance(inferred.get("page"), int):
            result["main_text_start_page"] = inferred["page"]
            result["main_text_start_inference"] = {key: inferred.get(key) for key in ("page", "confidence", "clues")}
        # Human-confirmed document structure outranks LLM page-range inference.
        if reviewed_layout:
            layout_start = reviewed_layout.get("main_text_pdf_start")
            bibliography_start = reviewed_layout.get("bibliography_pdf_start")
            if isinstance(layout_start, int):
                result["main_text_start_page"] = layout_start
                # A reviewer-defined start with no bibliography/end marker means
                # the main text remains open-ended; do not preserve an LLM-guessed
                # end page that could reclassify later records as apparatus.
                result["main_text_end_page"] = None
            if isinstance(bibliography_start, int) and bibliography_start > 1:
                result["main_text_end_page"] = bibliography_start - 1
        result["pdf_metadata"] = metadata
        result["source_asset_id"] = asset["asset_id"]
        result["sampled_block_ids"] = [block["block_id"] for block in chosen]
        from .source_media import apply_deterministic_ingest_metadata
        return apply_deterministic_ingest_metadata(result, asset)

    def _catalog_enrich_manifest(self, manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> dict[str, Any]:
        """Fill missing work-level bibliography through the same multi-catalog LLM path used by Works.

        Source-derived manifest values remain authoritative. Public catalogue values only
        fill blanks and are recorded separately for audit. Catalogue/network failure is
        non-fatal and never pauses corpus construction.
        """
        title = str(manifest.get("title") or manifest.get("document_title") or "").strip()
        if not title:
            return manifest
        current = {
            "document_title": manifest.get("title"),
            "short_title": manifest.get("short_title"),
            "original_title": manifest.get("original_title"),
            "document_author": manifest.get("document_author"),
            "document_type": manifest.get("document_type"),
            "publisher": manifest.get("publisher"),
            "publication_place": manifest.get("publication_place"),
            "publication_year": manifest.get("publication_year"),
            "edition": manifest.get("edition"),
            "translator": manifest.get("translator"),
            "isbn": manifest.get("isbn"),
            "document_language": manifest.get("language"),
            "original_language": manifest.get("original_language"),
            "document_is_translation": manifest.get("document_is_translation"),
        }
        try:
            # Local import keeps the corpus builder lightweight in test/runtime
            # contexts that do not initialize Chroma until the Works tool is used.
            from .llm_tools import run_work_metadata_lookup
            generation = request.get("generation")
            body = WorkMetadataRequest(
                works=[WorkMetadataSeed(work=title, current_metadata=current)],
                provider=request.get("provider") or "ollama",
                model=request.get("model"),
                base_url=request.get("base_url"),
                api_key=request.get("api_key"),
                generation=generation,
                provider_profile_id=request.get("provider_profile_id"),
            )
            proposal = run_work_metadata_lookup(
                body.works[0], body,
                cancelled=(lambda: self._cancelled(build_id)) if build_id else None,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            self._append_warning(build_id, f"Automatic bibliographic lookup was unavailable; continuing with source-derived metadata ({exc}).")
            return manifest
        changes = proposal.get("changes") if isinstance(proposal.get("changes"), dict) else {}
        mapping = {
            "document_title": "title", "short_title": "short_title", "original_title": "original_title",
            "document_author": "document_author", "document_type": "document_type", "publisher": "publisher",
            "publication_place": "publication_place", "publication_year": "publication_year", "edition": "edition",
            "translator": "translator", "isbn": "isbn", "document_language": "language",
            "original_language": "original_language", "document_is_translation": "document_is_translation",
        }
        applied: dict[str, Any] = {}
        for source_field, manifest_field in mapping.items():
            proposed = changes.get(source_field)
            if proposed in (None, "", []):
                continue
            if manifest.get(manifest_field) in (None, "", []):
                manifest[manifest_field] = proposed
                applied[manifest_field] = proposed
        manifest["catalog_metadata"] = {
            "source": proposal.get("catalog_source"),
            "sources_tried": proposal.get("catalog_sources_tried") or [],
            "confidence": proposal.get("confidence"),
            "match_reason": proposal.get("match_reason") or proposal.get("message"),
            "applied_missing_fields": applied,
        }
        return manifest


    def _compact_segment_prompt(self, window: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
        block_text = "\n\n".join(
            f"[{b['block_id']} | PDF p.{b['page']} | {b['type']}]\n{b['text']}"
            for b in window
        )
        manifest_summary = {
            key: manifest.get(key)
            for key in ("title", "document_author", "translator", "language", "document_type")
            if manifest.get(key) not in (None, "")
        }
        return f"""You are a conservative semantic-boundary auditor for a Derrida scholarly corpus.
Judge only genuine discourse boundaries. Split when one coherent argumentative/discursive unit ends because of a meaningful change in speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move. NEVER split because a page changes, an execution window ends, or text reaches a size. Keep a quotation with the attribution needed to understand who owns the quoted proposition.

Document context: {json.dumps(manifest_summary, ensure_ascii=False)}

SOURCE BLOCKS (immutable IDs):
{block_text}

Return a COMPACT JSON object containing ONLY transitions that plausibly need a split or explicit review. Omit ordinary KEEP transitions. For each returned transition use: `after` (the exact left-hand source block ID), `decision` (`split` or `uncertain`), `confidence` (0..1), and `changes` (zero or more of speaker, position_holder, stance, target, quotation_frame, discourse_role, argumentative_move). An omitted transition is deterministically treated as KEEP. Do not return source text, prose explanations, Markdown, or invented IDs.
"""

    def _segment_pair(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        prompt = f"""Classify ONE possible semantic record boundary in a Derrida scholarly corpus.
Do not use page changes or length as evidence. Decide whether the second source block begins a new coherent discourse/argument unit because of a meaningful change in speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move.

LEFT [{left['block_id']}]:\n{str(left.get('text') or '')[:7000]}

RIGHT [{right['block_id']}]:\n{str(right.get('text') or '')[:7000]}

Return only `decision`, `confidence`, and `changes` in the supplied schema.
"""
        limits = _stage_limits(request)
        try:
            result = self._chat_json(
                request,
                prompt,
                response_model=PairBoundaryResponseModel,
                max_tokens=min(700, limits["segmentation_num_predict"]),
                schema_name="derridai_boundary_pair",
                attempts=2,
                build_id=build_id,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            return None, {
                "after_block_id": left["block_id"],
                "next_block_id": right["block_id"],
                "reason": str(exc),
                "kind": "pair",
            }
        return {
            "after_block_id": left["block_id"],
            "decision": str(result.get("decision") or "uncertain"),
            "confidence": max(0.0, min(1.0, float(result.get("confidence") or 0))),
            "changes": list(result.get("changes") or []),
            "source": "pair_fallback",
        }, None

    def _segment_window_recursive(
        self,
        window: list[dict[str, Any]],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
        *,
        depth: int = 0,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        limits = _stage_limits(request)
        block_ids = {str(block.get("block_id") or "") for block in window}
        try:
            result = self._chat_json(
                request,
                self._compact_segment_prompt(window, manifest),
                response_model=CompactSegmentationResponseModel,
                max_tokens=limits["segmentation_num_predict"],
                schema_name="derridai_semantic_boundaries_compact",
                attempts=2,
                build_id=build_id,
            )
            candidates: list[dict[str, Any]] = []
            returned: set[str] = set()
            for item in result.get("boundaries") or []:
                block_id = str(item.get("after") or "")
                if block_id not in block_ids or block_id == str(window[-1].get("block_id") or ""):
                    continue
                returned.add(block_id)
                candidates.append({
                    "after_block_id": block_id,
                    "decision": str(item.get("decision") or "uncertain"),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                    "changes": list(item.get("changes") or []),
                    "source": "compact_window",
                    "depth": depth,
                })
            # Omitted transitions are ordinary KEEP decisions. Requiring a model
            # to echo every no-op transition made output scale with document length
            # and caused exactly the failure cascade this compact stage is intended
            # to avoid. Only explicit split/uncertain proposals are returned.
            return candidates, []
        except InterruptedError:
            raise
        except Exception as exc:
            self._increment_metric(build_id, "segmentation_window_failures")
            # A malformed large response should become a smaller problem, not a
            # missing slice of the book. Recursively divide the source evidence.
            if len(window) > 6 and depth < 4:
                midpoint = len(window) // 2
                left = window[:min(len(window), midpoint + 2)]
                right = window[max(0, midpoint - 1):]
                left_candidates, left_unresolved = self._segment_window_recursive(
                    left, manifest, request, build_id, depth=depth + 1
                )
                right_candidates, right_unresolved = self._segment_window_recursive(
                    right, manifest, request, build_id, depth=depth + 1
                )
                return left_candidates + right_candidates, left_unresolved + right_unresolved

            # At the minimum window size, classify each transition independently.
            # These tiny schemas are intentionally difficult for a model to truncate.
            pair_candidates: list[dict[str, Any]] = []
            unresolved: list[dict[str, Any]] = []
            for left, right in zip(window, window[1:]):
                candidate, failure = self._segment_pair(left, right, manifest, request, build_id)
                if candidate:
                    pair_candidates.append(candidate)
                if failure:
                    unresolved.append(failure)
            if unresolved:
                unresolved.append({
                    "after_block_id": str(window[0].get("block_id") or ""),
                    "next_block_id": str(window[-1].get("block_id") or ""),
                    "reason": f"Window remained unresolved after recursive reduction: {exc}",
                    "kind": "window",
                })
            return pair_candidates, unresolved


    def _boundary_cache_fingerprint(self, left: dict[str, Any], right: dict[str, Any], request: dict[str, Any]) -> str:
        generation = _generation_options(request)
        payload = {
            "prompt": SEGMENTATION_PROMPT_VERSION,
            "left_id": left.get("block_id"), "left_text": left.get("text"),
            "right_id": right.get("block_id"), "right_text": right.get("text"),
            "provider": request.get("provider"), "model": request.get("model"),
            "temperature": generation.temperature, "top_p": generation.top_p,
            "top_k": generation.top_k, "seed": generation.seed,
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _segment_candidate_batch(
        self,
        batch: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Adjudicate a small set of already-filtered transitions in one call.

        The schema is intentionally binary. If the model cannot support SPLIT,
        returns malformed output, omits an item, or attempts an `uncertain` value,
        the transition deterministically remains KEEP.
        """
        items=[]
        for c in batch:
            i=int(c["index"])
            left,right=blocks[i],blocks[i+1]
            items.append(
                f"TRANSITION {left['block_id']} -> {right['block_id']}\n"
                f"Signals: {', '.join(c.get('signals') or [])}\n"
                f"LEFT:\n{str(left.get('text') or '')[-3200:]}\nRIGHT:\n{str(right.get('text') or '')[:3200]}"
            )
        context={k:manifest.get(k) for k in ("title","document_author","language","document_type") if manifest.get(k) not in (None,"")}
        prompt=f"""You are a conservative semantic-boundary adjudicator for an auditable Derrida corpus.
Python has already filtered out ordinary prose and protected attribution-sensitive seams. For each listed transition choose SPLIT only when the right block clearly begins a new coherent discourse/argument unit because of a meaningful change in speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move. Otherwise choose KEEP. Page changes and text length are never evidence. When in doubt, KEEP.

Document context: {json.dumps(context, ensure_ascii=False)}

{"\n\n---\n\n".join(items)}

Return one compact decision per transition using its exact left-hand block ID in `after`. Do not return prose or source text."""
        limits=_stage_limits(request)
        try:
            result=self._chat_json(request,prompt,response_model=BoundaryBatchResponseModel,max_tokens=min(limits["segmentation_num_predict"],1400),schema_name="derridai_boundary_batch_v6",attempts=2,build_id=build_id)
        except InterruptedError:
            raise
        except Exception as exc:
            return {},str(exc)
        valid_ids={str(c.get("after_block_id") or "") for c in batch}
        out={}
        for item in result.get("decisions") or []:
            after=str(item.get("after") or "")
            if after not in valid_ids:
                continue
            out[after]={
                "after_block_id":after,
                "decision":str(item.get("decision") or "keep"),
                "confidence":max(0.0,min(1.0,float(item.get("confidence") or 0))),
                "changes":list(item.get("changes") or []),
                "source":"local_batch_classifier",
            }
        return out,None

    def _boundary_editorial_examples(self, build_id: str, limit: int = 3) -> list[dict[str, Any]]:
        checkpoint = self.repo.load_checkpoint(build_id, "boundary_editorial_memory", {})
        if not isinstance(checkpoint, dict):
            return []
        examples = checkpoint.get("examples") if isinstance(checkpoint.get("examples"), list) else []
        return [dict(item) for item in examples[-max(0, limit):] if isinstance(item, dict)]

    def _record_boundary_editorial_example(
        self,
        build_id: str,
        *,
        left: dict[str, Any],
        right: dict[str, Any],
        action: str,
        transaction_id: str,
    ) -> None:
        checkpoint = self.repo.load_checkpoint(build_id, "boundary_editorial_memory", {})
        if not isinstance(checkpoint, dict):
            checkpoint = {}
        examples = list(checkpoint.get("examples") or [])
        examples.append({
            "at": iso_now(),
            "action": action,
            "transaction_id": transaction_id,
            "left_record_id": left.get("record_id"),
            "right_record_id": right.get("record_id"),
            "left_excerpt": str(left.get("text") or "")[-900:],
            "right_excerpt": str(right.get("text") or "")[:900],
            "source": "human_confirmed_boundary",
        })
        self.repo.save_checkpoint(build_id, "boundary_editorial_memory", {"examples": examples[-40:]})


    def _adjudicate_record_boundary_pair(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
    ) -> dict[str, Any]:
        left_ids = [str(value) for value in (left.get("source_block_ids") or []) if value]
        right_ids = [str(value) for value in (right.get("source_block_ids") or []) if value]
        if not left_ids or not right_ids:
            return {
                "decision": "uncertain", "confidence": 0.0,
                "reason": "The adjacent records do not expose source-block boundaries for adjudication.",
                "source": "llm_boundary_audit",
            }
        current_after = left_ids[-1]
        boundary_id = f"{left.get('record_id')}->{right.get('record_id')}"
        candidates = _boundary_audit_candidates(left, right)
        examples = self._boundary_editorial_examples(build_id, 3)
        examples_text = ""
        if examples:
            rendered=[]
            for example in examples:
                rendered.append(
                    f"HUMAN-CONFIRMED EXAMPLE ({example.get('action','boundary edit')}):\n"
                    f"LEFT END: {str(example.get('left_excerpt') or '')[-700:]}\n"
                    f"RIGHT START: {str(example.get('right_excerpt') or '')[:700]}"
                )
            examples_text = "\n\nRelevant editorial examples from this build:\n" + "\n---\n".join(rendered)
        context = {k: manifest.get(k) for k in ("title", "document_author", "language", "document_type") if manifest.get(k) not in (None, "")}
        prompt = f"""You are the second-reader boundary adjudicator for an auditable Derrida corpus.
A deterministic segmentation system has already created two adjacent records. Decide whether the current boundary is semantically coherent.

Use KEEP when the left record ends a coherent discourse unit and the right record begins another.
Use MOVE_EARLIER only when material at the end of the left record clearly belongs with the right record.
Use MOVE_LATER only when material at the start of the right record clearly belongs with the left record.
Use UNCERTAIN when the evidence is genuinely ambiguous.

Strong signals include sentence/paragraph continuation, unfinished quotation framing, speaker or position-holder continuation, a heading stranded with the wrong unit, or an argumentative move that is visibly cut in half. Page boundaries and record length are never semantic evidence. Never rewrite, summarize, or invent text. If recommending a move, choose `suggested_after_block_id` only from the allowed seam IDs.

Document context: {json.dumps(context, ensure_ascii=False)}
Boundary id: {boundary_id}
Current seam after block: {current_after}
Allowed seam IDs: {json.dumps(candidates, ensure_ascii=False)}

LEFT RECORD END:
{str(left.get('text') or '')[-4200:]}

RIGHT RECORD START:
{str(right.get('text') or '')[:4200]}
{examples_text}

Return one decision for the exact boundary id. `signals` should contain compact labels such as sentence_continuation, quotation_continuation, heading_attachment, attribution_continuation, argumentative_transition, or coherent_boundary."""
        limits = _stage_limits(request)
        try:
            result = self._chat_json(
                request, prompt, response_model=BoundaryAuditResponseModel,
                max_tokens=min(int(limits.get("reconciliation_num_predict") or 1000), 1200),
                schema_name="derridai_boundary_second_reader_v1", attempts=2, build_id=build_id,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            return {
                "boundary_id": boundary_id, "decision": "uncertain", "confidence": 0.0,
                "reason": f"Boundary second-reader call failed: {exc}",
                "source": "llm_boundary_audit", "error": str(exc),
            }
        item = next((row for row in (result.get("decisions") or []) if str(row.get("boundary_id") or "") == boundary_id), None)
        if not isinstance(item, dict):
            return {
                "boundary_id": boundary_id, "decision": "uncertain", "confidence": 0.0,
                "reason": "The boundary second reader returned no usable decision.",
                "source": "llm_boundary_audit",
            }
        decision = str(item.get("decision") or "uncertain")
        suggested = str(item.get("suggested_after_block_id") or "").strip() or None
        if decision == "move_earlier":
            valid = [value for value in candidates if value in left_ids and value != current_after]
            if suggested not in valid:
                decision, suggested = "uncertain", None
        elif decision == "move_later":
            valid = [value for value in candidates if value in right_ids[:-1] or value in right_ids[:2]]
            if suggested not in valid:
                decision, suggested = "uncertain", None
        else:
            suggested = current_after if decision == "keep" else None
        return {
            "boundary_id": boundary_id,
            "left_record_id": left.get("record_id"),
            "right_record_id": right.get("record_id"),
            "decision": decision,
            "suggested_after_block_id": suggested,
            "current_after_block_id": current_after,
            "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0.0))),
            "signals": list(item.get("signals") or []),
            "reason": str(item.get("reason") or "").strip(),
            "source": "llm_boundary_audit",
            "editorial_examples_used": len(examples),
            "adjudicated_at": iso_now(),
        }


    def _audit_suspicious_record_boundaries(
        self, records: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str,
    ) -> dict[str, int]:
        threshold = float(self._profile_for(build_id).get("min_boundary_confidence") or 0.72)
        pairs=[]
        for index, (left, right) in enumerate(zip(records, records[1:])):
            left_flags = list(left.get("boundary_quality_issues") or [])
            right_flags = list(right.get("boundary_quality_issues") or [])
            heuristic = any(str(item.get("code") or "") == "boundary_suspect" and str(item.get("edge") or "") == "end" for item in left_flags) or any(str(item.get("code") or "") == "boundary_suspect" and str(item.get("edge") or "") == "start" for item in right_flags)
            unresolved = bool(left.get("boundary_review_after") or right.get("boundary_review_before"))
            if heuristic or unresolved:
                pairs.append((index, left, right))
        # This is a second-reader pass, not another book-scale segmentation pass.
        # Keep it bounded even on pathologically noisy extraction.
        pairs = pairs[:24]
        metrics = {"audited": 0, "keep": 0, "move": 0, "uncertain": 0, "failed": 0}
        decisions=[]
        for _, left, right in pairs:
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            decision = self._adjudicate_record_boundary_pair(left, right, manifest, request, build_id)
            decisions.append(decision)
            metrics["audited"] += 1
            choice = str(decision.get("decision") or "uncertain")
            if decision.get("error"):
                metrics["failed"] += 1
            if choice == "keep":
                metrics["keep"] += 1
            elif choice in {"move_earlier", "move_later"}:
                metrics["move"] += 1
            else:
                metrics["uncertain"] += 1
            _apply_boundary_adjudication_to_records(left, right, decision, threshold=threshold)
        self.repo.save_checkpoint(build_id, "boundary_second_reader", {"decisions": decisions, "metrics": metrics, "completed_at": iso_now()})
        return metrics


    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        """Build topology with deterministic-first routing and bounded LLM work.

        Human review is no longer an output of ordinary model uncertainty. The
        builder owns the topology: protected/weak seams KEEP, obvious structural
        seams SPLIT, and only a budgeted ambiguous subset reaches the LLM. The
        binary classifier's omission/failure/low confidence also means KEEP.
        """
        profile=self._profile_for(build_id)
        threshold=float(profile.get("min_boundary_confidence") or 0.72)
        sizing_policy=_record_sizing_policy(request,profile)
        _=sizing_policy["absolute_record_chars"]
        index_by_id={str(block.get("block_id") or ""):i for i,block in enumerate(blocks)}
        candidates=_deterministic_boundary_candidates(blocks,profile)
        state=self.repo.load_checkpoint(build_id,"local_boundary_state",{})
        if not isinstance(state,dict): state={}
        decisions=state.get("decisions") if isinstance(state.get("decisions"),dict) else {}

        accepted=[]
        boundary_reviews=[]
        llm_candidates=[]
        deterministic_split_count=0
        deterministic_keep_count=0
        for candidate in candidates:
            i=int(candidate.get("index") or 0)
            route=_candidate_route(candidate,profile)
            if route=="split":
                accepted.append({**candidate,"decision":"split","confidence":1.0,"changes":[],"source":"deterministic_structural_split"})
                deterministic_split_count+=1
            elif route=="keep":
                deterministic_keep_count+=1
            else:
                llm_candidates.append(candidate)

        import math
        max_adjudications=min(16,max(4,int(math.ceil(max(1,len(blocks))*float(profile.get("max_llm_boundary_calls_per_100_atoms") or 6)/100.0))))
        llm_candidates=sorted(llm_candidates,key=lambda c:float(c.get("candidate_score") or 0),reverse=True)
        budget_skipped=max(0,len(llm_candidates)-max_adjudications)
        llm_candidates=llm_candidates[:max_adjudications]
        batch_size=max(1,min(12,int(profile.get("boundary_batch_size") or 6)))
        llm_split_count=0
        llm_keep_count=budget_skipped
        batch_call_count=0
        classifier_failures=0

        # Reuse only provenance-compatible local decisions. The fingerprint binds
        # the prompt version, evidence text, model, and relevant generation knobs.
        pending=[]
        for candidate in llm_candidates:
            i=int(candidate["index"])
            left,right=blocks[i],blocks[i+1]
            bid=str(candidate["after_block_id"])
            fingerprint=self._boundary_cache_fingerprint(left,right,request)
            cached=decisions.get(bid)
            if isinstance(cached,dict) and cached.get("fingerprint")==fingerprint and isinstance(cached.get("pair"),dict):
                pair=cached["pair"]
                if pair.get("decision")=="split" and float(pair.get("confidence") or 0)>=threshold:
                    accepted.append({**candidate,**pair,"source":"cached_local_classifier"}); llm_split_count+=1
                else: llm_keep_count+=1
            else:
                pending.append((candidate,fingerprint))

        completed=len(llm_candidates)-len(pending)
        for offset in range(0,len(pending),batch_size):
            if self._cancelled(build_id): raise InterruptedError("Corpus build cancelled")
            chunk=pending[offset:offset+batch_size]
            batch=[item[0] for item in chunk]
            results,failure=self._segment_candidate_batch(batch,blocks,manifest,request,build_id)
            batch_call_count+=1
            if failure:
                classifier_failures+=len(batch)
                self._increment_metric(build_id,"local_boundary_classifier_failures",len(batch))
            for candidate,fingerprint in chunk:
                bid=str(candidate["after_block_id"])
                pair=results.get(bid) or {"after_block_id":bid,"decision":"keep","confidence":0.0,"changes":[],"source":"deterministic_keep_after_omission"}
                decisions[bid]={"pair":pair,"failure":failure,"fingerprint":fingerprint}
                if pair.get("decision")=="split" and float(pair.get("confidence") or 0)>=threshold:
                    accepted.append({**candidate,**pair,"source":"local_batch_classifier"}); llm_split_count+=1
                else:
                    llm_keep_count+=1
            self.repo.save_checkpoint(build_id,"local_boundary_state",{"decisions":decisions})
            completed+=len(chunk)
            self._update(build_id,stage="segmenting",progress=0.12+0.23*(completed/max(1,len(llm_candidates))),boundary_candidates_completed=min(len(candidates),deterministic_split_count+deterministic_keep_count+completed),boundary_candidate_count=len(candidates))

        def grouped(boundaries:list[dict[str,Any]])->list[list[dict[str,Any]]]:
            split_ids={str(item.get("after_block_id") or "") for item in boundaries}
            out=[]; current=[]
            for block in blocks:
                current.append(block)
                if str(block.get("block_id") or "") in split_ids:
                    out.append(current); current=[]
            if current: out.append(current)
            return out

        # Semantic topology is now normalized deterministically toward the soft
        # retrieval-size policy. Existing semantic boundaries are preserved; new
        # size-optimized boundaries record that they are retrieval boundaries, not
        # claims that the argument itself ends there.
        accepted, normalization_reviews, normalization_metrics = _normalize_topology(
            blocks, accepted, sizing_policy
        )
        boundary_reviews.extend(normalization_reviews)
        provisional=[item for item in accepted if item.get("boundary_kind") in {"retrieval_size_optimized","absolute_size_safety"}]
        accepted.sort(key=lambda item:index_by_id.get(str(item.get("after_block_id") or ""),10**9))
        review_map={(str(i.get("after_block_id") or ""),str(i.get("next_block_id") or ""),str(i.get("kind") or "")):i for i in boundary_reviews}
        boundary_reviews=list(review_map.values())

        build=self.repo.get_build(build_id)
        build.update({
            "segmentation_blocked":False,
            "segmentation_unresolved_regions":boundary_reviews[:500],
            "segmentation_boundary_reviews":boundary_reviews[:500],
            "boundary_review_count":len(boundary_reviews),
            "segmentation_failed_windows":0,"segmentation_total_windows":0,"segmentation_recovered_windows":0,
            "segmentation_degraded":bool(boundary_reviews),
            "boundary_candidate_count":len(candidates),"boundary_count":len(accepted),
            "provisional_boundary_count":len(provisional),
            "size_optimized_boundary_count":int(normalization_metrics.get("size_optimized_splits") or 0),
            "absolute_safety_boundary_count":int(normalization_metrics.get("absolute_safety_splits") or 0),
            "long_exception_record_count":int(normalization_metrics.get("long_exception_records") or 0),
            "record_sizing_policy":sizing_policy,
            "boundary_deterministic_split_count":deterministic_split_count,
            "boundary_deterministic_keep_count":deterministic_keep_count,
            "boundary_llm_adjudication_count":len(llm_candidates),
            "boundary_llm_batch_call_count":batch_call_count,
            "boundary_llm_split_count":llm_split_count,
            "boundary_llm_keep_count":llm_keep_count,
            "boundary_budget_skipped_count":budget_skipped,
            "boundary_classifier_failure_count":classifier_failures,
        })
        self.repo.save_build(build)
        self.repo.save_checkpoint(build_id,"boundaries_partial",accepted)
        if boundary_reviews:
            self._append_warning(build_id,f"Corpus topology contains {len(boundary_reviews)} demonstrated provenance hazard(s) requiring boundary review. Ordinary uncertainty has already resolved conservatively to KEEP.")
        self._update(build_id,stage="reconciling",progress=0.40)
        return accepted


    def _enrich_record(
        self,
        record: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
        *,
        previous_text: str = "",
        next_text: str = "",
        build_id: str = "",
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None = None,
    ) -> dict[str, Any]:
        """Infer interpretive metadata through several small structured tasks.

        A single all-fields JSON object proved fragile with local models: one
        truncated brace could invalidate every metadata dimension.  The staged
        design keeps output schemas small, preserves successful partial work, and
        makes retries/escalation local to the failed metadata family.
        """
        profile_id = PROFILE_VERSION
        if build_id:
            try:
                current_build = self.repo.get_build(build_id)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not refresh corpus build state before metadata enrichment: {exc}"
                ) from exc
            current_manifest = current_build.get("manifest")
            if isinstance(current_manifest, dict) and current_manifest:
                manifest = current_manifest
            profile_id = str(current_build.get("profile_id") or PROFILE_VERSION)
            if not bool(request.get("_interactive_provider_override")):
                # The runtime request carries the provider; the run's own identity and experiment switches stay.
                kept: dict[str, Any] = {key: request[key] for key in ("run_id", "arms", "arm_salt", "ablations", "arm", "model_version") if key in request}
                request = {**self._latest_runtime_request(build_id, request), **kept}
        request = experiment.with_arm(request, str(record.get("record_id") or ""))
        off = experiment.disabled(request)
        _apply_manifest_metadata(record, manifest)
        apply_metadata_constraints(record)
        editorial_memory = self._editorial_memory(build_id, record, exclude_record_id=str(record.get("record_id") or ""), use_global="cross_build_learning" not in off) if build_id else {"conventions": {}, "examples": {}}
        if "reviewer_conventions" in off:
            editorial_memory = {**editorial_memory, "conventions": {}, "examples": {}}
        if "rejection_memory" in off:
            editorial_memory = {**editorial_memory, "pass_learning": None}
        editorial_context = editorial_memory.get("conventions", {}) if isinstance(editorial_memory, dict) else {}
        editorial_examples = editorial_memory.get("examples", {}) if isinstance(editorial_memory, dict) else {}
        record["editorial_memory_used"] = {
            "convention_fields": sorted(editorial_context.keys()),
            "example_record_ids": sorted({str(item.get("record_id") or "") for values in editorial_examples.values() if isinstance(values, list) for item in values if isinstance(item, dict) and item.get("record_id")}),
        }
        if build_id:
            example_count = sum(len(values) for values in editorial_examples.values() if isinstance(values, list))
            if example_count:
                self._increment_metric(build_id, "editorial_examples_used", example_count)
        schema = self._schema_for(build_id)
        profile = {**CORPUS_PROFILES.get(profile_id, CORPUS_PROFILES[PROFILE_VERSION]), "review_metadata_fields": schema.review_fields()}
        required_metadata_fields = list(profile.get("required_metadata_fields") or [])
        if bool(request.get("llm_touchup_during_enrichment")) and "__text__" not in set(record.get("human_touched_fields") or []):
            current_text = str(record.get("text") or "")
            if current_text.strip():
                try:
                    proposal = self.touchup_record_text(
                        build_id, str(record.get("record_id") or ""), request,
                        text_override=current_text,
                    )
                    record["text_touchup_proposal"] = {
                        "proposal_id": f"touchup-{uuid.uuid4().hex[:12]}",
                        "run_id": str(request.get("run_id") or f"touchup-run-{uuid.uuid4().hex[:12]}"),
                        "status": "pending_review",
                        "source_text": proposal["source_text"],
                        "proposed_text": proposal["proposed_text"],
                        "changes": proposal["changes"],
                        "warnings": proposal["warnings"],
                        "provider": proposal["provider"],
                        "model": proposal["model"],
                        "created_at": iso_now(),
                    }
                    record["needs_review"] = True
                    record["metadata_needs_attention"] = True
                    reasons = list(record.get("metadata_attention_reasons") or [])
                    reasons.append("An LLM text touch-up proposal is available for review; reviewed text remains unchanged until approved.")
                    record["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
                except InterruptedError:
                    raise
                except Exception as exc:
                    record["text_touchup_proposal"] = {
                        "proposal_id": f"touchup-{uuid.uuid4().hex[:12]}",
                        "run_id": str(request.get("run_id") or f"touchup-run-{uuid.uuid4().hex[:12]}"),
                        "status": "failed",
                        "warnings": [f"LLM text touch-up failed: {exc}"],
                        "created_at": iso_now(),
                    }
                    self._append_warning(build_id, f"{record.get('record_id')}: LLM text touch-up failed; metadata enrichment continued.")
        if _metadata_source_quality_gate(record, required_metadata_fields, stage_callback):
            return record
        tasks, source_ids, obvious_apparatus = self._prepare_metadata_tasks(
            record, manifest, request, profile, editorial_context, editorial_examples,
            previous_text, next_text, stage_callback,
            pass_learning=editorial_memory.get("pass_learning") if isinstance(editorial_memory, dict) else None,
            schema=schema,
        )
        stage_results = self._execute_metadata_tasks(record, request, tasks, build_id, stage_callback)
        return self._reconcile_metadata_results(record, profile, source_ids, stage_results, obvious_apparatus, request=request, build_id=build_id, schema=schema)


    def _prepare_metadata_tasks(
        self, record: dict[str, Any], manifest: dict[str, Any], request: dict[str, Any],
        profile: dict[str, Any], editorial_context: dict[str, Any], editorial_examples: dict[str, Any],
        previous_text: str, next_text: str,
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
        *, pass_learning: dict[str, Any] | None = None, schema: MetadataSchema | None = None,
    ) -> tuple[list[tuple[str, str, type[BaseModel], int, str]], list[str], bool]:
        """Bound source context and select structured tasks without invoking a provider."""
        schema = schema or default_schema()
        allowed_region_types = list(profile.get("region_types") or REGION_TYPES)
        allowed_discourse_roles = list(profile.get("discourse_roles") or DISCOURSE_ROLES)
        limits = _stage_limits(request)
        neighbor_context = {
            "previous_record_tail": previous_text[-1800:] if previous_text else "",
            "next_record_head": next_text[:1800] if next_text else "",
        }
        source_ids = [str(value) for value in record.get("source_block_ids") or []]
        source_id_json = json.dumps(source_ids, ensure_ascii=False)
        # Semantic records should already be bounded. This is a context-safety
        # guard, not a segmentation rule: no source text is rewritten or split here.
        source_text = str(record.get("text") or "")
        context = _context_window(request)
        largest_metadata_output = max(limits["discourse_num_predict"], limits["quotation_num_predict"], limits["indexing_num_predict"])
        metadata_input_tokens = 9000 if not context else max(1800, min(12000, context - largest_metadata_output - 1800))
        metadata_char_budget = max(7000, metadata_input_tokens * 4)
        if len(source_text) > metadata_char_budget:
            half = max(2500, metadata_char_budget // 2)
            source_text = source_text[:half] + "\n\n[...middle retained in source record but omitted from this metadata prompt...]\n\n" + source_text[-half:]
            record["needs_review"] = True
            record["review_reason"] = "Record exceeds this model's metadata context envelope; metadata was inferred from head/tail context and requires review."

        human_status = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        human_locked_fields = sorted(
            field for field, info in human_status.items()
            if isinstance(info, dict) and str(info.get("status") or "") in {"human_confirmed", "human_override"}
        )
        base_context = f"""Document manifest: {json.dumps(manifest, ensure_ascii=False)}
Build-local editorial conventions confirmed on at least two other records (advisory context only; do not copy unless supported here): {json.dumps(editorial_context, ensure_ascii=False)}
Relevant human-confirmed examples retrieved from this build (few-shot guidance only; source evidence in THIS record remains authoritative): {json.dumps(editorial_examples, ensure_ascii=False)}
How earlier enrichment in this build went (advisory only; evidence in THIS record remains authoritative). Includes reviewer accepted/rejected counts when present, plus values the previous pass inferred on two or more other records (working conventions, not confirmed). Do not copy these; use them only when THIS record's evidence supports the same reading: {json.dumps(pass_learning or {}, ensure_ascii=False)}
Human-owned fields on this record (authoritative; DO NOT propose replacements): {json.dumps({field: record.get(field) for field in human_locked_fields}, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps(neighbor_context, ensure_ascii=False)}
Current source block IDs: {source_id_json}
CURRENT REVIEWED RECORD TEXT:
{source_text}
"""

        enrichment_mode = str(request.get("enrichment_mode") if "enrichment_mode" in request else "deep")
        semantic_indexing = bool(request.get("semantic_indexing")) or enrichment_mode == "deep"
        region_type = str(record.get("region_type") or "")
        obvious_apparatus = region_type in {"bibliography", "index", "copyright", "front_matter", "back_matter"} or record.get("primary_text") is False
        quote_signal = any(token in source_text for token in ('“', '”', '"', '«', '»', '‘', '’')) or bool(re.search(r"\b(?:quotes?|writes?|says?|according to|cites?)\b", source_text, re.I))
        # One task per group of the build's schema: the prompt is assembled from the schema and the answer's shape is generated from it.
        all_task_specs: dict[str, tuple[str, str, type[BaseModel], int, str]] = {}
        run_guidance = request.get("run_guidance") if isinstance(request.get("run_guidance"), dict) else {}
        guidance_matches = record.get("metadata_guidance_matches")
        if not isinstance(guidance_matches, dict):
            guidance_matches = find_guidance_matches(source_text, run_guidance)
        for group in schema.groups:
            group_fields = [field.name for field in schema.fields_in(group.key)]
            if group.key == CORE_GROUP:
                group_fields = [*CORE_FIELDS, *group_fields]
            prompt = build_group_prompt(
                schema,
                group.key,
                base_context=base_context,
                allowed_region_types=allowed_region_types,
                allowed_discourse_roles=allowed_discourse_roles,
            )
            guidance_prompt = format_group_guidance(group_fields, run_guidance, guidance_matches)
            if guidance_prompt:
                prompt = prompt + "\n\n" + guidance_prompt
            all_task_specs[group.key] = (
                group.key,
                prompt,
                response_model_for(schema, group.key, region_types=allowed_region_types, roles=allowed_discourse_roles),
                int(limits.get(f"{group.key}_num_predict") or limits["indexing_num_predict"]),
                f"derridai_record_{group.key}",
            )
        requested_families = request.get("families")
        if isinstance(requested_families, list) and requested_families:
            # Explicit human reruns bypass Fast-mode routing, but only for the
            # selected family/families. This prevents a text correction from
            # needlessly repeating every expensive metadata task.
            requested = {str(value) for value in requested_families}
            tasks = [spec for name, spec in all_task_specs.items() if name in requested]
        else:
            tasks = []
            # Discourse classification is the semantic corroboration layer for
            # deterministic region/primary-text rules and is therefore always
            # scheduled unless the family is already human-owned. This catches
            # bad or unreviewed main-text page ranges while also supplying the
            # high-value discourse_role proposal. Quotation and indexing keep their
            # routing; any group a schema adds runs every time.
            for name, spec in all_task_specs.items():
                if name == "quotation" and not (enrichment_mode == "deep" or quote_signal):
                    continue
                if name == "indexing" and not semantic_indexing:
                    continue
                tasks.append(spec)
        selected_names = {item[0] for item in tasks}
        # Normal Fast-mode routing settles unneeded families as skipped. An
        # explicit selective rerun must leave every unselected family's prior
        # terminal state and normalized metadata untouched.
        if not (isinstance(requested_families, list) and requested_families):
            for skipped_family in set(all_task_specs) - selected_names:
                record.setdefault("metadata_stage_status", {})[skipped_family] = "skipped"
                record.setdefault("metadata_execution_ledger", {})[skipped_family] = {
                    "state": "skipped", "finished_at": iso_now(),
                    "error": "Skipped by fast enrichment routing; no strong signal required this LLM family.",
                }
                if stage_callback:
                    stage_callback(record, skipped_family, "skipped", "Fast enrichment routing")
        return tasks, source_ids, obvious_apparatus

    def _execute_metadata_tasks(
        self, record: dict[str, Any], request: dict[str, Any],
        tasks: list[tuple[str, str, type[BaseModel], int, str]], build_id: str,
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
    ) -> list[tuple[str, dict[str, Any] | None, Exception | None]]:
        """Run unsettled families with live ownership checks and durable stage callbacks."""
        requested_families = request.get("families")
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]] = []
        persisted_stage_results = record.setdefault("metadata_stage_results", {})
        stage_status = record.setdefault("metadata_stage_status", {})
        stage_ledger = record.setdefault("metadata_execution_ledger", {})
        for task_name, prompt, response_model, max_tokens, schema_name in tasks:
            if build_id:
                try:
                    live_rows = self.repo.load_records(build_id)
                    live_record = next((row for row in live_rows if str(row.get("record_id") or "") == str(record.get("record_id") or "")), None)
                except Exception as exc:
                    reason = (
                        f"Could not verify live reviewer ownership before {task_name} metadata enrichment: {exc}"
                    )
                    failure = RuntimeError(reason)
                    stage_status[task_name] = "needs_review"
                    stage_ledger[task_name] = {
                        "state": "needs_review", "finished_at": iso_now(),
                        "error": reason, "reason_code": "ownership_state_unavailable",
                    }
                    stage_results.append((task_name, None, failure))
                    if stage_callback:
                        stage_callback(record, task_name, "needs_review", reason)
                    self._append_warning(build_id, f"{record.get('record_id')}: {reason}")
                    continue
                if isinstance(live_record, dict):
                    touched = {str(value) for value in (live_record.get("human_touched_fields") or [])}
                    live_status = live_record.get("metadata_field_status") if isinstance(live_record.get("metadata_field_status"), dict) else {}
                    family_fields = self._schema_for(build_id).family_fields().get(task_name, set())
                    all_owned = bool(family_fields) and all(
                        isinstance(live_status.get(field), dict) and str(live_status[field].get("status") or "") in {"human_confirmed", "human_override", "deterministic"}
                        for field in family_fields if field not in {"attribution_confidence", "semantic_classification_confidence"}
                    )
                    if "__text__" in touched or "__review__" in touched or all_owned:
                        reason = "Human reviewed this record before automatic enrichment." if {"__text__", "__review__"} & touched else "All fields in this metadata family are already human-owned or deterministic."
                        stage_status[task_name] = "skipped"
                        stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": reason}
                        stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                        if stage_callback:
                            stage_callback(record, task_name, "skipped", reason)
                        continue
            adaptive_skip, adaptive_reason = self._adaptive_family_should_skip(build_id, task_name, request)
            if adaptive_skip and not (isinstance(requested_families, list) and requested_families):
                stage_status[task_name] = "skipped"
                stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": adaptive_reason, "reason_code": "adaptive_low_yield"}
                stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                if stage_callback:
                    stage_callback(record, task_name, "skipped", adaptive_reason)
                continue
            prior = persisted_stage_results.get(task_name)
            prior_state = str(stage_status.get(task_name) or "")
            if isinstance(prior, dict):
                stage_status[task_name] = "complete"
                stage_results.append((task_name, prior, None))
                continue
            # A fully materialized family no longer needs its bulky raw response.
            # Its status is sufficient to skip the provider on crash-safe resume;
            # the normalized metadata/evidence already lives on the record. Failed
            # and user-skipped families are also terminal until an explicit retry.
            if prior_state == "complete":
                stage_results.append((task_name, {"metadata": {}, "field_evidence": {}, "review_reason": ""}, None))
                continue
            if prior_state in {"failed", "needs_review", "skipped"}:
                prior_error = RuntimeError(f"{task_name} metadata previously settled as {prior_state}.")
                stage_results.append((task_name, None, prior_error))
                continue
            if build_id:
                try:
                    if bool(self.repo.get_build(build_id).get("metadata_settle_requested")):
                        exc = RuntimeError("Automatic metadata was settled as unresolved by the user.")
                        stage_status[task_name] = "skipped"
                        stage_ledger[task_name] = {"state": "skipped", "finished_at": iso_now(), "error": str(exc)}
                        stage_results.append((task_name, None, exc))
                        if stage_callback:
                            stage_callback(record, task_name, "skipped", str(exc))
                        continue
                except KeyError as exc:
                    raise RuntimeError(
                        "Could not verify metadata-settle state because the corpus build no longer exists."
                    ) from exc
            # Resolve the active build profile at task start. A profile switch does
            # not interrupt an in-flight request, but the next family/record picks
            # up the newly selected profile.
            active_request = self._latest_runtime_request(build_id, request) if build_id else request
            started_at = iso_now()
            ledger_context = {
                "provider_profile_id": active_request.get("provider_profile_id"),
                "provider": active_request.get("provider"),
                "model": active_request.get("model"),
                "attempts_allowed": 2,
                "input_chars": len(prompt),
                "max_output_tokens": max_tokens,
                "timeout_seconds": _stage_timeouts(active_request).get(task_name),
            }
            stage_status[task_name] = "running"
            stage_ledger[task_name] = {**ledger_context, "state": "running", "started_at": started_at, "finished_at": None, "error": None}
            if stage_callback:
                stage_callback(record, task_name, "running", None)
            started_clock = time.monotonic()
            try:
                result = self._chat_json(
                    active_request,
                    prompt,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    schema_name=schema_name,
                    build_id=build_id,
                )
                persisted_stage_results[task_name] = result
                stage_status[task_name] = "complete"
                stage_ledger[task_name] = {
                    **ledger_context, "state": "complete", "started_at": started_at, "finished_at": iso_now(),
                    "elapsed_ms": int((time.monotonic() - started_clock) * 1000), "error": None,
                }
                stage_results.append((task_name, result, None))
                self._ledger.append(CALL, model=str(active_request.get("model") or ""), field=task_name, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=str(request.get("run_id") or (f"build-{build_id}" if build_id else "")), elapsed_ms=stage_ledger[task_name].get("elapsed_ms", 0), ok=True, **experiment.context(request, model=str(active_request.get("model") or ""), record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION))
                self._record_family_effectiveness(
                    build_id, task_name, result, elapsed_ms=stage_ledger[task_name].get("elapsed_ms", 0),
                    provider_profile_id=str(ledger_context.get("provider_profile_id") or ""),
                    provider=str(ledger_context.get("provider") or ""), model=str(ledger_context.get("model") or ""),
                )
                if stage_callback:
                    stage_callback(record, task_name, "complete", None)
            except InterruptedError:
                raise
            except Exception as exc:
                stage_status[task_name] = "failed"
                stage_ledger[task_name] = {
                    **ledger_context, "state": "failed", "started_at": started_at, "finished_at": iso_now(),
                    "elapsed_ms": int((time.monotonic() - started_clock) * 1000), "error": str(exc)[:1200],
                }
                stage_results.append((task_name, None, exc))
                self._ledger.append(CALL, model=str(active_request.get("model") or ""), field=task_name, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=str(request.get("run_id") or (f"build-{build_id}" if build_id else "")), elapsed_ms=int((time.monotonic() - started_clock) * 1000), ok=False, **experiment.context(request, model=str(active_request.get("model") or ""), record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION))
                if stage_callback:
                    stage_callback(record, task_name, "failed", str(exc))
                if build_id:
                    self._append_warning(build_id, f"{record.get('record_id')}: {task_name} metadata requires review ({exc})")

        return stage_results

    def _reconcile_metadata_results(
        self, record: dict[str, Any], profile: dict[str, Any], source_ids: list[str],
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]],
        obvious_apparatus: bool,
        request: dict[str, Any] | None = None,
        build_id: str = "",
        schema: MetadataSchema | None = None,
    ) -> dict[str, Any]:
        """Bind proposals to source evidence while retaining reviewer-owned values."""
        schema = schema or default_schema()
        # What may be proposed, cited and reviewed comes from the build's schema, not from a fixed list.
        allowed_fields = _allowed_for(schema)
        attribution_fields = schema.attribution_fields()
        evidence_required_fields = schema.evidence_fields()
        assessment_required_fields = set(CORE_FIELDS) | {field.name for field in schema.fields if field.assess}
        model = str((request or {}).get("model") or "")
        run_id = str((request or {}).get("run_id") or (f"build-{build_id}" if build_id else ""))
        off = experiment.disabled(request)
        conditions = experiment.context(request, model=model, record_id=str(record.get("record_id") or ""), code_version=APP_VERSION, prompt_version=PROFILE_VERSION)

        def autofill(field: str, value: Any, confidence: float | None, evidence_info: dict[str, Any]) -> dict[str, Any] | None:
            """The status for a value the model is sure enough about to fill in, or None.

            The blended confidence (see autofill.py) outranks the model's own needs_review flag, but
            never the absence of a cited source block or a self-report at or below the profile floor.
            """
            if "autofill" in off or conditions["blind"] or value in (None, "", []) or confidence is None or confidence <= minimum or not evidence_info.get("block_ids"):
                return None
            reviews, accepted = (0, 0) if "blended_confidence" in off else self._ledger.review_counts(model, field)
            decision = decide_autofill(confidence, reviews, accepted)
            self._note_suspension(model, field, bool(decision["suspended"]), reviews, accepted, build_id, run_id)
            if not decision["autofill"]:
                return None
            audit = in_audit_sample(str(record.get("record_id") or ""), field)
            filled_confidence = decision["confidence"] or 0.0
            self._ledger.append(AUTOFILLED, model=model, field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=run_id, confidence=filled_confidence, self_reported=confidence, audit=audit, **conditions)
            return {
                "status": "model_inferred", "method": "llm", "model": model, "confidence": filled_confidence,
                "self_reported_confidence": confidence, "auto_populated": True, "autofilled": True, "audit_sample": audit,
                "proposed_value": value, "reason_code": "resolved",
                "reason": f"Filled in automatically at {round(filled_confidence * 100)}% confidence, with cited evidence.",
            }
        allowed_region_types = list(profile.get("region_types") or REGION_TYPES)
        allowed_discourse_roles = list(profile.get("discourse_roles") or DISCOURSE_ROLES)
        required_metadata_fields = list(profile.get("required_metadata_fields") or [])
        stage_status = record.setdefault("metadata_stage_status", {})
        stage_ledger = record.setdefault("metadata_execution_ledger", {})
        # Expose whether the semantic reader actually evaluated deterministic
        # structural fields. A final value alone must never imply corroboration.
        discourse_state = str(stage_status.get("discourse") or "")
        discourse_ledger = stage_ledger.get("discourse") if isinstance(stage_ledger.get("discourse"), dict) else {}
        if discourse_state in {"skipped", "failed", "needs_review"}:
            skip_reason = str(discourse_ledger.get("error") or f"Discourse metadata stage was {discourse_state}.")
            for structural_field in ("region_type", "primary_text"):
                structural_status = record.setdefault("metadata_field_status", {}).get(structural_field)
                if isinstance(structural_status, dict) and structural_status.get("status") == "deterministic" and "llm_checked" not in structural_status:
                    structural_status["llm_checked"] = False
                    structural_status["llm_skip_reason"] = skip_reason

        minimum = float(profile.get("min_metadata_confidence") or 0.65)
        clean_evidence: dict[str, Any] = dict(record.get("metadata_evidence") or {})
        valid_ids = set(source_ids)
        review_reasons: list[str] = []
        evidence_confidences: list[float] = []
        attribution_confidences: list[float] = []
        model_review_reasons: list[str] = []
        field_assessments: dict[str, dict[str, Any]] = {}
        llm_populated_fields: set[str] = set()
        raw_llm_values: dict[str, Any] = {}
        # Presence in the required metadata object means the field was requested,
        # not that the model supplied an assessment. Keep those facts separate.
        llm_requested_fields: set[str] = set()
        llm_value_returned_fields: set[str] = set()
        llm_checked_fields: set[str] = set()  # compatibility alias: actually assessed
        successful_tasks = 0

        for task_name, result, failure in stage_results:
            if failure is not None or not isinstance(result, dict):
                review_reasons.append(f"{task_name} metadata extraction could not be validated: {failure}")
                continue
            successful_tasks += 1
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            if isinstance(result.get("field_assessments"), dict):
                assessed = {str(key): value for key, value in result.get("field_assessments", {}).items() if isinstance(value, dict)}
                field_assessments.update(assessed)
                llm_checked_fields.update(key for key in assessed if key in allowed_fields)
            field_status = record.setdefault("metadata_field_status", {})
            for key, value in metadata.items():
                if key not in allowed_fields or key in SOURCE_BOUND_FIELDS:
                    continue
                llm_requested_fields.add(key)
                value, raw_llm_value = _normalize_semantic_value(key, value)
                if value not in (None, "", []):
                    llm_value_returned_fields.add(key)
                if raw_llm_value is not None:
                    raw_llm_values[key] = raw_llm_value
                existing_status = field_status.get(key) if isinstance(field_status.get(key), dict) else {}
                # Human decisions are authoritative. Background/retry enrichment
                # may add evidence, but it must never resurrect an already
                # confirmed review issue or overwrite a human value.
                if existing_status.get("status") in {"human_confirmed", "human_override"}:
                    continue
                if key in {"region_type", "primary_text"} and existing_status.get("status") == "deterministic":
                    # Structural classifications remain selected. The semantic
                    # reader may corroborate or dispute them, but reviewer-owned
                    # document structure is never replaced by an LLM proposal.
                    assessment = field_assessments.get(key) if isinstance(field_assessments.get(key), dict) else {}
                    result_evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
                    key_evidence = result_evidence.get(key) if isinstance(result_evidence.get(key), dict) else {}
                    confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else (key_evidence.get("confidence") if isinstance(key_evidence.get("confidence"), (int, float)) else None)
                    deterministic_value = record.get(key)
                    deterministic_method = str(existing_status.get("method") or "")
                    strong_structure = deterministic_method in STRONG_STRUCTURAL_METHODS
                    existing_status = dict(existing_status)
                    existing_status["llm_requested"] = True
                    existing_status["llm_value_returned"] = value not in (None, "", [])
                    existing_status["llm_assessed"] = bool(assessment)
                    existing_status["llm_checked"] = bool(assessment)  # backward-compatible UI/API key
                    existing_status["llm_value"] = value
                    existing_status["llm_confidence"] = confidence
                    if value is None:
                        existing_status["llm_corroborates"] = None
                        existing_status["llm_skip_reason"] = "Semantic LLM returned no supported value for this field."
                    else:
                        corroborates = value == deterministic_value
                        existing_status["llm_corroboration"] = value
                        existing_status["llm_corroborates"] = corroborates
                        existing_status["corroboration_method"] = "llm"
                        if not corroborates:
                            deterministic_strength = float(existing_status.get("confidence") or 0.0)
                            existing_status["status"] = "unresolved"
                            existing_status["method"] = "deterministic+llm"
                            existing_status["reason_code"] = "deterministic_llm_disagreement"
                            existing_status["deterministic_value"] = deterministic_value
                            existing_status["deterministic_reason"] = str(existing_status.get("reason") or f"Deterministic inference selected {deterministic_value!r}.")
                            existing_status["llm_reason"] = str(assessment.get("reason") or "Semantic LLM check selected a different value.")
                            if strong_structure:
                                existing_status["reason"] = (
                                    f"Reviewer-defined document structure requires {deterministic_value!r}; semantic LLM check suggests {value!r}"
                                    + (f" at {round(float(confidence)*100)}% confidence" if confidence is not None else "")
                                    + ". The structural value remains selected; the disagreement is retained for review."
                                )
                                existing_status["prefilled_candidate"] = "deterministic"
                                existing_status["auto_populated"] = False
                            else:
                                existing_status["reason"] = (
                                    f"Deterministic inference suggests {deterministic_value!r}; semantic LLM check suggests {value!r}"
                                    + (f" at {round(float(confidence)*100)}% confidence" if confidence is not None else "")
                                    + ". Review both candidates."
                                )
                                weak_manifest_range = deterministic_method == "manifest_page_range"
                                if key != "primary_text" and confidence is not None and float(confidence) > minimum and (weak_manifest_range or deterministic_strength < 0.9):
                                    record[key] = value
                                    existing_status["prefilled_candidate"] = "llm"
                                    existing_status["auto_populated"] = True
                                elif key != "primary_text":
                                    existing_status["prefilled_candidate"] = "deterministic"
                                    existing_status["auto_populated"] = False
                                else:
                                    existing_status["prefilled_candidate"] = "deterministic"
                    field_status[key] = existing_status
                    continue
                if key == "region_type" and value is not None and value not in allowed_region_types:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": f"Model returned an unsupported region type: {value}"}
                    continue
                if key == "discourse_role" and value is not None and value not in allowed_discourse_roles:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": f"Model returned an unsupported discourse role: {value}"}
                    continue
                if key == "primary_text" and value is not None and not isinstance(value, bool):
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "reason": "Model returned a non-boolean primary_text value."}
                    continue
                if key == "proposition_status" and value is not None and value not in PROPOSITION_STATUS_VALUES:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "proposed_value": value, "reason": f"Model returned an unsupported proposition status: {value}"}
                    continue
                if key == "stance" and value is not None and value not in STANCE_VALUES:
                    field_status[key] = {"status": "invalid", "method": "llm", "reason_code": "invalid_value", "proposed_value": value, "raw_llm_value": raw_llm_value or value, "llm_checked": True, "reason": f"Model returned an unsupported stance: {value}"}
                    continue
                # A valid model value is a proposal and should be visible to the reviewer
                # regardless of confidence. Confidence/evidence determine whether it is
                # auto-resolved, not whether the record is populated.
                record[key] = value
                if value not in (None, "", []):
                    llm_populated_fields.add(key)
            evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
            for field, info in evidence.items():
                if field not in allowed_fields or not isinstance(info, dict):
                    continue
                block_ids = [str(value) for value in info.get("block_ids") or [] if str(value) in valid_ids]
                raw_confidence = info.get("confidence")
                try:
                    confidence = max(0.0, min(1.0, float(raw_confidence))) if isinstance(raw_confidence, (int, float)) else None
                except (TypeError, ValueError):
                    confidence = None
                clean_evidence[field] = {
                    "block_ids": block_ids,
                    "confidence": confidence,
                    "reason": str(info.get("reason") or ""),
                }
                if confidence is not None:
                    evidence_confidences.append(confidence)
                    if field in attribution_fields:
                        attribution_confidences.append(confidence)
            reason = str(result.get("review_reason") or "").strip()
            if reason:
                model_review_reasons.append(reason)

        for field in sorted(evidence_required_fields):
            value = record.get(field)
            if value in (None, "", []):
                continue
            existing_status = (record.get("metadata_field_status") or {}).get(field) if isinstance(record.get("metadata_field_status"), dict) else {}
            if isinstance(existing_status, dict) and existing_status.get("status") == "deterministic":
                continue
            info = clean_evidence.get(field)
            if not isinstance(info, dict):
                review_reasons.append(f"{field} has no bound source evidence")
                continue
            if not info.get("block_ids"):
                review_reasons.append(f"{field} evidence does not identify a current-record source block")
            evidence_confidence = info.get("confidence")
            if not isinstance(evidence_confidence, (int, float)):
                review_reasons.append(f"{field} evidence confidence was not reported")
            elif float(evidence_confidence) <= minimum:
                review_reasons.append(f"{field} evidence confidence is below {minimum:.2f}")

        record["metadata_evidence"] = clean_evidence
        field_status = record.setdefault("metadata_field_status", {})
        # Every model-populated field gets explicit provenance/confidence, not only
        # the publication-critical discourse fields. This keeps quotation/indexing
        # suggestions reviewable and prevents later records from appearing as if the
        # LLM suddenly stopped supplying metadata merely because those fields were
        # outside REVIEW_METADATA_FIELDS.
        for field in sorted(llm_populated_fields):
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            if current.get("status") in {"deterministic", "inherited", "human_confirmed", "human_override"} or current.get("reason_code") == "deterministic_llm_disagreement":
                continue
            assessment = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            evidence_info = clean_evidence.get(field) if isinstance(clean_evidence.get(field), dict) else {}
            assessment_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else None
            evidence_confidence = evidence_info.get("confidence") if isinstance(evidence_info.get("confidence"), (int, float)) else None
            confidence = float(assessment_confidence if assessment_confidence is not None else evidence_confidence) if (assessment_confidence is not None or evidence_confidence is not None) else None
            needs_human = bool(assessment.get("needs_review"))
            requires_confidence = field in assessment_required_fields or field in evidence_required_fields
            evidence_failed = field in evidence_required_fields and (
                not evidence_info.get("block_ids")
                or not isinstance(evidence_info.get("confidence"), (int, float))
                or float(evidence_info.get("confidence")) <= minimum
            )
            auto = autofill(field, record.get(field), confidence, evidence_info)
            if auto:
                auto["value_source"] = "llm"
                auto["verification_status"] = "auto_resolved"
                field_status[field] = auto
                continue
            if needs_human or (requires_confidence and confidence is None) or (requires_confidence and confidence <= minimum) or evidence_failed:
                if needs_human:
                    reason_code = "ambiguous"
                elif requires_confidence and confidence is None:
                    reason_code = "confidence_missing"
                elif requires_confidence and confidence <= minimum:
                    reason_code = "low_confidence"
                else:
                    reason_code = "evidence_failed"
                field_status[field] = {
                    "status": "unresolved",
                    "method": "llm",
                    "confidence": confidence,
                    # The value is populated; it simply has not been verified.
                    "auto_populated": True,
                    "autofilled": False,
                    "value_source": "llm",
                    "verification_status": "pending_review",
                    "proposed_value": record.get(field),
                    "reason_code": reason_code,
                    "reason": str(assessment.get("reason") or evidence_info.get("reason") or "Model proposal requires reviewer confirmation."),
                }
                continue
            field_status[field] = {
                "status": "unresolved",
                "method": "llm",
                "confidence": confidence,
                "auto_populated": True,
                "autofilled": False,
                "value_source": "llm",
                "verification_status": "pending_review",
                "proposed_value": record.get(field),
                "reason_code": "autofill_not_approved",
                "reason": str(
                    assessment.get("reason")
                    or evidence_info.get("reason")
                    or "Model value was populated, but calibrated autofill did not approve automatic verification."
                ),
            }
        review_metadata_fields = list(profile.get("review_metadata_fields") or REVIEW_METADATA_FIELDS)
        for field in review_metadata_fields:
            value = record.get(field)
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            if current.get("status") in {"deterministic", "inherited", "human_confirmed", "human_override", "invalid"} or current.get("reason_code") in {"deterministic_llm_disagreement", "low_confidence", "confidence_missing"}:
                continue
            evidence_info = clean_evidence.get(field) if isinstance(clean_evidence.get(field), dict) else {}
            assessment = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            assessment_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else None
            evidence_confidence = evidence_info.get("confidence") if isinstance(evidence_info.get("confidence"), (int, float)) else None
            confidence = float(assessment_confidence if assessment_confidence is not None else evidence_confidence) if (assessment_confidence is not None or evidence_confidence is not None) else None
            reason = str(assessment.get("reason") or evidence_info.get("reason") or "Model assessment.")
            needs_human = bool(assessment.get("needs_review"))
            outcome = str(assessment.get("outcome") or "")
            if field not in required_metadata_fields and value in (None, "", []) and not assessment:
                # Backward compatibility for old persisted model output that had no
                # assessment object at all. New structured output requires one.
                continue
            if field not in required_metadata_fields and value in (None, "", []) and outcome == "no_supported_value":
                if confidence is not None and confidence > minimum and not needs_human:
                    field_status[field] = {
                        "status": "model_inferred", "method": "llm", "confidence": confidence,
                        "auto_populated": False, "autofilled": False, "value_source": "llm",
                        "verification_status": "auto_resolved", "proposed_value": None,
                        "reason_code": "no_supported_value", "reason": reason or "Model found no supported value for this field.",
                    }
                else:
                    field_status[field] = {
                        "status": "unresolved", "method": "llm", "confidence": confidence,
                        "auto_populated": False, "autofilled": False, "value_source": "llm",
                        "verification_status": "pending_review", "proposed_value": None,
                        "reason_code": "ambiguous" if needs_human else ("confidence_missing" if confidence is None else "low_confidence"),
                        "reason": reason or "Model proposed that no supported value applies; reviewer confirmation is required.",
                    }
                continue
            if value in (None, "", []) and outcome == "uncertain":
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": False, "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": None,
                    "reason_code": "ambiguous", "reason": reason or "The model could not determine a supported value.",
                }
                continue
            auto = autofill(field, value, confidence, evidence_info)
            if auto:
                auto["value_source"] = "llm"
                auto["verification_status"] = "auto_resolved"
                field_status[field] = auto
            elif field in required_metadata_fields and value in (None, "", []):
                field_status[field] = {"status": "unresolved", "method": "hybrid", "confidence": confidence, "auto_populated": False, "value_source": "llm", "verification_status": "pending_review", "proposed_value": value, "reason_code": "ambiguous", "reason": reason}
            elif (confidence is None or confidence <= minimum) and value not in (None, "", []):
                # The proposal is already populated. Missing/low confidence blocks
                # automatic resolution, not visibility of the value.
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": True, "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "confidence_missing" if confidence is None else "low_confidence",
                    "reason": reason or ("Model confidence was not reported." if confidence is None else f"Model confidence is below {minimum:.2f}."),
                }
            elif value in (None, "", []) and field in evidence_required_fields and confidence is not None and confidence > minimum and not needs_human:
                # A confident assessment with no value cannot be shown as an
                # inference: there is nothing to display, populate, or cite. Keep it
                # in the review queue (one click confirms a genuine absence).
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence, "auto_populated": False,
                    "proposed_value": None, "reason_code": "no_value_returned",
                    "reason": f"The model reported {round(confidence * 100)}% confidence but returned no value. {reason}".strip(),
                }
            elif needs_human or (value not in (None, "", []) and field in evidence_required_fields and (not evidence_info.get("block_ids") or not isinstance(evidence_info.get("confidence"), (int, float)) or float(evidence_info.get("confidence")) <= minimum)):
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": value not in (None, "", []), "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "ambiguous" if needs_human else "evidence_failed", "reason": reason,
                }
            else:
                field_status[field] = {
                    "status": "unresolved", "method": "llm", "confidence": confidence,
                    "auto_populated": value not in (None, "", []), "autofilled": False, "value_source": "llm",
                    "verification_status": "pending_review", "proposed_value": value,
                    "reason_code": "autofill_not_approved",
                    "reason": reason or "Model value was populated, but calibrated autofill did not approve automatic verification.",
                }

        apply_metadata_constraints(record)
        for requested_field in llm_requested_fields:
            requested_status = field_status.get(requested_field)
            if isinstance(requested_status, dict):
                requested_status.setdefault("llm_requested", True)
                requested_status.setdefault("llm_value_returned", requested_field in llm_value_returned_fields)
                requested_status.setdefault("llm_assessed", requested_field in llm_checked_fields)
                # Kept for API/UI compatibility; it now means "the model returned a
                # field assessment", not merely "metadata JSON contained this key".
                requested_status.setdefault("llm_checked", requested_field in llm_checked_fields)
                if requested_field in raw_llm_values:
                    requested_status.setdefault("raw_llm_value", raw_llm_values[requested_field])

        shown: dict[str, Any] = {}
        for field in sorted(llm_populated_fields):
            proposed_status = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            shown[field] = record.get(field)
            if conditions["blind"] and proposed_status.get("method") == "llm" and proposed_status.get("status") in {"model_inferred", "unresolved"}:
                # Blind review: the model's value is sealed in the ledger and the reviewer sees an empty field.
                record[field] = [] if isinstance(shown[field], list) else None
                field_status[field] = proposed_status = {
                    "status": "unresolved", "method": "llm", "blind": True, "reason_code": "blind_review", "auto_populated": False,
                    "reason": "",
                }
                _scrub_sealed_field(record, field)
            if proposed_status.get("method") == "llm":
                # Later human decisions on this value are attributed to the model and conditions that produced it.
                proposed_status.setdefault("model", model)
                proposed_status["conditions"] = conditions
            assessed = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            self._ledger.append(
                PROPOSED, model=model, field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), run_id=run_id,
                value=shown.get(field), self_reported=assessed.get("confidence"),
                grounded=bool((clean_evidence.get(field) or {}).get("block_ids")), outcome=proposed_status.get("status"),
                supported=experiment.supported_in_text(shown.get(field), str(record.get("text") or "")) if field in experiment.FREE_TEXT_FIELDS else None, **conditions,
            )
        record["semantic_classification_confidence"] = round(sum(evidence_confidences) / len(evidence_confidences), 4) if evidence_confidences else None
        record["attribution_confidence"] = round(min(attribution_confidences), 4) if attribution_confidences else 1.0
        if any(isinstance(info, dict) and info.get("blind") for info in field_status.values()):
            # These aggregates are the model's own confidence in a record whose values are sealed.
            record["semantic_classification_confidence"] = None
            record["attribution_confidence"] = None
        review_reasons.extend(model_review_reasons)
        if review_reasons:
            record["metadata_needs_attention"] = True
            record["metadata_attention_reasons"] = list(dict.fromkeys(value for value in review_reasons if value))[:50]
        else:
            record["metadata_needs_attention"] = False
            record["metadata_attention_reasons"] = []
        _sync_record_metadata_state(record, profile)
        incomplete_fields = list(record.get("metadata_incomplete_fields") or [])
        review_fields = list(record.get("metadata_review_fields") or [])
        # Optional indexing/quotation failures remain visible but do not make a structurally
        # valid record permanently unpublishable. Required hybrid classifications and
        # the discourse task are the publication-critical metadata gate.
        discourse_ok = any(name == "discourse" and failure is None for name, _result, failure in stage_results)
        if not discourse_ok and str(record.get("metadata_stage_status", {}).get("discourse") or "") == "skipped":
            status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            required_discourse = [field for field in required_metadata_fields if field in schema.family_fields()[CORE_GROUP]]
            human_or_deterministic = all(
                isinstance(status_map.get(field), dict) and str(status_map[field].get("status") or "") in {"human_confirmed", "human_override", "deterministic", "inherited", "model_inferred"}
                for field in required_discourse
            ) if required_discourse else True
            discourse_ok = obvious_apparatus or human_or_deterministic
        record["metadata_complete"] = discourse_ok and not incomplete_fields and not review_fields
        # Preserve exact terminal states (complete/failed/skipped) from execution
        # instead of flattening every exception into a generic needs_review state.
        # After normalization the raw successful response objects are redundant;
        # stage_status plus normalized record fields are enough to resume without
        # re-running already settled families.
        record["metadata_stage_status"] = dict(stage_status)
        record.pop("metadata_stage_results", None)
        inline, full = _citation_strings(record)
        record["inline_citation"] = inline
        record["full_citation"] = full
        return record


    def _llm_text_noise_pass(
        self,
        build_id: str,
        records: list[dict[str, Any]],
        request: dict[str, Any],
        threshold: float,
    ) -> None:
        """Optional second reader: may only raise the deterministic noise score."""
        for record in records:
            current = record.get("text_noise") if isinstance(record.get("text_noise"), dict) else {}
            try:
                det = float(current.get("deterministic_score") or current.get("score") or 0)
            except (TypeError, ValueError):
                det = 0.0
            if not should_ask_llm(det):
                continue
            excerpt = str(record.get("text") or "")[:500]
            try:
                parsed = self._chat_json(
                    request,
                    f"{TEXT_NOISE_LLM_PROMPT}\n\nTEXT:\n{excerpt}",
                    response_model=TextNoiseLlmResult,
                    max_tokens=256,
                    schema_name="derridai_text_noise",
                    build_id=build_id,
                )
            except Exception as exc:  # noqa: BLE001 - a noise pass must not abort the build
                self._append_warning(
                    build_id,
                    f"{record.get('record_id')}: text-noise LLM pass failed ({exc}); deterministic score kept.",
                )
                continue
            record["text_noise"] = fuse_record_noise(
                current,
                None,
                llm_score=parsed.get("noise"),
                llm_confidence=parsed.get("confidence"),
                threshold=threshold,
            )
            noise = record["text_noise"]
            noise["prompt_version"] = TEXT_NOISE_PROMPT_VERSION
            if parsed.get("reason"):
                noise["llm_reason"] = str(parsed.get("reason") or "")[:500]

    def _apply_source_illegibility(
        self,
        build_id: str,
        records: list[dict[str, Any]],
        request: dict[str, Any],
        source_quality: dict[str, Any],
        pages: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Score illegibility, flag source problems, and compute the 10% trash ratio.

        Runs after record construction and deterministic cleanup, before metadata
        enrichment, so garbled OCR is not sent to discourse/quotation/indexing.
        """
        try:
            threshold = float(request.get("noise_unusable_threshold"))
        except (TypeError, ValueError):
            threshold = float(DEFAULT_NOISE_THRESHOLD)
        threshold = max(0.0, min(100.0, threshold))
        self._attach_ingest_noise(records, request, pages, threshold)
        if request.get("llm_assess_text_noise"):
            self._llm_text_noise_pass(build_id, records, request, threshold)
        blocking_pages = set(int(value) for value in (source_quality.get("blocking_pages") or []))
        for record in records:
            record_pages = set(int(value) for value in (record.get("pdf_pages") or []) if isinstance(value, int))
            affected = sorted(record_pages & blocking_pages)
            issues = list(record.get("source_quality_issues") or [])
            if affected:
                page_findings = [item for item in (source_quality.get("issues") or []) if int(item.get("page") or 0) in affected]
                issues.append({
                    "code": "source_quality_blocking", "severity": "blocking", "pages": affected,
                    "message": "The PDF text layer contains replacement or control characters on one or more pages.",
                    "page_findings": page_findings,
                })
            glyph_issues = _record_extraction_quality_issues(record)
            for item in glyph_issues:
                item.setdefault("severity", "blocking")
            issues.extend(glyph_issues)
            noise = record.get("text_noise") if isinstance(record.get("text_noise"), dict) else {}
            if glyph_issues:
                noise["score"] = max(float(noise.get("score") or 0), 88.0)
                noise["unusable"] = float(noise["score"]) >= threshold
                reasons = list(noise.get("reasons") or [])
                if "fragmented_glyph_layout" not in reasons:
                    reasons.append("fragmented_glyph_layout")
                noise["reasons"] = reasons
                record["text_noise"] = noise
            pages_list = sorted(record_pages)
            if noise.get("unusable"):
                reasons = list(noise.get("reasons") or [])
                if "low_raster_quality" in reasons:
                    issues.append({
                        "code": "low_raster_quality",
                        "severity": "blocking",
                        "pages": pages_list,
                        "message": "Embedded page image resolution is too low to trust as a scholarly scan.",
                    })
                if "high_text_noise" in reasons or float(noise.get("score") or 0) >= threshold:
                    issues.append({
                        "code": "illegible_text",
                        "severity": "blocking",
                        "pages": pages_list,
                        "message": "Extracted text does not look like words in a writing system.",
                        "noise": noise.get("score"),
                    })
            # Deduplicate by code so a re-run does not stack identical findings.
            seen: set[str] = set()
            unique: list[dict[str, Any]] = []
            for item in issues:
                code = str(item.get("code") or "")
                if code in seen:
                    continue
                seen.add(code)
                unique.append(item)
            if unique:
                record["source_quality_issues"] = unique
                record["needs_review"] = True
                record["review_reason"] = (
                    "Source extraction issue: inspect the affected source, correct the reviewed "
                    "record text when appropriate, or rebuild/re-extract the source before acceptance."
                )
        self.repo.save_records(build_id, records)
        trash_quality = _trash_quality_report(records, source_quality)
        current_build = self.repo.get_build(build_id)
        current_build["trash_quality"] = trash_quality
        self.repo.save_build(current_build)
        if trash_quality["exceeds_threshold"]:
            self._append_warning(
                build_id,
                f"{trash_quality['trash_record_count']} of {trash_quality['record_count']} records "
                f"({round(float(trash_quality['trash_ratio']) * 100, 1)}%) appear unusable. "
                "Review the source quality before continuing enrichment.",
            )
        return trash_quality

    def _attach_ingest_noise(
        self,
        records: list[dict[str, Any]],
        request: dict[str, Any],
        pages: list[dict[str, Any]] | None,
        threshold: float,
    ) -> None:
        """Copy page scores computed at PDF ingest onto records; do not rescore text here."""
        asset_id = str(request.get("asset_id") or "")
        extraction_noise: dict[str, Any] | None = None
        if asset_id:
            try:
                extraction_noise = self.repo.get_asset(asset_id).get("extraction_noise")
            except Exception:  # noqa: BLE001
                extraction_noise = None
        page_rows = {
            int(item.get("page") or 0): item
            for item in ((extraction_noise or {}).get("pages") or [])
            if int(item.get("page") or 0) > 0
        }
        if not page_rows:
            annotate_text_noise(records, pages=pages, threshold=threshold)
            return
        unmatched: list[dict[str, Any]] = []
        for record in records:
            rec_pages = [int(value) for value in (record.get("pdf_pages") or []) if isinstance(value, int)]
            hits = [page_rows[page] for page in rec_pages if page in page_rows]
            if not hits:
                unmatched.append(record)
                continue
            best = max(hits, key=lambda item: float(item.get("score") or 0))
            record["text_noise"] = {
                "score": best.get("score"),
                "deterministic_score": best.get("score"),
                "raster_score": None,
                "threshold": threshold,
                "unusable": bool(best.get("unusable")),
                "reasons": list(best.get("reasons") or []),
                "method": "ingest_page",
                "effective_dpi": best.get("effective_dpi"),
            }
        if unmatched:
            annotate_text_noise(unmatched, pages=pages, threshold=threshold)


    @staticmethod
    def validate_records(blocks: list[dict[str, Any]], records: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
        source_ids = [block["block_id"] for block in blocks]
        source_index = {block_id: index for index, block_id in enumerate(source_ids)}
        used_ids = [block_id for record in records for block_id in record.get("source_block_ids") or []]
        missing = [block_id for block_id in source_ids if block_id not in used_ids]
        usage_counts = Counter(used_ids)
        duplicates = sorted(block_id for block_id, count in usage_counts.items() if count > 1)
        block_map = {block["block_id"]: block for block in blocks}
        fidelity_errors: list[str] = []
        order_errors: list[str] = []
        page_errors: list[str] = []
        printed_page_errors: list[str] = []
        evidence_errors: list[dict[str, str]] = []
        citation_errors: list[str] = []
        metadata_schema_errors: list[dict[str, str]] = []
        relationship_errors: list[dict[str, str]] = []
        human_ownership_errors: list[dict[str, str]] = []
        record_content_errors: list[dict[str, str]] = []
        suspicious: list[dict[str, Any]] = []
        previous_last = -1
        min_conf = float(profile.get("min_metadata_confidence") or 0.65)

        for record in records:
            record_id = str(record.get("record_id") or "")
            ids = [str(value) for value in record.get("source_block_ids") or []]
            expected = "\n\n".join(
                block_map[block_id]["text"].strip()
                for block_id in ids
                if block_id in block_map and block_map[block_id]["text"].strip()
            )
            # Reviewed/cleaned text is allowed to differ from the immutable PDF
            # extraction. Source fidelity validates the preserved extraction, not
            # the editorial layer that intentionally repairs layout/OCR noise.
            fidelity_text = record.get("source_extracted_text") if record.get("source_extracted_text") is not None else record.get("text")
            if _normalize_text(expected) != _normalize_text(fidelity_text or ""):
                fidelity_errors.append(record_id)

            indexes = [source_index[value] for value in ids if value in source_index]
            if indexes:
                if indexes != sorted(indexes) or any(b != a + 1 for a, b in zip(indexes, indexes[1:])):
                    order_errors.append(record_id)
                if indexes[0] <= previous_last:
                    order_errors.append(record_id)
                previous_last = max(previous_last, indexes[-1])

            expected_pdf_pages = sorted({int(block_map[value]["page"]) for value in ids if value in block_map})
            actual_pdf_pages = sorted(int(value) for value in record.get("pdf_pages") or [] if isinstance(value, int))
            if expected_pdf_pages != actual_pdf_pages:
                page_errors.append(record_id)
            group = [block_map[value] for value in ids if value in block_map]
            expected_start, expected_end = _scholarly_page_range(group)
            if record.get("page_start") != expected_start or record.get("page_end") != expected_end:
                page_errors.append(record_id)
            source_labels = [str(block.get("printed_page_label") or "").strip() for block in group]
            disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            if disposition == "rejected":
                # Keep rejected records in topology/source validation so the workspace
                # remains auditable, but exclude them from publication-facing
                # metadata/content requirements.
                continue
            if ids and not any(source_labels):
                printed_page_errors.append(record_id)

            try:
                RecordMetadataModel.model_validate({
                    key: record.get(key)
                    for key in RecordMetadataModel.model_fields
                    if key in record
                })
            except ValidationError as exc:
                metadata_schema_errors.append({"record_id": record_id, "reason": str(exc)[:1200]})

            if not str(record.get("text") or "").strip():
                record_content_errors.append({"record_id": record_id, "reason": "record text is empty"})
            if str(record.get("discourse_role") or "") == "reported_position" and "position_holder" in (profile.get("schema_field_names") or ["position_holder"]) and not record.get("position_holder"):
                relationship_errors.append({"record_id": record_id, "reason": "reported_position requires a position_holder"})
            touched = {str(value) for value in (record.get("human_touched_fields") or [])}
            status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            for field in touched:
                if field.startswith("__"):
                    continue
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else {}
                if str(info.get("status") or "") == "model_inferred":
                    human_ownership_errors.append({"record_id": record_id, "reason": f"{field} is human-touched but still marked model_inferred"})

            evidence = record.get("metadata_evidence") if isinstance(record.get("metadata_evidence"), dict) else {}
            valid_ids = set(ids)
            for field in (profile.get("attribution_evidence_fields") or ATTRIBUTION_EVIDENCE_FIELDS):
                value = record.get(field)
                if value in (None, "", []):
                    continue
                info = evidence.get(field) if isinstance(evidence.get(field), dict) else None
                if not info:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": "missing evidence"})
                    continue
                bound = [str(v) for v in info.get("block_ids") or [] if str(v) in valid_ids]
                try:
                    confidence = float(info.get("confidence") or 0)
                except (TypeError, ValueError):
                    confidence = 0.0
                if not bound:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": "no valid source block"})
                elif confidence < min_conf:
                    evidence_errors.append({"record_id": record_id, "field": field, "reason": f"confidence {confidence:.2f} below {min_conf:.2f}"})

            if record.get("work") and record.get("document_author"):
                if not str(record.get("inline_citation") or "").strip() or not str(record.get("full_citation") or "").strip():
                    citation_errors.append(record_id)

            length = len(record.get("text") or "")
            if length < int(profile.get("soft_min_chars") or 0) or length > int(profile.get("soft_max_chars") or 10**9):
                suspicious.append({
                    "record_id": record_id,
                    "text_length": length,
                    "reason": "Length is an audit warning only; it did not create or change a semantic boundary.",
                })

        source_valid = not missing and not duplicates and not fidelity_errors and not order_errors and not page_errors
        metadata_valid = not evidence_errors and not citation_errors and not printed_page_errors and not metadata_schema_errors and not relationship_errors and not human_ownership_errors and not record_content_errors
        return {
            "source_block_count": len(source_ids),
            "used_block_count": len(used_ids),
            "coverage": (len(set(used_ids) & set(source_ids)) / len(source_ids)) if source_ids else 1.0,
            "missing_block_ids": missing,
            "duplicate_block_ids": duplicates,
            "text_fidelity_errors": fidelity_errors,
            "source_order_errors": sorted(set(order_errors)),
            "page_mapping_errors": sorted(set(page_errors)),
            "printed_page_label_errors": sorted(set(printed_page_errors)),
            "metadata_evidence_errors": evidence_errors,
            "metadata_schema_errors": metadata_schema_errors,
            "relationship_errors": relationship_errors,
            "human_ownership_errors": human_ownership_errors,
            "record_content_errors": record_content_errors,
            "citation_errors": sorted(set(citation_errors)),
            "suspicious_record_sizes": suspicious,
            "source_valid": source_valid,
            "metadata_valid": metadata_valid,
            "valid": source_valid and metadata_valid,
        }

    def _run(self, build_id: str, request: dict[str, Any], resume: bool = False) -> None:
        """Coordinate checkpointed stages; retain failure/cancellation recovery at one boundary."""
        try:
            self._update(build_id, stage="preparing")
            scope = self._prepare_build_scope(build_id, request, resume)
            if scope is None:
                return
            self._update(build_id, stage="constructing_topology")
            records = self._construct_build_topology(build_id, request, resume, scope)
            self._update(build_id, stage="enriching")
            records = self._schedule_build_enrichment(build_id, request, scope.manifest, records)
            self._update(build_id, stage="finalizing_review")
            self._finalize_build_review(build_id, scope, records)
            if AutonomousPolicy.from_request(request).enabled:
                self.run_autonomous(build_id, request)
        except InterruptedError as exc:
            self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True, retrying_segmentation=False)
        except Exception as exc:
            # Checkpoints intentionally survive a failed stage. The user can repair
            # provider configuration and resume instead of restarting a long book.
            stage = str(self.repo.get_build(build_id).get("stage") or "unknown")
            self._update(
                build_id,
                status="failed",
                stage="failed",
                finished_at=iso_now(),
                error=f"{stage}: {exc}",
                resumable=True,
                retrying_segmentation=False,
            )
        finally:
            with self._lock:
                self._cancel.discard(build_id)

    def _prepare_build_scope(self, build_id: str, request: dict[str, Any], resume: bool) -> BuildScope | None:
        """Restore/review the manifest and conserve the authoritative source scope."""
        build = self._update(
            build_id,
            status="running",
            stage="resuming" if resume else "structure",
            progress=max(float(self.repo.get_build(build_id).get("progress") or 0.0), 0.03),
            started_at=self.repo.get_build(build_id).get("started_at") or iso_now(),
            finished_at=None,
            error=None,
            resumable=True,
        )
        asset = self.repo.get_asset(build["asset_id"])
        all_blocks = self.repo.load_blocks(build["asset_id"])
        blocks = [block for block in all_blocks if not block.get("excluded_reason")]
        if not blocks:
            raise ValueError("No SourceUnits were extracted from the PDF. Check OCR support and extraction warnings.")

        manifest = self.repo.load_checkpoint(build_id, "manifest") if resume else None
        if not isinstance(manifest, dict):
            manifest = self._document_manifest(asset, blocks, request, build_id)
            if bool(request.get("auto_enrich_work_metadata", True)):
                manifest = self._catalog_enrich_manifest(manifest, request, build_id)
            self.repo.save_checkpoint(build_id, "manifest", manifest)
        current_manifest_revision = int(self.repo.get_build(build_id).get("manifest_revision") or 1)
        self._update(build_id, stage="document_review", progress=max(float(build.get("progress") or 0), 0.12), manifest=manifest, manifest_revision=current_manifest_revision)

        manifest_build = self.repo.get_build(build_id)
        prior_main_text_block_count = int(manifest_build.get("main_text_block_count") or 0)
        # The reviewed manifest defines the semantic-analysis region. Source
        # blocks outside it remain in the persisted source asset for audit.
        manifest_bounds_confirmed = bool(manifest_build.get("manifest_confirmed_at"))
        source_blocks = _manifest_main_text_blocks(
            blocks, manifest, bounds_confirmed=manifest_bounds_confirmed
        )
        # 0.56.0 hotfix: earlier automatic builds could accept an LLM-suggested
        # main-text range before human confirmation.  Dense final pages could
        # satisfy the old block-count plausibility guard and leave only the
        # tail of the PDF in topology.  On resume, detect that persisted scope
        # and rebuild segmentation/records from the full conserved source.
        source_scope_repair = bool(
            resume
            and not manifest_bounds_confirmed
            and prior_main_text_block_count > 0
            and prior_main_text_block_count < len(source_blocks)
        )
        if source_scope_repair:
            self.repo.save_checkpoint(build_id, "segmentation_state", {})
            self.repo.save_checkpoint(build_id, "reconciliation_state", {})
            self.repo.save_checkpoint(build_id, "boundaries_partial", [])
            self._append_warning(
                build_id,
                "Recovered a previously truncated automatic main-text scope; segmentation is being rebuilt from the full extracted PDF source."
            )
        source_quality = page_source_quality_report(source_blocks, asset.get("pages") or [])
        self._update(build_id, source_quality=source_quality)
        semantic_blocks = _semantic_atoms(source_blocks)
        if len(semantic_blocks) < 2:
            semantic_blocks = source_blocks
        self._update(
            build_id, stage="segmenting", progress=max(float(build.get("progress") or 0), 0.12),
            semantic_atom_count=len(semantic_blocks), main_text_block_count=len(source_blocks),
        )
        return BuildScope(build, asset, manifest, source_blocks, semantic_blocks, source_quality, source_scope_repair)

    def _construct_build_topology(
        self, build_id: str, request: dict[str, Any], resume: bool, scope: BuildScope,
    ) -> list[dict[str, Any]]:
        """Recover semantic boundaries, construct source-bound records, and checkpoint them."""
        asset, manifest = scope.asset, scope.manifest
        source_blocks, semantic_blocks = scope.source_blocks, scope.semantic_blocks
        source_quality, source_scope_repair = scope.source_quality, scope.source_scope_repair
        previous_build = self.repo.get_build(build_id)
        # A segmentation-blocked build intentionally has no authoritative final
        # boundary checkpoint. Resume retries unresolved semantic regions using
        # the currently selected provider/settings instead of reusing the
        # partial topology that caused the block.
        boundaries = None
        if resume and not source_scope_repair and not previous_build.get("segmentation_blocked"):
            boundaries = self.repo.load_checkpoint(build_id, "boundaries")
        if not isinstance(boundaries, list):
            segmentation_clock = time.monotonic()
            boundaries = self._segment(semantic_blocks, manifest, request, build_id)
            self._update(build_id, segmentation_elapsed_ms=int((time.monotonic()-segmentation_clock)*1000))
        if self._cancelled(build_id):
            raise InterruptedError("Corpus build cancelled")
        self._update(build_id, retrying_segmentation=False)
        # Whoever proposed the boundaries (the model, a checkpoint, a heuristic), a record must not
        # start or end mid-sentence. This is deterministic and idempotent, so it also repairs
        # checkpoints written before it existed.
        soft_max = int(CORPUS_PROFILES[str(previous_build.get("profile_id") or PROFILE_VERSION)].get("soft_max_chars") or 3500)
        boundaries, sentence_report = snap_boundaries_to_sentences(semantic_blocks, boundaries, hard_max_chars=soft_max * 3)
        self._update(build_id, sentence_boundary_report={key: len(value) for key, value in sentence_report.items()})
        self.repo.save_checkpoint(build_id, "boundaries", boundaries)

        self._update(build_id, stage="constructing_records", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.36))
        records = self.repo.load_records(build_id) if resume and not source_scope_repair else []
        if not records:
            records = _construct_records(asset, source_blocks, boundaries)
            _mark_segmentation_review(records, list(self.repo.get_build(build_id).get("segmentation_unresolved_regions") or []))
            boundary_suspect_count = annotate_boundary_suspects(records)
            if boundary_suspect_count:
                current_build = self.repo.get_build(build_id)
                current_build["boundary_suspect_count"] = boundary_suspect_count
                self.repo.save_build(current_build)
            # A bounded second-reader pass checks only heuristically suspicious
            # or already-demonstrated risky seams. It never rewrites source
            # topology on its own; it corroborates KEEP or creates an explicit
            # human-review recommendation with an exact source-block seam.
            # Suspicious-boundary second reading is advisory and must not delay first
            # record availability. Reviewers can invoke the boundary adjudicator on demand.
            second_reader = {"audited": 0, "keep": 0, "move": 0, "uncertain": 0, "failed": 0, "deferred": boundary_suspect_count}
            current_build = self.repo.get_build(build_id)
            current_build.update({
                "boundary_second_reader_count": int(second_reader.get("audited") or 0),
                "boundary_second_reader_keep_count": int(second_reader.get("keep") or 0),
                "boundary_second_reader_move_count": int(second_reader.get("move") or 0),
                "boundary_second_reader_uncertain_count": int(second_reader.get("uncertain") or 0),
                "boundary_second_reader_failure_count": int(second_reader.get("failed") or 0),
                "boundary_second_reader_deferred_count": int(second_reader.get("deferred") or 0),
            })
            self.repo.save_build(current_build)
            for record in records:
                _apply_manifest_metadata(record, manifest)
                inline, full = _citation_strings(record)
                record["inline_citation"] = inline
                record["full_citation"] = full
            # Validate topology before spending time on metadata enrichment.
            # At this point all source-derived text and boundaries are deterministic;
            # any failure is therefore an implementation/topology problem, not an
            # invitation to burn more LLM calls and ask the user to clean it up.
            active_profile = self._profile_for(build_id)
            sizing_policy = _record_sizing_policy(request, active_profile)
            topology_validation = _topology_sanity(records, sizing_policy, source_blocks)
            topology_quality = _topology_quality_report(records, source_blocks, sizing_policy, topology_validation)
            current_build = self.repo.get_build(build_id)
            current_build["topology_validation"] = topology_validation
            current_build["topology_quality"] = topology_quality
            current_build["record_sizing_policy"] = sizing_policy
            self.repo.save_build(current_build)
            if not topology_validation.get("valid"):
                raise RuntimeError(
                    "Deterministic topology sanity check failed before metadata enrichment: "
                    + ", ".join(topology_validation.get("issues") or ["unknown topology error"])
                )
            # Optionally clean obvious extraction/layout noise before metadata
            # enrichment. The immutable extracted text remains bound in
            # source_extracted_text and the transformation is revisioned.
            if bool(request.get("auto_clean_text", True)):
                cleanup_rules = request.get("text_cleanup_rules") or sorted(TEXT_CLEANUP_RULES)
                cleanup_report = apply_automatic_text_cleanup(records, cleanup_rules, [current_build.get("manifest", {}).get(key) for key in ("title", "short_title", "original_title")])
                current_build = self.repo.get_build(build_id)
                current_build["text_cleanup"] = cleanup_report
                self.repo.save_build(current_build)
            else:
                current_build = self.repo.get_build(build_id)
                current_build["text_cleanup"] = {"enabled": False, "rules": [], "records_changed": 0, "changes": 0, "removed_lines": 0}
                self.repo.save_build(current_build)
            # Persist deterministic records before any metadata call. A provider
            # failure can therefore never discard successful segmentation work.
            self.repo.save_records(build_id, records)
        guidance = request.get("run_guidance") if isinstance(request.get("run_guidance"), dict) else {}
        for record in records:
            matches = find_guidance_matches(str(record.get("text") or ""), guidance)
            if matches:
                record["metadata_guidance_matches"] = matches
            else:
                record.pop("metadata_guidance_matches", None)
        self.repo.save_records(build_id, records)
        trash_quality = self._apply_source_illegibility(
            build_id, records, request, source_quality, asset.get("pages") or [],
        )
        self._update(build_id, stage="enriching", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42), boundary_count=len(boundaries), record_count=len(records), source_problem_count=sum(1 for record in records if record.get("source_quality_issues")), trash_quality=trash_quality)

        return records


    def _persist_build_metadata_stage(
        self, build_id: str, metadata_task_total: int, snapshot: dict[str, Any],
        task_name: str, state: str, error_text: str | None,
    ) -> None:
        """Atomically checkpoint one family and refresh live task telemetry."""
        metadata_families = ("discourse", "quotation", "indexing")
        record_id = str(snapshot.get("record_id") or "")
        with self._lock:
            live_records = self.repo.load_records(build_id)
            live_index = next((i for i, row in enumerate(live_records) if str(row.get("record_id") or "") == record_id), None)
            if live_index is None:
                return
            copy = json.loads(json.dumps(snapshot))
            copy["metadata_enrichment_state"] = "running" if state == "running" else str(copy.get("metadata_enrichment_state") or "running")
            live_records[live_index] = _merge_enrichment_snapshot(live_records[live_index], copy, self._allowed_fields(build_id))
            self.repo.save_records(build_id, live_records)
            states: list[str] = []
            active: list[dict[str, Any]] = []
            for row in live_records:
                row_status = row.get("metadata_stage_status") if isinstance(row.get("metadata_stage_status"), dict) else {}
                ledger = row.get("metadata_execution_ledger") if isinstance(row.get("metadata_execution_ledger"), dict) else {}
                for family in metadata_families:
                    fallback = "complete" if row.get("metadata_complete") else "queued"
                    family_state = str(row_status.get(family) or fallback)
                    states.append(family_state)
                    if family_state == "running":
                        entry = ledger.get(family) if isinstance(ledger.get(family), dict) else {}
                        active.append({
                            "record_id": row.get("record_id"), "task": family,
                            "started_at": entry.get("started_at"),
                        })
            completed_tasks = sum(1 for value in states if value == "complete")
            failed_tasks = sum(1 for value in states if value in {"failed", "needs_review"})
            skipped_tasks = sum(1 for value in states if value == "skipped")
            running_tasks = sum(1 for value in states if value == "running")
            queued_tasks = max(0, metadata_task_total - completed_tasks - failed_tasks - skipped_tasks - running_tasks)
            updates = {
                "metadata_tasks_total": metadata_task_total,
                "metadata_tasks_completed": completed_tasks,
                "metadata_tasks_failed": failed_tasks,
                "metadata_tasks_skipped": skipped_tasks,
                "metadata_tasks_running": running_tasks,
                "metadata_tasks_queued": queued_tasks,
                "metadata_active_tasks": active[:32],
                "metadata_last_progress_at": iso_now() if state in {"complete", "failed", "skipped"} else self.repo.get_build(build_id).get("metadata_last_progress_at"),
            }
            self._update(build_id, **updates)

    def _schedule_build_enrichment(
        self, build_id: str, request: dict[str, Any], manifest: dict[str, Any], records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Schedule incomplete records and merge worker checkpoints with live human edits."""
        total = max(1, len(records))
        pending = [index for index, record in enumerate(records) if not record.get("metadata_complete")]
        priority_ids = {str(value) for value in request.get("_priority_record_ids", [])}
        pending.sort(key=lambda index: (0 if str(records[index].get("record_id") or "") in priority_ids else 1, index))
        already_complete = len(records) - len(pending)
        metadata_started_at = self.repo.get_build(build_id).get("metadata_started_at") or iso_now()
        self._update(
            build_id,
            metadata_enriched_count=already_complete,
            metadata_enrichment_total=len(records),
            metadata_concurrency=max(1, min(16, int(request.get("max_concurrent_requests") or 1))),
            metadata_started_at=metadata_started_at,
            metadata_last_progress_at=iso_now(),
            metadata_settle_requested=False,
        )
        # Metadata enrichment is book-length work and may take minutes on a
        # local model. Track readiness per record so completed records can be
        # reviewed immediately instead of locking the entire book until the
        # final LLM call finishes.
        for index, record in enumerate(records):
            if index in pending:
                # A process restart may leave a record marked running. No worker
                # survives the restart, so it safely returns to the queue while
                # per-family checkpoints determine where enrichment resumes.
                record["metadata_enrichment_state"] = "queued"
                record.setdefault("metadata_stage_status", {})
            else:
                record["metadata_enrichment_state"] = "complete"
        self.repo.save_records(build_id, records)
        max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
        metadata_families = ("discourse", "quotation", "indexing")
        # Fast mode still exposes all three family states, but deliberately
        # skipped families settle immediately and do not consume provider time.
        metadata_task_total = len(records) * len(metadata_families)

        initial_states = _metadata_family_states(records)
        self._update(
            build_id, metadata_tasks_total=metadata_task_total,
            metadata_tasks_completed=sum(1 for value in initial_states if value == "complete"),
            metadata_tasks_failed=sum(1 for value in initial_states if value in {"failed", "needs_review"}),
            metadata_tasks_skipped=sum(1 for value in initial_states if value == "skipped"),
            metadata_tasks_running=0,
            metadata_tasks_queued=sum(1 for value in initial_states if value == "queued"),
            metadata_active_tasks=[],
        )

        def persist_metadata_stage(snapshot: dict[str, Any], task_name: str, state: str, error_text: str | None) -> None:
            self._persist_build_metadata_stage(build_id, metadata_task_total, snapshot, task_name, state, error_text)

        if pending:
            # Parallelism is a build-level execution concern. Each worker performs
            # the three small metadata families serially for one record, while the
            # main thread alone updates/checkpoints the shared JSONL. This avoids
            # corrupting restart state and respects provider-profile concurrency.
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-corpus-meta") as pool:
                futures = {}
                for index in pending:
                    if self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled")
                    record = dict(records[index])
                    previous_text = str(records[index - 1].get("text") or "") if index > 0 else ""
                    next_text = str(records[index + 1].get("text") or "") if index + 1 < len(records) else ""
                    future = pool.submit(
                        self._enrich_record,
                        record,
                        manifest,
                        request,
                        previous_text=previous_text,
                        next_text=next_text,
                        build_id=build_id,
                        stage_callback=persist_metadata_stage,
                    )
                    futures[future] = index
                completed = already_complete
                for future in as_completed(futures):
                    if self._cancelled(build_id):
                        for outstanding in futures:
                            outstanding.cancel()
                        raise InterruptedError("Corpus build cancelled")
                    index = futures[future]
                    try:
                        completed_record = future.result()
                        completed_record["metadata_enrichment_state"] = "complete"
                        records[index] = completed_record
                    except Exception as exc:
                        # A programming/provider failure in one metadata worker
                        # must never discard the other successfully enriched
                        # records in a book-length build. Preserve the immutable
                        # source-derived record and route this item to review.
                        fallback = dict(records[index])
                        fallback["metadata_complete"] = False
                        fallback["metadata_needs_attention"] = True
                        profile_for_failure = self._profile_for(build_id)
                        required_failure_fields = list(profile_for_failure.get("required_metadata_fields") or [])
                        failure_status = fallback.setdefault("metadata_field_status", {})
                        for field in required_failure_fields:
                            current = failure_status.get(field) if isinstance(failure_status.get(field), dict) else {}
                            if current.get("status") == "deterministic":
                                continue
                            failure_status[field] = {
                                "status": "unresolved", "method": "llm", "confidence": None,
                                "reason_code": "llm_failed",
                                "reason": f"Metadata worker failed before this field could be validated: {exc}",
                            }
                        fallback["metadata_incomplete_fields"] = [field for field in required_failure_fields if str((failure_status.get(field) or {}).get("status") or "") in {"unresolved", "invalid"} or fallback.get(field) in (None, "", [])]
                        fallback["metadata_stage_status"] = {**(fallback.get("metadata_stage_status") or {}), "worker": "needs_review"}
                        reasons = list(fallback.get("metadata_attention_reasons") or [])
                        reasons.append(f"Metadata worker failed and requires review: {exc}")
                        fallback["metadata_attention_reasons"] = list(dict.fromkeys(reason for reason in reasons if reason))[:50]
                        fallback["metadata_enrichment_state"] = "failed"
                        records[index] = fallback
                        self._append_warning(build_id, f"{fallback.get('record_id')}: metadata worker failed; the source-bound record was preserved for review.")
                    completed += 1
                    # Persist one completed worker result without overwriting
                    # human review decisions already made on other completed
                    # records while enrichment continues. The disk copy is the
                    # authoritative live review state; replace only this record.
                    with self._lock:
                        live_records = self.repo.load_records(build_id)
                        completed_id = str(records[index].get("record_id") or "")
                        live_index = next((i for i, row in enumerate(live_records) if str(row.get("record_id") or "") == completed_id), None)
                        if live_index is None:
                            live_records = records
                        else:
                            live_records[live_index] = _merge_enrichment_snapshot(live_records[live_index], records[index], self._allowed_fields(build_id))
                        records = live_records
                        self.repo.save_records(build_id, records)
                    self._update(
                        build_id,
                        stage="enriching",
                        progress=0.42 + 0.43 * (completed / total),
                        metadata_enriched_count=completed,
                        metadata_enrichment_total=len(records),
                        metadata_total=len(records),
                        metadata_concurrency=max_workers,
                    )

        settled_records = self.repo.load_records(build_id)
        requeued = [row for row in settled_records if row.get("metadata_requeue_requested")]
        if requeued:
            # A boundary edit may arrive while the first worker pass is still
            # running. Clear the one-shot marker and immediately schedule the
            # changed records again against their new reviewed text.
            priority_ids = [str(row.get("record_id") or "") for row in requeued]
            for row in requeued:
                row.pop("metadata_requeue_requested", None)
            self.repo.save_records(build_id, settled_records)
            prioritized_request = dict(request)
            prioritized_request["_priority_record_ids"] = priority_ids
            return self._schedule_build_enrichment(build_id, prioritized_request, manifest, settled_records)
        settled_states = _metadata_family_states(settled_records)
        self._update(
            build_id,
            metadata_tasks_total=metadata_task_total,
            metadata_tasks_completed=sum(1 for value in settled_states if value == "complete"),
            metadata_tasks_failed=sum(1 for value in settled_states if value in {"failed", "needs_review"}),
            metadata_tasks_skipped=sum(1 for value in settled_states if value == "skipped"),
            metadata_tasks_running=0,
            metadata_tasks_queued=0,
            metadata_active_tasks=[],
            metadata_last_progress_at=iso_now(),
        )

        return records

    def _finalize_build_review(self, build_id: str, scope: BuildScope, records: list[dict[str, Any]]) -> None:
        """Revalidate settled records and publish the authoritative handoff to review."""
        build, source_blocks = scope.build, scope.source_blocks
        # All automatic workers have now settled. Recompute the authoritative
        # record/metadata queues once before handing control to human review so
        # the first review screen is already internally consistent.
        self._rewrite_and_validate(build_id, records)
        records = self.repo.load_records(build_id)
        profile = self._profile_of_build(build)
        validation = self.validate_records(source_blocks, records, profile)
        needs_review = sum(1 for record in records if record.get("needs_review"))
        boundary_review_count = len(self.repo.get_build(build_id).get("segmentation_boundary_reviews") or [])
        # Construction is complete, but the corpus lifecycle is not complete
        # until review/acceptance and publication finish. Keep a clear 90%
        # handoff into human review instead of declaring 100% prematurely.
        status = "awaiting_review"
        current = self.repo.get_build(build_id)
        existing_op = current.get("metadata_operation") if isinstance(current.get("metadata_operation"), dict) else {}
        if str(existing_op.get("state") or "") in {"queued", "running"}:
            operation = existing_op
        else:
            operation = _initial_enrichment_operation(
                build_id, records, started_at=str(current.get("metadata_started_at") or "") or None,
            )
        self._update(
            build_id,
            status=status,
            stage="review",
            progress=0.90,
            finished_at=iso_now(),
            record_count=len(records),
            needs_review_count=needs_review,
            boundary_review_count=boundary_review_count,
            accepted_count=sum(1 for record in records if record.get("accepted")),
            rejected_count=sum(1 for record in records if str(record.get("review_disposition") or "") == "rejected"),
            source_problem_count=sum(1 for record in records if record.get("source_quality_issues")),
            validation=validation,
            resumable=False,
            retrying_segmentation=False,
            metadata_operation=operation,
        )


    def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        automation_running = str(build.get("status") or "") in {"queued", "running"} and str(build.get("stage") or "") in {"enriching", "metadata_retry"}
        # A re-run pass overlaps review too. Its records already finished their first
        # enrichment, so it only needs the running state preserved (below), not the
        # per-record "still enriching" handling that automation_running drives.
        pass_running = str(build.get("status") or "") in {"queued", "running"} and str(build.get("stage") or "") == "metadata_enrichment_rerun"
        for record in records:
            if not record.get("review_disposition"):
                record["review_disposition"] = "accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"
            record["rejected"] = str(record.get("review_disposition")) == "rejected"
        blocks = [
            block for block in self.repo.load_blocks(build["asset_id"])
            if not block.get("excluded_reason")
        ]
        blocks = _manifest_main_text_blocks(
            blocks, build.get("manifest") or {}, bounds_confirmed=bool(build.get("manifest_confirmed_at"))
        )
        build["source_quality"] = page_source_quality_report(blocks)
        profile = self._profile_of_build(build)
        validation = self.validate_records(blocks, records, profile)
        self.repo.save_records(build_id, records)
        build["record_count"] = len(records)
        build["validation"] = validation
        # Metadata completion is derived from persisted record state, never from a
        # stale worker counter. This makes retries, human edits, refreshes, and
        # publication gating agree on the same truth.
        build["metadata_total"] = len(records)
        # Required-metadata completeness is derived from unresolved/review queues.
        # This prevents stale worker booleans from contradicting an empty issue list.
        for record in records:
            if not (automation_running and not _metadata_enrichment_finished(record)):
                _sync_record_metadata_state(record, profile)
                _enforce_review_invariants(record)
            _decorate_review_state(record)
        self.repo.save_records(build_id, records)
        # Review counts are derived only after metadata state and review invariants
        # have been synchronized. Otherwise a record reopened by validation could
        # still be reported as accepted until the next request, which is exactly
        # the kind of stale state that makes review appear to "come back."
        build["needs_review_count"] = sum(1 for record in records if record.get("needs_review"))
        build["accepted_count"] = sum(1 for record in records if str(record.get("review_disposition") or "") == "accepted")
        build["rejected_count"] = sum(1 for record in records if str(record.get("review_disposition") or "") == "rejected")
        build["source_problem_count"] = sum(1 for record in records if bool(record.get("source_quality_issues")))
        build["metadata_completed"] = sum(1 for record in records if bool(record.get("metadata_complete")))
        issue_records: list[dict[str, Any]] = []
        issue_rows: list[dict[str, Any]] = []
        by_field: Counter[str] = Counter()
        by_reason: Counter[str] = Counter()
        invalid_by_field: Counter[str] = Counter()
        retryable_record_ids: set[str] = set()
        human_record_ids: set[str] = set()
        retryable_types = {"not_run", "llm_failed", "evidence_failed", "invalid_value", "unresolved"}
        for record in records:
            if str(record.get("review_disposition") or "") == "rejected" or record.get("rejected"):
                # Rejected records remain recoverable but are outside the publishable
                # corpus, so their unresolved metadata must not block publication.
                continue
            if automation_running and not _metadata_enrichment_finished(record):
                continue
            incomplete = list(dict.fromkeys([str(value) for value in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])]))
            statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            record_issues: list[dict[str, Any]] = []
            for field in incomplete:
                by_field[field] += 1
                status_info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
                if status_info.get("status") == "invalid":
                    invalid_by_field[field] += 1
                issue_type = _metadata_issue_type(status_info, record)
                by_reason[issue_type] += 1
                retryable = issue_type in retryable_types
                row = {
                    "record_id": record.get("record_id"), "field": field,
                    "issue_type": issue_type, "retryable": retryable,
                    "status": status_info.get("status") or "unresolved",
                    "reason": status_info.get("reason") or "",
                    "method": status_info.get("method") or "",
                    "confidence": status_info.get("confidence"),
                    "current_value": record.get(field),
                    "page_start": record.get("page_start"), "page_end": record.get("page_end"),
                }
                issue_rows.append(row); record_issues.append(row)
                rid = str(record.get("record_id") or "")
                if retryable: retryable_record_ids.add(rid)
                else: human_record_ids.add(rid)
            if incomplete:
                issue_records.append({
                    "record_id": record.get("record_id"),
                    "fields": incomplete,
                    "issues": record_issues,
                    "page_start": record.get("page_start"),
                    "page_end": record.get("page_end"),
                })
        build["metadata_issue_summary"] = {
            "records_incomplete": len(issue_records),
            "fields_unresolved": sum(by_field.values()),
            "by_field": dict(sorted(by_field.items())),
            "by_reason": dict(sorted(by_reason.items())),
            "invalid_by_field": dict(sorted(invalid_by_field.items())),
            "auto_retry_records": len(retryable_record_ids),
            "human_review_records": len(human_record_ids),
            "auto_retry_fields": sum(1 for row in issue_rows if row["retryable"]),
            "human_review_fields": sum(1 for row in issue_rows if not row["retryable"]),
            "issues": issue_rows[:1000],
            "records": issue_records[:250],
        }
        # Measure automation by useful, persisted contribution rather than merely
        # counting successful HTTP/model calls. These metrics let the UI make the
        # cost/benefit of enrichment visible to reviewers.
        contribution: Counter[str] = Counter()
        llm_elapsed_ms = 0
        llm_family_calls = 0
        for record in records:
            status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            for _field, info in status_map.items():
                if not isinstance(info, dict):
                    continue
                state = str(info.get("status") or "")
                if state == "inherited": contribution["inherited_fields"] += 1
                elif state == "deterministic": contribution["deterministic_fields"] += 1
                elif state == "model_inferred": contribution["llm_fields_usable"] += 1
                elif state in {"unresolved", "invalid"} and str(info.get("method") or "").startswith("llm"):
                    contribution["llm_fields_review"] += 1
                    if info.get("proposed_value") not in (None, "", []):
                        contribution["llm_fields_proposed"] += 1
                elif state in {"human_confirmed", "human_override"}: contribution["human_fields"] += 1
            ledger = record.get("metadata_execution_ledger") if isinstance(record.get("metadata_execution_ledger"), dict) else {}
            for family in ("discourse", "quotation", "indexing"):
                entry = ledger.get(family) if isinstance(ledger.get(family), dict) else {}
                state = str(entry.get("state") or "")
                if state in {"complete", "failed"}: llm_family_calls += 1
                try: llm_elapsed_ms += int(entry.get("elapsed_ms") or 0)
                except (TypeError, ValueError): pass
                contribution[f"tasks_{state or 'unknown'}"] += 1
        useful = int(contribution.get("llm_fields_usable") or 0) + int(contribution.get("llm_fields_proposed") or 0)
        build["llm_contribution"] = {
            **dict(contribution),
            "family_calls": llm_family_calls,
            "elapsed_ms": llm_elapsed_ms,
            "useful_fields_per_minute": round(useful / max(1 / 60, llm_elapsed_ms / 60000), 2) if llm_elapsed_ms else 0.0,
            "enrichment_mode": str((build.get("request") or {}).get("enrichment_mode") or "fast"),
            "semantic_indexing": bool((build.get("request") or {}).get("semantic_indexing")),
        }
        build["review_queue_counts"] = _queue_counts(records)
        build["boundary_review_count"] = len(build.get("segmentation_boundary_reviews") or build.get("segmentation_unresolved_regions") or [])
        # Any human/topology edit after publication creates a new unpublished
        # revision. Keep the old publication in history rather than presenting
        # a stale JSONL as if it represented the edited records.
        if build.get("publication"):
            history = list(build.get("publication_history") or [])
            history.append(build["publication"])
            build["publication_history"] = history[-20:]
            build["publication"] = None
            build["publication_status"] = "unpublished"
        reviewed_count = min(build["record_count"], build["accepted_count"] + build["rejected_count"])
        review_fraction = reviewed_count / max(1, build["record_count"])
        blockers = bool(build["needs_review_count"] or build["boundary_review_count"] or not validation.get("valid"))
        records_accepted = bool(build["accepted_count"] > 0 and build["accepted_count"] + build.get("rejected_count", 0) == build["record_count"] and not build["needs_review_count"] and not build["boundary_review_count"])
        metadata_total = int(build.get("metadata_total") or 0)
        metadata_completed = int(build.get("metadata_completed") or 0)
        metadata_complete = metadata_total == 0 or metadata_completed >= metadata_total
        all_ready = bool(records_accepted and metadata_complete and not blockers)
        # Automated construction owns the first 90% of lifecycle progress. Human
        # review may begin progressively during book-length metadata enrichment,
        # but a review mutation must never make the build look as though the
        # background enrichment job has stopped. Preserve the running stage until
        # the coordinator itself performs the final handoff to review.
        if automation_running or pass_running:
            build["status"] = "running"
            build["stage"] = str(build.get("stage") or "enriching")
            build["progress"] = max(float(build.get("progress") or 0.42), 0.42)
        elif all_ready:
            build["progress"] = 0.98
            build["status"] = "ready"
            build["stage"] = "ready"
        else:
            # Metadata decisions are part of record review in v11; there is no
            # second, opaque post-review metadata phase.
            build["progress"] = 0.90 + 0.06 * review_fraction
            build["status"] = "awaiting_review"
            build["stage"] = "review"
        self._refresh_workflow_fields(build)
        self.repo.save_build(build)
        return build

    @_serialize_record_mutation
    def _write_start_page_to_layout(self, asset_id: str, start_page: Any) -> None:
        """Keep one answer for "where does the main text start" per PDF.

        The reviewer-confirmed layout plan on the source asset is the authority (it also drives
        printed page numbers and region labels), so a start page edited on the document manifest is
        written through to it. A PDF with no confirmed layout has only the manifest value.
        """
        try:
            layout = self.repo.get_asset(asset_id).get("document_layout")
        except Exception:  # noqa: BLE001 - a missing asset means there is no layout to keep in step
            return
        if not isinstance(layout, dict) or layout.get("confirmed_by") != "human":
            return
        if layout.get("main_text_pdf_start") == start_page:
            return
        self.repo.update_document_layout(asset_id, {**layout, "main_text_pdf_start": start_page})

    def regenerate_manifest(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Ask the model for the document analysis again and fill only what is still empty.

        A build whose first analysis failed (a model that was still loading, a restart) falls back to the PDF's own
        properties. This tries again with the current provider without touching anything a person has entered or
        that an earlier analysis already found; values that are missing are added through the ordinary manifest save,
        so records inherit them and the affected ones are reopened as for any manifest edit.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before analysing the document again.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        asset = self.repo.get_asset(str(build.get("asset_id") or ""))
        blocks = self.repo.load_blocks(str(build.get("asset_id") or ""))
        active_request = self._interactive_llm_request(build_id, request or None)
        fresh = self._document_manifest(asset, blocks, active_request, build_id)
        if bool(active_request.get("auto_enrich_work_metadata", True)):
            fresh = self._catalog_enrich_manifest(fresh, active_request, build_id)
        current = dict(build.get("manifest") or {})
        empty: tuple[object, ...] = (None, "", [])
        filled = {
            key: fresh[key] for key in DocumentManifestModel.model_fields
            if current.get(key) in empty and fresh.get(key) not in empty
        }
        if not filled:
            return {"build": build, "filled": []}
        return {"build": self.patch_manifest(build_id, filled), "filled": sorted(filled)}

    def patch_manifest(self, build_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        # Serialized with enrichment's own record writes: this rewrites every record's inherited fields, and a
        # pass merging results at the same moment must not have its results overwritten by a stale copy.
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            if stage not in {"enriching", "metadata_retry", "metadata_enrichment_rerun"}:
                raise ValueError("Document metadata becomes editable after segmentation is complete.")
            if {"main_text_start_page", "main_text_end_page"} & set(changes):
                raise ValueError("Main-text page boundaries are structural and cannot change while background enrichment is running.")
        current_revision = int(build.get("manifest_revision") or 1)
        if expected_revision is not None and int(expected_revision) != current_revision:
            raise ValueError("This document manifest changed after it was opened. Reload it before saving.")
        allowed = set(DocumentManifestModel.model_fields)
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValueError(f"Unknown document manifest field(s): {', '.join(unknown)}")
        current = dict(build.get("manifest") or {})
        candidate = {key: current.get(key) for key in allowed}
        candidate.update(changes)
        validated = DocumentManifestModel.model_validate(candidate).model_dump(mode="json")
        manifest = {**current, **validated}
        manifest["source_asset_id"] = build.get("asset_id")
        start_changed = "main_text_start_page" in changes and validated.get("main_text_start_page") != current.get("main_text_start_page")
        if start_changed:
            manifest.pop("main_text_start_inference", None)  # its clues describe a value that is no longer the one in use
            self._write_start_page_to_layout(str(build.get("asset_id") or ""), validated.get("main_text_start_page"))
        build["manifest"] = manifest
        build["manifest_revision"] = current_revision + 1
        build["manifest_reviewed_at"] = iso_now()
        self.repo.save_checkpoint(build_id, "manifest", manifest)
        self.repo.save_build(build)

        records = self.repo.load_records(build_id)
        if records:
            for record in records:
                # The page range also classifies the record (main text, front matter, back matter), so a change to it
                # must count as a change here even though those fields are not inherited from the manifest.
                before = ({field: record.get(field) for field in MANIFEST_INHERITED_FIELDS}, record.get("inline_citation"), record.get("full_citation"), record.get("primary_text"), record.get("region_type"))
                field_status = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
                if start_changed:
                    # The layout plan labelled these records from the old start page; the new one relabels them.
                    for field in ("region_type", "primary_text"):
                        info = field_status.get(field)
                        if isinstance(info, dict) and info.get("method") == "human_document_layout":
                            field_status.pop(field, None)
                for field in MANIFEST_INHERITED_FIELDS:
                    info = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
                    if str(info.get("status") or "") in {"human_override", "human_confirmed"}:
                        continue
                    record.pop(field, None)
                    if str(info.get("status") or "") == "inherited":
                        field_status.pop(field, None)
                record["metadata_field_status"] = field_status
                _apply_manifest_metadata(record, manifest)
                inline, full = _citation_strings(record)
                record["inline_citation"] = inline
                record["full_citation"] = full
                after = ({field: record.get(field) for field in MANIFEST_INHERITED_FIELDS}, inline, full, record.get("primary_text"), record.get("region_type"))
                # A record whose inherited values did not actually change has nothing new to review: leave its
                # acceptance alone instead of reopening every record for an edit that did not touch it.
                if after == before:
                    continue
                record["accepted"] = False
                record["needs_review"] = True
                record["review_reason"] = "Document manifest changed during human review; inherited metadata and citations were regenerated."
                record["record_revision"] = int(record.get("record_revision") or 1) + 1
            self._rewrite_and_validate(build_id, records)
            build = self.repo.get_build(build_id)
        return build


    # Backward-compatible internal alias for older call sites in this source tree.


    def preview_record(self, build_id: str, record_id: str) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        record = next((row for row in records if row.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        _present_for_reviewer(record)  # the preview is built from the record as this reviewer may see it
        public = serialize_public_record(record)
        errors = validate_publication_record(public)
        unresolved = list(dict.fromkeys([str(v) for v in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])]))
        return {
            "record": public,
            "jsonl": json.dumps(public, ensure_ascii=False),
            "validation_errors": errors,
            "unresolved_fields": unresolved,
            "would_publish": str(record.get("review_disposition") or "pending") == "accepted" and not errors and not unresolved,
        }

    def touchup_record_text(self, build_id: str, record_id: str, request: dict[str, Any], instructions: str = "", text_override: str | None = None) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        record = next((row for row in records if row.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        current_text = str(text_override if text_override is not None else record.get("text") or "")
        if not current_text.strip():
            raise ValueError("Record text is empty.")
        _ = self.repo.get_build(build_id).get("request") or {}
        active_request = self._interactive_llm_request(build_id, request or None)
        prompt = build_text_touchup_prompt(current_text, instructions)
        result = self._chat_json(active_request, prompt, response_model=TextTouchupResponseModel, max_tokens=min(8192, max(2048, len(current_text)//3)), schema_name="record_text_touchup", attempts=2, build_id=build_id)
        proposed = _sanitize_touchup_output(str(result.get("text") or ""), current_text)
        if not proposed:
            raise ValueError("LLM text touch-up returned empty text.")
        no_change = proposed == current_text
        provider, model, _, _, _ = _llm_config(active_request)
        return {
            "record_id": record_id,
            "proposal_id": f"touchup-{uuid.uuid4().hex[:12]}",
            "run_id": str(request.get("run_id") or f"touchup-run-{uuid.uuid4().hex[:12]}"),
            "source_text": current_text,
            "proposed_text": proposed,
            "no_change": no_change,
            "changes": list(result.get("changes") or []),
            "warnings": list(result.get("warnings") or []),
            "provider": provider,
            "model": model,
            "created_at": iso_now(),
        }

    @_serialize_record_mutation
    def set_text_touchup_proposal_status(self, build_id: str, record_id: str, status: str) -> dict[str, Any]:
        if status not in {"pending_review", "dismissed"}:
            raise ValueError("Proposal status must be pending_review or dismissed.")
        records = self.repo.load_records(build_id)
        record = next((row for row in records if row.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        proposal = record.get("text_touchup_proposal")
        if not isinstance(proposal, dict) or not proposal.get("proposed_text"):
            raise ValueError("This record has no text touch-up proposal.")
        proposal["status"] = status
        proposal["updated_at"] = iso_now()
        record["text_touchup_proposal"] = proposal
        if status == "dismissed":
            reasons = [
                reason
                for reason in record.get("metadata_attention_reasons") or []
                if "text touch-up proposal" not in str(reason).casefold()
            ]
            record["metadata_attention_reasons"] = reasons
            if not record.get("metadata_review_fields") and not record.get("metadata_incomplete_fields"):
                record["metadata_needs_attention"] = False
                record["needs_review"] = bool(record.get("source_quality_issues"))
        else:
            record["metadata_needs_attention"] = True
            record["needs_review"] = True
        self._rewrite_and_validate(build_id, records)
        return next(
            row for row in self.repo.load_records(build_id)
            if row.get("record_id") == record_id
        )

    @_serialize_record_mutation
    def save_text_touchup_proposal(self, build_id: str, record_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        record = next((row for row in records if row.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        record["text_touchup_proposal"] = {
            "proposal_id": str(proposal.get("proposal_id") or f"touchup-{uuid.uuid4().hex[:12]}"),
            "run_id": str(proposal.get("run_id") or ""),
            "status": "pending_review",
            "source_text": str(proposal.get("source_text") or ""),
            "proposed_text": str(proposal.get("proposed_text") or ""),
            "changes": list(proposal.get("changes") or []),
            "warnings": list(proposal.get("warnings") or []),
            "provider": str(proposal.get("provider") or ""),
            "model": str(proposal.get("model") or ""),
            "created_at": iso_now(),
        }
        record["needs_review"] = True
        record["metadata_needs_attention"] = True
        reasons = list(record.get("metadata_attention_reasons") or [])
        reasons.append("An LLM text touch-up proposal is available for review; reviewed text remains unchanged until approved.")
        record["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
        self._rewrite_and_validate(build_id, records)
        return next(row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id)

    @_serialize_record_mutation
    def publish(self, build_id: str, *, require_acceptance: bool = True) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        validation = build.get("validation") or {}
        self._refresh_workflow_fields(build)
        publishable = publishable_records(records)
        blocker = publication_blocker(build, publishable, validation, require_acceptance=require_acceptance)
        if blocker:
            raise ValueError(blocker)
        publication_id = f"publication-{build_id.removeprefix('build-')}-{uuid.uuid4().hex[:8]}"
        created_at = iso_now()
        path = self.repo.publication_path(publication_id)
        hasher = hashlib.sha256()
        with path.open("wb") as handle:
            for record in publishable:
                # Use the same serializer as the per-record JSONL preview so the
                # reviewer sees the exact eventual public record shape.
                public = serialize_public_record(record)
                schema_errors = validate_publication_record(public)
                if schema_errors:
                    joined = "; ".join(schema_errors[:8])
                    raise ValueError(f"Publication schema validation failed for {public.get('record_id') or 'unknown record'}: {joined}")
                line = (json.dumps(public, ensure_ascii=False) + "\n").encode("utf-8")
                hasher.update(line)
                handle.write(line)
        publication = {"publication_id": publication_id, "filename": f"{Path(build.get('source_filename') or 'corpus').stem}.jsonl", "sha256": hasher.hexdigest(), "record_count": len(publishable), "excluded_rejected_count": len(records) - len(publishable), "created_at": created_at}
        build["publication"] = publication
        # Build lifecycle and publication lifecycle are separate. A publication is
        # an immutable snapshot of a ready build, not a new build-processing state.
        build["publication_status"] = "published"
        build["status"] = "ready"
        build["stage"] = "ready"
        build["progress"] = 1.0
        build["published_at"] = created_at
        build["finished_at"] = created_at
        self.repo.save_build(build)
        return publication


pdf_corpus_repository = PdfCorpusRepository()
pdf_corpus_builds = PdfCorpusBuildManager(pdf_corpus_repository)
