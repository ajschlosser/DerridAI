# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def _worker_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "booknlp-worker" / "app.py"
    spec = importlib.util.spec_from_file_location("derridai_booknlp_worker_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_booknlp_offsets_use_character_positions_before_utf8_fallback():
    worker = _worker_module()
    text = "Élise parle."
    rows = [
        {
            "token_ID_within_document": "0",
            "word": "Élise",
            "lemma": "Élise",
            # BookNLP 1.0.8 calls these byte offsets but writes spaCy character offsets.
            "byte_onset": "0",
            "byte_offset": "5",
            "event": "O",
        }
    ]
    boundaries, lookup = worker._utf8_map(text)
    start, end = worker._token_span(rows, 0, 0, text, boundaries, lookup, "Élise")
    assert (start, end) == (0, 5)
    assert text[start:end] == "Élise"


def test_book_character_data_matches_booknlp_book_schema(tmp_path):
    worker = _worker_module()
    text = "Elizabeth walked home."
    rows = [
        {
            "token_ID_within_document": "0",
            "word": "Elizabeth",
            "lemma": "Elizabeth",
            "byte_onset": "0",
            "byte_offset": "9",
            "event": "O",
        },
        {
            "token_ID_within_document": "1",
            "word": "walked",
            "lemma": "walk",
            "byte_onset": "10",
            "byte_offset": "16",
            "event": "EVENT",
        },
        {
            "token_ID_within_document": "2",
            "word": "home",
            "lemma": "home",
            "byte_onset": "17",
            "byte_offset": "21",
            "event": "O",
        },
    ]
    book = {
        "characters": [
            {
                "id": 7,
                "count": 4,
                "mentions": {
                    "proper": [{"c": 2, "n": "Elizabeth"}],
                    "common": [{"c": 1, "n": "the woman"}],
                    "pronoun": [{"c": 1, "n": "she"}],
                },
                "agent": [{"w": "walked", "i": 1}],
                "patient": [],
                "poss": [{"w": "home", "i": 2}],
                "mod": [],
                "g": {"she/her": 0.99},
            }
        ]
    }
    path = tmp_path / "document.book"
    path.write_text(json.dumps(book), encoding="utf-8")
    boundaries, lookup = worker._utf8_map(text)

    characters = worker._book_character_data(path, rows, text, boundaries, lookup)

    assert len(characters) == 1
    character = characters[0]
    assert character["cluster_id"] == "7"
    assert character["aliases"] == ["Elizabeth", "the woman", "she"]
    assert character["mention_count"] == 4
    assert character["mentions"]["proper"] == [{"text": "Elizabeth", "count": 2}]
    assert character["actions_as_agent"][0]["lemma"] == "walk"
    assert character["actions_as_agent"][0]["start_char"] == 10
    assert character["possessions"][0]["text"] == "home"
    # Referential gender is intentionally not normalized into a character fact.
    assert "g" not in character


def test_event_pipeline_does_not_require_a_separate_event_model(monkeypatch, tmp_path):
    worker = _worker_module()
    paths = {}
    for env_name in ("BOOKNLP_ENTITY_MODEL", "BOOKNLP_COREF_MODEL", "BOOKNLP_QUOTE_MODEL"):
        artifact = tmp_path / f"{env_name.lower()}.model"
        artifact.write_bytes(b"approved")
        monkeypatch.setenv(env_name, str(artifact))
        paths[env_name] = artifact
    monkeypatch.delenv("BOOKNLP_EVENT_MODEL", raising=False)

    assert worker._missing_models(include_events=True) == []
    assert set(worker._paths(include_events=True)) == {
        "entity_model_path",
        "coref_model_path",
        "quote_attribution_model_path",
    }


def test_booknlp_model_digest_mismatch_is_reported(monkeypatch, tmp_path):
    worker = _worker_module()
    artifacts = {}
    for env_name in ("BOOKNLP_ENTITY_MODEL", "BOOKNLP_COREF_MODEL", "BOOKNLP_QUOTE_MODEL"):
        artifact = tmp_path / f"{env_name.lower()}.model"
        artifact.write_bytes(env_name.encode("utf-8"))
        monkeypatch.setenv(env_name, str(artifact))
        artifacts[env_name] = artifact

    import hashlib

    entity_digest = hashlib.sha256(artifacts["BOOKNLP_ENTITY_MODEL"].read_bytes()).hexdigest()
    monkeypatch.setenv("BOOKNLP_ENTITY_SHA256", entity_digest)
    monkeypatch.setenv("BOOKNLP_COREF_SHA256", "0" * 64)
    monkeypatch.delenv("BOOKNLP_QUOTE_SHA256", raising=False)

    manifest = {item["role"]: item for item in worker._artifact_manifest()}
    assert manifest["entity_model_path"]["verified"] is True
    assert manifest["coref_model_path"]["verified"] is False
    assert manifest["quote_attribution_model_path"]["expected_sha256"] is None
    assert worker._digest_mismatches() == ["coref_model_path"]
