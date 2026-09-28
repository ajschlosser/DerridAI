# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic and model-assisted source-language fallback behavior."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app import llm_tools
from app.models import PdfAssetLanguagePatch, PdfLlmRequest
from app.source_text import infer_initial_metadata


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
