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

# Research Workspace UX Implementation Plan

**Scope:** Research (`/rag`), persisted Research threads and turns, Research Library entry points, evidence/claim inspection, and follow-up composition.  
**Status:** Phase 1 in progress on `task/research-workspace-ux`; source changes and focused tests are committed, CI/browser validation outstanding. Unchecked tasks are not implemented by virtue of appearing here.  
**Design input:** October 2026 Research / Research Threads UX assessment; treat illustrative mockups as proposals, not live screenshots.  
**Normative authority:** [cELF 1.0](../SPECIFICATION.md), [research requirements](requirements/RESEARCH_RETRIEVAL_AND_EVIDENCE.md), [architecture](ARCHITECTURE.md), [current user guide](USER_GUIDE.md), and [contributor instructions](../AGENTS.md).

## 1. Product objectives and boundaries

Make a single Research workspace in which a researcher can find an inquiry, read its ordered turns, compose a follow-up, inspect the exact evidence supporting a generated proposition, and open a run audit without losing the reading position.

1. **Thread navigation:** A persistent desktop navigation rail (collapsible), with a responsive drawer on narrow screens. A selected thread is always evident; `?thread=` and `?job=` remain deep-linkable.
2. **Conversation:** Consistent scholarly answer typography, citation resolution, failure and streamed-draft semantics, and per-turn controls. Do not render a second full answer when inspecting a citation.
3. **Inspection:** One contextual, accessible inspector for the selected turn and evidence/claim, with actions for source Record, relationships and audit. Source location, citation formatting, support binding and claim validation remain separate.
4. **Composition:** New inquiries and follow-ups use one composer with plainly visible effective scope/profile/retrieval/context; advanced controls are progressively disclosed rather than silently omitted.
5. **Lifecycle:** Distinguish queued, running, completed, failed, cancelled and missing-result turns. Keep retry and per-attempt auditing reliable.
6. **Responsive/a11y/i18n:** WCAG 2.2 AA; semantic keyboard navigation and focus recovery; English (en-US) and Canadian French (fr-CA) parity; light/dark/high-contrast and 200–400% zoom.

### Non-goals / invariants

- Do not change the cELF semantic object model, authoritative Record metadata, `FieldAssertion` authority, or run-specific provenance to serve cosmetic UI state.
- Do not treat prior LLM answers as evidentiary support for follow-ups. Conversation context assists interpretation; each ResearchRun supplies its own documentary evidence.
- Preserve owner isolation, archived/read-only behavior, tombstone semantics, one active turn per thread, exact attempt-linked answer recovery, and permissions.
- Never equate source located, citation resolved, support binding present, and claim validated. No synthetic confidence or fabricated progress.
- Retain existing generic UI components/tokens, typed APIs, real-time invalidation, and independent per-turn runs.

## 2. Verified baseline (2026-10-11, master)

<!-- prettier-ignore -->
| Surface | Current implementation | UX/engineering consequence |
| --- | --- | --- |
| Research page | `web/src/views/ResearchView.vue` orchestrates workspace, thread browser toggle, composer, active runs, drawers and standalone result | Concurrent top-level surfaces compete for attention; view owns too many concerns |
| Thread list/conversation | `ResearchThreadBrowser.vue` and `ResearchThreadNavigation.vue` use a nested two-column section with 50-item pages | Thread list looks like an optional embedded feature rather than navigation |
| Thread answers | `ResearchThreadAnswer.vue` first renders a plain `<p>` with marker replacement; `ResearchAnswerWorkspace.vue` has structured headings/lists/citations | Answer format varies between threaded and standalone research; audit repeats answer |
| Research evidence | `ResearchResultPresentation.vue` couples answer and `ResearchEvidencePanel.vue`; a thread nests this inside `details` | Citation inspection can require an additional, duplicated workspace |
| Composer | `ResearchComposer.vue` `compact` mode hides most scope/settings controls | Follow-up effective execution settings can be difficult to discover |
| Persistence | `api/app/research_thread_store.py`, `researchThreadsApi`, owner-scoped queries, immutable per-attempt result keys | Reuse existing contracts; no new thread storage needed for initial phases |

The original [Research Threads Implementation Plan](RESEARCH_THREADS_IMPLEMENTATION_PLAN.md) covers data and backend workflow. This plan is specifically a follow-on interaction/design migration. Verify the latest branch before each phase.

## 3. Target information architecture

Desktop wide: `ThreadRail | Conversation + ComposerDock | Inspector`. Initial sizing targets: rail 264–288px; readable central text measure ~65–80ch, inspector 320–380px; resize/collapse without horizontal overflow. The evidence inspector is not a second conversation.

At 900–1200px, preserve conversation width by moving inspector to a toggleable drawer. Below ~900px, make the thread rail a drawer, keep composer in flow or as a non-obscuring sticky dock, and open citation inspection as an accessible sheet/drawer. Breakpoints should be validated by available space, not screen-class assumptions.

A single `ResearchWorkspaceShell` coordinates navigation, conversation and inspection. Define stable selection context `{ threadId, turnId, attempt, jobId, evidenceId?, claimId? }` as **ephemeral UI state**: clear/rebind atomically on run changes, preserve only safe identifiers in shareable URLs, and never leak stale evidence across turns. Server remains authority for source/citation/support data.

### Intended component boundaries

<!-- prettier-ignore -->
| Component/composable | Responsibility | Migration |
| --- | --- | --- |
| `ResearchWorkspaceShell` | Responsive regions, keyboard landmarks, inspector visibility, focus return | Extract from `ResearchView` incrementally |
| `ResearchThreadList` | Search/list, selection, recent/pinned/archived, pagination/virtualization | Evolve `ResearchThreadNavigation` first; keep API |
| `ResearchConversation` | Ordered turn list, transition between turns, per-turn loading and status | Extract presentational code from thread navigation |
| `ResearchTurnCard` | Question, lifecycle, one consistent answer, action toolbar | Evolve `ResearchThreadAnswer` |
| `ResearchAnswerContent` | Shared escaped structured answer blocks and bound inline citations | Factor out of `ResearchAnswerWorkspace`; reuse for thread and standalone |
| `ResearchInspector` | Tabbed sources/claims/run details for the **active** run, no duplicated answer | Reuse existing evidence and claim components, separate display from selection |
| `ResearchComposerDock` | Primary question, visible effective settings/context, run action | Evolve `ResearchComposer`; retain API `runResearch` behavior |
| `useResearchWorkspaceSelection` | Selection and focus invariants, route hydration and keyboard return | Extract only once lifecycle is covered by tests |

Prefer an evolutionary extraction over a parallel implementation. The names are suggested boundaries, not an instruction to create inert wrapper components.

## 4. Phased execution, with reviewable commits

### Phase 0 — Baseline and tests

- [ ] Capture **actual** before screenshots at desktop (1440, 1280), tablet (~900), mobile (390, 320), and zoomed layouts from a locally running app (not illustrative mockups).
- [ ] Inventory current Storybook and Playwright scenarios for Research, thread management, evidence, citation links, streaming, retry and authorized-result recovery.
- [ ] Add focused characterization tests for answer markup, citation activation, thread change cleanup and evidence selection; ensure static-source locale checks are preserved.
- [ ] Record baseline performance for 1, 10 and 100 turns, and network requests on thread switch. Do not assert timings without measurements.

### Phase 1 — Answer parity and safe citation activation (P0, start here)

- [x] Extract a shared, escaped answer-body renderer from `ResearchAnswerWorkspace.vue` or adopt its existing `parseResearchAnswer` + `segmentResearchAnswer` logic in both contexts.
- [x] Render headings, ordered/unordered lists, paragraph emphasis and citations identically in thread/standalone results; treat unresolved markers as text, never false links.
- [x] Ensure both `[E1]` and `[[E1]]` markers and already-bound inline citations resolve correctly only against **this turn's** evidence packet; avoid brittle global regex replacement.
- [ ] Remove redundant second rendering of the answer in the expanded thread audit where possible; retain access to works cited, claim review, evidence and run details.
- [ ] Tests: multiple citations, different turn evidence with reused `E1`, unresolved/stale citations, HTML-like source content escaped, multi-paragraph/list answers, rerenders after attempt changes.

**Phase 1 exit:** A completed thread answer requires no expansion to obtain the same structured scholarly answer as a standalone run; every citation selects only its own turn's evidence.

### Phase 2 — Unified desktop workspace (P0)

- [ ] Bring thread navigation into persistent layout rather than the toggled section preceding composer/result. Preserve a genuinely useful new-question view and no-database state.
- [ ] Establish one reading column with ordered turns; distinguish question from answer through alignment, hierarchy and spacing, without nesting repetitive cards.
- [ ] Ensure `?thread` selection and browser Back/Forward stay consistent with internal selection; return focus to selected thread heading where appropriate.
- [ ] Integrate run status affordances without competing full-width run/activity panels.
- [ ] Tests: empty/new, selected/archived, 1 vs many turns, historical missing artifact, permissions and account change, deep links.

**Phase 2 exit:** Research navigation, reading, and composer feel like a single application surface at desktop widths.

### Phase 3 — Contextual evidence & claim inspector (P0)

- [ ] Create turn-scoped evidence selection; clicking a citation opens the matching EvidenceRef or explains why it cannot resolve.
- [ ] One inspector shows direct quote, work/edition, source locator precision, Record revision, speaker/position holder/stance/discourse role, claim bindings and validation status as **distinct** fields when known.
- [ ] Provide original Record, relationship trace and cELF model actions using existing navigation; distinguish no binding, unsupported, disputed, unresolved and validated.
- [ ] Supply inspector Sources / Claims / Run views; render clear states for missing sources and unavailable audit artifacts.
- [ ] Support Escape, focus return, tab order, and non-disruptive live-region status. Clear selection synchronously on turn/attempt change.
- [ ] Tests: same E marker in two turns, cross-thread navigation, revision mismatch, missing locator, multiple binding relations, keyboard/a11y.

**Phase 3 exit:** One citation interaction shows the right documentary passage; no nested second full workspace is required.

### Phase 4 — Thread/library navigation and composer (P1)

- [ ] Collapse competing history patterns into shared thread-list primitives while keeping Research Library accessible.
- [ ] Improve search/filters, active-run/error cues, stable URL restoration and progressive pagination. Add pinning only with an explicit owner-scoped API and migrations.
- [ ] Show effective corpus, provider/model, retrieval preset, selected evidence mode and prior-turn context summary in compact follow-ups; disclose full per-run settings on demand.
- [ ] Avoid implying that pinned workspace evidence is used in ordinary retrieval presets; show contextualization vs evidence selection separately.
- [ ] Ensure draft persistence and reset behavior remain predictable between new threads, existing threads, retries and reruns.
- [ ] Tests: composer settings on all states, long names, keyboard search, archived read-only, no-profile/no-corpus, no stale history after owner changes.

### Phase 5 — Advanced scholarly capabilities (P2; separate PRs)

- [ ] Search within a single thread across questions and available answers without fetching all audit payloads.
- [ ] Start a follow-up from selected answer/source passage with explicit, editable context scope.
- [ ] Compare two turns/runs and their bound evidence without flattening identity or validation status.
- [ ] Export conversation and bibliographic/audit references with deterministic citation construction and preserved run/record identities.
- [ ] Add optional thread pins/labels only if justified by observed library usage.

## 5. Accessibility, localization, design-system checks (all phases)

- WCAG 2.2 AA with Playwright/axe **plus** manual keyboard, screen-reader and zoom checks. Focus visible, not hidden beneath sticky composer; touch targets meet 2.5.8, aiming for 44px where practical.
- Use native semantics and existing `Ui*` wrappers for menus, dialogs, inputs, buttons; no custom inaccessible pseudo-selects. Source text must be escaped, not HTML injected.
- Dynamic results: announce completion once, do not repeatedly announce streaming text. Mark provisional draft as provisional.
- All new copy in en-US and fr-CA with exact key and interpolation parity. Verify light, dark, high-contrast and reduced motion.
- Align spacing, type, surfaces, focus outlines, borders with existing tokens and Storybook guidance; keep Research-specific CSS narrow.

## 6. Scholarly and security acceptance gates

1. `GeneratedClaim -> SupportBinding -> EvidenceRef -> RecordRevision -> SourceSpan -> SourceDocument` remains resolvable when the source supports it; visual citation alone cannot claim full traceability.
2. Show textual speaker vs proposition holder distinctly when available; no attribution reassignments from display conveniences.
3. No cross-turn evidence leak, no stale selected evidence after account/thread/attempt change, and no assumption that `record_id` is a storage ID.
4. Do not silently coerce unresolved, missing, invalid, confirmed-absent, and unreviewed states; never manufacture confidence or approval.
5. Preserve saved-run settings snapshot and evidence bindings; a retry is its own audit attempt, never an overwrite of prior scholarship.
6. Unauthorized or missing job results preserve shell/owner rules without showing cached private answer bodies.
7. Initial screen and long-thread interaction must remain responsive; virtualize or defer expensive detail, not authoritative identities.

## 7. Verification commands and release discipline

Run as appropriate after every phase:

```bash
cd web
npm run format:repo:check
npm run typecheck:app
npm run typecheck:tests
npm run test:unit -- --run tests/frontend/research-threads.test.ts
npm run test:e2e -- tests/e2e/research-threads.spec.ts
npm run build-storybook
```

Also run other relevant Research/citation/claim/e2e tests, `npm run lint`, full `npm run test:unit`, `npm run test:e2e:a11y` and a production build before declaring the feature complete. CI and local screenshots are required to confirm; passing tests alone are not proof of full WCAG conformance.

Update `docs/USER_GUIDE.md` **when behavior ships**, and `docs/ARCHITECTURE.md` if component/domain boundaries materially change. Add Storybook stories and tests with the same changes as their UI components. Preserve existing test expectations unless the intentional new behavior is documented. Avoid changing backend API contracts or generated client bundles without a separate need.

## 8. Delivery checkpoints

- **Checkpoint A:** plan and Phase 1 focused implementation/tests on a dedicated branch; PR explicitly lists remaining P0 work.
- **Checkpoint B:** Phase 2 navigation/conversation layout; screenshot review and cross-breakpoint/a11y validation.
- **Checkpoint C:** Phase 3 inspector and citation evidence binding; provenance tests.
- **Checkpoint D:** Phase 4 library/composer usability and performance.
- **Checkpoint E:** independently scoped Phase 5 features.

No phase is complete without its implementation, tests, documentation when applicable, and visual/keyboard review. Do not describe a draft plan or illustrative mockups as actual deployed features.
