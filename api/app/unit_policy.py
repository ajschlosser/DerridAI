# Copyright 2026 Aaron John Schlosser, PhD.
"""Source-unit policies: how finely a source is divided into evidence units.

A source unit is the smallest span an evidence reference can point to. The default keeps
whatever the extractor produced (paragraphs for prose, layout blocks for PDFs). A policy may
divide those blocks further, into sentences, lines, or fixed-size windows, or merge nothing.
Division is deterministic and conserves text: the pieces of a block, joined, are that block.
Page, locator, speaker and label fields are inherited by every piece; headings, headers and
footers are never divided.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

from .language_segmentation import (
    profile_metadata,
    split_sentences as _language_split_sentences,
)

MODES = ("default", "paragraph", "line", "sentence", "chars", "auto")
MIN_CHARS, MAX_CHARS = 60, 20000
MAX_GROUP = 50
GROUPABLE = {"paragraph", "sentence"}
DIVISIBLE = {"paragraph", "block_quote", "list_item", "footnote", "speech", "text"}


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Validated policy; raises ValueError for unknown modes or unusable sizes."""
    raw = dict(policy or {})
    mode = str(raw.get("mode") or "default")
    if mode not in MODES:
        raise ValueError(f"Unknown source-unit mode {mode!r}; choose one of {', '.join(MODES)}.")
    out: dict[str, Any] = {"mode": mode}
    language = str(raw.get("language") or "").strip()
    if language:
        out["language"] = language
    if mode == "auto":
        # Paragraphs that fit are kept whole; a longer one is divided into sentences. The limit is the build's long
        # record size, so the record size, not the extractor's paragraphing, decides how small records can be.
        try:
            limit = int(raw.get("max_chars"))
        except (TypeError, ValueError) as exc:
            raise ValueError("An automatic policy needs the longest paragraph to keep whole, in characters.") from exc
        if not MIN_CHARS <= limit <= MAX_CHARS * 5:
            raise ValueError(f"The automatic paragraph limit must be between {MIN_CHARS} and {MAX_CHARS * 5}.")
        out["max_chars"] = limit
    if mode == "chars":
        try:
            size = int(raw.get("chars"))
        except (TypeError, ValueError) as exc:
            raise ValueError("A character-window policy needs a size in characters.") from exc
        if not MIN_CHARS <= size <= MAX_CHARS:
            raise ValueError(f"Characters per unit must be between {MIN_CHARS} and {MAX_CHARS}.")
        out["chars"] = size
    if mode in GROUPABLE:
        raw_per = raw.get("per")
        if raw_per not in (None, ""):
            try:
                per = int(raw_per)
            except (TypeError, ValueError) as exc:
                raise ValueError("Units per group must be a whole number.") from exc
            if not 1 <= per <= MAX_GROUP:
                raise ValueError(f"Units per group must be between 1 and {MAX_GROUP}.")
            if per > 1:
                out["per"] = per
    return out


def split_sentences(text: str, language: str | None = None) -> list[str]:
    """Lossless language/script-aware sentence units.

    The optional language comes from source/document metadata when available.
    Without it, the shared segmentation layer falls back to conservative
    Unicode-script inference rather than assuming English punctuation rules.
    """
    return _language_split_sentences(text, language)


def split_lines(text: str) -> list[str]:
    parts = re.split(r"(?<=\n)", text)
    return [part for part in parts if part.strip()]


def split_chars(text: str, size: int) -> list[str]:
    """Windows of about ``size`` characters, cut at whitespace where possible."""
    pieces: list[str] = []
    start, length = 0, len(text)
    while start < length:
        end = min(length, start + size)
        if end < length:
            cut = text.rfind(" ", start + size // 2, end)
            cut = cut if cut != -1 else text.rfind("\n", start + size // 2, end)
            end = cut + 1 if cut != -1 else end
        pieces.append(text[start:end])
        start = end
    return [piece for piece in pieces if piece.strip()]


def divide(text: str, policy: dict[str, Any]) -> list[str]:
    mode = policy["mode"]
    if mode == "sentence":
        sentences = split_sentences(text, str(policy.get("language") or "") or None)
        per = int(policy.get("per") or 1)
        if per > 1:
            # Whitespace stays attached to each sentence, so joining a group loses nothing.
            return ["".join(sentences[i:i + per]) for i in range(0, len(sentences), per)]
        return sentences
    if mode == "line":
        return split_lines(text)
    if mode == "chars":
        return split_chars(text, int(policy["chars"]))
    if mode == "auto":
        return (
            split_sentences(text, str(policy.get("language") or "") or None)
            if len(text) > int(policy["max_chars"])
            else [text]
        )
    return [text]


def apply_unit_policy(
    blocks: list[dict[str, Any]], policy: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[int, list[str]]]:
    """Return ``(blocks, remap)``: derived blocks and, per parent index, its new block IDs.

    Excluded blocks (page numbers, repeated headers) and non-prose block types pass through
    untouched. Child IDs are ``<parent>-u001``; children keep the parent's page and locators.
    """
    resolved = normalize_policy(policy)
    if resolved["mode"] == "paragraph" and resolved.get("per"):
        return _group_paragraphs(blocks, int(resolved["per"]), resolved)
    if resolved["mode"] in {"default", "paragraph"}:
        return [dict(block) for block in blocks], {i: [str(b.get("block_id"))] for i, b in enumerate(blocks)}
    out: list[dict[str, Any]] = []
    remap: dict[int, list[str]] = {}
    for index, block in enumerate(blocks):
        text = str(block.get("text") or "")
        divisible = (
            not block.get("excluded_reason")
            and str(block.get("type") or "paragraph") in DIVISIBLE
            and str(block.get("locator_kind") or "") != "time"
        )
        parts = divide(text, resolved) if divisible else [text]
        if len(parts) <= 1:
            out.append(dict(block))
            remap[index] = [str(block.get("block_id"))]
            continue
        ids: list[str] = []
        for number, part in enumerate(parts, 1):
            child = dict(block)
            child["block_id"] = f"{block.get('block_id')}-u{number:03d}"
            child["text"] = part.strip()
            child["parent_block_id"] = block.get("block_id")
            child["unit_policy"] = resolved["mode"]
            out.append(child)
            ids.append(child["block_id"])
        remap[index] = ids
    return out, remap


def _mergeable(block: dict[str, Any]) -> bool:
    return (
        not block.get("excluded_reason")
        and str(block.get("type") or "paragraph") == "paragraph"
        and str(block.get("locator_kind") or "") != "time"
    )


def _group_paragraphs(
    blocks: list[dict[str, Any]], per: int, resolved: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[int, list[str]]]:
    """Merge runs of ``per`` adjacent paragraphs that sit on the same page into one unit.

    Text is conserved: a merged unit is its paragraphs joined by a blank line, in order. Runs never
    cross a page, an excluded block or a non-paragraph block, so page semantics stay truthful.
    """
    out: list[dict[str, Any]] = []
    remap: dict[int, list[str]] = {}
    run: list[tuple[int, dict[str, Any]]] = []
    group_number = 0

    def flush() -> None:
        nonlocal group_number
        if not run:
            return
        if len(run) == 1:
            index, block = run[0]
            out.append(dict(block))
            remap[index] = [str(block.get("block_id"))]
        else:
            group_number += 1
            merged = dict(run[0][1])
            merged["block_id"] = f"{run[0][1].get('block_id')}-g{group_number:03d}"
            merged["text"] = "\n\n".join(str(b.get("text") or "").strip() for _, b in run)
            merged["parent_block_ids"] = [str(b.get("block_id")) for _, b in run]
            merged["unit_policy"] = "paragraph"
            out.append(merged)
            for index, _ in run:
                remap[index] = [merged["block_id"]]
        run.clear()

    for index, block in enumerate(blocks):
        if not _mergeable(block):
            flush()
            out.append(dict(block))
            remap[index] = [str(block.get("block_id"))]
            continue
        if run and (block.get("page") != run[0][1].get("page") or len(run) >= per):
            flush()
        run.append((index, block))
    flush()
    return out, remap


def preview(blocks: list[dict[str, Any]], policy: dict[str, Any] | None, *, sample: int = 8) -> dict[str, Any]:
    """Counts and a few sample units, without building anything."""
    resolved = normalize_policy(policy)
    derived, _ = apply_unit_policy(blocks, resolved)
    included = [b for b in derived if not b.get("excluded_reason")]
    sizes = [len(str(b.get("text") or "")) for b in included]
    return {
        "policy": resolved,
        "unit_count": len(included),
        "source_block_count": len([b for b in blocks if not b.get("excluded_reason")]),
        "median_chars": int(statistics.median(sizes)) if sizes else 0,
        "max_chars": max(sizes, default=0),
        "min_chars": min(sizes, default=0),
        "language_segmentation": profile_metadata(
            str(resolved.get("language") or "") or None,
            "\n".join(str(block.get("text") or "") for block in included[:8]),
        ),
        "sample": [
            {"block_id": b.get("block_id"), "page": b.get("page"), "text": str(b.get("text") or "")[:240]}
            for b in included[:sample]
        ],
    }
