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

"""Compatibility facade for Corpus Builder orchestration.

This module still owns the public manager surface and historical compatibility
exports, but most behavior is deliberately split into focused `corpus_*` and
`source_*` modules. New extraction, enrichment, review, or publication logic
belongs in the focused owner module unless it genuinely coordinates multiple
stages; do not grow this file simply because older callers import from it.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
import unicodedata
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import Any

import fitz
from pydantic import BaseModel, ValidationError

from . import (
    corpus_document_context,
    corpus_queue_projection,
    metadata_exemplar_journal,
)
from .autonomous import Policy as AutonomousPolicy
from .celf_conformance import evaluate_celf_conformance
from .concurrency import (
    bounded_as_completed,
    capacity_coordinator,
    provider_capacity_key,
    provider_limit,
)
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
    _merge_preparation_snapshot,
    _metadata_family_states,
    _record_source_matches,
)
from .corpus_enrichment_helpers import (
    _semantic_atoms as _semantic_atoms,
)
from .corpus_enrichment_reruns import EnrichmentRerunsMixin
from .corpus_extraction import (
    extract_source_document as _extract_source_document,
)
from .corpus_llm_helpers import (
    StructuredOutputError,
    _context_window,
    _llm_config,
    _parse_json_robust,  # noqa: F401 - compatibility export
    _provider_roles,
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
    CORPUS_PROFILES as CORPUS_PROFILES,
)
from .corpus_models import (
    DOCUMENT_PROMPT_VERSION as DOCUMENT_PROMPT_VERSION,
)
from .corpus_models import (
    METADATA_PROMPT_VERSION as METADATA_PROMPT_VERSION,
)
from .corpus_models import (
    PROFILE_VERSION as PROFILE_VERSION,
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
    DocumentManifestModel,
    PageMarkerChoiceModel,
    TextTouchupResponseModel,
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
    mark_unreviewed_publication,
    provenance_warnings,
    publication_blocker,
    publishable_records,
    serialize_public_record,
    validate_publication_record,
    warning_key,
)
from .corpus_record_quality import (
    _record_extraction_quality_issues,
    _trash_quality_report,
    iso_now,
)
from .corpus_review_actions import ReviewActionsMixin, _serialize_record_mutation
from .corpus_review_aggregates import record_review_aggregate
from .corpus_review_queue import (
    QueueFilter,
    QueueSelection,
    QueueSelectionCache,
    select_queue,
)
from .corpus_review_state import (
    _decorate_review_state,
    _enforce_review_invariants,
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
    _operation_from_build as _operation_from_build,
)
from .corpus_reviewer_helpers import (
    _present_for_reviewer,
    _scrub_canonical_transport,
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
from .derridai_ledger import write_jsonl_zst
from .document_intelligence import (
    analyze_document,
    document_text_for_records,
    project_annotations_to_records,
)
from .enrichment_cycles import (
    GlobalLearningStore,
)
from .enrichment_ledger import (
    ACCEPTED,
    BLIND_LABEL,
    CORRECTED,
    REJECTED,
    UNRESOLVED,
    EnrichmentLedger,
)
from .error_severity import severity as error_severity
from .field_assertions import (
    create_unresolved_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
)
from .language_segmentation import ends_sentence_text, starts_mid_sentence_text
from .language_segmentation import (
    profile_metadata as language_segmentation_profile,
)
from .main_text_start import infer_main_text_start
from .memory_prefill import prefill_records
from .metadata_exemplar_projection import (
    dirty_metadata_exemplar_build_ids,
    project_build_metadata_exemplars,
    record_projection_result,
)
from .metadata_exemplar_retrieval import ChromaMetadataExemplarIndex
from .metadata_schema import (
    MetadataSchema,
)
from .metadata_schema_store import SchemaStore
from .models import WorkMetadataRequest, WorkMetadataSeed
from .nlp_annotations import annotate_record, annotation_run_summary
from .operation_events import (
    note_corpus_build,
    note_record_metadata,
    note_resource_changed,
)
from .page_markers import DETECTOR_VERSION as PAGE_DETECTOR_VERSION
from .pipelines.corpus_document_manifest import DocumentManifestSession
from .pipelines.corpus_text_touchup import TextTouchupSession
from .rag import _citation_strings, chat_complete
from .record_semantic_map import build_semantic_map_projections
from .reviewer_context import current_reviewer
from .run_guidance import find_guidance_matches
from .semantic_content_graph import (
    build_semantic_content_graph,
    semantic_content_graph_view,
)
from .semantic_identity import ValueEquivalenceResult
from .semantic_identity_registry import (
    SemanticIdentityRegistry,
    compare_field_values,
    registry_for_record,
)
from .semantic_identity_store import build_registry, review_registry
from .sentence_boundaries import snap_boundaries_to_sentences
from .source_embeddings import SourceEmbeddingProjection
from .source_quality import assess_extracted_source, page_source_quality_report
from .structured_completion import (
    StructuredAttemptContext,
    StructuredAttemptOutcome,
    StructuredCompletionError,
    complete_structured_json,
)
from .structured_json import (
    StructuredJsonMalformedError,  # noqa: F401 - compatibility export
    StructuredJsonTruncatedError,  # noqa: F401 - compatibility export
)
from .system_store import system_store
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
logger = logging.getLogger(__name__)


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


def annotate_boundary_suspects(
    records: list[dict[str, Any]],
    language: str | None = None,
) -> int:
    """Flag likely sentence/quotation cuts without assuming Latin lowercase rules."""

    def record_language(record: dict[str, Any]) -> str | None:
        values = record.get("region_language")
        if isinstance(values, list):
            cleaned = [str(value).strip() for value in values if str(value).strip()]
            if len(cleaned) == 1:
                return cleaned[0]
        elif isinstance(values, str) and values.strip():
            return values.strip()
        return language

    count = 0
    for left, right in zip(records, records[1:]):
        lt = str(left.get("text") or "").rstrip()
        rt = str(right.get("text") or "").lstrip()
        if not lt or not rt:
            continue
        incomplete_left = not ends_sentence_text(lt, record_language(left))
        continuation_right = starts_mid_sentence_text(rt, record_language(right))
        open_quote = (
            (lt.count('"') % 2 == 1)
            or (lt.count("“") > lt.count("”"))
            or (lt.count("「") > lt.count("」"))
            or (lt.count("『") > lt.count("』"))
            or (lt.count("«") > lt.count("»"))
        )
        if incomplete_left and (continuation_right or open_quote):
            reason = "Possible sentence/quotation continuation across this record boundary."
            for row, edge in ((left, "end"), (right, "start")):
                flags = list(row.get("boundary_quality_issues") or [])
                flags.append({"code": "boundary_suspect", "edge": edge, "reason": reason})
                row["boundary_quality_issues"] = flags
                row["needs_review"] = True
                if (
                    not row.get("review_reason")
                    or str(row.get("review_reason")).lower() == "pending human review."
                ):
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
    for attempt in range(4):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except PermissionError:
            if os.name != "nt" or attempt == 3:
                raise
            # Windows can briefly deny opens while another repository atomically replaces this file.
            time.sleep(0.005 * (2 ** attempt))
        except (FileNotFoundError, json.JSONDecodeError):
            return default


# 2026: renamed to match the cELF Core Specification's assertion-status vocabulary
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

def _one_record_per_estimated_page(asset: dict[str, Any]) -> bool:
    """Word-count pages become one record each unless the reviewer turned that off."""
    detection = asset.get("page_number_detection") if isinstance(asset.get("page_number_detection"), dict) else {}
    if detection.get("status") != "estimated":
        return False
    estimate = asset.get("page_estimate") if isinstance(asset.get("page_estimate"), dict) else {}
    if "one_record_per_page" in estimate:
        return bool(estimate.get("one_record_per_page"))
    return bool(detection.get("one_record_per_page", True))


def _can_use_synthetic_record_pages(asset: dict[str, Any]) -> bool:
    """Synthetic Record pages never replace physical or detected source pagination."""
    media_kind = str(asset.get("media_kind") or "").lower()
    if media_kind in {"pdf", "image", "audio"}:
        return False
    detection = asset.get("page_number_detection") if isinstance(asset.get("page_number_detection"), dict) else {}
    return str(detection.get("status") or "") != "detected"


def _apply_synthetic_record_pages(records: list[dict[str, Any]], records_per_page: int) -> None:
    """Group Records into stable synthetic pages without rewriting source-span locators."""
    per_page = max(1, int(records_per_page or 1))
    for index, record in enumerate(records):
        page = index // per_page + 1
        record["page_start"] = page
        record["page_end"] = page
        record["synthetic_page"] = page
        record["page_number_source"] = "record_grouping"


class RecordStateConflict(ValueError):
    """A conditional Record write lost a concurrent canonical-state race."""


class PdfCorpusRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or corpus_root()
        for part in ("assets", "builds", "publications"):
            (self.root / part).mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._asset_ingest_lock = threading.RLock()
        # Registry access stays under _lock. Retain entries after deletion so a
        # queued caller cannot obtain a different admission lock for the same ID.
        self._checkpoint_locks: dict[str, Any] = {}
        # Review paging is read-heavy. Keep a small, read-only parsed snapshot cache so
        # changing pages does not JSON-decode and migrate the entire corpus on every
        # GraphQL request. The SQLite file signature catches writers in another process;
        # local writers also invalidate explicitly below.
        self._review_records_cache: dict[
            str, tuple[tuple[int, int], list[dict[str, Any]]]
        ] = {}
        self._review_records_cache_capacity = 4
        self._queue_selection_cache = QueueSelectionCache()
        # (payload digest, schema signature) pairs known to be fixed points of
        # ``migrate_record_assertions``/``_migrate_status_vocabulary``. Migration is
        # idempotent and every writer already migrates, so re-running it on every read
        # of an unchanged payload was most of the cost of loading or saving a corpus.
        self._migration_fixed_points: set[tuple[bytes, bytes]] = set()
        self._metadata_projection_callback: Callable[[str], None] | None = None
        self._initialized_record_databases: dict[str, tuple[int, int, int]] = {}

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
        source_url: str | None = None, detect_page_numbers: bool = True,
        page_llm: Any = None,
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
        # OCR is an image-region operation. Keep legacy request fields accepted for
        # compatibility, but never let them affect text, audio, URL, or Gutenberg
        # extraction identities or behavior.
        if kind not in {"pdf", "image"}:
            ocr_mode = "never"
            illegibility = 0.0
        digest = hashlib.sha256(data).hexdigest()
        # Default PDF uploads keep the historical content-addressed id.
        identity = digest
        if kind != "pdf" or ocr_mode != "auto" or illegibility:
            identity = hashlib.sha256(f"{digest}|{kind}|source-extraction-v2|{ocr_mode}|{illegibility:.2f}".encode()).hexdigest()
        if catalog_metadata and catalog_metadata.get("gutenberg_id"):
            identity = hashlib.sha256(f"{identity}|gutenberg|{catalog_metadata['gutenberg_id']}".encode()).hexdigest()
        if page_llm is not None and kind not in {"pdf", "audio", "image"}:
            identity = hashlib.sha256(f"{identity}|page-detection-llm".encode()).hexdigest()
        if not detect_page_numbers and kind not in {"pdf", "audio", "image"}:
            # A different page structure is a different asset; keep the two apart.
            identity = hashlib.sha256(f"{identity}|page-detection-off".encode()).hexdigest()
        else:
            identity = hashlib.sha256(f"{identity}|page-detect-v{PAGE_DETECTOR_VERSION}".encode()).hexdigest() if kind not in {"pdf", "audio", "image"} else identity
        asset_id = f"pdf-{identity[:24]}"
        suffix = ".pdf" if kind == "pdf" else content_suffix_for(kind, filename)
        meta_path = self.asset_meta_path(asset_id)
        # Keep extractor admission serialized without holding canonical coordination.
        # Lock order is ingestion then repository; extraction runs outside the latter.
        with self._asset_ingest_lock:
            with self._lock:
                existing = _json_read(meta_path)
                existing_suffix = str(existing.get("content_suffix") or ".pdf") if isinstance(existing, dict) else suffix
                if isinstance(existing, dict) and self.asset_content_path(asset_id, existing_suffix).exists():
                    return existing
            extracted = self._extract_for_ingest(
                data, filename=filename, kind=kind, ocr_mode=ocr_mode, ocr_languages=ocr_languages,
                source_illegibility=illegibility, catalog_metadata=catalog_metadata,
                detect_page_numbers=detect_page_numbers, page_llm=page_llm,
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
            staged = self.root / "assets" / f".ingest-{uuid.uuid4().hex}"
            staged.mkdir()
            published: list[Path] = []
            try:
                self._stage_asset(staged, data, blocks, meta)
                with self._lock:
                    existing = _json_read(meta_path)
                    existing_suffix = str(existing.get("content_suffix") or ".pdf") if isinstance(existing, dict) else suffix
                    if isinstance(existing, dict) and self.asset_content_path(asset_id, existing_suffix).exists():
                        return existing
                    try:
                        for source, target in (
                            (staged / "content", self.asset_content_path(asset_id, suffix)),
                            (staged / "blocks", self.asset_blocks_path(asset_id)),
                            (staged / "meta", meta_path),
                        ):
                            os.replace(source, target)
                            published.append(target)
                    except BaseException:
                        for target in reversed(published):
                            target.unlink(missing_ok=True)
                        raise
                return meta
            finally:
                shutil.rmtree(staged)

    @staticmethod
    def _stage_asset(staged: Path, data: bytes, blocks: list[dict[str, Any]], meta: dict[str, Any]) -> None:
        # Metadata is the publication marker and is replaced last. Flush source
        # artifacts before admission; repository coordination only covers renames.
        with (staged / "content").open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        with (staged / "blocks").open("w", encoding="utf-8") as handle:
            for block in blocks:
                handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _json_write(staged / "meta", meta)

    def preview_unit_policy(self, asset_id: str, policy: dict[str, Any] | None) -> dict[str, Any]:
        """Counts and sample units for a source-unit policy, without saving anything."""
        from .unit_policy import preview

        resolved_policy = dict(policy or {})
        if not resolved_policy.get("language"):
            asset = self.get_asset(asset_id)
            initial = asset.get("initial_metadata") if isinstance(asset.get("initial_metadata"), dict) else {}
            embedded = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
            source_language = initial.get("language") or embedded.get("language")
            if source_language not in (None, ""):
                resolved_policy["language"] = str(source_language)
        return preview(self.load_blocks(asset_id), resolved_policy)

    def derive_asset_with_units(self, asset_id: str, policy: dict[str, Any] | None) -> dict[str, Any]:
        """A new source asset whose evidence units follow ``policy``.

        The original asset is untouched. The derived asset shares the original bytes and content
        digest, divides prose blocks deterministically (text conserved), and remembers where it
        came from. Choosing ``default`` returns the asset this one was derived from, if any.
        """
        from .source_quality import page_source_quality_report
        from .unit_policy import apply_unit_policy, normalize_policy

        resolved = normalize_policy(policy)
        source = _json_read(self.asset_meta_path(asset_id))
        if not isinstance(source, dict):
            raise KeyError(asset_id)
        origin_id = str(source.get("derived_from_asset_id") or asset_id)
        if resolved["mode"] == "default":
            return self.get_asset(origin_id)
        origin = _json_read(self.asset_meta_path(origin_id))
        if not isinstance(origin, dict):
            raise KeyError(origin_id)
        if resolved["mode"] in {"sentence", "auto"} and not resolved.get("language"):
            initial = origin.get("initial_metadata") if isinstance(origin.get("initial_metadata"), dict) else {}
            embedded = origin.get("metadata") if isinstance(origin.get("metadata"), dict) else {}
            source_language = initial.get("language") or embedded.get("language")
            if source_language not in (None, ""):
                resolved = {**resolved, "language": str(source_language)}
        size_key = resolved.get("chars", "") if resolved["mode"] != "auto" else f"auto{resolved['max_chars']}"
        per_key = f"|per{resolved['per']}" if resolved.get("per") else ""
        language_key = f"|lang{resolved['language']}" if resolved.get("language") else ""
        digest = hashlib.sha256(
            f"{origin_id}|units|{resolved['mode']}|{size_key}{per_key}{language_key}".encode()
        ).hexdigest()
        derived_id = f"pdf-{digest[:24]}"
        meta_path = self.asset_meta_path(derived_id)
        with self._lock:
            existing = _json_read(meta_path)
            if isinstance(existing, dict):
                return self.get_asset(derived_id)
            blocks = self._load_block_rows(origin_id)
            derived_blocks, remap = apply_unit_policy(blocks, resolved)
            children: dict[str, list[str]] = {
                str(block.get("block_id")): remap[index] for index, block in enumerate(blocks)
            }
            pages = []
            for page in origin.get("pages") or []:
                page = dict(page)
                page["block_ids"] = list(dict.fromkeys(
                    child for old in page.get("block_ids") or [] for child in children.get(str(old), [str(old)])
                ))
                pages.append(page)
            suffix = str(origin.get("content_suffix") or ".pdf")
            source_path = self.asset_content_path(origin_id, suffix)
            if source_path.exists():
                self.asset_content_path(derived_id, suffix).write_bytes(source_path.read_bytes())
            excluded = sum(1 for block in derived_blocks if block.get("excluded_reason"))
            meta = {
                **origin,
                "asset_id": derived_id,
                "created_at": iso_now(),
                "derived_from_asset_id": origin_id,
                "unit_policy": resolved,
                **(
                    {
                        "unit_segmentation": language_segmentation_profile(
                            str(resolved.get("language") or "") or None,
                            "\n".join(str(block.get("text") or "") for block in blocks[:8]),
                        )
                    }
                    if resolved["mode"] in {"sentence", "auto"}
                    else {}
                ),
                "pages": pages,
                "block_count": len(derived_blocks),
                "included_block_count": len(derived_blocks) - excluded,
                "excluded_block_count": excluded,
                "source_quality": page_source_quality_report(derived_blocks, pages),
            }
            with self.asset_blocks_path(derived_id).open("w", encoding="utf-8") as handle:
                for block in derived_blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            _json_write(meta_path, meta)
            return self.get_asset(derived_id)

    def _extract_for_ingest(
        self, data: bytes, *, filename: str, kind: str, ocr_mode: str, ocr_languages: str,
        source_illegibility: float, catalog_metadata: dict[str, Any] | None,
        detect_page_numbers: bool = True,
        page_llm: Any = None,
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
        return extract_non_pdf(
            data, filename=filename, kind=kind, catalog=catalog_metadata,
            detect_page_numbers=detect_page_numbers, page_llm=page_llm,
        )

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
            # Read the rows directly: load_blocks() calls get_asset(), which would re-enter this
            # inference (the key is not persisted yet) until the recursion limit, silently failing
            # and repeating that cost, plus its writes, on every read of such an asset.
            meta["main_text_start_inference"] = infer_main_text_start(self._load_block_rows(asset_id), meta.get("pages") or [], outline)
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
        with self._lock:
            self.get_asset(asset_id)
            return self._load_block_rows(asset_id)

    def load_selected_blocks(self, asset_id: str, block_ids: list[str]) -> list[dict[str, Any]]:
        from .source_block_index import load_selected_blocks

        if not block_ids:
            return []
        with self._lock:
            if not isinstance(_json_read(self.asset_meta_path(asset_id)), dict):
                raise KeyError(asset_id)
            return load_selected_blocks(self.asset_blocks_path(asset_id), block_ids)

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
        self._invalidate_asset_metadata_exemplars(asset_id)
        return asset

    def apply_page_estimate(self, asset_id: str, *, words_per_page: int, one_record_per_page: bool) -> dict[str, Any]:
        """Rebuild estimated pages from a reviewer-chosen word length. Printed pages are left alone."""
        from .source_text import (
            MAX_WORDS_PER_PAGE,
            MIN_WORDS_PER_PAGE,
            blocks_from_word_groups,
            pack_paragraphs_by_words,
        )

        if not MIN_WORDS_PER_PAGE <= int(words_per_page) <= MAX_WORDS_PER_PAGE:
            raise ValueError(f"Words per page must be between {MIN_WORDS_PER_PAGE} and {MAX_WORDS_PER_PAGE}.")
        with self._lock:
            asset = self.get_asset(asset_id)
            detection = dict(asset.get("page_number_detection") or {})
            if detection.get("status") != "estimated":
                raise ValueError("Page length applies only when printed page numbers were not found.")
            paragraphs = [
                block for block in self._load_block_rows(asset_id)
                if block.get("type") == "paragraph" and not block.get("excluded_reason") and str(block.get("text") or "").strip()
            ]
            if not paragraphs:
                raise ValueError("This source has no text to paginate.")
            before = " ".join(word for block in paragraphs for word in str(block.get("text") or "").split())
            groups = pack_paragraphs_by_words(paragraphs, int(words_per_page))
            blocks, pages = blocks_from_word_groups(
                groups, extraction_method=str(paragraphs[0].get("extraction_method") or "text"),
            )
            after = " ".join(word for block in blocks for word in str(block.get("text") or "").split())
            if before != after:
                raise ValueError("Repaginating would change the source text.")
            for page in pages:
                page["words_per_page"] = int(words_per_page)
            detection.update({
                "status": "estimated",
                "pattern": "word_count",
                "convention": "word_count",
                "marker_count": len(pages),
                "first": 1 if pages else None,
                "last": len(pages) or None,
                "words_per_page": int(words_per_page),
                "one_record_per_page": bool(one_record_per_page),
                "confirmed": True,
            })
            asset["page_number_detection"] = detection
            asset["page_estimate"] = {
                "words_per_page": int(words_per_page),
                "one_record_per_page": bool(one_record_per_page),
                "confirmed": True,
            }
            asset["pages"] = pages
            asset["page_count"] = len(pages)
            asset["block_count"] = len(blocks)
            asset["included_block_count"] = len(blocks)
            asset["excluded_block_count"] = 0
            tmp = self.asset_blocks_path(asset_id).with_suffix(".blocks.jsonl.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                for block in blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            os.replace(tmp, self.asset_blocks_path(asset_id))
            _json_write(self.asset_meta_path(asset_id), asset)
        self._invalidate_asset_metadata_exemplars(asset_id)
        return asset

    def _invalidate_asset_metadata_exemplars(self, asset_id: str) -> None:
        offset = 0
        while True:
            listing = self.list_builds(offset=offset, limit=100, asset_id=asset_id)
            for build in listing["items"]:
                self.invalidate_metadata_exemplars(str(build["build_id"]))
            offset += len(listing["items"])
            if offset >= listing["total"]:
                break

    def store_source_scans(self, asset_id: str, scans: list[dict[str, Any]], *, source: str, warnings: list[str] | None = None) -> dict[str, Any]:
        """Save bounded provider scan images beside a text source. The transcription stays authoritative."""
        with self._lock:
            asset = self.get_asset(asset_id)
            folder = self.root / "assets" / f"{asset_id}.scans"
            folder.mkdir(parents=True, exist_ok=True)
            stored: list[dict[str, Any]] = []
            for index, scan in enumerate(scans, 1):
                data = scan.get("data")
                if not isinstance(data, (bytes, bytearray)) or not bytes(data).startswith(b"\xff\xd8"):
                    continue
                name = f"{index:04d}.jpg"
                (folder / name).write_bytes(bytes(data))
                stored.append({
                    "file": scan.get("file"),
                    "djvu_page": scan.get("djvu_page"),
                    "image": name,
                    "bytes": len(data),
                })
            labels = [page.get("printed_page_label") for page in asset.get("pages") or []]
            if stored and len(labels) == len(stored):
                for item, label in zip(stored, labels):
                    item["printed_page_label"] = label
            asset["scans"] = {
                "source": source,
                "count": len(stored),
                "pages": stored,
                "warnings": list(warnings or []),
            }
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def scan_image_path(self, asset_id: str, index: int) -> Path:
        asset = self.get_asset(asset_id)
        pages = (asset.get("scans") or {}).get("pages") or []
        if index < 1 or index > len(pages):
            raise KeyError(asset_id)
        name = str(pages[index - 1].get("image") or "")
        path = self.root / "assets" / f"{asset_id}.scans" / name
        if not path.is_file():
            raise KeyError(asset_id)
        return path

    def update_asset_language(self, asset_id: str, *, language: str | None, skipped: bool = False) -> dict[str, Any]:
        """Persist an explicit language decision without rewriting extracted source data."""
        with self._lock:
            asset = self.get_asset(asset_id)
            initial = dict(asset.get("initial_metadata") or {})
            provenance = dict(initial.get("field_provenance") or {})
            if skipped:
                initial.pop("language", None)
                initial["language_status"] = "confirmed_absent"
                provenance["language"] = {
                    "method": "human_review",
                    "confidence": 1.0,
                    "derivation": "human",
                    "status": "confirmed_absent",
                }
            else:
                assert language
                initial["language"] = language
                initial["language_status"] = "human_confirmed"
                provenance["language"] = {
                    "method": "human_review",
                    "confidence": 1.0,
                    "derivation": "human",
                    "status": "human_confirmed",
                }
            initial["field_provenance"] = provenance
            asset["initial_metadata"] = initial
            asset["metadata_revision"] = int(asset.get("metadata_revision") or 0) + 1
            asset["metadata_updated_at"] = iso_now()
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def update_asset_metadata(
        self,
        asset_id: str,
        *,
        metadata: dict[str, Any],
        skip_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Persist explicit source metadata decisions without changing extracted source text."""
        from .source_text import MANIFEST_FIELDS

        allowed = set(MANIFEST_FIELDS) | {"original_language", "document_is_translation"}
        unknown = (set(metadata) | set(skip_fields or [])) - allowed
        if unknown:
            raise ValueError("Unsupported source metadata field(s): " + ", ".join(sorted(unknown)))
        skipped = set(skip_fields or [])
        if skipped & set(metadata):
            raise ValueError("A source metadata field cannot be entered and skipped together.")
        with self._lock:
            asset = self.get_asset(asset_id)
            initial = dict(asset.get("initial_metadata") or {})
            provenance = dict(initial.get("field_provenance") or {})
            for field, value in metadata.items():
                if value in (None, "", []):
                    raise ValueError(f"Metadata field '{field}' needs a value or must be skipped.")
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        raise ValueError(f"Metadata field '{field}' needs a value or must be skipped.")
                initial[field] = value
                provenance[field] = {
                    "method": "human_review",
                    "confidence": 1.0,
                    "derivation": "human",
                    "status": "human_confirmed",
                }
            for field in skipped:
                initial.pop(field, None)
                provenance[field] = {
                    "method": "human_review",
                    "confidence": 1.0,
                    "derivation": "human",
                    "status": "confirmed_absent",
                }
            initial["field_provenance"] = provenance
            asset["initial_metadata"] = initial
            asset["metadata_revision"] = int(asset.get("metadata_revision") or 0) + 1
            asset["metadata_updated_at"] = iso_now()
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def update_voice_assignments(
        self,
        asset_id: str,
        assignments: dict[str, str],
        *,
        reviewer: str = "",
    ) -> dict[str, Any]:
        """Review diarized voice identities without rewriting extracted blocks."""
        with self._lock:
            asset = self.get_asset(asset_id)
            if asset.get("media_kind") != "audio":
                raise ValueError("Voice assignments are available only for audio sources.")
            voices = list(dict.fromkeys(
                str(block.get("speaker") or "").strip()
                for block in self._load_block_rows(asset_id)
                if str(block.get("speaker") or "").strip()
            ))
            unknown = sorted(set(assignments) - set(voices))
            if unknown:
                raise ValueError("Unknown diarized voice(s): " + ", ".join(unknown))
            normalized: dict[str, dict[str, Any]] = {}
            previous = asset.get("voice_assignments")
            previous = previous if isinstance(previous, dict) else {}
            for voice_id in voices:
                name = str(assignments.get(voice_id) or "").strip()
                prior = previous.get(voice_id) if isinstance(previous.get(voice_id), dict) else {}
                normalized[voice_id] = {
                    "voice_id": voice_id,
                    "display_name": name,
                    "authority": "human" if name else "unassigned",
                    "reviewer": reviewer if name else "",
                    "updated_at": iso_now() if name != str(prior.get("display_name") or "") else prior.get("updated_at"),
                }
            asset["voice_assignments"] = normalized
            asset["voice_assignment_revision"] = int(asset.get("voice_assignment_revision") or 0) + 1
            asset["voice_assignments_updated_at"] = iso_now()
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def update_document_layout(self, asset_id: str, plan: dict[str, Any]) -> dict[str, Any]:
        """Persist reviewer-owned document structure and derive page metadata deterministically.

        The immutable physical PDF page remains the source coordinate. The layout plan may
        derive scholarly folios, main-text/bibliography regions, logical left/right pages,
        and alternating thread hints. These reviewer-owned facts outrank later LLM guesses.
        """
        with self._lock:
            from .unit_policy import normalize_policy

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
            unit_policy = normalize_policy(plan.get("unit_policy"))
            from .document_layout_regions import apply_layout_regions, normalize_regions

            regions = normalize_regions(plan.get("layout_regions"), page_count)
            clean_plan = {
                "page_layout": layout, "reading_order": order,
                "main_text_pdf_start": main_pdf, "main_text_printed_start": main_printed,
                "main_text_slot": first_slot if layout == "two_up" else None,
                "bibliography_pdf_start": bib_pdf, "thread_mode": thread_mode,
                "thread_a_language": str(plan.get("thread_a_language") or "").strip() or None,
                "thread_b_language": str(plan.get("thread_b_language") or "").strip() or None,
                "unit_policy": unit_policy,
                "layout_regions": regions,
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
                for key in ("logical_page_slot", "logical_printed_page_label", "deterministic_region_type", "document_thread", "thread_language", "layout_region_id", "layout_region_role", "layout_flow"):
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
            if regions:
                apply_layout_regions(blocks, pages, regions)
            tmp = self.asset_blocks_path(asset_id).with_suffix(".blocks.jsonl.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                for block in blocks:
                    handle.write(json.dumps(block, ensure_ascii=False) + "\n")
            os.replace(tmp, self.asset_blocks_path(asset_id))
            asset["pages"] = pages
            asset["unit_policy"] = unit_policy
            asset["document_layout"] = clean_plan
            asset["document_layout_revision"] = int(asset.get("document_layout_revision") or 0) + 1
            _json_write(self.asset_meta_path(asset_id), asset)
            return asset

    def build_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "build.json"

    def build_records_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "records.jsonl"

    def build_records_db_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "records.sqlite3"

    def build_source_units_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "source_units.jsonl"

    def _set_source_units_projection_state(self, build_id: str, *, dirty: bool) -> None:
        build_path = self.build_path(build_id)
        build = _json_read(build_path)
        if not isinstance(build, dict):
            raise KeyError(build_id)
        state = dict(build.get("source_unit_projection") or {})
        revision = int(state.get("revision") or 0) + (1 if dirty else 0)
        build["source_unit_projection"] = {
            "revision": revision,
            "dirty": dirty,
            "updated_at": iso_now(),
        }
        _json_write(build_path, build)

    def source_unit_projection_dirty(self, build_id: str) -> bool:
        build = self.get_build(build_id)
        return bool((build.get("source_unit_projection") or {}).get("dirty"))

    def load_source_units(self, build_id: str) -> list[dict[str, Any]]:
        """Load authoritative source units, migrating legacy blocks on demand."""
        build = self.get_build(build_id)
        path = self.build_source_units_path(build_id)
        rows: list[dict[str, Any]] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
        blocks = self.load_blocks(str(build["asset_id"]))
        from .corpus_record_restructure import normalize_source_units

        normalized = normalize_source_units(
            rows,
            blocks,
            source_document_id=str(build["asset_id"]),
        )
        if normalized != rows:
            self.save_source_units(build_id, normalized)
        return normalized

    def normalize_source_units(self, build_id: str) -> list[dict[str, Any]]:
        """Public migration helper for builds created before source units existed."""
        return self.load_source_units(build_id)

    def load_active_source_units(self, build_id: str) -> list[dict[str, Any]]:
        return [unit for unit in self.load_source_units(build_id) if unit.get("active")]

    def save_source_units(self, build_id: str, units: list[dict[str, Any]]) -> None:
        """Persist canonical source-unit rows; vectors remain a derived projection."""
        self.get_build(build_id)
        path = self.build_source_units_path(build_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._set_source_units_projection_state(build_id, dirty=True)
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    for unit in units:
                        handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

    def _set_records_projection_state(self, build_id: str, *, dirty: bool) -> None:
        build_path = self.build_path(build_id)
        build = _json_read(build_path)
        if not isinstance(build, dict):
            raise KeyError(build_id)
        state = dict(build.get("records_projection") or {})
        revision = int(state.get("revision") or 0) + (1 if dirty else 0)
        build["records_projection"] = {
            "revision": revision,
            "dirty": dirty,
            "updated_at": iso_now(),
        }
        _json_write(build_path, build)

    def records_projection_dirty(self, build_id: str) -> bool:
        build = self.get_build(build_id)
        return bool((build.get("records_projection") or {}).get("dirty"))

    @contextmanager
    def _records_db(self, build_id: str) -> Iterator[sqlite3.Connection]:
        path = self.build_records_db_path(build_id)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=30)
        try:
            stat = path.stat()
            identity = (stat.st_dev, stat.st_ino, int(connection.execute("PRAGMA schema_version").fetchone()[0]))
            if self._initialized_record_databases.get(build_id) != identity:
                with self._lock:
                    stat = path.stat()
                    identity = (stat.st_dev, stat.st_ino, int(connection.execute("PRAGMA schema_version").fetchone()[0]))
                    if self._initialized_record_databases.get(build_id) != identity:
                        self._initialize_records_db(connection)
                    identity = (stat.st_dev, stat.st_ino, int(connection.execute("PRAGMA schema_version").fetchone()[0]))
                    self._initialized_record_databases[build_id] = identity
                    if len(self._initialized_record_databases) > 64:
                        del self._initialized_record_databases[next(iter(self._initialized_record_databases))]
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_records_db(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS corpus_records (
                record_id TEXT PRIMARY KEY,
                ordinal INTEGER NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_corpus_records_ordinal "
            "ON corpus_records (ordinal)"
        )
        corpus_queue_projection.initialize(connection)
        corpus_document_context.initialize(connection)
        metadata_exemplar_journal.initialize(connection)
        connection.commit()

    @contextmanager
    def _review_read_db(self, build_id: str) -> Iterator[tuple[sqlite3.Connection, MetadataSchema | None, bytes]]:
        self._read_build_snapshot(build_id)
        if not self.build_records_db_path(build_id).exists():
            with self._lock:
                self._bootstrap_records_db(build_id)
        for _attempt in range(3):
            with self._records_db(build_id) as connection:
                schema = self._record_schema(build_id, build_snapshot=self._read_build_snapshot(build_id))
                signature = self._schema_signature(schema)
                identity = self._review_projection_schema_identity(schema)
                connection.execute("BEGIN")
                meta = connection.execute(
                    "SELECT contract,schema_identity FROM review_projection_meta WHERE id=1"
                ).fetchone()
                document = connection.execute(
                    "SELECT contract FROM document_context_state WHERE id=1"
                ).fetchone()
                dirty = connection.execute("SELECT 1 FROM review_projection_dirty LIMIT 1").fetchone()
                if (
                    meta == (corpus_queue_projection.CONTRACT, identity)
                    and document == (corpus_document_context.CONTRACT,)
                    and dirty is None
                ):
                    yield connection, schema, signature
                    return
                connection.rollback()
                with self._lock:
                    connection.execute("BEGIN IMMEDIATE")
                    self._ensure_review_projection(connection, build_id)
                    connection.commit()
        raise RuntimeError("Review projection changed repeatedly during read preparation.")

    def _bootstrap_records_db(self, build_id: str) -> None:
        if self.build_records_db_path(build_id).exists():
            return
        records_path = self.build_records_path(build_id)
        records: list[dict[str, Any]] = []
        if records_path.exists():
            with records_path.open("r", encoding="utf-8") as handle:
                records = [
                    _migrate_status_vocabulary(json.loads(line))
                    for line in handle
                    if line.strip()
                ]
        with self._records_db(build_id) as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO corpus_records(record_id, ordinal, payload) VALUES (?, ?, ?)",
                [
                    (
                        str(record.get("record_id") or ""),
                        ordinal,
                        json.dumps(record, ensure_ascii=False),
                    )
                    for ordinal, record in enumerate(records)
                    if record.get("record_id")
                ],
            )
            self._ensure_review_projection(connection, build_id, rebuild=True)
            connection.commit()

    def build_checkpoint_path(self, build_id: str, name: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or "checkpoint"))
        return self.root / "builds" / build_id / "checkpoints" / f"{safe}.json"

    def save_checkpoint(self, build_id: str, name: str, payload: Any) -> None:
        # Order: repository then checkpoint. Never reacquire repository while
        # holding checkpoint admission. Canonical Record writers are unchanged.
        with self._lock:
            self._read_build_snapshot(build_id)
            lock = self._checkpoint_locks.setdefault(build_id, threading.RLock())
            lock.acquire()
        try:
            _json_write(self.build_checkpoint_path(build_id, name), payload)
            if name == "document_intelligence":
                system_store.mark_semantic_map_dirty(build_id, reason="document_intelligence_checkpoint")
        finally:
            lock.release()

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

    _SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

    def delete_build_files(self, build_id: str) -> None:
        """Remove a build's whole workspace (records, checkpoints, history). Publications are separate files."""
        if not self._SAFE_ID.match(build_id):
            raise KeyError(build_id)
        target = self.root / "builds" / build_id
        with self._lock:
            lock = self._checkpoint_locks.setdefault(build_id, threading.RLock())
            with lock:
                if not target.is_dir():
                    raise KeyError(build_id)
                shutil.rmtree(target)
                self._invalidate_review_records_cache(build_id)

    def delete_asset_files(self, asset_id: str) -> None:
        """Remove a source asset's metadata, extracted blocks and stored bytes."""
        with self._lock:
            if not self._SAFE_ID.match(asset_id) or not self.asset_meta_path(asset_id).exists():
                raise KeyError(asset_id)
            for path in (self.root / "assets").glob(f"{asset_id}.*"):
                if path.is_file():
                    path.unlink()

    def save_build(self, build: dict[str, Any]) -> None:
        build_id = str(build["build_id"])
        with self._lock:
            previous = _json_read(self.build_path(build_id), {})
            dependencies = ("schema", "asset_id", "source_document_id", "editorial_memory_reset_at", "manifest")
            changed = bool(previous) and any(previous.get(key) != build.get(key) for key in dependencies)
            if changed:
                self.invalidate_metadata_exemplars(build_id, schedule=False)
            _json_write(self.build_path(build_id), build)
        if changed:
            self._notify_metadata_projection(build_id)
        # Realtime clients learn that the durable build changed; they still read
        # the build itself through REST.
        note_corpus_build(_operation_from_build(build))

    def _record_schema(
        self, build_id: str, *, build_snapshot: dict[str, Any] | None = None,
    ) -> MetadataSchema | None:
        # Schema lookup needs one atomic JSON snapshot, not a writer reservation.
        build = build_snapshot if build_snapshot is not None else self._read_build_snapshot(build_id)
        raw_schema = build.get("schema") if isinstance(build, dict) else None
        if not isinstance(raw_schema, dict):
            return None
        try:
            return MetadataSchema.model_validate(raw_schema)
        except ValidationError:
            return None

    def get_build(self, build_id: str) -> dict[str, Any]:
        with self._lock:
            return self._read_build_snapshot(build_id)

    def _read_build_snapshot(self, build_id: str) -> dict[str, Any]:
        # Build summaries are atomically replaced; one read retains one complete snapshot.
        build = _json_read(self.build_path(build_id))
        if not isinstance(build, dict):
            raise KeyError(build_id)
        return _migrate_status_vocabulary(build)

    def list_builds(self, *, offset: int = 0, limit: int = 50, asset_id: str | None = None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for path in (self.root / "builds").glob("build-*/build.json"):
            with self._lock:
                build = _json_read(path)
            if isinstance(build, dict) and (not asset_id or build.get("asset_id") == asset_id):
                items.append(_migrate_status_vocabulary(build))
        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        total = len(items)
        return {"items": items[offset:offset + limit], "total": total, "offset": offset, "limit": limit}

    def _invalidate_review_records_cache(self, build_id: str) -> None:
        with self._lock:
            self._review_records_cache.pop(str(build_id), None)

    def _records_snapshot_signature(self, build_id: str) -> tuple[int, int]:
        """Cheap cross-process identity for the interactive SQLite record store."""
        try:
            stat = self.build_records_db_path(build_id).stat()
        except OSError:
            return (0, 0)
        return (int(stat.st_mtime_ns), int(stat.st_size))

    @staticmethod
    def _schema_signature(schema: MetadataSchema | None) -> bytes:
        if schema is None:
            return b""
        try:
            names = "\x1f".join(sorted(str(name) for name in schema.field_names()))
        except AttributeError:
            names = ""
        return hashlib.blake2b(names.encode("utf-8"), digest_size=8).digest()

    @staticmethod
    def _payload_digest(payload: str) -> bytes:
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=16).digest()

    def _remember_fixed_point(self, payload: str, signature: bytes) -> None:
        if len(self._migration_fixed_points) > 400_000:
            self._migration_fixed_points.clear()
        self._migration_fixed_points.add((self._payload_digest(payload), signature))

    def _decode_migrated(
        self, payload: str, schema: MetadataSchema | None, signature: bytes,
    ) -> dict[str, Any]:
        """Decode a stored payload, migrating only when it is not already known to be migrated."""
        record = json.loads(payload)
        if (self._payload_digest(payload), signature) in self._migration_fixed_points:
            return record
        migrated = migrate_record_assertions(_migrate_status_vocabulary(record), schema)
        # Both the stored form and its migrated form are stable under migration (it is
        # idempotent), so neither needs migrating again until the schema changes.
        self._remember_fixed_point(payload, signature)
        self._remember_fixed_point(json.dumps(migrated, ensure_ascii=False), signature)
        return migrated

    def _encode_migrated(
        self, record: dict[str, Any], schema: MetadataSchema | None, signature: bytes,
    ) -> tuple[dict[str, Any], str]:
        """Migrate a record for storage unless its serialized form is already a known fixed point."""
        if "queue_state_version" in record:
            record = dict(record)
            record.pop("queue_state_version")
        payload = json.dumps(record, ensure_ascii=False)
        if (self._payload_digest(payload), signature) in self._migration_fixed_points:
            return record, payload
        migrated = migrate_record_assertions(_migrate_status_vocabulary(record), schema)
        migrated_payload = json.dumps(migrated, ensure_ascii=False)
        self._remember_fixed_point(migrated_payload, signature)
        return migrated, migrated_payload

    def save_records(self, build_id: str, records: list[dict[str, Any]]) -> None:
        """Atomically persist the record store.

        The repository lock serializes writers in this process; the unique temp
        file prevents two writers from ever sharing/truncating the same staging
        file. This is critical while progressive review and metadata checkpoints
        are both active.
        """
        schema = self._record_schema(build_id)
        signature = self._schema_signature(schema)
        encoded = [self._encode_migrated(record, schema, signature) for record in records]
        records = [record for record, _payload in encoded]
        payloads = [payload for _record, payload in encoded]
        path = self.build_records_path(build_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._set_records_projection_state(build_id, dirty=True)
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    for payload in payloads:
                        handle.write(payload + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    # Safe: best-effort temp-file cleanup; see _json_write.
                    pass
            with self._records_db(build_id) as connection:
                if not connection.in_transaction:
                    connection.execute("BEGIN IMMEDIATE")
                metadata_exemplar_journal.invalidate(connection)
                connection.execute("DELETE FROM corpus_records")
                connection.executemany(
                    "INSERT INTO corpus_records(record_id, ordinal, payload) VALUES (?, ?, ?)",
                    [
                        (
                            str(record.get("record_id") or ""),
                            ordinal,
                            payload,
                        )
                        for ordinal, (record, payload) in enumerate(zip(records, payloads))
                        if record.get("record_id")
                    ],
                )
                self._ensure_review_projection(connection, build_id, rebuild=True)
                connection.commit()
            self._set_records_projection_state(build_id, dirty=False)
            self._invalidate_review_records_cache(build_id)
        # Semantic maps are System Data. Invalidate by generation in O(1);
        # rebuilding is deferred until a map is actually requested.
        system_store.mark_semantic_map_dirty(build_id, reason="records_saved")
        self._notify_metadata_projection(build_id)

    def update_record(
        self, build_id: str, record: dict[str, Any], *, expected_queue_version: int | None = None,
    ) -> dict[str, Any]:
        """Persist one validated record without rebuilding the whole JSONL file.

        The SQLite index is authoritative for interactive reads. JSONL is a
        publication projection and is marked dirty until an explicit projection
        refresh completes, so a process crash cannot make divergence invisible.
        Return the committed payload with its transaction's operational version;
        later notifications or writes cannot certify this payload as newer state.
        """
        if "queue_state_version" in record:
            record = dict(record)
            record.pop("queue_state_version")
        record = migrate_record_assertions(
            _migrate_status_vocabulary(record),
            self._record_schema(build_id),
        )
        record_id = str(record.get("record_id") or "")
        if not record_id:
            raise ValueError("A record ID is required.")
        payload = json.dumps(record, ensure_ascii=False)
        with self._lock:
            self._bootstrap_records_db(build_id)
            with self._records_db(build_id) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_review_projection(connection, build_id)
                row = connection.execute(
                    "SELECT ordinal FROM corpus_records WHERE record_id = ?",
                    (record_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(record_id)
                if expected_queue_version is not None:
                    version = connection.execute(
                        "SELECT state_version FROM review_queue_rows WHERE record_id=?", (record_id,),
                    ).fetchone()
                    if version is None or int(version[0]) != expected_queue_version:
                        raise RecordStateConflict("Record changed during preparation; retry the merge against current state.")
                self._set_records_projection_state(build_id, dirty=True)
                connection.execute(
                    "UPDATE corpus_records SET payload = ? WHERE record_id = ?",
                    (payload, record_id),
                )
                corpus_document_context.ensure(connection)
                corpus_queue_projection.update_rows(connection, [(int(row[0]), record)])
                version = connection.execute(
                    "SELECT state_version FROM review_queue_rows WHERE record_id=?", (record_id,),
                ).fetchone()
                if version is None:
                    raise RuntimeError("Committed Record requires a matching review queue row.")
                state_version = int(version[0])
                connection.commit()
            self._remember_fixed_point(payload, self._schema_signature(self._record_schema(build_id)))
            self._invalidate_review_records_cache(build_id)
        # Committed single-record write (not a per-batch build write): readers may hold stale text.
        note_resource_changed("corpus_records")
        system_store.mark_semantic_map_dirty(build_id, reason=f"record_updated:{record_id}")
        self._notify_metadata_projection(build_id)
        return {**record, "queue_state_version": state_version}

    def _notify_metadata_projection(self, build_id: str) -> None:
        callback = self._metadata_projection_callback
        if callback is not None:
            callback(build_id)

    def reconcile_records(
        self, build_id: str, reconcile: Callable[[list[dict[str, Any]]], None], *,
        record_ids: list[str] | None = None, optimistic: bool = False,
        coordination_lock: AbstractContextManager[Any] | None = None,
        is_current: Callable[[], bool] | None = None,
        on_commit: Callable[[], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Reconcile current rows, atomically committing only changed payloads.

        The callback must not call a provider or write other durable state. Optimistic
        callbacks run outside locks and may be retried. An optional reusable
        coordination lock guards capture/commit, including a current-state check
        and post-commit handoff; it is always acquired before the repository lock.
        """
        if optimistic:
            return self._reconcile_records_optimistic(
                build_id, reconcile, record_ids=record_ids, coordination_lock=coordination_lock,
                is_current=is_current, on_commit=on_commit,
            )
        if coordination_lock is not None or is_current is not None or on_commit is not None:
            raise ValueError("Coordination hooks require optimistic reconciliation.")
        schema = self._record_schema(build_id)
        signature = self._schema_signature(schema)
        changed: list[tuple[int, dict[str, Any], str]] = []
        with self._lock:
            self._bootstrap_records_db(build_id)
            with self._records_db(build_id) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_review_projection(connection, build_id)
                if record_ids is None:
                    rows = connection.execute(
                        "SELECT record_id, ordinal, payload FROM corpus_records ORDER BY ordinal"
                    ).fetchall()
                else:
                    rows = [
                        row for record_id in dict.fromkeys(record_ids)
                        if (row := connection.execute(
                            "SELECT record_id, ordinal, payload FROM corpus_records WHERE record_id=?",
                            (record_id,),
                        ).fetchone()) is not None
                    ]
                records = [self._decode_migrated(str(row[2]), schema, signature) for row in rows]
                before = json.loads(json.dumps(records))
                reconcile(records)
                if [record.get("record_id") for record in records] != [row[0] for row in rows]:
                    raise ValueError("Reconciliation cannot change Record identities or topology.")
                for row, original, record in zip(rows, before, records):
                    if record != original:
                        migrated, payload = self._encode_migrated(record, schema, signature)
                        changed.append((int(row[1]), migrated, payload))
                self._write_reconciled_rows(connection, build_id, changed)
                connection.commit()
            if changed:
                self._invalidate_review_records_cache(build_id)
        if changed:
            note_resource_changed("corpus_records")
            system_store.mark_semantic_map_dirty(build_id, reason="records_reconciled")
            self._notify_metadata_projection(build_id)
        return records

    def _write_reconciled_rows(
        self, connection: sqlite3.Connection, build_id: str,
        changed: list[tuple[int, dict[str, Any], str]],
    ) -> None:
        if not changed:
            return
        self._set_records_projection_state(build_id, dirty=True)
        connection.executemany(
            "UPDATE corpus_records SET payload=? WHERE record_id=?",
            [(payload, str(record["record_id"])) for _ordinal, record, payload in changed],
        )
        corpus_document_context.ensure(connection)
        corpus_queue_projection.update_rows(
            connection, [(ordinal, record) for ordinal, record, _payload in changed],
        )

    def _reconcile_records_optimistic(
        self, build_id: str, reconcile: Callable[[list[dict[str, Any]]], None], *,
        record_ids: list[str] | None,
        coordination_lock: AbstractContextManager[Any] | None,
        is_current: Callable[[], bool] | None,
        on_commit: Callable[[], None] | None,
    ) -> list[dict[str, Any]]:
        guard = coordination_lock if coordination_lock is not None else nullcontext()
        with guard, self._lock:
            self._bootstrap_records_db(build_id)
        for _attempt in range(3):
            with self._records_db(build_id) as connection:
                with guard, self._lock:
                    connection.execute("BEGIN IMMEDIATE")
                    self._ensure_review_projection(connection, build_id)
                    schema = self._record_schema(build_id)
                    signature = self._schema_signature(schema)
                    # data_version is comparable only on this same open connection.
                    # It detects external commits even if projection counters reset.
                    version = connection.execute("PRAGMA data_version").fetchone()[0]
                    if record_ids is None:
                        rows = connection.execute(
                            "SELECT record_id, ordinal, payload FROM corpus_records ORDER BY ordinal"
                        ).fetchall()
                    else:
                        rows = [
                            row for record_id in dict.fromkeys(record_ids)
                            if (row := connection.execute(
                                "SELECT record_id, ordinal, payload FROM corpus_records WHERE record_id=?",
                                (record_id,),
                            ).fetchone()) is not None
                        ]
                    connection.commit()
                records = [self._decode_migrated(str(row[2]), schema, signature) for row in rows]
                before = json.loads(json.dumps(records))
                reconcile(records)
                if [record.get("record_id") for record in records] != [row[0] for row in rows]:
                    raise ValueError("Reconciliation cannot change Record identities or topology.")
                changed = []
                for row, original, record in zip(rows, before, records):
                    if record != original:
                        migrated, payload = self._encode_migrated(record, schema, signature)
                        changed.append((int(row[1]), migrated, payload))
                with guard:
                    with self._lock:
                        connection.execute("BEGIN IMMEDIATE")
                        if (
                            connection.execute("PRAGMA data_version").fetchone()[0] != version
                            or self._record_schema(build_id) != schema
                            or (is_current is not None and not is_current())
                        ):
                            connection.rollback()
                            continue
                        self._write_reconciled_rows(connection, build_id, changed)
                        connection.commit()
                        if changed:
                            self._invalidate_review_records_cache(build_id)
                    try:
                        if on_commit is not None:
                            on_commit()
                    finally:
                        if changed:
                            note_resource_changed("corpus_records")
                            system_store.mark_semantic_map_dirty(build_id, reason="records_reconciled")
                            self._notify_metadata_projection(build_id)
            return records
        raise RecordStateConflict("Records changed during validation; retry against the current corpus.")

    def document_context(
        self, build_id: str, records: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Read the current annotation epoch; optionally verify a captured scope."""
        with self._review_read_db(build_id) as (connection, _schema, _signature):
            row = connection.execute("SELECT epoch FROM document_context_state WHERE id=1").fetchone()
            if row is None or not row[0]:
                raise RuntimeError("Document context snapshot requires an initialized annotation epoch.")
            if records is not None and not corpus_document_context.matches(connection, records):
                return None
            return str(row[0])

    def invalidate_metadata_exemplars(self, build_id: str, *, schedule: bool = True) -> None:
        self._bootstrap_records_db(build_id)
        with self._lock, self._records_db(build_id) as connection:
            metadata_exemplar_journal.invalidate(connection)
        if schedule:
            self._notify_metadata_projection(build_id)

    def metadata_exemplar_dirty(self, build_id: str, *, limit: int = 100) -> list[dict[str, str]]:
        with self._record_store_read_db(build_id) as connection:
            return metadata_exemplar_journal.dirty(connection, limit)

    def metadata_exemplar_dirty_count(self, build_id: str) -> int:
        with self._record_store_read_db(build_id) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM metadata_exemplar_dirty").fetchone()[0])

    def complete_metadata_exemplar_dirty(self, build_id: str, items: list[dict[str, Any]]) -> int:
        with self._lock, self._records_db(build_id) as connection:
            return metadata_exemplar_journal.complete(connection, items)

    def metadata_exemplar_state(self, build_id: str) -> tuple[str, str]:
        with self._record_store_read_db(build_id) as connection:
            row = connection.execute("SELECT epoch,context FROM metadata_exemplar_state WHERE singleton=1").fetchone()
            if row is None:
                raise RuntimeError("Metadata exemplar journal requires an initialized state row.")
            return str(row[0]), str(row[1])

    @contextmanager
    def _record_store_read_db(self, build_id: str) -> Iterator[sqlite3.Connection]:
        """Read raw canonical/journal rows without repairing derived projections."""
        self._read_build_snapshot(build_id)
        if not self.build_records_db_path(build_id).exists():
            with self._lock:
                self._bootstrap_records_db(build_id)
        with self._records_db(build_id) as connection:
            connection.execute("BEGIN")
            yield connection

    def save_metadata_exemplar_state(self, build_id: str, epoch: str, context: str) -> None:
        with self._lock, self._records_db(build_id) as connection:
            connection.execute(
                "UPDATE metadata_exemplar_state SET epoch=?,context=? WHERE singleton=1",
                (epoch, context),
            )

    def refresh_records_projection(self, build_id: str) -> None:
        """Rebuild the JSONL publication projection from the transactional index."""
        with self._lock:
            self._bootstrap_records_db(build_id)
            self._set_records_projection_state(build_id, dirty=True)
            with self._records_db(build_id) as connection:
                connection.execute("BEGIN")
                rows = connection.execute(
                    "SELECT payload FROM corpus_records ORDER BY ordinal"
                ).fetchall()
                connection.commit()
            path = self.build_records_path(build_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
            tmp = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    for (payload,) in rows:
                        handle.write(payload + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            with self._records_db(build_id) as connection:
                # A different connection cannot compare SQLite data_version
                # values. Compare the captured payloads under a writer reservation.
                connection.execute("BEGIN IMMEDIATE")
                current_rows = connection.execute(
                    "SELECT payload FROM corpus_records ORDER BY ordinal"
                ).fetchall()
                if current_rows != rows:
                    raise RecordStateConflict("Records changed while refreshing JSONL; retry the projection refresh.")
                self._set_records_projection_state(build_id, dirty=False)

    def get_records(
        self, build_id: str, record_ids: list[str] | tuple[str, ...], *,
        include_queue_version: bool = False,
    ) -> list[dict[str, Any] | None]:
        """Read selected interactive records with indexed SQLite lookups.

        Review opens/prefetches only a handful of records. Reading those rows directly
        avoids the historical O(corpus-size) deserialize/migration cost on every click.
        Missing ids remain None and input order (including duplicates) is preserved.
        """
        requested = [str(record_id) for record_id in record_ids]
        if not requested:
            self._read_build_snapshot(build_id)
            return []
        unique_ids = list(dict.fromkeys(requested))
        found: dict[str, str] = {}
        versions: dict[str, int] = {}
        with self._review_read_db(build_id) as (connection, schema, signature):
            # Fixed-shape indexed queries preserve order and duplicate semantics.
            for record_id in unique_ids:
                row = connection.execute(
                    """SELECT c.payload,q.state_version FROM corpus_records c
                           LEFT JOIN review_queue_rows q ON q.record_id=c.record_id
                           WHERE c.record_id=?"""
                    if include_queue_version else "SELECT payload FROM corpus_records WHERE record_id = ?",
                    (record_id,),
                ).fetchone()
                if row is not None:
                    found[record_id] = str(row[0])
                    if include_queue_version:
                        if row[1] is None:
                            raise RuntimeError("Canonical record has no review projection version.")
                        versions[record_id] = int(row[1])
        decoded: dict[str, dict[str, Any]] = {
            record_id: self._decode_migrated(payload, schema, signature)
            for record_id, payload in found.items()
        }
        for record_id, version in versions.items():
            decoded[record_id]["queue_state_version"] = version
        return [decoded.get(record_id) for record_id in requested]

    def get_record(self, build_id: str, record_id: str, *, include_queue_version: bool = False) -> dict[str, Any]:
        """Read one interactive record without parsing the complete corpus."""
        record = self.get_records(build_id, [str(record_id)], include_queue_version=include_queue_version)[0]
        if record is None:
            raise KeyError(record_id)
        return record

    def record_context(
        self, build_id: str, record_id: str, *, before: int = 6, after: int = 6, max_chars: int = 24000,
    ) -> dict[str, Any]:
        """Text of the records around one record, in document order, for reading in context.

        Only what a reader needs is returned (identity, text, pages, state): never metadata or
        review internals. ``max_chars`` bounds the total text so a request stays small.
        """
        before, after = max(0, min(30, int(before))), max(0, min(30, int(after)))
        with self._record_store_read_db(build_id) as connection:
            row = connection.execute(
                "SELECT ordinal FROM corpus_records WHERE record_id = ?", (str(record_id),)
            ).fetchone()
            if row is None:
                raise KeyError(record_id)
            ordinal = int(row[0])
            previous = connection.execute(
                "SELECT payload FROM corpus_records WHERE ordinal < ? ORDER BY ordinal DESC LIMIT ?",
                (ordinal, before),
            ).fetchall()
            following = connection.execute(
                "SELECT payload FROM corpus_records WHERE ordinal > ? ORDER BY ordinal ASC LIMIT ?",
                (ordinal, after),
            ).fetchall()
        total_budget = max(0, int(max_chars))
        before_budget = total_budget // 2 if previous and following else total_budget
        after_budget = total_budget - before_budget if previous else total_budget
        truncated = False

        def slim(payload: str, budget: int, *, preceding: bool) -> tuple[dict[str, Any] | None, int]:
            nonlocal truncated
            record = json.loads(payload)
            text = str(record.get("text") or "")
            if budget <= 0:
                truncated = True
                return None, budget
            length = min(len(text), budget)
            start = len(text) - length if preceding else 0
            truncated = truncated or length < len(text)
            return {
                "record_id": record.get("record_id"),
                "record_revision": record.get("record_revision"),
                "source_document_id": record.get("source_document_id"),
                "text": text[start:start + length],
                "text_length": len(text),
                "text_truncated": length < len(text),
                "record_character_start": start,
                "record_character_end": start + length,
                "page_start": record.get("page_start"),
                "page_end": record.get("page_end"),
                "review_disposition": record.get("review_disposition"),
            }, budget - length

        # Reserve both sides and keep the text closest to the selected Record.
        near_before, near_after = [], []
        for payload, in previous:
            item, before_budget = slim(payload, before_budget, preceding=True)
            if item:
                near_before.append(item)
        for payload, in following:
            item, after_budget = slim(payload, after_budget, preceding=False)
            if item:
                near_after.append(item)
        return {
            "record_id": record_id,
            "before": list(reversed(near_before)),  # document order, farthest first
            "after": near_after,
            "truncated": truncated,
        }

    def load_records(self, build_id: str) -> list[dict[str, Any]]:
        with self._record_store_read_db(build_id) as connection:
            schema = self._record_schema(build_id)
            rows = connection.execute(
                "SELECT payload FROM corpus_records ORDER BY ordinal"
            ).fetchall()
        signature = self._schema_signature(schema)
        records = [self._decode_migrated(payload, schema, signature) for (payload,) in rows]
        for record in records:
            if any(
                isinstance(status, dict) and status.get("recheck")
                for status in (record.get("metadata_field_status") or {}).values()
            ):
                _scrub_canonical_transport(record)
        return records

    def select_review_queue(
        self, records: list[dict[str, Any]], filters: QueueFilter, *, offset: int, limit: int,
    ) -> QueueSelection:
        """Share bounded selections across transports for repository-owned snapshots.

        Caller-owned lists remain uncached: their contents may change in place.
        Evicted snapshots also use the pure selector without retaining new cache entries.
        """
        with self._lock:
            owned = any(snapshot is records for _signature, snapshot in self._review_records_cache.values())
        return select_queue(
            records, filters, offset=offset, limit=limit,
            cache=self._queue_selection_cache if owned else None,
        )

    def _ensure_review_projection(
        self, connection: sqlite3.Connection, build_id: str, *, rebuild: bool = False,
    ) -> None:
        corpus_document_context.ensure(connection)
        schema = self._record_schema(build_id)
        signature = self._schema_signature(schema)
        identity = self._review_projection_schema_identity(schema)
        corpus_queue_projection.ensure(
            connection, identity, lambda payload: self._decode_migrated(payload, schema, signature),
            rebuild=rebuild,
        )

    @staticmethod
    def _review_projection_schema_identity(schema: MetadataSchema | None) -> str:
        return hashlib.sha256(
            json.dumps(schema.model_dump(mode="json") if schema else None, sort_keys=True).encode()
        ).hexdigest()

    def projected_review_page(
        self, build_id: str, filters: QueueFilter, *, offset: int = 0, limit: int = 50,
        cursor: str | None = None, direction: str = "forward", include_facets: bool = False,
    ) -> dict[str, Any]:
        with self._review_read_db(build_id) as (connection, schema, signature):
            selected, page = corpus_queue_projection.select(
                connection, build_id, filters, offset=offset, limit=limit, cursor=cursor, direction=direction,
            )
            payloads = []
            for record_id, ordinal, version in selected:
                payload = connection.execute("SELECT payload FROM corpus_records WHERE record_id=?", (record_id,)).fetchone()
                if payload is None:
                    raise RuntimeError("Review projection references a missing canonical record.")
                payloads.append((payload[0], ordinal, version))
            if include_facets:
                page["metadata_values"] = corpus_queue_projection.facets(connection)
        items = []
        for payload, ordinal, version in payloads:
            record = corpus_queue_projection._transport_record(self._decode_migrated(payload, schema, signature))
            record["topology_index"] = int(ordinal)
            record["topology_count"] = page["topology_count"]
            record["queue_state_version"] = int(version)
            _decorate_review_state(record)
            _present_for_reviewer(record)
            items.append(record)
        page["items"] = items
        return page

    def review_metadata_facets(self, build_id: str, fields: list[str] | None = None) -> dict[str, list[str]]:
        with self._review_read_db(build_id) as (connection, _schema, _signature):
            return corpus_queue_projection.facets(connection, fields)

    def review_build_aggregates(self, build_id: str, *, automation_running: bool) -> dict[str, Any]:
        with self._review_read_db(build_id) as (connection, _schema, _signature):
            return corpus_queue_projection.build_aggregates(connection, automation_running)

    def rebuild_review_queue(self, build_id: str) -> dict[str, Any]:
        self.get_build(build_id)
        with self._lock:
            self._bootstrap_records_db(build_id)
            with self._records_db(build_id) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._ensure_review_projection(connection, build_id, rebuild=True)
                _, page = corpus_queue_projection.select(
                    connection, build_id, QueueFilter(), offset=0, limit=0, cursor=None, direction="forward",
                )
                return page

    def review_queue_summary(self, build_id: str, record_id: str, review_queue: str | None = None) -> tuple[dict[str, int], dict[str, Any] | None]:
        with self._review_read_db(build_id) as (connection, schema, signature):
            _, page = corpus_queue_projection.select(
                connection, build_id, QueueFilter(), offset=0, limit=0, cursor=None, direction="forward",
            )
            next_id = corpus_queue_projection.next_pending(connection, record_id, review_queue)
            if next_id is None:
                return page["queue_counts"], None
            payload = connection.execute("SELECT payload FROM corpus_records WHERE record_id=?", (next_id,)).fetchone()
            if payload is None:
                raise RuntimeError("Selected review queue Record is missing from its canonical snapshot.")
        record = corpus_queue_projection._transport_record(self._decode_migrated(payload[0], schema, signature))
        _decorate_review_state(record)
        _present_for_reviewer(record)
        return page["queue_counts"], record

    def page_records(self, build_id: str, *, offset: int = 0, limit: int = 50, needs_review: bool | None = None, disposition: str | None = None, metadata_incomplete: bool | None = None, source_problem: bool | None = None, review_queue: str | None = None, query: str = "", cursor: str | None = None, direction: str = "forward") -> dict[str, Any]:
        """REST's composite review page: full presented Records, queue counts and observed values.

        Reads the transactional index so review pagination sees interactive
        updates immediately. Structural edits intentionally use load_records().
        """
        filters = QueueFilter(
            needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete,
            source_problem=source_problem, review_queue=review_queue, query=query,
        )
        return self.projected_review_page(
            build_id, filters, offset=offset, limit=limit, cursor=cursor, direction=direction, include_facets=True,
        )

    def review_records(self, build_id: str) -> list[dict[str, Any]] | None:
        """Read-only parsed snapshot for review paging, cached across HTTP requests.

        Queue selections may reuse this immutable snapshot across page navigation.
        Record writes replace the snapshot, invalidating selections by identity.
        """
        self.get_build(build_id)
        if not self.build_records_path(build_id).exists() and not self.build_records_db_path(build_id).exists():
            return None
        with self._lock:
            self._bootstrap_records_db(build_id)
            signature = self._records_snapshot_signature(build_id)
            cached = self._review_records_cache.get(str(build_id))
            if cached is not None and cached[0] == signature:
                # Refresh insertion order to approximate a tiny LRU without another dependency.
                self._review_records_cache.pop(str(build_id), None)
                self._review_records_cache[str(build_id)] = cached
                return cached[1]
        records = self.load_records(build_id)
        with self._lock:
            signature_after = self._records_snapshot_signature(build_id)
            if signature_after == signature:
                self._review_records_cache[str(build_id)] = (signature_after, records)
                while len(self._review_records_cache) > self._review_records_cache_capacity:
                    self._review_records_cache.pop(next(iter(self._review_records_cache)))
        return records

    def publication_path(self, publication_id: str) -> Path:
        """Return the immutable publication path, preserving legacy JSONL snapshots."""
        compressed = self.root / "publications" / f"{publication_id}.jsonl.zst"
        legacy = self.root / "publications" / f"{publication_id}.jsonl"
        if compressed.exists() or not legacy.exists():
            return compressed
        return legacy

    def publication_integrity_path(self, publication_id: str) -> Path:
        """Return the SHA-512 sidecar path for a publication artifact."""
        return self.publication_path(publication_id).with_name(
            f"{self.publication_path(publication_id).name}.sha512"
        )



class PdfCorpusBuildManager(BuildLifecycleMixin, EditorialMemoryMixin, ManifestWorkflowMixin, OperationsMixin, ReviewActionsMixin, EnrichmentRerunsMixin, SchemaProfileMixin, BuildSegmentationExecutionMixin, MetadataEnrichmentExecutionMixin):
    def __init__(self, repository: PdfCorpusRepository | None = None, max_workers: int = 2) -> None:
        self.repo = repository or PdfCorpusRepository()
        self._lock = threading.RLock()
        # Cache/registry admission never acquires the manager or repository writer
        # locks. Release it before I/O or entering manager -> repository order.
        self._cache_lock = threading.RLock()
        self._cancel: set[str] = set()
        # Resolved provider requests may contain server-owned credentials and must
        # never be serialized into build.json. Keep the current execution contract
        # in memory so a reviewer can hot-swap profiles for subsequently scheduled
        # metadata work while the public build manifest remains secret-free.
        self._runtime_requests: dict[str, dict[str, Any]] = {}
        from .metadata_request_coalescer import MetadataRequestCoalescer

        self._metadata_request_coalescer = MetadataRequestCoalescer()
        # Semantic projections are persisted as rebuildable System Data. Per-build
        # locks make generation single-flight so concurrent Record/Work opens join
        # one materialization instead of repeating graph traversal.
        self._semantic_graph_cache: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
        self._semantic_projection_locks: dict[str, threading.RLock] = {}
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="derridai-pdf-corpus")
        # Conventions confirmed independently in several builds; see enrichment_cycles.
        self._global_learning = GlobalLearningStore(self.repo.root / "global_learning.json")
        # Semantic metadata memory is derived and best-effort. The Chroma client is
        # opened lazily only when reviewed exemplars actually exist for retrieval.
        self._progressive_metadata_index = ChromaMetadataExemplarIndex()
        self._progressive_metadata_warning_builds: set[str] = set()
        self._metadata_projection_lock = threading.RLock()
        self._metadata_schedule_lock = threading.RLock()
        self._metadata_scheduled: set[str] = set()
        self._metadata_reschedule: set[str] = set()
        self.repo._metadata_projection_callback = self._schedule_metadata_exemplar_projection
        self._progressive_metadata_index.on_recreated = self._invalidate_all_metadata_exemplar_scopes
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

    def _persist_preparation_records(
        self, build_id: str, base: list[dict[str, Any]], workers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge optional preparation without replacing the canonical Record set."""
        baseline = {str(row["record_id"]): row for row in base}
        allowed = self._allowed_fields(build_id)
        for worker in workers:
            record_id = str(worker["record_id"])
            if record_id not in baseline:
                raise ValueError("Preparation cannot introduce a new Record identity.")
            for attempt in range(3):
                with self._lock:
                    live = self.repo.get_records(build_id, [record_id], include_queue_version=True)[0]
                    if live is None:
                        break
                    merged = _merge_preparation_snapshot(baseline[record_id], live, worker, allowed)
                    if merged == live:
                        break
                    try:
                        self.repo.update_record(
                            build_id, merged, expected_queue_version=int(live["queue_state_version"]),
                        )
                    except RecordStateConflict:
                        if attempt == 2:
                            raise
                        continue
                    except KeyError:
                        if self.repo.get_records(build_id, [record_id])[0] is None:
                            break
                        raise
                    break
        return self.repo.load_records(build_id)

    def _run_document_intelligence(
        self,
        build_id: str,
        records: list[dict[str, Any]],
        manifest: dict[str, Any],
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Refresh all text-bound linguistic projections without changing scholarly authority."""
        context_epoch = self.repo.document_context(build_id, records)
        analysis_id = uuid.uuid4().hex
        schema = self._schema_for(build_id)
        language = str(manifest.get("language") or "")
        annotation_results = [
            annotate_record(record, schema, language=language)
            for record in records
        ]
        linguistic_annotations = annotation_run_summary(annotation_results)
        build = self.repo.get_build(build_id)
        build["linguistic_annotations"] = linguistic_annotations
        self.repo.save_build(build)
        try:
            analysis = analyze_document(
                records,
                source_document_id=str(self.repo.get_build(build_id).get("asset_id") or build_id),
                language=language,
                request=request,
            )
            analysis["analysis_id"] = analysis_id
            analysis["document_context_epoch"] = context_epoch
            if context_epoch is None or self.repo.document_context(build_id) != context_epoch:
                analysis["stale"] = True
                analysis["warnings"] = [
                    *(analysis.get("warnings") or []),
                    "Documentary text, source bindings, or topology changed during analysis; reanalyse the current scope.",
                ]
            projection_counts = project_annotations_to_records(records, analysis)
            self.repo.save_checkpoint(build_id, "document_intelligence", analysis)
            semantic_graph = build_semantic_content_graph(
                records, analysis, schema=schema,
                registry=build_registry(self.repo, build_id, schema=schema, records=records),
            )
            self.repo.save_checkpoint(build_id, "semantic_content_graph", semantic_graph)
            build = self.repo.get_build(build_id)
            build["document_intelligence"] = {
                "status": analysis.get("status"),
                "profile": analysis.get("profile"),
                "selected_provider": analysis.get("selected_provider"),
                "provider": analysis.get("provider"),
                "provider_version": analysis.get("provider_version"),
                "model": analysis.get("model"),
                "capabilities": analysis.get("capabilities") or [],
                "entity_clusters": len(analysis.get("entity_clusters") or []),
                "characters": len(analysis.get("characters") or []),
                "entity_mentions": projection_counts.get("entity_mentions", 0),
                "quotations": projection_counts.get("quotations", 0),
                "events": projection_counts.get("events", 0),
                "model_artifacts": analysis.get("model_artifacts") or [],
                "warnings": analysis.get("warnings") or [],
                "reason": analysis.get("reason"),
                "text_sha256": analysis.get("text_sha256"),
                "document_context_epoch": context_epoch,
                "stale": bool(analysis.get("stale")),
                "analysis_id": analysis_id,
            }
            build["semantic_content_graph"] = semantic_graph.get("summary") or {}
            self.repo.save_build(build)
            for warning in analysis.get("warnings") or []:
                self._append_warning(build_id, str(warning))
            return analysis
        except Exception as exc:  # noqa: BLE001 - optional derived analysis must not fail corpus work
            for record in records:
                record.pop("document_intelligence", None)
            self._append_warning(
                build_id,
                f"Document intelligence was unavailable; corpus work continued without it ({exc}).",
            )
            build = self.repo.get_build(build_id)
            build["document_intelligence"] = {
                "status": "unavailable",
                "profile": str(request.get("document_intelligence_profile") or "scholarly"),
                "selected_provider": str(request.get("document_nlp_provider") or "auto"),
                "reason": str(exc),
                "document_context_epoch": context_epoch,
                "analysis_id": analysis_id,
            }
            self.repo.save_checkpoint(build_id, "document_intelligence", build["document_intelligence"])
            self.repo.save_build(build)
            return dict(build["document_intelligence"])

    def rerun_document_intelligence(self, build_id: str) -> dict[str, Any]:
        """Recompute text-bound annotations and the graph after review/text changes."""
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        preparation_base = json.loads(json.dumps(records))
        manifest = build.get("manifest") if isinstance(build.get("manifest"), dict) else {}
        request = build.get("request") if isinstance(build.get("request"), dict) else {}
        self._run_document_intelligence(build_id, records, manifest, request)
        self._persist_preparation_records(build_id, preparation_base, records)
        graph = self.semantic_content_graph(build_id)
        return {
            "document_intelligence": self.document_intelligence(build_id),
            "semantic_content_graph": graph,
        }

    def _document_intelligence_for_records(
        self,
        build_id: str,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        value = self.repo.load_checkpoint(build_id, "document_intelligence", {})
        if not isinstance(value, dict):
            return {}
        current_text, _ = document_text_for_records(records)
        current_sha256 = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
        context_epoch = self.repo.document_context(build_id, records)
        return {
            **value,
            "stale": bool(
                value.get("stale")
                or (value.get("text_sha256") and value.get("text_sha256") != current_sha256)
                or (
                    value.get("status") == "ok"
                    and (
                        context_epoch is None
                        or value.get("document_context_epoch") != context_epoch
                    )
                )
            ),
            "current_text_sha256": current_sha256,
        }

    def document_intelligence(self, build_id: str) -> dict[str, Any]:
        """Return the retained annotation run and whether current text has made it stale."""
        self.repo.get_build(build_id)
        return self._document_intelligence_for_records(
            build_id,
            self.repo.load_records(build_id),
        )

    def _semantic_projection_lock(self, build_id: str) -> threading.RLock:
        with self._cache_lock:
            return self._semantic_projection_locks.setdefault(str(build_id), threading.RLock())

    @staticmethod
    def _semantic_projection_audience() -> str:
        """Stable reviewer key for blind-review-safe derived projections."""
        return str(current_reviewer.get() or "")

    def _materialize_semantic_projections(self, build_id: str) -> tuple[int, dict[str, Any]]:
        """Materialize graph/Record/node/Work views once for the current generation.

        The hot read path checks only System Data state and projection rows. Whole-
        build loading, identity resolution, term folding and relationship indexing
        happen here only after an explicit invalidation.
        """
        lock = self._semantic_projection_lock(build_id)
        audience = self._semantic_projection_audience()
        with lock:
            state = system_store.semantic_map_state(build_id)
            generation = int(state["generation"])
            existing = system_store.get_semantic_map_projection(
                "graph", build_id, build_id, audience=audience
            )
            if (
                not state.get("dirty")
                and existing is not None
                and int(existing.get("generation") or 0) == generation
            ):
                graph = existing["payload"]
                with self._cache_lock:
                    self._semantic_graph_cache[(build_id, audience)] = (generation, graph)
                return generation, graph

            records = [json.loads(json.dumps(row)) for row in self.repo.load_records(build_id)]
            for row in records:
                _present_for_reviewer(row)
            analysis = self._document_intelligence_for_records(build_id, records)
            schema = self._schema_for(build_id)
            graph = build_semantic_content_graph(
                records,
                analysis,
                schema=schema,
                registry=build_registry(self.repo, build_id, schema=schema, records=records),
            )
            record_maps, node_maps, work_maps = build_semantic_map_projections(
                graph,
                records,
                analysis=analysis,
            )

            work_by_record = {
                str(row.get("record_id") or ""): str(
                    row.get("work") or row.get("document_title") or ""
                ).strip()
                for row in records
            }
            projection_rows: list[dict[str, Any]] = [{
                "scope_type": "graph",
                "scope_id": build_id,
                "build_id": build_id,
                "generation": generation,
                "audience": audience,
                "payload": graph,
            }]
            projection_rows.extend(
                {
                    "scope_type": "record",
                    "scope_id": record_id,
                    "build_id": build_id,
                    "generation": generation,
                    "audience": audience,
                    "work": work_by_record.get(record_id) or None,
                    "payload": payload,
                }
                for record_id, payload in record_maps.items()
            )
            projection_rows.extend(
                {
                    "scope_type": "node",
                    "scope_id": node_id,
                    "build_id": build_id,
                    "generation": generation,
                    "audience": audience,
                    "payload": payload,
                }
                for node_id, payload in node_maps.items()
            )
            projection_rows.extend(
                {
                    "scope_type": "work",
                    "scope_id": work,
                    "build_id": build_id,
                    "generation": generation,
                    "audience": audience,
                    "work": work,
                    "payload": payload,
                }
                for work, payload in work_maps.items()
            )
            system_store.put_semantic_map_projections(projection_rows)

            with self._cache_lock:
                self._semantic_graph_cache[(build_id, audience)] = (generation, graph)
            system_store.mark_semantic_map_clean(build_id, generation)
            return generation, graph

    def _semantic_projection(
        self,
        build_id: str,
        scope_type: str,
        scope_id: str,
    ) -> dict[str, Any]:
        audience = self._semantic_projection_audience()
        state = system_store.semantic_map_state(build_id)
        generation = int(state["generation"])
        row = system_store.get_semantic_map_projection(
            scope_type, scope_id, build_id, audience=audience
        )
        if (
            not state.get("dirty")
            and row is not None
            and int(row.get("generation") or 0) == generation
        ):
            return row["payload"]

        self._materialize_semantic_projections(build_id)
        state = system_store.semantic_map_state(build_id)
        row = system_store.get_semantic_map_projection(
            scope_type, scope_id, build_id, audience=audience
        )
        if (
            row is not None
            and int(row.get("generation") or 0) == int(state["generation"])
        ):
            return row["payload"]
        # A concurrent write may have invalidated the just-built generation.
        # Rebuild once against the new generation rather than returning "not available".
        self._materialize_semantic_projections(build_id)
        state = system_store.semantic_map_state(build_id)
        row = system_store.get_semantic_map_projection(
            scope_type, scope_id, build_id, audience=audience
        )
        if row is None or int(row.get("generation") or 0) != int(state["generation"]):
            raise KeyError(scope_id)
        return row["payload"]

    def _current_semantic_graph(
        self, build_id: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        """Compatibility helper for callers that still need graph + source inputs.

        New map reads do not use this method: they read persisted projections.
        """
        graph = self._semantic_projection(build_id, "graph", build_id)
        records = [json.loads(json.dumps(row)) for row in self.repo.load_records(build_id)]
        for row in records:
            _present_for_reviewer(row)
        return graph, records, self.document_intelligence(build_id)

    def record_semantic_map(self, build_id: str, record_id: str) -> dict[str, Any]:
        """Persisted bounded semantic map centred on one Record."""
        self.repo.get_build(build_id)
        return self._semantic_projection(build_id, "record", record_id)

    def semantic_graph_node(self, build_id: str, node_id: str) -> dict[str, Any]:
        """Persisted node neighbourhood from the current semantic generation."""
        self.repo.get_build(build_id)
        return self._semantic_projection(build_id, "node", node_id)

    def work_semantic_map(self, build_id: str, work: str) -> dict[str, Any]:
        """Visual Work-map sources projected from the canonical semantic graph."""
        self.repo.get_build(build_id)
        return self._semantic_projection(build_id, "work", work)

    def semantic_content_graph(self, build_id: str) -> dict[str, Any]:
        """Return the current persisted semantic graph without rebuilding on read."""
        self.repo.get_build(build_id)
        return self._semantic_projection(build_id, "graph", build_id)

    def semantic_content_graph_view(self, build_id: str, **params: Any) -> dict[str, Any]:
        """Bounded, filterable slice of the persisted current graph."""
        graph = self._semantic_projection(build_id, "graph", build_id)
        return semantic_content_graph_view(graph, **params)

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

    def _project_metadata_exemplars_best_effort(self, build_id: str) -> dict[str, Any]:
        """Project reviewed metadata without making human review depend on Chroma.

        The durable SQLite outbox is written before this method is scheduled.
        Projection failures therefore remain dirty for startup/next-review retry
        instead of escaping through executors that run submitted work inline or
        otherwise coupling review success to vector availability.
        """
        try:
            result = self._project_metadata_exemplars(build_id)
            record_projection_result(build_id)
            return result
        except Exception as exc:
            self._report_metadata_projection_failure(build_id, exc)
            return {
                "scope_id": build_id,
                "skipped": False,
                "projected": False,
                "error": str(exc),
            }

    def _report_metadata_projection_failure(self, build_id: str, exc: Exception) -> None:
        record_projection_result(build_id, f"{type(exc).__name__}: {exc}")
        self._append_warning(
            build_id,
            "Metadata exemplar projection is pending. Reviewed metadata was saved; "
            "only the rebuildable semantic example index could not be refreshed. "
            "This projection failure does not block review or publication. Check "
            "vector-store and embedding-provider health; DerridAI will retry the "
            "derived index.",
        )

    def _schedule_metadata_exemplar_projection(self, build_id: str) -> None:
        # Review durability never depends on Chroma. The SQLite outbox is committed
        # first; projection runs best-effort and an unacknowledged item is retried
        # after restart or the next review in this build.
        with self._metadata_schedule_lock:
            if build_id in self._metadata_scheduled:
                self._metadata_reschedule.add(build_id)
                return
            self._metadata_scheduled.add(build_id)
        try:
            self._executor.submit(self._drain_metadata_exemplar_projection, build_id)
        except RuntimeError as exc:
            with self._metadata_schedule_lock:
                self._metadata_scheduled.discard(build_id)
            self._report_metadata_projection_failure(build_id, exc)

    def _drain_metadata_exemplar_projection(self, build_id: str) -> None:
        result: dict[str, Any] = {}
        try:
            result = self._project_metadata_exemplars_best_effort(build_id)
        finally:
            with self._metadata_schedule_lock:
                requested = build_id in self._metadata_reschedule
                self._metadata_reschedule.discard(build_id)
                self._metadata_scheduled.discard(build_id)
        if not result.get("error") and (requested or result.get("pending")):
            self._schedule_metadata_exemplar_projection(build_id)

    def _recover_metadata_exemplar_projections(self) -> None:
        try:
            build_ids = dirty_metadata_exemplar_build_ids(self.repo)
        except Exception as exc:
            record_projection_result("recovery", type(exc).__name__)
            logger.error(
                "Metadata exemplar recovery is pending (%s); inspect operational storage. Canonical review remains available.",
                type(exc).__name__,
            )
            return
        record_projection_result("recovery")
        for build_id in build_ids:
            self._schedule_metadata_exemplar_projection(build_id)

    def _invalidate_all_metadata_exemplar_scopes(self) -> None:
        offset = 0
        while True:
            listing = self.repo.list_builds(offset=offset, limit=100)
            for build in listing["items"]:
                self.repo.invalidate_metadata_exemplars(str(build["build_id"]))
            offset += len(listing["items"])
            if offset >= listing["total"]:
                break











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

    def _review_registry(self, build_id: str, record: dict[str, Any] | None, schema: MetadataSchema | None) -> SemanticIdentityRegistry | None:
        """Reviewed aliases for the build plus the Record's own analysis; None if neither can be read."""
        if record is None:
            return None
        try:
            return review_registry(self.repo, build_id, record, schema)
        except (KeyError, RuntimeError):
            return registry_for_record(record)

    def _record_human_llm_feedback(self, build_id: str, field: str, prior_value: Any, new_value: Any, prior_status: dict[str, Any] | None, record: dict[str, Any] | None = None, equivalence: ValueEquivalenceResult | None = None) -> None:
        """Score a reviewer's decision against the model value it replaced.

        ``equivalence`` is computed once at the review boundary. An equivalent surface edit
        is an acceptance; only a ``different`` value is a correction and becomes a remembered
        rejection; an ``unknown`` one is neutral and teaches nothing either way.
        """
        info = prior_status or {}
        method = str(info.get("method") or "")
        state = str(info.get("status") or "")
        if "llm" not in method and state != "model_inferred":
            return
        try:
            schema: MetadataSchema | None = self._schema_for(build_id)
        except (KeyError, ValueError):
            schema = None  # without the build's policy, values compare exactly
        if info.get("blind") and info.get("model") and record is not None:
            sealed = self._ledger.sealed_value(build_id, str(record.get("record_id") or ""), field)
            blind = compare_field_values(schema, field, sealed, new_value, record=record, registry=self._review_registry(build_id, record, schema))
            self._ledger.append(BLIND_LABEL, model=str(info["model"]), field=field, build_id=build_id, record_id=str(record.get("record_id") or ""), value=sealed, new_value=new_value, agreed=blind.same, severity=None if blind.same else error_severity(sealed, new_value), **blind.audit(), **(info.get("conditions") or {}))
            record.setdefault("blind_reveals", {})[field] = sealed  # now that they have decided, the reviewer may see it
            return
        if equivalence is None:
            equivalence = compare_field_values(schema, field, prior_value, new_value, record=record, registry=self._review_registry(build_id, record, schema))
        relation = equivalence.relation
        kept = equivalence.same
        if info.get("model"):
            if relation == "unknown":
                kind = UNRESOLVED
            else:
                kind = ACCEPTED if kept else (REJECTED if new_value in (None, "", []) else CORRECTED)
            self._ledger.append(kind, model=str(info["model"]), field=field, build_id=build_id, record_id=str((record or {}).get("record_id") or ""), confidence=info.get("confidence"), autofilled=bool(info.get("autofilled")), value=prior_value, new_value=new_value, severity=None if kept or relation == "unknown" else error_severity(prior_value, new_value), surface_changed=relation != "exact", **equivalence.audit(), **(info.get("conditions") or {}))
        if relation == "unknown":
            return
        if record is not None and not kept and prior_value not in (None, "", []):
            # Remembered: the next pass is shown this as a value people turned down, and it lowers the
            # model's blended confidence on this field through the ledger.
            rejections = [r for r in record.get("llm_rejections") or [] if isinstance(r, dict)]
            rejections.append({"field": field, "rejected_value": prior_value, "chosen_value": new_value, "model": info.get("model"), "at": iso_now(), **equivalence.audit()})
            record["llm_rejections"] = rejections[-40:]
        family = next((name for name, fields in (schema or self._schema_for(build_id)).family_fields().items() if field in fields), None)
        if not family:
            return
        key = "human_accepted_fields" if kept else "human_corrected_fields"
        with self._lock, self.repo._lock:
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
                if kept:
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
        with self._lock, self.repo._lock:
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
        with self._lock, self.repo._lock:
            build = self.repo.get_build(build_id)
            warnings = list(build.get("warnings") or [])
            if message not in warnings:
                warnings.append(message)
            build["warnings"] = warnings[-100:]
            self.repo.save_build(build)

    def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None:
        if not build_id:
            return
        with self._lock, self.repo._lock:
            build = self.repo.get_build(build_id)
            metrics = dict(build.get("llm_metrics") or {})
            metrics[key] = int(metrics.get(key) or 0) + int(amount)
            build["llm_metrics"] = metrics
            self.repo.save_build(build)

    def page_marker_chooser(self, request: dict[str, Any]) -> Any:
        """A callable that asks the configured model which candidate lines are printed page numbers."""

        def ask(candidates: list[dict[str, Any]]) -> list[int]:
            listing = "\n".join(
                f'{c["id"]}: "{c["text"]}"  (before: "{c["before"]}" | after: "{c["after"]}")' for c in candidates
            )
            prompt = (
                "Below are short lines from a plain-text source, each with the line before and after it. "
                "Choose the lines that are PRINTED PAGE NUMBERS (folios or page markers such as 32, [32], "
                "Page 32, - 32 -, xii), which appear once per page in increasing order. Do NOT choose chapter "
                "numbers, list numbers, footnote numbers, dates, years, verse numbers, or lines that are part of "
                "the text. If you are not confident, return an empty list.\n\n"
                f"{listing}\n\nAnswer as JSON: {{\"page_marker_ids\": [ids]}}"
            )
            result = self._chat_json(
                request, prompt, response_model=PageMarkerChoiceModel, max_tokens=1200,
                schema_name="page_marker_choice", attempts=2,
            )
            return [int(i) for i in result.get("page_marker_ids") or []]

        return ask

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
        roles: tuple[str, ...] = ("primary", "review"),
        escalated: bool = False,
    ) -> dict[str, Any]:
        """Generate typed JSON through the shared structured-completion policy.

        Provider-native JSON Schema is requested when supported. Syntax repair,
        cutoff classification, retry prompts, token-budget growth, schema
        validation, and structured-output metrics are centralized in
        complete_structured_json. This method keeps Corpus Builder-specific
        provider escalation, tracing, stage metrics, and cancellation.
        """
        schema = response_model.model_json_schema()
        request_chain: list[tuple[str, dict[str, Any]]] = [("primary", request)] if "primary" in roles else []
        reviewer = request.get("_review_provider")
        if "review" in roles and isinstance(reviewer, dict) and reviewer:
            request_chain.append(("review", reviewer))
        if not request_chain:
            raise LookupError("No review provider is configured for this build.")

        all_failures: list[str] = []
        timed_out = False
        any_truncated = False

        def run_role(
            role: str,
            active_request: dict[str, Any],
            *,
            provider: str,
            model: str,
            base_url: str | None,
            api_key: str | None,
            generation: Any,
            escalating: bool,
        ) -> dict[str, Any]:
            """Run one provider role while keeping trace state scoped to that role."""
            if escalating and build_id:
                self._increment_metric(build_id, "escalations")

            timeout_key = (
                "manifest" if "manifest" in schema_name else
                "reconciliation" if "reconciliation" in schema_name else
                "segmentation" if ("boundar" in schema_name or "segment" in schema_name) else
                "discourse" if "record_discourse" in schema_name else
                "quotation" if "record_quotation" in schema_name else
                "indexing"
            )
            attempt_state: dict[int, tuple[Any, str]] = {}
            capacity_key = provider_capacity_key(
                provider_profile_id=str(active_request.get("provider_profile_id") or "") or None,
                provider=provider,
                base_url=base_url,
                model=model,
            )
            capacity_limit = provider_limit(
                active_request.get("max_concurrent_requests"), default=1, maximum=64
            )

            initial_note = ""
            if escalating:
                initial_note = (
                    "\n\nESCALATION REVIEW: a first-pass model could not produce a valid structured "
                    "answer. Independently perform the task from the supplied source evidence and "
                    "return ONLY one complete JSON object matching the schema."
                )

            def retry_guidance(error: Exception) -> str:
                if "field_evidence" not in str(error):
                    return ""
                return (
                    "The validation error concerns evidence, not the metadata value. For every "
                    "field whose assessment outcome is supported_value and whose schema requires "
                    "evidence, include a field_evidence object with at least one valid current-record "
                    "block_id. Use the block IDs shown in the source context; never invent IDs and "
                    "never omit the evidence object for a supported value."
                )

            def note_metric(name: str, amount: int) -> None:
                if build_id:
                    self._increment_metric(build_id, name, amount)

            def attempt_started(context: StructuredAttemptContext) -> None:
                structured_counter = request.get("_structured_call_counter")
                if isinstance(structured_counter, dict):
                    structured_counter["attempts"] = (
                        int(structured_counter.get("attempts") or 0) + 1
                    )
                if build_id and self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")
                if build_id:
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

                call_token = self._note_llm_call_start(
                    build_id, metric_stage_of(schema_name), provider, model, base_url
                )
                call_id = f"{build_id}:{call_token}" if build_id else ""
                attempt_state[context.attempt] = (call_token, call_id)
                if build_id:
                    self._llm_trace_start(
                        build_id,
                        call_id=call_id,
                        schema_name=schema_name,
                        role=role,
                        attempt=context.attempt,
                        provider=provider,
                        model=model,
                        prompt=context.prompt,
                        response_schema=schema,
                        generation=generation,
                        max_tokens=context.max_tokens,
                    )

            def request_once(context: StructuredAttemptContext) -> str:
                call_token, _ = attempt_state[context.attempt]

                def cancelled() -> bool:
                    return bool(build_id and self._cancelled(build_id))

                def waiting(snapshot: Any) -> None:
                    if build_id:
                        self._increment_metric(build_id, "provider_capacity_waits")

                try:
                    with capacity_coordinator.acquire(
                        "provider_generation",
                        capacity_key,
                        capacity_limit,
                        cancelled=cancelled if build_id else None,
                        on_wait=waiting,
                        priority="foreground" if request.get("_capacity_priority") == "foreground" else "background",
                    ) as permit:
                        if build_id and permit.waited_seconds > 0:
                            self._increment_metric(
                                build_id,
                                "provider_capacity_wait_ms",
                                int(round(permit.waited_seconds * 1000)),
                            )

                        def perform_request() -> str:
                            return self._with_transport_retry(
                                build_id,
                                chat_complete,
                                provider=provider,
                                model=model,
                                base_url=base_url,
                                api_key=api_key,
                                prompt=context.prompt,
                                options=generation,
                                json_mode=True,
                                json_schema=schema,
                                schema_name=schema_name,
                                max_tokens=context.max_tokens,
                                cancelled=(lambda: self._cancelled(build_id)) if build_id else None,
                                timeout_seconds=float(_stage_timeouts(active_request).get(timeout_key, 240)),
                                on_delta=(
                                    (lambda piece, token=call_token: self._note_llm_call_delta(build_id, token, piece))
                                    if build_id
                                    else None
                                ),
                            )

                        if provider == "ollama":
                            ollama_limit = capacity_coordinator.configured_limit(
                                "ollama_runtime",
                                "global",
                                fallback=max(1, int(settings.rag_ollama_max_concurrent)),
                            )

                            def waiting_ollama(snapshot: Any) -> None:
                                if build_id:
                                    self._increment_metric(build_id, "ollama_capacity_waits")

                            with capacity_coordinator.acquire(
                                "ollama_runtime",
                                "global",
                                ollama_limit,
                                cancelled=cancelled if build_id else None,
                                on_wait=waiting_ollama,
                                priority="foreground" if request.get("_capacity_priority") == "foreground" else "background",
                            ) as ollama_permit:
                                if build_id and ollama_permit.waited_seconds > 0:
                                    self._increment_metric(
                                        build_id,
                                        "ollama_capacity_wait_ms",
                                        int(round(ollama_permit.waited_seconds * 1000)),
                                    )
                                return perform_request()
                        return perform_request()
                finally:
                    self._note_llm_call_end(build_id, call_token)

            def validate(value: dict[str, Any]) -> dict[str, Any]:
                parsed = response_model.model_validate(value)
                return parsed.model_dump(mode="json")

            def attempt_finished(outcome: StructuredAttemptOutcome[dict[str, Any]]) -> None:
                if not build_id:
                    return
                _, call_id = attempt_state.pop(outcome.context.attempt, (None, ""))
                if outcome.error is not None:
                    self._llm_trace_finish(
                        build_id,
                        call_id,
                        raw_response=outcome.raw_response,
                        error=f"{type(outcome.error).__name__}: {outcome.error}",
                    )
                    return
                self._llm_trace_finish(
                    build_id,
                    call_id,
                    raw_response=outcome.raw_response,
                    validated_response=outcome.value,
                )

            return complete_structured_json(
                request_once,
                prompt=prompt,
                validate=validate,
                attempts=attempts,
                max_tokens=max_tokens,
                max_token_cap=8192,
                initial_note=initial_note,
                retry_guidance=retry_guidance,
                on_attempt_start=attempt_started,
                on_attempt_finish=attempt_finished,
                on_metric=note_metric,
            )

        for chain_index, (role, active_request) in enumerate(request_chain):
            provider, model, base_url, api_key, generation = _llm_config(active_request)
            try:
                return run_role(
                    role,
                    active_request,
                    provider=provider,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    generation=generation,
                    escalating=chain_index > 0 or escalated,
                )
            except InterruptedError:
                raise
            except StructuredCompletionError as exc:
                failure = exc.last_error or exc
                all_failures.append(f"{role} {provider}/{model}: {failure}")
                timed_out = timed_out or exc.timed_out
                any_truncated = any_truncated or exc.truncated

        raise StructuredOutputError(
            "LLM structured output failed after bounded retry"
            + (" and review-provider escalation" if len(request_chain) > 1 else "")
            + ": " + " | ".join(all_failures),
            failures=all_failures,
            timed_out=timed_out,
            truncated=any_truncated,
        )

    def _document_manifest_call(
        self, session: DocumentManifestSession, request: dict[str, Any], prompt: str, *, max_tokens: int, build_id: str,
    ) -> dict[str, Any]:
        """Ask for the document manifest through the corpus_document_manifest pipeline, one provider role per stage."""

        def invoke(role: str, attempts: int, escalated: bool) -> dict[str, Any]:
            if role not in _provider_roles(request):
                raise LookupError("No review provider is configured for this build.")
            return self._chat_json(
                request, prompt, response_model=DocumentManifestModel, max_tokens=max_tokens,
                schema_name="derridai_document_manifest", attempts=attempts, build_id=build_id,
                roles=(role,), escalated=escalated,
            )

        return session.run(invoke, response_contract="derridai_document_manifest", providers=_provider_roles(request))

    def _record_document_manifest_pipeline(self, build_id: str, session: DocumentManifestSession) -> None:
        """Keep which pipeline ran each analysis beside the manifest, not in it.

        The manifest itself is sent verbatim in metadata-enrichment prompts, so the identity
        lives in its own checkpoint.
        """
        if not build_id or not session.last_path:
            return
        runs = list(self.repo.load_checkpoint(build_id, "document_manifest_pipeline", {}).get("runs") or [])
        runs.append({**session.identity(), "recorded_at": iso_now()})
        self.repo.save_checkpoint(build_id, "document_manifest_pipeline", {"runs": runs[-20:]})

    def _document_manifest(self, asset: dict[str, Any], blocks: list[dict[str, Any]], request: dict[str, Any], build_id: str) -> dict[str, Any]:
        metadata = asset.get("metadata") or {}
        media_kind = str(asset.get("media_kind") or "pdf")
        metadata_label = "PDF metadata" if media_kind == "pdf" else "source metadata"
        metadata_method = "pdf_metadata" if media_kind == "pdf" else "source_metadata"
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
        def excerpt(block: dict[str, Any]) -> str:
            if media_kind == "audio" or block.get("locator_kind") == "time":
                location = block.get("time_label") or f"{block.get('start')}–{block.get('end')} seconds"
                locator = f"audio time={location} speaker={block.get('speaker')!r}"
            elif block.get("page") is not None:
                locator = f"{media_kind} p.{block['page']} label={block.get('printed_page_label')!r}"
            else:
                locator = f"{media_kind} source unit"
            return f"[{block['block_id']} {locator} {block.get('type', 'paragraph')}] {str(block.get('text') or '')[:per_excerpt]}"

        sample_text = "\n".join(excerpt(block) for block in chosen)[:sample_char_budget]
        prompt = f"""You are establishing a source-bound document manifest for an auditable scholarly corpus build.
Use only evidence in the supplied {metadata_label} and source blocks. Use null when unsupported. Never fill bibliographic facts from general knowledge. Distinguish a physical page index from a printed page label. Audio timestamps and source-unit identifiers are not pages. The manifest will be inherited deterministically by generated records, so be conservative.

Source media: {media_kind}
{metadata_label}: {json.dumps(metadata, ensure_ascii=False)}
Filename: {asset.get('filename')}
Reviewer-confirmed document structure (authoritative where present): {json.dumps(reviewed_layout, ensure_ascii=False)}
Strategic whole-document sample:
{sample_text}

Return one JSON object matching the schema. `main_text_start_page` and `main_text_end_page` are physical pages only for PDF/image sources when supported; use null for audio and other media. `document_is_translation` should be null unless the source itself supports that conclusion.
"""
        # One trace per analysis. If the pipeline cannot be resolved no model is asked and the
        # embedded-metadata fallback below applies, with the reason in the build warning.
        session: DocumentManifestSession | None = None
        try:
            session = DocumentManifestSession.open()
            result = self._document_manifest_call(
                session, request, prompt, max_tokens=limits["manifest_num_predict"], build_id=build_id,
            )
        except InterruptedError:
            if session is not None:
                session.finish(cancelled=True)
            raise
        except Exception as exc:
            self._append_warning(build_id, f"Document manifest used {metadata_label.replace(' ', '-')} fallback: {exc}")
            result = DocumentManifestModel(
                title=metadata.get("title") or None,
                document_author=metadata.get("author") or None,
                notes=f"LLM manifest unavailable; values are limited to embedded {metadata_label}.",
            ).model_dump(mode="json")
        if session is not None:
            session.finish()
            self._record_document_manifest_pipeline(build_id, session)
        # Embedded source metadata is a deterministic source assertion. A model
        # may enrich missing bibliography, but must not replace an author
        # explicitly declared by the source file.
        if metadata.get("author"):
            result["document_author"] = str(metadata["author"]).strip()
            result["document_author_source"] = metadata_method
            result["document_author_confidence"] = 1.0
            result["document_author_assertion"] = {
                "field": "document_author",
                "value": result["document_author"],
                "status": "deterministic",
                "method": metadata_method,
                "checked": True,
                "confidence": 1.0,
                "reason": f"Author value was read from embedded {metadata_label}.",
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
        preparation_base = json.loads(json.dumps(records))
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
        records[:] = self._persist_preparation_records(build_id, preparation_base, records)
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
            self._update(build_id, stage="preparing", text_review_available_at=None)
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
            if self.repo.get_build(build_id).get("pause_requested"):
                self._update(build_id, status="cancelled", stage="paused", finished_at=iso_now(), error=None, resumable=True, paused=True, pause_requested=False, retrying_segmentation=False)
            else:
                self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True, paused=False, retrying_segmentation=False)
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
        layout = asset.get("document_layout") if isinstance(asset.get("document_layout"), dict) else {}
        raw_regions = layout.get("layout_regions") if isinstance(layout.get("layout_regions"), list) else []
        if raw_regions:
            from .document_layout_regions import reading_sequence

            blocks = reading_sequence(
                blocks,
                [str(item.get("id")) for item in raw_regions if isinstance(item, dict) and item.get("id")],
            )
        if not blocks:
            raise ValueError("No SourceUnits were extracted from the PDF. Check OCR support and extraction warnings.")

        manifest = self.repo.load_checkpoint(build_id, "manifest") if resume else None
        if not isinstance(manifest, dict):
            manifest = self._document_manifest(asset, blocks, request, build_id)
            if bool(request.get("auto_enrich_work_metadata", True)):
                manifest = self._catalog_enrich_manifest(manifest, request, build_id)
            if isinstance(request.get("work_metadata"), dict) and request["work_metadata"]:
                # Reviewer-supplied, work-wide values travel with the manifest, so they survive resume and edits.
                manifest = {**manifest, "work_metadata": dict(request["work_metadata"])}
            supplied = request.get("document_metadata")
            if isinstance(supplied, dict) and supplied:
                # Supplied because detection on source load could not find them: the reviewer's values outrank
                # model and catalog inference, and are recorded so inherited assertions can say where they came from.
                manifest = {**manifest, **supplied, "reviewer_supplied": dict(supplied)}
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
        topology_policy = request.get("topology_policy") if isinstance(request.get("topology_policy"), dict) else {}
        fixed_unit_records = str(topology_policy.get("mode") or "semantic") == "source_units"
        source_units_per_record = max(1, int(topology_policy.get("source_units_per_record") or 1))
        records_per_page = (
            max(1, int(topology_policy["records_per_page"]))
            if topology_policy.get("records_per_page") is not None
            else None
        )
        page_records = (
            _one_record_per_estimated_page(asset)
            and not fixed_unit_records
            and records_per_page is None
        )
        if fixed_unit_records or page_records or not isinstance(boundaries, list):
            segmentation_clock = time.monotonic()
            if fixed_unit_records:
                from .corpus_segmentation import source_unit_record_boundaries

                boundaries = source_unit_record_boundaries(source_blocks, source_units_per_record)
            elif page_records:
                from .corpus_segmentation import page_record_boundaries

                boundaries = page_record_boundaries(semantic_blocks)
            else:
                boundaries = self._segment(semantic_blocks, manifest, request, build_id)
            self._update(build_id, segmentation_elapsed_ms=int((time.monotonic()-segmentation_clock)*1000))
        if self._cancelled(build_id):
            raise InterruptedError("Corpus build cancelled")
        self._update(build_id, retrying_segmentation=False)
        # Whoever proposed the boundaries (the model, a checkpoint, a heuristic), a record must not
        # start or end mid-sentence. This is deterministic and idempotent, so it also repairs
        # checkpoints written before it existed.
        # The build's own ceiling bounds any join: sentence ends are preferred, never at the cost of the record size
        # the build asked for (the profile's generic limit let a small-record build grow records to 10,500 characters).
        ceiling = _record_sizing_policy(request, self._profile_for(build_id))["absolute_record_chars"]
        segmentation_language = str(
            manifest.get("language")
            or manifest.get("document_language")
            or ""
        ).strip() or None
        sentence_report: dict[str, Any] = {}
        if not page_records and not fixed_unit_records:
            boundaries, sentence_report = snap_boundaries_to_sentences(
                semantic_blocks,
                boundaries,
                hard_max_chars=ceiling,
                language=segmentation_language,
            )
        self._update(
            build_id,
            sentence_boundary_report={key: len(value) for key, value in sentence_report.items()},
            sentence_boundary_language_profile=language_segmentation_profile(
                segmentation_language,
                "\n".join(str(block.get("text") or "") for block in semantic_blocks[:8]),
            ),
        )
        self.repo.save_checkpoint(build_id, "boundaries", boundaries)

        self._update(build_id, stage="constructing_records", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.36))
        records = self.repo.load_records(build_id) if resume and not source_scope_repair else []
        preparation_base = json.loads(json.dumps(records))
        if not records:
            records = _construct_records(asset, source_blocks, boundaries)
            if records_per_page and _can_use_synthetic_record_pages(asset):
                _apply_synthetic_record_pages(records, records_per_page)
            _mark_segmentation_review(records, list(self.repo.get_build(build_id).get("segmentation_unresolved_regions") or []))
            boundary_suspect_count = (
                0
                if fixed_unit_records
                else annotate_boundary_suspects(records, segmentation_language)
            )
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
            nlp_schema = self._schema_for(build_id)
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
            # Records above the absolute ceiling are not a build failure: keep them, flag them
            # for review, and let the reviewer split them (a single block may be larger than
            # any configured ceiling, and a reviewer's small targets are legitimate).
            oversize = {
                str(f.get("record_id")): f for f in topology_validation.get("findings") or []
                if f.get("code") == "topology.over_absolute_limit"
            }
            for record in records:
                found = oversize.get(str(record.get("record_id")))
                if found:
                    record["needs_review"] = True
                    record["review_reason"] = (
                        f"Record is {found['params'].get('chars')} characters, above the "
                        f"{found['params'].get('limit')}-character ceiling; split it during review."
                    )
            current_build = self.repo.get_build(build_id)
            current_build["topology_validation"] = topology_validation
            current_build["topology_quality"] = topology_quality
            current_build["record_sizing_policy"] = sizing_policy
            current_build["topology_policy"] = {
                "mode": "source_units" if fixed_unit_records else "semantic",
                "source_units_per_record": source_units_per_record,
                "records_per_page": records_per_page,
            }
            self.repo.save_build(current_build)
            if not topology_validation.get("valid"):
                raw_issues = [str(issue) for issue in topology_validation.get("issues") or []]
                counts = {issue: raw_issues.count(issue) for issue in dict.fromkeys(raw_issues)}
                issues = [
                    f"{issue} ({count} records)" if count > 1 else issue
                    for issue, count in counts.items()
                ]
                detail = ", ".join(issues or ["unknown topology error"])
                if "topology.over_absolute_limit" in raw_issues:
                    detail += (
                        ". One or more source units exceed the absolute character ceiling; "
                        "choose a finer evidence-unit rule or split the affected unit during review."
                    )
                raise RuntimeError(
                    "Deterministic topology sanity check failed before metadata enrichment: " + detail
                )
            # Optionally clean obvious extraction/layout noise before metadata
            # enrichment. The immutable extracted text remains bound in
            # source_extracted_text and the transformation is revisioned.
            if bool(request.get("auto_clean_text", False)):
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
            self._update(
                build_id, record_count=len(records), boundary_count=len(boundaries),
                topology_persisted_at=self.repo.get_build(build_id).get("topology_persisted_at") or iso_now(),
                text_review_available_at=iso_now(),
            )
            records = self.repo.load_records(build_id)
            preparation_base = json.loads(json.dumps(records))
            # Text review is available; metadata and structural decisions still wait.
            source_projection = SourceEmbeddingProjection(self._progressive_metadata_index.store)
            try:
                provider, model = source_projection.store.default_embedding_spec()
                source_embedding_projection = source_projection.sync(
                    str(asset.get("asset_id") or build_id), source_blocks,
                    provider=provider, model=model, prune=True,
                )
            except Exception as exc:
                source_embedding_projection = {
                    "status": "unavailable", "error": f"{type(exc).__name__}: {exc}"[:300],
                }
                self._append_warning(
                    build_id,
                    "Source-unit semantic indexing is unavailable; canonical source and records remain intact. "
                    + str(source_embedding_projection["error"]),
                )
            current_build = self.repo.get_build(build_id)
            current_build["source_unit_embedding_projection"] = source_embedding_projection
            self.repo.save_build(current_build)
            memory_prefill = (
                prefill_records(records, source_blocks, nlp_schema, self._progressive_metadata_index, build_id=build_id, registry=build_registry(self.repo, build_id, schema=nlp_schema))
                if bool(request.get("memory_prefill", True))
                else {"status": "disabled"}
            )
            if memory_prefill.get("status") == "unavailable":
                self._append_warning(
                    build_id,
                    "Metadata memory could not pre-fill fields (embedding provider or vector store unavailable). "
                    "The build continues without it: " + str(memory_prefill.get("error") or ""),
                )
            current_build = self.repo.get_build(build_id)
            current_build["memory_prefill"] = memory_prefill
            self.repo.save_build(current_build)
        else:
            # Recheck conserved source coverage, not an old readiness timestamp.
            # Reviewed text and split/merge identities remain authoritative.
            sizing_policy = _record_sizing_policy(request, self._profile_for(build_id))
            validation_records = [
                {**record, "text_length": len(str(record.get("text") or ""))}
                for record in records
            ]
            topology_validation = _topology_sanity(validation_records, sizing_policy, source_blocks)
            source_ids = {str(block["block_id"]) for block in source_blocks}
            unknown_source_ids = sorted({
                str(block_id)
                for record in records
                for block_id in record.get("source_block_ids") or []
                if str(block_id) not in source_ids
            })
            if unknown_source_ids:
                topology_validation["valid"] = False
                topology_validation["issues"].append("topology.unknown_source")
                topology_validation["findings"].append({
                    "code": "topology.unknown_source", "severity": "error",
                    "record_id": None, "auto_repairable": False,
                    "params": {"count": len(unknown_source_ids), "block_ids": unknown_source_ids[:50]},
                })
            self._update(
                build_id,
                topology_validation=topology_validation,
                topology_quality=_topology_quality_report(records, source_blocks, sizing_policy, topology_validation),
                record_count=len(records),
                text_review_available_at=iso_now() if topology_validation["valid"] else None,
            )
        records = self._persist_preparation_records(build_id, preparation_base, records)
        preparation_base = json.loads(json.dumps(records))
        guidance = request.get("run_guidance") if isinstance(request.get("run_guidance"), dict) else {}
        for record in records:
            matches = find_guidance_matches(str(record.get("text") or ""), guidance)
            if matches:
                record["metadata_guidance_matches"] = matches
            else:
                record.pop("metadata_guidance_matches", None)

        # Whole-document intelligence runs only after deterministic text cleanup, so
        # its offsets and record-local projections are bound to the exact text that
        # metadata enrichment will see. It is optional and never authoritative.
        self._update(
            build_id,
            stage="document_intelligence",
            record_count=len(records),
            progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.40),
        )
        self._run_document_intelligence(build_id, records, manifest, request)

        records = self._persist_preparation_records(build_id, preparation_base, records)
        trash_quality = self._apply_source_illegibility(
            build_id, records, request, source_quality, asset.get("pages") or [],
        )
        self._update(
            build_id, stage="enriching",
            progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42),
            boundary_count=len(boundaries), record_count=len(records),
            source_problem_count=sum(1 for record in records if record.get("source_quality_issues")),
            trash_quality=trash_quality,
            review_available_at=self.repo.get_build(build_id).get("review_available_at") or iso_now(),
        )

        return records


    def _persist_build_metadata_stage(
        self, build_id: str, metadata_task_total: int, snapshot: dict[str, Any],
        task_name: str, state: str, error_text: str | None,
    ) -> None:
        """Checkpoint one family with Record-targeted persistence and incremental counters.

        The old path reparsed and rewrote the entire corpus on every running/terminal
        family transition. Initial counters are already derived once when enrichment is
        scheduled, so under the manager lock each later callback can move exactly one
        task between counter buckets while updating only the affected Record.
        """
        del error_text  # the snapshot's execution ledger already carries the bounded error text
        record_id = str(snapshot.get("record_id") or "")
        if not record_id:
            return

        counter_for_state = {
            "complete": "metadata_tasks_completed",
            "failed": "metadata_tasks_failed",
            "needs_review": "metadata_tasks_failed",
            "skipped": "metadata_tasks_skipped",
            "running": "metadata_tasks_running",
            "queued": "metadata_tasks_queued",
        }
        with self._lock:
            allowed_fields = self._allowed_fields(build_id)
            prior_state = ""
            applied = False
            copy = json.loads(json.dumps(snapshot))
            copy["metadata_enrichment_state"] = (
                "running"
                if state == "running"
                else str(copy.get("metadata_enrichment_state") or "running")
            )

            def merge_stage(rows: list[dict[str, Any]]) -> None:
                nonlocal prior_state, applied
                if not rows or not _record_source_matches(rows[0], copy):
                    return
                live_record = rows[0]
                row_status = (
                    live_record.get("metadata_stage_status")
                    if isinstance(live_record.get("metadata_stage_status"), dict)
                    else {}
                )
                prior_state = str(
                    row_status.get(task_name)
                    or ("complete" if live_record.get("metadata_complete") else "queued")
                )
                # A sibling may have advanced since this worker's snapshot.
                # Merge only the callback's own status and ledger entry.
                for map_key in ("metadata_stage_status", "metadata_execution_ledger"):
                    live_map = (
                        dict(live_record.get(map_key) or {})
                        if isinstance(live_record.get(map_key), dict)
                        else {}
                    )
                    worker_map = (
                        dict(copy.get(map_key) or {})
                        if isinstance(copy.get(map_key), dict)
                        else {}
                    )
                    if task_name in worker_map:
                        live_map[task_name] = worker_map[task_name]
                    copy[map_key] = live_map
                rows[0] = _merge_enrichment_snapshot(live_record, copy, allowed_fields)
                applied = True

            current = self.repo.reconcile_records(build_id, merge_stage, record_ids=[record_id])
            if not applied:
                if current:
                    logger.warning("Discarded stale initial metadata checkpoint for build %s record %s", build_id, record_id)
                return
            merged = current[0]

            build = self.repo.get_build(build_id)
            updates: dict[str, Any] = {"metadata_tasks_total": metadata_task_total}
            prior_counter = counter_for_state.get(prior_state)
            settled_state = str((merged.get("metadata_stage_status") or {}).get(task_name) or state)
            next_counter = counter_for_state.get(settled_state)
            if prior_counter != next_counter:
                if prior_counter:
                    updates[prior_counter] = max(0, int(build.get(prior_counter) or 0) - 1)
                if next_counter:
                    updates[next_counter] = int(build.get(next_counter) or 0) + 1

            active = [
                item
                for item in (build.get("metadata_active_tasks") or [])
                if not (
                    str(item.get("record_id") or "") == record_id
                    and str(item.get("task") or "") == task_name
                )
            ]
            if settled_state == "running":
                ledger = (
                    merged.get("metadata_execution_ledger")
                    if isinstance(merged.get("metadata_execution_ledger"), dict)
                    else {}
                )
                entry = ledger.get(task_name) if isinstance(ledger.get(task_name), dict) else {}
                active.append({
                    "record_id": record_id,
                    "task": task_name,
                    "started_at": entry.get("started_at"),
                })
            updates["metadata_active_tasks"] = active[:32]
            if settled_state in {"complete", "failed", "needs_review", "skipped"}:
                updates["metadata_last_progress_at"] = iso_now()
            self._update(build_id, **updates)


    def _initialize_build_enrichment(
        self, build_id: str, request: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Recover interrupted work without requeueing completed review-pending passes."""
        updates: dict[str, Any] = {}

        def check_cancelled() -> bool:
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            return True

        def initialize_current(rows: list[dict[str, Any]]) -> None:
            nonlocal updates
            check_cancelled()
            for record in rows:
                enrichment_state = str(record.get("metadata_enrichment_state") or "").strip().casefold()
                if enrichment_state == "complete":
                    record["metadata_enrichment_state"] = "complete"
                else:
                    # Scholarly metadata completeness is not execution completion.
                    # Deterministic/inherited values can satisfy the schema before
                    # this Record's scheduled LLM enrichment pass has run.
                    record["metadata_enrichment_state"] = "queued"
                    record.setdefault("metadata_stage_status", {})
            states = _metadata_family_states(rows)
            updates = {
                "metadata_enriched_count": sum(
                    1 for row in rows if row.get("metadata_enrichment_state") == "complete"
                ),
                "metadata_enrichment_total": len(rows),
                "metadata_concurrency": max(1, min(64, int(request.get("max_concurrent_requests") or 1))),
                "metadata_tasks_total": len(rows) * 3,
                "metadata_tasks_completed": sum(1 for value in states if value == "complete"),
                "metadata_tasks_failed": sum(1 for value in states if value in {"failed", "needs_review"}),
                "metadata_tasks_skipped": sum(1 for value in states if value == "skipped"),
                "metadata_tasks_running": 0,
                "metadata_tasks_queued": sum(1 for value in states if value == "queued"),
                "metadata_active_tasks": [],
            }

        def committed() -> None:
            current = self.repo.get_build(build_id)
            self._update(
                build_id, **updates,
                metadata_started_at=current.get("metadata_started_at") or iso_now(),
                metadata_last_progress_at=iso_now(),
                metadata_settle_requested=bool(current.get("metadata_settle_requested")),
            )

        try:
            return self.repo.reconcile_records(
                build_id, initialize_current, optimistic=True, coordination_lock=self._lock,
                is_current=check_cancelled, on_commit=committed,
            )
        except RecordStateConflict as exc:
            raise RecordStateConflict(
                "Records changed during enrichment queue setup; retry against the current corpus."
            ) from exc

    def _schedule_build_enrichment(
        self, build_id: str, request: dict[str, Any], manifest: dict[str, Any], records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Schedule unfinished passes, not completed passes awaiting scholarly review."""
        records = self._initialize_build_enrichment(build_id, request)
        total = max(1, len(records))
        pending = [
            index for index, record in enumerate(records)
            if record.get("metadata_enrichment_state") != "complete"
        ]
        priority_ids = {str(value) for value in request.get("_priority_record_ids", [])}
        pending.sort(key=lambda index: (0 if str(records[index].get("record_id") or "") in priority_ids else 1, index))
        already_complete = len(records) - len(pending)
        max_workers = max(1, min(64, int(request.get("max_concurrent_requests") or 1)))
        metadata_task_total = len(records) * 3

        def persist_metadata_stage(snapshot: dict[str, Any], task_name: str, state: str, error_text: str | None) -> None:
            self._persist_build_metadata_stage(build_id, metadata_task_total, snapshot, task_name, state, error_text)

        if pending:
            # Records share the bounded family pool. Family checkpoints and
            # completed results persist through targeted SQLite writes; JSONL
            # remains a dirty-tracked projection until explicit refresh/export.
            with (
                ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="pdf-corpus-meta",
                ) as pool,
                ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="pdf-corpus-family",
                ) as family_pool,
            ):
                def submit_record(index: int):
                    record = dict(records[index])
                    previous_text = str(records[index - 1].get("text") or "") if index > 0 else ""
                    next_text = str(records[index + 1].get("text") or "") if index + 1 < len(records) else ""
                    return pool.submit(
                        self._enrich_record,
                        record,
                        manifest,
                        request,
                        previous_text=previous_text,
                        next_text=next_text,
                        build_id=build_id,
                        stage_callback=persist_metadata_stage,
                        family_executor=family_pool,
                    )
                completed = already_complete
                for index, future in bounded_as_completed(
                    pending, submit_record, max_pending=max_workers,
                    cancelled=lambda: self._cancelled(build_id),
                ):
                    if self._cancelled(build_id):
                        raise InterruptedError("Corpus build cancelled")
                    baseline = records[index]
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
                        schema_for_failure = self._schema_for(build_id)
                        migrate_record_assertions(fallback, schema_for_failure)
                        for field in required_failure_fields:
                            current = current_assertion_by_name(fallback, field)
                            if current is not None and current.derivation_method == "deterministic":
                                continue
                            create_unresolved_assertion(
                                fallback,
                                field,
                                schema=schema_for_failure,
                                derivation_method="model",
                                evaluation_status="evaluation_failed",
                                method="llm",
                                reason=f"Metadata worker failed before this field could be validated: {exc}",
                                legacy_metadata={"reason_code": "llm_failed"},
                            )
                        project_record_assertions(fallback)
                        fallback["metadata_incomplete_fields"] = [
                            field
                            for field in required_failure_fields
                            if (
                                (current_assertion_by_name(fallback, field) is None)
                                or current_assertion_by_name(fallback, field).value_status in {"unresolved", "invalid"}
                                or fallback.get(field) in (None, "", [])
                            )
                        ]
                        fallback["metadata_stage_status"] = {**(fallback.get("metadata_stage_status") or {}), "worker": "needs_review"}
                        reasons = list(fallback.get("metadata_attention_reasons") or [])
                        reasons.append(f"Metadata worker failed and requires review: {exc}")
                        fallback["metadata_attention_reasons"] = list(dict.fromkeys(reason for reason in reasons if reason))[:50]
                        fallback["metadata_enrichment_state"] = "failed"
                        records[index] = fallback
                        self._append_warning(build_id, f"{fallback.get('record_id')}: metadata worker failed; the source-bound record was preserved for review.")
                    completed += 1
                    # Merge only this completion into the latest authoritative row.
                    # Human decisions and family checkpoints share the manager lock.
                    # The final handoff reloads all rows once, including other edits.
                    completed_id = str(records[index].get("record_id") or "")
                    with self._lock:
                        allowed_fields = self._allowed_fields(build_id)
                        applied = False

                        def merge_completion(
                            rows: list[dict[str, Any]], baseline: dict[str, Any] = baseline,
                            worker: dict[str, Any] = records[index], allowed: set[str] = allowed_fields,
                        ) -> None:
                            nonlocal applied
                            if rows and _record_source_matches(rows[0], baseline):
                                rows[0] = _merge_enrichment_snapshot(
                                    rows[0], worker, allowed,
                                )
                                applied = True

                        current = self.repo.reconcile_records(
                            build_id, merge_completion, record_ids=[completed_id],
                        )
                        if not applied:
                            # Retired identities and changed documentary snapshots
                            # cannot install stale assertions or completion state.
                            if current:
                                logger.warning("Discarded stale initial metadata completion for build %s record %s", build_id, completed_id)
                            continue
                        records[index] = current[0]
                        build = self.repo.get_build(build_id)
                        if not build.get("metadata_first_settled_at"):
                            self._update(build_id, metadata_first_settled_at=iso_now())
                    # The terminal realtime hint means a subsequent read can observe
                    # the enriched Record. Emit it only after the durable merge/save.
                    note_record_metadata(build_id, completed_id, "record_completed")
                    self._update(
                        build_id,
                        stage="enriching",
                        progress=0.42 + 0.43 * (completed / total),
                        metadata_enriched_count=completed,
                        metadata_enrichment_total=len(records),
                        metadata_total=len(records),
                        metadata_concurrency=max_workers,
                    )
                if self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")

        settled_records = self.repo.load_records(build_id)
        requeued = [row for row in settled_records if row.get("metadata_requeue_requested")]
        if requeued:
            # A boundary edit may arrive while the first worker pass is still
            # running. Clear the one-shot marker and immediately schedule the
            # changed records again against their new reviewed text.
            priority_ids = [str(row.get("record_id") or "") for row in requeued]
            def clear_requeue(rows: list[dict[str, Any]]) -> None:
                for row in rows:
                    row.pop("metadata_requeue_requested", None)
            self.repo.reconcile_records(build_id, clear_requeue, record_ids=priority_ids)
            settled_records = self.repo.load_records(build_id)
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

        return settled_records

    def _finalize_build_review(self, build_id: str, scope: BuildScope, records: list[dict[str, Any]]) -> None:
        """Revalidate settled records and publish the authoritative handoff to review."""
        # All automatic workers have now settled. Recompute the authoritative
        # record/metadata queues once before handing control to human review so
        # the first review screen is already internally consistent.
        self._reconcile_and_validate(build_id)
        with self._lock:
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            current = self.repo.get_build(build_id)
            records = self.repo.load_records(build_id)
            existing_op = current.get("metadata_operation") if isinstance(current.get("metadata_operation"), dict) else {}
            if str(existing_op.get("state") or "") in {"queued", "running"}:
                operation = existing_op
            else:
                operation = _initial_enrichment_operation(
                    build_id, records, started_at=str(current.get("metadata_started_at") or "") or None,
                )
            # Keep the coherent validation already saved, including any later
            # targeted human edit; the worker's BuildScope is not current truth.
            self._update(
                build_id,
                status="awaiting_review",
                stage="review",
                progress=0.90,
                finished_at=iso_now(),
                record_count=len(records),
                needs_review_count=sum(1 for record in records if record.get("needs_review")),
                boundary_review_count=len(current.get("segmentation_boundary_reviews") or []),
                accepted_count=sum(1 for record in records if record.get("accepted")),
                rejected_count=sum(1 for record in records if str(record.get("review_disposition") or "") == "rejected"),
                source_problem_count=sum(1 for record in records if record.get("source_quality_issues")),
                resumable=False,
                retrying_segmentation=False,
                metadata_operation=operation,
            )


    def _rewrite_and_validate(
        self,
        build_id: str,
        records: list[dict[str, Any]],
        *,
        persist_records: bool = True,
    ) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        self._validate_record_states(build, records)
        if persist_records:
            self.repo.save_records(build_id, records)
        self.repo.save_build(build)
        return build

    def _reconcile_and_validate(self, build_id: str) -> dict[str, Any]:
        """Validate current topology without restoring a settled worker snapshot."""
        base: dict[str, Any] = {}
        build: dict[str, Any] = {}

        def validate_current(records: list[dict[str, Any]]) -> None:
            nonlocal base, build
            with self._lock:
                base = self.repo.get_build(build_id)
            build = json.loads(json.dumps(base))
            self._validate_record_states(build, records)

        def committed() -> None:
            build["records_projection"] = self.repo.get_build(build_id).get("records_projection")
            self.repo.save_build(build)

        self.repo.reconcile_records(
            build_id, validate_current, optimistic=True, coordination_lock=self._lock,
            is_current=lambda: self.repo.get_build(build_id) == base, on_commit=committed,
        )
        return build

    def _validate_record_states(self, build: dict[str, Any], records: list[dict[str, Any]]) -> None:
        """Derive validation and review state without performing durable writes."""
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
        # Review counts are derived only after metadata state and review invariants
        # have been synchronized. Otherwise a record reopened by validation could
        # still be reported as accepted until the next request, which is exactly
        # the kind of stale state that makes review appear to "come back."
        self._apply_review_aggregates(
            build, records, validation,
            automation_running=automation_running, pass_running=pass_running,
        )
        self._refresh_workflow_fields(build)

    def _record_review_aggregate(self, record: dict[str, Any], automation_running: bool) -> dict[str, Any]:
        return record_review_aggregate(record, automation_running)

    def _apply_review_aggregates(
        self,
        build: dict[str, Any],
        records: list[dict[str, Any]],
        validation: dict[str, Any],
        *,
        automation_running: bool,
        pass_running: bool,
    ) -> None:
        """Derive every build-level review/metadata aggregate from persisted Record state."""
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
        contribution: Counter[str] = Counter()
        llm_elapsed_ms = 0
        llm_family_calls = 0
        for record in records:
            part = self._record_review_aggregate(record, automation_running)
            by_field.update(part["by_field"])
            by_reason.update(part["by_reason"])
            invalid_by_field.update(part["invalid_by_field"])
            contribution.update(part["contribution"])
            llm_elapsed_ms += part["llm_elapsed_ms"]
            llm_family_calls += part["llm_family_calls"]
            rid = str(record.get("record_id") or "")
            for row in part["rows"]:
                issue_rows.append(row)
                (retryable_record_ids if row["retryable"] else human_record_ids).add(rid)
            if part["incomplete"]:
                issue_records.append({
                    "record_id": record.get("record_id"),
                    "fields": part["incomplete"],
                    "issues": part["rows"],
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
        self._apply_review_workflow(
            build, validation, automation_running=automation_running, pass_running=pass_running,
        )

    def _apply_review_workflow(
        self, build: dict[str, Any], validation: dict[str, Any], *, automation_running: bool, pass_running: bool,
    ) -> None:
        if (
            str(build.get("status") or "") in {"queued", "running"}
            and str(build.get("stage") or "") in {"constructing_records", "document_intelligence"}
            and build.get("text_review_available_at")
            and (build.get("topology_validation") or {}).get("valid") is True
        ):
            return
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

    def _rewrite_targeted_record(
        self,
        build_id: str,
        record: dict[str, Any],
        previous: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and persist one ordinary review edit without corpus scans.

        Structural edits continue through ``_rewrite_and_validate`` because they
        change topology. Ordinary text, metadata, evidence, and disposition
        edits only need record-local validation plus scalar build-counter deltas.
        """
        build = self.repo.get_build(build_id)
        blocks = [
            block for block in self.repo.load_blocks(str(build["asset_id"]))
            if not block.get("excluded_reason")
        ]
        blocks = _manifest_main_text_blocks(
            blocks,
            build.get("manifest") or {},
            bounds_confirmed=bool(build.get("manifest_confirmed_at")),
        )
        profile = self._profile_of_build(build)
        _sync_record_metadata_state(record, profile)
        _enforce_review_invariants(record)
        local = self.validate_records(blocks, [record], profile)
        existing = dict(build.get("validation") or {})
        record_id = str(record.get("record_id") or "")
        list_fields = (
            "text_fidelity_errors", "source_order_errors", "page_mapping_errors",
            "printed_page_label_errors", "metadata_schema_errors",
            "relationship_errors", "human_ownership_errors", "record_content_errors",
            "citation_errors", "suspicious_record_sizes",
            "metadata_evidence_errors",
        )
        for field in list_fields:
            prior = existing.get(field)
            if not isinstance(prior, list):
                continue
            retained = [
                item for item in prior
                if str(item.get("record_id") if isinstance(item, dict) else item) != record_id
            ]
            additions = local.get(field)
            if isinstance(additions, list):
                existing[field] = retained + additions
        existing["metadata_valid"] = not any(
            existing.get(field) for field in (
                "metadata_evidence_errors", "metadata_schema_errors",
                "relationship_errors", "human_ownership_errors",
                "record_content_errors", "citation_errors",
                "printed_page_label_errors",
            )
        )
        existing["valid"] = bool(existing.get("source_valid", True) and existing["metadata_valid"])
        build["validation"] = existing
        if build.get("publication"):
            history = list(build.get("publication_history") or [])
            history.append(build["publication"])
            build["publication_history"] = history[-20:]
            build["publication"] = None
            build["publication_status"] = "unpublished"
        for field in ("needs_review_count", "accepted_count", "rejected_count", "source_problem_count", "metadata_completed"):
            before = bool(previous.get("needs_review")) if field == "needs_review_count" else (
                str(previous.get("review_disposition") or "") == "accepted" if field == "accepted_count" else
                str(previous.get("review_disposition") or "") == "rejected" if field == "rejected_count" else
                bool(previous.get("source_quality_issues")) if field == "source_problem_count" else
                bool(previous.get("metadata_complete"))
            )
            after = bool(record.get("needs_review")) if field == "needs_review_count" else (
                str(record.get("review_disposition") or "") == "accepted" if field == "accepted_count" else
                str(record.get("review_disposition") or "") == "rejected" if field == "rejected_count" else
                bool(record.get("source_quality_issues")) if field == "source_problem_count" else
                bool(record.get("metadata_complete"))
            )
            build[field] = max(0, int(build.get(field) or 0) + int(after) - int(before))
        persisted = self.repo.update_record(build_id, record)
        record.clear()
        record.update(persisted)
        running = str(build.get("status") or "") in {"queued", "running"}
        stage = str(build.get("stage") or "")
        automation_running = running and stage in {"enriching", "metadata_retry"}
        build.update(self.repo.review_build_aggregates(build_id, automation_running=automation_running))
        build["llm_contribution"].update({
            "enrichment_mode": str((build.get("request") or {}).get("enrichment_mode") or "fast"),
            "semantic_indexing": bool((build.get("request") or {}).get("semantic_indexing")),
        })
        build["boundary_review_count"] = len(build.get("segmentation_boundary_reviews") or build.get("segmentation_unresolved_regions") or [])
        self._apply_review_workflow(
            build, build.get("validation") or {}, automation_running=automation_running,
            pass_running=running and stage == "metadata_enrichment_rerun",
        )
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
        blinded = _present_for_reviewer(record)  # the preview is built from the record as this reviewer may see it
        public = serialize_public_record(record)
        if blinded:
            _scrub_canonical_transport(public)
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
        max_tokens = min(8192, max(2048, len(current_text)//3))

        def invoke(role: str, attempts: int, escalated: bool) -> dict[str, Any]:
            if role not in _provider_roles(active_request):
                raise LookupError("No review provider is configured for this build.")
            return self._chat_json(
                active_request, prompt, response_model=TextTouchupResponseModel, max_tokens=max_tokens,
                schema_name="record_text_touchup", attempts=attempts, build_id=build_id,
                roles=(role,), escalated=escalated,
            )

        # One trace per proposal. Without a resolvable pipeline no model is asked and the request fails
        # with the reason, as any failed touch-up does; reviewed text is never touched here.
        try:
            session = TextTouchupSession.open()
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
        try:
            result = session.run(invoke, response_contract="record_text_touchup", providers=_provider_roles(active_request))
        except InterruptedError:
            session.finish(cancelled=True)
            raise
        except Exception:
            session.finish()
            raise
        session.finish()
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
            "pipeline": session.identity(),
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
        if isinstance(proposal.get("pipeline"), dict):
            record["text_touchup_proposal"]["pipeline"] = dict(proposal["pipeline"])
        record["needs_review"] = True
        record["metadata_needs_attention"] = True
        reasons = list(record.get("metadata_attention_reasons") or [])
        reasons.append("An LLM text touch-up proposal is available for review; reviewed text remains unchanged until approved.")
        record["metadata_attention_reasons"] = list(dict.fromkeys(reasons))[-50:]
        self._rewrite_and_validate(build_id, records)
        return next(row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id)

    @_serialize_record_mutation
    def acknowledge_warnings(self, build_id: str, warnings: list[str], actor: str) -> dict[str, Any]:
        """Record that a person has seen these build warnings. The warnings stay; they travel with the corpus."""
        with self._lock, self.repo._lock:
            build = self.repo.get_build(build_id)
            current = {str(item) for item in build.get("warnings") or []}
            unknown = [text for text in warnings if text not in current]
            if unknown:
                raise ValueError(f"Not a warning of this build: {unknown[0][:120]}")
            acknowledgements = dict(build.get("warning_acknowledgements") or {})
            now = iso_now()
            for text in warnings:
                acknowledgements.setdefault(
                    warning_key(text),
                    {"warning": text, "acknowledged_by": actor, "acknowledged_at": now},
                )
            build["warning_acknowledgements"] = acknowledgements
            self.repo.save_build(build)
            return build

    def publish(self, build_id: str, *, require_acceptance: bool = True, accept_unreviewed: bool = False) -> dict[str, Any]:
        """Publish an immutable snapshot of the build's non-rejected records.

        With `accept_unreviewed`, every eligible suggestion is selected in the immutable
        snapshot without mutating stored review state. The publication records autonomous
        decision provenance and evaluates cELF conformance independently of review mode.
        """
        build = self.repo.get_build(build_id)
        if self.repo.records_projection_dirty(build_id):
            self.repo.refresh_records_projection(build_id)
        records = self.repo.load_records(build_id)
        validation = build.get("validation") or {}
        self._refresh_workflow_fields(build)
        publishable = publishable_records(records)
        blocker = publication_blocker(
            build, publishable, validation, require_acceptance=require_acceptance, accept_unreviewed=accept_unreviewed
        )
        if blocker:
            raise ValueError(blocker)
        bypassed_review = accept_unreviewed and publication_blocker(
            build, publishable, validation, require_acceptance=True
        )
        unreviewed_count = accepted_field_count = 0
        if accept_unreviewed:
            publishable, unreviewed_count, accepted_field_count = mark_unreviewed_publication(publishable)
            bypassed_review = bypassed_review or (
                f"{accepted_field_count} suggested field value(s) were accepted without review." if accepted_field_count else False
            )
        publication_id = f"publication-{build_id.removeprefix('build-')}-{uuid.uuid4().hex[:8]}"
        created_at = iso_now()
        # Warnings are provenance: those about a record are published with it, the rest with the publication.
        build_warnings, record_warnings = provenance_warnings(
            build, {str(record.get("record_id") or "") for record in publishable}
        )
        publishable = [
            {**record, "provenance_warnings": record_warnings[str(record.get("record_id") or "")]}
            if str(record.get("record_id") or "") in record_warnings
            else record
            for record in publishable
        ]
        conformance = evaluate_celf_conformance(build, publishable)
        human_reviewed_count = 0
        autonomous_count = 0
        for record in publishable:
            review_status = str(record.get("publication_review_status") or "")
            actor_kind = str(record.get("acceptance_actor_kind") or "").casefold()
            accepted_by = str(record.get("accepted_by") or "").casefold()
            autonomous = (
                review_status == "unreviewed_suggestion"
                or actor_kind == "policy"
                or accepted_by == "autonomous"
                or bool(record.get("autonomous_decision"))
            )
            if autonomous:
                autonomous_count += 1
                continue
            reviewed = (
                review_status == "reviewer_accepted"
                or actor_kind == "human"
                or bool(accepted_by)
                or bool(record.get("accepted"))
                or str(record.get("review_disposition") or "") == "accepted"
            )
            if reviewed:
                human_reviewed_count += 1
        if autonomous_count and human_reviewed_count:
            review_mode = "hybrid"
        elif autonomous_count:
            review_mode = "autonomous"
        else:
            review_mode = "reviewed"
        path = self.repo.publication_path(publication_id)
        result = write_jsonl_zst(
            path,
            publishable,
            serialize_record=serialize_public_record,
            validate_record=validate_publication_record,
            compression_level=10,
        )
        integrity_path = self.repo.publication_integrity_path(publication_id)
        integrity_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_integrity = integrity_path.with_name(f".{integrity_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary_integrity.write_text(
                f"{result.archive_sha512}  {path.name}\n",
                encoding="ascii",
            )
            os.replace(temporary_integrity, integrity_path)
        finally:
            temporary_integrity.unlink(missing_ok=True)
        publication = {
            "publication_id": publication_id,
            "filename": f"{Path(build.get('source_filename') or 'corpus').stem}.jsonl.zst",
            # Preserve the historical meaning of sha256 as the hash of the
            # canonical decompressed JSONL content; archive_sha256 identifies
            # the exact compressed artifact.
            "sha256": result.content_sha256,
            "archive_sha256": result.archive_sha256,
            "sha512": result.archive_sha512,
            "content_sha512": result.content_sha512,
            "archive_sha512": result.archive_sha512,
            "integrity_filename": integrity_path.name,
            "compression": "zstd",
            "media_type": "application/zstd",
            "record_count": result.record_count,
            "excluded_rejected_count": len(records) - len(publishable),
            "uncompressed_bytes": result.uncompressed_bytes,
            "compressed_bytes": result.compressed_bytes,
            "created_at": created_at,
            "provenance_warnings": build_warnings,
            "record_warning_count": sum(len(items) for items in record_warnings.values()),
            "review_mode": review_mode,
            "decision_mode": review_mode,
            "human_reviewed_record_count": human_reviewed_count,
            "autonomous_record_count": autonomous_count,
            "celf_conformance": conformance,
            "celf_conformant": conformance["conformant"],
            "unreviewed_record_count": unreviewed_count,
            "unreviewed_accepted_field_count": accepted_field_count,
            "bypassed_review_blocker": bypassed_review or None,
        }
        # Document Intelligence stays build-scoped storage; remember which build each
        # published record came from so its semantic map can be resolved after publish.
        for record in publishable:
            record_id = str(record.get("record_id") or "").strip()
            if record_id:
                system_store.set_record_build_provenance(
                    record_id, build_id, work=record.get("work")
                )
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
        note_resource_changed("corpus_records")
        return publication


pdf_corpus_repository = PdfCorpusRepository()
pdf_corpus_builds = PdfCorpusBuildManager(pdf_corpus_repository)
