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
- **Bounded documents.** `GRAPHQL_MAX_DEPTH` (8), `GRAPHQL_MAX_ALIASES` (20) and `GRAPHQL_MAX_TOKENS` (2000) are enforced by Strawberry extensions. The largest real frontend operation (`RecordGraph`) has depth 3; the limits leave room for nested provenance reads without allowing amplification. `GRAPHQL_MAX_RECORD_BYTES` caps the client Record snapshot accepted by `record_graph`.
- **Masked errors.** Only deliberate public errors (forbidden, not found, invalid argument, unavailable) and the caller's own validation errors are returned; any other exception becomes `Internal server error.`.
- **Partial data is a failure.** The frontend client treats any `errors` entry as a failed request even with HTTP 200.

## Code layout

| Path                                         | Role                                                                                                                                 |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `api/app/celf_queries/`                      | Transport-independent read services shared with REST: `AccessContext`, owner scoping, blind-review scrubbing, support-binding joins. |
| `api/app/graphql/schema.py`                  | Query root assembly, limits, masking, introspection rule, default-deny self-check.                                                   |
| `api/app/graphql/queries/`                   | Root fields grouped by area (`celf`, `records`, `research`). Each declares its policy with `classify()`.                             |
| `api/app/graphql/types/`                     | Typed cELF objects (`SourceSpan`, `FieldAssertion`, `EvidenceRef`, `GeneratedClaim`, `SupportBinding`, graph nodes/edges, model).    |
| `api/app/graphql/permissions.py`             | `require_authenticated`, `require_admin`, `require_capability`, `require_owner_or_admin`.                                            |
| `api/app/graphql/loaders.py`                 | Request-scoped DataLoaders (claims by id, support bindings by claim).                                                                |
| `web/src/api/graphql/`                       | Typed client (`graphqlRequest`, `runOperation`) and the checked-in `.graphql` operation documents.                                   |
| `scripts/check_frontend_graphql_contract.py` | Validates every frontend operation against the live schema (run by `tests/test_frontend_graphql_contract.py`).                       |

Resolvers are thin: they authorize, call a `celf_queries` function through `run_in_threadpool` (persistence is synchronous), and map the result onto types. REST routes in `routers/derridai.py` call the same services, so REST and GraphQL cannot drift in authorization, owner scoping, blind-review presentation or support resolution.

## Current roots

| Root                                                                                | REST equivalent                         | Policy        |
| ----------------------------------------------------------------------------------- | --------------------------------------- | ------------- |
| `celf_model`                                                                        | `GET /api/derridai/model`               | authenticated |
| `record_graph(record, include_assertion_history)`                                   | `POST /api/derridai/graph/record`       | administrator |
| `generated_claim(claim_id)` → `support_bindings`, `similar_validated_claims(limit)` | `GET /api/derridai/claims/{id}/similar` | administrator |

`record_graph` and `generated_claim` stay administrator-only because the REST `/api/derridai/*` routes are administrator-only and graph node details carry assertion values. The underlying services are owner-scoped regardless, so opening a root to a capability later is a policy change in `classify()`, not a new query path. Researcher text protection (`RESEARCHER_TEXT_MAX_CHARS`) must be designed into any root before it is opened to non-administrators; no current root returns Record text to a researcher.

`POST /api/graphql` itself is reachable by non-administrators with `corpus.read` (route policy), so a researcher can read the type-level `celf_model` and nothing else.

## cELF fidelity rules

- Field names keep cELF snake_case (`StrawberryConfig(auto_camel_case=False)`); there is no second naming system.
- `FieldAssertion` is never reduced to field/value: it exposes derivation, evaluation, authority and value status, confidence, reason, actor, model, run, revision, evidence, creation time, supersession and whether it is the current assertion.
- `speaker`, `quoted_speaker` and `position_holder` are separate assertions and stay separate.
- `SourceSpan` is medium-aware. Audio spans carry `time_start`/`time_end`/`speaker` and never inherit PDF page or character fields.
- `materialization`, `status` and `record_state_origin` say what is canonical, embedded, a reference, or a client snapshot. Chroma-derived data is never labelled canonical. Stale or unresolvable support bindings stay visible with their status.
- `similar_validated_claims` is advisory precedent only (`advisory: true`); similarity never asserts support.

## Blind review and privacy

A client Record snapshot is passed through the same second-opinion scrubber used for corpus-build responses before any graph is built, with the caller's reviewer identity. A second reviewer therefore never sees the sealed first answer through record fields, field assertions, node `details`, or nested relationships. Claims and support bindings are always read server-side and owner-scoped; the client snapshot supplies Record state only.

## Adding a field or root

1. Add or extend a transport-independent function in `app/celf_queries/` (no Strawberry, FastAPI or WebSocket imports) and make the REST route call it too when one exists.
2. Add the type/field under `app/graphql/types/`; use `JSON` only where the schema genuinely allows arbitrary user-defined values.
3. For a root field, call `classify("<name>", "<policy>")` and enforce the matching `require_*` helper at the top of the resolver. Unclassified roots fail the schema self-check.
4. Batch any per-parent lookup through a request-scoped loader in `loaders.py`; never add module-level caches.
5. Add the frontend document under `web/src/api/graphql/operations/<Name>.graphql`, register it in `operations/index.ts`, and add its result/variable types to `types.ts`. The contract test validates it against the schema.
6. Add parity tests against the REST equivalent (if any), authorization tests, and blind-review/researcher-text tests for anything text-bearing.
