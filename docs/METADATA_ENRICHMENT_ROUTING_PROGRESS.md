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

# Metadata enrichment routing progress

Updated: 2026-10-04. Branch: `task/metadata-candidate-routing`.

This is the authoritative resume point for the revised Pipeline Studio candidate-routing implementation plan. Historical metadata enrichment now executes through the generic graph engine. Adaptive routing is not enabled; no latency improvement is claimed.

## Checkpoints

| Step                                                    | Status   | Evidence                                                                                                                  |
| ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| Generic named-port execution foundation                 | Complete | `0eee61b7`, `d2e52720`; repeated stages, branching, fan-in, fallbacks, empty-branch skips, safe telemetry                 |
| Typed metadata artifacts and computational traits       | Complete | Explicit candidate/hypothesis/inference-request/proposal/embedding types; required/produced port traits; run-input traits |
| Consumer terminal guarantees                            | Complete | Compile-time type/trait checks; run-time terminal-output enforcement; `any` cannot satisfy a concrete final contract      |
| Historical enrichment migration to generic executor     | Complete | `9381c191`; generic scheduling with historical provider/ledger/ownership/concurrency parity                               |
| Safe parallel scheduling                                | Pending  | Executor is serial; capability declarations and concurrency tests required                                                |
| Baseline benchmark and instrumentation                  | Pending  | Original baseline: `94ca23d9`; no real-provider benchmark run                                                             |
| Candidate packet, collection, aggregation, invalidation | Pending  | Reuse existing memory, semantic identity, NLP/DI and evidence contracts                                                   |
| Current-record support and observe-only router          | Pending  | Must precede activation of RESOLVE/VERIFY                                                                                 |
| RESOLVE, VERIFY, scoped INFER and proposal fan-in       | Pending  | No new routing behavior enabled                                                                                           |
| Retrieval consolidation, calibration, benchmark tuning  | Pending  | No 33% performance or reviewer-quality claim                                                                              |

## Current contract

- Traits are code-owned computational guarantees. Every bound source must satisfy the receiving port; fan-in cannot borrow a guarantee from another branch.
- Fallbacks carry the failed stage's input. They cannot inherit guarantees from its unproduced output, including when `next` and fallback share a target.
- Terminal artifacts must satisfy the purpose's output type and `required_output_traits`. Missing terminal execution is a visible failure. Consumer outputs are returned separately as `GraphResult.terminal_outputs`.
- Computational outputs cannot establish `human_confirmed`, `human_override`, or `reviewer_approval`. Existing authority/access obligations remain outside graph computation.
- Named-output bindings determine delivered types; primary output summaries do not override explicit wiring.
- Empty trait fields are omitted from serialization. Existing catalog bytes and built-in identities remain unchanged. New types/traits are available to server contracts; no new production strategy or UI control is registered yet.
- Handlers still validate payloads and evidence. Declared traits are not a substitute for checking actual current-record support at the domain boundary.

## Earlier validation: artifact traits checkpoint

- 93 focused backend tests passed: graph execution, wiring/analysis, contracts, workflow semantics, and catalog fixture.
- Ruff passed for changed Python files; targeted mypy passed for the five changed pipeline modules.
- 47 focused frontend tests passed across workflow semantics, overrides, graph domain, and graph component suites. Frontend application/test typechecks and targeted ESLint passed. Prettier checked changed frontend/docs files.
- Catalog exporter `--check` passed; regeneration was unnecessary because legacy serialized contracts are unchanged.
- Full preflight was attempted. Backend lint/syntax, full frontend lint, frontend typechecks, and the production app build passed. Backend regression reported 865 passed, 48 failed, 2 skipped, and 115 collection errors; failures include missing HTTPX/FastAPI/JSON repair/Strawberry and incomplete test imports. None of the new graph/trait tests failed. Remaining broader failures are unresolved, not accepted as passing.
- Preflight also could not find the mypy CLI (targeted module-based mypy passed) and could not validate the generated GraphQL artifact. The separately checked pipeline catalog is current. Real-provider latency and reviewer-quality benchmarks have not run.

## Integration

PR #508 merged into master at `51b481cf`; that master was merged into this branch before the trait changes. The migration checkpoint also incorporates master `caad9c43`, including PR #512. Its Research configuration override contracts are retained. No Research settings or authority behavior was changed by this work.

## Next action

Add explicit concurrency capabilities and safe parallel scheduling to the generic executor, preserving definition order for merges/traces and provider capacity controls. Then construct the candidate packet and collection stages; keep routing observe-only until current-record support and authority invariants pass. The historical compiler still accepts its bounded provider graph; arbitrary adaptive graph compilation awaits registered domain handlers.

## Historical executor migration checkpoint (`9381c191`)

- Metadata provider scheduling now follows the generic executor's resolved ports and selected edges. The assigned pipeline, built-in versions, attempt budgets and schema-derived tasks remain unchanged.
- One executor snapshot is compiled per session. Each call supplies server-owned task context; sibling calls share only locked telemetry. Call-local stage paths and existing execution-ledger linkage are retained.
- `StageFailure` lets a server handler declare a coded failure edge without leaking private exception text. Metadata retains its historical unavailable/timeout/error classification and original caller error aggregation.
- Identity/trace persistence remains on the existing session surface. Reconciliation, evidence validation and canonical authority handling are unchanged. No adaptive branches or parallel graph scheduling are enabled.
- Before migration: 169 passed, 6 skipped. After migration: the same suite passed; expanded parity coverage passed 266 tests with 6 existing skips. Tests also prove the legacy provider loop is unused, compilation happens once per session, and cancellation does not invoke fallback.
- Ruff and targeted mypy passed. Full backend mypy passed for 265 source files. Schema/catalog checks passed (6 tests) after moving dependencies into the workspace Python environment; the first preflight generated-artifact gate had lost the target dependency paths.
- Full backend regression: 2340 passed, 28 skipped, 4 failed. Full frontend lint/typechecks and production build passed. Full preflight remains red because of the four failures below; no CI or real-provider performance claim is made.

### Existing failures reproduced on the baseline

All four also fail on an isolated archive of pre-migration commit `c2192a5e`, using the same workspace environment:

- `test_review_queue_projection.py::test_projection_refresh_rejects_external_write_and_recovers`: projection refresh assertion.
- `test_gutenberg_catalogue.py::test_streamed_archive_extraction_installs_text_in_database_and_zip_is_disposable`: Windows file-handle conflict.
- `test_gutenberg_catalogue.py::test_pause_during_inflight_chunk_does_not_resurrect_download`: Windows file-handle conflict.
- `test_corpus_enrichment_handoffs.py::test_loaded_model_cache_is_detached_and_rejects_late_response`: late model-cache response assertion.

These remain unresolved and outside this checkpoint. Fix them separately before claiming full regression/merge readiness.
