# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD

from __future__ import annotations

from app.research_semantics import (
    QUOTED_AUTHOR_ID,
    SOURCE_AUTHOR_ID,
    rerank_attribution_context,
    semantic_value,
    source_author,
)


def _assertion(record_id: str, assertion_id: str, field_id: str, field_name: str, value: str):
    return {
        "assertion_id": assertion_id,
        "record_id": record_id,
        "field_id": field_id,
        "field_name": field_name,
        "value": value,
        "derivation_method": "human",
        "evaluation_status": "value_supported",
        "authority_status": "human_confirmed",
        "value_status": "present",
    }


def test_research_semantics_resolve_custom_field_names_by_stable_identity() -> None:
    record = {
        "record_id": "r1",
        "document_author": "Legacy Wrong Author",
        "quoted_author": "Legacy Wrong Quoted Author",
        "field_assertions": {
            SOURCE_AUTHOR_ID: [
                _assertion("r1", "a-source", SOURCE_AUTHOR_ID, "creator_name", "Source Author")
            ],
            QUOTED_AUTHOR_ID: [
                _assertion("r1", "a-quoted", QUOTED_AUTHOR_ID, "cited_thinker", "Quoted Author")
            ],
        },
        "current_field_assertions": {
            SOURCE_AUTHOR_ID: "a-source",
            QUOTED_AUTHOR_ID: "a-quoted",
        },
    }

    assert source_author(record) == "Source Author"
    assert semantic_value(record, QUOTED_AUTHOR_ID) == "Quoted Author"
    context = rerank_attribution_context(record, "Passage text")
    assert "Source document author: Source Author" in context
    assert "Quoted author: Quoted Author" in context
    assert "Legacy Wrong" not in context


def test_research_semantics_fall_back_to_registered_legacy_projection() -> None:
    record = {"document_author": "Compatibility Author"}
    assert source_author(record) == "Compatibility Author"
