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

## Remaining work (separate PRs, each based on master)

1. **System Data / Settings pages**: done for Vector Stores (`vector_collections`, emitted by decorated `ChromaStore` mutations), Metadata Memory and System Data Metadata examples (`metadata_exemplars`), Response Library and System Data Saved responses (`response_library`, also emitted by retention deletes), and the Storage overview. Intentionally left: the Databases and Advanced inspectors (raw tables of arbitrary SQLite stores, no write hook) keep **Refresh**; backups are a command with no listing. Follow-ups: widen `response_library` to the `page.faq` capability (needs a capability-only audience in `broker.audience_allows`, which today requires an owner for non-admins), and switch the Overview pipeline count to `useDataQuery("pipelines")` once the Pipeline Studio change is on master.
2. **Remove the remaining HTTP pollers**: `ResearchView.vue` (3s `setTimeout` loop; move to `job:<id>` events), `composables/useCapturePolling.ts` (captures: add a `captures` key), `CorpusModelActivity.vue` (`setInterval`; confirm whether it is only a clock like `OperationsPanel.vue`).
3. **Reader-facing pages** (Search, Record, Compare): do not replace content under a reader. Show a "newer data available" banner driven by the same invalidation (decision recorded with the user: banner, not silent replace; confirm if unsure).
4. ~~Ratchet~~ Done: `web/tests/frontend/realtime-polling-ratchet.test.ts` forbids new `setInterval` and new manual refresh controls; shrink its allow-lists as pages migrate.
5. **Docs**: update `docs/USER_GUIDE.md` where it mentions refreshing; add a release note when cutting a release.

## Gotchas

- `operation_events.Drained` gained a `resources` field; `tests/test_realtime_live_hints.py` pins its shape.
- Widening a resource beyond administrators needs `DataResource.allows` and `Audience` (owner/capability) changes, not just a new key; match the REST route's permission.
- `event_id` is per API process. A multi-worker deployment would need a shared broker; out of scope.
- Run backend tests with `PYTHONPATH=api` and the venv at `DerridAI-Claude/.venv`; `web/node_modules` must be a hard-linked copy (`cp -al`), not a symlink.
- Not run for PR 1: Playwright e2e, Storybook build, Docker build.
