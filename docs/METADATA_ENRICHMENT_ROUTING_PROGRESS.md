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

Updated: 2026-10-04. Branch: `task/metadata-routing-continuation`.

This is the authoritative resume point for the revised Pipeline Studio candidate-routing implementation plan. Historical metadata enrichment now executes through the generic graph engine. Adaptive routing is not enabled; no latency improvement is claimed.

## Checkpoints

| Step                                                    | Status   | Evidence                                                                                                                        |
| ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Generic named-port execution foundation                 | Complete | `0eee61b7`, `d2e52720`; repeated stages, branching, fan-in, fallbacks, empty-branch skips, safe telemetry                       |
| Typed metadata artifacts and computational traits       | Complete | Explicit candidate/hypothesis/inference-request/proposal/embedding types; required/produced port traits; run-input traits       |
| Consumer terminal guarantees                            | Complete | Compile-time type/trait checks; run-time terminal-output enforcement; `any` cannot satisfy a concrete final contract            |
| Historical enrichment migration to generic executor     | Complete | `9381c191`; generic scheduling with historical provider/ledger/ownership/concurrency parity                                     |
| Safe parallel scheduling                                | Complete | `394745cf`; bounded server opt-in, stable fan-in/traces, shared capacity and cancellation coverage                              |
| Baseline benchmark and instrumentation                  | Partial  | Isolated runner and character/lookup counters implemented; real-provider case/model selection remains pending                   |
| Candidate packet, collection, aggregation, invalidation | Complete | `fcf4ab99`; server-only collection foundation; production registration and routing remain disabled                              |
| Current-record support and observe-only router          | Complete | Exact current-locator checks and server-only advisory route observations                                                        |
| RESOLVE, VERIFY, scoped INFER and proposal fan-in       | Complete | Server-only proposal routing, exact evidence gates, scoped structured adapters and ordered terminal fan-in; production disabled |
| Retrieval consolidation, calibration, benchmark tuning  | Pending  | No 33% performance or reviewer-quality claim                                                                                    |

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

Continue with retrieval consolidation, calibration and benchmark tuning. Choose a researcher-approved local benchmark corpus and provider/model, preserve A/B input/configuration fingerprints, and measure reviewer quality and complete enrichment latency before production activation. The experimental routing adapter is server-only; existing historical enrichment assignments, call counts and authority reconciliation remain unchanged. Production integration still requires calibrated policy and a reviewer-visible proposal/reconciliation path.

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

Post-integration validation: 178 focused tests passed, including the concurrent benchmark-runner tests; full backend Ruff and full mypy passed for 267 source files. The earlier full regression and its baseline reproduction preceded this integration; no green full-regression claim is made for the merged head.

Final handoff: draft PR #517 is open at https://github.com/ajschlosser/DerridAI/pull/517. After the validated integration was pushed, master advanced to `7243f61e` (audio word/speaker alignment, PR #514). That later master is not merged into this checkpoint; refresh it and revalidate before claiming merge readiness. Work stopped with 16% of the five-hour usage window remaining, as requested.

## Current support and observe-only routing checkpoint (2026-10-04)

- Added `metadata_candidate_observation.py`: typed, read-only route observations bound to the exact collection snapshot. Changed Record/schema/reviewer/configuration dependencies, incompatible packet bindings, mismatched field identities and out-of-scope candidates fail visibly.
- Current support checks require matching Record ID, RecordRevision and SourceDocument, integer offsets (booleans rejected), bounds and an exact text slice. Only NLP current locators establish `exact_mention`; historical precedents, exact memory and Document Intelligence hints never acquire current evidence by transfer. Semantic support remains explicitly unchecked.
- A single exact person-indexing value suggests RESOLVE; rival candidates, corrections, absence and other candidate-bearing fields suggest VERIFY; candidate-free fields suggest scoped INFER. These labels are observations only: no resolver, verifier or provider executes, no canonical field changes, and no human authority is established. Duplicate origins conservatively remain separate and can force VERIFY; no calibrated confidence is invented.
- Server-only strategy/handler consumes `metadata_candidate_set` and returns `metadata_hypothesis_set` through named ports. Public registration, UI controls and production assignments remain unchanged. Callers retain responsibility for canonical exemplar selection and reviewer/blind-review visibility, as at the collection boundary. The observation API does not create a new client-facing review surface.
- Refreshed master to `c4dc05aa` before validation. 233 focused tests passed across candidate collection/observation, generic execution, contracts, workflow semantics, public catalog, historical enrichment, benchmark runner and human ownership/reruns. Fifteen new cases cover invalid/current/historical locators, stale snapshots, rival/absent/corrected candidates, incompatible fields, scoped empty routes, read-only authority and named-port/source-free traces. Ruff and catalog exporter `--check` passed. No dead code was found in the touched implementation.
- Validation limitations: the reused Python environment lacks mypy. Full preflight is recorded below; no full-regression, real-provider latency, reviewer-quality, calibrated resolution or merge-readiness claim is made. The initial sandbox test run could not create temporary storage; rerunning with scratch storage under this workspace passed. Git Bash required execution outside the Windows sandbox.

- Checkpoint implementation commit: `ad0a7fe7`. Full preflight attempted after commit: full backend Ruff and Python syntax passed; required formatting gate could not find this fresh clone's `web/node_modules`, generated-artifact gate reported stale/unverifiable artifacts, mypy was missing, and full regression could not start because pytest-xdist was missing (`-n`/`--dist` unsupported). The separately executed public pipeline catalog check passed, and the touched Markdown was formatted with the existing workspace Prettier. These limitations are not accepted passes. Commit/push use `DERRIDAI_SKIP_PREFLIGHT=1` after the manual targeted checks and this failed full-preflight attempt.
- Stopping after this bounded observation checkpoint with 11% of the five-hour allowance remaining at the latest usage check, above the requested 8% floor. Resume with semantic-support/reviewer gates and RESOLVE/VERIFY/scoped INFER/proposal fan-in; do not enable adaptive production routing based on exact mention occurrence alone.

## Experimental RESOLVE/VERIFY/scoped INFER/proposal fan-in checkpoint (2026-10-04)

- Added a server-only `CandidateRouting` adapter and code-owned graph contracts/handlers. RESOLVE consumes exact current person-indexing mentions, produces schema-validated list/text values with exact evidence and unavailable confidence, and makes no provider call. It establishes mention occurrence only, never attribution or reviewer approval.
- VERIFY evaluates candidate-bearing fields through an injected field-scoped adapter. Returned values must belong to the supplied candidates (including list cardinality), pass current schema/placeholder/control-vocabulary checks, and carry matching Record ID/revision/SourceDocument, exact integer offsets and quote text. Semantic judgments retain `model_inferred` derivation. Unsupported/uncertain verification emits a visible diagnostic and forwards only that field to INFER; transport/domain failures remain failures rather than silent inference success.
- INFER receives only unresolved fields and their exact field definitions. A provider-neutral factory uses `structured_completion.complete_structured_json`, the shared bounded retry policy and domain validation. Provider request factories still own credentials, transport, cancellation and quotas; no new production provider adapter or assignment is registered. Prompt contract is `metadata-candidate-routing-v1`; source/candidate contents are explicitly inert data, and speaker/author/position-holder distinctions remain instructions.
- Typed proposal packets remain advisory and always require review. `no_supported_value` remains an evaluation result and does not become human-confirmed absence. Fan-in rechecks current dependencies, field/schema identity, evidence and ownership, rejects duplicates/missing field outputs, and preserves requested-field order. A separate preserved packet carries collector diagnostics and permits an all-owned graph to return an explicit empty terminal packet.
- Human-touched, human-confirmed/override/absent and selected deterministic/inherited fields are preserved without provider calls. Collection identity now also fingerprints `human_touched_fields`, so an ownership change invalidates in-flight tasks even without a RecordRevision change. Canonical records, assertions and review decisions are not mutated by this adapter. Trace tests verify that source/quote text and private provider errors stay out of operational traces.
- Refreshed master to `ad28261f` before implementation. Initial expanded validation: 253 focused tests passed; full backend Ruff, public catalog exporter `--check`, targeted mypy and full backend mypy (269 source files) passed. Later added graph-fallback, vocabulary and selected-assertion ownership cases are included in final focused validation below. Final validation and broader regression limitations are recorded below. Real-provider benchmarking, calibrated resolution, reviewer-quality improvement and production readiness remain unclaimed.

- Final focused validation: 260 passed, including 27 routing tests. Full backend Ruff, full mypy (269 source files), Python syntax and catalog exporter check passed. Added mypy/pytest-xdist only to this chat's scratch tooling directory; reused environments were not modified. No dead code was found in touched code; new files were formatted with Ruff and the progress document with the existing workspace Prettier.
- Full preflight was attempted with four workers and fail-fast regression. Backend lint, typechecking and syntax passed. The formatting gate cannot find this fresh clone's `web/node_modules`; the touched Markdown was separately formatted. Generated-artifact validation and backend regression are blocked by missing `chromadb`: fail-fast regression stops during collection of `test_audio_settings_and_topology.py`. Separate artifact tests report three GraphQL failures from that missing import and three passing catalog tests; schema staleness is not established by the failed import.
- An earlier non-fail-fast full regression attempt reported a failure and reached approximately 23% before it was interrupted in favor of the explicit fail-fast diagnosis. It did not produce a completed suite summary and cannot establish baseline failure equivalence. Full regression remains unresolved, not accepted as passing. The implementation checkpoint is `b14bde49`; the checkpoint push uses `DERRIDAI_SKIP_PREFLIGHT=1` after the manual checks and recorded preflight failure.
- The user superseded the prior usage stop condition and requested this checkpoint regardless of usage. Work ends at this coherent server-only routing checkpoint. Next: retrieval consolidation, calibrated policy and real-provider/reviewer-quality benchmark tuning, followed by an explicit production integration/reconciliation gate. No private benchmark case was selected, and no latency or reviewer-quality result is claimed.

## PR #520 CI repair (2026-10-04)

- Merged current master `ad28261f`, including the completed legacy-runtime retirement from PR #518, before revalidating this branch.
- Updated the researcher text-policy wiring guard to read the canonical `domain/appBootstrap.ts` and `domain/researcherInputFilter.ts` modules directly now that `runtime.js` has been retired. This removes the stale collection-time dependency on the deleted compatibility file without changing policy behavior.
- Restored the touched files' UTF-8 copyright marker after an earlier shell-encoding round trip. This is repository hygiene only; it does not alter candidate-routing semantics.

- Integrated concurrent remote commit `da71a8ad`, preserving its researcher text-policy wiring repair and UTF-8 copyright cleanup alongside the routing checkpoint. Resolved the append-only progress conflict by retaining both checkpoint sections. Post-integration validation: 261 focused tests passed, including the researcher text-policy repair; full backend Ruff and touched-test lint passed. Earlier full backend mypy remains applicable because the integrated Python changes only restore copyright text. Full preflight/regression limitations above remain unresolved.

- PR #520 merged the earlier observation checkpoint before this routing checkpoint was pushed. Refreshed and merged master `a6020e9c`, including metadata failure recovery and the next runtime-retirement step. Post-refresh validation: 277 focused tests passed (including failure recovery/provider health), full backend mypy passed for 272 files, and full backend Ruff passed. The follow-up diff remains limited to routing/collection context, routing tests and this progress document. Draft follow-up PR #524 tracks this unmerged routing checkpoint: https://github.com/ajschlosser/DerridAI/pull/524. Refreshed fail-fast preflight again passed backend lint/typechecking/syntax and remained blocked at the documented chromadb collection error and formatting/artifact gates.

## Exact-memory lookup consolidation checkpoint (2026-10-04)

- PR #524 is merged; continuation starts from master `8d572f7d` in an isolated worktree. Experimental routing remains server-only and unregistered. Adaptive production routing is still disabled.
- Historical task preparation now snapshots each exact adjudication key once per call. Keys retain field, cardinality and schema-version distinctions; Record identity and prompt text are fixed within the call. Cached misses avoid repeated reads, values are copied at acquisition and delivery, and subsequent preparation reads fresh memory. Prefill and advisory prompt consumers use the same snapshot without transferring historical evidence or authority.
- Existing lookup counters now measure actual storage reads; matching schema-version preparation drops from two reads per field to one, with zero duplicate reads. Distinct schema versions still require separate reads. No provider, end-to-end latency, calibrated resolution or reviewer-quality improvement is claimed.
- Baseline benchmark suite passed 3 tests before edits. Updated suite passed 4 tests, including prompt/prefill parity, miss caching, value isolation, fresh reads and version-key separation. Expanded validation: 241 passed, 1 failed in the concurrent JSONL write test with Windows access denial. Isolated reruns of that test passed on both merged baseline and this branch; the expanded run is not reported as green. Targeted Ruff and mypy passed. Broader checks and preflight are recorded below.
- No dead code was found in touched files. No unrelated bug fix or public API change is included.
- Next: integrate the candidate-routing adapter with explicit server-owned reviewer/semantic-support gates and consolidate remaining retrieval sources; select a researcher-approved private case/provider before real-provider benchmarking. Exact mention occurrence alone must not enable adaptive production routing.
