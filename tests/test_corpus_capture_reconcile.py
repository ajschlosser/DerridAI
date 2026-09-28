# Copyright 2026 Aaron John Schlosser, PhD.
"""Reconciliation groups provider representations under a work without ever merging them.

Why: an original, its translations, and two translators' versions are different sources
with different evidence. Grouping by a shared title across languages, or collapsing
representations from two libraries, would silently lose editions.
"""
from __future__ import annotations

import pytest
from _capture_support import candidate
from app.source_reconcile import dedupe_exact, main_title, reconcile, summarize

pytestmark = pytest.mark.unit


def _rows(candidates):
    return {c.provider_key: row for c, row in zip(candidates, reconcile(candidates), strict=True)}


def test_the_same_wikidata_work_is_grouped_across_providers():
    items = [
        candidate("1998", "Also sprach Zarathustra", document_languages=["de"], wikidata_work_id="Q156548"),
        candidate("de:Also sprach Zarathustra", "Also sprach Zarathustra", provider="wikisource", document_languages=["de"], wikidata_work_id="Q156548"),
    ]
    rows = _rows(items)
    assert {row["canonical_work_id"] for row in rows.values()} == {"wd:Q156548"}
    assert {row["reconciliation_status"] for row in rows.values()} == {"exact_identity"}
    # Same title and language from two libraries: flagged as possible duplicate representations, not merged.
    assert rows["gutenberg:1998"]["possible_duplicates"] == ["wikisource:de:Also sprach Zarathustra"]


def test_translations_and_different_translators_stay_distinct_members_of_one_work():
    items = [
        candidate("1998", "Also sprach Zarathustra", document_languages=["de"], wikidata_work_id="Q1"),
        candidate("1999", "Thus Spake Zarathustra", document_languages=["en"], wikidata_work_id="Q1", translators=["Thomas Common"], relationship_to_work="translation"),
        candidate("en:Thus Spoke Zarathustra", "Thus Spoke Zarathustra", provider="wikisource", document_languages=["en"], wikidata_work_id="Q1", translators=["Walter Kaufmann"], relationship_to_work="translation"),
    ]
    rows = reconcile(items)
    assert len(rows) == 3
    assert {row["canonical_work_id"] for row in rows} == {"wd:Q1"}
    assert not any(row.get("possible_duplicates") for row in rows)


def test_exact_provider_duplicates_are_the_only_automatic_dedupe():
    items = [candidate("1", "A"), candidate("1", "A"), candidate("1", "A", provider="wikisource"), candidate("2", "A")]
    kept, dropped = dedupe_exact(items)
    assert dropped == 1
    assert [c.provider_key for c in kept] == ["gutenberg:1", "wikisource:1", "gutenberg:2"]


def test_a_matching_title_in_another_language_is_not_grouped():
    items = [
        candidate("1", "Faust", document_languages=["de"]),
        candidate("2", "Faust", document_languages=["en"]),
    ]
    rows = reconcile(items)
    assert rows[0]["canonical_work_id"] != rows[1]["canonical_work_id"]
    assert {row["reconciliation_status"] for row in rows} == {"separate"}


def test_same_title_and_language_without_identity_is_a_reviewable_possible_match():
    items = [
        candidate("1", "Ecce Homo", document_languages=["de"]),
        candidate("de:Ecce homo", "Ecce homo: Wie man wird, was man ist", provider="wikisource", document_languages=["de"]),
    ]
    rows = reconcile(items)
    assert rows[0]["canonical_work_id"] == rows[1]["canonical_work_id"]
    assert {row["reconciliation_status"] for row in rows} == {"possible_match"}


def test_a_title_match_joins_an_identified_group_only_in_the_same_language():
    items = [
        candidate("1", "Ecce Homo", document_languages=["de"], wikidata_work_id="Q2"),
        candidate("de:Ecce Homo", "Ecce Homo", provider="wikisource", document_languages=["de"]),
    ]
    rows = reconcile(items)
    assert rows[1] == {**rows[1], "canonical_work_id": "wd:Q2", "reconciliation_status": "deterministic_match"}


def test_main_title_stops_at_the_subtitle():
    assert main_title("Also sprach Zarathustra: Ein Buch für Alle und Keinen") == "also sprach zarathustra"


def test_summary_counts_review_state_from_stored_rows():
    rows = [
        {"provider": "gutenberg", "canonical_work_id": "wd:Q1", "document_languages": ["de"], "identity_confidence": "exact", "selection_status": "selected", "acquisition_status": "pending", "contribution_role": "author"},
        {"provider": "wikisource", "source_project_language": "en", "canonical_work_id": "wd:Q1", "document_languages": ["en"], "relationship_to_work": "translation", "identity_confidence": "needs_review", "selection_status": "excluded", "acquisition_status": "pending", "possible_duplicates": ["x"], "contribution_role": "author"},
        {"provider": "wikisource", "source_project_language": "en", "canonical_work_id": "title:en:x", "document_languages": [], "reconciliation_status": "possible_match", "identity_confidence": "exact", "selection_status": "excluded", "acquisition_status": "pending", "contribution_role": "unknown"},
    ]
    summary = summarize(rows)
    assert summary["candidates"] == 3
    assert summary["work_groups"] == 2
    assert summary["languages"] == {"de": 1, "en": 1, "und": 1}
    assert summary["projects"] == {"en": 2, "gutenberg": 1}
    assert (summary["translations"], summary["possible_duplicates"], summary["needs_review"], summary["selected"]) == (1, 1, 2, 1)
