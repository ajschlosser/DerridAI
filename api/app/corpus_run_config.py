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

"""Version-2 run envelope for headless Corpus Builder execution.

The v1 CorpusProcessingConfig remains a compatibility input. Version 2 separates
run-envelope concerns from executable pipeline definitions and pins the pipeline
identities/strategy versions that were current when the file was exported. The
existing v1 adapter remains the temporary bridge into the Corpus Builder request
model while more execution settings move onto registered pipeline strategies.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .corpus_cli_config import (
    AutomaticReviewConfig,
    CorpusProcessingConfig,
    EnrichmentConfig,
    MetadataConfig,
    ProcessingConfig,
    ProviderConfig,
    PublicationConfig,
    SourceConfig,
)
from .pipelines.compatibility import (
    pipeline_strategy_requirements,
    validate_pipeline_strategy_requirements,
)
from .pipelines.models import (
    InputBinding,
    PipelineConfigOverrideSet,
    PipelineDefinition,
    PipelineStageDefinition,
)
from .pipelines.service import pipeline_hash

RUN_ENVELOPE_FORMAT = "derridai-corpus-run"
RUN_ENVELOPE_VERSION = 2

# Assignments the unattended Corpus Builder can exercise during a normal
# source -> enrichment -> publication run. Reviewer-only actions are excluded.
HEADLESS_CORPUS_PIPELINE_FEATURES: tuple[str, ...] = (
    "corpus_document_manifest",
    "corpus_segmentation",
    "corpus_metadata_enrichment",
    "corpus_text_touchup",
    "metadata_prefill",
    "metadata_precedents",
)


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _reject_unknown_model_keys(
    value: Any,
    model: type[BaseModel],
    *,
    label: str,
) -> None:
    if not isinstance(value, Mapping):
        return
    unknown = sorted(set(value) - set(model.model_fields))
    if unknown:
        raise ValueError(
            f"{label} contains unknown field(s): {', '.join(unknown)}"
        )


class CorpusPipelineBinding(_StrictConfigModel):
    """One feature binding frozen to an exact executable definition."""

    definition: PipelineDefinition
    pipeline_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    required_strategies: dict[str, int] = Field(min_length=1, max_length=64)
    overrides: PipelineConfigOverrideSet | None = None

    @field_validator("definition", mode="before")
    @classmethod
    def reject_unknown_definition_fields(cls, value: Any) -> Any:
        _reject_unknown_model_keys(value, PipelineDefinition, label="Pipeline definition")
        if isinstance(value, Mapping):
            for index, stage in enumerate(value.get("stages") or []):
                _reject_unknown_model_keys(
                    stage,
                    PipelineStageDefinition,
                    label=f"Pipeline stage {index}",
                )
                if isinstance(stage, Mapping):
                    for port, bindings in (stage.get("inputs") or {}).items():
                        for binding_index, binding in enumerate(bindings or []):
                            _reject_unknown_model_keys(
                                binding,
                                InputBinding,
                                label=(
                                    f"Pipeline stage {index} input {port!r} "
                                    f"binding {binding_index}"
                                ),
                            )
        return value

    @field_validator("required_strategies")
    @classmethod
    def validate_strategy_versions_shape(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for strategy_id, version in value.items():
            key = str(strategy_id).strip()
            if not key:
                raise ValueError("Strategy IDs cannot be empty.")
            version = int(version)
            if version < 1:
                raise ValueError("Strategy versions must be positive integers.")
            normalized[key] = version
        return dict(sorted(normalized.items()))

    @model_validator(mode="after")
    def validate_binding(self) -> "CorpusPipelineBinding":
        actual_hash = pipeline_hash(self.definition)
        if self.pipeline_hash != actual_hash:
            raise ValueError(
                f"Pipeline hash mismatch for {self.definition.pipeline_id}@"
                f"{self.definition.version}: expected {actual_hash}."
            )

        stage_strategies = {stage.strategy for stage in self.definition.stages}
        if set(self.required_strategies) != stage_strategies:
            missing = sorted(stage_strategies - set(self.required_strategies))
            extra = sorted(set(self.required_strategies) - stage_strategies)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise ValueError(
                "Pipeline strategy requirements do not match the definition"
                + (": " + "; ".join(details) if details else ".")
            )
        validate_pipeline_strategy_requirements(self.required_strategies)

        if self.overrides is not None:
            if (
                self.overrides.pipeline_id != self.definition.pipeline_id
                or self.overrides.pipeline_version != self.definition.version
            ):
                raise ValueError(
                    "Pipeline overrides must target the embedded pipeline ID/version."
                )
        return self


class CorpusPipelineBundle(_StrictConfigModel):
    """Feature -> immutable pipeline binding for one corpus run."""

    assignments: dict[str, CorpusPipelineBinding] = Field(
        min_length=1,
        max_length=32,
    )

    @field_validator("assignments")
    @classmethod
    def validate_assignment_names(
        cls,
        value: dict[str, CorpusPipelineBinding],
    ) -> dict[str, CorpusPipelineBinding]:
        normalized: dict[str, CorpusPipelineBinding] = {}
        for feature, binding in value.items():
            name = str(feature).strip()
            if not name:
                raise ValueError("Pipeline feature names cannot be empty.")
            normalized[name] = binding
        return dict(sorted(normalized.items()))


class CorpusRunConfigV2(_StrictConfigModel):
    """Portable run envelope around canonical pipeline definitions."""

    format: Literal["derridai-corpus-run"] = RUN_ENVELOPE_FORMAT
    version: Literal[2] = RUN_ENVELOPE_VERSION
    source: SourceConfig = Field(default_factory=SourceConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    review: AutomaticReviewConfig = Field(default_factory=AutomaticReviewConfig)
    publication: PublicationConfig = Field(default_factory=PublicationConfig)
    pipelines: CorpusPipelineBundle

    def _v1_adapter(self) -> CorpusProcessingConfig:
        """Project envelope-only settings through the existing request adapter."""

        return CorpusProcessingConfig.model_validate(
            {
                "version": 1,
                "source": self.source.model_dump(mode="json"),
                "processing": self.processing.model_dump(mode="json"),
                "metadata": self.metadata.model_dump(mode="json"),
                "enrichment": self.enrichment.model_dump(mode="json"),
                "provider": self.provider.model_dump(mode="json"),
                "review": self.review.model_dump(mode="json"),
                "publication": self.publication.model_dump(mode="json"),
            }
        )

    def build_request(
        self,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._v1_adapter().build_request(environ=environ)

    def public_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def assert_installed_pipeline_bindings(self) -> None:
        """Fail before source extraction if installed assignments have drifted.

        This is a conservative bridge while Corpus Builder call sites are taught
        to consume embedded definitions directly. A v2 run never silently falls
        back to a different active assignment.
        """

        from .pipelines.manager import pipeline_manager

        for feature, binding in self.pipelines.assignments.items():
            try:
                resolved = pipeline_manager.resolve(feature)
            except KeyError as exc:
                raise ValueError(
                    f"Pipeline feature {feature!r} is not available in this DerridAI installation."
                ) from exc
            installed = PipelineDefinition.model_validate(resolved["pipeline"])
            installed_hash = str(resolved.get("pipeline_hash") or pipeline_hash(installed))
            expected = binding.definition
            if (
                installed.pipeline_id != expected.pipeline_id
                or installed.version != expected.version
                or installed_hash != binding.pipeline_hash
            ):
                raise ValueError(
                    f"Pipeline feature {feature!r} is pinned to "
                    f"{expected.pipeline_id}@{expected.version} ({binding.pipeline_hash[:12]}), "
                    f"but this installation resolves "
                    f"{installed.pipeline_id}@{installed.version} ({installed_hash[:12]}). "
                    "Import/activate the pinned definition or migrate the run configuration."
                )


CorpusRunConfig = CorpusProcessingConfig | CorpusRunConfigV2


def _binding_for_feature(feature: str) -> CorpusPipelineBinding:
    from .pipelines.manager import pipeline_manager

    resolved = pipeline_manager.resolve(feature)
    definition = PipelineDefinition.model_validate(resolved["pipeline"])
    return CorpusPipelineBinding(
        definition=definition,
        pipeline_hash=str(resolved.get("pipeline_hash") or pipeline_hash(definition)),
        required_strategies=pipeline_strategy_requirements(definition),
    )


def migrate_v1_config(config: CorpusProcessingConfig) -> CorpusRunConfigV2:
    """Wrap a v1 CLI config in the canonical v2 pipeline run envelope."""

    bindings: dict[str, CorpusPipelineBinding] = {}
    for feature in HEADLESS_CORPUS_PIPELINE_FEATURES:
        try:
            bindings[feature] = _binding_for_feature(feature)
        except KeyError as exc:
            raise ValueError(
                f"Cannot migrate v1 configuration: required pipeline feature "
                f"{feature!r} is unavailable."
            ) from exc

    payload = config.public_snapshot()
    payload.pop("version", None)
    return CorpusRunConfigV2.model_validate(
        {
            "format": RUN_ENVELOPE_FORMAT,
            "version": RUN_ENVELOPE_VERSION,
            **payload,
            "pipelines": {"assignments": bindings},
        }
    )


def load_run_config(path: str | Path) -> CorpusRunConfig:
    """Load either legacy v1 YAML or the v2 run envelope."""

    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read configuration {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Corpus processing configuration must be a YAML mapping")

    if payload.get("format") == RUN_ENVELOPE_FORMAT or payload.get("version") == 2:
        return CorpusRunConfigV2.model_validate(payload)
    return CorpusProcessingConfig.model_validate(payload)


def dump_run_config(config: CorpusRunConfigV2) -> str:
    """Serialize a v2 run envelope deterministically without runtime secrets."""

    return yaml.safe_dump(
        config.public_snapshot(),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
