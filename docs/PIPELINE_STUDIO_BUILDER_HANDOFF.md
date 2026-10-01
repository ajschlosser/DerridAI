# Pipeline Studio Builder Handoff

**Repository:** `ajschlosser/DerridAI`  
**Prepared:** 2026-10-01  
**Work branch:** `feature/pipeline-studio-builder` (PR #368, based on `master`)  
**Related:** [PIPELINE_MIGRATION_HANDOFF.md](PIPELINE_MIGRATION_HANDOFF.md), `AGENTS.md` (Pipeline execution and traceability)

This is an implementation handoff, not a release note. PR #368 landed typed stage ports, input-binding validation, latency/complexity analysis and a from-scratch builder. It deliberately did **not** make rewired pipelines executable. This document covers what remains: a generic executor (step 1), constant inputs (step 2), calibrating the declared complexities (step 3) and smaller follow-ups (step 4). These were items 2–5 of the “what is next” list in the PR discussion (item 1 was browser review); they are numbered 1–4 here. Verify every claim against the code before relying on it.

## 1. State after PR #368

- `api/app/pipelines/contracts.py`: named, typed input/output ports and declared complexity for every strategy. A test (`tests/test_pipeline_wiring_and_analysis.py`) fails if a registered strategy lacks them.
- `api/app/pipelines/wiring.py`: resolves each stage input to one source (explicit binding, graph edge, or run input the purpose supplies). `ordering_only_edges` marks `next` edges that only make a producer run first for an explicit binding. `bindings_changing_wiring` lists bindings that differ from the automatic wiring.
- `api/app/pipelines/complexity.py`, `latency.py`, `analysis.py`: composed complexity, trace-based latency, and `TraceSampler` (30 s cache). Endpoints: `POST /analyze`, `POST /definitions/new-draft`, `GET /strategy-latency`.
- `PipelineStageDefinition.inputs` (`dict[port, list[InputBinding]]`) is omitted from dumps while empty so historical pipeline hashes stay valid. Keep it that way.
- `workflows.runtime_support` marks a version **inspect-only** when `bindings_changing_wiring` is non-empty, because every adapter reads inputs from the graph edges.
- Frontend: `domain/pipelineBindings.ts`, `domain/pipelineAnalysisPresentation.ts`, `composables/usePipelineAnalysis.ts` and `useStrategyLatency.ts` (owned by the container `SystemDataPipelines.vue`), and the components listed in the PR.

Invariants that must survive everything below: purposes still own which strategies run and what the output may be trusted to mean; provenance gates stay mandatory; a pipeline assignment never becomes scholarly authority; the legacy-equivalent pipeline stays the default assignment; no default increase in model calls or retrieval depth (see the user's recorded design preferences: cELF path plus loosenable variants, parity first).

## 2. Step 1 — Generic dataflow executor (largest item)

**Goal.** A saved version whose explicit bindings change the wiring becomes executable, so `runtime_support` stops forcing inspect-only for them.

**Why it does not exist yet.** Each purpose has a code-owned adapter (`workflows.PURPOSE_ADAPTERS`) that compiles the graph into a purpose-specific plan (`compile_research_pipeline`, `compile_evidence_pipeline`, …) and runs a hard-coded sequence. Strategy implementations live inside those modules and read request context directly.

**Recommended first workflow: vector-store search (`store_search`).** It is already the closest thing to an executor:

- `execute_store_search` walks a topological order (`_topological_order`) and calls `_Runner.run(stage, inputs)` with `inputs` as `(source_stage_id, value)` pairs, routing `on_empty/on_unavailable/on_timeout/on_error` edges.
- Its strategies (`_QUERY`, `_DENSE`, `_LEXICAL`, `_KEYWORD`, `_FILTER`, `_RRF`, `_MMR`, `_SELECT`) are self-contained and its built-in pipelines are small.

**Couplings to remove (each is a place the runner reads the graph instead of ports):**

1. `_candidate_depth` peeks at `stage.next[0]` to decide depth (MMR pool vs fusion pool). Replace with an explicit rule driven by the consumer's declared need, or by config.
2. The dense branch calls `mmr_candidates` instead of `search` when the next stage is MMR (it needs embeddings). Make "needs embeddings" a declared output property of the retrieval strategy, not an adjacency check.
3. `_single` raises when a stage receives several result sets, which is the executor's own statement of "single-valued port". Move that check to wiring (it is already `input_multiple_sources`).
4. `compile_store_search_pipeline` rejects MMR unless it directly follows dense. Replace with a port/capability check.

**Design.**

- A shared `pipelines/executor.py` that takes a resolved `PipelineDefinition`, the wiring from `resolve_wiring`, a registry of **handlers** (`strategy_id -> callable(stage, resolved_inputs, context)`), and a run context holding the run inputs. It executes in topological order, passes each stage exactly the values its resolved sources supply (by port name), and enforces the declared output type before handing a value on.
- Reuse, do not rewrite, the trace/fallback machinery (`tracing.py`, `store.py`, the `_Runner` fallback routing). Stage traces must keep recording elapsed time, input/output counts and the resolved pipeline identity; they still must not copy source text, prompts or secrets.
- Handlers are the existing strategy bodies lifted out of `_Runner.run`. Handler lookup is a closed, server-owned map; never execute anything named by a pipeline definition.
- Behaviour parity is the acceptance test. Before moving code, capture characterization output of the six built-in `store_search.*` pipelines on a fixed collection (results, order, traces' stage IDs and counts, fallback paths). The refactor must reproduce it exactly.
- Only when parity holds, let `runtime_support` report such versions as supported for `vector_store_search`. Gate the rest: other purposes keep the current inspect-only rule until migrated.

**Then** migrate the other adapters one at a time, smallest first (memory, metadata precedents, prefill, remap, then evidence recovery, evidence suggestion, Research last). Each migration keeps the legacy-equivalent pipeline as the default and proves parity first. Corpus purposes (`corpus_*`) are single-stage LLM workflows and are the least interesting to rewire.

**Open decisions to put to the user before starting:** which workflow first (the recommendation above is `store_search`); whether loosened or rewired graphs must be flagged in the Studio and in each trace (the recorded preference says yes: runnable but marked); and whether the executor should run independent branches concurrently (today's runners are sequential; the Latency tab already reports both the sum and the longest chain).

**Done when:** a rewired `store_search` version validates, compiles, runs, records a trace, and appears as executable in the Studio; the built-ins produce identical output to before; the adapter-specific "explicit bindings change wiring" rule is lifted only for migrated purposes; `AGENTS.md` no longer says free-form wiring cannot execute for that purpose.

## 3. Step 2 — Constant inputs

**Goal.** An input may take a fixed value (a literal query, a threshold) as well as another stage's output or a run input.

**Depends on step 1** for anything beyond display, because adapters ignore bindings today.

**Shape.** Extend `InputBinding` (in `api/app/pipelines/models.py`) with a third source, `constant`, carrying a value and a declared data type; validate it in `wiring.py` next to `run_input` (type check, bounded size, JSON scalar or small structure only). Constants are pipeline tuning, not domain policy, so apply the user's rule to classify before exposing one: nothing that weakens provenance gates, support thresholds that the purpose fixes, access rules or reviewer decisions may become a constant knob. Add them to the stage inputs UI as a fourth group in the source picker. Include the constant in the pipeline's canonical hash (it already follows from being in the dump) and keep `inputs` omitted while empty.

**Open decision:** whether a constant should be allowed for `query`-typed ports at all (it makes a pipeline ignore the user's question), or only for tuning-like values already expressed as `config`. Ask before building; a likely answer is that constants are for non-query ports and `config` keeps owning numeric settings.

**Done when:** a constant binds, validates, round-trips through save and clone, shows in the wiring panel with its type, and the executor (step 1) delivers it. Tests cover type mismatch, oversize values and hash stability for pipelines without constants.

## 4. Step 3 — Calibrate declared complexity against real traces

**Goal.** Find where a declared cost in `contracts.py` is wrong, using the measured-growth column.

**Method.**

1. Run representative pipelines across at least three corpus/collection sizes and several candidate counts so `latency.fit_scaling` has the distinct input sizes it needs (`MIN_SCALING_POINTS = 8`, at least 3 distinct sizes). Traces already record `input_count`, `output_count`, `elapsed_ms`, provider and model.
2. Use `GET /api/system/pipelines/strategy-latency` for per-strategy `observed_scaling` (exponent, R², points) and `by_model`.
3. Compare each exponent with the declared order: linear in candidates should fit near 1, `select.mmr` (declared `O(n·k²·d)`) well above 1 when `k` varies, and scope scans should track collection size, which the current trace does not record. If collection size matters, add a bounded `scope_size` to `PipelineStageTrace.parameters` (counts only, no text) and fit against it; do not infer it from `input_count`.
4. Where observation disagrees, read the implementation again before editing the declaration. A short, noisy sample is not evidence; require enough runs and a reasonable R².
5. Update `COMPLEXITY_*` terms, the formulas, and the matching locale text (`pipelines.complexity_order.*`, `pipelines.complexity_variable.*`) in both languages; regenerate `pipelineCatalogContract.json` with `scripts/export_pipeline_catalog_fixture.py`.

**Known soft spots to check first:** `rerank.cross_encoder` scores all incoming candidates in the Research path but only the head `top_k` in the evidence adapter (`pipelines/evidence.py`), so its worst-case model-call count is an upper bound; `validate.evidence_support` is declared `O(n·L)` but may be model-assisted; fusion cardinality assumes distinct origins and is an upper bound. `retrieve.chroma_similarity` is declared sublinear in `N` (approximate index) and is only valid for that index type.

**Done when:** each declared cost either agrees with measurement within reason or carries a corrected formula and a comment on how it was checked, and the Complexity tab no longer shows a measured exponent that contradicts its declaration without explanation.

## 5. Step 4 — Smaller follow-ups

- **Stale ordering edge on reset.** `setInputBinding(..., null)` in `web/src/domain/pipelineBindings.ts` removes the binding but leaves any `next` edge that was added only to order a producer, which then fails as `incompatible_stage_types` (see `ordering_only_edges` in `wiring.py`). Record, at binding time, that the edge was added for ordering (for example by returning it from the helper and storing it in editor state) and remove it on reset when nothing else uses it. Do not guess from the graph alone.
- **Edge type labels on the diagram.** Show the data type carried by each `next` edge in `PipelineGraphDiagram.vue`, and mark ordering-only edges distinctly. Keep it readable at the compact density; the diagram is relation-viewport based and edges are SVG paths without labels today, so decide on a hover/focus affordance before adding permanent text.
- **Live validation message friendliness.** While a stage ID is being retyped the draft is briefly invalid and `/analyze` returns 422; the panel then shows the raw error while keeping the last analysis. Consider showing "The draft is incomplete" for 422s.
- **Do not** add a changelog entry now; it belongs to the release cut.

## 6. Working notes and gotchas

- Work in a worktree if the main checkout is mid-rebase. `web/node_modules` must match the lockfile (`npm ci`); a hard-linked copy from an older checkout lacked `@tanstack/vue-query`.
- `pipelineCatalogContract.json` is generated; regenerate it, never `git checkout` it after Prettier. `enUsDefaults.json`: add only new keys; regenerating wholesale from Python drops unrelated keys. i18n `t(key, fallback)` prefers the fallback.
- Tests: `pytest -q -n auto --dist=worksteal`; mypy from `api/` with `--config-file ../mypy.ini` has a baseline of 7 errors in 5 pipeline files; Playwright needs `npm run build` and `build-storybook` first and `CI=1 STORYBOOK_PORT=6117 APP_PORT=5217`; its webServer start exceeds short foreground timeouts, so run it in the background. `npm run build` produces `web/sdk/dist/`, which trips the repo-wide Prettier check; remove it before checking.
- `UiButton` applies attributes to its wrapper span, not the button; give buttons accessible names through slot content.
- Scripted string replacements can silently miss; assert that each landed (a missed dialog insertion was caught only by a test).
- Keep `docs/USER_GUIDE.md` describing current behaviour only; update its "Building a pipeline" subsection when step 1 or 2 changes what users can do, and relax the inspect-only paragraph accordingly.
