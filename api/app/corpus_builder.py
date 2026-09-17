# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import APP_VERSION, settings
from .models import OllamaTouchupOptions, WorkMetadataRequest, WorkMetadataSeed
from .rag import _citation_strings, _extract_json, chat_complete

SCHEMA_VERSION = "pdf-corpus-v3"
SEGMENTATION_PROMPT_VERSION = "derridai-local-boundaries-v6"
METADATA_PROMPT_VERSION = "derridai-record-metadata-v3"
DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v2"
PROFILE_VERSION = "derrida-scholarly-v6"


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
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
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
    region_type: str | None = None
    region_author: str | None = None
    speaker: str | None = None
    position_holder: str | None = None
    target: str | None = None
    discourse_role: str | None = None
    proposition_status: str | None = None
    semantic_function: list[str] = Field(default_factory=list, max_length=12)
    stance: str | None = None
    claim_scope: str | None = None


class DiscourseMetadataResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: DiscourseMetadataModel = Field(default_factory=DiscourseMetadataModel)
    field_evidence: dict[str, FieldEvidenceModel] = Field(default_factory=dict)
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
    review_reason: str = Field(default="", max_length=1000)


ATTRIBUTION_EVIDENCE_FIELDS = {
    "speaker", "position_holder", "target", "stance", "proposition_status",
    "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
    "quoted_addressee", "quoted_referent", "quotation_chain",
}

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

MANIFEST_INHERITED_FIELDS = {
    "work", "document_title", "short_title", "original_title", "canonical_work_id",
    "document_author", "translator", "edition", "year", "publication_year", "publisher",
    "publication_place", "isbn", "document_language", "original_language",
    "document_is_translation", "primary_text",
}

HUMAN_EDITABLE_METADATA_FIELDS = {
    "language", "region_type", "region_author", "speaker",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _json_read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00ad", "")).strip()


def _block_text(block: dict[str, Any]) -> str:
    if "lines" in block:
        chunks: list[str] = []
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            text = "".join(str(span.get("text") or "") for span in spans)
            if text.strip():
                chunks.append(text.rstrip())
        return "\n".join(chunks).strip()
    return str(block.get("text") or "").strip()


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
        path = self.build_records_path(build_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(tmp, path)

    def load_records(self, build_id: str) -> list[dict[str, Any]]:
        self.get_build(build_id)
        path = self.build_records_path(build_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def page_records(self, build_id: str, *, offset: int = 0, limit: int = 50, needs_review: bool | None = None, query: str = "") -> dict[str, Any]:
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
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if needs_review is not None and bool(record.get("needs_review")) is not needs_review:
                    continue
                if q and q not in line.casefold():
                    continue
                if total >= offset and len(items) < limit:
                    items.append(record)
                total += 1
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    def publication_path(self, publication_id: str) -> Path:
        return self.root / "publications" / f"{publication_id}.jsonl"


CORPUS_PROFILES: dict[str, dict[str, Any]] = {
    "derrida-scholarly-v1": {
        "id": "derrida-scholarly-v1",
        "name": "Derrida scholarly corpus v1 (legacy)",
        "version": 1,
        "description": "Legacy 0.40.0 semantic/discourse profile retained for historical build compatibility.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 18000,
        "topology_review_chars": 36000,
    },
    "derrida-scholarly-v2": {
        "id": "derrida-scholarly-v2",
        "name": "Derrida scholarly corpus v2 (legacy)",
        "version": 2,
        "description": "0.40.1 typed semantic/discourse profile retained for historical build compatibility.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 18000,
        "topology_review_chars": 36000,
    },
    "derrida-scholarly-v3": {
        "id": "derrida-scholarly-v3",
        "name": "Derrida scholarly corpus v3 (legacy)",
        "version": 3,
        "description": "0.40.5/0.40.6 compact semantic segmentation profile retained for historical build compatibility.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 18000,
        "topology_review_chars": 36000,
    },
    "derrida-scholarly-v5": {
        "id": "derrida-scholarly-v5",
        "name": "Derrida scholarly corpus v5 (legacy)",
        "version": 5,
        "description": "0.40.8 deterministic topology with local LLM boundary classification, retained so existing 0.40.8 builds remain resumable and auditable.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 9000,
        "topology_review_chars": 12000,
    },
    PROFILE_VERSION: {
        "id": PROFILE_VERSION,
        "name": "Derrida scholarly corpus v6",
        "version": 6,
        "description": "Conservative deterministic-first topology: obvious seams are handled locally, ambiguous high-value seams are batch-adjudicated, uncertainty defaults to KEEP, and human review is reserved for demonstrated provenance hazards.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "candidate_llm_threshold": 0.30,
        "deterministic_split_threshold": 0.92,
        "review_risk_threshold": 0.90,
        "max_llm_boundary_calls_per_100_atoms": 18,
        "boundary_batch_size": 6,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 9000,
        "topology_review_chars": 12000,
    }
}


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
        build["operation_hidden"] = False

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
        return {
            "id": str(build.get("build_id") or ""),
            "type": "pdf_corpus",
            "kind": "pdf_corpus",
            "label": f"PDF corpus · {build.get('source_filename') or 'source'}",
            "status": status,
            "raw_status": raw_status,
            "stage": build.get("stage"),
            "stage_detail": (
                f"Retrying {len(unresolved)} unresolved segmentation region(s)"
                if raw_status in {"queued", "running"} and build.get("retrying_segmentation")
                else f"{len(unresolved)} unresolved segmentation region(s)"
                if build.get("segmentation_blocked")
                else str(build.get("stage") or raw_status).replace("_", " ")
            ),
            "provider": build.get("provider"),
            "model": build.get("model"),
            "provider_profile_id": (build.get("request") or {}).get("provider_profile_id"),
            "max_concurrent_requests": (build.get("request") or {}).get("max_concurrent_requests", 1),
            "request": build.get("request") or {},
            "source_filename": build.get("source_filename"),
            "build_id": build.get("build_id"),
            "record_count": int(build.get("record_count") or 0),
            "review_count": int(build.get("needs_review_count") or 0),
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

    def _cancelled(self, build_id: str) -> bool:
        with self._lock:
            return build_id in self._cancel

    def _update(self, build_id: str, *, stage: str | None = None, progress: float | None = None, **changes: Any) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if stage is not None:
            build["stage"] = stage
        if progress is not None:
            build["progress"] = max(0.0, min(1.0, float(progress)))
        build.update(changes)
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
        build = self.repo.get_build(build_id)
        warnings = list(build.get("warnings") or [])
        if message not in warnings:
            warnings.append(message)
        build["warnings"] = warnings[-100:]
        self.repo.save_build(build)

    def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None:
        if not build_id:
            return
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
        attempts: int = 3,
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
                    )
                except InterruptedError:
                    raise
                except Exception as exc:
                    failure = exc
                    diagnostic = ""
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

    @staticmethod
    def _topology_sanity(records: list[dict[str, Any]], hard_max: int) -> dict[str, Any]:
        sizes=[int(r.get("text_length") or len(str(r.get("text") or ""))) for r in records]
        issues=[]
        if not records:
            issues.append("no_records")
        if any(size <= 0 for size in sizes):
            issues.append("empty_record")
        if any(size > int(hard_max*1.15) for size in sizes):
            issues.append("oversized_record")
        return {
            "valid":not issues,
            "issues":issues,
            "record_count":len(records),
            "max_record_chars":max(sizes,default=0),
            "median_record_chars":sorted(sizes)[len(sizes)//2] if sizes else 0,
        }

    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        """Build topology with deterministic-first routing and bounded LLM work.

        Human review is no longer an output of ordinary model uncertainty. The
        builder owns the topology: protected/weak seams KEEP, obvious structural
        seams SPLIT, and only a budgeted ambiguous subset reaches the LLM. The
        binary classifier's omission/failure/low confidence also means KEEP.
        """
        profile=CORPUS_PROFILES[str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)]
        threshold=float(profile.get("min_boundary_confidence") or 0.72)
        hard_max=max(12000,int(profile.get("topology_review_chars") or 36000))
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

        # Reuse only provenance-compatible local decisions. Old 0.40.8 checkpoints
        # cannot silently affect 0.40.9 topology because the fingerprint contains
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

        provisional=[]
        while True:
            span=next((g for g in grouped(accepted+provisional) if len(g)>1 and sum(len(str(b.get("text") or "")) for b in g)>hard_max),None)
            if span is None: break
            choice,forced_protected=self._best_safety_boundary(span,hard_max)
            boundary={"after_block_id":str(choice.get("block_id") or ""),"decision":"split","confidence":0.0,"changes":[],"provisional":True,"source":"best_local_size_safety_split"}
            if any(str(item.get("after_block_id") or "")==boundary["after_block_id"] for item in accepted+provisional): break
            provisional.append(boundary)
            if forced_protected:
                idx=index_by_id.get(boundary["after_block_id"],-1)
                boundary_reviews.append({"after_block_id":boundary["after_block_id"],"next_block_id":str(blocks[idx+1].get("block_id") or "") if 0<=idx<len(blocks)-1 else "","kind":"forced_protected_size_split","reason":"Every nearby seam was attribution/syntax-protected; a hard-size split was unavoidable and this exact provenance hazard requires human review."})

        accepted.extend(provisional)
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
        title = manifest.get("title")
        author = manifest.get("document_author")
        translator = manifest.get("translator")
        edition = manifest.get("edition") or manifest.get("publisher")
        year = manifest.get("publication_year")
        language = manifest.get("language")
        original_language = manifest.get("original_language")
        if title:
            record["work"] = title
            record["document_title"] = title
            record["canonical_work_id"] = re.sub(r"[^a-z0-9]+", "-", str(title).casefold()).strip("-")[:120]
        if manifest.get("short_title"):
            record["short_title"] = manifest.get("short_title")
        if manifest.get("original_title"):
            record["original_title"] = manifest.get("original_title")
        if author:
            record["document_author"] = author
        if translator:
            record["translator"] = translator
        if edition:
            record["edition"] = edition
        if manifest.get("publisher"):
            record["publisher"] = manifest.get("publisher")
        if manifest.get("publication_place"):
            record["publication_place"] = manifest.get("publication_place")
        if manifest.get("isbn"):
            record["isbn"] = manifest.get("isbn")
        if year is not None:
            try:
                parsed_year = int(year)
                record["year"] = parsed_year
                record["publication_year"] = parsed_year
            except (TypeError, ValueError):
                record["publication_year"] = year
        if language:
            record["document_language"] = [str(language)]
            record.setdefault("language", str(language))
        if original_language:
            record["original_language"] = [str(original_language)]
        if manifest.get("document_is_translation") is not None:
            record["document_is_translation"] = bool(manifest.get("document_is_translation"))

        start_page = manifest.get("main_text_start_page")
        end_page = manifest.get("main_text_end_page")
        pdf_pages = [int(value) for value in record.get("pdf_pages") or [] if isinstance(value, int)]
        if pdf_pages and isinstance(start_page, int):
            inside = min(pdf_pages) >= start_page and (not isinstance(end_page, int) or max(pdf_pages) <= end_page)
            record["primary_text"] = inside
            if inside:
                record["region_type"] = "main_text"
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
    ) -> dict[str, Any]:
        """Infer interpretive metadata through several small structured tasks.

        A single all-fields JSON object proved fragile with local models: one
        truncated brace could invalidate every metadata dimension.  The staged
        design keeps output schemas small, preserves successful partial work, and
        makes retries/escalation local to the failed metadata family.
        """
        self._apply_manifest_metadata(record, manifest)
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

        base_context = f"""Document manifest: {json.dumps(manifest, ensure_ascii=False)}
Neighbor context (context only; never cite it as evidence): {json.dumps(neighbor_context, ensure_ascii=False)}
Current source block IDs: {source_id_json}
CURRENT RECORD TEXT (immutable):
{source_text}
"""
        stage_results: list[tuple[str, dict[str, Any] | None, Exception | None]] = []

        discourse_prompt = f"""Infer ONLY discourse/attribution metadata for one immutable DerridAI record.
Distinguish the grammatical/textual speaker from the POSITION HOLDER whose proposition is being presented. A named person is not automatically a speaker or position holder. Preserve modality, negation, uncertainty, and stance. Do not return quotation relations, topical indexing, bibliographic metadata, summaries, or source text.

{base_context}
For every populated attribution-bearing field in this task (speaker, position_holder, target, stance, proposition_status), include field_evidence using only current-record block IDs, confidence 0..1, and a short reason. Use null or [] when unsupported.
"""
        quotation_prompt = f"""Infer ONLY quotation relations for one immutable DerridAI record.
Determine whether there is direct quotation and, only when source-supported, identify quoted speaker/author/work/position-holder/addressee/referent and quotation chains. A mentioned name is not automatically a quoted source. Do not return discourse fields, topical indexing, bibliographic metadata, summaries, or source text.

{base_context}
For every populated quoted_* or quotation_chain field, include field_evidence using only current-record block IDs, confidence 0..1, and a short reason. Use [] when unsupported.
"""
        indexing_prompt = f"""Infer ONLY conservative semantic indexing metadata for one immutable DerridAI record.
Return topics, concepts, persons, and works_referenced that are materially present in this record. Do not infer discourse attribution, quotation ownership, bibliography, summaries, or source text. Prefer a short precise list to speculative coverage.

{base_context}
"""

        tasks = [
            ("discourse", discourse_prompt, DiscourseMetadataResponseModel, limits["discourse_num_predict"], "derridai_record_discourse"),
            ("quotation", quotation_prompt, QuotationMetadataResponseModel, limits["quotation_num_predict"], "derridai_record_quotation"),
            ("indexing", indexing_prompt, IndexMetadataResponseModel, limits["indexing_num_predict"], "derridai_record_indexing"),
        ]
        for task_name, prompt, response_model, max_tokens, schema_name in tasks:
            try:
                result = self._chat_json(
                    request,
                    prompt,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    schema_name=schema_name,
                    build_id=build_id,
                )
                stage_results.append((task_name, result, None))
            except InterruptedError:
                raise
            except Exception as exc:
                stage_results.append((task_name, None, exc))
                if build_id:
                    self._append_warning(build_id, f"{record.get('record_id')}: {task_name} metadata requires review ({exc})")

        clean_evidence: dict[str, Any] = dict(record.get("metadata_evidence") or {})
        valid_ids = set(source_ids)
        review_reasons: list[str] = []
        evidence_confidences: list[float] = []
        attribution_confidences: list[float] = []
        model_review_reasons: list[str] = []
        successful_tasks = 0

        for task_name, result, failure in stage_results:
            if failure is not None or not isinstance(result, dict):
                review_reasons.append(f"{task_name} metadata extraction could not be validated: {failure}")
                continue
            successful_tasks += 1
            metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            for key, value in metadata.items():
                if key in ALLOWED_METADATA_FIELDS and key not in SOURCE_BOUND_FIELDS:
                    record[key] = value
            evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
            for field, info in evidence.items():
                if field not in ALLOWED_METADATA_FIELDS or not isinstance(info, dict):
                    continue
                block_ids = [str(value) for value in info.get("block_ids") or [] if str(value) in valid_ids]
                try:
                    confidence = max(0.0, min(1.0, float(info.get("confidence") or 0)))
                except (TypeError, ValueError):
                    confidence = 0.0
                clean_evidence[field] = {
                    "block_ids": block_ids,
                    "confidence": confidence,
                    "reason": str(info.get("reason") or ""),
                }
                evidence_confidences.append(confidence)
                if field in ATTRIBUTION_EVIDENCE_FIELDS:
                    attribution_confidences.append(confidence)
            reason = str(result.get("review_reason") or "").strip()
            if reason:
                model_review_reasons.append(reason)

        profile_id = PROFILE_VERSION
        if build_id:
            try:
                profile_id = str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)
            except Exception:
                pass
        minimum = float(CORPUS_PROFILES.get(profile_id, CORPUS_PROFILES[PROFILE_VERSION]).get("min_metadata_confidence") or 0.72)
        for field in sorted(ATTRIBUTION_EVIDENCE_FIELDS):
            value = record.get(field)
            if value in (None, "", []):
                continue
            info = clean_evidence.get(field)
            if not isinstance(info, dict):
                review_reasons.append(f"{field} has no bound source evidence")
                continue
            if not info.get("block_ids"):
                review_reasons.append(f"{field} evidence does not identify a current-record source block")
            if float(info.get("confidence") or 0) < minimum:
                review_reasons.append(f"{field} evidence confidence is below {minimum:.2f}")

        record["metadata_evidence"] = clean_evidence
        record["semantic_classification_confidence"] = round(sum(evidence_confidences) / len(evidence_confidences), 4) if evidence_confidences else 0.0
        record["attribution_confidence"] = round(min(attribution_confidences), 4) if attribution_confidences else 1.0
        review_reasons.extend(model_review_reasons)
        if review_reasons:
            record["needs_review"] = True
            prior = str(record.get("review_reason") or "").strip()
            combined = ([prior] if prior else []) + review_reasons
            record["review_reason"] = "; ".join(dict.fromkeys(value for value in combined if value))[:2400]
        record["metadata_complete"] = successful_tasks == len(tasks)
        record["metadata_stage_status"] = {
            task_name: ("complete" if failure is None else "needs_review")
            for task_name, _result, failure in stage_results
        }
        inline, full = _citation_strings(record)
        record["inline_citation"] = inline
        record["full_citation"] = full
        return record

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
            if _normalize_text(expected) != _normalize_text(record.get("text") or ""):
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
                hard_max = max(12000, int(active_profile.get("topology_review_chars") or 36000))
                topology_validation = self._topology_sanity(records, hard_max)
                current_build = self.repo.get_build(build_id)
                current_build["topology_validation"] = topology_validation
                self.repo.save_build(current_build)
                if not topology_validation.get("valid"):
                    raise RuntimeError(
                        "Deterministic topology sanity check failed before metadata enrichment: "
                        + ", ".join(topology_validation.get("issues") or ["unknown topology error"])
                    )
                # Persist deterministic records before any metadata call. A provider
                # failure can therefore never discard successful segmentation work.
                self.repo.save_records(build_id, records)
            self._update(build_id, stage="enriching", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42), boundary_count=len(boundaries), record_count=len(records))

            total = max(1, len(records))
            pending = [index for index, record in enumerate(records) if not record.get("metadata_complete")]
            already_complete = len(records) - len(pending)
            max_workers = max(1, min(16, int(request.get("max_concurrent_requests") or 1)))
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
                            records[index] = future.result()
                        except Exception as exc:
                            # A programming/provider failure in one metadata worker
                            # must never discard the other successfully enriched
                            # records in a book-length build. Preserve the immutable
                            # source-derived record and route this item to review.
                            fallback = dict(records[index])
                            fallback["metadata_complete"] = False
                            fallback["needs_review"] = True
                            reasons = [str(fallback.get("review_reason") or "").strip()]
                            reasons.append(f"Metadata worker failed and requires review: {exc}")
                            fallback["review_reason"] = " ".join(reason for reason in reasons if reason).strip()
                            records[index] = fallback
                            self._append_warning(build_id, f"{fallback.get('record_id')}: metadata worker failed; the source-bound record was preserved for review.")
                        completed += 1
                        # Persist each finished record in the coordinator thread. A
                        # provider/API restart therefore loses at most the calls that
                        # were actively in flight, never the completed book so far.
                        self.repo.save_records(build_id, records)
                        self._update(
                            build_id,
                            stage="enriching",
                            progress=0.42 + 0.43 * (completed / total),
                            metadata_completed=completed,
                            metadata_total=len(records),
                            metadata_concurrency=max_workers,
                        )

            profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
            validation = self.validate_records(source_blocks, records, profile)
            needs_review = sum(1 for record in records if record.get("needs_review"))
            boundary_review_count = len(self.repo.get_build(build_id).get("segmentation_boundary_reviews") or [])
            status = "awaiting_review" if needs_review or boundary_review_count or not validation.get("valid") else "ready"
            self._update(
                build_id,
                status=status,
                stage="review" if status == "awaiting_review" else "ready",
                progress=1.0,
                finished_at=iso_now(),
                record_count=len(records),
                needs_review_count=needs_review,
                boundary_review_count=boundary_review_count,
                accepted_count=sum(1 for record in records if record.get("accepted")),
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

    def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        blocks = [
            block for block in self.repo.load_blocks(build["asset_id"])
            if not block.get("excluded_reason")
        ]
        blocks = self._manifest_main_text_blocks(blocks, build.get("manifest") or {})
        profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
        validation = self.validate_records(blocks, records, profile)
        self.repo.save_records(build_id, records)
        build["record_count"] = len(records)
        build["needs_review_count"] = sum(1 for record in records if record.get("needs_review"))
        build["accepted_count"] = sum(1 for record in records if record.get("accepted"))
        build["validation"] = validation
        build["boundary_review_count"] = len(build.get("segmentation_boundary_reviews") or build.get("segmentation_unresolved_regions") or [])
        requires_review = bool(build["needs_review_count"] or build["boundary_review_count"] or not validation.get("valid"))
        build["status"] = "awaiting_review" if requires_review else "ready"
        build["stage"] = "review" if requires_review else "ready"
        self.repo.save_build(build)
        return build

    def patch_manifest(self, build_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Pause or wait for the corpus build before editing its document manifest.")
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
                for field in MANIFEST_INHERITED_FIELDS:
                    record.pop(field, None)
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

    def accept_record(self, build_id: str, record_id: str, accepted: bool = True) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        found = False
        for record in records:
            if record.get("record_id") == record_id:
                record["accepted"] = bool(accepted)
                if accepted:
                    record["needs_review"] = False
                    record["review_reason"] = ""
                found = True
                break
        if not found:
            raise KeyError(record_id)
        self._rewrite_and_validate(build_id, records)
        return next(record for record in records if record.get("record_id") == record_id)

    def patch_metadata(self, build_id: str, record_id: str, changes: dict[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
        forbidden = sorted(set(changes) - HUMAN_EDITABLE_METADATA_FIELDS)
        if forbidden:
            raise ValueError(
                "Source-bound fields cannot be edited here; manifest- and system-bound fields are also protected: "
                + ", ".join(forbidden)
            )
        # Validate the editable interpretive schema before modifying the persisted record.
        schema_input = {key: value for key, value in changes.items() if key in RecordMetadataModel.model_fields}
        try:
            RecordMetadataModel.model_validate(schema_input)
        except ValidationError as exc:
            raise ValueError(f"Invalid interpretive metadata: {exc}") from exc

        records = self.repo.load_records(build_id)
        target = None
        for record in records:
            if record.get("record_id") == record_id:
                target = record
                current_revision = int(record.get("record_revision") or 1)
                if expected_revision is not None and current_revision != int(expected_revision):
                    raise ValueError("This record changed after it was opened. Reload it before saving metadata.")
                for key, value in changes.items():
                    record[key] = value
                record["accepted"] = False
                record["needs_review"] = True
                record["review_reason"] = "Metadata edited during human review."
                record["record_revision"] = current_revision + 1
                break
        if target is None:
            raise KeyError(record_id)
        self._rewrite_and_validate(build_id, records)
        return target

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
        target["accepted"] = False
        target["needs_review"] = True
        target["review_reason"] = "Source evidence binding edited during human review."
        target["record_revision"] = current_revision + 1
        self._rewrite_and_validate(build_id, records)
        return target

    def merge(self, build_id: str, record_id: str, direction: str) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
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
        merged = {**first, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_block_ids": merged_ids, "source_spans": list(first.get("source_spans") or []) + list(second.get("source_spans") or []), "needs_review": True, "accepted": False, "review_reason": "Record boundaries were merged during human review.", "metadata_evidence": {}, "record_revision": max(int(first.get("record_revision") or 1), int(second.get("record_revision") or 1)) + 1}
        records[first_index:second_index + 1] = [merged]
        # Stable sequential IDs after a structural edit avoid duplicate IDs.
        prefix = re.sub(r"-\d{5}$", "", str(records[0].get("record_id") or "pdf"))
        for i, record in enumerate(records, 1):
            record["record_id"] = f"{prefix}-{i:05d}"
        self._rewrite_and_validate(build_id, records)
        return merged

    def split(self, build_id: str, record_id: str, after_block_id: str) -> dict[str, Any]:
        records = self.repo.load_records(build_id)
        index = next((i for i, record in enumerate(records) if record.get("record_id") == record_id), -1)
        if index < 0:
            raise KeyError(record_id)
        target = records[index]
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
            pieces.append({**target, "text": text, "text_length": len(text), "page_start": page_start, "page_end": page_end, "pdf_pages": pages, "source_block_ids": piece_ids, "source_spans": [span for span in target.get("source_spans") or [] if span.get("block_id") in piece_ids], "needs_review": True, "accepted": False, "review_reason": "Record boundary was split during human review.", "metadata_evidence": {}, "record_revision": int(target.get("record_revision") or 1) + 1})
        records[index:index + 1] = pieces
        prefix = re.sub(r"-\d{5}$", "", str(records[0].get("record_id") or "pdf"))
        for i, record in enumerate(records, 1):
            record["record_id"] = f"{prefix}-{i:05d}"
        self._rewrite_and_validate(build_id, records)
        return {"records": pieces}

    def rerun_metadata(self, build_id: str, record_id: str, request: dict[str, Any]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        target = next((record for record in records if record.get("record_id") == record_id), None)
        if target is None:
            raise KeyError(record_id)
        # Clear only model-owned fields; source fields remain byte-for-byte source-derived.
        for key in ALLOWED_METADATA_FIELDS:
            if key not in {"needs_review", "review_reason"}:
                target.pop(key, None)
        index = records.index(target)
        self._enrich_record(
            target,
            build.get("manifest") or {},
            request,
            previous_text=str(records[index - 1].get("text") or "") if index > 0 else "",
            next_text=str(records[index + 1].get("text") or "") if index + 1 < len(records) else "",
            build_id=build_id,
        )
        target["accepted"] = False
        self._rewrite_and_validate(build_id, records)
        return target

    def publish(self, build_id: str, *, require_acceptance: bool = True) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        records = self.repo.load_records(build_id)
        validation = build.get("validation") or {}
        if not validation.get("valid"):
            raise ValueError("Publication is blocked until source coverage and text-fidelity validation pass.")
        unresolved = [record for record in records if record.get("needs_review")]
        if unresolved:
            raise ValueError(f"Publication is blocked: {len(unresolved)} record(s) still need review.")
        if require_acceptance:
            unaccepted = [record for record in records if not record.get("accepted")]
            if unaccepted:
                raise ValueError(f"Publication is blocked: {len(unaccepted)} record(s) have not been accepted.")
        publication_id = f"publication-{build_id.removeprefix('build-')}-{uuid.uuid4().hex[:8]}"
        path = self.repo.publication_path(publication_id)
        hasher = hashlib.sha256()
        with path.open("wb") as handle:
            for record in records:
                # Internal review/provenance stays in the build; published JSONL keeps
                # audit identifiers and source spans but drops UI-only acceptance state.
                public = {k: v for k, v in record.items() if k not in {"accepted"}}
                line = (json.dumps(public, ensure_ascii=False) + "\n").encode("utf-8")
                hasher.update(line)
                handle.write(line)
        publication = {"publication_id": publication_id, "filename": f"{Path(build.get('source_filename') or 'corpus').stem}.jsonl", "sha256": hasher.hexdigest(), "record_count": len(records), "created_at": iso_now()}
        build["publication"] = publication
        build["status"] = "published"
        build["stage"] = "published"
        self.repo.save_build(build)
        return publication


pdf_corpus_repository = PdfCorpusRepository()
pdf_corpus_builds = PdfCorpusBuildManager(pdf_corpus_repository)
