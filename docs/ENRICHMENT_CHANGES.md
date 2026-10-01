# Metadata Enrichment Latency Changes

Status: active implementation plan  
Branch: `task/enrichment-latency`  
Baseline: `master` at `deb99aab48d23189cbccf4a9f70a667b40dd84df`

## Goal

Reduce Corpus Builder metadata-enrichment wall-clock latency by at least 50% on representative local-model workloads without weakening DerridAI's provenance, evidence, review, or cELF invariants.

The intended architecture is **deterministic candidate generation first, LLM adjudication only where semantic judgment remains necessary**. A larger/slower model should be an escalation path for ambiguous or invalid results, not the default engine for every field on every Record.

The latency target is not allowed to be met by silently dropping metadata quality. Changes should be evaluated against at least:

- wall-clock p50/p95 per Record and per build;
- model calls per Record and retries per successful family;
- valid proposal coverage;
- reviewer acceptance/correction/rejection rates;
- evidence-support/provenance-gate pass rates;
- unresolved-field rate;
- Record reopening rate after reruns;
- source-binding and attribution regressions.

## Current implementation

### Record-level orchestration

`MetadataEnrichmentExecutionMixin._enrich_record` currently performs the following broad sequence:

1. refreshes live build state and provider configuration;
2. applies deterministic manifest metadata and schema constraints;
3. retrieves editorial/reviewer memory and reviewed metadata precedents;
4. optionally runs an LLM text touch-up proposal;
5. applies the source-quality gate;
6. builds one structured metadata task per schema group;
7. runs selected metadata groups through the configured structured-LLM pipeline;
8. reconciles model output into Record metadata;
9. recovers missing evidence for evidence-bearing model proposals;
10. computes field status/autofill/review requirements and persists telemetry.

This is robust and auditable, but several independent expensive operations now occur on the hot path for each Record.

### Schema-family model calls

The default schema has three model groups:

- `discourse`: speaker, position holder, target, stance, proposition status, claim scope, semantic function, etc.;
- `quotation`: direct quotation and quoted-party/reference relations;
- `indexing`: topics, concepts, persons, and works referenced.

Each selected family is a separate structured model generation. Families are serial inside one Record.

Fast mode skips quotation without a quotation signal and skips indexing unless semantic indexing is enabled. Deep mode schedules all three.

The default output budgets are currently large for constrained metadata JSON:

- discourse: 1600 output tokens;
- quotation: 1500;
- indexing: 1200.

Each family prompt can repeat substantial shared context: manifest information, local conventions, precedents, prior-pass learning, human-owned fields, neighboring text, NLP hints, source-unit IDs, source-unit text, and current Record text.

### LLM retry/escalation

The built-in `corpus.metadata_enrichment.current@1` pipeline uses:

- primary provider, two attempts;
- on failure/timeout, review provider, two attempts.

A single troublesome metadata family can therefore spend up to four generations.

### Reviewed-precedent retrieval

Metadata enrichment retrieves reviewed precedents before model calls. The assigned `metadata.precedents.current@1` pipeline currently performs:

1. semantic metadata-exemplar retrieval, fetch K = 16;
2. scope filtering;
3. semantic/lexical hybrid fusion;
4. CrossEncoder reranking;
5. correction/positive quotas;
6. MMR diversity;
7. bounded packet packing.

This is useful advisory context, but its output is still normally fed into a later generative model instead of being used as a first-class candidate-resolution layer.

DerridAI also has exact adjudication memory and a separate `metadata.prefill.current@1` pipeline that can surface strong reviewed-memory hints. Those mechanisms can be leveraged more aggressively before asking a generative model.

### Evidence recovery

Model proposals for evidence-bearing fields are reconciled against source-unit evidence. When evidence is absent, enrichment runs the assigned evidence-recovery pipeline per field.

At the baseline, the system assignment points to `evidence.recovery.cascade@1`. That pipeline can execute:

`lexical -> semantic -> CrossEncoder -> MMR -> closed-choice LLM -> provenance -> selection`

It is explicitly non-cELF-guaranteed at its output boundary because semantic relevance/reranking can surface advisory passages without establishing direct support.

The repository already includes `evidence.recovery.celf@1`, whose normal path is substantially simpler:

`lexical/direct support -> deterministic support validation -> provenance -> selection`

with a closed-choice LLM only as a fallback. It avoids embeddings, CrossEncoder reranking, and MMR for normal directly supported evidence.

### Reviewer evidence suggestions

Reviewer-facing evidence suggestions already follow the desired division of labor more closely. `evidence.reviewer.current@2` combines lexical and semantic candidate generation, then requires deterministic direct-support and provenance gates before candidates become eligible suggestions.

This machinery should inform automatic enrichment evidence selection as well.

### Repository I/O in the hot path

Before each metadata family, `_run_metadata_tasks` currently reloads the full Record set and scans it to find the current Record before checking whether a reviewer has taken ownership of the relevant fields.

The repository already exposes `get_record(build_id, record_id)`, specifically for reading one interactive Record without parsing the complete corpus. Full-corpus reads in each family are unnecessary overhead and become increasingly costly for large builds.

Workers also save/merge build state frequently for crash-safety and reviewer concurrency. Those guarantees should remain, but operations should become as targeted as repository primitives permit.

### Concurrency

Enrichment passes can run Records concurrently through a `ThreadPoolExecutor`, bounded by `max_concurrent_requests`. The model/provider profile commonly defaults to one concurrent request.

Concurrency is useful only after unnecessary work is removed. On a single local GPU, over-concurrency can increase total latency or VRAM pressure, so it should remain benchmark-driven rather than becoming the primary optimization.

## Target architecture

The desired pipeline is:

```text
Record
  -> deterministic/source-derived assertions
  -> NLP + Document Intelligence candidates
  -> exact adjudication-memory candidates
  -> reviewed-precedent candidates
  -> deterministic evidence/support lookup
  -> resolve high-certainty fields
  -> route only unresolved semantic fields
  -> compact LLM adjudication
  -> deterministic validation
  -> selective escalation
  -> human review
```

The key distinction is that retrieval, NLP, source structure, exact memory, and reviewed precedents should produce inspectable candidates directly. The LLM should adjudicate ambiguity rather than re-derive every field from scratch.

## Proposed changes

### Phase 0 — measurement and low-risk hot-path cleanup

1. Preserve/expand existing per-family timing and reviewed-precedent timing telemetry.
2. Add benchmark reporting that separates:
   - precedent retrieval;
   - prompt/model time by family;
   - retry/escalation time;
   - evidence recovery;
   - validation/reconciliation;
   - persistence.
3. Replace full-corpus live-ownership reads with `repo.get_record(build_id, record_id)`.
4. Switch the default automatic evidence-recovery assignment from the heavy non-cELF relevance cascade to the direct-support-first cELF pipeline.
5. Keep the heavier relevance cascade available as an explicit optional Pipeline Studio assignment.

Expected benefit: modest but low-risk wall-clock savings, especially on large builds and evidence-heavy records, while creating a cleaner baseline for the larger model-call reductions.

### Phase 1 — deterministic-first evidence

1. Treat direct-support lexical retrieval plus provenance validation as the default automatic evidence path.
2. Reuse reviewer evidence-suggestion support/provenance semantics rather than maintaining divergent evidence eligibility rules.
3. Do not spend a generative evidence-selection call automatically when deterministic support yields no result unless an explicit build policy enables it.
4. Keep unresolved evidence visible as unresolved; do not convert relevance into proof.
5. Preserve evidence-pipeline identity and exact source bindings on every suggestion.

Expected benefit: eliminate most evidence-recovery model calls and expensive semantic/reranking work from the normal path.

### Phase 2 — indexing without routine generation

Move `topics`, `concepts`, `persons`, and `works_referenced` to a deterministic/candidate-first path.

Candidate inputs can include:

- spaCy/BookNLP annotations;
- NER/POS tags configured on the schema field;
- exact aliases and reviewed adjudication memory;
- reviewed metadata precedents;
- normalized title/person/entity matches;
- controlled vocabulary matches;
- lexical phrase extraction.

The output must retain derivation/provenance. A candidate generated by NLP/retrieval is not represented as an LLM inference.

Invoke a model only where candidate normalization or semantic ambiguity remains unresolved.

Expected benefit: remove one of three serial LLM generations from Deep-mode Records in the common case.

### Phase 3 — quotation routing

Use deterministic quotation structure and Document Intelligence before scheduling the quotation model.

The quotation family should be skipped when there is no plausible quotation relation to resolve. For simple direct quotes with a single high-confidence source-bound attribution candidate, produce a reviewable non-LLM candidate.

The LLM remains appropriate for:

- nested quotation chains;
- indirect or ambiguous attribution;
- multiple plausible speakers/authors/referents;
- malformed extraction where quote punctuation alone is insufficient.

Expected benefit: many ordinary prose Records require only the discourse model call.

### Phase 4 — reviewed memory as candidate resolution

Today reviewed precedents are primarily prompt examples. Change them into first-class advisory candidates.

Order of precedence:

1. human-confirmed/override state;
2. deterministic/source assertions;
3. exact adjudication-memory hit for the same context;
4. high-consensus reviewed precedent candidate supported by the current Record;
5. LLM proposal;
6. unresolved/no supported value.

A precedent never becomes authoritative merely because it is similar. The current Record must independently support the value according to the field's evidence/review contract.

When two or more sufficiently similar reviewed precedents agree and no close rival exists, the system may skip model generation for that field/family and surface the candidate for review.

### Phase 5 — compact semantic adjudication

Once deterministic/candidate fields are removed from the prompt, reduce metadata LLM calls to the genuinely interpretive core.

Likely LLM-first fields include:

- stance;
- proposition status;
- difficult position-holder attribution;
- target;
- claim scope;
- semantic function where not rule-resolvable.

The model should receive:

- current Record text;
- only source units relevant to the unresolved fields;
- only precedents relevant to those fields;
- only necessary neighboring context;
- bounded candidate sets where available.

Do not repeat unrelated indexing/quotation data.

Benchmark reduced output ceilings against observed valid structured-output sizes rather than maintaining 1200–1600 token defaults without evidence that they are needed.

### Phase 6 — validator-driven escalation and retries

Replace unconditional two-attempt-primary/two-attempt-review behavior with validation-driven escalation.

Initial target:

- one primary attempt;
- deterministic JSON/schema repair where safe;
- one review-provider attempt only if validation marks the result unusable or unsupported.

A larger/slower provider should receive only the failed/ambiguous semantic task, not every Record.

Retry policy remains configurable through Pipeline Studio.

### Phase 7 — targeted persistence and state checks

Continue replacing full-corpus operations inside hot loops with Record-targeted repository methods.

Required invariants:

- a reviewer edit that races with enrichment must never be overwritten;
- Record text/revision mismatches must cause merge/skip, not silent replacement;
- crash-safe resume must retain completed-family state;
- realtime events must not claim completion before the persisted Record is readable.

Where possible, use `record_id + record_revision`/ownership state as the concurrency check instead of reparsing every Record before every family.

## Implementation progress

The first tranche is now in progress on this branch:

- **Implemented:** per-family live reviewer-ownership checks use `repo.get_record(build_id, record_id)` instead of reparsing/scanning the complete Record set before every family.
- **Implemented:** per-family build checkpoints now persist the affected Record through `repo.update_record` and move build task counters incrementally, instead of loading/scanning/rewriting the entire corpus on every running/completed family transition.
- **Implemented:** enrichment retains the reviewed-precedent identities/similarities used in the prompt but no longer runs precedent-to-current-Record evidence remapping on every Record. That embedding/pipeline work now runs lazily when a reviewer opens the precedents view, preserving evidence suggestions while removing review-only computation from the enrichment critical path.
- **Implemented:** the built-in `evidence_recovery` assignment now points to `evidence.recovery.celf@1`; the heavier relevance cascade remains available for explicit assignment.
- **Implemented:** automatic evidence recovery's closed-choice LLM fallback is deployment-opt-in by default (`METADATA_EVIDENCE_CASCADE_LLM_ENABLED=false`). Direct-support recovery therefore spends no additional model call in the normal configuration.
- **Implemented:** enrichment metrics now expose call-latency p50, p95, max, and total, including the existing per-family slices. This is the first benchmark gate for the latency work.
- **Implemented:** quotation enrichment is now signal-routed in Deep mode too. A quotation-family model call requires quotation punctuation/attribution language or a current Document Intelligence quotation projection; Deep mode no longer spends the quotation call on ordinary prose solely because the user selected Deep enrichment.
- **Implemented:** automatic indexing now skips its generative family call when every indexing field already has a strong `derridai:memory` prefill (value-supported, present, confidence ≥ 0.88). The reviewed-memory assertions remain advisory/pending review, and an explicit indexing rerun always bypasses this router.
- **Tests updated:** focused ownership-failure, evidence-pipeline identity/default-assignment, and latency-metric coverage track these changes.

The next implementation slice is broader deterministic/candidate-first indexing: use NLP/Document Intelligence and reviewed-memory candidates to reduce routine generation even when not every indexing field has a strong memory prefill. It should extend the existing FieldAssertion authority model rather than introduce a parallel candidate store.

## Implementation sequence on this branch

The first implementation tranche will deliberately stay small and independently reviewable:

1. add this design/baseline document;
2. use `repo.get_record` for the per-family live ownership check;
3. make the direct-support-first cELF evidence-recovery pipeline the built-in default assignment;
4. update focused tests for both changes;
5. then implement instrumentation and the deterministic-first indexing/quotation routers in separate commits.

Larger behavioral changes must be benchmarked against the current baseline before becoming default.

## Acceptance target

For a representative fixed corpus/model/schema benchmark:

- total enrichment wall-clock p50 <= 50% of baseline;
- p95 materially reduced, not merely the mean;
- no increase in unsupported evidence suggestions;
- no regression in citation/source binding;
- no overwrite of human/deterministic assertions;
- reviewer correction/rejection rate does not materially worsen;
- proposal coverage remains useful rather than achieving speed by leaving most fields blank.

The benchmark should report both **latency** and **scholarly quality**. A faster pipeline is not considered better merely because it is faster.

## Architectural invariants

This work must preserve the following:

- canonical Record/review state remains authoritative;
- FieldAssertion derivation and authority remain distinct;
- retrieval relevance never establishes evidence support;
- provenance validation stays deterministic;
- reviewer-confirmed values are never overwritten by later enrichment;
- reviewed metadata precedents remain advisory for new Records;
- model output remains validated even when schema-valid;
- pipeline version/trace identity remains inspectable for every model or evidence operation;
- any fallback that weakens a guarantee is explicit in status/telemetry rather than silent.
