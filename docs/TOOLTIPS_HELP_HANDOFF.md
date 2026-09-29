# Tooltip and Helper-Text Cleanup Handoff

## Purpose

This branch implements the first pass of a full-app audit of helper text, tooltips, technical labels, status explanations, and discoverability. The goal is not to hide documentation. The goal is to put each kind of explanation in the right UI pattern:

- **Persistent helper text** for consequences, authority/provenance, scope, destructive actions, security, publication, state changes, and anything a user must understand before making a decision.
- **Tooltips** for definitions, abbreviations, technical parameter meanings, compact secondary detail, and unfamiliar status terminology.
- **Disclosures / Help Center links** for explanations too long for a tooltip and not essential to keep permanently visible.
- **Inline validation/error text** for current invalid state, not general documentation.
- **No duplicate explanation** in both persistent helper text and a tooltip unless the two deliberately serve different levels of detail.

The primary audience is a non-technical academic researcher. Technical implementation vocabulary should remain available without dominating the interface.

## Branch state

Branch: `task/tooltips-help`

The branch was created from `master` at:

`44c9707eb26699a10c5dc949b0b97f037fc541bf`

At the time of this handoff, `master` has advanced. GitHub reports the branch as **29 commits ahead and 6 commits behind** current `master`, whose compared base commit is:

`db0eeb9daae3d8847fd119299b7c7a7d535ceb20`

Before continuing substantial work, sync this branch with current `master` and resolve conflicts conservatively. Do not discard branch work in order to make the update easier.

All work described below is already committed to the remote branch. No uncommitted local work is required for the handoff.

### Progress update — 2026-09-29

The branch has now been synchronized with `master` at `db0eeb9daae3d8847fd119299b7c7a7d535ceb20` by merge commit `8ac4be754d4b97576fe004b4691e94b7315d58d1`. The first post-handoff implementation pass has also started:

- `UiTooltip` now supports a compact content-trigger mode so status chips can expose help without adding a second information icon.
- `UiStatusBadge` no longer uses native `title` for its `help` text.
- `UiHealthChip` no longer uses native `title` for its `detail` text.
- Focused Vitest coverage now checks keyboard focus, Escape, click/touch-style toggling, accessible descriptions, and the absence of native-title help on these primitives.

The next priority remains the repository-wide native-title / disabled-reason audit, followed by Corpus Builder and Record Review.

### Completion update — 2026-09-29

The finishing pass has now covered the shared tooltip contract, major native-title and disabled-reason dependencies, Corpus Builder sizing/source/review surfaces, Record review and attribution semantics, Search, Records, Works, Semantic Map, Operations, Sources, Languages, Users/Roles, System Data, provider selection, Pipeline Studio, and supporting shell controls.

The branch is synchronized with current `master` at `d56ec6596647400c16409724bb4b3ecb76abf983` by merge commit `92e48ea3711da708d8b529393c3b9f5dcee39832`. en-US and fr-CA have exact key parity, and the generated frontend English defaults have been refreshed from the merged locale dictionary.

Repository-wide Prettier formatting has been applied. The implementation is ready for the repository CI gate. Any remaining native `title` uses should be limited to non-help metadata/truncation affordances rather than being the primary way a major workflow communicates a definition, disabled reason, or decision consequence.

## Files currently changed on the branch

The current branch differs from `master` in these files:

- `api/app/locales/en_us.py`
- `api/app/locales/fr_ca.py`
- `web/src/components/CorpusExecutionSettings.vue`
- `web/src/components/CorpusFieldOwnershipBadge.vue`
- `web/src/components/metadata-memory/MetadataMemoryTable.vue`
- `web/src/components/metadata-schemas/SchemaFieldForm.vue`
- `web/src/components/pipelines/PipelineComparisonPanel.vue`
- `web/src/components/pipelines/PipelineDefinitionEditor.vue`
- `web/src/components/pipelines/PipelineStageEditor.vue`
- `web/src/components/providers/ProviderTuningFields.vue`
- `web/src/components/research/ResearchSettingsDrawer.vue`
- `web/src/components/system-data/SystemDataDatabases.vue`
- `web/src/components/ui/UiField.vue`
- `web/src/components/vector/VectorBackendPanel.vue`
- `web/src/views/DashboardView.vue`
- `web/src/views/SearchView.vue`
- `web/src/views/SettingsView.vue`

Treat this as a partial implementation rather than proof that every audit item in those files is complete.

## Shared implementation already started

### `UiField`

`UiField.vue` now supports a dedicated `tooltip` and optional `tooltipLabel` prop in addition to persistent `hint` text.

Use this contract intentionally:

- `hint`: short persistent information needed while making the decision.
- `tooltip`: a compact definition or secondary explanation.
- `error`: current validation state.
- Do not feed the same text into both `hint` and `tooltip`.

This is the preferred path for continuing form cleanup instead of hand-building an information icon beside every `UiField`.

### Canonical tooltip copy

Where possible, reuse Help Center glossary copy rather than creating competing definitions. Existing useful keys include:

- `help.glossary.context_window.definition`
- `help.glossary.temperature.definition`
- `help.glossary.top_p.definition`
- `help.glossary.seed.definition`
- `help.glossary.fetch_k.definition`
- `help.glossary.mmr_lambda.definition`
- `help.glossary.rrf_k.definition`
- `help.glossary.rerank_top_n.definition`
- `help.glossary.cross_encoder.definition`
- `help.glossary.query_decomposition.definition`
- `help.glossary.evidence_budget.definition`
- `help.glossary.max_chars_evidence.definition`

New provider-oriented tooltip copy has also been added in en-US / fr-CA for output limits, `top_k`, thinking/reasoning mode, keep-alive behavior, and provider-specific JSON options.

Do not fork the same concept into different explanations on Settings, Research, Providers, and Corpus Builder unless the context genuinely changes the meaning.

## Work already implemented or partially implemented

### Research settings

`ResearchSettingsDrawer.vue` has begun moving compact parameter definitions out of persistent helper text and into `UiTooltip`.

Work includes retrieval parameters such as:

- retrieval `k`
- `fetch_k`
- MMR lambda
- RRF k
- rerank top N
- reranker / cross-encoder terminology
- query decomposition
- generation context window
- maximum output
- thinking mode
- temperature
- `top_p`
- `top_k`
- seed
- keep-alive
- advanced provider JSON

Prior-response memory and prior-claim memory now distinguish concise persistent consequences from fuller tooltip detail. Prompt-metadata guidance has also been split into a shorter visible explanation and a technical tooltip.

Continue to protect the important provenance rules: cached responses are advisory rather than source evidence, and prior claims cannot supply citations absent from the current evidence.

### Provider tuning

`ProviderTuningFields.vue` now exposes tooltips for major technical controls instead of presenting naked parameter names.

The localization layer includes new provider help strings. Continue the pattern for any remaining provider-specific controls, especially if `min_p`, repeat penalty, Mirostat, Mirostat eta/tau, model-kind semantics, or raw options are still exposed without sufficient context after syncing with master.

### Corpus Builder execution settings

`CorpusExecutionSettings.vue` has begun adding tooltips to generation parameters, context size, concurrency, segmentation/output budgets, and other technical controls.

This does **not** complete the Corpus Builder audit. See the outstanding section below.

### Settings retrieval defaults

`SettingsView.vue` now uses the `UiField.tooltip` contract for several retrieval defaults instead of persistent hints, including retrieval count, rerank depth, `fetch_k`, MMR lambda, RRF k, cross-encoder concepts, query decomposition, and evidence-character budgets.

Do not convert security, reset, backup, or other destructive-action warnings to tooltips.

### Vector backend

`VectorBackendPanel.vue` has moved basic Chroma connection definitions such as path, URL, tenant, and database from persistent hints to tooltips.

Keep backend-switching consequences visible; only the field definitions belong in tooltips.

### Other branch work already present

The branch also contains tooltip/helper-text work in:

- Dashboard
- Search
- Metadata Schema field editing
- Pipeline definition/stage/comparison UI
- Metadata Memory table
- Corpus field-ownership badge
- System Data database browser

Review those implementations after rebasing. Do not assume every change is finished merely because the file is modified.

## Required design rules for the remaining pass

### Keep visible

Do **not** hide these categories behind a tooltip:

1. A setting changes what becomes authoritative.
2. A choice changes publication, review, evidence, or memory behavior.
3. A destructive action can delete, reset, replace, or invalidate data.
4. A security or permissions choice changes access.
5. A backend/provider/store switch changes which data is in scope.
6. A human-confirmed value will be reused as precedent or memory.
7. An action can overwrite, rerun, requeue, retry, or otherwise modify derived state.
8. A warning explains why the system is blocking an action.
9. A concept is essential to interpreting a visualization correctly, e.g. “co-occurrence is not scholarly evidence.”

### Use a tooltip

Prefer a tooltip for:

- abbreviations;
- parameter definitions;
- technical names;
- units when non-obvious;
- status-badge terminology;
- derived score meanings;
- unfamiliar infrastructure vocabulary;
- icon-only controls;
- disabled reasons when the reason can be expressed briefly.

### Use a disclosure or Help Center

Use a disclosure, “Learn more” link, or Help Center destination when an explanation needs more than roughly two short sentences. Do not create paragraph-sized tooltips.

### Avoid native `title` as primary help

Native HTML `title` is not an adequate primary help pattern for keyboard, touch, or consistent styling. Replace meaningful uses with `UiTooltip`, a real popover, or visible text as appropriate.

## Outstanding audit work

The following is the remaining work from the full-app audit. Work top-down by priority and verify the current implementation before editing because `master` is moving quickly.

### Critical: cross-app primitives and status semantics

#### `UiStatusBadge`

Current audit finding: meaningful `help` is exposed through native `title` plus screen-reader text.

Required work:

- Replace native-title-only behavior with an accessible `UiTooltip` or equivalent interaction.
- Preserve the visible status label and dot.
- Tooltip must work on hover, keyboard focus, click/touch, and Escape.
- Do not turn every badge into an info button if there is no help text.

#### `UiHealthChip`

Current audit finding: `detail` also relies on native `title`.

Required work:

- Migrate meaningful detail to the shared tooltip behavior.
- Keep health state itself visible.
- Do not hide errors that users need in order to recover; long failure information belongs inline.

#### Icon-only controls

Search the app for remaining `title=`, `:title=`, and ad-hoc hover-only help.

Priority examples identified in the audit:

- sidebar controls;
- rotate controls;
- annotation open actions;
- record previous/next actions;
- source warnings;
- refresh actions;
- disabled icon actions.

Use the shared accessible tooltip pattern rather than native title.

#### Disabled reasons

The app currently mixes `data-tooltip`, native title, `disabledReason`, and inline explanatory copy.

Standardize disabled-reason behavior through shared primitives. The reason must be available to keyboard and touch users. Do not make a disabled native button the only trigger because disabled elements cannot reliably receive focus/events.

### Critical: Corpus Builder remaining work

The Corpus Builder is still the densest technical surface.

#### Record sizing

Inspect `CorpusRecordSizingSettings.vue` and related components.

Audit recommendation:

- Keep the visual sizing/ruler concept and one concise persistent explanation.
- Move character/word conversion detail, tolerances, absolute limits, and auto-sizing definitions into tooltips.
- Keep warnings about truncation or source-boundary consequences visible.

#### Stage timeouts

Execution settings currently have several timeout fields.

Required behavior:

- One visible section-level explanation of what a timeout means operationally.
- Tooltip each field only if the stage name or scope is not obvious.
- Preserve the fact that timeout/failure becomes reviewable rather than silently accepted.

#### Source facts

Inspect `CorpusSourceFacts.vue`.

Audit recommendation:

- Replace the long source-facts paragraph with specific tooltips for “source units,” OCR pages, deterministic author candidates, and similar terms.
- Keep source-quality warnings visible.

#### Source setup / ingestion

Inspect `CorpusSourceIngest.vue`, `PdfCorpusBuilder.vue`, and format-specific setup components.

Required:

- Supported formats can remain compactly visible.
- Move implementation details about how each medium becomes spans/records into tooltip or Help Center.
- Media-specific controls must remain media-specific; do not reintroduce PDF language for audio/images/other formats.

#### Document intelligence

The warning that document-intelligence output is a navigation aid rather than evidence/authority is epistemically important.

- Keep that warning visible.
- Definitions such as coreference/entity cluster can be tooltips.

#### Retry / rerun / requeue / provider changes

These are consequential actions.

- Keep the consequence visible near the action.
- Add concise tooltips to the action labels only as supplementary clarification.
- Do not replace the consequence with a tooltip.

#### Review-state badges

Ensure tooltips exist and are consistent for:

- Needs review
- LLM checked
- confidence not reported / unknown confidence
- evidence status
- authority
- confirmed absence
- deterministic/model disagreement
- stale evidence/binding
- retryable/failed enrichment states

A tooltip must distinguish “checked” from “verified.” Missing confidence must not be presented as zero confidence.

### Critical: Record View / review surfaces

Inspect `RecordInspector.vue`, `RecordWorkspaceHeader.vue`, `RecordTraceabilityExplorer.vue`, metadata review components, and assertion/evidence panels.

Add or normalize help for:

- authority state;
- evaluation status;
- assertion source/method;
- confidence;
- evidence binding;
- revision/staleness;
- speaker vs. position holder;
- target and stance;
- derived vs. reviewed metadata;
- model-inferred vs. human-confirmed values.

Do not add more long paragraphs to the traceability explorer. Keep core interpretation/scope warnings visible and move definition-level concepts into tooltips.

### Critical: Metadata Schemas remaining work

The branch modifies `SchemaFieldForm.vue`, but complete the whole schema workflow.

#### Field role

The original tooltip was too long and too important.

Desired UI:

- Short visible descriptions for the available role choices (scholarly, structural, document, operational), ideally in option descriptions or compact helper text.
- Optional tooltip for additional detail.
- Do not put the entire multi-category explanation back into one long tooltip.

#### Field scope

The record-level vs corpus-level distinction is decision-critical.

- Keep the core distinction visible.
- Tooltip or Help Center can explain how this differs from later bulk editing.

#### Review visibility

Show concise descriptions of “Show in review,” “Show in details,” and “Hidden” at selection time. This should not require memorizing a paragraph tooltip.

#### Strict allowed values

Tooltip is appropriate but should be one short sentence. Avoid paragraph-sized help.

#### POS / NER tags

Tooltip is appropriate. Use concise language such as:

“Hints only; they do not populate the field.”

The full taxonomy belongs in autocomplete / Help Center, not the tooltip.

#### Memory & retrieval

Audit remaining schema-memory controls.

- Keep one concise visible section intro explaining that reviewed examples can guide future model runs and do not rewrite existing records.
- Move individual numerical/tuning controls into tooltips.
- Remove duplicate section-level tooltip + section-level helper text if both say the same thing.
- Keep provenance/authority consequences visible.

### High: Pipeline Studio remaining work

The branch already touches Pipeline definition, stage, and comparison components. Re-evaluate after rebasing.

#### Strategy

Keep visibly stated that a strategy is a registered server operation, not arbitrary executable code. This is architecture/safety semantics, not tooltip trivia.

#### Pipeline identity/version

Show the stable-ID + immutable-version model persistently in the identity area. Tooltips can explain details.

#### Status

Draft / Active / Disabled semantics should be visible at selection time or in option descriptions, not buried in a long tooltip.

#### Entry stage

Keep a concise persistent description where edited. Tooltip may expand.

#### Deterministic / learned / LLM labels

These are definition-level concepts and are good tooltip candidates.

#### Comparison metrics

Candidate overlap / Jaccard / final-evidence overlap need a visible warning that overlap measures similarity, not quality. Formula/details can stay in tooltips.

#### Dry-run explanation

Keep it as persistent/disclosed explanatory copy. It is too long and too consequential for a tooltip.

#### Strategy config fields

Existing tooltip-driven config help is generally the right pattern. Enforce concise tooltip length and use Help Center for long explanations.

### High: Search remaining work

The branch modifies `SearchView.vue`; verify all of the following are actually complete.

- Retrieval method definitions for similarity, MMR, lexical, hybrid/filter-only where applicable.
- `fetch_k` tooltip.
- MMR lambda tooltip.
- Similarity threshold terminology where exposed.
- “Advanced filters” explanation should be compact and not take persistent vertical space unless needed.
- Saved views / recent searches browser-storage semantics can be tooltips.
- Do not hide active-filter state or why a search returned no results.

### High: Semantic Map

Add help for:

- edge strength;
- node size/weight;
- co-occurrence;
- derived relationship;
- semantic similarity score if displayed.

Keep visible the caveat that proximity/co-occurrence is a derived navigation signal, not proof of a philosophical or causal relation.

### High: Relationships

Add concise tooltips for specialized relationship terminology:

- relation direction;
- speaker;
- position holder;
- target;
- stance;
- proposition;
- evidence/provenance markers.

Preserve the full speaker → position holder → stance → proposition → evidence distinctions. Do not flatten them into a generic “relationship” explanation.

### High: Records table

Add/normalize tooltips for non-obvious columns/badges such as:

- review status;
- authority;
- database/synchronization state;
- provenance indicators;
- canonical vs browser-local state.

The Copy View Link action should explain what state is encoded in the URL. A tooltip is appropriate.

### High: Works

The empty-state phrase “No indexed values in the loaded records” was identified as opaque.

Replace it with visible plain-language explanation of:

- which metadata/indexed values are required for the metric;
- why the metric cannot be computed yet;
- what action could make it available.

If “indexed values” remains a term, define it with a tooltip.

### High: Corpus Data / Vector Stores

Beyond the Chroma field-definition work already started:

- Keep backend-switch consequences visible.
- Shorten the long “unsynced changes” message to the user-facing consequence; move implementation detail about caches/suppression to disclosure/tooltip.
- When an embedding model is locked because records exist, keep the lock consequence visible and use tooltip to explain rebuild requirements.
- Review collection-name field helpers; basic naming definitions can be tooltips.

### High: System Data

`SystemDataDatabases.vue` has branch changes. Verify the intended state:

- Table descriptions should be visible under the selected table heading.
- The same description may remain as a tooltip in the narrow table-directory rail.
- Do not show the exact same description as both inline text and a tooltip in the main table heading.
- Read-only policy and “use purpose-built admin pages for changes” should remain visible.

Advanced System Data query/command surfaces must retain validation and plain-language execution explanations. Tooltips should only define syntax/operators.

### High: Operations

The drag-grip interaction is nonstandard and the audit found its instructions hidden in native title/ARIA.

Add a real focusable tooltip explaining drag / double-click / keyboard behavior.

For cancelled jobs, keep “partial results may still be available” visible when applicable.

### Medium: Dashboard

The branch includes Dashboard changes. Verify:

- Appearance, Language, and Provider quick-setting cards do not carry redundant explanatory paragraphs.
- Card-heading tooltip is enough for secondary context.
- Corpus Builds or workflow-status cards may keep a short visible sentence because their state/action is less obvious.

### Medium: Response Library

Keep visible:

- provenance/citation consequences;
- grading consequences that affect future memory eligibility.

Move definition-level content into tooltips:

- retrieval diagnostics;
- query decomposition;
- reranker;
- self-grade vs independent grade terminology.

### Medium: Sources

Add/normalize help for:

- acquisition/capture state badges;
- discovery/source states;
- Retry failed.

Replace meaningful disabled native `title` explanations with shared tooltip behavior.

### Medium: Metadata Memory

The branch modifies `MetadataMemoryTable.vue`. Verify consistent tooltip coverage for:

- authority;
- correction;
- confirmed absence;
- stale binding;
- evidence-bound state.

Stat-card tooltips are an appropriate pattern if concise.

### Medium: Languages

Move basic field definitions to tooltips:

- locale code;
- display name;
- flag;
- source language.

Keep visible or in an explicit disclosure:

- content-policy effects;
- atomic install behavior;
- partial-resume semantics.

### Medium: Users and Roles

Users:

- Password requirements stay visible while editing a password.
- Delete/deactivation consequences belong in confirmation/persistent warning, not tooltip.
- Basic “create account” explanatory copy can be shortened or moved to a section-level tooltip if redundant.

Roles:

- Keep human-readable permission descriptions visible next to capabilities; hiding them would make authorization changes unsafe.
- Tooltip may explain technical capability IDs only.

### Medium: Compare

Overall pattern was acceptable.

- Keep scratch-copy semantics and the fact that audit history is intentionally hidden.
- Shorten researcher-specific prose where repetitive.
- Do not turn the core read-only semantics into a tooltip.

### Low / generally good

Annotations currently has a reasonable amount of visible help. Avoid adding explanatory clutter. Ensure existing annotation hover/focus detail remains keyboard- and touch-accessible.

The Help Center itself is the canonical detailed reference and should remain scan-first rather than becoming a page full of tooltip-only definitions.

## Search queries for the finishing pass

Run repository searches after rebasing for all of the following:

```
title=
:title=
data-tooltip
UiTooltip
:hint=
class="help
class="hint
aria-describedby
disabledReason
_help
_description
_hint
_note
```

For locale files, inspect helper values longer than roughly 120 characters. Long length alone is not a bug; it is a signal to decide whether the text should be persistent, shortened, split, or moved into Help Center/disclosure.

Also inspect visible technical labels with no nearby help, especially:

```
top_k
top_p
min_p
fetch_k
lambda
rrf
rerank
cross-encoder
temperature
seed
context window
num_ctx
num_predict
Mirostat
embedding
Chroma
authority
provenance
confidence
stale
binding
precedent
derived
```

## Localization requirements

Every new user-facing string must be added to both:

- `api/app/locales/en_us.py`
- `api/app/locales/fr_ca.py`

Do not add English-only fallback prose as the final implementation.

Where frontend defaults exist for the same keys, keep them synchronized with locale content.

Preserve plain-language wording. For academic users, explain what a setting _does_ before naming its algorithmic implementation.

## Accessibility requirements

All new tooltip/help behavior must satisfy the existing WCAG 2.2 AA direction:

- Tooltip trigger reachable by keyboard.
- Tooltip appears on focus, not hover only.
- Escape closes it.
- Touch/click can reveal it.
- Trigger has an accessible name.
- Help is not conveyed by color alone.
- Tooltips do not contain essential interactive controls.
- Tooltip content is not clipped by scrolling panes/modals.
- Forced-colors/high-contrast states remain usable.
- Avoid text smaller than the app’s 12px accessibility floor.
- Do not remove visible information if doing so would make a decision ambiguous for users who never open tooltips.

## Testing / validation to add or update

At minimum, finish with:

1. Frontend typecheck.
2. Frontend lint.
3. Prettier/repository format check.
4. Unit/component tests.
5. Production build.
6. Storybook build.
7. Existing frontend E2E shards.
8. Dedicated WCAG 2.2 AA sweep.
9. French/long-string coverage on representative dense forms.
10. Dark/high-contrast/forced-colors snapshots where the affected primitives are covered.

Add focused tests for `UiField.tooltip` and for any shared status-chip tooltip migration. Verify keyboard focus, Escape, click/touch toggling, and accessible naming.

## Completion criteria

The work is complete when:

- technical parameters across Research, Providers, Settings, Corpus Builder, Search, and Pipelines have consistent concise definitions;
- important provenance/authority/destructive consequences remain visible;
- no major workflow depends on native `title` as its primary explanation;
- no dense form repeats the same paragraph as both helper text and tooltip;
- no major review/status badge is unexplained;
- the Help Center remains the detailed canonical reference;
- en-US and fr-CA remain in parity;
- branch is synchronized with current `master`;
- full CI is green.

## Suggested order for the next agent

1. Sync `task/tooltips-help` with latest `master`.
2. Run formatting/typecheck immediately; fix any merge fallout before adding more changes.
3. Finish shared primitives: `UiStatusBadge`, `UiHealthChip`, native-title audit, disabled reasons.
4. Finish Corpus Builder and Record Review.
5. Finish Metadata Schemas and Pipeline Studio.
6. Finish Search, Records, Works, Semantic Map, Relationships, and Corpus Data.
7. Finish secondary admin surfaces: Operations, Sources, Metadata Memory, Languages, Users/Roles.
8. Run the repository-wide searches above again.
9. Add/adjust tests and Storybook examples for the shared tooltip contract.
10. Run complete CI and fix failures rather than weakening checks.

Do not open a PR until the branch has been synchronized with `master`, the full audit pass is complete, and CI is green.
