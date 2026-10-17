<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Corpus Builder UX implementation plan

Started: 2026-10-15. Implementation and bounded integration audit completed: 2026-10-16. Status: implemented and locally validated with documented limits; draft PR publication authorized. No release performed.
Inspected baseline: `399e250f2`, version 0.62.19. Recheck HEAD and local changes before starting.

## Objective and approved direction

Redesign three related surfaces: source/setup with build switching, running-build overview, and record review. Make the next research action prominent, keep source text central, and move operational detail behind deliberate disclosure. The user requested this plan after reviewing generated screenshot concepts. This document is the implementation contract; generated text, counts, inferred capabilities, and source passages in those concepts are illustrative, not authoritative.

Reference images are stored beside this document in `design/corpus-builder-ux/`:

- `review-workspace.png`: compact build status above queue, source text, and decisions.
- `build-issues.png`: grouped issues in a secondary details surface.
- `build-overview.png`: ready-record action, separate record counts and task progress.
- `source-setup.png`: separate new-build setup and existing-build navigation.

Do not copy invented model identifiers, quotations, timestamps, bibliographic facts, page labels, or counts into production. Do not reproduce mockup inconsistencies: the issues drawer must not show published items under an Active-only filter; avoid duplicate retry buttons. “Changes saved” must reflect actual persistence, not optimism.

## Start here: current implementation and ownership

The supplied screenshots differ from this checkout. In particular this checkout's source setup still has a PDF select/upload workflow. Find the actual renderer and compare the running app before changing anything; do not assume a screenshot proves a feature exists in this branch.

| File | Verified role / work destination |
| --- | --- |
| `web/src/components/PdfCorpusBuilder.vue` | Main orchestration, setup, current build, warnings, review layout, navigation and mutations. Inspect targeted ranges, not the whole file. |
| `web/src/views/CorpusView.vue` | Thin `RuntimeSurface` wrapper, not the full builder implementation. Trace mounting before editing runtime. |
| `web/src/views/PdfWorkspaceView.vue` | Inspect workspace integration and tab ownership. |
| `web/src/composables/useCorpusBuildLifecycle.ts` | Review availability, locks, finish/configuration visibility, resumability and retry permissions. Preserve these contracts. |
| `web/src/api/pdfCorpus.ts` | `CorpusBuild`, queue counts, task counters, API methods and server readiness. |
| `CorpusMetadataLiveStatus.vue` | Task totals, completed/failed/skipped, active tasks, settle/cancel actions; currently contains estimated fallback totals and truthy fallbacks. |
| `CorpusBuildHistoryMenu.vue` | Existing build selection/refresh events and popover; evolve to an accessible side panel. |
| `CorpusBuildLifecycleCard.vue`, `CorpusWorkflowStepper.vue`, `CorpusBuildProgress.vue`, `CorpusBuildStageNotice.vue` | Existing overlapping progress/stage presentations; consolidate at presentation boundaries. |
| `CorpusBuildReadiness.vue`, `CorpusSourceSummary.vue`, `CorpusSourceIssuePanel.vue` | Setup/readiness/source facts; reuse where appropriate. |
| `CorpusReviewSessionBar.vue`, `CorpusReviewQueueTabs.vue`, `CorpusMetadataIssues.vue`, `CorpusMetadataFieldEditor.vue`, `CorpusFieldOwnershipBadge.vue` | Review and provenance affordances to preserve. |
| `CorpusExecutionSettings.vue`, `CorpusLlmEffectivenessPanel.vue`, `CorpusTextCleanupSummary.vue`, `CorpusBuildTimeline.vue` | Secondary operational detail; relocate without removing capabilities. |
| `api/app/locales/en_us.py`, `api/app/locales/fr_ca.py`, `web/src/stores/i18n.ts` | Current translation dictionary pipeline. Add matching keys/placeholders in both locales. |

Component names without a directory above are under `web/src/components/`; existing `.stories.ts` siblings are available for most components.

Before work: inspect `git status`, applicable AGENTS instructions, and current code. Untracked `.metadata-routing-work/`, `.research-filters-work/`, and `.research-thread-work/` existed at intake: leave them alone. No subagents unless asked. Keep this document current at each checkpoint. Follow current commit/push authorization; do not stage unrelated files.

## Non-negotiable behavior

- Presentation redesign first. No extraction, segmentation, enrichment/provider, publication, schema, or persisted-data semantic changes in this workstream.
- Source text, source locations, logical IDs, revisions, attribution distinctions, human decisions and evidence remain intact. Display physical and printed pages distinctly; never infer equivalence.
- Server authorization, review locks, structural locks, expected-revision checks, acceptance blockers and publication readiness remain authoritative.
- Review during enrichment is available only when existing lifecycle rules permit it. Do not unlock structural mutations while work runs.
- Existing settle-with-unresolved, cancel, resume, bulk review, source/evidence comparison, text editing and manual metadata decisions remain reachable with their current semantics.
- Existing retry permission currently requires a non-running, unpublished build and retryable fields. The generated running-build retry button does not authorize bypassing that guard. Disable with a reason, or omit until eligible.
- Dismissing/acknowledging a warning only changes its visibility under existing semantics; it does not resolve metadata or unblock publication.
- Sparse patches remain sparse. Never send entire records or histories merely to implement navigation or display changes.

## State and count contract

Create one small typed, pure presentation derivation, preferably alongside the existing lifecycle composable/domain logic. All three surfaces consume it rather than independently recomputing counts.

| Display | Authority and rules |
| --- | --- |
| Record total / accepted / rejected | `record_count`, `accepted_count`, `rejected_count`; label accepted separately from reviewed. |
| Queue filters | `review_queue_counts` and existing lifecycle derivations. Inspect server meanings before defining exclusive tiles. `issues`, `metadata`, `source`, and `topology` may overlap. Never sum overlapping queues. |
| Record status tiles | Use only verified mutually exclusive categories. If no partition exists, present independent explicitly scoped filter counts; do not force their sum to equal total or invent “enriching records” from running tasks. |
| Task progress | `metadata_tasks_total`, completed, failed, skipped, running and queued. Verify whether attempts/retries are cumulative before summing settled counts. Failed/skipped are not successful completion. |
| Missing task total | Show known counts and indeterminate progress. Do not invent `record_count * 3`. Explicit zero is not missing; use nullish handling after validation. |
| Inconsistent counters | Preserve raw diagnostics in details; show “Updating task counts”/indeterminate status rather than a contradictory fraction, fabricated denominator or successful 100%. Bound ARIA values only when determinate values are valid. |
| Warnings | Number of warning entries, distinct from tasks, affected fields, or distinct records. Never equate 100 warnings with 100 failed tasks. |
| Decisions remaining | Name scope explicitly: “1 required decision for this record” versus build-wide unresolved fields/records. Use server decision results. |
| Checkpoint | Only label saved if the payload provides actual checkpoint evidence. `metadata_last_progress_at` alone must not be relabeled as durable checkpoint confirmation without verifying its contract. |

If current API data cannot express an intended status truthfully, use a simpler truthful UI and record the gap here. Backend changes require a separately described increment, behavior tests and contract review; do not silently enlarge this redesign.

## Surface specifications

### 1. Source/setup and build navigation

Use explicit page modes: new-build draft, existing-build overview, record review, finish/publication. Selecting an existing build opens its mode; configuring another build opens a separate draft. Existing settings are immutable snapshots, not a form that appears to edit a running build.

New setup: heading “New corpus build”; concise source selection, structure, metadata and start steps. Put supported source acquisition paths behind Your sources / Upload / Web & libraries tabs only when those paths actually exist. Preserve current PDF-only capability in this checkout unless another verified integration owns additional types. No nonfunctional search-library or author-import controls.

After selection, emphasize source title/author/language and known units/page mapping. Hide hashes, IDs and diagnostics in Source details. Retain filenames as a secondary fallback and provenance detail; use authoritative title when available. Continue to structure is the clear next action, subject to existing readiness gates.

Replace the crowded history popover with one bounded, opaque panel. Use existing select/refresh contracts; show localized status, record count and date, with IDs in details. Active and All filters operate on actual statuses; handle loading, empty, failure/retry, pagination and unknown titles. Never claim all builds are listed if only a page is loaded. Keep published build download/access intact.

Do not duplicate global navigation or rebuild the app shell for this task. Preserve setup draft when inspecting another build, and restore it when returning. `startNewBuildSetup` currently stops polling and clears selection; `chooseBuild` resets selected record/queue. Introduce an explicit transient draft/return state if necessary, preserving provider/source/schema choices. Viewing background activity must not accidentally cancel work or stop monitoring all active builds. Reject stale reads after switching build identity.

### 2. Running-build overview

Primary content: “N records are ready to review” with one review-ready action and a secondary needs-attention action. Zero ready records gets a truthful waiting message and available issue/source actions. No empty review action that implies readiness.

One compact task-status card: stage, known counts, determinate or indeterminate progress, Pause only if supported, and secondary lifecycle actions. Reuse existing handlers; do not invent pause/resume semantics. Record filter counts are separate from task progress. Retain preparation, manifest review, interruption, failure and no-record states.

One warning summary grouped by verified cause; details expose original messages. Put provider/model, active task IDs, elapsed/ETA, concurrency, metrics, cleanup, timeline and technical diagnostics under Build details. Keep critical source/provenance/publication blockers visible even when details are closed. Do not let generic warning grouping hide severe failures.

### 3. Review workspace

Above the workspace: compact build identity/accepted count, one activity strip and at most one concise grouped-warning summary. Hide detailed provider controls, task lists, metrics and cleanup information behind disclosures. No repeated dashboard above the text.

Keep queue, reading pane and decision inspector. At 1440x900 and 1920x1080 the workspace should receive at least 65% of usable content height; aim for 75% at larger sizes. Usable height excludes global shell chrome. At 1280x720 keep the source and primary action visible without scrolling past a dashboard. Starting widths: queue 240–280px, inspector 320–380px, flexible center with approximately 60–80 character reading measure; adapt to existing splitters rather than overriding saved preferences.

Inspector: required unresolved decisions first; proposed value, provenance/status and evidence remain distinct; Confirm/Change uses existing validated mutations. Keep uncertainty/explicit absence visible. Do not add unsourced explanations. Optional metadata/analytics may collapse, but source/evidence access remains obvious. Make record-specific decision counts agree between inspector and footer.

One sticky decision bar: actual save/error state, Skip, Reject & next, Accept & next. Preserve keyboard shortcuts and conflict handling. Bulk acceptance belongs to the queue toolbar/secondary menu and must retain blockers. Avoid presenting “Mark reviewed” and “Accept” as interchangeable. The bar must not overlap text, validation errors, focused controls or horizontal scrollbars.

### 4. Build details / issues

Provide Activity / Issues / Settings sections in one reusable details surface. Use a docked panel on wide screens where practical; overlay or full-screen dialog on narrow screens. Do not render all hidden expensive content eagerly.

Warnings are currently string arrays. Group only safely recognized formats into a normalized cause; keep unknown entries under Other warnings and retain exact messages in expandable details. Do not parse arbitrary text into authoritative IDs. Link affected records only when a validated ID resolves within the same build. Preserve source ordering or stable group ordering across refreshes. Show group entry count and, only when known, distinct affected-record count.

Retry invokes existing supported operations and indicates their actual scope. No fictitious per-group retry API; if only build-wide retry exists, label it accordingly. Opening issues must preserve the review selection, draft, queue filter, splitters and scroll. Switching builds must clear identity-specific data and reject old responses.

## Implementation checkpoints (in order)

1. **Inventory and state contract.** Trace actual mounting and current setup/build/review flags; inspect server counter semantics and retry handlers. Capture baseline screenshots for the three supplied states. Add shared typed presentation derivation and focused tests for valid/zero/missing/inconsistent counters and overlapping queues. Record any gaps below.
2. **Compact status and grouped warnings.** Refactor existing live status and warning rendering; introduce a small shared summary component only if reuse warrants it. Implement details grouping, raw-message access and truthful progress. Add stories for running, waiting, stalled, inconsistent and failed states. Validate preserved lifecycle handlers.
3. **Build overview.** Make ready-record review the primary action; use existing queue-opening handlers. Replace duplicate progress/lifecycle presentations with one summary plus details. Test ready=0, issue-only, pre-record, awaiting-manifest, interrupted/resumable and published states.
4. **Review layout.** Reallocate height, reduce top chrome, prioritize decisions, consolidate action hierarchy and preserve splitters/focus/selection. Add viewport tests and retain source/metadata modes, text drafts, bulk actions and revision conflicts.
5. **Setup and build switching.** Introduce explicit draft/selected-build mode, compact selected-source details and accessible build panel. Test draft return, route restoration, source readiness, concurrent-build limits, pagination and stale polling responses. Preserve supported upload types and server rules.
6. **Integration and documentation.** Remove obsolete render paths/state/styles introduced by this redesign only after checking consumers. Update USER_GUIDE, stories, locale parity and this plan; capture final screenshots and run the checks below. Keep publication/finish behavior unchanged unless a separately documented UI-only adjustment is needed.

Each checkpoint should be independently reviewable. Update status, files, checks and next action below; do not claim screenshot parity as functional completion.

## Tests and acceptance

Extend existing behavior suites instead of snapshot-only/source-string assertions:

- `web/tests/frontend/corpus-builder-setup.test.ts`: selected source, draft preservation, active build/settings distinction and gates.
- `corpus-builder-build-review.test.ts`, `corpus-builder-metadata.test.ts`, `corpus-builder-focus-review.test.ts`: review availability, mutation/retry permissions, scope labels, selection and text draft retention, conflicts, build identity isolation.
- `corpus-review-layout.test.ts` and `web/tests/e2e/corpus-review-layout.spec.ts`: readable text, splitters, toolbar/footer collisions and compact chrome.
- Existing e2e `corpus-builder-workflows.spec.ts`, `corpus-builder-surfaces.spec.ts`, `corpus-builder-theme-sweep.spec.ts`, `corpus-builder-bugfixes.spec.ts`: integrated navigation, theme and accessibility coverage as applicable.
- Add focused presentation/grouping unit tests for explicit queued=0, total missing/0, settled>total, failed/skipped meaning, unknown warning formats, repeated messages, invalid record links and overlapping counts. Verify existing semantics before changing implementation.

Scenario fixture: 370 records; 18 ready / 101 waiting / 251 attention only if verified exclusive; 973 settled of 1110 tasks; 137 queued, 0 running; 100 repeated warnings. Separately reproduce settled=1324,total=1110; missing counters; task failures different from warning counts; paused/cancelled/failed; source blockers; published; 0 records; long French titles; 1000 warnings; stale response after build switch; network refresh failure with an unsaved draft.

Keyboard: focus visible, logical traversal, Escape closes overlays, close restores trigger focus, modal focus containment only for modal presentation, background inert only when modal, no keyboard shortcut firing inside text inputs. Status announcements must be concise and not reread whole task lists on each poll. Semantic headings/tabs and non-color status cues required. Use existing tokens, no literal colors; minimum 12px, preferably 14px for operational text and 16px+ reading text. Check English/French, light/dark, 200% zoom, 1920x1080, 1440x900, 1280x720, 1024px and 768px widths. Narrow layouts must keep review actions accessible; do not squash three columns.

Run from `web/`: `npm run typecheck`, relevant `npm run test:unit -- <test paths>`, `npm run build`, `npm run build-storybook`, relevant `npm run test:e2e -- <spec paths>`. Run locale parity and backend regression tests relevant to any changed locale/contracts after locating their actual filenames. Broaden tests for integration changes; disclose missing browser/dependencies and baseline failures. No release bump/tag or Docker rebuild is required merely for this planning document; do not claim release readiness without repository release gates.

Done means: all three surfaces work with real current data; counts are truthful and scoped; no repetitive warning stack; review remains usable during permitted enrichment; drafts survive secondary inspection/refresh; identity switches cannot display stale data; mutation/publication gates and provenance remain intact; both locales and themes pass applicable checks; USER_GUIDE and handoff status reflect the shipped behavior.

## Handoff status

- Completed: source inventory and this plan; four concept references preserved.
- Implementation: checkpoints 1–10 implemented within this checkout's supported PDF workflow. Shared status, grouped warnings, overview, responsive review, setup-draft separation, history side panel and stale-read integration guards are in place.
- Validation: production/Storybook builds and all 23 offline browser cases passed, including all 161 Corpus Builder stories in both light and dark (322 story/theme scans). The first full frontend suite passed 453 tests across 75 files; a repeat passed all assertions but reported one asynchronous OperationsPanel teardown error. Its 21 tests pass alone; the repeated full suite must not be labelled clean. Four pure Python locale/accessibility checks passed via direct invocation; pytest remains unavailable. See checkpoint 10 and `design/corpus-builder-ux/validation-2026-10-16.json`.
- Limits: only supported PDF acquisition is exposed. No invented pause, per-warning retry, checkpoint proof or task denominator was added. Actual browser zoom, the app-wide Storybook sweep beyond Corpus Builder, backend pytest, Docker/CI and live-backend validation remain uncompleted. Local services and Docker's Linux engine are unavailable. The OperationsPanel teardown error remains unresolved and is outside this task's modified product files.
- Next action: for further development, re-inventory the existing PDF asset/source-readiness contract before improving the source picker; preserve setup draft isolation and do not add unsupported library/web/HTML acquisition. A real smoke test requires the local frontend/API to be running. Keep the OperationsPanel teardown investigation separately scoped; do not silently broaden this UX patch. Review the local diff and evidence before publication.
- Future agents: append checkpoint entries with commit (if authorized), changed files, actual commands/results, unresolved gaps and the exact next task.

### Checkpoint 1 — 2026-10-15

- Added `web/src/domain/corpusBuildPresentation.ts` and `web/tests/frontend/corpus-build-presentation.test.ts`; updated live status, its stories, both locale dictionaries and USER_GUIDE.
- Backend evidence: `corpus_builder.py` `_checkpoint_metadata_task` rebuilds counters from current record/family states; complete/failed-or-needs-review/skipped are distinct terminal states. `_queue_counts` partitions pending records into preparing/ready/issues; metadata/topology/source subqueues overlap. Accepted and rejected records are outside that pending partition.
- Shared helpers expose independent record counts without summing overlapping issue subqueues. Live status no longer guesses tasks from records or replaces explicit queued=0; incomplete terminal counters and missing/zero totals produce indeterminate progress. Overcommitted snapshots retain raw outcome diagnostics and show Updating task counts, without invalid ARIA values or ETA.
- Removed the unsupported durable-checkpoint claim and its unused style. Last task activity remains visible. Settlement is explicitly separated from success, failure and skipped outcomes. Settle/cancel actions remain unchanged and tested.
- Commands: `npm --prefix web run test:unit -- tests/frontend/corpus-build-presentation.test.ts tests/frontend/corpus-domain.test.ts` (17 passed); `npm --prefix web run build` (passed, includes typecheck); `npm --prefix web run build-storybook` (passed). Existing chunk-size/docgen warnings were reported. Direct Python dictionary/placeholder checks passed. `python -m pytest -q tests/test_locale_dictionaries.py` could not run because pytest is absent in the bundled interpreter.
- No backend processing or lifecycle permission changes. No browser verification, commit or push performed. The screenshot/checkout renderer difference remains a discovery task before layout work.

### Checkpoint 2 — 2026-10-15

- Verified mounting: `PdfWorkspaceView.vue` mounts `PdfCorpusBuilder.vue` in builder mode. Screenshots still include newer/different source setup capabilities; do not invent those in this checkout.
- Added `CorpusBuildWarnings.vue`, stories, domain grouping and unit/browser regression cases. Builder summary exposes warnings even during review; technical progress reuses the same component in standalone usage and does not duplicate warnings in the main builder.
- Grouping recognizes only the narrow `record-id: family metadata failed (code); review required.` display format; unknown messages keep their exact text and exact duplicates share a group. Every original warning entry is retained, including duplicates. Parsed strings never become links, IDs or mutation requests. No unsupported retry or acknowledgement operations added.
- Compact live status now places timing/concurrency/active IDs in a keyboard-operable native disclosure. Existing settle/cancel controls remain visible. Provider switcher, metrics, cleanup and effectiveness are collapsed together during review; pass controls and hands-free exceptions remain visible. Details reset on build identity change; no record selection mutations were added.
- Removed obsolete warning styles in progress and reused token-based styles in new disclosures. Added matching English/French strings and USER_GUIDE instructions.
- Validation: 42 tests passed across status/warnings/build-review/focus/layout; an additional run covering setup and metadata passed 45 tests. Production build passed; final typecheck passed; locale key and Corpus Builder placeholder parity passed. Browser and Storybook results recorded below when complete. Full frontend suite and backend pytest not run.
- Remaining: full docked details panel, verified record links, build overview, source/setup draft isolation and full review viewport redesign belong to later checkpoints. This increment deliberately uses inline native disclosures.
- Final checkpoint validation: Storybook production build and final typecheck passed. Playwright first failed before tests with EPERM removing an existing `web/test-results` artifact. Retrying with isolated output could not start the Storybook development server; a temporary configuration using static Storybook/Vite preview also failed to become available in this environment and was stopped. Temporary configuration removed; existing results left untouched. The new browser regression spec is **unverified**, not a passing browser/visual check. Run `npm run test:e2e -- corpus-build-status.spec.ts --project=chromium-desktop --output=test-results-corpus-status` from `web/` in a functioning local preview environment.

### Checkpoint 3 — 2026-10-15

- Added `CorpusBuildOverview.vue` and stories for running, no-ready, unavailable-count, locked and interrupted states; added overview behavior tests and a builder navigation regression test.
- Header Build overview / Review records switch is available only when the existing lifecycle exposes review and the build is outside finish/publication. Existing automatic entry into review remains the default; no route, backend or persisted state contract changed.
- Overview shows server ready/preparing/issues counts, with accepted/rejected totals separate. It does not infer ready records from pending-minus-issues or create an enriching-record count from active tasks. Missing counts render unavailable; zero-ready state offers inspection/issue review without a misleading ready action.
- Ready and issues actions use existing queue/record reads and preserve locks/busy guards. Running enrichment reuses live task status and settle/cancel events. Existing summary controls retain cancellation in other running stages and resume for eligible stopped builds. Lifecycle, quality and timeline move under technical details in overview; pre-record, manifest-review and finish/publication rendering paths are unchanged.
- Review remains mounted under `v-show` while overview is open. A shallow-mounted actual-builder test confirms the editor DOM node and unsaved text survive switching out and back; it also verifies hidden review shortcuts cannot submit a review decision. Explicit queue navigation changes selection under existing semantics.
- Validation: 56 targeted tests passed across nine frontend files, including lifecycle, setup, review, metadata, status/warnings, overview and navigation. Final build/Storybook results below. Direct locale key/Corpus Builder placeholder parity passed. Browser layout/a11y checks remain unverified due to the checkpoint-2 local preview startup limitation; no full frontend/backend suite or Docker checks claimed.
- Next task: checkpoint 4. Measure real review viewport behavior before altering pane dimensions; do not disturb unsaved drafts, saved splitters, queue filters or the sticky decision dock.
- Final checkpoint checks: production build (vue-tsc + Vite), Storybook build and `git diff --check` passed after the shortcut guard. Existing chunk-size/docgen warnings remain. No commit or push performed.

### Checkpoint 4 — completed 2026-10-16

- Review responds to actual container width (1100px threshold), retaining three panes on wide workspaces and using the existing Metadata/Source workspace modes on narrower desktops. Saved splitter preferences remain unchanged. On small/short screens the grid has natural height; the builder locally clears the collapsed shell rail.
- Measured with the production frontend and mock API at 1280×720: record width grew from 378px to 754px; decision dock height fell from about 155px to 109px. At 1024×768 record-pane height grew from about 358px to 547px. These are fixture/layout measurements, not application performance claims.
- Required metadata has a direct review action, with a deduplicated required-field count. Inspector counts explicitly refer to fields needing review for the current record, including optional attention fields; they are not equated with acceptance blockers. Text drafts survive inspector navigation. Bulk acceptance is secondary. Compact session identity avoids repeating queue counts and model/build IDs.
- Native sizing and wrapping fixes cover French controls at 320px; removed the obsolete blocking-field label computation and blocker-heading styles. Added compact session stories, navigation/state tests and viewport regressions.
- Browser discovery: installed Chromium is under `C:/Users/aaron/AppData/Local/ms-playwright`; the sandbox's default cache location differs. Local preview-server startup remained unreliable. Added `web/playwright.corpus-offline.config.ts` and `web/tests/e2e/support/built-app.ts` to run the actual built frontend through Playwright route fulfillment plus the existing mock API. This is a frontend integration check, not a live-backend test.
- Reproduce from `web/`: build first, then `npm run test:e2e -- --config=playwright.corpus-offline.config.ts --project=chromium-desktop --output=test-results-corpus-ux`. If the browser cache is redirected, set `PLAYWRIGHT_BROWSERS_PATH` to the installed cache first. The helper serves only local production assets; `/api` remains owned by the mock fixture.
- Twelve layout browser cases passed at this checkpoint (thirteen including checkpoint 5 history). A separate browser smoke used actual English/French dictionaries in light/dark: review-frame axe WCAG 2.2 AA checks passed at 1280px, with reflow/metadata navigation checked at 768px. Additional effective-viewport reflow checks at 640×360 and 320×800 found and fixed the French min-content overflow. Actual browser-zoom behavior and the full Storybook theme sweep remain unverified.
- Real fixture screenshots: `design/corpus-builder-ux/review-implemented-1280.png` and `review-implemented-768.png`. These are implemented UI captures, distinct from the four generated concepts. Temporary diagnostic scripts/configs were removed; their generated test artifacts were moved to this chat's visualization folder.

### Checkpoint 5 — 2026-10-16

- `CorpusBuildHistoryMenu.vue` now uses the existing `UiDialog` focus/Escape handling with a side placement. `UiDialog.vue` adds only an optional `placement` presentation prop, defaulting to its existing centered behavior. The history panel has title/filename search, loaded Active/All filters, refresh/error/loading states and explicit loaded/total pagination. Published status stays distinct; no generic percentage is presented as metadata progress.
- Main builder loads additional history pages with ID deduplication and retains rows on refresh failure. Panel opening suppresses global review shortcuts; selecting the already selected build is a no-op, preserving local editor state.
- New setup is separate from selected-build settings: `useCorpusBuildLifecycle` shows configuration only without a selected current build. Draft persistence no longer writes inspected-build values into the setup cache; saved provider/schema/source/execution/enrichment preferences are restored when configuring another build. Existing PDF acquisition remains supported; no unsupported web/library/audio import controls were introduced. Source hash/time details are collapsed.
- Setup mode prevents background history refresh from automatically reopening an existing build. Known active builds continue list polling. Build selection invalidates pending record reads; build refresh checks the selected ID before accepting a response. A delayed-build-response test confirms returning to setup wins the race.
- Validation: 75 targeted unit tests across twelve files; production build (vue-tsc + Vite); Storybook build; 13 browser integration checks via the permanent offline configuration passed. The history test checks docked width, search/filter counts, Escape/focus restoration and unsaved-editor retention. A separate targeted rerun passed its scoped axe WCAG 2.2 AA scan. Existing build chunk-size/docgen warnings remain. No backend processing/publication changes, full regression suite, CI, Docker build, commit or push claimed.
- Remaining checkpoint 6 audit: verify stale **source block** responses on asset/record changes (`refreshBlocks` currently assigns its awaited response without an identity guard); review failed-build error messages after switching identities; exercise history pagination under concurrent list changes and default centered UiDialog consumers. Expand accessibility/theme/zoom checks as warranted. Update checks and USER_GUIDE after any follow-up fix; do not silently expand into backend semantics.

### Checkpoint 6 — 2026-10-16

- Wrote delayed-source/build, local failure/retry and history-pagination regressions against the preceding implementation first. They reproduced four failures and three unhandled read errors; all now pass after the implementation change.
- Source reads are scoped to build ID, asset ID, record ID and the exact requested source-block IDs, with a monotonically increasing request token. Identity changes clear obsolete payloads immediately. Older successes, failures and denials cannot replace or clear the currently selected record's source evidence; unmount invalidates outstanding reads.
- Same-scope source refresh failures retain useful evidence with a localized error and local Retry; current 401/403 denials clear that payload. No provider failure is converted into semantic absence, metadata completion or acceptance. Retry restores keyboard focus only when its removed button left focus on the document body; user focus moved elsewhere during the read is preserved. Long error reasons wrap on narrow screens.
- Build refreshes also reject superseded reads and errors. New setup invalidates pending build/record/source reads. Existing pagination logic passed overlapping-page tests: duplicate IDs update in place and loaded distinct builds remain available. Existing centered Records Columns dialog tests pass with UiDialog's default placement.
- Fixed the legacy Configure another build settings shortcut to call `startNewBuildSetup`, restoring the separate saved draft and shared invalidation/polling behavior. History selection and all new-setup entry points are guarded while a foreground save/action is pending; monitoring/refresh remains available. A regression confirms an in-flight text save cannot switch to another build through the history event.
- Validation: **88 unit tests across 13 files passed**, including source races, denials, retention/retry, setup shortcut, mutation guard and a centered UiDialog consumer. **14 browser integration cases passed** with `playwright.corpus-offline.config.ts` against the production build and existing mock API. The source browser case covers retained evidence through HTTP 500, keyboard Retry, non-stealing focus after intervening interaction, narrow long-error reflow and scoped axe WCAG 2.2 AA. Production build (vue-tsc + Vite), Storybook build, direct locale parity and diff whitespace checks passed. Existing chunk/docgen warnings remain.
- USER_GUIDE and this handoff describe the implemented behavior. Generated local test-result folders were moved out of the checkout into this chat's visualization directory; unrelated agent work was preserved. No commit, push, PR, release tag or deployment performed.

### Checkpoint 7 — 2026-10-16: consolidated build details

- Added `web/src/components/CorpusBuildDetailsPanel.vue` and its Storybook stories. The shared `UiDialog` side placement supplies an opaque modal panel, focus containment, Escape, and trigger-focus restoration at desktop and narrow widths. This increment does **not** implement a nonmodal desktop dock.
- Activity / Issues / Settings tabs have arrow/Home/End navigation, roving tabindex and individual labelled panels. Content mounts on first visit; visited sections remain mounted while the dialog is open, preserving pending local settings edits across tab changes. Closing unmounts operational contents. No hidden detail fetch is started before the section is visited.
- `PdfCorpusBuilder.vue` relocates technical progress, timeline, quality, cleanup, metrics and effectiveness into Activity; raw grouped warning entries and the build error into Issues; inspected-build identity and existing provider/configure controls into Settings. A warning-count trigger opens Issues directly. Warnings are still entry counts, separate from failed tasks and affected records; zero warning entries is never labelled as zero unresolved record decisions.
- Removed the replaced inline disclosures and obsolete styles. Provider controls stack within the narrow side panel independently of viewport width; provider history stays inside the panel. Existing retry, resume, publication, required manifest review and finish controls keep their original guards. Opening details suppresses review keyboard shortcuts; build identity changes close the panel and reset its tab. The review editor remains mounted.
- Added `corpus-build-details.test.ts` for lazy sections, retained settings input across tabs, keyboard/ARIA behavior, same-identity refresh and build switches; extended overview-navigation tests for shortcut suppression. Existing settings shortcut/during-save tests render the relocated named settings slot and still exercise the parent handler and gates.
- Validation: **92 targeted unit tests across 14 files**, **16 offline production-frontend browser cases**, production build including vue-tsc, Storybook build, locale key/Corpus Builder placeholder parity and `git diff --check` passed. The two new browser cases cover 1440px and 320px, tab keys, scoped axe WCAG 2.2 AA, horizontal fit, Escape/focus restoration and unsaved review text. Existing build chunk/docgen warnings remain. Browser API data is mocked; no live backend, full regression, Docker or CI claim.
- Recorded and visually inspected synthetic-fixture screenshots: `design/corpus-builder-ux/details-implemented-1440.png` and `details-implemented-320.png`. `USER_GUIDE.md` now describes the new location of operational controls. No backend contract, scholarly metadata semantics or unsupported acquisition controls changed. Changes remain local; no commit/push/PR/release performed.

### Checkpoint 8 — 2026-10-16: verified warning record navigation

- Verified the backend contract: `_append_warning` retains plain strings, while the current metadata issue summary is rebuilt from actual non-rejected records and unresolved fields. Its `issues` and `records` arrays carry authoritative record IDs, capped to 1000 fields / 250 records. No new backend contract or inferred warning-to-field relation was introduced.
- Added `currentWarningRecordIds` in `corpusBuildPresentation.ts`. Only the existing narrow metadata-failure format supplies candidate IDs. IDs must exactly match a current structured issue/record reference; duplicates are removed. Unknown formats, arbitrary prose, partial ID matches and historical warnings absent from the current summary never produce review actions. Matching does not establish that the old warning caused today's field issue.
- `CorpusBuildWarnings.vue` shows distinct current-record review buttons within a group, alongside the unchanged original messages and warning-entry count. Both locales explain the historical/current distinction. The action is read navigation only; no automatic retry, acceptance, field confirmation or metadata mutation is implied. Controls honor the parent's busy/topology/review gates. Updated warning stories include available and locked actions.
- `PdfCorpusBuilder.vue` performs a build-scoped records search, finds the exact requested ID (never the first similar result), and rechecks current issue membership before committing selection. The endpoint search includes ID/text rather than being an exact-ID endpoint: if the exact record is absent from the returned page, navigation fails explicitly and preserves the existing workspace. This conservative limitation is intentional; no speculative backend API was added.
- Failures and unmatched results appear locally in Issues and allow another attempt. Queue/query/selection and drafts remain unchanged until verification succeeds. Success closes the panel, opens metadata review and focuses its inspector; a completed review session uses the existing metadata queue to remain in review. Same-record text and advanced-metadata drafts remain intact, and other-record text drafts remain in their existing per-record cache.
- Request/identity guards reject late results and failures after a build or review navigation change. A narrow commit guard prevents the normal filter watcher from clearing the already verified selection and launching a competing read. Navigation completion clears only the read-loading state it owns; existing mutation/publication gates are unchanged.
- Added two warning-helper/component regressions and six parent regressions: unknown/unverified candidates, duplicate/partial IDs, exact fetch selection, failed/unmatched lookup, stale build completion, same-record draft retention, membership removed during fetch and metadata navigation from a completed review session. Two new browser scenarios at 1440px / 320px cover historical messages, one verified action, grouped-message accessibility/reflow, failed/mismatched reads preserving drafts, successful metadata focus and existing text-draft persistence.
- Validation: **100 targeted unit tests across 14 files**, **18 offline production-frontend browser cases**, production build including vue-tsc, Storybook build, locale key/Corpus Builder placeholder parity and diff whitespace checks passed. Scoped axe checks passed on the expanded Issues groups. Browser API data remains mocked; live backend, full suites, full theme sweep/zoom, Docker and CI are still unverified. No commit/push/PR/release performed; unrelated work directories were preserved.

- Recorded and visually inspected the expanded Issues panel using synthetic fixtures: `design/corpus-builder-ux/warnings-implemented-1440.png` and `warnings-implemented-320.png`. Test-result directories were moved to the chat visualization directory after verifying their workspace paths.

### Checkpoint 9 — 2026-10-16: responsive nonmodal desktop dock

- `PdfCorpusBuilder.vue` observes the actual builder workspace width with ResizeObserver. At 1600px or more of available workspace, opening Build details reserves a 440px grid column; narrower layouts retain the existing modal side presentation. It does not choose docking solely by the browser's screen width. The observer disconnects on unmount.
- The dock is opaque, separately scrollable, and sticky beneath the top bar. It sits beside, rather than over, the main review region. At docked review widths up to 1400px, the review uses queue + record with Metadata/Source available in their existing full workspaces. This prevents fitting the dock plus three squeezed review panes into a modest desktop width. Existing splitter preferences remain stored. At larger working widths, the three-pane layout remains available.
- `UiDialog.vue` adds optional `dockTarget: HTMLElement | null`, default null. A target changes the same Teleport's destination and presents a labelled nonmodal region without aria-modal or a blocking backdrop. The default dialog path, focus trap, side/center presentation and trigger restoration remain intact. Callers without a target retain their previous behavior.
- Resizing moves the existing dialog and slot instances rather than conditionally constructing a second panel. The current tab, visited sections, input values, and focused child survive modal-to-dock transitions. Becoming modal while focus is outside the panel moves focus into it. Tab is untrapped in the dock; Escape closes it only when the event originates inside it, so Escape in the record editor does not dismiss the dock. Closing restores the original trigger; explicit warning navigation still moves focus into metadata review afterward.
- Review shortcuts are suppressed for events originating in the dock and whenever details is modal. Outside the dock, review remains usable with its existing shortcut/input/mutation guards. Added a Docked Storybook example and the shared-dialog copyright header; no user-facing strings or backend contracts changed.
- Added three `ui-dialog-docking.test.ts` cases for retained DOM/input/focus across relocation, untrapped Tab and scoped Escape, and default modal/trigger behavior. Existing centered Records Columns, history, details-tab and warning-navigation checks still pass. The new production-frontend browser case verifies docking at 1920px, non-overlap, a record pane wider than 600px, background text editing, a pending model input retained through 1280px modal reflow and back, focused input retention, scoped axe, no page overflow, sticky top alignment, reachable decision dock and close/trigger behavior.
- Validation: **103 targeted unit tests across 15 files**, **19 browser cases with the mock API**, production build including vue-tsc, Storybook build, and diff whitespace checks passed. The browser dock case also passed after adding sticky/decision-dock assertions. Recorded and visually inspected `design/corpus-builder-ux/details-docked-1920.png` using synthetic fixtures. No live-backend/full-suite/full-theme/actual-zoom/Docker/CI claim. No commit/push/PR/release performed.

### Checkpoint 10 — 2026-10-16: broader validation and overview semantics

- Read-only live checks confirmed that neither `127.0.0.1:8000/api/live` nor the frontend on port 8181 is accepting connections. `docker compose ps` cannot reach Docker Desktop's Linux engine. Initial sandbox socket restrictions were distinguished from the actual connection refusals by an approved read-only local check. No server, Docker daemon, provider job or existing corpus state was started or modified.
- The bundled Python interpreter still has no pytest. Four pure test functions were invoked directly from `test_locale_dictionaries.py` and `test_locale_and_accessibility_floor.py`: dictionary/placeholder parity, every literal frontend translation key, canonical locales, and the 12px font floor all passed. This is not the backend pytest suite.
- Extended `web/tests/e2e/support/built-app.ts` to route both the built app and built Storybook assets, including JSON. Storybook uses exact static paths and 404s for missing files; the app keeps its existing navigation fallback. `/api` remains owned by fixtures. `playwright.corpus-offline.config.ts` now includes review layout, build status, and theme sweep specs, with no preview server dependency.
- Updated the previously unverified `corpus-build-status.spec.ts` for the new Issues panel instead of the removed inline disclosure. It verifies keyboard expansion of 100 grouped raw warnings without changing review selection, plus the Storybook timing/reflow case. Both passed before the overview markup correction.
- The first full theme sweep scanned all 161 indexed Corpus Builder stories in light and dark. It failed only the five new Build Overview variants in both themes, all for axe `definition-list`: a button was a direct child of a definition-list group instead of belonging to its description. `CorpusBuildOverview.vue` now groups the count and action inside `dd`, preserving labels, counts, actions and visual spacing. The six overview behavior tests pass with the new count wrapper.
- The theme sweep now waits for Storybook's rendered-body state and attaches a JSON summary with theme, story count, and failures. Failure details include axe's node failure summary when available. No accessibility rule, story, or theme was excluded.
- Final validation: **23 browser cases passed**, including all **161 Corpus Builder stories in each of light and dark** (322 scans, no axe violations after the correction). Production build including vue-tsc and Storybook build passed. The first full frontend run passed **453 tests across 75 files**; a repeat after the markup correction passed all 453 assertions but reported one unhandled `Element is not defined` rejection after the OperationsPanel test environment had torn down. `OperationsPanel.vue` and its test are unchanged in this task; its 21 tests pass in isolation. This does not establish a clean repeated full-suite result or prove the failure is baseline. No unrelated OperationsPanel fix or test suppression was made.
- Outstanding external/environment gates: live-backend/provider integration, backend pytest suite, actual browser zoom, Docker builds and CI. The offline browser checks use fixtures and do not establish any of those results. No commit/push/PR/release performed.

- Reproduce the browser checks from `web/` after `npm run build` and `npm run build-storybook`: set `PLAYWRIGHT_BROWSERS_PATH=C:/Users/aaron/AppData/Local/ms-playwright`, then run `npm run test:e2e -- --config=playwright.corpus-offline.config.ts --project=chromium-desktop --workers=2 --output=<new-results-directory>`. This runs 19 integration cases, two status/disclosure cases, and two complete theme sweeps. The ordinary configuration still uses its preview servers; the offline configuration routes built assets and fixtures locally.
- The initial failed and final passing browser artifacts, plus full-unit logs, were retained outside the checkout in this chat's visualization directory. Snapshot writers rewrote three unrelated snapshot files' line endings during the full suite; their contents were verified against HEAD and checkout CRLF endings restored without changing their content. Machine-readable checkpoint evidence is in `design/corpus-builder-ux/validation-2026-10-16.json`.

### PR preparation — 2026-10-16

- The user explicitly requested a PR. Publish this change as `codex/corpus-builder-ux`, targeting the original remote checkout branch `codex/extract-vector-runtime-bridge` at `399e250f2`.
- Verified that the original remote branch still points to the tested baseline. Current `master` at `668156c58` has substantially different Corpus Builder, API and shared dialog implementations. The original checkout also has six historical commits not in master's ancestry. Targeting the original published branch keeps those unrelated changes out of this PR's review diff and avoids overwriting current contracts with older files.
- This is a draft review checkpoint, not a current-master-ready change. A separate port and validation on master remains required. Preserve all limitations above, especially the full-unit repeat's OperationsPanel teardown error and unavailable live-backend/Docker/backend-pytest/actual-zoom checks.
- Unrelated `.metadata-routing-work/`, `.research-filters-work/`, and `.research-thread-work/` directories are excluded from staging. Commit with the repository owner's specified identity. No release version bump or tag is part of this PR.
