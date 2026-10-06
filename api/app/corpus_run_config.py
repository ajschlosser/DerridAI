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

"""Version-2 corpus-run envelope around the canonical pipeline contract.

Version 1 remains readable for compatibility. Version 2 adds an exact
PipelineDefinition (or immutable reference) and typed stage overrides while
retaining the still-transitional Corpus Builder settings that have not yet moved
onto generic pipeline strategies. Those compatibility settings deliberately
reuse the v1 projection into the shared Corpus Builder engine so migration does
not change scholarly behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

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
from .pipelines.models import (
    InputBinding,
    PipelineConfigOverrideSet,
    PipelineDefinition,
    PipelineStageDefinition,
)
from .pipelines.overrides import resolve_pipeline_config
from .pipelines.service import pipeline_hash


class _StrictRunModel(BaseModel):
    """Reject unknown run-envelope keys instead of silently reinterpreting them."""

    model_config = ConfigDict(extra="forbid")


class PipelineDefinitionRef(_StrictRunModel):
    """Immutable reference to a saved or built-in pipeline definition."""

    pipeline_id: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)


class RunEnvelopeMigration(_StrictRunModel):
    """Non-authoritative record of a deterministic run-envelope migration."""

    source_format: Literal["derridai-corpus-processing"]
    source_version: Literal[1]


def _unknown_keys(payload: object, model: type[BaseModel]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(set(payload) - set(model.model_fields))


def _reject_unknown_pipeline_fields(value: object) -> object:
    """Apply strict import semantics without changing native pipeline persistence.

    Historical native PipelineDefinition rows predate a global extra-forbid
    policy. The portable run envelope is stricter: unknown executable fields are
    rejected at this transport boundary rather than being discarded by Pydantic.
    """

    if not isinstance(value, dict):
        return value

    unknown = _unknown_keys(value, PipelineDefinition)
    if unknown:
        raise ValueError(
            "Unknown pipeline definition field(s): " + ", ".join(unknown)
        )

    stages = value.get("stages")
    if isinstance(stages, list):
        for index, stage in enumerate(stages):
            stage_unknown = _unknown_keys(stage, PipelineStageDefinition)
            if stage_unknown:
                raise ValueError(
                    f"Unknown pipeline stage field(s) at stages[{index}]: "
                    + ", ".join(stage_unknown)
                )
            if not isinstance(stage, dict):
                continue
            inputs = stage.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for port_name, bindings in inputs.items():
                if not isinstance(bindings, list):
                    continue
                for binding_index, binding in enumerate(bindings):
                    binding_unknown = _unknown_keys(binding, InputBinding)
                    if binding_unknown:
                        raise ValueError(
                            "Unknown pipeline input-binding field(s) at "
                            f"stages[{index}].inputs[{port_name!r}][{binding_index}]: "
                            + ", ".join(binding_unknown)
                        )
    return value


class PipelineRunSelection(_StrictRunModel):
    """One exact executable pipeline plus optional bounded configuration overrides."""

    definition: PipelineDefinition | None = None
    ref: PipelineDefinitionRef | None = None
    overrides: PipelineConfigOverrideSet | None = None

    @field_validator("definition", mode="before")
    @classmethod
    def reject_unknown_definition_fields(cls, value: object) -> object:
        return _reject_unknown_pipeline_fields(value)

    @model_validator(mode="after")
    def validate_selection(self) -> "PipelineRunSelection":
        if (self.definition is None) == (self.ref is None):
            raise ValueError("pipeline must contain exactly one of definition or ref")

        if self.definition is not None:
            pipeline_id = self.definition.pipeline_id
            version = self.definition.version
        else:
            assert self.ref is not None
            pipeline_id = self.ref.pipeline_id
            version = self.ref.version
        if self.overrides is not None and not self.overrides.empty:
            if (
                self.overrides.pipeline_id != pipeline_id
                or self.overrides.pipeline_version != version
            ):
                raise ValueError(
                    "pipeline overrides must target the selected pipeline ID/version"
                )
        return self

    def resolve(self, manager: Any) -> PipelineDefinition:
        """Resolve and validate the selected immutable pipeline definition."""

        if self.definition is not None:
            definition = self.definition
        else:
            assert self.ref is not None
            definition = manager.get_definition(self.ref.pipeline_id, self.ref.version)
            if definition is None:
                raise ValueError(
                    f"Pipeline {self.ref.pipeline_id}@{self.ref.version} was not found."
                )

        validation = manager.service.validate(definition)
        errors = [
            issue.message
            for issue in validation.issues
            if issue.level == "error"
        ]
        if errors:
            raise ValueError(
                f"Pipeline {definition.pipeline_id}@{definition.version} is invalid: "
                + "; ".join(errors)
            )
        return definition

    def effective(self, manager: Any) -> PipelineDefinition:
        """Return the definition after applying the envelope's typed overrides."""

        definition = self.resolve(manager)
        if self.overrides is None or self.overrides.empty:
            return definition
        return resolve_pipeline_config(
            definition,
            run_overrides=self.overrides,
            service=manager.service,
        ).effective


class CorpusRunEnvelopeV2(_StrictRunModel):
    """Portable v2 corpus-run configuration.

    processing and enrichment are explicitly transitional. They remain here only
    for v1 behavioral parity while their execution-affecting properties move to
    registered pipeline strategies.
    """

    format: Literal["derridai-corpus-run"]
    version: Literal[2]
    migration: RunEnvelopeMigration | None = None
    source: SourceConfig = Field(default_factory=SourceConfig)
    pipeline: PipelineRunSelection
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    review: AutomaticReviewConfig = Field(default_factory=AutomaticReviewConfig)
    publication: PublicationConfig = Field(default_factory=PublicationConfig)

    def _legacy_adapter(self) -> CorpusProcessingConfig:
        """Build the temporary v1 adapter used by the existing corpus engine."""

        return CorpusProcessingConfig(
            version=1,
            source=self.source,
            processing=self.processing,
            metadata=self.metadata,
            enrichment=self.enrichment,
            provider=self.provider,
            review=self.review,
            publication=self.publication,
        )

    def build_request(
        self,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Project non-pipeline run settings through the existing shared adapter."""

        return self._legacy_adapter().build_request(environ=environ)

    def public_snapshot(self) -> dict[str, Any]:
        """Return the complete non-secret run envelope retained for reproducibility."""

        return self.model_dump(mode="json")

    def validate_current_headless_execution(self, manager: Any) -> PipelineDefinition:
        """Ensure today's Corpus Builder executes the pipeline the file declares.

        The v2 format can carry portable definitions and typed overrides, but the
        current Corpus Builder still resolves its metadata-enrichment pipeline
        from the shared assignment registry. Until the executor accepts a per-run
        definition directly, headless execution fails rather than silently
        ignoring a different portable definition or override.
        """

        selected = self.effective(manager)
        if selected.purpose != "corpus_metadata_enrichment":
            raise ValueError(
                "The current headless corpus adapter requires a "
                "corpus_metadata_enrichment pipeline."
            )

        try:
            active = manager.resolve("corpus_metadata_enrichment")
        except KeyError as exc:
            raise ValueError(
                "No corpus_metadata_enrichment pipeline is assigned in this installation."
            ) from exc
        active_definition = PipelineDefinition.model_validate(active["pipeline"])
        if pipeline_hash(selected) != pipeline_hash(active_definition):
            raise ValueError(
                "This v2 run declares a pipeline definition or override that differs "
                "from the corpus_metadata_enrichment pipeline currently assigned to "
                "the shared Corpus Builder. Per-run pipeline injection is not yet "
                "available; assign the same definition in Pipeline Studio or use a "
                "matching exported run configuration."
            )
        return selected


def migrate_v1_to_v2(
    config: CorpusProcessingConfig,
    *,
    pipeline: PipelineDefinition,
) -> CorpusRunEnvelopeV2:
    """Create a portable, behavior-preserving v2 envelope from one v1 file.

    The caller supplies the exact pipeline resolved for the migration environment;
    this avoids pretending that a v1 file itself recorded pipeline identity.
    """

    return CorpusRunEnvelopeV2(
        format="derridai-corpus-run",
        version=2,
        migration=RunEnvelopeMigration(
            source_format="derridai-corpus-processing",
            source_version=1,
        ),
        source=config.source,
        pipeline=PipelineRunSelection(definition=pipeline.model_copy(deep=True)),
        processing=config.processing,
        metadata=config.metadata,
        enrichment=config.enrichment,
        provider=config.provider,
        review=config.review,
        publication=config.publication,
    )
