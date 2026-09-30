# Corpus Builder Happy-Path UX — Agent Handoff

Branch: `task/corpus-builder-happy-path-ux`

Related implementation plan: `docs/CORPUS_BUILDER_HAPPY_PATH_UX_PLAN.md`

Draft PR noted in the implementation plan: **#336**

## Handoff purpose

This branch is a substantial UX refactor of Corpus Builder aimed at making the happy path obvious:

> Load a source, accept or adjust a sensible build plan, start processing, then either watch the build or begin reviewing Records as soon as they exist. Pause/resume from Build or Review. Accept ready Records in bulk, adjudicate exceptions, or explicitly publish eligible suggestions as-is without falsely recording human review.

The core implementation is largely in place. The remaining work is primarily integration, validation, conflict resolution against current `master`, and any fixes exposed by CI/E2E/accessibility testing.

## Current repository state

Current integration state:

- branch: `task/corpus-builder-happy-path-ux`
- synchronized with `master` commit: `2560d801300226595455ee2a98054641bdd5a7fa`
- synchronization merge commit: `9d13da310fc36edf8ba8168ea1781adfccfb8c67`
- branch vs current `master` immediately after synchronization: **0 commits behind**
- status: **master reconciliation completed; validation in progress**

The synchronization retained both the Corpus Builder UX work and the overlapping publication-delivery-mode additions to English/Québec French locale dictionaries, generated English fallbacks, and the User Guide.

## Non-negotiable architectural constraints

Do not simplify this work by weakening DerridAI's provenance or authority model.

1. Build and Review are concurrent user activities once Record topology exists.
2. Internally, route-backed workspaces remain `setup | build | review | publish`; the UI groups Build and Review into one researcher-facing phase.
3. Human confirmation remains an authority event. Do not relabel autonomous/model-selected suggestions as human-confirmed.
4. The suggestions-as-is publication path must keep using the existing backend `accept_unreviewed` semantics.
5. Source/text-conservation validation is never skipped.
6. Media-specific behavior must remain media-specific. Do not leak PDF/page assumptions into text/audio/image workflows.
7. Existing durable lifecycle state, deep links, Back/Forward behavior, and build resumption must remain intact.
8. Realtime UI updates must not become authoritative state or steal focus.
9. English and Québec French must remain in key/placeholder parity.
10. WCAG 2.2 AA, keyboard navigation, reduced motion, forced colors/high contrast, and long-string behavior are release requirements.

## What has been implemented

### 1. Researcher-facing workflow is now three phases

The top-level header presents:

- **Setup**
- **Build & review**
- **Publish**

Build and Review remain distinct internal workspaces and deep-link targets. The grouped phase includes a small Build/Review sub-navigation.

Key file:
- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`

### 2. Setup is organized around a Build plan

Setup now uses a two-column desktop layout:

- configuration sections in the main column;
- sticky **Build plan** rail beside them.

The Build plan summarizes:

- source identity/media facts;
- structure state where relevant;
- metadata schema;
- enrichment mode/provider/model;
- Record sizing;
- blocker/warning count.

Each summary fact can open the corresponding setup section. The old bottom sticky launch/readiness treatment has been replaced by this plan.

A blocking issue makes **Fix** the dominant action. When setup is valid, **Build record set** is dominant.

The old user-facing **Advanced** label is now **Run settings**. A blocking context/run-setting issue is no longer presented as merely optional.

Key files:
- `web/src/components/corpus-builder/CorpusSetupWorkspace.vue`
- `web/src/components/CorpusBuildReadiness.vue`
- `web/src/features/corpus-builder/domain/setupState.ts`
- `web/src/components/CorpusBuildReadiness.stories.ts`

### 3. Build makes concurrent Review explicit

The live Build surface now promotes a primary **Review N ready Records** action as soon as ready Records exist.

It explicitly tells the researcher that review can begin while automated work continues.

The live Build surface also includes a compact activity strip backed only by persisted `build_events`; it does not invent events or ETAs.

Diagnostics/audit material is presented under **Run details** rather than competing with the primary build task.

Key files:
- `web/src/components/corpus-builder/CorpusBuildPrimaryStatus.vue`
- `web/src/components/corpus-builder/CorpusBuildWorkspace.vue`
- `web/src/components/corpus-builder/CorpusBuildActivity.vue`
- `web/src/components/corpus-builder/CorpusBuildActivity.stories.ts`

### 4. Pause/resume is available while reviewing

An active corpus build can now be paused directly from Review. Resume remains available for resumable states.

Important distinction: this Pause control applies to the corpus build lifecycle. Auxiliary metadata operations are not falsely represented as sharing identical pause semantics.

Key file:
- `web/src/components/corpus-builder/CorpusReviewRunStatus.vue`

Wiring:
- `web/src/components/PdfCorpusBuilder.vue`

### 5. Review command hierarchy is less cluttered

The Review toolbar now:

- keeps queue tabs/filter/search as primary navigation;
- shows **Accept clean (N)** only when ready Records actually exist;
- uses an accessible shared dialog instead of `window.confirm`;
- explains that bulk acceptance records human review decisions;
- shows selected-record edit/reject actions in a contextual selection bar;
- leaves non-selection operations behind **More actions**.

The Record/Metadata/Source view switch remains in the consolidated review header. The implementation plan deliberately records this as a conscious choice: moving it elsewhere would duplicate inspector navigation and fragment an existing accessible view contract.

Key files:
- `web/src/components/corpus-builder/CorpusReviewToolbar.vue`
- `web/src/components/corpus-builder/CorpusReviewHeader.vue`
- `web/src/features/corpus-builder/composables/useCorpusReviewDecisions.ts`

### 6. Publish is simplified

Publish now emphasizes three readiness dimensions:

- Records;
- Required metadata;
- Source & validation.

Duplicate metadata-issue presentation was removed, and nested card treatment was flattened.

The skip-review action is now labeled:

**Use suggestions as-is & publish…**

The confirmation dialog explicitly states that:

- no human-review claim is created;
- derivation/evaluation/authority/confidence/evidence are preserved;
- source/text-fidelity validation is still mandatory;
- cELF conformance is evaluated separately and blockers may remain.

After publication, pre-publication readiness counters are hidden and the publication snapshot becomes the completion state.

Key files:
- `web/src/components/corpus-builder/CorpusPublishWorkspace.vue`
- `web/src/components/CorpusFinishWorkspace.vue`
- `web/src/components/CorpusUnreviewedPublishDialog.vue`

No backend publication contract was intentionally changed.

### 7. Documentation and Help were updated

Updated:

- `docs/ARCHITECTURE.md`
- `docs/USER_GUIDE.md`
- Corpus Builder Help Center page-guide copy in locale dictionaries
- `docs/CORPUS_BUILDER_HAPPY_PATH_UX_PLAN.md`

The architecture documentation now explains the distinction between:

- three user-facing phases; and
- four internal route-backed workspaces.

## Main files touched

Primary implementation:

- `web/src/components/PdfCorpusBuilder.vue`
- `web/src/components/CorpusBuildReadiness.vue`
- `web/src/components/CorpusFinishWorkspace.vue`
- `web/src/components/CorpusUnreviewedPublishDialog.vue`
- `web/src/components/corpus-builder/CorpusBuildActivity.vue`
- `web/src/components/corpus-builder/CorpusBuildPrimaryStatus.vue`
- `web/src/components/corpus-builder/CorpusBuildWorkspace.vue`
- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`
- `web/src/components/corpus-builder/CorpusPublishWorkspace.vue`
- `web/src/components/corpus-builder/CorpusReviewRecordQueue.vue`
- `web/src/components/corpus-builder/CorpusReviewRunStatus.vue`
- `web/src/components/corpus-builder/CorpusReviewToolbar.vue`
- `web/src/components/corpus-builder/CorpusSetupWorkspace.vue`
- `web/src/features/corpus-builder/composables/useCorpusReviewDecisions.ts`
- `web/src/features/corpus-builder/domain/setupState.ts`

Localization:

- `api/app/locales/en_us.py`
- `api/app/locales/fr_ca.py`
- `web/src/i18n/enUsDefaults.json`

Tests/stories:

- `web/src/components/CorpusBuildReadiness.stories.ts`
- `web/src/components/corpus-builder/CorpusBuildActivity.stories.ts`
- `web/tests/frontend/corpus-builder-build-review.test.ts`
- `web/tests/frontend/corpus-builder-setup.test.ts`
- `web/tests/frontend/corpus-builder-workspaces.test.ts`
- `web/tests/frontend/ui-notice-stack.test.ts`
- `web/tests/e2e/corpus-builder-workflows.spec.ts`

## Focused coverage added or changed

Coverage was added for, among other things:

- three-phase header presentation;
- Build/Review in-phase navigation;
- pausing an active corpus build from Review;
- Review-ready CTA during active enrichment;
- Build activity strip;
- blocking Run settings state;
- Build-plan direct section editing;
- accessible bulk ready-Record confirmation;
- contextual selected-Record action bar;
- concise published completion state;
- suggestions-as-is authority/source-gate language.

Storybook coverage now includes:

- ready Build plan;
- no-source Build plan;
- warning/blocking Build plan;
- Québec French long-string stress;
- narrow/mobile Build plan;
- live build activity strip.

## Remaining work

Treat the implementation plan as authoritative for remaining checklist items, but the highest-priority work is:

### 1. Current-master reconciliation — completed

Current `master` was merged into this branch at `9d13da310fc36edf8ba8168ea1781adfccfb8c67`. The branch was 0 commits behind immediately after that merge. The overlapping locale/fallback/User Guide changes were merged semantically rather than choosing one side wholesale.

### 2. Run formatting and static checks

The handoff branch has not been certified by a local/full validation pass in this session.

Run the repository-prescribed commands for:

- Prettier/formatting;
- ESLint;
- TypeScript/vue typecheck;
- locale parity / placeholder parity;
- Storybook/static checks if part of CI.

Do not assume connector commits are formatted exactly as repository tooling expects.

### 3. Run focused frontend tests

At minimum, exercise:

- `web/tests/frontend/corpus-builder-build-review.test.ts`
- `web/tests/frontend/corpus-builder-setup.test.ts`
- `web/tests/frontend/corpus-builder-workspaces.test.ts`
- `web/tests/frontend/ui-notice-stack.test.ts`

Then run the full frontend test suite.

### 4. Run representative E2E/WCAG checks

Critical scenarios:

1. PDF default happy path.
2. Text/non-paginated source.
3. Audio or image source where available.
4. Build → Review while enrichment continues.
5. Pause from Build.
6. Pause from Review.
7. Resume after navigation/reload.
8. Accept clean Records in bulk.
9. Queue reaches zero.
10. Reviewed Publish path.
11. Suggestions-as-is Publish path.
12. Published completion/download state.

Accessibility checks:

- keyboard-only;
- dialog focus return;
- screen-reader labels/live regions;
- 320 px/reflow;
- long Québec French strings;
- reduced motion;
- dark mode;
- high contrast;
- forced colors.

### 5. Validate Storybook after synchronization

Check the Build-plan and activity stories in both themes and at narrow widths. The new Build plan uses dense `dl` summary markup and direct Edit controls; ensure the semantic structure and focus order remain sensible after formatting/tooling.

### 6. Review visual hierarchy after real rendering

The implementation was performed from source/component architecture rather than a live browser rendering in this handoff session. Inspect:

- Setup spacing at desktop widths;
- sticky Build-plan behavior under the global top bar;
- transition from two-column to one-column layout;
- Build activity overflow;
- Review header density with long localized strings;
- selection bar wrapping;
- Publish spacing after nested-card flattening.

If the rendering reveals issues, fix composition/CSS without reopening the underlying workflow architecture unless a real usability problem requires it.

## Known implementation decisions that should not be casually reversed

### Keep Build and Review internally separate

The product presentation is grouped, but the route values remain separate. This preserves durable deep links and lets a researcher intentionally open either the live build monitor or review workspace.

### Keep autonomous publication semantically autonomous

The new label is intentionally not “Accept all.” The publication shortcut must not imply that the user reviewed or confirmed values they did not adjudicate.

### Do not manufacture an ETA

The existing progress is coarse stage progress. The activity strip exposes real stage transitions only.

### Do not turn every warning into a blocker

Setup warnings and blockers remain distinct. Only actual blockers suppress Build.

### Do not make Run settings globally mandatory

Run settings are normally optional. They become visibly incomplete only when a contained setting genuinely blocks execution.

### Do not restore duplicate Publish issue panels

The new Publish design intentionally points repair actions back into Review instead of repeating the same metadata issue browser inside Publish.

## Suggested next-agent execution order

1. Fetch latest `master` and inspect the 28 commits added since this branch diverged.
2. Synchronize `task/corpus-builder-happy-path-ux` with current master.
3. Update this handoff and the implementation plan with any conflict-resolution decisions.
4. Run formatter/lint/typecheck/i18n checks.
5. Run focused Corpus Builder unit/component tests.
6. Fix failures and commit a checkpoint.
7. Run full frontend tests/build.
8. Run representative E2E/WCAG/Storybook checks.
9. Fix visual/accessibility regressions.
10. Update the implementation plan to completed status only when the validation checklist is actually satisfied.
11. Push each coherent checkpoint.
12. Update draft PR #336 with final validation notes and mark it ready only after CI is clean.

## Commit discipline

Continue the pattern requested for this branch:

- commit coherent checkpoints rather than one final mega-commit;
- update `docs/CORPUS_BUILDER_HAPPY_PATH_UX_PLAN.md` as progress changes;
- update this handoff if architecture or remaining-risk assumptions change materially;
- push after meaningful checkpoints so work is not stranded locally.

## Final acceptance target

A researcher with no prior Corpus Builder knowledge should be able to:

1. add/select a supported source;
2. understand the proposed Build plan without opening every setting;
3. start the build;
4. understand live progress without reading telemetry;
5. begin Review while automated work continues;
6. pause/resume from where they are working;
7. accept ready Records quickly while preserving human-authority semantics;
8. resolve only the exceptions that need attention;
9. choose between reviewed publication and the explicit suggestions-as-is path;
10. publish/download an auditable immutable artifact.

The feature is not finished until that flow also holds under keyboard-only use, Québec French, narrow layouts, non-PDF media, reduced motion, dark/high-contrast/forced-colors modes, and current CI.
