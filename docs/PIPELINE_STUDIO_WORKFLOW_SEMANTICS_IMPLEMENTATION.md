# Pipeline Studio Workflow Semantics Implementation Instructions

**Repository:** `ajschlosser/DerridAI`  
**Target branch:** `master`  
**Scope:** Pipeline Studio information architecture, domain contracts, workflow semantics, strategy semantics, editor guidance, execution history, operations, accessibility, i18n, tests, and documentation.

## Objective

Implement a substantial Pipeline Studio information-architecture and UX improvement. The goal is to make it immediately clear what each pipeline is for—Research, Evidence, Search, Metadata, Memory, Corpus processing, etc.—while preserving the important distinction between the purpose of an entire pipeline and the computational strategies used by individual stages.

Do not implement this as a frontend-only labeling exercise. The current opacity exposes a missing domain abstraction. Add the appropriate backend/domain contracts and make the frontend consume them.

Before changing code, update your local view of `master`, inspect the current implementation, open PRs that touch Pipeline Studio/pipelines, and the relevant requirements/docs. Do not overwrite newer work or reintroduce superseded patterns.

Relevant existing areas include at least:

- `api/app/pipelines/models.py`
- `api/app/pipelines/registry.py`
- `api/app/pipelines/defaults.py`
- `api/app/pipelines/service.py`
- `api/app/pipelines/manager.py`
- `api/app/routers/pipelines.py`
- `web/src/types/pipelines.ts`
- `web/src/domain/pipelinePresentation.ts`
- `web/src/views/PipelineStudioView.vue`
- `web/src/components/system-data/SystemDataPipelines.vue`
- `web/src/components/pipelines/PipelineDefinitionBrowser.vue`
- `web/src/components/pipelines/PipelineDefinitionDetail.vue`
- `web/src/components/pipelines/PipelineDefinitionEditor.vue`
- `web/src/components/pipelines/PipelineStageEditor.vue`
- `web/src/components/pipelines/PipelineStageList.vue`
- `web/src/components/pipelines/PipelineGraphDiagram.vue`
- `web/src/components/pipelines/PipelineExecutionHistory.vue`
- `web/src/components/pipelines/PipelineOperationsSummary.vue`
- associated Storybook stories and frontend/backend tests
- `docs/requirements/PIPELINES_AND_SYSTEM_DATA.md`
- `docs/PIPELINE_MIGRATION_HANDOFF.md`
- `docs/ARCHITECTURE.md`
- `docs/USER_GUIDE.md`
- cELF specification/reference material where relevant

Preserve the repository's existing requirements around WCAG 2.2 AA, i18n, Canadian French parity, semantic tokens, dark mode, high contrast, forced colors, keyboard support, Storybook coverage, Prettier, human-readable code, and decomposition of large UI units.

## Core conceptual rule

Make this distinction explicit throughout the implementation:

> **Pipeline purpose / workflow = what the entire pipeline is for.**  
> **Stage strategy / operation = how an individual step performs part of that work.**

Do **not** classify strategies themselves as exclusively “Research”, “Evidence”, or “Search”.

For example:

- semantic retrieval can appear in Research, Evidence, Search, Metadata, or Memory;
- a CrossEncoder may rerank candidates in several workflows;
- MMR may diversify several kinds of result;
- those operations do not become “evidence strategies” simply because an Evidence pipeline uses them.

Pipeline Studio must make the two dimensions separately understandable:

**Workflow semantics**

- Research
- Evidence
- Search
- Metadata
- Memory
- Corpus processing

**Computational mechanics**

- Query preparation
- Retrieval / candidate generation
- Filtering
- Normalization
- Fusion
- Reranking
- Support/provenance validation
- Diversity
- Selection
- Context packing
- Generation
- Evaluation

This distinction is important to DerridAI's scholarly architecture. Retrieval relevance does not itself create evidence, scholarly support, or authority.

## 1. Introduce a first-class pipeline purpose / workflow contract

The current backend has `PipelineDefinition.purpose`, but the semantics associated with a purpose are scattered. In particular, inspect the existing `featureForPurpose()` mapping in the Pipeline Studio frontend. This should not remain a manually maintained frontend mapping.

Introduce a server-owned registry/specification for supported pipeline purposes.

Use an abstraction along the lines of:

```text
PipelinePurposeSpec
  id
  category
  label
  description
  consuming_feature
  input_semantics
  output_semantics
  authority_semantics
  assignment_scope
  override_allowed
  required_guarantees
  optional UI/i18n keys as appropriate
```

Names may differ if a cleaner design fits existing repository conventions, but preserve the semantics.

Examples conceptually:

```text
research
  category: research
  consuming feature: research
  input: research question + retrieval/corpus scope
  output: generated research response / claims / citations
  authority semantics:
    retrieval and generation remain evidence-bound and provenance-aware

evidence_suggestion
  category: evidence
  consuming feature: evidence_suggestion.reviewer
  input: field/value/proposition + current source scope
  output: advisory source candidates
  authority semantics:
    ranking alone never makes a candidate admissible evidence
  required guarantees:
    direct support
    source provenance

evidence_recovery
  category: evidence
  output: advisory recovered evidence candidates

vector_store_search
  category: search
  output: matching Records / retrieval results
  authority semantics:
    search results do not constitute evidence or generated research claims

metadata_precedents
  category: metadata
  output: advisory reviewed precedents

claim_memory
response_memory
  category: memory
```

Classify metadata prefill/enrichment and segmentation/manifest/touch-up/reviewer workflows according to their actual current application role. Do not invent semantics. Derive them from the current adapters, assignments, documentation, requirements, and tests.

Expose the purpose registry through the pipeline catalog/API so the frontend receives authoritative purpose metadata together with strategies, definitions, and assignments.

Remove or replace frontend hard-coded purpose→feature routing wherever the backend contract can supply it.

The backend must remain authoritative for:

- valid purpose IDs;
- consuming feature assignment;
- category;
- compatibility/assignment semantics;
- required workflow guarantees.

Do not let translated display strings become identifiers.

## 2. Add a strategy scholarly / epistemic effect dimension

Current strategies already expose useful metadata such as:

- family;
- input/output type;
- deterministic vs learned/model-based;
- whether they invoke an LLM;
- capabilities;
- configuration schema.

Add a separate semantic property describing what scholarly effect the strategy may have.

Do not overload `family` with this.

Use a small controlled vocabulary, for example:

```text
none
advisory
eligibility_gate
provenance_gate
transformation
generation
evaluation
```

Refine the names if the repository suggests better terminology.

The purpose is to support statements such as:

- Chroma semantic similarity
  - computational role: candidate generation
  - scholarly effect: none/advisory
  - meaning: ranks or retrieves candidates; does not establish support
- Cross-encoder reranker
  - computational role: rerank
  - scholarly effect: none/advisory
  - meaning: changes relevance ordering; does not establish support
- MMR
  - computational role: diversity
  - scholarly effect: none/advisory
  - meaning: balances relevance and diversity
- Evidence support validator
  - computational role: support validation
  - scholarly effect: eligibility gate
- Provenance validator
  - computational role: support validation
  - scholarly effect: provenance gate
- Answer generation
  - computational role: LLM
  - scholarly effect: generation

Do not imply that `eligibility_gate` means a strategy creates human authority. Preserve the existing distinction between computational validation, evidence admissibility, provenance, reviewer authority, and final scholarly authority.

Add tests ensuring the registry can be serialized and consumed safely.

## 3. Reorganize Pipeline Studio around “Used for”

The present flat list plus Purpose filter does not make workflow differences sufficiently prominent.

Change the user-facing conceptual label from the relatively technical “Purpose” to something clearer such as **Used for** or **Workflow**. Keep `purpose` as the technical backend concept.

The Pipeline browser should support primary high-level workflow categories such as:

- All
- Research
- Evidence
- Search
- Metadata
- Memory
- Corpus

Use the backend purpose registry as the source of truth.

Do not hard-code which raw purpose strings belong to those categories in the frontend.

A user should be able to determine at a glance whether:

- a pipeline generates Research output;
- retrieves Evidence candidates;
- performs Vector Store Search;
- finds Metadata precedents;
- searches Research memory;
- performs Corpus processing.

Retain precise lower-level purpose labels beneath the category. For example, two separate Evidence purposes should remain distinguishable:

```text
Evidence
  Reviewer evidence suggestion

Evidence
  Evidence recovery
```

Preserve filtering/searching and canonical route behavior.

## 4. Add a “What this pipeline does” contract panel

Before the graph/details of a selected pipeline, add a concise workflow-contract summary driven by the purpose metadata.

It should communicate, in plain language:

- Used for / workflow category;
- specific pipeline purpose;
- where in DerridAI it is consumed;
- expected input;
- expected output;
- scholarly/authority implications;
- important required guarantees;
- active assignment status;
- exact version where appropriate.

Examples of the desired style:

**Reviewer evidence**

```text
Reviewer evidence suggestion
Used by: Record Review → Evidence suggestions
Input: metadata field/value and current source scope
Output: advisory source candidates
Authority: relevance ranking alone does not make a candidate evidence
Required guarantees: direct support and source provenance
```

**Research**

```text
Research
Used by: Research Workspace
Input: research question and corpus/retrieval scope
Output: generated research response with evidence-bound claims/citations
Includes retrieval, ranking, provenance checks, evidence packing,
generation, citation binding, and optional evaluation.
```

**Vector Store Search**

```text
Vector Store search
Used by: Vector Store search
Input: search query and filters
Output: matching Records and retrieval scores
Does not establish evidence, validate a research claim, or generate a
research response.
```

Do not hard-code these paragraphs directly in the Vue component. They should derive from purpose registry metadata plus localized presentation strings where appropriate.

Keep the presentation concise and enterprise-grade rather than turning the panel into documentation prose.

## 5. Add a first-class Strategies workspace to Pipeline Studio

Pipeline Studio currently separates:

```text
Pipelines
Executions
Operations
```

Add:

```text
Strategies
```

Result:

```text
Pipelines
Strategies
Executions
Operations
```

This view should make the server strategy registry understandable on its own.

Provide search/filter capabilities appropriate for:

- strategy family;
- deterministic / learned / generative;
- required capability;
- scholarly/epistemic effect;
- optionally workflow usage.

For each strategy, show a readable summary such as:

```text
Semantic similarity retrieval
retrieve.chroma_similarity

Family: Candidate retrieval
Input → output: Query → candidate set
Computation: Learned model
Requires: embeddings, Chroma
Scholarly effect: Candidate ranking only
Used by: Research, Search, etc.

Embeds the query and retrieves nearby candidates. Similarity does not
establish direct support or evidence authority.
```

And:

```text
Evidence support validator
validate.evidence_support

Family: Support validation
Scholarly effect: Evidence eligibility gate
Used by: reviewer evidence / recovery workflows
```

Allow the user to discover which saved/built-in pipelines use a strategy.

Do not duplicate the registry manually in frontend code.

Use progressive disclosure. Human-readable meaning should come before raw IDs/config schema, but expert technical details should remain inspectable.

## 6. Make stage cards explain their effect, not just their implementation

Update `PipelineStageList` and graph node presentation so stages communicate their practical role.

Existing family / deterministic / LLM metadata should remain.

Add concise semantic annotations based on the strategy's scholarly-effect metadata.

Especially for retrieval/ranking stages used in Evidence workflows, clearly communicate statements such as:

- **Produces candidates — not evidence**
- **Relevance ranking only — does not establish support**
- **Diversity selection — does not establish support**

For support/provenance stages:

- **Evidence eligibility gate**
- **Provenance gate**

For LLM generation:

- **Generates model output from supplied context**

Do not clutter every node with a paragraph. Use concise badges/secondary copy and accessible tooltips.

The UI must not imply that an embedding score, CrossEncoder score, MMR score, or retrieval assignment creates scholarly truth.

## 7. Improve the graph’s conceptual readability

Preserve the existing accessible relational graph behavior, normal/fallback edges, graph validation, and execution overlays.

Improve the visual semantics so users can understand a pipeline as a workflow rather than merely a graph of implementation IDs.

Where feasible, visually identify broad functional phases such as:

- Prepare
- Find
- Rank
- Validate
- Select / Pack
- Generate
- Bind / Evaluate

Map these from registered stage families rather than maintaining an unrelated frontend taxonomy.

Do not force every pipeline through every phase.

Examples:

**Research**

```text
Prepare question
  ↓
Find candidates
  ↓
Merge / rank
  ↓
Validate provenance
  ↓
Pack evidence
  ↓
Generate
  ↓
Bind citations
  ↓
Evaluate
```

**Evidence**

```text
Build evidence query
  ↓
Find candidates
  ↓
Validate direct support
  ↓
Validate provenance
  ↓
Select advisory suggestions
```

**Search**

```text
Prepare query
  ↓
Find candidates
  ↓
Normalize / fuse
  ↓
Rank
  ↓
Return Records
```

Do not invent artificial nodes. This is presentation over the actual graph, not a second executable pipeline model.

Fallback edges must remain clearly distinct.

## 8. Make the pipeline editor purpose-aware

The editor currently exposes the registered strategy list grouped primarily by family.

Improve this so the current pipeline purpose provides context.

Requirements:

- visibly show the pipeline's **Used for** / purpose near the beginning of the editor;
- explain that cloning/versioning preserves that purpose;
- do not make a cloned Evidence pipeline appear to be an arbitrary graph that can later become a Research pipeline;
- use backend-provided compatibility/runtime metadata to distinguish strategies appropriate for the workflow from unsupported or advanced options.

A strategy picker should ideally present:

```text
Recommended / supported for this workflow

Other compatible operations

Unsupported for this workflow
```

If an operation is unsupported by the purpose's runtime adapter, either:

- disable it with an accessible explanation; or
- place it behind an explicit expert/advanced affordance if saving inspect-only graphs is an intentional supported feature.

Do not simply hide every unsupported strategy if the existing system deliberately permits structurally valid inspect-only graphs.

Respect the existing difference between:

- graph structural validity;
- current runtime executability.

Do not create another frontend-only compatibility table. Compatibility information should be produced from backend adapter/registry logic.

Examples of good disabled reasons:

```text
Answer generation is not supported by the Reviewer Evidence adapter.

This operation produces a model response, but this workflow's output
contract is a candidate set.
```

Keep validation as the final authoritative check, but provide earlier guidance.

## 9. Purpose must be visible during cloning/versioning

The cloned-pipeline editor should prominently show something equivalent to:

```text
Used for: Reviewer evidence suggestion
```

and explain:

```text
This new version remains a Reviewer Evidence pipeline. To create a pipeline
for another workflow, begin from a pipeline for that workflow instead.
```

Do not make `purpose` casually editable unless there is an established, validated product requirement for changing it.

Preserve immutable saved versions and the current server-authoritative version allocation behavior.

## 10. Apply the same workflow semantics to Executions

Execution history should not require users to interpret raw feature identifiers such as `evidence_suggestion.reviewer` as the primary label.

Render the human workflow first, for example:

```text
Evidence
Reviewer evidence suggestion
Evidence suggestion — reviewer support-gated v2
```

Keep feature IDs, pipeline IDs, version, hash, stage IDs, and other audit details available as secondary/expert information.

Execution filtering should allow meaningful filtering by workflow/purpose/category, while preserving existing feature/pipeline/status/owner/search behavior and URL-addressable state.

Do not weaken trace reproducibility.

## 11. Apply the same model to Operations

Operational telemetry should become understandable at two levels:

```text
Workflow
  Research
  Evidence
  Search
  Metadata
  Memory
  Corpus
```

and:

```text
Strategy
  individual computational operations
```

Maintain the existing rule that operational metrics describe computational health, not scholarly validity.

For example:

```text
Evidence workflows
  runs
  failures
  fallbacks
  latency
```

and separately:

```text
Cross-encoder reranker
  executions
  timeout rate
  fallback count
  latency
```

Do not infer that a workflow with lower latency or fewer failures produces better scholarship.

## 12. Remove frontend semantic hard-coding where possible

Audit the pipeline frontend for hard-coded semantic maps.

In particular, replace purpose/feature/category/compatibility mappings that belong to backend domain contracts.

Frontend code may still provide localized presentation, icons, layout decisions, and fallback text. It should not independently define the application's pipeline semantics.

Keep deterministic transformations and presentation helpers focused and testable.

## 13. i18n

All added user-facing copy must use the existing i18n architecture.

Maintain full en-US / fr-CA parity.

Do not put untranslated domain descriptions into the UI if the existing catalog uses label/description keys.

Extend the registry/API types to carry translation keys where that is consistent with existing strategy handling.

Test long strings and French layouts.

Avoid concatenating sentence fragments that translate badly.

## 14. Accessibility

Maintain WCAG 2.2 AA expectations.

At minimum:

- all tabs keyboard operable;
- workflow filters accessible by name and state;
- graph semantics remain available independently of color;
- strategy badges do not rely on color alone;
- disabled strategy choices explain why they are disabled;
- tooltips work with keyboard/focus, not hover only;
- all new status/purpose/effect badges remain comprehensible to screen readers;
- responsive/mobile overflow is intentional;
- forced-colors/high-contrast modes remain usable;
- no inaccessible nested interactive controls.

Run existing axe/Playwright coverage and add targeted coverage for new components/interactions.

## 15. Design / UX quality

Treat this as a professional 2026 enterprise research application.

Avoid:

- huge colored banners;
- excessive pills;
- decorative gradients;
- repeating the same information in several adjacent cards;
- making technical IDs visually dominant;
- tooltip-only essential information;
- dense settings-wall layouts;
- treating every semantic distinction as a different color.

Prefer:

- strong information hierarchy;
- concise labels;
- progressive disclosure;
- aligned data/value presentation;
- readable empty states;
- subtle but distinct workflow/category signifiers;
- plain-language summaries with technical detail available on demand;
- shared design-system primitives and tokens.

Create or reuse shared components where they eliminate real duplication. Do not make a giant all-purpose pipeline card component with dozens of modes.

## 16. Tests

Add comprehensive tests.

Backend coverage should include at least:

- purpose registry uniqueness and serialization;
- every built-in pipeline refers to a registered purpose;
- purpose→consuming-feature mapping is valid;
- assignment resolution still behaves correctly;
- no frontend-dependent semantic mapping is needed;
- strategy scholarly-effect values validate;
- strategy registry serialization includes the new fields;
- purpose compatibility/runtime metadata is deterministic;
- built-in pipelines remain valid;
- existing mandatory scholarly/provenance gates remain enforced.

Frontend unit/integration coverage should include:

- workflow categories are rendered from catalog metadata;
- filtering by workflow;
- precise purpose remains visible;
- contract panel renders input/output/authority semantics;
- Strategies tab;
- strategy filtering;
- pipelines using a strategy are discoverable;
- epistemic/scholarly effect labels;
- candidate-generating Evidence stages communicate that candidates are not evidence;
- purpose-aware strategy picker;
- unsupported-strategy explanation;
- clone editor retains/shows purpose;
- execution rows use workflow/purpose labels;
- operations aggregate/present workflow semantics correctly;
- route state remains stable/shareable where appropriate;
- French strings;
- keyboard behavior;
- empty/loading/error states.

Add/update Storybook stories for materially changed or new presentational components.

Do not rely primarily on snapshots. Prefer behavior and semantic assertions.

## 17. Documentation / requirements

Update the relevant repository documentation after implementation.

At minimum evaluate changes needed in:

- `docs/requirements/PIPELINES_AND_SYSTEM_DATA.md`
- `docs/PIPELINE_MIGRATION_HANDOFF.md`
- `docs/ARCHITECTURE.md`
- `docs/USER_GUIDE.md`

Document the distinction explicitly:

> Pipeline purpose describes the application/research workflow contract.  
> Strategy family describes the computational role of a stage.  
> Scholarly/epistemic effect describes what, if anything, that operation establishes with respect to evidence/support/provenance.

Also document that a single strategy may be reused across several pipeline purposes.

Do not imply that computational relevance equals evidence or authority.

If the normative cELF specification itself does not require changes, do not edit normative text merely to match the UI. Keep implementation documentation and normative specification appropriately separated.

## 18. Preserve existing invariants

Do not weaken any of these existing behaviors:

- saved pipeline versions remain immutable;
- assignments point to exact versions;
- traces bind to exact pipeline/version/hash;
- runtime support is separate from structural graph validity;
- server-owned strategies are the only executable operations;
- user-authored pipeline definitions cannot inject executable code;
- fallback edges remain explicit;
- support/provenance gates remain non-bypassable where required;
- pipeline metrics remain operational telemetry, not scholarly validity;
- retrieval scores remain distinct from support/provenance judgments;
- researcher permissions, source visibility, ownership and review authority remain outside tunable pipeline configuration where currently required;
- pipeline traces do not start storing source text, secrets, prompt bodies, sealed reviewer content, or other prohibited material.

## 19. Refactoring expectations

While implementing this feature, improve nearby architecture where justified.

Specifically:

- remove duplicated semantic maps;
- keep Vue components focused;
- move domain derivation into typed domain helpers;
- avoid growing `SystemDataPipelines.vue` into another monolith;
- split new Strategies/workflow surfaces into focused components;
- keep presentation functions in an appropriate domain/presentation module;
- preserve existing selectors/test hooks where practical;
- add comments only where the reason or invariant is non-obvious;
- run Prettier and repository lint/type checks.

Do not perform unrelated broad rewrites.

## 20. Acceptance scenarios

After the change, a researcher or administrator unfamiliar with internal strategy IDs should be able to perform these tasks without reading source code.

### Scenario A

Open Pipeline Studio and answer:

> What pipelines are responsible for Evidence?

The user should immediately see the Evidence workflow/category and its distinct Evidence Suggestion / Evidence Recovery pipelines.

### Scenario B

Open `research.current` and answer:

> Does this pipeline merely search, or does it produce a research response?

The workflow contract must make clear that it is a Research pipeline and includes generation/output semantics.

### Scenario C

Open `store_search.similarity` and answer:

> Does this create evidence?

The UI must clearly say that it produces search results/candidates and does not itself establish evidence or research claims.

### Scenario D

Inspect CrossEncoder reranking and answer:

> Does a high CrossEncoder score mean this passage directly supports my claim?

The UI must clearly communicate that CrossEncoder measures/ranks relevance and does not establish direct support.

### Scenario E

Inspect `validate.evidence_support` and understand that this is materially different from retrieval/reranking because it participates in evidence eligibility/support validation.

### Scenario F

Clone a Reviewer Evidence pipeline.

The editor should clearly say that the new version remains a Reviewer Evidence pipeline and should prioritize/support operations compatible with that workflow.

### Scenario G

Open execution history for an Evidence run.

The UI should say **Evidence / Reviewer evidence suggestion** prominently and expose the raw feature ID only as technical detail.

### Scenario H

Open Strategies and search for “semantic”.

The user should see semantic retrieval strategies, their computational family, input/output type, model/capability requirements, scholarly effect, and which workflows/pipelines use them.

## 21. Implementation process

Work from current `master`.

Before writing code:

1. Inspect current open PRs touching Pipeline Studio, pipeline contracts, navigation, System Data, graph rendering, or i18n.
2. Read the relevant current requirements and migration handoff.
3. Identify all current raw `purpose` strings and active assignments.
4. Identify every place frontend code maps purpose/feature semantics manually.
5. Identify adapter/runtime compatibility logic that can supply purpose-aware editor guidance.
6. Write a short implementation plan before changing code.

Then implement in coherent commits. Keep commits reasonably small and descriptive.

Suggested sequencing:

1. Backend purpose/strategy semantic contracts
2. API/catalog serialization and tests
3. TypeScript types/domain presentation
4. Pipeline workflow browser + contract panel
5. Strategies workspace
6. Stage semantic/effect presentation
7. Purpose-aware editor
8. Executions/Operations integration
9. i18n + accessibility + Storybook
10. Documentation and final regression pass

Run the full relevant quality gates before finishing, not only the new unit tests.

At minimum run the repository's formatting, backend lint/type/test, frontend lint/static/unit, E2E, and accessibility checks that CI will run.

Do not declare completion with failing tests.

## 22. Final report

When finished, report:

- branch name;
- commits created;
- architecture changes;
- backend contract changes;
- removed frontend hard-coding;
- UI components added/changed;
- i18n work;
- accessibility work;
- tests added;
- documentation changed;
- commands/test suites run and their results;
- any deliberate limitations or follow-up work;
- any current open PR conflicts you found.

The result should make Pipeline Studio understandable in terms of both:

> **What is this workflow for?**

and

> **How does it perform that workflow?**

without collapsing retrieval, evidence, and research into the same concept.
