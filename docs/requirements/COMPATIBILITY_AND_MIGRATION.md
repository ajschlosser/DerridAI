# Compatibility, Migration, and Deprecation Requirements

**Scope:** Data/schema compatibility, FieldAssertion migration, pipeline migration, legacy routes/runtime behavior, historical inspectability, deprecation, and migration safety.  
**Parent requirements:** [Global requirements](GLOBAL_REQUIREMENTS.md)

## General compatibility requirements

| ID | Requirement | Acceptance criteria | Parent | Implementation trace | Verification |
| --- | --- | --- | --- | --- | --- |
| **PRD-COMP-001** | Durable user/scholarly state SHOULD remain readable across product evolution where doing so does not violate current integrity requirements. | Existing corpora, schemas, assertions, memories, pipelines, and configured workspaces are migrated or loaded through explicit compatibility paths rather than silently discarded. | PRD-G-039 | [Architecture](../ARCHITECTURE.md) | **Architectural/Partial:** subsystem migration/regression tests |
| **PRD-COMP-002** | Compatibility code MUST NOT cause legacy representations to become the preferred architecture for new features. | New code writes current contracts; legacy loaders/adapters exist at boundaries and do not require new feature logic to duplicate old state shapes. | PRD-G-035, PRD-G-039 | [FieldAssertion migration](../FIELD_ASSERTION_MIGRATION.md); [Architecture](../ARCHITECTURE.md) | **Architectural/Partial:** FieldAssertion/schema/pipeline tests |
| **PRD-COMP-003** | Where legacy behavior conflicts with provenance, authority, security, or evidence correctness, current integrity requirements take precedence over behavioral compatibility. | Unsafe/invalid historical definitions may remain inspectable but are not executed as though valid. | PRD-G-039, PRD-G-040 | [cELF](../../SPECIFICATION.md) | **Direct/Partial:** [evidence pipeline](../../tests/test_evidence_pipeline.py); security/route tests |

## Metadata and schema migration

| ID | Requirement | Acceptance criteria | Parent | Implementation trace | Verification |
| --- | --- | --- | --- | --- | --- |
| **PRD-COMP-004** | Legacy top-level scholarly metadata MUST migrate lazily/idempotently into canonical FieldAssertions without changing the selected scholarly value. | Re-reading/migrating a Record does not duplicate assertions or erase original provenance; public materialized values remain available. | PRD-G-004, PRD-G-017, PRD-G-039 | [FieldAssertion migration](../FIELD_ASSERTION_MIGRATION.md) | **Direct:** [FieldAssertions](../../tests/test_field_assertions.py); [DerridAI ledger](../../tests/test_derridai_ledger.py) |
| **PRD-COMP-005** | Compatibility loaders MAY accept older metadata-schema formats, but new writes/documentation MUST use the current schema identity/retrieval contract. | Older supported schema files import through deterministic migration/defaulting; current export writes the current format. | PRD-G-007, PRD-G-039 | [Metadata Schemas](../METADATA_SCHEMAS.md) | **Direct:** [metadata schema](../../tests/test_metadata_schema.py); [metadata field scope](../../tests/test_metadata_field_scope.py) |
| **PRD-COMP-006** | Legacy work-wide schema flags MUST migrate to the current corpus-scope semantics deterministically. | Format-1 `applies_to_work` maps to the current corpus-scoped field contract without ambiguous per-Record duplication. | PRD-G-007, PRD-G-039 | [Metadata Schemas](../METADATA_SCHEMAS.md) | **Direct:** [metadata field scope](../../tests/test_metadata_field_scope.py) |
| **PRD-COMP-007** | Builds created before schema snapshots existed MUST use the documented historical-default fallback rather than the current mutable saved schema. | Historical builds remain interpretable without retroactively changing their schema assumptions. | PRD-G-014, PRD-G-039 | [Metadata Schemas](../METADATA_SCHEMAS.md) | **Partial:** metadata schema/run-guidance tests |

## Pipeline migration and deprecation

| ID | Requirement | Acceptance criteria | Parent | Implementation trace | Verification |
| --- | --- | --- | --- | --- | --- |
| **PRD-COMP-008** | Historical pipeline versions MAY remain stored/inspectable after strategy or validation requirements change. | User can inspect the old definition/status/warnings for audit/reproducibility. | PRD-G-014, PRD-G-039 | [Pipeline migration handoff](../PIPELINE_MIGRATION_HANDOFF.md) | **Direct/Partial:** pipeline store/manager tests |
| **PRD-COMP-009** | A legacy pipeline that lacks currently mandatory provenance/support gates MUST NOT execute. | Compiler/validator returns a clear cannot-execute result while preserving the saved definition. | PRD-G-012, PRD-G-039 | [PR #279](https://github.com/ajschlosser/DerridAI/pull/279) | **Direct:** [evidence pipeline](../../tests/test_evidence_pipeline.py) (`test_legacy_reviewer_pipeline_remains_inspectable_but_not_executable`) |
| **PRD-COMP-010** | Pipeline import/migration SHOULD validate strategy-version compatibility and dependencies before assignment/execution. | Unsupported/deprecated strategy versions produce actionable diagnostics without mutating the stored source definition. | PRD-G-010, PRD-G-039 | [Pipeline migration handoff](../PIPELINE_MIGRATION_HANDOFF.md) | **Partial/Gap:** pipeline contract tests cover graph/strategy validity; explicit strategy-version migration tests should expand as deprecation tooling matures |

## UI/route/runtime migration

| ID | Requirement | Acceptance criteria | Parent | Implementation trace | Verification |
| --- | --- | --- | --- | --- | --- |
| **PRD-COMP-011** | Canonical route migrations SHOULD provide redirects/aliases for supported historical links where practical and safe. | Old bookmarks do not unnecessarily fail when the destination has a clear current equivalent; redirects do not preserve unsafe query-state semantics. | PRD-G-020, PRD-G-039 | [PR #270](https://github.com/ajschlosser/DerridAI/pull/270) | **Partial/Gap:** router/navigation tests; maintain explicit redirect regression coverage for supported legacy routes |
| **PRD-COMP-012** | Legacy runtime decomposition MUST preserve user-visible behavior until a deliberate product requirement changes it. | Refactors from legacy runtime/string-rendered code to Vue/domain modules retain established workflow semantics; intentional redesign updates requirements/tests rather than snapshots alone. | PRD-G-035, PRD-G-039 | [Architecture](../ARCHITECTURE.md); [AGENTS](../../AGENTS.md) | **Direct/Partial:** [legacy DOM baseline](../../web/tests/e2e/legacy-dom-baseline.spec.ts); frontend characterization tests |
| **PRD-COMP-013** | New functionality MUST NOT add dependencies on deprecated monolithic runtime interfaces when an established typed/domain service exists. | Migration moves behavior toward typed API/domain/components rather than adding new `runtime.js` branches. | PRD-G-035 | [Architecture](../ARCHITECTURE.md) | **Architectural:** code review/static boundaries |
| **PRD-COMP-014** | Characterization snapshots MUST be regenerated only for understood intentional changes. | Refactor PRs explain snapshot changes; unexplained snapshot churn is treated as a possible regression. | PRD-G-036, PRD-G-039 | testing contract | **Process:** [legacy DOM baseline](../../web/tests/e2e/legacy-dom-baseline.spec.ts) |

## Deprecation requirements

| ID | Requirement | Acceptance criteria | Parent | Implementation trace | Verification |
| --- | --- | --- | --- | --- | --- |
| **PRD-COMP-015** | Deprecation MUST distinguish “no longer recommended for new use” from “cannot safely execute/read.” | Deprecated but valid definitions can remain readable/usable according to policy; unsafe definitions are disabled with reason. | PRD-G-039 | migration contracts | **Architectural/Partial:** pipeline/schema compatibility tests |
| **PRD-COMP-016** | Removing a durable field/route/contract MUST identify migration/export impact before deletion. | PR documents affected persisted state, compatibility window or migration, and associated requirement/test updates. | PRD-G-032, PRD-G-039 | requirements governance | **Process:** change review |
| **PRD-COMP-017** | Migration operations that materially transform scholarly data MUST be deterministic, idempotent where practical, and auditable. | Re-running migration does not compound changes; source/target identity and migration version/method are recoverable. | PRD-G-002, PRD-G-011, PRD-G-014 | [cELF](../../SPECIFICATION.md) | **Direct/Partial:** FieldAssertion/schema migration tests; add dedicated migration fixtures for future migrations |
