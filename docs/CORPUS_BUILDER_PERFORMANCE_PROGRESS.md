<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Corpus Builder performance progress

Related contract: [implementation plan](CORPUS_BUILDER_PERFORMANCE_PLAN.md).

## Baseline and branch

- Branch: `perf/corpus-builder-throughput`.
- Fetched master: `ebf30937` on 2026-10-02; includes #417 and #418.
- Working scope: first measured persistence optimization; later increments remain planned.
- No 50% improvement is claimed. Live-model preparation and human review studies have not run.

## Checkpoints

| Checkpoint                                 | State   | Evidence                                                                    |
| ------------------------------------------ | ------- | --------------------------------------------------------------------------- |
| Plan and tracker                           | Written | Detailed scope, invariants, acceptance gates, and rollout sequence recorded |
| Baseline instrumentation                   | Pending | Characterize full-store saves and affected-record updates before edits      |
| Incremental enrichment completion          | Pending | Preserve latest human decisions and durable recovery                        |
| Queue projection                           | Pending | Follow persistence checkpoint                                               |
| Dependency caching / incremental exemplars | Pending | Extend existing mechanisms                                                  |
| Readiness / scheduling                     | Pending | Preserve publication and ownership gates                                    |
| Evaluated learning / review assistance     | Pending | Requires held-out evaluation                                                |

## Validation and measurements

No implementation tests or new timings recorded yet. The first benchmark must separate synthetic persistence cost from end-to-end model processing and must record the exact baseline and method.

## Next actions

1. Commit and push planning documents.
2. Characterize existing persistence and human-edit preservation tests; establish a reproducible baseline.
3. Replace repeated full-store completion saves using the existing incremental persistence contract.
4. Run focused regressions and comparison benchmarks; update this tracker, commit, and push.
