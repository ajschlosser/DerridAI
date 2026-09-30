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
- [ ] Preserve route-backed workspace behavior and existing deep links.
- [ ] Add/adjust focused tests before or alongside each behavioral change.

### Phase 1 — Workflow presentation: Setup / Build & review / Publish

Status: **not started**

Goal: correct the conceptual hierarchy without rewriting authoritative workspace state.

- [ ] Add a presentation grouping that maps internal `build` and `review` to one user-facing **Build & review** phase.
- [ ] Update `CorpusBuilderWorkspaceHeader.vue` to render three user-facing phases while still routing to the correct internal workspace.
- [ ] When Build & review is selected:
  - [ ] route to Review if Records are available and the user was already reviewing;
  - [ ] otherwise route to Build;
  - [ ] preserve direct links to explicit `workspace=build` or `workspace=review`.
- [ ] Ensure step completion does not falsely imply automated work and human review must happen sequentially.
- [ ] Add English and Québec French copy.
- [ ] Update workspace unit/characterization tests.

Likely files:
- `web/src/features/corpus-builder/domain/workflowPresentation.ts`
- `web/src/features/corpus-builder/domain/workspace.ts` only if a presentation helper cannot live elsewhere
- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`
- `web/src/components/PdfCorpusBuilder.vue`
- locale modules
- Corpus Builder workspace tests

### Phase 2 — Build plan and setup hierarchy

Status: **not started**

Goal: make setup feel like a prepared plan rather than a long form.

- [ ] Introduce a reusable `CorpusBuildPlan` / equivalent component based on existing `setupSections` and `setupIssues`.
- [ ] Desktop layout: configuration content + sticky Build plan rail.
- [ ] Build plan summarizes:
  - [ ] source identity/media facts;
  - [ ] structure/transcription state;
  - [ ] metadata schema/document fields;
  - [ ] enrichment/provider/model;
  - [ ] Record sizing;
  - [ ] warning/blocker count.
- [ ] Keep a single dominant **Build corpus** action.
- [ ] Collapse/edit sections directly from Build plan.
- [ ] Remove or simplify the duplicate sticky launch/status treatment in `CorpusBuildReadiness.vue`.
- [ ] Rename/demote “Advanced” presentation to “Run settings” or equivalent.
- [ ] Fix the semantic contradiction where Advanced can appear optional while containing a blocking context-safety issue.
- [ ] Ensure media-specific summaries do not leak PDF/page language into audio/image/text sources.
- [ ] Responsive/mobile layout.
- [ ] Storybook states: no source, ready, warning, blocking, long French copy, narrow layout.

Likely files:
- `CorpusSetupWorkspace.vue`
- `CorpusSetupSection.vue`
- `CorpusBuildReadiness.vue`
- `setupState.ts`
- new component(s) under `components/corpus-builder/`

### Phase 3 — Live build workspace

Status: **not started**

Goal: turn the build screen into a live, legible work surface.

- [ ] Recompose `CorpusBuildPrimaryStatus.vue` into:
  - lifecycle headline;
  - current operation;
  - progress;
  - key counts;
  - stage rail;
  - primary controls.
- [ ] Add a high-priority **Review ready Records** state as soon as topology exists.
- [ ] Copy should explicitly state enrichment/build work can continue in the background.
- [ ] Add a restrained activity feed derived from existing authoritative/realtime state where sufficient; do not invent fake events.
- [ ] Keep detailed diagnostics behind **Run details**.
- [ ] Keep warnings/errors visible without duplicating the same message in multiple surfaces.
- [ ] Keep progress semantics honest: coarse cross-stage progress is not an ETA.
- [ ] Reduced-motion and screen-reader behavior remain intact.

### Phase 4 — Persistent run control in Review

Status: **in progress**

Goal: allow researchers to control the build without leaving Review.

- [x] Add **Pause** to `CorpusReviewRunStatus.vue` while the corpus build itself is active.
- [x] Keep **Resume** for resumable states.
- [ ] Keep cancel/settle/provider switching inside expanded details unless it is contextually primary.
- [x] Preserve the existing compact active-state label (“Enriching/Running · percent · model”).
- [x] Wire pause from the Review run control through `PdfCorpusBuilder.vue` to the existing lifecycle pause mutation.
- [x] Add a focused component test proving Pause is available and emits directly from Review.
- [ ] Ensure live updates do not steal keyboard focus.

### Phase 5 — Review command hierarchy and bulk happy paths

Status: **not started**

Goal: reduce control competition and make fast adjudication obvious.

- [ ] Keep queue tabs + issue filter + search as primary review-navigation controls.
- [ ] Promote **Accept N ready Records** when `ready > 0`.
- [ ] Replace native `window.confirm` for this important workflow with the shared accessible dialog/confirmation pattern.
- [ ] Move selection-only bulk commands into a contextual selection bar when selected count > 0.
- [ ] Reduce permanent header density by relocating Record/Metadata/Source view controls closer to the inspected pane where practical.
- [ ] Preserve keyboard shortcuts and announce resulting queue/count changes.
- [ ] When the current queue becomes empty, show a clear completion state and next action.
- [ ] Preserve authoritative human-ownership semantics and mutation queue behavior.

### Phase 6 — Publish simplification and explicit skip-review path

Status: **not started**

Goal: make publication readiness understandable at a glance.

- [ ] Reduce duplicate readiness information between `CorpusPublishWorkspace.vue`, `CorpusFinishWorkspace.vue`, and `CorpusMetadataIssues.vue`.
- [ ] Present three principal readiness groups:
  - [ ] Records;
  - [ ] Required metadata;
  - [ ] Source & validation.
- [ ] Each blocked group gets one primary repair action into the exact review context.
- [ ] Rename/reframe `accept_unreviewed` UI as **Use suggestions as-is & publish** (or final localized equivalent).
- [ ] Confirmation dialog must clearly state:
  - [ ] no human-review claim is created;
  - [ ] suggestion/provenance state remains preserved;
  - [ ] source/text-conservation validation still applies;
  - [ ] publication may be non-conformant/unreviewed where applicable.
- [ ] Published completion surface: publication identity, Record count, review mode/conformance, download, start-new-build.
- [ ] Preserve backend publication gates and cELF assertion authority semantics.

### Phase 7 — Visual polish and “joy”

Status: **not started**

- [ ] Reduce nested card-on-card borders where grouping can be expressed with whitespace and typography.
- [ ] Use accent emphasis primarily for the next useful action/current operation.
- [ ] Add restrained transitions for:
  - [ ] stage completion;
  - [ ] newly available review action;
  - [ ] queue completion;
  - [ ] count changes where motion is not distracting.
- [ ] Disable nonessential motion under `prefers-reduced-motion`.
- [ ] Strengthen source identity so the build visually belongs to the selected work/source rather than a build ID.
- [ ] Keep IDs/hashes/provider internals behind details.
- [ ] Verify dark/high-contrast/forced-colors states.

### Phase 8 — Documentation, Storybook, regression, cleanup

Status: **not started**

- [ ] Update User Guide for the new happy path.
- [ ] Update architecture wording if user-facing phases change while internal route state remains four-part.
- [ ] Update Help Center/page guide copy if it names the old workflow.
- [ ] Add/adjust Storybook stories for all new reusable components/states.
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
