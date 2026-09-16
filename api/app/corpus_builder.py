# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import fitz

from .config import APP_VERSION, settings
from .models import OllamaTouchupOptions
from .rag import _extract_json, chat_complete

SCHEMA_VERSION = "pdf-corpus-v1"
SEGMENTATION_PROMPT_VERSION = "derridai-semantic-boundaries-v1"
METADATA_PROMPT_VERSION = "derridai-record-metadata-v1"
DOCUMENT_PROMPT_VERSION = "derridai-document-manifest-v1"
PROFILE_VERSION = "derrida-scholarly-v1"

SOURCE_BOUND_FIELDS = {
    "record_id", "text", "text_length", "page_start", "page_end", "pdf_file",
    "pdf_pages", "source_asset_id", "source_block_ids", "source_spans",
}

ALLOWED_METADATA_FIELDS = {
    "work", "document_author", "language", "region_author", "speaker",
    "position_holder", "target", "discourse_role", "proposition_status",
    "semantic_function", "stance", "claim_scope", "quoted_speaker",
    "quoted_author", "quoted_work", "quoted_position_holder", "quoted_addressee",
    "quoted_referent", "quotation_chain", "topics", "concepts", "persons",
    "works_referenced", "needs_review", "review_reason",
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
        if median_size and max_size >= median_size * 1.35 and len(value) < 240:
            kind = "heading"
        elif top < height * 0.055 or bottom > height * 0.955:
            kind = "header_footer"
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
                printed_label = page.get_label() or None
            except Exception:
                printed_label = None
            page_blocks, source, warning = _page_blocks(page, ocr_mode=ocr_mode, ocr_languages=ocr_languages)
            for block in page_blocks:
                block["printed_page_label"] = printed_label
            if source == "ocr":
                ocr_pages += 1
            if warning:
                warnings.append(warning)
            pages.append({
                "pdf_page": page_index + 1,
                "printed_page_label": printed_label,
                "width": round(float(page.rect.width), 2),
                "height": round(float(page.rect.height), 2),
                "block_ids": [block["block_id"] for block in page_blocks],
                "extraction_method": source,
            })
            blocks.extend(page_blocks)

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
            "extractor": "pymupdf-layout-v1",
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

    def build_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "build.json"

    def build_records_path(self, build_id: str) -> Path:
        return self.root / "builds" / build_id / "records.jsonl"

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
    PROFILE_VERSION: {
        "id": PROFILE_VERSION,
        "name": "Derrida scholarly corpus v1",
        "version": 1,
        "description": "Semantic/discourse segmentation for Derrida primary texts with conservative attribution and quotation provenance.",
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
                build["status"] = "failed"
                build["stage"] = "interrupted"
                build["error"] = "Build was interrupted by an API restart. Retry the build with the same source and profile."
                build["finished_at"] = iso_now()
                self.repo.save_build(build)

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        asset = self.repo.get_asset(str(request["asset_id"]))
        profile_id = str(request.get("profile_id") or PROFILE_VERSION)
        if profile_id not in CORPUS_PROFILES:
            raise ValueError(f"Unknown corpus profile: {profile_id}")
        public_request = {k: v for k, v in request.items() if k != "api_key"}
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
        self._executor.submit(self._run, build["build_id"], request)
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

    def _chat_json(self, request: dict[str, Any], prompt: str, *, max_tokens: int = 4096) -> dict[str, Any]:
        provider, model, base_url, api_key, generation = self._llm_config(request)
        raw = chat_complete(
            provider=provider, model=model, base_url=base_url, api_key=api_key,
            prompt=prompt, options=generation, json_mode=True, max_tokens=max_tokens,
        )
        value = _extract_json(raw)
        if not isinstance(value, dict):
            raise ValueError("LLM did not return a JSON object.")
        return value

    def _document_manifest(self, asset: dict[str, Any], blocks: list[dict[str, Any]], request: dict[str, Any]) -> dict[str, Any]:
        metadata = asset.get("metadata") or {}
        sample = blocks[:80]
        sample_text = "\n".join(f"[{b['block_id']} p.{b['page']} {b['type']}] {b['text'][:700]}" for b in sample)
        prompt = f"""You are establishing a document manifest for an auditable scholarly corpus build.
Return exactly one JSON object. Use only source-supported facts; use null when unsupported.
Do not infer bibliographic facts from general knowledge.

PDF metadata: {json.dumps(metadata, ensure_ascii=False)}
Filename: {asset.get('filename')}
Source sample:
{sample_text[:42000]}

Schema:
{{"title":string|null,"document_author":string|null,"translator":string|null,"publisher":string|null,"publication_year":string|number|null,"language":string|null,"document_type":string|null,"main_text_start_page":number|null,"notes":"short source-bound note"}}
"""
        try:
            result = self._chat_json(request, prompt, max_tokens=1600)
        except Exception as exc:
            result = {"title": metadata.get("title"), "document_author": metadata.get("author"), "language": None, "notes": f"Manifest LLM unavailable: {exc}"}
        result["pdf_metadata"] = metadata
        result["source_asset_id"] = asset["asset_id"]
        return result

    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        window_size = 24
        overlap = 6
        windows = []
        start = 0
        while start < len(blocks):
            windows.append(blocks[start:start + window_size])
            if start + window_size >= len(blocks):
                break
            start += window_size - overlap
        for wi, window in enumerate(windows):
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            block_text = "\n\n".join(f"[{b['block_id']} | PDF p.{b['page']} | {b['type']}]\n{b['text']}" for b in window)
            prompt = f"""You are a conservative semantic boundary auditor for a Derrida scholarly corpus.
Determine where records should end because the discourse relation changes. Boundaries are governed by speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move. NEVER split merely because a page changes, a processing window ends, or text reaches a size. Keep quotations with the attribution needed to identify them. Prefer coherent argumentative units.

Document manifest: {json.dumps(manifest, ensure_ascii=False)}

SOURCE BLOCKS (immutable IDs):
{block_text[:52000]}

Return exactly one JSON object:
{{"boundaries":[{{"after_block_id":"p00001-b0001","confidence":0.0,"reason":"...","change":{{"speaker":false,"position_holder":false,"stance":false,"target":false,"quotation_frame":false,"discourse_role":false,"argumentative_move":false}}}}]}}
Only name block IDs supplied above. Do not return source text."""
            result = self._chat_json(request, prompt, max_tokens=2600)
            for item in result.get("boundaries") or []:
                block_id = str(item.get("after_block_id") or "")
                if block_id not in {b["block_id"] for b in window}:
                    continue
                try:
                    confidence = max(0.0, min(1.0, float(item.get("confidence") or 0)))
                except (TypeError, ValueError):
                    confidence = 0.0
                previous = candidates.get(block_id)
                candidate = {"after_block_id": block_id, "confidence": confidence, "reason": str(item.get("reason") or ""), "change": item.get("change") or {}}
                if previous is None or confidence > float(previous.get("confidence") or 0):
                    candidates[block_id] = candidate
            self._update(build_id, stage="segmenting", progress=0.12 + 0.28 * ((wi + 1) / max(1, len(windows))))

        ordered_ids = [b["block_id"] for b in blocks]
        index_by_id = {block_id: i for i, block_id in enumerate(ordered_ids)}
        # Never permit a boundary after the final source block; the end is implicit.
        result = [item for key, item in candidates.items() if index_by_id.get(key, len(blocks) - 1) < len(blocks) - 1]
        result.sort(key=lambda item: index_by_id.get(item["after_block_id"], 10**9))
        # Collapse adjacent competing boundaries to the strongest decision. This is
        # reconciliation of model decisions, not a length-based split.
        reconciled: list[dict[str, Any]] = []
        for item in result:
            if reconciled and index_by_id[item["after_block_id"]] - index_by_id[reconciled[-1]["after_block_id"]] <= 1:
                if item["confidence"] > reconciled[-1]["confidence"]:
                    reconciled[-1] = item
            else:
                reconciled.append(item)
        return reconciled

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
            printed_numbers = []
            for block in group:
                label = str(block.get("printed_page_label") or "").strip()
                if label.isdigit():
                    printed_numbers.append(int(label))
            page_start = min(printed_numbers) if printed_numbers else (min(pages) if pages else None)
            page_end = max(printed_numbers) if printed_numbers else (max(pages) if pages else None)
            last_id = group[-1]["block_id"]
            boundary = boundary_map.get(last_id)
            records.append({
                "record_id": f"{prefix}-{index:05d}",
                "text": text,
                "text_length": len(text),
                "page_start": page_start,
                "page_end": page_end,
                "pdf_file": asset["filename"],
                "pdf_pages": pages,
                "source_asset_id": asset["asset_id"],
                "source_block_ids": [block["block_id"] for block in group],
                "source_spans": [{"block_id": block["block_id"], "page": block["page"], "printed_page_label": block.get("printed_page_label"), "bbox": block.get("bbox"), "extraction_method": block.get("extraction_method")} for block in group],
                "boundary_evidence": boundary,
                "metadata_evidence": {},
                "needs_review": bool(boundary and float(boundary.get("confidence") or 0) < 0.72),
                "review_reason": "Low-confidence semantic boundary." if boundary and float(boundary.get("confidence") or 0) < 0.72 else "",
                "accepted": False,
                "updates": [],
            })
        return records

    def _enrich_record(self, record: dict[str, Any], manifest: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""Infer ONLY source-supported interpretive metadata for one immutable DerridAI record.
Do not rewrite, summarize, or return the record text. Distinguish the grammatical/textual speaker from the POSITION HOLDER whose proposition is being presented. A named person is not automatically a quoted speaker or position holder. Preserve modality and negation. Use null or [] when unsupported.

Document manifest: {json.dumps(manifest, ensure_ascii=False)}
Source block IDs: {json.dumps(record['source_block_ids'])}
RECORD TEXT:
{record['text'][:36000]}

Return exactly one JSON object:
{{"metadata":{{"speaker":null,"position_holder":null,"target":null,"discourse_role":null,"proposition_status":null,"semantic_function":null,"stance":null,"claim_scope":null,"quoted_speaker":null,"quoted_author":null,"quoted_work":null,"quoted_position_holder":null,"quoted_addressee":null,"quoted_referent":null,"quotation_chain":[],"topics":[],"concepts":[],"persons":[],"works_referenced":[]}},"field_evidence":{{"position_holder":{{"block_ids":[],"confidence":0.0,"reason":""}}}},"review_reason":""}}
For every non-null attribution field, include field_evidence with supporting source block IDs and confidence 0..1."""
        result = self._chat_json(request, prompt, max_tokens=3000)
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        for key, value in metadata.items():
            if key in ALLOWED_METADATA_FIELDS and key not in SOURCE_BOUND_FIELDS:
                record[key] = value
        evidence = result.get("field_evidence") if isinstance(result.get("field_evidence"), dict) else {}
        valid_ids = set(record["source_block_ids"])
        clean_evidence: dict[str, Any] = {}
        low_confidence = False
        for field, info in evidence.items():
            if field not in ALLOWED_METADATA_FIELDS or not isinstance(info, dict):
                continue
            block_ids = [str(value) for value in info.get("block_ids") or [] if str(value) in valid_ids]
            try:
                confidence = max(0.0, min(1.0, float(info.get("confidence") or 0)))
            except (TypeError, ValueError):
                confidence = 0.0
            clean_evidence[field] = {"block_ids": block_ids, "confidence": confidence, "reason": str(info.get("reason") or "")}
            if record.get(field) not in (None, "", []) and (not block_ids or confidence < 0.72):
                low_confidence = True
        record["metadata_evidence"] = clean_evidence
        manifest_title = manifest.get("title")
        manifest_author = manifest.get("document_author")
        if manifest_title and not record.get("work"):
            record["work"] = manifest_title
        if manifest_author and not record.get("document_author"):
            record["document_author"] = manifest_author
        if low_confidence:
            record["needs_review"] = True
            record["review_reason"] = str(result.get("review_reason") or "One or more attribution fields lack strong source evidence.")
        elif result.get("review_reason"):
            record["needs_review"] = True
            record["review_reason"] = str(result["review_reason"])
        return record

    @staticmethod
    def validate_records(blocks: list[dict[str, Any]], records: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
        source_ids = [block["block_id"] for block in blocks]
        used_ids = [block_id for record in records for block_id in record.get("source_block_ids") or []]
        missing = [block_id for block_id in source_ids if block_id not in used_ids]
        usage_counts = Counter(used_ids)
        duplicates = sorted(block_id for block_id, count in usage_counts.items() if count > 1)
        block_map = {block["block_id"]: block for block in blocks}
        fidelity_errors: list[str] = []
        suspicious: list[dict[str, Any]] = []
        for record in records:
            expected = "\n\n".join(block_map[block_id]["text"].strip() for block_id in record.get("source_block_ids") or [] if block_id in block_map and block_map[block_id]["text"].strip())
            if _normalize_text(expected) != _normalize_text(record.get("text") or ""):
                fidelity_errors.append(str(record.get("record_id") or ""))
            length = len(record.get("text") or "")
            if length < int(profile.get("soft_min_chars") or 0) or length > int(profile.get("soft_max_chars") or 10**9):
                suspicious.append({"record_id": record.get("record_id"), "text_length": length, "reason": "Length is an audit warning only; it did not create or change a semantic boundary."})
        return {
            "source_block_count": len(source_ids),
            "used_block_count": len(used_ids),
            "coverage": (len(set(used_ids) & set(source_ids)) / len(source_ids)) if source_ids else 1.0,
            "missing_block_ids": missing,
            "duplicate_block_ids": duplicates,
            "text_fidelity_errors": fidelity_errors,
            "suspicious_record_sizes": suspicious,
            "valid": not missing and not duplicates and not fidelity_errors,
        }

    def _run(self, build_id: str, request: dict[str, Any]) -> None:
        try:
            build = self._update(build_id, status="running", stage="structure", progress=0.03, started_at=iso_now())
            asset = self.repo.get_asset(build["asset_id"])
            all_blocks = self.repo.load_blocks(build["asset_id"])
            blocks = [block for block in all_blocks if not block.get("excluded_reason")]
            if not blocks:
                raise ValueError("No source text blocks were extracted from the PDF. Check OCR support and extraction warnings.")
            manifest = self._document_manifest(asset, blocks, request)
            self._update(build_id, stage="segmenting", progress=0.12, manifest=manifest)
            boundaries = self._segment(blocks, manifest, request, build_id)
            if self._cancelled(build_id):
                raise InterruptedError("Corpus build cancelled")
            records = self._construct_records(asset, blocks, boundaries)
            self._update(build_id, stage="enriching", progress=0.42, boundary_count=len(boundaries), record_count=len(records))
            for index, record in enumerate(records):
                if self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")
                records[index] = self._enrich_record(record, manifest, request)
                self._update(build_id, stage="enriching", progress=0.42 + 0.43 * ((index + 1) / max(1, len(records))))
            self.repo.save_records(build_id, records)
            profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
            validation = self.validate_records(blocks, records, profile)
            needs_review = sum(1 for record in records if record.get("needs_review"))
            status = "awaiting_review" if needs_review else "ready"
            self._update(build_id, status=status, stage="review" if needs_review else "ready", progress=1.0, finished_at=iso_now(), record_count=len(records), needs_review_count=needs_review, accepted_count=sum(1 for record in records if record.get("accepted")), validation=validation)
        except InterruptedError as exc:
            self._update(build_id, status="cancelled", stage="cancelled", finished_at=iso_now(), error=str(exc))
        except Exception as exc:
            self._update(build_id, status="failed", stage="failed", finished_at=iso_now(), error=str(exc))
        finally:
            with self._lock:
                self._cancel.discard(build_id)

    def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        blocks = self.repo.load_blocks(build["asset_id"])
        profile = CORPUS_PROFILES[str(build.get("profile_id") or PROFILE_VERSION)]
        validation = self.validate_records(blocks, records, profile)
        self.repo.save_records(build_id, records)
        build["record_count"] = len(records)
        build["needs_review_count"] = sum(1 for record in records if record.get("needs_review"))
        build["accepted_count"] = sum(1 for record in records if record.get("accepted"))
        build["validation"] = validation
        build["status"] = "awaiting_review" if build["needs_review_count"] else "ready"
        build["stage"] = "review" if build["needs_review_count"] else "ready"
        self.repo.save_build(build)
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

    def patch_metadata(self, build_id: str, record_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        forbidden = sorted(set(changes) & SOURCE_BOUND_FIELDS)
        if forbidden:
            raise ValueError(f"Source-bound fields cannot be edited: {', '.join(forbidden)}")
        records = self.repo.load_records(build_id)
        target = None
        for record in records:
            if record.get("record_id") == record_id:
                target = record
                for key, value in changes.items():
                    if key in ALLOWED_METADATA_FIELDS or key in {"inline_citation", "full_citation"}:
                        record[key] = value
                record["needs_review"] = True
                record["review_reason"] = "Metadata edited during human review."
                break
        if target is None:
            raise KeyError(record_id)
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
        merged = {**first, "text": text, "text_length": len(text), "page_start": min(pages), "page_end": max(pages), "pdf_pages": pages, "source_block_ids": merged_ids, "source_spans": list(first.get("source_spans") or []) + list(second.get("source_spans") or []), "needs_review": True, "accepted": False, "review_reason": "Record boundaries were merged during human review.", "metadata_evidence": {}}
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
            pieces.append({**target, "text": text, "text_length": len(text), "page_start": min(pages), "page_end": max(pages), "pdf_pages": pages, "source_block_ids": piece_ids, "source_spans": [span for span in target.get("source_spans") or [] if span.get("block_id") in piece_ids], "needs_review": True, "accepted": False, "review_reason": "Record boundary was split during human review.", "metadata_evidence": {}})
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
        self._enrich_record(target, build.get("manifest") or {}, request)
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
