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

`metadata_field_status` may still be written or read while constructing compatibility projections, preserving blind-review/recheck telemetry, or migrating historical records. New scholarly authority decisions must not originate from that flattened status token.

## Canary coverage

The regression suite uses the custom field `conceptual_tension` without adding it to production field constants.

Backend coverage verifies schema -> enrichment -> FieldAssertion -> human review while preserving the stable field ID `field-conceptual-tension`.

Frontend coverage verifies assertion-driven Record Inspector discovery, Research evidence shaping, and touch-up discovery.

A separate legacy/custom-field assertion test continues to verify stable identity for `interlocutor_role`.

## Rule for future development

When adding metadata behavior:

- use stable semantic compatibility identity when behavior belongs to a particular DERRIDAI scholarly concept;
- use MetadataSchema properties when behavior belongs to field type, group, evidence, assessment, or review policy;
- use FieldAssertion for value provenance and authority;
- do not add an ordinary schema field to a global hard-coded whitelist merely to make it work in another surface.

A new ordinary schema field should not require source-code changes unless a deliberately specialized presentation or domain invariant is desired.
