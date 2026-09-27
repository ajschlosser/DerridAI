<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# GraphQL read façade

DerridAI exposes a small, **read-only**, cELF-aware GraphQL endpoint beside the REST API:

```text
GraphQL  = which scholarly/provenance data do I want to read?   POST /api/graphql
REST     = which explicit state change do I want to perform?     /api/...
WebSocket= what is happening right now?                          WS /api/ws/events (docs/REALTIME.md)
```

GraphQL and WebSockets are choices of the DerridAI reference implementation. They are not normative cELF requirements; cELF semantics live in [SPECIFICATION.md](../SPECIFICATION.md).

## Policy

- **Queries only.** There is no Mutation root. Every command (uploads, review decisions, claim validation, job creation/cancellation, schema CRUD, publication, backup/restore, administration) stays on REST. The schema self-check (`assert_root_fields_classified`) fails at import if a Mutation or Subscription root appears.
- **No subscriptions.** Live operational events use the WebSocket realtime plane.
- **POST only.** GET queries, multipart uploads and GraphQL-over-WebSocket protocols are disabled.
- **IDE and introspection off by default** (`GRAPHQL_IDE_ENABLED`, `GRAPHQL_INTROSPECTION_ENABLED`). Enable them only for local development.
- **Bounded documents.** `GRAPHQL_MAX_DEPTH` (8), `GRAPHQL_MAX_ALIASES` (20) and `GRAPHQL_MAX_TOKENS` (2000) are enforced by Strawberry extensions. Each paginated root also clamps its own `limit` (`corpus_build.review_queue`/`records` to `MAX_QUEUE_PAGE` = 200, `vector_store.records` to `MAX_RECORD_PAGE` = 1000). `GRAPHQL_MAX_RECORD_BYTES` caps the client Record snapshot accepted by `record_graph`.
- **Masked errors.** Only deliberate public errors (`api/app/graphql/errors.py`: forbidden, not found, invalid argument, unavailable) and the caller's own validation errors are returned; any other exception becomes `Internal server error.`.
- **Partial data is a failure.** The frontend client (`web/src/api/graphql/client.ts`) treats any `errors` entry as a failed request even with HTTP 200.

## Code layout

| Path                                          | Role                                                                                                                                              |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api/app/celf_queries/`                       | Transport-independent read services shared with REST: `AccessContext`, owner scoping, blind-review scrubbing, support-binding joins, corpus queue/vector/research-run/metadata-exemplar reads. |
| `api/app/graphql/schema.py`                   | Query root assembly, limits, masking, introspection rule, default-deny self-check.                                                                |
| `api/app/graphql/queries/`                    | Root fields grouped by area (`celf`, `records`, `research`, `corpus`, `vector`, `metadata`). Each declares its policy with `classify()`.          |
| `api/app/graphql/types/`                      | Typed cELF objects (`SourceSpan`, `FieldAssertion`, `EvidenceRef`, `GeneratedClaim`, `SupportBinding`, graph nodes/edges, model, corpus review, vector, research run, metadata exemplar). |
| `api/app/graphql/permissions.py`              | `require_authenticated`, `require_admin`, `require_capability`, `require_owner_or_admin`.                                                          |
| `api/app/graphql/loaders.py`                  | Request-scoped DataLoaders (claims by id, support bindings by claim, one corpus build's Records per request).                                     |
| `api/app/graphql/errors.py`                   | `PublicError` and its subclasses (`Forbidden`, `NotFoundError`, `BadRequest`, `Unavailable`); each sets a stable `extensions.code`.                |
| `scripts/export_graphql_schema.py`            | Writes `web/src/api/graphql/schema.graphql` from the live Strawberry schema. `--check` fails if the checked-in SDL is stale (CI gate).            |
| `web/codegen.ts`                              | GraphQL Code Generator config: reads `schema.graphql` and every `web/src/**/*.graphql`, emits `web/src/api/graphql/generated.ts`.                  |
| `web/src/api/graphql/client.ts`               | Typed client: `execute(document, variables, { signal })`, `GraphQLRequestError` (`hasCode`), `isAbortError`.                                       |
| `web/src/api/graphql/generated.ts`            | Generated (never hand-edited): typed `TypedDocumentString`s and result/variable types for every document.                                          |
| `web/src/features/*/graphql/*.graphql`        | Operation and fragment documents, colocated with the feature that uses them (not one shared `operations/` folder).                                 |
| `scripts/check_frontend_graphql_contract.py`  | Validates every `.graphql` document under `web/src/` against the live schema (run by `tests/test_frontend_graphql_contract.py`).                   |

Resolvers are thin: they authorize, call a `celf_queries` function through `run_in_threadpool` (persistence is synchronous), and map the result onto types. REST routes (`routers/stores.py`, `routers/system_data.py`, `routers/derridai.py`) call the same services, so REST and GraphQL cannot drift in authorization, owner scoping, blind-review presentation or support resolution.

## Current roots

| Root                                               | Key fields                                                                                       | REST equivalent                                                                                          | Policy                        |
| ---------------------------------------------------| ----------------------------------------------------------------------------------------------------| -------------------------------------------------------------------------------------------------------------| --------------------------------|
| `celf_model`                                       | —                                                                                                  | `GET /api/derridai/model`                                                                                | authenticated                 |
| `record_graph(record, include_assertion_history)`  | —                                                                                                  | `POST /api/derridai/graph/record`                                                                        | administrator                  |
| `generated_claim(claim_id)`                        | `support_bindings`, `similar_validated_claims(limit)`                                             | `GET /api/derridai/claims/{id}/similar`                                                                  | administrator                  |
| `corpus_build(build_id)`                           | `review_queue(filter, offset, limit)`, `rows(record_ids)`, `record(record_id)`, `records(record_ids)`, `metadata_facets(fields)` | `GET /api/pdf/corpus-builds/{id}/records`                                                                 | administrator                  |
| `vector_store(name)`                               | `records(offset, limit, work)`, `record(chroma_id)`, `works`                                      | `GET /api/stores/{name}/records`, `GET /api/stores/{name}/records/{id}`, `GET /api/stores/{name}/works`  | `corpus.read` capability       |
| `research_run(run_id)`                             | `generated_claims` (administrator-only field)                                                     | `GET /api/jobs/{id}` (RAG jobs)                                                                           | owner or administrator         |
| `metadata_exemplars(filter, offset, limit)`        | —                                                                                                  | `GET /api/system/data/metadata-exemplars`                                                                | administrator                   |

`record_graph`, `generated_claim` and `corpus_build` stay administrator-only because their REST equivalents are administrator-only and their fields carry assertion values or full Record text. `vector_store` is reachable by any account with the `corpus.read` capability (including Researchers) because `VectorRecordRow`/`VectorRecord` apply the same researcher-text policy as REST (`text_summarized` reports when a Record's text was shortened for that reason); hidden/system collections and `_response_cache` read as `NotFound` for non-administrators, matching REST. `research_run` is owner-scoped like `GET /api/jobs/{id}`; only `generated_claims` is further restricted to administrators. The underlying services are owner/capability-scoped regardless of root policy, so opening a root further is a change in `classify()`, not a new query path. Researcher text protection (`RESEARCHER_TEXT_MAX_CHARS`) must be designed into any root before it is opened to non-administrators.

`POST /api/graphql` itself is reachable by non-administrators with `corpus.read` (route policy), so a researcher can read `celf_model` and `vector_store` and nothing else.

### `CorpusBuildReview`: rows vs. Records

A queue page (`review_queue`, `rows`) returns `CorpusQueueRow` — identifiers, page labels, review state and a short `text_preview`, never the full text or metadata. Opening a Record for review reads `record`/`records`, which return `CorpusRecord` (the reviewer-presented Record, including the transitional `review_document: JSON` field used by the review panels). This split is why the Corpus Builder review queue page is more than 10× smaller than the REST response it replaces (`tests/test_graphql_record_reads.py`), and why a second reviewer never receives another reviewer's sealed metadata through a queue row: build-wide `metadata_facets`/counts are computed on the reviewer-presented view, not the raw stored Records.

### `VectorStore`: derived, not canonical

Every `VectorRecordRow`/`VectorRecord` field is read from a Chroma-backed projection (`materialization: "vector_projection"`), never the canonical corpus/review store. `vector_store.record(chroma_id).graph` builds a `record_graph` from the stored record's own fields (`origin: "vector_projection"`), which is weaker provenance than a `record_graph` built from the canonical Record — do not treat it as authoritative for anything beyond "what this vector currently holds."

## cELF fidelity rules

- Field names keep cELF snake_case (`StrawberryConfig(auto_camel_case=False)`); there is no second naming system.
- `FieldAssertion` is never reduced to field/value: it exposes derivation, evaluation, authority and value status, confidence, reason, actor, model, run, revision, evidence, creation time, supersession and whether it is the current assertion.
- `speaker`, `quoted_speaker` and `position_holder` are separate assertions and stay separate.
- `SourceSpan` is medium-aware. Audio spans carry `time_start`/`time_end`/`speaker` and never inherit PDF page or character fields.
- `materialization`, `status` and `record_state_origin` say what is canonical, embedded, a reference, or a client snapshot. Chroma-derived data is never labelled canonical. Stale or unresolvable support bindings stay visible with their status.
- `similar_validated_claims` is advisory precedent only (`advisory: true`); similarity never asserts support.

## Blind review and privacy

A client Record snapshot is passed through the same second-opinion scrubber used for corpus-build responses before any graph is built, with the caller's reviewer identity. A second reviewer therefore never sees the sealed first answer through record fields, field assertions, node `details`, or nested relationships. Claims and support bindings are always read server-side and owner-scoped; the client snapshot supplies Record state only. `CorpusBuildReview`'s rows and Records are read through the same reviewer-presented view REST uses, so a second reviewer never sees a sealed first answer through a queue row, a Record field, or a build-wide facet.

## Frontend: codegen and fragment colocation

GraphQL operation and fragment documents live next to the feature that uses them (for example `web/src/features/corpus-builder/graphql/CorpusReviewQueue.graphql`), not in one shared `operations/` folder. Types are never hand-written:

1. `python scripts/export_graphql_schema.py` writes `web/src/api/graphql/schema.graphql` from the live Strawberry schema.
2. `npm run codegen` (from `web/`) reads that SDL plus every `web/src/**/*.graphql` and writes `web/src/api/graphql/generated.ts` — one `TypedDocumentString` and matching result/variable types per named operation or fragment.
3. Application code imports the generated document and calls `execute(document, variables, { signal })` from `web/src/api/graphql/client.ts`. There are no raw query strings or a name-based `runOperation` dispatcher.

`python scripts/export_graphql_schema.py --check` and `npm run codegen:check` fail CI when either generated artifact is stale relative to the schema/documents; both files are excluded from Prettier (`.prettierignore`) because their exact bytes are checked by their own generators, not reformatted.

## Adding a field or root

1. Add or extend a transport-independent function in `app/celf_queries/` (no Strawberry, FastAPI or WebSocket imports) and make the REST route call it too when one exists.
2. Add the type/field under `app/graphql/types/`; use `JSON` only where the schema genuinely allows arbitrary user-defined values.
3. For a root field, call `classify("<name>", "<policy>")` and enforce the matching `require_*` helper at the top of the resolver. Unclassified roots fail the schema self-check.
4. Batch any per-parent lookup through a request-scoped loader in `loaders.py`; never add module-level caches.
5. Run `python scripts/export_graphql_schema.py` to refresh `schema.graphql`, add the frontend document under `web/src/features/<feature>/graphql/<Name>.graphql` (colocated with its feature; shared fields go in a `Fields` fragment), and run `npm run codegen`. The contract test (`tests/test_frontend_graphql_contract.py`) and the schema-artifact test (`tests/test_graphql_schema_artifact.py`) validate both are in sync.
6. Add parity tests against the REST equivalent (if any), authorization tests, and blind-review/researcher-text tests for anything text-bearing.
