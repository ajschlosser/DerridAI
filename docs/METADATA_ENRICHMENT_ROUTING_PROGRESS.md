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

This is the authoritative resume point for the revised Pipeline Studio candidate-routing implementation plan. Production enrichment remains on its historical adapter. Adaptive routing is not enabled; no latency improvement is claimed.

## Checkpoints

| Step                                                    | Status   | Evidence                                                                                                                  |
| ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| Generic named-port execution foundation                 | Complete | `0eee61b7`, `d2e52720`; repeated stages, branching, fan-in, fallbacks, empty-branch skips, safe telemetry                 |
| Typed metadata artifacts and computational traits       | Complete | Explicit candidate/hypothesis/inference-request/proposal/embedding types; required/produced port traits; run-input traits |
| Consumer terminal guarantees                            | Complete | Compile-time type/trait checks; run-time terminal-output enforcement; `any` cannot satisfy a concrete final contract      |
| Historical enrichment migration to generic executor     | Pending  | Fake-provider `@1`/`@2` characterization exists; production session migration and full domain parity remain               |
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

## Validation

- 93 focused backend tests passed: graph execution, wiring/analysis, contracts, workflow semantics, and catalog fixture.
- Ruff passed for changed Python files; targeted mypy passed for the five changed pipeline modules.
- 47 focused frontend tests passed across workflow semantics, overrides, graph domain, and graph component suites. Frontend application/test typechecks and targeted ESLint passed. Prettier checked changed frontend/docs files.
- Catalog exporter `--check` passed; regeneration was unnecessary because legacy serialized contracts are unchanged.
- Full preflight and full API regression remain unverified in this fresh environment; required API dependencies are missing. Real-provider latency and reviewer-quality benchmarks have not run.

## Integration

PR #508 merged into master at `51b481cf`; that master was merged into this branch before the trait changes. Its Research configuration override contracts are retained. No Research settings or authority behavior was changed by this work.

## Next action

Migrate historical metadata enrichment sessions to the generic executor using the existing schema-derived task and provider invoker. Preserve attempt budgets, failure classification, cancellation, call-local stage identity, ledger linkage, and concurrent-session trace aggregation. Validate full enrichment/evidence/reconciliation parity before changing production assignments. Then add safe concurrency declarations and the candidate collection artifact; keep the router observe-only until support and authority invariants pass.
