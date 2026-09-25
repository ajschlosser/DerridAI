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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import fitz
from pydantic import BaseModel, ValidationError

from .autonomous import Policy as AutonomousPolicy
from .config import APP_VERSION as APP_VERSION
from .config import settings
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
    _llm_config,
    _parse_json_robust,
    _stage_limits,
    _stage_timeouts,
)
from .corpus_llm_helpers import (
    _validate_execution_budget as _validate_execution_budget,
)
from .corpus_manifest_workflow import ManifestWorkflowMixin

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
from .corpus_metadata_enrichment_execution import MetadataEnrichmentExecutionMixin
from .corpus_models import (
    CORPUS_PROFILES,
    PROFILE_VERSION,
    DocumentManifestModel,
    TextTouchupResponseModel,
)
from .corpus_models import (
    DOCUMENT_PROMPT_VERSION as DOCUMENT_PROMPT_VERSION,
)
from .corpus_models import (
    METADATA_PROMPT_VERSION as METADATA_PROMPT_VERSION,
)
from .corpus_models import (
    SCHEMA_VERSION as SCHEMA_VERSION,
)
from .corpus_models import (
    SEGMENTATION_PROMPT_VERSION as SEGMENTATION_PROMPT_VERSION,
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
    _metadata_issue_type,
    _present_for_reviewer,
)
from .corpus_reviewer_helpers import (
    _operation_from_build as _operation_from_build,
)
from .corpus_schema_profile import SchemaProfileMixin
from .corpus_segmentation import (
    _apply_boundary_adjudication_to_records as _apply_boundary_adjudication_to_records,
)
from .corpus_segmentation import (
    _apply_manifest_metadata,
    _construct_records,
    _manifest_main_text_blocks,
    _mark_segmentation_review,
    _record_sizing_policy,
    _topology_quality_report,
    _topology_sanity,
)
from .corpus_segmentation import (
    _candidate_route as _candidate_route,
)
from .corpus_segmentation import (
    _deterministic_boundary_candidates as _deterministic_boundary_candidates,
)
from .corpus_segmentation import (
    _is_protected_transition as _is_protected_transition,
)
from .corpus_segmentation import (
    _normalize_text as _normalize_text,
)
from .corpus_segmentation import (
    _normalize_topology as _normalize_topology,
)
from .corpus_segmentation_execution import BuildSegmentationExecutionMixin
from .enrichment_cycles import (
    GlobalLearningStore,
)
from .enrichment_ledger import (
    ACCEPTED,
    BLIND_LABEL,
    CORRECTED,
    REJECTED,
    EnrichmentLedger,
)
from .error_severity import severity as error_severity
from .main_text_start import infer_main_text_start
from .metadata_exemplar_projection import (
    dirty_metadata_exemplar_build_ids,
    project_build_metadata_exemplars,
)
from .metadata_exemplar_retrieval import ChromaMetadataExemplarIndex
from .metadata_schema import (
    MetadataSchema,
)
from .metadata_schema_store import SchemaStore
from .metadata_values import is_placeholder
from .models import WorkMetadataRequest, WorkMetadataSeed
from .rag import _citation_strings, chat_complete
from .run_guidance import find_guidance_matches
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
    from .source_safety import validate_image

    validate_image(data)
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
        from .source_safety import check_size, executable_version, extraction_provenance

        check_size(data, settings.pdf_max_upload_mb * 1024 * 1024)
        illegibility = clamp_illegibility(source_illegibility)
        kind = detect_media_kind(filename, data, content_type)
        digest = hashlib.sha256(data).hexdigest()
        # Default PDF uploads keep the historical content-addressed id.
        identity = digest
        if kind != "pdf" or ocr_mode != "auto" or illegibility:
            identity = hashlib.sha256(f"{digest}|{kind}|source-extraction-v2|{ocr_mode}|{illegibility:.2f}".encode()).hexdigest()
        if catalog_metadata and catalog_metadata.get("gutenberg_id"):
            identity = hashlib.sha256(f"{identity}|gutenberg|{catalog_metadata['gutenberg_id']}".encode()).hexdigest()
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
            provenance = extraction_provenance(str(extracted.get("extractor") or kind))
            if extracted.get("ocr_pages"):
                provenance["tools"]["tesseract"] = executable_version("tesseract")
                provenance["ocr_languages"] = ocr_languages
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
                "extraction_provenance": provenance,
                "catalog_metadata": dict(catalog_metadata or {}),
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
        if meta.get("media_kind", "pdf") not in {"pdf", "image"}:
            return meta
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
            if asset.get("media_kind", "pdf") not in {"pdf", "image"}:
                raise ValueError("Page layout is unavailable for this source format.")
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
            if asset.get("media_kind", "pdf") not in {"pdf", "image"}:
                raise ValueError("Page layout is unavailable for this source format.")
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
                deterministic_ingest = record.get("deterministic_ingest")
                if isinstance(deterministic_ingest, dict):
                    speakers = deterministic_ingest.get("speakers")
                    if isinstance(speakers, (list, tuple)):
                        for speaker in speakers:
                            if isinstance(speaker, str) and speaker.strip() and not is_placeholder(speaker):
                                metadata_values.setdefault("speaker", set()).add(speaker.strip())
                field_status = record.get("metadata_field_status")
                if isinstance(field_status, dict):
                    for field, status in field_status.items():
                        if not isinstance(status, dict):
                            continue
                        for candidate_key in ("proposed_value", "llm_value"):
                            candidate = status.get(candidate_key)
                            candidates = candidate if isinstance(candidate, (list, tuple)) else [candidate]
                            for item in candidates:
                                if isinstance(item, str) and item.strip() and not is_placeholder(item):
                                    metadata_values.setdefault(field, set()).add(item.strip())
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




class PdfCorpusBuildManager(BuildLifecycleMixin, EditorialMemoryMixin, ManifestWorkflowMixin, OperationsMixin, ReviewActionsMixin, EnrichmentRerunsMixin, SchemaProfileMixin, BuildSegmentationExecutionMixin, MetadataEnrichmentExecutionMixin):
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
        # Semantic metadata memory is derived and best-effort. The Chroma client is
        # opened lazily only when reviewed exemplars actually exist for retrieval.
        self._progressive_metadata_index = ChromaMetadataExemplarIndex()
        self._progressive_metadata_warning_builds: set[str] = set()
        self._metadata_projection_lock = threading.RLock()
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
        self._recover_metadata_exemplar_projections()

    def _project_metadata_exemplars(
        self,
        build_id: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        with self._metadata_projection_lock:
            return project_build_metadata_exemplars(
                self.repo,
                build_id,
                self._progressive_metadata_index,
                force=force,
            )

    def _schedule_metadata_exemplar_projection(self, build_id: str) -> None:
        # Review durability never depends on Chroma. The SQLite outbox is committed
        # first; projection runs best-effort and an unacknowledged item is retried
        # after restart or the next review in this build.
        self._executor.submit(self._project_metadata_exemplars, build_id)

    def _recover_metadata_exemplar_projections(self) -> None:
        try:
            build_ids = dirty_metadata_exemplar_build_ids(self.repo)
        except Exception:
            return
        for build_id in build_ids:
            self._schedule_metadata_exemplar_projection(build_id)

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
        if asset.get("media_kind", "pdf") not in {"pdf", "image"}:
            result["main_text_start_page"] = None
            result["main_text_end_page"] = None
            result.pop("main_text_start_inference", None)
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
                raw_issues = [str(issue) for issue in topology_validation.get("issues") or []]
                counts = {issue: raw_issues.count(issue) for issue in dict.fromkeys(raw_issues)}
                issues = [
                    f"{issue} ({count} records)" if count > 1 else issue
                    for issue, count in counts.items()
                ]
                raise RuntimeError(
                    "Deterministic topology sanity check failed before metadata enrichment: "
                    + ", ".join(issues or ["unknown topology error"])
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
