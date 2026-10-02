# Concurrency Architecture and Corpus Builder Throughput Plan

Status: active implementation  
Branch: `task/corpus-builder-concurrency`  
Base: `master@9f01334749bdca98915ce7f162f8d4b41855db3d` (2026-10-02)  
Primary scope: Corpus Builder; secondary scope: shared provider/job scheduling, retrieval, embeddings, reranking, extraction, observability, and benchmarking.

## Goal

DerridAI should use all *useful* concurrency made available by a configured provider or execution resource without weakening scholarly authority, provenance, source binding, review safety, deterministic ordering, crash recovery, or local-first operation.

The target is not “more threads.” The target is a bounded dataflow in which independent work is visible to one scheduler, shared capacities are enforced globally, authoritative writes remain deterministic, and the same corpus semantics are produced at concurrency 1 and concurrency N for fixed provider outputs.

The guiding sequence is:

```text
Do less work first
        ↓
Expose independent work
        ↓
Schedule all ready work centrally
        ↓
Acquire the appropriate shared capacity
        ↓
Execute concurrently
        ↓
Merge authoritative state deterministically
```

This work extends, rather than replaces, the latency work in `docs/ENRICHMENT_CHANGES.md`: deterministic/source-derived resolution, candidate routing, and validator-driven escalation still come before concurrency.

## Current baseline

The current implementation already contains several concurrency mechanisms, but they are fragmented.

- `PdfCorpusBuildManager` has a background `ThreadPoolExecutor` (default two build workers).
- Corpus Builder metadata enrichment uses a per-build `ThreadPoolExecutor` bounded by `max_concurrent_requests`, currently clamped to 1–16.
- Each metadata worker owns one Record and executes that Record's selected metadata families serially.
- Enrichment reruns also use a Record-level `ThreadPoolExecutor`.
- Segmentation batches ambiguous boundary candidates, but those batch calls are serial.
- Boundary second-reader calls are serial.
- `LLMJobManager`, `LLMToolJobManager`, and `RAGJobManager` each maintain their own provider concurrency bookkeeping.
- RAG separately maintains an Ollama GPU-oriented process gate.
- Metadata exemplar retrieval has its own bounded thread pool.
- Vector-store pipeline execution already has a strategy-level concurrency declaration: `safe | provider_limited | exclusive`.
- Corpus Builder makes completed Records progressively reviewable, so throughput policy must preserve early Record completion rather than simply maximizing the number of partially started Records.

The principal architectural defect is therefore not “no concurrency.” It is **concurrency without one capacity authority**. Several subsystems can each believe that the same provider still has capacity.

## Non-negotiable invariants

1. Human-confirmed/override state always outranks automatic work.
2. A Record text/revision change while automatic work is in flight must cause merge/skip/revalidation, never silent overwrite.
3. No repository/global lock may be held while waiting for provider capacity or while performing remote/model inference.
4. Provider/profile limits are process-wide, not per feature.
5. Cancellation and exceptions always release acquired capacity.
6. Crash-safe resume preserves completed family/stage state.
7. Realtime “complete” events are emitted only after the durable Record write is readable.
8. Concurrent inference may finish out of order; authoritative topology and publication order remain deterministic.
9. Retrieval/reranking similarity never becomes evidence authority merely because it ran in parallel.
10. Fixed fake-provider outputs must produce equivalent scholarly state at concurrency 1 and concurrency N.
11. Optional/local providers may legitimately benchmark best at concurrency 1. DerridAI must use configured capacity, not silently force additional GPU parallelism.
12. Concurrency controls are operational state, not scholarly metadata.

## Target architecture

### 1. Process-wide capacity coordinator

Introduce one process-wide `ConcurrencyCoordinator` / `CapacityCoordinator`. It owns named resource gates and exposes cancellable permit acquisition, release, snapshots, and wait timing.

Initial resource classes:

- `provider_generation` — structured/chat generation against a named provider profile or normalized provider endpoint/model fallback identity.
- `ollama_runtime` — optional local GPU/endpoint cap layered under a provider-profile gate.
- `embedding` — embedding-provider/model capacity.
- `model_inference` — local inference such as CrossEncoder reranking.
- `cpu` — bounded CPU work where parallelism is known safe.
- `storage` — bounded storage-heavy work where necessary.

A profile limit must bound the aggregate active count across Corpus Builder, RAG, LLM review jobs, LLM tools, and other callers that share the key.

The normal key is `provider_profile_id`; callers without one fall back to a normalized provider/base URL/model identity. Ollama may additionally use an endpoint-level runtime gate so two profile aliases cannot accidentally overload the same local runtime.

### 2. Operation-level throttles remain distinct

A build/job may choose a lower operation-level concurrency than the provider profile. That is a local scheduling throttle, not a second independent provider capacity pool.

Conceptually:

```text
ready Corpus tasks --build throttle--> shared provider capacity --provider call-->
ready RAG task -----------------------> shared provider capacity --provider call-->
ready tool task ----------------------> shared provider capacity --provider call-->
```

The provider limit is authoritative across all three.

### 3. Corpus Builder ready-work scheduling

Move from “one worker owns one Record” toward small work units with dependencies.

Candidate work-unit classes:

- Record deterministic preparation
- precedent/memory retrieval
- discourse family generation
- quotation family generation
- indexing family generation
- evidence recovery
- reconciliation/validation
- targeted durable merge
- Record settlement
- boundary-classifier batch
- boundary second-reader call
- Document Intelligence
- extraction/OCR/transcription units where safe

The scheduler should submit any ready work whose resource permits are available. It should avoid nested, multiplicative pools.

### 4. Bounded-breadth progressive review policy

Provider utilization and progressive review are both goals.

When C provider slots are available:

1. open enough Records/tasks to fill C slots;
2. prefer ready work that completes already-started Records;
3. prioritize explicit reviewer requeues and targeted reruns;
4. age lower-priority bulk work to prevent starvation;
5. do not open hundreds of partially processed Records merely because thousands exist.

This produces early reviewable Records while maintaining saturation.

### 5. Record-local authoritative merge

Workers should return immutable/bounded stage results. A Record-level merger owns authoritative writes.

Before merge:

- reload current Record;
- compare Record identity, text/revision/fingerprint as applicable;
- inspect human-touched/authority state;
- merge only still-eligible automatic fields;
- persist the specific Record;
- then publish realtime completion.

The existing targeted `repo.get_record` / `repo.update_record` work should be extended rather than returning to whole-corpus rewrites.

## Corpus Builder concurrency opportunities

### Metadata families

Current selected families are serial inside one Record. Built-in families whose inputs are already prepared and whose outputs do not depend on one another should be eligible to overlap.

Do not blindly parallelize every custom schema group. Add an explicit family/stage dependency/concurrency contract. Unknown/custom groups default to `exclusive`.

Expected built-in behavior when safe:

```text
Record A: discourse ─┐
          quotation ─┼─> reconcile -> durable merge -> reviewable
          indexing  ─┘
```

All provider calls still pass through shared provider capacity.

### Segmentation

The deterministic candidate pass remains ordered.

Independent boundary-classifier batches may run concurrently. Results are gathered by batch/document ordinal and applied in source order.

The bounded boundary second-reader pass may likewise run inference concurrently over immutable pair snapshots, then apply mutations in order.

Pipeline traces must remain deterministic. If one shared session is not thread safe, concurrent calls receive child sessions/traces that are merged into a stable parent trace in definition/document order.

### Document Intelligence overlap

Metadata prompts currently consume Document Intelligence hints, so actual metadata generation should not race ahead and silently lose those hints.

However, once topology and cleanup have fixed the Record text, run these in parallel with whole-document intelligence where safe:

- Record-local deterministic NLP;
- direct indexing candidate resolution;
- source-quality calculations;
- schema/family routing preparation;
- source-span/label preparation;
- reviewed-memory and precedent preparation;
- safe embedding/retrieval preparation that does not depend on Document Intelligence output.

When Document Intelligence settles, Records already prepared can immediately enter provider scheduling.

### Retrieval, embeddings and reranking

Converge existing pools on the same resource model.

- Prefer batching embeddings/reranking before parallelizing batches.
- `provider_limited` pipeline strategies must acquire a real shared capacity permit.
- Extend `STRATEGY_CONCURRENCY` only after thread/process safety is established.
- Avoid nested fan-out such as N Record workers each starting M retrieval workers without a shared bound.

### Ingestion/extraction

Implement after enrichment/segmentation.

Add extractor capability declarations matching the same general semantics:

- `safe`: independent immutable units may overlap;
- `provider_limited`: external OCR/transcription/model service;
- `exclusive`: parser/runtime not proven thread safe or ordering-sensitive.

Potentially parallel units include independent raster/OCR pages, bounded remote transcription chunks, image preprocessing, and independent external extraction requests.

Reassembly must conserve source text/order/locators and retain extractor provenance. Do not share mutable parser/PDF objects across threads unless the library contract explicitly supports it.

## Shared job/provider migration

Migrate these to the shared coordinator:

- `LLMJobManager`
- `LLMToolJobManager`
- `RAGJobManager`
- Corpus Builder `_chat_json`
- future provider-backed Pipeline Studio executors

RAG's Ollama runtime gate remains a second resource constraint but should live in the coordinator rather than a manager-local condition variable.

Do not claim the migration complete while any major generation path maintains an independent counter for the same provider key.

## Observability

Concurrency requires queue/service-time telemetry, not only call duration.

Per capacity acquisition/task record:

- resource class;
- resource key/profile ID (secret-safe);
- configured/effective limit;
- queued timestamp;
- permit-requested timestamp;
- permit-acquired timestamp;
- wait duration;
- execution started/finished;
- active count when admitted;
- operation/build/job ID;
- Record ID and family/stage when applicable;
- cancellation/failure status.

Corpus Builder live state should expose, without pretending it is canonical scholarly state:

- effective build concurrency;
- active metadata tasks;
- Records actively enriching;
- provider active/limit/waiting;
- total provider wait time;
- per-family active/queued/completed counts where useful.

The UI should normally inherit provider profile capacity. Explicit per-build throttling is an advanced control.

## Provider configuration UX

Normal Corpus Builder behavior should inherit concurrency from the selected provider profile.

An explicit build/job setting may lower that capacity as an operation throttle, but it must not silently raise the process-wide provider limit. The product should distinguish these concepts in both copy and telemetry:

- saved provider capacity;
- effective operation/build throttle;
- current active/waiting provider usage;
- whether other DerridAI workflows are sharing the same profile capacity;
- local-runtime constraints such as the separate Ollama gate.

For local GPUs, higher numerical concurrency must never be presented as inherently faster. Benchmarking should determine the provider profile's configured capacity.

## Cancellation and fairness

Capacity waiting and scheduling must remain cancellation-aware and starvation-safe.

Required behavior:

- a cancelled task stops waiting promptly;
- failure/cancellation always releases permits;
- no repository/domain lock is held while waiting for capacity;
- separate provider profiles do not block one another;
- explicit reviewer requeues/reruns receive elevated scheduling priority once the ready-work scheduler is introduced;
- long-waiting normal work receives aging so priority does not become starvation;
- bounded breadth prefers finishing already-started Records while still keeping available provider slots occupied.

The initial shared-capacity implementation deliberately uses simple condition-based admission. Priority and aging belong in the Corpus Builder work scheduler, not in provider-capacity accounting itself.

## Benchmark plan

Measure concurrency 1/2/4/8/16 where supported, plus larger remote-provider limits after the Corpus Builder 16-request operation ceiling is deliberately reviewed.

Report:

- build wall-clock p50/p95;
- Record completion p50/p95;
- time-to-first-reviewable Record;
- provider slot utilization;
- provider wait p50/p95/total;
- model-call service time separate from queue time;
- calls/retries/escalations per Record;
- retrieval/rerank/embedding time;
- persistence/merge time;
- CPU and memory pressure;
- provider throttling/error rate;
- proposal coverage;
- reviewer accept/correct/reject rates;
- unsupported-evidence rate;
- source-binding/attribution regressions;
- Record reopening rate.

A local GPU benchmark may choose 1–2 as the useful capacity. A remote endpoint may sustain many more. No hard-coded universal “optimal” concurrency is assumed.

## Test plan

Use barriers/events rather than sleep-heavy timing tests.

Required tests:

1. coordinator never admits more than N callers for one key;
2. cancellation while waiting does not acquire/leak a permit;
3. exception after acquisition releases the permit;
4. two different provider keys can both reach their own limits;
5. Corpus Builder + RAG + LLM/tool jobs sharing one profile never exceed the aggregate profile limit;
6. operation-level throttle can be lower than provider capacity;
7. `max_concurrent_requests=1` preserves serial behavior;
8. Record-level enrichment reaches configured concurrency when enough ready Records exist;
9. independent metadata families can overlap only when declared safe;
10. human edit racing with a family result is not overwritten;
11. text/revision change causes stale automatic output to be skipped/revalidated;
12. cancellation of a build releases provider capacity;
13. failed family releases capacity and leaves other Records intact;
14. crash/resume skips completed families and resumes unsettled work;
15. segmentation batch calls may finish out of order while applied topology remains source ordered;
16. second-reader calls likewise preserve deterministic application order;
17. realtime terminal Record event occurs after durable write;
18. fixed fake-provider outputs yield equivalent final scholarly state at concurrency 1 and N;
19. multiple profile aliases/endpoints obey the chosen Ollama runtime rule;
20. pipeline `provider_limited` stages use the shared coordinator;
21. no secret/API key enters capacity telemetry.

## Implementation phases and progress

Legend: `[ ]` not started, `[~]` in progress, `[x]` implemented on this branch.

### Phase A — shared capacity substrate

- [x] Add process-wide concurrency/capacity coordinator with cancellable permits, stable provider keys, snapshots, wait timing, and leak-safe context management.
- [x] Add focused coordinator unit tests.
- [x] Add a cross-workflow admission test proving LLM and RAG managers sharing one provider profile share one process-wide limit; independent profiles do not block each other.
- [x] Migrate `LLMJobManager` provider gate.
- [x] Migrate `LLMToolJobManager` provider gate.
- [x] Migrate `RAGJobManager` provider-profile gate.
- [x] Move/bridge Ollama process gate into the coordinator.
- [x] Gate Corpus Builder structured provider calls through shared provider capacity.
- [x] Expose safe capacity snapshots to operational status. RAG and Corpus build reads now report shared provider capacity; Corpus live metadata status shows active/limit utilization.

### Phase B — Corpus Builder scheduling

- [~] Separate build-level worker count, operation throttle, and provider capacity. Shared provider capacity is now independent; Record/family pools share the provider contract, while a distinct user-facing operation throttle remains pending.
- [~] Introduce explicit metadata-family concurrency/dependency policy (built-in discourse/quotation/indexing are explicitly parallel-safe; schema-extensible dependency metadata remains pending).
- [x] Execute independent built-in metadata families concurrently. Build/retry/rerun orchestration now supplies one shared family-work pool so active Records steal from the same bounded queue instead of creating a family executor per Record.
- [x] Preserve Record-local staged checkpoint callbacks and deterministic reconciliation.
- [ ] Add bounded-breadth/finish-started-record priority behavior.
- [ ] Ensure targeted reruns/requeues receive priority without starving bulk work.
- [~] Add Record concurrency/barrier tests. Coordinator/family overlap and sibling-checkpoint isolation are covered; end-to-end multi-Record scheduler barriers remain pending.

### Phase C — segmentation and document preparation

- [x] Parallelize independent boundary-classifier batches under provider capacity.
- [x] Parallelize bounded second-reader inference over immutable pair snapshots.
- [x] Merge/apply segmentation decisions in stable source order.
- [x] Make structured-stage tracing concurrency-safe with synchronized aggregate counters and thread-local call paths.
- [ ] Identify Document Intelligence-independent Record preparation.
- [ ] Overlap safe deterministic/retrieval preparation with Document Intelligence without changing prompt semantics.

### Phase D — retrieval/model resources

- [ ] Route metadata precedent/retrieval fan-out through bounded resource policy.
- [ ] Make Pipeline Studio `provider_limited` concurrency operational, not only declarative.
- [ ] Add/verify model-inference resource gate for CrossEncoder-like work.
- [ ] Prefer batch-first embedding/reranking, with bounded concurrent batches where useful.
- [ ] Audit nested executors and remove multiplicative fan-out.

### Phase E — extraction/ingestion

- [ ] Add extractor concurrency capability declaration.
- [ ] Parallelize only proven-safe independent extraction/OCR/transcription units.
- [ ] Preserve deterministic reassembly, locators, source coverage and extractor/tool provenance.
- [ ] Add malformed/cancellation/resource-bound concurrency tests.

### Phase F — UI, metrics and benchmarks

- [ ] Add queue-time/utilization metrics separate from service time.
- [ ] Surface provider active/limit/waiting and active Record/task counts in Corpus Builder operational state.
- [ ] Make provider-profile capacity inheritance the normal UI behavior; keep explicit build throttle advanced.
- [ ] Add localized help/copy and WCAG 2.2 AA coverage for new controls/status.
- [ ] Add benchmark harness/results for 1/2/4/8/16 and representative local/remote providers.
- [ ] Update architecture/user/provider requirement docs after implementation is stable.

## Definition of done

This effort is complete when all of the following are true:

1. one provider-profile concurrency setting is enforced across every major workflow that uses that profile;
2. Corpus Builder keeps available provider capacity busy whenever enough independent eligible work exists;
3. independent metadata families and segmentation batches overlap only under explicit safe/provider-limited contracts;
4. Document Intelligence no longer forces unrelated deterministic/preparatory work to sit idle;
5. retrieval, embedding, reranking, and extraction concurrency use explicit shared resource limits rather than multiplicative nested pools;
6. cancellation, retry, resume, and reviewer edits remain race-safe;
7. fixed provider outputs produce canonically equivalent scholarly state at concurrency 1 and concurrency N;
8. live UI/telemetry truthfully distinguishes operation throttle, provider capacity, active work, and queueing;
9. fixed-corpus benchmarks report latency/utilization gains together with source-binding, provenance, authority, and review-quality regression checks.

## Progress log

### 2026-10-01 / initial branch setup

- Created `task/corpus-builder-concurrency` from latest `master@9f01334749bdca98915ce7f162f8d4b41855db3d`.
- Re-audited current Corpus Builder scheduling, metadata-family execution, segmentation batching, RAG/LLM/tool provider gates, Pipeline Studio concurrency declarations, and the active enrichment latency plan.
- Confirmed the first implementation slice should be the shared capacity substrate. Adding more Corpus Builder fan-out before a process-wide provider gate would permit aggregate oversubscription across independent managers.

### 2026-10-01 / shared capacity and first Corpus fan-out slice

- Added `api/app/concurrency.py` as the process-wide authority for named resource capacity. Permits are cancellable, context-managed, wait-timed, snapshot-capable, and secret-safe.
- Added configured resource limits so the legacy server Ollama cap can be shared across RAG, Corpus Builder, LLM review jobs, and LLM tools instead of living inside RAG alone.
- Migrated `LLMJobManager`, `LLMToolJobManager`, and `RAGJobManager` off independent provider counters. RAG operational status now reads shared coordinator snapshots.
- Gated every Corpus Builder structured provider attempt through the same provider-profile capacity key; Ollama calls additionally pass through the shared runtime gate. Build metrics now distinguish provider/Ollama wait counts and wait milliseconds from provider service time.
- Made `StructuredStageSession` safe for overlapping sibling calls: trace aggregation is locked, model work occurs outside the lock, and each thread retains its own last stage path for point-of-use provenance.
- Enabled bounded overlap of the built-in discourse, quotation, and indexing metadata families. Results are consumed in schema order even when calls finish out of order; unknown/custom families remain exclusive.
- Parallelized segmentation classifier batches and the bounded boundary second-reader pass. Inference uses immutable pair snapshots and authoritative boundary mutations are applied in document order.
- Added barrier-based coordinator tests plus metadata-family scheduling tests. Full branch CI has not yet been triggered; a draft PR/check run is still pending after the next integration slice.
- Replaced the per-Record family executor with one shared family-work pool per build/retry/rerun operation. Record workers prepare bounded breadth while family calls steal from the shared queue; a fuller explicit dependency scheduler and finish-started-Record priority policy remain pending.
- Isolated concurrent family task state onto per-family Record snapshots and changed durable stage checkpointing to merge only the callback family's status/ledger entry. This prevents a stale quotation/indexing snapshot from regressing a sibling family's running/completed checkpoint.
- Removed the hidden Corpus Builder 16-request ceiling across API validation, backend worker pools, setup controls and browser draft restoration. Corpus operations now preserve the provider profile's supported 1–64 range; local Ollama remains constrained by the separate shared runtime gate.
- Added live provider-capacity snapshots to Corpus build reads and wired the existing metadata status surface to report active/limit utilization instead of only the configured concurrency number.

### 2026-10-01 / shared work queue and capacity-range follow-up

- Corpus first-pass enrichment, automatic retry, and enrichment reruns now create one family executor per operation and pass it into Record workers. This avoids multiplicative nested pools while retaining bounded Record preparation.
- Concurrent metadata families use isolated Record snapshots; only their own stage result/status/ledger entries are merged back in schema order. Durable callbacks likewise preserve sibling family entries from the live Record.
- Added a regression test where a stale quotation snapshot arrives after discourse has already started; both family checkpoints and build counters must remain correct.
- Expanded Corpus concurrency from the old 1–16 operation clamp to the provider contract's full 1–64 range in Pydantic validation, worker scheduling, settings controls, provider payloads, draft restoration, and tests.
- Corpus build GET responses now attach live, non-persisted provider/Ollama capacity snapshots. The metadata live-status component displays active provider slots over the configured limit.
- Shared capacity limits are re-read while callers wait, so lowering the Ollama runtime cap takes effect for already-queued callers; a focused test covers this transition.

### 2026-10-01 / PR reconciliation checkpoint

- Reviewed every currently open PR. PR #407 covered concurrent-review UI/state, explicit SourceUnit → Record → Page topology, and early editable manifest setup; PR #408 covered the shared concurrency substrate and backend/provider fan-out.
- Reconciled both PRs onto current master in `task/corpus-builder-concurrency-unified`, preserving upstream runtime-retirement/i18n changes and manually resolving the overlapping Corpus Builder files.
- Combined the PR #407 active-Record grouping with PR #408 provider active/limit reporting in the live metadata status surface.
- Combined explicit topology/manifest setup with the 1–64 concurrency contract in the same `PdfCorpusBuilder`, request model, and setup tests.
- Retained PR #408's more complete `api/app/concurrency.py` implementation rather than adding the earlier experimental `capacity_coordinator.py` from `task/concurrency-coordinator`; this avoids two competing process-wide capacity authorities.
- Reconciled the earlier branch's additional plan requirements here: provider-capacity UX distinctions, cancellation/fairness policy, cross-workflow provider-limit testing, and an explicit definition of done.
- Added `tests/test_shared_provider_capacity.py` to prove two independent managers (LLM and RAG) cannot collectively exceed one shared profile limit and that independent profiles can proceed concurrently.
- PR #407 and PR #408 were merged into the unified staging branch rather than into `master`; the next public PR is the single consolidated review surface.

### 2026-10-01 / integration checkpoint

- Opened draft PR #408 to run the repository quality gates while implementation continues.
- Master advanced after branch creation through PR #405. Merged current `master@12c6cbfeb5b68c0d5117dd2263f3d624aa188ab5` into this branch; the upstream navigation/runtime-retirement changes did not overlap the concurrency files.
- GitHub Actions quality gates are now running against the merged head.
