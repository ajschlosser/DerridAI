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
from app.corpus_cli import ExitCode, main
from app.corpus_cli_config import CorpusProcessingConfig, load_processing_config
from app.corpus_run_config import (
    HEADLESS_CORPUS_PIPELINE_FEATURES,
    CorpusRunConfigV2,
    dump_run_config,
    load_run_config,
    migrate_v1_config,
)
from app.pipelines.execution_resolution import (
    RUN_PIPELINE_BINDINGS_KEY,
    resolve_execution_pipeline,
)
from pydantic import ValidationError


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


def test_v1_config_migrates_to_pipeline_bound_v2_envelope(tmp_path):
    config = CorpusProcessingConfig.model_validate(
        {
            "version": 1,
            "provider": {"model": "qwen3:14b"},
            "publication": {"profile": "celf"},
        }
    )

    migrated = migrate_v1_config(config)

    assert migrated.format == "derridai-corpus-run"
    assert migrated.version == 2
    assert migrated.provider.model == "qwen3:14b"
    assert migrated.publication.profile == "celf"
    assert set(migrated.pipelines.assignments) == set(
        HEADLESS_CORPUS_PIPELINE_FEATURES
    )
    for binding in migrated.pipelines.assignments.values():
        assert len(binding.pipeline_hash) == 64
        assert binding.required_strategies
        assert set(binding.required_strategies) == {
            stage.strategy for stage in binding.definition.stages
        }

    path = tmp_path / "corpus-run.yaml"
    path.write_text(dump_run_config(migrated), encoding="utf-8")
    loaded = load_run_config(path)
    assert isinstance(loaded, CorpusRunConfigV2)
    assert loaded.public_snapshot() == migrated.public_snapshot()


def test_v2_config_rejects_tampered_pipeline_hash():
    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    payload = migrated.public_snapshot()
    feature = HEADLESS_CORPUS_PIPELINE_FEATURES[0]
    payload["pipelines"]["assignments"][feature]["pipeline_hash"] = "0" * 64

    with pytest.raises(ValidationError, match="Pipeline hash mismatch"):
        CorpusRunConfigV2.model_validate(payload)


def test_cli_migrate_emits_v2_yaml(tmp_path, capsys):
    source = tmp_path / "legacy.yaml"
    source.write_text("version: 1\nprovider:\n  model: qwen3:14b\n", encoding="utf-8")

    code = main(["config", "migrate", "--config", str(source)])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    migrated_path = tmp_path / "migrated.yaml"
    migrated_path.write_text(captured.out, encoding="utf-8")
    migrated = load_run_config(migrated_path)
    assert isinstance(migrated, CorpusRunConfigV2)
    assert migrated.provider.model == "qwen3:14b"


def test_cli_pipeline_capabilities_reports_contract_identity(capsys):
    code = main(["pipeline", "capabilities", "--json"])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    payload = json.loads(captured.out)
    assert payload["pipeline_contract_version"] >= 1
    assert payload["application_version"]
    assert "llm.structured_metadata" in payload["strategies"]


def test_cli_doctor_reports_required_headless_pipeline_bindings(capsys):
    code = main(["doctor", "--json"])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    payload = json.loads(captured.out)
    assert payload["status"] == "ok"
    assert payload["missing_features"] == []
    assert set(payload["headless_corpus_pipelines"]) == set(
        HEADLESS_CORPUS_PIPELINE_FEATURES
    )



def test_v2_config_requires_every_headless_pipeline_binding():
    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    payload = migrated.public_snapshot()
    payload["pipelines"]["assignments"].pop("corpus_segmentation")

    with pytest.raises(ValidationError, match="missing required Corpus Builder pipeline"):
        CorpusRunConfigV2.model_validate(payload)


def test_v2_config_rejects_unknown_embedded_pipeline_fields():
    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    payload = migrated.public_snapshot()
    feature = HEADLESS_CORPUS_PIPELINE_FEATURES[0]
    payload["pipelines"]["assignments"][feature]["definition"]["surprise"] = True

    with pytest.raises(ValidationError, match="unknown field"):
        CorpusRunConfigV2.model_validate(payload)


def test_v2_config_rejects_strategy_version_drift():
    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    payload = migrated.public_snapshot()
    feature = "corpus_metadata_enrichment"
    requirements = payload["pipelines"]["assignments"][feature]["required_strategies"]
    strategy_id = next(iter(requirements))
    requirements[strategy_id] += 1

    with pytest.raises(ValidationError, match="provides v"):
        CorpusRunConfigV2.model_validate(payload)



def test_frozen_run_binding_executes_without_consulting_active_assignment(monkeypatch):
    import app.pipelines.manager as manager_module

    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    request = {
        RUN_PIPELINE_BINDINGS_KEY: migrated.execution_pipeline_bindings(),
    }

    def unexpected_resolve(_feature):
        raise AssertionError("active assignment must not be consulted")

    monkeypatch.setattr(manager_module.pipeline_manager, "resolve", unexpected_resolve)
    resolved = resolve_execution_pipeline("corpus_metadata_enrichment", request)

    binding = migrated.pipelines.assignments["corpus_metadata_enrichment"]
    assert resolved["pipeline"]["pipeline_id"] == binding.definition.pipeline_id
    assert resolved["pipeline_hash"] == binding.pipeline_hash
    assert resolved["source"] == "run_envelope"


def test_frozen_run_binding_applies_typed_overrides():
    migrated = migrate_v1_config(CorpusProcessingConfig.model_validate({"version": 1}))
    payload = migrated.public_snapshot()
    binding = payload["pipelines"]["assignments"]["corpus_metadata_enrichment"]
    definition = binding["definition"]
    binding["overrides"] = {
        "pipeline_id": definition["pipeline_id"],
        "pipeline_version": definition["version"],
        "stages": {"primary": {"attempts": 2}},
    }
    config = CorpusRunConfigV2.model_validate(payload)

    resolved = resolve_execution_pipeline(
        "corpus_metadata_enrichment",
        {RUN_PIPELINE_BINDINGS_KEY: config.execution_pipeline_bindings()},
    )

    primary = next(
        stage for stage in resolved["pipeline"]["stages"] if stage["id"] == "primary"
    )
    assert primary["config"]["attempts"] == 2
    assert resolved["pipeline_hash"] != binding["pipeline_hash"]
    assert resolved["config_resolution"]["run_overrides"]["stages"]["primary"] == {
        "attempts": 2
    }
