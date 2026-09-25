# Progressive Metadata Enhancement

Status: active implementation specification and audit log  
Foundation: progressive backend slice merged in PR #149  
Current integration: PR #145 (`ajschlosser-solid-goggles`), rebased onto current `master` at `335f3048b3d4c65226d4aa4033808f40dd222c30`  
Current focus: System Data inspection, PR #145 reconciliation, and validation without exposing vector storage as product semantics.

## 1. Purpose

DerridAI should become progressively better at metadata enrichment as researchers review and correct corpus records, without changing model weights and without treating model output as authoritative.

The core mechanism is retrieval-augmented metadata enrichment:

1. retain validated metadata decisions as provenance-bound exemplars;
2. bind each exemplar to the exact evidence span that supports the field/value assertion;
3. derive compact embeddings from those exemplars;
4. retrieve field-specific, semantically similar precedents when enriching a new record;
5. give the enrichment model only the small number of precedents needed for the current metadata task;
6. validate the new proposal normally;
7. promote only trustworthy reviewed outcomes into future exemplar retrieval.

This is a learning loop through retrieval, not model training.

The intended effect is to turn difficult enrichment calls from:

> Infer the meaning of DerridAI's metadata ontology from scratch.

into:

> Classify this passage using a few closely related, already validated applications of the same ontology.

This should make smaller local models more useful, reduce repeat mistakes, improve consistency with corpus-specific editorial decisions, and potentially reduce retries/escalations enough to offset the small retrieval overhead.

## 2. Current `master`: build on, do not duplicate

Current `master` already contains an important first-generation form of progressive learning:

- `api/app/corpus_editorial_memory.py` derives advisory conventions and few-shot examples from human-confirmed/human-overridden metadata.
- examples are field-specific;
- the current similarity method is deterministic token/Jaccard overlap plus a small region-type tie-break;
- examples include `record_id`, `value`, a similarity score, and a record excerpt;
- only reviewed values are eligible as durable editorial examples;
- cross-pass learning also exists through `api/app/enrichment_cycles.py`;
- global learning is deliberately restricted to fields considered generalizable;
- enrichment records which editorial examples were used;
- the existing system keeps reviewer decisions advisory rather than copying them into new records as truth.

Progressive Metadata Enhancement should evolve this architecture rather than introduce a parallel memory system.

The key missing capability is evidence-bound semantic retrieval. Current few-shot examples use record excerpts and token overlap; they do not yet model each accepted field assertion as a first-class exemplar with an exact evidence reference and a derived semantic representation optimized for that metadata field.

## 3. Architectural principles

### 3.1 Canonical data remains canonical

The corpus/database representation is authoritative.

A vector index is derived data only. Deleting the progressive-metadata vector index must not delete or corrupt the reviewed metadata decisions from which it was produced.

The authoritative object is the reviewed metadata assertion and its evidence/provenance. The vector projection is rebuildable.

### 3.2 Do not embed anonymous truth

A vector entry must never be just:

```text
"Levinas" -> [embedding]
```

Every retrievable exemplar must resolve back to persistent scholarly identity:

```text
metadata exemplar
  -> field assertion
  -> record / record revision
  -> exact evidence span
  -> source document
  -> page/source span
  -> work / edition where available
  -> review/validation event
```

### 3.3 Exact evidence is preferred to entire-record embedding

For metadata enrichment, the full record is often too broad a retrieval unit.

If a 1,500-word record contains one sentence establishing:

```text
position_holder = Levinas
```

embedding all 1,500 words dilutes the signal.

The preferred retrievable text is:

```text
small semantic context window
+ exact supporting evidence span
```

The exact span remains separately identified even when a slightly larger context window is embedded.

### 3.4 Field-aware retrieval

A record that is a good precedent for `speaker` may be irrelevant for `stance`.

Retrieval must therefore be logically field-specific. This may be implemented as one collection with filterable `field_name` metadata rather than many physical collections.

### 3.5 Only send what is needed

Metadata RAG must not inflate every prompt with whole prior records.

Retrieved examples should be compact and bounded. A useful packet is closer to:

```text
FIELD: position_holder
VALUE: Levinas
EVIDENCE: "For Levinas, the relation to the other ..."
DISCOURSE ROLE: exposition
REVIEW STATE: human_confirmed
```

than to a complete JSON record.

### 3.6 Human review is the safest promotion path

Unreviewed model inference must not recursively teach future model inference as if it were fact.

The first implementation should promote only outcomes whose authority state permits learning. At minimum:

- `human_confirmed`;
- `human_override`;
- potentially `confirmed_absent` where the field and evidence model support absence exemplars;
- explicitly rejected/corrected model proposals as hard-negative examples.

Any use of deterministic/model-only assertions must be separately justified and lower-trust.

### 3.7 Failure stays visible

If exemplar retrieval fails, enrichment may continue without it, but the failure must be observable.

If an exemplar cannot be resolved to its evidence/source identity, it must not be silently supplied to the model.

## 4. Proposed data model

The implementation should align with the DERRIDAI Core concepts already present in `SPECIFICATION.md`, especially `FieldAssertion`, `RecordRevision`, `EvidenceRef`, `StorageProjection`, and the rule that vector storage is derived.

A conceptual exemplar:

```json
{
  "metadata_exemplar_id": "mex_...",
  "record_id": "rec_...",
  "record_revision": "...",
  "source_document_id": "src_...",
  "field_name": "position_holder",
  "field_value": "Levinas",
  "assertion_status": "human_confirmed",
  "assertion_method": "review",
  "evidence_ref": {
    "record_id": "rec_...",
    "record_revision": "...",
    "source_spans": [],
    "record_char_start": 412,
    "record_char_end": 489,
    "quote_hash": "..."
  },
  "evidence_text": "For Levinas ...",
  "context_text": "... For Levinas ...",
  "language": "en",
  "region_type": "main_text",
  "speaker": "Derrida",
  "position_holder": "Levinas",
  "stance": "exposition",
  "discourse_role": "exposition",
  "review_event_id": "...",
  "schema_id": "...",
  "schema_version": "...",
  "schema_hash": "...",
  "created_at": "...",
  "embedding_projection": {
    "provider": "...",
    "model": "...",
    "revision": "...",
    "dimension": 0
  }
}
```

The exact schema can differ, but the relationships must remain recoverable.

The vector store should retain only the fields needed to filter/resolve the exemplar. Canonical evidence/assertion content remains outside the vector store where practical.

## 5. Evidence-span construction

### 5.1 Exact span

When a reviewer selects evidence explicitly, preserve the exact offsets/reference.

When a field already has structured evidence references from enrichment, reuse them after validation.

If a reviewed field lacks exact evidence today, the system may derive a candidate span conservatively, but that candidate must not be represented as human-selected evidence unless the reviewer actually selected it.

### 5.2 Embedding context

Exact evidence can be too short to embed effectively. The embedding text should therefore be configurable as something like:

```text
preceding sentence(s)
+ exact evidence
+ following sentence(s)
```

while separately retaining the exact evidence locator.

Initial target: one to three surrounding sentences, bounded by a token/character ceiling.

### 5.3 Revision safety

Evidence offsets are revision-sensitive.

If authoritative record text changes, an exemplar tied to an older revision must not silently resolve its offsets against the new text.

It should be:

- revalidated/rebound;
- rebuilt from preserved source evidence;
- or excluded from retrieval until valid.

## 6. Retrieval strategy

### 6.1 Query once where possible

Do not perform a new expensive embedding call for every metadata field unless experiments show that field-conditioned query text materially improves quality.

Preferred initial flow:

```text
record / target passage
    -> one query embedding
    -> parallel field-filtered nearest-neighbor searches
       -> speaker
       -> quoted_speaker
       -> position_holder
       -> stance
       -> discourse_role
       -> other configured semantic fields
    -> compact exemplar selector
    -> metadata enrichment stages
```

### 6.2 Hybrid selection

Vector similarity is a candidate signal, not a truth signal.

Selection may combine:

- semantic similarity;
- field-name filter;
- language;
- schema/schema-version compatibility;
- source/document region;
- entity/name overlap;
- lexical overlap;
- same-work/same-document affinity where useful;
- review authority;
- correction/hard-negative status;
- diversity/deduplication.

The first implementation does not need every signal, but the API/data model should not prevent them.

### 6.3 Field-specific top-k

Default to very small result sets.

A reasonable initial ceiling:

- `speaker`: 0-2;
- `quoted_speaker`: 0-2 when relevant;
- `position_holder`: 2-3;
- `stance`: 2-3;
- `discourse_role`: 1-2;
- custom semantic fields: configurable, bounded.

### 6.4 Hard negatives and corrections

Human corrections are unusually valuable because they represent known failure modes.

Example:

```text
MODEL PROPOSED: speaker = Derrida
REVIEWER CHOSE: speaker = interviewer
EVIDENCE: "..."
REASON/PROVENANCE: human_override
```

When relevant, these may be supplied as concise "do not repeat this classification pattern" examples.

Rejected proposals must never be flattened into positive exemplars.

## 7. Prompt integration

Progressive examples should augment the existing staged metadata enrichment prompts, not create a separate all-fields LLM call.

Each metadata family receives only its relevant exemplars.

Conceptually:

```text
FIELD TO DETERMINE
stance

CURRENT PASSAGE
...

VALIDATED PRECEDENTS

Example 1
Evidence: "..."
Value: critical
Position holder: Heidegger

Example 2
Evidence: "..."
Value: exposition
Position holder: Kant

Return only the structured result required by the active metadata schema.
```

The model remains responsible for semantic inference. The examples are advisory, not authoritative.

## 8. Latency budget

The vector lookup itself should be cheap relative to local LLM generation. The main latency risk is prompt expansion and avoidable embedding calls.

Expected rough local overhead per record for an optimized implementation:

| Operation | Target/expected order of magnitude |
| --- | ---: |
| Reuse existing query embedding | ~0 ms incremental |
| Local vector lookup | ~2-30 ms |
| Parallel field-filtered lookups | ~10-100 ms total |
| Deterministic selection/deduplication | ~1-20 ms |
| Exemplar packet construction | ~1-10 ms |
| Additional LLM prefill from examples | ~50-500+ ms depending on model/hardware |
| New query embedding when required | ~5-500 ms depending on provider/hardware |

Design target: approximately **0.1-0.5 seconds incremental latency per record** in the normal case.

Several seconds of new latency per record should be treated as an implementation problem, not an inherent cost of the feature.

### 8.1 Prompt budget

Do not allow top-k across many fields to explode the prompt.

Initial total exemplar budget per record:

```text
800-1,500 tokens maximum
```

with a lower default preferred when adequate.

### 8.2 Measure useful throughput

Do not evaluate this feature only by raw per-call overhead.

Track:

- total enrichment latency per record;
- total enrichment latency per accepted field;
- total enrichment latency per record that clears review;
- retry rate;
- escalation rate;
- malformed/failed structured-output rate;
- needs-review rate;
- reviewer correction rate;
- exemplar hit rate;
- exemplar packet tokens.

A 200 ms retrieval/prefill cost that prevents a multi-second retry or a larger-model escalation is a net performance improvement.

## 9. Telemetry requirements

At minimum record:

```text
metadata_rag_query_ms
metadata_rag_search_ms
metadata_rag_select_ms
metadata_rag_packet_tokens
metadata_rag_examples_considered
metadata_rag_examples_used
metadata_rag_fields_served
metadata_rag_fallback_reason
metadata_llm_elapsed_ms
```

Each exemplar used by a call should be recoverable for audit/evaluation by stable identifier, without forcing the full exemplar payload into the public scholarly record.

The enrichment ledger should make it possible to compare runs with and without progressive retrieval.

## 10. Promotion and trust policy

Suggested initial states:

```text
unreviewed
validated_automatically
human_accepted
human_corrected
rejected
invalidated
```

These need not become new public FieldAssertion statuses if existing vocabulary already expresses the authoritative state. They may be internal exemplar-lifecycle states.

Initial retrieval eligibility:

- positive exemplar: human-confirmed/accepted;
- positive exemplar: human override/correction for the chosen value;
- negative exemplar: rejected model proposal paired with chosen value;
- excluded: unresolved;
- excluded: invalid;
- excluded by default: unreviewed model-only proposal;
- excluded: stale revision/evidence mismatch.

The policy must be deterministic and unit tested.

## 11. Interaction with existing editorial memory

This feature should replace or extend the *retrieval mechanism* inside the existing editorial-memory abstraction rather than make a competing prompt-memory path.

The likely direction is:

```text
EditorialMemoryMixin
  -> deterministic conventions (retain)
  -> prior-pass advisory learning (retain)
  -> lexical fallback examples (retain initially)
  -> progressive exemplar repository
  -> semantic/hybrid retrieval
  -> compact field-specific examples
```

This provides backward-compatible behavior when:

- the vector backend is unavailable;
- no exemplar index exists yet;
- the embedding provider is unavailable;
- the corpus has too few reviewed examples;
- progressive retrieval is disabled in an experiment arm.

The existing lexical/Jaccard example retrieval is therefore useful as a zero-dependency fallback and comparison baseline.

## 12. Vector-store design

Do not put progressive metadata exemplars indiscriminately into a user's ordinary research collection.

They have a different collection role and different filtering/rebuild semantics.

Preferred options, in order:

1. a dedicated derived collection/index role managed internally;
2. a storage abstraction that can use the configured vector backend without exposing exemplars as ordinary corpus records;
3. only if unavoidable, a clearly namespaced collection with a manifest declaring its role as metadata-exemplar memory.

The manifest/metadata should identify:

- collection role;
- exemplar schema version;
- source corpus/build/publication scope;
- embedding provider/model/revision/dimension;
- indexed text policy;
- eligible assertion statuses;
- rebuild timestamp/version.

## 13. Scope and privacy boundaries

Progressive metadata memory is local to the DerridAI deployment unless explicitly exported.

Corpus-specific entities such as `speaker`, `position_holder`, and `target` must not automatically become global cross-corpus "truth".

Cross-build sharing should remain conservative and scope-aware.

Schema-specific/custom fields must only retrieve examples compatible with the active schema semantics/version unless an explicit migration says otherwise.

## 14. Failure and fallback behavior

Progressive retrieval is advisory. It should not make enrichment unavailable.

On retrieval failure:

1. record telemetry/warning;
2. continue with existing editorial conventions/lexical fallback where available;
3. otherwise enrich without exemplars;
4. do not change assertion authority merely because RAG was unavailable.

On exemplar-resolution failure:

1. exclude the bad exemplar;
2. report/measure the failure;
3. never fabricate evidence text or provenance.

On embedding-contract mismatch:

1. fail/rebuild the derived index explicitly;
2. do not silently mix dimensions/models.

## 15. Evaluation plan

Use fixed records and fixed reviewed exemplars to compare:

- no editorial memory;
- current lexical editorial memory;
- progressive semantic retrieval;
- semantic + hybrid filters;
- positive-only exemplars;
- positive + corrected hard negatives.

Evaluate at least:

- field accuracy against reviewed outcomes;
- attribution/source discrimination;
- evidence correctness;
- reviewer correction rate;
- needs-review rate;
- model confidence calibration where available;
- retry/escalation rate;
- total latency;
- prompt-token overhead.

The most important question is not "did the examples sound useful?" but "did they reduce incorrect or review-required metadata while preserving evidence/provenance?"

## 16. Tests

Backend unit tests should cover:

- exemplar eligibility by authority state;
- exact evidence binding and quote/hash validation;
- stale RecordRevision exclusion;
- deterministic exemplar ID/rebuild behavior;
- field filters;
- language/schema filters;
- positive vs hard-negative handling;
- top-k and total token budgets;
- deduplication;
- no learning from gold/frozen evaluation records;
- vector-backend unavailable fallback;
- embedding dimension/model mismatch;
- no recursive promotion of unreviewed model output;
- no mutation of canonical records during retrieval;
- telemetry emission.

Integration tests should cover:

- reviewed decision -> exemplar -> index -> later enrichment prompt;
- correction -> hard negative -> later retrieval;
- record text revision invalidates/rebinds evidence safely;
- deletion/rebuild of derived index leaves corpus data intact;
- current lexical behavior remains a functioning fallback.

Performance tests should set a generous but explicit ceiling for retrieval overhead and prevent accidental per-field embedding/model calls.

## 17. Compatibility with concurrent work

### PR #145 System Data reconciliation

PR #145 introduces a first-class **System Data** administration surface. Progressive Metadata Enhancement uses that surface for inspection rather than exposing its derived storage as a normal research corpus.

The integration contract is now:

- `/api/system/data/metadata-exemplars` is the read-only administrative inspection API;
- the System Data page presents **Metadata exemplars** as domain data, not as a vector-store browser;
- visible exemplar fields include metadata field/value, positive/correction kind, authority status, source record/revision/build, schema/version, language/region, evidence block IDs/hash, and the bounded evidence-context window;
- filters and pagination operate on those semantic/audit fields;
- embeddings, vector dimensions, Chroma IDs, similarity internals, and collection-storage names are intentionally not part of the ordinary System Data UX;
- `derridai_metadata_exemplars` remains a rebuildable implementation projection whose authoritative source is reviewed corpus metadata plus evidence;
- absence of the derived projection is represented as an empty/not-yet-built System Data state rather than an application error.

PR #145 also introduced an earlier `derridai_metadata_memory` semantic reviewer-memory path. That path is superseded by the evidence-bound exemplar architecture and must not coexist as a second semantic learning system. The PR #145 branch has therefore been reconciled so:

- the exact-value SQLite adjudication cache remains useful for deterministic same-record suggestions;
- semantic reviewer examples are supplied only through the progressive evidence-bound exemplar pipeline;
- the older Chroma metadata-memory indexing/retrieval hooks are removed;
- the obsolete semantic-memory clear endpoint/UI action is removed;
- System Data inspects the progressive exemplar projection instead.

This preserves one semantic precedent model and one provenance contract.

At branch creation, open PR #145 ("Improve corpus enrichment, system data, and source-aware metadata") overlaps the same general area and describes "semantic reviewer memory".

The compatibility rule is now explicit: **metadata memory is the product/domain abstraction; a vector collection is only one derived storage adapter.**

The follow-up inspection work therefore exposes a backend-neutral System API contract rather than a Vector Stores route:

- canonical endpoint: `GET /api/system/metadata-memory`;
- System Data-compatible alias: `GET /api/system/data/metadata-memory`;
- normalized entries describe reviewed field/value, correction status, source record/revision, schema/build/language scope, evidence references/text, and indexed context;
- no collection/storage name is exposed in the normalized response;
- the inspector discovers the current `metadata_exemplars` projection and the `metadata_memory` projection proposed by PR #145;
- when both projections contain the same reviewed decision, the service deduplicates them and prefers the evidence-bound exemplar;
- PR #145's System Data page can consume this contract directly without depending on Chroma, collection aliases, or metadata encodings.

This permits PR #145 to change the physical storage implementation without changing the inspection UI/API contract. It also provides a migration path away from two competing reviewer-memory projections: converge storage later while preserving one conceptual System surface.

Before either branch merges across the other:

- rebase against the latest `master`;
- preserve the conceptual `MetadataMemoryService` boundary;
- reconcile duplicate semantic-memory writes so one reviewed decision does not become two long-term stores;
- preserve evidence-bound, field-specific, schema-aware, latency-budgeted retrieval requirements;
- retain the System Data alias so PR #145's administrative workspace can link/embed the same memory view.

## 18. Implementation plan

### Current implementation status

The initial backend slice merged to `master` in PR #149. The current follow-up branch adds the first audit/inspection surface:

- evidence-bound positive, correction/hard-negative, and explicitly evidenced confirmed-absence exemplars;
- strict evidence-to-record membership: a globally resolvable source block is not enough unless it belongs to the reviewed RecordRevision;
- human value changes and confirmed-absence decisions invalidate prior field evidence so stale evidence cannot silently teach a revised assertion;
- conservative promotion from human-reviewed metadata only;
- revision-aware, rebuildable Chroma projection;
- build/schema/language/field scoping;
- one query embedding shared across concurrent field-filtered searches;
- MMR selection, per-field limits, and a global prompt budget;
- family-specific prompt injection;
- lexical editorial-memory fallback when semantic retrieval is unavailable;
- stable exemplar IDs recorded on enrichment output;
- explicit hard-negative prompt semantics: `rejected_value` is a known model mistake, never a positive precedent;
- retrieval latency/count/token telemetry;
- internal system collection hidden from ordinary Vector Stores;
- focused regression tests for provenance, trust, rebuilding, fallback, prompt budgets, semantic retrieval, and family scoping;
- backend-neutral `MetadataMemoryService` for inspection, independent of collection/storage names;
- normalization of both PR #149 evidence-bound exemplars and PR #145-style semantic reviewer memory;
- deduplication that prefers evidence-bound reviewed precedents when both representations exist;
- admin-only System API at `/api/system/metadata-memory` plus the PR #145-compatible `/api/system/data/metadata-memory` alias;
- canonical evidence-text resolution from retained block IDs where the source build is still available;
- evidence-integrity verification against the exemplar's stored SHA-256 quote hash, with stale/mismatched evidence surfaced explicitly;
- source-revision currency checks for audit warnings;
- projection v3 fields for rejected model values, review method, review timestamp, and page range;
- first-class System → Metadata memory page with summary counts, filters, pagination, correction visibility, provenance/evidence/context inspection, EN/FR copy, and no Vector Stores terminology.

Empirical quality/latency benchmarking across real corpora and models remains an evaluation activity rather than a prerequisite for the initial implementation. The current semantic index is deliberately build-scoped; a cross-build exemplar catalogue requires an authoritative resolver for source build/record/revision/evidence identity before it should be enabled.

Validation note (PR #145, quality-gates run #503): backend Ruff, mypy, Python syntax, the full backend regression suite, frontend lint, frontend typecheck, frontend unit/component tests, the production build, and the Storybook build have passed on the reconciled branch. The long composed UI/opacity/WCAG E2E phase was still running when this status was recorded; do not describe the complete workflow as green until that final phase succeeds.


### Phase 0 - Baseline and contracts

- document current editorial-memory flow and call sites;
- identify the existing embedding/vector abstraction appropriate for an internal derived index;
- identify existing FieldAssertion/evidence structures usable without schema duplication;
- establish experiment flag/config and telemetry names;
- add baseline tests for current lexical retrieval so behavior is measurable before changing it.

### Phase 1 - First-class metadata exemplars

- add a compact internal MetadataExemplar representation;
- derive positive exemplars from eligible reviewed FieldAssertions;
- derive correction/hard-negative exemplars from review/rejection history;
- bind exact evidence references where currently available;
- validate revision/source identity;
- keep canonical exemplar data outside the vector projection;
- unit test promotion/exclusion rules.

### Phase 2 - Derived semantic index

- add internal collection role/manifest;
- build/rebuild incrementally from canonical eligible exemplars;
- enforce embedding contract/dimension compatibility;
- support deterministic deletion/rebuild;
- expose no misleading ordinary-record semantics.

### Phase 3 - Retrieval service

- query embedding once per record/passage where possible;
- run field-filtered searches in parallel;
- apply authority/schema/language filters;
- add lexical/entity tie-breakers where useful;
- deduplicate;
- enforce per-field top-k and total token budget;
- fall back to current lexical editorial-memory examples.

### Phase 4 - Enrichment integration

- replace current field-example selection with progressive retrieval behind a feature/experiment flag;
- retain deterministic conventions and prior-pass learning;
- format compact family-specific packets;
- record exemplar IDs actually supplied;
- ensure no extra LLM call is introduced solely for retrieval.

### Phase 5 - Telemetry and evaluation

- emit retrieval/query/select/prompt-token timings;
- add ledger/report comparisons for progressive vs lexical/no memory;
- measure retry, escalation, review and correction rates;
- add performance regression tests.

### Phase 6 - UX/audit surface

Status: **partially implemented through PR #145 System Data**.

Implemented:

- System Data now exposes a read-only Metadata Exemplars inspector rather than a research-corpus/vector-store surface;
- show exemplar source record/revision/build, field/value, authority state, schema/language/region, evidence block IDs/hash, and bounded context;
- field/kind/language/build/schema/record filtering and pagination;
- explicitly hide vector implementation details from the normal administrative UX;
- English and French copy;
- focused backend and frontend regression tests.

Remaining:

- add a direct navigation path from an exemplar to the corresponding Corpus Builder review/evidence surface once that route can preserve build/record context reliably;
- show retrieval-use history (which enrichment run consumed an exemplar and why it was selected) rather than only the exemplar projection itself;
- distinguish retrieval/MMR score from model confidence wherever retrieval-use history is shown;
- run representative WCAG 2.2 AA, forced-colors, dark-mode, long-string, and mobile interaction checks on the inspector.

## 19. Initial acceptance criteria

The first shippable slice is complete when:

1. a human-reviewed metadata assertion with valid evidence can become a canonical metadata exemplar;
2. the exemplar can be projected into a rebuildable semantic index;
3. a later record can retrieve that exemplar only for a compatible metadata field/schema scope;
4. the enrichment prompt receives a bounded compact exemplar rather than the whole source record;
5. the model's result remains an untrusted proposal subject to existing validation/review rules;
6. retrieval failure falls back cleanly;
7. the exemplar used in a run is auditable back to record/revision/evidence/review state;
8. unreviewed model output cannot recursively promote itself into trusted training context;
9. vector-store deletion/rebuild does not affect authoritative corpus metadata;
10. measured normal-case overhead stays near the 0.1-0.5 s/record design target or is explicitly justified by a demonstrated net reduction in retries/escalations.

## 20. Longer-term extensions

Once the evidence-bound exemplar layer is reliable, it can support:

- corpus-specific ontology learning for custom metadata schemas;
- confidence calibration based on neighboring reviewed exemplars;
- ambiguity detection from heterogeneous nearest neighbors;
- validator-driven escalation to larger models;
- multilingual exemplar retrieval;
- aligned original/translation metadata precedents;
- active-learning queues that prioritize records unlike the reviewed exemplar space;
- identification of repeated reviewer corrections as prompt/schema quality problems;
- reproducible metadata-enrichment benchmarks using frozen exemplar snapshots.

The core constraint remains unchanged: progressive learning must increase semantic usefulness without weakening provenance, attribution, evidence binding, review authority, or rebuildability.
