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

from __future__ import annotations

import hashlib
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


def test_book_character_data_normalizes_supported_booknlp_fixture(tmp_path):
    """Normalize the provider shape DerridAI consumes; do not re-test BookNLP semantics."""
    worker = _worker_module()
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "booknlp"
        / "1.0.8"
        / "character-normalization.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    text = fixture["text"]
    rows = fixture["tokens"]
    path = tmp_path / "document.book"
    path.write_text(json.dumps(fixture["book"]), encoding="utf-8")
    boundaries, lookup = worker._utf8_map(text)

    characters = worker._book_character_data(path, rows, text, boundaries, lookup)

    assert len(characters) == 1
    character = characters[0]
    expected = fixture["expected"]
    assert character["cluster_id"] == expected["cluster_id"]
    assert character["aliases"] == expected["aliases"]
    assert character["actions_as_agent"][0]["lemma"] == expected["agent_lemma"]
    assert character["actions_as_agent"][0]["start_char"] == expected["agent_start_char"]
    assert character["possessions"][0]["text"] == expected["possession_text"]
    for key in expected["excludes"]:
        assert key not in character

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

    entity_digest = hashlib.sha256(artifacts["BOOKNLP_ENTITY_MODEL"].read_bytes()).hexdigest()
    monkeypatch.setenv("BOOKNLP_ENTITY_SHA256", entity_digest)
    monkeypatch.setenv("BOOKNLP_COREF_SHA256", "0" * 64)
    monkeypatch.delenv("BOOKNLP_QUOTE_SHA256", raising=False)

    manifest = {item["role"]: item for item in worker._artifact_manifest()}
    assert manifest["entity_model_path"]["verified"] is True
    assert manifest["coref_model_path"]["verified"] is False
    assert manifest["quote_attribution_model_path"]["expected_sha256"] is None
    assert worker._digest_mismatches() == ["coref_model_path"]


def test_worker_loads_the_installed_language_pack_and_its_pinned_digests(monkeypatch, tmp_path):
    for name in ("ENTITY", "COREF", "QUOTE"):
        monkeypatch.delenv(f"BOOKNLP_{name}_MODEL", raising=False)
        monkeypatch.delenv(f"BOOKNLP_{name}_SHA256", raising=False)
    monkeypatch.setenv("BOOKNLP_MODELS_DIR", str(tmp_path))
    pack = tmp_path / "en" / "booknlp-en-small"
    pack.mkdir(parents=True)
    digests = {}
    for role in ("entity", "coref", "quote"):
        (pack / f"{role}.model").write_bytes(role.encode())
        digests[role] = hashlib.sha256(role.encode()).hexdigest()
    digests["quote"] = "0" * 64  # the worker re-verifies rather than trusting the manifest
    (tmp_path / "en" / "active.json").write_text(json.dumps({
        "pack_id": "booknlp-en-small", "language": "en", "engine": "booknlp",
        "files": {role: f"booknlp-en-small/{role}.model" for role in ("entity", "coref", "quote")},
        "sha256": digests,
    }))
    worker = _worker_module()

    assert worker._missing_models() == []
    assert worker._paths()["coref_model_path"] == str((pack / "coref.model").resolve())
    assert worker._digest_mismatches() == ["quote_attribution_model_path"]


def test_worker_ignores_pack_paths_that_escape_the_models_directory(monkeypatch, tmp_path):
    for name in ("ENTITY", "COREF", "QUOTE"):
        monkeypatch.delenv(f"BOOKNLP_{name}_MODEL", raising=False)
    monkeypatch.setenv("BOOKNLP_MODELS_DIR", str(tmp_path / "models"))
    (tmp_path / "secret.model").write_bytes(b"x")
    (tmp_path / "models" / "en").mkdir(parents=True)
    (tmp_path / "models" / "en" / "active.json").write_text(json.dumps({
        "engine": "booknlp", "files": {"entity": "../../secret.model"}, "sha256": {},
    }))
    assert _worker_module()._paths()["entity_model_path"] == ""
