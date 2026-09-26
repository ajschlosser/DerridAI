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
