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

"""Deterministic record restructuring: split, merge, and create-from-selection.

A structural edit never mutates a Record in place. The affected Records are
*retired* (kept as lineage tombstones, their IDs never reused) and new Records
with new IDs are minted from the exact source text. Text is conserved: the
whitespace-insensitive concatenation of the new Records must equal that of the
retired ones, or the edit is refused.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from .corpus_record_quality import iso_now
from .corpus_segmentation import _construct_records

JOIN = "\n\n"


def _squash(text: str) -> str:
    return "".join(str(text or "").split())


def source_unit_text_hash(text: str) -> str:
    """Return the content identity persisted for an authoritative source unit."""
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def normalize_source_units(
    rows: list[dict[str, Any]] | None,
    blocks: list[dict[str, Any]],
    *,
    source_document_id: str,
) -> list[dict[str, Any]]:
    """Normalize legacy block rows into the build's source-unit representation.

    Older builds have no unit store and only carry ``source_block_ids`` on
    records.  A block is therefore the compatibility unit until a structural
    edit explicitly replaces it.
    """
    by_id = {str(block.get("block_id")): block for block in blocks if block.get("block_id")}
    source: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        unit_id = str(raw.get("source_unit_id") or raw.get("unit_id") or raw.get("block_id") or "")
        if not unit_id or unit_id in seen:
            continue
        block_id = str(raw.get("block_id") or (raw.get("source_block_ids") or [unit_id])[0] or unit_id)
        block = by_id.get(block_id) or {}
        text = str(raw.get("text") if raw.get("text") is not None else block.get("text") or "")
        item = {
            **dict(block),
            **dict(raw),
            "source_unit_id": unit_id,
            "unit_id": unit_id,
            "block_id": block_id,
            "source_block_ids": list(dict.fromkeys(str(value) for value in (raw.get("source_block_ids") or [block_id]) if value)),
            "source_document_id": str(raw.get("source_document_id") or source_document_id),
            "text": text,
            "text_hash": source_unit_text_hash(text),
            "parent_unit_ids": list(dict.fromkeys(str(value) for value in (raw.get("parent_unit_ids") or []) if value)),
            "consumed_ranges": list(raw.get("consumed_ranges") or []),
            "active": bool(raw.get("active", True)),
        }
        item.setdefault("locator_kind", block.get("locator_kind"))
        source.append(item)
        seen.add(unit_id)
    for block in blocks:
        block_id = str(block.get("block_id") or "")
        if not block_id or block_id in seen:
            continue
        text = str(block.get("text") or "")
        source.append({
            **dict(block),
            "source_unit_id": block_id,
            "unit_id": block_id,
            "block_id": block_id,
            "source_block_ids": [block_id],
            "source_document_id": str(source_document_id),
            "text": text,
            "text_hash": source_unit_text_hash(text),
            "parent_unit_ids": [],
            "consumed_ranges": [],
            "active": True,
        })
    return source


def safe_neighbor_absorption(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Whether two adjacent source units may be folded into one replacement.

    Missing locators are deliberately unsafe.  This keeps a structural edit
    from silently erasing an unknown page/time/type boundary.
    """
    if str(left.get("type") or "") != str(right.get("type") or ""):
        return False
    left_kind = str(left.get("locator_kind") or ("time" if left.get("start") is not None else "page"))
    right_kind = str(right.get("locator_kind") or ("time" if right.get("start") is not None else "page"))
    if left_kind != right_kind:
        return False
    if left_kind == "time":
        try:
            left_end = left.get("locator_end", left.get("end"))
            right_start = right.get("locator_start", right.get("start"))
            return abs(float(right_start) - float(left_end)) <= 0.001
        except (TypeError, ValueError):
            return False
    try:
        left_page = int(left.get("page"))
        right_page = int(right.get("page"))
    except (TypeError, ValueError):
        return False
    return left_page == right_page


def assert_active_source_unit_ownership(
    records: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> None:
    """Reject active topology that shares or references a retired unit."""
    active = {
        str(unit.get("source_unit_id") or unit.get("unit_id"))
        for unit in units
        if unit.get("active")
    }
    owners: dict[str, str] = {}
    for record in records:
        record_id = str(record.get("record_id") or "")
        for value in record.get("source_unit_ids") or record.get("source_block_ids") or []:
            unit_id = str(value)
            if not unit_id:
                continue
            if unit_id not in active:
                raise ValueError("A Record references an inactive source unit.")
            prior = owners.get(unit_id)
            if prior is not None and prior != record_id:
                raise ValueError("An active source unit cannot be shared across Records.")
            owners[unit_id] = record_id


def active_source_unit_map(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return active SourceUnits keyed by canonical unit ID."""
    return {
        str(unit.get("source_unit_id") or unit.get("unit_id")): unit
        for unit in units
        if unit.get("active")
        and str(unit.get("source_unit_id") or unit.get("unit_id") or "")
    }


def record_source_unit_ids(record: dict[str, Any]) -> list[str]:
    """Return the canonical topology IDs for a Record, with legacy block fallback."""
    explicit = [
        str(value)
        for value in record.get("source_unit_ids") or []
        if str(value)
    ]
    if explicit:
        return explicit
    return [
        str(value)
        for value in record.get("source_block_ids") or []
        if str(value)
    ]


def source_unit_root_block_ids(
    unit_id: str,
    units_by_id: dict[str, dict[str, Any]],
    source_block_ids: set[str],
    seen: set[str] | None = None,
) -> list[str]:
    """Resolve a SourceUnit through lineage to immutable extraction-block IDs.

    Structural edits may replace one extraction block with multiple SourceUnits,
    or later replace those replacement units again. Publication validation needs
    the immutable extraction roots for coverage/order checks without flattening
    the current SourceUnit topology back into legacy block ownership.
    """
    value = str(unit_id or "")
    if not value:
        return []
    if value in source_block_ids:
        return [value]
    visited = set(seen or ())
    if value in visited:
        return []
    visited.add(value)
    unit = units_by_id.get(value)
    if not unit:
        return []
    parents = [
        str(parent)
        for parent in unit.get("parent_unit_ids") or []
        if str(parent)
    ]
    if not parents:
        parents = [
            str(parent)
            for parent in unit.get("source_block_ids") or []
            if str(parent)
        ]
    if not parents:
        block_id = str(unit.get("block_id") or "")
        parents = [block_id] if block_id else []
    roots: list[str] = []
    for parent in parents:
        for root in source_unit_root_block_ids(
            parent,
            units_by_id,
            source_block_ids,
            visited,
        ):
            if root not in roots:
                roots.append(root)
    return roots



def _source_unit_descends_from(
    unit_id: str,
    ancestor_id: str,
    units_by_id: dict[str, dict[str, Any]],
    seen: set[str] | None = None,
) -> bool:
    """Whether a SourceUnit has an ancestor in its explicit lineage."""
    if unit_id == ancestor_id:
        return True
    visited = set(seen or ())
    if unit_id in visited:
        return False
    visited.add(unit_id)
    unit = units_by_id.get(unit_id)
    if not unit:
        return False
    parents = [
        str(value)
        for value in unit.get("parent_unit_ids") or []
        if str(value)
    ]
    return any(
        parent == ancestor_id
        or _source_unit_descends_from(parent, ancestor_id, units_by_id, visited)
        for parent in parents
    )


def repair_record_source_topology(
    records: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Repair only provably equivalent stale Record-to-SourceUnit bindings.

    A retired SourceUnit may be replaced by its active descendants only when
    their concatenated extraction is identical. A missing/stale unit ID may also
    be recovered when immutable roots plus the previous source extraction identify
    exactly one contiguous active window. Ambiguity remains a validation blocker.

    Every applied repair is appended to source_topology_reconciliation_history so
    compatibility migration never erases the prior topology.
    """
    all_units = {
        str(unit.get("source_unit_id") or unit.get("unit_id")): unit
        for unit in units
        if str(unit.get("source_unit_id") or unit.get("unit_id") or "")
    }
    active = active_source_unit_map(units)
    active_order = [
        str(unit.get("source_unit_id") or unit.get("unit_id"))
        for unit in units
        if unit.get("active")
        and str(unit.get("source_unit_id") or unit.get("unit_id") or "")
    ]
    if not active_order:
        return []

    immutable_roots = {
        str(value)
        for unit in units
        for value in unit.get("source_block_ids") or []
        if str(value)
    }

    def active_descendants(unit_id: str) -> list[str]:
        return [
            candidate
            for candidate in active_order
            if _source_unit_descends_from(candidate, unit_id, all_units)
        ]

    def unit_text(unit_ids: list[str]) -> str:
        return JOIN.join(
            str(active[unit_id].get("text") or "").strip()
            for unit_id in unit_ids
            if unit_id in active
            and str(active[unit_id].get("text") or "").strip()
        )

    proposals: dict[str, tuple[list[str], str, list[str]]] = {}
    fixed_owners: dict[str, str] = {}

    for record in records:
        record_id = str(record.get("record_id") or "")
        current_ids = record_source_unit_ids(record)
        if current_ids and all(unit_id in active for unit_id in current_ids):
            for unit_id in current_ids:
                fixed_owners.setdefault(unit_id, record_id)
            continue

        replacement: list[str] = []
        reasons: list[str] = []
        lineage_safe = bool(current_ids)
        for unit_id in current_ids:
            if unit_id in active:
                replacement.append(unit_id)
                continue
            descendants = active_descendants(unit_id)
            if not descendants:
                lineage_safe = False
                break
            prior = all_units.get(unit_id)
            if prior is not None:
                prior_text = _squash(str(prior.get("text") or ""))
                descendant_text = _squash(unit_text(descendants))
                if prior_text != descendant_text:
                    lineage_safe = False
                    break
            replacement.extend(descendants)
            reasons.append(f"{unit_id} -> {','.join(descendants)}")

        replacement = list(dict.fromkeys(replacement))
        if lineage_safe and replacement:
            proposals[record_id] = (
                replacement,
                "active_descendant_lineage",
                reasons,
            )
            continue

        roots = {
            str(value)
            for value in record.get("source_block_ids") or []
            if str(value)
        }
        target = _squash(str(record.get("source_extracted_text") or ""))
        if not roots or not target:
            continue
        candidates = [
            unit_id
            for unit_id in active_order
            if (
                set(
                    source_unit_root_block_ids(
                        unit_id,
                        all_units,
                        immutable_roots,
                    )
                )
                & roots
            )
        ]
        matches: list[list[str]] = []
        for start in range(len(candidates)):
            parts: list[str] = []
            for end in range(start, len(candidates)):
                parts.append(str(active[candidates[end]].get("text") or "").strip())
                joined = _squash(JOIN.join(part for part in parts if part))
                if joined == target:
                    matches.append(candidates[start : end + 1])
                if len(joined) > len(target):
                    break
        if len(matches) == 1:
            proposals[record_id] = (
                matches[0],
                "unique_source_projection_match",
                [],
            )

    proposed_owners: dict[str, list[str]] = {}
    for record_id, (unit_ids, _method, _reasons) in proposals.items():
        for unit_id in unit_ids:
            proposed_owners.setdefault(unit_id, []).append(record_id)

    events: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record.get("record_id") or "")
        proposal = proposals.get(record_id)
        if proposal is None:
            continue
        unit_ids, method, reasons = proposal
        if any(
            (
                unit_id in fixed_owners
                and fixed_owners[unit_id] != record_id
            )
            or len(proposed_owners.get(unit_id) or []) != 1
            for unit_id in unit_ids
        ):
            continue

        previous_ids = [
            str(value)
            for value in record.get("source_unit_ids") or []
            if str(value)
        ]
        if previous_ids == unit_ids:
            continue
        event = {
            "event_id": f"source-topology-{uuid.uuid4().hex}",
            "at": iso_now(),
            "method": method,
            "previous_source_unit_ids": previous_ids,
            "source_unit_ids": list(unit_ids),
            "source_block_ids": [
                str(value)
                for value in record.get("source_block_ids") or []
                if str(value)
            ],
            "lineage_replacements": reasons,
            "source_text_conserved": True,
        }
        record["source_unit_ids"] = list(unit_ids)
        history = [
            dict(item)
            for item in record.get("source_topology_reconciliation_history") or []
            if isinstance(item, dict)
        ]
        history.append(event)
        record["source_topology_reconciliation_history"] = history[-50:]
        events.append({"record_id": record_id, **event})
    return events


def synchronize_record_source_projection(
    records: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> int:
    """Rebuild derived Record extraction text from authoritative active SourceUnits.

    The Record text field is an editorial/review layer and may legitimately differ
    from the immutable extraction. source_extracted_text is a provenance projection:
    after split/combine/create operations it must be derived from the SourceUnits
    owned by the Record, never copied from reviewed text. This migration is
    deterministic and does not claim a human decision.
    """
    active = active_source_unit_map(units)
    changed = 0
    for record in records:
        unit_ids = record_source_unit_ids(record)
        if not unit_ids or any(unit_id not in active for unit_id in unit_ids):
            continue
        if not record.get("source_unit_ids"):
            record["source_unit_ids"] = list(unit_ids)
            changed += 1
        extracted = JOIN.join(
            str(active[unit_id].get("text") or "").strip()
            for unit_id in unit_ids
            if str(active[unit_id].get("text") or "").strip()
        )
        if record.get("source_extracted_text") != extracted:
            record["source_extracted_text"] = extracted
            changed += 1
    return changed

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


def reconcile_source_units(
    units: list[dict[str, Any]],
    retiring: list[dict[str, Any]],
    pieces: list[dict[str, Any]],
    created: list[dict[str, Any]],
    *,
    source_document_id: str,
    operation: str,
    transaction_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Reconcile active units and return the IDs assigned to each new record.

    ``unit_ranges`` is optional metadata supplied by the structural action.  A
    full range reuses its unit; a partial range mints a replacement unit.  A
    leading/trailing partial range may absorb its complete neighbour only when
    :func:`safe_neighbor_absorption` proves that the locator boundary is safe.
    """
    by_id = {str(item.get("source_unit_id") or item.get("unit_id")): item for item in units}
    retired_ids: list[str] = []
    old_ids: list[str] = []
    for record in retiring:
        for value in record.get("source_unit_ids") or record.get("source_block_ids") or []:
            value = str(value)
            if value and value not in old_ids:
                old_ids.append(value)
    for value in old_ids:
        if value in by_id:
            retired_ids.append(value)

    taken = set(by_id)
    replacement_ids: list[str] = []

    def mint(text: str, parent_ids: list[str], consumed: list[dict[str, Any]], template: dict[str, Any] | None = None) -> str:
        seed = str(parent_ids[0] if parent_ids else source_document_id or "unit")
        while True:
            candidate = f"{seed}-u-{uuid.uuid4().hex[:8]}"
            if candidate not in taken:
                break
        taken.add(candidate)
        row = {
            **({k: v for k, v in (template or {}).items() if k not in {"source_unit_id", "unit_id", "text", "text_hash", "active", "parent_unit_ids", "consumed_ranges", "lineage"}}),
            "source_unit_id": candidate,
            "unit_id": candidate,
            "source_document_id": source_document_id,
            "source_block_ids": list(dict.fromkeys(str(value) for value in parent_ids if value)),
            "text": str(text),
            "text_hash": source_unit_text_hash(text),
            "parent_unit_ids": list(dict.fromkeys(parent_ids)),
            "consumed_ranges": consumed,
            "transaction_id": transaction_id,
            "active": True,
            "lineage": {
                "operation": operation,
                "transaction_id": transaction_id,
                "parent_unit_ids": list(dict.fromkeys(parent_ids)),
                "consumed_ranges": consumed,
                "at": iso_now(),
            },
        }
        by_id[candidate] = row
        replacement_ids.append(candidate)
        return candidate

    for piece, record in zip(pieces, created):
        ranges = list(piece.get("unit_ranges") or [])
        assigned: list[str] = []
        if not ranges:
            ranges = [
                {"unit_id": str(value), "start": 0, "end": len(str((by_id.get(str(value)) or {}).get("text") or ""))}
                for value in piece.get("block_ids") or []
            ]
        partial: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for item in ranges:
            unit_id = str(item.get("unit_id") or item.get("source_unit_id") or "")
            unit = by_id.get(unit_id)
            if not unit:
                continue
            start = int(str(item.get("start") or 0))
            end = int(str(item.get("end") if item.get("end") is not None else len(str(unit.get("text") or ""))))
            whole = start <= 0 and end >= len(str(unit.get("text") or ""))
            if whole:
                assigned.append(unit_id)
            else:
                partial.append((item, unit))
        # Fold a partial at either edge into a complete adjacent unit only when
        # the source locator says the join is unambiguous.
        if len(partial) > 1 and all(item.get("text") is None for item, _unit in partial):
            parent_ids = [
                str(item.get("unit_id") or item.get("source_unit_id") or "")
                for item, _unit in partial
            ]
            assigned = [mint(str(piece.get("text") or ""), parent_ids, ranges)]
            partial = []
        if partial and len(ranges) == 2 and len(assigned) == 1:
            item, fragment = partial[0]
            neighbour = by_id.get(assigned[0])
            if neighbour and (
                safe_neighbor_absorption(fragment, neighbour)
                or safe_neighbor_absorption(neighbour, fragment)
            ):
                ordered = [str(item.get("unit_id") or item.get("source_unit_id") or "") for item in ranges]
                parent_ids = list(dict.fromkeys(value for value in ordered if value))
                assigned = [mint(str(record.get("text") or piece.get("text") or ""), parent_ids, ranges, fragment)]
                partial = []
        for item, unit in partial:
            unit_id = str(unit.get("source_unit_id") or unit.get("unit_id"))
            fragment_text = str(item.get("text") if item.get("text") is not None else piece.get("text") or "")
            assigned.append(mint(fragment_text, [unit_id], [item], unit))
        assigned = list(dict.fromkeys(assigned))
        record["source_unit_ids"] = assigned
        # source_block_ids remains the compatibility field. Replacement units
        # carry their consumed legacy block IDs so existing evidence lookups
        # continue to resolve while source_unit_ids carries new topology.
        record["source_block_ids"] = list(dict.fromkeys(
            source_block_id
            for unit_id in assigned
            for source_block_id in (
                (by_id.get(unit_id) or {}).get("source_block_ids")
                or [str((by_id.get(unit_id) or {}).get("block_id") or unit_id)]
            )
        ))
        record["source_unit_ids"] = assigned
    reused_ids = {
        str(unit_id)
        for record in created
        for unit_id in record.get("source_unit_ids") or []
    }
    for unit_id in retired_ids:
        if unit_id in reused_ids:
            continue
        by_id[unit_id]["active"] = False
        by_id[unit_id]["retired_at"] = iso_now()
        by_id[unit_id]["retired_transaction_id"] = transaction_id
        successors = [value for value in replacement_ids if unit_id in (by_id.get(value) or {}).get("parent_unit_ids", [])]
        if successors:
            by_id[unit_id]["successor_unit_ids"] = successors
    active = [item for item in by_id.values() if item.get("active")]
    inactive = [item for item in by_id.values() if not item.get("active")]
    return inactive + active, replacement_ids


def remap_evidence_bindings(
    retiring: list[dict[str, Any]],
    created: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Carry reviewed source-unit evidence across a structural replacement.

    Evidence is copied only when every referenced unit resolves to one created
    record. A split or other one-to-many mapping is retained as an explicit
    review item instead of binding evidence to an arbitrary successor.
    """
    by_id = {
        str(unit.get("source_unit_id") or unit.get("unit_id")): unit
        for unit in units
        if str(unit.get("source_unit_id") or unit.get("unit_id") or "")
    }
    created_by_unit: dict[str, list[int]] = {}
    for index, record in enumerate(created):
        for unit_id in record.get("source_unit_ids") or record.get("source_block_ids") or []:
            created_by_unit.setdefault(str(unit_id), []).append(index)
    result: dict[str, dict[str, Any]] = {}
    pending: list[dict[str, Any]] = []
    for parent in retiring:
        evidence = parent.get("metadata_evidence")
        if not isinstance(evidence, dict):
            continue
        for field, raw in evidence.items():
            if not isinstance(raw, dict) or not raw.get("block_ids"):
                continue
            target_indexes: set[int] = set()
            replacement_ids: list[str] = []
            ambiguous = False
            for raw_id in raw.get("block_ids") or []:
                unit_id = str(raw_id)
                unit = by_id.get(unit_id) or {}
                successors = [str(value) for value in unit.get("successor_unit_ids") or []]
                candidates = successors or [unit_id]
                owners = {
                    owner
                    for candidate in candidates
                    for owner in created_by_unit.get(candidate, [])
                }
                if len(owners) != 1:
                    ambiguous = True
                    break
                target_indexes.update(owners)
            if ambiguous or len(target_indexes) != 1:
                pending.append({
                    "field": str(field),
                    "parent_record_id": str(parent.get("record_id") or ""),
                    "block_ids": [str(value) for value in raw.get("block_ids") or []],
                    "reason": "Structural edit changed the evidence topology; reviewer remapping is required.",
                })
                continue
            target_index = next(iter(target_indexes))
            for raw_id in raw.get("block_ids") or []:
                unit_id = str(raw_id)
                unit = by_id.get(unit_id) or {}
                candidates = [str(value) for value in unit.get("successor_unit_ids") or []] or [unit_id]
                replacement_ids.extend(
                    candidate
                    for candidate in candidates
                    if target_index in created_by_unit.get(candidate, [])
                )
            target = dict(raw)
            target["block_ids"] = list(dict.fromkeys(replacement_ids)) or list(
                map(str, raw.get("block_ids") or [])
            )
            target["remapped_from_record_id"] = str(parent.get("record_id") or "")
            target["remapped_at"] = iso_now()
            result.setdefault(str(target_index), {})[str(field)] = target
    return result, pending
