<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# FieldAssertion migration status

The canonical FieldAssertion migration is complete for ordinary schema-defined scholarly metadata.

## Canonical boundary

DerridAI now treats a FieldAssertion as the authoritative account of a record-level scholarly metadata value. Top-level record fields and `metadata_field_status` remain materialized compatibility views for readable JSONL and older clients.

The application preserves derivation, evaluation, authority, value state, confidence, evidence, record revision, stable field identity, and assertion history independently.

## What remains intentionally explicit

The following are not candidates for generic metadata-field abstraction:

- Record and SourceDocument identity;
- authoritative record text and source spans;
- page, character, and time locators;
- publication/build/job state;
- retrieval and vector-store scores;
- citation projections;
- review queues and other operational projections;
- the locked structural semantics `region_type`, `primary_text`, and `discourse_role`;
- semantic segmentation signals such as speaker, position-holder, stance, target, quotation frame, discourse role, and argumentative move.

These concepts participate in application invariants rather than merely naming arbitrary metadata columns.

## Compatibility constants

Legacy constants such as `ALLOWED_METADATA_FIELDS`, `HUMAN_EDITABLE_METADATA_FIELDS`, `REVIEW_METADATA_FIELDS`, `ATTRIBUTION_EVIDENCE_FIELDS`, and `METADATA_FAMILY_FIELDS` remain exported where older integrations, fixtures, or default-schema characterization tests rely on them.

They are not the runtime universe of schema-defined metadata.

Active allow/edit policy is now:

```text
fixed document/computed metadata
+ fields from the build's pinned MetadataSchema
```

Review fields, evidence requirements, and metadata families are derived from that pinned schema.

## User-facing schema propagation

Schema-defined assertion fields can now flow without production code changes through:

1. schema-defined model enrichment;
2. canonical FieldAssertion creation;
3. evidence and human review;
4. readable record projections;
5. Search facets and filters;
6. touch-up field discovery;
7. RAG evidence transport;
8. Record Inspector field discovery and layout configuration;
9. Research evidence metadata presentation.

Built-in field lists remain as useful ordering and presentation defaults. They are no longer closed whitelists for ordinary custom metadata.

## Canonical policy reads

Backend policy now reads FieldAssertions directly for:

- record acceptance and implicit confirmation;
- human edits and confirmed absence;
- reviewed evidence changes;
- source-quality gating;
- manifest inheritance and deterministic structural ownership;
- enrichment ownership/protection;
- enrichment-pass disagreement and rerun resets;
- metadata exemplar/editorial-memory trust;
- hands-free settlement;
- metadata retry eligibility;
- metadata issue summaries and enrichment contribution metrics.

`metadata_field_status` may still be written or read while constructing compatibility projections, preserving blind-review/recheck and model-run telemetry, formatting legacy API/UI output, or normalizing an in-flight model response before it is converted to assertions. New scholarly authority decisions must not originate from that flattened status token.

Persistent scholarly mutation paths are assertion-native. This includes initial deterministic segmentation metadata, manifest inheritance/reclassification, source-quality and worker failures, human confirmation/override/confirmed absence, evidence edits, record acceptance, hands-free settlement, enrichment merges, multi-pass disagreements, rerun resets, blind rechecks, editorial memory, exemplar trust, retry classification, and unresolved-field metrics.

A useful maintenance test is intentional projection corruption: changing only a compatibility `status` token must not change which value is authoritative, whether automatic enrichment may overwrite it, whether a field is epistemically unresolved, or whether reviewed evidence is eligible as precedent.

## Canary coverage

The regression suite uses the custom field `conceptual_tension` without adding it to production field constants.

Backend coverage verifies schema -> enrichment -> FieldAssertion -> human review while preserving the stable field ID `field-conceptual-tension`.

Frontend coverage verifies assertion-driven Record Inspector discovery, Research evidence shaping, and touch-up discovery.

A separate legacy/custom-field assertion test continues to verify stable identity for `interlocutor_role`.

## Rule for future development

When adding metadata behavior:

- use stable semantic compatibility identity when behavior belongs to a particular cELF scholarly concept;
- use MetadataSchema properties when behavior belongs to field type, group, evidence, assessment, or review policy;
- use FieldAssertion for value provenance and authority;
- do not add an ordinary schema field to a global hard-coded whitelist merely to make it work in another surface.

A new ordinary schema field should not require source-code changes unless a deliberately specialized presentation or domain invariant is desired.

## Metadata-field decoupling follow-up

The canonical assertion migration is complete, but several production surfaces still recognize the built-in scholarly profile by storage/display field name. That coupling is now tracked as a follow-up migration rather than as a reason to reopen the assertion-authority model.

The target architecture is:

```text
MetadataSchema / stable field identity / semantic compatibility identity
    -> generic policy and presentation
    -> FieldAssertion authority/provenance
    -> materialized record compatibility projection
```

A literal field name is acceptable only when one of the following is true:

1. it is a cELF/DerridAI structural or source invariant such as Record identity, source spans, locators, or intentionally locked core semantics;
2. the code is defining the built-in default schema/profile itself;
3. it is a compatibility adapter whose scope is explicit and tested;
4. a deliberately specialized feature depends on a stable semantic concept and resolves that concept through semantic compatibility identity rather than by assuming a mutable field name.

### Progress tracker

Status values are **not started**, **in progress**, **blocked**, and **complete**. Update this table in the same commit that changes a tracked area.

| Workstream                                  | Status      | Primary files                                                                          | Completion criterion                                                                                                                                                        |
| ------------------------------------------- | ----------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inventory and guardrails                    | complete    | this document, tests added per workstream                                              | Production hard-coding is classified as structural, compatibility-only, default-schema definition, or migration target.                                                     |
| Semantic Content Graph semantic-ID routing  | in progress | `api/app/semantic_content_graph.py`, `api/app/metadata_schema.py`, graph tests         | Graph node/edge projection discovers scholarly roles through schema semantic compatibility identities; renamed schema fields with the same semantics behave like built-ins. |
| Backend compatibility constants containment | in progress | `api/app/corpus_metadata.py`, `api/app/corpus_review_queue.py`, callers                | Legacy constants no longer determine the runtime universe; remaining uses are compatibility/default-profile characterization and are documented as such.                    |
| Segmentation/profile semantics              | not started | `api/app/corpus_models.py`, segmentation/profile code                                  | Profile-specific segmentation signals are owned by an explicit profile contract rather than presented as universal metadata fields.                                         |
| Record/touch-up/RAG transport               | not started | `web/src/domain/recordPayloads.ts`, backend request models/adapters                    | Schema-authorized fields are transported from pinned schema/assertion metadata; adding or renaming an ordinary field does not require a transport whitelist edit.           |
| Work-metadata scope handling                | not started | `web/src/domain/workMetadata.ts`                                                       | Record-vs-document/work exclusion follows schema scope/field identity rather than a negative list of scholarly field names.                                                 |
| Record Inspector and edit layouts           | not started | `web/src/domain/inspectorLayout.ts`, `recordDialogs.ts`, Record edit/bulk components   | Groups/order/control metadata come from schema/group/UI descriptors, with built-in ordering only as a fallback.                                                             |
| Search facets and filters                   | not started | `web/src/domain/searchFilterSchema.ts`, `searchFacets.ts`, runtime constants           | Filter/facet behavior follows schema type, cardinality, controlled values, indexing/filter capability, and field identity rather than built-in names.                       |
| Touch-up presets                            | not started | `web/src/domain/runtimeConstants.ts`, `sharedTouchupWorkflow.ts`                       | Presets resolve schema fields by semantic identity/group capability; custom equivalent fields participate without code edits.                                               |
| Research evidence presentation              | not started | `web/src/domain/evidenceSelection.ts`, `web/src/types/research.ts`, `ResearchView.vue` | Research evidence carries generic metadata/assertions; specialized attribution helpers resolve semantic identities instead of direct properties.                            |
| Public SDK metadata model                   | not started | `web/sdk/src/types.ts`, SDK adapters/tests                                             | Base publication/evidence interfaces expose generic metadata/assertions; profile-specific convenience access does not imply universal field presence.                       |
| Frontend duplicated field registries        | not started | `runtimeConstants.ts`, `fieldAssertions.ts`, components                                | Repeated production lists are removed or generated from one schema-derived registry; stories/fixtures may retain explicit built-in examples.                                |
| Compatibility cleanup and docs              | not started | `corpus_metadata.py`, architecture/user docs, migration tests                          | Dead constants are removed or marked compatibility-only, current docs describe the final contract, and custom-field/renamed-field canaries cover backend + frontend.        |

### Implementation sequence for an AI agent

#### Phase 0 — protect invariants before refactoring

1. Read `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `docs/METADATA_SCHEMAS.md`, this document, and the local README for each subsystem touched.
2. Work from current `master`; preserve concurrent changes and avoid drive-by formatting.
3. Before changing a hard-coded name, classify it:
   - **structural** — keep explicit;
   - **default profile definition** — keep explicit inside the schema/profile definition;
   - **compatibility projection** — keep only if older persisted/API shapes require it;
   - **behavioral dispatch** — migrate to schema/semantic identity.
4. Add a regression canary before or with every behavioral migration. Prefer a renamed field carrying the same `semantic_compatibility_id` because it proves the behavior does not depend on the storage name.
5. Preserve all FieldAssertion authority/evidence state. This project must never gain field-name independence by flattening provenance.

#### Phase 1 — Semantic Content Graph

1. Add schema helpers that resolve fields by `semantic_compatibility_id` and, where appropriate, by `identity_kind`.
2. Replace the graph's fallback-name iteration for people, concepts, topics, works, position holder, target, stance, speaker, and quotation relations with resolved schema bindings.
3. Keep fallback behavior only for schema-less/legacy records. Isolate it in a named compatibility helper.
4. Ensure a renamed field such as `interlocutor` with semantic identity `derridai.position_holder` produces the same graph relation as `position_holder`.
5. Ensure custom fields without known semantic identity remain generic values and do not acquire built-in scholarly meaning accidentally.
6. Preserve relation authority, evidence references, record IDs, and observational-vs-semantic distinction.
7. Add tests for:
   - renamed person/indexing fields;
   - renamed position-holder/target/stance fields;
   - renamed quotation fields;
   - no-schema legacy fallback;
   - two fields sharing an identity kind but different semantic roles;
   - disputed/unreviewed assertion aggregation.

#### Phase 2 — backend policy and compatibility constants

1. Trace every production caller of `ALLOWED_METADATA_FIELDS`, `HUMAN_EDITABLE_METADATA_FIELDS`, `REVIEW_METADATA_FIELDS`, `ATTRIBUTION_EVIDENCE_FIELDS`, `EVIDENCE_REQUIRED_FIELDS`, and `METADATA_FAMILY_FIELDS`.
2. Replace runtime policy with the pinned schema methods already available: `field_names()`, `review_fields()`, `evidence_fields()`, `attribution_fields()`, `family_fields()`, plus fixed structural/document fields.
3. For review facets, initialize from the pinned schema rather than `ALLOWED_METADATA_FIELDS`. Retain arbitrary observed assertion fields only when they are authorized by the schema or an explicit legacy compatibility path.
4. Move deterministic-ingest speaker candidate routing behind semantic identity resolution.
5. Keep compatibility exports until no external/test contract depends on them; mark each remaining caller with why it is compatibility-only.
6. Add tests proving a new schema field appears in review facets/edit policy without changing a Python constant.

#### Phase 3 — profile-specific segmentation

1. Separate segmentation-change signals from generic record metadata.
2. Define the scholarly/default profile's segmentation semantic roles explicitly.
3. Keep `BoundaryChangeModel` only as a profile-specific transport if required, or generate/validate the relevant signal set from profile configuration.
4. Do not make arbitrary metadata fields segmentation signals merely because they share a group.
5. Characterize current default-profile behavior before changing model prompt contracts; bump prompt/profile versions only if semantics change.

#### Phase 4 — transport boundaries

1. Replace `TOUCHUP_TRANSPORT_CONTEXT_FIELDS` and `RAG_EVIDENCE_TRANSPORT_FIELDS` as closed metadata lists.
2. Split structural transport fields from schema metadata.
3. Resolve permitted metadata from the active schema and current FieldAssertions.
4. Continue sending only the minimum data required for the operation.
5. Ensure sealed/blind-review values cannot leak because a generic transport suddenly includes everything.
6. Add contract tests using `conceptual_tension` and at least one renamed semantic field.

#### Phase 5 — frontend schema-derived registry

1. Establish one typed frontend registry derived from API schema data:
   - stable field ID;
   - storage name;
   - display label/i18n key;
   - group/order;
   - scope;
   - type/cardinality;
   - controlled values;
   - review/evidence/assessment flags;
   - semantic compatibility ID;
   - optional UI control/preset hints.
2. Make Record Inspector, record edit sheet, bulk editor, and record dialogs consume that registry.
3. Retain built-in ordering only as fallback for old publications that lack full schema descriptors.
4. Remove duplicated arrays from production components after coverage proves parity.
5. Keep all user-visible labels localized through existing locale infrastructure.

#### Phase 6 — work metadata, search, and touch-up

1. Replace `WORK_METADATA_EXCLUDED_ASSERTION_FIELDS` with positive scope checks.
2. Derive collection/filter control behavior from field type/cardinality and controlled values.
3. Derive facet eligibility from schema/index capability rather than name.
4. Convert touch-up presets from storage-name arrays to semantic/group selectors.
5. A custom schema field should join the correct UI automatically when its schema metadata says it should.

#### Phase 7 — Research and public SDK

1. Treat generic metadata plus FieldAssertion summaries as the primary Research evidence contract.
2. Replace direct `speaker`/`position_holder`/etc. projection with semantic-role accessors.
3. In the SDK, keep cELF structural fields first-class but move profile-specific scholarly metadata under generic metadata/assertion structures.
4. If convenience accessors remain, implement them by semantic compatibility ID and document that they are optional profile semantics.
5. Preserve backward compatibility through adapters/deprecated properties for at least one compatibility window if public consumers require it.

#### Phase 8 — cleanup and proof

1. Re-run repository search for the built-in scholarly field names.
2. For every remaining occurrence, document why it is:
   - schema definition;
   - structural invariant;
   - compatibility;
   - fixture/test/story/example.
3. Remove unused compatibility constants only after callers are gone.
4. Update `docs/ARCHITECTURE.md`, `docs/METADATA_SCHEMAS.md`, and `docs/USER_GUIDE.md` if user-visible behavior or public contracts changed.
5. Run the smallest relevant suites continuously, then the full quality gates before handoff:
   - `pytest -q -n auto --dist=worksteal`;
   - contract tests;
   - `python -m compileall -q api/app`;
   - frontend formatting/typecheck/unit tests/build;
   - Storybook/e2e when UI behavior changes.
6. Do not mark this tracker complete if only the default field names pass. Completion requires a renamed-semantic-field canary and an unrelated custom-field canary.

### Definition of done

This follow-up is complete when an ordinary schema field can be added or renamed without production code changes across enrichment, review, graph projection where semantically applicable, Search, touch-up, Record Inspector, Research evidence, and transport; specialized behavior is selected by stable semantic identity or explicit schema capability; and remaining literal scholarly field names are confined to default-profile definitions, structural invariants, compatibility adapters, tests, examples, and fixtures.
