<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Metadata memory and reviewed precedents

DerridAI can use prior human-reviewed metadata decisions to guide later metadata enrichment. This is retrieval over reviewed precedents, not model training, and it does not make prior values authoritative for a new record.

## Authority model

The authoritative chain is:

```text
reviewed record / RecordRevision
→ field assertion or explicit absence decision
→ reviewer action
→ exact bound evidence
→ source identity / source span
```

A **metadata exemplar** is derived from that chain. Its semantic embedding/index is a rebuildable projection. Deleting the projection must not delete or alter the reviewed record, review event, or evidence binding.

Unreviewed or unresolved model output is never eligible to become trusted precedent merely because it exists in a completed run.

## Eligible precedent kinds

DerridAI distinguishes:

- **positive precedents** — reviewer-confirmed/accepted field values with valid provenance;
- **corrections** — a reviewed replacement for a rejected model proposal; the rejected value is negative evidence and must never be presented as the correct precedent;
- **confirmed absence** — a reviewed no-value decision. It is reusable only when the reviewer explicitly bound source evidence supporting that absence.

Stale revisions, broken evidence bindings, unresolved assertions, and incompatible schema identities are excluded or surfaced as stale rather than silently repaired.

## Field identity and retrieval policy

Schema fields have stable semantic identities independent of display labels. A deliberate rename can retain identity so compatible reviewed precedents remain attached to the same semantic field.

The current retrieval-policy contract is:

| Field | Meaning |
| --- | --- |
| `enabled` | Whether reviewed precedents may be supplied for this field/group |
| `max_items` | Maximum precedents contributed by the field |
| `min_similarity` | Minimum semantic similarity accepted for a retrieved precedent |
| `include_corrections` | Whether reviewed correction/hard-negative cases may participate |
| `include_confirmed_absence` | Whether explicitly evidence-bound no-value precedents may participate |

Locked core metadata fields inherit applicable group policy. Legacy routing/scope/Research-memory flags are migrated for compatibility and are not part of the current schema contract.

## Retrieval and prompt discipline

Retrieval is field-aware and bounded:

1. derive or resolve eligible exemplars from reviewed canonical state;
2. query the semantic projection with schema/field/language/build constraints as applicable;
3. apply similarity, correction/absence, deduplication, and packet-budget rules;
4. pass only the small evidence/context packet needed by the relevant metadata-family call;
5. record which exemplar IDs were supplied;
6. validate the new model proposal using the normal schema, evidence, and review rules.

A precedent is advisory context. It does not copy a value into a new record as truth and it does not weaken source-evidence requirements.

## Separation from other memory

Do not conflate these systems:

- **metadata exemplars / metadata memory** guide metadata enrichment;
- **Research response/claim memory** stores prior Research outputs, generated claims, and support bindings;
- **metadata adjudication cache** supports exact/same-context deterministic review assistance;
- **Response Library/cache** is operational Research cache/history;
- **ordinary corpus vector collections** support Search/Research over scholarly records.

They may share storage technology, but they have different authority, scope, lifecycle, and privacy semantics.

## Administrative inspection

System Data exposes reviewed metadata precedents as domain/audit data. The ordinary UI should show field/value, precedent kind, review authority, source record/revision/build, schema/language/region scope, evidence references/text, and stale state where available. Chroma collection names, vector dimensions, embedding IDs, and other storage mechanics are implementation details.

The restricted System Chroma console is for administrative inspection/debugging only. It does not change the authority model above.

## Failure behavior

Metadata retrieval is advisory and must fail open with visible diagnostics:

- if the vector projection is absent or unavailable, continue without semantic precedents or use the supported deterministic/lexical fallback;
- if an exemplar cannot resolve to its source revision/evidence, exclude or mark it stale;
- if embedding contracts mismatch, rebuild/fail the derived projection explicitly rather than mixing incompatible vectors;
- never fabricate evidence text or silently substitute a newer record revision.

See [METADATA_SCHEMAS.md](METADATA_SCHEMAS.md) for schema controls and [ARCHITECTURE.md](ARCHITECTURE.md) for persistence boundaries.
