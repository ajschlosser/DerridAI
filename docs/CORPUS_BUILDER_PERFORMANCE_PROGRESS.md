<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Corpus Builder performance progress

Related contract: [implementation plan](CORPUS_BUILDER_PERFORMANCE_PLAN.md).

## Baseline and branch

- Current branch: `ajschlosser-corpus-builder-performance`; earlier checkpoints used `perf/corpus-builder-throughput`.
- Continuation baseline: fetched `master` at `ab2b097a`, including #419 and the earlier #417/#418 work.
- Working scope: persistent transactional queue projection, live cursor pagination, reviewer-visible search, incremental build summaries, and targeted frontend reconciliation. Dependency caching and later performance phases remain planned.
- No 50% improvement is claimed. Live-model preparation and human review studies have not run.

## Checkpoints

| Checkpoint                                 | State                       | Evidence                                                                                              |
| ------------------------------------------ | --------------------------- | ----------------------------------------------------------------------------------------------------- |
| Plan and tracker                           | Committed/pushed `dc0b35f0` | Scope, invariants, acceptance gates, rollout sequence                                                 |
| Baseline instrumentation                   | Partial                     | Synthetic persistence/write counts captured; stable wall-clock and end-to-end baselines pending       |
| Incremental enrichment completion          | Committed/pushed `d9c30235` | Ownership, restart, failure, and retired-record regressions                                           |
| Audio manifest preparation                 | Committed/pushed `6fff2e0e` | Transcript time locators and provider fallback                                                        |
| Remove review navigation modal             | Committed/pushed `bb066a35` | 18 production-browser cases pass; local draft recovery retained                                       |
| Restore document metadata editor           | Committed/pushed `0be91ae9` | Component-resolution regression and typechecks                                                        |
| Queue projection                           | Committed `85d74a35`        | Transactional SQLite projection, live cursors, scoped reconciliation, repository scaling measurements |
| Dependency caching / incremental exemplars | Pending                     | Extend existing mechanisms                                                                            |
| Readiness / scheduling                     | Pending                     | Preserve publication and ownership gates                                                              |
| Evaluated learning / review assistance     | Pending                     | Requires held-out evaluation                                                                          |

## Validation and measurements

Focused validation is recorded below by checkpoint; overlapping test counts are not additive. The synthetic persistence benchmark verifies fewer full-store writes, not an end-to-end speedup. Shared-machine disk variability prevents a reliable elapsed-time conclusion. Live-model preparation and human-review measurements remain outstanding.

## Next actions

1. Establish isolated real-source and end-to-end timing baselines, including browser/save tail latency, before claiming progress toward 50%.
2. Continue dependency-aware caching and incremental exemplars behind the plan's correctness gates.
3. Evaluate earlier readiness, scheduling, and review assistance separately from repository queue improvements.

## Persistence checkpoint (2026-10-02)

- Replaced per-completion full-corpus reload/save with an indexed read and existing `update_record` merge under the manager lock. The final handoff reloads authoritative records once.
- Replaced repeated list membership during queue initialization with a set and removed the obsolete serial-family/JSONL-writer comment.
- With explicit user approval, late results for retired records are ignored instead of restoring an obsolete topology snapshot.
- Three behavioral characterizations passed on unchanged implementation. Two regression tests failed as expected before the patch (repeated full saves and retired-record resurrection).
- After the patch: 51 focused backend tests passed; six opt-in benchmark cases skipped in the normal regression run. Covers human ownership, failure fallback, durable notification ordering/restart, projection refresh, family concurrency, and existing text/rerun behavior.
- The real-repository synthetic benchmark completes 20 records in a 1,000- or 10,000-record corpus, three samples per size, one worker, fake provider, no browser. Full saves fall from 21 to 1, with 20 targeted row updates; full-save rows fall from 21,000 to 1,000 and 210,000 to 10,000 respectively (95.2% less full-save row serialization). This is not an end-to-end time reduction.
- Initial timing comparison is inconclusive: the after run overlapped frontend dependency installation and showed variable disk contention. Repeat in isolation before attributing wall-clock improvements. No live-model or human-review speed claim.
- Reproduce with `PYTHONPATH=api CORPUS_PERSISTENCE_BENCHMARK=/absolute/output.jsonl python -m pytest -q tests/test_corpus_enrichment_persistence.py -k benchmark`; run against the baseline and optimized code with the same dependencies and no competing workload. Benchmark output includes sample counts, Python/platform, timings, and write counts.

## Additional user-requested work

- Fix audio preparation failing at `structure` with missing `page`.
- Remove the unsaved-review navigation modal, retaining existing draft recovery.
- Double-check recent Corpus Builder changes, prioritizing preparation, navigation, recovery, and persistence; no broad review completion claimed.

## Audio preparation checkpoint (2026-10-02)

- Reproduced the reported `structure: 'page'` failure in document-manifest sampling: transcript SourceUnits have time locators and no page field.
- Format manifest excerpts using audio time ranges/speaker labels, physical pages where present, or source-unit identity; do not fabricate audio page numbers. The source-media prompt explicitly keeps audio page bounds null.
- Preserve embedded non-PDF author metadata with `source_metadata` provenance; retain existing PDF provenance and fallback behavior. Bumped the document-manifest prompt contract to v4.
- 49 focused backend tests passed, including real transcript-block preparation through the structure stage, provider-unavailable fallback, existing manifest pipeline behavior, audio settings/topology, ownership, and build resilience. No live transcription service was used.
- Persistence implementation checkpoint `d9c30235` was pushed. Additional timing attempts showed unstable shared-machine disk latency (including a 54.6-second baseline sample at 1,000 records) and were stopped; deterministic write-count improvement is validated, but elapsed-time targets remain unverified.

## Review navigation checkpoint (2026-10-02)

- Removed the unsaved-review modal and its navigation/decision gates. Navigation never implicitly confirms unsaved values. Existing local text and advanced-JSON draft recovery remains; ordinary field edits still require an explicit save.
- Removed modal-only save/discard component APIs, refs, retry state, and English/French strings. Retained explicit advanced-metadata save and existing save-error handling.
- Updated user guidance and replaced modal tests with immediate-navigation, draft-restoration, new-build, rejection, and French keyboard coverage.
- Moved the metadata dirty-state regression out of a nested test definition so it actually executes, using public field buttons rather than removed modal-only APIs.
- App/SDK and test TypeScript checks passed; 86 focused frontend tests passed; production build passed (existing large-chunk warning). Thirteen locale/accessibility-floor/API-contract tests passed. All 18 production-browser cases passed, including desktop/laptop/short/mobile layouts, zoom reflow, draft restoration, rejection, and French keyboard navigation. An initial rejection-test failure was a missing mock response; the corrected fixture passed.
- Review found `DocumentManifestEditor` lost its import in `8cfda23c` while the build-workspace template still renders it. A new component-resolution test reproduces the failure. The approved repair is completed in the following checkpoint.

## Document editor and structural concurrency checkpoint (2026-10-02)

- Restored the build-workspace `DocumentManifestEditor` import after reproducing a missing-component failure. The regression mounts the manifest slot and checks that the real component resolves with its document metadata.
- 34 focused frontend tests passed, with app/SDK and test typechecks, touched-file ESLint, and a final production frontend build. No complete release/CI or Docker claim.
- A real split during a running enrichment worker now has integration coverage: the parent remains retired, both successor IDs are requeued, text is conserved, lineage survives, and the returned handoff matches durable state. Together with record/source-unit restructuring suites: 34 backend tests passed, six optional benchmark cases skipped.
- Review scope covered the reported audio failure, review modal and draft recovery, missing document editor, enrichment ownership/restart, and structural late-completion behavior. This is not an exhaustive audit of all Copilot-authored changes; no particular additional PR was specified.

## Bounded queue navigation checkpoint (2026-10-02)

- REST review paging now reuses matching topology positions and counts for immutable repository snapshots. Cache keys include snapshot identity, filters, and reviewer; records are copied and presented afresh for every request. Existing filter/search/count semantics are preserved.
- Reuse is bounded to four entries and 40,000 retained record references per repository. Larger snapshots fall back to uncached selection. Writes replace snapshots; external writes are detected through the existing repository signature. The cache is disposable and stores no authoritative decisions.
- Eleven characterization cases passed before implementation, while the new no-rescan regression failed as expected. After implementation: 43 queue/decision/persistence tests passed, six optional persistence benchmarks skipped. A separate visibility run passed 28 tests; GraphQL facade/indexed-read compatibility plus queue coverage passed 51 tests. Each skipped two optional queue benchmarks. Ruff passed.
- Tests cover filter results, Unicode substring search, original topology positions, pre-queue-filter counts, per-record writes, structural replacement, external writes, restart, reviewer switching, independent response copies, eviction, oversized snapshots, and mutable callers using the uncached default.
- Synthetic selection-only benchmark: 20 one-record pages, one unchanged snapshot, Unicode text search, three alternating uncached/cached samples per size, Python 3.12.14 on Windows. The cached run includes initial fill. Median totals: 1,000 records **0.1343 s -> 0.00676 s**; 10,000 records **1.3703 s -> 0.06846 s** (about 95% reduction in this component). Both benchmark cases passed. This excludes repository I/O, facets, HTTP, browser rendering, model calls, and human decisions; it is not a 95% end-to-end improvement.
- Reproduce with `PYTHONPATH=api CORPUS_QUEUE_BENCHMARK=/absolute/output.jsonl python -m pytest -q tests/test_review_queue_navigation_cache.py -k benchmark`. Use a fresh output path. The uncached comparison uses the same selection implementation with reuse disabled, isolating the cache benefit.
- Limitations: each mutation or filter/reviewer change can require a fresh scan. GraphQL initially kept the uncached default; the following checkpoint adds shared reuse. Persistent indexed projection, incremental counts/facets after edits, two-build cold-load measurements, and the 50% end-to-end target remain outstanding.

## Shared REST/GraphQL selection checkpoint (2026-10-02)

- REST and GraphQL now call the same repository selection boundary and reuse the same bounded cache for repository-owned immutable snapshots. Page navigation across either transport avoids repeated corpus selection scans for the same filters and reviewer.
- The boundary checks snapshot ownership by identity. Caller-owned mutable lists and evicted snapshots use the uncached selector; each response still receives fresh reviewer presentation. No API/schema or authoritative-state changes.
- Two cross-transport no-rescan regressions failed before the change; the mutable-list characterization passed. After implementation, 83 focused queue, GraphQL, decision, and second-opinion tests passed; two optional queue benchmarks skipped. Ruff passed. Master was refreshed and remains an ancestor of this branch.
- This extends the previous selection optimization to GraphQL; it does not establish new end-to-end timings. Persistent transactional projection, incremental post-edit counts/facets, cold-load measurements, dependency caching, and evaluated learning remain planned.

## Persistent review-queue projection checkpoint

- Canonical per-build SQLite Records remain authoritative. Versioned queue/search/facet/metric tables are derived and updated in the same transaction as ordinary Record writes; topology replacements also rebuild their contributions. Dirty-row triggers detect canonical writes from another repository instance. Restart, schema/projection changes, and missing projection tables repair from canonical payloads.
- REST and GraphQL pages/facets no longer load the full corpus. Ordinary targeted edits use incremental build aggregates and bounded issue summaries rather than reloading Records for aggregation. Full initialization, topology replacement, and explicit repair still perform corpus-wide work.
- Search preserves literal Unicode casefolded JSON substring matching, including punctuation and `%`/`_`. Blind-review search intentionally uses reviewer-visible values: sealed answers cannot change hits, filtered counts, or facets. Queue categories retain overlapping membership and independent pre-queue-filter counts.
- Live source-order cursors coexist with offset paging. Ordinary updates preserve cursors while totals/membership remain live; topology or explicit repair expires them. Reviewer/filter/build mismatches are rejected. Operational row `state_version` and page generations are distinct from scholarly `record_revision` and are not canonical publication fields.
- Full-record payloads and their operational versions are read in one transaction, so a concurrent writer cannot label an older payload with a newer version. Queue versions are excluded from canonical writes, FieldAssertions, publication JSONL, and custom scholarly field names.
- Scoped frontend invalidation preserves unaffected Record reads, drafts, and selection guards. Coalesced authoritative reconciliation refreshes membership, backfill, counts, and facets; sequential navigation uses cursors, with offsets retained for random access/history.
- Final combined queue/transport, structural/source-unit, publication, FieldAssertion, and metadata-schema regression run: **220 passed, 12 opt-in benchmarks skipped**. Four opt-in repository benchmark cases passed separately. Backend Ruff and mypy passed. Focused frontend validation: **144 unit tests passed**, application/test typechecks and touched-file ESLint/Prettier passed. Generated GraphQL schema/codegen checks passed. Production frontend and Storybook builds passed with existing chunk-size warnings. **19 production-browser cases passed**, including rejection/draft navigation and live cursor paging. The browser gate used an available port because the shared default port served a different stale build; no shared server was changed. Docker, live-model preparation, and human review studies were not run; this is not a release-readiness claim.
- Repository-wide Prettier reports 1,306 files in the existing Windows checkout. An unchanged `web/package.json` is formatted in HEAD but fails locally solely because checkout uses CRLF. Changed files pass with the repository's generated-artifact exclusions; unrelated files were not reformatted.
- PR preparation merged refreshed master `e751a365`. The complete backend regression suite then passed **1,846 tests**, with 14 opt-in cases skipped, using a correctly quoted Windows temp path; 15 transport contract tests passed. Full frontend tests passed 1,471 cases but the two unchanged realtime-polling ratchet cases failed on Windows path separators. Full mypy reported 10 errors in seven unchanged pipeline modules. The broader preflight also encountered Windows SDK-consumer process-launch incompatibility, generated SDK output being picked up by lint, and browser failures against the old production build/dev Storybook. These are not a green full-preflight result and must not be represented as one; the earlier focused gates remain distinct.
- Three samples per size/build/mode on Windows 11, Python 3.12.15. Median seconds below compare current snapshot-selection reads with projection reads; both modes use current canonical writes and human FieldAssertion overrides. The comparison is not an exact prior-deployment baseline. Each warm measurement performs 20 one-record pages **per build**; cold/edit columns total all listed builds.

| Records/build | Builds | Cold: snapshot → projection | Warm 20 pages: snapshot → projection | Edit + read: snapshot → projection |
| ------------- | ------ | --------------------------- | ------------------------------------ | ---------------------------------- |
| 1,000         | 1      | 0.304 → 0.010               | 0.00382 → 0.194                      | 0.178 → 0.036                      |
| 1,000         | 2      | 0.629 → 0.021               | 0.00827 → 0.405                      | 0.349 → 0.061                      |
| 10,000        | 1      | 3.408 → 0.081               | 0.00384 → 1.676                      | 2.036 → 0.105                      |
| 10,000        | 2      | 7.146 → 0.171               | 0.00782 → 3.490                      | 3.927 → 0.197                      |

- Cold payload decoding falls from all 1,000/10,000 Records to one selected Record per build; the full cold/warm/edit sequence decodes 23 rather than 2,001/20,001 payloads per build. Correctness assertions verify authoritative post-edit facet changes, not just timing.
- **Trade-off:** unchanged in-memory snapshot paging is faster than fresh transactional SQL/search reads. Projection warm averages remain approximately 10–87 ms per repository page in these samples, but these are averages/medians, not p95 or browser latency guarantees. Projection gains are cold loading and bounded post-edit decoding, not faster warm snapshot-cache hits.
- Measurements include repository search, counts, facets, and targeted writes; exclude initial projection construction, HTTP, browser rendering, live models, and human decisions. The shared machine and three-sample runs do not establish population tail latency or an end-to-end improvement. Real-source/live-model/human-review studies and the 50% target remain outstanding.
- Reproduce with a fresh `CORPUS_PROJECTION_BENCHMARK=/absolute/output.jsonl` output path and `python -m pytest -q tests/test_review_queue_projection.py -k repository_projection_benchmark`. Use the same dependencies and avoid competing workloads for an isolated comparison.
