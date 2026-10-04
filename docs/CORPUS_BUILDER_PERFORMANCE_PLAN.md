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

The post-#448 continuation closes the remaining initial handoff read/write gap: family checkpoints and Record completions use selected-row reconciliation inside the existing SQLite writer transaction, with documentary/revision freshness checks and the existing human-authority merge. Retired or stale work cannot advance completion state or its first-settled milestone; existing requeue requests still schedule current identities. Unchanged checkpoints avoid Record/queue writes and exemplar notifications. Final scope reads and build/task JSON summaries retain their existing boundaries. These are correctness and bounded-work improvements, not measured end-to-end or save-tail gains.

Initial enrichment queue setup now uses optimistic reconciliation of current canonical topology instead of conditional per-Record preparation writes. Queue-state/counter computation runs outside review/writer locks; a guarded commit writes only changed rows in one batch and publishes counters together afterward. Concurrent Record changes trigger bounded recomputation; cancellation prevents the candidate commit, and current settle requests and completed family checkpoints survive initialization. Other optional preparation stages retain their three-way merge path. Three synthetic scheduler samples per size at 1,000 and 10,000 Records complete with zero full-store saves; timings and unmatched-baseline limitations are recorded in the tracker. Snapshot/commit work remains corpus-scoped, summaries remain separately durable, and no end-to-end or save-tail improvement is established.

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

The current continuation records separate durable topology, post-preparation review-unlock, and first newly settled metadata milestones. Post-topology memory prefill, guidance/Document Intelligence, source-illegibility assessment, and explicit annotation reruns now persist conditional Record deltas instead of replacing the corpus. Three-way merges preserve intervening edits and human authority; transactional queue-version checks reject concurrent changes, and retired identities are not restored. Initial enrichment queue setup uses the optimistic batch described above. Initial topology creation still uses a full replacement.

Optional source indexing, memory prefill, and Document Intelligence still precede the unlock boundary. The post-#439 continuation removes full-snapshot writes from initial requeue, retry/rerun completions, and automatic final validation. Selected completions reconcile current rows in a SQLite writer transaction; final validation reads current topology once and persists only changed rows. Human authority and documentary/revision/source changes remain protected, and retired identities are not restored. Queued retries resolve stable identities rather than obsolete ordinals.

Merged #444 adds exact documentary-context epochs and analysis IDs to Document Intelligence. Text, source bindings, extraction text, identity, and topology invalidate the annotation context; unrelated metadata does not. Snapshot checks detect edits during analysis, current graph reads exclude stale results, and metadata routing uses bounded epoch checks rather than whole-corpus reads. Failed reanalysis cannot impersonate a fresh success by retaining the preceding checkpoint.

The post-#444 continuation moves automatic validation computation outside manager, repository, and SQLite writer locks. A short coordinated snapshot transaction precedes validation; changed-row commit checks the same connection's SQLite data version, exact metadata schema, and captured build state, retrying concurrent changes at most three times before failing visibly. The manager guard spans Record commit and the separate build-summary handoff. Text, human authority, current topology, cancellation requests, and transactional queue updates remain protected. Selected completion merges retain their locked path. Finalization no longer repeats validation against an obsolete worker scope, and retries read only their selected extant identities at closure. API/frontend readiness keeps review available during `finalizing_review`.

Freshly constructed topology now exposes a narrower text-only boundary after conservation validation and deterministic cleanup are durably saved, before optional source indexing, memory prefill, and Document Intelligence finish. A current-preparation `text_review_available_at` milestone plus valid topology permits text edits/saves and review marks during `constructing_records` and `document_intelligence`; text decisions preserve the running preparation lifecycle. Metadata, disposition, structural edits, and model assistance remain locked. Preparation/resume clears the milestone before work. Existing-topology resume now rechecks canonical source coverage and nonempty text before exposing the same boundary, without reconstructing Records or repeating cleanup. Coverage that cannot pass the existing topology check, including overlapping source-unit bindings, remains conservatively gated; a stale valid report cannot unlock it. English/French notices and ordinary/focus reader controls distinguish these dependencies.

Earlier metadata/structural preparation review remains gated on readiness and scheduling coordination. Full validation still scans the corpus; snapshot capture/commit, projection repair, and final operation-summary work still require locks. Contention and save-tail timing remain unmeasured. JSONL stays visibly dirty until explicit projection refresh or publication/export. Keeping already available review open through final validation is distinct from the new text-only preparation boundary; neither establishes a measured end-to-end improvement.

## 4. Exact dependency-aware caching

Extend existing source embeddings, precedent caches, family checkpoints, and selective reruns rather than introduce competing caches.

Stage fingerprints include only consumed inputs: authoritative text and relevant neighbours; span/topology/page-map versions; relevant schema/instruction hashes; provider/model configuration and known revision; prompt/pipeline/validator versions; applicable document metadata, guidance, and memory snapshot.

Post-#428 continuation bounds reads of the existing source-embedding cache: partial synchronization and vector lookup fetch only selected source-unit identities in bounded batches. Full-snapshot pruning remains document-wide. This removes whole-document vector reads from narrow reuse paths; it does not implement the broader semantic-stage fingerprinting or concurrent request coalescing below. Work-count evidence and remaining validation limits are in the progress tracker.

Merged #430 adds exact dependency fingerprints and response revalidation to existing raw metadata-family checkpoints. Unchanged raw families avoid provider calls; changed family prompts/configuration/source locators or unknown legacy provenance force recomputation, with reuse/invalidation retained in the execution ledger. That increment left materialized completed-family resume behavior unchanged; the current continuation extends exact checking to normalized family outputs as described below.

- Store validated results, provenance, and dependency fingerprints; record reuse in execution history.
- Coalesce concurrent identical requests and invalidate only dependent stages.
- Keep failure/malformed states distinct from reusable valid results.
- Support explicit recomputation, bounded storage, and authorization-scoped reads.
- Follow registered retention policy: do not silently apply generic eviction to protected exemplars, benchmark cases, or canonical research state.

Acceptance: unchanged warm stages avoid provider calls; field edits do not restart unrelated work. Citation formatting must not rerun semantic classification; text changes invalidate dependent evidence locators; changed attribution instructions invalidate attribution output.

Post-#430 continuation implements bounded in-flight provider-call coalescing for exact build/Record/operation dependencies. Matching calls share only schema-valid, assessment-consistent responses; keys additionally bind actual provider credentials, role, repair prompt, schema, attempts, and token budget without persisting these inputs. Consumers keep independent pipeline traces, reconciliation, and joined-call ledger counts. Capacity bypass uses normal provider admission; errors and bounded wait expiry remain visible. This is not completed-stage caching, cross-Record transfer, or permission to reuse a settled family under changed dependencies.

Normalized completed families now retain a second opaque fingerprint of materialized values/assertions/evidence in their existing ledger. When scheduled again, exact execution and output matches reuse those already-authoritative values without reconstructing or retaining a bulky raw response. A mismatch or unknown materialized fingerprint recomputes only the scheduled affected family through the assigned pipeline; missing pipeline state cannot certify reuse. Legacy normalized families lacking execution fingerprints retain their historical resume semantics but do not count as exact cache hits. Human ownership, explicit retries, and failure states still take priority. Broader non-family stages and deeper dependency minimization remain outstanding.

## 5. Incremental vector memory

Delivered continuation after #425: `project_build_metadata_exemplars` now derives complete exemplar sets for changed Records and reconciles only their vector rows. Unchanged evidence contexts reuse compatible vectors even when revision-bound exemplar IDs change; metadata-only changes do not request embeddings. Durable per-build dirty tokens and the reviewed-memory outbox survive failure/restart, and background tasks coalesce per build. The progress tracker records equivalence checks, work counts, and component timings.

The reconciliation unit is a complete Record, rather than only the edited field: RecordRevision and other reviewed-value snapshots can affect all of its exemplars. Full rebuilds remain for initialization, repair, broad invalidation and collection replacement. Record-local derivation now loads only the affected Records' source blocks through a rebuildable, file-version-bound byte-offset index; cold initialization or a changed source requires one streaming indexing pass. Full rebuild and diagnosis paths retain complete source reads. Pending sealed second opinions and disputed, invalid, or unresolved assertions cannot enter the trusted exemplar projection.

Post-#430 measurement extends the existing repository benchmark with file-level source-block read calls, decoded rows, bytes, and read/parse duration. The initial warm synthetic measurements showed document-sized reads even for one Record. The subsequent user-directed bounded lookup removes those reads after index initialization. Contract `corpus-exemplar-repository-v3` measures actual indexed row byte lengths; selected-read duration includes lookup overhead, and cold index construction is outside its expressly warm workload. See the tracker for sample counts, timings, and limitations; these measurements do not establish end-to-end improvement.

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

Record-open follow-up: distinguish current LRU/prefetch hits from cold GraphQL reads and source-block/render completion. Cold full-Record reads acquire the repository lock and SQLite writer reservation to ensure current queue versions/projections. The asynchronous viewed-counter write uses the same lock, fsyncs the JSONL dirty marker, and advances the Record's operational queue version, which can make subsequent opens cold. A single-ID foreground read also has a different coalescing key from a two-ID neighbour prefetch. These code-traced mechanisms are not live latency attribution; measure cache outcome, request/lock wait, projection repair, payload size, and render time before adjusting them. Preserve current enrichment/reviewer visibility and activity/audit durability; do not obtain faster opens by serving stale scholarly state or dropping view events.

### Reviewer hot-path audit and decomposition plan (2026-10-03)

Status: historical audit with incremental delivery recorded below and in the tracker. The opportunities table describes the inspected pre-continuation behavior, not the current implementation. These are code-confirmed work paths, not measured latency attribution. Retiring automatic view counting is an explicit behavior change, not permission to drop scholarly review events or historical activity.

#### Confirmed opportunities

| Work                                   | Current avoidable cost                                                                                                                                                                                                                         | Proposed treatment                                                                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Per-open view counting                 | `markViewed` writes a canonical Record, dirty-marker JSON, queue state, and derived invalidations. Its consumer is an activity label, not review authority.                                                                                    | Stop automatic counting; preserve historical counts and explicit review decisions. No mandatory replacement telemetry.             |
| Hidden precedent assistance            | Metadata stays mounted with `v-show`. Its immediate pending-field watcher requests `fieldPrecedents` even when hidden. Reverification through `_editorial_memory` loads all Records and source blocks; candidate remapping can use embeddings. | Visibility-gate requests without unmounting dirty editors. Resolve referenced precedents directly; rank candidates only on demand. |
| Eager source-block reads               | Every different Record activation requests source blocks, including with the source inspector closed.                                                                                                                                          | Load for visible consumers; share bounded reads/cache entries keyed by exact source/extractor revision.                            |
| All-field autocomplete refresh         | Facets load outside the active Metadata inspector and invalidate on queue data-generation changes. Backend aggregates are already materialized, but field filtering occurs after fetching rows.                                                | Demand-load relevant fields, filter in SQL, and invalidate on actual facet dependencies while preserving reviewer visibility.      |
| Advanced JSON and draft storage        | Every activation pretty-prints advanced metadata, and its watcher writes even clean server copies to synchronous localStorage.                                                                                                                 | Generate lazily; persist actual drafts while preserving recovery.                                                                  |
| Read-side setup and writer reservation | Each `_records_db` connection initializes storage objects and commits. Selected reads ensure projections with `BEGIN IMMEDIATE` under the repository-wide lock shared across builds.                                                           | Separate versioned initialization, clean snapshot reads, explicit repair, and canonical mutation.                                  |
| Duplicate/obsolete requests            | Two-ID prefetch and single-ID foreground reads have different coalescing keys. Ignoring stale precedent responses does not cancel backend work.                                                                                                | Bounded per-Record sharing with freshness guards; explicit cancellation/admission for expensive assistance.                        |

Several source/evidence/semantic inspectors and individual precedent disclosures already load on demand. Preserve that prior art. Full-Record reads are indexed, not unconditional whole-corpus scans or synchronous LLM calls. Evidence validation is useful; its unnecessary eager execution is the target.

#### Delivery order

1. **Measure the reviewer critical path.** Establish a valid environment despite the current host fixture-fsync stalls and missing frontend dependencies. Capture bounded, text-free timings for cache/prefetch outcomes, request/lock wait, projection repair, returned bytes, optional requests, and first render. Compare cached/cold opens, pending/completed Records, hidden/visible inspectors, rapid navigation, and one/two builds under enrichment at 1,000 and 10,000 Records. Include real-source cases and sufficient observations for reported percentiles.
2. **Remove bookkeeping and hidden eager work.** Retire the automatic viewed POST and its ordinary activity label with explicit endpoint compatibility/deprecation and both locale updates. Preserve historical counts and meaningful review events. Gate precedent remapping, source blocks, facets, and advanced JSON on actual consumer demand. Keep draft-bearing editors mounted; do not solve visibility by destroying unsaved state. Optional-load errors remain visible.
3. **Bound useful assistance and refreshes.** Reuse canonical exemplar/binding helpers to resolve only kept references, retaining exact revision/evidence checks and visible stale states. Provider-backed candidate ranking must use its assigned pipeline, normal admission, and explicit cancellation. Share foreground/prefetch reads by exact Record context. Investigate redundant post-save reads: retain an authoritative mutation result only when its returned version proves freshness, never merely because a save succeeded.
4. **Decompose responsibilities inside one API.** Separate coherent read transactions, short transactional canonical writes, explicit projection repair, background computation, and operational telemetry. Initialize/version storage at its lifecycle boundary rather than on every hot read. Narrow coordination to the affected build, with documented lock order and separate protection for shared registries. Read/repair races must retry or fail visibly; preserve durability, blind review, and payload/version consistency.
5. **Consider worker isolation only after remeasurement.** Keep one authenticated REST/GraphQL façade initially. Extract jobs only if measured contention remains, after durable ownership/leases, bounded admission, cancellation, restart recovery, and provider limits exist. Extra Uvicorn workers are not a shortcut: job execution is process-local and Chroma requires one writer per persistence path. More services sharing the same bottleneck are not a performance result.

The post-#472 measurement continuation extends the synthetic selected-read harness to one shared repository with one/two builds and synchronized optional canonical writes. This exercises shared repository coordination absent from the earlier separate-instance, read-only measurements. It is a contention baseline harness, not an actual enrichment workload or evidence for worker isolation; live browser/save-tail and real-source acceptance remain required.

All eight 1,000/10,000-Record cases have now run, with 40 read-batch observations each and canonical lookup/update timings retained separately. The v3 harness checks operational payload/version coherence and bounded decoding during concurrent writes. Synthetic read-batch p95 stayed below 8 ms; canonical lookup/update p95 varied from approximately 97 to 702 ms. This points to a need for write-path timing decomposition, not proof of a particular lock or persistence bottleneck. Full measurements and environment limits are recorded in the tracker.

The v4 harness now records named inclusive write-path scopes. It identified avoidable repository-wide lock acquisition in schema lookup; that lookup now reads one atomically replaced build snapshot without a writer reservation, with a blocked-writer regression. Canonical writer coordination and repair locks are unchanged. Repeated synthetic runs remove the schema-wait contribution but show variable overall write tails, so they do not establish an end-to-end speedup. SQLite commit/lock-wait attribution and broader per-build coordination remain open.

The v6 continuation separately times transaction admission, SQL statements and commit, and compares verified FULL-synchronous DELETE/WAL modes in the isolated harness. SQL execution and SQLite admission were small in those samples; commit, dirty-marker persistence and repository coordination remain material. WAL did not consistently improve whole lookup/update tails, so production journaling and durability are unchanged. Physical fsync attribution, controlled repeated trials, browser saves, backup/crash/filesystem acceptance, and broader per-build coordination remain open.

Targeted-save rejection now checks Record identity and expected queue version before writing the JSONL dirty marker, avoiding a durable build-summary write for missing identities and stale conflicts. Successful saves retain marker-before-mutation ordering; marker failures prevent mutation and later transactional failures leave conservative dirty state. Restart-based failure regressions cover these boundaries. This is rejected-request work avoidance, not a successful-save latency improvement.

Next-Record review handoffs now use the shared deferred snapshot instead of reserving a SQLite writer under the repository-wide lock. Counts and selected canonical payload remain coherent; decoding/presentation run after snapshot release, and dirty repair retains its coordinated path. Filter/reviewer parity and blocked-writer regressions cover this narrower read-side decomposition. Canonical writer coordination remains unchanged.

Annotation-context checks now also use deferred snapshots: clean epoch reads and exact captured-scope comparisons do not reserve writers or repository coordination. Dirty context retains explicit repair, and source/topology changes still invalidate annotations. This removes another read-side reservation used by metadata workers and semantic readers, not canonical writer coordination or whole-build contention.

Initialized exemplar-journal status reads likewise use deferred snapshots without repository-wide coordination. Cold bootstrap/schema setup, invalidation, token acknowledgment and state writes remain locked. Snapshot visibility, legacy bootstrap and explicit missing-state failure are regression-covered; the three independent status calls do not claim cross-call atomicity. Single-writer vector projection and canonical writer coordination remain unchanged.

Three follow-on slices generalize the raw canonical/journal snapshot boundary, migrate bounded neighbour-context reads to it, and release full-corpus read snapshots before migration/decoding. Missing-store bootstrap remains coordinated; raw reads do not force review-projection repair. Neighbour locators/budgets and captured canonical payload order remain intact under writer contention. Full-scope reads remain document-sized, and canonical write/manager coordination still needs separate decomposition; these changes do not claim whole-build latency gains.

Six coordination follow-ups guard explicit JSONL refresh against concurrent canonical changes, verify replacement/race recovery, prevent duplicate cold initialization, preserve neighbour topology within snapshots, protect newer exemplar invalidations from stale acknowledgment, and rerun the eight large synthetic contention cases. Refresh remains visibly dirty on conflict or replacement failure and now pays for a second full canonical read under its final writer reservation. The tracker records observed timings and regression evidence; production journal/durability settings are unchanged, and canonical writer/manager decomposition plus live acceptance remain open.

The writer/manager continuation serializes summary read/modify/write in manager-then-repository order and protects deletion and snapshot-cache invalidation with repository coordination. Short cache/registry admission uses a separate lock, released before provider I/O or manager/repository acquisition; provider epoch and runtime-request capture remain under manager coordination. Regression coverage verifies competing writers, cache independence and late-provider cache responses. These process-local race fixes do not replace canonical SQLite version guards, establish cross-process manifest compare-and-swap, or deliver per-build writer decomposition. Broader decomposition and live acceptance remain open.

The post-#484 ingestion continuation separates source-extractor admission from canonical repository coordination. Upload extraction, transcription, page detection, and extraction-quality preparation run outside the repository lock; admission remains serialized within a repository so this does not introduce parallel extractor/provider execution. Admission precedes repository locking, and the admission lock is never acquired by canonical writers. Existing-asset checks and source publication remain coordinated, with an additional existing-asset check before publication. A blocked extractor no longer prevents an unrelated Record save or restart read of that save. This is a narrow removal of long-running computation from canonical coordination, not per-build writer decomposition, cross-process source publication coordination, or measured save-tail improvement.

Three bounded follow-ons stage source bytes, JSONL blocks, and metadata in private same-filesystem directories outside repository coordination, flush the staged files, then recheck the winner and rename metadata last as the visibility marker. Handled failures remove staged/partially published artifacts; interrupted unmarked content is retryable. Crash-left hidden staging directories are inert, not automatically scavenged while another ingestion could own them. Existing durability settings and the single-process repository ownership requirement remain; this is not a multi-file filesystem transaction or cross-process publication lock.

Per-build coordination begins only with checkpoint persistence. Admission and its retained lock registry are protected by repository coordination; the order is repository then checkpoint, and checkpoint persistence never reacquires repository coordination. Build deletion uses the same order and cannot resurrect a checkpoint workspace. Ordinary admitted checkpoint I/O releases the repository lock; outer caller-held repository reservations, queued same-build admission and deletion can still serialize unrelated work. Canonical Record transactions, dependency invalidation, snapshot/queue caches and manager locks keep their existing coordination. This deliberately does not migrate canonical writers wholesale.

The existing opt-in selected-read harness now also compares these source-staging and checkpoint scopes against an explicit coarse reservation around current code, with a controlled 40-ms I/O delay, two synthetic builds, canonical revision/version checks, named inclusive writer phases and bounded decode counts. Run `CORPUS_READ_BENCHMARK=/absolute/output.jsonl python -m pytest -q tests/test_review_queue_projection.py -k test_scoped_coordination_benchmark`. This is scoped coordination evidence, not a prior-deployment replay, p95 population guarantee, or live end-to-end save improvement.

Post-#453 continuation removes automatic view bookkeeping from Record activation and the ordinary activity label. The deprecated legacy POST remains a non-mutating historical-activity read; stored counts and meaningful review events are preserved. Metadata precedent batch reads and open per-field disclosures now defer new requests while the inspector is hidden, without unmounting draft-bearing editors. Responses invalidated by visibility/context changes are not installed, revision changes invalidate retained assistance, and batch failures remain visible. Already-dispatched server work is not cancelled by this visibility gate. Autocomplete facet reads now require a visible metadata inspector, bulk editor, or focus-review metadata consumer; hiding cancels in-flight client reads, and invalidated facets reload only on demand. Requested field subsets are filtered in SQL, preserving blind-review visibility. The UI still requests its build-wide field set and queue-generation changes still invalidate it; per-field demand and finer facet-generation dependencies remain follow-ups. Source-block demand gates, advanced-draft work, explicit precedent cancellation, measurement, and storage-decomposition gates remain outstanding.

The post-#455 source-block continuation removes eager activation/hydration reads. Visible Source/Evidence consumers and explicit selected-text evidence commands request blocks; exact reviewer/build/asset/Record/revision/source-binding context bounds reuse and rejects late responses. This completes the source-block demand gate, not server-side cancellation, storage decomposition, or measured latency acceptance.

The advanced-metadata continuation suppresses browser draft writes for clean activation and canonical refresh/save updates. Clean JSON formatting now waits for the visible advanced disclosure; ordinary field changes also avoid formatting its hidden draft. Recovery text restores independently of disclosure, dirty edits remain recoverable, failed saves retain their submitted draft, and successful saves do not recreate removed drafts. Production browser coverage verifies disclosure and recovery behavior. Live critical-path measurements remain outstanding.

Foreground selection now joins matching in-flight neighbour prefetches by exact build/reviewer epoch, Record invalidation generation, revision, and operational state version. Repeated matching foreground opens also retain one transport rather than aborting and restarting it; only the latest selection may activate the result or report its failure. A different context/selection, complete authoritative selection, reset, or disposal cancels the independent foreground transport. Pending prefetch admission is bounded and late prefetches cannot overwrite a newer cache entry. Cancellation of already-dispatched server work and live navigation acceptance remain outstanding.

The repository continuation uses deferred snapshots for clean selected/page/facet/aggregate reads, checks projection/schema/documentary identity inside the read transaction, and repairs only dirty/incompatible state under a separate coordinated writer transaction. Initialization is cached by database identity/schema version; decoding and presentation follow snapshot capture outside the transaction. Version 3 kept-precedent references permit selected-Record/source-unit canonical revalidation while version 2 retains its legacy fallback. Writer-lock decomposition and explicit candidate cancellation/disclosure remain outstanding. Synthetic browser and 1,000/10,000-Record read timings are recorded in the tracker; live-source/model, human-review, and contention gates remain unverified.

Kept-precedent batch reads now revalidate canonical precedent identity/evidence without candidate ranking or embedding access. Nonempty fields declare `candidates_pending`; opening that field's disclosure requests its current candidate ranking through the assigned pipeline. Empty fields do not trigger ranking, and completed results are reused for the same context. Closing/hiding, Record-context changes, and disposal abort the client transport and reject late results. This is disclosure-local provider demand and client cancellation, not cancellation of already-dispatched server/provider work.

Targeted review-save responses now carry the committed normalized payload and its same-transaction operational queue version. Queue reconciliation still determines current membership, counts, and freshness, but an exact revision/version match reuses that payload instead of fetching it again. Optimistic copies and unversioned compatibility responses cannot certify reuse; later enrichment or topology/context changes retain the current read path. Production mocked-browser text saves verify the avoided full-Record fetch in both colour schemes. This does not establish a live save-tail improvement or remove source-validation and writer contention from saves.

#### Acceptance gates

- Ordinary navigation performs no canonical mutation, dirty-marker write, revision change, exemplar scheduling, or semantic-map invalidation.
- Hidden optional inspectors perform no assistance/provider, source-block, or autocomplete requests unless another visible consumer needs them. Opening them restores full functionality and truthful provenance.
- Clean selected reads decode only requested identities, without corpus-wide scans, schema initialization, or writer reservations, and return coherent payload/version snapshots. Dirty repair, external writers, schema changes, restart, and topology changes remain correct.
- Overlapping foreground/prefetch work shares at most one current read per Record/context. Caches stay bounded; reviewer/build/revision/generation changes cannot install or disclose stale results.
- Clean advanced-metadata activation writes no draft. Unsaved recovery, sparse serialized saves, selection/viewport stability, and failed-save reporting remain intact.
- Preserve the sub-250-ms cached-navigation target. Set cold-open/save-tail budgets from the valid baseline and report before/after p50/p95 with sample sizes under enrichment and two-build contention. Work-count improvements do not replace browser measurements.
- Cover real reviewer commands, blind second opinions, exact evidence/citations, human authority, stale bindings, publication gates, cancellation, keyboard behavior, and light/dark accessibility. Run relevant backend/contracts and frontend units/typechecks, then browser cases. Regenerate GraphQL artifacts only when their contract changes.

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
