# Copyright 2026 Aaron John Schlosser, PhD.
"""Helpers for advisory, per-build metadata guidance.

Run guidance never changes the metadata schema. Exact phrase matches are cues
for the model and reviewer, not assertions that the matched field applies.
"""

from __future__ import annotations

import re
from typing import Any


def find_guidance_matches(
    text: str, guidance: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Return bounded, case-insensitive whole-phrase hits for user-supplied terms."""
    matches: dict[str, list[dict[str, Any]]] = {}
    source = str(text or "")
    for field, raw in guidance.items():
        if not isinstance(raw, dict):
            continue
        field_hits: list[dict[str, Any]] = []
        for term in raw.get("look_for") or []:
            phrase = str(term or "").strip()
            if not phrase:
                continue
            pattern = re.compile(
                r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                re.IGNORECASE | re.UNICODE,
            )
            count = sum(1 for _ in pattern.finditer(source))
            if count:
                field_hits.append({"term": phrase, "occurrences": count})
        if field_hits:
            matches[str(field)] = field_hits
    return matches


def format_group_guidance(
    group_fields: list[str],
    guidance: dict[str, Any],
    matches: dict[str, list[dict[str, Any]]],
) -> str:
    """Format only this schema group's run guidance for its LLM task."""
    sections: list[str] = []
    for field in group_fields:
        raw = guidance.get(field)
        if not isinstance(raw, dict):
            continue
        instructions = str(raw.get("instructions") or "").strip()
        terms = [str(value).strip() for value in raw.get("look_for") or [] if str(value).strip()]
        hits = matches.get(field) or []
        if not instructions and not terms:
            continue
        details = [f"Field `{field}`:"]
        if instructions:
            details.append(f"User guidance: {instructions}")
        if terms:
            details.append(
                "Values or phrases to look for (not a closed list): " + ", ".join(terms)
            )
        if hits:
            details.append(
                "Exact phrase matches in this record: "
                + ", ".join(f"{item['term']} ({item['occurrences']} occurrence(s))" for item in hits)
            )
        sections.append("\n".join(details))
    if not sections:
        return ""
    return (
        "RUN-SPECIFIC FIELD GUIDANCE (advisory; it does not change the schema or make a value mandatory).\n"
        "Use these cues to inspect the current record. A phrase match is not proof that the field applies: "
        "return a value only when this record's context supports it, and cite source evidence when "
        "the schema requires it. The listed values are examples or search cues, not an exhaustive "
        "allowed-value list.\n"
        + "\n".join(sections)
    )
