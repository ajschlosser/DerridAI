# Decomposition hand-off

Temporary file for two ongoing, parallel decomposition efforts: the frontend `web/src/runtime/runtime.js` (legacy
imperative runtime being replaced with Vue idioms) and the backend `api/app/corpus_builder.py` (a single ~8,000-line
class being split into focused modules). It exists so another agent (Codex, Copilot, another Claude) can continue if
the current one stops. **Delete this file when both efforts are finished** -- git log and `docs/notes/` are the
permanent record; keep only what a fresh session needs to pick up work safely.

## Corpus Builder generic media

Status: rebuilt on current `master`.

Generic media is added beside the current extractor, segmentation, enrichment, and review code. It does not restore the older corpus-builder monolith. Text, Word, images, audio, URLs, and Project Gutenberg become source spans. A deterministic metadata check runs on load. The illegibility slider stays before Choose source PDF.

New modules: `source_media.py`, `source_text.py`, `source_audio.py`, `source_gutenberg.py`, `source_kinds.py`. Setup UI is `CorpusSourceIngest.vue`.

`tests/test_0610_warbling_wombat.py`: 9 passed, through behavior rather than source scans.

## Current state

- **`runtime.js`: 2,410 lines**, down from 10,472 at the start (77.0% removed). Sections A and B of the plan below
  are done: every cluster that could move to a `domain/*.ts` factory has moved, and every legacy HTML-string view
  (dashboard, PDF Explorer, response cache) is a real Vue component. `legacyCompat.js`/`translateLegacyDom` were
  audited and found still load-bearing (see "Concluded, do not re-open" below) -- not dead code. What's left is
  small glue plus whatever remaining pure helpers a skim turns up (see "Next steps").
- **`api/app/corpus_builder.py`: 2,784 lines**, down from 8,236 when this effort started (66.2% removed so far). All
  seven originally-planned clusters are extracted (publication/touchup, record-quality, segmentation, review-state
  derivation, human review's stateful mutation methods, enrichment reruns, build lifecycle/provider session
  management), plus the smaller supporting clusters found after them: operations/job tracking
  (`corpus_operations.py`, an `OperationsMixin`), editorial memory (`corpus_editorial_memory.py`, an
  `EditorialMemoryMixin`), and schema/profile resolution (`corpus_schema_profile.py`, a `SchemaProfileMixin`).
  **The circular-import blocker that deferred nine methods across five sessions is resolved.** `SCHEMA_VERSION`/
  `SEGMENTATION_PROMPT_VERSION`/`METADATA_PROMPT_VERSION`/`DOCUMENT_PROMPT_VERSION`/`PROFILE_VERSION`,
  `CORPUS_PROFILES`, and all 27 Pydantic response models (`DocumentManifestModel` through
  `IndexMetadataResponseModel`) moved verbatim into a new `corpus_models.py` (self-contained: only depends on
  `pydantic` and `corpus_metadata`'s closed vocabularies). That unblocked `create`, `preview_schema_group`,
  `_edit_model`, `_profile_of_build`, `_profile_for`, `_refresh_workflow_fields`, `validate_records`,
  `regenerate_manifest`, and `patch_manifest`, all now moved verbatim into a new `corpus_manifest_workflow.py`
  (`ManifestWorkflowMixin`). The ten LLM-driven boundary-segmentation execution methods (`_compact_segment_prompt`
  through `_segment`, the recursive windowed pass, pairwise/batch classification, and boundary adjudication) moved
  into a new `corpus_segmentation_execution.py` (`BuildSegmentationExecutionMixin`) -- see "Gotchas learned" below
  for the monkeypatch fix this required in three test files. The four metadata-enrichment execution methods
  (`_enrich_record`, `_prepare_metadata_tasks`, `_execute_metadata_tasks`, `_reconcile_metadata_results` -- the
  latter alone ~450 lines, the largest single method in the file) moved into a new
  `corpus_metadata_enrichment_execution.py` (`MetadataEnrichmentExecutionMixin`). Plus three cross-cutting sets of
  pure helpers found by scanning the whole file's decorator list rather than any one planned cluster: LLM
  request/response handling (`corpus_llm_helpers.py`), reviewer-facing blind-review helpers
  (`corpus_reviewer_helpers.py`), and enrichment/editorial bookkeeping (`corpus_enrichment_helpers.py`).
  `PdfCorpusBuildManager` now inherits from eight mixins (`class
  PdfCorpusBuildManager(BuildLifecycleMixin, EditorialMemoryMixin, ManifestWorkflowMixin, OperationsMixin,
  ReviewActionsMixin, EnrichmentRerunsMixin, SchemaProfileMixin, BuildSegmentationExecutionMixin,
  MetadataEnrichmentExecutionMixin):`) -- see "The mixin technique" below, **including its `TYPE_CHECKING`-guard
  requirement, which is not optional**: an earlier version of this extraction shipped without it and silently broke
  `rerun_metadata_enrichment` (see "Concluded, do not re-open" below). What remains of `PdfCorpusBuildManager`
  itself is mostly build orchestration (`_run`, `_prepare_build_scope`, `_construct_build_topology`,
  `_persist_build_metadata_stage`, `_schedule_build_enrichment`, `_finalize_build_review`,
  `_rewrite_and_validate`, `publish`, and related) plus a handful of small standalone methods
  (`_write_start_page_to_layout`, `preview_record`, `touchup_record_text`,
  `set_text_touchup_proposal_status`/`save_text_touchup_proposal`). `PdfCorpusRepository` (the separate,
  lower-level class in the same file, ~540 lines of asset/build/record persistence, no static/classmethods --
  already a cohesive
  single-responsibility class) has been surveyed and does not look like a good decomposition candidate on its own.
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
- **`llm_inferred`/`human_confirmed_absent` vs. spec's `model_inferred`/`confirmed_absent`:** renamed to match the
  spec exactly, with a lazy migration for existing persisted data (see `_migrate_status_vocabulary` in
  `corpus_builder.py`, next to `_json_read`). Confirmed neither string ever appeared inside a prompt sent to a
  model, so no prompt-contract version bump was needed.
- **The `CORPUS_PROFILES`/`PROFILE_VERSION`/response-models circular import that deferred nine methods across five
  sessions is resolved** by extracting them verbatim into `corpus_models.py` (see "Current state" above). Do not
  re-open this as an open question -- `create`, `preview_schema_group`, `_edit_model`, `_profile_of_build`,
  `_profile_for`, `_refresh_workflow_fields`, `validate_records`, `regenerate_manifest`, and `patch_manifest` are
  all extracted into `corpus_manifest_workflow.py`.
- **A mixin stub shadowed a real method at runtime and broke it silently** (`rerun_metadata_enrichment`, caught by
  the full pytest suite, not by mypy or ruff) when `BuildLifecycleMixin` was first written without wrapping its
  stub block in `if TYPE_CHECKING:`. Fixed, and the same guard retrofitted onto the two earlier mixins, which had
  the identical latent risk. See "The mixin technique" below -- **the `TYPE_CHECKING` guard is mandatory for any
  mixin's stub block, not an optional style choice.**

## Next steps

1. **All seven originally-planned `corpus_builder.py` clusters, every method the circular-import blocker had
   deferred, boundary-segmentation execution, and metadata-enrichment execution are done.**
   `PdfCorpusRepository` was surveyed and does not look worth decomposing on its own (537 lines, no
   static/classmethods, already single-responsibility persistence code). What's left in `PdfCorpusBuildManager` is
   build orchestration (`_run`, `_prepare_build_scope`, `_construct_build_topology`,
   `_persist_build_metadata_stage`, `_schedule_build_enrichment`, `_finalize_build_review`,
   `_rewrite_and_validate`, `publish`) -- entirely stateful, zero `@staticmethod`/`@classmethod` candidates, same
   shape as the two clusters just extracted -- plus a handful of small standalone methods
   (`_write_start_page_to_layout`, `preview_record`, `touchup_record_text`,
   `set_text_touchup_proposal_status`/`save_text_touchup_proposal`) that may or may not be worth their own mixin
   depending on size once the orchestration cluster is out. Follow "The mixin technique" including its
   `TYPE_CHECKING` guard, and expect the same monkeypatch-module gotcha (see "Gotchas learned"): any test that
   patches `cb.some_free_function` where `some_free_function` is called bare from inside the *new* mixin module
   needs to patch that new module instead, not `cb` -- and also check for `cb.some_name` re-exports that quietly
   depended on a *removed* method still needing that name (see the `APP_VERSION` re-export fix from this round).
   `metric_stage_of`/`annotate_boundary_suspects`, two pure functions sitting near where the old models block used
   to be, have not yet been investigated for extraction.
2. **`PdfCorpusBuilder.vue`'s composables/CSS extraction has a real blocker: no test coverage exists for this file at
   all** (no `.stories.ts`, no dedicated Vitest file, not in the 131-scenario DOM baseline) -- confirmed by checking
   before starting, not assumed. Every other decomposition in this effort had a full test suite to verify "no
   behavior change" against; this one does not. **Do not start a large-scale extraction here without first adding
   characterization coverage** (at minimum a `.stories.ts` and/or a baseline scenario exercising its main paths), or
   accept and disclose the higher risk explicitly before touching it. This is why backend work (which has full
   coverage) took priority once the safe frontend wins ran out.
3. **Frontend:** skim `runtime.js` top to bottom for any remaining pure helper still sitting next to
   state-coupled code (the same way `recordTableHelpers.ts` was found -- see "How to find the next pure cluster").
   Most of what's left is small glue (`tr`, `trf`, `shell()`, `setShellRefreshHook`, `getShellSnapshot`,
   `translatedNavLabel`/`translatedSectionLabel`, `currentContext`) or DOM/render-coupled code that stays.
4. **Section C/D from the original runtime.js plan, still not started:** turn the `*Workspace` factories into
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

### The mixin technique, for a cluster that is entirely (or mostly) stateful

`corpus_builder.py`'s remaining clusters (human review, enrichment reruns, and likely build lifecycle next) turned
out to have few or zero `@staticmethod`/`@classmethod` candidates -- their methods call a dozen-plus different
`self.*` members across the manager (`self.repo`, `self._chat_json`, `self._profile_for`,
`self._rewrite_and_validate`, `self._ledger`, ...). Converting a method like that into a free function would mean
threading a dozen-plus dependencies through its signature and every call site -- a much larger, riskier change than
this effort's other extractions, and exactly the kind of change that could introduce a subtle wiring bug in
human-review or enrichment logic (high-stakes: see `AGENTS.md`'s "Human review is an authority event").

**Use a mixin instead.** Move the method bodies verbatim into a new module as a class (`class SomeMixin:`), with
`self` left completely untouched -- no signature edits, no dedent (the methods already have the right
class-member indentation), no call-site rewrites anywhere, because `self.*` still resolves through Python's normal
method resolution order once `PdfCorpusBuildManager` inherits from the mixin
(`class PdfCorpusBuildManager(ReviewActionsMixin, EnrichmentRerunsMixin):`). This is dramatically lower-risk than
the free-function pattern for a stateful cluster, and it has a real, pleasant side effect: **no monkeypatch or
call-site gotcha exists for a mixin.** `monkeypatch.setattr(manager, "some_method", fake)` and
`cb.PdfCorpusBuildManager.some_method` both keep working exactly as before, since Python's attribute lookup does
not care which class in the MRO defines a method.

The one real cost: **mypy checks a mixin's body in isolation** and cannot see that the eventual composed class
provides `self.repo`, `self._rewrite_and_validate`, etc. It reports every one of them as `attr-defined` (92 errors
on the first mixin). Fix with a documented stub block at the top of the mixin class: bare type annotations for
plain attributes the mixin never assigns (`repo: Any`, `_lock: Any` -- typed `Any` rather than their real classes,
since e.g. `PdfCorpusRepository` is defined in `corpus_builder.py` itself and importing it back would be circular),
and one-line method stubs with real signatures and a `...` body for every other `self.*` member the mixin's methods
call (`def _rewrite_and_validate(self, build_id: str, records: list[dict[str, Any]]) -> dict[str, Any]: ...`),
mirroring how an ABC declares an abstract method. Get each stub's exact signature by grepping the real method's
`def` line in `corpus_builder.py` rather than guessing.

**Wrap the entire stub block in `if TYPE_CHECKING:`. This is not optional.** An unguarded `def name(self): ...` is
a real, empty method at runtime, not just a type-checker hint. `PdfCorpusBuildManager`'s own directly-defined
methods always take precedence over any base class's, so a stub is harmless *as long as the real implementation
stays directly on `PdfCorpusBuildManager` itself* -- but the moment that real implementation moves to a **second**
mixin, Python's left-to-right MRO means whichever mixin is listed first in
`class PdfCorpusBuildManager(BuildLifecycleMixin, ReviewActionsMixin, EnrichmentRerunsMixin):` wins for any name
both mixins mention, real implementation or not. This is exactly what happened building
`BuildLifecycleMixin`: it stubs `rerun_metadata_enrichment` (because its own methods call it), but the *real*
`rerun_metadata_enrichment` lives in `EnrichmentRerunsMixin`, listed after it -- so the stub silently won, and
calling it did nothing instead of running. No import error, no mypy error; only the full pytest suite caught it (7
failures, `full backend suite` in the Verification section is not optional for a mixin commit). `TYPE_CHECKING` is
always `False` at runtime, so a guarded stub block never creates real attributes and can never shadow anything,
while mypy (which evaluates `TYPE_CHECKING` as `True`) sees the same signatures either way. Guard every mixin's
stub block this way, including ones that look safe today -- correctness that depends on inheritance order is
fragile the moment a fourth mixin is added.

Any decorator the moved methods use (this effort found `_serialize_record_mutation`, a `@wraps`-based lock
decorator used by 20+ methods across multiple clusters) moves into whichever mixin module needs it, with
`corpus_builder.py` importing it back -- same circular-import handling as a moved pure helper
(`_normalize_text`/`iso_now`); see "Circular imports" below.

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
- **`monkeypatch.setattr(cb, "name", fake)` also silently stops working** if a mixin extraction moves the *caller*
  of `name` (a bare free function, e.g. `_deterministic_boundary_candidates`) into a new module -- the caller now
  resolves `name` against the new module's own globals, not `corpus_builder`'s. Caught by three tests going from
  pass to a wrong-value assertion failure (not an error) when `_segment`/`_segment_candidate_batch` moved into
  `corpus_segmentation_execution.py`. Fix: `monkeypatch.setattr(<new_module>, "name", fake)` and import that module
  in the test (`from app import corpus_segmentation_execution as cse`) -- run the **full** pytest suite after every
  mixin extraction, not just `compileall`/`mypy`/`ruff`, since this class of bug produces no import or type error.
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
