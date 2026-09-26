# CBII — Corpus Builder session handoff

Progress and next steps from a long Claude session on the Corpus Builder, ingestion and review
(follows [CBI_PROGRESS.md](CBI_PROGRESS.md), which tracks the `PdfCorpusBuilder.vue` decomposition).
Verify against the code before relying on anything here; AGENTS.md rules apply.

## Open pull requests (merge in this order)

| PR | Branch | Notes |
| --- | --- | --- |
| #197 | `claude/audio-key-and-topology` | **Source-unit policies** (default / paragraph / line / sentence / every n characters). Pushed after #194 merged, so it never reached master. Mergeable. |
| #199 | `claude/record-length-advice` | Stacked on #197: notice when source units are too coarse for the requested record length. |
| #198 | `claude/document-prefill` | Front-matter pre-fill (computed / NLP-derived) with clickable suggestions. |
| #201 | `claude/memory-prefill` | **Record pre-fill from metadata memory, matched on source spans** (done; see below). Adds `derridai:memory|nlp|computed` derivations. |
| #202 | `claude/llm-page-fallback` | **Model-assisted page-number fallback** (done; see below). Small conflict expected with #197 in `sources.ts` / `useCorpusSourceConfiguration.ts`: keep both. |
| #200 | `claude/cbii-handoff` | This file. |

Conflict recipe (locale files only, both sides additive): `git merge origin/master`, resolve `<<<<<<<` blocks by
keeping both sides in `api/app/locales/*.py` and `web/src/i18n/enUsDefaults.json`, then run the two locale tests.

## What was built (all on master unless listed above)

- Go fix / Accept & next / Wikisource via MediaWiki API / record-sizing floors and warnings / `.jsonl.zst` import.
- Retire-and-mint **split, merge, create-from-selection** (`corpus_record_restructure.py`, lineage tombstones, spec "Record identity").
- Validated-claim memory, deterministic **spaCy** POS/NER hints (`nlp_annotations.py`, models in `api/requirements-nlp.txt`).
- Metadata-exemplar diagnosis/backlog, embedding reachability probe (Settings), audio key in Settings, topology ceiling is a warning.
- Save-and-use-selected-text-as-evidence (one atomic, optimistic request), deterministic **page-number detection** (`page_markers.py`).
- Operational record keys kept out of scholarly review (`field_assertions._operational_key`, `isOperationalKey`).
- Source tab redesign, review-in-context neighbours, New schema button.

## Done since the first version of this file

- **Memory pre-fill (#201)**: `api/app/memory_prefill.py`, called from `corpus_builder.py` right after `annotate_record`.
  Queries the exemplar collection with each record's *source spans* (batched embeddings), excludes the current build,
  pre-fills only when ≥ 2 distinct earlier records agree at ≥ 0.88 similarity with no close rival, binds the matching
  span as evidence (`reviewed_by: "memory"`, never human), keeps the rest as `memory_hints` (clickable chips in the field
  editor), enforces closed vocabularies, skips human-owned/filled fields, treats absence as hint-only, and reports failure
  on `build["memory_prefill"]` plus a warning without blocking. Thresholds are constants at the top of the module.
- **LLM page-number fallback (#202)**: `page_markers.llm_candidates` / `detect_with_llm`; the manager's
  `page_marker_chooser(request)` asks the model (`PageMarkerChoiceModel`); the answer is re-verified with the same
  sequence rules. Upload / URL / Gutenberg routes take `page_number_detection = auto | auto_llm | off` and
  `provider_profile_id`; the Source tab has the checkbox (default on).

## Also still to do

- Real-model check of the page-number fallback and memory pre-fill (only unit-tested with fakes so far).
- A build-request switch and a Settings toggle for `memory_prefill` (the backend flag `request["memory_prefill"]` exists, default on).
- Advanced exception limits UX (single linked range control; make invalid states impossible).
- Digital libraries: "Start collection download" as a real background job; results UI redesign.
- DERRIDAI spec conformance matrix (one test per MUST/MUST NOT row); PROV / RO-Crate exporters are not started.
- Browser IndexedDB: the user said "never mind for now"; the restore direction is still unclear (ask first).
- Ideas discussed, not started: rules-as-data pipeline UI (glass-box first), desktop wrapper (Tauri/Electron +
  PyInstaller sidecar), mobile as a thin client.

## Working notes and gotchas

- Python venv is at `../../../.venv` relative to the worktree; run backend tests with
  `PYTHONPATH=api ../../../.venv/bin/python -m pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py`
  and the contract test with `-m contract tests/test_frontend_api_contract.py`. Some tests need `PYTHONPATH=api`
  when run alone. Scripts that import `app.*` need `CHROMA_DATA_ROOT`, `CHROMA_PATH`, `AUTH_DB_PATH`,
  `SYSTEM_DB_PATH` pointed at a temp dir.
- CI gates: ruff (`api/app tests scripts/check_frontend_api_contract.py`), mypy, ESLint `--max-warnings 0`,
  Prettier (`npm run format:repo:check`), `vue-tsc` for app and tests, Vitest, `build:ci`, Storybook build,
  Playwright e2e / legacy-DOM / a11y. spaCy models are deliberately *not* in `api/requirements.txt` (CI size).
- **Legacy DOM baselines** (`web/tests/e2e/legacy-dom-baseline.spec.ts-snapshots/*.html`) change whenever Settings
  markup changes: `npm run test:e2e:legacy -- --update-snapshots`, then restore `<p>Build <hash></p>` (the local run
  writes the real commit hash) and review the diff.
- **Locale merges**: every new string goes into `api/app/locales/en_us.py`, `fr_ca.py` and
  `web/src/i18n/enUsDefaults.json`. Concurrent PRs conflict only there; resolve by keeping both sides, then run
  `tests/test_locale_dictionaries.py` and `tests/test_locale_and_accessibility_floor.py`.
- New corpus-build routes must be classified in `tests/test_second_opinion_scrub.py` (`CARRIES_RECORDS` or
  `BUILD_LEVEL`).
- **Push discipline**: a commit pushed to a PR branch *after* the PR was merged is lost (this happened to the
  source-unit commit). Check `git log origin/master..origin/<branch>` before assuming work landed.
- Storybook locale only sets `lang`/`dir`; to see French strings, inject the real dictionary into the Pinia
  `i18n` store from the story iframe (see the screenshot scripts approach used for the Source tab).
- Screenshots for visual review: build Storybook (`npx storybook build -o <dir>`), serve it, drive with
  Playwright (mock API routes with `page.route`), and run axe (`@axe-core/playwright`, use `browser.newContext()`).
- Record sizing floors are 100 / 10 / 100 / 100 characters (API and UI). A 100-character target is only reachable
  with small units (Structure → Source units); see `tests/test_unit_policy.py::test_small_records_need_small_units`.

## Memory notes

The user's preferred local model for live-provider runs is `qwen3.5:4b` (see the auto-memory index).
