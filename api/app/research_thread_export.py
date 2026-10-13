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

Citations are the run's own deterministic ``inline_citation``/``full_citation``
strings recorded at retrieval time; nothing here asks a model or reformats a
citation. Each turn keeps its run, job and attempt identity, and each cited
EvidenceRef keeps its own marker, collection, Record ID and revision. Passage
text is never exported, so a Researcher export carries no corpus text.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .rag import extract_evidence_ids
from .research_thread_store import ThreadNotFound

EXPORT_FORMAT = "derridai-research-thread-export-v1"

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
        "locator": {k: record[k] for k in _LOCATOR_FIELDS if record.get(k) not in (None, "")},
    }


def _turn_export(turn: dict[str, Any], load_result: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
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
    evidence = [item for item in result.get("evidence") or [] if isinstance(item, dict)]
    cited = set(extract_evidence_ids(result.get("raw_answer") or ""))
    out.update(
        answer=result.get("answer") or None, answer_available=bool(result.get("answer")),
        provider=result.get("provider"), model=result.get("model"),
        # Without a raw answer the cited subset is unknown, so every bound EvidenceRef is kept.
        references=[_reference(item) for item in evidence if not cited or item.get("evidence_id") in cited],
    )
    return out


def build_thread_export(thread: dict[str, Any], load_result: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    turns = [_turn_export(turn, load_result) for turn in thread.get("turns") or []]
    works: list[str] = []
    for turn in turns:
        for ref in turn["references"]:
            citation = str(ref.get("full_citation") or "").strip()
            if citation and citation not in works:
                works.append(citation)
    return {
        "format": EXPORT_FORMAT,
        "thread": {key: thread.get(key) for key in ("thread_id", "title", "created_at", "updated_at", "archived_at")},
        "turns": turns,
        "works_cited": works,
    }

