# Pipeline Studio Remaining Migration Handoff

**Repository:** `ajschlosser/DerridAI`  
**Prepared:** 2026-09-29  
**Authoritative master at preparation:** `cb4654e71f0489c21f04566797c612af76170904`  
**Pipeline benchmark work:** PR #286 merged as `4694f38f9333117121f338791aae52be088abb99`  
**Primary background:** `docs/RETRIEVAL_RERANKING_LLM_AUDIT.md` and `docs/PIPELINE_MIGRATION_HANDOFF.md`

This handoff is narrowly about the remaining production paths that are **not yet controlled by Pipeline Studio**. It is not a general architecture document and it does not reopen already-migrated Research, reviewer-evidence, metadata-precedent, claim-memory, or response-memory work.

The short version is:

> Pipeline Studio now controls several important scholarly retrieval chains, but it still does not control every production retrieval, reranking, evidence-recovery, Corpus Builder LLM, record-touchup, grading, or utility-model path. The remaining work is to migrate the scholarly/configurable paths and explicitly classify true operational utilities as documented exceptions rather than forcing every model call through the scholarly pipeline system.

---

## 1. What “controlled by Pipeline Studio” means

A feature should only be described as controlled by Pipeline Studio when all of the following are true:

1. the feature resolves a named assignment through the pipeline manager;
2. the assignment points to an immutable pipeline ID/version;
3. the resolved definition is validated against the server-owned strategy registry;
4. the production runtime compiles or executes the resolved definition rather than merely displaying it;
5. stage configuration in the resolved definition is authoritative for the computational behavior it claims to configure;
6. configured fallback/timeout/unavailable/error edges are respected by the runtime;
7. the execution binds to the exact resolved pipeline hash/snapshot;
8. safe stage telemetry can show what actually ran;
9. the UI can identify the configured chain before execution where that matters;
10. the result can be audited after execution without treating pipeline telemetry as scholarly authority.

A feature is **not** considered migrated merely because:

- a matching strategy exists in the registry;
- a built-in pipeline definition resembles the feature;
- Pipeline Studio can display a plausible graph;
- a helper used by the feature is also used from a migrated pipeline;
- the feature emits some local telemetry;
- the user can tune related settings elsewhere.

The production call path itself must resolve and execute the pipeline.

---

## 2. What Pipeline Studio controls now

Current built-in assignments on master are:

| Feature | Assigned pipeline | Runtime status |
| --- | --- | --- |
| Research | `research.current@1` | controlled |
| Reviewer evidence suggestion | `evidence.reviewer.current@2` | controlled |
| Metadata precedents | `metadata.precedents.current@1` | controlled |
| Validated claim memory | `memory.claim.current@1` | controlled |
| Prior response memory | `memory.response.current@1` | controlled |

Research comparison and fixed-case benchmarking also execute saved Research pipeline versions through the same runtime, but they are evaluation modes over the Research pipeline rather than additional feature assignments.

The important distinction is that these five assignments do **not** imply that every use of Chroma, every CrossEncoder call, every evidence-recovery path, or every LLM request is pipeline-controlled.

---

## 3. Governing invariant for all remaining migration work

The migration must preserve the division between computational configuration and scholarly authority.

Pipeline stages may:

- transform a query;
- generate candidates;
- rank candidates;
- fuse ranks;
- rerank;
- apply diversity;
- select bounded candidates;
- pack context;
- invoke a model;
- emit structured proposals;
- evaluate generated output.

Pipeline stages must not silently become authoritative for:

- cELF provenance;
- source-document or source-unit identity;
- FieldAssertion ownership;
- reviewer acceptance/rejection;
- evidence support bindings;
- publication blockers;
- schema-owned eligibility rules;
- validated-claim authority;
- response-grade eligibility;
- current-record revision identity;
- document/corpus mutation rules that are supposed to remain deterministic.

The successful migration pattern so far is:

```text
domain-owned eligibility / authority
    -> pipeline-controlled computation
    -> deterministic validation / provenance gate
    -> bounded result
    -> domain-owned persistence/review
```

Keep using that pattern.

---

# Part I — Confirmed remaining retrieval and evidence paths

## 4. General Vector Stores / database search

### Current production path

Primary entry point:

- `api/app/routers/stores.py`
- `POST /api/stores/{store_name}/search`

The route still branches directly on `body.mode` and calls ChromaStore methods:

- `filter_search()`
- `keyword_search()`
- `lexical_search()`
- `hybrid_search()`
- `mmr_search()`
- `search()`

The route does not resolve a Pipeline Studio assignment before choosing the retrieval algorithm.

That means the user-visible Vector Stores/search workspace still exposes retrieval “modes” whose actual computational chains are hard-wired in route/store code rather than represented as assigned, versioned pipelines.

### Why this matters

This is one of the clearest remaining violations of the original audit criterion:

> Every vector-search feature should resolve through a named/versioned pipeline.

Research may use the same underlying Chroma helpers, but Research being migrated does not make the general store-search endpoint migrated.

### Recommended target

Add a separate pipeline purpose/feature family for general store search. A provisional shape could be:

- feature: `vector_store_search`
- scope: system by default, optionally store-specific later
- built-in definitions for similarity, lexical, hybrid, MMR, keyword/filter as appropriate

Do **not** simply turn the existing `mode` string into a fake pipeline ID. The runtime should resolve a real immutable definition and execute it.

A reasonable first implementation can preserve the existing UI modes as shortcuts that select built-in pipeline versions. Later, the UI can expose “Use assigned pipeline” plus explicit saved variants.

### Suggested strategy mapping

Existing registry strategies should be reused where semantics match. Add only what is missing.

Potential stages:

- query passthrough;
- deterministic filter/keyword candidate generation;
- dense Chroma retrieval;
- lexical BM25 retrieval;
- RRF fusion;
- MMR;
- top-K selection.

Keep filter authorization and researcher text-access policy outside the graph.

### Required trace data

At minimum:

- pipeline ID/version/hash;
- collection/storage identity;
- query mode/entry stage;
- candidate counts;
- distance/relevance semantics;
- RRF score where used;
- MMR score where used;
- filters applied, but without leaking restricted values;
- elapsed time;
- fallback/unavailable status.

### Do not migrate these as tunable scholarly semantics

- permission checks;
- researcher text sanitization;
- collection visibility;
- collection write policy.

Those remain route/domain authority.

---

## 5. Metadata prefill from reviewed precedent

### Current production path

Primary file:

- `api/app/memory_prefill.py`

The implementation still performs its own retrieval and decision flow. It:

- creates/uses `SourceEmbeddingProjection`;
- queries the metadata exemplar Chroma collection directly;
- batches vectors into `collection.query(query_embeddings=...)`;
- uses local constants such as:
  - `MIN_AGREE = 2`
  - `OBVIOUS_SIMILARITY = 0.88`
  - `HINT_SIMILARITY = 0.72`
  - `FETCH_K = 8`;
- groups prior reviewed support by field/value;
- decides whether a result becomes a hint or prefill candidate according to field policy.

There is no Pipeline Studio assignment resolution in this path.

### Important distinction

This is **not** the same workflow as `metadata_precedents.current@1`.

The migrated metadata-precedent pipeline builds a bounded precedent packet for model/editorial use. Metadata prefill is a separate operation that uses prior reviewed exemplars to propose or prefill field values.

Do not merge these concepts merely because both use the metadata exemplar projection.

### Recommended target

Add a pipeline-controlled computational layer for **candidate retrieval and scoring**, while keeping authoritative prefill policy outside the graph.

A provisional purpose could be:

- `metadata_prefill`

The pipeline may control:

- candidate fetch depth;
- semantic retrieval;
- optional lexical fallback;
- score normalization;
- candidate aggregation inputs;
- bounded candidate selection.

The pipeline should **not** own:

- whether a field is eligible for prefill;
- whether multi-record agreement is sufficient;
- whether a value is schema-valid;
- whether a hint becomes a FieldAssertion;
- reviewer state;
- source/provenance requirements.

Those are domain policy.

### Migration note on current constants

Not every constant should automatically become an editable stage parameter.

Classify each current threshold first:

- computational retrieval tuning -> pipeline config;
- editorial/schema authority -> domain policy;
- safety/resource bound -> server-enforced cap.

For example, `FETCH_K` is an obvious pipeline parameter. `MIN_AGREE` may be a stronger candidate for domain policy because it controls the evidentiary basis for using precedent, not merely retrieval mechanics.

---

## 6. Precedent evidence remapping

### Current production path

Primary files:

- `api/app/metadata_precedents_cache.py`
- `api/app/evidence_suggestions.py`

The cache calls `rank_blocks_for_texts()` to map prior reviewed evidence text onto source blocks in the current Record.

Current behavior is:

- embedding cosine similarity when an embedder is available;
- conservative token-overlap fallback otherwise;
- bounded picks;
- no Pipeline Studio assignment resolution.

### Why this remains separate from metadata precedents

The metadata-precedent pipeline determines which reviewed precedents to surface.

Evidence remapping answers a different question:

> Which current source units best correspond to the evidence text attached to the selected precedent?

That current-record source binding is a distinct computational workflow and must remain constrained by the current Record’s actual source units.

### Recommended target

A provisional purpose:

- `precedent_evidence_remap`

The pipeline may control:

- semantic candidate generation;
- lexical fallback;
- bounded top-K;
- minimum mapping relevance.

The pipeline must not be allowed to:

- map to a source unit outside the current Record/document;
- create reviewed evidence;
- bypass source-unit identity checks;
- carry an old precedent’s source identity forward as if it were current provenance.

The final remap remains an advisory current-record correspondence until accepted by the appropriate domain logic.

---

## 7. Automatic missing-evidence recovery during enrichment

### Current production path

Primary files:

- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/corpus_review_actions.py`
- `api/app/evidence_suggestions.py`

Reviewer-facing “suggest evidence” is migrated through:

- `evidence_suggestion.reviewer`
- `evidence.reviewer.current@2`

However, the automatic/advisory missing-evidence recovery path still has direct calls into the legacy evidence cascade.

The enrichment path still constructs a `SourceEmbeddingProjection` and can invoke a direct `_chat_json()` closed-choice evidence fallback.

The review-side advisory fill helper also calls `suggest_evidence_cascade()` directly for pending fields.

That direct helper can still reach:

- lexical support;
- semantic cosine candidates;
- the shared CrossEncoder;
- MMR;
- optional LLM closed-choice selection.

Therefore, one of the remaining direct CrossEncoder paths is still outside a resolved pipeline when it is reached through this cascade.

### Why this is high priority

This path is close to a migrated feature but not actually controlled by it. That creates architectural ambiguity:

- reviewer evidence suggestions are support/provenance-gated by the active pipeline;
- automatic enrichment evidence recovery can still execute a separate hard-coded cascade.

That split is exactly the kind of hidden divergence Pipeline Studio is intended to eliminate.

### Recommended target

Create a separate assignment for automatic enrichment evidence recovery, or explicitly reuse a suitable evidence pipeline through a distinct feature key.

A provisional feature:

- `evidence_suggestion.enrichment`

Do not silently point it at the reviewer assignment unless the runtime requirements are actually identical.

The existing draft `evidence.conservative@1` may be a useful design starting point, but it should not be activated without making sure:

- direct-support validation remains mandatory;
- provenance validation remains mandatory;
- the optional LLM is closed-choice over current source-unit IDs only;
- LLM selection cannot establish evidence authority;
- fallback edges are explicit;
- the final result remains pending review where current product policy requires review.

### Migration completion condition

There should be no production path in which `suggest_evidence_cascade()` independently decides CrossEncoder/MMR/LLM behavior outside a resolved evidence pipeline.

The helper may remain as a strategy implementation detail if useful, but not as a second orchestration layer.

---

# Part II — Corpus Builder LLM workflows still outside Pipeline Studio

## 8. Corpus Builder structured metadata enrichment

### Current production path

Primary file:

- `api/app/corpus_metadata_enrichment_execution.py`

The enrichment engine builds schema-derived group tasks and calls the manager’s `_chat_json()` directly for structured LLM output.

This is a major scholarly model path and is not currently driven by a resolved Pipeline Studio definition.

The registry already contains structured-LLM strategy concepts, but registration alone does not migrate this call path.

### Recommended target

Create a Corpus Builder metadata-enrichment pipeline purpose.

Provisional feature:

- `corpus.metadata_enrichment`

The pipeline should control computational/model behavior such as:

- optional precedent packet stage;
- context assembly stage;
- structured LLM invocation;
- retry/fallback behavior;
- optional model-family or provider-profile selection policy if the product permits pipeline-level selection;
- validation result routing.

The pipeline should not own:

- metadata schema definition;
- FieldAssertion authority;
- editable/review-required field policy;
- deterministic normalization rules;
- evidence requirements;
- publication blockers.

### Important architectural requirement

The schema should remain the source of the structured output contract.

Do not hard-code field names into pipeline definitions. The pipeline references a strategy such as “structured metadata generation”; the runtime supplies the active schema-derived response model.

That preserves the FieldAssertion/schema abstraction rather than recreating per-field pipeline hard-coding.

---

## 9. Corpus segmentation and boundary decisions

### Current production path

Primary file:

- `api/app/corpus_segmentation_execution.py`

The segmentation workflow performs multiple direct `_chat_json()` calls, including:

- pair boundary decisions;
- compact/window segmentation decisions;
- structured segmentation responses.

These calls are controlled by request settings/stage limits, not by a Pipeline Studio assignment.

### Recommended target

Provisional feature:

- `corpus.segmentation`

The pipeline can model:

- deterministic pre-segmentation/window construction;
- LLM boundary proposal;
- validation;
- fallback/skip behavior;
- bounded retries.

Keep topology authority and deterministic source-block identity outside the model stage.

The LLM proposes segmentation changes; deterministic code must continue to validate referenced block IDs and legal boundary transitions before mutation.

---

## 10. Document manifest / document-structure inference

### Current production paths

Relevant files include:

- `api/app/corpus_manifest_workflow.py`
- `api/app/corpus_builder.py`

The build workflow still uses direct typed `_chat_json()` calls for document-level inference and structured metadata/manifest analysis.

These are meaningful computational stages because they affect how later corpus-building work is scoped and prompted.

### Recommended target

Provisional feature:

- `corpus.document_manifest`

Potential stages:

- deterministic file/embedded metadata collection;
- source sampling;
- structured model inference;
- schema validation;
- deterministic merge with user-reviewed state.

Do not allow the model stage to overwrite reviewed document metadata silently.

---

## 11. Corpus text cleanup / touch-up

### Current production paths

Relevant files include:

- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/llm.py`
- `api/app/routers/llm.py`
- `api/app/job_llm.py`

There are both build-time and explicit interactive/background touch-up operations.

`propose_touchup()` is used directly by synchronous and background routes/jobs. The Corpus Builder can also invoke LLM text touch-up during enrichment.

These paths do not currently resolve Pipeline Studio assignments.

### Recommended target

Do not force all touch-up use cases into one pipeline until the authority model is clear.

At minimum separate:

- source-text cleanup proposal;
- metadata/record-field touch-up;
- build-time automatic cleanup proposal.

Possible feature keys:

- `corpus.text_touchup`
- `record.touchup`

The model should continue to return proposals. Human-reviewed or deterministic application logic owns whether the changes become canonical.

For source text, preservation constraints are especially strict: the model must not silently paraphrase or “improve” philosophical content.

---

## 12. Explicit reviewer LLM evidence choice

### Current production path

Primary file:

- `api/app/corpus_review_actions.py`

Reviewer semantic evidence suggestion is pipeline-controlled, but the explicit “ask the LLM to choose evidence” path still calls `_chat_json()` directly with the closed-choice evidence prompt and then validates returned block IDs.

### Recommended target

This should be folded into the evidence pipeline architecture rather than remain an unrelated direct model tool.

Two viable designs:

1. expose the LLM closed-choice stage as an optional branch of an evidence pipeline; or
2. give the explicit tool a separate evidence feature assignment whose only admissible model strategy is closed-choice over current source-unit IDs.

Either way, deterministic ID validation and provenance/support gates remain mandatory.

---

# Part III — Other direct LLM paths

## 13. Standalone RAG grading and re-grading

### Current production path

Primary files:

- `api/app/llm_tools.py`
- `api/app/job_rag.py`
- `api/app/job_tools.py`
- `api/app/routers/llm.py`

Research pipelines already model `llm.grade_rag` as an optional evaluation stage.

However, standalone grading and background re-grade flows can call `run_rag_grade()` directly.

That means the same conceptual operation exists both:

- as a pipeline stage inside Research; and
- as a direct utility/job call.

### Recommended target

Unify grading under a named evaluation pipeline or a reusable pipeline execution entry point.

A provisional feature:

- `research.grade`

Do not require a full Research retrieval pipeline merely to re-grade an existing fixed answer/evidence packet.

The grading pipeline should receive an immutable grading input packet and emit evaluation output only.

Keep response-cache persistence and eligibility outside the graph.

---

## 14. General LLM tools

### Current production path

Primary file:

- `api/app/llm_tools.py`

Direct model calls include operations such as:

- language detection;
- source text cleanup;
- draft Record creation;
- record/candidate matching;
- catalogue/edition selection;
- RAG grading.

These are not all the same kind of workflow.

### Required classification before migration

Do not create one catch-all “LLM tools pipeline.”

Classify each operation as one of:

- scholarly/corpus transformation;
- scholarly evaluation;
- administrative/document-processing utility;
- operational exception.

Then migrate only the operations for which versioned computational behavior is meaningful and useful to users.

Likely pipeline candidates:

- draft Record generation;
- source cleanup proposal;
- catalogue/edition matching where it affects corpus metadata;
- RAG grading.

Potential documented exceptions:

- lightweight language detection when used only as an operational helper, if product requirements do not need configurable variants.

The classification should be explicit in code/docs, not implicit.

---

## 15. Localization translation

### Current production path

Primary file:

- `api/app/i18n_translation.py`

Dictionary and repair translation calls `chat_complete()` directly.

### Recommendation

Treat this as an **operational/product-localization exception** unless there is a product requirement to benchmark/version localization chains through Pipeline Studio.

It is not scholarly retrieval or corpus evidence computation.

Document the exception and keep normal provider/model telemetry, but do not inflate Pipeline Studio with every infrastructure model call.

If localization pipelines become a first-class product feature later, migrate deliberately rather than as part of the scholarly pipeline-completeness project.

---

## 16. Content-policy generation

### Current production path

Primary file:

- `api/app/content_policy_generation.py`

The content-policy builder calls `chat_complete()` directly to create language-specific policy data.

### Recommendation

Treat this as an **administrative policy-generation exception** unless a separate governance project requires Pipeline Studio control.

It should still have:

- explicit provider/model identity;
- durable audit context where appropriate;
- deterministic schema validation;
- safe retry/failure behavior.

But it does not need to count against the scholarly pipeline migration if it is explicitly documented as an operational exception.

---

# Part IV — Diagnostic and infrastructure paths that should remain exceptions

## 17. System Chroma console

### Current production path

Primary file:

- `api/app/system_chroma_console.py`

The administrator console can issue validated read-only Chroma queries directly.

### Recommendation

Keep it outside Pipeline Studio.

This is diagnostic infrastructure. Its purpose is to inspect a collection and execute a user-specified Chroma operation, not to represent a stable scholarly retrieval chain.

Do not hide the direct query behind an assigned pipeline.

Instead:

- keep command validation;
- keep read-only enforcement;
- report embedding/collection identity;
- keep permissions strict;
- explicitly list the console as an operational exception in the final migration audit.

---

## 18. Embedding projection synchronization and health/probe operations

Examples include:

- `SourceEmbeddingProjection` synchronization;
- embedding-provider health checks;
- provider warm-up/readiness;
- Chroma connection checks;
- model discovery/probing.

These are infrastructure operations, not scholarly pipelines.

They may be used **by** pipeline stages, but they should not become editable Pipeline Studio chains themselves.

The pipeline trace should record the provider/model/index identity relevant to a scholarly execution; it should not turn maintenance/probe work into fake scholarly stages.

---

# Part V — CrossEncoder completion check

## 19. Remaining CrossEncoder risk

The original audit found three major production CrossEncoder consumers:

- Research;
- metadata precedents;
- automatic evidence recovery.

Current migration status:

- Research CrossEncoder use is attributable to the Research pipeline;
- metadata-precedent CrossEncoder use is attributable to the metadata-precedent pipeline;
- reviewer evidence CrossEncoder execution is available through the evidence pipeline adapter;
- the legacy/direct automatic evidence cascade can still call `predict_scores()` outside a resolved pipeline.

Therefore the acceptance criterion:

> Every CrossEncoder call resolves through a named/versioned pipeline stage

should remain **not globally closed** until the automatic enrichment/recovery path is migrated or deleted.

After that migration, perform a fresh code search for `predict_scores(` before marking the criterion complete.

---

# Part VI — Proposed migration order

## 20. Phase A — Close retrieval/evidence gaps first

Recommended order:

### A1. Automatic enrichment evidence recovery

Why first:

- it is adjacent to an already-migrated evidence system;
- it currently creates hidden behavior divergence;
- it closes the most important remaining direct CrossEncoder orchestration path;
- evidence/provenance authority is high-risk and benefits most from one architecture.

Deliverables:

- feature assignment;
- executable adapter;
- mandatory support/provenance gates;
- explicit fallback edges;
- no direct orchestration through `suggest_evidence_cascade()`;
- stage trace at the point of enrichment/review.

### A2. General Vector Store search

Why second:

- clean API boundary;
- easy to prove whether the route uses a resolved pipeline;
- closes a major vector-search acceptance criterion;
- useful proving ground for scoped assignments.

Deliverables:

- named/versioned store-search pipelines;
- adapter replacing route-level algorithm branching;
- mode-to-built-in compatibility mapping;
- collection/index trace identity.

### A3. Metadata prefill

Why third:

- important scholarly behavior;
- direct Chroma query path;
- must carefully separate retrieval tuning from editorial field policy.

### A4. Precedent evidence remapping

Why fourth:

- bounded local retrieval problem;
- comparatively small adapter;
- completes another hidden semantic-ranking path.

---

## 21. Phase B — Corpus Builder model stages

Migrate in this order:

1. metadata enrichment;
2. segmentation;
3. document manifest/structure inference;
4. text cleanup/touch-up;
5. explicit reviewer closed-choice evidence LLM.

Reasoning:

- metadata enrichment is the largest repeated scholarly structured-generation path;
- segmentation/manifest stages have clear typed inputs/outputs;
- touch-up has more nuanced human-approval semantics and should follow after the structured stages;
- evidence LLM choice can then reuse the unified evidence runtime.

Do not build one monolithic “Corpus Builder pipeline.” These are distinct computational purposes with different input/output contracts and authority rules.

A single visual workspace can group them, but runtime definitions should remain typed and purpose-specific.

---

## 22. Phase C — Evaluation and record tools

Then migrate:

- standalone RAG grading/re-grading;
- record/draft generation tools that materially affect corpus state;
- catalogue/edition matching if it remains model-configurable and scholarly.

Keep lightweight operational helpers as documented exceptions rather than forcing them into Pipeline Studio.

---

## 23. Phase D — Final exception registry and re-audit

Create an explicit documented list of model/vector operations intentionally outside Pipeline Studio.

Expected examples:

- provider/model warm-up;
- provider discovery;
- embedding health probes;
- Chroma connection probes;
- System Chroma read-only console;
- i18n translation;
- content-policy generation, unless product requirements change.

Then run a fresh production call-site audit.

No direct model/vector call should be left in an ambiguous state. Every one should be either:

1. executed through a named/versioned pipeline; or
2. listed as an intentional operational exception with a reason.

---

# Part VII — Runtime and API design pattern for new adapters

## 24. Do not create a generic “execute arbitrary graph” engine that bypasses feature contracts

The existing pipeline registry is intentionally server-owned.

Continue to use purpose-specific compilers/adapters.

A saved definition may choose among registered strategies and settings, but the adapter must enforce the feature’s real input/output and authority invariants.

For each new purpose:

1. define the built-in pipeline;
2. add the built-in assignment;
3. add/extend registered strategies only when real implementation exists;
4. implement a typed compiler;
5. validate runtime support;
6. execute through a feature adapter;
7. produce a bounded trace;
8. surface point-of-use identity where useful;
9. preserve immutable snapshots/hashes.

Do not let a graph reference an arbitrary Python function, prompt body, code snippet, or dynamic import.

---

## 25. Suggested provisional feature keys

These names are proposals, not requirements. Validate naming conventions before implementing.

| Remaining workflow | Provisional feature/purpose |
| --- | --- |
| General Vector Store search | `vector_store_search` |
| Metadata prefill | `metadata_prefill` |
| Precedent evidence remapping | `precedent_evidence_remap` |
| Automatic enrichment evidence recovery | `evidence_suggestion.enrichment` |
| Corpus metadata enrichment | `corpus.metadata_enrichment` |
| Corpus segmentation | `corpus.segmentation` |
| Corpus document manifest | `corpus.document_manifest` |
| Corpus text cleanup proposal | `corpus.text_touchup` |
| General Record touch-up | `record.touchup` |
| Standalone Research grading | `research.grade` |

Do not add these names to the registry simply because they appear here. Add them only when the corresponding runtime adapter is being implemented.

---

# Part VIII — Trace and provenance requirements

## 26. Minimum trace contract for migrated retrieval paths

Each migrated retrieval execution should retain, where applicable:

- feature;
- pipeline ID/version/hash;
- exact resolved snapshot;
- stage ID;
- strategy ID/version;
- status;
- elapsed time;
- input/output candidate counts;
- collection/index identity;
- embedding provider/model/revision when available;
- CrossEncoder provider/model/revision when used;
- fallback reason;
- warnings;
- score summaries by score type;
- bounded candidate IDs/ranks/reason codes where audit needs them.

Do not copy source text into generic pipeline traces.

The point-of-use domain object may retain authoritative evidence/source bindings separately.

---

## 27. Minimum trace contract for migrated LLM stages

Record:

- pipeline ID/version/hash;
- stage ID/strategy;
- provider profile identity;
- model identity;
- model revision when available;
- schema name/version or response-contract identity;
- elapsed time;
- status/fallback;
- bounded token/call counts where available.

Do not copy:

- API keys;
- unrestricted prompts;
- source-derived private text;
- sealed reviewer data;
- full raw model output into generic operational traces.

Feature-specific secure audit stores may retain additional material if existing policy permits it.

---

# Part IX — UI requirements

## 28. Pipeline Studio

Each newly migrated feature should become inspectable in the existing Pipeline Studio rather than creating a separate configuration island.

The UI should make clear:

- feature assignment;
- purpose;
- active pipeline;
- immutable version;
- runtime support;
- strategy descriptions;
- which settings are computational versus authoritative domain rules;
- fallback behavior;
- most recent traces where useful.

Do not expose an “editable” parameter if the runtime ignores it.

Do not expose authority rules such as reviewer acceptance or publication eligibility as if they were retrieval tuning knobs.

---

## 29. Point-of-use visibility

Pipeline Studio is the central management surface, but some workflows also require local trace identity.

Examples:

- Corpus Builder metadata panel should show the metadata-enrichment pipeline identity;
- evidence recovery should show its exact pipeline identity next to evidence suggestions/review diagnostics;
- Vector Store search results should show which search pipeline ran;
- metadata prefill diagnostics should show the pipeline version responsible for the proposed memory candidates;
- segmentation/manifest diagnostics should bind model proposals to the pipeline version that produced them.

Avoid dumping the whole graph into every feature UI. Usually pipeline name/version/hash plus a trace link is enough.

---

# Part X — Testing requirements

## 30. Backend tests per migrated feature

Add tests for:

- assigned pipeline resolution;
- saved override resolution when permitted;
- immutable version binding;
- exact pipeline hash;
- unsupported graph rejection;
- configured fallback edges;
- timeout/unavailable/error behavior;
- stage config actually changing runtime behavior;
- no hidden fallback outside the graph;
- safe trace persistence;
- trace-persistence failure not corrupting scholarly output where that is the established policy;
- domain authority cannot be bypassed by a custom graph.

For evidence paths specifically:

- support gate cannot be omitted from active evidence pipelines;
- provenance gate cannot be omitted;
- LLM choice is current-source closed-choice only;
- CrossEncoder relevance alone cannot establish evidence.

---

## 31. Frontend tests

For Pipeline Studio additions:

- clone/version workflow;
- assignment workflow;
- runtime-support explanation;
- strategy config controls;
- keyboard navigation;
- screen-reader labels;
- long-string/French coverage;
- dark/high-contrast/forced-colors behavior;
- Storybook story;
- route-addressable `/pipelines` behavior;
- URL state remains compatible with the current navigation architecture.

For point-of-use trace additions:

- trace identity present;
- unavailable trace degrades cleanly;
- no source text leaks into operational diagnostics.

---

## 32. Full repository gates

After each cross-cutting migration slice, run the full relevant quality gates:

- backend pytest;
- Ruff;
- mypy;
- API contract;
- frontend ESLint;
- Vue app/test type checks;
- focused Vitest;
- Storybook build;
- composed Playwright E2E;
- legacy characterization where affected;
- WCAG 2.2 AA checks;
- repository-wide Prettier.

Do not treat a focused adapter test as sufficient merge validation.

---

# Part XI — Files to inspect first

## 33. Existing pipeline architecture

- `api/app/pipelines/models.py`
- `api/app/pipelines/registry.py`
- `api/app/pipelines/defaults.py`
- `api/app/pipelines/service.py`
- `api/app/pipelines/manager.py`
- `api/app/pipelines/store.py`
- `api/app/pipelines/research.py`
- `api/app/pipelines/research_tracing.py`
- `api/app/pipelines/evidence.py`
- `api/app/pipelines/metadata_precedents.py`
- `api/app/pipelines/memory.py`
- `api/app/pipelines/comparison.py`
- `api/app/pipelines/benchmark.py`

## 34. Remaining retrieval/evidence surfaces

- `api/app/routers/stores.py`
- `api/app/chroma_store.py`
- `api/app/memory_prefill.py`
- `api/app/metadata_precedents_cache.py`
- `api/app/evidence_suggestions.py`
- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/corpus_review_actions.py`
- `api/app/source_embeddings.py`

## 35. Remaining Corpus Builder / LLM surfaces

- `api/app/corpus_segmentation_execution.py`
- `api/app/corpus_manifest_workflow.py`
- `api/app/corpus_builder.py`
- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/corpus_review_actions.py`
- `api/app/llm.py`
- `api/app/llm_tools.py`
- `api/app/job_llm.py`
- `api/app/job_rag.py`
- `api/app/job_tools.py`
- `api/app/routers/llm.py`

## 36. Operational-exception candidates

- `api/app/system_chroma_console.py`
- `api/app/i18n_translation.py`
- `api/app/content_policy_generation.py`
- provider/embedding health and warm-up code.

---

# Part XII — Concrete acceptance checklist

Do not call the Pipeline Studio migration complete until a fresh production-code audit can answer **yes** to all applicable items below.

### Retrieval

- [ ] General Vector Store search resolves a named/versioned pipeline rather than branching directly on hard-coded modes.
- [ ] Metadata prefill retrieval resolves a named/versioned pipeline.
- [ ] Precedent evidence remapping resolves a named/versioned pipeline.
- [ ] Automatic enrichment evidence recovery resolves a named/versioned pipeline.
- [ ] No direct CrossEncoder orchestration remains outside a pipeline or documented exception.
- [ ] MMR implementations and score semantics have been re-audited for consistency.
- [ ] Distance-to-relevance conversion has been re-audited for metric awareness.

### Corpus Builder

- [ ] Metadata enrichment model calls resolve a pipeline.
- [ ] Segmentation model calls resolve a pipeline.
- [ ] Document manifest/structure inference resolves a pipeline.
- [ ] Build-time text touch-up resolves a pipeline or a documented proposal workflow.
- [ ] Explicit reviewer LLM evidence selection resolves through the evidence pipeline architecture.
- [ ] The active metadata schema remains authoritative and is not duplicated into hard-coded pipeline fields.

### Other model calls

- [ ] Standalone RAG grading/re-grading resolves a named evaluation pipeline.
- [ ] Record/draft/touch-up scholarly tools have been classified and migrated where appropriate.
- [ ] Every remaining direct generative model call is either pipeline-controlled or listed in the operational-exception registry.

### Exceptions

- [ ] System Chroma console is explicitly documented as a diagnostic exception.
- [ ] Provider/model warm-up and health probes are explicitly documented as infrastructure exceptions.
- [ ] Embedding projection synchronization is explicitly documented as infrastructure.
- [ ] i18n translation is classified explicitly.
- [ ] content-policy generation is classified explicitly.

### Auditability

- [ ] Point-of-use UIs show pipeline identity where a researcher/reviewer needs it.
- [ ] Historical runs keep immutable resolved snapshots/hashes.
- [ ] Traces keep score types distinct.
- [ ] Generic traces do not copy source text or secrets.
- [ ] Custom graphs cannot bypass evidence/provenance authority.

---

# Part XIII — Immediate next implementation slice

The next agent should start with **automatic enrichment evidence recovery**, not with another generic framework layer.

Recommended concrete sequence:

1. inspect every production caller of `suggest_evidence_cascade()`;
2. define the exact difference between reviewer suggestion and enrichment recovery;
3. add a feature assignment for the enrichment path;
4. compile that assignment through the existing evidence pipeline runtime;
5. ensure direct-support and provenance gates are mandatory;
6. model lexical/semantic/CrossEncoder/MMR/closed-choice behavior as registered stages and explicit fallbacks;
7. remove orchestration decisions from the legacy cascade helper;
8. retain the helper only as implementation code behind registered strategies if still useful;
9. attach the exact pipeline ID/version/hash to enrichment evidence diagnostics;
10. add tests proving no direct CrossEncoder/LLM fallback is reachable outside the resolved graph;
11. run the full quality gates;
12. then move to general Vector Store search.

That sequence closes the highest-risk architectural inconsistency first and produces a reusable template for the remaining retrieval migrations.

---

# 37. Definition of done

The remaining Pipeline Studio migration is complete only when production code can be audited into two exhaustive buckets:

### Bucket A — Pipeline-controlled scholarly/configurable computation

Every relevant operation has:

- a feature assignment;
- immutable pipeline identity;
- registered strategies;
- an executable typed adapter;
- authoritative resolved configuration;
- safe stage telemetry;
- point-of-use trace identity where needed.

### Bucket B — Explicit operational exception

Every direct model/vector operation outside Pipeline Studio has:

- a documented purpose;
- a reason it should not be user-configurable as a scholarly pipeline;
- provider/model/index telemetry appropriate to the operation;
- deterministic validation and permissions appropriate to its risk.

There should be no third bucket called “legacy direct call that happens to work.”

Until that audit is complete, describe the system as:

> **Pipeline Studio controls the principal migrated scholarly pipelines, with remaining retrieval and LLM workflows still being brought under the same versioned runtime.**

Do not describe Pipeline Studio as controlling every pipeline in DerridAI yet.
