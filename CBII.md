# CBII — Corpus Builder session handoff

Progress and next steps from a long Claude session on the Corpus Builder, ingestion and review
(follows [CBI_PROGRESS.md](CBI_PROGRESS.md), which tracks the `PdfCorpusBuilder.vue` decomposition).
Verify against the code before relying on anything here; AGENTS.md rules apply.

## Open pull requests (merge in this order)

| PR | Branch | State | Notes |
| --- | --- | --- | --- |
| #197 | `claude/audio-key-and-topology` | mergeable, CI running | **Source-unit policies** (default / paragraph / line / sentence / every n characters). This commit was pushed after #194 had merged, so it never reached master. |
| #199 | `claude/record-length-advice` | conflicts (stacked on #197) | Structure-tab notice when source units are too coarse for the requested record length, with one-click fixes. After #197 merges, `git merge origin/master` on the branch (only locale files conflict: keep both sides). |
| #198 | `claude/document-prefill` | conflicts | Front-matter pre-fill (computed / NLP-derived) with suggestions. Same locale-conflict recipe. |

Already merged this session: #186–#196 (see `git log`). #196 = record context reader.

## What was built (all on master unless listed above)

- Go fix / Accept & next / Wikisource via MediaWiki API / record-sizing floors and warnings / `.jsonl.zst` import.
- Retire-and-mint **split, merge, create-from-selection** (`corpus_record_restructure.py`, lineage tombstones, spec "Record identity").
- Validated-claim memory, deterministic **spaCy** POS/NER hints (`nlp_annotations.py`, models in `api/requirements-nlp.txt`).
- Metadata-exemplar diagnosis/backlog, embedding reachability probe (Settings), audio key in Settings, topology ceiling is a warning.
- Save-and-use-selected-text-as-evidence (one atomic, optimistic request), deterministic **page-number detection** (`page_markers.py`).
- Operational record keys kept out of scholarly review (`field_assertions._operational_key`, `isOperationalKey`).
- Source tab redesign, review-in-context neighbours, New schema button.

## Next: record-level pre-fill from metadata memory (agreed design)

The user's clarification: **search with the source span, not the record text** — the span is the evidence
associated with the value.

1. New `memory_prefill.py`, run at record construction (after `annotate_record`, before topology validation).
2. For each record, take each of its source spans/units (`source_block_ids` → block text). Batch-embed all
   spans of the build once (`ChromaStore.embeddings.embed`), then query the exemplar collection
   (`derridai_metadata_exemplars`, class `ChromaMetadataExemplarIndex`) with those vectors.
   Filter: `kind in {positive, absence}`, `field_name in schema fields whose retrieval profile is enabled`,
   `scope_id != this build` (no self-retrieval). Similarity is `1/(1+distance)`; per-field `min_similarity`
   comes from the field's retrieval profile.
3. Aggregate by `(field, value)`. **Obvious** = at least two distinct exemplar records agree with high
   similarity (start ≈ 0.88) and nothing conflicts within ≈ 0.05: pre-fill the value, bind the *matching span* as
   its evidence, confidence = mean similarity (cap 0.9). Everything else stays a **less confident hint**
   (`record["memory_hints"][field] = [{value, similarity, exemplar_id, span_block_id}]`) shown in review and
   passed to the prompt.
4. Provenance: `DerivationMethod` (`field_assertions.py`) is a `Literal`; the spec allows namespaced values, so add
   `derridai:memory`, `derridai:nlp`, `derridai:computed`. Update `_compatibility_status` (map to
   `model_inferred`-like "unreviewed suggestion"), the two `derivation_method` checks in `corpus_builder.py` (~3031)
   and `corpus_reviewer_helpers.py`, and the UI mapping in `CorpusMetadataResolutionPanel.vue` (~line 89).
   Evidence must **not** be marked `reviewed_by: human` (exemplar derivation trusts that flag).
5. Never let a pre-fill confirm anything: authority stays `unreviewed`; human-owned fields are skipped.
6. Failure must be visible: if Chroma/embeddings are unreachable set `build["memory_prefill"] =
   {"status": "unavailable", "error": ...}` and warn; never block the build. Bound work (≈ 3000 spans,
   time budget) and report `truncated`.
7. Tests: fake index returning canned hits; agreement/conflict/threshold cases; evidence = matching span;
   human-owned skip; unavailable path. Do not regress the latency work (batch metadata persistence,
   optimistic feedback).

## Also still to do

- **LLM page-number fallback**: deterministic detection (`page_markers.detect`) already runs first. When
  `page_number_detection.status == "not_found"` and the option is on (default on, can be disabled; never for
  audio), ask the LLM at build start (provider is known then) to classify a *sample of candidate lines*; accept
  only if the answers form a valid sequence under the same acceptance rules. Needs an option in the Source tab
  next to "Detect printed page numbers" and a build-request flag.
- Label memory/NLP/computed values consistently in the record-level UI (manifest editor already shows origin chips).
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
