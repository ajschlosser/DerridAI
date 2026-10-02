<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Corpus Builder performance progress

Related contract: [implementation plan](CORPUS_BUILDER_PERFORMANCE_PLAN.md).

## Baseline and branch

- Branch: `perf/corpus-builder-throughput`.
- Fetched master: `ebf30937` on 2026-10-02; includes #417 and #418.
- Working scope: first measured persistence optimization; later increments remain planned.
- No 50% improvement is claimed. Live-model preparation and human review studies have not run.

## Checkpoints

| Checkpoint                                 | State                       | Evidence                                                                    |
| ------------------------------------------ | --------------------------- | --------------------------------------------------------------------------- |
| Plan and tracker                           | Committed/pushed `dc0b35f0` | Detailed scope, invariants, acceptance gates, and rollout sequence recorded |
| Baseline instrumentation                   | Pending                     | Characterize full-store saves and affected-record updates before edits      |
| Incremental enrichment completion          | Pending                     | Preserve latest human decisions and durable recovery                        |
| Queue projection                           | Pending                     | Follow persistence checkpoint                                               |
| Dependency caching / incremental exemplars | Pending                     | Extend existing mechanisms                                                  |
| Readiness / scheduling                     | Pending                     | Preserve publication and ownership gates                                    |
| Evaluated learning / review assistance     | Pending                     | Requires held-out evaluation                                                |

## Validation and measurements

No implementation tests or new timings recorded yet. The first benchmark must separate synthetic persistence cost from end-to-end model processing and must record the exact baseline and method.

## Next actions

1. Commit and push planning documents.
2. Characterize existing persistence and human-edit preservation tests; establish a reproducible baseline.
3. Replace repeated full-store completion saves using the existing incremental persistence contract.
4. Run focused regressions and comparison benchmarks; update this tracker, commit, and push.

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
- App/SDK and test TypeScript checks passed; 86 focused frontend tests passed; production build passed (existing large-chunk warning). Thirteen locale/accessibility-floor/API-contract tests passed. Browser verification is being finalized; initial run passed 17/18, with the new rejection case missing a mock command response; fixed that fixture and reran.
- Review found `DocumentManifestEditor` lost its import in `8cfda23c` while the build-workspace template still renders it. A new component-resolution test reproduces the failure. User approved the repair; implementation is next.
