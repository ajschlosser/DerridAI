# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic record restructuring: split, merge, and create-from-selection.

A structural edit never mutates a Record in place. The affected Records are
*retired* (kept as lineage tombstones, their IDs never reused) and new Records
with new IDs are minted from the exact source text. Text is conserved: the
whitespace-insensitive concatenation of the new Records must equal that of the
retired ones, or the edit is refused.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .corpus_record_quality import iso_now
from .corpus_segmentation import _construct_records

JOIN = "\n\n"


def _squash(text: str) -> str:
    return "".join(str(text or "").split())


def assert_text_conserved(before: list[str], after: list[str]) -> None:
    """Refuse an edit that loses, invents, duplicates, or reorders text."""
    if _squash("".join(before)) != _squash("".join(after)):
        raise ValueError("Restructuring would change the record text; refusing to lose, add, or reorder text.")


def new_record_id(seed_id: str, taken: set[str]) -> str:
    base = re.sub(r"-(?:[sm]|x)?[0-9a-f]{8}$", "", str(seed_id or "pdf")) or "pdf"
    while True:
        candidate = f"{base}-{uuid.uuid4().hex[:8]}"
        if candidate not in taken:
            taken.add(candidate)
            return candidate


def block_ids_for_range(text: str, block_ids: list[str], blocks: dict[str, dict[str, Any]], start: int, end: int) -> tuple[list[str], bool]:
    """Source blocks overlapping ``text[start:end]``.

    Returns ``(ids, precise)``. When the reviewed text can no longer be aligned
    to its blocks (it was edited), the parent's blocks are returned with
    ``precise=False`` so provenance is conservative rather than invented.
    """
    cursor = 0
    located: list[tuple[str, int, int]] = []
    for block_id in block_ids:
        block_text = str((blocks.get(block_id) or {}).get("text") or "").strip()
        if not block_text:
            continue
        index = text.find(block_text, cursor)
        if index < 0:
            return list(block_ids), False
        located.append((block_id, index, index + len(block_text)))
        cursor = index + len(block_text)
    chosen = [block_id for block_id, lo, hi in located if lo < end and hi > start]
    return (chosen, True) if chosen else (list(block_ids), False)


def mint_record(
    *,
    asset: dict[str, Any],
    blocks: dict[str, dict[str, Any]],
    block_ids: list[str],
    text: str,
    record_id: str,
    parents: list[dict[str, Any]],
    operation: str,
    transaction_id: str,
    manifest_apply: Any,
    precise: bool,
) -> dict[str, Any]:
    """Build a clean, unreviewed Record for ``text`` and stamp its lineage."""
    ordered = list(dict.fromkeys(block_ids))
    group = [blocks[block_id] for block_id in ordered if block_id in blocks]
    if not group:
        raise ValueError("Cannot locate source blocks for the new record.")
    record = _construct_records(asset, group, [])[0]
    record["record_id"] = record_id
    record["record_revision"] = 1
    clean = text.strip()
    record["text"] = clean
    record["text_length"] = len(clean)
    # The parents' original extraction stays in their retired tombstones; the
    # new record's reviewed text is the boundary decision itself.
    record["source_extracted_text"] = clean
    record["text_review_status"] = "human_corrected"
    record["text_review_source"] = f"human_{operation}"
    record["text_reviewed_at"] = iso_now()
    record["needs_review"] = True
    record["review_reason"] = "Record created by a structural edit; verify its text and metadata."
    record["review_disposition"] = "pending"
    record["accepted"] = False
    record["rejected"] = False
    record["lineage"] = {
        "operation": operation,
        "transaction_id": transaction_id,
        "parent_record_ids": [str(parent.get("record_id")) for parent in parents],
        "parent_revisions": {str(parent.get("record_id")): int(parent.get("record_revision") or 1) for parent in parents},
        "source_blocks_precise": precise,
        "at": iso_now(),
    }
    manifest_apply(record)
    return record


def tombstone(record: dict[str, Any], *, operation: str, transaction_id: str, successors: list[str]) -> dict[str, Any]:
    import json

    return {
        "record_id": str(record.get("record_id")),
        "retired_at": iso_now(),
        "operation": operation,
        "transaction_id": transaction_id,
        "successor_record_ids": successors,
        "record": json.loads(json.dumps(record)),
    }
