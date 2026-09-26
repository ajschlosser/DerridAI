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

MODES = ("default", "paragraph", "line", "sentence", "chars", "auto")
MIN_CHARS, MAX_CHARS = 60, 20000
DIVISIBLE = {"paragraph", "block_quote", "list_item", "footnote", "speech", "text"}
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "st", "sr", "jr", "vs", "cf", "etc", "eg", "ie", "fig", "no", "vol", "pp", "p",
    "ch", "ed", "eds", "trans", "op", "cit", "ibid", "viz", "al", "ca", "approx", "dept", "gen", "col", "rev", "hon",
    "m", "mme", "mlle", "mm", "me", "cie", "éd", "trad", "sq", "sqq", "l", "ll", "s", "v", "n",
}
_TERMINATORS = ".!?…"
_CLOSERS = "\"'”’»)]}"
_SENTENCE_END = re.compile(rf"([{re.escape(_TERMINATORS)}]+[{re.escape(_CLOSERS)}]*)(\s+)")


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Validated policy; raises ValueError for unknown modes or unusable sizes."""
    raw = dict(policy or {})
    mode = str(raw.get("mode") or "default")
    if mode not in MODES:
        raise ValueError(f"Unknown source-unit mode {mode!r}; choose one of {', '.join(MODES)}.")
    out: dict[str, Any] = {"mode": mode}
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
    return out


def _is_abbreviation(before: str) -> bool:
    word = re.search(r"([^\W\d_]+)\.?$", before, re.UNICODE)
    if not word:
        return bool(re.search(r"\d$", before)) and False
    token = word.group(1).lower()
    return token in _ABBREVIATIONS or (len(token) == 1 and token.isalpha())


def split_sentences(text: str) -> list[str]:
    """Sentences of ``text`` whose concatenation is ``text`` exactly (whitespace stays attached)."""
    pieces: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        end = match.end()
        head = text[start:match.start(1)]
        terminator = match.group(1)
        rest = text[end:end + 1]
        if terminator.startswith(".") and terminator == "." and _is_abbreviation(head):
            continue
        if terminator == "." and re.search(r"\d$", head) and rest.isdigit():
            continue  # "3. 5" style numbering artifacts
        if rest and rest.islower() and terminator == ".":
            continue  # a period followed by a lowercase word is not a sentence end
        pieces.append(text[start:end])
        start = end
    if start < len(text):
        pieces.append(text[start:])
    return [piece for piece in pieces if piece.strip()]


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
        return split_sentences(text)
    if mode == "line":
        return split_lines(text)
    if mode == "chars":
        return split_chars(text, int(policy["chars"]))
    if mode == "auto":
        return split_sentences(text) if len(text) > int(policy["max_chars"]) else [text]
    return [text]


def apply_unit_policy(
    blocks: list[dict[str, Any]], policy: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[int, list[str]]]:
    """Return ``(blocks, remap)``: derived blocks and, per parent index, its new block IDs.

    Excluded blocks (page numbers, repeated headers) and non-prose block types pass through
    untouched. Child IDs are ``<parent>-u001``; children keep the parent's page and locators.
    """
    resolved = normalize_policy(policy)
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
        "sample": [
            {"block_id": b.get("block_id"), "page": b.get("page"), "text": str(b.get("text") or "")[:240]}
            for b in included[:sample]
        ],
    }
