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

"""Plain text, rich text, Word, HTML, and deterministic ingest metadata."""
from __future__ import annotations

import io
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .language_segmentation import looks_like_speaker_start
from .source_safety import check_size, safe_xml, validate_docx, validate_rtf

MANIFEST_FIELDS = (
    "title", "document_author", "speaker", "language", "publisher",
    "publication_year", "document_type", "translator", "edition",
    "publication_place", "isbn",
)
_LABEL_FIELDS = {
    "title": {"title", "titre"},
    "document_author": {"author", "auteur"},
    "language": {"language", "langue"},
    "speaker": {"speaker", "locuteur", "intervenant"},
    "publisher": {"publisher", "editeur", "éditeur"},
    "translator": {"translator", "traducteur"},
    "publication_place": {"place of publication", "place", "lieu d'édition", "lieu de publication"},
    "isbn": {"isbn"},
}
_NOT_SPEAKERS = {
    "title", "author", "auteur", "by", "note", "notes", "chapter", "chapitre",
    "abstract", "introduction", "figure", "table", "page", "vol", "volume",
    "isbn", "doi", "http", "https", "editor", "translator", "publisher",
}
_START_MARK = re.compile(r"\*\*\*\s*START OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)
_END_MARK = re.compile(r"\*\*\*\s*END OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK.*", re.I | re.S)
_BYLINE = re.compile(r"^by\s+([A-Z][^.\n]{2,80})$", re.I)
DEFAULT_WORDS_PER_PAGE = 300
MIN_WORDS_PER_PAGE = 50
MAX_WORDS_PER_PAGE = 2000
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

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
    detect_pages: bool = True,
    page_llm: Any = None,
    words_per_page: int = DEFAULT_WORDS_PER_PAGE,
) -> dict[str, Any]:
    embedded = dict(embedded or {})
    native_labels = embedded.pop("_native_page_labels", None)
    native_pattern = embedded.pop("_native_page_pattern", None)
    detection: dict[str, Any] = {}
    blocks, pages = prose_to_blocks(
        text, extraction_method=extraction_method, confidence=confidence,
        detect_pages=detect_pages, detection_out=detection, page_llm=page_llm,
        native_page_labels=native_labels if isinstance(native_labels, list) else None,
        native_page_pattern=str(native_pattern) if native_pattern else None,
        words_per_page=words_per_page,
    )
    if not blocks:
        raise ValueError("The source did not contain extractable text.")
    page_estimate = None
    if detection.get("status") == "estimated":
        page_estimate = {
            "words_per_page": int(detection.get("words_per_page") or words_per_page),
            "one_record_per_page": True,
            "confirmed": False,
        }
    return {
        "filename": Path(str(filename or "source.txt")).name,
        "page_count": max(1, len(pages)),
        "metadata": embedded,
        "pages": pages,
        "blocks": blocks,
        "block_count": len(blocks),
        "included_block_count": sum(1 for block in blocks if not block.get("excluded_reason")),
        "excluded_block_count": sum(1 for block in blocks if block.get("excluded_reason")),
        "page_number_detection": detection,
        **({"page_estimate": page_estimate} if page_estimate else {}),
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


def prose_to_blocks(
    text: str,
    *,
    extraction_method: str,
    confidence: float = 0.99,
    detect_pages: bool = True,
    detection_out: dict[str, Any] | None = None,
    page_llm: Any = None,
    native_page_labels: list[str] | None = None,
    native_page_pattern: str | None = None,
    words_per_page: int = DEFAULT_WORDS_PER_PAGE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Blocks and pages for prose.

    Printed numbers win when a real sequence is found (file markers, Gutenberg/Wikisource
    anchors, or the pattern detector, then a model). A Word/RTF/form-feed page break is used
    when no printed sequence exists. Otherwise pages are an explicit word-count estimate.
    ``detection_out`` receives the method and its provenance.
    """
    from . import page_markers

    text, stripped_prefix = strip_line_frame(text)
    if detection_out is not None and stripped_prefix:
        detection_out["line_frame_stripped"] = stripped_prefix
    plain = text.replace("\f", "\n")
    if detect_pages:
        detection = page_markers.detect(plain)
        if detection.status != "detected" and page_llm is not None:
            # Deterministic detection failed: let a model pick candidate lines, then verify them the same way.
            try:
                assisted = page_markers.detect_with_llm(plain, page_llm)
                if assisted.status == "detected":
                    detection = assisted
                else:
                    detection.reason = f"{detection.reason}; {assisted.reason}".strip("; ")
            except Exception as exc:  # a model failure leaves the deterministic (not found) result
                detection.reason = f"{detection.reason}; model-assisted detection failed: {type(exc).__name__}".strip("; ")
    else:
        detection = page_markers.Detection(status="disabled", reason="page-number detection was turned off")
    if detection_out is not None:
        detection_out.update(detection.summary())
    if detection.status == "detected":
        detected = _blocks_with_detected_pages(plain, detection, extraction_method, confidence)
        if detected is not None:
            return detected
        if detection_out is not None:
            detection_out.update(status="not_found", reason="markers found but no text could be assigned to pages")
    labeled = _form_feed_pages(text, native_page_labels)
    if detect_pages and labeled and (native_page_pattern or "\f" in text):
        source = native_page_pattern or "form_feed"
        native = _blocks_from_labeled_pages(
            labeled, extraction_method=extraction_method, confidence=confidence, label_source=source,
        )
        if native is not None:
            blocks, pages = native
            if detection_out is not None:
                detection_out.update(_format_page_summary(pages, source))
            return blocks, pages
    if not detect_pages:
        return _synthetic_page_blocks(text.replace("\f", "\n"), extraction_method=extraction_method, confidence=confidence)
    words = words_per_page if MIN_WORDS_PER_PAGE <= int(words_per_page) <= MAX_WORDS_PER_PAGE else DEFAULT_WORDS_PER_PAGE
    blocks, pages = _word_count_pages(plain, extraction_method=extraction_method, confidence=confidence, words_per_page=words)
    if detection_out is not None:
        prior = str(detection_out.get("reason") or "").strip()
        reason = "No printed page numbers were found; pages were estimated from word count."
        if prior and prior != "too few candidates":
            reason = f"{prior}; {reason}"
        detection_out.update({
            "status": "estimated",
            "pattern": "word_count",
            "convention": "word_count",
            "confidence": 0.0,
            "marker_count": len(pages),
            "reason": reason,
            "first": 1 if pages else None,
            "last": len(pages) or None,
            "words_per_page": words,
            "one_record_per_page": True,
            "confirmed": False,
        })
    return blocks, pages


_LEAD_PIPE = re.compile(r"^[ \t]*\|[ \t]?")
_TRAIL_PIPE = re.compile(r"[ \t]?\|[ \t]*$")


def strip_line_frame(text: str) -> tuple[str, str]:
    """Remove a leading/trailing ``|`` that frames (almost) every line, e.g. quoted or table-style dumps.

    Only applied when at least 80% of the non-blank lines carry the frame, so ordinary text with an
    occasional pipe is untouched. Returns the text and a short description of what was removed
    (empty when nothing was), which the caller records as provenance.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    filled = [line for line in lines if line.strip()]
    if len(filled) < 3:
        return text, ""
    lead = sum(1 for line in filled if _LEAD_PIPE.match(line))
    if lead / len(filled) < 0.8:
        return text, ""
    trail = sum(1 for line in filled if _TRAIL_PIPE.search(line))
    strip_trail = trail / len(filled) >= 0.8
    out = []
    for line in lines:
        if line.strip():
            line = _LEAD_PIPE.sub("", line, count=1)
            if strip_trail:
                line = _TRAIL_PIPE.sub("", line, count=1)
        out.append(line)
    return "\n".join(out), "leading_and_trailing_pipe" if strip_trail else "leading_pipe"


def _paragraph_spans(lines: list[str]) -> list[tuple[int, int]]:
    """(first_line, last_line) of each run of non-blank lines, matching blank-line splitting."""
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip().strip("\f"):
            if start is None:
                start = index
        elif start is not None:
            spans.append((start, index - 1))
            start = None
    if start is not None:
        spans.append((start, len(lines) - 1))
    return spans


def _blocks_with_detected_pages(
    text: str, detection: Any, extraction_method: str, confidence: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    markers = detection.markers
    marker_lines = {m.line for m in markers if m.standalone}
    inline_lines = sorted({m.line for m in markers if not m.standalone})
    by_line = {m.line: m.value for m in markers}
    ordered = sorted(markers, key=lambda m: m.line)
    end_convention = detection.convention == "end"

    def label_at(line: int) -> tuple[str | None, str]:
        """Printed label of the page containing ``line`` and how it was established."""
        if not end_convention:
            prior = [m for m in ordered if m.line <= line]
            if prior:
                return str(prior[-1].value), "visible_folio"
            first = ordered[0].value
            return (str(first - 1), "inferred_from_folios") if first > 1 else (None, "")
        following = [m for m in ordered if m.line >= line]
        if following:
            return str(following[0].value), "visible_folio"
        return str(ordered[-1].value + 1), "inferred_from_folios"

    blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    page_index = 0
    current_label: str | None = object()  # type: ignore[assignment]
    current_ids: list[str] = []
    per_page_count = 0
    current_source = ""

    def close_page() -> None:
        if current_ids:
            pages.append({
                "pdf_page": page_index,
                "printed_page_label": current_label,
                "printed_page_label_source": current_source or None,
                "width": 0, "height": 0,
                "block_ids": list(current_ids),
                "extraction_method": extraction_method,
                "page_number_detection": {"pattern": detection.pattern, "confidence": round(detection.confidence, 3)},
            })

    def add_block(paragraph_lines: list[int], *, marker: bool) -> None:
        nonlocal page_index, current_label, current_ids, per_page_count, current_source
        first, last = paragraph_lines[0], paragraph_lines[-1]
        label, source = label_at(first)
        if label != current_label or page_index == 0:
            close_page()
            page_index += 1
            current_label, current_ids, per_page_count, current_source = label, [], 0, source
        per_page_count += 1
        block_id = f"p{page_index:05d}-b{per_page_count:04d}"
        body = "\n".join(lines[i].strip().strip("\f") for i in paragraph_lines).strip()
        block: dict[str, Any] = {
            "block_id": block_id, "page": page_index,
            "printed_page_label": label, "printed_page_label_source": source or None,
            "bbox": [0, 0, 0, 0], "type": "header_footer" if marker else "paragraph",
            "text": body, "extraction_method": extraction_method, "confidence": confidence,
        }
        if marker:
            block["excluded_reason"] = "page_number"
        else:
            speaker = leading_speaker(body)
            if speaker:
                block["speaker"] = speaker
            end_label, _ = label_at(last)
            inner = [line for line in inline_lines if first <= line <= last]
            if inner and end_label != label:
                block["printed_page_label_end"] = end_label
        blocks.append(block)
        current_ids.append(block_id)

    for first, last in _paragraph_spans(lines):
        run: list[int] = []
        for line in range(first, last + 1):
            is_marker = line in marker_lines
            if is_marker:
                if run:
                    add_block(run, marker=False)
                    run = []
                add_block([line], marker=True)
            else:
                run.append(line)
        if run:
            add_block(run, marker=False)
    close_page()
    if not any(block["type"] == "paragraph" for block in blocks):
        return None
    del by_line
    return blocks, pages


def _format_page_summary(pages: list[dict[str, Any]], pattern: str) -> dict[str, Any]:
    labels = [str(page.get("printed_page_label") or "") for page in pages]
    numeric = [int(label) for label in labels if label.isdigit()]
    return {
        "status": "detected",
        "pattern": pattern,
        "convention": "format",
        "confidence": 0.95,
        "marker_count": len(pages),
        "reason": "Page breaks come from the file or the provider.",
        "first": numeric[0] if numeric else None,
        "last": numeric[-1] if numeric else None,
    }


def _form_feed_pages(text: str, labels: list[str] | None) -> list[tuple[str, str]] | None:
    """Pages split on form feeds, or one page when the file names its starting number."""
    if "\f" not in text:
        if labels and len(labels) == 1 and text.strip():
            return [(str(labels[0]), text.strip())]
        return None
    parts = text.split("\f")
    while parts and not parts[0].strip():
        parts.pop(0)
        if labels:
            labels = labels[1:]
    while parts and not parts[-1].strip():
        parts.pop()
        if labels:
            labels = labels[:-1]
    if len(parts) < 2 and not (labels and len(labels) == 1):
        return None
    if labels and len(labels) == len(parts):
        return [(str(label), part.strip()) for label, part in zip(labels, parts)]
    return [(str(index), part.strip()) for index, part in enumerate(parts, 1)]


def _blocks_from_labeled_pages(
    pages_text: list[tuple[str, str]],
    *,
    extraction_method: str,
    confidence: float,
    label_source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    for index, (label, body) in enumerate(pages_text, 1):
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
        ids: list[str] = []
        for number, paragraph in enumerate(paragraphs, 1):
            block_id = f"p{index:05d}-b{number:04d}"
            speaker = leading_speaker(paragraph)
            blocks.append({
                "block_id": block_id,
                "page": index,
                "printed_page_label": str(label),
                "printed_page_label_source": label_source,
                "bbox": [0, 0, 0, 0],
                "type": "paragraph",
                "text": paragraph,
                "extraction_method": extraction_method,
                "confidence": confidence,
                **({"speaker": speaker} if speaker else {}),
            })
            ids.append(block_id)
        pages.append({
            "pdf_page": index,
            "printed_page_label": str(label),
            "printed_page_label_source": label_source,
            "width": 0,
            "height": 0,
            "block_ids": ids,
            "extraction_method": extraction_method,
        })
    if not blocks:
        return None
    return blocks, pages


def _word_count(text: str) -> int:
    return len(text.split())


def pack_paragraphs_by_words(paragraphs: list[dict[str, Any]], words_per_page: int) -> list[list[dict[str, Any]]]:
    """Group whole paragraphs into pages of about ``words_per_page`` words.

    A paragraph that is itself longer than the budget stays on its own page, so a page
    edge never cuts a paragraph in half.
    """
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    used = 0
    for paragraph in paragraphs:
        words = _word_count(str(paragraph.get("text") or ""))
        if current and used + words > words_per_page:
            groups.append(current)
            current = []
            used = 0
        current.append(paragraph)
        used += words
    if current:
        groups.append(current)
    return groups


def blocks_from_word_groups(
    groups: list[list[dict[str, Any]]],
    *,
    extraction_method: str,
    confidence: float = 0.99,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    for index, group in enumerate(groups, 1):
        ids: list[str] = []
        for number, paragraph in enumerate(group, 1):
            block_id = f"p{index:05d}-b{number:04d}"
            text = str(paragraph.get("text") or "").strip()
            speaker = paragraph.get("speaker") or leading_speaker(text)
            blocks.append({
                "block_id": block_id,
                "page": index,
                "printed_page_label": str(index),
                "printed_page_label_source": "word_count",
                "bbox": [0, 0, 0, 0],
                "type": "paragraph",
                "text": text,
                "extraction_method": paragraph.get("extraction_method") or extraction_method,
                "confidence": paragraph.get("confidence") if paragraph.get("confidence") is not None else confidence,
                **({"speaker": speaker} if speaker else {}),
            })
            ids.append(block_id)
        pages.append({
            "pdf_page": index,
            "printed_page_label": str(index),
            "printed_page_label_source": "word_count",
            "width": 0,
            "height": 0,
            "block_ids": ids,
            "extraction_method": extraction_method,
            "words_per_page": None,
        })
    return blocks, pages


def _word_count_pages(
    text: str, *, extraction_method: str, confidence: float, words_per_page: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    items = [{"text": paragraph, "extraction_method": extraction_method, "confidence": confidence} for paragraph in paragraphs]
    groups = pack_paragraphs_by_words(items, words_per_page)
    blocks, pages = blocks_from_word_groups(groups, extraction_method=extraction_method, confidence=confidence)
    for page in pages:
        page["words_per_page"] = words_per_page
    return blocks, pages


def _synthetic_page_blocks(text: str, *, extraction_method: str, confidence: float = 0.99) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
    """Return a source-visible speaker label without assuming a Latin script."""
    first = paragraph.strip().splitlines()[0] if paragraph.strip() else ""
    if not looks_like_speaker_start(first):
        return None
    positions = [
        position
        for marker in (":", "：")
        if (position := first.find(marker)) > 0
    ]
    if not positions:
        return None
    name = re.sub(r"\s+", " ", first[: min(positions)]).strip(" :-：")
    normalized_name = name.casefold()
    first_token = normalized_name.split()[0] if normalized_name.split() else ""
    if (
        not name
        or normalized_name in _NOT_SPEAKERS
        or first_token in _NOT_SPEAKERS
        or len(name) < 2
    ):
        return None
    if not any(ch.isalpha() for ch in name):
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

    def put(
        field: str, value: Any, method: str, confidence: float, *,
        derivation: str = "deterministic", reason: str = "", span: tuple[int, int] | None = None,
    ) -> None:
        """Record a value with its provenance. A value that loses to a more confident one is kept as
        an alternative (a suggestion for the reviewer), never silently discarded."""
        if value in (None, "", []):
            return
        cleaned = value
        if isinstance(cleaned, str):
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if not cleaned:
                return
        entry: dict[str, Any] = {"method": method, "confidence": round(confidence, 3), "derivation": derivation}
        if reason:
            entry["reason"] = reason
        if span:
            entry["span"] = [span[0], span[1]]
        current = provenance.get(field)
        if current and float(current.get("confidence") or 0) > confidence:
            if cleaned != values.get(field):
                alternatives = current.setdefault("alternatives", [])
                if all(alt["value"] != cleaned for alt in alternatives):
                    alternatives.append({"value": cleaned, **entry})
            return
        if current and values.get(field) != cleaned:
            entry["alternatives"] = [
                {"value": values.get(field), **{k: v for k, v in current.items() if k != "alternatives"}},
                *current.get("alternatives", []),
            ]
        elif current and current.get("alternatives"):
            entry["alternatives"] = current["alternatives"]
        values[field] = cleaned
        provenance[field] = entry

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
    # Provider catalogue values are provider assertions; name the provider that made them.
    origin = f"{catalog.get('provider') or 'gutenberg'}_catalog"
    put("edition", catalog.get("edition"), origin, 0.99)
    put("title", catalog.get("title"), origin, 0.99)
    put("document_author", catalog.get("document_author") or catalog.get("author"), origin, 0.99)
    put("language", catalog.get("language"), origin, 0.95)
    put("translator", catalog.get("translator"), origin, 0.95)
    put("original_language", catalog.get("original_language"), origin, 0.9)
    put("publisher", catalog.get("publisher"), origin, 0.9)
    put("publication_year", _year(catalog.get("publication_year")), origin, 0.9)
    put("document_type", catalog.get("document_type"), origin, 0.9)
    if catalog.get("gutenberg_id"):
        values["gutenberg_id"] = int(catalog["gutenberg_id"])

    # Front-matter pre-fill: exact patterns ("computed") and a statistical tagger ("nlp_derived").
    from .document_prefill import extract, guess_language

    # Use the bounded deterministic detector only when stronger source/catalogue
    # metadata did not provide a language.  This remains an assertion for review,
    # not a claim that the text's language has been authoritatively established.
    if not values.get("language"):
        detected_language = guess_language(text)
        if detected_language:
            put(
                "language",
                detected_language,
                "nlp:stopword_frequency",
                0.68,
                derivation="nlp_derived",
                reason="Deterministic language signal from bounded function-word frequency.",
            )

    for candidate in sorted(extract(text, language=str(values.get("language") or "")), key=lambda c: -c.confidence):
        put(
            candidate.field, candidate.value, candidate.method, candidate.confidence,
            derivation=candidate.derivation, reason=candidate.reason, span=candidate.span,
        )

    if values.get("language"):
        values.setdefault("language_status", "deterministic")
    else:
        values["language_status"] = "unresolved"
        provenance.setdefault(
            "language",
            {
                "method": "deterministic_ingest",
                "confidence": 0.0,
                "derivation": "deterministic",
                "status": "unresolved",
                "reason": "No bounded language signal was strong enough to propose a language.",
            },
        )
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
            applied[field] = {
                "value": value, "method": info.get("method") or "deterministic_ingest", "confidence": confidence,
                "derivation": info.get("derivation") or "deterministic",
                **({"reason": info["reason"]} if info.get("reason") else {}),
                **({"alternatives": info["alternatives"]} if info.get("alternatives") else {}),
            }
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


def _rtf_page_breaks(raw: str) -> tuple[str, list[str] | None, str | None]:
    """Turn ``\\page`` / ``\\pgnstartN`` into form feeds and printed labels, before control words are stripped."""
    number = 1
    labels: list[int] = []
    chunks: list[str] = []
    buf: list[str] = []
    saw_break = False
    saw_start = False

    def flush() -> None:
        chunks.append("".join(buf))
        labels.append(number)
        buf.clear()

    index = 0
    while index < len(raw):
        if raw.startswith("\\pgnstart", index):
            match = re.match(r"\\pgnstart(-?\d+)", raw[index:])
            if match:
                number = int(match.group(1))
                saw_start = True
                index += match.end()
                continue
        if raw.startswith("\\page", index) and (index + 5 >= len(raw) or not raw[index + 5].isalpha()):
            flush()
            saw_break = True
            number += 1
            index += 5
            if index < len(raw) and raw[index] == " ":
                index += 1
            continue
        buf.append(raw[index])
        index += 1
    flush()
    if not saw_break and not saw_start:
        return raw, None, None
    while chunks and not chunks[0].strip():
        chunks.pop(0)
        labels.pop(0)
    while chunks and not chunks[-1].strip():
        chunks.pop()
        labels.pop()
    if not chunks:
        return raw, None, None
    pattern = "rtf_page_break" if saw_break else "rtf_page_start"
    return "\f".join(chunks), [str(label) for label in labels], pattern


def rtf_to_text(data: bytes) -> tuple[str, dict[str, Any]]:
    validate_rtf(data)
    raw = data.decode("latin-1", errors="replace")
    raw, labels, pattern = _rtf_page_breaks(raw)
    embedded: dict[str, Any] = {}
    if labels and pattern:
        embedded["_native_page_labels"] = labels
        embedded["_native_page_pattern"] = pattern
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


def _pg_start(sect: Any) -> int | None:
    for node in sect.iter(W_NS + "pgNumType"):
        raw = node.get(W_NS + "start")
        if raw and raw.isdigit() and 0 < int(raw) <= 20000:
            return int(raw)
    return None


def _docx_body_pages(document: Any) -> tuple[str, list[str] | None, str | None]:
    """Printed pages from Word page breaks and ``w:pgNumType`` start values."""
    body = document.find(W_NS + "body")
    if body is None:
        return "", None, None
    pages: list[list[str]] = [[]]
    labels = [1]
    saw_break = False
    saw_start = False

    def close_page(start: int | None = None) -> None:
        pages.append([])
        labels.append(start if start is not None else labels[-1] + 1)

    for child in list(body):
        local = child.tag.rsplit("}", 1)[-1]
        if local == "sectPr":
            start = _pg_start(child)
            # The body's sectPr describes the section already read. Its start is that section's first page.
            if start is not None and not saw_start:
                delta = start - labels[0]
                labels[:] = [label + delta for label in labels]
                saw_start = True
            continue
        if local != "p":
            continue
        p_pr = child.find(W_NS + "pPr")
        if p_pr is not None and p_pr.find(W_NS + "pageBreakBefore") is not None and any(pages[-1]):
            saw_break = True
            close_page()
        if p_pr is not None:
            sect = p_pr.find(W_NS + "sectPr")
            if sect is not None:
                start = _pg_start(sect)
                if start is not None:
                    saw_start = True
                    if not saw_break:
                        labels[0] = start
        explicit = any(
            (node.get(W_NS + "type") == "page")
            for node in child.iter(W_NS + "br")
        )
        buf: list[str] = []
        for node in child.iter():
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "t" and node.text:
                buf.append(node.text)
            elif tag == "tab":
                buf.append(" ")
            elif tag == "br" and node.get(W_NS + "type") == "page":
                text = "".join(buf).strip()
                if text:
                    pages[-1].append(text)
                buf = []
                saw_break = True
                close_page()
            elif tag == "lastRenderedPageBreak" and not explicit:
                text = "".join(buf).strip()
                if text:
                    pages[-1].append(text)
                buf = []
                saw_break = True
                close_page()
            elif tag == "br":
                buf.append("\n")
        text = "".join(buf).strip()
        if text:
            pages[-1].append(text)
    while pages and not pages[-1]:
        pages.pop()
        labels.pop()
    if not pages or (not saw_break and not saw_start):
        flat = [paragraph for page in pages for paragraph in page]
        return "\n\n".join(flat), None, None
    pattern = "docx_page_break" if saw_break else "docx_page_start"
    return "\f".join("\n\n".join(page) for page in pages), [str(label) for label in labels], pattern


def docx_to_text(data: bytes) -> tuple[str, dict[str, Any]]:
    check_size(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            validate_docx(package)
            if "word/document.xml" not in package.namelist():
                raise ValueError("The Word document has no document body.")
            embedded: dict[str, Any] = {}
            if "docProps/core.xml" in package.namelist():
                core = safe_xml(package.read("docProps/core.xml"))
                mapping = {"title": "title", "creator": "author", "subject": "subject", "language": "language"}
                for node in core.iter():
                    key = mapping.get(node.tag.rsplit("}", 1)[-1])
                    if key and node.text:
                        embedded[key] = node.text
            document = safe_xml(package.read("word/document.xml"))
            text, labels, pattern = _docx_body_pages(document)
            if labels and pattern:
                embedded["_native_page_labels"] = labels
                embedded["_native_page_pattern"] = pattern
            return text, embedded
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError("The Word document could not be opened.") from exc


def ole_doc_to_text(data: bytes) -> tuple[str, dict[str, str]]:
    decoded = data.decode("utf-16le", errors="ignore")
    runs = re.findall(r"[^\x00-\x08\x0b\x0c\x0e-\x1f]{24,}", decoded)
    if not runs:
        runs = [item.decode("latin-1", errors="ignore") for item in re.findall(rb"[\x20-\x7e]{24,}", data)]
    text = "\n".join(run.strip() for run in runs if run.strip())
    return text, {}


_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# Page chrome that is not part of the work: MediaWiki/Wikisource mark it ws-noexport or noprint (their own export tools
# drop it: headers, navigation arrows, the hidden ws-data microformat), ambox is a MediaWiki maintenance notice ("not
# backed by a scanned copy"), and hidden text is unseen. Generic class names are deliberately not treated as chrome.
_CHROME_CLASSES = {"ws-noexport", "noprint", "ambox"}


def _page_token(value: str) -> str | None:
    """A printed page token from a Gutenberg/Wikisource page-number element."""
    text = re.sub(r"\s+", " ", value).strip(" []().")
    match = re.fullmatch(r"(?:page|pg|p\.?)?\s*(\d{1,5})", text, re.I)
    if match and match.group(1):
        return str(int(match.group(1)))
    if re.fullmatch(r"[ivxlcdm]{1,8}", text, re.I):
        return text.lower()
    return None


def _is_chrome(attr: dict[str, str]) -> bool:
    classes = set((attr.get("class") or "").lower().split())
    return (
        bool(classes & _CHROME_CLASSES)
        or (attr.get("id") or "").lower() == "ws-data"
        or bool(re.search(r"display\s*:\s*none", attr.get("style") or "", re.I))
    )


class _HtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: list[str] = []
        self.metas: dict[str, str] = {}
        self.lang = ""
        self._skip = 0
        self._in_title = False
        self._chrome_tag = ""
        self._chrome_depth = 0
        self._pagenum_tag = ""
        self._pagenum_depth = 0
        self._pagenum_buf: list[str] = []
        self._pagenum_attr = ""

    def _emit_pagenum(self) -> None:
        token = _page_token("".join(self._pagenum_buf)) or _page_token(self._pagenum_attr)
        self._pagenum_buf = []
        self._pagenum_attr = ""
        if not token:
            return
        if token.isdigit():
            self.parts.append(f"\n\n[Page {int(token)}]\n\n")
        else:
            self.parts.append(f"\n\n[{token}]\n\n")

    def handle_comment(self, data: str) -> None:
        if self._skip or self._chrome_depth or self._pagenum_depth:
            return
        match = re.search(r"\b(?:page|pg|p)\.?\s*#?\s*(\d{1,5})\b", data, re.I)
        if match:
            self.parts.append(f"\n\n[Page {int(match.group(1))}]\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if self._pagenum_depth:
            if tag == self._pagenum_tag and tag not in _VOID_TAGS:
                self._pagenum_depth += 1
            return
        if self._chrome_depth:
            if tag == self._chrome_tag and tag not in _VOID_TAGS:
                self._chrome_depth += 1
            return
        classes = set((attr.get("class") or "").lower().split())
        # Wikisource currently emits both historical `pagenum` and
        # ProofreadPage `pagenumber` variants. Treat provider-native page
        # markers as authoritative before generic chrome suppression so
        # classes such as `ws-noexport` do not discard the printed folio.
        is_page_number = bool(
            classes & {"pagenum", "pagenumber", "page-number", "ws-pagenumber"}
        )
        has_page_data = bool(
            attr.get("data-page")
            or attr.get("data-page-number")
            or attr.get("data-page-name")
        )
        if is_page_number or has_page_data:
            anchor = attr.get("id") or attr.get("name") or ""
            page_anchor = re.fullmatch(r"(?:page|pg|p)[_\-]?(\d{1,5})", anchor, re.I)
            # `data-page-name` identifies the ProofreadPage scan (for example
            # Page:Book.djvu/27), not necessarily the printed folio. Prefer
            # visible marker text and explicit numeric page attributes; only
            # use the anchor as a deterministic fallback.
            self._pagenum_attr = (
                attr.get("data-page")
                or attr.get("data-page-number")
                or (page_anchor.group(1) if page_anchor else "")
            )
            self._pagenum_buf = []
            if tag in _VOID_TAGS:
                self._emit_pagenum()
            else:
                self._pagenum_tag, self._pagenum_depth = tag, 1
            return
        if tag not in _VOID_TAGS and tag not in {"html", "head", "body", "title"} and _is_chrome(attr):
            self._chrome_tag, self._chrome_depth = tag, 1
            return
        if tag == "html" and attr.get("lang") and not self.lang:
            self.lang = attr["lang"].strip()
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (attr.get("name") or attr.get("property") or attr.get("itemprop") or "").lower()
            if key and attr.get("content"):
                self.metas[key] = attr["content"]
        anchor = attr.get("id") or attr.get("name") or ""
        page_anchor = re.fullmatch(r"(?:page|pg|p)[_\-]?(\d{1,5})", anchor, re.I)
        classes = (attr.get("class") or "").lower()
        if page_anchor and not self._skip:
            # Gutenberg/Wikisource-style page anchors become an explicit marker line.
            self.parts.append(f"\n\n[Page {int(page_anchor.group(1))}]\n\n")
        elif "pagebreak" in classes:
            self.parts.append("\n\n")
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._pagenum_depth:
            if tag == self._pagenum_tag:
                self._pagenum_depth -= 1
                if self._pagenum_depth == 0:
                    self._emit_pagenum()
            return
        if self._chrome_depth:
            if tag == self._chrome_tag:
                self._chrome_depth -= 1
            return
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "h1", "h2", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title.append(data)
        if self._pagenum_depth:
            self._pagenum_buf.append(data)
            return
        if self._chrome_depth:
            return
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, dict[str, str]]:
    parser = _HtmlText()
    parser.feed(html)
    embedded = {
        "title": re.sub(r"\s+", " ", "".join(parser.title)).strip() or parser.metas.get("og:title") or parser.metas.get("citation_title") or "",
        "author": parser.metas.get("author") or parser.metas.get("citation_author") or parser.metas.get("dc.creator") or "",
        "language": parser.metas.get("language") or parser.metas.get("dc.language") or parser.lang or "",
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
