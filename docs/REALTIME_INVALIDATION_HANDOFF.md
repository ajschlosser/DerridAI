<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Realtime data invalidation: handoff

Goal: pages show server changes immediately, with one mechanism and no HTTP polling. Delete this file once every item under "Remaining work" is done; the lasting contract lives in [REALTIME.md](REALTIME.md).

## The pattern (decided)

- The socket only says _that_ a registered data resource changed (`resource.changed` on `data:<key>`, no values). REST/GraphQL stays canonical.
- Pages read server data only through `useDataQuery(resource, fetcher)` (`web/src/realtime/dataQuery.ts`, TanStack Query). `web/src/realtime/dataBridge.ts` subscribes to the `data:` topics that have a mounted query and invalidates them; it also invalidates all on resync and clears the cache on logout.
- Server: domain code calls `operation_events.note_resource_changed("<key>")` after the mutation commits. Keys are registered in `api/app/realtime/resources.py` and mirrored in `web/src/realtime/resourceKeys.ts` (`tests/test_realtime_resources.py` checks they match).
- Pages must not subscribe, poll, or add reload buttons. REST polling exists only inside `useDataQuery` while the socket is down.
- Job and build progress keep using `followResource` and the existing job/corpus events. Do not convert progress streams to refetches.
- Existing `clearGraphQLReadCache()` already runs on every resource event, so GraphQL reads are covered; do not add a second cache.

## Done (PR 1)

- Protocol/registry/observer/authorization for `resource.changed`; emitters for `users` and `roles` in `auth.py`.
- Frontend bridge, composable, plugin registration in `main.ts`, `UsersView` migrated (its Refresh button and `users.refresh` strings removed).
- Tests: `tests/test_realtime_resources.py`, `web/tests/frontend/realtime-data-bridge.test.ts`, `web/tests/frontend/users-view-realtime.test.ts`.

## Done in follow-up PRs

- **#360** Research (`ResearchView`) follows `job:<id>` per live run; `useCapturePolling` became `useCaptureFollow` on the capture job topic. `CorpusModelActivity.vue` is only a local elapsed-seconds clock (no HTTP), like `OperationsPanel.vue`.
- **#362** Pipeline Studio: keys `pipelines` (definitions, assignments) and `pipeline_runs` (traces, stages, restore, clear), `usePipelineStudioData`, Refresh removed.
- **#364** Keys `vector_collections` (decorated `ChromaStore` mutations), `metadata_exemplars` (exemplar projection writers), `response_library` (cache writes, grades, deletes, retention). Migrated: Vector Stores, Metadata Memory, Response Library, System Data Saved responses and Metadata examples, Storage overview. Ratchet: `web/tests/frontend/realtime-polling-ratchet.test.ts` forbids new `setInterval` and new manual refresh controls; shrink its allow-lists as pages migrate.

Intentionally left: the System Data Databases and Advanced inspectors (raw tables of arbitrary SQLite stores, no write hook) keep **Refresh**; backups are a command with no listing.

## Done after #362 and #364 merged

- **Reader pages (Search, Record, Compare):** key `corpus_records`, noted from `PdfCorpusRepository.update_record`, `publish()`, and the Chroma record-content mutations (`finish_sync`, `delete_store`, `update_existing`, `patch_existing`, record/work deletes; not per-batch `upsert_many`). `useNewerData()` + `NewerDataBanner` show "Newer data is available / Load newer"; content is never replaced silently. Administrators only.
- **Pipeline benchmarks:** key `pipeline_benchmarks` (cases, results, clear, restore, retention). `PipelineBenchmarkWorkspace` reads cases and collections through `useDataQuery`.
- The Storage overview pipeline count already uses `useDataQuery("pipelines", ...)`.

## Remaining work

1. **Widen to non-administrators** (optional): allow the `page.faq` capability for `response_library`, `page.vector` for `vector_collections`, and researcher access to `corpus_records` (so reader banners reach researchers). `broker.audience_allows` requires an owner for non-administrators, so this needs a capability-only audience flag that cannot affect existing audiences (rag generation uses `capability="rag.jobs.own"` with an owner that can be None). Until then non-administrators refetch on window focus only. Researchers must still never receive record text; the key carries none.
2. **Release note:** add `docs/notes/<version>.md` when cutting a release (summarise the resources, the reader banner and the removed Refresh buttons), then delete this file; the lasting contract lives in [REALTIME.md](REALTIME.md).

## Gotchas

- `operation_events.Drained` gained a `resources` field; `tests/test_realtime_live_hints.py` pins its shape.
- Widening a resource beyond administrators needs `DataResource.allows` and `Audience` (owner/capability) changes, not just a new key; match the REST route's permission.
- `event_id` is per API process. A multi-worker deployment would need a shared broker; out of scope.
- Run backend tests with `PYTHONPATH=api` and the venv at `DerridAI-Claude/.venv`; `web/node_modules` must be a hard-linked copy (`cp -al`), not a symlink.
- Not run for any of the realtime PRs: Playwright e2e, Storybook build, Docker build.
- Tests that mount a migrated page need `VueQueryPlugin` with the shared `queryClient` (see `system-data-pipelines.test.ts`); clear it in `beforeEach` and set `retry: false` when asserting error states.
- A locally hard-linked `node_modules` may lack `fake-indexeddb`, which fails `derridai-sdk-local-index.test.ts` only.
