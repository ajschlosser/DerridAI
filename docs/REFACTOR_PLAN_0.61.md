# 0.61.0 decomposition plan

> Historical implementation plan. The work described here belongs to the 0.61.0 release and later decomposition has superseded several “follow-up” statements. Use [ARCHITECTURE.md](ARCHITECTURE.md) for current module ownership.

Approved before implementation. Baseline: master `4184f97`, 474 Python tests,
30 Vue component tests, and 36 Playwright/axe tests. Typechecking, production
build, and Storybook build pass. Local Windows browser tests use port 16006
and one worker because port 6006 is unavailable and parallel cold loads timed out.

1. Extract pure metadata vocabularies, normalization, and ownership constraints
   into `corpus_metadata.py`. Re-export existing names from `corpus_builder.py`.
2. Split `_enrich_record` into source-quality gating, context preparation,
   metadata-family execution, and reconciliation helpers. Preserve callback,
   cancellation, provenance, reviewer-ownership, and retry semantics.
3. Split `_run` into manifest/scope preparation, topology construction,
   enrichment scheduling, and final validation/checkpoint helpers. Preserve
   restart checkpoints and live reviewer edits.
4. Extract publication schema validation and serialization as pure functions,
   retaining manager methods as compatibility delegates.
5. Extract complex frontend lifecycle/review derivation and provider-budget
   logic into domain functions/composables with focused unit tests. Keep simple
   local presentation state in the component.

Each increment gets a separate commit and the existing relevant suites must
pass before the next increment. Imports and callers are searched after moves.
Behavioral fixes remain separate from structural changes.

Natural later seams are PDF source/repository persistence, boundary segmentation
and validation, FastAPI routers, and Chroma search/cache/synchronization modules.
Those larger splits are follow-ups: changing all of them in this release would
obscure review of the two long orchestration methods and their invariants.
