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

"""Versioned YAML contract for the headless Corpus Builder CLI.

The CLI configuration is deliberately independent of FastAPI request models.
Transport adapters may project this contract into the existing corpus engine, but
the YAML format must not drift simply because a web form changes.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from .corpus_run_config import CorpusRunEnvelopeV2


class _StrictConfigModel(BaseModel):
    """Base class that rejects misspelled/unknown YAML keys."""

    model_config = ConfigDict(extra="forbid")


class SourceConfig(_StrictConfigModel):
    ocr_mode: Literal["auto", "always", "never"] = "auto"
    ocr_languages: str = Field(default="eng+fra+deu", min_length=1, max_length=200)
    detect_page_numbers: bool = True
    audio_diarization: bool = True


class SegmentationConfig(_StrictConfigModel):
    mode: Literal["semantic", "source_units"] = "semantic"
    source_units_per_record: int = Field(default=1, ge=1, le=100)
    records_per_page: int | None = Field(default=None, ge=1, le=100)
    preferred_record_chars: int = Field(default=1750, ge=100, le=12000)
    record_length_tolerance: int = Field(default=200, ge=10, le=2000)
    long_record_chars: int = Field(default=3500, ge=100, le=24000)
    absolute_record_chars: int = Field(default=6000, ge=100, le=48000)

    def model_post_init(self, __context: Any) -> None:
        if self.long_record_chars < self.preferred_record_chars + self.record_length_tolerance:
            raise ValueError(
                "long_record_chars must be at least "
                "preferred_record_chars + record_length_tolerance"
            )
        if self.absolute_record_chars < self.long_record_chars:
            raise ValueError("absolute_record_chars must be at least long_record_chars")


class TextProcessingConfig(_StrictConfigModel):
    clean: bool = False
    llm_touchup: bool = False


class DocumentIntelligenceConfig(_StrictConfigModel):
    profile: Literal["none", "general", "fiction", "scholarly"] = "scholarly"
    provider: Literal["auto", "spacy", "booknlp"] = "auto"
    include_events: bool = False


class ProcessingConfig(_StrictConfigModel):
    profile_id: str = Field(default="derrida-scholarly-v12", min_length=1, max_length=200)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    text: TextProcessingConfig = Field(default_factory=TextProcessingConfig)
    document_intelligence: DocumentIntelligenceConfig = Field(
        default_factory=DocumentIntelligenceConfig
    )


class FieldGuidanceConfig(_StrictConfigModel):
    instructions: str = Field(default="", max_length=1200)
    look_for: list[str] = Field(default_factory=list, max_length=40)
    required: bool = False

    @field_validator("instructions", mode="before")
    @classmethod
    def trim_instructions(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("look_for", mode="before")
    @classmethod
    def normalize_look_for(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("look_for must be a list of phrases")
        terms: list[str] = []
        seen: set[str] = set()
        for raw in value:
            term = str(raw or "").strip()
            if not term:
                continue
            if len(term) > 160:
                raise ValueError("Each look_for phrase must be 160 characters or fewer")
            folded = term.casefold()
            if folded not in seen:
                terms.append(term)
                seen.add(folded)
        return terms


class MetadataConfig(_StrictConfigModel):
    schema_id: str = Field(default="default", min_length=1, max_length=64)
    work: dict[str, Any] = Field(default_factory=dict, max_length=60)
    document: dict[str, Any] = Field(default_factory=dict, max_length=20)
    guidance: dict[str, FieldGuidanceConfig] = Field(default_factory=dict, max_length=60)


class EnrichmentConfig(_StrictConfigModel):
    mode: Literal["fast", "deep"] = "fast"
    semantic_indexing: bool = False
    passes: int = Field(default=1, ge=1, le=3)


_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ProviderConfig(_StrictConfigModel):
    type: Literal["ollama", "openai"] = "ollama"
    model: str | None = Field(default=None, max_length=300)
    base_url: str | None = Field(default=None, max_length=2000)
    api_key_env: str | None = Field(default=None, max_length=200)
    concurrency: int = Field(default=1, ge=1, le=64)

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_environment_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            return None
        if not _ENVIRONMENT_NAME.fullmatch(name):
            raise ValueError("api_key_env must be a valid environment variable name")
        return name


class AutomaticReviewConfig(_StrictConfigModel):
    mode: Literal["automatic"] = "automatic"
    min_confidence: float = Field(default=0.8, ge=0.5, le=0.99)
    unresolved: Literal["best_guess", "leave"] = "best_guess"


class PublicationConfig(_StrictConfigModel):
    profile: Literal["research", "celf"] = "research"
    compression: Literal["zstd"] = "zstd"


class CorpusProcessingConfig(_StrictConfigModel):
    """Top-level v1 YAML processing contract."""

    version: Literal[1]
    source: SourceConfig = Field(default_factory=SourceConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    review: AutomaticReviewConfig = Field(default_factory=AutomaticReviewConfig)
    publication: PublicationConfig = Field(default_factory=PublicationConfig)

    def build_request(self, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Project YAML settings into the shared Corpus Builder request vocabulary.

        Source ingestion settings are intentionally not included here; the headless
        runner applies them while registering the source, then adds asset_id.
        """
        environment = os.environ if environ is None else environ
        segmentation = self.processing.segmentation
        guidance = {
            name: item.model_dump(mode="json")
            for name, item in self.metadata.guidance.items()
        }
        request: dict[str, Any] = {
            "profile_id": self.processing.profile_id,
            "provider": self.provider.type,
            "model": self.provider.model,
            "base_url": self.provider.base_url,
            "max_concurrent_requests": self.provider.concurrency,
            "record_sizing": {
                "preferred_record_chars": segmentation.preferred_record_chars,
                "record_length_tolerance": segmentation.record_length_tolerance,
                "long_record_chars": segmentation.long_record_chars,
                "absolute_record_chars": segmentation.absolute_record_chars,
            },
            "topology_policy": {
                "mode": segmentation.mode,
                "source_units_per_record": segmentation.source_units_per_record,
                "records_per_page": segmentation.records_per_page,
            },
            "schema_id": self.metadata.schema_id,
            "run_guidance": guidance,
            "auto_clean_text": self.processing.text.clean,
            "llm_touchup_during_enrichment": self.processing.text.llm_touchup,
            "enrichment_mode": self.enrichment.mode,
            "semantic_indexing": self.enrichment.semantic_indexing,
            "document_intelligence_profile": self.processing.document_intelligence.profile,
            "document_nlp_provider": self.processing.document_intelligence.provider,
            "document_nlp_include_events": self.processing.document_intelligence.include_events,
            "work_metadata": dict(self.metadata.work),
            "document_metadata": dict(self.metadata.document),
            "autonomous": {
                "enabled": True,
                "passes": self.enrichment.passes,
                "min_confidence": self.review.min_confidence,
                "unresolved": self.review.unresolved,
                "accept_records": True,
                "publish": False,
            },
        }
        if self.provider.api_key_env:
            api_key = str(environment.get(self.provider.api_key_env) or "").strip()
            if not api_key:
                raise ValueError(
                    f"Provider credential environment variable "
                    f"{self.provider.api_key_env!r} is not set"
                )
            request["api_key"] = api_key
        return {key: value for key, value in request.items() if value is not None}

    def public_snapshot(self) -> dict[str, Any]:
        """Return the reproducibility-safe configuration with no resolved secret."""
        return self.model_dump(mode="json")


def parse_processing_config(
    payload: object,
) -> CorpusProcessingConfig | CorpusRunEnvelopeV2:
    """Validate an already-decoded corpus configuration by explicit format version."""

    if not isinstance(payload, dict):
        raise ValueError("Corpus processing configuration must be a YAML mapping")

    version = payload.get("version")
    if version == 1:
        return CorpusProcessingConfig.model_validate(payload)
    if version == 2:
        from .corpus_run_config import CorpusRunEnvelopeV2

        return CorpusRunEnvelopeV2.model_validate(payload)
    raise ValueError(
        f"Unsupported corpus processing configuration version: {version!r}. "
        "Supported versions are 1 and 2."
    )


def load_processing_config(
    path: str | Path,
) -> CorpusProcessingConfig | "CorpusRunEnvelopeV2":
    """Load and validate one v1 or v2 YAML configuration file."""

    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read configuration {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc
    return parse_processing_config(payload)


def dump_processing_config_yaml(
    config: CorpusProcessingConfig | CorpusRunEnvelopeV2,
) -> str:
    """Serialize a validated, secret-free corpus configuration deterministically."""

    return yaml.safe_dump(
        config.public_snapshot(),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
