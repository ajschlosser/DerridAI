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

# Code readability

DerridAI treats human readability as a correctness and maintainability requirement. The codebase contains provenance-sensitive research logic, asynchronous UI coordination, compatibility layers, and rebuildable projections; a locally clever implementation that obscures those boundaries is harder to review safely.

Use this guide together with [CONTRIBUTING.md](../CONTRIBUTING.md), [AGENTS.md](../AGENTS.md), and [ARCHITECTURE.md](ARCHITECTURE.md). Local READMEs are authoritative for where new code belongs inside a subsystem.

## Naming

- Prefer names that identify the domain role, not the data type. Use `recordRevision`, `candidateSeam`, `sourceBlock`, `normalizedQuery`, and `reviewQueue` rather than `item`, `data`, `obj`, `x`, or `tmp` when the scope is more than a few obvious lines.
- One-letter names are appropriate only for conventional mathematical coordinates or very small comprehensions where the meaning is immediate. Graph/layout code should still name forces, distances, centers, and indices when several quantities coexist.
- Boolean names should read as predicates: `isCurrent`, `hasEvidence`, `needsReview`, `canPublish`.
- Collection names should be plural; maps and indexes should say what they index, for example `recordsByWork` or `blockIndexById`.
- Do not preserve a vague name merely because it came from the legacy runtime. Compatibility boundaries may keep public API names, but local variables and extracted helpers should be made descriptive.

## Functions and classes

- A function should have one intelligible responsibility. If understanding it requires holding several independent state machines in mind, extract named helpers along those seams.
- Prefer early returns for invalid, empty, or already-complete cases. Avoid adding another level of nesting around the main path.
- Name helpers after the decision they make or transformation they perform. `_best_record_sizing_boundary` is more useful than `_process`; `resolveSearchFilterFields` is more useful than `getFields`.
- Keep transport, persistence, domain rules, and presentation separate. A route/view may coordinate work, but domain decisions should live in the corresponding service/domain layer.
- Avoid wrappers that merely rename an existing call without clarifying ownership, invariants, or a stable interface.

## Comments and documentation

Comments should explain **why**, invariants, authority boundaries, non-obvious performance constraints, or failure semantics. Do not narrate syntax that is already clear from the code.

For Python:

- Use module docstrings for the module's responsibility and important architectural constraints.
- Use docstrings on public functions/classes and on private helpers whose contract or rationale is not obvious from the signature.
- Use inline comments immediately before the non-obvious branch or loop they explain.
- Keep provenance, review authority, revision identity, and stale-state behavior explicit when those rules constrain an algorithm.

For TypeScript/Vue:

- Use TSDoc/JSDoc comments for exported utilities, reusable types, and complex composables when the contract is not self-evident.
- Keep Vue templates focused on rendering and interaction. Explain asynchronous reconciliation, stale-response rejection, focus management, or compatibility behavior in the script/composable that owns it.
- Prefer named computed values and helpers over dense template expressions or nested ternaries.

## Complex logic

When a block contains nested loops, retries, optimistic concurrency, asynchronous races, ranking, graph layout, or provenance checks, make the phases visible in the code. A useful pattern is:

1. normalize/validate inputs;
2. build the candidate set or snapshot;
3. apply the deterministic rule;
4. reconcile/commit;
5. report or project the result.

Use comments at phase boundaries when the reason for the order matters. For example, if a lock is deliberately released before expensive validation, or an LLM may only choose among deterministic candidates, say so beside that logic.

## Readability without semantic drift

Readability refactors are behavior-preserving unless the change explicitly includes a bug fix. In provenance-sensitive areas, prefer small reviewed transformations over repository-wide rewrites.

- Do not replace exact source/revision/evidence identifiers with derived labels for convenience.
- Do not collapse canonical and derived state into one abstraction.
- Do not simplify review/authority logic by treating model suggestions as accepted values.
- Do not remove defensive stale-response, cancellation, or conflict checks because the happy path becomes shorter.
- Do not regenerate characterization snapshots simply because a refactor changed markup; verify whether behavior changed intentionally.

## Known traps

- `api/app/corpus_builder.py`, `api/app/chroma_store.py`, and several compatibility/frontend surfaces are still large. Add new logic to an established focused module when one exists; decompose large files only along tested domain seams.
- `web/src/runtime/registrations.js` and `domain/appBootstrap.ts` are the compatibility boundary, not the preferred home for new frontend behavior.
- Chroma collections, embeddings, Document Intelligence output, semantic-content projections, and caches are rebuildable projections. Reviewed Records, revisions, assertions, decisions, evidence, and publication state are not.
- `FieldAssertion` and related provenance structures carry authority that ordinary dictionary fields do not. Do not replace them with hard-coded field-specific shortcuts.
- GraphQL is read-only. REST owns commands/mutations; WebSocket messages are invalidation/progress signals, not canonical state.
- Frontend optimistic state must reconcile with the server. Do not make browser state authoritative for scholarly data.
- Source media are heterogeneous. Avoid PDF/page terminology in media-neutral code unless a path is genuinely PDF-specific.
- Generated files and build outputs should be changed through their generator, not hand-edited. See CONTRIBUTING for the current generated-artifact list.
- Legacy DOM snapshots are characterization artifacts. Do not run Prettier over them or update them to hide an unexplained difference.

## Readability review checklist

Before handing off a change, ask:

- Can a new contributor tell what each function/class/component owns from its name and local documentation?
- Are short variable names limited to truly local/conventional uses?
- Does nested logic expose its phases and invariants?
- Are comments explaining reasons rather than repeating code?
- Can a pure algorithm be read without knowing the transport or UI framework?
- Did the refactor preserve provenance, authority, cancellation, conflict, and stale-state safeguards?
- Is there a local README that tells the next contributor where adjacent work belongs?
- Did you run the smallest relevant formatting, lint, type, and regression checks described in CONTRIBUTING?

## Where to improve next

`docs/STATIC_ANALYSIS_FOLLOWUPS.md` tracks remaining deliberate formatting/static-analysis debt. Readability work should retire those entries module by module when the underlying debt is actually removed rather than broadening suppressions.
