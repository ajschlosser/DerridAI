# Corpus Builder UX Redesign Progress

Branch: `task/corpus-builder-visible-ux`  
Pull request: #179 — Redesign Corpus Builder workspace UX  
Base: current `master`; branch is currently zero commits behind.

## Completed and pushed

### Visible Corpus Builder redesign

- Replaced the visible A–H configuration metaphor with a focused Source / Structure / Enrichment / Metadata / Advanced workspace.
- Added keyboard-accessible configuration navigation and Storybook coverage.
- Added a contextual Corpus Builder workspace header that carries source/build/publication context.
- Reworked build readiness into a compact sticky command bar with setup details on demand.
- Flattened the configuration presentation so the active workspace no longer looks like the old stack of equally weighted cards.
- Kept Review as the dominant scholarly workspace.
- Kept Run Monitor above the review frame instead of CSS-reordering it beneath the full-height workspace.
- Changed the Record decision dock from browser-global fixed positioning to workspace-local sticky positioning.
- Continued the Finish → Publication readiness semantics already present on the branch.

### Metadata review regressions fixed

- Restored editing for fields with canonical FieldAssertion provenance. The provenance disclosure and edit controls are now independent instead of mutually exclusive.
- Added safe metadata value unwrapping/rendering so compatibility envelopes no longer display as `[object Object]`.
- Sanitized autocomplete at both the shared known-values cache and control boundary. Source block IDs, serialized JSON/assessment fragments, placeholders, and oversized runtime strings are rejected.
- Fixed Focus Review so **Save all suggestions** forwards the batch action to the parent.
- Hardened batch metadata persistence and generic field identity resolution.
- Added pending/success/failure handling for batch suggestion saves.
- Fixed **Accept & next** local advancement and server fallback navigation.
- Filtered acceptance blockers through the reviewable metadata contract so operational fields cannot block scholarly Record acceptance.

### Generic field-role contract

Schema fields now have product semantics independent of their arbitrary storage names:

- `role`: `scholarly | structural | document | operational`
- `review_visibility`: `primary | details | hidden`

The schema editor exposes both properties with English/fr-CA copy. Ordinary Record review is derived from locked structural fields, the pinned schema, canonical scholarly assertions, and inherited document metadata. Operational/runtime fields such as `text_revision_history`, execution ledgers, source arrays, review events, and assertion storage internals are excluded from ordinary scholarly metadata review.

### Structured-output contradiction handling

The metadata response validator no longer discards an otherwise parseable metadata-family response when a model returns contradictory assessment/value semantics such as:

- a value plus `outcome=no_supported_value`;
- an empty value plus `outcome=supported_value`;
- `outcome=uncertain` with `needs_review=false`.

The proposed value is retained for inspection, while the field assessment is normalized to `outcome=uncertain`, `needs_review=true`, with an explicit structured-output contradiction reason. This keeps the failure epistemically visible without turning one field contradiction into a whole-family retry/failure.

### Metadata exemplar projection

- Derived `derridai_metadata_exemplars` collection creation is deterministic on first use.
- Chroma 1.x constructor differences are handled without silently weakening collection metadata.
- Collection-creation failures are no longer masked by a misleading follow-up “Collection does not exist” error.
- Canonical reviewed records/assertions remain authoritative; the Chroma collection remains rebuildable derived state.

### Regression coverage added

Coverage now includes:

- editing a field while FieldAssertion provenance is present;
- structured metadata envelope rendering;
- runtime/JSON/source-block autocomplete rejection;
- Focus Review Save-all forwarding;
- authoritative batch suggestion persistence;
- operational-field filtering and field-role visibility;
- Accept & next navigation and fallback;
- contradictory LLM assessment normalization;
- missing derived exemplar collection creation and truthful initialization failures;
- accessible configuration-tab composition.

## Validation status

Latest full quality-gates run is queued for the current head. Before #179 is marked ready, the target remains:

- format;
- ESLint;
- frontend static/type/unit checks;
- backend tests;
- WCAG 2.2 AA story/app sweeps;
- both E2E shards;
- both legacy/characterization shards;
- API contract checks;
- branch synchronized with `master`.

The PR remains draft until the latest head passes all required gates.


## 2026-09-25 / PR #179 implementation update

Visible UX work now implemented:

- Replaced the visible A–H setup metaphor with Source / Structure / Enrichment / Metadata / Advanced workspace navigation.
- Added keyboard-accessible configuration tabs.
- Added a contextual Corpus Builder workspace header.
- Replaced the oversized build-readiness card with a compact sticky command bar and details-on-demand summary.
- Converted Finish copy and interaction framing toward explicit Publication readiness / immutable snapshot semantics.
- Preserved the Review session bar as the persistent header inside the scholarly review workspace.
- Kept Run Monitor diagnostics reachable above the sticky review frame.
- Added Storybook coverage for the new configuration navigation and workspace header.
- Added English and Canadian French copy for the new workspace affordances.

Metadata-review regressions addressed:

- Restored field editing when a canonical FieldAssertion is present; provenance no longer suppresses the editor.
- Added metadata value unwrapping / safe rendering so compatibility envelopes cannot render as `[object Object]`.
- Sanitized autocomplete suggestions and rejected JSON fragments, source-block IDs, assessment objects, and other runtime leakage.
- Constrained observed/autocomplete values to reviewable metadata fields rather than arbitrary Record properties.
- Added explicit schema `role` and `review_visibility` properties so behavior is not inferred from arbitrary field names.
- Added roles: `scholarly`, `structural`, `document`, `operational`.
- Added review visibility: `primary`, `details`, `hidden`.
- Operational/hidden fields no longer participate in ordinary Record-review presentation or acceptance gating.
- Explicitly filters legacy runtime properties such as `text_revision_history`, execution ledgers, review state, evidence/status containers, and source bookkeeping from scholarly metadata review.
- Fixed Focus Review so `Save all suggestions` forwards to the shared batch-save path.
- Made batch suggestion persistence authoritative and added pending-state feedback.
- Fixed the batch metadata-decision endpoint to use generic FieldAssertion field identity resolution.
- Fixed `Accept & next` optimistic state and fallback navigation when the server does not provide `next_record`.

Backend reliability fixes:

- Structured-output contradictions such as a non-empty value paired with `outcome=no_supported_value` now become explicit `uncertain` + `needs_review=true` field states instead of discarding the whole metadata-family response after retry/escalation.
- The contradictory proposed value is retained for human adjudication with a recorded contradiction reason; it is not silently promoted to supported truth.
- Metadata exemplar collection initialization is deterministic across supported Chroma constructor variants.
- Exemplar-index creation failures are no longer masked as a misleading follow-up `Collection ... does not exist` error.
- Added first-use creation/failure regression coverage for the derived metadata exemplar collection.

Regression coverage added for:

- editable canonical assertions;
- structured metadata value rendering;
- autocomplete junk rejection;
- focus-mode Save all suggestions;
- authoritative batch metadata decisions;
- operational-field filtering and role-based visibility;
- structured-output contradiction normalization;
- metadata exemplar collection initialization;
- optimistic Accept & next behavior.

Upstream status:

- PR #179 has been merged forward onto current `master` ancestry.
- Branch is zero commits behind `master` after merge commit `3100d16f359a14bfce2dd3b8c3cc1c4f4d8ded6a`.
- The merge preserved all upstream changes and manually reconciled the locale dictionaries and metadata field editor.
- A locale delimiter syntax issue introduced during that reconciliation was fixed immediately in commits `62012dd24e73e8325ed256c899236ecc5526c6f1` and `0300635082e54b150398a6acafadf2a50d2d4ee7`.

## Validation remaining

A fresh full quality-gates run is queued on head `0300635082e54b150398a6acafadf2a50d2d4ee7`.

Do not mark PR #179 ready until format, backend lint/types/tests, API contract, frontend lint/static/a11y, both E2E shards, both legacy/characterization shards, and the aggregate gate all pass on the current head.
