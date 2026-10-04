<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

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

### Where the work stands (2026-09-29)

- On `master`: Phase A (evidence recovery, Vector Store search, metadata pre-fill and precedent remapping; sections 4.10–4.13), PR #281's non-persistent Research dry-run and A/B comparison (section 6), metadata enrichment (4.14, #304) and segmentation (4.15, #306).
- In PR #312: the document manifest (4.16), text touch-up (4.17) and the reviewer's **Ask the model** evidence choice (4.18).
- Still calling a model directly: section 8.6 lists each call and how to move it.

Branch every slice from current `master` and open its PR against `master`. Do not stack PRs; if a slice depends on an unmerged one, say so in the PR body.

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
- Recovery-only settings (`retrieve.lexical_bm25.min_score`, `rerank.cross_encoder.min_score`, `select.mmr.min_relevance`, plus `llm.closed_choice_evidence.candidate_scope` / `candidate_limit`) are rejected by adapters that do not execute them rather than ignored.
- A record without a source-document identity is reported before any retrieval or model call.

Built-ins now include three recovery variants. `evidence.recovery.celf@1` is the lean text-support/closed-choice chain. `evidence.recovery.cascade@1` is retained as the original relevance-first historical graph and remains non-cELF-guaranteed because CrossEncoder/MMR output can feed provenance without a support decision. `evidence.recovery.cascade@2` is the corrected default: direct support exits early; otherwise semantic retrieval, CrossEncoder and MMR only rank and bound candidates; deterministic support or a closed-choice decision must occur before provenance. Traces list only the stages that ran, in execution order, with `fallback_reason` on each stage that left along a fallback edge.

Closed-choice model stage settings. `llm.closed_choice_evidence` has `provider_role` (`chain`, `primary`, `review`; default `chain`) and `attempts` (1–4, default 2). Evidence recovery also honors `candidate_scope` (`all` or `input_or_all`) and `candidate_limit` (1–32). With `input_or_all`, an upstream ranked set is the only set shown to the model, capped by `candidate_limit`; if no upstream set exists, the stage falls back to the Record's source units. Returned IDs are validated against exactly the set the model saw. The v1 built-ins retain their historical empty LLM-stage config; cascade v2 explicitly uses `input_or_all` with a limit of four. A clone can still choose one provider per stage and express provider escalation with fallback edges. Missing provider roles and timeouts retain their explicit runtime statuses, and the trace records provider/model plus candidate count when shortlist settings are active. The reviewer-suggestion graph never calls this model strategy, so all recovery-only settings are rejected there rather than displayed as effective configuration. Parity and bounded-candidate behavior are pinned by `tests/test_evidence_recovery_closed_choice.py` and `tests/test_evidence_recovery_pipeline.py`.

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

`_execute_metadata_tasks()` no longer decides how a metadata group's model call runs. It resolves the `corpus_metadata_enrichment` assignment once per Record and runs each group through `EnrichmentSession` in `api/app/pipelines/corpus_metadata_enrichment.py`. The active built-in `corpus.metadata_enrichment.current@2` gives `llm.structured_metadata` one primary-provider attempt and follows the error/timeout edge to one review-provider attempt when configured. Version 1 preserves the historical 2+2 chain as a disabled built-in for reproducibility. `_chat_json()` takes `roles` and `escalated` so one stage runs one provider role; its default chain is unchanged for callers that have not migrated (page-marker choice, the text-noise second reader, schema preview, evidence recovery's closed-choice callback).

- Classification: provider role and attempts are pipeline settings. The correction/escalation prompt notes, the growing token budget, not retrying a timed-out provider, and the per-family `max_tokens`/timeouts from build settings stay server policy. The schema-derived prompt and response model, family routing (fast/deep, human-owned, adaptive skip, settle), reconciliation, evidence and autofill stay domain code outside the pipeline.
- The compiler accepts one terminal structured stage with at most one terminal escalation stage on the other provider role. A review stage without a configured review provider is `unavailable`; with no edge, the primary failure is reported exactly as before.
- Precedent retrieval for the prompt stays on its own `metadata_precedents` assignment; it is not a stage of this pipeline.
- An unresolvable assignment fails the family with the reason before any model call; there is no hidden default.
- Parity is pinned by `tests/test_corpus_metadata_enrichment_pipeline.py`, which runs the same scripted provider through the legacy chain and the pipeline and compares calls, prompts, token budgets, results and error text. Existing enrichment tests pass with only their `_chat_json` stub signatures widened to accept the new keywords.
- One trace per Record (also on cancellation); each family's `metadata_execution_ledger` entry carries the pipeline identity, trace ID and the stages that ran. Traces carry provider, model, attempts, response-contract names and failure codes, never prompts or answers. The Corpus Builder does not display the identity yet.
- Pipeline Studio renders enumerated settings (such as `provider_role`) as a choice list.

### 4.15 Corpus Builder boundary questions moved onto pipeline runtime

The two boundary questions segmentation asks a model now run through the `corpus_segmentation` assignment (built-in `corpus.segmentation.current@1`: `llm.boundary_classification` on the primary provider, 2 attempts, escalating on error or timeout to the review provider, 2 attempts, the same chain `_chat_json()` ran before). Both calls sit in `corpus_segmentation_execution.py`:

- the batch classifier (`_segment_candidate_batch`, `derridai_boundary_batch_v6`), reached from `_segment()`; one trace per segmentation pass, and each cached `local_boundary_state` decision carries the pipeline identity;
- the second reader (`_adjudicate_record_boundary_pair`, `derridai_boundary_second_reader_v1`); one trace per build audit pass (`_audit_suspicious_record_boundaries`), and one per reviewer request from `adjudicate_record_boundary`. The reviewer path is in this slice because it is the same call; it is a boundary question, not the closed-choice evidence choice of Phase B slice 5. Each verdict (`boundary_llm_after`/`boundary_llm_before` and `boundary_second_reader_history`) carries the pipeline identity.

- The runtime is shared with enrichment: `pipelines/structured_llm_stage.py` holds the compiler, session and trace code; `corpus_metadata_enrichment.py` and `corpus_segmentation.py` only name their feature, purpose and strategy. `_provider_roles()` moved to `corpus_llm_helpers.py`.
- Classification: provider role and attempts are pipeline settings. Deterministic candidate routing, the adjudication budget, batch size, block-ID validation, the `min_boundary_confidence` threshold (0.72), text conservation, and the rule that a failed, omitted or low-confidence answer keeps the boundary are domain policy, not Studio settings. Prompt text, token budgets and timeouts stay server policy.
- An unresolvable assignment asks no model: the pass keeps every ambiguous transition, counts it as a classifier failure, adds one build warning, and does not cache those decisions, so a later run asks again. A second-reader verdict becomes `uncertain` with the error.
- The boundary cache fingerprint is unchanged (prompt version, block text, the request's provider/model, generation settings). It does not include the pipeline, so a cached answer is reused after an assignment change, as it already was when the review provider had answered.
- `_segment_pair`, `_segment_window_recursive` and `_compact_segment_prompt` were removed with their response models (`derridai_boundary_pair`, `derridai_semantic_boundaries_compact`): no production path reached them. `tests/test_prompt_author_neutrality.py` now checks the two live boundary prompts instead.
- Parity is pinned by `tests/test_corpus_segmentation_pipeline.py` (scripted provider, both calls, legacy chain against pipeline: calls, prompts, token budgets, results and error text). Existing segmentation tests pass unchanged.

### 4.16 Corpus Builder document manifest moved onto pipeline runtime

`_document_manifest()` in `corpus_builder.py` asks its one model call through the `corpus_document_manifest` assignment (built-in `corpus.document_manifest.current@1`: `llm.document_manifest` on the primary provider, 2 attempts, escalating on error or timeout to the review provider, 2 attempts, the same chain `_chat_json()` ran before). `pipelines/corpus_document_manifest.py` only names the feature, purpose and strategy; the runtime is `structured_llm_stage.py`. Both callers go through it: the build's `structure` stage (`_run`, whose result is the `manifest` checkpoint) and the reviewer's **Analyse the document again** (`regenerate_manifest` in `corpus_manifest_workflow.py`). `corpus_manifest_workflow.py` has no direct model call for the manifest; its remaining `_chat_json()` call is `preview_schema_group`.

- Classification: provider role and attempts are pipeline settings. The whole-document sample, prompt, `manifest_num_predict` and timeouts stay server policy. The embedded-metadata fallback and the values that outrank the model (embedded PDF author, a start-page inference above 90%, reviewer-confirmed layout, media-specific page semantics, deterministic ingest metadata) are domain policy.
- One trace per analysis (also on cancellation). The identity goes in its own `document_manifest_pipeline` checkpoint (`runs`, last 20), not in the manifest: the manifest is sent verbatim in metadata-enrichment prompts, so a trace ID there would change every enrichment prompt.
- An unresolvable assignment asks no model. The analysis takes the existing embedded-metadata fallback and its build warning names the reason. As with any failed analysis, the fallback manifest is checkpointed; **Analyse the document again** retries.
- Not in this slice: `_catalog_enrich_manifest()` → `llm_tools.run_work_metadata_lookup()` asks a model to choose a catalogue candidate through `chat_complete()` directly (not `_chat_json()`). It is shared with the Works metadata lookup tool and still needs its own slice.
- Parity is pinned by `tests/test_corpus_document_manifest_pipeline.py` (scripted provider, legacy chain against pipeline: calls, prompts, token budgets, results and fallback warning text). Existing manifest tests pass unchanged.

### 4.17 Corpus Builder text touch-up moved onto pipeline runtime

`touchup_record_text()` in `corpus_builder.py` asks its model call through the `corpus_text_touchup` assignment (built-in `corpus.text_touchup.current@1`: `llm.text_touchup` on the primary provider, 2 attempts, escalating on error or timeout to the review provider, 2 attempts, the chain `_chat_json()` ran before). Both callers go through it: the reviewer's text touch-up route (which saves the proposal) and enrichment when the build sets `llm_touchup_during_enrichment`. `pipelines/corpus_text_touchup.py` only names the feature, purpose and strategy.

- Classification: provider role and attempts are pipeline settings. The prompt (`build_text_touchup_prompt`), its token budget and timeouts are server policy. Sanitizing against the source (`_sanitize_touchup_output`) and "a touch-up is a proposal until a reviewer approves it" are domain policy.
- One trace per proposal (also on failure and cancellation); the proposal, saved or made during enrichment, carries `pipeline` (identity, trace ID, stages that ran).
- An unresolvable assignment asks no model: the reviewer request fails with the reason (HTTP 422), and during enrichment the record gets the existing failed-proposal entry and build warning while enrichment continues.
- Not in this slice: the general Records touch-up (`llm.propose_touchup`, routes in `routers/llm.py` and `job_llm.py`) is a different feature (`record.touchup` in the remaining-migration plan) and still calls the model directly.
- Parity is pinned by `tests/test_corpus_text_touchup_pipeline.py`.

### 4.18 Reviewer "Ask the model" evidence choice moved onto pipeline runtime

`suggest_evidence_llm()` in `corpus_review_actions.py`, the Evidence tab's **Ask the model**, asks its closed-choice question through a separate `corpus_reviewer_evidence_choice` assignment (built-in `corpus.reviewer_evidence_choice.current@1`: `llm.reviewer_evidence_choice` on the primary provider, 2 attempts, escalating on error or timeout to the review provider, 2 attempts, the chain `_chat_json()` ran before). This is design 2 of the remaining-migration plan: a separate feature whose only model strategy is closed choice over the Record's current source-unit IDs.

- It has its own strategy rather than configuring `llm.closed_choice_evidence`: that strategy has no settings, and giving it `provider_role`/`attempts` would show editable values in the reviewer-suggestion graph (which never calls a model; its closed-choice stage is skipped) and in evidence recovery (which calls it through its own callback), where nothing would apply them.
- Classification: provider role and attempts are pipeline settings. The prompt (`llm_prompt`), 800-token budget and timeouts are server policy. Block-ID validation and lexical-support flagging (`validate_llm_choice`) and "advisory until the reviewer binds it" are domain policy.
- One trace per request; each returned suggestion carries `pipeline`. An unresolvable assignment asks no model and the request fails with the reason (HTTP 422).
- Not in this slice: evidence recovery's closed-choice callback during enrichment (`_evidence_llm_choice` in `corpus_metadata_enrichment_execution.py`) still runs the default `_chat_json()` chain inside the recovery stage; its provider role and attempts are not yet stage settings.
- Parity is pinned by `tests/test_reviewer_evidence_choice_pipeline.py`.

### 4.19 Workflow semantics: purposes, scholarly effects and Pipeline Studio information architecture

Pipeline purpose, strategy family and scholarly effect are now separate server-owned dimensions (see [Architecture → Pipeline semantics](ARCHITECTURE.md#pipeline-semantics)).

- `pipelines/purposes.py` registers each purpose's workflow category, consuming feature, input/output/authority semantics and required guarantees, plus closed vocabularies (categories, guarantees, phases, scholarly effects, effect notes) with locale keys. `pipelines/workflows.py` maps each purpose to its one adapter and replaces the manager's two `if` chains; adapters' strategy allowlists are module constants (`SUPPORTED_STRATEGIES`, `memory.supported_strategies()`).
- A new purpose needs: a `PipelinePurposeSpec`, a `PURPOSE_ADAPTERS` entry, en-US/fr-CA keys for its six texts, and a regenerated Storybook/Vitest catalog fixture.
- A new strategy must declare `scholarly_effect`; its phase and effect note derive from family and effect.
- Stories and Vitest read `web/src/components/pipelines/fixtures/pipelineCatalogContract.json`, a generated copy of the served purposes, vocabularies and strategies. After changing any of them run `python scripts/export_pipeline_catalog_fixture.py`; `--check` (and `tests/test_pipeline_catalog_fixture.py`) fails with that command while the fixture is stale. Like the GraphQL SDL, its exact bytes are generated, so it is excluded from Prettier.
- Classification: `evidence_suggestion`, `evidence_recovery`, `precedent_evidence_remap` and `corpus_reviewer_evidence_choice` are Evidence; `metadata_precedents`, `metadata_prefill` and `corpus_metadata_enrichment` are Metadata; `corpus_document_manifest`, `corpus_segmentation` and `corpus_text_touchup` are Corpus processing.
- Behavior changes: assignment rejects a pipeline whose purpose is not the one the feature consumes, and validation rejects an unregistered purpose. Run history and metrics accept `category`.

## 5. Current built-in assignments

As of current `master`, built-in system assignments are:

| Feature                      | Assigned pipeline                           | Status |
| ---------------------------- | ------------------------------------------- | ------ |
| Research                     | `research.current@1`                        | active |
| Reviewer evidence suggestion | `evidence.reviewer.current@2`               | active |
| Evidence recovery            | `evidence.recovery.cascade@2`               | active |
| Vector Store search          | `store_search.similarity@1`                 | active |
| Metadata pre-fill            | `metadata.prefill.current@1`                | active |
| Precedent evidence remapping | `precedent.remap.current@1`                 | active |
| Corpus metadata enrichment   | `corpus.metadata_enrichment.current@2`      | active |
| Corpus segmentation          | `corpus.segmentation.current@1`             | active |
| Corpus document manifest     | `corpus.document_manifest.current@1`        | active |
| Corpus text touch-up         | `corpus.text_touchup.current@1`             | active |
| Reviewer evidence choice     | `corpus.reviewer_evidence_choice.current@1` | active |
| Metadata precedents          | `metadata.precedents.current@1`             | active |
| Validated claim memory       | `memory.claim.current@1`                    | active |
| Prior response memory        | `memory.response.current@1`                 | active |

There are also important draft/legacy definitions:

- `research.balanced@1` — draft target architecture;
- `evidence.reviewer.current@1` — disabled legacy reviewer chain;
- `corpus.metadata_enrichment.current@1` — disabled legacy 2+2 retry chain;
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

1. **Dry-run pipeline testing** — merged in PR #281 for Research retrieval/context.
2. **A/B pipeline comparison** — merged in PR #281 for Research retrieval/context.
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

Corpus Builder metadata enrichment migrated in section 4.14, segmentation's boundary questions in section 4.15, the document manifest in section 4.16, text touch-up in section 4.17 and the reviewer's **Ask the model** evidence choice in section 4.18; evidence recovery's closed-choice stage now applies its own provider role and attempts (section 4.10). Still calling a model directly: `page_marker_chooser`, `_llm_text_noise_pass` and `preview_schema_group` (`_chat_json()`), the catalogue-match lookup `llm_tools.run_work_metadata_lookup()` and the Records touch-up `llm.propose_touchup()` (`chat_complete()`). Planned: page-marker choice and the text-noise second reader as small slices of their own; the schema preview moves onto the `corpus_metadata_enrichment` pipeline so it runs like a build.

Only claim that acceptance criterion “every generative LLM call resolves through a pipeline” is met after a fresh call-site audit.

### 8.5 Research default algorithm

The target `research.balanced@1` graph exists as data, but the production assignment intentionally remains `research.current@1`.

Changing that assignment is a quality decision and must follow controlled comparisons/benchmarks, not architectural preference alone.

### 8.6 Finishing the remaining direct model calls

Every slice follows the pattern of sections 4.14–4.18 unless a subsection below says otherwise:

- **Feature module.** Add `pipelines/<feature>.py` declaring a `StructuredStageFeature` (feature, purpose, strategy, label), a `compile_*` wrapper around `compile_structured_stage_pipeline`, and a `*Session` whose `open()` returns `open_for(SPEC)`. Copy `pipelines/corpus_text_touchup.py`.
- **Call site.** Build an `invoke(role, attempts, escalated)` that raises `LookupError` for an unconfigured role, open the session, call `session.run(invoke, response_contract=..., providers=...)`, and `finish()` it on success, failure and cancellation (`cancelled=True`). Convert the `RuntimeError` from `open()` into the caller's normal failure path. Examples: `touchup_record_text` and `suggest_evidence_llm`.
- **Wiring.** A registry `StrategySpec` with `provider_role` (enum) and `attempts` (1–4) settings; a built-in pipeline and assignment in `defaults.py` that reproduce the current behaviour exactly; both branches in `manager.py` (assignment compile and `runtime_support`); `featureForPurpose` in `SystemDataPipelines.vue`; the label in `pipelinePresentation.ts`; the purpose and strategy keys in `en_us.py`, `fr_ca.py` and `web/src/i18n/enUsDefaults.json` (Python locale strings are single-quoted: no apostrophes); a row in the `it.each` of `web/tests/frontend/system-data-pipelines.test.ts`; a bullet in `docs/USER_GUIDE.md`; a section 4.x here and a row in section 5.
- **Tests.** A parity file like `tests/test_corpus_text_touchup_pipeline.py`: script `chat_complete`, run the pipeline, run the legacy call with the pipeline's recorded prompt, compare calls, token budgets, results and error text; then the built-in compiles and is assigned, identity and trace, a review-first clone (when the feature has a review role), an unresolvable assignment makes no model call, and cancellation. Stash the frontend wiring once to show the Vitest row fails without it.
- **Identity.** Put it on the result the reviewer sees. Never put it in anything that is later pasted into a prompt (see the manifest, section 4.16).
- **Default cost.** A built-in must make exactly the calls the legacy code makes. Ask before changing any default assignment.

#### 8.6.1 Already decided

- `corpus_builder.py` `page_marker_chooser` (`page_marker_choice`, two attempts, ingestion time, called from `routers/corpus.py`): its own small slice with the standard pattern.
- `corpus_builder.py` `_llm_text_noise_pass` (`derridai_text_noise`, per flagged record during a build): its own small `text_noise` slice. Open one session for the pass (one trace), like the segmentation second reader. An unresolvable assignment keeps the deterministic scores and adds one build warning.
- `corpus_manifest_workflow.py` `preview_schema_group` (run=true): send it through the existing `corpus_metadata_enrichment` pipeline (`EnrichmentSession`), not a new feature, so a schema preview runs like a build.

#### 8.6.2 Evidence recovery's closed-choice call

Done (section 4.10). The plan below is kept as the record of what was decided.

Where: `_evidence_llm_choice` in `corpus_metadata_enrichment_execution.py` is passed as `llm_choice` to `execute_evidence_recovery()`; the recovery runtime (`pipelines/evidence_recovery.py`, `_Run._llm`) calls it when the graph reaches an `llm.closed_choice_evidence` stage. The callback runs the full default `_chat_json()` chain (primary ×2, then review ×2). The reviewer's Evidence-tab recovery (`corpus_review_actions.py`, around `execute_evidence_recovery(..., llm_choice=None)`) never calls a model.

This is not a new feature. The call is already a stage of the `evidence_recovery` graph, so the fix is to make that stage's settings authoritative:

1. Give `llm.closed_choice_evidence` a `config_schema` with `provider_role` (enum `chain`, `primary`, `review`; default `chain`) and `attempts` (1–4, default 2). `chain` means today's behaviour (primary, then review). Existing built-ins set neither key, so `evidence.recovery.celf@1` and `evidence.recovery.cascade@1` keep their behaviour without a version bump.
2. Change the callback to `llm_choice(prompt, role, attempts)`: `_Run._llm` reads the stage's `config` (it is already passed in) and the callback calls `_chat_json(..., attempts=attempts, roles=("primary", "review") if role == "chain" else (role,))`. Map a missing role (`LookupError`) to `_Outcome("unavailable", ...)` and an exception with a true `timed_out` attribute to `_Outcome("timed_out", ...)` (today every failure is `failed`), so the graph's `on_unavailable`/`on_timeout` edges decide what follows. Record the answering role's provider and model in the stage observation (today it always records the primary).
3. A clone can then express primary → review escalation as two `llm.closed_choice_evidence` stages joined by `on_error`/`on_timeout`; the recovery compiler already allows more than one such stage. Check that `compile_recovery_pipeline` still marks the chain cELF-compliant.
4. The reviewer-suggestion graph (`pipelines/evidence.py`) never calls the model, so these keys must not look editable there. Add `"llm.closed_choice_evidence": frozenset({"provider_role", "attempts"})` to `RECOVERY_ONLY_CONFIG` in `registry.py`; `reject_unhonoured_config` (called by `compile_evidence_pipeline`) then rejects them. The recovery compiler does not call `reject_unhonoured_config`, so recovery keeps them.
5. Tests: extend the recovery tests with a scripted provider. Parity is the existing built-ins with no config (identical calls). Also cover a clone with `provider_role: review` answering first, a two-stage escalation, the key being rejected in a reviewer-suggestion pipeline, and `evidence_cascade_llm_enabled=false` still skipping the stage.
6. Docs: extend section 4.10 (not a new 4.x), plus the evidence-recovery paragraph of `docs/USER_GUIDE.md`.

#### 8.6.3 Records touch-up (`llm.propose_touchup`)

Where: `propose_touchup()` in `api/app/llm.py`, called by `POST /api/llm/touchup` (`routers/llm.py`) and by the background touch-up job (`job_llm.py`, one call per record). This is the Records tool's metadata or text touch-up, not the Corpus Builder touch-up of section 4.17 (the remaining-migration plan calls it `record.touchup`). It does not use `_chat_json()`: `_propose_ollama` and `_propose_openai` stream one request each over `httpx`, `_parse_proposal` validates it, and any failure raises `TouchupFailure(status_code, message)`. The request names one provider and model; there is no review provider.

1. Feature `record_touchup`, strategy `llm.record_touchup`, built-in `record.touchup.current@1`: one stage, `provider_role` enum `["primary"]` only, `attempts` default **1** (range 1–3), no escalation. That is today's behaviour exactly.
2. Wrap the provider branch in an invoker: `providers={"primary": (provider, selected_model)}`; retry only a response that failed `_parse_proposal` validation, never a timeout or transport error (server policy, as in `_chat_json`). Map the session's failures back to the same `TouchupFailure` status codes and messages, so the API and job errors don't change.
3. One trace per proposal: the route opens a session per request, the job one per record. Add an optional `pipeline` field to `TouchupResponse` (and its TypeScript type) and to the job's per-record result. That changes the public API schema, so update `tests/test_frontend_api_contract.py` and run `pytest -m contract`.
4. An unresolvable assignment makes no model call and raises `TouchupFailure(503, "The record touch-up pipeline is unavailable: …")`. The job records it per record, as it does other failures.
5. Parity test: monkeypatch `httpx.Client` (or the two `_propose_*` functions' transport) with scripted streamed replies; compare requests and `TouchupFailure` codes between legacy and pipeline for success, an invalid answer, a timeout and a transport error.

#### 8.6.4 Catalogue-match lookup (`run_work_metadata_lookup`)

Where: `run_work_metadata_lookup()` in `api/app/llm_tools.py` fetches catalogue candidates deterministically (`_multi_catalog_candidates`), then makes one `chat_complete()` call (384 tokens, JSON mode) asking which candidate matches, and copies bibliographic values from the chosen record deterministically. Callers: `_catalog_enrich_manifest()` in `corpus_builder.py` (every build and every **Analyse the document again**, unless `auto_enrich_work_metadata` is false) and the Works metadata lookup job (`run_work_metadata_batch` via `job_tools.py`). There is no retry, and an unparseable answer is treated as "no reliable match", not as an error.

1. Feature `work_metadata_match`, strategy `llm.catalogue_match`, built-in `work_metadata.match.current@1`: one stage, `provider_role` enum `["primary"]`, `attempts` default **1**, no escalation (`WorkMetadataRequest` has no review provider). Parity requires attempts 1 and the lenient `_extract_json` behaviour; a retry on an unparseable answer would be a new model call and a default cost increase.
2. Only the `chat_complete` call goes in the invoker. Candidate retrieval, the "no adapter configured" early return (which makes no model call and records no trace), index validation, `applicable_fields_for` and value copying stay domain code.
3. Identity goes on the proposal (`pipeline`). **Not** in the manifest: `_catalog_enrich_manifest` writes `catalog_metadata` into the manifest, which is sent verbatim in enrichment prompts. Append the identity to the `document_manifest_pipeline` checkpoint as a second run kind (e.g. `{"kind": "catalogue_match", ...}`), or give it its own checkpoint.
4. Unresolvable assignment: no model call; the manifest path takes its existing "Automatic bibliographic lookup was unavailable" warning; the Works batch records the error per work, as it does now.
5. Parity test: monkeypatch `llm_tools.chat_complete` and `_multi_catalog_candidates`; cover a match, `candidate_index: -1`, an unparseable answer and a provider exception, through both callers.

#### 8.6.5 After these

Re-run the generative-call audit (Step 4 of section 10): `grep -rn "chat_complete(\|_chat_json(" api/app` and account for every hit as a pipeline stage or a documented operational exception (for example provider warm-up or model probes in `llm.py`). Only then mark criterion 4 in section 9.

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

PR #281 is merged. The Corpus Builder model calls (section 8.6) are being finished first; then continue in this order.

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

General Vector Store search, metadata pre-fill and precedent evidence remapping are done (sections 4.11–4.13). Create a fresh checklist from the original audit and current code. Prioritize:

1. any remaining direct CrossEncoder caller (re-check the `predict_scores()` callers in `rag.py` and `metadata_exemplar_retrieval.py`);
2. any vector-search caller not resolving an assignment/version.

The migration pattern should be the same as the successful earlier work:

- compile a bounded typed plan;
- keep domain authority outside the configurable graph;
- execute through registered strategies;
- attach exact pipeline identity;
- retain safe stage/candidate telemetry;
- add point-of-use trace where a researcher would need to audit the result.

### Step 4 — Re-audit generative LLM call sites

Finish section 8.6 first, then repeat the “complete generative LLM-query inventory” section of the original audit against current `master`.

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

1. fetch current `master`; confirm PR #312 (manifest, text touch-up, reviewer evidence choice) has merged, or finish its review first;
2. read section 8.6 and pick the next call. Evidence recovery (8.6.2) is done; suggested order for the rest: the three already-decided small slices (8.6.1), then the Records touch-up (8.6.3) and the catalogue match (8.6.4);
3. branch each slice from `master` and open its PR against `master`;
4. run the full quality gates before reporting a slice done, and state in the PR which were not run;
5. after section 8.6, run the generative-call audit (section 8.6.5), then benchmark integration (section 10, Step 1).

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

## Adaptive metadata routing execution foundation (2026-10-04)

The revised candidate-routing plan requires Pipeline Studio to own the executable graph. The first checkpoint adds `graph_execution.py`, a server-handler runtime over the existing named-port wiring resolver. It supports repeated strategy instances, named branch outputs, definition-stable fan-in, explicit fallback input delivery, empty required-input skips, cancellation propagation, immutable definition/strategy snapshots, and safe count/configuration-hash telemetry. Multiple input ports receive ordered artifacts; handlers own payload merging and domain validation.

This checkpoint does not change production assignments or built-in versions. Historical metadata enrichment `@1` and `@2` have fake-provider graph characterization coverage for their primary attempt budgets and review-provider escalation. Existing enrichment sessions still use their historical adapter. The runtime currently schedules serially; declared concurrency capabilities, semantic artifact traits, terminal guarantee validation, and migration of the enrichment adapter remain prerequisites before activating adaptive routing.

Next implement metadata artifact/trait contracts and purpose-terminal guarantees, then migrate the historical enrichment path with full provider/evidence/reconciliation parity. Follow with candidate collection, current-record support, and observe-only routing before enabling RESOLVE or VERIFY. Preserve human ownership and current-source evidence at the canonical boundary. Do not claim the 33% latency gate until fixed-corpus A/B runs and reviewer quality checks demonstrate it.

Baseline is `master` at `94ca23d9`. PR #508's fetched head is `a59aac51`; it adds Research stage-configuration overrides and changes shared pipeline models/service. This checkpoint avoids those files and must be checked against the eventual merge of #508 before extending shared contracts.

Validation: 72 focused graph/wiring/contracts/workflow tests passed. Ruff checks passed for the new implementation and tests. Broader enrichment collection is unavailable in the bundled environment because PyMuPDF is missing; storage-related expansion also lacks Chroma. Full preflight, real-provider latency benchmarks, reviewer quality comparisons, and CI are not established by this checkpoint.
