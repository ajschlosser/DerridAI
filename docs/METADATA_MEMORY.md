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

## Value equivalence

A surface value is not a semantic identity, and a semantic identity is not evidence. `semantic_identity.py` decides deterministically, without embeddings or model calls, whether a reviewer's value is the same value the model proposed. It compares under the field's equivalence profile (see [METADATA_SCHEMAS.md](METADATA_SCHEMAS.md#value-matching)) and returns one of four relations:

| Relation     | Example                                                     | Review feedback                                                            |
| ------------ | ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| `exact`      | identical values                                            | accepted                                                                   |
| `equivalent` | `J.P. Dingus` → `J. P. Dingus`; `pushing` → `push` (lemmas) | accepted; evidence kept; no rejection or hard negative                     |
| `different`  | `Derrida` → `Levinas`; `critique` → `deconstruction`        | corrected or cleared; remembered as a rejection                            |
| `unknown`    | `J. Dingus` → `John Dingus`; inflection with no lemmatizer  | neutral: the reviewer's value stands, but it is neither kept nor corrected |

Established identities come first. An explicit reviewed alias can make two surfaces equivalent or keep two similar surfaces apart, and punctuation rules never merge two distinct reviewed identities. Document Intelligence entity clusters are advisory: they can turn an `unknown` comparison into `equivalent`, but never override a deterministic difference. Identities are scoped by kind, so a person called Derrida never merges with a concept labelled Derrida.

The relation is computed once, at the review boundary, and recorded with its profile, reasons and `equivalence_version` on the ledger row, the review decision, and any `llm_rejections` row. A later algorithm version never reinterprets an earlier decision. Neither value is rewritten: the model's assertion still states exactly what the model proposed, and the reviewer's exact surface becomes the current value. An equivalent edit carries the prior evidence forward without promoting it: model-selected evidence stays model-selected. A `different` or `unknown` edit starts without evidence, as before. An `unknown` edit is written to the ledger as `review_unresolved`, which is excluded from acceptance, calibration and autofill-suspension counts.

Only a `different` rejection becomes a correction precedent. Rejection rows written before equivalence existed stay in the audit history unchanged, but they are compared under the current policy when exemplars are rebuilt, so a trivial historical edit no longer becomes a hard negative. Positive and correction exemplars keep their exact `field_value` / `rejected_value` and add a derived `canonical_value_key` (and `rejected_canonical_value_key`). The key is `None` when no safe key exists, for example a lexical phrase with no lemmatizer installed.

### Reviewed alias sets

A reviewer can state that several surfaces name one identity of a kind: for example, that "Jacques Derrida", "J. Derrida" and "Derrida, Jacques" are one person. They do this in **Reviewed identities** in Corpus Builder review, or through `GET/POST/DELETE /api/pdf/corpus-builds/{id}/semantic-aliases`.

- **Canonical state.** Alias sets are canonical reviewer state for the build, stored beside its records. They are never inferred from model output or provider clusters.
- **Auditable history.** Editing a set retires it and records its replacement, and retiring keeps the set in the build's history.
- **No shared surfaces.** Two active sets of one kind may not share a surface. Two sets whose surfaces only normalize alike (`J. P. Dingus`, `JP Dingus`) are how a reviewer keeps two similar names apart.
- **Importing from another corpus.** A reviewer can import another build's active sets (all of them, or chosen ones) through **Import from another corpus** or `GET …/semantic-aliases/sources` and `POST …/semantic-aliases/import`. An import is a copy that records `imported_from` (source build, set, title, original reviewer). Later edits in the source build therefore never change this corpus. A set whose surfaces already belong to an identity here is skipped and reported, never merged, and so is a set already imported (an edited import keeps its provenance).
- **Where they are used.** Review comparisons, correction exemplars, precedent matching, pre-fill voting and the Semantic Content Graph all consult them.

### Identity in retrieval and suggestions

- **Analogy conditions.** `match_field_ids` compares reviewed values as semantic values: an equivalent value agrees, a different one contradicts, and a comparison that cannot be decided is skipped.
- **Precedent selection.** Each field's quota is filled with one precedent per semantic identity before equivalent restatements are used. Reviewed precedents are never merged or dropped.
- **Pre-fill votes.** Metadata pre-fill groups precedent votes by identity under this build's policy, so restatements agree instead of splitting the vote. The offered value is an allowed value's own spelling, or else the best-supported, most recently reviewed surface. Every supporting surface stays on the hint.
- **Adjudication cache.** The cache keeps its same-Record, same-text scope and the reviewer's exact `latest_value`. It stores an equivalent prior value only once and records `latest_canonical_key` and `prior_value_keys`. Older rows load unchanged.
- **Enrichment metrics.** Metrics report `accepted_exact`, `accepted_equivalent` and `unresolved_reviews` separately. "Accepted" never means "kept exactly as proposed".

## Field identity and retrieval policy

Schema fields have stable semantic identities independent of display labels. A deliberate rename can retain identity so compatible reviewed precedents remain attached to the same semantic field.

The current retrieval-policy contract is:

| Field                       | Meaning                                                               |
| --------------------------- | --------------------------------------------------------------------- |
| `enabled`                   | Whether reviewed precedents may be supplied for this field/group      |
| `max_items`                 | Maximum precedents contributed by the field                           |
| `min_similarity`            | Minimum semantic similarity accepted for a retrieved precedent        |
| `include_corrections`       | Whether reviewed correction/hard-negative cases may participate       |
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

### Query quality and latency

Only the transient query sent to the embedding provider removes a small,
locale-aware set of high-frequency function words. Stored evidence, canonical
exemplars, and citations are never normalized this way. The active collection
must match the configured embedding contract; the default local contract is
Ollama `bge-m3:latest`, and retrieval telemetry records the provider and model
used for each query.

Candidate ordering uses semantic distance with a bounded lexical-overlap
signal. When enabled and available, the existing RAG CrossEncoder capability
can rerank a small, field-balanced top-K candidate set in one batch. The
metadata-memory path never loads a second model implementation: it uses the
shared provider/model cache and inference boundary used by RAG. The configured
top-K is hard-capped, and the existing positive/correction quotas and MMR
diversity selection still run after reranking.

CrossEncoder use is advisory and fails open. Missing dependencies, model-load
failures, inference timeouts, malformed/non-finite scores, and disabled
configuration preserve the semantic-plus-lexical ranking. Retrieval telemetry
records the configured provider/model, candidate and reranked counts, mode,
fallback reason when applicable, and timing. The deterministic hybrid fallback
remains the supported behavior for fixed inputs and existing deployments.

## Metadata pre-fill

Before enrichment, each source span of a new Record can query reviewed exemplars from other builds (positive values and confirmed absences). The assigned `metadata_prefill` pipeline (built-in `metadata.prefill.current@1`) controls the computational part: how many exemplars each span retrieves (`fetch_k`, 8), how distance becomes similarity (`1 / (1 + distance)`, the only method pre-fill accepts because its thresholds were calibrated against it), and which advisory hints surface (up to 3 per field at similarity 0.72 or above, never below the field's own `min_similarity`).

Whether a value is actually pre-filled is DerridAI policy, not a pipeline setting: at least two distinct earlier Records must agree at mean similarity 0.88 with no rival value within 0.05; the value must be valid for the schema; confirmed absence is only ever a hint; reviewed or already-present values are never overwritten; confidence is capped at 0.9; and authority stays unreviewed. Span, batch, and time limits are server bounds.

Each build records one pipeline trace (spans queried, exemplars returned, similarity range, hints kept, embedding provider/model) and keeps the pipeline identity in its `memory_prefill` summary. An unavailable embedder, store, or pipeline assignment is reported there and the build continues without pre-fill.

## Candidate source units for a precedent

When the reviewer's precedents panel shows a precedent, DerridAI ranks the current Record's own source units against that precedent's reviewed evidence so the reviewer can check where this Record may support the same value. The assigned `precedent_evidence_remap` pipeline (built-in `precedent.remap.current@1`) runs embedding similarity, falls back to word overlap when no embedding service is available or it fails, passes a provenance gate that admits only source units of the current Record, and keeps the three best. Candidates are advisory: they never bind evidence, never carry the precedent's text or source identity, and are re-checked against the Record's current source units when read. Enrichment records one pipeline trace per Record (`candidate_pipeline` on the kept cache); a live panel search records one per request.

## Separation from other memory

Do not conflate these systems:

- **metadata exemplars / metadata memory** guide metadata enrichment;
- **Research response/claim memory** stores prior Research outputs, generated claims, and support bindings;
- **metadata adjudication cache** supports exact/same-context deterministic review assistance;
- **source-unit embeddings** are a reusable derived projection of source-block text; metadata prefill
  reuses those vectors and never owns their lifecycle;
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

## Why there may be bindings but no examples

Saving a reviewed value writes a **metadata memory binding** and an outbox row, whether or not evidence was bound. An **exemplar** additionally needs a human-owned value, reviewer-bound evidence blocks that belong to the record, and a successful vector projection (which needs a reachable embedding provider). Bindings without exemplars therefore usually mean one of:

- no evidence blocks were bound to the confirmed field;
- the evidence does not belong to the record, or is not human-reviewed;
- the projection is failing (for example the embedding provider or its model is unavailable). The outbox stays dirty until it succeeds.

`GET /api/pdf/corpus-builds/{build_id}/metadata-exemplars/diagnosis` counts, per outcome, why each current assertion did or did not yield an exemplar. `POST …/metadata-exemplars/project` rebuilds the build's projection now and returns the real error. The **Metadata examples** page shows the number of unprojected changes and the latest failure per build.
