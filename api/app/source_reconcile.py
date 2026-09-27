# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure, deterministic reconciliation of provider candidates into work groups.

Grouping is never merging: every candidate keeps its own identity, selection, and
acquisition state. The order of evidence is

1. exact external identity (a Wikidata work id)                  → ``exact_identity``
2. explicit provider relationship (edition-of on the provider)   → ``provider_relationship``
3. strong bibliographic match (same main title *and* language as
   a candidate already grouped by identity)                      → ``deterministic_match``
4. same main title and language without any identity            → grouped, ``possible_match`` (review)
5. otherwise                                                     → its own group, ``separate``

A shared title alone never groups representations in different languages, and
titles are compared in O(n) through dictionary keys, not pairwise.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .source_identity import SourceCandidate, fold


def main_title(title: str) -> str:
    """Folded title up to the first subtitle separator ("Also sprach Zarathustra: Ein Buch…" → "also sprach zarathustra")."""
    head = re.split(r"[:;.\n—]| - ", str(title or ""), maxsplit=1)[0]
    return fold(head)


def dedupe_exact(candidates: list[SourceCandidate]) -> tuple[list[SourceCandidate], int]:
    """Drop repeated (provider, provider item id) pairs — the only automatic de-duplication."""
    seen: set[str] = set()
    kept: list[SourceCandidate] = []
    for candidate in candidates:
        if candidate.provider_key in seen:
            continue
        seen.add(candidate.provider_key)
        kept.append(candidate)
    return kept, len(candidates) - len(kept)


def _lang_key(candidate: SourceCandidate) -> str:
    return "+".join(sorted(candidate.document_languages)) or "und"


def reconcile(candidates: list[SourceCandidate]) -> list[dict[str, Any]]:
    """One reconciliation row per candidate, in input order: work id, status, possible duplicates."""
    rows: list[dict[str, Any]] = [{} for _ in candidates]
    title_index: dict[tuple[str, str], str] = {}
    for index, candidate in enumerate(candidates):
        if candidate.wikidata_work_id:
            work = f"wd:{candidate.wikidata_work_id}"
            rows[index] = {"canonical_work_id": work, "reconciliation_status": "exact_identity"}
            title_index.setdefault((main_title(candidate.title), _lang_key(candidate)), work)
    unresolved: dict[tuple[str, str], list[int]] = {}
    for index, candidate in enumerate(candidates):
        if rows[index]:
            continue
        key = (main_title(candidate.title), _lang_key(candidate))
        if key[0] and key in title_index:
            rows[index] = {"canonical_work_id": title_index[key], "reconciliation_status": "deterministic_match"}
        elif key[0]:
            unresolved.setdefault(key, []).append(index)
        else:
            rows[index] = {"canonical_work_id": f"cand:{candidate.provider_key}", "reconciliation_status": "separate"}
    for (title, lang), indexes in unresolved.items():
        if len(indexes) == 1:
            only = candidates[indexes[0]]
            rows[indexes[0]] = {"canonical_work_id": f"cand:{only.provider_key}", "reconciliation_status": "separate"}
            continue
        group = f"title:{lang}:{title}"
        for index in indexes:
            rows[index] = {"canonical_work_id": group, "reconciliation_status": "possible_match"}
    # Possible duplicate representations: same full title and language from different providers.
    by_full: dict[tuple[str, str], list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_full.setdefault((fold(candidate.title), _lang_key(candidate)), []).append(index)
    for indexes in by_full.values():
        providers = {candidates[i].provider for i in indexes}
        if len(indexes) > 1 and len(providers) > 1:
            for index in indexes:
                rows[index]["possible_duplicates"] = [candidates[i].provider_key for i in indexes if i != index]
    return rows


def summarize(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts for the review manifest, computed from stored candidate rows."""
    languages: Counter[str] = Counter()
    for row in candidates:
        for code in row.get("document_languages") or ["und"]:
            languages[code] += 1
    return {
        "candidates": len(candidates),
        "work_groups": len({row.get("canonical_work_id") for row in candidates}),
        "languages": dict(languages.most_common()),
        "providers": dict(Counter(str(row.get("provider")) for row in candidates).most_common()),
        "projects": dict(Counter(str(row.get("source_project_language") or row.get("provider")) for row in candidates).most_common()),
        "roles": dict(Counter(str(row.get("contribution_role")) for row in candidates).most_common()),
        "translations": sum(1 for row in candidates if row.get("relationship_to_work") == "translation"),
        "possible_duplicates": sum(1 for row in candidates if row.get("possible_duplicates")),
        "needs_review": sum(1 for row in candidates if row.get("identity_confidence") != "exact" or row.get("reconciliation_status") == "possible_match"),
        "selected": sum(1 for row in candidates if row.get("selection_status") == "selected"),
        "acquisition": dict(Counter(str(row.get("acquisition_status")) for row in candidates).most_common()),
    }
