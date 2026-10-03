<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Corpus Builder performance implementation plan

Status: approved for incremental implementation. Baseline: `master` at `ebf30937`, including PRs #417 and #418. Progress and measured results live in [the related tracker](CORPUS_BUILDER_PERFORMANCE_PROGRESS.md).

## Goals and measurement contract

Target a 50% reduction in time to the first safely reviewable record and in active human review time on recurring metadata patterns. Target 30–50% lower full preparation time where measurements support it. These are engineering targets, not measured predictions or guarantees. Do not count #417's improvements again.

Measure first-readable, first-reviewable, full preparation, active reviewer seconds per 100 records, and interaction latency separately. Earlier reviewability does not necessarily reduce total computation. Preserve sub-250-ms cached navigation and improve cold-load/save tail latency under concurrent writes.

#417 reported synthetic cached navigation medians of approximately 84–88 ms, but excluded live model calls and lacked a complete pre-change baseline. It also identified corpus-wide queue work and two-build cold-load latency as follow-ups. #418 is included in the implementation baseline, not credited as new work here.

Instrument extraction, segmentation, source embeddings, precedent lookup, metadata-family execution, provider queue wait, persistence, review queue reads, and browser rendering. Collect bounded timings/counts, cache hits, avoided calls, retries, bytes written, and projection backlog; never copy source text, prompts, secrets, or sealed reviewer values into telemetry.

Benchmark 1,000 and 10,000 records, cold and warm runs, one and two builds, local and hosted models, and repetitive versus difficult attribution material. Include real-source fixtures alongside synthetic scaling tests. Report sample counts, p50/p95, model configuration, hardware/runtime, corpus identity, quality outcomes, and limitations. Avoid claiming population percentiles from tiny samples.

## 1. Incremental enrichment persistence

The inspected `_schedule_build_enrichment` completion path loads all records, searches for the completed record, and calls `save_records`. That serializes the collection, rewrites JSONL, and rebuilds the SQLite record table. Repeating it per completion can produce quadratic persistence work. Existing `update_record` already writes one SQLite row and marks JSONL dirty.

- First characterize durable record reads/writes and completion merge behavior, including human-owned fields.
- Replace per-completion collection replacement with a narrow repository merge/update operation. Read the latest affected record and merge worker results under the existing writer lock; retain human-ownership rules.
- Make stale-worker handling explicit. A later transactional contract should atomically update payload, task checkpoint, queue projection, and durable change event with an expected state version.
- Emit realtime notifications only after durable commit.
- Refresh JSONL at explicit finalization/export boundaries or coalesced checkpoints. Retain full replacement for actual topology changes.
- Remove whole-list searches and snapshot copying from hot paths as separately measured increments; do not expand the initial patch into a storage rewrite.

Code: `api/app/corpus_builder.py`, `corpus_enrichment_helpers.py`, `corpus_enrichment_reruns.py`.

Acceptance: no per-record full-store save during ordinary build enrichment; restart reads committed records even if JSONL is dirty; human edits survive; final JSONL agrees with authoritative SQLite state. Test crash/restart, stale completion, concurrent edits, cancellation, failure fallback, and publication. Measure both I/O work and wall time.

## 2. Incremental review-queue projection

Delivered checkpoint: REST and GraphQL queue reads now use a persistent transactional SQLite projection, live source-order cursors, incremental counts/facets/build summaries, and targeted frontend reconciliation. Bounded snapshot selection remains a compatibility path. See the progress tracker for repository measurements, the warm-cache trade-off, and outstanding end-to-end acceptance gates.

`select_queue` scans records; search serializes record JSON and counts perform corpus-wide work. Build a rebuildable SQLite queue projection with record identity, source order, state version, disposition, readiness, incomplete-field/source-problem flags, and review categories.

- Maintain rows transactionally with record changes and index common filters/orderings.
- Add cursor pagination for sequential review while preserving offset API compatibility.
- Incrementally maintain common counts; use indexed queries for uncommon combinations.
- Define searchable data explicitly. Preserve existing substring semantics initially; token search is a deliberate compatibility decision, not an invisible optimization.
- For blind review, search only the authenticated reviewer's presented Record. Sealed values must not affect hits, filtered counts, or facets; unsealed search retains casefolded Unicode JSON substring matching.
- Preserve reviewer-specific and blind-review visibility for rows, search, counts, and facets.
- Track projection generation/version and provide repair/rebuild support.
- Extend #417's bounded frontend cache and neighbour prefetch with targeted changed-record updates instead of full queue resets.
- Live cursors survive ordinary payload changes and reevaluate current membership/counts. Topology, repair, reviewer, or filter changes invalidate their context; retain offsets for random access/history. Records newly eligible behind an already traversed anchor are not guaranteed to be revisited.

Acceptance: equivalence tests against reviewer-visible queue selection for filters, reviewers, mutations, and restarts; common operations avoid full-corpus decoding; two-build cold loads meet the agreed latency budget. Repository decoding and timing checks are recorded in the tracker; HTTP/browser tail latency, real-source preparation, and human-review targets remain separate unverified gates.

## 3. Earlier safe review readiness

#417 exposes canonical topology before optional work but keeps preparation review locked. Define separate readiness dependencies for text and metadata review.

- Unlock text review only after relevant topology/conservation validation and when scheduled work cannot silently change that scope.
- Unlock metadata review when its required source context and assertions exist.
- Move optional semantic maps and nonessential projections off the readiness-critical path.
- Preserve genuinely document-wide dependencies; do not assume every stage can be partitioned.
- Prioritize the reviewer's next small record window, while protecting background throughput.
- Merge late proposals with version and human-ownership checks; expose honest stage readiness.

Acceptance: review during enrichment, late document results, split/merge invalidation, stale proposals, and unchanged publication gates. Report first-reviewable and full-preparation time separately. Any UI changes require English/French parity, accessibility, and browser coverage.

## 4. Exact dependency-aware caching

Extend existing source embeddings, precedent caches, family checkpoints, and selective reruns rather than introduce competing caches.

Stage fingerprints include only consumed inputs: authoritative text and relevant neighbours; span/topology/page-map versions; relevant schema/instruction hashes; provider/model configuration and known revision; prompt/pipeline/validator versions; applicable document metadata, guidance, and memory snapshot.

Post-#428 continuation bounds reads of the existing source-embedding cache: partial synchronization and vector lookup fetch only selected source-unit identities in bounded batches. Full-snapshot pruning remains document-wide. This removes whole-document vector reads from narrow reuse paths; it does not implement the broader semantic-stage fingerprinting or concurrent request coalescing below. Work-count evidence and remaining validation limits are in the progress tracker.

The next local checkpoint adds exact dependency fingerprints and response revalidation to existing raw metadata-family checkpoints. Unchanged raw families avoid provider calls; changed family prompts/configuration/source locators or unknown legacy provenance force recomputation, with reuse/invalidation retained in the execution ledger. Already materialized completed-family resume behavior is unchanged. This is a Record-scoped crash-checkpoint improvement, not a general completed-stage cache or in-flight request coalescer.

- Store validated results, provenance, and dependency fingerprints; record reuse in execution history.
- Coalesce concurrent identical requests and invalidate only dependent stages.
- Keep failure/malformed states distinct from reusable valid results.
- Support explicit recomputation, bounded storage, and authorization-scoped reads.
- Follow registered retention policy: do not silently apply generic eviction to protected exemplars, benchmark cases, or canonical research state.

Acceptance: unchanged warm stages avoid provider calls; field edits do not restart unrelated work. Citation formatting must not rerun semantic classification; text changes invalidate dependent evidence locators; changed attribution instructions invalidate attribution output.

## 5. Incremental vector memory

Delivered continuation after #425: `project_build_metadata_exemplars` now derives complete exemplar sets for changed Records and reconciles only their vector rows. Unchanged evidence contexts reuse compatible vectors even when revision-bound exemplar IDs change; metadata-only changes do not request embeddings. Durable per-build dirty tokens and the reviewed-memory outbox survive failure/restart, and background tasks coalesce per build. The progress tracker records equivalence checks, work counts, and component timings.

The reconciliation unit is a complete Record, rather than only the edited field: RecordRevision and other reviewed-value snapshots can affect all of its exemplars. Full rebuilds remain for initialization, repair, broad invalidation and collection replacement. Full-asset source blocks still load once per derivation batch; source-storage indexing and broader enrichment caching remain separate work. Pending sealed second opinions and disputed, invalid, or unresolved assertions cannot enter the trusted exemplar projection.

- Delivered: consume durable dirty work per Record; upsert or retire complete affected exemplar sets, including an empty set.
- Delivered: preserve originating assertion identity, record revision, and bound evidence; reconcile revision-dependent exemplar IDs without re-embedding identical context.
- Delivered: coalesce repeated edits; retain full rebuild for recovery/reconciliation and acknowledge only captured dirty tokens/events.
- Include model revision/digest and preprocessing identity in embedding contracts where available.
- Share exact compatible computations without collapsing source identity; batch bounded neighbour queries.
- Keep reverse dependencies for retractions and changed suggestions.
- Update only a bounded advisory neighbourhood of unresolved records after a review decision; avoid whole-corpus re-enrichment.

Acceptance: review saves never wait for vector service availability; each decision creates bounded indexing work; failures leave visible recoverable backlog and fully functional canonical review.

## 6. Evaluated learning and routing

Existing adaptive routing uses proposal and acceptance/correction counts; prefill uses similarity/agreement. Neither alone establishes calibrated correctness.

- Capture accept/correct/reject/abstain/reopened decisions with exact suggestions and evidence; distinguish individual inspection from bulk acceptance.
- Track outcomes by field, schema, language, source type, model, and proposal method.
- Count independent sources; duplicates and repeated model guesses must not inflate support.
- Evaluate on held-out documents and later decisions, with minimum sample requirements and uncertainty bounds.
- Separate vector similarity, model-reported confidence, and measured reliability. Confidence may decrease as evidence changes.
- Retain confirmed absence distinctly from missing/unevaluated fields; retain corrections as counterexamples.
- Version policies and retain the policy used by each stage. Keep random audits outside uncertainty-selected queues to detect confident mistakes.

Routing: exact applicable results are reused with provenance; validated recurring patterns receive evidence-bound prefills and may bypass eligible expensive stages; uncertain patterns use normal enrichment; conflicting/high-risk attribution escalates to deeper analysis or explicit review.

Transferred suggestions remain inferences, never `human_confirmed`. Keep strict safeguards for wrong-person attribution, quotation, negation, and editorial/primary-author distinctions. Roll out in shadow mode, then advisory mode, then selectively permit computation suppression.

Acceptance: fewer calls/corrections on held-out material without increased high-severity errors or hidden unresolved states. Required analysis must not be silently omitted to meet timing targets.

## 7. Reduce repeated human decisions

With cached navigation already fast, halve review effort by reducing repeated reading and decisions.

- Offer optional diverse early examples to establish recurring patterns, followed by grouping by field/value/evidence pattern.
- Show local supporting spans, precedents, and counterexamples together.
- Collapse settled fields while keeping unresolved/disputed fields prominent.
- Offer previewable batch confirmation for explicitly selected records; apply per-record version checks and audit entries and report conflicts individually.
- Preserve source-order review, keyboard navigation, drafts, and the active record while later suggestions refresh.
- Undo through auditable reversal and corresponding exemplar retirement.
- Include difficult cases and representative audits, not only easy records.

Acceptance: compare active time, corrections, reopened decisions, and independent quality assessment; 50% is most plausible for recurring metadata patterns. No automatic human-confirmed status by similarity.

## 8. Scheduling and contention

The local continuation bounds pending Record tasks to the Record-worker count in initial enrichment, retries, and rerun passes. Shared provider and Ollama gates now prioritize reviewer-triggered metadata work, Research, and tools, with FIFO ordering within each class and a background turn after at most three foreground admissions while background work waits. Capacity limits and ownership/publication policy remain unchanged. Earlier readiness, dedicated capacity reservation, and contention measurements remain planned; these increments do not establish an elapsed-time improvement.

Extend existing shared provider capacity and family parallelism; do not indiscriminately increase worker counts.

- Add foreground/background priorities with starvation protection.
- Submit a bounded task window instead of the whole build eagerly.
- Respect provider limits, token budgets, and local memory capacity; adapt within configured limits using observed throughput/retries/latency.
- Reserve capacity for reviewer-triggered work and reduce indexing pressure during resource contention.
- Evaluate small request batches only for independently identifiable tasks with per-record validation/retry.
- Enable smaller-model routing only after held-out quality evaluation.

Acceptance: improved throughput without degraded review responsiveness, cancellation, source fidelity, or scholarly quality.

## Sequence and checkpoints

| Increment | Deliverable                                           | Initial effort estimate |
| --------- | ----------------------------------------------------- | ----------------------- |
| 1         | Post-#417/#418 baseline instrumentation and benchmark | 2–3 days                |
| 2         | Incremental enrichment completion writes              | 3–5 days                |
| 3         | Queue projection and targeted invalidation            | 4–6 days                |
| 4         | Dependency-aware caching and incremental exemplars    | 5–8 days                |
| 5         | Earlier readiness and scheduling priorities           | 4–7 days                |
| 6         | Evaluated learning and assisted batch review          | 8–12 days               |

Estimates assume one engineer and include focused tests; evaluation additionally requires representative reviewed data. Commit and push tested increments and update the tracker with evidence and remaining work. Do not claim the entire plan complete after a single optimization.

Illustrative only: if persistence/queue work consumes 40% of preparation and model work 60%, reducing those components by 80% and 30% respectively yields 50% total reduction. Actual stage measurements determine whether that budget applies.
