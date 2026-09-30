# Copyright 2026 Aaron John Schlosser, PhD.
"""Server-owned workflow contracts for pipeline purposes.

A pipeline's ``purpose`` says what the whole pipeline is for: which application
feature consumes it, what it takes and returns, and what its output does and
does not establish. A stage's strategy family says how one step computes, and
its scholarly effect says what, if anything, that step establishes about
evidence, support or provenance. The three are separate on purpose: the same
retrieval or reranking strategy can serve Research, Evidence, Search, Metadata
and Memory pipelines without becoming an "evidence strategy".

English copy here is the fallback; clients resolve the ``*_key`` fields through
the locale dictionaries. Identifiers never depend on translated strings.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .models import ScholarlyEffect, StageFamily

WorkflowCategory = Literal["research", "evidence", "search", "metadata", "memory", "corpus"]
WorkflowGuarantee = Literal[
    "direct_support",
    "source_provenance",
    "citation_binding",
    "reviewed_precedents_only",
    "eligible_memory_only",
    "backend_validation",
    "reviewer_approval",
    "text_conservation",
    "access_outside_pipeline",
]
WorkflowPhase = Literal["prepare", "find", "rank", "validate", "select", "generate", "evaluate"]
EffectNote = Literal[
    "no_effect",
    "candidates_not_evidence",
    "ranking_only",
    "diversity_only",
    "selection_only",
    "scope_constraint",
    "eligibility_gate",
    "provenance_gate",
    "transformation",
    "generation",
    "evaluation",
]


class VocabularyTerm(BaseModel):
    id: str
    label: str
    description: str


class PipelinePurposeSpec(BaseModel):
    """What one pipeline purpose is for, and what its output may be trusted to mean."""

    purpose_id: str = Field(min_length=1, max_length=160)
    category: WorkflowCategory
    label: str
    description: str
    consuming_feature: str = Field(min_length=1, max_length=160)
    consumer: str
    input_semantics: str
    output_semantics: str
    authority_semantics: str
    output_type: str
    assignment_scope: Literal["system"] = "system"
    override_allowed: bool = False
    required_guarantees: list[WorkflowGuarantee] = Field(default_factory=list)


def _key_stem(value: str) -> str:
    return value.replace(".", "_").replace("-", "_")


WORKFLOW_CATEGORIES: tuple[VocabularyTerm, ...] = (
    VocabularyTerm(
        id="research",
        label="Research",
        description="Answers a research question with an evidence-bound, cited response.",
    ),
    VocabularyTerm(
        id="evidence",
        label="Evidence",
        description="Suggests source passages that may support a metadata value. Suggestions stay advisory until a reviewer binds them.",
    ),
    VocabularyTerm(
        id="search",
        label="Search",
        description="Finds matching Records. Search results are not evidence and make no research claim.",
    ),
    VocabularyTerm(
        id="metadata",
        label="Metadata",
        description="Proposes metadata values or finds reviewed precedents for them.",
    ),
    VocabularyTerm(
        id="memory",
        label="Memory",
        description="Finds earlier Research claims or responses that may be relevant again.",
    ),
    VocabularyTerm(
        id="corpus",
        label="Corpus processing",
        description="Prepares source text for review: document analysis, segmentation and text touch-up.",
    ),
)

WORKFLOW_GUARANTEES: tuple[VocabularyTerm, ...] = (
    VocabularyTerm(
        id="direct_support",
        label="Direct support",
        description="A candidate must directly support the exact value or proposition before it is suggested.",
    ),
    VocabularyTerm(
        id="source_provenance",
        label="Source provenance",
        description="Every result must bind to a real source unit of the current source document.",
    ),
    VocabularyTerm(
        id="citation_binding",
        label="Citation binding",
        description="Citations come from Record metadata through deterministic code, never from the model.",
    ),
    VocabularyTerm(
        id="reviewed_precedents_only",
        label="Reviewed precedents only",
        description="Only reviewed values can serve as precedents; unreviewed model output never does.",
    ),
    VocabularyTerm(
        id="eligible_memory_only",
        label="Eligible memory only",
        description="Only reviewer-validated claims or responses that passed the grade gate can be recalled.",
    ),
    VocabularyTerm(
        id="backend_validation",
        label="Backend validation",
        description="Every model answer is validated by DerridAI before it is used.",
    ),
    VocabularyTerm(
        id="reviewer_approval",
        label="Reviewer approval",
        description="Results are proposals until a reviewer approves or binds them.",
    ),
    VocabularyTerm(
        id="text_conservation",
        label="Text conservation",
        description="No source text may be lost, invented, duplicated or reordered.",
    ),
    VocabularyTerm(
        id="access_outside_pipeline",
        label="Access rules outside the pipeline",
        description="Permissions, visibility and text limits are enforced by DerridAI, not by pipeline settings.",
    ),
)

WORKFLOW_PHASES: tuple[VocabularyTerm, ...] = (
    VocabularyTerm(id="prepare", label="Prepare", description="Prepares the query or request."),
    VocabularyTerm(id="find", label="Find", description="Finds and scopes candidates."),
    VocabularyTerm(id="rank", label="Rank", description="Normalizes, merges or reorders candidates."),
    VocabularyTerm(id="validate", label="Validate", description="Checks support, provenance or citations."),
    VocabularyTerm(id="select", label="Select / pack", description="Keeps a bounded subset or packs context."),
    VocabularyTerm(id="generate", label="Generate", description="Asks a language model for output."),
    VocabularyTerm(id="evaluate", label="Evaluate", description="Assesses a finished result."),
)

# Phases are presentation over the executable graph, derived from the
# registered family so the UI never keeps a second taxonomy.
FAMILY_PHASES: dict[StageFamily, WorkflowPhase] = {
    "query_transform": "prepare",
    "candidate_generation": "find",
    "filter": "find",
    "normalization": "rank",
    "fusion": "rank",
    "rerank": "rank",
    "support_validation": "validate",
    "diversity": "select",
    "selection": "select",
    "context_pack": "select",
    "llm": "generate",
    "evaluation": "evaluate",
}

SCHOLARLY_EFFECTS: tuple[VocabularyTerm, ...] = (
    VocabularyTerm(
        id="none",
        label="No scholarly effect",
        description="Passes data along or rescales scores. It establishes nothing about evidence or support.",
    ),
    VocabularyTerm(
        id="advisory",
        label="Advisory only",
        description="Finds, orders or selects candidates by relevance. Relevance does not establish support, evidence or authority.",
    ),
    VocabularyTerm(
        id="scope_constraint",
        label="Scope constraint",
        description="Removes candidates outside the required schema, field, language or scope. It does not judge support.",
    ),
    VocabularyTerm(
        id="eligibility_gate",
        label="Evidence eligibility gate",
        description="Lets a candidate through only when it directly supports the exact value. Passing is computational validation, not reviewer authority.",
    ),
    VocabularyTerm(
        id="provenance_gate",
        label="Provenance gate",
        description="Requires deterministic source identity and citation bindings. It checks where a result comes from, not whether it is true.",
    ),
    VocabularyTerm(
        id="transformation",
        label="Transformation",
        description="Reshapes a query or packs context for a later step without judging it.",
    ),
    VocabularyTerm(
        id="generation",
        label="Model generation",
        description="Generates model output from the context it is given. The output is checked downstream and is never evidence by itself.",
    ),
    VocabularyTerm(
        id="evaluation",
        label="Evaluation",
        description="Assesses a finished result, for example by grading an answer against its evidence.",
    ),
)

EFFECT_NOTES: tuple[VocabularyTerm, ...] = (
    VocabularyTerm(id="no_effect", label="No scholarly effect", description="Establishes nothing about evidence or support."),
    VocabularyTerm(
        id="candidates_not_evidence",
        label="Produces candidates — not evidence",
        description="Retrieval finds possible passages or Records. A retrieval score does not show that a passage supports anything.",
    ),
    VocabularyTerm(
        id="ranking_only",
        label="Relevance ranking only — does not establish support",
        description="A higher score means more relevant to the query, not that the passage supports a claim.",
    ),
    VocabularyTerm(
        id="diversity_only",
        label="Diversity selection — does not establish support",
        description="Balances relevance against variety. It does not show that any passage supports a claim.",
    ),
    VocabularyTerm(
        id="selection_only",
        label="Selection only — does not establish support",
        description="Keeps a bounded subset in the order it was given.",
    ),
    VocabularyTerm(
        id="scope_constraint",
        label="Scope constraint",
        description="Removes candidates outside the required scope. It does not judge support.",
    ),
    VocabularyTerm(
        id="eligibility_gate",
        label="Evidence eligibility gate",
        description="Only candidates that directly support the exact value pass. A reviewer still decides what becomes evidence.",
    ),
    VocabularyTerm(
        id="provenance_gate",
        label="Provenance gate",
        description="Only results bound to real source units and citations pass.",
    ),
    VocabularyTerm(
        id="transformation",
        label="Prepares input for a later step",
        description="Reshapes the query or packs context without judging it.",
    ),
    VocabularyTerm(
        id="generation",
        label="Generates model output from supplied context",
        description="The model's answer is validated downstream and is never evidence by itself.",
    ),
    VocabularyTerm(
        id="evaluation",
        label="Evaluates a finished result",
        description="Grades the output. A grade describes the run, not the truth of its claims.",
    ),
)

_ADVISORY_NOTES: dict[StageFamily, EffectNote] = {
    "candidate_generation": "candidates_not_evidence",
    "filter": "candidates_not_evidence",
    "normalization": "ranking_only",
    "fusion": "ranking_only",
    "rerank": "ranking_only",
    "diversity": "diversity_only",
    "selection": "selection_only",
    "context_pack": "selection_only",
    "query_transform": "transformation",
    "support_validation": "selection_only",
    "llm": "candidates_not_evidence",
    "evaluation": "evaluation",
}


def effect_note(family: StageFamily, effect: ScholarlyEffect) -> EffectNote:
    """The short practical statement a stage card shows for its family and effect."""

    if effect == "advisory":
        return _ADVISORY_NOTES[family]
    if effect == "none":
        return "no_effect"
    return effect


PIPELINE_PURPOSES: tuple[PipelinePurposeSpec, ...] = (
    PipelinePurposeSpec(
        purpose_id="research",
        category="research",
        label="Research",
        description="Retrieves, ranks and packs evidence, then generates a cited Research response.",
        consuming_feature="research",
        consumer="Research workspace",
        input_semantics="A research question and the chosen corpus and retrieval scope.",
        output_semantics="A generated research response with evidence-bound claims and citations.",
        authority_semantics="Retrieval and generation stay evidence-bound and provenance-aware. Relevance scores and model prose are not scholarly authority.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["source_provenance", "citation_binding"],
    ),
    PipelinePurposeSpec(
        purpose_id="evidence_suggestion",
        category="evidence",
        label="Reviewer evidence suggestion",
        description="Suggests source passages of the current Record that may support a metadata value under review.",
        consuming_feature="evidence_suggestion.reviewer",
        consumer="Record review → Evidence suggestions",
        input_semantics="A metadata field and value, and the current source scope.",
        output_semantics="Advisory source candidates.",
        authority_semantics="Relevance ranking alone never makes a candidate evidence. A suggestion becomes evidence only when a reviewer binds it.",
        output_type="candidate_set",
        override_allowed=True,
        required_guarantees=["direct_support", "source_provenance", "reviewer_approval"],
    ),
    PipelinePurposeSpec(
        purpose_id="evidence_recovery",
        category="evidence",
        label="Evidence recovery",
        description="Finds evidence for values that reached enrichment or acceptance without bound evidence, running costlier stages only when cheaper ones find nothing.",
        consuming_feature="evidence_recovery",
        consumer="Corpus Builder → Metadata enrichment and value acceptance",
        input_semantics="A metadata value without bound evidence, and the current Record's source units.",
        output_semantics="Advisory recovered evidence candidates, without a confidence score.",
        authority_semantics="Recovered candidates are advisory and never count as reviewed evidence. Without the direct-support gate the output is not cELF-guaranteed.",
        output_type="candidate_set",
        override_allowed=True,
        required_guarantees=["source_provenance", "reviewer_approval"],
    ),
    PipelinePurposeSpec(
        purpose_id="precedent_evidence_remap",
        category="evidence",
        label="Precedent evidence remapping",
        description="Finds where the current Record may support a value adopted from a reviewed precedent.",
        consuming_feature="precedent_evidence_remap",
        consumer="Record review → Reviewed precedents",
        input_semantics="A reviewed precedent's evidence and the current Record's source units.",
        output_semantics="An advisory shortlist of the current Record's source units.",
        authority_semantics="The shortlist binds nothing and never carries the precedent's text or source identity.",
        output_type="candidate_set",
        override_allowed=True,
        required_guarantees=["source_provenance", "reviewer_approval"],
    ),
    PipelinePurposeSpec(
        purpose_id="corpus_reviewer_evidence_choice",
        category="evidence",
        label="Reviewer evidence choice",
        description="When a reviewer asks, a model chooses which of the Record's own source units support a metadata value.",
        consuming_feature="corpus_reviewer_evidence_choice",
        consumer="Record review → Ask the model to choose evidence",
        input_semantics="A metadata value and the Record's current source-unit IDs.",
        output_semantics="Model-chosen source units, each checked deterministically.",
        authority_semantics="A suggestion stays advisory until the reviewer binds it.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["backend_validation", "source_provenance", "reviewer_approval"],
    ),
    PipelinePurposeSpec(
        purpose_id="vector_store_search",
        category="search",
        label="Vector Store search",
        description="Searches a vector store collection for matching Records.",
        consuming_feature="vector_store_search",
        consumer="Vector Stores → Search",
        input_semantics="A search query and metadata filters.",
        output_semantics="Matching Records with retrieval scores.",
        authority_semantics="Search results do not establish evidence, validate a research claim or generate a research response.",
        output_type="candidate_set",
        override_allowed=True,
        required_guarantees=["access_outside_pipeline"],
    ),
    PipelinePurposeSpec(
        purpose_id="metadata_precedents",
        category="metadata",
        label="Metadata precedents",
        description="Finds reviewed metadata precedents and corrections for the metadata-enrichment prompt.",
        consuming_feature="metadata_precedents",
        consumer="Corpus Builder → Metadata enrichment prompts",
        input_semantics="The Record text and the metadata fields being enriched.",
        output_semantics="A bounded packet of advisory reviewed precedents.",
        authority_semantics="Precedents guide the model; they never decide a value. The metadata schema keeps field eligibility and thresholds.",
        output_type="context_packet",
        override_allowed=True,
        required_guarantees=["reviewed_precedents_only"],
    ),
    PipelinePurposeSpec(
        purpose_id="metadata_prefill",
        category="metadata",
        label="Metadata pre-fill",
        description="Retrieves reviewed precedents that agree on a value so it can be offered as a pre-fill hint.",
        consuming_feature="metadata_prefill",
        consumer="Corpus Builder → Metadata pre-fill",
        input_semantics="Source spans of the Record being built.",
        output_semantics="Advisory pre-fill hints from reviewed precedents.",
        authority_semantics="Whether a value is pre-filled is DerridAI's domain policy, not this pipeline's; reviewed or present values are never overwritten.",
        output_type="candidate_set",
        override_allowed=True,
        required_guarantees=["reviewed_precedents_only"],
    ),
    PipelinePurposeSpec(
        purpose_id="corpus_metadata_enrichment",
        category="metadata",
        label="Metadata enrichment",
        description="Asks a chat model for one schema-derived metadata group at a time.",
        consuming_feature="corpus_metadata_enrichment",
        consumer="Corpus Builder → Metadata enrichment",
        input_semantics="A Record and one metadata group from the active schema.",
        output_semantics="Proposed metadata values, validated at the backend.",
        authority_semantics="Model values are proposals. Reconciliation, evidence binding, field-assertion authority and autofill stay DerridAI's domain code.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["backend_validation", "reviewer_approval"],
    ),
    PipelinePurposeSpec(
        purpose_id="claim_memory",
        category="memory",
        label="Claim memory",
        description="Finds earlier reviewer-validated claims similar to the current research question.",
        consuming_feature="claim_memory",
        consumer="Research workspace → Advisory memory",
        input_semantics="A research question and its owner.",
        output_semantics="Similar validated claims, rejoined with their current support state.",
        authority_semantics="Memory is advisory. A pipeline changes how eligible claims are searched, never which claims are eligible.",
        output_type="candidate_set",
        override_allowed=False,
        required_guarantees=["eligible_memory_only"],
    ),
    PipelinePurposeSpec(
        purpose_id="response_memory",
        category="memory",
        label="Response memory",
        description="Finds earlier Research responses similar to the current research question.",
        consuming_feature="response_memory",
        consumer="Research workspace → Advisory memory",
        input_semantics="A research question and its owner.",
        output_semantics="Similar eligible Research responses.",
        authority_semantics="Memory is advisory. A pipeline changes how eligible responses are searched, never which responses are eligible.",
        output_type="candidate_set",
        override_allowed=False,
        required_guarantees=["eligible_memory_only"],
    ),
    PipelinePurposeSpec(
        purpose_id="corpus_document_manifest",
        category="corpus",
        label="Document manifest",
        description="Asks a chat model once per analysis for a source-bound description of the document.",
        consuming_feature="corpus_document_manifest",
        consumer="Corpus Builder → Document analysis",
        input_semantics="Embedded file metadata and a sample of the whole document.",
        output_semantics="A proposed bibliography, language and main-text page range.",
        authority_semantics="Embedded metadata, confident deterministic inferences and reviewer-confirmed structure outrank the model's answer.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["backend_validation"],
    ),
    PipelinePurposeSpec(
        purpose_id="corpus_segmentation",
        category="corpus",
        label="Segmentation",
        description="Asks a chat model closed-choice questions about ambiguous or suspicious Record boundaries.",
        consuming_feature="corpus_segmentation",
        consumer="Corpus Builder → Segmentation",
        input_semantics="An ambiguous boundary or suspicious Record seam, with its source blocks.",
        output_semantics="A proposed boundary decision, checked deterministically.",
        authority_semantics="A failed, omitted or low-confidence answer keeps the boundary where it is.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["backend_validation", "text_conservation"],
    ),
    PipelinePurposeSpec(
        purpose_id="corpus_text_touchup",
        category="corpus",
        label="Text touch-up",
        description="Asks a chat model to propose cleaned-up text for one Record.",
        consuming_feature="corpus_text_touchup",
        consumer="Record review and metadata enrichment → Text touch-up",
        input_semantics="One Record's text.",
        output_semantics="A proposed text revision, checked against the source text.",
        authority_semantics="A touch-up is only a proposal. Reviewed text changes only when a person approves it.",
        output_type="model_output",
        override_allowed=True,
        required_guarantees=["backend_validation", "reviewer_approval"],
    ),
)


class PurposeRegistry:
    """Lookup over the code-owned purpose contracts."""

    def __init__(self, specs: tuple[PipelinePurposeSpec, ...] = PIPELINE_PURPOSES) -> None:
        self._specs: dict[str, PipelinePurposeSpec] = {}
        self._by_feature: dict[str, PipelinePurposeSpec] = {}
        for spec in specs:
            if spec.purpose_id in self._specs:
                raise ValueError(f"Duplicate pipeline purpose: {spec.purpose_id}")
            if spec.consuming_feature in self._by_feature:
                raise ValueError(f"Duplicate consuming feature: {spec.consuming_feature}")
            self._specs[spec.purpose_id] = spec
            self._by_feature[spec.consuming_feature] = spec

    def get(self, purpose_id: str) -> PipelinePurposeSpec | None:
        return self._specs.get(str(purpose_id))

    def for_feature(self, feature: str) -> PipelinePurposeSpec | None:
        return self._by_feature.get(str(feature))

    def list(self) -> list[PipelinePurposeSpec]:
        return list(self._specs.values())


purpose_registry = PurposeRegistry()


def _vocabulary(prefix: str, terms: tuple[VocabularyTerm, ...]) -> list[dict[str, Any]]:
    return [
        {
            **term.model_dump(mode="json"),
            "label_key": f"pipelines.{prefix}.{term.id}.label",
            "description_key": f"pipelines.{prefix}.{term.id}.description",
        }
        for term in terms
    ]


def serialize_purpose(spec: PipelinePurposeSpec) -> dict[str, Any]:
    stem = f"pipelines.purpose.{_key_stem(spec.purpose_id)}"
    return {
        **spec.model_dump(mode="json"),
        "label_key": f"{stem}.label",
        "description_key": f"{stem}.description",
        "consumer_key": f"{stem}.consumer",
        "input_key": f"{stem}.input",
        "output_key": f"{stem}.output",
        "authority_key": f"{stem}.authority",
    }


def workflow_vocabulary() -> dict[str, list[dict[str, Any]]]:
    """Closed vocabularies the catalog serves so clients need no semantic tables."""

    return {
        "categories": _vocabulary("workflow_category", WORKFLOW_CATEGORIES),
        "guarantees": _vocabulary("guarantee", WORKFLOW_GUARANTEES),
        "phases": _vocabulary("phase", WORKFLOW_PHASES),
        "scholarly_effects": _vocabulary("scholarly_effect", SCHOLARLY_EFFECTS),
        "effect_notes": _vocabulary("effect_note", EFFECT_NOTES),
    }
