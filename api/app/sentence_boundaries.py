# Copyright 2026 Aaron John Schlosser, PhD.
"""Keep corpus record boundaries on sentence ends.

PDF blocks are layout units: a block, a column or a page can stop in the middle of a sentence, and
a language model that proposes record boundaries can pick any of them. A record is a unit people
quote and cite, so it must not start or stop mid-sentence. This module is the deterministic check
that enforces that after segmentation, whatever proposed the boundaries.

A boundary "after block B" is clean when B ends a sentence (or is not running text, such as a
heading) and the block after it does not continue one. An unclean boundary is moved to the nearest
clean one between its neighbours; if there is none it is dropped, which joins the two records. When
joining would make a record larger than `hard_max_chars` the boundary is kept and reported instead:
a single sentence longer than the limit cannot be split without cutting it, and cutting it is worse
than an oversized record. The report lists every such case so a reviewer sees it.

What this cannot know: a sentence-final full stop after an abbreviation ("Dr.") looks like a clean
end, and text with no punctuation at all (verse, lists, OCR noise) has no sentence ends to find.
Those are covered by the next-block-starts-lowercase test and by the size cap, not by certainty.
"""

from __future__ import annotations

import re
from typing import Any

# A sentence end: terminal punctuation, optionally followed by closing quotes or brackets.
_SENTENCE_END = re.compile(r"[.!?…]+[\"'’”»)\]]*\s*$")
# A next block that plainly continues the previous sentence.
_CONTINUATION_START = re.compile(r"^\s*(?:[a-zà-öø-ÿ]|[,;:)\]»”’])")
_RUNNING_TEXT = {"body", "paragraph", "text"}


def ends_sentence(block: dict[str, Any]) -> bool:
    """True when a block can be the last block of a record."""
    text = str(block.get("text") or "").rstrip()
    if not text:
        return True
    if str(block.get("type") or "body") not in _RUNNING_TEXT:
        return True  # a heading, caption or page furniture is not the middle of a sentence
    return bool(_SENTENCE_END.search(text))


def starts_mid_sentence(block: dict[str, Any]) -> bool:
    text = str(block.get("text") or "")
    if str(block.get("type") or "body") not in _RUNNING_TEXT:
        return False
    return bool(_CONTINUATION_START.match(text))


def clean_boundary(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return ends_sentence(left) and not starts_mid_sentence(right)


def snap_boundaries_to_sentences(
    blocks: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    hard_max_chars: int = 12000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return boundaries that fall on sentence ends, plus a report of what changed.

    `boundaries` are dicts with `after_block_id`; other keys travel with a boundary that is kept or
    moved. The last block of the document always ends a record whatever it says.
    """
    index_of = {str(block.get("block_id")): i for i, block in enumerate(blocks)}
    cuts = sorted({index_of[str(b["after_block_id"])] for b in boundaries if str(b.get("after_block_id")) in index_of})
    evidence = {index_of[str(b["after_block_id"])]: b for b in boundaries if str(b.get("after_block_id")) in index_of}
    lengths = [len(str(block.get("text") or "")) for block in blocks]
    last = len(blocks) - 1
    report: dict[str, Any] = {"moved": [], "merged": [], "unavoidable": []}

    def clean(i: int) -> bool:
        return i >= last or clean_boundary(blocks[i], blocks[i + 1])

    result: list[int] = []
    origin: dict[int, int] = {}
    previous = -1
    for position, cut in enumerate(cuts):
        following = cuts[position + 1] if position + 1 < len(cuts) else last
        if cut >= last:
            continue
        if clean(cut):
            result.append(cut)
            origin[cut] = cut
            previous = cut
            continue
        # Nearest clean boundary strictly between the neighbouring cuts.
        candidates = [i for i in range(previous + 1, min(following, last)) if clean(i)]
        if candidates:
            target = min(candidates, key=lambda i: (abs(i - cut), i - cut))
            result.append(target)
            origin[target] = cut
            previous = target
            report["moved"].append({"from": str(blocks[cut]["block_id"]), "to": str(blocks[target]["block_id"])})
            continue
        # None: drop it, joining this record to the next, unless that makes it too large.
        joined = sum(lengths[previous + 1 : following + 1])
        if joined <= hard_max_chars:
            report["merged"].append({"dropped": str(blocks[cut]["block_id"])})
            continue
        result.append(cut)
        origin[cut] = cut
        previous = cut
        report["unavoidable"].append({"after_block_id": str(blocks[cut]["block_id"]), "reason": "sentence_longer_than_record_limit"})

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for i in result:
        if i in seen:
            continue
        seen.add(i)
        base = dict(evidence.get(origin[i], {}))
        base["after_block_id"] = str(blocks[i]["block_id"])
        if origin[i] != i:
            base["moved_to_sentence_end_from"] = str(blocks[origin[i]]["block_id"])
        out.append(base)
    return out, report
