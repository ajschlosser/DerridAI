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

# DerridAI Product Requirements

This directory contains the normative product requirements and requirements traceability matrices for DerridAI.

The requirements are derived from the current product, cELF, the architecture and user documentation, merged implementation history, and the existing automated test suite. The current baseline was re-audited against `master` from the `v0.81.0` release forward through the October 3, 2026 post-release work, including Corpus Builder concurrency/review persistence, repeatable metadata, evidence recovery and generalized locators, record-size-aware Research, realtime invalidation, progressive loading, published research sites/SDK/browser indexing, and the latest static-site Vue reference interface. The purpose is to make the product contract explicit enough that product, design, architecture, implementation, review, and verification can all trace back to stable requirement IDs.

## How to use these documents

Requirements use **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in their normative sense.

Each detailed document contains requirement tables with stable IDs, acceptance criteria, parent/global trace, implementation/documentation trace, and verification links. Where an automated test exists, the row links it. Where a requirement directly corresponds to a tracked cELF conformance clause, the [Master Traceability Matrix](TRACEABILITY_MATRIX.md) also names and links the exact specification key (for example `CORE-ID-016` or `CLM-ID-005`). Where test coverage is incomplete, the row says **Partial**, **Architectural**, or **Gap** rather than implying verification.

Detailed requirements trace upward to [Global Product Requirements](GLOBAL_REQUIREMENTS.md). cELF remains authoritative for cELF conformance; these documents specify DerridAI product behavior in addition to those information-model requirements.

## Table of contents

| Section                                                           | Document                                                                   | Description                                                                                                                                                                                                                   |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Global product requirements                                    | [GLOBAL_REQUIREMENTS.md](GLOBAL_REQUIREMENTS.md)                           | Product-wide invariants: provenance, scholarly authority, source vs. derived state, human review, traceability, reproducibility, local-first operation, UX, accessibility, internationalization, quality, and change control. |
| 2. Source acquisition, ingestion, and Corpus Builder              | [INGESTION_AND_CORPUS_BUILDER.md](INGESTION_AND_CORPUS_BUILDER.md)         | SourceDocument acquisition, hostile-input boundaries, media-aware extraction, OCR/transcription, source locators, segmentation, Record creation, revision, validation, review, and publication readiness.                     |
| 3. Metadata schemas, assertions, and human review                 | [METADATA_AND_REVIEW.md](METADATA_AND_REVIEW.md)                           | MetadataSchema/SchemaField contracts, stable field identity, FieldAssertion semantics, attribution, evidence/assessment policy, human ownership, confirmed absence, review queues, and auditability.                          |
| 4. Search, retrieval, evidence, and Research                      | [RESEARCH_RETRIEVAL_AND_EVIDENCE.md](RESEARCH_RETRIEVAL_AND_EVIDENCE.md)   | Search/hybrid retrieval, bounded automatic sizing, scope-aware traces, evidence recovery/support gates, generalized EvidenceRef locators, EvidencePacket, Research generation, SupportBinding, deterministic citation binding, grading, and memory use. |
| 5. Configurable pipelines, benchmarks, and System Data            | [PIPELINES_AND_SYSTEM_DATA.md](PIPELINES_AND_SYSTEM_DATA.md)               | Immutable pipeline definitions, stages/strategies, validators, fallbacks, traces, operational telemetry, dry-run comparison, fixed benchmarks, reproducibility, and administrative System Data behavior.                      |
| 6. Application shell, UX, accessibility, and internationalization | [UX_ACCESSIBILITY_AND_I18N.md](UX_ACCESSIBILITY_AND_I18N.md)               | Task-oriented navigation, canonical routes, workspace URL state, shared data-workspace patterns, progressive disclosure, Help Center, design tokens, responsive behavior, WCAG 2.2 AA, and locale parity.                     |
| 7. Records, Works, and corpus management                          | [RECORDS_WORKS_AND_CORPORA.md](RECORDS_WORKS_AND_CORPORA.md)               | Records workspace/Inspector, Works, work/corpus-scoped metadata, bulk operations, source/evidence navigation, semantic maps, derived graph views, and corpus-management authority boundaries.                                 |
| 8. Metadata and research memory                                   | [MEMORY_AND_PRECEDENTS.md](MEMORY_AND_PRECEDENTS.md)                       | Metadata exemplars/precedents, editorial memory, claim memory, response memory, eligibility, owner scope, stable field identity, evidence status, projection indexes, fallback, and advisory authority.                       |
| 9. Vector stores and embeddings                                   | [VECTOR_STORES_AND_EMBEDDINGS.md](VECTOR_STORES_AND_EMBEDDINGS.md)         | Chroma embedded/HTTP modes, collection identity, derived-state authority, embedding contracts, language mirrors, synchronization/upserts, researcher access, and recovery/rebuild semantics.                                  |
| 10. LLM providers and model configuration                         | [LLM_PROVIDERS.md](LLM_PROVIDERS.md)                                       | Provider profiles, Ollama/OpenAI-compatible backends, model discovery, testing, warmup, provider switching, concurrency, credentials, embedding profiles, and degraded-state behavior.                                        |
| 11. Users, roles, capabilities, and security                      | [USERS_ROLES_AND_SECURITY.md](USERS_ROLES_AND_SECURITY.md)                 | Authentication, session hardening, role/capability enforcement, researcher/admin boundaries, blind-review privacy, owner scope, secrets, realtime authorization, and destructive administration.                              |
| 12. Operations and realtime behavior                              | [OPERATIONS_AND_REALTIME.md](OPERATIONS_AND_REALTIME.md)                   | Background-job lifecycle, progress, cancellation, durable history, restart semantics, Operations UI, WebSocket authorization, replay/resync, bounded delivery, polling fallback, and ephemeral live hints.                    |
| 13. Publication, export/import, and interoperability              | [PUBLICATION_AND_INTEROPERABILITY.md](PUBLICATION_AND_INTEROPERABILITY.md) | Publication validation, JSONL materialization, static research-site delivery modes, reader-optimized Records, browser semantic indexing, provider/proxy boundaries, SDK/citation binding, integrity, cELF interoperability, PROV, RO-Crate, and nanopublication compatibility. |
| 14. Persistence, backup, restore, and recovery                    | [PERSISTENCE_BACKUP_AND_RECOVERY.md](PERSISTENCE_BACKUP_AND_RECOVERY.md)   | SQLite/system durability, browser-vs-server state, job restart behavior, backup manifests, credentials disclosure, restore validation, ZIP safety, Chroma rollback, and recovery.                                             |
| 15. APIs and integration contracts                                | [API_AND_INTEGRATION_CONTRACTS.md](API_AND_INTEGRATION_CONTRACTS.md)       | REST commands/mutations, read-only GraphQL, realtime transport, typed frontend contracts, authorization, bounds, stable errors, schema/code generation, and compatibility.                                                    |
| 16. Reliability, performance, and failure handling                | [RELIABILITY_AND_PERFORMANCE.md](RELIABILITY_AND_PERFORMANCE.md)           | Failure visibility, resource limits, batching/checkpoints, concurrency safety, explicit fallbacks, derived-side-effect isolation, restart/realtime resilience, and integrity-over-performance constraints.                    |
| 17. Testing and quality gates                                     | [TESTING_AND_QUALITY_GATES.md](TESTING_AND_QUALITY_GATES.md)               | Test taxonomy, backend/frontend contracts, unit/regression/characterization/workflow tests, accessibility, localization, Storybook/build/static gates, release consistency, and requirement-to-test linkage.                  |
| 18. Compatibility, migration, and deprecation                     | [COMPATIBILITY_AND_MIGRATION.md](COMPATIBILITY_AND_MIGRATION.md)           | FieldAssertion/schema/pipeline migrations, legacy inspectability, safe execution boundaries, route/runtime migration, characterization baselines, and deprecation policy.                                                     |
| 19. Master traceability matrix                                    | [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md)                           | Consolidated index of all requirement IDs, source documents, parent/global traces, and linked verification status/tests.                                                                                                      |

## Requirement ID prefixes

| Prefix       | Area                                       |
| ------------ | ------------------------------------------ |
| `PRD-G-*`    | Global product requirements                |
| `PRD-ING-*`  | Source acquisition and ingestion           |
| `PRD-CB-*`   | Corpus Builder                             |
| `PRD-MDS-*`  | Metadata schemas and FieldAssertions       |
| `PRD-REV-*`  | Human review and editorial authority       |
| `PRD-REC-*`  | Records                                    |
| `PRD-WRK-*`  | Works                                      |
| `PRD-COR-*`  | Corpora and corpus management              |
| `PRD-SRCH-*` | Search and retrieval                       |
| `PRD-EVD-*`  | Evidence and citation                      |
| `PRD-RES-*`  | Research                                   |
| `PRD-MEM-*`  | Memory and precedents                      |
| `PRD-PIPE-*` | Configurable pipelines and Pipeline Studio |
| `PRD-SYS-*`  | System Data                                |
| `PRD-VEC-*`  | Vector stores and embeddings               |
| `PRD-LLM-*`  | LLM providers                              |
| `PRD-NAV-*`  | Application shell, navigation, and routing |
| `PRD-UX-*`   | Shared UX and data workspaces              |
| `PRD-HLP-*`  | Help and product explainability            |
| `PRD-USR-*`  | Users, roles, capabilities, and security   |
| `PRD-OPS-*`  | Operations and realtime behavior           |
| `PRD-PUB-*`  | Publication/import/export/interoperability |
| `PRD-BKP-*`  | Persistence, backup, restore, and recovery |
| `PRD-API-*`  | API and integration contracts              |
| `PRD-A11Y-*` | Accessibility                              |
| `PRD-I18N-*` | Internationalization                       |
| `PRD-NFR-*`  | Cross-cutting non-functional requirements  |
| `PRD-QA-*`   | Testing and quality gates                  |
| `PRD-COMP-*` | Compatibility, migration, and deprecation  |

## Verification labels

| Label             | Meaning                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Direct**        | One or more automated tests directly exercise the requirement or its principal invariant.                                 |
| **Partial**       | Tests cover important parts of the requirement, but the full requirement requires broader review or additional scenarios. |
| **Architectural** | Conformance spans multiple components/design boundaries and cannot be established by one test.                            |
| **Gap**           | Adequate automated verification has not yet been identified and should be treated as explicit QA debt.                    |

## Traceability model

The intended chain is:

`cELF / product invariant → PRD-G global requirement → area requirement → implementation/documentation → automated test or explicit verification gap`

The [Master Traceability Matrix](TRACEABILITY_MATRIX.md) provides a consolidated view of requirement text, source document, parent/global trace, exact cELF conformance keys where a direct mapping exists, and linked verification. A blank cELF-key cell means the product requirement is product-specific or that no tracked cELF catalogue key is precise enough; it does not imply that cELF is irrelevant. The detailed area document remains authoritative for each requirement's complete acceptance criteria and context.

## Change rules

1. Requirement IDs are stable. Do not renumber existing IDs merely to reorder prose.
2. New detailed requirements should identify their parent `PRD-G-*` requirement(s).
3. Mechanically testable requirements should link directly to validating tests; missing coverage must be labeled explicitly. Requirements with a direct normative cELF correspondence should also identify the exact tracked specification key in the master matrix.
4. A pull request that changes a global requirement should update the requirement document and affected tests in the same change.
5. A product behavior that intentionally departs from a SHOULD-level requirement should document the exception and rationale.
6. cELF requirements remain authoritative for cELF conformance.
7. When implementation changes make a requirement obsolete, deprecate or supersede it deliberately rather than silently deleting historical traceability.
