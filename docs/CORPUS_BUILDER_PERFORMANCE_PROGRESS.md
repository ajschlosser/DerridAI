<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Corpus Builder performance progress

Related contract: [implementation plan](CORPUS_BUILDER_PERFORMANCE_PLAN.md).

## Baseline and branch

- Branch: `perf/corpus-builder-throughput`.
- Fetched master: `ebf30937` on 2026-10-02; includes #417 and #418.
- Working scope: incremental persistence, audio preparation, review navigation, and document-editor regressions; queue and caching increments remain planned.
- No 50% improvement is claimed. Live-model preparation and human review studies have not run.

## Checkpoints

| Checkpoint | State | Evidence |
| --- | --- | --- |
| Plan and tracker | Committed/pushed `dc0b35f0` | Scope, invariants, acceptance gates, rollout sequence |
| Baseline instrumentation | Partial | Synthetic persistence/write counts captured; stable wall-clock and end-to-end baselines pending |
| Incremental enrichment completion | Committed/pushed `d9c30235` | Ownership, restart, failure, and retired-record regressions |
| Audio manifest preparation | Committed/pushed `6fff2e0e` | Transcript time locators and provider fallback |
| Remove review navigation modal | Committed/pushed `bb066a35` | 18 production-browser cases pass; local draft recovery retained |
| Restore document metadata editor | Committed/pushed `0be91ae9` | Component-resolution regression and typechecks |
| Queue projection | Pending | Next performance increment; preserve reviewer isolation |
| Dependency caching / incremental exemplars | Pending | Extend existing mechanisms |
| Readiness / scheduling | Pending | Preserve publication and ownership gates |
| Evaluated learning / review assistance | Pending | Requires held-out evaluation |

## Validation and measurements

Focused validation is recorded below by checkpoint; overlapping test counts are not additive. The synthetic persistence benchmark verifies fewer full-store writes, not an end-to-end speedup. Shared-machine disk variability prevents a reliable elapsed-time conclusion. Live-model preparation and human-review measurements remain outstanding.

## Next actions

1. Characterize queue selection, reviewer overlays, and mutation invalidation before introducing a derived queue projection.
2. Implement the smallest equivalent queue increment with restart and filter-equivalence tests.
3. Establish isolated timing baselines and measure preparation/review latency before claiming progress toward 50%.
4. Continue the dependency-cache and evaluated-learning phases behind the plan's correctness gates.

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
