# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import threading
import tempfile
import time
import uuid
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .config import APP_VERSION, settings
from .models import OllamaTouchupOptions, WorkMetadataRequest, WorkMetadataSeed
from .rag import _citation_strings, _extract_json, chat_complete

SCHEMA_VERSION = "pdf-corpus-v3"
SEGMENTATION_PROMPT_VERSION = "derridai-local-boundaries-v7"
METADATA_PROMPT_VERSION = "derridai-record-metadata-v7"
PUBLICATION_SCHEMA_VERSION = "derridai-corpus-jsonl-v1"
DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v2"
PROFILE_VERSION = "derrida-scholarly-v11"

REGION_TYPES = [
    "front_matter", "main_text", "notes", "bibliography", "index",
    "appendix", "back_matter", "paratext", "unknown",
]
DISCOURSE_ROLES = [
    "assertion", "analysis", "quotation", "reported_position", "critique",
    "qualification", "transition", "question", "definition", "example",
    "commentary", "paratext", "bibliographic",
]
HYBRID_REQUIRED_FIELDS = ("region_type", "primary_text", "discourse_role")
REVIEW_METADATA_FIELDS = ("region_type", "primary_text", "discourse_role", "speaker", "position_holder", "target", "stance", "proposition_status", "claim_scope")

NON_PRIMARY_REGION_TYPES = {"front_matter", "back_matter", "bibliography", "index", "paratext"}

def apply_metadata_constraints(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply deterministic record-metadata relationships.

    Apparatus/non-primary region types are hard invariants. ``main_text`` strongly
    defaults to primary text, but an explicit human decision may override that
    default for unusual records.
    """
    region = str(record.get("region_type") or "")
    status = record.setdefault("metadata_field_status", {})
    primary_status = status.get("primary_text") if isinstance(status.get("primary_text"), dict) else {}
    human_primary = str(primary_status.get("status") or "") in {"human_confirmed", "human_override"}
    desired: bool | None = None
    reason = ""
    hard = False
    if region in NON_PRIMARY_REGION_TYPES:
        desired = False
        hard = True
        reason = f"{region} cannot be primary text."
    elif region == "main_text" and not human_primary:
        desired = True
        reason = "main_text is deterministically suggested as primary text unless a reviewer overrides it."
    if desired is None:
        return []
    changed = record.get("primary_text") is not desired
    if hard or not human_primary:
        record["primary_text"] = desired
        status["primary_text"] = {
            "status": "deterministic", "method": "region_type_consistency", "confidence": 1.0,
            "reason_code": "semantic_invariant" if hard else "deterministic_default", "reason": reason,
        }
    return [{"field": "primary_text", "value": desired, "reason": reason}] if changed else []


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
    model_config = ConfigDict(extra="forbid")
    language: str | None = None
    region_type: Literal["front_matter", "main_text", "notes", "bibliography", "index", "appendix", "back_matter", "paratext", "unknown"] | None = None
    region_author: str | None = None
    primary_text: bool | None = None
    speaker: str | None = None
    position_holder: str | None = None
    target: str | None = None
    discourse_role: Literal["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary", "paratext", "bibliographic"] | None = None
    proposition_status: str | None = None
    semantic_function: list[str] = Field(default_factory=list, max_length=12)
    stance: str | None = None
    claim_scope: str | None = None


class RecordFieldAssessmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Missing model confidence is unknown, not 0%. This distinction matters in
    # review UI and avoids manufacturing false certainty from omitted fields.
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_review: bool = False
    reason: str = Field(default="", max_length=500)


class DiscourseMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: DiscourseMetadataModel = Field(default_factory=DiscourseMetadataModel)
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)


class QuotationMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_direct_quote: bool | None = None
    quoted_speaker: list[str] = Field(default_factory=list, max_length=12)
    quoted_author: list[str] = Field(default_factory=list, max_length=12)
    quoted_work: list[str] = Field(default_factory=list, max_length=12)
    quoted_position_holder: list[str] = Field(default_factory=list, max_length=12)
    quoted_addressee: list[str] = Field(default_factory=list, max_length=12)
    quoted_referent: list[str] = Field(default_factory=list, max_length=12)
    quotation_chain: list[str] = Field(default_factory=list, max_length=16)


class QuotationMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: QuotationMetadataModel = Field(default_factory=QuotationMetadataModel)
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)


class IndexMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topics: list[str] = Field(default_factory=list, max_length=24)
    concepts: list[str] = Field(default_factory=list, max_length=24)
    persons: list[str] = Field(default_factory=list, max_length=24)
    works_referenced: list[str] = Field(default_factory=list, max_length=24)


class IndexMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: IndexMetadataModel = Field(default_factory=IndexMetadataModel)
    field_assessments: dict[str, RecordFieldAssessmentModel] = Field(default_factory=dict)
    review_reason: str = Field(default="", max_length=1000)


ATTRIBUTION_EVIDENCE_FIELDS = {
    "speaker", "position_holder", "target", "stance", "proposition_status",
    "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
    "quoted_addressee", "quoted_referent", "quotation_chain",
}
EVIDENCE_REQUIRED_FIELDS = ATTRIBUTION_EVIDENCE_FIELDS | set(HYBRID_REQUIRED_FIELDS)

SOURCE_BOUND_FIELDS = {
    "record_id", "record_revision", "text", "text_length", "page_start", "page_end", "pdf_file",
    "pdf_pages", "source_asset_id", "source_block_ids", "source_spans",
}

ALLOWED_METADATA_FIELDS = {
    "work", "document_title", "short_title", "original_title", "document_author",
    "edition", "year", "publication_year", "publisher", "publication_place", "isbn",
    "language", "document_language", "original_language", "document_is_translation", "translator", "region_type",
    "region_author", "primary_text", "speaker", "position_holder", "target",
    "discourse_role", "proposition_status", "semantic_function", "stance",
    "claim_scope", "is_direct_quote", "quoted_speaker", "quoted_author",
    "quoted_work", "quoted_position_holder", "quoted_addressee", "quoted_referent",
    "quotation_chain", "topics", "concepts", "persons", "works_referenced",
    "attribution_confidence", "semantic_classification_confidence", "extraction_quality",
    "canonical_work_id", "inline_citation", "full_citation", "needs_review",
    "review_reason",
}


METADATA_FAMILY_FIELDS = {
    "discourse": {
        "region_type", "region_author", "primary_text", "speaker", "position_holder",
        "target", "discourse_role", "proposition_status", "semantic_function", "stance",
        "claim_scope", "attribution_confidence", "semantic_classification_confidence",
    },
    "quotation": {
        "is_direct_quote", "quoted_speaker", "quoted_author", "quoted_work",
        "quoted_position_holder", "quoted_addressee", "quoted_referent", "quotation_chain",
    },
    "indexing": {"topics", "concepts", "persons", "works_referenced"},
}

MANIFEST_INHERITED_FIELDS = {
    "work", "document_title", "short_title", "original_title", "canonical_work_id",
    "document_author", "translator", "edition", "year", "publication_year", "publisher",
    "publication_place", "isbn", "document_language", "original_language",
    "document_is_translation",
}

HUMAN_EDITABLE_METADATA_FIELDS = {
    # Record-level overrides of inherited bibliographic metadata are explicit
    # human decisions. They never mutate the document manifest and must survive
    # later automatic enrichment.
    "work", "document_title", "short_title", "original_title", "canonical_work_id",
    "document_author", "translator", "edition", "year", "publication_year",
    "publisher", "publication_place", "isbn", "document_language",
    "original_language", "document_is_translation",
    "language", "region_type", "region_author", "primary_text", "speaker",
    "position_holder", "target", "discourse_role", "proposition_status",
    "semantic_function", "stance", "claim_scope", "is_direct_quote",
    "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
    "quoted_addressee", "quoted_referent", "quotation_chain", "topics",
    "concepts", "persons", "works_referenced", "needs_review", "review_reason",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            except Exception:
                pdf_label = None
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
        offsets = Counter()
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
        return {
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
        return meta

    def list_assets(self) -> list[dict[str, Any]]:
        items = []
        for path in sorted((self.root / "assets").glob("pdf-*.json"), reverse=True):
            item = _json_read(path)
            if isinstance(item, dict):
                items.append(item)
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
        "name": "Derrida scholarly corpus v11",
        "version": 11,
        "description": "Feral Fox: editable reviewed text, explicit metadata ownership, selective LLM enrichment, measurable automation contribution, and concurrent-build clarity.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": DISCOURSE_ROLES,
        "region_types": REGION_TYPES,
        "required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "publication_required_metadata_fields": list(HYBRID_REQUIRED_FIELDS),
        "review_metadata_fields": list(REVIEW_METADATA_FIELDS),
        "min_boundary_confidence": 0.72,
        "candidate_llm_threshold": 0.30,
        "deterministic_split_threshold": 0.92,
        "review_risk_threshold": 0.90,
        "max_llm_boundary_calls_per_100_atoms": 18,
        "boundary_batch_size": 6,
        "min_metadata_confidence": 0.72,
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
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    wrapped.__name__ = getattr(method, "__name__", "wrapped")
    wrapped.__doc__ = getattr(method, "__doc__")
    return wrapped


class PdfCorpusBuildManager:
    def __init__(self, repository: PdfCorpusRepository | None = None, max_workers: int = 2) -> None:
        self.repo = repository or PdfCorpusRepository()
        self._lock = threading.RLock()
        self._cancel: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="derridai-pdf-corpus")
        self._mark_interrupted()

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

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
        self._validate_execution_budget(request)
        public_request = {k: v for k, v in request.items() if k not in {"api_key", "_review_provider"}}
        build = self.repo.create_build({
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
        source_quality = build.get("source_quality") if isinstance(build.get("source_quality"), dict) else {}
        publication = build.get("publication") if isinstance(build.get("publication"), dict) else None
        running = str(build.get("status") or "") in {"queued", "running"}
        stage = str(build.get("stage") or "")
        profile = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES.get(PROFILE_VERSION, {}))
        required_fields = list(profile.get("publication_required_metadata_fields") or profile.get("required_metadata_fields") or [])

        blockers: list[dict[str, Any]] = []
        if pending:
            blockers.append({"code": "review_pending", "count": pending})
        if rejected:
            blockers.append({"code": "rejected_records", "count": rejected})
        if int(build.get("needs_review_count") or 0):
            blockers.append({"code": "record_attention", "count": int(build.get("needs_review_count") or 0)})
        if int(build.get("boundary_review_count") or 0):
            blockers.append({"code": "boundary_attention", "count": int(build.get("boundary_review_count") or 0)})
        if metadata_remaining or unresolved_fields:
            blockers.append({"code": "required_metadata", "count": max(metadata_remaining, int(issue_summary.get("records_incomplete") or 0)), "fields": required_fields})
        if validation and not bool(validation.get("source_valid", validation.get("valid", True))):
            blockers.append({"code": "source_validation", "count": len(validation.get("missing_block_ids") or []) + len(validation.get("text_fidelity_errors") or []) + len(validation.get("source_order_errors") or [])})
        if validation and not bool(validation.get("metadata_valid", validation.get("valid", True))):
            blockers.append({"code": "metadata_validation", "count": len(validation.get("metadata_evidence_errors") or []) + len(validation.get("metadata_schema_errors") or []) + len(validation.get("citation_errors") or [])})
        # Raw PDF extraction findings remain in build.source_quality for audit,
        # but a reviewer may resolve a record-level extraction problem by
        # correcting the reviewed text while preserving source_extracted_text.
        # Publication is therefore gated by unresolved record source issues, not
        # forever by the immutable raw-page diagnostic.
        if int(build.get("source_problem_count") or 0):
            blockers.append({"code": "source_quality", "count": int(build.get("source_problem_count") or 0)})

        can_publish = bool(record_count and not blockers and bool(validation.get("valid", True)) and accepted == record_count)
        if publication:
            next_action = "download_publication"
        elif running:
            next_action = "wait"
        elif pending or int(build.get("needs_review_count") or 0) or int(build.get("boundary_review_count") or 0) or metadata_remaining or unresolved_fields:
            next_action = "review_records"
        elif rejected:
            next_action = "resolve_rejections"
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
        }
        return build

    def _update(self, build_id: str, *, stage: str | None = None, progress: float | None = None, **changes: Any) -> dict[str, Any]:
        # Metadata workers update telemetry and warnings concurrently. Serialize
        # read/modify/write of build.json so one worker cannot erase another
        # worker's metric, progress, or recovery flag.
        with self._lock:
            build = self.repo.get_build(build_id)
            prior_stage = str(build.get("stage") or "")
            prior_status = str(build.get("status") or "")
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
        except Exception:
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
                    raw = chat_complete(
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
    def _manifest_main_text_blocks(blocks: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply reviewed physical-page manifest bounds when they are plausible."""
        try:
            start = int(manifest.get("main_text_start_page")) if manifest.get("main_text_start_page") is not None else None
            end = int(manifest.get("main_text_end_page")) if manifest.get("main_text_end_page") is not None else None
        except (TypeError, ValueError):
            return blocks
        if start is None and end is None:
            return blocks
        selected = [
            block for block in blocks
            if (start is None or int(block.get("page") or 0) >= start)
            and (end is None or int(block.get("page") or 0) <= end)
        ]
        # Refuse implausible manifest ranges rather than accidentally erasing the book.
        return selected if len(selected) >= max(2, min(10, len(blocks) // 20)) else blocks

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
        right_text = str(right.get("text") or "").strip()
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
        total=max(1,sum(len(str(b.get("text") or "")) for b in span))
        scored=[]
        heading_types={"heading","title","subtitle","section","chapter"}
        speaker_re=re.compile(r"^\s*(?:[A-Z][A-Z .'-]{1,40}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*:\s+")
        for idx,(left,right) in enumerate(zip(span,span[1:])):
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
        profile=CORPUS_PROFILES[str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)]
        threshold=float(profile.get("min_boundary_confidence") or 0.72)
        sizing_policy=self._record_sizing_policy(request,profile)
        hard_max=sizing_policy["absolute_record_chars"]
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
        max_adjudications=max(8,int(math.ceil(max(1,len(blocks))*float(profile.get("max_llm_boundary_calls_per_100_atoms") or 18)/100.0)))
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

    def _reconcile_boundaries(
        self,
        blocks: list[dict[str, Any]],
        manifest: dict[str, Any],
        candidates: list[dict[str, Any]],
        request: dict[str, Any],
        build_id: str,
        threshold: float,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        block_index = {block["block_id"]: i for i, block in enumerate(blocks)}
        accepted: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        state = self.repo.load_checkpoint(build_id, "reconciliation_state", {})
        if not isinstance(state, dict):
            state = {}
        completed = {str(value) for value in state.get("completed") or []}
        restored = state.get("accepted") or []
        if isinstance(restored, list):
            accepted.extend(item for item in restored if isinstance(item, dict))
        limits = self._stage_limits(request)

        # Small batches keep structured output short and make local-model retries
        # cheap. No prose reasons are requested in this topology-changing stage.
        for offset in range(0, len(candidates), 8):
            batch = candidates[offset:offset + 8]
            batch_key = ",".join(str(item.get("after_block_id") or "") for item in batch)
            if batch_key in completed:
                continue
            excerpts: list[str] = []
            for candidate in batch:
                idx = block_index.get(str(candidate.get("after_block_id") or ""), -1)
                if idx < 0:
                    continue
                context = blocks[max(0, idx - 2):min(len(blocks), idx + 4)]
                excerpts.append(
                    f"CANDIDATE {candidate['after_block_id']} prior-confidence={float(candidate.get('confidence') or 0):.2f}\n"
                    + "\n".join(f"[{b['block_id']}] {str(b.get('text') or '')[:1000]}" for b in context)
                )
            prompt = f"""Reconcile uncertain semantic record boundaries. Keep a boundary only when the surrounding source shows a genuine discourse/argument transition. Do not use page changes, window seams, or length as evidence. Preserve attribution and quotation framing. Prefer KEEP when evidence is weak.

{chr(10).join(excerpts)}

Return one compact decision for every supplied candidate using exact `after` IDs. No prose explanations.
"""
            try:
                result = self._chat_json(
                    request,
                    prompt,
                    response_model=CompactReconciliationResponseModel,
                    max_tokens=limits["reconciliation_num_predict"],
                    schema_name="derridai_boundary_reconciliation_compact",
                    attempts=2,
                    build_id=build_id,
                )
            except InterruptedError:
                raise
            except Exception as exc:
                # Reconciliation is advisory. A failed compact reconciliation must
                # not turn every candidate in the batch into an apparent pipeline
                # failure. Preserve only genuinely uncertain/high-signal candidates
                # as localized review items; ordinary weak candidates become KEEP.
                self._increment_metric(build_id, "reconciliation_failures")
                for candidate in batch:
                    confidence = float(candidate.get("confidence") or 0)
                    if candidate.get("decision") != "uncertain" and confidence < threshold:
                        continue
                    block_id = str(candidate.get("after_block_id") or "")
                    idx = block_index.get(block_id, -1)
                    next_id = str(blocks[idx + 1].get("block_id") or "") if 0 <= idx < len(blocks) - 1 else ""
                    unresolved.append({
                        "after_block_id": block_id,
                        "next_block_id": next_id,
                        "kind": "reconciliation_review",
                        "reason": f"This candidate could not be automatically reconciled and remains a local review item: {exc}",
                    })
                continue
            original = {str(item["after_block_id"]): item for item in batch}
            decided: set[str] = set()
            for decision in result.get("decisions") or []:
                block_id = str(decision.get("after") or "")
                if block_id not in original:
                    continue
                decided.add(block_id)
                if decision.get("decision") != "split":
                    continue
                confidence = float(decision.get("confidence") or 0)
                if confidence < threshold:
                    continue
                merged = dict(original[block_id])
                merged.update({"decision": "split", "confidence": confidence, "reconciled": True})
                accepted.append(merged)
            batch_unresolved = False
            for block_id in sorted(set(original) - decided):
                idx = block_index.get(block_id, -1)
                if 0 <= idx < len(blocks) - 1:
                    pair, failure = self._segment_pair(blocks[idx], blocks[idx + 1], manifest, request, build_id)
                else:
                    pair, failure = None, None
                if pair and pair.get("decision") == "split" and float(pair.get("confidence") or 0) >= threshold:
                    merged = dict(original[block_id])
                    merged.update(pair)
                    merged["reconciled"] = True
                    merged["source"] = "reconciliation_pair_fallback"
                    accepted.append(merged)
                elif pair and pair.get("decision") == "keep":
                    continue
                else:
                    batch_unresolved = True
                    next_id = str(blocks[idx + 1].get("block_id") or "") if 0 <= idx < len(blocks) - 1 else ""
                    unresolved.append({
                        "after_block_id": block_id,
                        "next_block_id": next_id,
                        "kind": "reconciliation",
                        "reason": str((failure or {}).get("reason") or "Boundary reconciliation remained uncertain after pairwise fallback."),
                    })
            # Do not checkpoint an incomplete reconciliation batch as completed.
            if not batch_unresolved:
                completed.add(batch_key)
            self.repo.save_checkpoint(build_id, "reconciliation_state", {
                "completed": sorted(completed),
                "accepted": accepted,
            })
        return accepted, unresolved

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
            if primary_status.get("status") not in {"human_confirmed", "human_override"}:
                record["primary_text"] = inside
                field_status["primary_text"] = {
                    "status": "deterministic", "method": "manifest_page_range", "confidence": 1.0,
                    "reason": "Classified from the reviewed document main-text page range.",
                }
            if region_status.get("status") not in {"human_confirmed", "human_override"}:
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
            role_status = field_status.get("discourse_role") if isinstance(field_status.get("discourse_role"), dict) else {}
            if not inside and role_status.get("status") not in {"human_confirmed", "human_override"}:
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
        if build_id:
            try:
                current_manifest = self.repo.get_build(build_id).get("manifest")
                if isinstance(current_manifest, dict) and current_manifest:
                    manifest = current_manifest
            except Exception:
                pass
        self._apply_manifest_metadata(record, manifest)
        editorial_context = self._editorial_context(build_id, exclude_record_id=str(record.get("record_id") or "")) if build_id else {}
        profile_id = PROFILE_VERSION
        if build_id:
            try:
                profile_id = str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)
            except Exception:
                pass
        profile = CORPUS_PROFILES.get(profile_id, CORPUS_PROFILES[PROFILE_VERSION])
        allowed_region_types = list(profile.get("region_types") or REGION_TYPES)
        allowed_discourse_roles = list(profile.get("discourse_roles") or DISCOURSE_ROLES)
        required_metadata_fields = list(profile.get("required_metadata_fields") or [])
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
            return record
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
Human-owned fields on this record (authoritative; DO NOT propose replacements): {json.dumps({field: record.get(field) for field in human_locked_fields}, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps(neighbor_context, ensure_ascii=False)}
Current source block IDs: {source_id_json}
CURRENT REVIEWED RECORD TEXT:
{source_text}
"""
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]] = []

        discourse_prompt = f"""Infer ONLY discourse/attribution metadata for one immutable DerridAI record.
Distinguish the grammatical/textual speaker from the POSITION HOLDER whose proposition is being presented. A named person is not automatically a speaker or position holder. Preserve modality, negation, uncertainty, and stance. Do not return quotation relations, topical indexing, bibliographic metadata, summaries, or source text.

Hybrid classification fields are constrained:
- region_type MUST be one of: {json.dumps(allowed_region_types, ensure_ascii=False)}
- discourse_role MUST be one of: {json.dumps(allowed_discourse_roles, ensure_ascii=False)}
- primary_text MUST be true or false. It means the record belongs to the substantive work rather than front/back matter, bibliography, index, publishing paratext, or other apparatus.
If a field is genuinely unsupported, return null rather than inventing a value.

{base_context}
For every populated attribution-bearing field and every populated hybrid field (region_type, primary_text, discourse_role), include field_evidence using only current-record block IDs, confidence 0..1, and a short reason. Use null or [] when unsupported.
Also return field_assessments for region_type, primary_text, discourse_role, speaker, position_holder, target, stance, proposition_status, and claim_scope. Each assessment must contain confidence, needs_review, and a short reason. Mark needs_review=true whenever a proposed value or supported absence is genuinely ambiguous, attribution is uncertain, evidence is weak, or confidence is not sufficient for scholarly acceptance.
"""
        quotation_prompt = f"""Infer ONLY quotation relations for one immutable DerridAI record.
Determine whether there is direct quotation and, only when source-supported, identify quoted speaker/author/work/position-holder/addressee/referent and quotation chains. A mentioned name is not automatically a quoted source. Do not return discourse fields, topical indexing, bibliographic metadata, summaries, or source text.

{base_context}
For every populated quoted_* or quotation_chain field, include field_evidence using only current-record block IDs, confidence 0..1, and a short reason. Use [] when unsupported.
Also return field_assessments for is_direct_quote and every quotation field you populate. Each assessment must include confidence 0..1, needs_review, and a concise reason.
"""
        indexing_prompt = f"""Infer ONLY conservative semantic indexing metadata for one immutable DerridAI record.
Return topics, concepts, persons, and works_referenced that are materially present in this record. Do not infer discourse attribution, quotation ownership, bibliography, summaries, or source text. Prefer a short precise list to speculative coverage.

{base_context}
Return field_assessments for topics, concepts, persons, and works_referenced whenever you populate those fields. Each assessment must include confidence 0..1, needs_review, and a concise reason.
"""

        enrichment_mode = str(request.get("enrichment_mode") if "enrichment_mode" in request else "deep")
        semantic_indexing = bool(request.get("semantic_indexing")) or enrichment_mode == "deep"
        region_type = str(record.get("region_type") or "")
        obvious_apparatus = region_type in {"bibliography", "index", "copyright", "front_matter", "back_matter"} or record.get("primary_text") is False
        quote_signal = any(token in source_text for token in ('“', '”', '"', '«', '»', '‘', '’')) or bool(re.search(r"\b(?:quotes?|writes?|says?|according to|cites?)\b", source_text, re.I))
        all_task_specs = {
            "discourse": ("discourse", discourse_prompt, DiscourseMetadataResponseModel, limits["discourse_num_predict"], "derridai_record_discourse"),
            "quotation": ("quotation", quotation_prompt, QuotationMetadataResponseModel, limits["quotation_num_predict"], "derridai_record_quotation"),
            "indexing": ("indexing", indexing_prompt, IndexMetadataResponseModel, limits["indexing_num_predict"], "derridai_record_indexing"),
        }
        requested_families = request.get("families")
        if isinstance(requested_families, list) and requested_families:
            # Explicit human reruns bypass Fast-mode routing, but only for the
            # selected family/families. This prevents a text correction from
            # needlessly repeating every expensive metadata task.
            requested = [str(value) for value in requested_families if str(value) in all_task_specs]
            tasks = [all_task_specs[name] for name in ("discourse", "quotation", "indexing") if name in requested]
        else:
            tasks = []
            if not obvious_apparatus or enrichment_mode == "deep":
                tasks.append(all_task_specs["discourse"])
            if enrichment_mode == "deep" or quote_signal:
                tasks.append(all_task_specs["quotation"])
            if semantic_indexing:
                tasks.append(all_task_specs["indexing"])
        selected_names = {item[0] for item in tasks}
        # Normal Fast-mode routing settles unneeded families as skipped. An
        # explicit selective rerun must leave every unselected family's prior
        # terminal state and normalized metadata untouched.
        if not (isinstance(requested_families, list) and requested_families):
            for skipped_family in {"discourse", "quotation", "indexing"} - selected_names:
                record.setdefault("metadata_stage_status", {})[skipped_family] = "skipped"
                record.setdefault("metadata_execution_ledger", {})[skipped_family] = {
                    "state": "skipped", "finished_at": iso_now(),
                    "error": "Skipped by fast enrichment routing; no strong signal required this LLM family.",
                }
                if stage_callback:
                    stage_callback(record, skipped_family, "skipped", "Fast enrichment routing")
        persisted_stage_results = record.setdefault("metadata_stage_results", {})
        stage_status = record.setdefault("metadata_stage_status", {})
        stage_ledger = record.setdefault("metadata_execution_ledger", {})
        for task_name, prompt, response_model, max_tokens, schema_name in tasks:
            if build_id:
                try:
                    live_rows = self.repo.load_records(build_id)
                    live_record = next((row for row in live_rows if str(row.get("record_id") or "") == str(record.get("record_id") or "")), None)
                except Exception:
                    live_record = None
                if isinstance(live_record, dict):
                    touched = {str(value) for value in (live_record.get("human_touched_fields") or [])}
                    live_status = live_record.get("metadata_field_status") if isinstance(live_record.get("metadata_field_status"), dict) else {}
                    family_fields = METADATA_FAMILY_FIELDS.get(task_name, set())
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
                except KeyError:
                    pass
            started_at = iso_now()
            ledger_context = {
                "provider": request.get("provider"),
                "model": request.get("model"),
                "attempts_allowed": 2,
                "input_chars": len(prompt),
                "max_output_tokens": max_tokens,
                "timeout_seconds": self._stage_timeouts(request).get(task_name),
            }
            stage_status[task_name] = "running"
            stage_ledger[task_name] = {**ledger_context, "state": "running", "started_at": started_at, "finished_at": None, "error": None}
            if stage_callback:
                stage_callback(record, task_name, "running", None)
            started_clock = time.monotonic()
            try:
                result = self._chat_json(
                    request,
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
                if stage_callback:
                    stage_callback(record, task_name, "failed", str(exc))
                if build_id:
                    self._append_warning(build_id, f"{record.get('record_id')}: {task_name} metadata requires review ({exc})")

        clean_evidence: dict[str, Any] = dict(record.get("metadata_evidence") or {})
        valid_ids = set(source_ids)
        review_reasons: list[str] = []
        evidence_confidences: list[float] = []
        attribution_confidences: list[float] = []
        model_review_reasons: list[str] = []
        field_assessments: dict[str, dict[str, Any]] = {}
        llm_populated_fields: set[str] = set()
        successful_tasks = 0

        for task_name, result, failure in stage_results:
            if failure is not None or not isinstance(result, dict):
                review_reasons.append(f"{task_name} metadata extraction could not be validated: {failure}")
                continue
            successful_tasks += 1
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            if isinstance(result.get("field_assessments"), dict):
                field_assessments.update({str(key): value for key, value in result.get("field_assessments", {}).items() if isinstance(value, dict)})
            field_status = record.setdefault("metadata_field_status", {})
            for key, value in metadata.items():
                if key not in ALLOWED_METADATA_FIELDS or key in SOURCE_BOUND_FIELDS:
                    continue
                existing_status = field_status.get(key) if isinstance(field_status.get(key), dict) else {}
                # Human decisions are authoritative. Background/retry enrichment
                # may add evidence, but it must never resurrect an already
                # confirmed review issue or overwrite a human value.
                if existing_status.get("status") in {"human_confirmed", "human_override"}:
                    continue
                if key in {"region_type", "primary_text"} and existing_status.get("status") == "deterministic":
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
                record[key] = value
                if value not in (None, "", []):
                    llm_populated_fields.add(key)
            evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
            for field, info in evidence.items():
                if field not in ALLOWED_METADATA_FIELDS or not isinstance(info, dict):
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
                    if field in ATTRIBUTION_EVIDENCE_FIELDS:
                        attribution_confidences.append(confidence)
            reason = str(result.get("review_reason") or "").strip()
            if reason:
                model_review_reasons.append(reason)

        minimum = float(profile.get("min_metadata_confidence") or 0.72)
        for field in sorted(EVIDENCE_REQUIRED_FIELDS):
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
            elif float(evidence_confidence) < minimum:
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
            if current.get("status") in {"deterministic", "inherited", "human_confirmed", "human_override"}:
                continue
            assessment = field_assessments.get(field) if isinstance(field_assessments.get(field), dict) else {}
            evidence_info = clean_evidence.get(field) if isinstance(clean_evidence.get(field), dict) else {}
            assessment_confidence = assessment.get("confidence") if isinstance(assessment.get("confidence"), (int, float)) else None
            evidence_confidence = evidence_info.get("confidence") if isinstance(evidence_info.get("confidence"), (int, float)) else None
            confidence = float(assessment_confidence if assessment_confidence is not None else evidence_confidence) if (assessment_confidence is not None or evidence_confidence is not None) else None
            needs_human = bool(assessment.get("needs_review"))
            field_status[field] = {
                "status": "unresolved" if needs_human else "llm_inferred",
                "method": "llm",
                "confidence": confidence,
                "reason_code": "ambiguous" if needs_human else "resolved",
                "reason": str(assessment.get("reason") or evidence_info.get("reason") or "Model proposal."),
            }
        review_metadata_fields = list(profile.get("review_metadata_fields") or REVIEW_METADATA_FIELDS)
        for field in review_metadata_fields:
            value = record.get(field)
            current = field_status.get(field) if isinstance(field_status.get(field), dict) else {}
            if current.get("status") in {"deterministic", "inherited", "human_confirmed", "human_override"}:
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
            if field in required_metadata_fields and value in (None, "", []):
                field_status[field] = {"status": "unresolved", "method": "hybrid", "confidence": confidence, "reason_code": "ambiguous", "reason": reason}
            elif (confidence is None or confidence < minimum) and value not in (None, "", []):
                # Model self-confidence is never publication authority. Any LLM
                # proposal below the profile threshold is routed to the human
                # exception queue even when the model forgot to set needs_review.
                field_status[field] = {"status": "unresolved", "method": "llm", "confidence": confidence, "reason_code": "low_confidence", "reason": reason or f"Model confidence is below {minimum:.2f}."}
            elif needs_human or (value not in (None, "", []) and field in EVIDENCE_REQUIRED_FIELDS and (not evidence_info.get("block_ids") or not isinstance(evidence_info.get("confidence"), (int, float)) or float(evidence_info.get("confidence")) < minimum)):
                field_status[field] = {"status": "unresolved", "method": "llm", "confidence": confidence, "reason_code": "ambiguous" if needs_human else "evidence_failed", "reason": reason}
            else:
                field_status[field] = {"status": "llm_inferred", "method": "llm", "confidence": confidence, "reason_code": "resolved", "reason": reason}

        apply_metadata_constraints(record)
        record["semantic_classification_confidence"] = round(sum(evidence_confidences) / len(evidence_confidences), 4) if evidence_confidences else None
        record["attribution_confidence"] = round(min(attribution_confidences), 4) if attribution_confidences else 1.0
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
            required_discourse = [field for field in required_metadata_fields if field in METADATA_FAMILY_FIELDS["discourse"]]
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
        suspicious: list[dict[str, Any]] = []
        previous_last = -1
        min_conf = float(profile.get("min_metadata_confidence") or 0.72)

        for record in records:
            record_id = str(record.get("record_id") or "")
            ids = [str(value) for value in record.get("source_block_ids") or []]
            expected = "\n\n".join(
                block_map[block_id]["text"].strip()
                for block_id in ids
                if block_id in block_map and block_map[block_id]["text"].strip()
            )
            fidelity_text = record.get("source_extracted_text") if record.get("text_review_status") == "human_corrected" else record.get("text")
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

            evidence = record.get("metadata_evidence") if isinstance(record.get("metadata_evidence"), dict) else {}
            valid_ids = set(ids)
            for field in ATTRIBUTION_EVIDENCE_FIELDS:
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
        metadata_valid = not evidence_errors and not citation_errors and not printed_page_errors and not metadata_schema_errors
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
            "citation_errors": sorted(set(citation_errors)),
            "suspicious_record_sizes": suspicious,
            "source_valid": source_valid,
            "metadata_valid": metadata_valid,
            "valid": source_valid and metadata_valid,
        }

    def _run(self, build_id: str, request: dict[str, Any], resume: bool = False) -> None:
        try:
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
            if bool(request.get("review_manifest_before_segmentation", False)) and not manifest_build.get("manifest_confirmed_at"):
                self._update(
                    build_id,
                    status="awaiting_manifest_review",
                    stage="document_review",
                    progress=0.12,
                    finished_at=iso_now(),
                    resumable=True,
                    error=None,
                )
                return

            # The reviewed manifest defines the semantic-analysis region. Source
            # blocks outside it remain in the persisted source asset for audit.
            source_blocks = self._manifest_main_text_blocks(blocks, manifest)
            source_quality = self._source_quality_report(source_blocks)
            self._update(build_id, source_quality=source_quality)
            semantic_blocks = self._semantic_atoms(source_blocks)
            if len(semantic_blocks) < 2:
                semantic_blocks = source_blocks
            self._update(
                build_id, stage="segmenting", progress=max(float(build.get("progress") or 0), 0.12),
                semantic_atom_count=len(semantic_blocks), main_text_block_count=len(source_blocks),
            )
            previous_build = self.repo.get_build(build_id)
            # A segmentation-blocked build intentionally has no authoritative final
            # boundary checkpoint. Resume retries unresolved semantic regions using
            # the currently selected provider/settings instead of reusing the
            # partial topology that caused the block.
            boundaries = None
            if resume and not previous_build.get("segmentation_blocked"):
                boundaries = self.repo.load_checkpoint(build_id, "boundaries")
            if not isinstance(boundaries, list):
                boundaries = self._segment(semantic_blocks, manifest, request, build_id)
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            self._update(build_id, retrying_segmentation=False)
            self.repo.save_checkpoint(build_id, "boundaries", boundaries)

            records = self.repo.load_records(build_id) if resume else []
            if not records:
                records = self._construct_records(asset, source_blocks, boundaries)
                self._mark_segmentation_review(records, list(self.repo.get_build(build_id).get("segmentation_unresolved_regions") or []))
                for record in records:
                    self._apply_manifest_metadata(record, manifest)
                    inline, full = _citation_strings(record)
                    record["inline_citation"] = inline
                    record["full_citation"] = full
                # Validate topology before spending time on metadata enrichment.
                # At this point all source-derived text and boundaries are deterministic;
                # any failure is therefore an implementation/topology problem, not an
                # invitation to burn more LLM calls and ask the user to clean it up.
                active_profile = CORPUS_PROFILES[str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)]
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
            self._update(build_id, stage="enriching", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42), boundary_count=len(boundaries), record_count=len(records), source_problem_count=sum(1 for record in records if record.get("source_quality_issues")))

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

            def family_states_for(rows: list[dict[str, Any]]) -> list[str]:
                states: list[str] = []
                for row in rows:
                    row_status = row.get("metadata_stage_status") if isinstance(row.get("metadata_stage_status"), dict) else {}
                    for family in metadata_families:
                        fallback = "complete" if row.get("metadata_complete") else "queued"
                        states.append(str(row_status.get(family) or fallback))
                return states

            initial_states = family_states_for(records)
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
                """Atomically checkpoint one family and refresh live task telemetry."""
                record_id = str(snapshot.get("record_id") or "")
                with self._lock:
                    live_records = self.repo.load_records(build_id)
                    live_index = next((i for i, row in enumerate(live_records) if str(row.get("record_id") or "") == record_id), None)
                    if live_index is None:
                        return
                    copy = json.loads(json.dumps(snapshot))
                    copy["metadata_enrichment_state"] = "running" if state == "running" else str(copy.get("metadata_enrichment_state") or "running")
                    live_records[live_index] = self._merge_enrichment_snapshot(live_records[live_index], copy)
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
                            profile_for_failure = CORPUS_PROFILES.get(str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
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
                                live_records[live_index] = self._merge_enrichment_snapshot(live_records[live_index], records[index])
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
            settled_states = family_states_for(settled_records)
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

            # All automatic workers have now settled. Recompute the authoritative
            # record/metadata queues once before handing control to human review so
            # the first review screen is already internally consistent.
            self._rewrite_and_validate(build_id, records)
            records = self.repo.load_records(build_id)
            profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
            validation = self.validate_records(source_blocks, records, profile)
            needs_review = sum(1 for record in records if record.get("needs_review"))
            boundary_review_count = len(self.repo.get_build(build_id).get("segmentation_boundary_reviews") or [])
            # Construction is complete, but the corpus lifecycle is not complete
            # until review/acceptance and publication finish. Keep a clear 90%
            # handoff into human review instead of declaring 100% prematurely.
            status = "awaiting_review"
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
            )
        except InterruptedError as exc:
            self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True, retrying_segmentation=False)
        except Exception as exc:
            # Checkpoints intentionally survive a failed stage. The user can repair
            # provider configuration and resume instead of restarting a long book.
            self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc), resumable=True, retrying_segmentation=False)
        finally:
            with self._lock:
                self._cancel.discard(build_id)

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
        for record in records:
            if not record.get("review_disposition"):
                record["review_disposition"] = "accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"
            record["rejected"] = str(record.get("review_disposition")) == "rejected"
        blocks = [
            block for block in self.repo.load_blocks(build["asset_id"])
            if not block.get("excluded_reason")
        ]
        blocks = self._manifest_main_text_blocks(blocks, build.get("manifest") or {})
        build["source_quality"] = self._source_quality_report(blocks)
        profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
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
        contribution = Counter()
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
        blockers = bool(build["needs_review_count"] or build.get("rejected_count") or build["boundary_review_count"] or not validation.get("valid"))
        records_accepted = bool(build["record_count"] and build["accepted_count"] == build["record_count"] and not build["needs_review_count"] and not build.get("rejected_count") and not build["boundary_review_count"])
        metadata_total = int(build.get("metadata_total") or 0)
        metadata_completed = int(build.get("metadata_completed") or 0)
        metadata_complete = metadata_total == 0 or metadata_completed >= metadata_total
        all_ready = bool(records_accepted and metadata_complete and not blockers)
        # Automated construction owns the first 90% of lifecycle progress. Human
        # review may begin progressively during book-length metadata enrichment,
        # but a review mutation must never make the build look as though the
        # background enrichment job has stopped. Preserve the running stage until
        # the coordinator itself performs the final handoff to review.
        if automation_running:
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

    def patch_manifest(self, build_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            stage = str(build.get("stage") or "")
            if stage not in {"enriching", "metadata_retry"}:
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
        build["manifest"] = manifest
        build["manifest_revision"] = current_revision + 1
        build["manifest_reviewed_at"] = iso_now()
        self.repo.save_checkpoint(build_id, "manifest", manifest)
        self.repo.save_build(build)

        records = self.repo.load_records(build_id)
        if records:
            for record in records:
                field_status = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
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

    def _editorial_context(self, build_id: str, *, exclude_record_id: str = "") -> dict[str, Any]:
        """Return conservative build-local conventions derived from repeated human decisions.

        A one-off record correction is never generalized. A value becomes prompt context
        only after at least two distinct records have received the same human-confirmed
        value. The context is advisory for untouched fields and is never applied directly.
        """
        try:
            rows = self.repo.load_records(build_id)
        except Exception:
            return {}
        counts: dict[str, dict[str, tuple[Any, int]]] = {}
        for row in rows:
            if exclude_record_id and str(row.get("record_id") or "") == exclude_record_id:
                continue
            statuses = row.get("metadata_field_status") if isinstance(row.get("metadata_field_status"), dict) else {}
            for field, info in statuses.items():
                if not isinstance(info, dict) or str(info.get("status") or "") not in {"human_confirmed", "human_override"}:
                    continue
                value = row.get(field)
                if value in (None, "", []):
                    continue
                key = json.dumps(value, ensure_ascii=False, sort_keys=True)
                prior = counts.setdefault(str(field), {}).get(key)
                counts[str(field)][key] = (value, (prior[1] if prior else 0) + 1)
        conventions: dict[str, Any] = {}
        for field, values in counts.items():
            ranked = sorted(values.values(), key=lambda item: item[1], reverse=True)
            if ranked and ranked[0][1] >= 2:
                conventions[field] = {"value": ranked[0][0], "confirmed_records": ranked[0][1]}
        return conventions

    @classmethod
    def _merge_enrichment_snapshot(cls, live: dict[str, Any], worker: dict[str, Any]) -> dict[str, Any]:
        """Merge automatic enrichment into current human state without overwriting it."""
        merged = json.loads(json.dumps(live))
        live_status = live.get("metadata_field_status") if isinstance(live.get("metadata_field_status"), dict) else {}
        worker_status = worker.get("metadata_field_status") if isinstance(worker.get("metadata_field_status"), dict) else {}
        touched_markers = set(str(v) for v in (live.get("human_touched_fields") or []))
        text_was_touched = "__text__" in touched_markers
        record_frozen_by_review = "__review__" in touched_markers
        automatic_merge_blocked = text_was_touched or record_frozen_by_review
        for field in ALLOWED_METADATA_FIELDS:
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
            "semantic_classification_confidence", "attribution_confidence",
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
            if stage in {"enriching", "metadata_retry", "review"} and not structural:
                return build
            raise ValueError("Records are not editable until segmentation is complete. Structural merge/split operations wait until background enrichment stops.")
        return build

    def _assert_record_revision(self, record: dict[str, Any], expected_revision: int | None) -> int:
        current_revision = int(record.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before continuing.")
        return current_revision

    def _save_review_undo(self, build_id: str, records: list[dict[str, Any]], *, action: str, selected_record_id: str) -> None:
        # Single-level structural undo is deliberately stored outside build.json so
        # large record snapshots do not bloat normal build reads.
        self.repo.save_checkpoint(build_id, "review_undo", {
            "action": action,
            "selected_record_id": selected_record_id,
            "created_at": iso_now(),
            "records": records,
        })

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
        profile = CORPUS_PROFILES.get(str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
        self._sync_record_metadata_state(target, profile)
        if disposition == "accepted" and target.get("source_quality_issues"):
            raise ValueError("Resolve the source extraction problem before accepting this record.")
        if disposition == "accepted" and (list(target.get("metadata_review_fields") or []) or list(target.get("metadata_incomplete_fields") or [])):
            raise ValueError("Resolve the queued record metadata before accepting this record.")
        if disposition == "accepted":
            status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
            for field in REVIEW_METADATA_FIELDS:
                info = status_map.get(field) if isinstance(status_map.get(field), dict) else None
                if info and info.get("status") == "llm_inferred":
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
        profile = CORPUS_PROFILES.get(str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
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
        if disposition == "accepted":
            status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
            for field in REVIEW_METADATA_FIELDS:
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
            profile = CORPUS_PROFILES.get(str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
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
                for field in REVIEW_METADATA_FIELDS:
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
        checkpoint = self.repo.load_checkpoint(build_id, "review_undo", None)
        if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("records"), list):
            raise KeyError(build_id)
        records = checkpoint["records"]
        self._rewrite_and_validate(build_id, records)
        # Consuming the snapshot prevents an accidental second undo from applying stale topology.
        self.repo.save_checkpoint(build_id, "review_undo", {"consumed_at": iso_now()})
        return {"restored": True, "action": checkpoint.get("action"), "selected_record_id": checkpoint.get("selected_record_id"), "record_count": len(records)}

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
        forbidden = sorted(set(changes) - HUMAN_EDITABLE_METADATA_FIELDS)
        if forbidden:
            raise ValueError(
                "Source-bound fields cannot be edited as record metadata. These system/source-bound fields are protected: "
                + ", ".join(forbidden)
            )
        # Validate the editable interpretive schema before modifying the persisted record.
        schema_input = {key: value for key, value in changes.items() if key in RecordMetadataModel.model_fields}
        try:
            RecordMetadataModel.model_validate(schema_input)
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
        decision_log = list(target.get("metadata_decisions") or [])
        for key, value in changes.items():
            target[key] = value
            status = target.setdefault("metadata_field_status", {})
            if key in HUMAN_EDITABLE_METADATA_FIELDS:
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
        self._mark_human_touch(target, list(changes))
        profile = CORPUS_PROFILES.get(str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
        self._sync_record_metadata_state(target, profile)
        target["record_revision"] = current_revision + 1
        build = self._rewrite_and_validate(build_id, records)
        # Return the record as persisted after authoritative state derivation.
        persisted = next((row for row in self.repo.load_records(build_id) if row.get("record_id") == record_id), target)
        self._decorate_review_state(persisted)
        return persisted

    @_serialize_record_mutation
    def bulk_patch_metadata(
        self, build_id: str, changes: dict[str, Any], *, record_ids: list[str] | None = None,
        apply_to_all: bool = False, review_queue: str | None = None, query: str = "",
    ) -> dict[str, Any]:
        if not changes:
            raise ValueError("Choose at least one metadata field to update.")
        forbidden = sorted(set(changes) - HUMAN_EDITABLE_METADATA_FIELDS)
        if forbidden:
            raise ValueError("Unsupported bulk metadata field(s): " + ", ".join(forbidden))
        schema_input = {key: value for key, value in changes.items() if key in RecordMetadataModel.model_fields}
        try:
            RecordMetadataModel.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid bulk metadata: {exc}") from exc
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        wanted = {str(value) for value in (record_ids or []) if str(value)}
        query_l = str(query or "").strip().casefold()
        changed_ids: list[str] = []
        profile = CORPUS_PROFILES.get(str(build.get("profile_id") or PROFILE_VERSION), CORPUS_PROFILES[PROFILE_VERSION])
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
    def metadata_decision(self, build_id: str, record_id: str, field: str, value: Any, expected_revision: int | None = None) -> dict[str, Any]:
        """Persist one human metadata decision and return authoritative review state.

        This endpoint is deliberately transactional from the UI's perspective:
        one call saves the value, marks the field human-confirmed, recomputes all
        derived metadata/queue state, and returns the updated record and build.
        """
        if field not in HUMAN_EDITABLE_METADATA_FIELDS or field in {"needs_review", "review_reason"}:
            raise ValueError(f"Unsupported review metadata field: {field}")
        record = self.patch_metadata(build_id, record_id, {field: value}, expected_revision)
        records = self.repo.load_records(build_id)
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
        if field not in ATTRIBUTION_EVIDENCE_FIELDS and field not in RecordMetadataModel.model_fields:
            raise ValueError(f"Unsupported metadata evidence field: {field}")
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        self._assert_human_review_available(build_id, target)
        current_revision = int(target.get("record_revision") or 1)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("This record changed after it was opened. Reload it before editing evidence.")
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

    @_serialize_record_mutation
    def rerun_metadata(self, build_id: str, record_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        requested_families = request.get("families")
        families = [str(value) for value in requested_families or [] if str(value) in METADATA_FAMILY_FIELDS]
        if not families:
            families = ["discourse", "quotation", "indexing"]
        # Clear only values owned by the selected LLM family. Inherited,
        # deterministic, human-confirmed, and human-override values are
        # authoritative and survive reruns.
        status_map = target.get("metadata_field_status") if isinstance(target.get("metadata_field_status"), dict) else {}
        for family in families:
            for key in METADATA_FAMILY_FIELDS[family]:
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
        """Validate the stable public JSONL contract before bytes are written."""
        errors: list[str] = []
        record_id = str(record.get("record_id") or "").strip()
        if not record_id:
            errors.append("record_id is required")
        if not isinstance(record.get("text"), str) or not str(record.get("text") or "").strip():
            errors.append("text is required")
        source_ids = record.get("source_block_ids")
        if not isinstance(source_ids, list) or not source_ids or not all(isinstance(value, str) and value for value in source_ids):
            errors.append("source_block_ids must be a non-empty string array")
        details = record.get("corpus_build_details")
        if not isinstance(details, dict):
            errors.append("corpus_build_details is required")
        else:
            for field in ("build_id", "publication_id", "published_at", "app_version", "schema_version", "publication_schema_version", "profile_id", "source_sha256"):
                if details.get(field) in (None, ""):
                    errors.append(f"corpus_build_details.{field} is required")
        region = record.get("region_type")
        if region not in (None, "") and str(region) not in REGION_TYPES:
            errors.append(f"region_type is not a supported enum value: {region}")
        role = record.get("discourse_role")
        if role not in (None, "") and str(role) not in DISCOURSE_ROLES:
            errors.append(f"discourse_role is not a supported enum value: {role}")
        primary = record.get("primary_text")
        if primary is not None and not isinstance(primary, bool):
            errors.append("primary_text must be boolean when present")
        return errors

    def _publication_build_details(self, build: dict[str, Any], publication_id: str, created_at: str) -> dict[str, Any]:
        """Return locale-neutral build provenance embedded in every public record.

        Publication metadata belongs under one stable object instead of leaking
        build/runtime fields into the scholarly record namespace.
        """
        request = build.get("request") or {}
        return {
            "build_id": build.get("build_id"),
            "publication_id": publication_id,
            "published_at": created_at,
            "app_version": build.get("app_version"),
            "schema_version": build.get("schema_version"),
            "publication_schema_version": PUBLICATION_SCHEMA_VERSION,
            "profile_id": build.get("profile_id"),
            "profile_version": build.get("profile_version"),
            "source_asset_id": build.get("asset_id"),
            "source_sha256": build.get("source_sha256"),
            "source_filename": build.get("source_filename"),
            "provider_profile_id": request.get("provider_profile_id"),
            "provider": build.get("provider"),
            "model": build.get("model"),
            "document_prompt_version": build.get("document_prompt_version"),
            "segmentation_prompt_version": build.get("segmentation_prompt_version"),
            "metadata_prompt_version": build.get("metadata_prompt_version"),
            "record_sizing_policy": build.get("record_sizing_policy") or request.get("record_sizing"),
            "topology_quality": build.get("topology_quality"),
        }

    @_serialize_record_mutation
    def publish(self, build_id: str, *, require_acceptance: bool = True) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        validation = build.get("validation") or {}
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
        unresolved = [record for record in records if record.get("needs_review")]
        if unresolved:
            raise ValueError(f"Publication is blocked: {len(unresolved)} record(s) still need review.")
        rejected = [record for record in records if str(record.get("review_disposition") or "") == "rejected" or record.get("rejected")]
        if rejected:
            raise ValueError(f"Publication is blocked: {len(rejected)} record(s) were rejected and require correction or removal through topology review.")
        if require_acceptance:
            unaccepted = [record for record in records if not record.get("accepted")]
            if unaccepted:
                raise ValueError(f"Publication is blocked: {len(unaccepted)} record(s) have not been accepted.")
        publication_id = f"publication-{build_id.removeprefix('build-')}-{uuid.uuid4().hex[:8]}"
        created_at = iso_now()
        build_details = self._publication_build_details(build, publication_id, created_at)
        path = self.repo.publication_path(publication_id)
        hasher = hashlib.sha256()
        with path.open("wb") as handle:
            for record in records:
                # UI-only review state is not published. Build/run provenance is
                # namespaced so the main record remains a scholarly record schema.
                build_only_fields = {
                    "accepted", "rejected", "review_disposition", "build_id", "publication_id",
                    "app_version", "schema_version", "profile_id", "profile_version",
                    "provider_profile_id", "provider", "model", "document_prompt_version",
                    "segmentation_prompt_version", "metadata_prompt_version",
                    "record_sizing_policy", "topology_quality",
                }
                public = {k: v for k, v in record.items() if k not in build_only_fields}
                public["corpus_build_details"] = build_details
                schema_errors = self._validate_publication_record(public)
                if schema_errors:
                    joined = "; ".join(schema_errors[:8])
                    raise ValueError(f"Publication schema validation failed for {public.get('record_id') or 'unknown record'}: {joined}")
                line = (json.dumps(public, ensure_ascii=False) + "\n").encode("utf-8")
                hasher.update(line)
                handle.write(line)
        publication = {"publication_id": publication_id, "filename": f"{Path(build.get('source_filename') or 'corpus').stem}.jsonl", "sha256": hasher.hexdigest(), "record_count": len(records), "created_at": created_at}
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
