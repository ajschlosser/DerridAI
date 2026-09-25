# Corpus Builder UX Redesign Progress

Branch: `task/corpus-builder-visible-ux`  
Pull request: #179 — Redesign Corpus Builder workspace UX  
Base: `master` after the #176 architecture refactor and Core Specification 1.0 sync.

## Completed and pushed

- Added `CorpusConfigurationNav.vue` with Source / Structure / Enrichment / Metadata / Advanced workspace navigation.
- Removed the visible A–H configuration markers from `PdfCorpusBuilder.vue`.
- Wired configuration panels to the new workspace navigation.
- Added keyboard navigation for the configuration tablist.
- Added `CorpusBuilderWorkspaceHeader.vue` and replaced the old title/subtitle masthead with contextual source/build/publication status.
- Reworked `CorpusBuildReadiness.vue` into a compact sticky command bar with details on demand.
- Added English and Canadian French copy for the new workspace controls.
- Added source-selection reset behavior so the configuration workspace cannot remain on an invalid panel.

## Current investigation / required fixes

The next work includes both the visible UX redesign and metadata-review regressions reported during review:

- Metadata values are no longer reliably editable.
- Some field values render as `[object Object]`.
- `Accept & next` does not work.
- `Save all suggestions` does not work.
- Autocomplete is ingesting malformed/runtime material such as source-block arrays and JSON fragments.
- Utility/runtime fields such as text revision history are leaking into scholarly Record review.
- Generic metadata needs explicit field-role/presentation properties so arbitrary schema fields remain supported without exposing operational fields.
- Quotation structured-output responses can fail when a model emits a value together with `outcome=no_supported_value`; normalize/validate this contract safely while preserving the failure state.
- Metadata exemplar projection currently reports a pending state when the derived `derridai_metadata_exemplars` vector collection does not yet exist; initialization should be deterministic and non-destructive.

## Validation target

Before #179 is marked ready:

- preserve canonical FieldAssertion authority/provenance;
- keep arbitrary schema-defined scholarly fields editable and reviewable;
- hide operational/utility fields from ordinary scholarly metadata review unless explicitly configured for presentation;
- make all metadata review actions functional;
- sanitize autocomplete inputs to field-appropriate scalar/list values only;
- add regression tests for the reported failures;
- pass format, lint, static/type, accessibility, E2E, legacy/characterization, API-contract, and applicable backend tests.
