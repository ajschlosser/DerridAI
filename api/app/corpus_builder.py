# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import tempfile
import threading
import time
import unicodedata
import urllib.request
import uuid
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Literal

import fitz
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from . import experiment
from .autofill import decide as decide_autofill
from .autofill import in_audit_sample
from .autonomous import Policy as AutonomousPolicy
from .autonomous import may_accept, settle_record
from .config import APP_VERSION, settings

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
from .corpus_pipeline import BuildScope
from .corpus_publication import serialize_public_record, validate_publication_record
from .enrichment_cycles import (
    CONFIDENCE_FIELDS,
    HUMAN_OWNED_STATUSES,
    MAX_PASSES,
    GlobalLearningStore,
    learn_from_pass,
    resolve_conflict,
    same_value,
)
from .enrichment_ledger import (
    ACCEPTED,
    AUTOFILLED,
    BLIND_LABEL,
    CALL,
    CORRECTED,
    PROPOSED,
    RECHECK,
    RECHECK_SEAL,
    REJECTED,
    RESUMED,
    SUSPENDED,
    EnrichmentLedger,
)
from .enrichment_metrics import compute as compute_enrichment_metrics
from .error_severity import severity as error_severity
from .main_text_start import infer_main_text_start
from .metadata_schema import (
    CORE_GROUP,
    DEFAULT_SCHEMA_ID,
    MetadataSchema,
    build_group_prompt,
    default_schema,
    edit_model,
    response_model_for,
)
from .metadata_schema_store import SchemaNotFound, SchemaStore
from .models import OllamaTouchupOptions, WorkMetadataRequest, WorkMetadataSeed
from .rag import _citation_strings, _extract_json, chat_complete
from .reviewer_context import current_reviewer
from .sentence_boundaries import snap_boundaries_to_sentences

SCHEMA_VERSION = "pdf-corpus-v3"
SEGMENTATION_PROMPT_VERSION = "derridai-local-boundaries-v7"
METADATA_PROMPT_VERSION = "derridai-record-metadata-v10"
PUBLICATION_SCHEMA_VERSION = "derridai-corpus-jsonl-v1"
DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v3"
PROFILE_VERSION = "derrida-scholarly-v12"


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


class DocumentManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    short_title: str | None = None
    original_title: str | None = None
    document_author: str | None = None
    translator: str | None = None
    publisher: str | None = None
    publication_place: str | None = None
    publication_year: int | str | None = None
    edition: str | None = None
    isbn: str | None = None
    language: str | None = None
    original_language: str | None = None
    document_is_translation: bool | None = None
    document_type: str | None = None
    main_text_start_page: int | None = None
    main_text_end_page: int | None = None
    notes: str = ""

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_nullable_notes(cls, value: Any) -> str:
        # Optional LLM manifest notes may be JSON null. Normalize that at
        # the schema boundary so an internal validation detail never reaches UI.
        return "" if value is None else str(value)


class BoundaryChangeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: bool = False
    position_holder: bool = False
    stance: bool = False
    target: bool = False
    quotation_frame: bool = False
    discourse_role: bool = False
    argumentative_move: bool = False


class BoundaryDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_block_id: str
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    change: BoundaryChangeModel = Field(default_factory=BoundaryChangeModel)


class SegmentationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundaries: list[BoundaryDecisionModel] = Field(default_factory=list)


class ReconciliationDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_block_id: str
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""


class ReconciliationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[ReconciliationDecisionModel] = Field(default_factory=list)


class FieldEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str = ""


class RecordMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str | None = None
    region_type: str | None = None
    region_author: str | None = None
    primary_text: bool | None = None
    speaker: str | None = None
    position_holder: str | None = None
    target: str | None = None
    discourse_role: str | None = None
    proposition_status: str | None = None
    semantic_function: list[str] = Field(default_factory=list)
    stance: str | None = None
    claim_scope: str | None = None
    is_direct_quote: bool | None = None
    quoted_speaker: list[str] = Field(default_factory=list)
    quoted_author: list[str] = Field(default_factory=list)
    quoted_work: list[str] = Field(default_factory=list)
    quoted_position_holder: list[str] = Field(default_factory=list)
    quoted_addressee: list[str] = Field(default_factory=list)
    quoted_referent: list[str] = Field(default_factory=list)
    quotation_chain: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    works_referenced: list[str] = Field(default_factory=list)


class MetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: RecordMetadataModel = Field(default_factory=RecordMetadataModel)
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    review_reason: str = ""




BoundaryDimension = Literal[
    "speaker", "position_holder", "stance", "target", "quotation_frame",
    "discourse_role", "argumentative_move",
]


class CompactBoundaryDecisionModel(BaseModel):
    """Compact boundary response used by book-scale segmentation.

    Large prose reasons and nested boolean objects were a major source of local
    model truncation. The corpus builder asks only for the topology-changing
    facts here; uncertain boundaries can be adjudicated in a later, smaller call.
    """
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)


class PairBoundaryResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["split", "keep", "uncertain"] = "uncertain"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)


class BatchBoundaryDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[BoundaryDimension] = Field(default_factory=list, max_length=7)


class BoundaryBatchResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[BatchBoundaryDecisionModel] = Field(default_factory=list, max_length=12)


class BoundaryAuditDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundary_id: str = Field(min_length=1, max_length=240)
    decision: Literal["keep", "move_earlier", "move_later", "uncertain"] = "uncertain"
    suggested_after_block_id: str | None = Field(default=None, max_length=200)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list, max_length=8)
    reason: str = Field(default="", max_length=500)


class BoundaryAuditResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[BoundaryAuditDecisionModel] = Field(default_factory=list, max_length=12)


class CompactSegmentationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    boundaries: list[CompactBoundaryDecisionModel] = Field(default_factory=list, max_length=96)


class CompactReconciliationDecisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after: str = Field(min_length=1, max_length=200)
    decision: Literal["split", "keep"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CompactReconciliationResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[CompactReconciliationDecisionModel] = Field(default_factory=list, max_length=16)


class DiscourseMetadataModel(BaseModel):
    # Every field is required (null when unsupported). Optional fields let
    # schema-constrained decoders omit them, which small models do routinely.
    model_config = ConfigDict(extra="forbid")
    language: str | None
    region_type: Literal["front_matter", "main_text", "notes", "bibliography", "index", "appendix", "back_matter", "paratext", "unknown"] | None
    region_author: str | None
    primary_text: bool | None
    speaker: str | None
    position_holder: str | None
    target: str | None
    discourse_role: Literal["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary", "paratext", "bibliographic"] | None
    proposition_status: str | None
    semantic_function: list[str] = Field(max_length=12)
    stance: str | None
    claim_scope: str | None


class RecordFieldAssessmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Missing model confidence is unknown, not 0%. This distinction matters in
    # review UI and avoids manufacturing false certainty from omitted fields.
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_review: bool = False
    reason: str = Field(default="", max_length=500)


class DiscourseMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: DiscourseMetadataModel
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)


class QuotationMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_direct_quote: bool | None
    quoted_speaker: list[str] = Field(max_length=12)
    quoted_author: list[str] = Field(max_length=12)
    quoted_work: list[str] = Field(max_length=12)
    quoted_position_holder: list[str] = Field(max_length=12)
    quoted_addressee: list[str] = Field(max_length=12)
    quoted_referent: list[str] = Field(max_length=12)
    quotation_chain: list[str] = Field(max_length=16)


class QuotationMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: QuotationMetadataModel
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)


class IndexMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topics: list[str] = Field(max_length=24)
    concepts: list[str] = Field(max_length=24)
    persons: list[str] = Field(max_length=24)
    works_referenced: list[str] = Field(max_length=24)


class TextTouchupResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IndexMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required so schema-constrained decoding cannot return assessments alone.
    metadata: IndexMetadataModel
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)












def metric_stage_of(schema_name: str) -> str:
    """Which part of a build a model call belongs to, for words in the UI."""
    return (
        "manifest" if "manifest" in schema_name else
        "segmentation" if ("boundar" in schema_name or "segment" in schema_name or "reconciliation" in schema_name) else
        "metadata" if "record_" in schema_name else
        "other"
    )


def _same_label(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


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

def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_filename(value: str) -> str:
    name = Path(str(value or "source.pdf")).name
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name)[:240] or "source.pdf"


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


def _normalize_text(value: str) -> str:
    """Normalize whitespace without destroying non-ASCII scholarly text.

    NFC keeps composed diacritics stable across PDF-native and OCR extraction
    while retaining every Unicode letter/symbol in the source.
    """
    text = unicodedata.normalize("NFC", str(value or "").replace("\u00ad", ""))
    return re.sub(r"\s+", " ", text).strip()


def _block_text(block: dict[str, Any]) -> str:
    if "lines" in block:
        chunks: list[str] = []
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            text = unicodedata.normalize("NFC", "".join(str(span.get("text") or "") for span in spans))
            if text.strip():
                chunks.append(text.rstrip())
        return unicodedata.normalize("NFC", "\n".join(chunks).strip())
    return unicodedata.normalize("NFC", str(block.get("text") or "").strip())


def _page_blocks(page: fitz.Page, *, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu") -> tuple[list[dict[str, Any]], str, str | None]:
    source = "native"
    warning: str | None = None
    data = page.get_text("dict", sort=True)
    raw_blocks = data.get("blocks") or []
    native_chars = sum(len(_block_text(block)) for block in raw_blocks if block.get("type") == 0)
    should_ocr = ocr_mode == "always" or (ocr_mode == "auto" and native_chars < 24)
    if should_ocr:
        try:
            textpage = page.get_textpage_ocr(language=ocr_languages, dpi=200, full=True)
            data = page.get_text("dict", textpage=textpage, sort=True)
            raw_blocks = data.get("blocks") or []
            source = "ocr"
        except Exception as exc:
            warning = f"OCR unavailable for page {page.number + 1}: {exc}"
            if ocr_mode == "always" and native_chars < 1:
                source = "ocr_failed"

    sizes: list[float] = []
    for block in raw_blocks:
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                if str(span.get("text") or "").strip():
                    try:
                        sizes.append(float(span.get("size") or 0))
                    except (TypeError, ValueError):
                        pass
    median_size = sorted(sizes)[len(sizes) // 2] if sizes else 0.0
    height = float(page.rect.height or 1)
    width = float(page.rect.width or 1)
    blocks: list[dict[str, Any]] = []
    text_index = 0
    for raw in raw_blocks:
        if raw.get("type") != 0:
            continue
        value = _block_text(raw)
        if not value.strip():
            continue
        text_index += 1
        bbox = [round(float(x), 2) for x in (raw.get("bbox") or [0, 0, 0, 0])]
        span_sizes: list[float] = []
        for line in raw.get("lines") or []:
            for span in line.get("spans") or []:
                if str(span.get("text") or "").strip():
                    try:
                        span_sizes.append(float(span.get("size") or 0))
                    except (TypeError, ValueError):
                        pass
        max_size = max(span_sizes) if span_sizes else median_size
        top, bottom = (bbox[1] if len(bbox) > 1 else 0), (bbox[3] if len(bbox) > 3 else 0)
        kind = "paragraph"
        stripped = value.lstrip()
        if median_size and max_size >= median_size * 1.35 and len(value) < 240:
            kind = "heading"
        elif top < height * 0.055 or bottom > height * 0.955:
            kind = "header_footer"
        elif median_size and bottom > height * 0.72 and max_size <= median_size * 0.82:
            kind = "footnote"
        elif re.match(r"^(?:[•▪◦‣–—-]|\d+[.)])\s+", stripped):
            kind = "list_item"
        elif len(bbox) >= 4 and bbox[0] > width * 0.13 and bbox[2] < width * 0.87 and len(value) > 80:
            kind = "block_quote"
        blocks.append({
            "block_id": f"p{page.number + 1:05d}-b{text_index:04d}",
            "page": page.number + 1,
            "bbox": bbox,
            "type": kind,
            "text": value,
            "extraction_method": source,
            "confidence": 1.0 if source == "native" else 0.88 if source == "ocr" else 0.35,
        })
    return blocks, source, warning


def extract_source_document(data: bytes, *, filename: str, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu") -> dict[str, Any]:
    if not data:
        raise ValueError("The uploaded PDF was empty.")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF: {exc}") from exc
    try:
        metadata = {k: v for k, v in (doc.metadata or {}).items() if v}
        pages: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []
        warnings: list[str] = []
        ocr_pages = 0
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            try:
                pdf_label = page.get_label() or None
            except Exception as exc:
                pdf_label = None
                warnings.append(
                    f"PDF page-label lookup failed for physical page {page_index + 1}; "
                    f"continuing with visible-folio detection ({exc})."
                )
            page_blocks, source, warning = _page_blocks(page, ocr_mode=ocr_mode, ocr_languages=ocr_languages)
            visible_page_labels = []
            for candidate in page_blocks:
                if candidate.get("type") != "header_footer":
                    continue
                candidate_text = _normalize_text(candidate.get("text") or "")
                if re.fullmatch(r"(?:[ivxlcdm]+|\d+)", candidate_text, re.I):
                    visible_page_labels.append(candidate_text)
            # Visible printed folios are stronger evidence than the PDF page-label
            # dictionary, which is frequently absent or merely mirrors physical pages.
            printed_label = visible_page_labels[-1] if visible_page_labels else pdf_label
            label_source = "visible_folio" if visible_page_labels else "pdf_label" if pdf_label else None
            for block in page_blocks:
                block["printed_page_label"] = printed_label
                block["printed_page_label_source"] = label_source
            if source == "ocr":
                ocr_pages += 1
            if warning:
                warnings.append(warning)
            pages.append({
                "pdf_page": page_index + 1,
                "printed_page_label": printed_label,
                "printed_page_label_source": label_source,
                "width": round(float(page.rect.width), 2),
                "height": round(float(page.rect.height), 2),
                "block_ids": [block["block_id"] for block in page_blocks],
                "extraction_method": source,
            })
            blocks.extend(page_blocks)

        # Infer missing Arabic printed labels only when at least two visible folios
        # corroborate the same physical-to-printed offset. Every inferred value is
        # marked as such and remains editable in the source manifest.
        offsets: Counter[int] = Counter()
        for page_info in pages:
            if page_info.get("printed_page_label_source") != "visible_folio":
                continue
            label = str(page_info.get("printed_page_label") or "").strip()
            if label.isdigit():
                offsets[int(label) - int(page_info["pdf_page"])] += 1
        inferred_offset = None
        if offsets:
            candidate_offset, count = offsets.most_common(1)[0]
            if count >= 2:
                inferred_offset = int(candidate_offset)
        if inferred_offset is not None:
            page_lookup = {int(page_info["pdf_page"]): page_info for page_info in pages}
            for page_number, page_info in page_lookup.items():
                if page_info.get("printed_page_label_source") == "visible_folio":
                    continue
                inferred = page_number + inferred_offset
                if inferred < 1:
                    continue
                # Only infer within the span covered by visible Arabic folios; this
                # avoids turning Roman/front matter into fabricated Arabic pages.
                anchor_pages = [int(item["pdf_page"]) for item in pages if item.get("printed_page_label_source") == "visible_folio" and str(item.get("printed_page_label") or "").isdigit()]
                if not anchor_pages or page_number < min(anchor_pages):
                    continue
                page_info["printed_page_label"] = str(inferred)
                page_info["printed_page_label_source"] = "inferred_from_folios"
                for block in blocks:
                    if int(block.get("page") or 0) == page_number:
                        block["printed_page_label"] = str(inferred)
                        block["printed_page_label_source"] = "inferred_from_folios"

        # Repeated running headers/footers and bare page numbers are layout noise,
        # not record text. Mark them rather than deleting them so the source asset
        # remains fully auditable and excluded material can be inspected later.
        header_pages: dict[str, set[int]] = {}
        for block in blocks:
            if block.get("type") != "header_footer":
                continue
            normalized = _normalize_text(block.get("text") or "").casefold()
            if normalized:
                header_pages.setdefault(normalized, set()).add(int(block.get("page") or 0))
        repeat_threshold = max(3, int(max(1, doc.page_count) * 0.20))
        excluded_count = 0
        for block in blocks:
            if block.get("type") != "header_footer":
                continue
            normalized = _normalize_text(block.get("text") or "").casefold()
            is_page_number = bool(re.fullmatch(r"(?:[ivxlcdm]+|\d+)", normalized, re.I))
            if is_page_number or len(header_pages.get(normalized, set())) >= repeat_threshold:
                block["excluded_reason"] = "page_number" if is_page_number else "repeated_header_footer"
                excluded_count += 1
        try:
            outline = [(int(page), str(title)) for _level, title, page in doc.get_toc(simple=True)]
        except Exception:  # noqa: BLE001 - a broken outline only removes one clue
            outline = []
        return {
            "main_text_start_inference": infer_main_text_start(blocks, pages, outline),
            "outline": [{"page": page, "title": title} for page, title in outline[:400]],
            "filename": _safe_filename(filename),
            "page_count": doc.page_count,
            "metadata": metadata,
            "pages": pages,
            "blocks": blocks,
            "block_count": len(blocks),
            "included_block_count": len(blocks) - excluded_count,
            "excluded_block_count": excluded_count,
            "ocr_pages": ocr_pages,
            "warnings": warnings,
            "extractor": "pymupdf-layout-v2",
        }
    finally:
        doc.close()


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

    def save_asset(self, data: bytes, *, filename: str, ocr_mode: str = "auto", ocr_languages: str = "eng+fra+deu") -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        asset_id = f"pdf-{digest[:24]}"
        meta_path = self.asset_meta_path(asset_id)
        with self._lock:
            existing = _json_read(meta_path)
            if isinstance(existing, dict) and self.asset_pdf_path(asset_id).exists():
                return existing
            extracted = extract_source_document(data, filename=filename, ocr_mode=ocr_mode, ocr_languages=ocr_languages)
            self.asset_pdf_path(asset_id).write_bytes(data)
            with self.asset_blocks_path(asset_id).open("w", encoding="utf-8") as handle:
                for block in extracted.pop("blocks"):
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            meta = {
                "asset_id": asset_id,
                "sha256": digest,
                "filename": extracted["filename"],
                "created_at": iso_now(),
                **extracted,
            }
            _json_write(meta_path, meta)
            return meta

    def get_asset(self, asset_id: str) -> dict[str, Any]:
        meta = _json_read(self.asset_meta_path(asset_id))
        if not isinstance(meta, dict):
            raise KeyError(asset_id)
        return self._with_start_inference(meta)

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
                items.append(self._with_start_inference(item))
        return items

    def load_blocks(self, asset_id: str) -> list[dict[str, Any]]:
        self.get_asset(asset_id)
        blocks: list[dict[str, Any]] = []
        with self.asset_blocks_path(asset_id).open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    blocks.append(json.loads(line))
        return blocks

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
        return _json_read(self.build_checkpoint_path(build_id, name), default)

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
        return build

    def list_builds(self, *, offset: int = 0, limit: int = 50, asset_id: str | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for path in (self.root / "builds").glob("build-*/build.json"):
            build = _json_read(path)
            if isinstance(build, dict) and (not asset_id or build.get("asset_id") == asset_id):
                items.append(build)
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
                return [json.loads(line) for line in handle if line.strip()]

    def page_records(self, build_id: str, *, offset: int = 0, limit: int = 50, needs_review: bool | None = None, disposition: str | None = None, metadata_incomplete: bool | None = None, source_problem: bool | None = None, review_queue: str | None = None, query: str = "") -> dict[str, Any]:
        # Stream the JSONL rather than loading the entire generated corpus for a
        # browse request. Structural edits intentionally use load_records(); read
        # pagination remains bounded no matter how large the generated record set.
        self.get_build(build_id)
        path = self.build_records_path(build_id)
        if not path.exists():
            return {"items": [], "total": 0, "offset": offset, "limit": limit}
        q = query.casefold().strip()
        items: list[dict[str, Any]] = []
        total = 0
        topology_count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
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
                if review_queue and not PdfCorpusBuildManager._matches_review_queue(record, review_queue):
                    continue
                if q and q not in line.casefold():
                    continue
                if total >= offset and len(items) < limit:
                    record["topology_index"] = topology_index
                    PdfCorpusBuildManager._decorate_review_state(record)
                    PdfCorpusBuildManager._present_for_reviewer(record)
                    items.append(record)
                total += 1
        for record in items:
            record["topology_count"] = topology_count
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    def publication_path(self, publication_id: str) -> Path:
        return self.root / "publications" / f"{publication_id}.jsonl"


CORPUS_PROFILES: dict[str, dict[str, Any]] = {
    PROFILE_VERSION: {
        "id": PROFILE_VERSION,
        "name": "Derrida scholarly corpus v12",
        "version": 12,
        "description": "Testy Titmouse: reviewer-owned document structure outranks semantic inference, closed-vocabulary LLM output is normalized with raw provenance retained, and field-level LLM participation remains auditable.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": DISCOURSE_ROLES,
        "region_types": REGION_TYPES,
        "required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "publication_required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "publication_required_document_fields": ["title", "document_author"],
        "review_metadata_fields": list(REVIEW_METADATA_FIELDS),
        "min_boundary_confidence": 0.72,
        "candidate_llm_threshold": 0.30,
        "deterministic_split_threshold": 0.92,
        "review_risk_threshold": 0.90,
        "max_llm_boundary_calls_per_100_atoms": 18,
        "boundary_batch_size": 6,
        "min_metadata_confidence": 0.65,
        "soft_min_chars": 180,
        "preferred_record_chars": 1750,
        "record_length_tolerance": 200,
        "long_record_chars": 3500,
        "absolute_record_chars": 6000,
        "soft_max_chars": 3500,
        "topology_review_chars": 6000,
    }
}



def _serialize_record_mutation(method):
    """Serialize manager-level read/modify/write record transactions.

    Progressive enrichment and human review intentionally overlap. Any command
    that reads the whole JSONL, mutates it, then rewrites it must hold the same
    manager lock as metadata checkpoint persistence or a stale reviewer snapshot
    can overwrite a newer metadata checkpoint.
    """
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


class PdfCorpusBuildManager:
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
        self._loaded_models_cache: tuple[float, str, set[str]] = (0.0, "", set())
        self._provider_epoch: dict[str, int] = {}  # bumped whenever a build's provider is switched, so a running pass can notice
        self._mark_interrupted()

    def reset_in_memory_state(self) -> None:
        """Drop live cancel/runtime maps after the corpus tree has been deleted."""
        with self._lock:
            self._cancel.clear()
            self._runtime_requests.clear()

    def _mark_interrupted(self) -> None:
        listing = self.repo.list_builds(offset=0, limit=10000)
        for build in listing["items"]:
            if build.get("status") in {"queued", "running"}:
                build["status"] = "interrupted"
                build["stage"] = "interrupted"
                build["resumable"] = True
                build["error"] = "Build execution was interrupted by an API restart. Completed checkpoints were preserved; resume to continue."
                build["finished_at"] = iso_now()
                self.repo.save_build(build)

    @staticmethod
    def _generation_options(request: dict[str, Any]) -> OllamaTouchupOptions:
        generation = request.get("generation")
        if isinstance(generation, OllamaTouchupOptions):
            return generation
        if isinstance(generation, dict):
            return OllamaTouchupOptions.model_validate(generation)
        return OllamaTouchupOptions()

    @classmethod
    def _context_window(cls, request: dict[str, Any]) -> int | None:
        try:
            value = cls._generation_options(request).num_ctx
            return int(value) if value else None
        except (TypeError, ValueError, ValidationError):
            return None

    @classmethod
    def _validate_execution_budget(cls, request: dict[str, Any]) -> None:
        """Reject an explicitly impossible segmentation context before work starts.

        Context size is a model execution constraint, never a record-boundary rule.
        Unknown remote-provider context limits are allowed; explicit local limits
        must be large enough for the configured source window plus structured
        output and conservative schema/system overhead.
        """
        context = cls._context_window(request)
        if not context:
            return
        limits = cls._stage_limits(request)
        required = int(limits["segmentation_window_tokens"]) + int(limits["segmentation_num_predict"]) + 1536
        if context < required:
            raise ValueError(
                f"Corpus build context is too small for the configured segmentation turn: "
                f"num_ctx={context}, approximate minimum={required}. Increase the provider/build context "
                "or reduce the segmentation input/output budgets."
            )

    def _latest_runtime_request(self, build_id: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not build_id:
            return dict(fallback)
        with self._lock:
            current = self._runtime_requests.get(build_id)
            return dict(current) if isinstance(current, dict) and current else dict(fallback)

    def _interactive_llm_request(self, build_id: str, override: dict[str, Any] | None = None) -> dict[str, Any]:
        """Resolve a user-triggered LLM call without replacing it with build runtime state.

        Build workers intentionally follow the latest build-level provider switch. Interactive
        actions are different: the provider/model selected in the dialog is authoritative for
        that invocation. Build policy/budgets are inherited only for keys the action did not
        provide.
        """
        build = self.repo.get_build(build_id) if build_id else {}
        base = self._latest_runtime_request(build_id, dict(build.get("request") or {})) if build_id else {}
        chosen = {k: v for k, v in dict(override or {}).items() if v is not None}
        if not chosen:
            return dict(base)
        merged = dict(base)
        merged.update(chosen)
        return merged

    def switch_provider_profile(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Change the provider used by metadata tasks scheduled after this point.

        In-flight requests are intentionally not interrupted. The execution ledger
        records the actual provider/model for every family, so mixed-model builds
        remain auditable. Resolved credentials are kept only in memory.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable; create a new build instead.")
        profile_id = str(request.get("provider_profile_id") or "").strip()
        if not profile_id:
            raise ValueError("Choose an LLM provider profile.")
        with self._lock:
            prior = dict(self._runtime_requests.get(build_id) or {})
            # Preserve corpus-build policy/budgets while replacing only provider
            # configuration and optional escalation provider.
            merged = dict(prior) if prior else dict(build.get("request") or {})
            for key in ("provider", "model", "base_url", "api_key", "generation", "provider_profile_id", "review_provider_profile_id", "_review_provider"):
                if key in request:
                    merged[key] = request[key]
                elif key in {"review_provider_profile_id", "_review_provider"} and key in merged and key not in request:
                    merged.pop(key, None)
            self._runtime_requests[build_id] = merged
            self._provider_epoch[build_id] = self._provider_epoch.get(build_id, 0) + 1
            public = dict(build.get("request") or {})
            for key in ("provider", "model", "base_url", "generation", "provider_profile_id", "review_provider_profile_id"):
                if key in merged:
                    public[key] = merged[key]
                elif key in {"review_provider_profile_id"} and key in public:
                    public.pop(key, None)
            public.pop("api_key", None)
            public.pop("_review_provider", None)
            build["request"] = public
            build["provider"] = merged.get("provider") or build.get("provider")
            build["model"] = merged.get("model") or build.get("model")
            history = list(build.get("provider_profile_history") or [])
            history.append({
                "at": iso_now(), "provider_profile_id": profile_id,
                "provider": build.get("provider"), "model": build.get("model"),
                "metadata_completed": int(build.get("metadata_completed") or 0),
                "note": "Applies to newly scheduled metadata tasks; in-flight requests continue unchanged.",
            })
            build["provider_profile_history"] = history[-50:]
            self.repo.save_build(build)
        return build

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
        self._validate_execution_budget(request)
        try:
            schema = self._schemas.get(str(request.get("schema_id") or DEFAULT_SCHEMA_ID))
        except SchemaNotFound as exc:
            raise ValueError(f"Unknown metadata schema: {request.get('schema_id')}") from exc
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build = self.repo.create_build({
            "schema": schema.model_dump(mode="json"), "schema_id": schema.id, "schema_hash": schema.content_hash(), "schema_name": schema.name,
            "asset_id": asset["asset_id"],
            "source_sha256": asset["sha256"],
            "source_filename": asset["filename"],
            "source_page_count": asset["page_count"],
            "source_block_count": asset["block_count"],
            "schema_version": SCHEMA_VERSION,
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

    def resume(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            # Resume is intentionally idempotent while work is active. Stale
            # clients can safely repeat the action without creating a second
            # worker or surfacing an HTTP 422 for an operation already underway.
            return build
        if build.get("status") in {"published"}:
            raise ValueError("Published builds are immutable; create a new build instead.")
        self._validate_execution_budget(request)

        # A resume is also the supported way to recover a blocked build with a
        # better model, larger context, or different stage budgets. Persist the
        # new public execution contract so Operations and provenance describe the
        # run that actually completed, while keeping secrets out of build.json.
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build["provider"] = request.get("provider") or build.get("provider") or "ollama"
        build["model"] = request.get("model") or build.get("model")
        build["request"] = public_request
        build["status"] = "queued"
        build["stage"] = "resuming"
        build["error"] = None
        build["resumable"] = True
        build["finished_at"] = None
        build["cancel_requested"] = False
        build["metadata_settle_requested"] = False
        build["operation_hidden"] = False
        with self._lock:
            self._cancel.discard(build_id)

        # If the previous attempt reached a topology guard (for example, a long
        # book returned valid-but-empty boundary arrays), successful-window caches
        # are not useful: retry the segmentation topology with the new settings.
        unresolved = list(build.get("segmentation_unresolved_regions") or [])
        build["retrying_segmentation"] = bool(build.get("segmentation_blocked"))
        if any(str(item.get("kind") or "").startswith("topology_guard") for item in unresolved if isinstance(item, dict)):
            self.repo.save_checkpoint(build_id, "segmentation_state", {})
            self.repo.save_checkpoint(build_id, "reconciliation_state", {})
            self.repo.save_checkpoint(build_id, "boundaries_partial", [])
        self.repo.save_build(build)
        with self._lock:
            self._runtime_requests[build_id] = dict(request)
        self._executor.submit(self._run, build_id, request, True)
        return build

    def confirm_manifest(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Confirm the document-level contract and continue into segmentation.

        Book-level bibliographic/page structure is deliberately reviewed before it
        can influence hundreds of records. Confirmation records the exact manifest
        revision and then resumes from the persisted manifest checkpoint.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the document-analysis stage to finish before confirming its manifest.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        manifest = build.get("manifest")
        if not isinstance(manifest, dict) or not manifest:
            manifest = self.repo.load_checkpoint(build_id, "manifest")
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("This build does not yet have a document manifest to confirm.")
        build["manifest_confirmed_at"] = iso_now()
        build["manifest_confirmed_revision"] = int(build.get("manifest_revision") or 1)
        build["status"] = "awaiting_manifest_review"
        build["stage"] = "document_review"
        self.repo.save_build(build)
        return self.resume(build_id, request)

    def _request_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None:
        """Mark some decisions to be labelled again by a different reviewer, who will not see this answer."""
        reviewer = current_reviewer.get()
        if not reviewer or value in (None, "", []) or not experiment.needs_second_opinion(str(record.get("record_id") or ""), field, self._experiment_rate(build_id, "iaa_rate")):
            return
        # A later edit by the first reviewer replaces the answer, so an earlier second opinion no longer compares like with like.
        record.setdefault("second_opinion", {})[field] = {"first_reviewer": reviewer}

    def pending_second_opinions(self, build_id: str) -> list[dict[str, Any]]:
        """Fields the current reviewer is asked to label without seeing the first reviewer's answer."""
        me = current_reviewer.get()
        if not me:
            return []
        out = []
        for record in self.repo.load_records(build_id):
            for field, item in (record.get("second_opinion") or {}).items():
                if isinstance(item, dict) and not item.get("done") and item.get("first_reviewer") and item["first_reviewer"] != me:
                    out.append({"record_id": record.get("record_id"), "field": field, "text": record.get("text"), "page_start": record.get("page_start"), "page_end": record.get("page_end")})
        return out

    @_serialize_record_mutation
    def submit_second_opinion(self, build_id: str, record_id: str, field: str, value: Any) -> dict[str, Any]:
        me = current_reviewer.get()
        records = self.repo.load_records(build_id)
        record = next((r for r in records if r.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        item = (record.get("second_opinion") or {}).get(field)
        if not isinstance(item, dict) or item.get("done") or not me or item.get("first_reviewer") == me:
            raise ValueError("There is no second opinion for you to give on this field.")
        agreed = self._log_second_opinion(build_id, record, field, value, item)
        self.repo.save_records(build_id, records)
        return {"record_id": record_id, "field": field, "agreed": agreed}

    def _log_second_opinion(self, build_id: str, record: dict[str, Any], field: str, value: Any, item: dict[str, Any]) -> bool:
        first = record.get(field)
        agreed = _same_label(first, value)
        self._ledger.append(
            "second_label", model="", field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=first, new_value=value,
            agreed=agreed, first_reviewer=item["first_reviewer"], severity=None if agreed else error_severity(first, value),
        )
        item["done"] = True
        item["agreed"] = agreed
        return agreed

    @staticmethod
    def _second_opinion_owed(record: dict[str, Any], field: str) -> dict[str, Any] | None:
        """The pending second-opinion entry for this field if the current reviewer, not the first, is the one asked."""
        me = current_reviewer.get()
        item = (record.get("second_opinion") or {}).get(field)
        if me and isinstance(item, dict) and not item.get("done") and item.get("first_reviewer") and item["first_reviewer"] != me:
            return item
        return None

    @classmethod
    def _present_for_reviewer(cls, record: dict[str, Any]) -> None:
        """Hide, from a second reviewer, the answer they are about to independently give.

        Applied where records are served, never before saving: it must not reach storage.
        """
        for field in list((record.get("second_opinion") or {}).keys()):
            if cls._second_opinion_owed(record, field):
                record[field] = [] if isinstance(record.get(field), list) else None
                record.setdefault("metadata_field_status", {})[field] = {
                    "status": "unresolved", "method": "human", "blind": True, "reason_code": "second_opinion", "auto_populated": False, "reason": "",
                }
                for entry in record.get("metadata_decisions") or []:
                    if isinstance(entry, dict) and entry.get("field") == field:
                        entry["value"] = None  # the decision log holds the first answer too
                cls._scrub_sealed_field(record, field)
                # Everything else on the record that repeats the first reviewer's answer for this field.
                record["llm_rejections"] = [r for r in record.get("llm_rejections") or [] if not (isinstance(r, dict) and r.get("field") == field)]
                for key in ("recheck_results", "blind_reveals", "recheck_scheduled"):
                    if isinstance(record.get(key), dict):
                        record[key].pop(field, None)

    @staticmethod
    def _scrub_sealed_field(record: dict[str, Any], field: str) -> None:
        """Remove every copy of a sealed value, and the confidence and reasoning that would give it away, from the record."""
        evidence = record.get("metadata_evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get(field), dict):
            evidence[field] = {"block_ids": evidence[field].get("block_ids") or []}
        for result in (record.get("metadata_stage_results") or {}).values():
            if isinstance(result, dict):
                for section in ("metadata", "field_assessments", "field_evidence"):
                    if isinstance(result.get(section), dict):
                        result[section].pop(field, None)

    def _experiment_rate(self, build_id: str, key: str) -> float:
        build = self.repo.get_build(build_id)
        for source in (build.get("experiment"), build.get("request")):
            if isinstance(source, dict) and source.get(key):
                return float(source[key])
        return 0.0

    def _recheck_rate(self, build_id: str) -> float:
        return self._experiment_rate(build_id, "recheck_rate")

    def _schedule_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any) -> None:
        """Pick some of a reviewer's decisions to be asked again later, blind."""
        if value in (None, "", []) or not experiment.is_recheck(str(record.get("record_id") or ""), field, self._recheck_rate(build_id)):
            return
        build = self.repo.get_build(build_id)
        due = int(build.get("human_decision_count") or 0) + experiment.RECHECK_SPACING
        record.setdefault("recheck_scheduled", {})[field] = {"due": due, "reviewer": current_reviewer.get()}

    def _reopen_due_rechecks(self, build_id: str, records: list[dict[str, Any]], just_decided: dict[str, Any], profile: dict[str, Any]) -> None:
        """Count this decision, then reopen, blind, any earlier decision whose turn has come."""
        build = self.repo.get_build(build_id)
        count = int(build.get("human_decision_count") or 0) + 1
        build["human_decision_count"] = count
        self.repo.save_build(build)
        for record in records:
            scheduled = record.get("recheck_scheduled")
            if record is just_decided or not isinstance(scheduled, dict):
                continue
            for field, item in list(scheduled.items()):
                if not isinstance(item, dict) or int(item.get("due") or 0) > count:
                    continue
                self._ledger.append(RECHECK_SEAL, model="", field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=record.get(field), reviewer=str(item.get("reviewer") or ""))
                for entry in record.get("metadata_decisions") or []:
                    if isinstance(entry, dict) and entry.get("field") == field:
                        entry["value"] = None  # the earlier answer must not travel with the record
                        entry["sealed"] = True
                record[field] = [] if isinstance(record.get(field), list) else None
                record.setdefault("metadata_field_status", {})[field] = {
                    "status": "unresolved", "method": "human_recheck", "recheck": True, "reason_code": "recheck", "auto_populated": False,
                    "reason": "",
                }
                del scheduled[field]
                record["accepted"] = False
                record["needs_review"] = True
                self._sync_record_metadata_state(record, profile)

    def _score_recheck(self, build_id: str, record: dict[str, Any], field: str, value: Any, prior_status: dict[str, Any]) -> bool:
        """If this decision answers a re-check, log whether it matches the first answer and reveal that answer."""
        if not prior_status.get("recheck"):
            return False
        record_id = str(record.get("record_id") or "")
        first = self._ledger.sealed_value(build_id, record_id, field, RECHECK_SEAL)
        agreed = first == value
        first_reviewer = self._ledger.sealed_value(build_id, record_id, field, RECHECK_SEAL, column="reviewer")
        # Self-consistency only means something when the same person answers both times.
        self._ledger.append(RECHECK, model="", field=field, build_id=build_id, record_id=record_id, value=first, new_value=value, agreed=agreed, first_reviewer=first_reviewer or "", same_reviewer=(first_reviewer or "") == current_reviewer.get(), severity=None if agreed else error_severity(first, value))
        record.setdefault("recheck_results", {})[field] = {"first": first, "second": value, "agreed": agreed}
        return True

    _TRANSPORT_PAUSES = (3.0, 8.0, 15.0)
    _TRANSPORT_MARKERS = (
        "disconnected", "connection reset", "connection refused", "connection aborted", "broken pipe", "errno 97", "errno 104",
        "errno 111", "temporarily unavailable", "remote end closed", "eof occurred",
    )

    @classmethod
    def _is_transport_error(cls, exc: Exception) -> bool:
        """A dropped connection, not a bad answer or a timeout: worth trying again once the server is ready."""
        if isinstance(exc, (httpx.TimeoutException, InterruptedError)):
            return False
        text = f"{type(exc).__name__} {exc}".casefold()
        if "timeout" in text or "timed out" in text:
            return False
        return isinstance(exc, (httpx.TransportError, ConnectionError, OSError)) or any(marker in text for marker in cls._TRANSPORT_MARKERS)

    def _with_transport_retry(self, build_id: str, call: Callable[..., str], **kwargs: Any) -> str:
        """Run a model call, retrying with a growing pause when the connection itself fails.

        Restarting Ollama, or a model load being abandoned by whoever asked for it, drops every request waiting on
        it. Trying at once meets the same closed door, so wait a few seconds; a build should not fall back to a
        degraded result because a server was busy starting.
        """
        pauses = self._TRANSPORT_PAUSES
        for attempt in range(len(pauses) + 1):
            try:
                return call(**kwargs)
            except Exception as exc:  # noqa: BLE001 - classified below; anything else is re-raised untouched
                if attempt >= len(pauses) or not self._is_transport_error(exc):
                    raise
                if build_id:
                    self._increment_metric(build_id, "transport_retries")
                deadline = time.monotonic() + pauses[attempt]
                while time.monotonic() < deadline:
                    if build_id and self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled") from exc
                    time.sleep(0.25)
        raise RuntimeError("unreachable")  # pragma: no cover

    def _note_llm_call_start(self, build_id: str, task: str, provider: str, model: str, base_url: str) -> int:
        token = time.monotonic_ns()
        if build_id:
            with self._lock:
                self._llm_inflight.setdefault(build_id, {})[token] = {"since": time.monotonic(), "task": task, "provider": provider, "model": model, "base_url": base_url}
        return token

    def _note_llm_call_end(self, build_id: str, token: int) -> None:
        if build_id:
            with self._lock:
                calls = self._llm_inflight.get(build_id)
                if calls is not None:
                    calls.pop(token, None)
                    if not calls:
                        self._llm_inflight.pop(build_id, None)

    def _ollama_loaded_models(self, base_url: str) -> set[str] | None:
        """Names Ollama has in memory right now (its /api/ps), cached for a few seconds. None if it cannot be asked."""
        now = time.monotonic()
        cached_at, cached_url, cached = self._loaded_models_cache
        if cached_url == base_url and now - cached_at < 3.0:
            return cached
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=1.5) as response:  # noqa: S310 - the operator's configured Ollama URL
                names = {str(m.get("name") or m.get("model") or "") for m in json.loads(response.read()).get("models", []) if isinstance(m, dict)}
        except Exception:  # noqa: BLE001 - the status line is a courtesy; never let it break a build read
            return None
        self._loaded_models_cache = (now, base_url, names)
        return names

    def llm_activity(self, build_id: str) -> dict[str, Any] | None:
        """What the build is waiting on, for the status line: the oldest model call in flight and whether the model is loaded."""
        with self._lock:
            calls = list(self._llm_inflight.get(build_id, {}).values())
        if not calls:
            return None
        oldest = min(calls, key=lambda call: call["since"])
        state = "working"
        if oldest["provider"] == "ollama":
            loaded = self._ollama_loaded_models(str(oldest["base_url"] or settings.ollama_base_url))
            if loaded is None:
                state = "unknown"
            elif not any(oldest["model"] == name or name.startswith(oldest["model"] + ":") for name in loaded):
                state = "loading_model"
        return {
            "state": state, "task": oldest["task"], "model": oldest["model"], "provider": oldest["provider"],
            "seconds": round(time.monotonic() - oldest["since"], 1), "calls_in_flight": len(calls),
        }

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
        result = self._chat_json(active, prompt, response_model=model_cls, max_tokens=int(self._stage_limits(active).get("indexing_num_predict", 1200)), schema_name=f"derridai_record_{group}", build_id="")
        return {**out, "ran": True, "answer": result, "seconds": round(time.monotonic() - started, 1)}

    def start_autonomous(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Run hands-free mode on an existing build, in the background."""
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before running hands-free mode.")
        if build.get("status") == "published":
            raise ValueError("Published builds are immutable.")
        self._update(build_id, status="running", stage="autonomous", error=None, autonomous_report=None, resumable=False)

        def work() -> None:
            try:
                self.run_autonomous(build_id, request)
            except InterruptedError as exc:
                self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True)
            except Exception as exc:  # noqa: BLE001 - reported on the build, like any other stage failure
                self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc), resumable=True)

        self._executor.submit(work)
        return self.repo.get_build(build_id)

    def run_autonomous(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Hands-free finish: more enrichment passes, then settle what is waiting by policy, accept, optionally publish.

        Blocks until done, so it runs on a worker thread. Every decision is the policy's and is recorded as such (see
        autonomous.py); what it could not settle is left for a person and listed in the report on the build.
        """
        policy = AutonomousPolicy.from_request({"autonomous": {**(request.get("autonomous") or {}), "enabled": True}})
        notes: list[str] = []
        passes_run = 0
        if policy.passes and request.get("model"):
            try:
                self.rerun_metadata_enrichment(build_id, {**request, "passes": policy.passes})
                passes_run = policy.passes
                while True:  # the passes run on another worker; wait for them, honouring cancellation
                    if self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled")
                    current = self.repo.get_build(build_id)
                    if not (current.get("status") in {"queued", "running"} and current.get("stage") == "metadata_enrichment_rerun"):
                        break
                    time.sleep(2.0)
            except ValueError as exc:
                notes.append(f"Extra enrichment passes were skipped: {exc}")
        report = self._autonomous_settle(build_id, policy)
        report.update({"passes_run": passes_run, "notes": notes, "policy": policy.public(), "ran_at": iso_now()})
        if policy.publish:
            try:
                if report["left_for_review"] == 0:
                    self.publish(build_id)
                    report["published"] = True
                else:
                    report["published"] = False
                    notes.append("Not published: some records still need a person.")
            except ValueError as exc:
                report["published"] = False
                notes.append(f"Not published: {exc}")
        self._update(build_id, autonomous_report=report)
        return report

    @_serialize_record_mutation
    def _autonomous_settle(self, build_id: str, policy: AutonomousPolicy) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        profile = self._profile_for(build_id)
        filled_total = accepted = 0
        exceptions: list[dict[str, Any]] = []
        for record in records:
            if str(record.get("review_disposition") or "") in {"accepted", "rejected"} or self._human_touched(record):
                continue  # a person already decided this record
            outcome = settle_record(record, policy)
            filled_total += len(outcome["filled"])
            self._sync_record_metadata_state(record, profile)
            ok, reasons = may_accept(record)
            if policy.accept_records and ok:
                record["review_disposition"] = "accepted"
                record["accepted"] = True
                record["rejected"] = False
                record["needs_review"] = False
                record["review_reason"] = ""
                record["accepted_by"] = "autonomous"
                record["autonomous_decision"] = {"at": iso_now(), "filled": [f["field"] for f in outcome["filled"]]}
                record["record_revision"] = int(record.get("record_revision") or 1) + 1
                accepted += 1
            else:
                exceptions.append({"record_id": record.get("record_id"), "reasons": (reasons or [item["reason"] for item in outcome["left"]] or ["left for review by policy"])[:6]})
        self._rewrite_and_validate(build_id, records)
        return {"records": len(records), "fields_filled": filled_total, "accepted": accepted, "left_for_review": len(exceptions), "exceptions": exceptions[:200]}

    @staticmethod
    def _human_touched(record: dict[str, Any]) -> bool:
        return bool(record.get("human_touched_fields"))

    def enrichment_ledger_csv(self) -> str:
        return self._ledger.to_csv()

    def _schema_of_build(self, build: dict[str, Any]) -> MetadataSchema:
        """The schema a build was started with. It is a copy stored on the build, so editing or deleting the saved one changes nothing."""
        build_id = str(build.get("build_id") or "")
        cached = self._schema_cache.get(build_id)
        if cached is not None:
            return cached
        raw = build.get("schema")
        schema = MetadataSchema.model_validate(raw) if isinstance(raw, dict) and raw else default_schema()
        if build_id:
            self._schema_cache[build_id] = schema
        return schema

    def _allowed_fields(self, build_id: str) -> set[str]:
        """Every field a model or a person may set on a record of this build: the fixed ones plus its schema's."""
        return self._allowed_for(self._schema_for(build_id))

    @staticmethod
    def _allowed_for(schema: MetadataSchema) -> set[str]:
        """The fixed fields, minus those the default schema defines, plus this schema's: a schema that leaves a field out cannot have it set."""
        return (ALLOWED_METADATA_FIELDS - {f.name for f in default_schema().fields}) | set(schema.field_names())

    def _editable_fields(self, build_id: str) -> set[str]:
        """Fields a person may edit: the fixed editable ones, minus the default schema's, plus this build's schema's."""
        return (HUMAN_EDITABLE_METADATA_FIELDS - {f.name for f in default_schema().fields}) | set(self._schema_for(build_id).field_names())

    def _edit_model(self, build_id: str) -> type[BaseModel]:
        return edit_model(self._schema_for(build_id), RecordMetadataModel)

    def _schema_for(self, build_id: str) -> MetadataSchema:
        if not build_id:
            return default_schema()
        return self._schema_of_build(self.repo.get_build(build_id))

    def _profile_of_build(self, build: dict[str, Any]) -> dict[str, Any]:
        """The build's profile, with the fields a person must review taken from its schema."""
        base = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
        schema = self._schema_of_build(build)
        return {**base, "review_metadata_fields": schema.review_fields(), "attribution_evidence_fields": sorted(schema.attribution_fields()), "schema_field_names": schema.field_names()}

    def _profile_for(self, build_id: str) -> dict[str, Any]:
        return self._profile_of_build(self.repo.get_build(build_id))

    def _note_suspension(self, model: str, field: str, suspended: bool, reviews: int, accepted: int, build_id: str, run_id: str) -> None:
        """Log the moment autofill is switched off or back on for a model and field, once, not on every value."""
        with self._lock:
            was = (model, field) in self._suspended
            if suspended == was:
                return
            (self._suspended.add if suspended else self._suspended.discard)((model, field))
        self._ledger.append(SUSPENDED if suspended else RESUMED, model=model, field=field, build_id=build_id, run_id=run_id, reviews=reviews, accepted=accepted)

    def enrichment_metrics(self, build_id: str = "", run_id: str = "", arm: str = "", group_by: str = "") -> dict[str, Any]:
        """The ten enrichment measures for the whole ledger, one build, or one run."""
        records = self.repo.load_records(build_id) if build_id else None
        return {
            **compute_enrichment_metrics(self._ledger.events(), records, build_id=build_id, run_id=run_id, arm=arm, group_by=group_by),
            "concurrency": {"limit": max(1, int(settings.enrichment_max_concurrent_runs)), "working": self.active_enrichment_runs()},
        }

    def active_enrichment_runs(self) -> int:
        listing = self.repo.list_builds(offset=0, limit=10000)
        return sum(1 for b in listing["items"] if b.get("status") in {"queued", "running"} and b.get("stage") == "metadata_enrichment_rerun")

    def active_count(self) -> int:
        listing = self.repo.list_builds(offset=0, limit=10000)
        return sum(1 for build in listing["items"] if build.get("status") in {"queued", "running"})

    @staticmethod
    def _operation_from_build(build: dict[str, Any]) -> dict[str, Any]:
        raw_status = str(build.get("status") or "queued")
        if raw_status in {"queued", "running"}:
            status = raw_status
        elif raw_status == "cancelled":
            status = "cancelled"
        elif raw_status in {"failed", "interrupted"}:
            status = "failed"
        elif raw_status in {"blocked", "awaiting_manifest_review"}:
            status = "blocked"
        else:
            status = "completed"
        source_total = max(1, int(build.get("source_block_count") or 1))
        progress = max(0.0, min(1.0, float(build.get("progress") or 0.0)))
        unresolved = list(build.get("segmentation_unresolved_regions") or [])
        metadata_total = int(build.get("metadata_tasks_total") or 0)
        metadata_completed = int(build.get("metadata_tasks_completed") or 0)
        metadata_failed = int(build.get("metadata_tasks_failed") or 0)
        metadata_skipped = int(build.get("metadata_tasks_skipped") or 0)
        metadata_running = int(build.get("metadata_tasks_running") or 0)
        metadata_queued = int(build.get("metadata_tasks_queued") or 0)
        if raw_status in {"queued", "running"} and str(build.get("stage") or "") == "enriching" and metadata_total:
            settled = metadata_completed + metadata_failed + metadata_skipped
            metadata_stage_detail = (
                f"Metadata: {settled}/{metadata_total} settled · "
                f"{metadata_running} active · {metadata_queued} queued · "
                f"{metadata_failed + metadata_skipped} review"
            )
        else:
            metadata_stage_detail = None
        if metadata_stage_detail:
            operation_stage_detail = metadata_stage_detail
        elif raw_status in {"queued", "running"} and build.get("retrying_segmentation"):
            operation_stage_detail = f"Retrying {len(unresolved)} unresolved segmentation region(s)"
        elif build.get("segmentation_blocked"):
            operation_stage_detail = f"{len(unresolved)} unresolved segmentation region(s)"
        else:
            operation_stage_detail = str(build.get("stage") or raw_status).replace("_", " ")
        return {
            "id": str(build.get("build_id") or ""),
            "type": "pdf_corpus",
            "kind": "pdf_corpus",
            "label": f"PDF corpus · {build.get('source_filename') or 'source'}",
            "status": status,
            "raw_status": raw_status,
            "stage": build.get("stage"),
            "stage_detail": operation_stage_detail,
            "provider": build.get("provider"),
            "model": build.get("model"),
            "provider_profile_id": (build.get("request") or {}).get("provider_profile_id"),
            "max_concurrent_requests": (build.get("request") or {}).get("max_concurrent_requests", 1),
            "request": build.get("request") or {},
            "source_filename": build.get("source_filename"),
            "build_id": build.get("build_id"),
            "record_count": int(build.get("record_count") or 0),
            "review_count": int(build.get("needs_review_count") or 0),
            "metadata_tasks_total": metadata_total,
            "metadata_tasks_completed": metadata_completed,
            "metadata_tasks_failed": metadata_failed,
            "metadata_tasks_skipped": metadata_skipped,
            "metadata_tasks_running": metadata_running,
            "metadata_tasks_queued": metadata_queued,
            "metadata_started_at": build.get("metadata_started_at"),
            "metadata_last_progress_at": build.get("metadata_last_progress_at"),
            "unresolved_regions": len(unresolved),
            "progress": progress,
            "total": source_total,
            "completed": min(source_total, int(round(source_total * progress))),
            # Localized segmentation uncertainty is review work, not a failed operation.
            "failed": 1 if raw_status == "failed" else 0,
            "review_required": len(unresolved),
            "created_at": build.get("created_at"),
            "started_at": build.get("started_at"),
            "finished_at": build.get("finished_at"),
            "cancel_requested": bool(build.get("cancel_requested")),
            "fatal_error": build.get("error"),
            "href": f"/pdf?mode=builder&build={build.get('build_id')}",
        }

    def list_operations(self, limit: int = 200) -> list[dict[str, Any]]:
        listing = self.repo.list_builds(offset=0, limit=max(1, min(1000, limit)))
        return [
            self._operation_from_build(build)
            for build in listing["items"]
            if not build.get("operation_hidden")
        ]

    def operation(self, build_id: str) -> dict[str, Any]:
        return self._operation_from_build(self.repo.get_build(build_id))

    def delete(self, build_id: str) -> None:
        """Dismiss a finished build from the global Operations feed.

        Corpus builds are scholarly artifacts, not disposable job-log rows. The
        generic Operations "Remove" action therefore hides the operation entry
        without deleting the build, its source bindings, or a publication.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Running corpus builds must be cancelled before they can be dismissed from Operations.")
        build["operation_hidden"] = True
        build["operation_hidden_at"] = iso_now()
        self.repo.save_build(build)

    def clear_finished(self) -> int:
        count = 0
        listing = self.repo.list_builds(offset=0, limit=10000)
        for build in listing["items"]:
            if build.get("status") in {"queued", "running"} or build.get("operation_hidden"):
                continue
            build["operation_hidden"] = True
            build["operation_hidden_at"] = iso_now()
            self.repo.save_build(build)
            count += 1
        return count

    def cancel(self, build_id: str) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        with self._lock:
            self._cancel.add(build_id)
        if build.get("status") in {"queued", "running"}:
            build["cancel_requested"] = True
            self.repo.save_build(build)
        return build

    @_serialize_record_mutation
    def settle_metadata_unresolved(self, build_id: str) -> dict[str, Any]:
        """Ask active enrichment workers to stop scheduling automatic families.

        The currently executing provider call is allowed to reach its bounded read
        deadline; subsequent families settle as explicit review exceptions. Source
        text, topology, and already completed metadata checkpoints are preserved.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") not in {"queued", "running"} or build.get("stage") != "enriching":
            raise ValueError("Metadata can only be settled while enrichment is running.")
        build["metadata_settle_requested"] = True
        build["metadata_settle_requested_at"] = iso_now()
        self.repo.save_build(build)
        return build

    def _cancelled(self, build_id: str) -> bool:
        with self._lock:
            return build_id in self._cancel

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
        if "llm" not in method and state != "llm_inferred":
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

    @staticmethod
    def _metadata_issue_type(status: dict[str, Any] | None, record: dict[str, Any]) -> str:
        info = status or {}
        explicit = str(info.get("reason_code") or "").strip()
        if explicit:
            return explicit
        state = str(info.get("status") or "unresolved")
        reason = str(info.get("reason") or "").casefold()
        stage_status = record.get("metadata_stage_status") if isinstance(record.get("metadata_stage_status"), dict) else {}
        if "source quality" in reason or "extraction" in reason:
            return "source_quality"
        if state == "invalid":
            return "invalid_value"
        if any(value == "needs_review" for value in stage_status.values()) and "model" in reason:
            return "llm_failed"
        if "evidence" in reason or "confidence" in reason:
            return "evidence_failed"
        if "ambiguous" in reason or "disagree" in reason:
            return "ambiguous"
        if not info:
            return "not_run"
        return "unresolved"

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

    @staticmethod
    def _llm_config(request: dict[str, Any]) -> tuple[str, str, str | None, str | None, OllamaTouchupOptions | None]:
        provider = str(request.get("provider") or "ollama")
        model = str(request.get("model") or (settings.openai_compat_model if provider == "openai" else settings.ollama_model))
        generation = request.get("generation")
        if isinstance(generation, dict):
            generation = OllamaTouchupOptions.model_validate(generation)
        return provider, model, request.get("base_url"), request.get("api_key"), generation

    @staticmethod
    def _parse_json_robust(raw: str) -> dict[str, Any]:
        """Parse model JSON conservatively, repairing only syntax-level defects.

        The repair path never fabricates semantic values.  It handles the common
        local-model failures seen in long corpus runs: Markdown fences, leading
        prose, trailing commas and a response truncated after a complete object.
        """
        value = str(raw or "").strip()
        if not value:
            raise ValueError("LLM returned an empty response.")
        try:
            return _extract_json(value)
        except Exception:  # noqa: S110 — strict first pass; recovery below raises if nothing parses.
            pass
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
        start = value.find("{")
        if start < 0:
            raise ValueError("LLM response did not contain a JSON object.")
        # Find the last balanced object rather than assuming the final character
        # is a brace; routed/local providers occasionally append diagnostics.
        depth = 0
        in_string = False
        escaped = False
        end = -1
        for idx, char in enumerate(value[start:], start=start):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        if end < 0:
            raise ValueError("LLM JSON object was truncated before its closing brace.")
        candidate = value[start:end + 1]
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            # Some otherwise capable local models occasionally emit a Python-like
            # object (single quotes / True / False / None) even while JSON mode is
            # requested. ``literal_eval`` is deliberately limited to literals and
            # therefore repairs syntax without executing code or inventing values.
            try:
                parsed = ast.literal_eval(candidate)
            except (ValueError, SyntaxError) as literal_exc:
                raise ValueError(f"LLM returned malformed JSON: {exc.msg} at character {exc.pos}.") from literal_exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON was not an object.")
        return parsed

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
            provider, model, base_url, api_key, generation = self._llm_config(active_request)
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
                            timeout_seconds=float(self._stage_timeouts(request).get(timeout_key, 240)),
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
                    value = self._parse_json_robust(raw)
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
        limits = self._stage_limits(request)
        context = self._context_window(request)
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
        return result

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

    @staticmethod
    def _stage_limits(request: dict[str, Any]) -> dict[str, int]:
        defaults = {
            "manifest_num_predict": 1800,
            "segmentation_num_predict": 1200,
            "reconciliation_num_predict": 1000,
            "discourse_num_predict": 1600,
            "quotation_num_predict": 1500,
            "indexing_num_predict": 1200,
            "segmentation_window_tokens": 5000,
        }
        supplied = request.get("stage_limits")
        if hasattr(supplied, "model_dump"):
            supplied = supplied.model_dump()
        if isinstance(supplied, dict):
            for key, default in list(defaults.items()):
                try:
                    value = int(supplied.get(key, default))
                except (TypeError, ValueError):
                    value = default
                if key == "segmentation_window_tokens":
                    defaults[key] = max(1024, min(24000, value))
                else:
                    defaults[key] = max(256, min(8192, value))
        return defaults

    @staticmethod
    def _stage_timeouts(request: dict[str, Any]) -> dict[str, int]:
        """Per-call read deadlines for long-running corpus LLM stages.

        These are deliberately much shorter than the provider-wide emergency
        network ceiling so one unhealthy generation cannot monopolize a corpus
        worker indefinitely. Values remain configurable per build.
        """
        defaults = {
            "manifest": 300, "segmentation": 300, "reconciliation": 240,
            "discourse": 240, "quotation": 240, "indexing": 180,
        }
        supplied = request.get("stage_timeouts")
        if isinstance(supplied, dict):
            for key, default in list(defaults.items()):
                try:
                    value = int(supplied.get(key, default))
                except (TypeError, ValueError):
                    value = default
                defaults[key] = max(30, min(1800, value))
        return defaults

    @staticmethod
    def _semantic_atoms(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Reconstruct stable semantic atoms from noisy PDF layout blocks.

        PyMuPDF blocks are provenance units, not reliable discourse units. Many
        PDFs emit one block per visual line. We conservatively join adjacent tiny
        body blocks on the same physical page while preserving the last original
        block ID as the transition anchor and retaining every source block ID.
        """
        atoms: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []

        def flush() -> None:
            nonlocal pending
            if not pending:
                return
            last = pending[-1]
            text_parts = [str(item.get("text") or "").strip() for item in pending if str(item.get("text") or "").strip()]
            atom = dict(last)
            atom["text"] = " ".join(text_parts)
            atom["source_block_ids"] = [str(item.get("block_id") or "") for item in pending]
            atom["atom_first_block_id"] = str(pending[0].get("block_id") or "")
            atom["atom_last_block_id"] = str(last.get("block_id") or "")
            # Keep the last real source block ID so a boundary remains directly
            # applicable to deterministic record construction.
            atom["block_id"] = str(last.get("block_id") or "")
            atoms.append(atom)
            pending = []

        for block in blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue
            block_type = str(block.get("type") or "body")
            if block_type not in {"body", "paragraph", "text"}:
                flush()
                atom = dict(block)
                atom["source_block_ids"] = [str(block.get("block_id") or "")]
                atom["atom_first_block_id"] = atom["atom_last_block_id"] = str(block.get("block_id") or "")
                atoms.append(atom)
                continue
            if not pending:
                pending = [block]
                continue
            prev = pending[-1]
            same_page = int(prev.get("page") or 0) == int(block.get("page") or 0)
            pending_chars = sum(len(str(item.get("text") or "")) for item in pending)
            prev_text = str(prev.get("text") or "").rstrip()
            # Join line-like fragments, but stop at likely paragraph endings,
            # headings, quotations, list starts, or a healthy paragraph size.
            likely_continuation = (
                same_page
                and pending_chars < 1400
                and (len(prev_text) < 180 or not re.search(r'[.!?][”"\']?$', prev_text))
                and not re.match(r'^\s*(?:[-•*]|\d+[.)])\s+', text)
                and not (len(text) < 90 and text.isupper())
            )
            if likely_continuation:
                pending.append(block)
            else:
                flush()
                pending = [block]
        flush()
        return atoms

    @staticmethod
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

    @staticmethod
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
        limits = self._stage_limits(request)
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
        limits = self._stage_limits(request)
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

    @staticmethod
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

    @staticmethod
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
                "protected": PdfCorpusBuildManager._is_protected_transition(left, right) or "repeated_running_heading" in signals,
            })
        return candidates

    @staticmethod
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

    def _boundary_cache_fingerprint(self, left: dict[str, Any], right: dict[str, Any], request: dict[str, Any]) -> str:
        generation = self._generation_options(request)
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
        limits=self._stage_limits(request)
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

    @staticmethod
    def _boundary_audit_candidates(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
        left_ids = [str(value) for value in (left.get("source_block_ids") or []) if value]
        right_ids = [str(value) for value in (right.get("source_block_ids") or []) if value]
        # Candidate seams stay close to the current boundary.  The LLM never
        # invents a free-text cut point; deterministic code validates one of
        # these exact source-block IDs before exposing a recommendation.
        candidates = left_ids[-3:] + right_ids[:2]
        return list(dict.fromkeys(candidates))

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
        candidates = self._boundary_audit_candidates(left, right)
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
        limits = self._stage_limits(request)
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

    @staticmethod
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
            self._apply_boundary_adjudication_to_records(left, right, decision, threshold=threshold)
        self.repo.save_checkpoint(build_id, "boundary_second_reader", {"decisions": decisions, "metrics": metrics, "completed_at": iso_now()})
        return metrics

    @staticmethod
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

    @staticmethod
    def _seam_quality(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, bool, list[str]]:
        """Score a local retrieval seam without pretending length is semantic evidence."""
        if PdfCorpusBuildManager._is_protected_transition(left, right):
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

    @classmethod
    def _best_record_sizing_boundary(
        cls,
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
            quality, protected, signals = cls._seam_quality(left, right)
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

    @classmethod
    def _normalize_topology(
        cls,
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
                choice,info=cls._best_record_sizing_boundary(span,policy)
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

    @staticmethod
    def _percentile(values: list[int], percentile: float) -> int:
        if not values: return 0
        ordered=sorted(values)
        position=(len(ordered)-1)*max(0.0,min(1.0,percentile))
        lo=int(position); hi=min(len(ordered)-1,lo+1)
        if lo==hi: return ordered[lo]
        fraction=position-lo
        return int(round(ordered[lo]*(1-fraction)+ordered[hi]*fraction))

    @classmethod
    def _topology_sanity(cls, records: list[dict[str, Any]], policy: dict[str, int], source_blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
            "median_record_chars":cls._percentile(sizes,0.5),
            "p10_record_chars":cls._percentile(sizes,0.1),
            "p90_record_chars":cls._percentile(sizes,0.9),
            "preferred_record_chars":policy["preferred_record_chars"],
            "record_length_tolerance":policy["record_length_tolerance"],
            "long_record_chars":policy["long_record_chars"],
            "absolute_record_chars":policy["absolute_record_chars"],
            "records_in_preferred_range":sum(1 for x in sizes if policy["preferred_record_chars"]-policy["record_length_tolerance"] <= x <= policy["preferred_record_chars"]+policy["record_length_tolerance"]),
            "records_over_preferred_range":sum(1 for x in sizes if x>policy["preferred_record_chars"]+policy["record_length_tolerance"]),
            "records_over_long_limit":sum(1 for x in sizes if x>policy["long_record_chars"]),
            "micro_record_count":sum(1 for x in sizes if 0<x<180),
        }

    @classmethod
    def _topology_quality_report(cls, records:list[dict[str,Any]], source_blocks:list[dict[str,Any]], policy:dict[str,int], validation:dict[str,Any]) -> dict[str,Any]:
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

    @staticmethod
    def _best_safety_boundary(span: list[dict[str, Any]], hard_max: int) -> tuple[dict[str, Any], bool]:
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
            protected=PdfCorpusBuildManager._is_protected_transition(left,right)
            score=structural-(distance*0.55)-(3.0 if protected else 0.0)
            scored.append((score,not protected,left))
        safe=[item for item in scored if item[1]]
        if safe:
            return max(safe,key=lambda x:x[0])[2],False
        # Extremely unusual: every seam is protected. Force the least-bad seam and
        # surface exactly this demonstrated provenance hazard for human review.
        return max(scored,key=lambda x:x[0])[2],True

    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        """Build topology with deterministic-first routing and bounded LLM work.

        Human review is no longer an output of ordinary model uncertainty. The
        builder owns the topology: protected/weak seams KEEP, obvious structural
        seams SPLIT, and only a budgeted ambiguous subset reaches the LLM. The
        binary classifier's omission/failure/low confidence also means KEEP.
        """
        profile=self._profile_for(build_id)
        threshold=float(profile.get("min_boundary_confidence") or 0.72)
        sizing_policy=self._record_sizing_policy(request,profile)
        _=sizing_policy["absolute_record_chars"]
        index_by_id={str(block.get("block_id") or ""):i for i,block in enumerate(blocks)}
        candidates=self._deterministic_boundary_candidates(blocks,profile)
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
            route=self._candidate_route(candidate,profile)
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
        accepted, normalization_reviews, normalization_metrics = self._normalize_topology(
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

    @staticmethod
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

    @staticmethod
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
            page_start, page_end = PdfCorpusBuildManager._scholarly_page_range(group)
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
                "source_asset_id": asset["asset_id"],
                "source_block_ids": [block["block_id"] for block in group],
                "source_spans": [{"block_id": block["block_id"], "page": block["page"], "printed_page_label": block.get("printed_page_label"), "bbox": block.get("bbox"), "extraction_method": block.get("extraction_method"), "confidence": block.get("confidence")} for block in group],
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

    @staticmethod
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

    @staticmethod
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
        self._apply_manifest_metadata(record, manifest)
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
        if self._metadata_source_quality_gate(record, required_metadata_fields, stage_callback):
            return record
        tasks, source_ids, obvious_apparatus = self._prepare_metadata_tasks(
            record, manifest, request, profile, editorial_context, editorial_examples,
            previous_text, next_text, stage_callback,
            pass_learning=editorial_memory.get("pass_learning") if isinstance(editorial_memory, dict) else None,
            schema=schema,
        )
        stage_results = self._execute_metadata_tasks(record, request, tasks, build_id, stage_callback)
        return self._reconcile_metadata_results(record, profile, source_ids, stage_results, obvious_apparatus, request=request, build_id=build_id, schema=schema)

    @staticmethod
    def _metadata_source_quality_gate(
        record: dict[str, Any], required_metadata_fields: list[str],
        stage_callback: Callable[[dict[str, Any], str, str, str | None], None] | None,
    ) -> bool:
        """Settle unsafe source records without asking a model to interpret corruption."""
        # Do not ask a model to interpret source text that deterministic extraction
        # quality checks have already identified as corrupted. Preserve any
        # deterministic classifications and route only the unresolved fields to
        # explicit human/source repair.
        blocking_source_issues = [
            item for item in (record.get("source_quality_issues") or [])
            if str(item.get("severity") or "blocking") == "blocking"
        ]
        if blocking_source_issues and record.get("text_review_status") != "human_corrected":
            field_status = record.setdefault("metadata_field_status", {})
            for field in required_metadata_fields:
                current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
                if current.get("status") in {"deterministic", "human_confirmed"}:
                    continue
                field_status[field] = {
                    "status": "unresolved", "method": "source_quality_gate",
                    "confidence": None, "reason_code": "source_quality",
                    "reason": "Automatic enrichment was skipped because this record touches a source page with blocking extraction-quality findings.",
                }
            incomplete_fields = [field for field in required_metadata_fields if str((field_status.get(field) or {}).get("status") or "") in {"unresolved", "invalid"} or record.get(field) in (None, "", [])]
            record["metadata_incomplete_fields"] = incomplete_fields
            record["metadata_complete"] = not incomplete_fields
            record["metadata_stage_status"] = {"discourse": "skipped", "quotation": "skipped", "indexing": "skipped", "source_quality": "needs_review"}
            record["metadata_execution_ledger"] = {
                family: {"state": "skipped", "finished_at": iso_now(), "error": "Source quality gate"}
                for family in ("discourse", "quotation", "indexing")
            }
            if stage_callback:
                for family in ("discourse", "quotation", "indexing"):
                    stage_callback(record, family, "skipped", "Source quality gate")
            record["metadata_needs_attention"] = True
            record["metadata_attention_reasons"] = ["Source extraction quality must be resolved before scholarly metadata enrichment."]
            inline, full = _citation_strings(record)
            record["inline_citation"] = inline; record["full_citation"] = full
            return True
        return False

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
        limits = self._stage_limits(request)
        neighbor_context = {
            "previous_record_tail": previous_text[-1800:] if previous_text else "",
            "next_record_head": next_text[:1800] if next_text else "",
        }
        source_ids = [str(value) for value in record.get("source_block_ids") or []]
        source_id_json = json.dumps(source_ids, ensure_ascii=False)
        # Semantic records should already be bounded. This is a context-safety
        # guard, not a segmentation rule: no source text is rewritten or split here.
        source_text = str(record.get("text") or "")
        context = self._context_window(request)
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
        for group in schema.groups:
            all_task_specs[group.key] = (
                group.key,
                build_group_prompt(schema, group.key, base_context=base_context, allowed_region_types=allowed_region_types, allowed_discourse_roles=allowed_discourse_roles),
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
                "timeout_seconds": self._stage_timeouts(active_request).get(task_name),
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
        allowed_fields = self._allowed_for(schema)
        attribution_fields = schema.attribution_fields()
        evidence_required_fields = schema.evidence_fields()
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
                "status": "llm_inferred", "method": "llm", "model": model, "confidence": filled_confidence,
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
        llm_checked_fields: set[str] = set()
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
                llm_checked_fields.add(key)
                value, raw_llm_value = _normalize_semantic_value(key, value)
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
                    existing_status["llm_checked"] = True
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
                assessment = field_assessments.get(key) if isinstance(field_assessments.get(key), dict) else {}
                result_evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
                key_evidence = result_evidence.get(key) if isinstance(result_evidence.get(key), dict) else {}
                proposal_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else (key_evidence.get("confidence") if isinstance(key_evidence.get("confidence"), (int, float)) else None)
                if value not in (None, "", []) and (proposal_confidence is None or float(proposal_confidence) <= minimum):
                    # Keep low/unknown-confidence output as an explicit suggestion, not
                    # as the record's current value. The UI may display the proposal,
                    # but automatic population starts strictly above the configured threshold.
                    field_status[key] = {
                        "status": "unresolved", "method": "llm", "confidence": proposal_confidence,
                        "auto_populated": False, "proposed_value": value,
                        "reason_code": "low_confidence" if proposal_confidence is not None else "confidence_missing",
                        "reason": str(assessment.get("reason") or "Model proposal requires reviewer confirmation before population."),
                    }
                    continue
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
            auto = autofill(field, record.get(field), confidence, evidence_info) 
            if auto:
                field_status[field] = auto
                continue
            field_status[field] = {
                "status": "unresolved" if needs_human else "llm_inferred",
                "method": "llm",
                "confidence": confidence,
                "auto_populated": bool(confidence is not None and confidence > minimum and record.get(field) not in (None, "", [])),
                "proposed_value": record.get(field),
                "reason_code": "ambiguous" if needs_human else "resolved",
                "reason": str(assessment.get("reason") or evidence_info.get("reason") or "Model proposal."),
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
            if field not in required_metadata_fields and value in (None, "", []) and not assessment:
                # Optional attribution fields can be genuinely absent. If the model
                # made no assessment and proposed no value, do not manufacture an
                # uncertainty item merely because the field exists in the schema.
                continue
            auto = autofill(field, value, confidence, evidence_info) 
            if auto:
                field_status[field] = auto
            elif field in required_metadata_fields and value in (None, "", []):
                field_status[field] = {"status": "unresolved", "method": "hybrid", "confidence": confidence, "auto_populated": False, "proposed_value": value, "reason_code": "ambiguous", "reason": reason}
            elif (confidence is None or confidence <= minimum) and value not in (None, "", []):
                # Model self-confidence is never publication authority. Any LLM
                # proposal below the profile threshold is routed to the human
                # exception queue even when the model forgot to set needs_review.
                field_status[field] = {"status": "unresolved", "method": "llm", "confidence": confidence, "auto_populated": False, "proposed_value": value, "reason_code": "low_confidence", "reason": reason or f"Model confidence is below {minimum:.2f}."}
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
                field_status[field] = {"status": "unresolved", "method": "llm", "confidence": confidence, "auto_populated": bool(confidence is not None and confidence > minimum and value not in (None, "", [])), "proposed_value": value, "reason_code": "ambiguous" if needs_human else "evidence_failed", "reason": reason}
            else:
                field_status[field] = {"status": "llm_inferred", "method": "llm", "confidence": confidence, "auto_populated": bool(confidence is not None and confidence > minimum and value not in (None, "", [])), "proposed_value": value, "reason_code": "resolved", "reason": reason}

        apply_metadata_constraints(record)
        for checked_field in llm_checked_fields:
            checked_status = field_status.get(checked_field)
            if isinstance(checked_status, dict):
                checked_status.setdefault("llm_checked", True)
                if checked_field in raw_llm_values:
                    checked_status.setdefault("raw_llm_value", raw_llm_values[checked_field])

        shown: dict[str, Any] = {}
        for field in sorted(llm_populated_fields):
            proposed_status = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            shown[field] = record.get(field)
            if conditions["blind"] and proposed_status.get("method") == "llm" and proposed_status.get("status") in {"llm_inferred", "unresolved"}:
                # Blind review: the model's value is sealed in the ledger and the reviewer sees an empty field.
                record[field] = [] if isinstance(shown[field], list) else None
                field_status[field] = proposed_status = {
                    "status": "unresolved", "method": "llm", "blind": True, "reason_code": "blind_review", "auto_populated": False,
                    "reason": "",
                }
                self._scrub_sealed_field(record, field)
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
        self._sync_record_metadata_state(record, profile)
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
                isinstance(status_map.get(field), dict) and str(status_map[field].get("status") or "") in {"human_confirmed", "human_override", "deterministic", "inherited", "llm_inferred"}
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

    @staticmethod
    def _record_extraction_quality_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect layout/glyph fragmentation that page-level corruption checks miss.

        PDF text layers sometimes emit one glyph per line/position. Those records may
        contain valid Unicode yet are still unusable as scholarly text. Route them to
        the Source problem queue instead of presenting them as ready for acceptance.
        """
        text = unicodedata.normalize("NFC", str(record.get("text") or ""))
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 8:
            return []
        micro = sum(1 for line in lines if len(line) <= 2)
        punctuation_only = sum(1 for line in lines if line and all((not ch.isalnum()) for ch in line))
        alpha_chars = [ch for ch in text if ch.isalpha()]
        separated_alpha = sum(1 for line in lines if len(line) == 1 and line.isalpha())
        micro_ratio = micro / max(1, len(lines))
        separated_ratio = separated_alpha / max(1, len(alpha_chars))
        if micro_ratio >= 0.45 and (separated_alpha >= 5 or punctuation_only >= 5 or separated_ratio >= 0.12):
            pages = [int(v) for v in (record.get("pdf_pages") or []) if isinstance(v, int)]
            return [{
                "code": "fragmented_glyph_layout",
                "pages": sorted(set(pages)),
                "micro_line_ratio": round(micro_ratio, 3),
                "message": "Extracted text appears fragmented into individual glyphs or punctuation lines.",
            }]
        return []

    @staticmethod
    def _source_quality_report(blocks: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect extraction problems before asking an LLM to interpret damaged text.

        This is intentionally conservative: sparse pages are warnings, while only
        strong corruption signals (replacement/control characters) block automatic
        scholarly enrichment for records touching the affected page.
        """
        by_page: dict[int, list[str]] = {}
        methods: dict[int, Counter[str]] = {}
        for block in blocks:
            try:
                page = int(block.get("page") or 0)
            except (TypeError, ValueError):
                continue
            if page < 1:
                continue
            text = unicodedata.normalize("NFC", str(block.get("text") or ""))
            by_page.setdefault(page, []).append(text)
            methods.setdefault(page, Counter())[str(block.get("extraction_method") or "unknown")] += 1
        issues: list[dict[str, Any]] = []
        blocking_pages: list[int] = []
        warning_pages: list[int] = []
        for page, parts in sorted(by_page.items()):
            text = "\n".join(parts)
            chars = len(text)
            replacement = text.count("\ufffd")
            controls = sum(1 for ch in text if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t")
            printable = sum(1 for ch in text if not ch.isspace())
            replacement_ratio = replacement / max(1, printable)
            severity = "ok"
            codes: list[str] = []
            if replacement >= 2 and replacement_ratio >= 0.005:
                severity = "blocking"; codes.append("replacement_characters")
            if controls:
                severity = "blocking"; codes.append("control_characters")
            if chars < 20:
                if severity != "blocking": severity = "warning"
                codes.append("very_low_text_density")
            if codes:
                issue = {
                    "page": page, "severity": severity, "codes": codes,
                    "characters": chars, "replacement_characters": replacement,
                    "control_characters": controls, "extraction_methods": dict(methods.get(page) or {}),
                }
                issues.append(issue)
                (blocking_pages if severity == "blocking" else warning_pages).append(page)
        return {
            "valid_for_enrichment": not blocking_pages,
            "page_count": len(by_page),
            "blocking_page_count": len(blocking_pages),
            "warning_page_count": len(warning_pages),
            "blocking_pages": blocking_pages,
            "warning_pages": warning_pages,
            "issues": issues,
        }

    @staticmethod
    def _trash_quality_report(records: list[dict[str, Any]]) -> dict[str, Any]:
        """Measure records that are very likely unusable before semantic enrichment.

        This is deliberately deterministic and conservative. Strong extraction
        findings already live in ``source_quality_issues``; this ratio adds
        record-level signals for sparse, replacement-heavy, or glyph-fragmented
        text so a build can warn before spending model calls.
        """
        trash: list[dict[str, Any]] = []
        for record in records:
            text = unicodedata.normalize("NFC", str(record.get("text") or "")).strip()
            compact = "".join(ch for ch in text if not ch.isspace())
            alpha = sum(1 for ch in compact if ch.isalpha())
            replacement = compact.count("\ufffd")
            controls = sum(1 for ch in compact if unicodedata.category(ch) == "Cc")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            micro = sum(1 for line in lines if len(line) <= 2)
            fragmented = bool(PdfCorpusBuildManager._record_extraction_quality_issues(record))
            reasons: list[str] = []
            if len(compact) < 24:
                reasons.append("very_low_text_density")
            if replacement >= 2 or controls:
                reasons.append("corrupt_characters")
            if fragmented:
                reasons.append("fragmented_glyph_layout")
            if compact and alpha / max(1, len(compact)) < 0.25:
                reasons.append("low_alphabetic_density")
            if lines and micro / max(1, len(lines)) >= 0.65:
                reasons.append("micro_line_fragmentation")
            if reasons:
                trash.append({
                    "record_id": str(record.get("record_id") or ""),
                    "pages": list(record.get("pdf_pages") or []),
                    "reasons": reasons,
                    "characters": len(compact),
                })
        total = len(records)
        ratio = len(trash) / max(1, total)
        return {
            "record_count": total,
            "trash_record_count": len(trash),
            "trash_ratio": round(ratio, 4),
            "threshold": 0.10,
            "exceeds_threshold": bool(total and ratio > 0.10),
            "deterministic": True,
            "records": trash[:500],
        }

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
            expected_start, expected_end = PdfCorpusBuildManager._scholarly_page_range(group)
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
                if str(info.get("status") or "") == "llm_inferred":
                    human_ownership_errors.append({"record_id": record_id, "reason": f"{field} is human-touched but still marked llm_inferred"})

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
            scope = self._prepare_build_scope(build_id, request, resume)
            if scope is None:
                return
            records = self._construct_build_topology(build_id, request, resume, scope)
            records = self._schedule_build_enrichment(build_id, request, scope.manifest, records)
            self._finalize_build_review(build_id, scope, records)
            if AutonomousPolicy.from_request(request).enabled:
                self.run_autonomous(build_id, request)
        except InterruptedError as exc:
            self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True, retrying_segmentation=False)
        except Exception as exc:
            # Checkpoints intentionally survive a failed stage. The user can repair
            # provider configuration and resume instead of restarting a long book.
            self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc), resumable=True, retrying_segmentation=False)
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
            raise ValueError("No source text blocks were extracted from the PDF. Check OCR support and extraction warnings.")

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
        source_blocks = self._manifest_main_text_blocks(
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
        source_quality = self._source_quality_report(source_blocks)
        self._update(build_id, source_quality=source_quality)
        semantic_blocks = self._semantic_atoms(source_blocks)
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
            records = self._construct_records(asset, source_blocks, boundaries)
            self._mark_segmentation_review(records, list(self.repo.get_build(build_id).get("segmentation_unresolved_regions") or []))
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
                self._apply_manifest_metadata(record, manifest)
                inline, full = _citation_strings(record)
                record["inline_citation"] = inline
                record["full_citation"] = full
            # Validate topology before spending time on metadata enrichment.
            # At this point all source-derived text and boundaries are deterministic;
            # any failure is therefore an implementation/topology problem, not an
            # invitation to burn more LLM calls and ask the user to clean it up.
            active_profile = self._profile_for(build_id)
            sizing_policy = self._record_sizing_policy(request, active_profile)
            topology_validation = self._topology_sanity(records, sizing_policy, source_blocks)
            topology_quality = self._topology_quality_report(records, source_blocks, sizing_policy, topology_validation)
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
        blocking_pages = set(int(value) for value in (source_quality.get("blocking_pages") or []))
        for record in records:
            record_pages = set(int(value) for value in (record.get("pdf_pages") or []) if isinstance(value, int))
            affected = sorted(record_pages & blocking_pages)
            issues = []
            if affected:
                page_findings = [item for item in (source_quality.get("issues") or []) if int(item.get("page") or 0) in affected]
                issues.append({
                    "code": "source_quality_blocking", "severity": "blocking", "pages": affected,
                    "message": "The PDF text layer contains replacement or control characters on one or more pages.",
                    "page_findings": page_findings,
                })
            glyph_issues = self._record_extraction_quality_issues(record)
            for item in glyph_issues:
                item.setdefault("severity", "blocking")
            issues.extend(glyph_issues)
            if issues:
                record["source_quality_issues"] = issues
                record["needs_review"] = True
                record["review_reason"] = "Source extraction issue: inspect the affected source, correct the reviewed record text when appropriate, or rebuild/re-extract the source before acceptance."
        self.repo.save_records(build_id, records)
        trash_quality = self._trash_quality_report(records)
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
        self._update(build_id, stage="enriching", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42), boundary_count=len(boundaries), record_count=len(records), source_problem_count=sum(1 for record in records if record.get("source_quality_issues")), trash_quality=trash_quality)

        return records

    @staticmethod
    def _metadata_family_states(rows: list[dict[str, Any]]) -> list[str]:
        metadata_families = ("discourse", "quotation", "indexing")
        states: list[str] = []
        for row in rows:
            row_status = row.get("metadata_stage_status") if isinstance(row.get("metadata_stage_status"), dict) else {}
            for family in metadata_families:
                fallback = "complete" if row.get("metadata_complete") else "queued"
                states.append(str(row_status.get(family) or fallback))
        return states

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
            live_records[live_index] = self._merge_enrichment_snapshot(live_records[live_index], copy, self._allowed_fields(build_id))
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

        initial_states = self._metadata_family_states(records)
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
                            live_records[live_index] = self._merge_enrichment_snapshot(live_records[live_index], records[index], self._allowed_fields(build_id))
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
        settled_states = self._metadata_family_states(settled_records)
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
            operation = self._initial_enrichment_operation(
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

    @staticmethod
    def _metadata_value_missing(field: str, value: Any) -> bool:
        # Booleans are three-state in review: True, False, None. False is a
        # deliberate human decision and must never be treated as missing.
        if field == "primary_text":
            return value is None
        return value is None or value == "" or value == []

    @classmethod
    def _sync_record_metadata_state(cls, record: dict[str, Any], profile: dict[str, Any]) -> None:
        statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
        required = list(profile.get("required_metadata_fields") or [])
        reviewable = list(profile.get("review_metadata_fields") or REVIEW_METADATA_FIELDS)
        incomplete: list[str] = []
        review_fields: list[str] = []
        for field in required:
            info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
            state = str(info.get("status") or "")
            if state == "human_confirmed_absent":
                continue
            if cls._metadata_value_missing(field, record.get(field)) or state in {"unresolved", "invalid"}:
                incomplete.append(field)
        for field in reviewable:
            info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
            if str(info.get("status") or "") in {"unresolved", "invalid"}:
                review_fields.append(field)
        record["metadata_incomplete_fields"] = list(dict.fromkeys(incomplete))
        record["metadata_review_fields"] = list(dict.fromkeys(review_fields))
        record["metadata_complete"] = not record["metadata_incomplete_fields"] and not record["metadata_review_fields"]
        record["metadata_needs_attention"] = not record["metadata_complete"]
        if record["metadata_needs_attention"]:
            record["metadata_attention_reasons"] = ["Record metadata requires a human decision before acceptance."]
        else:
            record["metadata_attention_reasons"] = []

    @classmethod
    def _review_issue_codes(cls, record: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if record.get("source_quality_issues"):
            issues.append("source")
        if record.get("metadata_incomplete_fields") or record.get("metadata_review_fields"):
            issues.append("metadata")
        if record.get("needs_review") and str(record.get("review_reason") or "").strip():
            reason = str(record.get("review_reason") or "").casefold().strip()
            # Topology is a distinct exception class. Source/metadata review reasons
            # must not be flattened into topology merely because they are concrete.
            if reason not in {"pending human review.", "pending human review"} and any(token in reason for token in ("boundary", "topology", "merge", "split", "segmentation")):
                issues.append("topology")
        return list(dict.fromkeys(issues))

    @staticmethod
    def _metadata_enrichment_finished(record: dict[str, Any]) -> bool:
        state = str(record.get("metadata_enrichment_state") or "").strip().casefold()
        # Records produced before the progressive-review marker existed are
        # considered finished only when they already carry metadata stage output.
        if not state:
            return bool(record.get("metadata_stage_status") or record.get("metadata_complete"))
        return state in {"complete", "failed", "skipped"}

    @classmethod
    def _matches_review_queue(cls, record: dict[str, Any], queue: str | None) -> bool:
        if not queue or queue == "all":
            return True
        disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
        if queue in {"accepted", "rejected"}:
            return disposition == queue
        if disposition != "pending":
            return False
        codes = cls._review_issue_codes(record)
        if queue == "ready":
            return cls._metadata_enrichment_finished(record) and not codes
        if queue == "issues":
            return bool(codes)
        if queue in {"metadata", "topology", "source"}:
            return queue in codes
        return True

    @classmethod
    def _queue_counts(cls, records: list[dict[str, Any]]) -> dict[str, int]:
        result = {"all": len(records), "ready": 0, "preparing": 0, "issues": 0, "metadata": 0, "topology": 0, "source": 0, "accepted": 0, "rejected": 0, "pending": 0}
        for record in records:
            disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            if disposition == "accepted":
                result["accepted"] += 1
                continue
            if disposition == "rejected":
                result["rejected"] += 1
                continue
            result["pending"] += 1
            if not cls._metadata_enrichment_finished(record):
                result["preparing"] += 1
                continue
            codes = cls._review_issue_codes(record)
            if not codes:
                result["ready"] += 1
            else:
                result["issues"] += 1
                for code in ("metadata", "topology", "source"):
                    if code in codes:
                        result[code] += 1
        return result

    @classmethod
    def _decorate_review_state(cls, record: dict[str, Any]) -> dict[str, Any]:
        """Attach the one authoritative human-review state consumed by the UI.

        Queue membership is derived rather than independently persisted. This
        prevents a saved metadata decision from leaving behind a stale review
        flag that can resurrect the record in a later refresh.
        """
        disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
        issue_codes = cls._review_issue_codes(record)
        blocking_fields = list(dict.fromkeys([
            str(value) for value in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])
        ]))
        enrichment_finished = cls._metadata_enrichment_finished(record)
        if disposition in {"accepted", "rejected"}:
            state = disposition
        elif not enrichment_finished:
            state = "preparing"
        elif "source" in issue_codes:
            state = "source"
        elif "metadata" in issue_codes:
            state = "metadata"
        elif "topology" in issue_codes:
            state = "topology"
        else:
            state = "ready"
        record["review_state"] = state
        record["review_issue_codes"] = issue_codes
        record["acceptance_blocking_fields"] = blocking_fields
        record["metadata_enrichment_finished"] = enrichment_finished
        record["can_accept"] = bool(disposition == "pending" and enrichment_finished and not issue_codes)
        return record


    @classmethod
    def _enforce_review_invariants(cls, record: dict[str, Any]) -> None:
        """Keep persisted disposition consistent with authoritative blockers.

        Human approval is the last step for a record.  An accepted record may
        therefore never simultaneously carry source, metadata, or topology
        blockers.  If later deterministic validation discovers a blocker, reopen
        the record instead of letting contradictory state leak into queues or
        publication readiness.
        """
        disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
        if disposition != "accepted":
            return
        issues = cls._review_issue_codes(record)
        if not issues:
            return
        record["review_disposition"] = "pending"
        record["accepted"] = False
        record["rejected"] = False
        record["needs_review"] = True
        labels = ", ".join(issues)
        record["review_reason"] = f"Record reopened because validation found unresolved {labels} review work."
        audit = list(record.get("review_events") or [])
        audit.append({"at": iso_now(), "event": "acceptance_reopened", "issues": issues})
        record["review_events"] = audit[-100:]

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
        blocks = self._manifest_main_text_blocks(
            blocks, build.get("manifest") or {}, bounds_confirmed=bool(build.get("manifest_confirmed_at"))
        )
        build["source_quality"] = self._source_quality_report(blocks)
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
            if not (automation_running and not self._metadata_enrichment_finished(record)):
                self._sync_record_metadata_state(record, profile)
                self._enforce_review_invariants(record)
            self._decorate_review_state(record)
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
            if automation_running and not self._metadata_enrichment_finished(record):
                continue
            incomplete = list(dict.fromkeys([str(value) for value in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])]))
            statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            record_issues: list[dict[str, Any]] = []
            for field in incomplete:
                by_field[field] += 1
                status_info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
                if status_info.get("status") == "invalid":
                    invalid_by_field[field] += 1
                issue_type = self._metadata_issue_type(status_info, record)
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
                elif state == "llm_inferred": contribution["llm_fields_usable"] += 1
                elif state in {"unresolved", "invalid"} and str(info.get("method") or "").startswith("llm"):
                    contribution["llm_fields_review"] += 1
                elif state in {"human_confirmed", "human_override"}: contribution["human_fields"] += 1
            ledger = record.get("metadata_execution_ledger") if isinstance(record.get("metadata_execution_ledger"), dict) else {}
            for family in ("discourse", "quotation", "indexing"):
                entry = ledger.get(family) if isinstance(ledger.get(family), dict) else {}
                state = str(entry.get("state") or "")
                if state in {"complete", "failed"}: llm_family_calls += 1
                try: llm_elapsed_ms += int(entry.get("elapsed_ms") or 0)
                except (TypeError, ValueError): pass
                contribution[f"tasks_{state or 'unknown'}"] += 1
        useful = int(contribution.get("llm_fields_usable") or 0)
        build["llm_contribution"] = {
            **dict(contribution),
            "family_calls": llm_family_calls,
            "elapsed_ms": llm_elapsed_ms,
            "useful_fields_per_minute": round(useful / max(1 / 60, llm_elapsed_ms / 60000), 2) if llm_elapsed_ms else 0.0,
            "enrichment_mode": str((build.get("request") or {}).get("enrichment_mode") or "fast"),
            "semantic_indexing": bool((build.get("request") or {}).get("semantic_indexing")),
        }
        build["review_queue_counts"] = self._queue_counts(records)
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
                self._apply_manifest_metadata(record, manifest)
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

    @staticmethod
    def _mark_human_touch(record: dict[str, Any], fields: list[str] | set[str] | tuple[str, ...]) -> None:
        touched = [str(value) for value in (record.get("human_touched_fields") or []) if str(value)]
        for field in fields:
            field_name = str(field)
            if field_name and field_name not in touched:
                touched.append(field_name)
        record["human_touched_fields"] = touched
        record["human_touched_at"] = iso_now()
        record["human_touched_revision"] = int(record.get("record_revision") or 1) + 1
        activity = dict(record.get("activity") or {})
        activity["human_review_count"] = int(activity.get("human_review_count") or 0) + 1
        activity["last_human_reviewed_at"] = record["human_touched_at"]
        record["activity"] = activity

    @staticmethod
    def _editorial_tokens(value: str) -> set[str]:
        stop = {"the", "and", "for", "that", "this", "with", "from", "into", "dans", "les", "des", "une", "pour", "que", "qui", "sur", "est", "pas", "aux"}
        return {
            token for token in re.findall(r"[\wÀ-ÖØ-öø-ÿ]{3,}", str(value or "").casefold(), flags=re.UNICODE)
            if token not in stop
        }

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
                if self._second_opinion_owed(row, field):
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
        current_tokens = self._editorial_tokens(current_text)
        by_field: dict[str, list[dict[str, Any]]] = {}
        for row, field, value in eligible:
            row_tokens = self._editorial_tokens(str(row.get("text") or ""))
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

    @classmethod
    def _merge_enrichment_snapshot(cls, live: dict[str, Any], worker: dict[str, Any], allowed_fields: set[str] | None = None) -> dict[str, Any]:
        """Merge automatic enrichment into current human state without overwriting it."""
        merged = json.loads(json.dumps(live))
        live_status = live.get("metadata_field_status") if isinstance(live.get("metadata_field_status"), dict) else {}
        worker_status = worker.get("metadata_field_status") if isinstance(worker.get("metadata_field_status"), dict) else {}
        touched_markers = set(str(v) for v in (live.get("human_touched_fields") or []))
        text_was_touched = "__text__" in touched_markers
        record_frozen_by_review = "__review__" in touched_markers
        automatic_merge_blocked = text_was_touched or record_frozen_by_review
        for field in (allowed_fields if allowed_fields is not None else ALLOWED_METADATA_FIELDS):
            if field in MANIFEST_INHERITED_FIELDS:
                continue
            info = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
            if str(info.get("status") or "") in {"human_confirmed", "human_override"}:
                continue
            if not automatic_merge_blocked and field in worker:
                merged[field] = worker[field]
            if not automatic_merge_blocked and field in worker_status:
                merged.setdefault("metadata_field_status", {})[field] = worker_status[field]
        if not automatic_merge_blocked:
            worker_evidence = worker.get("metadata_evidence") if isinstance(worker.get("metadata_evidence"), dict) else {}
            live_evidence = merged.setdefault("metadata_evidence", {})
            for field, info in worker_evidence.items():
                status = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
                if str(status.get("status") or "") not in {"human_confirmed", "human_override"}:
                    live_evidence[field] = info
        for key in (
            "metadata_stage_status", "metadata_execution_ledger", "metadata_incomplete_fields",
            "metadata_review_fields", "metadata_needs_attention", "metadata_attention_reasons",
            "metadata_complete", "metadata_enrichment_state", "metadata_enrichment_finished",
            "semantic_classification_confidence", "attribution_confidence", "editorial_memory_used",
        ):
            if key in worker:
                merged[key] = worker[key]
        if automatic_merge_blocked:
            status = merged.setdefault("metadata_stage_status", {})
            ledger = merged.setdefault("metadata_execution_ledger", {})
            reason = "Human edited reviewed text before automatic enrichment settled." if text_was_touched else "Human completed record review before automatic enrichment settled."
            for family in ("discourse", "quotation", "indexing"):
                status[family] = "skipped"
                ledger[family] = {"state": "skipped", "finished_at": iso_now(), "error": reason}
        return merged

    def _assert_human_review_available(self, build_id: str, record: dict[str, Any] | None = None, *, structural: bool = False) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if str(build.get("status") or "") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            # Once segmentation has persisted the authoritative record topology,
            # non-structural review operations are available immediately. Bulk
            # review actions do not target one record object, so record=None must
            # not accidentally turn them into structural operations.
            if stage in {"enriching", "metadata_retry", "metadata_enrichment_rerun", "review"} and not structural:
                return build
            raise ValueError("Records are not editable until segmentation is complete. Structural merge/split operations wait until background enrichment stops.")
        return build

    def _assert_record_revision(self, record: dict[str, Any], expected_revision: int | None) -> int:
        current_revision = int(record.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before continuing.")
        return current_revision

    def _push_review_history(self, build_id: str, records: list[dict[str, Any]], *, action: str, selected_record_id: str) -> None:
        """Persist a reversible human-edit snapshot.

        Review history is intentionally separate from the append-only scholarly
        audit fields carried on each record.  The stack stores authoritative
        record-set snapshots so multi-record boundary operations can be undone
        atomically.  Any new human edit clears redo history.
        """
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        undo.append({
            "action": action, "selected_record_id": selected_record_id,
            "created_at": iso_now(), "records": json.loads(json.dumps(records)),
        })
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": []})

    # Backward-compatible internal alias for older call sites in this source tree.
    def _save_review_undo(self, build_id: str, records: list[dict[str, Any]], *, action: str, selected_record_id: str) -> None:
        self._push_review_history(build_id, records, action=action, selected_record_id=selected_record_id)

    @_serialize_record_mutation
    def set_disposition(self, build_id: str, record_id: str, disposition: str, reason: str = "", expected_revision: int | None = None) -> dict[str, Any]:
        if disposition not in {"pending", "accepted", "rejected"}:
            raise ValueError("Unsupported review disposition.")
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        self._assert_human_review_available(build_id, target)
        current_revision = self._assert_record_revision(target, expected_revision)
        self._push_review_history(build_id, records, action="disposition", selected_record_id=record_id)
        profile = self._profile_for(build_id)
        self._sync_record_metadata_state(target, profile)
        if disposition == "accepted" and target.get("source_quality_issues"):
            raise ValueError("Resolve the source extraction problem before accepting this record.")
        if disposition == "accepted" and (list(target.get("metadata_review_fields") or []) or list(target.get("metadata_incomplete_fields") or [])):
            raise ValueError("Resolve the queued record metadata before accepting this record.")
        if disposition == "accepted":
            status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
            for field in self._schema_for(build_id).review_fields():
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else None
                if info and info.get("status") == "llm_inferred":
                    if info.get("model"):
                        self._ledger.append(ACCEPTED, model=str(info["model"]), field=field, build_id=build_id, record_id=str(target.get("record_id") or ""), confidence=info.get("confidence"), autofilled=bool(info.get("autofilled")), value=target.get(field), new_value=target.get(field), **(info.get("conditions") or {}))
                    info["status"] = "human_confirmed"
                    info["method"] = "human_review_of_llm_proposal"
                    info["reason"] = (str(info.get("reason") or "") + " Confirmed when the reviewer accepted the record.").strip()
            target["metadata_reviewed_at"] = iso_now()
        target["review_disposition"] = disposition
        target["accepted"] = disposition == "accepted"
        target["rejected"] = disposition == "rejected"
        if disposition == "accepted":
            target["needs_review"] = False
            target["review_reason"] = ""
        elif disposition == "rejected":
            target["needs_review"] = False
            target["review_reason"] = str(reason or "Rejected during human review.")
        else:
            target["needs_review"] = True
            target["review_reason"] = str(reason or target.get("review_reason") or "Pending human review.")
        self._mark_human_touch(target, ["__review__"])
        target["record_revision"] = current_revision + 1
        self._rewrite_and_validate(build_id, records)
        return target

    @_serialize_record_mutation
    def review_decision(self, build_id: str, record_id: str, disposition: str, reason: str = "", expected_revision: int | None = None, review_queue: str | None = None) -> dict[str, Any]:
        """Apply one review decision and return the authoritative next step atomically.

        This is the UI-facing review command. It avoids the previous client-side
        accept -> refresh build -> refresh queue race that could look like a no-op.
        """
        if disposition not in {"accepted", "rejected"}:
            raise ValueError("Unsupported review decision.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_human_review_available(build_id, target)
        profile = self._profile_for(build_id)
        self._sync_record_metadata_state(target, profile)
        blocking_fields = list(dict.fromkeys([str(v) for v in (target.get("metadata_review_fields") or []) + (target.get("metadata_incomplete_fields") or [])]))
        if disposition == "accepted" and target.get("source_quality_issues"):
            return {
                "applied": False, "blocked": True, "blocker": "source_problem",
                "blocking_fields": [], "record": target, "next_record": None,
                "build": self._refresh_workflow_fields(self.repo.get_build(build_id)),
                "queue_counts": self._queue_counts(records),
            }
        if disposition == "accepted" and blocking_fields:
            return {
                "applied": False, "blocked": True, "blocker": "metadata_decision_required",
                "blocking_fields": blocking_fields, "record": target, "next_record": None,
                "build": self._refresh_workflow_fields(self.repo.get_build(build_id)),
                "queue_counts": self._queue_counts(records),
            }
        self._assert_record_revision(target, expected_revision)
        current_revision = int(target.get("record_revision") or 1)
        self._push_review_history(build_id, records, action=f"review_{disposition}", selected_record_id=record_id)
        if disposition == "accepted":
            status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
            for field in self._schema_for(build_id).review_fields():
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else None
                if info and info.get("status") == "llm_inferred":
                    info["status"] = "human_confirmed"
                    info["method"] = "human_review_of_llm_proposal"
            target["metadata_reviewed_at"] = iso_now()
        target["review_disposition"] = disposition
        target["accepted"] = disposition == "accepted"
        target["rejected"] = disposition == "rejected"
        target["needs_review"] = False
        target["review_reason"] = "" if disposition == "accepted" else str(reason or "Rejected during human review.")
        self._mark_human_touch(target, ["__review__"])
        target["record_revision"] = current_revision + 1
        build = self._rewrite_and_validate(build_id, records)
        # Prefer the next *pending* record in the active review queue.  `all` is
        # intentionally special: `_matches_review_queue(..., "all")` includes
        # already-reviewed records, which previously let Accept & next advance to
        # an accepted/rejected row and made the primary action look like a no-op.
        ordered = records[index + 1:] + records[:index]
        def pending(candidate: dict[str, Any]) -> bool:
            return str(candidate.get("review_disposition") or "pending") == "pending"
        if review_queue and review_queue != "all":
            next_record = next((candidate for candidate in ordered if pending(candidate) and self._matches_review_queue(candidate, review_queue)), None)
        else:
            next_record = next((candidate for candidate in ordered if pending(candidate)), None)
        if next_record is None:
            next_record = next((candidate for candidate in ordered if pending(candidate)), None)
        return {"applied": True, "blocked": False, "record": target, "next_record": next_record, "build": build, "queue_counts": self._queue_counts(records)}

    def accept_record(self, build_id: str, record_id: str, accepted: bool = True, expected_revision: int | None = None) -> dict[str, Any]:
        return self.set_disposition(build_id, record_id, "accepted" if accepted else "pending", expected_revision=expected_revision)

    @_serialize_record_mutation
    def bulk_disposition(self, build_id: str, disposition: str, reason: str = "", needs_review: bool | None = None, query: str = "", filter_disposition: str | None = None, review_queue: str | None = None, record_ids: list[str] | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=False)
        if disposition not in {"pending", "accepted", "rejected"}:
            raise ValueError("Unsupported review disposition.")
        records = self.repo.load_records(build_id)
        self._push_review_history(build_id, records, action=f"bulk_{disposition}", selected_record_id="")
        q = str(query or "").casefold().strip()
        selected_ids = {str(value) for value in (record_ids or []) if str(value).strip()}
        changed = 0
        blocked_metadata = 0
        blocked_record_ids: list[str] = []
        for record in records:
            if selected_ids and str(record.get("record_id") or "") not in selected_ids:
                continue
            if needs_review is not None and bool(record.get("needs_review")) is not needs_review:
                continue
            current_disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            profile = self._profile_for(build_id)
            self._sync_record_metadata_state(record, profile)
            if filter_disposition is not None and current_disposition != filter_disposition:
                continue
            if review_queue and not self._matches_review_queue(record, review_queue):
                continue
            if q and q not in json.dumps(record, ensure_ascii=False).casefold():
                continue
            if disposition == "accepted" and (record.get("source_quality_issues") or list(record.get("metadata_review_fields") or []) or list(record.get("metadata_incomplete_fields") or [])):
                blocked_metadata += 1
                if len(blocked_record_ids) < 100:
                    blocked_record_ids.append(str(record.get("record_id") or ""))
                continue
            current_revision = int(record.get("record_revision") or 1)
            if disposition == "accepted":
                status_map = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
                for field in self._schema_for(build_id).review_fields():
                    info = status_map.get(field) if isinstance(status_map.get(field), dict) else None
                    if info and info.get("status") == "llm_inferred":
                        info["status"] = "human_confirmed"
                        info["method"] = "human_review_of_llm_proposal"
                record["metadata_reviewed_at"] = iso_now()
            record["review_disposition"] = disposition
            record["accepted"] = disposition == "accepted"
            record["rejected"] = disposition == "rejected"
            # Bulk review is still a human decision. Freeze later automatic
            # enrichment from overwriting the reviewed record exactly as the
            # single-record review path does.
            self._mark_human_touch(record, ["__review__"])
            if disposition == "accepted":
                record["needs_review"] = False; record["review_reason"] = ""
            elif disposition == "rejected":
                record["needs_review"] = False; record["review_reason"] = str(reason or "Rejected during human review.")
            else:
                record["needs_review"] = True; record["review_reason"] = str(reason or record.get("review_reason") or "Pending human review.")
            record["record_revision"] = current_revision + 1
            changed += 1
        self._rewrite_and_validate(build_id, records)
        return {"changed": changed, "disposition": disposition, "blocked_metadata": blocked_metadata, "blocked_record_ids": blocked_record_ids, "queue_counts": self._queue_counts(records)}

    @_serialize_record_mutation
    def undo_last_review_edit(self, build_id: str) -> dict[str, Any]:
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        redo = list(checkpoint.get("redo") or []) if isinstance(checkpoint, dict) else []
        if not undo:
            raise KeyError(build_id)
        entry = undo.pop()
        current = self.repo.load_records(build_id)
        redo.append({
            "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"),
            "created_at": iso_now(), "records": json.loads(json.dumps(current)),
        })
        records = entry["records"]
        self._rewrite_and_validate(build_id, records)
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo, "redo": redo[-40:]})
        return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": len(records), "can_undo": bool(undo), "can_redo": True}

    @_serialize_record_mutation
    def redo_last_review_edit(self, build_id: str) -> dict[str, Any]:
        checkpoint = self.repo.load_checkpoint(build_id, "review_history", {})
        undo = list(checkpoint.get("undo") or []) if isinstance(checkpoint, dict) else []
        redo = list(checkpoint.get("redo") or []) if isinstance(checkpoint, dict) else []
        if not redo:
            raise KeyError(build_id)
        entry = redo.pop()
        current = self.repo.load_records(build_id)
        undo.append({
            "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"),
            "created_at": iso_now(), "records": json.loads(json.dumps(current)),
        })
        records = entry["records"]
        self._rewrite_and_validate(build_id, records)
        self.repo.save_checkpoint(build_id, "review_history", {"undo": undo[-40:], "redo": redo})
        return {"restored": True, "action": entry.get("action"), "selected_record_id": entry.get("selected_record_id"), "record_count": len(records), "can_undo": True, "can_redo": bool(redo)}

    @_serialize_record_mutation
    def patch_record_text(
        self, build_id: str, record_id: str, text: str, expected_revision: int | None = None,
        resolve_source_issues: bool = False,
    ) -> dict[str, Any]:
        """Save reviewer-corrected corpus text without destroying extraction provenance."""
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        self._assert_human_review_available(build_id, target)
        current_revision = self._assert_record_revision(target, expected_revision)
        self._push_review_history(build_id, records, action="text_edit", selected_record_id=record_id)
        cleaned = str(text or "").strip()
        if not cleaned:
            raise ValueError("Reviewed record text cannot be empty.")
        if "source_extracted_text" not in target:
            target["source_extracted_text"] = str(target.get("text") or "")
        previous = str(target.get("text") or "")
        unchanged = cleaned == previous
        if unchanged and not resolve_source_issues:
            target["text_review_status"] = "human_reviewed"
            target["text_reviewed_at"] = iso_now()
            target["text_review_source"] = "human"
            self._mark_human_touch(target, ["__text_reviewed__"])
            review_events = list(target.get("review_events") or [])
            review_events.append({"at": iso_now(), "event": "text_reviewed", "changed": False})
            target["review_events"] = review_events[-100:]
            target["record_revision"] = current_revision + 1
            self._rewrite_and_validate(build_id, records)
            return next((row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id), target)
        history = list(target.get("text_revision_history") or [])
        history.append({
            "at": iso_now(), "source": "human",
            "previous_sha256": hashlib.sha256(previous.encode("utf-8")).hexdigest(),
            "text_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            "previous_length": len(previous), "text_length": len(cleaned),
            "diff": "\n".join(difflib.unified_diff(
                previous.splitlines(), cleaned.splitlines(),
                fromfile="previous reviewed text", tofile="reviewed text", lineterm="",
            )),
            "resolved_source_issues": bool(resolve_source_issues),
        })
        target["text_revision_history"] = history[-20:]
        target["text"] = cleaned
        target["text_length"] = len(cleaned)
        target["text_review_status"] = "human_corrected"
        target["text_reviewed_at"] = iso_now()
        target["text_review_source"] = "human"
        self._mark_human_touch(target, ["__text__"])
        # Any text correction invalidates a prior record-level acceptance. The
        # reviewer may accept again after deciding whether selective metadata
        # reruns are warranted; automatic metadata is never silently treated as
        # newly human-approved merely because the text editor saved.
        target["review_disposition"] = "pending"
        target["accepted"] = False
        target["rejected"] = False
        target["needs_review"] = True
        target["review_reason"] = "Reviewed record text changed; verify the correction and rerun any affected metadata families before acceptance."
        review_events = list(target.get("review_events") or [])
        review_events.append({"at": iso_now(), "event": "text_corrected", "resolve_source_issues": bool(resolve_source_issues)})
        target["review_events"] = review_events[-100:]
        if resolve_source_issues:
            target["resolved_source_quality_issues"] = list(target.get("source_quality_issues") or [])
            target["source_quality_issues"] = []
            target["source_quality_resolved_at"] = iso_now()
        target["metadata_needs_attention"] = True
        reasons = list(target.get("metadata_attention_reasons") or [])
        reasons.append("Reviewed text changed; rerun only the metadata families that need reconsideration.")
        target["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
        target["record_revision"] = current_revision + 1
        self._rewrite_and_validate(build_id, records)
        persisted = next((row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id), target)
        self._decorate_review_state(persisted)
        return persisted

    @_serialize_record_mutation
    def patch_metadata(self, build_id: str, record_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        forbidden = sorted(set(changes) - self._editable_fields(build_id))
        if forbidden:
            raise ValueError(
                "Source-bound fields cannot be edited as record metadata. These system/source-bound fields are protected: "
                + ", ".join(forbidden)
            )
        # Validate the editable interpretive schema before modifying the persisted record.
        edit = self._edit_model(build_id)
        schema_input = {key: value for key, value in changes.items() if key in edit.model_fields}
        try:
            edit.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid interpretive metadata: {exc}") from exc

        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before saving metadata.")
        self._push_review_history(build_id, records, action="metadata_edit", selected_record_id=record_id)
        decision_log = list(target.get("metadata_decisions") or [])
        skipped: set[str] = set()
        for key, value in changes.items():
            status = target.setdefault("metadata_field_status", {})
            prior_status = dict(status.get(key) or {}) if isinstance(status.get(key), dict) else {}
            prior_value = target.get(key)
            owed = self._second_opinion_owed(target, key)
            if owed:
                # This is the independent second opinion, not an edit: it is compared with the first answer and the record is left alone.
                self._log_second_opinion(build_id, target, key, value, owed)
                skipped.add(key)
                continue
            answered_again = self._score_recheck(build_id, target, key, value, prior_status)
            if not answered_again:
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, target)
                self._schedule_recheck(build_id, target, key, value)
                self._request_second_opinion(build_id, target, key, value)
            target[key] = value
            if key in self._editable_fields(build_id):
                is_override = key in MANIFEST_INHERITED_FIELDS
                status[key] = {
                    "status": "human_override" if is_override else "human_confirmed",
                    "method": "human_record_override" if is_override else "human",
                    "confidence": 1.0,
                    "reason_code": "human_override" if is_override else "human_confirmed",
                    "reason": "Human record-level override of inherited document metadata." if is_override else "Confirmed during record review.",
                }
                decision_log.append({"field": key, "value": value, "at": iso_now(), "source": "human_override" if is_override else "human"})
        constraint_changes = apply_metadata_constraints(target)
        for item in constraint_changes:
            decision_log.append({"field": item["field"], "value": item["value"], "at": iso_now(), "source": "deterministic_constraint", "reason": item["reason"]})
        target["metadata_decisions"] = decision_log[-100:]
        target["metadata_reviewed_at"] = iso_now()
        self._mark_human_touch(target, [key for key in changes if key not in skipped])
        profile = self._profile_for(build_id)
        self._reopen_due_rechecks(build_id, records, target, profile)
        self._sync_record_metadata_state(target, profile)
        target["record_revision"] = current_revision + 1
        _ = self._rewrite_and_validate(build_id, records)
        # Return the record as persisted after authoritative state derivation.
        persisted = next((row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id), target)
        self._decorate_review_state(persisted)
        self._present_for_reviewer(persisted)
        return persisted

    @_serialize_record_mutation
    def bulk_patch_metadata(
        self, build_id: str, changes: dict[str, Any], *, record_ids: list[str] | None = None,
        apply_to_all: bool = False, review_queue: str | None = None, query: str = "",
    ) -> dict[str, Any]:
        if not changes:
            raise ValueError("Choose at least one metadata field to update.")
        forbidden = sorted(set(changes) - self._editable_fields(build_id))
        if forbidden:
            raise ValueError("Unsupported bulk metadata field(s): " + ", ".join(forbidden))
        edit = self._edit_model(build_id)
        schema_input = {key: value for key, value in changes.items() if key in edit.model_fields}
        try:
            edit.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid bulk metadata: {exc}") from exc
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        self._push_review_history(build_id, records, action="bulk_metadata_edit", selected_record_id=(str(record_ids[0]) if record_ids else ""))
        wanted = {str(value) for value in (record_ids or []) if str(value)}
        query_l = str(query or "").strip().casefold()
        changed_ids: list[str] = []
        profile = self._profile_of_build(build)
        for record in records:
            if wanted:
                selected = str(record.get("record_id") or "") in wanted
            elif apply_to_all:
                selected = True
            else:
                selected = self._matches_review_queue(record, review_queue) if review_queue else False
            if not selected:
                continue
            if query_l and query_l not in (str(record.get("record_id") or "") + " " + str(record.get("text") or "")).casefold():
                continue
            self._assert_human_review_available(build_id, record)
            decisions = list(record.get("metadata_decisions") or [])
            statuses = record.setdefault("metadata_field_status", {})
            for key, value in changes.items():
                prior_status = dict(statuses.get(key) or {}) if isinstance(statuses.get(key), dict) else {}
                prior_value = record.get(key)
                self._record_human_llm_feedback(build_id, key, prior_value, value, prior_status, record)
                record[key] = value
                override = key in MANIFEST_INHERITED_FIELDS
                statuses[key] = {
                    "status": "human_override" if override else "human_confirmed",
                    "method": "human_bulk_override" if override else "human_bulk",
                    "confidence": 1.0, "reason_code": "human_bulk",
                    "reason": "Applied through bulk record metadata editing.",
                }
                decisions.append({"field": key, "value": value, "at": iso_now(), "source": "human_bulk"})
            constraint_changes = apply_metadata_constraints(record)
            for item in constraint_changes:
                decisions.append({"field": item["field"], "value": item["value"], "at": iso_now(), "source": "deterministic_constraint", "reason": item["reason"]})
            record["metadata_decisions"] = decisions[-100:]
            record["metadata_reviewed_at"] = iso_now()
            self._mark_human_touch(record, list(changes))
            record["record_revision"] = int(record.get("record_revision") or 1) + 1
            self._sync_record_metadata_state(record, profile)
            inline, full = _citation_strings(record)
            record["inline_citation"] = inline; record["full_citation"] = full
            changed_ids.append(str(record.get("record_id") or ""))
        if not changed_ids:
            raise ValueError("No records matched the bulk metadata selection.")
        self._rewrite_and_validate(build_id, records)
        persisted = self.repo.load_records(build_id)
        return {"changed": len(changed_ids), "record_ids": changed_ids, "queue_counts": self._queue_counts(persisted)}

    @_serialize_record_mutation
    def record_view(self, build_id: str, record_id: str) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        target = next((row for row in records if str(row.get("record_id") or "") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        activity = dict(target.get("activity") or {})
        activity["human_view_count"] = int(activity.get("human_view_count") or 0) + 1
        activity["last_human_viewed_at"] = iso_now()
        target["activity"] = activity
        target["human_view_count"] = activity["human_view_count"]
        self._rewrite_and_validate(build_id, records)
        return {"record_id": record_id, "activity": activity}

    @_serialize_record_mutation
    def metadata_decision(self, build_id: str, record_id: str, field: str, value: Any, expected_revision: int | None = None, confirm_no_supported_value: bool = False) -> dict[str, Any]:
        """Persist one human metadata decision and return authoritative review state.

        This endpoint is deliberately transactional from the UI's perspective:
        one call saves the value, marks the field human-confirmed, recomputes all
        derived metadata/queue state, and returns the updated record and build.
        """
        if field not in self._editable_fields(build_id) or field in {"needs_review", "review_reason"}:
            raise ValueError(f"Unsupported review metadata field: {field}")
        if confirm_no_supported_value:
            records = self.repo.load_records(build_id)
            target = next((row for row in records if row.get("record_id") == record_id), None)
            if target is None: raise KeyError(record_id)
            self._assert_human_review_available(build_id, target)
            current_revision = self._assert_record_revision(target, expected_revision)
            self._push_review_history(build_id, records, action="metadata_confirm_absent", selected_record_id=record_id)
            prior_status = dict((target.get("metadata_field_status") or {}).get(field) or {})
            self._record_human_llm_feedback(build_id, field, target.get(field), None, prior_status, target)
            target[field] = None
            target.setdefault("metadata_field_status", {})[field] = {"status":"human_confirmed_absent","method":"human","confidence":1.0,"reason_code":"no_supported_value","reason":"Reviewer confirmed that no supported value applies to this record."}
            target.setdefault("metadata_decisions", []).append({"field":field,"value":None,"at":iso_now(),"source":"human_confirmed_absent"})
            target["metadata_decisions"] = target["metadata_decisions"][-100:]
            target["metadata_reviewed_at"] = iso_now(); self._mark_human_touch(target,[field])
            profile = self._profile_for(build_id)
            self._sync_record_metadata_state(target, profile); target["record_revision"] = current_revision + 1
            self._rewrite_and_validate(build_id, records)
            record = next((row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id), target)
        else:
            record = self.patch_metadata(build_id, record_id, {field: value}, expected_revision)
        records = self.repo.load_records(build_id)
        for row in records:
            if str(row.get("record_id") or "") != record_id:
                continue
            disputes = row.get("metadata_disputes") if isinstance(row.get("metadata_disputes"), list) else []
            for dispute in disputes:
                if isinstance(dispute, dict) and dispute.get("field") == field and not dispute.get("resolved_at"):
                    dispute["resolved_at"] = iso_now()
                    dispute["resolved_value"] = value
                    dispute["resolution_source"] = "human"
            row["metadata_disputes"] = disputes[-100:]
            record = row
            break
        self._rewrite_and_validate(build_id, records)
        for row in records:
            self._decorate_review_state(row)
        build = self.repo.get_build(build_id)
        self._refresh_workflow_fields(build)
        self.repo.save_build(build)
        remaining_fields = list(dict.fromkeys([
            str(v) for v in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])
        ]))
        return {
            "applied": True,
            "record": record,
            "build": build,
            "queue_counts": self._queue_counts(records),
            "remaining_fields": remaining_fields,
            "ready_for_acceptance": bool(record.get("can_accept")),
            "review_state": str(record.get("review_state") or "ready"),
        }

    @_serialize_record_mutation
    def patch_evidence(
        self,
        build_id: str,
        record_id: str,
        field: str,
        block_ids: list[str],
        confidence: float = 1.0,
        reason: str = "",
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        if field not in self._schema_for(build_id).attribution_fields() and field not in self._edit_model(build_id).model_fields:
            raise ValueError(f"Unsupported metadata evidence field: {field}")
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before editing evidence.")
        self._push_review_history(build_id, records, action="evidence_edit", selected_record_id=record_id)
        allowed_ids = set(map(str, target.get("source_block_ids") or []))
        unique_ids = list(dict.fromkeys(map(str, block_ids)))
        invalid = [block_id for block_id in unique_ids if block_id not in allowed_ids]
        if invalid:
            raise ValueError("Evidence blocks must belong to the selected record: " + ", ".join(invalid[:10]))
        evidence = dict(target.get("metadata_evidence") or {})
        if unique_ids:
            evidence[field] = {
                "block_ids": unique_ids,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "reason": str(reason or "Human-reviewed evidence binding."),
                "reviewed_by": "human",
                "reviewed_at": iso_now(),
            }
        else:
            evidence.pop(field, None)
        target["metadata_evidence"] = evidence
        target["metadata_needs_attention"] = True
        target["metadata_attention_reasons"] = ["Source evidence binding changed and metadata validation must be rerun."]
        target["record_revision"] = current_revision + 1
        self._rewrite_and_validate(build_id, records)
        return target

    @_serialize_record_mutation
    def slice_to_neighbor(
        self, build_id: str, record_id: str, direction: str, offset: int, expected_revision: int | None = None,
    ) -> dict[str, Any]:
        """Move reviewed text across an existing record boundary without creating a record.

        ``previous`` moves text before ``offset`` to the end of the previous record.
        ``next`` moves text after ``offset`` to the start of the next record.  The
        immutable extraction is retained on both records; this operation edits the
        reviewed corpus layer and records an atomic two-record revision.
        """
        if direction not in {"previous", "next"}:
            raise ValueError("Slice direction must be previous or next.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_human_review_available(build_id, target, structural=False)
        self._assert_record_revision(target, expected_revision)
        neighbor_index = index - 1 if direction == "previous" else index + 1
        if neighbor_index < 0 or neighbor_index >= len(records):
            raise ValueError(f"No {direction} record is available for this slice.")
        neighbor = records[neighbor_index]
        text = str(target.get("text") or "")
        original_texts = {str(target.get("record_id")): text, str(neighbor.get("record_id")): str(neighbor.get("text") or "")}
        if offset <= 0 or offset >= len(text):
            raise ValueError("Slice point must be inside the selected record text.")
        self._push_review_history(build_id, records, action=f"slice_{direction}", selected_record_id=record_id)
        if direction == "previous":
            moved, retained = text[:offset].strip(), text[offset:].lstrip()
            if not moved or not retained:
                raise ValueError("Slice must leave non-empty text in both records.")
            neighbor["text"] = (str(neighbor.get("text") or "").rstrip() + "\n\n" + moved).strip()
            target["text"] = retained
        else:
            retained, moved = text[:offset].rstrip(), text[offset:].strip()
            if not moved or not retained:
                raise ValueError("Slice must leave non-empty text in both records.")
            neighbor["text"] = (moved + "\n\n" + str(neighbor.get("text") or "").lstrip()).strip()
            target["text"] = retained
        now = iso_now()
        transaction_id = f"slice-{uuid.uuid4().hex[:12]}"
        for row in (target, neighbor):
            if "source_extracted_text" not in row:
                row["source_extracted_text"] = original_texts.get(str(row.get("record_id")), str(row.get("text") or ""))
            row["text_length"] = len(str(row.get("text") or ""))
            row["text_review_status"] = "human_corrected"
            row["text_reviewed_at"] = now
            row["text_review_source"] = "human_boundary_slice"
            row["review_disposition"] = "pending"
            row["accepted"] = False
            row["rejected"] = False
            row["needs_review"] = True
            row["review_reason"] = "Record boundary adjusted during human review; verify neighboring text and affected metadata."
            row["metadata_needs_attention"] = True
            reasons = list(row.get("metadata_attention_reasons") or [])
            reasons.append("Record boundary changed; metadata whose interpretation depends on moved text may need review.")
            row["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
            row["metadata_enrichment_state"] = "stale"
            row["record_revision"] = int(row.get("record_revision") or 1) + 1
            self._mark_human_touch(row, ["__text__", "__boundary__"])
            events = list(row.get("review_events") or [])
            events.append({"at": now, "event": "boundary_slice", "transaction_id": transaction_id, "direction": direction, "source_record_id": record_id})
            row["review_events"] = events[-100:]
        left_row, right_row = (neighbor, target) if direction == "previous" else (target, neighbor)
        self._record_boundary_editorial_example(
            build_id, left=left_row, right=right_row,
            action=f"human_slice_{direction}", transaction_id=transaction_id,
        )
        self._rewrite_and_validate(build_id, records)
        return {"record": target, "neighbor": neighbor, "direction": direction, "transaction_id": transaction_id}

    @_serialize_record_mutation
    def adjudicate_record_boundary(self, build_id: str, record_id: str, direction: str, request_override: dict[str, Any] | None = None) -> dict[str, Any]:
        if direction not in {"previous", "next"}:
            raise ValueError("Boundary direction must be previous or next.")
        records = self.repo.load_records(build_id)
        index = next((i for i, row in enumerate(records) if row.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        neighbor_index = index - 1 if direction == "previous" else index + 1
        if neighbor_index < 0 or neighbor_index >= len(records):
            raise ValueError(f"No {direction} record is available for boundary adjudication.")
        left, right = (records[neighbor_index], records[index]) if direction == "previous" else (records[index], records[neighbor_index])
        build = self.repo.get_build(build_id)
        request = self._interactive_llm_request(build_id, request_override)
        if not request.get("provider") and not request.get("provider_profile_id"):
            raise ValueError("No LLM provider is available for boundary adjudication.")
        decision = self._adjudicate_record_boundary_pair(left, right, build.get("manifest") or {}, request, build_id)
        profile = self._profile_of_build(build)
        self._apply_boundary_adjudication_to_records(left, right, decision, threshold=float(profile.get("min_boundary_confidence") or 0.72))
        self._rewrite_and_validate(build_id, records)
        current_build = self.repo.get_build(build_id)
        history = list(current_build.get("boundary_second_reader_history") or [])
        history.append({**decision, "requested_by": "human", "direction": direction})
        current_build["boundary_second_reader_history"] = history[-100:]
        self.repo.save_build(current_build)
        return {"decision": decision, "left_record": left, "right_record": right, "build": current_build}

    @_serialize_record_mutation
    def merge(self, build_id: str, record_id: str, direction: str, expected_revision: int | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=True)
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        self._assert_record_revision(records[index], expected_revision)
        self._save_review_undo(build_id, json.loads(json.dumps(records)), action="merge", selected_record_id=record_id)
        other_index = index - 1 if direction == "previous" else index + 1
        if other_index < 0 or other_index >= len(records):
            raise ValueError(f"No {direction} record is available to merge.")
        first_index, second_index = sorted((index, other_index))
        first, second = records[first_index], records[second_index]
        merged_ids = list(first.get("source_block_ids") or []) + list(second.get("source_block_ids") or [])
        blocks = {block["block_id"]: block for block in self.repo.load_blocks(self.repo.get_build(build_id)["asset_id"])}
        group = [blocks[block_id] for block_id in merged_ids if block_id in blocks]
        text = "\n\n".join(block["text"].strip() for block in group if block.get("text", "").strip())
        pages = sorted({int(block["page"]) for block in group})
        page_start, page_end = self._scholarly_page_range(group)
        merged_evidence: dict[str, Any] = {}
        for evidence_map in (first.get("metadata_evidence") or {}, second.get("metadata_evidence") or {}):
            for field, info in evidence_map.items():
                existing = merged_evidence.setdefault(field, {"block_ids": [], "confidence": 1.0, "reason": "Preserved across human merge.", "reviewed_by": "human", "reviewed_at": iso_now()})
                existing["block_ids"] = list(dict.fromkeys(list(existing.get("block_ids") or []) + list(info.get("block_ids") or [])))
                existing["confidence"] = min(float(existing.get("confidence") or 1.0), float(info.get("confidence") or 1.0))
        merged = {**first, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_block_ids": merged_ids, "source_spans": list(first.get("source_spans") or []) + list(second.get("source_spans") or []), "needs_review": True, "accepted": False, "rejected": False, "review_disposition": "pending", "review_reason": "Record boundaries were merged during human review.", "metadata_evidence": merged_evidence, "record_revision": max(int(first.get("record_revision") or 1), int(second.get("record_revision") or 1)) + 1}
        # Keep the first record's immutable identity. Unrelated downstream IDs never change.
        merged["record_id"] = first.get("record_id")
        records[first_index:second_index + 1] = [merged]
        self._rewrite_and_validate(build_id, records)
        return merged

    @_serialize_record_mutation
    def split(self, build_id: str, record_id: str, after_block_id: str, expected_revision: int | None = None) -> dict[str, Any]:
        self._assert_human_review_available(build_id, structural=True)
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
        self._assert_record_revision(target, expected_revision)
        self._save_review_undo(build_id, json.loads(json.dumps(records)), action="split", selected_record_id=record_id)
        ids = list(target.get("source_block_ids") or [])
        if after_block_id not in ids or ids.index(after_block_id) >= len(ids) - 1:
            raise ValueError("Split point must be a non-final source block in the selected record.")
        cut = ids.index(after_block_id) + 1
        block_map = {block["block_id"]: block for block in self.repo.load_blocks(self.repo.get_build(build_id)["asset_id"])}
        pieces = []
        for piece_ids in (ids[:cut], ids[cut:]):
            group = [block_map[block_id] for block_id in piece_ids if block_id in block_map]
            text = "\n\n".join(block["text"].strip() for block in group if block.get("text", "").strip())
            pages = sorted({int(block["page"]) for block in group})
            page_start, page_end = self._scholarly_page_range(group)
            piece_evidence: dict[str, Any] = {}
            for field, info in (target.get("metadata_evidence") or {}).items():
                kept = [block_id for block_id in (info.get("block_ids") or []) if block_id in piece_ids]
                if kept:
                    piece_evidence[field] = {**info, "block_ids": kept, "reason": str(info.get("reason") or "") + " Preserved across human split."}
            pieces.append({**target, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_block_ids": piece_ids, "source_spans": [span for span in target.get("source_spans") or [] if span.get("block_id") in piece_ids], "needs_review": True, "accepted": False, "rejected": False, "review_disposition": "pending", "review_reason": "Record boundary was split during human review.", "metadata_evidence": piece_evidence, "record_revision": int(target.get("record_revision") or 1) + 1})
        pieces[0]["record_id"] = target.get("record_id")
        pieces[1]["record_id"] = f"{re.sub(r'-[0-9a-f]{8}$', '', str(target.get('record_id') or 'pdf'))}-s{uuid.uuid4().hex[:8]}"
        records[index:index + 1] = pieces
        self._rewrite_and_validate(build_id, records)
        return {"records": pieces}

    @staticmethod
    def _initial_enrichment_operation(build_id: str, records: list[dict[str, Any]], *, started_at: str | None = None) -> dict[str, Any]:
        """Describe the book-scale first pass so the review workspace can start another immediately."""
        total = len(records)
        return {
            "operation_id": f"metadata-enrichment-initial-{str(build_id)[:12]}",
            "kind": "metadata_enrichment",
            "state": "completed",
            "started_at": started_at,
            "finished_at": iso_now(),
            "records_total": total,
            "records_processed": total,
            "passes_requested": 1,
            "passes_completed": 1,
            "current_pass": 1,
            "converged": False,
            "pass_results": [{"pass": 1, "records_processed": total}],
        }

    def retry_incomplete_metadata(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Retry only automatically-retryable metadata issues.

        This is deliberately separate from ``resume``: a metadata retry never
        re-enters document analysis, segmentation, or topology construction.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            return build
        records = self.repo.load_records(build_id)
        retryable_types = {"not_run", "llm_failed", "evidence_failed", "invalid_value", "unresolved"}
        target_indices: list[int] = []
        target_fields: dict[str, list[str]] = {}
        for index, record in enumerate(records):
            incomplete = [str(value) for value in record.get("metadata_incomplete_fields") or []]
            statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
            retry_fields = [field for field in incomplete if self._metadata_issue_type(statuses.get(field) if isinstance(statuses.get(field), dict) else {}, record) in retryable_types]
            if retry_fields:
                target_indices.append(index)
                target_fields[str(record.get("record_id") or index)] = retry_fields
        if not target_indices:
            raise ValueError("No automatically retryable metadata fields remain. Review the human-resolution queue instead.")
        self._validate_execution_budget(request)
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build["provider"] = request.get("provider") or build.get("provider") or "ollama"
        build["model"] = request.get("model") or build.get("model")
        build["request"] = {**(build.get("request") or {}), **public_request}
        operation_id = f"metadata-retry-{uuid.uuid4().hex[:10]}"
        operation = {
            "operation_id": operation_id, "kind": "metadata_retry", "state": "queued",
            "started_at": iso_now(), "finished_at": None,
            "records_total": len(target_indices), "records_processed": 0,
            "fields_total": sum(len(fields) for fields in target_fields.values()),
            "fields_resolved": 0, "fields_remaining": sum(len(fields) for fields in target_fields.values()),
            "provider_profile_id": public_request.get("provider_profile_id"),
            "provider": build.get("provider"), "model": build.get("model"),
            "target_fields": target_fields,
        }
        build["metadata_operation"] = operation
        self.repo.save_build(build)
        self._update(build_id, status="running", stage="metadata_retry", progress=max(0.96, float(build.get("progress") or 0.0)), error=None, resumable=False, metadata_operation=operation)
        self._executor.submit(self._retry_metadata_worker, build_id, request, operation_id, target_indices, target_fields)
        return self.repo.get_build(build_id)

    def _retry_metadata_worker(self, build_id: str, request: dict[str, Any], operation_id: str, target_indices: list[int], target_fields: dict[str, list[str]]) -> None:
        try:
            build = self.repo.get_build(build_id)
            records = self.repo.load_records(build_id)
            manifest = build.get("manifest") or {}
            total = max(1, len(target_indices))
            max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
            operation = dict(build.get("metadata_operation") or {})
            operation["state"] = "running"
            self._update(build_id, metadata_operation=operation)
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-corpus-meta-retry") as pool:
                futures = {}
                for index in target_indices:
                    record = dict(records[index])
                    previous_text = str(records[index - 1].get("text") or "") if index > 0 else ""
                    next_text = str(records[index + 1].get("text") or "") if index + 1 < len(records) else ""
                    before = list(record.get("metadata_incomplete_fields") or [])
                    future = pool.submit(self._enrich_record, record, manifest, request, previous_text=previous_text, next_text=next_text, build_id=build_id)
                    futures[future] = (index, before)
                processed = 0
                resolved = 0
                for future in as_completed(futures):
                    index, before = futures[future]
                    try:
                        updated = future.result()
                    except Exception as exc:
                        updated = dict(records[index])
                        statuses = updated.setdefault("metadata_field_status", {})
                        for field in target_fields.get(str(updated.get("record_id") or index), []):
                            statuses[field] = {"status": "unresolved", "method": "llm", "confidence": None, "reason_code": "llm_failed", "reason": f"Metadata retry failed: {exc}"}
                        updated["metadata_needs_attention"] = True
                        updated["metadata_attention_reasons"] = [f"Metadata retry failed: {exc}"]
                    records[index] = updated
                    after = set(updated.get("metadata_incomplete_fields") or [])
                    resolved += sum(1 for field in before if field not in after)
                    processed += 1
                    self.repo.save_records(build_id, records)
                    op = dict(self.repo.get_build(build_id).get("metadata_operation") or {})
                    op.update({
                        "state": "running", "records_processed": processed,
                        "fields_resolved": resolved,
                        "fields_remaining": max(0, int(op.get("fields_total") or 0) - resolved),
                    })
                    self._update(build_id, status="running", stage="metadata_retry", progress=min(0.979, 0.96 + 0.019 * (processed / total)), metadata_operation=op)
            final_build = self._rewrite_and_validate(build_id, records)
            target_remaining = 0
            for record in records:
                rid = str(record.get("record_id") or "")
                if rid not in target_fields:
                    continue
                incomplete_now = set(str(value) for value in record.get("metadata_incomplete_fields") or [])
                target_remaining += sum(1 for field in target_fields[rid] if field in incomplete_now)
            unresolved_after = int((final_build.get("metadata_issue_summary") or {}).get("fields_unresolved") or 0)
            op = dict(final_build.get("metadata_operation") or {})
            op.update({
                "state": "completed", "finished_at": iso_now(),
                "records_processed": len(target_indices),
                "fields_remaining": target_remaining,
                "fields_resolved": max(0, int(op.get("fields_total") or 0) - target_remaining),
                "unresolved_fields_after": unresolved_after,
            })
            final_build["metadata_operation"] = op
            self._refresh_workflow_fields(final_build)
            self.repo.save_build(final_build)
        except Exception as exc:
            build = self.repo.get_build(build_id)
            op = dict(build.get("metadata_operation") or {})
            op.update({"state": "failed", "finished_at": iso_now(), "error": str(exc)})
            build["metadata_operation"] = op
            build["status"] = "awaiting_review"
            build["stage"] = "review"
            build["error"] = None
            warnings = list(build.get("warnings") or [])
            warnings.append(f"Metadata retry failed: {exc}")
            build["warnings"] = warnings[-200:]
            self._refresh_workflow_fields(build)
            self.repo.save_build(build)

    @staticmethod
    def _enrichment_pass_indices(records: list[dict[str, Any]], scope: str, record_ids: list[str] | None = None) -> list[int]:
        """Records a pass should visit. Evaluated per pass: reviewers keep working between passes."""
        indices = []
        selected = {str(value) for value in (record_ids or []) if str(value)}
        for index, record in enumerate(records):
            if selected and str(record.get("record_id") or "") not in selected:
                continue
            disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
            if disposition == "rejected" or (scope == "accepted" and disposition != "accepted") or (scope == "pending" and disposition != "pending"):
                continue
            indices.append(index)
        return indices

    def rerun_metadata_enrichment(self, build_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Start one enrichment pass, or a chain of up to ``passes`` passes.

        The build stays open for review while passes run. A chain ends early once a
        pass changes nothing, because a further pass could only repeat itself.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Wait for the active corpus operation to finish before starting metadata enrichment.")
        self._validate_execution_budget(request)
        limit = max(1, int(settings.enrichment_max_concurrent_runs))
        working = self.active_enrichment_runs()
        if working >= limit:
            raise ValueError(f"{working} metadata enrichment run(s) are already working (the limit is {limit}). Wait for one to finish.")
        scope = str(request.get("scope") or "all")
        groups = self._schema_of_build(build).family_fields()
        families = [str(v) for v in request.get("families") or [] if str(v) in groups] or list(groups)
        passes = max(1, min(MAX_PASSES, int(request.get("passes") or 1)))
        record_ids = [str(value) for value in request.get("record_ids") or [] if str(value)]
        indices = self._enrichment_pass_indices(self.repo.load_records(build_id), scope, record_ids)
        if not indices:
            raise ValueError("No records match the selected metadata enrichment scope.")
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        operation_id = f"metadata-enrichment-{uuid.uuid4().hex[:10]}"
        run = {
            "operation_id": operation_id, "kind": "metadata_enrichment_rerun", "state": "queued",
            "started_at": iso_now(), "finished_at": None,
            "records_total": len(indices), "records_processed": 0, "records_unchanged": 0, "records_enriched": 0,
            "records_disputed": 0, "records_reopened": 0, "records_skipped": 0, "fields_replaced": 0, "fields_kept": 0,
            "provider_profile_id": public_request.get("provider_profile_id"),
            "provider": request.get("provider") or build.get("provider"), "model": request.get("model") or build.get("model"),
            "families": families, "scope": scope,
            "passes_requested": passes, "passes_completed": 0, "current_pass": 0, "converged": False, "pass_results": [],
            "record_ids": record_ids,
        }
        for key in ("recheck_rate", "iaa_rate"):
            if request.get(key) is not None:
                build["experiment"] = {**(build.get("experiment") or {}), key: float(request[key])}
        runs = list(build.get("metadata_enrichment_runs") or []) + [run.copy()]
        build["metadata_enrichment_runs"] = runs[-30:]
        build["metadata_operation"] = run.copy()
        self.repo.save_build(build)
        self._update(build_id, status="running", stage="metadata_enrichment_rerun", error=None, resumable=False, metadata_operation=run)
        # The operation id tags every ledger event this run writes, so runs never blur together.
        self._executor.submit(self._metadata_enrichment_rerun_worker, build_id, {**request, "run_id": operation_id}, operation_id, scope, families, passes)
        return self.repo.get_build(build_id)

    def _share_generalizable_learning(self, build_id: str) -> None:
        """Offer this build's reviewer-confirmed conventions to the cross-build store."""
        build = self.repo.get_build(build_id)
        if build.get("editorial_memory_reset_at"):
            return
        local = {field: value for field, value in self._editorial_memory(build_id).get("conventions", {}).items() if value.get("scope") != "global"}
        self._global_learning.observe(build_id, local)

    def _merge_enrichment_candidate(
        self, live: dict[str, Any], candidate: dict[str, Any], families: list[str], run_id: str, request: dict[str, Any], profile: dict[str, Any],
        schema: MetadataSchema | None = None,
    ) -> dict[str, Any]:
        """Fold one pass's candidate into the live record. Human-owned fields are never touched."""
        groups = (schema or default_schema()).family_fields()
        live_status = live.setdefault("metadata_field_status", {})
        cand_status = candidate.get("metadata_field_status") if isinstance(candidate.get("metadata_field_status"), dict) else {}
        cand_evidence = candidate.get("metadata_evidence") if isinstance(candidate.get("metadata_evidence"), dict) else {}
        live_evidence = live.setdefault("metadata_evidence", {})
        added: list[str] = []
        replaced: list[dict[str, Any]] = []
        kept: list[str] = []
        disputes: list[dict[str, Any]] = []
        known = {(d.get("field"), json.dumps(d.get("proposed"), sort_keys=True, default=str)) for d in live.get("metadata_disputes") or [] if isinstance(d, dict)}
        for family in families:
            for field in groups[family]:
                new, old = candidate.get(field), live.get(field)
                old_info = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
                new_info = cand_status.get(field) if isinstance(cand_status.get(field), dict) else {}
                if new in (None, "", []) or str(old_info.get("status") or "") in HUMAN_OWNED_STATUSES:
                    continue
                if old in (None, "", []):
                    live[field] = new
                    live_status[field] = new_info
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                    added.append(field)
                    continue
                if field in CONFIDENCE_FIELDS:
                    continue
                if same_value(old, new):
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                    continue
                if (field, json.dumps(new, sort_keys=True, default=str)) in known:
                    continue
                decision = resolve_conflict(old_info, new_info)
                if decision == "replace":
                    replaced.append({"field": field, "previous": old, "value": new, "confidence": new_info.get("confidence")})
                    live[field] = new
                    live_status[field] = new_info
                    if field in cand_evidence:
                        live_evidence[field] = cand_evidence[field]
                elif decision == "keep_existing":
                    kept.append(field)
                else:
                    known.add((field, json.dumps(new, sort_keys=True, default=str)))
                    candidate_entry = {"value": new, "source": run_id, "model": request.get("model")}
                    prior_dispute = next((item for item in live.get("metadata_disputes") or [] if isinstance(item, dict) and item.get("field") == field), None)
                    if prior_dispute is not None:
                        candidates = list(prior_dispute.get("candidates") or [{"value": prior_dispute.get("existing"), "source": "current"}])
                        if not any(same_value(item.get("value"), new) for item in candidates if isinstance(item, dict)):
                            candidates.append(candidate_entry)
                            prior_dispute["candidates"] = candidates[-12:]
                            prior_dispute["proposed"] = new
                            prior_dispute["run_id"] = run_id
                    else:
                        disputes.append({
                            "field": field, "existing": old, "proposed": new,
                            "candidates": [{"value": old, "source": "current"}, candidate_entry],
                            "confidence": new_info.get("confidence"), "reason": new_info.get("reason"), "run_id": run_id,
                        })
                    live_status[field] = {**old_info, "status": "unresolved", "reason_code": "llm_disagreement", "reason": "A later metadata enrichment pass proposed a different value and neither was confident enough to decide."}
        live["metadata_disputes"] = (list(live.get("metadata_disputes") or []) + disputes)[-100:]
        outcome = "enriched" if added or replaced else "disputed" if disputes else "unchanged"
        history = list(live.get("metadata_enrichment_history") or [])
        history.append({
            "run_id": run_id, "at": iso_now(), "state": "complete", "outcome": outcome, "added_fields": added,
            "replaced": replaced, "kept_existing": kept, "disputes": disputes,
            "provider_profile_id": request.get("provider_profile_id"), "model": request.get("model"),
        })
        live["metadata_enrichment_history"] = history[-30:]
        activity = dict(live.get("activity") or {})
        activity["llm_review_count"] = int(activity.get("llm_review_count") or 0) + 1
        activity["enrichment_pass_count"] = int(activity.get("enrichment_pass_count") or 0) + 1
        activity["last_llm_reviewed_at"] = iso_now()
        activity["last_enrichment_at"] = activity["last_llm_reviewed_at"]
        activity["last_enrichment_provider"] = request.get("provider")
        activity["last_enrichment_model"] = request.get("model")
        live["activity"] = activity
        if added or replaced or disputes:
            live["review_disposition"] = "pending"
            live["accepted"] = False
            live["rejected"] = False
            live["needs_review"] = True
            live["review_reason"] = "Metadata enrichment added, replaced, or disputed metadata; review the highlighted changes."
            self._sync_record_metadata_state(live, profile)
        return {"outcome": outcome, "added": len(added), "replaced": len(replaced), "kept": len(kept), "disputed": len(disputes)}

    def _run_enrichment_pass(
        self, build_id: str, request: dict[str, Any], run_id: str, scope: str, families: list[str],
        on_progress: Callable[[dict[str, int], int], None],
    ) -> dict[str, int]:
        """Run one pass over the records currently in scope, merging results into live state."""
        build = self.repo.get_build(build_id)
        manifest = build.get("manifest") or {}
        profile = self._profile_of_build(build)
        snapshot = self.repo.load_records(build_id)
        indices = self._enrichment_pass_indices(snapshot, scope, [str(value) for value in request.get("record_ids") or []])
        max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
        totals: Counter[str] = Counter()
        pass_schema = self._schema_for(build_id)
        epoch_at_start = self._provider_epoch.get(build_id, 0)
        provider_keys = ("provider", "model", "base_url", "api_key", "generation", "provider_profile_id", "review_provider_profile_id", "_review_provider")

        def effective_request() -> dict[str, Any]:
            """This run's request, with the provider the reviewer switched to since it started, if they did.

            A switch applies to records not yet started; requests already in flight finish on the old model.
            Each event in the ledger names the model that actually answered, so the metrics show both.
            """
            if self._provider_epoch.get(build_id, 0) == epoch_at_start:
                return request
            live = self._latest_runtime_request(build_id, request)
            return {**request, **{key: live[key] for key in provider_keys if key in live}}

        def candidate_for(index: int) -> dict[str, Any]:
            candidate = json.loads(json.dumps(snapshot[index]))
            status = candidate.get("metadata_field_status") if isinstance(candidate.get("metadata_field_status"), dict) else {}
            for family in families:
                for field in pass_schema.family_fields()[family]:
                    candidate.pop(field, None)
                    status.pop(field, None)
                candidate.setdefault("metadata_stage_status", {}).pop(family, None)
                candidate.setdefault("metadata_execution_ledger", {}).pop(family, None)
            candidate["metadata_field_status"] = status
            neighbors = {
                "previous_text": str(snapshot[index - 1].get("text") or "") if index > 0 else "",
                "next_text": str(snapshot[index + 1].get("text") or "") if index + 1 < len(snapshot) else "",
            }
            return self._enrich_record(
                candidate,
                manifest,
                {**effective_request(), "families": families, "_interactive_provider_override": True},
                build_id=build_id,
                previous_text=neighbors["previous_text"],
                next_text=neighbors["next_text"],
            )

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdf-corpus-meta-enrich") as pool:
            futures = {pool.submit(candidate_for, index): index for index in indices}
            for future in as_completed(futures):
                if self._cancelled(build_id):
                    for outstanding in futures:
                        outstanding.cancel()
                    break
                index = futures[future]
                record_id = str(snapshot[index].get("record_id") or "")
                try:
                    candidate = future.result()
                except Exception as exc:
                    candidate = None
                    failure = {"run_id": run_id, "at": iso_now(), "state": "failed", "error": str(exc)}
                # Merge into the live copy, never the snapshot: the reviewer may have
                # edited this or any other record while the model was thinking.
                result: dict[str, Any]
                with self._lock:
                    live_records = self.repo.load_records(build_id)
                    live = next((row for row in live_records if str(row.get("record_id") or "") == record_id), None)
                    if live is None:
                        continue
                    if candidate is None:
                        live["metadata_enrichment_history"] = (list(live.get("metadata_enrichment_history") or []) + [failure])[-30:]
                        result = {"outcome": "failed"}
                    elif live.get("text") != snapshot[index].get("text"):
                        result = {"outcome": "skipped"}
                    else:
                        was_accepted = str(live.get("review_disposition") or "pending") == "accepted"
                        result = self._merge_enrichment_candidate(live, candidate, families, run_id, effective_request(), profile, schema=pass_schema)
                        if was_accepted and result["outcome"] != "unchanged":
                            totals["records_reopened"] += 1
                    self.repo.save_records(build_id, live_records)
                totals["records_processed"] += 1
                for key, name in (("added", "fields_added"), ("replaced", "fields_replaced"), ("kept", "fields_kept"), ("disputed", "fields_disputed")):
                    totals[name] += result.get(key, 0)
                totals[f"records_{result['outcome']}"] += 1
                on_progress(dict(totals), len(indices))
        return dict(totals)

    def _metadata_enrichment_rerun_worker(self, build_id: str, request: dict[str, Any], operation_id: str, scope: str, families: list[str], passes: int) -> None:
        op = dict(self.repo.get_build(build_id).get("metadata_operation") or {})
        try:
            counter_keys = ("records_processed", "records_enriched", "records_disputed", "records_unchanged", "records_skipped", "records_reopened", "fields_replaced", "fields_kept")
            for pass_number in range(1, passes + 1):
                if self._cancelled(build_id):
                    op["state"] = "cancelled"
                    break
                # Each pass starts from what reviewers and earlier passes settled,
                # and the editorial memory it reads reflects both.
                self._share_generalizable_learning(build_id)
                before = {key: int(op.get(key) or 0) for key in counter_keys}

                def on_progress(totals: dict[str, int], pass_total: int, pass_number: int = pass_number, before: dict[str, int] = before) -> None:
                    op.update({key: before[key] + totals.get(key, 0) for key in counter_keys})
                    op.update({"state": "running", "current_pass": pass_number, "records_total": max(int(op.get("records_total") or 0), pass_total)})
                    fraction = ((pass_number - 1) + totals.get("records_processed", 0) / max(1, pass_total)) / passes
                    self._update(build_id, metadata_operation=dict(op), progress=min(0.995, 0.78 + 0.20 * fraction))

                op.update({"state": "running", "current_pass": pass_number})
                totals = self._run_enrichment_pass(build_id, request, operation_id, scope, families, on_progress)
                changed = totals.get("fields_added", 0) + totals.get("fields_replaced", 0) + totals.get("fields_disputed", 0)
                op["passes_completed"] = pass_number
                op["pass_results"] = list(op.get("pass_results") or []) + [{"pass": pass_number, "changed_fields": changed, **totals}]
                self._update(build_id, metadata_operation=dict(op))
                if self._cancelled(build_id):
                    op["state"] = "cancelled"
                    break
                if changed == 0:
                    # A pass that changes nothing has converged; more would repeat it.
                    op["converged"] = True
                    break
            self._share_generalizable_learning(build_id)
            with self._lock:
                final = self._rewrite_and_validate(build_id, self.repo.load_records(build_id))
                op.update({"state": op["state"] if op.get("state") == "cancelled" else "completed", "finished_at": iso_now()})
                final["metadata_operation"] = op
                final["metadata_enrichment_runs"] = [({**r, **op} if r.get("operation_id") == operation_id else r) for r in final.get("metadata_enrichment_runs") or []]
                final.update({"status": "awaiting_review", "stage": "review", "progress": 1.0, "cancel_requested": False})
                self._cancel.discard(build_id)
                self._refresh_workflow_fields(final)
                self.repo.save_build(final)
        except Exception as exc:
            build = self.repo.get_build(build_id)
            op.update({"state": "failed", "finished_at": iso_now(), "error": str(exc)})
            build.update({"metadata_operation": op, "status": "awaiting_review", "stage": "review", "cancel_requested": False})
            self._cancel.discard(build_id)
            self.repo.save_build(build)

    @_serialize_record_mutation
    def rerun_metadata(self, build_id: str, record_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        requested_families = request.get("families")
        rerun_groups = self._schema_for(build_id).family_fields()
        families = [str(value) for value in requested_families or [] if str(value) in rerun_groups]
        if not families:
            families = list(rerun_groups)
        # Clear only values owned by the selected LLM family. Inherited,
        # deterministic, human-confirmed, and human-override values are
        # authoritative and survive reruns.
        status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
        for family in families:
            for key in rerun_groups[family]:
                info = status_map.get(key) if isinstance(status_map.get(key), dict) else {}
                if str(info.get("status") or "") in {"human_confirmed", "human_override", "inherited", "deterministic"}:
                    continue
                if str(info.get("method") or "").startswith("llm") or str(info.get("status") or "") in {"llm_inferred", "unresolved", "invalid"}:
                    target.pop(key, None)
                    status_map.pop(key, None)
            target.setdefault("metadata_stage_status", {}).pop(family, None)
            target.setdefault("metadata_stage_results", {}).pop(family, None)
            target.setdefault("metadata_execution_ledger", {}).pop(family, None)
        target["metadata_field_status"] = status_map
        rerun_request = dict(request)
        rerun_request["families"] = families
        rerun_request["_interactive_provider_override"] = True
        index = records.index(target)
        self._enrich_record(
            target,
            build.get("manifest") or {},
            rerun_request,
            previous_text=str(records[index - 1].get("text") or "") if index > 0 else "",
            next_text=str(records[index + 1].get("text") or "") if index + 1 < len(records) else "",
            build_id=build_id,
        )
        self._rewrite_and_validate(build_id, records)
        return target

    @staticmethod
    def _validate_publication_record(record: dict[str, Any]) -> list[str]:
        return validate_publication_record(record)

    def _serialize_public_record(self, build: dict[str, Any], record: dict[str, Any], publication_id: str, created_at: str) -> dict[str, Any]:
        return serialize_public_record(record)

    def preview_record(self, build_id: str, record_id: str) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        record = next((row for row in records if row.get("record_id") == record_id), None)
        if record is None:
            raise KeyError(record_id)
        self._present_for_reviewer(record)  # the preview is built from the record as this reviewer may see it
        preview_id = f"preview-{build_id.removeprefix('build-')}"
        created_at = iso_now()
        public = self._serialize_public_record(build, record, preview_id, created_at)
        errors = self._validate_publication_record(public)
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
        prompt = f"""You are performing a conservative scholarly text touch-up on OCR/PDF extracted text.

RULES:
- Preserve wording, meaning, quotations, terminology, paragraph order, and authorial style.
- Do NOT paraphrase, summarize, modernize, translate, or add content.
- Correct only obvious OCR artifacts, broken words, spacing, punctuation, accidental line wrapping, duplicated running headers/footers/page numbers, and clear textual errata caused by extraction.
- Preserve poetry, verse, block quotations, lists, footnotes, and deliberate typographic/orthographic oddities unless the artifact is unambiguous.
- When uncertain, leave the source text unchanged and mention the uncertainty in warnings.
- Return the COMPLETE touched-up text.
- In the JSON text field, return ONLY the corrected passage text. Do not add Markdown fences, triple-hyphen separators, SOURCE_TEXT labels, quotation wrappers, or commentary around the passage.

Optional reviewer instruction: {instructions or 'None'}

SOURCE_TEXT:
<SOURCE_TEXT>
{current_text}
</SOURCE_TEXT>
"""
        result = self._chat_json(active_request, prompt, response_model=TextTouchupResponseModel, max_tokens=min(8192, max(2048, len(current_text)//3)), schema_name="record_text_touchup", attempts=2, build_id=build_id)
        proposed = _sanitize_touchup_output(str(result.get("text") or ""), current_text)
        if not proposed:
            raise ValueError("LLM text touch-up returned empty text.")
        provider, model, _, _, _ = self._llm_config(active_request)
        return {
            "record_id": record_id,
            "source_text": current_text,
            "proposed_text": proposed,
            "changes": list(result.get("changes") or []),
            "warnings": list(result.get("warnings") or []),
            "provider": provider,
            "model": model,
        }

    @_serialize_record_mutation
    def publish(self, build_id: str, *, require_acceptance: bool = True) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        validation = build.get("validation") or {}
        self._refresh_workflow_fields(build)
        readiness = build.get("publication_readiness") if isinstance(build.get("publication_readiness"), dict) else {}
        readiness_blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
        missing_document = [item for item in readiness_blockers if isinstance(item, dict) and item.get("code") == "required_document_metadata"]
        if missing_document:
            fields = ", ".join(str(value) for value in (missing_document[0].get("fields") or []))
            raise ValueError(f"Publication is blocked: required document metadata is missing ({fields}).")
        metadata_total = int(build.get("metadata_total") or 0)
        metadata_completed = int(build.get("metadata_completed") or 0)
        if metadata_total and metadata_completed < metadata_total:
            summary = build.get("metadata_issue_summary") or {}
            by_field = summary.get("by_field") if isinstance(summary, dict) else {}
            detail = ", ".join(f"{field}: {count}" for field, count in sorted((by_field or {}).items()))
            suffix = f" Unresolved fields — {detail}." if detail else ""
            raise ValueError(f"Publication is blocked: metadata is complete for {metadata_completed} of {metadata_total} record(s).{suffix} Resolve the metadata issue queue before publishing.")
        if not validation.get("valid"):
            raise ValueError("Publication is blocked until source coverage and text-fidelity validation pass.")
        publishable_records = [record for record in records if str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "pending")) != "rejected" and not record.get("rejected")]
        if not publishable_records:
            raise ValueError("Publication is unavailable because every record is rejected. Restore at least one record or discard this build.")
        unresolved = [record for record in publishable_records if record.get("needs_review")]
        if unresolved:
            raise ValueError(f"Publication is blocked: {len(unresolved)} publishable record(s) still need review.")
        if require_acceptance:
            unaccepted = [record for record in publishable_records if not record.get("accepted")]
            if unaccepted:
                raise ValueError(f"Publication is blocked: {len(unaccepted)} publishable record(s) have not been accepted.")
        publication_id = f"publication-{build_id.removeprefix('build-')}-{uuid.uuid4().hex[:8]}"
        created_at = iso_now()
        path = self.repo.publication_path(publication_id)
        hasher = hashlib.sha256()
        with path.open("wb") as handle:
            for record in publishable_records:
                # Use the same serializer as the per-record JSONL preview so the
                # reviewer sees the exact eventual public record shape.
                public = self._serialize_public_record(build, record, publication_id, created_at)
                schema_errors = self._validate_publication_record(public)
                if schema_errors:
                    joined = "; ".join(schema_errors[:8])
                    raise ValueError(f"Publication schema validation failed for {public.get('record_id') or 'unknown record'}: {joined}")
                line = (json.dumps(public, ensure_ascii=False) + "\n").encode("utf-8")
                hasher.update(line)
                handle.write(line)
        publication = {"publication_id": publication_id, "filename": f"{Path(build.get('source_filename') or 'corpus').stem}.jsonl", "sha256": hasher.hexdigest(), "record_count": len(publishable_records), "excluded_rejected_count": len(records) - len(publishable_records), "created_at": created_at}
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
