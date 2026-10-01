# Metadata Enrichment Benchmark and Tuning Plan

Branch: `task/enrichment-benchmark-tuning`  
Baseline: `master` at `37096de7cb104c3fd4fd0f4c91f50b5504842de3`  
Predecessors: merged PR #366 and merged PR #369

## Purpose

The enrichment-latency work has reached the point where additional optimizations should be driven by measurements rather than architectural intuition.

PR #366 removed several avoidable hot-path costs and made evidence recovery, persistence, quotation routing, and precedent retrieval cheaper. PR #369 then introduced candidate-first, field-scoped indexing and changed the default metadata model pipeline from the historical two-primary-plus-two-review retry chain to one validated primary attempt followed by at most one review-provider escalation.

The next objective is to determine, on fixed representative corpora and model configurations, whether those changes achieve the project target:

- enrichment wall-clock p50 <= 50% of the pre-optimization baseline;
- materially lower p95;
- no material reduction in useful proposal coverage;
- no increase in unsupported evidence suggestions;
- no regression in citation/source binding;
- no overwrite of human or deterministic authority;
- no material worsening of reviewer correction/rejection rates.

A faster run is not considered successful merely because it emits fewer useful proposals.

## Current implementation state

Already merged:

- Record-targeted enrichment ownership checks and checkpoints instead of repeated whole-corpus hot-path reads/writes.
- Direct-support-first cELF evidence recovery as the built-in default.
- Automatic closed-choice evidence-model fallback disabled unless explicitly enabled.
- Lazy precedent-evidence remapping for reviewer inspection.
- Family-level call latency telemetry.
- Signal-routed quotation enrichment in both Fast and Deep modes.
- Field-scoped precedent retrieval and cache semantics that distinguish “not searched” from “searched with zero results.”
- Field-scoped indexing model contracts.
- Strong reviewed-memory values can remove only the indexing fields they resolve from a model call.
- Exact current-text NER spans can become unreviewed `derridai:nlp` FieldAssertions only for conservative direct-mention person/work indexing semantics.
- Crowded NER candidate sets fall back to semantic generation.
- Prompt context is scoped to the actual requested fields.
- Execution ledgers retain the requested field contract.
- Call telemetry includes requested-field count and prompt character count.
- `corpus.metadata_enrichment.current@2` uses one primary attempt and at most one validation-driven review-provider escalation; version 1 retains the historical 2+2 chain for reproducibility.

## Benchmark principle

The benchmark must separate three questions.

### 1. How long does enrichment actually take?

Measure real per-Record wall clock, not only individual LLM call duration. Per-family model latency is still retained because it explains where Record time went.

Required timing metrics:

- Record wall-clock p50, p95, max, total;
- per-family model call p50, p95, max, total;
- model-call count per Record and per family;
- failed-call and escalation counts;
- prompt size;
- requested-field count;
- configured output ceiling;
- retrieval/preparation time where already instrumented;
- persistence/checkpoint time where practical.

### 2. How much work was avoided?

Measure the mechanism of the speedup rather than inferring it.

Required workload metrics:

- percentage of Records that schedule discourse, quotation, and indexing;
- percentage of indexing fields resolved before generation;
- number of model-requested fields per family;
- direct-NLP candidate fields resolved/deferred;
- reviewed-memory fields resolved before generation;
- evidence-recovery invocations and model-fallback invocations;
- total structured-model attempts.

### 3. Did scholarly usefulness change?

Use existing review/enrichment ledger events wherever possible.

Required quality metrics:

- proposal coverage by field/family;
- grounded/evidence-supported rate where checkable;
- acceptance, correction, rejection, and unresolved-review rates;
- substantive-error rate;
- autofill precision where applicable;
- unresolved fields remaining;
- source/evidence validation failures;
- human/deterministic assertion overwrite count, which must remain zero.

The benchmark should expose descriptive metrics and acceptance gates; it must not collapse these dimensions into a single opaque “quality score.”

## Reproducibility contract

A benchmark comparison is valid only when the two arms share the same fixed input identity.

The fixture identity should bind at minimum:

- Record IDs;
- Record revisions;
- hashes of reviewed Record text;
- source-block IDs / source identity needed by enrichment;
- active metadata-schema ID and version plus a canonical schema hash;
- document/build manifest identity relevant to prompts;
- enrichment mode and semantic-indexing setting;
- evidence mode and relevant enrichment feature flags;
- provider profile identity;
- provider type;
- exact model/model-version identity when available;
- generation parameters that can affect outputs;
- concurrency setting;
- application/code version;
- assigned pipeline ID/version/hash.

Credentials must never be retained in the benchmark fixture.

Historical comparisons should not be simulated by silently changing production semantics. When comparing code revisions, capture a frozen fixture and run each revision against that fixture or compare explicitly retained benchmark-run artifacts whose fixture fingerprints match.

## Implementation plan

### Phase A — finish measurement instrumentation

Status: **implemented on this branch; pending full CI and benchmark execution**.

1. An enrichment-ledger `record_run` event records one Record’s actual processing wall clock.
2. The event retains Record outcome, pass number, family scope, model/provider identity, and concurrency.
3. Enrichment metrics expose Record wall-clock p50/p95/max/total in addition to per-family latency.
4. Family call events now retain actual structured-model invocation counts, including provider escalation and exceptional recovery turns.
5. Recovery-call counts are separated from routine model calls.
6. Focused tests verify that Record timing is emitted only after the merged Record is durably readable.

This is the minimum instrumentation needed to evaluate the 50% target honestly.

### Structured-output reliability work discovered during benchmarking

Status: **implemented on this branch; pending full CI**.

Real Corpus Builder runs exposed two failures that would otherwise contaminate both latency and quality measurements.

**Truncated structured JSON.** A local model can reach its output limit after a long discourse response. PR #374 now classifies structurally incomplete/token-limited output explicitly and repairs only malformed-but-complete JSON. Metadata enrichment keeps that safety rule: it does **not** close or invent missing JSON structure. When the active one-attempt metadata pipeline returns a classified truncation, the family receives one exceptional recovery turn through the same pipeline graph with bounded additional output headroom and a prompt that requires a fresh complete object with concise reasons. Normal Records still use one routine attempt.

**Assessment/value contradictions.** A model can return an assessment such as `outcome=supported_value` while leaving the corresponding metadata value null, sometimes placing the intended classification only in the assessment reason. The schema validator continues to downgrade that field to `uncertain` rather than treating it as supported truth. Before sending this mechanical contradiction to a human, automatic enrichment now gets one bounded consistency-repair turn. The repair explicitly requires `supported_value` to have a non-empty metadata value and asks the model to re-evaluate the affected fields from the current Record.

Both paths are recorded in the family execution ledger and enrichment ledger. The benchmark must report their frequency and extra model invocations. Frequent recovery is a signal to adjust prompt/contract/output budgets or model choice; it must not be hidden inside average latency.

### Phase B — immutable enrichment benchmark fixture

Status: **planned**.

Introduce a typed benchmark-fixture contract that contains no source text but fingerprints the exact input records/schema/configuration.

The fixture should:

- be immutable/versioned;
- hash canonical input identity;
- reject comparisons when Record/schema/provider/model/config identities drift;
- retain explicit reproducibility limitations when an exact provider/model revision is unavailable;
- remain separate from canonical corpus authority.

### Phase C — benchmark-run artifact and comparison

Status: **planned**.

Create a non-authoritative enrichment benchmark result containing:

- fixture fingerprint;
- code/app version;
- provider/model identity;
- pipeline identity/hash;
- per-Record timing distribution;
- per-family call distribution;
- requested-field and prompt-size distributions;
- workload-routing metrics;
- existing review/grounding quality metrics when available;
- explicit limitations.

A comparison should report raw left/right values and deltas. It may state whether a declared acceptance gate was met, but must not manufacture an overall winner.

### Phase D — reproducible runner

Status: **planned**.

Add a runner that can execute a frozen Record fixture without mutating the source build.

Preferred implementation:

1. snapshot the eligible pre-enrichment Records and required build/schema context;
2. create an isolated temporary benchmark repository/workspace;
3. run the real enrichment code against copied Records;
4. use an explicitly selected pipeline version without mutating the production Pipeline Studio assignment;
5. keep benchmark ledger/traces isolated from ordinary build/review state;
6. discard the temporary workspace after the benchmark artifact is built.

This is preferable to adding “legacy behavior” switches inside production enrichment code.

### Phase E — output-budget tuning

Status: **blocked on benchmark data**.

Once enough successful calls have been measured, compute actual structured output-size distributions per family and requested-field count.

Then:

- lower `num_predict` only where observed valid outputs leave safe headroom;
- avoid a single large ceiling for one-field and full-family calls;
- retain an explicit override for unusual schemas;
- test truncation/validation failure and escalation rates after every reduction.

Do not reduce token ceilings merely because the existing values look large.

### Phase F — expand deterministic/candidate resolution

Status: **blocked on reviewer-quality data**.

Potential next candidates include controlled-vocabulary matches, exact adjudication-memory matches, normalized aliases/titles, and carefully bounded topic/concept phrase candidates.

Any expansion must preserve:

- derivation distinct from authority;
- current-Record support;
- exact source/span provenance where applicable;
- conservative ambiguity routing;
- reviewer correction/rejection rates within the benchmark tolerance.

Raw retrieval similarity or NLP/tagger confidence alone is never sufficient authority.

### Phase G — compact interpretive-core prompts

Status: **planned after Phases E/F**.

After candidate-first resolution removes routine fields, reduce remaining model work to the genuinely interpretive core, typically:

- stance;
- proposition status;
- difficult position-holder attribution;
- target;
- claim scope;
- semantic function when not rule-resolvable.

Each call should receive only relevant source units, precedents, neighboring context, and bounded candidate sets.

## Benchmark acceptance gates

Default project target:

| Dimension | Gate |
| --- | --- |
| Record wall-clock p50 | <= 50% of baseline |
| Record wall-clock p95 | materially lower than baseline |
| Human/deterministic overwrites | 0 |
| Unsupported evidence suggestions | no increase |
| Source/citation binding failures | no increase |
| Proposal coverage | no material degradation |
| Reviewer correction/rejection | no material degradation |
| Autofill precision | no material degradation where measured |

“Material” tolerances must be declared in the benchmark case/report rather than chosen after seeing the result.

## Progress log

### 2026-10-01

- PR #366 merged: first latency-reduction tranche.
- PR #369 merged: field-scoped candidate-first indexing, scoped prompt/retrieval context, richer cost telemetry, and validation-driven one-attempt escalation.
- Created `task/enrichment-benchmark-tuning` from current `master`.
- Implemented Phase A Record wall-clock instrumentation and actual structured-model invocation/recovery counts.
- Integrated the structured-JSON classification introduced by merged PR #374; incomplete JSON remains a classified failure rather than being syntactically “completed” by DerridAI.
- Added one exceptional metadata-family recovery turn for classified truncation with bounded output headroom.
- Added one bounded consistency-repair turn for assessment/value contradictions such as `supported_value` with an empty metadata value.
- Tightened built-in metadata prompts so assessment reasons stay concise and cannot substitute for the metadata value itself.

## Non-goals for this tranche

- Do not add more deterministic metadata semantics merely to improve benchmark speed.
- Do not weaken evidence/provenance gates.
- Do not change human-authority precedence.
- Do not make the benchmark runner write canonical review decisions.
- Do not use a different model/provider between comparison arms unless the benchmark explicitly studies models rather than enrichment architecture.
- Do not treat LLM call latency alone as total enrichment latency.
