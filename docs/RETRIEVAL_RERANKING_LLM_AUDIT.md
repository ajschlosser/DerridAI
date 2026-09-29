# Retrieval, Reranking, and LLM Query Audit

**Repository:** `ajschlosser/DerridAI`  
**Branch audited:** `master`  
**Master commit at audit time:** `a6c00f77fd1193d3c3fe0a88100a49d038afb972`  
**Audit date:** 2026-09-28 / 2026-09-29 UTC boundary

## Purpose

This document inventories the current DerridAI production paths that:

1. perform vector or semantic retrieval;
2. perform reranking, cross-encoding, rank fusion, or MMR selection; and
3. query generative LLMs.

It also proposes a future architecture in which retrieval, reranking, model invocation, evidence validation, and context construction are explicit, inspectable, configurable pipeline stages rather than partly hard-coded behavior scattered across feature-specific code.

The audit focuses on production code rather than tests and documentation. The principal implementation files reviewed include:

- `api/app/evidence_suggestions.py`
- `api/app/chroma_store.py`
- `api/app/rag.py`
- `api/app/cross_encoder.py`
- `api/app/metadata_exemplar_retrieval.py`
- `api/app/memory_prefill.py`
- `api/app/claim_memory.py`
- `api/app/research_memory.py`
- `api/app/source_embeddings.py`
- `api/app/system_chroma_console.py`
- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/corpus_review_actions.py`
- `api/app/corpus_segmentation_execution.py`
- `api/app/corpus_manifest_workflow.py`
- `api/app/corpus_builder.py`
- `api/app/llm.py`
- `api/app/llm_tools.py`
- `api/app/i18n_translation.py`
- `api/app/content_policy_generation.py`

---

## Executive summary

DerridAI does **not** use one uniform retrieval strategy.

For evidence suggestion, the current system uses both similarity and MMR, but in different paths:

- reviewer-facing semantic evidence suggestion uses lexical matching plus cosine similarity;
- automatic missing-evidence recovery uses lexical matching, semantic similarity, optional cross-encoder reranking, MMR fallback, and finally an optional LLM closed-choice step;
- metadata precedent retrieval uses semantic + lexical scoring, optional cross-encoder reranking, and MMR as the final diversity-selection stage;
- Research/RAG builds one dense candidate pool, exposes similarity and MMR as parallel retrieval legs, adds a lexical leg, fuses results with reciprocal-rank fusion, and then optionally cross-encoder-reranks the fused pool.

Therefore, "MMR or similarity?" is not a binary system-wide question. DerridAI already uses both, but the ordering and semantics differ by workflow.

The strongest current design is metadata precedent retrieval:

```text
filtered candidate generation
    -> semantic + lexical scoring
    -> bounded cross-encoder reranking
    -> field/kind quota preservation
    -> MMR diversity selection
    -> prompt packet construction
```

That architecture is close to the direction DerridAI should standardize on.

For evidence spans, however, MMR should not become the principal relevance mechanism. Evidence acquisition asks which exact source spans directly support a proposition or metadata value. Two adjacent, semantically similar passages may both be required to establish a claim, so a diversity penalty can suppress genuinely necessary evidence. The preferred evidence path is therefore:

```text
deterministic lexical support
    -> broad semantic candidate generation
    -> support-aware reranking
    -> evidence sufficiency / entailment validation
    -> optional diversity only among alternate suggestions
```

For Research/RAG, the current ordering can also be improved. A cleaner default would be:

```text
dense + lexical candidate generation
    -> rank fusion
    -> cross-encoder relevance reranking
    -> final diversity/context-packing constraints
    -> evidence packet
    -> generation
```

rather than using similarity and MMR as partly redundant parallel legs before a cross-encoder that can subsequently undo the diversity MMR introduced.

A broader architectural recommendation follows from the audit: DerridAI should expose these choices through a single typed **pipeline contract and strategy registry**, with every execution producing an auditable stage trace. The application should make it possible to answer, at any time:

- Which retrieval chain is configured for this feature?
- Which exact stages ran?
- Which stages were skipped, fell back, timed out, or failed open?
- Which provider/model/index/collection was used?
- What candidate counts entered and left each stage?
- Which scores caused a candidate to advance or be rejected?
- Which final evidence/context items were selected and why?
- Which LLM calls were made, using which prompt/schema/provider/model?
- Which defaults were inherited and which values were overridden?
- What would change if a different chain were selected?

---

# Part I — Current state

## Evidence suggestion: current behavior

There are two materially different evidence-suggestion paths.

### Reviewer-facing semantic evidence suggestion

`api/app/corpus_review_actions.py` calls `suggest_evidence_blocks_semantic()` in `api/app/evidence_suggestions.py`.

That path:

1. performs deterministic lexical matching;
2. constructs a field-aware semantic query with `semantic_query()`;
3. synchronizes source-unit embeddings through `SourceEmbeddingProjection`;
4. embeds the query;
5. calculates cosine similarity between the query vector and each source-unit vector;
6. preserves lexical and semantic signals separately;
7. uses the stronger of the lexical or semantic score as the top-level score;
8. sorts by that score and returns the top candidates.

It does **not** use MMR.

It also does **not** use the cross-encoder.

So reviewer-facing "Suggest spans"/semantic evidence suggestion is currently a lexical + cosine-similarity ranking path.

### Automatic missing-evidence recovery

`api/app/corpus_metadata_enrichment_execution.py` calls `suggest_evidence_cascade()` from `api/app/evidence_suggestions.py`.

Its ordered fallback is:

```text
deterministic lexical match
    -> dense semantic candidates
    -> cross-encoder rerank
    -> MMR / similarity fallback
    -> optional LLM closed-choice selection
```

More specifically:

1. strong deterministic lexical support wins immediately;
2. otherwise the system creates a field-aware semantic query;
3. source-unit embeddings are loaded/generated and cosine similarity is computed;
4. candidates are sorted by cosine score;
5. when `METADATA_CROSS_ENCODER_ENABLED` is enabled, the bounded top-K candidates are passed to the shared `predict_scores()` cross-encoder boundary;
6. if that produces usable positive candidates, the cascade returns them;
7. otherwise, if semantic similarity reaches the minimum threshold, `_mmr_select()` chooses up to the configured evidence limit;
8. if enabled, the last fallback asks the generative model to select from a closed list of source block IDs and validates those IDs against the actual candidates.

The relevant defaults in `api/app/config.py` are:

- metadata cross-encoder enabled: `True`;
- metadata cross-encoder top-K: default `8`, hard-capped at `32`;
- evidence-cascade LLM fallback enabled: `True`;
- evidence MMR lambda: `0.72`.

Therefore, in the ordinary default configuration, MMR is generally **not** the first semantic selector in the automatic evidence cascade. The cross-encoder gets the first opportunity to resolve the dense candidate set.

### Precedent evidence remapping

`api/app/metadata_precedents_cache.py` uses `rank_blocks_for_texts()` in `api/app/evidence_suggestions.py` to map previously reviewed evidence text onto source blocks in the current record.

This path:

- uses embedding cosine similarity when an embedding function is available;
- falls back to conservative token-overlap ranking otherwise;
- does not use MMR;
- does not use the cross-encoder.

### Current evidence-suggestion matrix

| Evidence operation                                      | Current retrieval/selection behavior                                                               |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Reviewer semantic "Suggest spans/evidence"              | Lexical + cosine similarity; no MMR; no cross-encoder                                              |
| Automatic evidence recovery during enrichment           | Lexical -> cosine candidates -> cross-encoder -> MMR fallback -> optional LLM                      |
| Mapping reviewed precedent evidence onto current record | Cosine similarity with lexical fallback; no MMR; no cross-encoder                                  |
| Explicit reviewer "ask LLM to choose evidence"          | Closed-choice LLM over this record's actual source blocks, followed by deterministic ID validation |

---

## Complete vector-search / semantic-retrieval inventory

The following are production areas in which DerridAI performs vector retrieval or source/query embedding comparisons.

### 1. Research/RAG corpus retrieval

**Primary files**

- `api/app/rag.py`
- `api/app/chroma_store.py`

**Key functions**

- `run_rag_pipeline()`
- `ChromaStore.semantic_candidates()`
- `ChromaStore.lexical_search()`
- `_mmr_select()`

**Behavior**

A dense Chroma candidate pool is fetched once per collection when either the `similarity` or `mmr` route is requested.

That same dense pool then feeds:

- a similarity leg;
- an MMR leg.

A separate deterministic lexical/BM25-style leg is also available.

The resulting retrieval hits are deduplicated by logical record ID and fused with reciprocal-rank fusion (RRF). User-selected evidence is pinned and cannot be removed by reranking.

The fused retrieved pool is then reranked by one of:

- cross-encoder;
- lexical/vector fallback;
- none.

Research therefore currently uses:

```text
dense candidate generation
    -> similarity leg
    -> MMR leg
    -> lexical leg
    -> RRF fusion/deduplication
    -> cross-encoder or lexical final rerank
    -> provenance/evidence sufficiency filtering
    -> evidence packet
```

### 2. Vector Stores / database search

**Primary files**

- `api/app/chroma_store.py`
- `api/app/routers/stores.py`

**Modes**

- similarity;
- MMR;
- hybrid;
- lexical/keyword/filter paths.

`ChromaStore.search()` is ordinary embedding similarity search.

`ChromaStore.mmr_search()`:

- fetches a larger semantic candidate set;
- requests candidate embeddings from Chroma;
- uses relevance minus embedding similarity to already selected candidates;
- returns an `mmr_score`.

`ChromaStore.hybrid_search()`:

- executes dense semantic search;
- executes deterministic BM25-style lexical search;
- fuses the ranks using reciprocal-rank fusion;
- does not invoke the cross-encoder.

### 3. Reviewer evidence suggestion

**Primary files**

- `api/app/corpus_review_actions.py`
- `api/app/evidence_suggestions.py`
- `api/app/source_embeddings.py`

The system embeds a field-aware evidence query and compares it against embeddings of source blocks belonging to the Record being reviewed.

Current selection is cosine similarity plus lexical support, without MMR or cross-encoding.

### 4. Automatic missing-evidence cascade

**Primary files**

- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/evidence_suggestions.py`
- `api/app/source_embeddings.py`
- `api/app/cross_encoder.py`

Source blocks are embedded and compared with a field-aware semantic query.

Selection can then proceed through:

- cross-encoder reranking;
- MMR;
- optional generative LLM closed-choice selection.

Candidates remain restricted to the current Record's source blocks.

### 5. Progressive metadata precedent retrieval

**Primary files**

- `api/app/metadata_exemplar_retrieval.py`
- `api/app/corpus_editorial_memory.py`

Reviewed metadata exemplars are stored in the derived `derridai_metadata_exemplars` Chroma collection.

Retrieval is filtered by relevant provenance/schema dimensions, including:

- build/scope;
- metadata field;
- schema ID;
- schema version;
- language.

A single query embedding is reused across bounded field-specific queries.

For each candidate, the current hybrid score is:

```text
0.8 * semantic_similarity + 0.2 * lexical_similarity
```

Candidates may then be cross-encoder-reranked.

After reranking, positive examples and corrections retain separate quotas, match tiers are preserved, and MMR is the final diversity-selection step.

This is currently the most complete staged retrieval pipeline in DerridAI.

### 6. Metadata prefill from reviewed precedent

**Primary file**

- `api/app/memory_prefill.py`

Current source spans are embedded through the source embedding projection and then used directly as Chroma query vectors against prior reviewed metadata exemplars.

The system:

- excludes exemplars from the current build;
- gathers similarity evidence from earlier reviewed records;
- groups support by field/value;
- requires sufficient multi-record precedent according to field policy;
- can create memory hints or prefill a field when policy allows.

This path uses similarity thresholds and support aggregation.

It does not use MMR.

It does not use the cross-encoder.

### 7. Precedent evidence remapping

**Primary files**

- `api/app/metadata_precedents_cache.py`
- `api/app/evidence_suggestions.py`

Reviewed precedent evidence text is compared with current-record source blocks using embedding cosine similarity. Token overlap is the fallback when embedding is unavailable.

No MMR or cross-encoder is used.

### 8. Validated-claim semantic memory

**Primary file**

- `api/app/claim_memory.py`

`ClaimMemoryIndex` is a derived vector projection of reviewer-validated generated claims.

`ClaimMemoryIndex.similar()`:

- embeds the claim text;
- performs owner-scoped Chroma similarity search;
- applies a minimum similarity threshold;
- excludes the current claim if requested.

The result is then rejoined to authoritative generated-claim rows and support bindings before being surfaced.

No MMR or cross-encoder is used.

### 9. Prior Research-response semantic memory

**Primary file**

- `api/app/research_memory.py`

`ResponseMemoryIndex` is a derived vector projection of eligible graded Research responses, keyed by the original question.

`ResponseMemoryIndex.similar()`:

- embeds the current question;
- performs owner-scoped Chroma similarity search;
- filters by minimum similarity;
- rejoins results to authoritative durable response-memory rows.

If semantic memory fails, the code visibly falls back to lexical overlap.

No MMR or cross-encoder is used.

### 10. Research prior-claim memory

Also in `api/app/research_memory.py`, `select_prior_claims()` uses the validated-claim semantic index described above.

Retrieved claims are rejoined to authority and their support bindings are checked against the evidence packet for the current Research run. Each support item is classified as:

- in current evidence;
- revised since validation;
- not in current evidence.

No MMR or cross-encoder is used.

### 11. System Data Chroma console

**Primary file**

- `api/app/system_chroma_console.py`

The administrative Chroma console supports semantic `query` operations over system collections.

For text queries it:

- resolves the collection embedding contract;
- embeds the query;
- sends the resulting vector to Chroma.

This is diagnostic/admin tooling rather than a scholarly retrieval workflow.

### Embedding infrastructure that is not itself search

`api/app/source_embeddings.py` provides `SourceEmbeddingProjection`.

It is shared infrastructure used by evidence suggestion, precedent remapping, and metadata prefill to persist, retrieve, or generate source-unit embeddings.

Embedding generation, projection synchronization, and embedding-health probes are not counted as independent search workflows in this audit.

---

## Complete cross-encoder and reranking inventory

There are currently **three production callers** of the shared `api/app/cross_encoder.py::predict_scores()` inference boundary.

### 1. Research/RAG final reranking

**File:** `api/app/rag.py`  
**Function:** `_cross_encoder_rerank()`

The cross-encoder scores pairs of:

```text
(research query, candidate record text)
```

It reranks the retrieved pool after retrieval fusion.

If the cross-encoder is unavailable or fails, Research falls open to `_lexical_rerank()`, which combines:

- query-token overlap;
- vector similarity derived from Chroma distance;
- a small retrieval-rank bonus.

### 2. Progressive metadata precedent reranking

**File:** `api/app/metadata_exemplar_retrieval.py`  
**Function:** `_rerank_candidates()`

A field-balanced bounded candidate set is passed through the cross-encoder.

Cross-encoder scores are added to candidate state and used to reorder the selected subset.

The pipeline then preserves:

- field quotas;
- positive/correction quotas;
- match tiers;

and finally applies MMR for diversity.

### 3. Automatic evidence-cascade reranking

**File:** `api/app/evidence_suggestions.py`  
**Function:** `suggest_evidence_cascade()`

The top semantic evidence candidates are cross-encoded as:

```text
(field-aware evidence query, source block text)
```

If usable candidates result, the cascade returns those candidates before reaching MMR.

### Shared cross-encoder implementation

**File:** `api/app/cross_encoder.py`

The shared implementation:

- uses `sentence_transformers.CrossEncoder`;
- caches models by model name;
- uses the configured model cache directory;
- bounds inference with a timeout;
- validates score count and finiteness;
- fails open with telemetry rather than crashing the calling workflow.

The default configured model is:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

This is a relevance reranker, not an evidentiary-entailment model. A high score should therefore be interpreted as pair relevance, not proof that a passage logically or textually warrants a metadata assertion.

### Other reranking/fusion mechanisms

DerridAI also uses several deterministic reranking mechanisms that are not cross-encoders:

- Research RRF fusion across retrieval legs;
- Research lexical/vector fallback reranking;
- MMR in Research;
- MMR in direct vector-store search;
- BM25-style lexical ranking in `ChromaStore.lexical_search()`;
- dense + lexical RRF in `ChromaStore.hybrid_search()`;
- 80/20 semantic/lexical hybrid scoring in metadata exemplar retrieval;
- MMR after metadata-exemplar reranking;
- similarity/threshold/support aggregation in memory prefill.

---

## Complete generative LLM-query inventory

At the transport level, generative model calls are concentrated in two implementation families:

1. `api/app/rag.py::chat_complete()`
2. `api/app/llm.py` through the general LLM review/touch-up provider paths.

Corpus Builder's `_chat_json()` is a typed, retrying, schema-validating wrapper around `chat_complete()`.

No third production chat/completions transport was identified in this audit.

### 1. Research query decomposition

**File:** `api/app/rag.py`  
**Function:** `run_rag_pipeline()`

When query decomposition is enabled, the generation model is asked to produce structured query metadata, including:

- prompt query;
- French prompt query;
- prompt instructions;
- response language.

Retrieval and reranking limits remain deterministic request controls rather than LLM decisions.

### 2. Research answer generation

**File:** `api/app/rag.py`

After retrieval, reranking, provenance filtering, evidence packet construction, and optional memory selection, `chat_complete()` generates the Research answer.

Research generation can stream draft deltas through the realtime layer; the authoritative result is the completed persisted answer.

### 3. RAG grading/evaluation

**File:** `api/app/llm_tools.py`  
**Function:** `run_rag_grade()`

The model grades a Research answer against its supplied evidence across categories including:

- query relevance;
- source binding;
- claim traceability;
- attribution/source discrimination;
- claim/evidence fidelity;
- conceptual precision;
- coverage;
- interpretive usefulness.

This is used both directly and by automatic/background grading flows.

### 4. General Record LLM review / auto-improve

**Files**

- `api/app/llm.py`
- `api/app/routers/llm.py`
- `api/app/job_llm.py`

`propose_touchup()` asks a configured Ollama or OpenAI-compatible model to propose bounded changes to requested Record fields.

It is used both synchronously and in background jobs.

### 5. Source-language detection

**File:** `api/app/llm_tools.py`  
**Function:** `run_pdf_llm(mode="detect_language")`

The model returns a language code, confidence, and source-grounded reason for a source excerpt.

### 6. Extracted-text cleanup

**File:** `api/app/llm_tools.py`  
**Function:** `run_pdf_llm(mode="clean_text")`

The model is asked to conservatively repair extraction artifacts while preserving wording and source structure.

### 7. Draft-record creation

**File:** `api/app/llm_tools.py`  
**Function:** `run_pdf_llm(mode="draft_record")`

The model creates a draft corpus Record from source text under source-grounding constraints.

### 8. Existing-record linking

**File:** `api/app/llm_tools.py`

For PDF/source linking, the model ranks a bounded preselected set of candidate Records and returns a candidate key/Record ID with confidence and explanation.

The model is not allowed to invent candidate IDs.

### 9. Document manifest inference

**File:** `api/app/corpus_builder.py`

A typed `_chat_json()` call establishes a source-bound document manifest from embedded file metadata, reviewed document structure, and a strategic source sample.

The deterministic source metadata remains authoritative where explicitly present.

### 10. Printed page-marker disambiguation

**File:** `api/app/corpus_builder.py`

A bounded closed-choice model task determines which suspicious short lines are printed page markers/folios.

### 11. Optional text-noise second opinion

**File:** `api/app/corpus_builder.py`

When configured, an LLM can provide an advisory text-noise assessment. The deterministic noise score remains the base signal and the LLM pass must not abort the build.

### 12. Semantic segmentation

**File:** `api/app/corpus_segmentation_execution.py`

The model is used in several segmentation/adjudication tasks:

- compact-window semantic boundary detection;
- pairwise boundary fallback;
- bounded batch classification of candidate transitions;
- boundary second-reader/audit for suspicious seams.

Prompts explicitly prohibit page boundaries and Record length from being treated as semantic evidence.

### 13. Corpus metadata enrichment

**File:** `api/app/corpus_metadata_enrichment_execution.py`

Metadata enrichment runs one structured model task per selected schema group.

Default/standard groups include:

- discourse;
- quotation;
- indexing.

Schemas can introduce additional groups.

Fast/deep routing can skip some groups according to configured policy and source signals.

The model responses are schema-generated and Pydantic-validated rather than accepted as arbitrary free text.

### 14. Automatic evidence-choice fallback

**Files**

- `api/app/corpus_metadata_enrichment_execution.py`
- `api/app/evidence_suggestions.py`

If lexical, cross-encoder, and semantic/MMR evidence recovery do not produce a usable result, the configured evidence cascade may ask the LLM to choose from the current Record's actual source-block IDs.

The answer is deterministically validated before use.

### 15. Explicit reviewer LLM evidence suggestion

**File:** `api/app/corpus_review_actions.py`  
**Function:** `suggest_evidence_llm()`

A reviewer can explicitly invoke the same style of closed-choice evidence task.

Returned block IDs are validated against the actual candidate set.

### 16. Record text touch-up

**File:** `api/app/corpus_builder.py`  
**Function:** `touchup_record_text()`

The model proposes source-conservative text cleanup. The result remains a proposal for review rather than an automatic rewrite of immutable source text.

### 17. Metadata schema preview

**File:** `api/app/corpus_manifest_workflow.py`  
**Function:** `preview_schema_group(..., run=True)`

A schema group can be previewed against arbitrary sample text. When `run=True`, the exact group prompt/response-model path is sent to the configured LLM.

### 18. Work/bibliographic metadata candidate matching

**File:** `api/app/llm_tools.py`  
**Function:** `run_work_metadata_lookup()`

Public catalogues provide deterministic candidate records first.

The LLM chooses the best candidate index or declines to choose.

DerridAI then copies bibliographic values deterministically from the selected catalogue record. The LLM does not generate the bibliographic values themselves.

### 19. UI language translation

**File:** `api/app/i18n_translation.py`  
**Function:** `translate_english_dictionary()`

The LLM translates batches of canonical English UI strings.

The workflow includes:

- structured batch translation;
- validation;
- retry/bisection;
- syntax repair handling;
- single-string plain-text fallback;
- placeholder preservation.

### 20. Language content-policy generation

**File:** `api/app/content_policy_generation.py`

The LLM generates candidate policy terms for an installed language and is then used again in a language-audit stage to validate that candidate terms actually belong to the target language.

### 21. Model warmup

**File:** `api/app/llm.py`  
**Function:** `warmup_model()`

This sends an inference request to load/warm a model.

It is operational model invocation rather than a scholarly reasoning task, but it is still a production LLM-query path.

### Typical call counts

An ordinary Research run can involve:

1. query-decomposition generation;
2. final answer generation;
3. optional post-run grading.

A Corpus Builder Record can involve multiple LLM calls because segmentation, metadata enrichment, evidence recovery, and optional review/touch-up tasks are intentionally separated rather than collapsed into one monolithic prompt.

---

# Part II — Assessment and proposed changes

## A. Preserve the strong staged design in metadata precedent retrieval

The metadata-exemplar pipeline is already close to the desired architectural pattern.

It separates:

- candidate generation;
- field/schema filtering;
- semantic scoring;
- lexical scoring;
- cross-encoder reranking;
- field/kind quota enforcement;
- diversity selection;
- prompt-packet construction.

MMR is especially appropriate **after** relevance reranking here because the final product is a small few-shot context packet. The system wants relevant precedents but does not want the entire prompt budget consumed by several nearly identical examples.

This path should be treated as a reference implementation for a shared retrieval contract.

## B. Do not make MMR the principal evidence-span relevance ranker

Evidence selection has a different objective from few-shot precedent selection.

The question is not merely:

> What passages are relevant and diverse?

It is:

> Which exact source spans directly support this proposition or metadata value?

Adjacent or highly similar source blocks may both be required to establish the support relation. A diversity penalty can therefore suppress necessary evidence.

Recommended evidence architecture:

```text
deterministic lexical support
    -> broad semantic candidate generation
    -> support-aware relevance reranking
    -> evidence sufficiency / entailment validation
    -> optional diversity among alternate evidence sets
```

MMR is useful for presenting alternate suggestions, but should not be treated as proof-oriented evidence validation.

## C. Unify reviewer evidence suggestion with the stronger automatic path

The reviewer-facing semantic suggestion path currently stops at lexical + cosine similarity, while the automatic cascade can use the cross-encoder and MMR.

This is an unnecessary divergence.

The reviewer-facing path should use the same shared candidate-generation and reranking primitives, while still exposing the individual signals and retaining reviewer control.

A unified candidate should be capable of reporting:

- lexical score;
- semantic similarity;
- cross-encoder score;
- MMR score, if used;
- support/entailment score, if configured;
- final selection stage/method;
- source-unit ID;
- source-document ID;
- provenance identity;
- fallback reason when a stage is unavailable.

## D. Treat cross-encoder relevance as relevance, not evidence entailment

The default `cross-encoder/ms-marco-MiniLM-L-6-v2` model is a relevance reranker.

Its output can improve candidate ordering, but it should not be treated as a determination that the source block actually warrants the asserted metadata value.

For evidence-sensitive workflows, the final support decision should remain deterministic or be delegated to a specifically designed support/entailment validator whose output is itself treated as advisory until provenance constraints pass.

## E. Simplify Research/RAG ordering

Current Research retrieval is approximately:

```text
dense pool
    -> similarity leg
    -> MMR leg
    -> lexical leg
    -> RRF
    -> cross-encoder
```

Similarity and MMR are partly redundant because they derive from the same dense pool.

The subsequent cross-encoder can also reorder candidates in a way that removes the diversity benefit MMR added earlier.

A cleaner default is:

```text
dense retrieval
    + lexical retrieval
    -> rank fusion
    -> cross-encoder relevance reranking
    -> final constrained diversity/context packing
```

The final diversity stage should preferably consider more than embedding similarity. Useful constraints include:

- logical `record_id`;
- work;
- source document;
- page/source-unit adjacency;
- overlapping source spans;
- duplicate quotations;
- discourse/attribution roles.

For scholarly RAG, avoiding six adjacent chunks from one passage is often more useful than generic embedding-space diversity alone.

## F. Keep claim memory and prior-response memory similarity-first

These memory workflows seek the closest prior precedent under authority and eligibility constraints.

They do not normally need a diverse packet.

Similarity-first retrieval with deterministic authority rejoin is appropriate.

MMR becomes useful only if multiple retrieved memories are going to be placed together into a bounded prompt context and redundancy becomes a real problem.

## G. Keep metadata prefill similarity/support-first

Metadata prefill is trying to discover stable precedent from earlier reviewed evidence, not generate a diverse retrieval set.

Its multi-record support aggregation and field-policy thresholds are more important than MMR.

The current approach is therefore appropriate in principle.

---

## Specific technical changes

### 1. Introduce one metric-aware relevance normalization contract

Several places convert Chroma distance to relevance with approximately:

```python
1.0 / (1.0 + max(0.0, distance))
```

Variants exist in:

- `api/app/rag.py`;
- `api/app/chroma_store.py`;
- `api/app/metadata_exemplar_retrieval.py`;
- memory-related helpers.

DerridAI supports multiple collection distance metrics, including cosine, L2, and inner product.

A generic nonnegative-distance transformation is not a correct universal normalization for all metrics. In particular, clamping negative values to zero can destroy information under inner-product semantics.

The collection retrieval contract should own a single metric-aware:

```text
distance/raw score -> normalized relevance
```

function.

All MMR, threshold, hybrid, display, and telemetry paths should use that shared normalization.

### 2. Consolidate duplicate MMR implementations

MMR logic currently exists independently in at least:

- `api/app/rag.py`;
- `api/app/chroma_store.py`;
- `api/app/metadata_exemplar_retrieval.py`;
- `api/app/evidence_suggestions.py`.

These implementations are similar but not identical.

Create one reusable selector with a typed candidate contract and explicit:

- relevance accessor;
- vector accessor;
- lambda;
- limit;
- tie-breaking policy;
- metric/normalization provenance;
- selected MMR objective score.

Feature-specific code should configure the shared primitive rather than reimplement it.

### 3. Preserve stage-specific score provenance

The evidence cascade currently uses an MMR objective internally but returns the source candidate's original semantic similarity as the top-level score.

That makes it difficult to know which score actually caused selection.

Do not collapse heterogeneous scores into one ambiguous `score`.

Use a structured score bundle such as:

```json
{
  "scores": {
    "lexical": 0.41,
    "semantic": 0.81,
    "cross_encoder": null,
    "mmr": 0.49,
    "support": null
  },
  "selected_by": "mmr",
  "strategy": "evidence-default-v2"
}
```

Every score should carry enough metadata to identify its model/method/version.

### 4. Create a shared retrieval-candidate type

Introduce a typed internal candidate representation rather than passing feature-specific loose dictionaries.

A candidate should be able to carry:

- candidate ID;
- logical Record ID;
- source-document ID;
- source-unit ID;
- collection/index ID;
- text or a safe text reference;
- metadata/provenance reference;
- embedding reference/vector when needed;
- retrieval hits by stage;
- raw distances;
- normalized relevance scores;
- lexical scores;
- fusion scores;
- reranker scores;
- diversity scores;
- support-validation scores;
- exclusion/selection reasons.

This becomes the common currency of retrieval stages.

### 5. Separate retrieval, reranking, validation, and packing

A retrieval stage should not silently become an evidence validator.

A reranker should not silently decide provenance sufficiency.

A diversity selector should not silently become a relevance threshold.

A context packer should not have to reconstruct why a candidate survived earlier stages.

Use explicit stage families:

1. **query transform**
2. **candidate generation**
3. **filter**
4. **score normalization**
5. **fusion**
6. **rerank**
7. **support/evidence validation**
8. **diversity selection**
9. **quota/constraint selection**
10. **context packing**
11. **LLM generation**
12. **post-generation validation/evaluation**

### 6. Add a support/entailment stage for evidence-sensitive chains

For evidence suggestion and automatic evidence binding, add an optional explicit support validator after broad relevance reranking.

The validator's job is narrower than the generic cross-encoder:

> Does this source span directly support this exact value/proposition under the field's semantics?

Possible implementations can include:

- deterministic phrase/attribute checks;
- a dedicated NLI/entailment model;
- a field-aware cross-encoder trained/evaluated for support;
- a bounded structured LLM adjudicator as a last resort.

Regardless of implementation, the stage should produce its own score/status and never be conflated with generic relevance.

### 7. Make fallback behavior first-class configuration

Today, fallback behavior is embedded in feature code: cross-encoder failure may fall back to lexical scoring; evidence recovery may fall through to MMR and then an LLM.

Represent fallback edges explicitly in the pipeline definition.

Examples:

```text
cross_encoder
  on_success -> support_validator
  on_unavailable -> mmr
  on_timeout -> mmr
  on_error -> mmr
```

or:

```text
support_validator
  on_no_supported_candidates -> llm_closed_choice
  on_success -> evidence_pack
```

This is necessary for both visibility and configurable chains.

### 8. Unify execution telemetry

Every stage should emit the same execution envelope:

- `run_id`;
- `pipeline_id`;
- `pipeline_version`;
- `stage_id`;
- `stage_type`;
- `strategy_id`;
- `strategy_version`;
- `status`;
- `started_at`;
- `finished_at`;
- `elapsed_ms`;
- `input_count`;
- `output_count`;
- `parameters`;
- `provider`;
- `model`;
- `collection/index`;
- `fallback_reason`;
- `warnings`;
- score summaries;
- safe candidate IDs;
- optional privileged trace references for prompt/source text.

The Operations system, Research run inspector, Corpus Builder model-activity inspector, and System Data should consume this same contract rather than each inventing separate telemetry shapes.

---

# Part III — Total visibility and user-configurable chains

## Goal

The application should make retrieval/model behavior both **declarative** and **observable**.

A user should never need to inspect Python code to answer:

- What strategy does Evidence Suggestion use?
- Is MMR enabled here?
- Did the cross-encoder actually run?
- Which model did it use?
- Was there a timeout or fallback?
- Which Chroma collection was searched?
- Which embedding provider/model produced the query vector?
- How many candidates were fetched?
- How many survived each filter?
- Why was this block selected?
- Did an LLM get called?
- Which model and schema were used?
- Was this behavior inherited from a system default, a feature profile, a corpus build, or a per-run override?

The user should also be able to define a chain, preview it, validate it, save it, assign it to a feature, override it for a run when authorized, and inspect the exact resolved chain after execution.

---

## 1. Add a central Pipeline Studio

Create an administrative workspace tentatively named **Pipeline Studio**.

It should be the canonical interface for configuring and understanding AI/retrieval execution.

The workspace should have four primary views.

### A. Pipelines

A table/card workspace listing named pipeline definitions, for example:

- Research — Balanced
- Research — High recall
- Research — Selected evidence only
- Evidence suggestion — Default
- Evidence suggestion — Conservative
- Metadata precedents — Default
- Metadata prefill — Default
- Claim memory — Default
- Prior response memory — Default
- Corpus metadata enrichment — Fast
- Corpus metadata enrichment — Deep

Each row should show:

- status: active/draft/disabled;
- version;
- assigned features;
- number of stages;
- last edited;
- validation status;
- estimated cost/latency class;
- providers/models referenced.

### B. Chain Builder

Provide a visual but accessible ordered stage editor.

The core interaction should work without drag-and-drop. Up/down controls and an ordered table/list must support keyboard and screen-reader use. Dragging can be an enhancement.

Each stage card should expose:

- stage name;
- stage type;
- strategy;
- input/output type;
- important parameters;
- fallback route;
- estimated candidate expansion/reduction;
- model/provider when applicable;
- whether the stage is deterministic, embedding-based, cross-encoder-based, or generative.

Example:

```text
1  Query transform       Research decomposition       GPT/Local LLM
2  Dense retrieval       Chroma semantic             fetch 500
3  Lexical retrieval     BM25 local                  fetch 500
4  Fusion                Reciprocal rank fusion      k=60
5  Rerank                CrossEncoder                top 80
6  Diversity             Constrained MMR             top 24
7  Provenance gate       Evidence sufficiency        required
8  Context pack          Character/token budget      80k chars
9  Generation            Research answer             configured profile
10 Evaluation            RAG grade                   optional
```

### C. Assignments

Show which feature resolves to which pipeline.

This is critical because total configurability without assignment visibility simply moves the hidden behavior elsewhere.

Example table:

| Feature                     | Active pipeline            | Source         | Override allowed |
| --------------------------- | -------------------------- | -------------- | ---------------- |
| Research                    | Research — Balanced v4     | system default | per run          |
| Evidence suggestion         | Evidence — Conservative v2 | system default | per corpus build |
| Metadata precedents         | Metadata precedent v3      | system default | build/schema     |
| Claim memory                | Claim similarity v1        | system default | no               |
| Corpus enrichment/discourse | Corpus metadata v5         | build profile  | build            |
| Corpus enrichment/quotation | Corpus metadata v5         | build profile  | build            |

"Source" should tell the user whether the assignment came from:

- built-in default;
- system setting;
- role/user preference;
- provider/research profile;
- metadata schema;
- corpus-build configuration;
- per-run override.

### D. Strategy catalog

A searchable catalog of every registered stage/strategy.

Examples:

- Chroma similarity
- Chroma MMR
- local BM25
- RRF fusion
- CrossEncoder reranker
- evidence support validator
- deterministic lexical evidence match
- source-unit cosine scorer
- provenance gate
- context packer
- LLM closed-choice selector
- Research query decomposition
- answer generator
- RAG grader

Each strategy should show:

- what it does;
- where it is currently used;
- accepted input/output contract;
- configurable parameters;
- provider/model dependencies;
- whether it invokes an LLM;
- whether it is deterministic;
- fallback behavior;
- telemetry emitted;
- known limitations.

---

## 2. Add a backend strategy registry

Do not implement configurable chains as arbitrary user-supplied Python or an unrestricted generic DAG.

Create a registry of server-owned stage implementations.

Conceptually:

```python
StrategySpec(
    id="rerank.cross_encoder",
    version=1,
    family="rerank",
    input_type="candidate_set",
    output_type="candidate_set",
    config_model=CrossEncoderConfig,
    executor=cross_encoder_stage,
    deterministic=False,
    capabilities={"model_inference"},
)
```

The registry should be the source of truth for:

- stage IDs;
- display metadata;
- configuration schema;
- valid input/output types;
- defaults;
- runtime implementation;
- telemetry schema;
- whether the stage can branch/fallback;
- authorization/capability requirements.

The frontend should consume a safe serialized form of this registry to build controls rather than hard-coding every strategy option in Vue components.

---

## 3. Add a typed pipeline-definition model

A saved pipeline should be data, not executable code.

Example conceptual shape:

```json
{
  "pipeline_id": "evidence-default",
  "version": 3,
  "purpose": "evidence_suggestion",
  "stages": [
    {
      "id": "lexical",
      "strategy": "evidence.lexical",
      "config": {"min_score": 0.5},
      "next": "semantic"
    },
    {
      "id": "semantic",
      "strategy": "retrieve.source_cosine",
      "config": {"fetch_k": 24},
      "next": "rerank"
    },
    {
      "id": "rerank",
      "strategy": "rerank.cross_encoder",
      "config": {"top_k": 8},
      "on_unavailable": "diversity",
      "next": "support"
    },
    {
      "id": "support",
      "strategy": "evidence.support_validator",
      "config": {"min_score": 0.65},
      "on_empty": "llm_choice",
      "next": "select"
    }
  ]
}
```

The persisted definition must reference only registered server-owned strategies.

---

## 4. Support chains without creating an unsafe workflow language

Users should be able to create useful chains, but the system does not need arbitrary programming constructs.

Initially support:

- ordered stages;
- parallel retrieval branches;
- merge/fusion nodes;
- bounded fallback edges;
- conditional edges based on typed statuses such as `empty`, `unavailable`, `timeout`, or `below_threshold`;
- optional stages;
- stage enable/disable;
- reusable subchains.

Do not initially support:

- arbitrary loops;
- arbitrary user code;
- unbounded recursion;
- arbitrary network calls;
- arbitrary SQL/Python expressions.

A chain validator should reject:

- incompatible stage input/output types;
- missing terminal stages;
- cycles where cycles are not explicitly supported;
- impossible fallbacks;
- references to unavailable providers/models;
- retrieval chains without a source/index;
- evidence-binding chains that omit mandatory provenance validation;
- generation chains that bypass required security/content controls.

---

## 5. Introduce pipeline inheritance and resolution

Users need configurability without duplicating huge definitions everywhere.

Use layered resolution:

```text
built-in safe default
    -> system assignment
    -> role/profile preference
    -> feature profile
    -> corpus build / metadata schema policy
    -> per-run override
```

The execution record must persist the **fully resolved pipeline snapshot**, not merely the pipeline ID.

That prevents later edits to a saved pipeline from changing the historical meaning of an old run.

The UI should show each resolved value with provenance:

- inherited from default;
- inherited from pipeline;
- overridden by Research profile;
- overridden for this run.

---

## 6. Make execution traces first-class application data

Every pipeline execution should create a trace.

At minimum, traces should persist:

### Run-level data

- run ID;
- pipeline ID and version;
- resolved pipeline snapshot/hash;
- feature/purpose;
- user/owner where appropriate;
- start/end/status;
- total latency;
- model-call count;
- embedding-call count;
- candidate counts;
- warnings/fallbacks.

### Stage-level data

- stage ID/type/strategy/version;
- parameters;
- provider/model/index/collection;
- input/output counts;
- elapsed time;
- status;
- fallback reason;
- score distribution summary;
- selected/rejected candidate IDs and reason codes;
- token/context budgets when relevant.

### Candidate-level lineage

For retrieval-sensitive stages, retain enough information to reconstruct:

```text
candidate
  <- generated by dense retrieval rank 14
  <- lexical retrieval rank 3
  <- fused RRF rank 5
  <- cross-encoder score 7.2
  <- diversity-selected rank 2
  <- provenance gate passed
  <- evidence packet E3
```

This is the retrieval equivalent of DerridAI's proposition-level source traceability.

Full source text and rendered prompts should remain permission-controlled; ordinary telemetry can use IDs, hashes, counts, scores, and safe summaries.

---

## 7. Surface visibility at the point of use

A central Pipeline Studio is not enough. Users should see the resolved behavior where they are working.

### Research

The Research page should show a compact **Pipeline** chip/button near the run controls.

Before a run it should summarize:

```text
Dense + lexical -> RRF -> CrossEncoder -> diversity -> provenance gate
```

Clicking opens the resolved pipeline with per-run overrides.

After/during a run, the Research pipeline bar and Runs drawer should show actual execution:

- Query decomposition — GPT/phi/Qwen/etc. — 1.2 s
- Dense retrieval — collection X — 500 candidates
- Lexical retrieval — 500 candidates
- RRF — 742 unique -> 80
- CrossEncoder — model X — 80 -> 24
- Diversity — 24 -> 12
- Provenance gate — 12 -> 10
- Generation — model Y — 6.4 s
- Grade — model Z — optional

Selecting a stage should show its telemetry and candidate transitions.

### Corpus Builder evidence review

The evidence-suggestion panel should say exactly how suggestions were produced.

For each proposed span, expose expandable "Why this suggestion?" details:

- lexical match: 0.44;
- semantic similarity: 0.82;
- cross-encoder: 0.71;
- support validator: passed;
- selected by: support rank;
- source unit: `...`;
- model/index versions.

The reviewer should be able to switch among authorized evidence pipelines for the current build or run a comparison preview without persisting evidence.

### Corpus Builder enrichment

The initialization/configuration view should show the active pipeline for:

- manifest;
- segmentation;
- each metadata schema group;
- precedent retrieval;
- evidence recovery;
- optional second-reader stages.

The Run Monitor and Model Activity inspector should show each actual model invocation and deterministic retrieval stage using the unified trace contract.

### Vector Stores/Search

The search workspace should expose the selected search pipeline rather than presenting "similarity", "MMR", and "hybrid" as isolated magic modes.

Simple presets remain useful, but each preset should expand to its actual chain.

### Metadata memory / System Data

System Data should gain a **Pipelines & traces** area showing:

- saved pipeline definitions;
- assignments;
- execution traces;
- strategy registry;
- model/index dependencies;
- recent fallbacks/errors;
- aggregate latency/use metrics.

This belongs conceptually beside the existing internal vector collections and system databases because pipeline definitions and traces are operational/system data, not corpus authority.

---

## 8. Keep simple presets while allowing expert chains

Most users should not need to build a chain from scratch.

Provide opinionated presets such as:

### Research

- Balanced
- High recall
- Fast local
- Lexical-heavy
- Selected evidence only

### Evidence

- Conservative support
- Fast semantic
- Exact/lexical first
- Deep adjudication

### Metadata precedent

- Balanced precedents
- Diverse precedents
- Strict analogy

A preset should simply be a named versioned pipeline definition.

The UI can show a simple preset selector by default and expose **Customize chain** for advanced users.

Once edited, a preset becomes a user/system pipeline derived from the original.

---

## 9. Add comparison and dry-run tools

A chain builder is much safer and more useful if users can compare configurations before assigning them.

Provide **Test pipeline** using a selected existing Record/query without mutating corpus state.

Comparison mode should be able to run Pipeline A and Pipeline B and show:

- candidate overlap;
- top-K changes;
- evidence-span differences;
- latency;
- model calls;
- cross-encoder calls;
- context size;
- score distributions;
- final selected IDs;
- for benchmark prompts, evaluation scores.

For DerridAI's local-model benchmarking use case, the same mechanism can support controlled retrieval ablations:

- similarity only;
- dense + lexical;
- dense + lexical + CE;
- CE + MMR;
- different MMR lambda;
- different embedding models.

---

## 10. Add pipeline versioning and reproducibility

A saved pipeline definition should be immutable once referenced by a completed scholarly/benchmark run.

Editing should create a new version.

Persist:

- pipeline ID;
- pipeline version;
- resolved pipeline JSON/hash;
- strategy versions;
- model IDs;
- embedding provider/model;
- cross-encoder model;
- collection/index revision where available;
- code version;
- prompt/schema version where applicable.

This allows a benchmark or Research result to be reproduced and audited later.

---

## 11. Add configuration scopes and permissions

Not every user should be able to rewrite system retrieval behavior.

Suggested capabilities:

- `pipelines.read`
- `pipelines.run`
- `pipelines.override`
- `pipelines.manage`
- `pipeline_traces.read`
- `pipeline_traces.read_sensitive`

Researchers can be allowed to choose among approved pipelines or override safe parameters without gaining permission to change global defaults.

Administrators can create, version, assign, and deprecate pipelines.

---

## 12. Keep provenance authority separate from pipeline configuration

Pipeline configuration is operational/computational state.

It must not become source authority.

A retrieval score, cross-encoder score, MMR score, or LLM choice can explain why a source candidate was surfaced, but it does not replace:

- source-span identity;
- Record provenance;
- reviewer decisions;
- FieldAssertion ownership;
- support bindings;
- publication validation.

This distinction should remain visible in the UI: "retrieval rationale" is not "scholarly evidence authority."

---

# Part IV — Proposed target architecture

## Core domain objects

### StrategySpec

Server-owned description of an executable stage type.

Suggested fields:

- `strategy_id`
- `version`
- `family`
- `label`
- `description`
- `input_contract`
- `output_contract`
- `config_schema`
- `capabilities`
- `determinism`
- `sensitive_trace_fields`

### PipelineDefinition

Saved versioned graph/chain.

Suggested fields:

- `pipeline_id`
- `version`
- `name`
- `purpose`
- `status`
- `stages`
- `edges`
- `created_at`
- `created_by`
- `derived_from`
- `notes`

### PipelineAssignment

Maps a feature/purpose to a pipeline.

Suggested dimensions:

- feature;
- scope;
- scope ID;
- pipeline ID/version;
- precedence;
- allowed override policy.

### PipelineRun

One resolved execution.

Suggested fields:

- run ID;
- feature/purpose;
- pipeline ID/version;
- resolved snapshot/hash;
- owner;
- status;
- code version;
- started/finished timestamps;
- summary metrics.

### PipelineStageRun

One actual stage execution.

Suggested fields are the unified telemetry envelope described above.

### CandidateTrace

Optional high-detail lineage for retrieval candidates.

This can be retained at full fidelity for benchmarks/admin diagnostics and sampled or summarized for ordinary operations if storage becomes significant.

---

## Pipeline stage families

A useful first registry would include:

### Query transforms

- passthrough;
- Research LLM decomposition;
- field-aware evidence-query builder;
- multilingual query expansion.

### Candidate generators

- Chroma similarity;
- source-unit cosine;
- lexical/BM25;
- filter-only;
- metadata-exemplar semantic search;
- claim-memory semantic search;
- response-memory semantic search.

### Fusion

- reciprocal-rank fusion;
- weighted score fusion;
- union/deduplicate.

### Rerankers

- CrossEncoder;
- lexical/vector fallback;
- score sort;
- future support-specific reranker.

### Evidence/support validators

- deterministic lexical support;
- provenance sufficiency;
- support/entailment classifier;
- closed-choice LLM adjudicator.

### Diversity/selectors

- MMR;
- source-aware constrained diversity;
- quotas by work/document/field/kind;
- top-K.

### Context packers

- character budget;
- token budget;
- field-balanced round robin;
- citation-aware evidence packet.

### LLM stages

- structured JSON generation;
- free-text generation;
- closed-choice selection;
- grading/evaluation.

---

# Part V — Implementation plan

## Phase 1 — Instrument and normalize without changing behavior

Goal: gain visibility first.

1. Introduce shared `RetrievalCandidate`, `StageTrace`, and relevance-normalization primitives.
2. Consolidate metric-aware distance normalization.
3. Consolidate MMR into one reusable implementation.
4. Wrap the three existing cross-encoder call sites in a common rerank stage adapter.
5. Add unified telemetry around existing retrieval and LLM paths.
6. Persist resolved existing settings as an implicit pipeline snapshot.
7. Surface the trace in Research Runs/Operations and Corpus Builder debug/admin surfaces.
8. Preserve existing defaults and output behavior as closely as possible.

This phase creates observability without requiring chain configurability yet.

## Phase 2 — Strategy registry and built-in pipelines

1. Add the server-owned strategy registry.
2. Express current hard-coded workflows as built-in declarative pipeline definitions.
3. Add validation of stage input/output contracts.
4. Add assignment resolution by feature.
5. Continue to preserve current behavior through built-in defaults.
6. Add read-only Pipeline Studio showing "what is used where."

At the end of this phase, every workflow should be explainable through pipeline data even if custom editing is still disabled.

## Phase 3 — Editable chains and versioning

1. Add saved pipeline definitions and immutable versions.
2. Build the accessible Chain Builder.
3. Add feature assignments.
4. Add per-run/per-build overrides where appropriate.
5. Add fallback-edge editing.
6. Add strategy parameter forms generated from backend schemas.
7. Add permission controls.
8. Store resolved snapshots on every execution.

## Phase 4 — Retrieval quality improvements

After visibility exists, change default algorithms deliberately and benchmark the changes.

1. Upgrade reviewer evidence suggestion to the shared staged evidence chain.
2. Add a support/entailment validation stage.
3. Move Research diversity selection after cross-encoder reranking.
4. Add source-aware diversity constraints.
5. Remove redundant parallel similarity/MMR retrieval where experiments show no benefit.
6. Keep memory/prefill paths similarity-first unless prompt-packet diversity is actually required.
7. Compare changes against fixed DerridAI benchmark prompts and corpus-review cases.

## Phase 5 — Comparison, benchmarking, and governance

1. Add dry-run pipeline testing.
2. Add A/B pipeline comparison.
3. Add aggregate stage latency/error/fallback dashboards.
4. Add benchmark-run integration.
5. Add export/import for pipeline definitions.
6. Add deprecation/migration tooling for strategy versions.
7. Add automated warnings for unsafe or incoherent chains.

---

# Part VI — Recommended built-in defaults after the migration

These are proposed starting defaults, not universal rules.

## Research — Balanced

```text
query decomposition (optional)
    -> dense retrieval
    + lexical retrieval
    -> RRF
    -> CrossEncoder
    -> source-aware diversity / de-duplication
    -> provenance sufficiency
    -> context pack
    -> generation
    -> optional grading
```

## Evidence suggestion — Conservative

```text
deterministic lexical evidence
    -> source-unit semantic retrieval
    -> CrossEncoder relevance rerank
    -> support/entailment validator
    -> top supported spans
    -> optional alternate-set diversity
    -> optional LLM closed-choice fallback
```

## Metadata precedents — Balanced

```text
schema/field/language filter
    -> semantic retrieval
    + lexical signal
    -> hybrid score
    -> CrossEncoder
    -> match-tier and positive/correction quotas
    -> MMR
    -> bounded prompt packet
```

## Metadata prefill — Conservative

```text
source-span embedding
    -> prior exemplar similarity
    -> field/value grouping
    -> independent-record support requirement
    -> field policy threshold
    -> hint or prefill
```

## Claim memory — Similarity

```text
owner/status filter
    -> semantic similarity
    -> threshold
    -> authoritative claim/support rejoin
```

## Prior response memory — Similarity

```text
eligibility filter
    -> semantic similarity
    -> threshold
    -> authoritative response/grade rejoin
    -> lexical fallback only on semantic failure
```

---

# Part VII — Acceptance criteria

The migration should not be considered complete until the following statements are true.

1. There is one documented registry of every retrieval, reranking, validation, packing, and LLM strategy available in DerridAI.
2. Every feature that uses vector search resolves through a named/versioned pipeline.
3. Every cross-encoder call resolves through a named/versioned pipeline stage.
4. Every generative LLM call resolves through a named/versioned pipeline stage or an explicitly documented operational exception such as model warmup.
5. The UI can show which pipeline is assigned to every relevant feature.
6. The UI can show the fully resolved pipeline before a run.
7. The UI can show which stages actually ran after a run.
8. Every fallback, timeout, skipped stage, or unavailable dependency is visible.
9. Candidate counts and stage-specific scores are preserved rather than collapsed into ambiguous generic scores.
10. Distance-to-relevance normalization is metric-aware and shared.
11. MMR uses one shared implementation.
12. Historical runs preserve immutable resolved pipeline snapshots.
13. Authorized users can create/version chains from registered strategies without writing code.
14. Chains are validated for type compatibility, provenance requirements, bounded execution, and permissions.
15. Evidence-binding chains cannot bypass required source/provenance validation.
16. Research and Corpus Builder expose stage traces at the point of use.
17. System Data provides a central operational view of pipelines, assignments, and traces.
18. Benchmark tooling can compare pipeline variants with fixed prompts/corpora.
19. All new controls meet the project's WCAG 2.2 AA, i18n, keyboard, high-contrast, dark-mode, and long-string requirements.
20. Retrieval configuration remains computational state and never replaces cELF/corpus provenance authority.

---

## Bottom line

DerridAI already contains the pieces of a sophisticated retrieval architecture: dense retrieval, lexical retrieval, hybrid fusion, MMR, cross-encoding, provenance gates, progressive metadata memory, validated-claim memory, prior-response memory, and multiple structured LLM stages.

The problem is not that it uses "similarity instead of MMR" or vice versa. The more important issue is that these mechanisms are currently assembled differently in separate feature-specific code paths, with inconsistent visibility and configurability.

The preferred direction is to make those mechanisms explicit stages in a common typed pipeline system.

That would provide three benefits at once:

1. **higher retrieval quality**, because stage ordering can be made appropriate to each task rather than copied ad hoc;
2. **scholarly auditability**, because the exact route from query to candidate to evidence to model output can be inspected after the fact; and
3. **user control**, because authorized users can choose, version, compare, and compose retrieval/model chains without changing Python code.

For DerridAI's stated provenance goals, the key principle should be:

> Retrieval and models may propose, rank, and transform computational candidates; deterministic provenance and validation layers remain responsible for establishing what the system may treat as evidence or authoritative state.
