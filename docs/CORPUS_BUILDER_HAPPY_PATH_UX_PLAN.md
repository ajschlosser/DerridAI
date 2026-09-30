# Corpus Builder Happy-Path UX Implementation Plan

Branch: `task/corpus-builder-happy-path-ux`

## Goal

Make Corpus Builder's primary experience obvious and low-friction:

> Load a source, choose or accept sensible configuration, start the build, then either watch it progress or begin reviewing as soon as Records exist. Pause and resume from wherever the researcher is working. When automated work is finished, either adjudicate remaining issues, accept ready suggestions in bulk, or explicitly publish suggestions as-is without misrepresenting them as human-reviewed.

The implementation must preserve DerridAI's provenance, cELF authority semantics, media-aware controls, WCAG 2.2 AA behavior, i18n, keyboard use, realtime resilience, and existing build/review/publication correctness.

## UX principles

1. **One dominant next action.** Every Corpus Builder state should make the most useful next action obvious without hiding secondary capabilities.
2. **Build and Review are concurrent activities.** The machine can continue building/enriching while the researcher reviews Records that already exist. The UI must not imply a hard sequential dependency.
3. **Defaults are decisions already made.** Recommended/provider/schema/sizing defaults should read as an already-valid plan, not unanswered form questions.
4. **Blockers are actionable.** A blocker must identify what is wrong and open the exact section/Record/field needed to fix it.
5. **Technical detail is available, not dominant.** Telemetry, IDs, traces, provider internals, and diagnostics remain accessible behind explicit disclosures.
6. **Human authority must remain explicit.** Bulk acceptance and unreviewed publication must not launder model/system suggestions into human-confirmed assertions.
7. **Source medium drives the interface.** PDF/page concepts stay restricted to paginated sources; audio/image/text workflows keep media-appropriate controls and language.
8. **No destructive visual churn.** Realtime progress should update in place without stealing focus or rebuilding review panes.
9. **Joy comes from momentum.** Use restrained motion, completion feedback, concise live activity, and progressive disclosure rather than decorative complexity.
10. **Accessibility and i18n are release gates, not cleanup work.**

## Existing architecture to preserve

The current implementation already provides the right major state and mutation boundaries:

- `PdfCorpusBuilder.vue` owns orchestration and composes Setup, Build, Review, and Publish workspaces.
- `workspace.ts` permits Review/Publish once Record topology exists.
- `workflowPresentation.ts` converts authoritative build state into user-facing status.
- `CorpusBuildPrimaryStatus.vue` exposes progress and build controls.
- `CorpusReviewRunStatus.vue` keeps live run information available inside Review.
- `CorpusReviewToolbar.vue` exposes bulk acceptance of ready Records.
- `CorpusPublishWorkspace.vue` and the publication API already support explicit unreviewed publication.
- The backend's `accept_unreviewed` path selects eligible suggestions without converting their derivation/authority into human confirmation.

This project is therefore primarily a hierarchy, interaction, and composition refactor. Backend changes should be limited to missing state/actions that the UI cannot faithfully express.

## Target information architecture

### User-facing phases

The top-level product presentation should become:

1. **Setup**
2. **Build & review**
3. **Publish**

Internal routes may continue to use `setup | build | review | publish` where that reduces risk. The header/presentation layer may group Build and Review as one phase while preserving deep links to `?workspace=build` and `?workspace=review`.

### Setup

Desktop target:

- Main configuration column.
- Sticky **Build plan** rail.
- Primary CTA: **Build corpus**.
- Source identity and detected facts are immediately visible.
- Configuration sections summarize current selections and open only when edited.
- Advanced execution is demoted to an explicit secondary disclosure.
- Blocking conditions in Advanced must not be visually described as optional.
- At most one dominant build-launch surface.

Narrow layouts:

- Single-column configuration.
- Build plan becomes a bottom command surface or in-flow summary without duplicate sticky chrome.

### Active build

Primary live surface should communicate:

- lifecycle state in plain language;
- current operation;
- coarse overall progress;
- Records created;
- ready / needs-attention counts when available;
- provider/model only as secondary context;
- machine-stage rail;
- **Pause / Resume**;
- an obvious **Review ready Records** action as soon as topology exists.

The product should explicitly say that automated work can continue while review happens.

### Review

Preserve the three-pane review workspace, but simplify its command hierarchy:

- compact run-status pill persists while reviewing;
- run pill exposes **Pause** while active and **Resume** while paused/interrupted;
- queue/filter/search remain in the primary review header;
- view controls move closer to the pane they affect where practical;
- bulk actions become contextual rather than permanently competing with navigation;
- **Accept N ready Records** is prominent when N > 0;
- field/Record completion should move focus to the next meaningful unresolved item without losing viewport;
- empty queues should provide a meaningful next action.

### Publish

Publication should read as a conclusion:

- compact readiness summary;
- three principal readiness groups: Records, Required metadata, Source & validation;
- one direct repair action per group when blocked;
- primary **Publish corpus** action when ready;
- secondary explicit shortcut for **Use suggestions as-is & publish** when allowed;
- completion state shows publication identity, review mode/conformance context, Record count, download, and start-new-build.

The unreviewed shortcut must continue using the existing publication semantics and must not be labeled as human acceptance.

## Implementation phases

### Phase 0 — Baseline and safety net

Status: **complete**

- [x] Create this implementation branch from latest `master`.
- [x] Document the implementation plan before changing behavior.
- [x] Re-read current Corpus Builder characterization/workspace/build-review tests before changing markup.
- [x] Identify i18n source files for all touched Corpus Builder copy (`api/app/locales/{en_us,fr_ca}.py` with `web/src/i18n/enUsDefaults.json` as the frontend English fallback snapshot).
- [x] Preserve route-backed workspace behavior and existing deep links.
- [x] Add/adjust focused tests alongside each behavioral change.

### Phase 1 — Workflow presentation: Setup / Build & review / Publish

Status: **complete**

Goal: correct the conceptual hierarchy without rewriting authoritative workspace state.

- [x] Add a presentation grouping that maps internal `build` and `review` to one user-facing **Build & review** phase.
- [x] Update `CorpusBuilderWorkspaceHeader.vue` to render three user-facing phases while still routing to the correct internal workspace.
- [x] When Build & review is selected:
  - [x] preserve the current Build/Review workspace when the grouped phase is already active;
  - [x] from another phase, route to Review once Records exist, otherwise Build;
  - [x] preserve direct links to explicit `workspace=build` or `workspace=review` and expose both as an in-phase sub-navigation.
- [x] Ensure combined phase completion requires both automated Build completion and Review completion, so the UI no longer implies a false sequential handoff.
- [x] Add English and Québec French copy.
- [x] Update workspace unit coverage for the three-phase presentation and internal Build/Review navigation.

Likely files:
- `web/src/features/corpus-builder/domain/workflowPresentation.ts`
- `web/src/features/corpus-builder/domain/workspace.ts` only if a presentation helper cannot live elsewhere
- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`
- `web/src/components/PdfCorpusBuilder.vue`
- locale modules
- Corpus Builder workspace tests

### Phase 2 — Build plan and setup hierarchy

Status: **complete**

Goal: make setup feel like a prepared plan rather than a long form.

- [x] Use the existing `CorpusBuildReadiness.vue` boundary as the Build-plan component so setup logic stays centralized rather than adding a second wrapper.
- [x] Desktop layout: configuration content + sticky Build plan rail.
- [x] Build plan summarizes:
  - [x] source identity/media facts;
  - [x] structure/transcription state where the medium supports it;
  - [x] metadata schema;
  - [x] enrichment/provider/model;
  - [x] Record sizing;
  - [x] warning/blocker count.
- [x] Keep a single dominant launch/fix action: Build is primary when ready; Fix is primary when blocked.
- [x] Edit setup sections directly from the corresponding Build-plan fact; the section component itself continues to own collapse state.
- [x] Replace the duplicate sticky-bottom launch treatment with the dedicated Build plan rail.
- [x] Rename/demote “Advanced” presentation to **Run settings**.
- [x] Fix the semantic contradiction where Run settings can appear optional while containing a blocking context-safety issue.
- [x] Media-aware source facts use page extent only for paginated sources and otherwise fall back to medium/source-unit facts.
- [x] Responsive layout collapses the sticky rail into the single-column flow below 1100 px and the plan itself to one-column controls below 720 px.
- [x] Storybook states cover no source, ready, warning/blocking, long Québec French copy, and narrow/mobile layout.

Likely files:
- `CorpusSetupWorkspace.vue`
- `CorpusSetupSection.vue`
- `CorpusBuildReadiness.vue`
- `setupState.ts`
- new component(s) under `components/corpus-builder/`

### Phase 3 — Live build workspace

Status: **complete**

Goal: turn the build screen into a live, legible work surface.

- [x] Keep/recompose `CorpusBuildPrimaryStatus.vue` around:
  - [x] lifecycle headline;
  - [x] current operation;
  - [x] progress;
  - [x] key counts;
  - [x] stage rail;
  - [x] primary controls.
- [x] Add a high-priority **Review N ready Records** action as soon as topology exists and ready Records are available.
- [x] Copy explicitly states that review can begin while automated build work continues in the background.
- [x] Add a restrained activity strip derived only from persisted authoritative `build_events`; do not invent fake events.
- [x] Keep detailed audit/diagnostic material behind the renamed **Run details** disclosure.
- [x] Keep actionable warnings/errors visible in Build while detailed audit material stays in Run details.
- [x] Keep progress semantics honest: the existing coarse cross-stage percentage remains explicitly non-ETA in documentation and no synthetic timing was added.
- [x] Preserve the progressbar ARIA contract and existing reduced-motion override; the new activity strip is static and keyboard-neutral.

### Phase 4 — Persistent run control in Review

Status: **complete**

Goal: allow researchers to control the build without leaving Review.

- [x] Add **Pause** to `CorpusReviewRunStatus.vue` while the corpus build itself is active.
- [x] Keep **Resume** for resumable states.
- [x] Keep cancel/settle/provider switching inside expanded run details; only Pause/Resume and Run another pass can be primary beside the compact run label.
- [x] Preserve the existing compact active-state label (“Enriching/Running · percent · model”).
- [x] Wire pause from the Review run control through `PdfCorpusBuilder.vue` to the existing lifecycle pause mutation.
- [x] Add a focused component test proving Pause is available and emits directly from Review.
- [x] Live status remains text/state updates only; no focus-changing watcher or remount was introduced.

### Phase 5 — Review command hierarchy and bulk happy paths

Status: **complete**

Goal: reduce control competition and make fast adjudication obvious.

- [x] Keep queue tabs + issue filter + search as the primary review-navigation controls.
- [x] Promote **Accept N ready Records** only when ready work exists.
- [x] Replace native `window.confirm` for ready-Record bulk acceptance with the shared accessible dialog pattern.
- [x] Move selected-record edit/reject commands into a contextual selection bar when selected count > 0; non-selection actions remain under More actions.
- [x] Keep the compact Record/Metadata/Source switch in the consolidated review header: moving it would duplicate inspector navigation and split one existing accessible view contract; density is instead reduced through contextual bulk actions.
- [x] Preserve the existing roving-keyboard queue tabs and live/status announcements; the new confirmation dialog uses the shared focus-managed dialog.
- [x] When Ready or issue queues empty, show a completion state with Show all and Publication readiness actions.
- [x] Preserve authoritative human-ownership semantics and the existing serialized mutation path; only the confirmation surface moved out of `window.confirm`.

### Phase 6 — Publish simplification and explicit skip-review path

Status: **complete**

Goal: make publication readiness understandable at a glance.

- [x] Remove the duplicate metadata-issues surface from Publish and flatten the nested Finish card while keeping direct queue/repair actions.
- [x] Present three principal readiness groups:
  - [x] Records;
  - [x] Required metadata;
  - [x] Source & validation.
- [x] Each blocked readiness group retains a direct repair path into the relevant Record/queue/validation context; optional retry/rerun utilities remain secondary.
- [x] Rename/reframe `accept_unreviewed` UI as **Use suggestions as-is & publish**.
- [x] Confirmation dialog clearly states:
  - [x] no human-review claim is created;
  - [x] suggestion/provenance state remains preserved;
  - [x] source/text-conservation validation still applies;
  - [x] conformance is evaluated independently and blockers may remain.
- [x] Published completion surface: hide readiness counters after publication and rely on the publication snapshot for identity, Record count, review mode/conformance, and download.
- [x] Preserve the existing backend `accept_unreviewed` publication path and cELF assertion authority semantics; no publication API contract changed.

### Phase 7 — Visual polish and “joy”

Status: **complete**

- [x] Flatten nested Finish/Publish card treatment and use whitespace/rows for grouping.
- [x] Use primary accent emphasis for Build/Fix, Review-ready work, bulk ready acceptance, Publish, and completion paths rather than secondary controls.
- [x] Keep motion restrained: existing control/progress transitions remain, while live stage, queue-completion, and count changes update in place without attention-stealing animation.
- [x] Preserve existing `prefers-reduced-motion` behavior and add no new essential animation.
- [x] Keep source filename/media facts prominent in the header and Build plan.
- [x] Keep build IDs/hashes and provenance internals behind Build details / Run details.
- [ ] Verify dark/high-contrast/forced-colors states in CI/E2E before marking the PR ready.

### Phase 8 — Documentation, Storybook, regression, cleanup

Status: **in progress**

- [x] Update User Guide for the three-phase happy path, Build plan, concurrent Review, pause/resume, contextual bulk actions, and suggestions-as-is publication.
- [x] Update architecture wording: three user-facing phases with four route-backed internal workspaces.
- [x] Update the Corpus Builder Help Center page-guide task copy to the three-phase happy path.
- [x] Add Storybook coverage for the Build plan's ready/no-source/warning states and the new live build activity strip; remaining touched states still need final audit.
- [ ] Run formatting/Prettier.
- [ ] Run focused frontend tests after each checkpoint.
- [ ] Run full frontend test suite and build.
- [ ] Run repository-required CI/lint/typecheck/i18n/WCAG checks.
- [ ] Check English and Québec French.
- [ ] Check keyboard-only operation.
- [ ] Check screen-reader labels/live regions.
- [ ] Check 320 px/mobile overflow.
- [ ] Check reduced motion, dark mode, high contrast, forced colors.
- [ ] Ensure no regression to non-PDF media.
- [ ] Remove superseded CSS/components only after characterization tests prove equivalence.

## Acceptance scenarios

The implementation is complete when these scenarios are straightforward without prior Corpus Builder knowledge.

### A. Default happy path

1. Open Corpus Builder.
2. Add/select a text/PDF/document source.
3. See detected source facts and a valid default build plan.
4. Click **Build corpus** without opening every configuration section.
5. Watch understandable live progress.
6. When Records exist, click **Review ready Records** while enrichment continues.
7. Pause/resume the build from Review.
8. Accept ready Records in bulk and adjudicate exceptions.
9. Open Publish and see a concise readiness checklist.
10. Publish and download the immutable artifact.

### B. Sit-back path

1. Configure and start.
2. Stay on the live build surface.
3. Automated work reaches completion without requiring Review navigation.
4. Open Publish when ready.

### C. Fast publication path

1. Let automated work finish.
2. Choose **Use suggestions as-is & publish**.
3. Read a clear confirmation that this is not human review.
4. Publish only if source/text-conservation gates allow it.
5. Published provenance retains unreviewed/autonomous authority semantics.

### D. Interrupted build

1. Start build.
2. Pause from Build or Review.
3. Leave the page.
4. Return through build history/deep link.
5. See **Paused** with the same progress.
6. Resume from the current workspace.

### E. Blocked setup

1. Introduce an invalid context/execution setting.
2. The main plan says exactly what blocks launch.
3. **Fix** opens the relevant setting even if it normally lives under Run settings.
4. Clearing the blocker immediately restores launch readiness.

### F. Non-PDF source

1. Load audio/image/text.
2. Setup and Build plan use appropriate units/structure/transcription language.
3. No page-specific control or copy appears where the source has no scholarly pages.

## Checkpoint / commit protocol

Work on this branch will be committed in coherent checkpoints. At each checkpoint:

1. update this plan's phase status and “Progress log”;
2. commit implementation plus plan update together when practical;
3. keep commits small enough to review and revert independently;
4. run the most relevant focused tests before moving on;
5. do not wait until the end to record architecture or UX decisions.

## Progress log

### Checkpoint 0 — planning

- Created `task/corpus-builder-happy-path-ux` from current `master`.
- Audited the current Setup, Build, Review, Publish composition and existing happy-path capabilities.
- Confirmed the implementation already supports concurrent build/review state, pause/resume at the build layer, bulk “ready” acceptance, and provenance-safe unreviewed publication.
- Added this implementation plan before behavior changes.

### Checkpoint 1 — pause/resume from Review

- Added an always-visible **Pause** action beside the compact run monitor when the corpus build is actively queued/running in Review.
- Routed the action to the existing durable `pauseBuild` lifecycle operation, so checkpoint/resume behavior is unchanged.
- Kept metadata-only follow-up operations distinct: Pause is shown only for the corpus build itself rather than implying that every auxiliary operation shares the same pause semantics.
- Added focused component coverage for the Review pause action.
- No new copy was required; the existing localized Pause/Resume strings are reused.

### Checkpoint 2 — review while the build continues

- Promoted Review to a primary action on the live Build surface when ready Records exist, including the current ready count.
- Added an explicit explanation that researchers can begin reviewing while automated work continues.
- Passed the existing authoritative `readyCount` through the Build workspace rather than deriving a second count in presentation code.
- Added English, Québec French, and frontend English-fallback copy.
- Extended the active-enrichment component test to cover the new concurrent-review affordance and explanatory copy.

### Checkpoint 3 — three-phase workflow presentation

- Replaced the four peer phase buttons with **Setup → Build & review → Publish** at the user-facing level.
- Kept `build` and `review` as internal route-backed workspaces to avoid breaking deep links or lifecycle logic.
- Added an in-phase Build/Review sub-navigation so users can switch between live status and Record review without reintroducing them as separate top-level phases.
- Combined phase completion now requires both Build and Review completion.
- Added English and Québec French labels plus focused workspace-header coverage.

### Checkpoint 4 — Setup becomes a Build plan

- Re-composed Setup into a two-column desktop workspace: configuration sections remain the main work area and launch/readiness now lives in a sticky **Build plan** rail.
- Reworked `CorpusBuildReadiness.vue` from a second sticky command bar into a focused plan card with one dominant action.
- When setup is blocked, **Fix** becomes the primary action and **Build** becomes secondary/disabled; when setup is ready, **Build** is primary.
- Renamed the user-facing **Advanced** section to **Run settings**.
- Corrected setup-state semantics so a blocking context/run-setting problem is reported as incomplete rather than optional.
- Added English/Québec French/fallback copy and focused tests for the Build plan label and blocking run-setting state.

### Checkpoint 5 — faster review and clearer publication

- Promoted **Accept clean (N)** only when ready Records actually exist, reducing disabled-control noise.
- Replaced the native browser confirmation with the shared focus-managed `UiDialog`, including explicit copy that bulk acceptance records a human review decision while unresolved exceptions remain queued.
- Removed the now-redundant second metadata-issues panel from Publish; publication repair remains available through the single Required metadata readiness row.
- Reduced the publication summary from five competing counters to the three quantities that map to the readiness groups: pending review, metadata issues, and validation blockers.
- Flattened the nested Finish surface so Publish reads as one workspace rather than cards inside cards.
- Renamed the provenance-safe skip-review path to **Use suggestions as-is & publish…** and updated the confirmation action/title in English, Québec French, frontend fallbacks, frontend tests, and the representative E2E workflow.

### Checkpoint 6 — momentum, contextual review, and current docs

- Added a compact **Build timeline** activity strip to the live Build surface using only the build's persisted `build_events`; it shows recent real stage transitions and progress without fabricating an ETA or event stream.
- Added Storybook and focused component coverage for the activity strip.
- Moved selected-record **Bulk edit metadata** and **Reject selected** actions into a contextual selection bar; non-selection actions remain behind **More actions**.
- Tightened the Build plan's source identity with media-aware extent facts while continuing to suppress page semantics for non-paginated media.
- Made the published state read as completion by removing pre-publication readiness counters after a publication exists.
- Updated `docs/ARCHITECTURE.md` and the User Guide to explain the three user-facing phases, four internal routes, concurrent Build/Review behavior, Build plan, Review controls, and provenance-safe suggestions-as-is publication.

### Checkpoint 7 — draft PR and validation handoff

- Opened draft PR **#336** from `task/corpus-builder-happy-path-ux` to `master` so the repository's full quality gates can validate the branch while final cleanup continues.
- The branch is currently rebased/aligned with `master` (0 commits behind at PR creation).
- Closed the remaining implementation-plan gaps that were already satisfied by the current composition: queue completion actions, direct Build-plan editing, media-aware summary facts, Run details progressive disclosure, and explicit source/text-fidelity language in the suggestions-as-is publication dialog.
- Corrected the Build plan's description-list markup so the new summary remains semantically valid for assistive technology.
- Remaining work is validation-driven: formatting, lint/typecheck, unit/E2E/a11y results, then any fixes those gates uncover.


### Checkpoint 8 — agent handoff

- Added `docs/CORPUS_BUILDER_HAPPY_PATH_UX_HANDOFF.md` with the architectural constraints, completed work, touched files, coverage changes, remaining validation work, and a recommended execution order for the next agent.
- Re-checked branch divergence at handoff time: the branch is currently **100 commits ahead and 28 commits behind current `master`**, with merge base `7b805d83f9f1ef87aa37a785bc64ac0f78e93cd5`.
- The handoff explicitly supersedes the older “aligned with master” observation from draft-PR creation time. Current master synchronization is now the first remaining integration task.
- No remaining Phase 8 validation checkbox was marked complete without actually running the corresponding formatter/test/CI/accessibility gate.


### Checkpoint 9 — current master synchronized

- Merged current `master` (`2560d801300226595455ee2a98054641bdd5a7fa`) into the branch as `9d13da310fc36edf8ba8168ea1781adfccfb8c67`.
- Reconciled the only overlapping master changes semantically: English/Québec French locale dictionaries, generated English fallbacks, and the User Guide's static-site publication section. Corpus Builder UX copy and master’s publication-delivery-mode work are both retained.
- The branch is now **0 commits behind master**. Remaining work is validation-driven: CI/static checks, focused/full frontend coverage, E2E/WCAG/Storybook rendering, and fixes exposed by those gates.
