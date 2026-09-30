# Configurable Retrieval / Pipeline Migration Handoff

**Repository:** `ajschlosser/DerridAI`  
**Prepared:** 2026-09-29  
**Authoritative default branch at handoff:** `master` @ `66320989434bf17225f8d3867dc11f1eff1eddb6`  
**Current work branch:** `task/pipeline-dry-run-comparison`  
**Open PR:** #281 — “Add non-persistent Research pipeline A/B comparison”  
**Primary design/audit source:** `docs/RETRIEVAL_RERANKING_LLM_AUDIT.md`

This document is an implementation handoff, not a release note. It records what has actually landed, what is still in PR #281, what remains incomplete from the retrieval/reranking/LLM audit, and the safest next sequence of work.

## 1. Purpose and invariant

The pipeline migration exists to make DerridAI’s computational path from query/input to retrieved candidates, reranking, selection, evidence/context packing, and LLM invocation inspectable and configurable without weakening scholarly provenance.

The governing separation remains:

> Retrieval and model stages may propose, rank, select, or transform computational candidates. They do not create scholarly authority. cELF provenance, source-unit identity, FieldAssertion ownership, reviewer decisions, support bindings, publication validation, and deterministic evidence/provenance gates remain authoritative.

Do not turn pipeline scores, model confidence, CrossEncoder relevance, MMR scores, or pipeline assignment into a substitute for source binding or human review.

## 2. Read this before continuing

The original audit in `docs/RETRIEVAL_RERANKING_LLM_AUDIT.md` is still useful as the design baseline, but its “current state” sections predate the migration work summarized here. Treat the audit as:

- the original inventory of retrieval/reranking/LLM paths;
- the target architecture and acceptance criteria;
- the source of the phased migration plan.

Treat this handoff as the current implementation-status document.

The most important repository rules for the next pass are unchanged:

- pipeline definitions are data, not executable user code;
- executable strategies remain registered, server-owned implementations;
- saved versions are immutable;
- runtime traces must bind to the exact resolved pipeline/version/hash;
- candidate telemetry must keep distinct signals distinct;
- ordinary traces must not copy source text, prompt bodies, secrets, or sealed reviewer content;
- retrieval configuration is operational state, not corpus authority;
- en-US/fr-CA parity, WCAG 2.2 AA, keyboard behavior, dark/high-contrast/forced-colors coverage, Storybook coverage, and repository Prettier remain required for UI work.

## 3. Current repository state

### Default branch

`master` currently includes PR #270, “Modernize global navigation and route workspaces,” merged as:

`66320989434bf17225f8d3867dc11f1eff1eddb6`

That change matters to this work because Pipeline Studio is now a first-class `/pipelines` workspace under **AI & Automation**, with canonical route state and hierarchical breadcrumbs rather than being only a System Data subsection.

### Current pipeline-comparison branch

PR #281 is based on an older master and must be synchronized with the current default branch before merge. At the latest comparison captured during this handoff, the branch had diverged from `master`: it contained the comparison work but was behind by the commits that landed with PR #270.

GitHub currently reports the PR as mergeable, but that is not a substitute for explicitly bringing current `master` into the branch and rerunning the quality gates. Do that before considering #281 complete.

### CI status at handoff

The latest PR #281 quality-gate run is GitHub Actions run **2000** (`36614460202`) for head `cb340d420ef6bff582ab41d66c2138a0487c93ae`.

Run 2000 completed successfully. All jobs were green, including:

- changes
- format-check
- backend
- backend-lint
- backend-types
- api-contract
- frontend-lint
- frontend-static
- frontend-e2e (1/2)
- frontend-e2e (2/2)
- frontend-legacy (1/2)
- frontend-legacy (2/2)
- frontend-a11y

This validates the comparison implementation on its pre-PR-#270 base. It is **not** final merge validation: rerun the full quality gates after synchronizing the branch with current `master`.

## 4. What has landed

The migration has progressed materially beyond the original audit. The following is the practical sequence.

### 4.1 Core typed pipeline architecture — PR #253

PR #253 introduced the structural foundation:

- typed pipeline contracts;
- a server-owned strategy registry;
- built-in pipeline definitions;
- versioned saved definitions;
- assignments;
- immutable resolved pipeline snapshots/hashes;
- execution traces;
- administrative Pipeline Studio surfaces;
- backup participation.

This established the central rule that a pipeline definition may reference only known server-owned strategies. A definition cannot inject code.

### 4.2 Runtime-integrity hardening and operator UX — PR #267

PR #267 landed the integrity fixes that were originally developed in #263:

- Research stage configuration is authoritative when explicitly configured;
- configured fallback edges are followed instead of inferred fallback behavior;
- persisted Research trace stage IDs bind to the resolved immutable definition;
- citation-binding stages are explicit;
- unknown strategy config keys and built-in ID/version collisions are rejected;
- pipeline backup restore is validated before mutation and applied atomically;
- cloning/version allocation is server-authoritative;
- Pipeline Studio explains stages, strategies, fallbacks, assignments, immutable versions, runtime support, and trace semantics in plain language;
- strategy parameter help/tooltips distinguish deterministic rules, learned rerankers, and generative LLM stages;
- English and Canadian French coverage was added.

This is the baseline to preserve when extending the graph model.

### 4.3 Reviewer evidence suggestions moved onto pipeline runtime — PR #262

PR #262 added the first bounded executable adapter for reviewer evidence suggestion:

- assigned evidence pipelines resolve through Pipeline Studio;
- Record Review evidence suggestions execute through the resolved pipeline;
- stage-level operational traces are persisted;
- lexical, semantic, CrossEncoder relevance, and support signals remain separate;
- candidate retention/rejection decisions are bounded and do not copy source text;
- telemetry persistence failure does not invalidate a completed scholarly operation.

This was an important architectural proof: feature code can move onto the pipeline runtime without making pipeline telemetry authoritative.

### 4.4 Metadata precedent retrieval moved onto pipeline runtime — PR #273

PR #273 made `metadata_precedents` executable through the pipeline system:

- retrieve → scope → hybrid fusion → optional CrossEncoder → quotas → MMR → pack is compiled from the assigned immutable pipeline;
- candidate depth, fusion weights, CrossEncoder settings, MMR lambda, and packet budget are pipeline-configurable;
- schema-owned eligibility, analogy policy, similarity floors, and positive/correction quotas remain authoritative outside the tunable graph;
- fallback to deterministic editorial memory remains explicit;
- pipeline ID/version/hash is attached to retrieval telemetry.

This preserved the audit’s recommendation that metadata precedents remain one of the strongest staged retrieval designs in DerridAI.

### 4.5 Claim and response memory moved onto pipeline runtime — PR #277

PR #277 made Research advisory memory pipeline-executable:

- shared bounded compiler for `claim_memory` and `response_memory`;
- semantic candidate depth, similarity floor, lexical fallback depth, and final top-K are pipeline settings;
- lexical degradation is an explicit fallback stage;
- fallback behavior respects configured timeout/unavailable/error edges;
- custom pipelines can omit a fallback deliberately;
- validated-claim authority, support bindings, owner scope, response-grade eligibility, and evidence-status checks remain outside the tunable graph.

A custom memory pipeline therefore changes search mechanics only; it cannot promote unreviewed or ineligible material into trusted memory.

### 4.6 Metadata pipeline traces surfaced at the point of review — PR #278

PR #278 closed an auditability gap for Corpus Builder metadata precedents:

- metadata semantic-retrieval degradation is represented as an explicit registered fallback stage;
- normal and fallback execution is converted into a trace bound to immutable stage IDs;
- per-record metadata-precedent traces are persisted in the shared trace store;
- the reviewed Record retains the exact trace;
- Corpus Builder exposes the trace directly in the Metadata panel;
- copy explicitly distinguishes computational selection telemetry from authoritative metadata provenance.

This is the pattern to use for other point-of-use trace surfaces.

### 4.7 Evidence authority made structurally non-bypassable — PR #279

PR #279 introduced `evidence.reviewer.current@2` and made it the active reviewer default.

The active reviewer evidence chain now requires:

1. lexical and semantic candidate generation;
2. deterministic direct-support validation;
3. deterministic provenance validation against a real source unit in the current source document;
4. bounded final selection.

The prior v1 chain remains disabled as inspectable history.

Important constraint: CrossEncoder or semantic relevance may surface a candidate, but relevance alone cannot make it admissible evidence.

### 4.8 Pipeline operational health metrics — PR #280

PR #280 implemented the aggregate operational telemetry portion of Phase 5:

- run counts/status;
- fallback and stage-failure incidence;
- warning incidence;
- average/p95 runtime;
- per-feature execution health;
- per-strategy execution counts;
- unavailable/timeout/error/fallback counts;
- model/provider call counts;
- latency;
- average candidate flow.

The admin endpoint is:

`GET /api/system/pipelines/metrics`

Pipeline Studio presents these as operational health, not scholarly validity.

### 4.9 Global navigation/route modernization — PR #270

PR #270 is not part of the retrieval algorithm itself, but it changes the integration point for this work:

- Pipeline Studio is a first-class `/pipelines` route;
- it belongs to **AI & Automation**;
- route state is URL-addressable;
- breadcrumbs and global navigation are derived from route metadata;
- System Data remains a separate system workspace.

Any follow-up Pipeline Studio UI should target the routed `/pipelines` experience and preserve the new navigation architecture rather than recreating the older “System Data subsection only” mental model.

### 4.10 Automatic evidence recovery moved onto pipeline runtime

Enrichment evidence recovery and accept-time evidence backfill no longer call the removed `suggest_evidence_cascade()`. Both resolve the `evidence_recovery` assignment and execute it through `execute_evidence_recovery()` in `api/app/pipelines/evidence_recovery.py`, a cascade runtime over a closed set of registered strategies.

Runtime contract (purpose `evidence_recovery`):

- A stage that produces candidates follows its single `next` edge; an empty result follows `on_empty`; unavailable, timed-out, and failed stages follow `on_unavailable`, `on_timeout`, and `on_error`. A fallback edge hands the target the input the failed stage received, and service validation now type-checks fallback edges on that basis. Stages the graph never routes to never run, so expensive stages run only when cheaper ones find nothing.
- The provenance gate and terminal top-K selection are mandatory, and only the provenance gate may route to selection.
- cELF compliance is computed, not assumed: a graph is compliant only when every edge into provenance comes from `validate.evidence_support` (at least 0.50) or the closed-choice model. Non-compliant graphs are executable, carry a validation warning, report `celf_compliant: false` in runtime support, and stamp every evidence entry they produce.
- Recovery-only settings (`retrieve.lexical_bm25.min_score`, `rerank.cross_encoder.min_score`, `select.mmr.min_relevance`) are rejected by the Research, reviewer-evidence, and metadata-precedent adapters rather than ignored.
- A record without a source-document identity is reported before any retrieval or model call.

Built-ins: `evidence.recovery.celf@1` (text support, then closed-choice model; no embeddings or reranking) and `evidence.recovery.cascade@1` (relevance-first order: text, similarity, cross-encoder, MMR, model). The cascade is non-cELF-guaranteed at its output boundary, so its suggestions remain advisory until direct evidence is bound and validated. Traces list only the stages that ran, in execution order, with `fallback_reason` on each stage that left along a fallback edge.

The remaining direct `predict_scores()` callers are `rag.py` (Research pipeline) and `metadata_exemplar_retrieval.py` (metadata-precedent pipeline). Re-verify they are unreachable outside those pipelines before closing the CrossEncoder criterion.

### 4.11 General Vector Store search moved onto pipeline runtime

`POST /api/stores/{store}/search` no longer branches on `mode`. It resolves a `vector_store_search` pipeline and executes it with `execute_store_search()` in `api/app/pipelines/store_search.py`, a dataflow runtime over registered strategies (`query.passthrough`, `retrieve.chroma_similarity`, `retrieve.lexical_bm25`, `retrieve.store_keyword`, `retrieve.store_filter`, `fusion.rrf`, `select.mmr`, `select.top_k`). `ChromaStore.hybrid_search()` and `mmr_search()` are removed; fusion and MMR selection are pipeline stages.

- Each existing mode is a shortcut to its built-in `store_search.<mode>@1`; `mode: "assigned"` runs the assignment (built-in: `store_search.similarity@1`); administrators may name an exact saved version.
- The fallbacks that used to be implicit (empty query in hybrid/lexical, no lexical terms, hybrid on a collection without query embeddings) are graph edges. An unavailable or failed stage without a matching edge fails the request, as before.
- Stage `fetch_k`, `lambda_mult`, `rrf_k`, and `limit` settings override request values when set. Without `fetch_k`, a retrieval stage fetches what its consumer needs (request `fetch_k` for MMR; four times the result count, 32–400, for fusion; otherwise the result count).
- Output is pinned by `tests/test_store_search_characterization.py`, whose snapshot was captured from the pre-migration route.
- Responses carry pipeline identity; traces keep collection, embedding provider/model, counts, score types, and filtered field names, never query text or filter values.

Follow-up: show the pipeline identity next to results in the Search workspace; one trace is persisted per search, so trace retention is now pressing.

### 4.12 Metadata pre-fill retrieval moved onto pipeline runtime

`memory_prefill.prefill_records()` resolves the `metadata_prefill` assignment (built-in `metadata.prefill.current@1`: `retrieve.metadata_exemplars` → `normalize.collection_relevance` → new `select.memory_hints`) through `api/app/pipelines/metadata_prefill.py`.

Classification of the former constants: `FETCH_K`, the distance-to-similarity conversion, `HINT_SIMILARITY`, and `MAX_HINTS_PER_FIELD` are pipeline settings; `MIN_AGREE`, `OBVIOUS_SIMILARITY`, `CONFLICT_MARGIN`, one vote per earlier Record, the 0.9 confidence cap, exemplar eligibility, excluding the current build, schema validity, and never overwriting reviewed or present values remain domain policy; `MAX_SPANS`, `BATCH`, `MIN_SPAN_CHARS`, and the time budget remain server bounds. The existing pre-fill tests pass unchanged.

Metric-awareness finding: pre-fill converts distance with `1 / (1 + distance)` regardless of the collection metric. It is kept for parity because the pre-fill threshold was calibrated against it; the adapter rejects other normalization methods until one is calibrated.

One trace is recorded per build; the build's `memory_prefill` summary carries the pipeline identity. The Corpus Builder does not display it yet.

### 4.13 Precedent evidence remapping moved onto pipeline runtime

`metadata_precedents_cache.rank_candidates()` (enrichment cache and live precedents panel) ranks through a `RemapSession` for the `precedent_evidence_remap` assignment (built-in `precedent.remap.current@1`: `retrieve.source_cosine`, falling back on unavailable/error to the new `retrieve.token_overlap`, then `validate.provenance` and `select.top_k` limit 3) in `api/app/pipelines/precedent_remap.py`. `rank_blocks_for_texts()` is replaced by strategy functions (`semantic_block_scores`, `lexical_block_scores`, `ranked_block_candidates`); its tests now run through the pipeline with the same assertions.

The provenance gate and top-K selection cannot be removed; candidates remain advisory current-Record correspondences. An unresolvable assignment yields no candidates (logged) rather than failing the panel or the enrichment cache.

### 4.14 Corpus Builder metadata enrichment moved onto pipeline runtime

`_execute_metadata_tasks()` no longer decides how a metadata group's model call runs. It resolves the `corpus_metadata_enrichment` assignment once per Record (built-in `corpus.metadata_enrichment.current@1`: `llm.structured_metadata` on the primary provider, 2 attempts, escalating on error or timeout to `llm.structured_metadata` on the review provider, 2 attempts) and runs each group through `EnrichmentSession` in `api/app/pipelines/corpus_metadata_enrichment.py`. `_chat_json()` takes `roles` and `escalated` so one stage runs one provider role; its default chain is unchanged for the callers that have not migrated (segmentation, manifest, touch-up, reviewer evidence choice).

- Classification: provider role and attempts are pipeline settings. The correction/escalation prompt notes, the growing token budget, not retrying a timed-out provider, and the per-family `max_tokens`/timeouts from build settings stay server policy. The schema-derived prompt and response model, family routing (fast/deep, human-owned, adaptive skip, settle), reconciliation, evidence and autofill stay domain code outside the pipeline.
- The compiler accepts one terminal structured stage with at most one terminal escalation stage on the other provider role. A review stage without a configured review provider is `unavailable`; with no edge, the primary failure is reported exactly as before.
- Precedent retrieval for the prompt stays on its own `metadata_precedents` assignment; it is not a stage of this pipeline.
- An unresolvable assignment fails the family with the reason before any model call; there is no hidden default.
- Parity is pinned by `tests/test_corpus_metadata_enrichment_pipeline.py`, which runs the same scripted provider through the legacy chain and the pipeline and compares calls, prompts, token budgets, results and error text. Existing enrichment tests pass with only their `_chat_json` stub signatures widened to accept the new keywords.
- One trace per Record (also on cancellation); each family's `metadata_execution_ledger` entry carries the pipeline identity, trace ID and the stages that ran. Traces carry provider, model, attempts, response-contract names and failure codes, never prompts or answers. The Corpus Builder does not display the identity yet.
- Pipeline Studio renders enumerated settings (such as `provider_role`) as a choice list.

## 5. Current built-in assignments

As of current `master`, built-in system assignments are:

| Feature                      | Assigned pipeline                      | Status |
| ---------------------------- | -------------------------------------- | ------ |
| Research                     | `research.current@1`                   | active |
| Reviewer evidence suggestion | `evidence.reviewer.current@2`          | active |
| Evidence recovery            | `evidence.recovery.cascade@1`          | active |
| Vector Store search          | `store_search.similarity@1`            | active |
| Metadata pre-fill            | `metadata.prefill.current@1`           | active |
| Precedent evidence remapping | `precedent.remap.current@1`            | active |
| Corpus metadata enrichment   | `corpus.metadata_enrichment.current@1` | active |
| Metadata precedents          | `metadata.precedents.current@1`        | active |
| Validated claim memory       | `memory.claim.current@1`               | active |
| Prior response memory        | `memory.response.current@1`            | active |

There are also important draft/legacy definitions:

- `research.balanced@1` — draft target architecture;
- `evidence.reviewer.current@1` — disabled legacy reviewer chain;
- `evidence.conservative@1` — draft deeper evidence chain.

### Research remains deliberately on the current production ordering

The active `research.current@1` still models the existing production path:

```text
optional query decomposition
    -> dense candidate generation
       -> similarity/RRF path
       -> MMR -> RRF path
    + lexical retrieval
    -> RRF
    -> CrossEncoder
       -> lexical fallback on unavailable/timeout/error
    -> provenance
    -> context pack
    -> generation
    -> citation binding
    -> optional grade
```

The proposed `research.balanced@1` remains a **draft**, not the active default:

```text
optional query decomposition
    -> dense + lexical
    -> relevance normalization / RRF
    -> CrossEncoder
    -> source-aware diversity
    -> provenance
    -> context pack
    -> generation
    -> citation binding
    -> optional grade
```

Do not silently activate the draft architecture. The audit explicitly called for changing defaults only after visibility and controlled comparison/benchmarking exist.

## 6. PR #281: non-persistent Research dry-run and A/B comparison

PR #281 is the current unfinished slice.

### What it adds

Backend:

- `POST /api/system/pipelines/compare/research`;
- administrator-only comparison of two saved/executable Research pipeline versions;
- both sides execute the real Research retrieval/reranking/provenance/context path;
- execution stops after context construction via `stop_after_context=True`;
- no final answer is generated;
- no grade is produced;
- response memory and claim memory are disabled;
- no Research job is created;
- no response-cache entry is created;
- no persisted pipeline-run trace is created;
- no corpus state is mutated.

The comparison contract retains bounded candidate lineage without source text:

- pre-rerank candidate IDs/ranks/routes/scores;
- post-rerank candidate IDs/ranks/routes/scores;
- final selected evidence IDs;
- candidate overlap;
- post-rerank overlap;
- final evidence overlap;
- rank changes for shared records;
- elapsed time;
- context size;
- query-transform call count;
- CrossEncoder call count;
- score-distribution summaries.

Frontend:

- `PipelineComparisonPanel.vue`;
- exposed in Pipeline Studio;
- same Research question and same corpus collection on both sides;
- initial UI forces `query_decomposition: false` so comparison is retrieval-focused and reproducible and does not require a generation provider;
- descriptive overlap/latency/candidate-flow presentation;
- no “winner,” score, or quality verdict;
- English/Canadian French localization;
- Storybook and frontend regression coverage;
- backend regression coverage for non-persistence and source-text exclusion.

### Important distinction

This first comparison mode is **not yet benchmark-run integration**. It compares computational retrieval behavior. It does not determine which pipeline is academically or empirically better.

A useful interpretation is:

- overlap and rank movement = “how differently did the two chains retrieve/select?”;
- latency/model-call counts = “what did each chain cost operationally?”;
- fixed benchmark grading = future work.

### PR #270 integration work still required

Before merging #281:

1. synchronize `task/pipeline-dry-run-comparison` with current `master`;
2. resolve any overlap in `SystemDataPipelines.vue` and its tests in favor of PR #270’s route-addressable Pipeline Studio behavior;
3. verify the comparison panel renders correctly through the canonical `/pipelines` route;
4. verify URL-backed selected pipeline/run state introduced by #270 still works;
5. rerun the full quality gate;
6. only then mark #281 ready.

## 7. Phase status against the original audit

### Phase 1 — Instrument and normalize

**Substantially complete, but not universal.**

Done:

- typed pipeline/run/stage trace contracts;
- shared runtime trace surfaces;
- Research runtime settings bound to resolved pipeline definitions;
- reviewer evidence telemetry;
- metadata precedent telemetry;
- claim/response memory execution detail;
- safe candidate-level diagnostics in migrated paths.

Still incomplete:

- not every original retrieval or LLM call site resolves through a pipeline;
- some non-migrated paths still have feature-local telemetry/logic;
- the audit acceptance criteria should not be marked globally complete yet.

### Phase 2 — Strategy registry and built-ins

**Complete for the migrated purposes.**

Done:

- server-owned registry;
- built-in definitions;
- validation;
- assignments;
- Pipeline Studio inspection;
- runtime-support reporting.

Still incomplete at system-wide level:

- several production computational workflows from the original audit still do not have executable pipeline adapters.

### Phase 3 — Editable chains and versioning

**Mostly implemented for current supported pipeline purposes.**

Done:

- saved immutable versions;
- cloning/version allocation;
- validation;
- assignments;
- fallback editing;
- schema-driven strategy configuration;
- resolved immutable snapshots/hashes;
- permissions/admin management.

Still incomplete:

- export/import as a first-class operator workflow;
- broader strategy-version deprecation/migration tooling;
- some scope/resolution ideas from the original target architecture remain narrower than originally proposed.

### Phase 4 — Retrieval quality improvements

**Partially complete.**

Done:

- reviewer evidence is now support-gated;
- provenance gating is structurally required for active reviewer evidence pipelines;
- metadata precedent retrieval is configurable and traceable;
- evidence relevance and evidence authority are kept separate.

Not done:

- `research.balanced@1` is still a draft;
- Research has not yet moved diversity after CrossEncoder in the active production default;
- fixed benchmark evidence is not yet available to justify switching the default;
- the deeper `evidence.conservative@1` chain is still draft.

### Phase 5 — Comparison, benchmarking, and governance

Status:

1. **Dry-run pipeline testing** — implemented in PR #281 for Research retrieval/context, pending merge.
2. **A/B pipeline comparison** — implemented in PR #281 for Research retrieval/context, pending merge.
3. **Aggregate stage latency/error/fallback dashboards** — merged in PR #280.
4. **Benchmark-run integration** — not implemented.
5. **Export/import for pipeline definitions** — not implemented as a first-class Pipeline Studio workflow.
6. **Deprecation/migration tooling for strategy versions** — not implemented.
7. **Automated warnings for unsafe/incoherent chains** — partial through structural validation, but no broader governance warning system yet.

## 8. Important non-migrated or partially migrated areas

The next developer should not infer that “Pipeline Studio exists” means every retrieval/LLM path has moved behind it.

Re-audit these original inventory items before claiming migration completeness.

### 8.1 General Vector Stores / database search

Similarity, MMR, hybrid, lexical, and filter modes remain important search behaviors. The audit target was to expose them as named pipeline chains instead of isolated “magic modes.”

Migrated in section 4.11: every mode now runs a versioned `store_search.<mode>` pipeline.

### 8.2 Metadata prefill

Migrated in section 4.12; pre-fill policy remains domain code.

### 8.3 Precedent evidence remapping

Migrated in section 4.13.

### 8.4 Generic/feature-specific LLM operations

The original audit identified many generative/structured LLM uses beyond Research answer generation, including Corpus Builder segmentation/metadata work, touch-up/review operations, translation, and other utility calls.

Corpus Builder metadata enrichment migrated in section 4.14; segmentation, manifest, touch-up, and reviewer evidence choice still call `_chat_json()` directly.

Only claim that acceptance criterion “every generative LLM call resolves through a pipeline” is met after a fresh call-site audit.

### 8.5 Research default algorithm

The target `research.balanced@1` graph exists as data, but the production assignment intentionally remains `research.current@1`.

Changing that assignment is a quality decision and must follow controlled comparisons/benchmarks, not architectural preference alone.

## 9. Acceptance-criteria status

The audit defined 20 completion criteria. Current approximate status:

| #   | Criterion                                                                                 | Status                                                              |
| --- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 1   | One documented registry of retrieval/reranking/validation/packing/LLM strategies          | largely met for registered pipeline strategies                      |
| 2   | Every vector-search feature resolves through a named/versioned pipeline                   | not met                                                             |
| 3   | Every CrossEncoder call resolves through a named/versioned pipeline stage                 | verify before claiming; migrated major paths, but re-audit          |
| 4   | Every generative LLM call resolves through a pipeline or documented operational exception | not met                                                             |
| 5   | UI can show assigned pipeline for every relevant feature                                  | partial                                                             |
| 6   | UI can show fully resolved pipeline before a run                                          | met for supported Research configuration; not universal             |
| 7   | UI can show actual stages after a run                                                     | met for migrated Research/metadata/evidence surfaces; not universal |
| 8   | Fallback/timeout/skipped/unavailable behavior visible                                     | met in migrated runtimes; not universal                             |
| 9   | Candidate counts and stage-specific scores remain distinct                                | met in migrated retrieval traces                                    |
| 10  | Distance-to-relevance normalization is metric-aware/shared                                | verify globally before closing                                      |
| 11  | MMR uses one shared implementation                                                        | verify globally before closing                                      |
| 12  | Historical runs preserve immutable resolved pipeline snapshots                            | met for pipeline-traced runs                                        |
| 13  | Authorized users can create/version chains from registered strategies                     | met for supported purposes                                          |
| 14  | Chains validated for type/provenance/bounds/permissions                                   | substantially met; continue hardening                               |
| 15  | Evidence-binding chains cannot bypass source/provenance validation                        | met for active reviewer evidence pipeline                           |
| 16  | Research and Corpus Builder expose point-of-use traces                                    | substantially met                                                   |
| 17  | Central operational view of pipelines/assignments/traces                                  | met in Pipeline Studio                                              |
| 18  | Benchmark tooling can compare variants with fixed prompts/corpora                         | not met; #281 is retrieval comparison, not benchmark integration    |
| 19  | New controls meet project accessibility/i18n/theme requirements                           | enforced per change; continue CI gates                              |
| 20  | Retrieval configuration remains separate from cELF provenance authority                   | met architecturally; preserve this invariant                        |

Do not convert “partial” rows to “met” without inspecting current production call sites and tests.

## 10. Recommended next work order

After PR #281 is synchronized with `master`, green, and merged, continue in this order.

### Step 1 — Finish benchmark-run integration

Build a fixed-corpus/fixed-prompt benchmark runner on top of the non-persistent comparison contract.

Requirements:

- benchmark case ID/version;
- fixed corpus/index revision;
- fixed prompt/instructions;
- exact pipeline ID/version/hash per side;
- embedding/CrossEncoder/model versions;
- deterministic retrieval settings where possible;
- retrieval overlap/rank/context metrics from #281;
- existing Research grading dimensions only when a generated answer is deliberately included;
- persisted benchmark result distinct from ordinary Research jobs and ordinary operational traces;
- no automatic “winner” label unless the benchmark definition itself names an objective metric and the UI presents the raw result rather than an opaque score.

For retrieval-only ablations, do not invent answer-quality conclusions from overlap or latency.

### Step 2 — Use benchmarks to evaluate `research.balanced@1`

Compare at minimum:

- current production chain;
- dense + lexical + RRF + CE + post-CE diversity target;
- similarity-only baseline;
- dense + lexical without CE;
- current MMR-before-fusion behavior;
- different bounded diversity settings where meaningful.

Measure:

- candidate/evidence overlap;
- fixed relevance/support metrics if a labeled benchmark exists;
- provenance-gate attrition;
- context size;
- latency;
- CrossEncoder/model calls;
- downstream answer grades only when generated under a controlled generation configuration.

Do not activate `research.balanced@1` based only on architectural neatness.

### Step 3 — Inventory and migrate remaining retrieval paths

Create a fresh checklist from the original audit and current code. Prioritize:

1. general Vector Store/search pipelines;
2. metadata prefill;
3. precedent evidence remapping;
4. any remaining direct CrossEncoder caller;
5. any vector-search caller not resolving an assignment/version.

The migration pattern should be the same as the successful earlier work:

- compile a bounded typed plan;
- keep domain authority outside the configurable graph;
- execute through registered strategies;
- attach exact pipeline identity;
- retain safe stage/candidate telemetry;
- add point-of-use trace where a researcher would need to audit the result.

### Step 4 — Re-audit generative LLM call sites

Repeat the “complete generative LLM-query inventory” section of the original audit against current `master`.

Classify each call as:

- scholarly pipeline stage;
- corpus-processing pipeline stage;
- review/editorial tool;
- operational exception (for example provider/model probe or warmup).

Do not force operational probes into scholarly pipelines, but explicitly document exceptions.

### Step 5 — Governance and portability

Then add:

- pipeline definition export;
- validated import;
- strategy-version deprecation metadata;
- migration/upgrade assistance for saved pipelines;
- warnings for deprecated/unavailable strategies;
- warnings for unusual but technically valid graphs;
- dependency/model/index compatibility checks;
- clear “cannot execute” diagnostics that do not mutate saved definitions.

Structural rejection and advisory warnings should remain separate concepts.

## 11. How to extend comparison safely

The comparison work deliberately stops before answer generation in its initial UI.

If extending it:

- keep a retrieval-only mode;
- make generation an explicit opt-in benchmark mode;
- never write response memory from comparison runs;
- never write claim memory from comparison runs;
- never mutate corpus or reviewer state;
- never create ordinary Research jobs unless the user explicitly chooses to promote/run a configuration;
- keep benchmark persistence separate from operational pipeline traces;
- preserve exact immutable pipeline snapshots/hashes;
- preserve candidate lineage by ID/scores/reason codes rather than copying source text into generic diagnostics;
- include index/collection/embedding revision when available;
- expose missing revision metadata as a reproducibility limitation rather than silently omitting it.

## 12. Testing/CI expectations for the next developer

For backend-only runtime work, run focused pytest first, then the full CI path as needed.

For cross-cutting Pipeline Studio work, expect at minimum:

- backend pytest for pipeline compiler/manager/store/feature adapter;
- API contract tests;
- Ruff;
- mypy;
- frontend ESLint;
- `vue-tsc` app/test type checks;
- focused Vitest;
- Storybook build when components change;
- Playwright composed E2E;
- legacy DOM characterization where affected;
- WCAG 2.2 AA sweep;
- repository-wide Prettier check.

Do not report “all tests pass” based only on a focused suite.

For PR #281 specifically, rerun all quality gates after syncing PR #270/current `master`.

## 13. Files to understand first

Backend pipeline core:

- `api/app/pipelines/models.py`
- `api/app/pipelines/registry.py`
- `api/app/pipelines/service.py`
- `api/app/pipelines/manager.py`
- `api/app/pipelines/store.py`
- `api/app/pipelines/defaults.py`
- `api/app/pipelines/research.py`
- `api/app/pipelines/research_tracing.py`
- `api/app/pipelines/evidence.py`
- `api/app/pipelines/metadata_precedents.py`
- `api/app/pipelines/memory.py`
- `api/app/pipelines/metrics.py`

PR #281 adds/changes:

- `api/app/pipelines/comparison.py`
- `api/app/routers/pipelines.py`
- `api/app/rag.py`
- `tests/test_pipeline_comparison.py`
- `web/src/components/pipelines/PipelineComparisonPanel.vue`
- `web/src/components/pipelines/PipelineComparisonPanel.stories.ts`
- `web/src/api/pipelines.ts`
- `web/src/types/pipelines.ts`
- `web/tests/frontend/pipeline-comparison-panel.test.ts`

Point-of-use/frontend:

- `web/src/components/system-data/SystemDataPipelines.vue`
- `web/src/views/PipelineStudioView.vue`
- `web/src/components/pipelines/PipelineRunTracePanel.vue`
- `web/src/components/pipelines/PipelineExecutionHistory.vue`
- `web/src/components/pipelines/PipelineOperationsSummary.vue`
- `web/src/components/research/ResearchSettingsDrawer.vue`
- `web/src/components/research/ResearchRunsDrawer.vue`
- `web/src/components/CorpusMetadataResolutionPanel.vue`

Reference documents:

- `docs/RETRIEVAL_RERANKING_LLM_AUDIT.md`
- `docs/ARCHITECTURE.md`
- `docs/METADATA_MEMORY.md`
- `docs/METADATA_SCHEMAS.md`
- `SPECIFICATION.md`

## 14. Known traps

### Do not flatten score semantics

Keep at least these conceptually separate:

- lexical support;
- semantic similarity/relevance;
- RRF rank;
- CrossEncoder relevance;
- MMR/diversity score;
- evidence-support result;
- provenance-gate result;
- model confidence.

A generic `score` field is not enough for auditability.

### Do not let relevance establish evidence authority

The CrossEncoder currently used in retrieval is a relevance model, not proof of entailment/support. A high relevance score cannot replace deterministic support and provenance checks.

### Do not let a custom pipeline override domain-authority rules

Examples that must remain outside tunable retrieval graphs unless there is a deliberate specification change:

- reviewer validation state;
- claim support bindings;
- response-grade eligibility;
- schema-owned field policy;
- FieldAssertion authority;
- source-document/source-unit identity;
- publication blockers.

### Do not silently rewrite old runs

Pipeline edits produce new immutable versions. Historical runs/traces keep their resolved snapshot/hash and exact version identity.

### Do not treat a dry run as an ordinary run

The #281 comparison path is intentionally non-persistent with respect to Research jobs, response memory, claim memory, and ordinary pipeline traces.

### Do not undo PR #270’s navigation model

Pipeline Studio now has its own canonical route. New Pipeline Studio UI should integrate with the routed workspace, URL state, and current shell instead of reviving old “More tools” or query-parameter-only navigation patterns.

## 15. Immediate handoff checklist

The next person taking this work should begin with:

1. pull/fetch current `master` and confirm `66320989434bf17225f8d3867dc11f1eff1eddb6` or newer;
2. inspect PR #281 and current head;
3. synchronize `task/pipeline-dry-run-comparison` with current `master`;
4. preserve PR #270’s `/pipelines` route/navigation changes;
5. run focused comparison tests;
6. run the full quality gates;
7. fix any post-sync conflicts/regressions;
8. merge #281 only when the post-sync CI is fully green;
9. then begin benchmark-run integration;
10. use benchmark evidence before considering activation of `research.balanced@1`.

## 16. Definition of “done” for this migration

Do not call the overall audit/migration complete merely because Pipeline Studio exists or because PR #281 lands.

The migration is complete only when a fresh production-code audit can demonstrate that:

- all scholarly retrieval paths have an explicit named/versioned computational chain;
- all CrossEncoder calls are attributable to a pipeline stage;
- all scholarly generative LLM calls are attributable to a pipeline stage or explicitly documented exception;
- the assigned/resolved chain is visible before execution where relevant;
- actual stage execution and fallbacks are visible after execution;
- benchmark tooling can compare immutable variants on fixed cases;
- saved pipelines have workable lifecycle/deprecation/export/import governance;
- evidence/provenance validation cannot be bypassed by configurable relevance stages;
- historical runs remain reproducible enough to identify exact pipeline/strategy/model/index configuration;
- none of that computational configuration replaces cELF provenance authority.

Until those statements are true, use “pipeline migration in progress,” not “pipeline migration complete.”
