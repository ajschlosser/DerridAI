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

1. **System Data / Settings pages** (`components/system-data/*`, Vector Stores, Metadata Memory, Operations panel): add keys (for example `vector_collections`, `metadata_exemplars`, `response_library`, `pipelines`, `backups`), emit from the owning stores, migrate views, remove their refresh buttons and now-unused locale keys in `enUsDefaults.json`, `api/app/locales/en_us.py` and `fr_ca.py`.
2. ~~Remove the remaining HTTP pollers~~ Done (PR 2): `ResearchView.vue` follows `job:<id>` per live run via `followResource`; `useCapturePolling` became `useCaptureFollow` on the capture job topic (captures already emit job events, so no `captures` key was needed); `CorpusModelActivity.vue` only ticks a local elapsed-seconds clock (no HTTP), so the ratchet must allow it.
3. **Reader-facing pages** (Search, Record, Compare): do not replace content under a reader. Show a "newer data available" banner driven by the same invalidation (decision recorded with the user: banner, not silent replace; confirm if unsure).
4. **Ratchet**: a Vitest check that forbids new `setInterval`/`setTimeout` polling and manual `refresh` handlers outside `realtime/` (model on the hex-colour ratchet).
5. **Docs**: update `docs/USER_GUIDE.md` where it mentions refreshing; add a release note when cutting a release.

## Gotchas

- `operation_events.Drained` gained a `resources` field; `tests/test_realtime_live_hints.py` pins its shape.
- Widening a resource beyond administrators needs `DataResource.allows` and `Audience` (owner/capability) changes, not just a new key; match the REST route's permission.
- `event_id` is per API process. A multi-worker deployment would need a shared broker; out of scope.
- Run backend tests with `PYTHONPATH=api` and the venv at `DerridAI-Claude/.venv`; `web/node_modules` must be a hard-linked copy (`cp -al`), not a symlink.
- Not run for PR 1: Playwright e2e, Storybook build, Docker build.
