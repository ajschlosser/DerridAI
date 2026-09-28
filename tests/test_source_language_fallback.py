# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic and model-assisted source-language fallback behavior."""

from __future__ import annotations

import json

import pytest
from app import llm_tools
from app.models import PdfAssetLanguagePatch, PdfLlmRequest
from app.source_identity import CaptureError, CaptureOptions, ResolvedAuthor
from app.source_text import infer_initial_metadata
from pydantic import ValidationError


def test_ambiguous_source_language_remains_explicitly_unresolved():
    metadata = infer_initial_metadata("12345 !!!", blocks=[{"text": "12345 !!!"}])

    assert metadata["language_status"] == "unresolved"
    assert metadata["field_provenance"]["language"]["status"] == "unresolved"
    assert "language" not in metadata


def test_language_decision_requires_one_explicit_outcome():
    assert PdfAssetLanguagePatch(language="FR_ca").language == "fr-ca"
    assert PdfAssetLanguagePatch(skip_language=True).skip_language is True

    with pytest.raises(ValidationError):
        PdfAssetLanguagePatch()
    with pytest.raises(ValidationError):
        PdfAssetLanguagePatch(language="fr", skip_language=True)


def test_language_detector_validates_and_normalizes_model_output(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "chat_complete",
        lambda **_: json.dumps({"language": "FR_ca", "confidence": 0.91, "reason": "French function words"}),
    )

    result = llm_tools.run_pdf_llm(
        PdfLlmRequest(mode="detect_language", raw_text="Bonjour, le monde.", provider="ollama")
    )

    assert result["language"] == "fr-ca"
    assert result["confidence"] == 0.91
    assert result["reason"] == "French function words"


def test_language_detector_rejects_invalid_model_code(monkeypatch):
    monkeypatch.setattr(
        llm_tools,
        "chat_complete",
        lambda **_: json.dumps({"language": "not a language", "confidence": 1}),
    )

    with pytest.raises(ValueError, match="invalid language code"):
        llm_tools.run_pdf_llm(
            PdfLlmRequest(mode="detect_language", raw_text="Bonjour.", provider="ollama")
        )


def _author(**kwargs) -> ResolvedAuthor:
    return ResolvedAuthor(identity_id="wikidata:Q1", canonical_name="Author", **kwargs)


def test_capture_language_does_not_use_spoken_language_as_original_default():
    options = CaptureOptions(include_translations=False, languages=None)

    with pytest.raises(CaptureError, match="exactly one original language"):
        options.validate_for_author(_author(languages=["en", "fr"]))


def test_capture_language_accepts_one_explicit_language_without_known_original():
    options = CaptureOptions(include_translations=False, languages=["fr"])

    options.validate_for_author(_author(languages=["en"]))

    assert options.languages == ["fr"]


def test_capture_language_defaults_only_from_one_authoritative_original_language():
    options = CaptureOptions(include_translations=False, languages=None)

    options.validate_for_author(
        _author(languages=["en", "fr"], original_languages=["de"])
    )

    assert options.languages == ["de"]


def test_audio_spans_use_time_locators_without_page_semantics():
    from app.source_audio import spans_from_transcript

    blocks = spans_from_transcript(
        {
            "text": "Hello world.",
            "segments": [{"start": 0, "end": 1.2, "text": "Hello world."}],
        },
        [],
    )
    assert blocks[0]["locator_kind"] == "time"
    assert "page" not in blocks[0]
