# DerridAI Product Requirements

This directory contains the normative product requirements and requirements traceability matrices for DerridAI.

The requirements are derived from the current product on `master`, the cELF specification, current architecture and user documentation, and behavior already protected by the test suite. These documents are intended to make the product contract explicit enough that product, design, architecture, implementation, review, and verification can all trace back to stable requirement IDs.

## How to read these documents

Requirements use the normative terms **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**.

Each detailed requirements document uses a traceability table with stable IDs. Where an automated test directly or partially verifies a requirement, the requirement links to that test. Where no test fully establishes the requirement, the verification column says so rather than implying automated coverage.

Detailed requirements should trace upward to one or more [global requirements](GLOBAL_REQUIREMENTS.md). Where a cELF requirement applies, the product requirement should also identify the cELF source or invariant.

## Table of contents

| Section | Document | Description | Status |
| --- | --- | --- | --- |
| 1. Global product requirements | [GLOBAL_REQUIREMENTS.md](GLOBAL_REQUIREMENTS.md) | Product-wide invariants: provenance, scholarly authority, source vs. derived state, human review, traceability, reproducibility, local-first operation, UX, accessibility, internationalization, quality, and requirements governance. | Initial baseline |
| 2. Source acquisition, ingestion, and Corpus Builder | [INGESTION_AND_CORPUS_BUILDER.md](INGESTION_AND_CORPUS_BUILDER.md) | SourceDocument acquisition, media-aware extraction, hostile-input boundaries, OCR/transcription, source locations, segmentation, Record creation, revision, review, and publication readiness. | Initial requirements |
| 3. Metadata schemas, assertions, and human review | [METADATA_AND_REVIEW.md](METADATA_AND_REVIEW.md) | MetadataSchema and SchemaField contracts, stable field identity, FieldAssertion semantics, evidence and assessment, human authority, confirmed absence, review queues, and audit history. | Initial requirements |
| 4. Search, retrieval, evidence, and Research | [RESEARCH_RETRIEVAL_AND_EVIDENCE.md](RESEARCH_RETRIEVAL_AND_EVIDENCE.md) | Search and retrieval, hybrid candidate generation, reranking, provenance/support gates, EvidenceRef/EvidencePacket, Research generation, GeneratedClaim, SupportBinding, citation, memory, and research traceability. | Initial requirements |
| 5. Configurable pipelines, benchmarks, and System Data | [PIPELINES_AND_SYSTEM_DATA.md](PIPELINES_AND_SYSTEM_DATA.md) | Immutable pipeline definitions, stage contracts, fallbacks, traces, operational metrics, dry-run comparison, fixed benchmarks, reproducibility, and administrative presentation of system data. | Initial requirements |
| 6. Application shell, UX, accessibility, and internationalization | [UX_ACCESSIBILITY_AND_I18N.md](UX_ACCESSIBILITY_AND_I18N.md) | Navigation, canonical routes, workspace state, shared data-workspace patterns, progressive disclosure, semantic design tokens, responsive behavior, WCAG 2.2 AA, Help Center, and locale parity. | Initial requirements |
| 7. Records, Works, and corpus management | _Planned: `RECORDS_WORKS_AND_CORPORA.md`_ | Records workspace, Record Inspector, Works, work-level metadata, JSONL workspaces, subset/merge flows, corpus views, Semantic Map, and bulk operations. | Planned |
| 8. Metadata and research memory | _Planned: `MEMORY_AND_PRECEDENTS.md`_ | Metadata exemplars, Metadata Memory, claim memory, response memory, eligibility, owner scope, evidence status, rebuild semantics, and advisory authority. | Planned |
| 9. Vector stores and embeddings | _Planned: `VECTOR_STORES_AND_EMBEDDINGS.md`_ | Chroma modes, collection roles, embedding contracts, language mirrors, derived-state authority, upserts, pending synchronization, and round trips. | Planned |
| 10. LLM providers and model configuration | _Planned: `LLM_PROVIDERS.md`_ | Provider profiles, Ollama and OpenAI-compatible backends, discovery, warmup, model parameters, concurrency, secret handling, embeddings, and availability. | Planned |
| 11. Users, roles, capabilities, and security | _Planned: `USERS_ROLES_AND_SECURITY.md`_ | Authentication, capability enforcement, researcher/admin boundaries, sensitive-data filtering, secrets, destructive administration, and realtime authorization. | Planned |
| 12. Operations and realtime behavior | _Planned: `OPERATIONS_AND_REALTIME.md`_ | Background jobs, progress, cancellation, restart semantics, durable history, realtime events, polling fallback, Operations workspace, and undo behavior. | Planned |
| 13. Publication, import/export, and interoperability | _Planned: `PUBLICATION_AND_INTEROPERABILITY.md`_ | Publication validation, JSONL interchange, citation projections, import/export, cELF conformance, PROV, RO-Crate, nanopublication compatibility, and round trips. | Planned |
| 14. Persistence, backup, restore, and recovery | _Planned: `PERSISTENCE_BACKUP_AND_RECOVERY.md`_ | Canonical persistence, browser-local state, SQLite/system data, backup contents, restore integrity, derived-index recovery, and concurrent-operation guards. | Planned |
| 15. APIs and integration contracts | _Planned: `API_AND_INTEGRATION_CONTRACTS.md`_ | REST, GraphQL, realtime transport, typed contracts, errors, pagination, capability enforcement, schema/code generation, and compatibility. | Planned |
| 16. Reliability, performance, and failure handling | _Planned: `RELIABILITY_AND_PERFORMANCE.md`_ | Resource bounds, timeouts, concurrency, caching, partial failure, fallback behavior, dependency unavailability, stale state, and integrity-over-performance rules. | Planned |
| 17. Testing and quality gates | _Planned: `TESTING_AND_QUALITY_GATES.md`_ | Backend/frontend/E2E testing, Storybook, contracts, accessibility sweeps, localization checks, type/lint/format/build gates, and test-to-requirement linkage. | Planned |
| 18. Compatibility, migration, and deprecation | _Planned: `COMPATIBILITY_AND_MIGRATION.md`_ | Schema migration, FieldAssertion migration, pipeline migration, legacy routes/runtime behavior, historical inspectability, and deprecation policy. | Planned |
| 19. Master traceability matrix | _Planned: `TRACEABILITY_MATRIX.md`_ | Consolidated requirement → parent requirement → cELF requirement → implementation → test → documentation → status mapping. | Planned |

## Requirement ID prefixes

| Prefix | Area |
| --- | --- |
| `PRD-G-*` | Global product requirements |
| `PRD-ING-*` | Source acquisition and ingestion |
| `PRD-CB-*` | Corpus Builder |
| `PRD-MDS-*` | Metadata schemas |
| `PRD-REV-*` | Human review and editorial authority |
| `PRD-REC-*` | Records |
| `PRD-WRK-*` | Works |
| `PRD-COR-*` | Corpora and corpus management |
| `PRD-SRCH-*` | Search and retrieval |
| `PRD-EVD-*` | Evidence and citation |
| `PRD-RES-*` | Research |
| `PRD-MEM-*` | Memory and precedents |
| `PRD-PIPE-*` | Configurable pipelines and Pipeline Studio |
| `PRD-SYS-*` | System Data |
| `PRD-VEC-*` | Vector stores and embeddings |
| `PRD-LLM-*` | LLM providers |
| `PRD-NAV-*` | Application shell, navigation, and routing |
| `PRD-UX-*` | Shared UX and data workspaces |
| `PRD-HLP-*` | Help and product explainability |
| `PRD-USR-*` | Users, roles, capabilities, and security |
| `PRD-OPS-*` | Operations and realtime behavior |
| `PRD-PUB-*` | Publication/import/export/interoperability |
| `PRD-BKP-*` | Persistence, backup, restore, and recovery |
| `PRD-API-*` | API and integration contracts |
| `PRD-A11Y-*` | Accessibility |
| `PRD-I18N-*` | Internationalization |
| `PRD-NFR-*` | Cross-cutting non-functional requirements |
| `PRD-QA-*` | Testing and quality gates |
| `PRD-COMP-*` | Compatibility, migration, and deprecation |

## Verification labels

| Label | Meaning |
| --- | --- |
| **Direct** | An automated test directly exercises the requirement or its principal invariant. |
| **Partial** | Tests cover important parts of the requirement, but the requirement is broader than any individual test. |
| **Architectural** | Conformance requires design/code review plus lower-level tests; no single automated test establishes the full requirement. |
| **Gap** | A requirement is implemented or intended but lacks adequate automated verification and should receive explicit test coverage. |

## Change rules

1. Requirement IDs are stable identifiers and should not be renumbered merely to reorder a document.
2. New detailed requirements should identify their parent `PRD-G-*` requirement(s).
3. Requirements that are mechanically testable should link directly to the validating test file and, when useful, name the validating test case.
4. A pull request that changes a global requirement should update these documents in the same change.
5. A product behavior that intentionally violates a SHOULD-level requirement should document the exception and rationale.
6. cELF requirements remain authoritative for cELF conformance. These documents specify DerridAI product behavior in addition to those information-model invariants.
