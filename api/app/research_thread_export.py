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

"""Research thread export: questions, answers and audit references.

Citations are MLA 9, built deterministically from each cited Record's recorded
metadata: answers carry MLA in-text citations in place of evidence markers, and
one alphabetical Works Cited covers the thread. Nothing here asks a model. Each turn keeps its run, job and attempt identity, and each cited
EvidenceRef keeps its own marker, collection, Record ID and revision. Passage
text is never exported, so a Researcher export carries no corpus text.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from .corpus_citations import mla_works_cited
from .rag import _annotate_mla, _bind_sources, extract_evidence_ids
from .record_types import EvidenceItem
from .research_thread_store import ThreadNotFound

EXPORT_FORMAT = "derridai-research-thread-export-v2"

_LOCATOR_FIELDS = (
    "printed_page_start", "printed_page_end", "printed_page_label",
    "physical_page_start", "physical_page_end", "page_start", "page_end", "page",
    "start_seconds", "end_seconds",
)


def _reference(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("record") if isinstance(item.get("record"), dict) else {}
    return {
        "evidence_id": item.get("evidence_id"),
        "collection": item.get("collection"),
        "record_id": record.get("record_id"),
        "record_revision": record.get("record_revision"),
        "source_document_id": record.get("source_document_id"),
        "inline_citation": item.get("inline_citation"),
        "full_citation": item.get("full_citation"),
        "mla_citation": item.get("mla_citation") or None,
        "mla_in_text": item.get("mla_in_text") or None,
        "locator": {k: record[k] for k in _LOCATOR_FIELDS if record.get(k) not in (None, "")},
    }


def _turn_export(
    turn: dict[str, Any],
    load_result: Callable[[dict[str, Any]], dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "turn_id": turn["turn_id"], "ordinal": turn["ordinal"], "attempt": turn["attempt"],
        "status": turn["status"], "question": turn["user_question"],
        "instructions": turn.get("user_instructions"),
        "research_run_id": turn.get("research_run_id"), "job_id": turn.get("job_id"),
        "answer": None, "answer_available": False, "provider": None, "model": None,
        "references": [],
    }
    if turn["status"] != "completed":
        return out
    try:
        result = load_result(turn).get("result") or {}
    except (KeyError, ThreadNotFound):
        # A missing artifact stays visible as unavailable rather than invented.
        return out
    evidence = [dict(item) for item in result.get("evidence") or [] if isinstance(item, dict)]
    raw_answer = result.get("raw_answer") or ""
    cited = set(extract_evidence_ids(raw_answer))
    answer = result.get("answer") or None
    if raw_answer and evidence and all(isinstance(item.get("record"), dict) for item in evidence):
        # Cached JSON objects have the EvidenceItem shape but no static type.
        # Keep the original dict list for reference serialization and share the
        # same mutable items with the citation helpers (which annotate in place).
        typed_evidence = cast(list[EvidenceItem], evidence)
        # Recomputed from recorded metadata so runs saved before MLA strings existed match.
        _annotate_mla(typed_evidence, raw_answer)
        # Rebind only when every cited source has an MLA form; otherwise keep the run's
        # own bound answer rather than mixing citation styles.
        if all(item["mla_in_text"] for item in evidence if item["evidence_id"] in cited):
            answer = _bind_sources(raw_answer, typed_evidence, False, citation_map={
                item["evidence_id"]: item["mla_in_text"][1:-1] for item in evidence
            }).strip() or answer
    out.update(
        answer=answer, answer_available=bool(answer),
        provider=result.get("provider"), model=result.get("model"),
        # Without a raw answer the cited subset is unknown, so every bound EvidenceRef is kept.
        references=[_reference(item) for item in evidence if not cited or item.get("evidence_id") in cited],
    )
    records.extend(
        item["record"] for item in evidence
        if isinstance(item.get("record"), dict) and (not cited or item.get("evidence_id") in cited)
    )
    return out


def build_thread_export(thread: dict[str, Any], load_result: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    turns = [_turn_export(turn, load_result, records) for turn in thread.get("turns") or []]
    # One alphabetical MLA Works Cited for the thread; a reference whose Record is
    # unavailable keeps its recorded citation rather than being dropped.
    works = mla_works_cited(records, extra=[
        str(ref.get("full_citation") or "").strip()
        for turn in turns for ref in turn["references"] if not ref.get("mla_citation")
    ])
    return {
        "format": EXPORT_FORMAT,
        "thread": {key: thread.get(key) for key in ("thread_id", "title", "created_at", "updated_at", "archived_at")},
        "turns": turns,
        "works_cited": works,
    }

