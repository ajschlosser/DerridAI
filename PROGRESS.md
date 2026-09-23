# Decomposition hand-off

Temporary file for two ongoing, parallel decomposition efforts: the frontend `web/src/runtime/runtime.js` (legacy
imperative runtime being replaced with Vue idioms) and the backend `api/app/corpus_builder.py` (a single ~8,000-line
class being split into focused modules). It exists so another agent (Codex, Copilot, another Claude) can continue if
the current one stops. **Delete this file when both efforts are finished** -- git log and `docs/notes/` are the
permanent record; keep only what a fresh session needs to pick up work safely.

## Current state

- **`runtime.js`: 2,410 lines**, down from 10,472 at the start (77.0% removed). Sections A and B of the plan below
  are done: every cluster that could move to a `domain/*.ts` factory has moved, and every legacy HTML-string view
  (dashboard, PDF Explorer, response cache) is a real Vue component. `legacyCompat.js`/`translateLegacyDom` were
  audited and found still load-bearing (see "Concluded, do not re-open" below) -- not dead code. What's left is
  small glue plus whatever remaining pure helpers a skim turns up (see "Next steps").
- **`api/app/corpus_builder.py`: 6,939 lines**, down from 8,236 when this effort started (16% removed so far). Four
  of the ~7 planned clusters are extracted: publication/touchup (`corpus_publication.py`), most of the record-quality
  cluster (`corpus_record_quality.py`; `validate_records` deliberately deferred, see below), segmentation
  (`corpus_segmentation.py`), review-state derivation (`corpus_review_state.py`); plus two cross-cutting sets of pure
  helpers found by scanning the whole file's decorator list rather than any one planned cluster: LLM
  request/response handling (`corpus_llm_helpers.py`) and reviewer-facing blind-review helpers
  (`corpus_reviewer_helpers.py`; `_refresh_workflow_fields` deferred alongside it for the same
  `CORPUS_PROFILES`/`PROFILE_VERSION` circular-import reason as `validate_records`). Human review's stateful
  mutation methods, build lifecycle/provider session
  management, enrichment reruns, and the smaller supporting clusters (operations/job tracking, schema/profile
  resolution, editorial memory, manifest patching) are not started.
- **Release:** 0.70.0 "Amesbury" is tagged (`v0.70.0`) and current. See `docs/notes/0.70.0.md`.
- **Assertion-status vocabulary** matches `SPECIFICATION.md` exactly (`model_inferred`, `confirmed_absent`); a
  lazy read-time migration in `corpus_builder.py`'s `PdfCorpusRepository` upgrades any build/record/checkpoint still
  carrying the old `llm_inferred`/`human_confirmed_absent` values.

## Concluded, do not re-open

- **`legacyCompat.js`/`translateLegacyDom` cannot be deleted.** Most of the file (`syncColorScheme`, `tr`, `trf`,
  etc.) is core theme/i18n plumbing, unrelated to legacy rendering. `translateLegacyDom` specifically still
  translates any `v-html`'d markup-generator output (e.g. the dashboard's metric carousel) into French; none of the
  three Vue-owned former-legacy views call it themselves, so this depends on the ~20 scattered `renderView()` call
  sites across `pdfLinking.ts`/`appLifecycle.ts`/`workDialogs.ts`/`recordDialogs.ts`/`jobDialogs.ts`/`navigation.ts`.
  Deleting it would silently regress French-locale translation with no test coverage that would catch it.
- **A separate, small i18n bug found but not fixed:** `dashboardPieChart`/`lineChart`/`multiLineChart`'s "no data
  yet" empty-state text (`dashboardCharts.ts`/`recordPresenters.ts`) is a hardcoded English literal, never run
  through `tr()`. Fixing it means threading `state`/`tr` through those currently-pure chart functions and every call
  site -- a real, self-contained follow-up, not a quick fix.
- **`validate_records` (in `corpus_builder.py`, ~140 lines) was deliberately not extracted** with the rest of the
  record-quality cluster. It depends on `RecordMetadataModel`, a Pydantic model also used by two other manager
  methods, so extracting it alone would recreate a circular import. Next session on this: either move
  `RecordMetadataModel` (and its immediate neighborhood) into `corpus_record_quality.py` too, since Pydantic models
  are usually safe to relocate wholesale, or accept it stays a manager method permanently. Not decided -- a real
  design choice.
- **`llm_inferred`/`human_confirmed_absent` vs. spec's `model_inferred`/`confirmed_absent`:** renamed to match the
  spec exactly, with a lazy migration for existing persisted data (see `_migrate_status_vocabulary` in
  `corpus_builder.py`, next to `_json_read`). Confirmed neither string ever appeared inside a prompt sent to a
  model, so no prompt-contract version bump was needed.

## Next steps

1. **Backend, cluster "human review" (stateful mutation methods):** `set_disposition`, `review_decision`,
   `accept_record`, `bulk_disposition`, `undo_last_review_edit`/`redo_last_review_edit`, `patch_record_text`,
   `patch_metadata`, `bulk_patch_metadata`, `patch_evidence`, `slice_to_neighbor`, and their supporting
   `_assert_human_review_available`/`_assert_record_revision`/`_push_review_history`/`_save_review_undo`. Mostly
   stateful (repo I/O), unlike the review-*state* cluster already extracted -- grep the decorator list first (see
   "How to find the next pure cluster" below) before assuming there's a clean mechanical move; there may not be one,
   in which case skip to the next cluster rather than forcing an extraction.
2. **Backend, cluster "build lifecycle / provider session management":** `switch_provider_profile`, `create`,
   `resume`, `confirm_manifest`, second-opinion handling, recheck scheduling, transport retry, LLM call logging,
   `llm_activity`, autonomous-run start/settle.
3. **Backend, cluster "enrichment reruns":** `retry_incomplete_metadata` through `rerun_metadata`.
4. **Backend, smaller supporting clusters:** operations/job tracking, schema/profile resolution, editorial memory,
   manifest patching (~150-250 lines each) -- likely become shared helper modules rather than domain modules, since
   the clusters above depend on them.
5. **Frontend:** skim `runtime.js` top to bottom for any remaining pure helper still sitting next to
   state-coupled code (the same way `recordTableHelpers.ts` was found -- see "How to find the next pure cluster").
   Most of what's left is small glue (`tr`, `trf`, `shell()`, `setShellRefreshHook`, `getShellSnapshot`,
   `translatedNavLabel`/`translatedSectionLabel`, `currentContext`) or DOM/render-coupled code that stays.
6. **`PdfCorpusBuilder.vue`'s composables/CSS extraction** (frontend, ~8,186 lines, the largest file in the repo
   besides `corpus_builder.py`): phased plan already given to the owner (composable extraction, then CSS
   distribution, then template trim) and never blocked on anything backend-side -- independent of every item above.
7. **Section C/D from the original runtime.js plan, still not started:** turn the `*Workspace` factories into
   composables reading Pinia stores instead of polling `runtime.get*Snapshot()` (per view, only where a probe shows
   stale/wrong behavior); CSS unification per `docs/STYLE_AUDIT.md`.

### How to find the next pure cluster (backend or frontend)

The fast, reliable way to find a safe mechanical-extraction candidate in either `corpus_builder.py` or `runtime.js`:
grep for `@staticmethod`/`@classmethod` (Python) or scan a section's functions for ones that never reference
`self`/`state` (JS), across the *whole remaining file*, not just the line range a prior plan assumed was one
cluster. Segmentation and metadata had similar per-line size in `corpus_builder.py` but very different pure/stateful
ratios (19 of ~30 methods vs. 5 of ~10) -- a cluster's size does not predict how much of it is actually extractable.
After wiring up an extraction's imports, **run `ruff`/`eslint` and treat every unused-import warning as an "is this
really called from here" question** -- it is how two genuinely dead methods (`_segmentation_windows`,
`_best_safety_boundary`) and one dead thin wrapper (`_source_quality_report`) were found in this effort. Preserve
dead code found this way rather than deleting it; that is a separate decision from decomposition.

## Hazards specific to this decomposition (read before extracting another Python cluster)

- **Circular imports:** a pure helper used both inside and outside the cluster being extracted (`_normalize_text`,
  `iso_now`) must move to the new module too, with the old module importing it back -- never leave it in the old
  module and have the new module import it from there, or vice versa if the old module still needs it, since Python
  cannot resolve two modules that both need something from each other at import time.
- **`monkeypatch.setattr(manager, "name", fake)` silently stops working** once `name` becomes a bare module-level
  function: Python resolves `self._name(...)` via the instance/class at call time, but a bare `_name(...)` resolves
  against its enclosing module's own globals at call time instead. Fix: `monkeypatch.setattr(cb, "name", fake)`
  (patching the *module* attribute) -- this still works because global-name lookup happens at each call, not at
  import time. **Grep every cluster's target names for `monkeypatch.setattr(manager,` / `monkeypatch.setattr(self,`
  in `tests/` before extracting, not after** -- the test does not error until its assertion fails, so this is easy
  to miss.
- **A test or another module accessing `PdfCorpusBuildManager._name` or `manager.instance._name` directly** breaks
  the same way once `_name` is a module function, but under a different alias than `cb.PdfCorpusBuildManager.` (seen
  once as `from app.corpus_builder import PdfCorpusBuildManager as M`, once as `pdf_corpus_builds._name(...)` in
  `main.py` on the live singleton instance) -- grep the bare method name across `tests/` and `api/app/*.py`, not
  just the one import-alias pattern already checked.
- **A name still needed via `cb.name` externally (tests or other modules) after the definition moves** needs the
  `from .new_module import name as name` re-export idiom already used elsewhere in `corpus_builder.py`'s own
  imports -- a bare `from .new_module import name` gets flagged and removed by ruff's unused-import check the
  moment nothing *inside* `corpus_builder.py` calls it anymore, even though external code still needs it importable
  from that module.
- **Use the `ast` module, not manual line-counting or regex, to find method boundaries and strip `self`/`cls`** from
  a signature -- a naive single-line regex misses multi-line parameter lists (caught twice: once by inspecting
  extracted output before wiring it in, not by assuming the regex was correct).
- **A pre-existing ruff per-file-ignore for `corpus_builder.py`'s dense legacy style (`E701`/`E702`) does not carry
  over to a new module** -- add the same ignore for each new `corpus_*.py` module in `ruff.toml`, since the moved
  code is verbatim, not reformatted.
- **Two clusters extracted on parallel branches from the same base will both add a `ruff.toml` per-file-ignore near
  the same line, and both may touch this file** -- expect a trivial merge conflict on whichever branch merges
  second; resolve by keeping both entries and both sessions' notes.

## Goal and hard requirements (frontend, from the owner)

- **No functionality changes or loss. No layout, UI or UX changes.** Rendered markup and computed styles stay
  identical for `runtime.js` work; the same discipline applies to the backend extractions (pure refactor, verified
  behavior-identical by the existing test suite).
- A behavior change is allowed only to fix an obvious bug, and only after checking: probe the current behavior, add
  a test that fails without the fix, keep the fix in its own commit.
- Human-readable code: run Prettier on every new or edited TS/Vue file (`runtime.js` itself is dense on purpose; do
  not reformat it -- that would bury the moves). The equivalent backend rule: `corpus_builder.py` and every
  `corpus_*.py` module extracted from it keep the same dense, unformatted style; do not run a Python formatter on
  them.
- Commit and push often; pull `master` periodically; check `gh pr list` for conflicting open PRs before starting a
  new cluster, and re-base onto fresh `master` if the previous PR in this effort already merged rather than
  continuing on a stale branch.
- Before calling anything done: typecheck, lint (`ruff`/`eslint`), unit tests, `mypy`/`compileall` as applicable,
  and -- for anything that touches `web/` -- the DOM baseline, the full e2e suite, and the Storybook build all pass.
  A backend-only change does not need the frontend baseline/e2e re-run (the harness drives a mocked backend that
  cannot observe a Python-only change).

## State of the frontend code

`web/src/runtime/runtime.js` is now thin: it owns `const state = createRuntimeState()`, a set of
`const {a,b}=createX({state, ...helper lambdas})` calls, small shared helpers, and one big `export {...}` block
that Vue code imports (do not change export names). Everything else lives in `web/src/domain/*.ts` as verbatim
moves:

- **Pure helpers:** citations, recordValues, urlState, recordQuery, researchPayloads, html (`esc`, `icon`),
  runtimeConstants, dashboardCharts, recordHistory, providerRequest, pastedRecord, httpErrors, recordFormatting,
  recordPayloads, workMetadata, touchupFields, reviewPresentation, operationsDock, recordTableHelpers.
- **Factories** (`createX(deps)`; `deps.state` is the runtime state object, other deps are helper lambdas):
  operationPresenters, fieldFormatting, corpusAnalytics, searchFacets, recordPresenters, providerProfilesService,
  searchWorkspace, recordsWorkspace, recordWorkspace, worksWorkspace, annotationsWorkspace, researchWorkspace,
  jobsWorkspace, backupWorkspace, operationDock (toasts and the floating operation dock), and the renderers/dialogs:
  dashboardRenderer, responseCacheRenderer, pdfExplorerRenderer, jobDialogs, workDialogs, recordDialogs.
- **State:** `state/jobsState.ts`, `state/workspaceState.ts` (shallow-reactive groups bound onto `runtime.state`
  with `bindJobsState`/`bindSharedState`; Pinia stores in `stores/jobs.ts`, `stores/workspace.ts`; the runtime
  bumps a `version` counter where it already notifies, e.g. `invalidateCorpusCache()` calls `touchCorpus()`). Vue
  views refresh by watching `corpusState.version` and `activeFileId`. Gotcha: a `computed` that returns the same
  array does not notify; return a count.
- **Deleted:** the legacy Record, Annotations, List, Global, Compare, Faq, Rag and Works renderers (no route reaches
  them); `RuntimeSurface.vue`, `CorpusView.vue`, `SystemView.vue` (confirmed zero live consumers before deleting).
  `renderView()` no longer dispatches to any legacy renderer -- every route it used to serve is now a real Vue
  component that owns its own `#main` and refresh cycle.

## Verification (run all before each push)

Frontend, from `web/`:

```bash
npx vue-tsc --noEmit && npx eslint src && npx vitest run   # unit tests
npx vite build
APP_PORT=5299 npx playwright test -c playwright.legacy.config.ts --workers=3  # DOM baseline, 131 scenarios, ~3-6 min
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2   # full e2e, ~15 min
npm run build-storybook
```

Backend, from the repo root:

```bash
python -m compileall -q api/app
python -m mypy      # requires mypy.ini / ruff.toml at repo root; venv at /tmp/derridai-venv in this environment
python -m ruff check api/app tests
pytest -q
```

`npx eslint .` reports errors in other people's `tests/frontend/corpus-builder-*.test.ts` (pre-existing); lint what
you touch. `npx prettier --check` flags `src/views/PdfWorkspaceView.vue` (existing compact style; leave it).

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`, snapshots next to it)

131 scenarios: normalized markup (`*.html`) and computed styles (`styles-*.txt`; light, dark, tablet, phone) for the
dashboard, PDF Explorer, response cache, every Vue view that talks to the runtime, the runtime-built dialogs, the
operation dock, and the backup/restore flows. Scenario options: `nav` (click a sidebar item), `path` (open a
Vue-native route directly), `load` (import the sample JSONL), `records`, `role`, `scheme`, `viewport`, `fixtures`
(API mocks; `liveJobs()` is a stateful jobs endpoint), `steps`, `target` (`main`, `runtime` = `#main`, `dialog`,
`app`, `dock`), `styles: true`.

- UTC and en-US pinned, `Math.random=0`, fixed clock, reduced motion; `data-v-*`, UUIDs, dates, and the
  `Build <hash>` text masked.
- **Never regenerate snapshots to make a change pass.** New scenarios are recorded from the pre-change build in
  their own commit. A snapshot changed to reflect a real, disclosed, checked-first behavior fix (not a UI change)
  is re-recorded only after confirming it is the *only* diff, in its own commit, with the reasoning documented in
  that commit's message.
- Not covered (add before touching): hover and focus states, the bulk-edit and upsert-queue dialogs, the
  works-metadata editor and remove-work, confirm modals other than backup/restore/response-cache, job types outside
  `RAG_JOBS`/`JOBS`, Research streaming.
- The PDF Explorer scenarios click the sidebar's "Corpus Builder", then the "PDF Explorer" tab (`inPdfExplorer`);
  the PDF is generated by `samplePdf()` in the spec.

## Gotchas learned (durable, still relevant)

- **Port 5199 may already be served by another session's build.** With `reuseExistingServer` the baseline then
  tests the wrong code (unrelated snapshot diffs everywhere). Use `APP_PORT=5299` (or any free port) and stop your
  own server afterwards with `scripts/runtime-refactor/kill_port.sh <port>`. Never `pkill -f` a word that appears in
  your own command line.
- Machine load (orphan Chromium, another Storybook) causes 30s timeouts in random scenarios: check `uptime`, kill
  orphans, use `--workers=3`.
- **Factory call sites must come after the `const`s they receive by value**; hoisted `function`s are safe, later
  `const`s need a lambda. This also happens if an *earlier* factory call references the moved name directly instead
  of as a lambda -- a clean `tsc`/eslint does not catch it, only `npx vitest run` failing many unrelated files does
  (a TDZ crash at import time). Grep before trusting a clean typecheck:
  ```bash
  N=$(grep -n "=create<Factory>(" src/runtime/runtime.js | cut -d: -f1)
  for n in fn1 fn2 ...; do
    head -$N src/runtime/runtime.js | grep -nE "[,{ ]$n[,}:]" | grep -v ":(\.\.\.args)=>$n(\.\.\.args)"
  done
  ```
- `mk_factory.py` never indents bodies (template literals must stay byte-identical).
- After Prettier expands a dense `try{}catch{}`, an `eslint-disable no-empty` comment no longer lines up: use a
  commented empty catch. Prettier also breaks Python `str.replace` patterns aimed at formatted code: use regex or
  line-based edits.
- Some tools turn a `\u0000` escape into a literal NUL byte; check new files for it.
- Import de-duplicates by content hash: identical JSONL content does not import twice.
- The runtime restores the saved workspace at start-up; loading a JSONL too early races with it (the baseline waits
  for network idle).
- The direct URL `/pdf?mode=explorer` renders the dashboard (the runtime's view comes from in-app navigation);
  reach the Explorer through the sidebar, then the tab.
- Do not `git stash` (the stack is shared across worktrees) and do not `git checkout origin/master --`; use a WIP
  commit. Do not run `git checkout <branch>` casually either -- a local branch can be many commits behind
  `origin/<branch>`; fast-forward (`git merge --ff-only origin/<branch>`) immediately after switching, before
  editing anything, to avoid silently reverting files to a stale state.
- Dashboard date keys use local midnight then `toISOString()`, so tests pin `TZ=UTC`.
- `countOccurrences(text, [])` loops forever (legacy bug, unreachable with real input; left on purpose).
- After a version bump, the app-build-info string appears in several baseline snapshots (backup/restore/settings
  scenarios); re-record just those after confirming the version string is the only diff.

## Helper scripts (`scripts/runtime-refactor/`)

`extract_factory.sh` (one-command cluster move for the frontend), `mk_factory.py`, `wire_factory.py`, `fix_any.py`,
`dead_functions.py`, `kill_port.sh`, `deps.py` (names and state fields a group uses), `purity.py`, `mv_fn.py`,
`splice.py` (older pure-helper moves), `style_audit.py`, `style_prune.py`, `style_move.py` (CSS; see
`docs/STYLE_AUDIT.md`). No equivalent scripted extraction exists yet for the backend; each Python cluster has been
extracted with an ad hoc `ast`-based script written per session (see "Hazards specific to this decomposition"
above for the technique) -- worth generalizing into a script if this becomes many more sessions of work.
