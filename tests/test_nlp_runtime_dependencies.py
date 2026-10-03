# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026 Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Container NLP dependencies stay minimal; additional languages are managed packs."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NLP_REQUIREMENTS = ROOT / "api" / "requirements-nlp.txt"


def test_container_bundles_only_small_english_and_french_spacy_models():
    lines = NLP_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    model_lines = [
        line.strip()
        for line in lines
        if "github.com/explosion/spacy-models/releases/download/" in line
    ]

    assert len(model_lines) == 2
    assert model_lines[0].startswith("en_core_web_sm @ ")
    assert "en_core_web_sm-3.8.0" in model_lines[0]
    assert model_lines[1].startswith("fr_core_news_sm @ ")
    assert "fr_core_news_sm-3.8.0" in model_lines[1]
    assert all("_lg" not in line for line in model_lines)
    assert all("de_core_news_" not in line for line in model_lines)
