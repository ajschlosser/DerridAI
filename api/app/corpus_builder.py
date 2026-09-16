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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import APP_VERSION, settings
from .models import OllamaTouchupOptions
from .rag import _citation_strings, _extract_json, chat_complete

SCHEMA_VERSION = "pdf-corpus-v2"
SEGMENTATION_PROMPT_VERSION = "derridai-semantic-boundaries-v2"
METADATA_PROMPT_VERSION = "derridai-record-metadata-v2"
DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v2"
PROFILE_VERSION = "derrida-scholarly-v2"


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
            "validation": {},
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
    },
    PROFILE_VERSION: {
        "id": PROFILE_VERSION,
        "name": "Derrida scholarly corpus v2",
        "version": 2,
        "description": "Typed, reconciled semantic/discourse segmentation with checkpointed metadata provenance and conservative attribution.",
        "boundary_dimensions": ["speaker", "position_holder", "stance", "target", "quotation_frame", "discourse_role", "argumentative_move"],
        "discourse_roles": ["assertion", "analysis", "quotation", "reported_position", "critique", "qualification", "transition", "question", "definition", "example", "commentary"],
        "min_boundary_confidence": 0.72,
        "min_metadata_confidence": 0.72,
        "soft_min_chars": 180,
        "soft_max_chars": 18000,
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

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
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
            raise ValueError("This corpus build is already running.")
        if build.get("status") in {"published"}:
            raise ValueError("Published builds are immutable; create a new build instead.")
        build["status"] = "queued"
        build["stage"] = "resuming"
        build["error"] = None
        build["resumable"] = True
        self.repo.save_build(build)
        self._executor.submit(self._run, build_id, request, True)
        return build

    def active_count(self) -> int:
        listing = self.repo.list_builds(offset=0, limit=10000)
        return sum(1 for build in listing["items"] if build.get("status") in {"queued", "running"})

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
        sample_text = "\n".join(
            f"[{b['block_id']} PDF p.{b['page']} label={b.get('printed_page_label')!r} {b['type']}] {b['text'][:900]}"
            for b in chosen
        )
        prompt = f"""You are establishing a source-bound document manifest for an auditable scholarly corpus build.
Use only evidence in the supplied PDF metadata and source blocks. Use null when unsupported. Never fill bibliographic facts from general knowledge. Distinguish the PDF page index from a printed page label. The manifest will be inherited deterministically by generated records, so be conservative.

PDF metadata: {json.dumps(metadata, ensure_ascii=False)}
Filename: {asset.get('filename')}
Strategic whole-document sample:
{sample_text[:56000]}

Return one JSON object matching the schema. `main_text_start_page` and `main_text_end_page` are physical PDF pages when supported. `document_is_translation` should be null unless the source itself supports that conclusion.
"""
        try:
            result = self._chat_json(
                request,
                prompt,
                response_model=DocumentManifestModel,
                max_tokens=2200,
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

    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        profile = CORPUS_PROFILES[str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)]
        threshold = float(profile.get("min_boundary_confidence") or 0.72)
        window_size = 24
        overlap = 6
        windows: list[list[dict[str, Any]]] = []
        start = 0
        while start < len(blocks):
            windows.append(blocks[start:start + window_size])
            if start + window_size >= len(blocks):
                break
            start += window_size - overlap

        segmentation_state = self.repo.load_checkpoint(build_id, "segmentation_state", {})
        if not isinstance(segmentation_state, dict):
            segmentation_state = {}
        candidates = {str(key): value for key, value in (segmentation_state.get("candidates") or {}).items() if isinstance(value, dict)}
        next_window = max(0, min(len(windows), int(segmentation_state.get("next_window") or 0)))
        failed_windows = int(segmentation_state.get("failed_windows") or 0)

        for wi, window in enumerate(windows):
            if wi < next_window:
                continue
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            block_ids = {b["block_id"] for b in window}
            block_text = "\n\n".join(
                f"[{b['block_id']} | PDF p.{b['page']} | {b['type']}]\n{b['text']}"
                for b in window
            )
            prompt = f"""You are a conservative semantic-boundary auditor for a Derrida scholarly corpus.
Judge only genuine discourse boundaries. A split is warranted when a coherent argumentative/discursive unit ends because of a meaningful change in speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move. NEVER split merely because a page changes, a processing window ends, or text reaches a size. Keep quotations with the attribution necessary to identify them. Prefer fewer coherent records over fragmentary records.

Document manifest: {json.dumps(manifest, ensure_ascii=False)}

SOURCE BLOCKS (immutable IDs):
{block_text[:52000]}

Return decisions only for plausible transition points. `decision=split` means the next source block begins a new semantic/discourse unit. `decision=uncertain` means there is evidence of a transition but the context is insufficient. `decision=keep` may be used to explicitly reject an apparent boundary. Never return source text and never invent block IDs.
"""
            try:
                result = self._chat_json(
                    request,
                    prompt,
                    response_model=SegmentationResponseModel,
                    max_tokens=3000,
                    schema_name="derridai_semantic_boundaries",
                    build_id=build_id,
                )
            except InterruptedError:
                raise
            except Exception as exc:
                failed_windows += 1
                self._append_warning(build_id, f"Segmentation window {wi + 1}/{len(windows)} could not be validated and was skipped: {exc}")
                self.repo.save_checkpoint(build_id, "segmentation_state", {"next_window": wi + 1, "failed_windows": failed_windows, "candidates": candidates})
                self._update(build_id, stage="segmenting", progress=0.12 + 0.24 * ((wi + 1) / max(1, len(windows))))
                continue
            for item in result.get("boundaries") or []:
                block_id = str(item.get("after_block_id") or "")
                if block_id not in block_ids:
                    continue
                candidate = {
                    "after_block_id": block_id,
                    "decision": str(item.get("decision") or "uncertain"),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                    "reason": str(item.get("reason") or ""),
                    "change": item.get("change") or {},
                    "window": wi,
                }
                previous = candidates.get(block_id)
                if previous is None or candidate["confidence"] > float(previous.get("confidence") or 0):
                    candidates[block_id] = candidate
            self.repo.save_checkpoint(build_id, "segmentation_state", {"next_window": wi + 1, "failed_windows": failed_windows, "candidates": candidates})
            self._update(build_id, stage="segmenting", progress=0.12 + 0.24 * ((wi + 1) / max(1, len(windows))))

        ordered_ids = [b["block_id"] for b in blocks]
        index_by_id = {block_id: i for i, block_id in enumerate(ordered_ids)}
        raw = [
            item for item in candidates.values()
            if index_by_id.get(item["after_block_id"], len(blocks) - 1) < len(blocks) - 1
            and item.get("decision") != "keep"
        ]
        raw.sort(key=lambda item: index_by_id.get(item["after_block_id"], 10**9))

        # Adjacent proposals usually describe the same transition. Keep the
        # strongest candidate, then ask a second semantic pass to adjudicate
        # low-confidence/window-seam decisions instead of treating every proposal
        # as a record boundary.
        collapsed: list[dict[str, Any]] = []
        for item in raw:
            if collapsed and index_by_id[item["after_block_id"]] - index_by_id[collapsed[-1]["after_block_id"]] <= 1:
                if item["confidence"] > collapsed[-1]["confidence"]:
                    collapsed[-1] = item
            else:
                collapsed.append(item)

        accepted = [item for item in collapsed if item.get("decision") == "split" and float(item.get("confidence") or 0) >= threshold]
        uncertain = [item for item in collapsed if item not in accepted]
        if uncertain:
            accepted.extend(self._reconcile_boundaries(blocks, manifest, uncertain, request, build_id, threshold))
        accepted.sort(key=lambda item: index_by_id.get(item["after_block_id"], 10**9))
        self.repo.save_checkpoint(build_id, "boundaries", accepted)
        degraded = bool(windows and (failed_windows / len(windows)) >= 0.20) or (len(blocks) > window_size and not accepted)
        if degraded:
            self._append_warning(build_id, "Semantic segmentation is degraded: too many windows failed validation or no validated boundaries were retained. Records are preserved but must be reviewed before publication.")
        self._update(build_id, stage="reconciling", progress=0.40, boundary_count=len(accepted), boundary_candidate_count=len(collapsed), segmentation_failed_windows=failed_windows, segmentation_total_windows=len(windows), segmentation_degraded=degraded)
        return accepted

    def _reconcile_boundaries(
        self,
        blocks: list[dict[str, Any]],
        manifest: dict[str, Any],
        candidates: list[dict[str, Any]],
        request: dict[str, Any],
        build_id: str,
        threshold: float,
    ) -> list[dict[str, Any]]:
        block_index = {block["block_id"]: i for i, block in enumerate(blocks)}
        accepted: list[dict[str, Any]] = []
        reconciliation_state = self.repo.load_checkpoint(build_id, "reconciliation_state", {})
        if not isinstance(reconciliation_state, dict):
            reconciliation_state = {}
        completed_batches = {
            int(value)
            for value in reconciliation_state.get("completed_batches") or []
            if isinstance(value, int) or str(value).isdigit()
        }
        restored = reconciliation_state.get("accepted") or []
        if isinstance(restored, list):
            accepted.extend(item for item in restored if isinstance(item, dict))

        for offset in range(0, len(candidates), 12):
            batch_number = offset // 12
            if batch_number in completed_batches:
                continue
            batch = candidates[offset:offset + 12]
            excerpts: list[str] = []
            for candidate in batch:
                idx = block_index.get(candidate["after_block_id"], -1)
                if idx < 0:
                    continue
                context = blocks[max(0, idx - 2):min(len(blocks), idx + 4)]
                excerpts.append(
                    "\n".join([
                        f"CANDIDATE after {candidate['after_block_id']} confidence={candidate['confidence']:.2f} reason={candidate.get('reason','')}",
                        *[f"[{b['block_id']}] {b['text'][:900]}" for b in context],
                    ])
                )
            prompt = f"""You are reconciling uncertain semantic boundaries proposed by an earlier pass. Decide whether each candidate is a genuine record boundary. Use the surrounding source context, not character length or page changes. A split must preserve coherent attribution, quotation framing and argumentative relations. Prefer KEEP when the evidence for a discourse transition is weak.

Document manifest: {json.dumps(manifest, ensure_ascii=False)}

CANDIDATES AND LOCAL CONTEXT:
{chr(10).join(excerpts)[:52000]}

Return one decision for each supplied candidate ID. `split` means retain the boundary; `keep` means remove it.
"""
            try:
                result = self._chat_json(
                    request,
                    prompt,
                    response_model=ReconciliationResponseModel,
                    max_tokens=2200,
                    schema_name="derridai_boundary_reconciliation",
                    build_id=build_id,
                )
            except InterruptedError:
                raise
            except Exception as exc:
                self._append_warning(build_id, f"Boundary reconciliation batch {offset // 12 + 1} failed; only already high-confidence boundaries were retained: {exc}")
                continue
            original = {item["after_block_id"]: item for item in batch}
            for decision in result.get("decisions") or []:
                block_id = str(decision.get("after_block_id") or "")
                if block_id not in original or decision.get("decision") != "split":
                    continue
                confidence = float(decision.get("confidence") or 0)
                if confidence < threshold:
                    continue
                merged = dict(original[block_id])
                merged.update({
                    "decision": "split",
                    "confidence": confidence,
                    "reconciled": True,
                    "reconciliation_reason": str(decision.get("reason") or ""),
                })
                accepted.append(merged)
            completed_batches.add(batch_number)
            self.repo.save_checkpoint(build_id, "reconciliation_state", {
                "completed_batches": sorted(completed_batches),
                "accepted": accepted,
            })
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
        self._apply_manifest_metadata(record, manifest)
        neighbor_context = {
            "previous_record_tail": previous_text[-2200:] if previous_text else "",
            "next_record_head": next_text[:2200] if next_text else "",
        }
        prompt = f"""Infer ONLY source-supported interpretive metadata for one immutable DerridAI record.
Do not rewrite, summarize, or return the record text. Distinguish the grammatical/textual speaker from the POSITION HOLDER whose proposition is being presented. A named person is not automatically a quoted speaker or position holder. Preserve modality, negation, uncertainty, and quotation framing. Use null or [] when unsupported.

The neighboring excerpts are context only. Evidence for an attribution field MUST cite immutable source block IDs from the current record; do not cite neighboring text as field evidence.

Document manifest: {json.dumps(manifest, ensure_ascii=False)}
Neighbor context: {json.dumps(neighbor_context, ensure_ascii=False)}
Current source block IDs: {json.dumps(record['source_block_ids'])}
CURRENT RECORD TEXT:
{record['text'][:42000]}

For every populated attribution-bearing field (speaker, position_holder, target, stance, proposition_status, quoted_* and quotation_chain), include `field_evidence` with supporting current-record block IDs, confidence 0..1, and a short evidence reason. `semantic_function` is an array. Quotation relation fields are arrays. Do not invent bibliographic metadata; document-level bibliography is inherited separately by deterministic code.
"""
        try:
            result = self._chat_json(
                request,
                prompt,
                response_model=MetadataResponseModel,
                max_tokens=4200,
                schema_name="derridai_record_metadata",
                build_id=build_id,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            record["needs_review"] = True
            record["review_reason"] = f"Metadata extraction could not be validated: {exc}"
            record["metadata_evidence"] = {}
            record["metadata_complete"] = False
            if build_id:
                self._append_warning(build_id, f"{record.get('record_id')}: metadata extraction requires review ({exc})")
            inline, full = _citation_strings(record)
            record["inline_citation"] = inline
            record["full_citation"] = full
            return record

        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        for key, value in metadata.items():
            if key in ALLOWED_METADATA_FIELDS and key not in SOURCE_BOUND_FIELDS:
                record[key] = value

        evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
        valid_ids = set(record["source_block_ids"])
        clean_evidence: dict[str, Any] = {}
        review_reasons: list[str] = []
        confidences: list[float] = []
        attribution_confidences: list[float] = []
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
            confidences.append(confidence)
            if field in ATTRIBUTION_EVIDENCE_FIELDS:
                attribution_confidences.append(confidence)

        # Validate evidence from the metadata outward. A populated high-risk field
        # is unsupported unless its corresponding evidence entry exists and points
        # to at least one source block in this record.
        profile_id = PROFILE_VERSION
        if build_id:
            try:
                profile_id = str(self.repo.get_build(build_id).get("profile_id") or PROFILE_VERSION)
            except Exception:
                profile_id = PROFILE_VERSION
        minimum = float(CORPUS_PROFILES.get(profile_id, CORPUS_PROFILES[PROFILE_VERSION]).get("min_metadata_confidence") or 0.72)
        for field in sorted(ATTRIBUTION_EVIDENCE_FIELDS):
            value = record.get(field)
            populated = value not in (None, "", [])
            if not populated:
                continue
            info = clean_evidence.get(field)
            if not info:
                review_reasons.append(f"{field} has no bound source evidence")
                continue
            if not info.get("block_ids"):
                review_reasons.append(f"{field} evidence does not identify a current-record source block")
            if float(info.get("confidence") or 0) < minimum:
                review_reasons.append(f"{field} evidence confidence is below {minimum:.2f}")

        record["metadata_evidence"] = clean_evidence
        record["semantic_classification_confidence"] = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        record["attribution_confidence"] = round(min(attribution_confidences), 4) if attribution_confidences else 1.0
        model_review_reason = str(result.get("review_reason") or "").strip()
        if model_review_reason:
            review_reasons.append(model_review_reason)
        if review_reasons:
            record["needs_review"] = True
            record["review_reason"] = "; ".join(dict.fromkeys(review_reasons))[:1800]
        record["metadata_complete"] = True
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
                self.repo.save_checkpoint(build_id, "manifest", manifest)
            current_manifest_revision = int(self.repo.get_build(build_id).get("manifest_revision") or 1)
            self._update(build_id, stage="segmenting", progress=max(float(build.get("progress") or 0), 0.12), manifest=manifest, manifest_revision=current_manifest_revision)

            boundaries = self.repo.load_checkpoint(build_id, "boundaries") if resume else None
            if not isinstance(boundaries, list):
                boundaries = self._segment(blocks, manifest, request, build_id)
                self.repo.save_checkpoint(build_id, "boundaries", boundaries)
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")

            records = self.repo.load_records(build_id) if resume else []
            if not records:
                records = self._construct_records(asset, blocks, boundaries)
                segmentation_degraded = bool(self.repo.get_build(build_id).get("segmentation_degraded"))
                for record in records:
                    self._apply_manifest_metadata(record, manifest)
                    inline, full = _citation_strings(record)
                    record["inline_citation"] = inline
                    record["full_citation"] = full
                    if segmentation_degraded:
                        record["needs_review"] = True
                        record["review_reason"] = "Semantic segmentation was degraded; verify this record boundary before publication."
                # Persist deterministic records before any metadata call. A provider
                # failure can therefore never discard successful segmentation work.
                self.repo.save_records(build_id, records)
            self._update(build_id, stage="enriching", progress=max(float(self.repo.get_build(build_id).get("progress") or 0), 0.42), boundary_count=len(boundaries), record_count=len(records))

            total = max(1, len(records))
            for index, record in enumerate(records):
                if self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")
                if record.get("metadata_complete"):
                    continue
                previous_text = str(records[index - 1].get("text") or "") if index > 0 else ""
                next_text = str(records[index + 1].get("text") or "") if index + 1 < len(records) else ""
                records[index] = self._enrich_record(
                    record,
                    manifest,
                    request,
                    previous_text=previous_text,
                    next_text=next_text,
                    build_id=build_id,
                )
                # Checkpoint every completed record. JSONL rewrite is intentionally
                # simple and atomic; correctness/restart safety is more important
                # than micro-optimizing this offline corpus-construction path.
                self.repo.save_records(build_id, records)
                self._update(build_id, stage="enriching", progress=0.42 + 0.43 * ((index + 1) / total))

            profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
            validation = self.validate_records(blocks, records, profile)
            needs_review = sum(1 for record in records if record.get("needs_review"))
            status = "awaiting_review" if needs_review or not validation.get("valid") else "ready"
            self._update(
                build_id,
                status=status,
                stage="review" if status == "awaiting_review" else "ready",
                progress=1.0,
                finished_at=iso_now(),
                record_count=len(records),
                needs_review_count=needs_review,
                accepted_count=sum(1 for record in records if record.get("accepted")),
                validation=validation,
                resumable=False,
            )
        except InterruptedError as exc:
            self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc), resumable=True)
        except Exception as exc:
            # Checkpoints intentionally survive a failed stage. The user can repair
            # provider configuration and resume instead of restarting a long book.
            self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc), resumable=True)
        finally:
            with self._lock:
                self._cancel.discard(build_id)

    def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        blocks = [
            block for block in self.repo.load_blocks(build["asset_id"])
            if not block.get("excluded_reason")
        ]
        profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
        validation = self.validate_records(blocks, records, profile)
        self.repo.save_records(build_id, records)
        build["record_count"] = len(records)
        build["needs_review_count"] = sum(1 for record in records if record.get("needs_review"))
        build["accepted_count"] = sum(1 for record in records if record.get("accepted"))
        build["validation"] = validation
        requires_review = bool(build["needs_review_count"] or not validation.get("valid"))
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
