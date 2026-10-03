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

# Metadata Enrichment Latency Changes

Status: active implementation plan  
Branch: `task/enrichment-candidate-routing`  
Enrichment baseline: merged `master` at `d63e5df1c2b6251a47dd22b68b207ab5ca388db0` (PR #366)

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

The active built-in `corpus.metadata_enrichment.current@2` pipeline now uses:

- one primary-provider attempt;
- conservative syntax-level JSON repair plus the schema-derived Pydantic contract;
- on validation/provider failure or timeout, one review-provider attempt when configured.

The historical `corpus.metadata_enrichment.current@1` two-primary-plus-two-review chain remains available as a disabled built-in for reproducibility. Pipeline Studio clones can still choose a larger attempt budget explicitly.

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
4. The first latency tranche switched automatic evidence recovery to the direct-support-first cELF pipeline. Subsequent review found that this reduced useful evidence-suggestion recall, so the current default is the corrected `evidence.recovery.cascade@2`: direct support still short-circuits, while semantic/CrossEncoder/MMR stages only build a bounded shortlist and cannot establish evidence authority.
5. Keep `evidence.recovery.celf@1` and legacy `evidence.recovery.cascade@1` available for explicit assignment and reproducible comparisons.

The original switch reduced the amount of computation on the evidence-recovery path, but its end-to-end latency/quality trade-off was not measured with a controlled fixed-corpus benchmark before becoming the default. Cascade v2 therefore restores richer retrieval while bounding the expensive final adjudication and preserving the other hot-path optimizations.

### Phase 1 — deterministic-first evidence

1. Treat direct-support lexical retrieval plus provenance validation as the cheapest automatic evidence path and stop immediately when it succeeds.
2. When direct support is absent, use semantic retrieval, CrossEncoder reranking and MMR only to locate and bound plausible passages; relevance scores are never evidence authority.
3. Require every ranked candidate to pass direct-support validation or a closed-choice support decision before it can reach provenance.
4. Bound the closed-choice model to the ranked shortlist (four candidates in the built-in v2 graph) and fall back to the Record's source units only when retrieval cannot produce a shortlist.
5. Keep unresolved evidence visible as unresolved and preserve evidence-pipeline identity, trace, exact source bindings and separate score semantics on every suggestion.

Expected benefit: retain much of the old cascade's recall while avoiding its two main defects—premature CrossEncoder termination and relevance being treated as support—and keep the final model context substantially smaller than the full Record in the normal path.

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
- **Implemented in PR #366:** the built-in `evidence_recovery` assignment moved from legacy `evidence.recovery.cascade@1` to `evidence.recovery.celf@1`, and the automatic closed-choice LLM fallback became opt-in. This removed semantic/reranking/model work from the normal recovery path but also reduced useful suggestion recall.
- **Implemented on `fix/evidence-recovery-cascade-v2`:** `evidence.recovery.cascade@2` restores semantic retrieval, CrossEncoder reranking and MMR as candidate-location stages while preventing any of them from establishing evidence. Direct support still exits early; otherwise a support gate or a closed-choice model decision over at most four ranked candidates is required before provenance. The built-in assignment now points to v2, the bounded LLM fallback is enabled by default, and both older pipelines remain available for reproducibility. A controlled fixed-corpus latency/coverage comparison is still required; no latency percentage is claimed from this change.
- **Implemented:** enrichment metrics now expose call-latency p50, p95, max, and total, including the existing per-family slices. This is the first benchmark gate for the latency work.
- **Implemented:** quotation enrichment is now signal-routed in Deep mode too. A quotation-family model call requires quotation punctuation/attribution language or a current Document Intelligence quotation projection; Deep mode no longer spends the quotation call on ordinary prose solely because the user selected Deep enrichment.
- **Implemented:** automatic indexing now skips its generative family call when every indexing field already has a strong `derridai:memory` prefill (value-supported, present, confidence ≥ 0.88). The reviewed-memory assertions remain advisory/pending review, and an explicit indexing rerun always bypasses this router.
- **Implemented:** reviewed-precedent retrieval is now field-scoped to the metadata families actually scheduled for the Record. Signal-skipped quotation/indexing families no longer contribute candidates to the semantic/CrossEncoder/MMR precedent packet, reducing retrieval work and prompt preparation together.
- **Implemented:** the kept precedent cache now records only fields that were actually searched. An unscheduled family is left uncached, so opening its reviewer precedent panel later performs a live lookup instead of incorrectly treating “not searched” as “searched with zero matches.”
- **Implemented on the follow-up branch:** indexing generation is now field-scoped rather than only family-scoped. Strong reviewed-memory values remove only the fields they resolve from the indexing response contract, prompt, reviewer-memory packet, and precedent retrieval; unresolved indexing fields still go to the model. Explicit human reruns restore the complete family contract.
- **Implemented on the follow-up branch:** exact current-text NER spans may resolve only the stable direct-mention indexing semantics `derridai.indexing.persons` and `derridai.indexing.works_referenced`. They are stored as unreviewed `derridai:nlp` FieldAssertions with exact offsets/text digest/tagger provenance and no invented confidence. Topics, concepts, discourse attribution, and quotation relations are not promoted from raw tags.
- **Implemented on the follow-up branch:** per-family execution ledger entries record `requested_fields`, so audits can distinguish a full-family model call from a candidate-reduced field contract.
- **Implemented on the follow-up branch:** the active metadata-enrichment pipeline is now `corpus.metadata_enrichment.current@2`: one primary attempt followed by at most one review-provider attempt after structured-output validation/provider failure. The old 2+2 chain is retained as disabled version 1 for reproducibility, and Pipeline Studio remains the explicit override point.
- **Implemented on the follow-up branch:** call telemetry now records requested-field count and prompt character count, and enrichment metrics expose their p50/p95/totals alongside family latency so candidate reduction can be measured rather than inferred.
- **Tests updated:** focused ownership-failure, evidence-pipeline identity/default-assignment, and latency-metric coverage track these changes.

The current follow-up slice implements candidate-first indexing and validation-driven one-attempt escalation. The remaining performance work is benchmark-led: compare the new requested-field/prompt-size/call-latency telemetry against the PR #366 baseline, then reduce per-family output ceilings only where observed valid structured outputs show sufficient headroom. Any further deterministic promotion should be gated by reviewer correction/rejection data rather than by tagger confidence alone.

## Implementation sequence on this branch

PR #366 established the first tranche. The follow-up branch proceeds in independently auditable layers:

1. allow metadata family prompts and structured response contracts to name only unresolved fields;
2. remove strong reviewed-memory fields from automatic indexing calls while preserving complete explicit reruns;
3. expose current structured NLP spans without changing their rebuildable/advisory status;
4. promote only direct-mention indexing semantics through unreviewed `derridai:nlp` FieldAssertions with exact span provenance;
5. scope precedent retrieval to the same unresolved field set and retain the requested field contract in the execution ledger;
6. gate with focused provenance/routing tests and the full quality workflow;
7. switch the default metadata-enrichment pipeline to one validated primary attempt plus at most one review-provider escalation, while preserving the 2+2 chain as a historical built-in;
8. benchmark candidate-first plus one-attempt escalation versus the PR #366 baseline before tightening output budgets or expanding deterministic promotion further.

Larger behavioral changes must be benchmarked against the merged enrichment baseline before becoming default.

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
