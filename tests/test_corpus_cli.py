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

"""Headless corpus CLI configuration and process-contract tests.

These tests exercise the transport-independent YAML contract and the thin CLI
surface without starting FastAPI, a provider, or a corpus build.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.corpus_cli import ExitCode, main
from app.corpus_cli_config import CorpusProcessingConfig, load_processing_config


def test_minimal_yaml_uses_versioned_defaults(tmp_path):
    """A v1 document can be minimal while still resolving deterministic defaults."""
    path = tmp_path / "corpus-processing.yaml"
    path.write_text("version: 1\n", encoding="utf-8")

    config = load_processing_config(path)

    assert config.version == 1
    assert config.publication.profile == "research"
    assert config.processing.segmentation.mode == "semantic"
    assert config.review.mode == "automatic"


def test_unknown_yaml_keys_are_rejected(tmp_path):
    """Misspelled settings fail before source extraction instead of being ignored."""
    path = tmp_path / "corpus-processing.yaml"
    path.write_text("version: 1\nprocessing:\n  profle_id: typo\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_processing_config(path)


def test_provider_secret_is_resolved_from_environment_without_entering_snapshot():
    """API keys may enter the runtime request but never the retained YAML snapshot."""
    config = CorpusProcessingConfig.model_validate(
        {
            "version": 1,
            "provider": {
                "type": "openai",
                "model": "example-model",
                "api_key_env": "DERRIDAI_TEST_KEY",
            },
        }
    )

    request = config.build_request(environ={"DERRIDAI_TEST_KEY": "top-secret"})
    snapshot = config.public_snapshot()

    assert request["api_key"] == "top-secret"
    assert "top-secret" not in json.dumps(snapshot)


def test_missing_configured_provider_secret_is_a_configuration_error():
    """A named credential environment variable must exist before a build starts."""
    config = CorpusProcessingConfig.model_validate(
        {"version": 1, "provider": {"api_key_env": "DERRIDAI_MISSING_KEY"}}
    )

    with pytest.raises(ValueError, match="DERRIDAI_MISSING_KEY"):
        config.build_request(environ={})


def test_build_request_maps_yaml_to_existing_corpus_engine_vocabulary():
    """The CLI adapter uses existing Corpus Builder request names rather than a fork."""
    config = CorpusProcessingConfig.model_validate(
        {
            "version": 1,
            "processing": {
                "segmentation": {
                    "mode": "source_units",
                    "source_units_per_record": 2,
                    "preferred_record_chars": 1200,
                    "record_length_tolerance": 100,
                    "long_record_chars": 2000,
                    "absolute_record_chars": 3000,
                },
                "text": {"clean": True},
            },
            "metadata": {
                "schema_id": "philosophy",
                "guidance": {
                    "position_holder": {
                        "look_for": ["Kant", "Kant"],
                        "instructions": " distinguish attribution ",
                    }
                },
            },
            "provider": {"model": "qwen3:14b", "concurrency": 3},
            "enrichment": {"mode": "deep", "passes": 2},
        }
    )

    request = config.build_request(environ={})

    assert request["topology_policy"] == {
        "mode": "source_units",
        "source_units_per_record": 2,
        "records_per_page": None,
    }
    assert request["record_sizing"]["preferred_record_chars"] == 1200
    assert request["auto_clean_text"] is True
    assert request["schema_id"] == "philosophy"
    assert request["run_guidance"]["position_holder"]["look_for"] == ["Kant"]
    assert request["max_concurrent_requests"] == 3
    assert request["enrichment_mode"] == "deep"
    assert request["autonomous"]["passes"] == 2


def test_cli_validate_can_emit_machine_readable_configuration(tmp_path, capsys):
    """Config validation is already usable from the eventual compiled entry point."""
    path = tmp_path / "corpus-processing.yaml"
    path.write_text("version: 1\npublication:\n  profile: celf\n", encoding="utf-8")

    code = main(["config", "validate", "--config", str(path), "--json"])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    payload = json.loads(captured.out)
    assert payload["version"] == 1
    assert payload["publication"]["profile"] == "celf"
    assert captured.err == ""


def test_cli_validate_returns_stable_config_error_code(tmp_path, capsys):
    """Invalid YAML/configuration uses the documented configuration exit category."""
    path = tmp_path / "bad.yaml"
    path.write_text("version: 99\n", encoding="utf-8")

    code = main(["config", "validate", "--config", str(path)])
    captured = capsys.readouterr()

    assert code == ExitCode.USAGE_OR_CONFIG
    assert "Configuration error:" in captured.err
