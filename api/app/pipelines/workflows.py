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

"""Runtime adapters for each pipeline purpose, and the compatibility they imply.

Each purpose has exactly one code-owned adapter. Compiling a graph with it is the
runtime-support check, and its strategy allowlist is the source for the editor's
"supported for this workflow" guidance. Structural validity stays separate: a
graph using other strategies can still be saved as an inspect-only version.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from . import (
    evidence,
    evidence_recovery,
    memory,
    metadata_precedents,
    metadata_prefill,
    precedent_remap,
    research,
    store_search,
)
from .corpus_document_manifest import (
    DOCUMENT_MANIFEST,
    compile_document_manifest_pipeline,
)
from .corpus_metadata_enrichment import ENRICHMENT, compile_enrichment_pipeline
from .corpus_reviewer_evidence_choice import (
    REVIEWER_EVIDENCE_CHOICE,
    compile_reviewer_evidence_choice_pipeline,
)
from .corpus_segmentation import SEGMENTATION, compile_segmentation_pipeline
from .corpus_text_touchup import TEXT_TOUCHUP, compile_text_touchup_pipeline
from .models import PipelineDefinition, StrategySpec
from .purposes import PipelinePurposeSpec, purpose_registry, serialize_purpose
from .registry import StrategyRegistry, strategy_registry
from .wiring import bindings_changing_wiring

StrategyFit = Literal["supported", "inspect_only", "output_contract"]


@dataclass(frozen=True)
class PurposeAdapter:
    compile: Callable[[PipelineDefinition], Any]
    supported_strategies: frozenset[str]
    describe: Callable[[Any], dict[str, Any]] | None = None
    # True when the adapter delivers stage inputs from the resolved wiring, so explicit bindings run.
    honours_bindings: bool = False


def _recovery_details(plan: Any) -> dict[str, Any]:
    return {"celf_compliant": plan.celf_compliant, "reason": plan.compliance_reason}


PURPOSE_ADAPTERS: dict[str, PurposeAdapter] = {
    "research": PurposeAdapter(research.compile_research_pipeline, research.SUPPORTED_STRATEGIES),
    "evidence_suggestion": PurposeAdapter(
        evidence.compile_evidence_pipeline, evidence.SUPPORTED_STRATEGIES
    ),
    "evidence_recovery": PurposeAdapter(
        evidence_recovery.compile_recovery_pipeline,
        evidence_recovery.SUPPORTED_STRATEGIES,
        _recovery_details,
        honours_bindings=True,
    ),
    "precedent_evidence_remap": PurposeAdapter(
        precedent_remap.compile_remap_pipeline, precedent_remap.SUPPORTED_STRATEGIES
    ),
    "corpus_reviewer_evidence_choice": PurposeAdapter(
        compile_reviewer_evidence_choice_pipeline,
        frozenset({REVIEWER_EVIDENCE_CHOICE.strategy}),
    ),
    "vector_store_search": PurposeAdapter(
        store_search.compile_store_search_pipeline,
        store_search.SUPPORTED_STRATEGIES,
        honours_bindings=True,
    ),
    "metadata_precedents": PurposeAdapter(
        metadata_precedents.compile_metadata_precedent_pipeline,
        metadata_precedents.SUPPORTED_STRATEGIES,
    ),
    "metadata_prefill": PurposeAdapter(
        metadata_prefill.compile_prefill_pipeline, metadata_prefill.SUPPORTED_STRATEGIES
    ),
    "corpus_metadata_enrichment": PurposeAdapter(
        compile_enrichment_pipeline, frozenset({ENRICHMENT.strategy})
    ),
    "claim_memory": PurposeAdapter(
        memory.compile_memory_pipeline, memory.supported_strategies("claim_memory")
    ),
    "response_memory": PurposeAdapter(
        memory.compile_memory_pipeline, memory.supported_strategies("response_memory")
    ),
    "corpus_document_manifest": PurposeAdapter(
        compile_document_manifest_pipeline, frozenset({DOCUMENT_MANIFEST.strategy})
    ),
    "corpus_segmentation": PurposeAdapter(
        compile_segmentation_pipeline, frozenset({SEGMENTATION.strategy})
    ),
    "corpus_text_touchup": PurposeAdapter(
        compile_text_touchup_pipeline, frozenset({TEXT_TOUCHUP.strategy})
    ),
}


def runtime_support(pipeline: PipelineDefinition) -> dict[str, Any]:
    """Describe whether a saved graph can currently drive production code."""

    adapter = PURPOSE_ADAPTERS.get(pipeline.purpose)
    if adapter is None:
        return {
            "supported": False,
            "adapter": None,
            "reason": "This pipeline purpose does not have a runtime adapter.",
        }
    try:
        plan = adapter.compile(pipeline)
    except ValueError as exc:
        return {"supported": False, "adapter": None, "reason": str(exc)}
    changed = (
        []
        if adapter.honours_bindings
        else bindings_changing_wiring(pipeline, strategy_registry, purpose_registry.get(pipeline.purpose))
    )
    if changed:
        return {
            "supported": False,
            "adapter": None,
            "reason": (
                "The runtime adapter takes stage inputs from the graph edges and cannot "
                "apply explicit input bindings that change them: " + ", ".join(changed) + ". "
                "The pipeline stays inspect-only."
            ),
        }
    details = adapter.describe(plan) if adapter.describe else {}
    return {"supported": True, "adapter": pipeline.purpose, **details}


def compile_for_feature(feature: str, pipeline: PipelineDefinition) -> None:
    """Raise unless ``pipeline`` is a runnable graph for the purpose ``feature`` consumes."""

    spec = purpose_registry.for_feature(feature)
    if spec is None or spec.purpose_id not in PURPOSE_ADAPTERS:
        raise ValueError(f"Pipeline feature {feature!r} is not supported.")
    if pipeline.purpose != spec.purpose_id:
        raise ValueError(
            f"Feature {feature!r} runs {spec.purpose_id} pipelines; "
            f"{pipeline.pipeline_id!r} is a {pipeline.purpose} pipeline."
        )
    PURPOSE_ADAPTERS[spec.purpose_id].compile(pipeline)


def _strategy_fit(
    strategy: StrategySpec,
    supported: frozenset[str],
    adapter_types: set[str],
) -> StrategyFit:
    if strategy.strategy_id in supported:
        return "supported"
    # A strategy whose output this adapter never handles would change what the
    # workflow returns (for example a model response where candidates are due).
    if strategy.output_type != "any" and strategy.output_type not in adapter_types:
        return "output_contract"
    return "inspect_only"


def strategy_compatibility(
    spec: PipelinePurposeSpec,
    registry: StrategyRegistry = strategy_registry,
) -> dict[str, StrategyFit]:
    """How each registered strategy fits one purpose's runtime adapter, deterministically."""

    adapter = PURPOSE_ADAPTERS[spec.purpose_id]
    specs = registry.list()
    adapter_types = {spec.output_type} | {
        value
        for item in specs
        if item.strategy_id in adapter.supported_strategies
        for value in (item.input_type, item.output_type)
    }
    return {
        item.strategy_id: _strategy_fit(item, adapter.supported_strategies, adapter_types)
        for item in specs
    }


def purpose_catalog(registry: StrategyRegistry = strategy_registry) -> list[dict[str, Any]]:
    """Serialized purpose contracts with their adapter's strategy compatibility."""

    return [
        {**serialize_purpose(spec), "strategy_fit": strategy_compatibility(spec, registry)}
        for spec in purpose_registry.list()
    ]
