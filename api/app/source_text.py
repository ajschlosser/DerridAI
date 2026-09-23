# Copyright 2026 Aaron John Schlosser, PhD.
"""Plain text, rich text, Word, HTML, and deterministic ingest metadata."""
from __future__ import annotations

import io
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MANIFEST_FIELDS = (
    "title", "document_author", "speaker", "language", "publisher",
    "publication_year", "document_type", "translator",
)
_LABEL_FIELDS = {
    "title": {"title", "titre"},
    "document_author": {"author", "auteur"},
    "language": {"language", "langue"},
    "speaker": {"speaker", "locuteur", "intervenant"},
    "publisher": {"publisher", "editeur", "éditeur"},
    "translator": {"translator", "traducteur"},
}
_NOT_SPEAKERS = {
    "title", "author", "auteur", "by", "note", "notes", "chapter", "chapitre",
    "abstract", "introduction", "figure", "table", "page", "vol", "volume",
    "isbn", "doi", "http", "https", "editor", "translator", "publisher",
}
_START_MARK = re.compile(r"\*\*\*\s*START OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)
_END_MARK = re.compile(r"\*\*\*\s*END OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK.*", re.I | re.S)
_SPEAKER_LINE = re.compile(r"^([A-Z][\w .'\-]{1,48}?):\s+\S")
_BYLINE = re.compile(r"^by\s+([A-Z][^.\n]{2,80})$", re.I)

def prepare_text(text: str) -> tuple[str, str]:
    """Keep Gutenberg header lines for metadata, and drop them from source spans."""
    if "PROJECT GUTENBERG" in text.upper() and "***" in text:
        return strip_gutenberg_boilerplate(text), text
    return text, text


def strip_gutenberg_boilerplate(text: str) -> str:
    start = _START_MARK.search(text)
    body = text[start.end():] if start else text
    end = _END_MARK.search(body)
    if end:
        body = body[:end.start()]
    return body.strip()


def document_from_text(
    text: str,
    *,
    filename: str,
    extraction_method: str,
    embedded: dict[str, Any] | None = None,
    media_kind: str,
    metadata_text: str | None = None,
    catalog: dict[str, Any] | None = None,
    confidence: float = 0.99,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    blocks, pages = prose_to_blocks(text, extraction_method=extraction_method, confidence=confidence)
    if not blocks:
        raise ValueError("The source did not contain extractable text.")
    embedded = dict(embedded or {})
    return {
        "filename": Path(str(filename or "source.txt")).name,
        "page_count": max(1, len(pages)),
        "metadata": embedded,
        "pages": pages,
        "blocks": blocks,
        "block_count": len(blocks),
        "included_block_count": len(blocks),
        "excluded_block_count": 0,
        "ocr_pages": 0,
        "warnings": list(warnings or []),
        "extractor": f"derridai-{media_kind}-v1",
        "media_kind": media_kind,
        "initial_metadata": infer_initial_metadata(
            metadata_text if metadata_text is not None else text,
            embedded=embedded,
            blocks=blocks,
            catalog=catalog,
        ),
    }


def prose_to_blocks(text: str, *, extraction_method: str, confidence: float = 0.99) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    page = 1
    used = 0
    index = 0
    page_ids: list[str] = []
    for paragraph in paragraphs:
        if used >= 2800 and page_ids:
            pages.append(_page_info(page, page_ids, extraction_method))
            page += 1
            used = 0
            index = 0
            page_ids = []
        index += 1
        block_id = f"p{page:05d}-b{index:04d}"
        speaker = leading_speaker(paragraph)
        blocks.append({
            "block_id": block_id,
            "page": page,
            "printed_page_label": str(page),
            "printed_page_label_source": "synthetic_span",
            "bbox": [0, 0, 0, 0],
            "type": "paragraph",
            "text": paragraph,
            "extraction_method": extraction_method,
            "confidence": confidence,
            **({"speaker": speaker} if speaker else {}),
        })
        page_ids.append(block_id)
        used += len(paragraph)
    if page_ids:
        pages.append(_page_info(page, page_ids, extraction_method))
    return blocks, pages


def leading_speaker(paragraph: str) -> str | None:
    first = paragraph.strip().splitlines()[0] if paragraph.strip() else ""
    match = _SPEAKER_LINE.match(first)
    if not match:
        return None
    name = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
    if not name or name.casefold() in _NOT_SPEAKERS or len(name) < 2:
        return None
    letters = [ch for ch in name if ch.isalpha()]
    if not letters:
        return None
    return name


def infer_initial_metadata(
    text: str,
    *,
    embedded: dict[str, Any] | None = None,
    blocks: list[dict[str, Any]] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fill document_author, speaker, and related fields from the source itself."""
    values: dict[str, Any] = {}
    provenance: dict[str, dict[str, Any]] = {}

    def put(field: str, value: Any, method: str, confidence: float) -> None:
        if value in (None, "", []):
            return
        cleaned = value
        if isinstance(cleaned, str):
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if not cleaned:
                return
        current = provenance.get(field)
        if current and float(current.get("confidence") or 0) > confidence:
            return
        values[field] = cleaned
        provenance[field] = {"method": method, "confidence": round(confidence, 3)}

    embedded = embedded or {}
    for source_key, field, confidence in (
        ("title", "title", 0.84),
        ("author", "document_author", 0.86),
        ("artist", "document_author", 0.8),
        ("language", "language", 0.8),
        ("publisher", "publisher", 0.75),
        ("subject", "document_type", 0.45),
    ):
        put(field, embedded.get(source_key) or embedded.get(field), "embedded_metadata", confidence)
    year = _year(embedded.get("publication_year") or embedded.get("year") or embedded.get("creationDate"))
    put("publication_year", year, "embedded_metadata", 0.7)

    for field, raw in _labeled_header_fields(text).items():
        if field == "publication_year":
            put(field, _year(raw), "labeled_line", 0.9)
        else:
            put(field, raw, "labeled_line", 0.9)
    byline = _byline(text)
    put("document_author", byline.get("document_author"), "byline", 0.82)
    put("title", byline.get("title"), "byline", 0.8)

    speakers: list[str] = []
    for block in blocks or []:
        name = str(block.get("speaker") or "").strip()
        if name and name not in speakers:
            speakers.append(name)
    if len(speakers) == 1:
        put("speaker", speakers[0], "source_span_speaker", 0.9)
    elif len(speakers) > 1:
        values["speakers"] = speakers

    catalog = catalog or {}
    put("title", catalog.get("title"), "gutenberg_catalog", 0.99)
    put("document_author", catalog.get("document_author") or catalog.get("author"), "gutenberg_catalog", 0.99)
    put("language", catalog.get("language"), "gutenberg_catalog", 0.95)
    put("publisher", catalog.get("publisher"), "gutenberg_catalog", 0.9)
    put("publication_year", _year(catalog.get("publication_year")), "gutenberg_catalog", 0.9)
    put("document_type", catalog.get("document_type"), "gutenberg_catalog", 0.9)
    if catalog.get("gutenberg_id"):
        values["gutenberg_id"] = int(catalog["gutenberg_id"])

    if "speakers" not in values and speakers:
        values["speakers"] = speakers
    values["field_provenance"] = provenance
    values["source"] = "deterministic_ingest"
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


def apply_deterministic_ingest_metadata(result: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    """Prefer high-confidence ingest metadata and fill any remaining blanks."""
    initial = asset.get("initial_metadata") if isinstance(asset.get("initial_metadata"), dict) else {}
    provenance = initial.get("field_provenance") if isinstance(initial.get("field_provenance"), dict) else {}
    applied: dict[str, Any] = {}
    for field in MANIFEST_FIELDS:
        value = initial.get(field)
        if value in (None, "", []):
            continue
        info = provenance.get(field) if isinstance(provenance.get(field), dict) else {}
        confidence = float(info.get("confidence") or 0)
        if result.get(field) in (None, "", []) or confidence >= 0.8:
            result[field] = value
            applied[field] = {"value": value, "method": info.get("method") or "deterministic_ingest", "confidence": confidence}
    result["deterministic_ingest"] = {
        "checked_at": asset.get("deterministic_checked_at"),
        "applied": applied,
        "speakers": list(initial.get("speakers") or []),
        "gutenberg_id": initial.get("gutenberg_id"),
    }
    return result


def _labeled_header_fields(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()][:40]
    for line in lines:
        if ":" not in line:
            continue
        label, raw = line.split(":", 1)
        key = label.strip().casefold()
        value = raw.strip()
        if not value:
            continue
        for field, names in _LABEL_FIELDS.items():
            if key in names and field not in found:
                found[field] = value
        if key in {"year", "date", "publication year", "annee", "année"} and "publication_year" not in found:
            found["publication_year"] = value
    return found


def _byline(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()][:8]
    if len(lines) < 2:
        return {}
    match = _BYLINE.match(lines[1])
    if match and len(lines[0]) <= 180:
        return {"title": lines[0], "document_author": match.group(1).strip()}
    return {}


def _year(value: Any) -> int | None:
    match = re.search(r"(1[5-9]\d{2}|20\d{2})", str(value or ""))
    if not match:
        return None
    return int(match.group(1))


def _page_info(page: int, block_ids: list[str], extraction_method: str) -> dict[str, Any]:
    return {
        "pdf_page": page,
        "printed_page_label": str(page),
        "printed_page_label_source": "synthetic_span",
        "width": 0,
        "height": 0,
        "block_ids": list(block_ids),
        "extraction_method": extraction_method,
    }


def decode_plain_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _looks_like_text(data: bytes) -> bool:
    sample = data[:4000]
    if not sample or b"\x00" in sample:
        return False
    textish = sum(1 for byte in sample if byte in b"\t\r\n" or 32 <= byte < 127)
    return textish / len(sample) > 0.9


def rtf_to_text(data: bytes) -> tuple[str, dict[str, str]]:
    raw = data.decode("latin-1", errors="replace")
    embedded: dict[str, str] = {}
    author = re.search(r"\{\\author\s+([^{}]*)\}", raw, re.I)
    title = re.search(r"\{\\title\s+([^{}]*)\}", raw, re.I)
    if author:
        embedded["author"] = _rtf_plain(author.group(1))
    if title:
        embedded["title"] = _rtf_plain(title.group(1))
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda match: chr(int(match.group(1), 16)), raw)
    text = text.replace("\\par", "\n").replace("\\line", "\n").replace("\\tab", "\t")
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = text.replace("{", "").replace("}", "").replace("\\", "")
    return text.strip(), embedded


def _rtf_plain(value: str) -> str:
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda match: chr(int(match.group(1), 16)), value)
    return re.sub(r"\s+", " ", text).strip()


def docx_to_text(data: bytes) -> tuple[str, dict[str, str]]:
    try:
        package = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("The Word document could not be opened.") from exc
    embedded: dict[str, str] = {}
    if "docProps/core.xml" in package.namelist():
        core = package.read("docProps/core.xml").decode("utf-8", errors="replace")
        embedded["title"] = _office_text(core, "title")
        embedded["author"] = _office_text(core, "creator")
        embedded["subject"] = _office_text(core, "subject")
        embedded["language"] = _office_text(core, "language")
    if "word/document.xml" not in package.namelist():
        raise ValueError("The Word document has no document body.")
    document = package.read("word/document.xml").decode("utf-8", errors="replace")
    paragraphs = [re.sub(r"\s+", " ", "".join(parts)).strip() for parts in re.findall(r"<w:p\b[^>]*>(.*?)</w:p>", document, re.S)]
    paragraphs = [re.sub(r"<[^>]+>", "", paragraph).strip() for paragraph in paragraphs]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    return "\n\n".join(paragraphs), {key: value for key, value in embedded.items() if value}


def _office_text(xml: str, local: str) -> str:
    match = re.search(rf"<(?:[\w-]+:)?{re.escape(local)}\b[^>]*>(.*?)</(?:[\w-]+:)?{re.escape(local)}>", xml, re.S)
    if not match:
        return ""
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def ole_doc_to_text(data: bytes) -> tuple[str, dict[str, str]]:
    decoded = data.decode("utf-16le", errors="ignore")
    runs = re.findall(r"[^\x00-\x08\x0b\x0c\x0e-\x1f]{24,}", decoded)
    if not runs:
        runs = [item.decode("latin-1", errors="ignore") for item in re.findall(rb"[\x20-\x7e]{24,}", data)]
    text = "\n".join(run.strip() for run in runs if run.strip())
    return text, {}


class _HtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: list[str] = []
        self.metas: dict[str, str] = {}
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (attr.get("name") or attr.get("property") or attr.get("itemprop") or "").lower()
            if key and attr.get("content"):
                self.metas[key] = attr["content"]
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "h1", "h2", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title.append(data)
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, dict[str, str]]:
    parser = _HtmlText()
    parser.feed(html)
    embedded = {
        "title": re.sub(r"\s+", " ", "".join(parser.title)).strip() or parser.metas.get("og:title") or parser.metas.get("citation_title") or "",
        "author": parser.metas.get("author") or parser.metas.get("citation_author") or parser.metas.get("dc.creator") or "",
        "language": parser.metas.get("language") or parser.metas.get("dc.language") or "",
        "publisher": parser.metas.get("citation_publisher") or "",
    }
    text = re.sub(r"\n{3,}", "\n\n", "".join(parser.parts))
    return text.strip(), {key: value for key, value in embedded.items() if value}


def png_text_metadata(data: bytes) -> dict[str, str]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return {}
    found: dict[str, str] = {}
    offset = 8
    while offset + 8 <= len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if chunk == b"IEND":
            break
        if chunk not in {b"tEXt", b"iTXt"}:
            continue
        if chunk == b"tEXt" and b"\x00" in payload:
            key, value = payload.split(b"\x00", 1)
            found[key.decode("latin-1", errors="ignore").casefold()] = value.decode("latin-1", errors="ignore").strip()
        elif chunk == b"iTXt" and b"\x00" in payload:
            key = payload.split(b"\x00", 1)[0].decode("latin-1", errors="ignore").casefold()
            text = payload.rsplit(b"\x00", 1)[-1].decode("utf-8", errors="ignore").strip()
            if key and text:
                found[key] = text
    mapped: dict[str, str] = {}
    if found.get("title"):
        mapped["title"] = found["title"]
    if found.get("author"):
        mapped["author"] = found["author"]
    return mapped

