# runtime.js decomposition: hand-off

## Session 6 status (Tools route boundary)

Corpus Builder is already owned by `PdfWorkspaceView` through the Vue `PdfCorpusBuilder` component. The next safe
surface was therefore the Tools route boundary: `/pdf` now resolves directly to `PdfWorkspaceView` and `/databases`
resolves directly to `VectorStoresView`, instead of passing through the compatibility `ToolsView` wrapper with a
`RuntimeSurface` fallback. The wrapper was unused after both concrete routes were native and has been removed. The PDF
Explorer branch remains intentionally runtime-backed inside its Vue-owned workspace; its DOM baseline and public runtime
exports are unchanged.

The focused route-boundary regression test is `web/tests/frontend/tools-route-boundary.test.ts`. Remaining runtime
compatibility hosts are the dashboard, PDF Explorer branch, response cache, and dead legacy view files that are not
reachable from the current router; do not remove the shared runtime host until those live branches are migrated.

Temporary file. **Delete it before the effort ends** (last commit of the last PR). It exists so another agent (Codex, Copilot,
another Claude) can continue if the current one stops.

## Session 7 status (branch `claude/runtime-refactor-20`)

Reviewed Copilot's session-6 work (through PR #93, and then #95/#96/#97/#98 which merged during this session) against
the actual code, not just this file's claims -- verified: typecheck, lint, unit tests, the 131-scenario DOM baseline,
the full e2e suite, and the backend pytest suite all pass at each point. Confirmed no overclaiming; `DashboardView.vue`
and the PDF Explorer surface still delegate their markup entirely to the legacy HTML-string renderers (that is accurate
to what "Vue-owned route/surface boundary" means here -- routing ownership, not a markup rewrite yet). `ResponseCacheView`
was further along: real `<script setup>` data-fetching, but its markup was still a hand-built HTML string set via
`v-html`, byte-identical to the old `domain/responseCacheRenderer.ts` output.

**Found and fixed a real gap in the baseline harness**, in its own commit before touching any view: `rawMarkup()` never
actually normalized insignificant HTML whitespace or Vue's `<!---->` v-if placeholder comments, despite this file's
own "Section B" note (written by an earlier session) claiming it already did. This meant any move from a hand-indented
template-literal renderer to a real Vue template would fail the baseline on incidental formatting alone, never on real
content -- a structural blocker for finishing section B as written. Fixed by collapsing whitespace-only runs between
tags and stripping empty comments; re-recorded every affected snapshot (117 across two commits, the second catching
files PR #96/#97/#98 touched independently) and confirmed for **every one** that the tag-stripped visible text is
byte-identical before and after. See the updated "DOM baseline" section below for the exact rule.

**Then replaced `ResponseCacheView.vue`'s `v-html` string with a real template** (same class names, ids, element order;
`AppIcon` in place of the `icon()` string helper), verified against the now-fixed baseline (4 scenarios, unchanged) plus
the full suites. This is response cache **done** for section B -- no more HTML-string renderer, no more `v-html`.
`domain/responseCacheRenderer.ts` and its `runtime.js` wiring are now dead code (nothing calls `renderResponseCache`);
left in place deliberately, since `runtime.js` is heavily in flux from PR #98's in-parallel work and removing it now
would raise conflict risk for no behavioral benefit -- next session should confirm it is still dead and remove it then.

**Conflict avoidance:** before starting, checked all open PRs and recently-pushed branches (`gh pr list`, `git branch -r
--sort=-committerdate`). PR #96 (Copilot, Corpus Builder / record-review persistence) touched only `api/app/corpus_builder.py`
and friends plus Corpus Builder Vue components -- no overlap. PR #97 (language policy) touched only `LanguagesView.vue` and
`jobs.py` -- no overlap. **PR #98** (`claude/records-page-ui-refinements-fc519c`, moved the subset dialog to Vue) touched
`runtime.js`, `recordDialogs.ts`, `evidenceSelection.ts`, and `operationDock.ts` heavily -- all files this session's
predecessor had just finished extracting. Deliberately avoided all four for this session's work. All three PRs merged to
master mid-session; merged master in twice (see commits), resolving DOM-baseline-snapshot conflicts by re-normalizing the
`theirs` content rather than picking a side, and re-verified the full suite both times.

## Session 8 status (branch `claude/runtime-refactor-21`)

Removed the dead `responseCacheRenderer` wiring left from session 7 (confirmed still unreachable, `runtime.js` was
quiet by the time this session started). Then took on the dashboard, the larger of the two remaining legacy views.

**`DashboardView.vue` is now a real Vue component**, not a host for an HTML-string renderer: same markup, ids, classes
and behavior as `domain/dashboardRenderer.ts`'s old `renderDashboard`, built as a real template. It calls the SAME
underlying domain functions (`dashboardTotals`, `dashboardRecordPreview`, `pieShareSeries`, `workInsightMetrics`,
`dashboardMetricBody`, ...) via new `runtime.js` exports, rather than reimplementing any of that logic -- only the
markup-building and DOM-wiring layer changed. The metric-carousel chart body stays `v-html`'d (it is already a pure
markup generator, `dashboardMetricBody`, the same pattern `AppIcon` itself uses for SVGs); every other element is a
real template node with real bindings.

**Two hazards found and fixed, both real, both would have caused live bugs if missed:**
1. `renderView()` still dispatched to the legacy `renderDashboard` for `state.view==="home"`, and two other call sites
   (in `appLifecycle.ts`, `workDialogs.ts`) called it directly after provider warm-up / work-metadata actions. Left in
   place, any of these firing while `DashboardView.vue` is mounted would have overwritten Vue's own `#main` with the
   old HTML string -- exactly the class of bug the response-cache session already worked around by removing that
   renderer's dispatch. Removed all three call sites; the two that existed to keep the dashboard's own content fresh
   after an action now dispatch a `derridai:dashboard-refresh` window event instead, which the new view listens for --
   matching the `derridai:navigate-native` / `derridai:pdf-builder` bridge pattern already used elsewhere for exactly
   this legacy-code-talks-to-a-specific-Vue-component situation.
2. The old renderer was re-invoked fresh on every navigation to the dashboard, so it always reflected the latest
   corpus/job state. A Vue component that mounts once does not get that for free -- the dashboard would have gone
   stale after a file import or job progress while it stayed the open view (caught by the `home-with-jobs` /
   `jobs-*` baseline scenarios, which import a file first: works count and job cards showed 0/stale until this was
   added). Fixed with a `watch` on `corpusState.version`/`activeFileId` and the jobs store's `version`, the same
   pattern `useRecordsWorkspace` already established for the same reason.

**Small pre-existing issues surfaced by using the runtime's real types/exports directly, fixed as pure fixes (no
behavior change), each because it broke this page's own baseline until fixed:**
- `navigation.ts`'s `navigateTo()` had no type annotation on its options parameter; TS inferred `fileId`/`index` as
  exactly `null` from their default values. Harmless while every caller went through the untyped `Fn` dependency
  alias; broke as soon as something called the real exported function directly. Type-only fix.
- `AppIcon.vue` had no "chart" icon; added it, copied verbatim from `domain/html.ts`'s `icon()`.
- **Found but deliberately not touched:** `AppIcon.vue`'s "gear" path has drifted one coordinate from
  `domain/html.ts`'s "gear" (`l.1.1` vs `l.1-.1`), and that drift is already baked into two other currently-passing
  baseline snapshots (`SearchView`, `ResearchComposer`, both already use `AppIcon name="gear"`). Fixing `AppIcon`
  would break those two unrelated scenarios. Used `domain/html.ts`'s `icon()` directly (via `v-html`) for the
  dashboard's three gear icons instead, matching the dashboard's own existing correct baseline. Whoever eventually
  reconciles this should fix `AppIcon.vue`'s gear path AND re-record those two snapshots together, in one commit.
- A Vue `:style` binding (even given a plain string) always goes through Vue's own CSSStyleDeclaration-based patching,
  which normalizes serialization (`width:0%` becomes `width: 0%;`) -- there is no way to get byte-identical `style=`
  output from any `:style` binding. This is not new: the existing baseline already had both formats coexisting
  (`<col style="width: 240px;">` from a browser/JS-set style next to `<em style="width:100%">` from a hand-built HTML
  string). Accepted this for the one corpus-builds progress-bar span, re-recorded that one snapshot, and confirmed the
  only diff was this formatting.

**A real mistake made and caught this session, noted here so it is not repeated:** a `npx prettier --write` call
during cleanup included `runtime.js` in its file list by accident, fully reformatting the entire file (a 4,700-line
diff, all noise). Caught before committing by noticing the line count jump; reverted with `git checkout HEAD --
runtime.js` and the small logical edits (the export additions, the three dispatch removals) were redone by hand with
targeted string edits, never touching Prettier on that file. **`runtime.js` must never appear in a `prettier --write`
file list, even in a batch command with other files that should be formatted.**

`runtime.js`: 2,399 lines (barely moved -- this tranche only added exports and removed dead dispatch code; the
dashboard's own ~650 lines of markup-building logic left the file with the earlier `dashboardRenderer.ts` extraction,
not this session).

**Conflict avoidance:** checked `gh pr list` and `git branch -r --sort=-committerdate` before starting; PR #100 (Corpus
Builder cleanup) and the language-dictionary-ux branch had no overlap with anything touched here. Master moved twice
during this session (through PR #101, then PR #102/#103); merged both times, no conflicts either time, full suite
re-verified both times.

## Session 9 status (branch `claude/runtime-refactor-22`)

Converted the last legacy view, PDF Explorer. **`PdfExplorerSurface.vue` is now a real Vue component**, same markup,
ids, classes and behavior as `domain/pdfExplorerRenderer.ts`'s old `renderPdf`, calling the same underlying domain
functions (`linkedPdfRows`, `allLinkedRowsForLoadedPdf`, `renderPdfCanvas`, `extractPdfPageSmart`, `loadPdfMetadata`,
`persistCurrentPdfAsset`, ...) via new `runtime.js` exports rather than reimplementing them. Removed the `renderPdf`
dispatch from `renderView()` and its two remaining direct-call sites (`jobDialogs.ts`, `pdfLinking.ts`), replaced by
the same `window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"))` bridge pattern the dashboard
established, and removed the now-dead `nextTick`/`runtime.renderView()` call from `PdfWorkspaceView.vue`'s
`setMode()` (the surface now owns its own render on mount and refresh).

**A new, generalizable reactivity gotcha found here (did not come up in the dashboard, which never read `state.pdf.*`
inside a `computed`):** `runtime.state` is a plain, non-reactive object except for the specific fields Pinia binds.
A `computed()` whose getter reads `state.pdf.*` directly registers no tracked dependency and caches its first-ever
value forever -- it does not re-run even when something else re-renders the component. This silently broke "Extract
current page": the text was set into `state.pdf.text` correctly, but the `.pdftext` div kept showing the "no text
extracted" fallback. A plain `{{ state.pdf.text }}` template read would have worked (no caching), and so does a ref
explicitly reassigned inside `refresh()` -- only a `computed()` reading the raw field is broken. Fixed by mirroring
`state.pdf.text`/`search`/`relatedSearch` into plain `ref()`s set every `refresh()`, with setter functions that write
both the ref and `state.pdf.*` (some legacy code, e.g. `persistCurrentPdfAsset`, still reads `state.pdf.*` directly
for IndexedDB persistence, so the write-through has to stay). **Any future runtime-to-Vue conversion that wants a
`computed()` over `state.*` should mirror the field into a ref first; do not read `state.*` inside a `computed`
getter.**

**A genuine legacy race condition found and fixed as a disclosed, checked-first bug fix (not a redesign):**
`enhanceCollapsibles(root)` (adds the collapse/expand affordance to over-tall cards) was, in the legacy code, only
ever called from `renderView()`'s `requestAnimationFrame`-deferred hook -- never from the in-page action handlers
(rotate, extract, next-page) that called `renderPdf()` directly and skipped it. Whether a tall card got the
affordance therefore depended on exactly when that rAF fired relative to an unrelated, not-awaited canvas-paint
promise -- confirmed non-deterministic by testing (the same baseline-recording helper produced flipping results
across otherwise-identical runs). Checked the legacy source first per policy (nothing else reads or depends on the
inconsistency) and made it deterministic: `enhanceCollapsibles` now runs unconditionally on every `refresh()`. This
changed three snapshots (`pdf-explorer-extract`, `pdf-explorer-next-page`, `pdf-explorer-rotate`) to consistently show
the affordance; re-recorded after confirming the only diffs were the added `data-collapsible-ready`/toggle markup.

**Other fixes, each because it broke this page's own baseline until fixed, no behavior change beyond formatting/UI
consistency:**
- `pdfSearch`/`pdfRelatedSearch`/`pdfRecordSearch` switched from `v-model` to `:value.attr` + manual `@input`
  (same technique the dashboard's search box already used) -- Vue's property-based `v-model` binding does not always
  produce a literal `value=""` HTML attribute for an initially empty string.
- The record-search autocomplete's "No matching records" empty state rendered even when the dropdown was closed
  (`suggestions` was `[]` for both "closed" and "open, zero matches"); wrapped the whole suggestions/empty block in
  `<template v-if="suggestionsOpen">`. This was a real, if minor, logic bug in the new component, caught before
  ship by the a11y/keyboard e2e coverage, not present in the legacy renderer.
- Multiple `v-text`/no-whitespace-continuation fixes for stray spaces Vue's template whitespace-condensing mode
  introduces around multi-line button/paragraph text (same class of fix as sessions 7-8).
- `AppIcon.vue`'s "copy" and "close" paths have also drifted from `domain/html.ts` (in addition to the already-known
  "gear" drift from session 8); other passing baseline scenarios depend on the current drifted values, so `AppIcon`
  was again left alone and the exact legacy SVG markup for "gear"/"copy"/"close" was inlined locally in this
  component instead (same reasoning as session 8's gear fix). Whoever eventually reconciles `AppIcon.vue` with
  `domain/html.ts` should fix all three paths and re-record every affected snapshot together, in one commit.
- `pdf-explorer-link-page`'s `class="btn small "` / `class="copy-record-mini "` (trailing space from legacy's string
  interpolation) versus Vue's `:class="{soft: cond}"` cleanly omitting the class when false: accepted as the same
  harmless formatting difference already established for `:style` output in session 8, re-recorded that one snapshot
  after confirming it was the only diff.
- I initially wrapped the "no text extracted" hint in `i18n.t("pdf.no_text_hint", ...)`, but the legacy renderer
  never localized this string (`domain/pdfExplorerRenderer.ts:169` is a hardcoded literal) -- adding a new key here
  would have been scope creep beyond decomposition, and `tests/test_locale_dictionaries.py` caught the missing key
  immediately. Reverted to the same hardcoded literal, matching legacy exactly.
- New buttons carrying `data-copy-row-key`/`data-cite-row-key`/`data-toggle-workspace-evidence` need no `@click`
  handler of their own: `runtime.js` already has one global delegated `document.addEventListener("click", ...)`
  handler for these attributes (not per-view). Adding a component-local handler would double-fire.

`runtime.js`: still 2,399 lines (this tranche only added exports and removed the `renderPdf` dispatch/lambdas; the
~500 lines of PDF Explorer markup-building logic left the file earlier with the `pdfExplorerRenderer.ts` extraction).

**Every remaining legacy view is now gone.** The next session should do the "when the last legacy view is gone"
cleanup listed in section B below (delete `RuntimeSurface.vue` if it has zero remaining consumers, `translateLegacyDom`,
the collapsible `MutationObserver`, `legacyCompat.js`, unused `runtimeBridge.ts` exports, shrink the `export {}` block)
before starting anything else, since it is now unblocked and was deferred at every one of the last several sessions.

**Conflict avoidance and branch note:** checked `gh pr list`/branches before continuing from the previous session's
summary; found PR #107 (the branch this work continued on, `claude/runtime-refactor-21`) and PR #104 (Corpus Builder,
`ajschlosser-record-review-enrichment`) had both already merged into `master` mid-session, so `claude/runtime-refactor-21`
had zero unique commits left. Re-based this tranche onto fresh `master` as a new branch, `claude/runtime-refactor-22`,
rather than building further on an already-merged branch; verified none of the touched files (`runtime.js`,
`jobDialogs.ts`, `pdfLinking.ts`, `PdfWorkspaceView.vue`, `PdfExplorerSurface.vue`) had changed on `master` beyond
what this branch already had before re-pointing. Full verification suite (typecheck, lint, 508 unit tests, production
build, Storybook build, 131-scenario baseline, 287-test e2e suite, 429 backend tests) re-run clean against `master`
before commit.

## Session 10 status (branch `claude/runtime-refactor-23`)

PR #108 (session 9, PDF Explorer) merged. Followed up on session 9's own flagged correction: session 9 said "no
legacy views remain," which is true for *routed* views, but a closer look found `RuntimeSurface.vue` still had three
listed consumers (`CorpusView.vue`, `SystemView.vue`, `ResearchView.vue`'s `v-if="!isNativeResearch"` branch).
Verified all three were actually dead before touching anything:

- `CorpusView.vue` and `SystemView.vue` have zero references anywhere (`router/index.ts`, every `.vue`/`.ts` under
  `src`, and `tests/`) -- they were never wired into the router at all, presumably leftover from an earlier
  refactoring pass. Deleted both.
- `ResearchView.vue`'s `isNativeResearch` computed checks `route.name === "rag"`, and `"rag"` is the *only* route
  `router/index.ts` ever mounts `ResearchView` under, so `isNativeResearch` is always `true` and the
  `v-if="!isNativeResearch"` / `v-else` split always takes the `v-else` branch. Removed the dead `<RuntimeSurface
  v-if="!isNativeResearch" />` line and made the `<main>` unconditional; left `isNativeResearch` and its other
  (script-level) guards alone -- collapsing every one of those would be a larger refactor than this cleanup pass
  warrants, and they are harmless no-ops as written.
- With those three gone, `RuntimeSurface.vue` and `RuntimeSurface.stories.ts` had zero remaining consumers; deleted
  both. Fixed one stale comment in `runtime.js`'s `bootstrapRuntime` that still referred to "RuntimeSurface will
  render when mounted" (the mounted Vue view now owns `#main` and its own render directly).

**Deliberately not done, flagged for whoever picks this up next:** `legacyCompat.js`/`translateLegacyDom` and the
collapsible-card `enhanceCollapsibles`/`decorateDisabledControls` trio are **not** dead, even though `RuntimeSurface`
is gone. `renderView()` (which calls all three) is still invoked from roughly 20 call sites across `pdfLinking.ts`,
`appLifecycle.ts`, `workDialogs.ts`, `recordDialogs.ts`, `jobDialogs.ts`, `navigation.ts`, and `stores/i18n.ts` --
not to render a legacy view anymore (it always returns `null` now), but as a generic "an action just happened,
refresh `#main`'s decorations" hook that the now-Vue-owned dashboard/PDF-Explorer/response-cache pages still rely on
for their own post-action UI refresh (see the `derridai:dashboard-refresh` / `derridai:pdf-explorer-refresh` event
bridges those views listen for -- `renderView()` and those bridges are two different mechanisms doing adjacent jobs).
Removing `legacyCompat.js` requires auditing each of those ~20 sites to confirm nothing still needs
`enhanceCollapsibles`/`decorateDisabledControls`/`translateLegacyDom` run against the current `#main`, which is a
real, mechanical, but nontrivial task on its own -- treat it as the next self-contained unit of work, not a quick
follow-on to this session's file deletions.

Full verification suite re-run clean after the deletions: typecheck, lint, 520 unit tests (up from 508 -- unrelated
tests landed on `master` via other merges since session 9), production build, Storybook build, 131-scenario baseline,
287-test e2e suite, 429 backend tests.

**Conflict avoidance and branch note:** `master` had moved (PR #108 merge plus whatever else landed); re-based onto
fresh `master` as `claude/runtime-refactor-23` rather than continuing on a now-merged branch, same pattern as
session 9.

## Session 11 status (branch `claude/runtime-refactor-24`) -- `legacyCompat.js` audit concluded: keep it

Finished the audit flagged in section B / session 10. **Conclusion: `legacyCompat.js`/`translateLegacyDom` cannot be
deleted; do not attempt this again without re-reading this note.**

`legacyCompat.js` is not one thing -- most of its exports (`syncColorScheme`, `wireAppearanceMedia`, `applyUiTheme`,
`applyAppearance`, `setTranslationDictionary`, `tr`, `trf`) are core, actively-used theme/i18n plumbing, unrelated to
legacy view rendering; only `translateLegacyDom` (plus its private helpers `translateExactUiValue`/
`translateDynamicUiValue`) was ever a candidate for removal, and even that piece is still load-bearing. It exists to
translate text in any `v-html`'d markup-generator output that was not itself produced through `tr()`/`i18n.t()` --
which still exists: `DashboardView.vue`'s metric carousel (`dashboardMetricBody` → `dashboardPieChart`/`lineChart` in
`recordPresenters.ts`/`dashboardCharts.ts`) is `v-html`-bound and none of the three Vue-owned former-legacy views
(`DashboardView.vue`, `PdfExplorerSurface.vue`, `ResponseCacheView.vue`) call `translateLegacyDom` themselves --
French-locale translation of that markup, to the extent it happens at all, depends entirely on one of the ~20
`renderView()` call sites elsewhere firing while that view is mounted. Deleting `legacyCompat.js` now would silently
regress French-locale translation for that markup with no test coverage that would catch it (the baseline pins
`en-US`; no French-locale dashboard-carousel scenario exists).

**A real, separate i18n bug found along the way, not fixed here (out of this session's scope, logged instead):**
`dashboardPieChart`/`lineChart`/`multiLineChart`'s empty-state text -- `` `${esc(title)} · no data yet` `` -- is a
hardcoded English literal, never run through `tr()`, in four places across `dashboardCharts.ts` and
`recordPresenters.ts`. It cannot pick up `translateDynamicUiValue`'s exact-match path either, since the composed
string (title + " · no data yet") never matches a fixed dictionary value. Fixing it means threading `state`/`tr`
through these currently-pure chart-rendering functions (`multiLineChart`, `lineChart`, `dashboardPieChart`) and every
call site -- a real but self-contained follow-up, not attempted here to avoid scope creep on an audit task.

No code changed in this session beyond this investigation; nothing to re-verify or commit for the audit itself.

## Corpus Builder monolith: initial scope against `SPECIFICATION.md` (no code changed yet -- see below)

`api/app/corpus_builder.py` is 8,105 lines, almost all of it one class, `PdfCorpusBuildManager` (~6,800 lines,
~200 methods: segmentation, boundary detection, metadata assessment, review-state decoration, patch/merge/publish,
editorial memory, checkpoints, second-opinions, LLM activity tracking). `web/src/components/PdfCorpusBuilder.vue`
(8,186 lines) is the other largest file in the repo. Both are far larger than any other file and are the natural
next monolith-decomposition target once the runtime-refactor work (this branch line) is done.

**The domain model is already substantively spec-aligned**, which is the good news: `record_id` (197 uses),
per-field assertion dicts with `status`/`method`/`confidence`/`reason` keys (matching the spec's FieldAssertion
shape almost exactly), and an integer `record_revision` counter that increments on authoritative-text and
human-touch changes (matching the spec's RecordRevision concept, though not its full recommended shape --
`record_revision` is a bare counter, not an object with its own actor/time/reason/parent-revision fields; those
appear to live in a separate `metadata_decisions`/undo-history structure instead. Not yet confirmed whether every
revision-worthy change is captured there.).

**Two naming deviations from the spec's own vocabulary found, both wide-reaching enough that renaming is a real
decision, not a typo fix:**
- Spec's assertion-status vocabulary is `deterministic`, `model_inferred`, `human_confirmed`, `human_override`,
  `unresolved`, `invalid`, `confirmed_absent`. The codebase uses `deterministic`, `human_confirmed`,
  `human_override`, `unresolved`, `invalid` -- matching -- but `llm_inferred` where the spec says `model_inferred`
  (27 occurrences in `corpus_builder.py` alone), and `human_confirmed_absent` where the spec says `confirmed_absent`
  (used in `autonomous.py`, `enrichment_cycles.py`, `corpus_builder.py`, and at least 6 frontend files:
  `pdfCorpus.ts`, `CorpusFieldOwnershipBadge.vue` and its story, `CorpusEnrichmentChanges.vue`,
  `CorpusMetadataFieldEditor.stories.ts`, `CorpusRecordFocusReview.stories.ts`,
  `CorpusMetadataResolutionPanel.stories.ts`).
- These values are very likely persisted in existing build data (SQLite/on-disk manifests), not just used
  in-memory. A rename touches backend, frontend, and stored state -- exactly the kind of change AGENTS.md says to
  version and migrate deliberately, not do as a drive-by rename alongside a decomposition. **Decision needed from
  the owner: rename to match the spec's exact vocabulary (with a migration for existing persisted builds), or treat
  `llm_inferred`/`human_confirmed_absent` as an intentional, documented profile extension of the spec's base
  vocabulary and leave them as-is?** The spec does say "Profiles MAY add others" for statuses, so leaving them is
  defensible, but the fact that `llm_inferred` has an exact spec synonym (`model_inferred`) rather than being a
  genuinely new status suggests it was written before the spec settled on that term, not a deliberate profile
  extension.

## Session 12 status (branch `claude/runtime-refactor-25`) -- vocabulary rename done; `PdfCorpusBuildManager` decomposition plan

### Part 1: renamed `llm_inferred` -> `model_inferred`, `human_confirmed_absent` -> `confirmed_absent` (done, committed)

Mechanical rename across 16 source files (`corpus_builder.py`, `autonomous.py`, `enrichment_cycles.py`, both locale
modules -- including the `pdf_corpus.field_status.llm_inferred`/`pdf_corpus.metadata_field_status.llm_inferred`
locale *keys*, not just values; the human-readable label text itself, e.g. "LLM inferred", is UI copy and was left
alone -- `pdfCorpus.ts`, five `Corpus*` components/stories, and four frontend tests) plus 11 backend test files.
Verified the old strings never appeared inside a prompt sent to a model (status is assigned by our own code after
receiving a model's raw value, never returned by the model itself), so no prompt-contract version bump was needed
per AGENTS.md's rule -- this is a pure internal-vocabulary rename, not a change to what a provider is asked to do.

**Existing persisted builds still have the old vocabulary on disk.** Added a lazy, read-time migration
(`_migrate_status_vocabulary`, next to `_json_read`) that walks any `status`/`source` key and rewrites the two old
values, following the exact precedent `_with_start_inference` already established for backfilling assets read
before a field existed. Wired into every read path that returns build/record/checkpoint data:
`PdfCorpusRepository.get_build`, `list_builds`, `load_records`, `page_records`, and `load_checkpoint`. New
regression coverage in `tests/test_status_vocabulary_migration.py` (6 tests) writes old-vocabulary data directly to
disk (bypassing the repository's own write path, the way a real old build actually looks) and asserts every one of
those five read paths returns the new vocabulary, plus one test that the migration leaves unrelated status-bearing
values (`human_confirmed`, `human_confirmed_boundary`, `deterministic`) untouched.

Full verification: typecheck, lint, 525 unit tests (up from 520), production build, 437 backend tests (up from 429
-- the new migration test file), full 131-scenario baseline and 287-test e2e suite (both re-run since this branch
touches backend files that could theoretically be exercised by the baseline's live-provider-mocked scenarios, even
though no frontend-visible markup changed).

### Part 2: `PdfCorpusBuildManager` decomposition plan (not yet executed -- for a future session)

`PdfCorpusBuildManager` is one class, ~6,800 lines, 201 methods, with no internal section markers and heavy mutual
coupling through `self.repo`, `self._update`, `self._chat_json`, and shared build/record dicts passed between
methods. A structural read of every method name and its surrounding code (not just headers) groups them into the
following clusters, ordered by size and by how directly each maps to a `SPECIFICATION.md` section -- the same
"read the whole thing before moving anything" discipline the runtime-refactor work used for
`pdfExplorerRenderer.ts`/`dashboardRenderer.ts`:

1. **Segmentation** (~1,200 lines: `_segmentation_windows` through `_segment`/`_construct_records`/
   `_mark_segmentation_review`, plus boundary detection/adjudication/audit and topology normalization/quality). The
   single largest cluster; maps directly to the spec's "Segmentation" subsection ("An implementation MUST NOT
   represent an engineering size split as semantic evidence merely because it created a Record boundary").
2. **Metadata enrichment / FieldAssertion** (~1,100 lines: `_apply_manifest_metadata` through
   `_reconcile_metadata_results`, `_metadata_source_quality_gate`, `validate_records`, source/trash quality
   reports). Maps to the spec's "Record Field Classes and Assertions" section; this is also where the assertion
   `status` vocabulary this session just renamed lives, so it is a natural second step once the rename has soaked.
3. **Human review and record editing** (~600 lines: `_assert_human_review_available` through `patch_evidence`,
   `slice_to_neighbor` -- disposition, review decisions, undo/redo, patch text/metadata/evidence). Maps to the
   spec's "Human review is an authority event" language and to RecordRevision (`_assert_record_revision`,
   `_push_review_history` already exist as seams).
4. **Build lifecycle and provider/LLM session management** (~500 lines: `switch_provider_profile`, `create`,
   `resume`, `confirm_manifest`, second-opinion handling, recheck scheduling, transport retry, LLM call logging,
   `llm_activity`, autonomous-run start/settle).
5. **Enrichment reruns** (~650 lines: `retry_incomplete_metadata` through `rerun_metadata`) -- could merge into
   cluster 2 or stay separate; decide once cluster 2 is actually extracted and its real boundaries are visible.
6. **Publication and text touchup** (~175 lines: `_validate_publication_record` through `publish`). Smallest
   cluster; maps to the spec's "Publication and Corpus Interchange" section. Good first-extraction candidate
   precisely because it is small and low-risk, to prove the extraction pattern before tackling segmentation.
7. **Operations/job tracking, schema/profile resolution, editorial memory, manifest patching** -- smaller
   supporting clusters (~150-250 lines each) that the above five depend on; likely become shared helper modules
   rather than their own domain modules.

**Recommended order: 6, then 1, then 2, then 3, then 4/5/7 as they shake out** -- smallest and most self-contained
first to establish the extraction pattern (module boundary, how `self.repo`/`self._update`/`self._chat_json` get
passed in, what the regression-test seam looks like) with the lowest blast radius, before the two largest and most
interconnected clusters. Each extraction needs, at minimum: a verbatim move (not a rewrite) into its own module, a
regression test for the extracted surface if one does not already exist, and a full `pytest -q` run before and
after -- the same discipline `mk_factory.py`/`extract_factory.sh` enforced for the frontend runtime work, though
those exact scripts are JS/TS-specific and a Python equivalent does not yet exist (worth writing one if this
becomes a multi-session effort the way the runtime decomposition was).

**Not started in this session; no `corpus_builder.py` structural changes beyond the vocabulary rename above.**

The parallel plan for `PdfCorpusBuilder.vue`'s composables/CSS extraction was already given to the owner in an
earlier session (phased: composable extraction, then CSS distribution, then template trim) and deferred only for a
PR conflict that has since merged and quieted down -- it does not need re-planning, just a green light to start,
independently of the backend plan above (different files, no shared risk).

## Goal and hard requirements (from the owner)

Decompose `web/src/runtime/runtime.js` (a legacy runtime: one mutable `state`, imperative HTML-string renderers, services and the
Vue-facing API; 10,472 lines at the start, **2,399 now**) toward modern Vue patterns.

- **No functionality changes or loss. No layout, UI or UX changes.** Rendered markup and computed styles stay identical.
- A behavior change is allowed only to fix an obvious bug, and only after checking: probe the current behavior, add a test that
  fails without the fix, keep the fix in its own commit.
- Human-readable code: run Prettier on every new or edited TS/Vue file (`runtime.js` itself is dense on purpose; do not reformat
  it, that would bury the moves).
- Commit and push often; pull master periodically; one tranche per branch (`claude/runtime-refactor-N`), cut from master after the
  previous PR merged (if it did not, merge it in). The owner merges PRs. Keep chat and token use small.
- Before calling anything done: typecheck, lint, unit, the DOM baseline, the full e2e suite and the Storybook build pass.

## State of the code

`web/src/runtime/runtime.js` is now thin: it owns `const state = createRuntimeState()`, a set of
`const {a,b}=createX({state, ...helper lambdas})` calls, small shared helpers, and one big `export {...}` block that Vue code
imports (do not change export names). Everything else lives in `web/src/domain/*.ts` as verbatim moves:

- **Pure helpers:** citations, recordValues, urlState, recordQuery, researchPayloads, html (`esc`, `icon`), runtimeConstants,
  dashboardCharts, recordHistory, providerRequest, pastedRecord, httpErrors, recordFormatting, recordPayloads, workMetadata,
  touchupFields, reviewPresentation, operationsDock.
- **Factories** (`createX(deps)`; `deps.state` is the runtime state object, other deps are helper lambdas): operationPresenters,
  fieldFormatting, corpusAnalytics, searchFacets, recordPresenters, providerProfilesService, searchWorkspace, recordsWorkspace,
  recordWorkspace, worksWorkspace, annotationsWorkspace, researchWorkspace, jobsWorkspace, backupWorkspace, operationDock (toasts
  and the floating operation dock), and the renderers and dialogs: **dashboardRenderer, responseCacheRenderer,
  pdfExplorerRenderer, jobDialogs, workDialogs, recordDialogs**.
- **State:** `state/jobsState.ts`, `state/workspaceState.ts` (shallow-reactive groups bound onto `runtime.state` with
  `bindJobsState`/`bindSharedState`; Pinia stores in `stores/jobs.ts`, `stores/workspace.ts`; the runtime bumps a `version`
  counter where it already notifies, e.g. `invalidateCorpusCache()` calls `touchCorpus()`). Vue views refresh by watching
  `corpusState.version` and `activeFileId`. Gotcha: a `computed` that returns the same array does not notify; return a count.
- **Deleted:** the legacy Record, Annotations, List, Global, Compare, Faq, Rag and Works renderers (no route reaches them).
  `renderView()` dispatches only `home` (dashboard), `pdf` (PDF Explorer) and `responsecache`. `RuntimeSurface.vue` mounts `#main`
  for exactly those three (see `views/DashboardView.vue`, `PdfWorkspaceView.vue`, `ResearchView.vue`).

## Session 5 status (branch `claude/runtime-refactor-19`, stopped here — see below)

Since this file was last written (PR #86 merged), all of section A's remaining clusters have been extracted, each in its
own commit, each verified with unit tests, build, the 131-scenario baseline and the full 270-test e2e suite before
committing: modalDialogs, navigation, workspacePersistence, evidenceSelection, recordEditing, dbPresenceUpsert,
operationsPanelBridge, pdfLinking, appLifecycle, compareLibrary. `runtime.js` is now **2,376 lines** (was 3,421 at the
start of this session; 10,472 at the very start).

**Section A (mechanical cluster moves) is essentially done.** What's left in `runtime.js` is mostly: `translateLegacyDom`
and the collapsible MutationObserver (deliberately kept until the last legacy view is gone, see section B), the small
shared runtime helpers (`tr`, `trf`, `esc`-adjacent wiring, `shell()`, `setShellRefreshHook`), `getShellSnapshot`,
`translatedNavLabel`/`translatedSectionLabel`, `currentContext`, and glue that is not worth its own factory. Skim
`runtime.js` top to bottom before assuming there's another clean cluster; most of what's left is either tiny or
DOM/render-coupled and belongs with section B instead.

**New gotcha found this session, added below too:** a cluster move can silently introduce a **TDZ (temporal dead zone)
crash** even when `extract_factory.sh` reports no errors and `tsc`/eslint are clean, if some *other*, earlier factory
call in `runtime.js` references one of the moved names directly (not wrapped in a lambda) — e.g.
`const {...} = createX({state, api, persistPrefs, ...})` instead of `persistPrefs:(...args)=>persistPrefs(...args)`.
This compiles fine (both are function-typed) but throws `Cannot access 'NAME' before initialization` at runtime,
because the new call site is much later in the file than the old one was. **`npx vitest run` will fail dozens of
unrelated test files at import** — that's the signal. Grep for it before trusting a clean typecheck:

```bash
N=$(grep -n "=create<Factory>(" src/runtime/runtime.js | cut -d: -f1)
for n in fn1 fn2 ...; do
  head -$N src/runtime/runtime.js | grep -nE "[,{ ]$n[,}:]" | grep -v ":(\.\.\.args)=>$n(\.\.\.args)"
done
```//run this after every extraction, before `npx vitest run`. It caught two live bugs this session (one in
`providerProfiles`'s call, one in `searchFacets`'s call, both referencing `recordDbStatus` unwrapped).

**Was about to start, not done:** continuing the mechanical extraction (little left, see above) and then moving into
section B (Vue replacement of the dashboard/PDF Explorer/response cache). That first Vue-surface tranche is now
complete; the current next step is the remaining legacy surfaces listed below.

## Copilot progress through PR #93 (2026-09-22)

The work described above has since been carried forward and merged into `master`:

- The Response Cache, Dashboard, and PDF Explorer now have Vue-owned route/surface boundaries while preserving
  their legacy DOM IDs, classes, URL synchronization, dialogs, disabled states, and characterization coverage.
- The unified theme work and related provider-layout changes were merged without changing the runtime contract.
- The corpus and metadata fixes addressed indexed-value extraction, accumulated autocomplete suggestions and repeated
  array additions, slice requeueing, Corpus Builder step progression, metadata-schema preview providers, provider
  routing, invalid `generation.num_ctx`, and Ollama embedding endpoint compatibility.
- Duplicate backend locale keys that blocked lint were removed without changing the canonical translations.
- Settings persistence now sanitizes the complete IndexedDB preference payload before structured cloning. PR #93
  contains that fix and merged on 2026-09-22.
- Validation completed for the merged work included frontend tests, typecheck, lint, production build, Storybook,
  DOM baselines, and Playwright/axe. Backend quality gates passed in GitHub Actions; local Windows validation did
  not have a Python launcher.

This is the end of the first Vue-surface tranche, not the end of the runtime decomposition. `runtime.js` remains
approximately 2,376 lines and `RuntimeSurface.vue` remains the compatibility host for surfaces that have not yet
been migrated.

## What is left, in order

### A. Move the remaining runtime.js clusters (mechanical, low risk each) — mostly DONE, see Session 5 status above

All the clusters originally listed here (workspace persistence, evidence/review selection, record editing, DB
presence/upsert, navigation/URL, the operations panel + RAG progress panel, modal helpers, the compare library, PDF
linking, app lifecycle) have been extracted into their own `domain/*.ts` factories (see the module list under "State of
the code" — add: modalDialogs, navigation, workspacePersistence, evidenceSelection, recordEditing, dbPresenceUpsert,
operationsPanelBridge, pdfLinking, appLifecycle, compareLibrary). What's left in `runtime.js` is small glue and the
render/DOM-coupled code that belongs with section B (`translateLegacyDom`, the collapsible MutationObserver, `shell()`,
`getShellSnapshot`, nav label translation). Skim the file before assuming another clean cluster exists; if one does,
follow the same procedure below.

Procedure per cluster (about 10 minutes each), from `web/`:

1. `bash ../scripts/runtime-refactor/extract_factory.sh <module> <createFactory> "fn1,fn2,..." "header line 1|header line 2" [importsJSON]`
   copies the functions verbatim (`mk_factory.py`), lists the missing names from `tsc` (TS2304), builds the `Deps` type, wires a
   `const {fn1,fn2}=createX({state, helper lambdas})` call into `runtime.js`, adds `Any` annotations (`fix_any.py`) and prints
   `LET` / `MISSING` warnings. `importsJSON` maps pure helpers to the module that exports them, for example
   `{"esc":"./html","icon":"./html"}` (the default); add e.g. `dockCollapsedSummary` from `./operationsDock`. Read
   `wire_factory.py` first: it inserts the new call right after the `createDashboardRenderer(` call; if a value dependency is
   declared later in `runtime.js`, move the call to after that declaration.
2. A helper that is a value (array, Map, object) rather than a function needs care. If only the cluster uses it, move the const
   into the new module (`WORK_METADATA_FIELDS`, `EDITOR_GROUPS`). If others use it, move the factory call after the const and pass
   it by value (`fileTimers`, `corpusCache`). A reassigned `let` (`urlSyncHook`, `shellRefreshHook`) must be passed as a getter
   (`getUrlSyncHook:()=>urlSyncHook`) when the code reads it as a value; a lambda wrapper is only right when it is called.
3. Fix leftovers by hand: `catch (error: Any)`, `let x: Any`, `new Set<Any>()`, `const changes: Any = {}`, unused-variable lint
   (prefix `_` or a one-line `eslint-disable-next-line` with a reason), then `npx prettier --write` the new file.
4. Verify (see Verification), commit, push. One cluster per commit. If the baseline does not cover the cluster, add scenarios
   first, in their own commit, recorded from the pre-move build.
5. Afterwards `python3 ../scripts/runtime-refactor/dead_functions.py` removes top-level functions nothing references (run it only
   after deleting a caller; it deliberately ignores the `export {}` block).

### B. Replace the remaining legacy views with Vue -- DONE; `RuntimeSurface.vue` deleted (session 10); `legacyCompat.js` audit is next

Response cache (session 7), the dashboard (session 8), and PDF Explorer (session 9) are all done: real Vue templates,
no more `v-html`d whole-page strings, no more `renderResponseCache`/`renderDashboard`/`renderPdf` dispatch in
`runtime.js`. **No legacy views are left**, and `RuntimeSurface.vue`, `CorpusView.vue`, `SystemView.vue`, and
`RuntimeSurface.stories.ts` are deleted (session 10 -- all four were confirmed to have zero live consumers first).

- **Next session should start here.** `legacyCompat.js`/`translateLegacyDom` are still imported by `runtime.js` and
  are **not** dead: `renderView()` (which calls `translateLegacyDom`, `enhanceCollapsibles`, and
  `decorateDisabledControls` on `#main`) is still invoked from roughly 20 call sites across `pdfLinking.ts`,
  `appLifecycle.ts`, `workDialogs.ts`, `recordDialogs.ts`, `jobDialogs.ts`, `navigation.ts`, and `stores/i18n.ts` as a
  generic post-action "refresh `#main`'s decorations" hook, separate from the `derridai:*-refresh` event bridges the
  Vue-owned views use for their own data refresh. Audit each call site: does the Vue view currently mounted at
  `#main` (dashboard, PDF Explorer, or response cache) still need `enhanceCollapsibles`/`decorateDisabledControls`
  run again after that specific action, and if so, is `renderView()` actually still doing that job or is it a no-op
  now that `result` is always `null`? Only once every site is accounted for can `legacyCompat.js`, `translateLegacyDom`,
  and the collapsible `MutationObserver` be deleted and `runtimeBridge.ts` exports nothing imports anymore be removed.
  Shrink `runtime.js`'s `export {}` block to match (re-run the duplicate-export check: `sed -n '/^export {/,/^};/p'
  src/runtime/runtime.js | sort | uniq -d`). Re-run the full verification suite after.

### C. State and services to Vue idioms

Turn the `*Workspace` factories into composables that read Pinia stores instead of polling `runtime.get*Snapshot()`, and make
`annotationsService` call its factory directly. Do this per view, and only where a probe shows stale or wrong behavior (import a
file with distinct content while the view is open; see whether it updates). Do not bind view-local refs to store fields without a
test pinning the intended behavior first (`VectorStoresView.load()` has a branch that is dead today and would wake up).

### D. Styles (`web/src/style.css`, see `docs/STYLE_AUDIT.md`)

After each renderer is replaced its classes move into the component. Then: hand-resolve classes styled in several places (merge
duplicate selectors, then move the group), extract a small shared base layer (`btn`, `badge`, `chip`, `card`, forms) next to
`styles/tokens.css`, then normalize breakpoints, replace hard-coded colors with tokens, and only then reduce `!important`.
`CommandSearch.vue` is excluded from automatic moves (moving its rules changed its look).

### E. End of effort

Delete `PROGRESS.md`. Keep `docs/STYLE_AUDIT.md` only if CSS work continues.

## Verification (run all before each push; from `web/`)

```bash
npx vue-tsc --noEmit && npx eslint src && npx vitest run                     # 459 unit tests at last count
npx vite build
APP_PORT=5299 npx playwright test -c playwright.legacy.config.ts --workers=3  # DOM baseline, 131 scenarios, about 3 min
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2   # full e2e, 270 tests, about 13 min
```

Also run the Storybook build once per PR. `npx eslint .` reports errors in other people's `tests/frontend/corpus-builder-*.test.ts`
(pre-existing); lint what you touch. `npx prettier --check` flags `src/views/PdfWorkspaceView.vue` (existing compact style; leave it).

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`, snapshots next to it)

131 scenarios: normalized markup (`*.html`) and computed styles (`styles-*.txt`; light, dark, tablet, phone) for the dashboard, PDF
Explorer, response cache, every Vue view that talks to the runtime, the runtime-built dialogs, the operation dock and the backup
and restore flows. Scenario options: `nav` (click a sidebar item), `path` (open a Vue-native route directly), `load` (import the
sample JSONL), `records`, `role`, `scheme`, `viewport`, `fixtures` (API mocks; `liveJobs()` is a stateful jobs endpoint), `steps`,
`target` (`main`, `runtime` = `#main`, `dialog`, `app`, `dock`), `styles: true`.

- UTC and en-US pinned, `Math.random=0`, fixed clock, reduced motion; `data-v-*`, UUIDs, dates and the `Build <hash>` text masked.
- **Never regenerate snapshots to make a change pass.** New scenarios are recorded from the pre-change build in their own commit
  (`--update-snapshots=missing`; Playwright reports the first write as a failure, so rerun). The only snapshot changed for a bug fix
  so far is `jobs-dock-running`.
- Not covered (add before touching): hover and focus states, the bulk-edit and upsert-queue dialogs, the works-metadata editor and
  remove-work, confirm modals other than backup, restore and response cache, job types outside `RAG_JOBS`/`JOBS`, Research streaming.
- The PDF Explorer scenarios click the sidebar's "Corpus Builder", then the "PDF Explorer" tab (`inPdfExplorer`); the PDF is
  generated by `samplePdf()` in the spec.

## Gotchas learned (things that cost time)

- **Port 5199 may already be served by another session's build.** With `reuseExistingServer` the baseline then tests the wrong code
  (unrelated snapshot diffs everywhere). Use `APP_PORT=5299` (or any free port) and stop your own server afterwards with
  `scripts/runtime-refactor/kill_port.sh <port>`. Never `pkill -f` a word that appears in your own command line.
- Machine load (orphan Chromium, another Storybook) causes 30 s timeouts in random scenarios: check `uptime`, kill orphans, use
  `--workers=3`.
- Factory call sites must come after the `const`s they receive by value; hoisted `function`s are safe, later `const`s need a lambda.
  TDZ errors break dozens of unit test files at import.
  **This also happens if an *earlier* factory call references the moved name directly instead of as a lambda** — grep for it
  after every extraction (see Session 5 status above for the exact command); a clean `tsc`/eslint does not catch it, only
  `npx vitest run` failing many unrelated files does.
- `mk_factory.py` never indents bodies (template literals must stay byte-identical).
- After Prettier expands a dense `try{}catch{}`, an `eslint-disable no-empty` comment no longer lines up: use a commented empty catch.
  Prettier also breaks Python `str.replace` patterns aimed at formatted code: use regex or line-based edits.
- Some tools turn a `\u0000` escape into a literal NUL byte; check new files for it.
- Import de-duplicates by content hash: identical JSONL content does not import twice.
- The runtime restores the saved workspace at start-up; loading a JSONL too early races with it (the baseline waits for network idle).
- The direct URL `/pdf?mode=explorer` renders the dashboard (the runtime's view comes from in-app navigation); reach the Explorer
  through the sidebar, then the tab.
- Do not `git stash` (the stack is shared across worktrees) and do not `git checkout origin/master --`; use a WIP commit.
- Copilot works in parallel on `ajschlosser-unified-web-theme` (UiPageHeader, tokens, `style.css`). It touches no runtime file, but
  when it merges the Vue-view baseline snapshots (page headers) will change: re-record those from the pre-change build in a separate
  commit, and expect `style.css` conflicts with any CSS move.
- Dashboard date keys use local midnight then `toISOString()`, so tests pin `TZ=UTC`.
- `countOccurrences(text, [])` loops forever (legacy bug, unreachable with real input; left on purpose).

## Helper scripts (`scripts/runtime-refactor/`)

`extract_factory.sh` (one-command cluster move), `mk_factory.py`, `wire_factory.py`, `fix_any.py`, `dead_functions.py`,
`kill_port.sh`, `deps.py` (names and state fields a group uses), `purity.py`, `mv_fn.py`, `splice.py` (older pure-helper moves),
`style_audit.py`, `style_prune.py`, `style_move.py` (CSS; see `docs/STYLE_AUDIT.md`).

## Merged PRs and next branch

PR #86 (`claude/runtime-refactor-18`) delivered the dashboard, PDF Explorer and response cache renderers, three dialog
factories, the operation dock, backup/restore and response-cache coverage, and three runtime bug fixes. The follow-up
theme and bug-fix work merged through PRs #90, #91, #92, and #93.

The next runtime tranche must be cut from the latest `master` and should begin with one remaining legacy surface,
preferably Corpus Builder or Tools, after confirming its current DOM baseline. Do not combine that migration with
unrelated CSS cleanup or provider changes. Preserve the existing runtime exports and delete compatibility code only
after every dependent surface has moved.
