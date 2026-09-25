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
