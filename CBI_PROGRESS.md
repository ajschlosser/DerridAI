# Corpus Builder UX Redesign Progress

Branch: `task/corpus-builder-visible-ux`

Pull request: #179 — Redesign Corpus Builder workspace UX

Base: current `master`; branch is zero commits behind.

## Visible Corpus Builder redesign

Completed and pushed:

- Replaced the visible A–H configuration metaphor with Source / Structure / Enrichment /
  Metadata / Advanced workspace navigation.
- Added keyboard-accessible configuration navigation and Storybook coverage.
- Added a contextual workspace header carrying source, build, and publication context.
- Reworked build readiness into a compact sticky command bar with details on demand.
- Flattened configuration presentation so the active workspace no longer looks like a stack of
  equally weighted cards.
- Kept Review as the dominant scholarly workspace.
- Kept Run Monitor diagnostics reachable above the sticky review frame.
- Preserved the Review session bar as the persistent header inside scholarly review.
- Continued Finish → Publication readiness semantics and immutable-snapshot framing.
- Added English and Canadian French copy for the new workspace controls.

## Metadata review regressions fixed

- Restored editing for fields with canonical FieldAssertion provenance. Provenance and editing are
  no longer mutually exclusive.
- Added safe metadata value unwrapping/rendering so compatibility envelopes do not display as
  `[object Object]`.
- Sanitized autocomplete at the shared known-values boundary. Source-block IDs, serialized
  JSON/assessment fragments, placeholders, and oversized runtime strings are rejected.
- Constrained observed autocomplete values to reviewable metadata fields instead of arbitrary
  Record properties.
- Fixed Focus Review so **Save all suggestions** forwards to the shared batch-save path.
- Hardened batch metadata persistence and generic FieldAssertion identity resolution.
- Added pending, success, and failure handling for batch suggestion saves.
- Fixed **Accept & next** optimistic state and fallback navigation.
- Filtered acceptance blockers through the reviewable metadata contract so operational fields
  cannot block scholarly Record acceptance.

## Generic field-role contract

Schema fields now carry product semantics independently of arbitrary storage names:

- `role`: `scholarly | structural | document | operational`
- `review_visibility`: `primary | details | hidden`

The schema editor exposes both properties. Ordinary Record review is derived from locked structural
fields, the pinned schema, canonical scholarly assertions, and inherited document metadata.
Operational/runtime fields such as `text_revision_history`, execution ledgers, source arrays,
review events, and assertion-storage internals are excluded from ordinary scholarly metadata
review.

## Structured-output contradiction handling

The metadata response validator no longer discards an otherwise parseable metadata-family response
when a model returns contradictory assessment/value semantics such as:

- a value plus `outcome=no_supported_value`;
- an empty value plus `outcome=supported_value`;
- `outcome=uncertain` with `needs_review=false`.

The proposed value is retained for human inspection. The field assessment becomes
`outcome=uncertain`, `needs_review=true`, with an explicit structured-output contradiction reason.
This keeps the failure visible without turning one field contradiction into a whole-family
retry/failure.

## Metadata exemplar projection

- Derived `derridai_metadata_exemplars` collection creation is deterministic on first use.
- Supported Chroma constructor differences are handled without weakening collection metadata.
- Collection-creation failures are no longer masked by a misleading follow-up
  `Collection ... does not exist` error.
- Canonical reviewed records/assertions remain authoritative; Chroma remains rebuildable derived
  state.

## Regression coverage

Added coverage for:

- editing while FieldAssertion provenance is present;
- structured metadata envelope rendering;
- runtime/JSON/source-block autocomplete rejection;
- Focus Review Save-all forwarding;
- authoritative batch suggestion persistence;
- operational-field filtering and field-role visibility;
- Accept & next navigation and fallback;
- contradictory LLM assessment normalization;
- missing derived exemplar collection creation and truthful initialization failures;
- accessible configuration-tab composition.

## Post-#179 workflow reliability follow-up

A fresh `task/corpus-builder-workflow-reliability` branch was created from remote
`master` at `bd9ca93c6066a227285a61f1b494566acacac0b3`, the #179 merge commit.

Current fixes:

- Review queue/context changes now clear stale Record selection before fetching the destination
  queue, so **Continue review**, rejected/source/metadata repair actions, and other queue switches
  cannot preserve an invisible Record from the previous queue.
- Publication validation repair targets the validation Record directly in the all-Records scope
  instead of assuming every validator finding is also a member of the generic Issues queue.
- Publication blockers now route to their owning review surfaces:
  - `record_attention` → Issues;
  - `boundary_attention` → Topology;
  - `required_metadata` → Metadata;
  - `metadata_validation` → validation-targeted Record review;
  - source blockers → Source review.
- Text review now applies the authoritative server Record after persistence. This fixes
  **Mark reviewed** appearing to do nothing when the server changes only
  `text_review_status`/`text_reviewed_at`.
- Configuration tabs now expose a stronger selected-state treatment using semantic tokens and a
  forced-colors fallback, with regression coverage that verifies the controlled `v-model` state
  actually moves between tabs.
- Ollama embedding 404s now report that both the current `/api/embed` and legacy
  `/api/embeddings` calls failed and point to base URL/version/model configuration instead of
  leaking a raw HTTP exception as the main explanation.
- Metadata-exemplar projection warnings now explicitly say that reviewed metadata is durable and
  that only the rebuildable semantic example index is pending; this projection failure does not
  block Record review or publication.

Open PR #181 also touches `PdfCorpusBuilder.vue` for Source-ingestion modernization. This branch
keeps its edits to that parent component to narrow controller/event wiring so rebasing after #181
should remain localized.

## Shared embedding-provider contract

System-owned derived vector projections now follow the same embedding defaults used by ordinary
Chroma collection creation instead of independently falling back to the process-wide Ollama URL.

- Embedding defaults are persisted in the durable server system store and included in full
  configuration backup/restore.
- Settings can select Chroma default, precomputed vectors, legacy Ollama, or a named provider
  profile; saving the default updates both the browser workspace and the server-owned contract.
- Existing browser-only defaults are migrated on first Settings load. An unpersisted legacy
  `ollama` default resolves to the first configured Ollama provider profile, matching the Vector
  Store creation wizard's existing behavior.
- `ChromaStore` resolves omitted provider/model settings through the server-owned contract.
- The derived `derridai_metadata_exemplars` collection records that contract and is rebuilt from
  canonical reviewed metadata when the configured provider/model changes.
- A precomputed-vector default is rejected for metadata exemplars because that projection needs to
  generate query/document embeddings; canonical review data remains authoritative and unaffected.
- Vector Store preflight now accepts `profile:<id>` providers, and Ollama model selections are no
  longer dropped from preflight/create requests.
- Health/config diagnostics report the effective configured embedding provider/model rather than
  only the environment fallback.

Regression coverage includes durable system-setting round trips, provider-profile defaults,
legacy-Ollama migration, exemplar rebuild on embedding-contract changes, precomputed rejection, and
Settings persistence.

## Validation status

Focused regression coverage has been added for:

- stale-selection clearing on review queue changes;
- validation Record deep links;
- topology/Issues publication repair routing;
- authoritative **Mark reviewed** reconciliation;
- configuration-tab active state;
- actionable Ollama embedding 404 diagnostics.

The branch still requires the repository CI gate set before merge. Do not claim release readiness
until those required checks pass.

## Configuration workspace decomposition

A follow-up branch, `task/corpus-builder-configuration-workspaces-v2`, continues the post-#179
monolith reduction from current `master` after Source ingestion (#181), compact publication
ledgers (#183), the shared embedding-provider contract (#184), and source-library reliability
work (#186) merged.

Current slice:

- Extracted the full **Enrichment** configuration tab into
  `CorpusEnrichmentConfiguration.vue`.
- Kept provider/build request state in `useCorpusProviderConfiguration`; the extracted component
  owns presentation and emits typed changes rather than duplicating domain logic.
- Moved the tabpanel semantics, provider/escalation UI, enrichment strategy, semantic indexing,
  text-cleanup/touch-up controls, text-noise policy, and manual-provider disclosure out of
  `PdfCorpusBuilder.vue`.
- Removed the parent-only `advancedOpen` disclosure state and direct
  `ProviderProfileSelect`/`CorpusTextNoiseSettings` dependencies.
- Preserved the configuration-navigation `aria-controls` contract by making the extracted
  component root `#corpus-config-panel-enrichment`.
- Moved the relevant scoped presentation rules into the extracted component so Vue scoped-style
  boundaries do not cause a visual regression after extraction.
- Added focused unit coverage and Storybook states for fast/deep/manual-provider configurations.
- Reduced `PdfCorpusBuilder.vue` from 3,945 lines to 3,813 lines in this first extraction slice.

Next extraction targets are the Metadata and Advanced tab workspaces, followed by the Review shell
and Finish/repair-intent orchestration.

### Metadata and Advanced workspace extraction

The stacked `task/corpus-builder-metadata-advanced-workspaces` follow-up continues the setup
decomposition without moving domain policy out of the existing composables.

- Extracted **Metadata** configuration into `CorpusMetadataConfiguration.vue`.
  - The schema selector and per-field run guidance now share one
    `#corpus-config-panel-metadata` tabpanel instead of being separate sibling surfaces.
  - Schema choice and run-guidance state remain parent/composable-owned through typed models.
- Extracted **Advanced** configuration into `CorpusAdvancedConfiguration.vue`.
  - Hands-free policy and execution tuning now share one
    `#corpus-config-panel-advanced` tabpanel.
  - Generation, stage limits/timeouts, concurrency, and profile-default policy remain owned by
    `useCorpusProviderConfiguration`; the component only forwards typed changes.
- Added focused component tests for tabpanel ownership and execution-setting forwarding.
- Added Storybook states for built-in/custom metadata schemas, hands-free policy, custom execution,
  and Canadian French length stress.
- Reduced `PdfCorpusBuilder.vue` further, from 3,813 lines after the Enrichment extraction to
  3,744 lines.

### Review record queue extraction

The next monolith-reduction slice moves the record queue/list out of
`PdfCorpusBuilder.vue` without moving review decisions or mutation ownership.

- Extracted queue rendering into `CorpusReviewRecordQueue.vue`.
- Moved row-state presentation, non-colour WCAG state icons, “LLM processed” markers,
  source-warning affordances, selected-record styling, select-visible controls, and empty/loading
  states into the queue component.
- Kept queue selection, record navigation, pagination, search/filter state, and all review
  mutations in the existing parent/composables.
- Preserved the existing `recordListEl` focus/viewport-restoration contract through an explicit
  root-element handoff from the child component.
- Moved queue-local CSS out of `CorpusBuilderWorkspace.css` while retaining three-pane grid,
  splitter, collapse, and responsive layout rules in the parent workspace stylesheet.
- Added focused component coverage and Storybook states for mixed record states, source warnings,
  loading/empty queues, selection, and Canadian French length stress.
- Reduced `PdfCorpusBuilder.vue` from 3,744 lines to 3,622 lines and the shared workspace
  stylesheet from about 2,623 lines to 2,395 lines.

### Review toolbar extraction

The Review workspace decomposition now separates the toolbar/filter/bulk-control surface from
`PdfCorpusBuilder.vue` while leaving review state and mutations in the existing controllers.

- Extracted queue tabs, record search, workspace switching, clean-record acceptance, bulk-action
  menu, bulk metadata editor, feedback, and pagination into `CorpusReviewToolbar.vue`.
- Kept queue/query state in the parent through typed models; workspace changes, bulk operations,
  pagination, and clean-record acceptance are emitted back to the existing parent handlers.
- Preserved the original busy-state behavior: queue/bulk actions disable while busy, while search
  and paging retain their prior behavior; Metadata/Source workspace buttons still require a
  selected record.
- Removed toolbar-local CSS from `CorpusBuilderWorkspace.css` and removed an obsolete
  four-column grid override that could conflict with the extracted toolbar root.
- Retained only the shell-level `.review-frame .review-toolbar` rule in the parent stylesheet,
  because frame positioning/border integration belongs to the three-pane Review shell.
- Added focused component tests and Storybook states for queue/search models, workspace switching,
  bulk mutation forwarding, paging, busy/no-selection states, feedback, and Canadian French
  length stress.
- Reduced `PdfCorpusBuilder.vue` to 3,543 lines and the shared Corpus
  Builder workspace stylesheet to 2,219 lines.

### Review evidence panel extraction

The Review inspector decomposition now separates the evidence-assignment surface from
`PdfCorpusBuilder.vue` without moving evidence mutation ownership.

- Extracted field-evidence selection and source-block evidence toggles into
  `CorpusReviewEvidencePanel.vue`.
- Kept the selected evidence field and evidence-block mutation in the parent; the child emits only
  selected-field and toggle-evidence events.
- Preserved the evidence tabpanel ID/ARIA relationship, field evidence list, paginated/time source
  locators, non-destructive evidence highlighting, and busy-state mutation gating.
- Moved evidence-panel-local source-block styling into the extracted component while retaining the
  shared source-panel styles in the parent until the Source inspector is extracted.
- Removed the now-dead parent `.compact-source-blocks` selector.
- Added focused component tests and Storybook states for selected/unbound evidence, busy state,
  page locators, evidence toggles, and Canadian French length stress.
- Reduced `PdfCorpusBuilder.vue` to 3,500 lines and the shared Corpus
  Builder workspace stylesheet to 2,216 lines.

### Review source panel extraction

The Source inspector tab is now `CorpusReviewSourcePanel.vue`; `PdfCorpusBuilder.vue` still owns
every mutation.

- Extracted the source viewer, boundary second reader, extracted-text blocks (evidence toggle and
  split-after controls) and revision history. The child only emits events (`previousPage`,
  `nextPage`, `openViewer`, `openPdfExplorer`, `adjudicate`, `toggleEvidence`, `split`, provider
  and model updates).
- Kept the `review-panel-source` tabpanel ID and `review-tab-source` labelling.
- Moved the boundary-provider concurrency calculation out of the template into computed values.
- Moved panel-local styles (source blocks, evidence toggle, split button, extraction snapshot,
  tool sections, detail-mode widths) into the component and removed them from the shared
  stylesheet.
- Added focused component tests and Storybook states.
- Reduced `PdfCorpusBuilder.vue` to about 3,430 lines.
- Validation: `vue-tsc`, the full Vitest suite and the production build pass; Storybook and
  Playwright were not run.
