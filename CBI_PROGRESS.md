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

## Upstream synchronization

PR #179 was merged forward onto current `master` ancestry in merge commit
`3100d16f359a14bfce2dd3b8c3cc1c4f4d8ded6a`.

The branch is zero commits behind `master`. The merge preserved upstream changes and manually
reconciled the locale dictionaries and metadata field editor. Locale delimiter fixes followed in
`62012dd24e73e8325ed256c899236ecc5526c6f1` and
`0300635082e54b150398a6acafadf2a50d2d4ee7`.

## Validation status

PR #179 remains draft until the latest head passes all required gates:

- format;
- backend lint, types, and tests;
- API contract;
- frontend lint, static/type/unit checks, and accessibility;
- both E2E shards;
- both legacy/characterization shards;
- aggregate frontend gate.

Do not mark the PR ready before the full current-head run is green.
