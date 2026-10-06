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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Version-2 corpus-run configuration and migration contract tests."""

from __future__ import annotations

import copy

import pytest
import yaml
from app.corpus_cli import ExitCode, main
from app.corpus_cli_config import (
    CorpusProcessingConfig,
    load_processing_config,
)
from app.corpus_run_config import (
    CorpusRunEnvelopeV2,
    migrate_v1_to_v2,
)
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import PipelineConfigOverrideSet, PipelineDefinition
from app.pipelines.service import PipelineService, pipeline_hash
from pydantic import ValidationError


def _metadata_pipeline() -> PipelineDefinition:
    pipeline = built_in_pipeline("corpus.metadata_enrichment.current", 2)
    assert pipeline is not None
    return pipeline


class _PipelineManager:
    def __init__(self, pipeline: PipelineDefinition) -> None:
        self.pipeline = pipeline
        self.service = PipelineService()

    def get_definition(self, pipeline_id: str, version: int | None = None):
        if pipeline_id != self.pipeline.pipeline_id:
            return None
        if version is not None and version != self.pipeline.version:
            return None
        return self.pipeline

    def resolve(self, feature: str):
        if feature != "corpus_metadata_enrichment":
            raise KeyError(feature)
        return {
            "pipeline": self.pipeline.model_dump(mode="json"),
            "pipeline_hash": pipeline_hash(self.pipeline),
        }


def test_v1_migration_preserves_legacy_build_request_and_binds_pipeline():
    legacy = CorpusProcessingConfig.model_validate(
        {
            "version": 1,
            "processing": {
                "segmentation": {
                    "mode": "source_units",
                    "source_units_per_record": 2,
                },
                "text": {"clean": True},
            },
            "provider": {"model": "qwen3:14b", "concurrency": 3},
            "enrichment": {"mode": "deep", "passes": 2},
        }
    )
    pipeline = _metadata_pipeline()

    migrated = migrate_v1_to_v2(legacy, pipeline=pipeline)

    assert migrated.format == "derridai-corpus-run"
    assert migrated.version == 2
    assert migrated.migration is not None
    assert migrated.migration.source_version == 1
    assert migrated.pipeline.definition is not None
    assert pipeline_hash(migrated.pipeline.definition) == pipeline_hash(pipeline)
    assert migrated.build_request(environ={}) == legacy.build_request(environ={})


def test_v2_requires_explicit_format():
    migrated = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=_metadata_pipeline(),
    )
    payload = migrated.public_snapshot()
    payload.pop("format")

    with pytest.raises(ValidationError):
        CorpusRunEnvelopeV2.model_validate(payload)


def test_v2_pipeline_selection_requires_exactly_one_definition_or_reference():
    pipeline = _metadata_pipeline().model_dump(mode="json")
    base = {
        "format": "derridai-corpus-run",
        "version": 2,
        "pipeline": {},
    }

    with pytest.raises(ValidationError, match="exactly one"):
        CorpusRunEnvelopeV2.model_validate(base)

    both = copy.deepcopy(base)
    both["pipeline"] = {
        "definition": pipeline,
        "ref": {
            "pipeline_id": pipeline["pipeline_id"],
            "version": pipeline["version"],
        },
    }
    with pytest.raises(ValidationError, match="exactly one"):
        CorpusRunEnvelopeV2.model_validate(both)


def test_v2_rejects_unknown_pipeline_execution_fields():
    migrated = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=_metadata_pipeline(),
    )
    payload = migrated.public_snapshot()
    payload["pipeline"]["definition"]["unexpected_execution_field"] = True

    with pytest.raises(ValidationError, match="Unknown pipeline definition field"):
        CorpusRunEnvelopeV2.model_validate(payload)


def test_v2_rejects_overrides_for_a_different_pipeline_identity():
    pipeline = _metadata_pipeline()
    payload = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=pipeline,
    ).public_snapshot()
    payload["pipeline"]["overrides"] = {
        "pipeline_id": "different.pipeline",
        "pipeline_version": pipeline.version,
        "stages": {"primary": {"attempts": 2}},
    }

    with pytest.raises(ValidationError, match="must target the selected pipeline"):
        CorpusRunEnvelopeV2.model_validate(payload)


def test_current_headless_execution_accepts_the_same_assigned_pipeline():
    pipeline = _metadata_pipeline()
    config = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=pipeline,
    )

    selected = config.validate_current_headless_execution(_PipelineManager(pipeline))

    assert pipeline_hash(selected) == pipeline_hash(pipeline)


def test_current_headless_execution_rejects_unapplied_per_run_override():
    pipeline = _metadata_pipeline()
    config = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=pipeline,
    )
    config.pipeline.overrides = PipelineConfigOverrideSet(
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        stages={"primary": {"attempts": 2}},
    )

    with pytest.raises(ValueError, match="Per-run pipeline injection is not yet available"):
        config.validate_current_headless_execution(_PipelineManager(pipeline))


def test_loader_accepts_v2_yaml(tmp_path):
    migrated = migrate_v1_to_v2(
        CorpusProcessingConfig.model_validate({"version": 1}),
        pipeline=_metadata_pipeline(),
    )
    path = tmp_path / "run.yaml"
    path.write_text(
        yaml.safe_dump(migrated.public_snapshot(), sort_keys=False),
        encoding="utf-8",
    )

    loaded = load_processing_config(path)

    assert isinstance(loaded, CorpusRunEnvelopeV2)
    assert loaded.pipeline.definition is not None
    assert pipeline_hash(loaded.pipeline.definition) == pipeline_hash(_metadata_pipeline())


def test_cli_migrates_v1_to_v2_with_the_resolved_pipeline(
    tmp_path,
    monkeypatch,
    capsys,
):
    pipeline = _metadata_pipeline()
    source = tmp_path / "v1.yaml"
    source.write_text("version: 1\n", encoding="utf-8")

    from app.pipelines.manager import pipeline_manager

    monkeypatch.setattr(
        pipeline_manager,
        "resolve",
        lambda feature: {
            "pipeline": pipeline.model_dump(mode="json"),
            "pipeline_hash": pipeline_hash(pipeline),
        },
    )

    code = main(["config", "migrate", "--config", str(source)])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    payload = yaml.safe_load(captured.out)
    assert payload["format"] == "derridai-corpus-run"
    assert payload["version"] == 2
    assert payload["migration"]["source_version"] == 1
    assert payload["pipeline"]["definition"]["pipeline_id"] == pipeline.pipeline_id
    assert captured.err == ""
