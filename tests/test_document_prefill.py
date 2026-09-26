# Copyright 2026 Aaron John Schlosser, PhD.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import document_prefill as dp  # noqa: E402

TITLE_PAGE = """OF GRAMMATOLOGY

Jacques Derrida

Translated by Gayatri Chakravorty Spivak

The Johns Hopkins University Press
Baltimore and London

First published 1967. Copyright © 1976, 1997 by The Johns Hopkins University Press.
ISBN 0-8018-5830-5
"""


def by_field(candidates):
    out = {}
    for c in candidates:
        out.setdefault(c.field, []).append(c)
    return out


def test_computed_fields_come_from_exact_patterns_with_spans():
    found = by_field(dp.computed_candidates(TITLE_PAGE))
    assert found["isbn"][0].value == "0801858305" and found["isbn"][0].derivation == "computed"
    assert TITLE_PAGE[slice(*found["isbn"][0].span)].replace("-", "") == "0801858305"
    assert found["translator"][0].value == "Gayatri Chakravorty Spivak"
    # The earliest year wins; a later reprint year is kept only as a low-confidence alternative.
    years = sorted(found["publication_year"], key=lambda c: -c.confidence)
    assert years[0].value == "1967" and years[0].confidence > 0.85
    assert {c.value for c in years[1:]} == {"1976", "1997"} and all(c.confidence < 0.6 for c in years[1:])


def test_an_isbn_with_a_bad_check_digit_is_ignored():
    assert not [c for c in dp.computed_candidates("ISBN 0-8018-5830-4") if c.field == "isbn"]


def test_published_by_notice_gives_publisher_and_place():
    found = by_field(dp.computed_candidates("Published by Gallimard, Paris. Tous droits réservés."))
    assert found["publisher"][0].value == "Gallimard" and found["publication_place"][0].value == "Paris"


def test_language_guess():
    assert dp.guess_language("the cat and the dog went to the market with a friend of the family " * 5) == "en"
    assert dp.guess_language("le chat et la souris sont dans la maison pour les enfants de la ville " * 5) == "fr"
    assert dp.guess_language("short") == ""


def test_nlp_places_the_place_of_publication_beside_the_publisher():
    spacy = pytest.importorskip("spacy")
    try:
        spacy.load("en_core_web_lg", exclude=["parser", "lemmatizer"])
    except Exception:
        pytest.skip("English model not installed")
    found = by_field(dp.nlp_candidates(TITLE_PAGE, "English"))
    publisher = found["publisher"][0]
    assert "Press" in publisher.value and publisher.derivation == "nlp_derived"
    assert publisher.method.startswith("nlp:spacy:") and publisher.confidence < 0.8
    assert found["publication_place"][0].value == "Baltimore"


def test_extract_is_safe_when_models_are_missing(monkeypatch):
    from app import nlp_annotations

    monkeypatch.setattr(nlp_annotations, "load_pipeline", lambda language: None)
    found = dp.extract(TITLE_PAGE, language="English")
    assert {c.field for c in found} >= {"isbn", "translator", "publication_year"}


def test_ingest_prefills_the_work_metadata_with_labelled_provenance(tmp_path, monkeypatch):
    from app import corpus_builder as cb
    from app import nlp_annotations
    from app.source_text import apply_deterministic_ingest_metadata

    monkeypatch.setattr(nlp_annotations, "load_pipeline", lambda language: None)  # patterns only: model-independent
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    body = "\n\n".join([TITLE_PAGE] + ["A long paragraph of philosophy. " * 20] * 4)
    asset = repo.save_asset(body.encode(), filename="grammatology.txt")
    initial = asset["initial_metadata"]
    assert initial["isbn"] == "0801858305" and initial["publication_year"] == "1967"
    provenance = initial["field_provenance"]
    assert provenance["isbn"]["derivation"] == "computed" and provenance["isbn"]["span"]
    assert {alt["value"] for alt in provenance["publication_year"]["alternatives"]} == {"1976", "1997"}
    manifest = apply_deterministic_ingest_metadata({}, asset)
    assert manifest["isbn"] == "0801858305" and manifest["translator"] == "Gayatri Chakravorty Spivak"
    applied = manifest["deterministic_ingest"]["applied"]
    assert applied["publication_year"]["derivation"] == "computed"
    assert applied["publication_year"]["alternatives"]


def test_inherited_values_keep_their_origin_until_a_reviewer_changes_them():
    from app.corpus_segmentation import _apply_manifest_metadata
    from app.field_assertions import current_assertion_by_name

    manifest = {
        "title": "Of Grammatology", "publisher": "The Johns Hopkins University Press", "publication_place": "Baltimore",
        "deterministic_ingest": {"applied": {
            "publication_place": {"value": "Baltimore", "method": "nlp:spacy:en_core_web_lg:place_near_publisher", "confidence": 0.7, "derivation": "nlp_derived"},
            "publisher": {"value": "Johns Hopkins University Press", "method": "nlp:spacy:x", "confidence": 0.72, "derivation": "nlp_derived"},
        }},
    }
    record = {"record_id": "r1", "source_document_id": "d", "text": "t", "source_spans": []}
    _apply_manifest_metadata(record, manifest)
    place = current_assertion_by_name(record, "publication_place")
    assert "Origin: NLP-derived" in place.reason and "70% confidence" in place.reason
    # The reviewer edited the publisher, so it no longer claims an automatic origin.
    assert "Origin" not in current_assertion_by_name(record, "publisher").reason
