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
**Status:** Phases 0–5 are implemented and merged (PRs #605–#613 and the Phase 0 baseline in §14). Only manual screen-reader, keyboard, zoom and reduced-motion review remains (see §13). Phases 1–2 merged into `master` in PR #605; the final quality-gate run passed. Phase 3 merged in PR #606 with a passing quality gate; manual visual/screen-reader review and full cELF chain display remain pending.
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

- [x] Capture **actual** before screenshots at desktop (1440, 1280), tablet (~900), mobile (390, 320), and zoomed layouts from a locally running app (not illustrative mockups).
- [x] Inventory current Storybook and Playwright scenarios for Research, thread management, evidence, citation links, streaming, retry and authorized-result recovery.
- [x] Add focused characterization tests for answer markup, citation activation, thread change cleanup and evidence selection; ensure static-source locale checks are preserved.
- [x] Record baseline performance for 1, 10 and 100 turns, and network requests on thread switch. Do not assert timings without measurements.

### Phase 1 — Answer parity and safe citation activation (P0, start here)

- [x] Extract a shared, escaped answer-body renderer from `ResearchAnswerWorkspace.vue` or adopt its existing `parseResearchAnswer` + `segmentResearchAnswer` logic in both contexts.
- [x] Render headings, ordered/unordered lists, paragraph emphasis and citations identically in thread/standalone results; treat unresolved markers as text, never false links.
- [x] Ensure both `[E1]` and `[[E1]]` markers and already-bound inline citations resolve correctly only against **this turn's** evidence packet; avoid brittle global regex replacement.
- [x] Remove redundant second rendering of the answer in the expanded thread audit where possible; retain access to works cited, claim review, evidence and run details.
- [x] Tests: multiple citations, different turn evidence with reused `E1`, unresolved/stale citations, HTML-like source content escaped, multi-paragraph/list answers, rerenders after attempt changes.

**Phase 1 exit:** A completed thread answer requires no expansion to obtain the same structured scholarly answer as a standalone run; every citation selects only its own turn's evidence.

### Phase 2 — Unified desktop workspace (P0)

- [x] Bring thread navigation into persistent layout rather than the toggled section preceding composer/result. Preserve the new-question view and no-database state.
- [x] Establish one reading column with ordered turns and a composer in the same layout. Deeper visual refinement of the existing turn cards remains outstanding.
- [x] Ensure `?thread` selection and browser Back/Forward stay consistent with internal selection; return focus to selected thread heading where appropriate.
- [x] Integrate run status affordances without competing full-width run/activity panels.
- [x] Tests: empty/new, selected/archived, 1 vs many turns, historical missing artifact, permissions and account change, deep links.

**Phase 2 exit:** Research navigation, reading, and composer feel like a single application surface at desktop widths.

### Phase 3 — Contextual evidence & claim inspector (P0)

- [x] Create turn-scoped evidence selection; resolved citations open only their run's EvidenceRef; unresolved citations remain visibly unlinked.
- [x] One inspector shows direct quote, work/edition, source locator precision, Record revision, speaker/position holder/stance/discourse role, claim bindings and validation status as **distinct** fields when known.
- [x] Provide original Record, relationship trace and cELF model actions using existing navigation; distinguish no binding, unsupported, disputed, unresolved and validated.
- [x] Supply one turn-scoped Sources / Claims / Run inspector, with explicit empty-source/claim states and no duplicate answer.
- [x] Support Escape, focus return, keyboard-operable section buttons, and turn/job/attempt selection reset. Existing evidence panel provides a live region; manual screen-reader review remains outstanding.
- [x] Tests: same E marker in two turns, retry attempt resets the inspector, empty evidence/claim states, revision mismatch, missing locator, multiple binding relations, and cross-thread navigation e2e. Manual keyboard/screen-reader review remains (§13).

**Phase 3 exit:** One citation interaction shows the right documentary passage; no nested second full workspace is required.

### Phase 4 — Thread/library navigation and composer (P1)

- [x] Collapse competing history patterns into shared thread-list primitives while keeping Research Library accessible.
- [x] Improve search/filters, active-run/error cues, stable URL restoration and progressive pagination. Add pinning only with an explicit owner-scoped API and migrations.
- [x] Show effective corpus, provider/model, retrieval preset, selected evidence mode and prior-turn context summary in compact follow-ups; disclose full per-run settings on demand.
- [x] Avoid implying that pinned workspace evidence is used in ordinary retrieval presets; show contextualization vs evidence selection separately.
- [x] Ensure draft persistence and reset behavior remain predictable between new threads, existing threads, retries and reruns.
- [x] Tests: composer settings on all states, long names, keyboard search, archived read-only, no-profile/no-corpus, no stale history after owner changes.

### Phase 5 — Advanced scholarly capabilities (P2; separate PRs)

- [x] Search within a single thread across questions and available answers without fetching all audit payloads.
- [x] Start a follow-up from selected answer/source passage with explicit, editable context scope.
- [x] Compare two turns/runs and their bound evidence without flattening identity or validation status.
- [x] Export conversation and bibliographic/audit references with deterministic citation construction and preserved run/record identities.
- [x] Add optional thread pins (owner-scoped API + migration). Labels were not added: no observed library usage justifies a second taxonomy.

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

## 9. Phase 3 stopping point / handoff (2026-10-12)

**Repository state:** PR #605 has been merged into `master`. PR #606 targets current `master` from `task/research-turn-inspector`. The former implementation branch was not reused as the merge target; its Phase 3 file edits were transferred to the new branch. Do **not** interpret PR #606 as complete or merge-ready yet.

### Implemented and committed in PR #606

- `ResearchTurnInspector.vue` provides one contextual Sources / Claims / Run surface, reusing `ResearchEvidencePanel` and `ResearchClaimReviewPanel` instead of duplicating `ResearchAnswerWorkspace`.
- `ResearchThreadAnswer.vue` now opens the inspector from a resolvable citation or its inspection button; it passes the turn's own result packet, supports Escape and explicit close, and restores the prior focus target on deliberate dismissal.
- `ResearchThreadBrowser.vue` owns a single expanded inspector turn and clears selection synchronously on thread/job/account/permission changes. The cited evidence index stays local to the turn.
- Existing thread unit and Playwright cases were adapted to verify nonduplicated answer content, inspector switching, run/claim sections, evidence attribution and keyboard use.
- `docs/ARCHITECTURE.md` and `docs/USER_GUIDE.md` describe the changed interaction and authorization boundaries.

### CI and verification at handoff

- Initial Phase 3 CI build, lint and Storybook jobs passed. Formatting failed in three Vue files, and one test asserted the old nested result presentation.
- The obsolete unit-test expectation was corrected. The exact Prettier diagnostic diff was applied to all three files.
- A **temporary formatting diagnostic workflow was removed** from the branch after use; it is not intended to ship.
- **The latest normal PR quality-gate run was still in progress at the handoff.** Its completion, end-to-end results and accessibility verdict must be checked on PR #606 before requesting review.
- No genuine browser screenshot review or manual screen-reader, keyboard/zoom sweep has been completed for this Phase 3 branch.

### Open work required before Phase 3 acceptance

1. Examine final CI failures and correct them without loosening substantive provenance or accessibility assertions. Run both E2E shards after fixes.
2. Verify that a citation referring to evidence `E1` in two different turns never opens the wrong turn's passage, including saved-result recovery and retry/attempt switches.
3. Verify the inspector's claim-validation states and source-binding relations against authoritative per-run data; currently the existing claim/evidence panels are reused, **not** expanded to a full cELF source-span/record-revision chain.
4. Verify absent evidence, absent claim provenance, missing locator, rejected/unresolved/stale support, long citations, and mobile sheet focus/scroll behavior.
5. Add Storybook stories and actual captured desktop/mobile screenshots; perform manual WCAG 2.2 AA keyboard, focus return, screen-reader, 200–400% zoom and reduced-motion review.
6. Validate locale parity for new labels and confirm visible text refers to known source metadata rather than inferred fields. The implementation uses existing translation keys.

**Stopping rule:** Leave PR #606 as draft and do not mark the Phase 3 acceptance checklist complete until CI, visual/a11y, metadata and provenance checks above are verified. Phase 4/5 work has not begun on this branch.

### Follow-up after merge (2026-10-12)

- PR #606 merged with all quality-gate jobs (both E2E shards and a11y) passing.
- Retry fix: when a retry gives the inspected turn a new attempt/job, `ResearchThreadBrowser` now closes the inspector instead of carrying it onto the new attempt's evidence.
- Unit tests now cover a reused `E1` marker in two turns, closing on a retry attempt, and explicit empty Sources/Claims states. Added the `Research/Turn Inspector` Storybook story.
- `ResearchEvidenceProvenance.vue` (in the Sources section) shows, for the selected EvidenceRef only: work/edition/translator when recorded, a medium-appropriate locator (printed vs PDF pages, or audio time) or an explicit "not recorded", the Record revision, and the support bindings for that evidence marker with relation, binding status and claim status as separate fields plus a revision-mismatch warning. Bindings fall back to record identity only when no marker is recorded. New en-US/fr-CA keys: `research.provenance_*`, `claims.binding_status_*`.
- Still open: SourceSpan/SourceDocument identifiers are not displayed (the evidence payload does not carry span IDs); captured screenshots; manual screen-reader, keyboard and 200–400% zoom review; cross-thread navigation e2e. Phase 4 has not started.

## 10. Phase 4 progress

- Follow-up composer (`ResearchComposer` `compact` mode) now shows an effective-settings summary: corpus, profile/model, retrieval preset, scope filter when set, evidence mode, and a statement that prior turns are context rather than evidence. Selected passages are reported as used only for the `evidence` and `hybrid` presets. **Show all run settings** discloses the full fieldset on demand.
- Drafts are scoped: the new-question view keeps `research-composer-draft` and each thread keeps `research-composer-draft:thread:<id>` in the per-account workspace store. A switch writes the pending draft to the scope it was typed in before loading the next; a successful new question or follow-up clears its scope; a retry leaves the draft alone.
- Thread list: debounced search (250 ms, clearing applies at once), Escape clears an active search, a no-match state names the query, and Research `/rag` now keeps `thread_q`/`thread_offset`/`thread_archived` in the URL like the Research Library, preserved across thread selection, new question and run navigation.
- History patterns: the Research Library and Research already share `ResearchThreadBrowser`/`ResearchThreadNavigation`. The composer's **Recent questions** menu reuses prompt text rather than navigating inquiries, so it stays.
- Test matrix covered by unit tests: composer summary with and without profile/corpus, keyboard search, debounced paging reset, URL filter restoration, per-thread drafts. Existing tests already cover archived read-only follow-ups and owner changes. Long titles wrap (`overflow-wrap: anywhere`).
- Not done: pinning, which needs an owner-scoped API and migration first (the plan says to add it only then); manual a11y and screenshot review.

## 11. Phase 2 follow-up

- Thread selection is derived from `?thread`, so Back/Forward and in-app selection share one source of truth. When a different thread loads and focus is on the page body (Back/Forward) or in the thread list, `ResearchThreadNavigation` moves focus to the conversation heading; focus elsewhere, such as the composer, is not taken. Covered by a unit test.
- In a thread, the active-pipelines bar collapses to one line counting only runs outside that thread (its own turns already show status) and opens **All runs**; outside a thread it keeps the chip list.
- Still open in Phase 2: the remaining test matrix (permissions/account change and deep links are covered; historical missing artifact and archived states in e2e).
- Thread list API returns `has_more` (the route reads one row past the page), so **Next** is disabled on an exactly full last page.

## 12. Phase 5 progress

- **Search this thread** (threads with more than one turn) filters turns by question, instructions and answers already loaded in this browser. It never requests answers or audit payloads; a status line says how many matched and how many answers were not loaded, so only their questions were searched. Escape clears it, and it resets on thread change.
- **Follow up on this turn** (completed turns) and **Follow up on this passage** (inspector Sources) set an explicit context scope shown in the follow-up composer, where each turn can be removed or the scope reset to automatic. A passage follow-up prefills an empty question with the run's own deterministic inline citation, as editable text. Only turn IDs travel (`context_turn_ids`); the scope applies to one follow-up and is kept on retry. The passage is not added to selected evidence: the new run retrieves its own evidence.
- **Compare turns** (threads with two or more completed turns) opens `ResearchTurnComparison`: two turn pickers, each side's run ID, provider/model, claim validation counts as recorded and read-only answer, and a cited-passages table that aligns EvidenceRefs by collection + Record ID. Each side keeps its own marker, citation and revision; a shared Record at a different or unrecorded revision is flagged, and evidence without a Record ID is never matched. Both sides load through `useResearchTurnResult`, now shared with `ResearchThreadAnswer`.

- **Export** (Manage thread): `GET /api/research/threads/{id}/export` (owner-scoped, `rag.run`) builds `derridai-research-thread-export-v1` server-side from each completed turn's authorized result: question, instructions, answer, turn/attempt/run/job IDs, provider/model, and for each cited EvidenceRef (from the raw answer's markers; all EvidenceRefs when no raw answer is recorded) its marker, collection, Record ID, revision, locator fields and the run's recorded inline/full citation, plus a deduplicated works-cited list. Passage text is never exported, so Researcher exports carry no corpus text. Turns without an available answer stay listed as unavailable. The client offers JSON (verbatim) and a localized Markdown rendering.

## 13. Remaining work (as of 2026-10-12)

- **Thread pins**: `research_threads.pinned_at` is added by an idempotent column migration; `PATCH /api/research/threads/{id}` accepts `pinned`, scoped to the owner (non-owners get 404). The list orders pinned threads first (most recently pinned first), then by activity; pinning does not change `updated_at`. **Pin thread** in Manage thread is an `aria-pressed` toggle and pinned rows show **Pinned**. Labels were deliberately not added.
- **Verification debt across phases:** Storybook captures of the turn inspector, comparison, thread navigation and follow-up composer were reviewed at 1440×900 and 390×844 in light and dark (no horizontal page overflow). That review fixed the comparison's unstyled run metadata and its cited-passages table splitting citations per character on mobile; the table now wraps at words and scrolls in a labelled, focusable region. Still missing: screenshots of the full running app; no manual screen-reader, keyboard, 200–400% zoom or reduced-motion review (these need a person at a real browser and screen reader). Done since: `Research/Turn Comparison` story (seeds the per-turn query cache), and a Playwright case covering cross-thread navigation with an open inspector, an archived thread (no follow-up, export still available) and a historical turn whose run and saved answer are both gone.
- Source identity: the inspector's provenance section now shows the Record's `source_document_id` and its source unit IDs (deduplicated from `source_spans[].source_unit_id` and `source_unit_ids`) when the run's evidence record carries them, and omits the rows otherwise. Thread export references include `source_document_id`. Spans have no stable span ID of their own, so none is shown.
- `tests/frontend/sidebar-navigator.test.ts` failed locally because its spy was on `Storage.prototype.setItem`, which some happy-dom builds bypass (`localStorage` has its own `setItem`); the test now spies on the instance. Not a product bug.

## 14. Phase 0 baseline (recorded after the fact, 2026-10-12)

Phase 0 was not done before implementation; this records the same measurements against current `master`, so it is a baseline for future work, not a before/after comparison.

- **Screenshots:** the production build against the e2e mock backend, with a 10-turn thread open, at 1440, 1280, 900, 390 and 320px in light and dark. (A CSS-`zoom` capture was discarded: it does not trigger responsive breakpoints the way browser zoom does, so zoom review stays manual.) These are review aids and are not committed. At 320px, **Inspect this answer and its evidence** did not wrap and scrolled the page 15px sideways; it now wraps, and the inspector e2e asserts no horizontal overflow at 320px. No other width overflowed.
- **Contrast:** the selected thread row's metadata used `--text-tertiary` on the dark `--soft` background (4.06:1), which failed the existing "active thread previews" axe test on `master`. Selected rows now use `--text-secondary`.
- **Scenario inventory:** Playwright `research-threads.spec.ts` covers URL state and guarded follow-ups, thread management, retry, active previews in both themes, per-turn inspection with saved-answer recovery, first question, follow-up, Library import, and cross-thread/archived/missing-artifact navigation; `research-progressive-loading.spec.ts` and `research-filter-editor-a11y.spec.ts` cover loading and filters. Storybook has `Research/Turn Inspector` and `Research/Turn Comparison`. Answer markup and citation activation are characterized in `research-answer-content.test.ts` and `research-answer-formatting.test.ts`, which now include several citations (resolved, repeated and unresolved) in one paragraph.
- **Performance (one local run, Chromium, mock backend; not asserted):** opening a thread with 10 or 100 turns rendered all turns and reached network idle in about 70–160 ms with 5 API requests, of which **one** was a job result, so turn results load lazily rather than once per turn. The 1-turn figure (~3.9 s, 8 requests) includes cold application start-up and is not comparable.
