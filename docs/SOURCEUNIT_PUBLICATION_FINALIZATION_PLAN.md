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

# SourceUnit publication finalization implementation plan

Status: in progress on `fix/unreviewed-topology-finalization` / PR #532.

This plan addresses the publication failure in which **Use suggestions as-is** can still receive:

> HTTP 409 Conflict · Publication is blocked until source coverage and text-fidelity validation pass.

The failure is valid when source material is genuinely lost, duplicated, invented, or reordered. It is not valid when the current corpus topology is source-conserving but publication validation is still judging it through obsolete legacy `source_block_ids` after split, combine, or create-from-selection operations.

The goal is therefore not to weaken the cELF source-conservation gate. The goal is to make publication validation use the same authoritative topology that Corpus Builder now uses.

## Product contract

When the reviewer chooses **Use suggestions as-is**, DerridAI should:

1. accept unresolved model/deterministic suggestions as autonomous publication decisions rather than human confirmations;
2. finalize the current SourceUnit topology deterministically;
3. rebuild derived source projections from that topology;
4. rerun source coverage, fidelity, ordering, and locator validation against the finalized topology;
5. publish when the finalized topology conserves the declared source scope;
6. block only when a real, unresolved source-integrity failure remains.

The action must never silently convert a real source loss into a valid publication.

## Architectural invariants

### Source layers remain distinct

DerridAI must preserve three different concepts:

- **Immutable extraction blocks** are the original extraction/evidence coordinate.
- **SourceUnits** are the authoritative post-structural-edit topology coordinate.
- **Record text** is the editorial/review layer and may legitimately differ from extracted text.

`source_extracted_text` is a derived provenance projection. It must be reconstructed from the Record's authoritative SourceUnits, not copied from reviewed Record text.

### Structural edits do not make legacy block ownership authoritative

A single immutable extraction block may legitimately be replaced by multiple active SourceUnits. Those SourceUnits may belong to different Records. That is not duplicate source ownership as long as the active SourceUnits themselves have unique owners and their lineage conserves the original extraction.

### Evidence remains source-bound

Existing evidence and citations that refer to immutable extraction blocks remain valid when the block is structurally partitioned into SourceUnits. SourceUnit topology must not silently rewrite scholarly evidence to a new coordinate system.

### Publication stays strict

The following remain publication blockers:

- immutable source scope that is not represented by the active SourceUnit lineage;
- active SourceUnits not owned by any Record;
- active SourceUnits owned by more than one Record;
- references to inactive or missing SourceUnits;
- SourceUnit extraction that no longer reconstructs the declared source scope;
- reordered source material;
- invalid page/time mapping;
- any other cELF publication blocker already enforced independently.

## Implementation phases

### Phase 1 — Canonical SourceUnit helpers

Centralize the topology operations needed by both structural editing and validation.

Required helpers:

- map active SourceUnits by canonical ID;
- resolve the authoritative SourceUnit IDs for a Record, with legacy fallback for older builds;
- resolve SourceUnit lineage recursively to immutable extraction-block roots;
- rebuild `source_extracted_text` deterministically from owned SourceUnits.

Acceptance criteria:

- legacy builds without an explicit SourceUnit store continue to validate;
- nested replacement-unit lineage resolves back to original extraction roots;
- rebuilding the extraction projection does not alter reviewed `text`;
- no helper assigns human-review provenance.

### Phase 2 — Validate the current topology, not the compatibility projection

Extend `validate_records()` so that, when SourceUnits exist, source topology is validated against active `source_unit_ids`.

Coverage and ordering use immutable extraction roots only to prove source-scope conservation. Ownership, duplicates, and fidelity use the active SourceUnits.

The validator must distinguish:

- missing immutable source roots;
- missing active SourceUnits;
- duplicate active SourceUnit ownership;
- missing/inactive SourceUnit references;
- Record/SourceUnit text-fidelity mismatches;
- source-order failures;
- page/time mapping failures;
- whole-corpus source-conservation failure.

Local single-Record validation must not run corpus-wide conservation checks.

Acceptance criteria:

- splitting one extraction block into two legitimate SourceUnits does not create a false duplicate-block error;
- two adjacent SourceUnits descending from the same root block are allowed in source order;
- a missing active SourceUnit still blocks;
- a duplicated active SourceUnit still blocks;
- a Record whose `source_extracted_text` differs from its owned SourceUnits is detected until reconciliation repairs the derived projection.

### Phase 3 — Reconciliation repairs derived source state

Before authoritative publication-readiness validation:

1. load the current active SourceUnits;
2. derive `source_extracted_text` from each Record's SourceUnits;
3. fill legacy Records' `source_unit_ids` from their compatibility block IDs when safe;
4. validate current Records against current SourceUnits;
5. persist only changed Record projections through ordinary reconciliation.

This is a deterministic repair of derived provenance state, not acceptance of a scholarly claim.

Acceptance criteria:

- stale `source_extracted_text` from a prior structural state is repaired without requiring manual Record editing;
- reconciliation is idempotent;
- repeated reconciliation does not increment scholarly review authority;
- concurrent Record changes still use the repository's existing optimistic conflict handling.

### Phase 4 — Make “Use suggestions as-is” own finalization

`publish(..., accept_unreviewed=True)` must perform authoritative final reconciliation server-side before checking publication blockers.

The web client may reconcile first for responsive UI, but correctness must not depend on that client behavior. Direct API callers must receive the same result.

Strict reviewed publication keeps its existing lifecycle and readiness contract.

Acceptance criteria:

- stale readiness state cannot cause a false 409 on the autonomous publication path;
- an in-progress build still cannot publish;
- genuine source loss still receives a 409;
- a source-conserving SourceUnit topology can publish even if the pre-reconciliation build summary contained legacy duplicate/fidelity errors.

### Phase 5 — Publication and cELF blocker accounting

Update publication-readiness and cELF conformance accounting so the new SourceUnit integrity failures are first-class blockers.

The validation payload should expose actionable `validation_issues` for:

- `source_coverage`;
- `source_duplicate`;
- `source_reference`;
- `source_fidelity`;
- `source_order`;
- `source_page_mapping`;
- `source_conservation`.

Acceptance criteria:

- the readiness blocker count includes SourceUnit failures;
- cELF conformance cannot report conformant while any SourceUnit integrity blocker remains;
- the generic HTTP 409 is accompanied by structured issues that identify the actual affected Record or SourceUnit where possible.

### Phase 6 — UX and terminology

Update **Use suggestions as-is** copy so that it describes the actual behavior:

- DerridAI finalizes the current topology automatically;
- legacy topology/fidelity warnings do not require manual acceptance;
- real source-integrity failures still block publication.

Do not describe the action as bypassing source validation.

Acceptance criteria:

- English and French copy remain in parity;
- no UI suggests that cELF source conservation is optional;
- when finalization succeeds, the reviewer does not have to manually adjudicate topology merely to clear stale compatibility errors.

### Phase 7 — Regression coverage

Required automated scenarios:

1. one legacy extraction block split into two active SourceUnits;
2. multiple generations of SourceUnit replacement lineage;
3. stale `source_extracted_text` repaired at reconciliation;
4. missing active SourceUnit;
5. duplicate active SourceUnit ownership;
6. inactive/missing SourceUnit reference;
7. reordered SourceUnits;
8. whole-corpus source text loss;
9. page-based locator mismatch;
10. timed-media locator mismatch;
11. old build with only `source_block_ids`;
12. direct API autonomous publication;
13. web autonomous publication;
14. reviewed publication remains unchanged;
15. cELF conformance reports remaining source blockers;
16. evidence bound to immutable extraction blocks survives topology replacement.

A real corpus fixture that previously produced the reported 409 should be retained as a regression fixture if it can be reduced without storing copyrighted source text beyond repository policy.

## Rollout sequence

The intended merge order is:

1. canonical helpers;
2. SourceUnit-aware validator;
3. reconciliation repair;
4. autonomous publication finalization;
5. blocker/conformance integration;
6. UX copy;
7. focused regression suite;
8. repository-wide CI;
9. reproduce against the originally failing corpus build;
10. merge only after the source-conservation gate is shown to remain strict.

No migration that destroys retired SourceUnits or retired Records is required. Existing lineage remains the audit trail.

## Progress tracker

Legend: checked means implemented on the feature branch; unchecked means still pending final verification or merge.

- [x] Create `fix/unreviewed-topology-finalization` from current `master`.
- [x] Add active SourceUnit lookup.
- [x] Add Record SourceUnit-ID resolution with legacy fallback.
- [x] Resolve SourceUnit lineage recursively through retired replacement generations to immutable extraction roots.
- [x] Rebuild `source_extracted_text` deterministically from authoritative SourceUnits without changing reviewed Record text.
- [x] Keep optimistic validation side-effect free for legacy builds by normalizing SourceUnits in memory instead of persisting migration state inside validation callbacks.
- [x] Make source validation SourceUnit-aware.
- [x] Allow adjacent SourceUnit fragments that share one immutable extraction root.
- [x] Report missing, duplicate, inactive/missing-reference, fidelity, order, locator, and corpus-conservation failures as structured validation findings.
- [x] Disable corpus-wide conservation checks during Record-local validation.
- [x] Reconcile derived source projections before full publication-readiness validation.
- [x] Finalize topology server-side for `accept_unreviewed=True`.
- [x] Extend publication blocker keys to SourceUnit integrity failures.
- [x] Extend cELF conformance source-integrity keys.
- [x] Extend publication-readiness blocker counts.
- [x] Update English and French autonomous-publication copy.
- [x] Add regression coverage for one extraction block partitioned into multiple active SourceUnits.
- [x] Add nested replacement-lineage regression coverage.
- [x] Add duplicate active SourceUnit ownership regression coverage.
- [x] Add inactive SourceUnit reference regression coverage.
- [x] Add reordered SourceUnit regression coverage.
- [x] Add timed-media locator regression coverage.
- [x] Verify immutable-block evidence remains valid after SourceUnit partition.
- [x] Add autonomous-publication regression coverage for stale derived extraction projections.
- [x] Verify genuine missing source coverage still blocks autonomous publication.
- [x] Preserve the existing three-argument `validate_records` seam used by coordination/integration wrappers.
- [x] Update the user guide with the released behavior contract.
- [ ] Full backend lint, type, and test CI is green on the final head.
- [ ] Frontend/static/build CI is green on the final head.
- [ ] Format check is green on the final head.
- [ ] Exercise a previously failing real Corpus Builder build, when a reproducible local build is available.
- [ ] Rebase or merge latest `master` if the PR base moves materially before merge.
- [ ] Merge PR #532.

## Completion definition

This work is complete when **Use suggestions as-is** can publish a source-conserving corpus whose current topology is expressed through SourceUnits without forcing the reviewer to manually clear stale legacy topology/text-fidelity errors, while the same path still refuses a corpus with genuine missing, duplicated, invented, or reordered source material.

A green UI path alone is insufficient. Completion requires the backend publication path, validation payload, cELF conformance report, and persisted source provenance to agree on the same authoritative topology.
