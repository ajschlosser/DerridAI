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
| Safe parallel scheduling                                | Complete | `394745cf`; bounded server opt-in, stable fan-in/traces, shared capacity and cancellation coverage                        |
| Baseline benchmark and instrumentation                  | Partial  | Isolated runner and character/lookup counters implemented; real-provider case/model selection remains pending             |
| Candidate packet, collection, aggregation, invalidation | Complete | `fcf4ab99`; server-only collection foundation; production registration and routing remain disabled                        |
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

Implement current-Record support validation and the observe-only router over the collected packets. Do not activate RESOLVE/VERIFY or register a production adaptive graph until support, reviewer visibility, authority and failure invariants pass. The historical compiler still accepts its bounded provider graph; the new collection contracts/handlers are available only to explicit server-owned observation graphs, outside the public catalog.

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

## Safe parallel scheduling checkpoint (`394745cf`)

- Server-owned `ConcurrencyCapability` declarations opt handlers into parallel execution. The default worker limit is one; undeclared handlers form serial barriers. Historical metadata scheduling remains unchanged.
- Independent ready stages run in bounded waves. Edge and explicit-port dependencies finish before consumers; outputs, merges and traces retain definition order regardless of completion order.
- A capacity key shares one semaphore across strategies and concurrent calls on an executor. Conflicting limits are rejected. Wider provider quotas remain the adapter's responsibility; separate executors do not share this semaphore.
- Opted-in handlers must be thread-safe and treat inputs as read-only. Capabilities are supplied by server code, never editable pipeline JSON. Existing catalog bytes, assignment identities and public schema are unchanged.
- Fatal failure/cancellation cancels queued futures and joins running work before returning. In-flight provider I/O still needs adapter cancellation support. Elapsed traces include local capacity waiting, excluding waits for earlier traces to be projected.
- Added ten tests covering actual overlap, reverse completion order, default/undeclared serialization, unsafe-handler barriers, capacity across runs, empty branches, fallbacks, fatal failure/cancellation and inconsistent capacity declarations.
- Expanded parity: 276 passed, 6 existing skips. Ruff and targeted mypy passed. Full backend typechecking passed (265 source files); catalog exporter check passed. Full backend regression: 2349 passed, 28 skipped, 5 failed. Four failures match the documented baseline failures; the additional provider-profile switch test hit Windows `os.replace` access denial and passed isolated reruns on both this branch and baseline `c2192a5e`. Frontend lint, app/test typechecks and production build passed; dependency-selected frontend unit tests selected no files. Full preflight remains red. The checkpoint push uses the documented preflight bypass after this completed run; it does not indicate merge readiness.
- Merged current master `7f6c3015` (PR #513) at `0df67aff` before expanded validation. No adaptive routing, new production provider concurrency or latency claim is enabled.

## Candidate collection foundation checkpoint (`fcf4ab99`)

- Added typed, context-bound candidate packets and server-owned contracts/handlers for NLP, provider-neutral Document Intelligence person-indexing hints, exact adjudication memory, reviewed precedents and candidate aggregation. These are not registered in the public strategy catalog or selected by a production assignment. Historical enrichment behavior, providers and call counts remain unchanged; an observe-only router is still the next step.
- Collection snapshots its Record/schema and exact-memory rows once. Packet identity includes full source/text locators, RecordRevision, schema hash, requested fields, current values/assertion selection/evidence, projection payloads, canonical exemplar snapshots and caller-owned reviewer/configuration/memory epochs. Fan-in rejects any incompatible packet or graph context. No candidate artifact is persisted on canonical Records.
- Existing NLP digest and exact-span checks, Document Intelligence text/source fingerprint gates, exact-memory keys, schema field/semantic identities and semantic value keys are reused. Renamed indexing fields retain stable identities. Missing safe semantic keys stay unavailable; candidate collection does not invent confidence.
- Every candidate is advisory and current-Record support remains unchecked. Historical evidence retains its original Record/revision/source; it never becomes evidence for the current Record. Human-confirmed/override provenance is required for reviewed exemplars but does not confer authority on the new candidate. Explicit absence, corrections, rival values and contributing origins remain distinct. Exact duplicate candidates are removed, with a 32-candidate per-field cap and explicit cap diagnostics.
- Callers must provide canonical exemplars already selected under schema retrieval policy and reviewer/blind-review visibility rules; collection does not query vector projections or bypass those boundaries. Document Intelligence collection currently covers person-indexing hints only; quotation/discourse interpretation awaits the support/router checkpoint. Exact-memory acquisition errors propagate visibly; stale, failed, unavailable and empty annotation states have distinct bounded diagnostics.
- New tests cover unchanged legacy span contracts, stale/malformed offsets, source-location changes, real exact-memory lookup, absence/correction distinction, ineligible precedents, same-revision dependency changes, input snapshots, semantic field renaming, bounded/deduplicated aggregation, generic named-port fan-in and source-free traces.
- Validation: 175 focused tests passed, including 35 new candidate tests and existing enrichment/graph/contracts/catalog coverage. Ruff and targeted mypy passed. Full backend lint, full mypy (266 source files), syntax, frontend lint, frontend application/test typechecks and production build passed in preflight. Dependency-selected frontend unit tests selected no files. Initial preflight could not run regression because pytest-xdist was missing; installed the runner in this chat's scratch directory and launched the full regression separately. The full backend regression then reported 2306 passed, 29 skipped, 20 failed and one collection error (missing Pillow/PIL). All 20 failing tests and the collection error reproduced on an isolated pre-collection archive of `8248afec` using the same environment (20 failed, one error). They cover researcher text policy, review projection, Windows/CRLF hook fixtures, Gutenberg file handles, publication/provenance and late model-cache responses. None of the new candidate tests failed. These are unresolved baseline/environment failures, not accepted passes; full preflight remains red. The checkpoint push uses the documented preflight bypass after this completed validation and does not imply merge readiness.
- No real-provider benchmark, latency improvement, calibrated resolution, current-Record support, reviewer-quality improvement or merge-readiness claim is made.

- Merged current master `1eb7a14b` at `8248afec` before this checkpoint. Prettier checked every changed supported file; the initial Windows line-ending notices were normalized without semantic changes. The PR is a draft because the broader regression gate remains red.

## Paused checkpoint: baseline runner and instrumentation (`33beed23`)

User requested a pause at this checkpoint to continue in a new session. At that pause, candidate packet/collection work had not begun; the later foundation checkpoint above now supplies server-only collection contracts and handlers. The baseline phase remains partial: no real-provider timing or reviewer-quality result has been collected. The pending question is which local benchmark corpus and provider/model to use.

- Before edits: 59 baseline tests passed. After edits: 208 focused tests passed with 6 existing skips; targeted mypy passed for all three changed backend modules. Full backend mypy passed for 266 files. Full backend regression finished with 2352 passed, 28 skipped and 5 failures. Four match the previously documented baseline failures; the fifth is `test_review_queue_projection.py::test_selected_reads_with_concurrent_canonical_writes[wal-2]`, not investigated in this paused checkpoint. Frontend lint, application/test typechecks and production build passed; dependency-selected frontend unit tests selected no files. Full preflight remains red. Remote checkpoint pushes use the documented preflight bypass; they do not indicate merge readiness.
- Provider attempt counters now measure actual prompt characters and raw response characters, including repair prompts, retries and malformed output. Counts are added to existing family CALL ledger events. Raw text and credentials are not added to counters; actual provider token usage stays unavailable.
- `metadata_candidate_workload` records exact lookup count, distinct keys and duplicate count. No lookup behavior changed. Regression coverage confirms preparation performs two same-key lookups per schema field even for families subsequently skipped. The collection checkpoint must replace those repeated reads with one run-local snapshot per exact key.
- Added `api/app/metadata_enrichment_benchmark.py` and `scripts/benchmark_metadata_enrichment.py`. The CLI isolates system/auth/Chroma stores before importing application configuration and uses a temporary corpus repository. It invokes the historical `corpus.metadata_enrichment.current@2` through the existing enrichment/reconciliation path, starts each repeat with a fresh record copy, persists local JSON and emits only hashed input identity and measurements.
- This first benchmark profile disables cross-build/reviewer/rejection memory. It measures direct enrichment plus local JSON persistence, excluding job admission, memory retrieval and reviewer quality. It reports failed family calls explicitly. It cannot support a production end-to-end latency or 33% improvement claim.
- Real-provider execution has not run. The scripted-provider smoke test exercises the runner but is not a latency baseline. Original reference commit remains `94ca23d9`; the immediate pre-instrumentation checkpoint is `a7d6d553`.

### Resume command and private input

Prepare a private UTF-8 case JSON with `case_id`, optional `version`, exact `schema` snapshot, `build` (manifest/source digest), `records` (IDs/revisions/text/source bindings), and `request` (provider/model/generation/families/concurrency settings). Use researcher-approved source text and an existing provider profile; credentials may be supplied privately in the case but are excluded from the report. Do not commit the private case or normalized temporary records.

```powershell
../venv/Scripts/python.exe scripts/benchmark_metadata_enrichment.py --case ../metadata-benchmark-case.json --output ../metadata-baseline-report.json --baseline-commit a7d6d553 --repeats 3
```

Record the chosen corpus/configuration and the report summary here. For A/B runs, preserve the fixture input fingerprint, memory profile, provider configuration and environment. Then implement candidate sources, semantic identity aggregation, corrections/absence, fingerprint invalidation and named-port collection handlers. Preserve human ownership and historical prompt behavior while consolidating exact lookups. Do not enable adaptive routing in that checkpoint.

Concurrent integration: preserved `33beed23` and `4ba99d92` baseline-runner/instrumentation commits. The existing production path still performs its historical exact-memory lookups; the new collector snapshots each requested exact key once, but production lookup consolidation is a follow-up integration step. Real-provider case/model selection remains pending alongside current-Record support and the observe-only router. No private benchmark case was selected or run in this chat.
`nPost-integration validation: 178 focused tests passed, including the concurrent benchmark-runner tests; full backend Ruff and full mypy passed for 267 source files. The earlier full regression and its baseline reproduction preceded this integration; no green full-regression claim is made for the merged head.
