<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Realtime operations plane

`WS /api/ws/events` is one authenticated WebSocket per browser session. It tells the browser **that** background work changed so the page can update immediately instead of polling. It is a notification channel, not a store:

- canonical state stays in the corpus/build files, SQLite job snapshots/history, and canonical Record/FieldAssertion/evidence structures;
- commands (create, cancel, pause, resume, review, publish) stay on REST;
- losing the socket never loses or stops a job, and every page can resynchronize from REST/GraphQL.

GraphQL is the read façade for scholarly data ([GRAPHQL.md](GRAPHQL.md)); it has no subscriptions. The socket is plain JSON over native WebSockets (no Socket.IO, no extra service). WebSockets were chosen over Server-Sent Events because one connection must carry many dynamically (un)subscribed topics with client acknowledgements and heartbeats, and because future interactive model/tool control needs a client→server channel on the same authenticated connection.

## Server components

| Module                      | Role                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `realtime/protocol.py`      | Envelope, event taxonomy, client messages, topic grammar, close codes, ephemeral/coalescable classification.                                                 |
| `realtime/auth.py`          | Session-cookie authentication and origin check (HTTP middleware does not run for WebSockets).                                                                |
| `realtime/subscriptions.py` | Per-topic authorization, including `ACTIVITY_KINDS` for `activity:<kind>`.                                                                                   |
| `realtime/broker.py`        | Stamps `event_id`/`revision`, keeps a bounded replay ring (skipping ephemeral events), fans out to authorized subscribers.                                   |
| `realtime/coalescing.py`    | Bounded per-connection queue; drops droppable (coalescable or ephemeral) events first, then overflow → resync.                                               |
| `realtime/events.py`        | The observer: samples shared job state and domain change notes and publishes normalized events.                                                              |
| `realtime/router.py`        | The socket endpoint: handshake, reader/writer/heartbeat tasks, limits, logging.                                                                              |
| `job_state.py`              | `job_realtime_summary` / `PersistentJobStateMixin.realtime_job_summaries`: the one bounded, text-free view of live job state every manager shares.           |
| `operation_events.py`       | Transport-neutral notes from domain code (`save_build`, model-call start/end, per-record metadata progress, generation deltas, activity). No socket imports. |

Job managers never call the socket. The observer thread reads `realtime_job_summaries()` from the LLM, RAG, LLM-tool (languages, work metadata, grading) and upsert managers plus corpus-build/model-activity/per-record/generation/activity notes at most `REALTIME_PROGRESS_MAX_HZ` times per second, diffs against what it last published and emits events. A failing manager, a publish error, or a slow browser therefore cannot stall, fail or corrupt a job, and SQLite checkpointing is untouched.

## Connection lifecycle

1. The browser connects after authentication (`bootstrapRuntime` → `startRealtime`).
2. The server authenticates the `derridai_session` cookie (identity never comes from the client), checks `Origin` (same host or `REALTIME_ALLOWED_ORIGINS`), and sends `connection.ready` with `protocol_version`, `connection_id`, the current `last_event_id`, `heartbeat_seconds` and `idle_timeout_seconds`.
3. The client subscribes to its topics, passing `last_event_id` when resuming.
4. The server re-queues missed events from its ring buffer in `event_id` order ahead of anything newer, or sends `connection.resync_required`.
5. Every `REALTIME_HEARTBEAT_SECONDS` the server re-validates the session (closing 4401 if it expired, 4403 with `auth.permissions_changed` if the role changed) and sends `connection.heartbeat`. The client pings every ¾ heartbeat; a socket silent for `REALTIME_IDLE_TIMEOUT_SECONDS` is closed.
6. Logout, session expiry and account switches pause the runtime, which closes the socket; nothing reconnects until the next login. Nuke/reset invalidates sessions, which the next heartbeat turns into a 4401 close.

### Close codes

| Code | Meaning                                                                        | Client behaviour                                                                                                                                                                        |
| ---- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4400 | Malformed frame, unknown message type, invalid topic list                      | Reconnect with backoff                                                                                                                                                                  |
| 4401 | No valid session / session expired                                             | Stop reconnecting and poll; confirm with `GET /api/auth/me` and run the auth-expiry flow only if REST also reports 401 (a proxy that drops cookies on upgrades must not log anyone out) |
| 4403 | Forbidden: realtime disabled, origin refused, no topic available, role changed | Fallback polling; slow retry (or refresh auth)                                                                                                                                          |
| 4404 | Resource not found (used in subscription rejections)                           | —                                                                                                                                                                                       |
| 4408 | Policy: oversized message, rate limit, too many topics, idle timeout           | Reconnect with backoff                                                                                                                                                                  |
| 1011 | Unexpected internal failure                                                    | Reconnect with backoff                                                                                                                                                                  |

## Protocol (version 1)

Every resource event uses one envelope:

```json
{
  "type": "job.progress",
  "event_id": 9182,
  "resource_type": "job",
  "resource_id": "job-123",
  "revision": 47,
  "timestamp": "2026-09-27T09:20:13Z",
  "payload": {
    "job": {
      "id": "job-123",
      "status": "running",
      "completed": 12,
      "total": 40
    }
  }
}
```

Client messages: `subscribe {topics, last_event_id?}`, `unsubscribe {topics}`, `resync {last_event_id?}`, `ping`. Future control messages (`generation.cancel`, `tool.approve`, `tool.reject`, `tool.input`, `generation.guidance`) will be added as new `type`s on the same connection when a feature needs them; today cancel/pause/resume stay on REST.

Control frames: `connection.ready`, `connection.resync_required`, `connection.heartbeat`, `pong`, `subscription.updated {topics, rejected[]}`, `auth.permissions_changed`.

Resource events:

| Type                                                                                                                                                                                                                   | Topic(s)                             | Payload                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------ |
| `job.snapshot`, `job.created`, `job.queued`, `job.started`, `job.stage_changed`, `job.progress`, `job.warning`, `job.needs_attention`, `job.cancelling`, `job.cancelled`, `job.completed`, `job.failed`, `job.removed` | `jobs`, `job:<id>`                   | `job` summary (+ `previous_status`)                                            |
| `corpus.build_changed`, `corpus.stage_changed`, `corpus.progress`, `corpus.metadata_progress`, `corpus.review_queue_changed`                                                                                           | `corpus-builds`, `corpus-build:<id>` | `build` summary (status, stage, counts)                                        |
| `llm.started`, `llm.progress`, `llm.completed`                                                                                                                                                                         | `corpus-builds`, `corpus-build:<id>` | `activity`: calls in flight, task, provider, model                             |
| `llm.token` (ephemeral)                                                                                                                                                                                                | `job:<id>` only                      | `generation`: `seq`, `delta` (≤4096 chars), `gap`, `final`                     |
| `corpus.llm_progress` (ephemeral)                                                                                                                                                                                      | `corpus-build:<id>` only             | `generation`: `call_id`, `seq`, `chars`, `gap`, `final`; **no model text**     |
| `corpus.record_started`, `corpus.field_checked`, `corpus.record_completed` (ephemeral)                                                                                                                                 | `corpus-build:<id>` only             | `metadata`: `record_id`, `family?`, `state?`, `field_ids?`, `precedents_used?` |
| `activity.changed`                                                                                                                                                                                                     | `activity:<kind>` only               | `activity`: a bounded, kind-specific public summary                            |
| `resource.changed`                                                                                                                                                                                                     |

Job summaries contain only bounded, text-free fields (status, stage, a truncated stage detail, counts, timestamps, warning count, `has_error`, pending-result count). They never contain requests, prompts, results, evidence, answers, diagnostics, API keys or owners. Clients read details through the owner-scoped REST endpoints; for example upsert receipts are fetched from `GET /api/jobs/{id}` when the completed count rises.

`corpus.metadata_progress` carries the build's task counters (total, completed, failed, skipped, running, queued) and review count. `corpus.record_started`/`corpus.field_checked`/`corpus.record_completed` carry per-record progress instead — identifiers, family, terminal state and precedent counts, never field values or evidence — sent only on the build's own topic (never the global `corpus-builds` feed) because only a view already watching that build can use them. The server emits `corpus.record_completed` only after the enriched Record has been durably merged and saved. The Corpus Builder refreshes the finished queue row and, when that Record is open, its full reviewer projection so metadata and evidence appear without a page refresh.

`corpus.llm_progress` is deliberately text-free. It announces that one build-local model call advanced, with a call ID, sequence counter, retained-character count, gap flag, and final flag. The administrator-only **Model activity** inspector uses that notification to refresh `GET /api/pdf/corpus-builds/{build_id}/llm-live-output` only while the inspector is open. Rendered prompts and completed raw/validated responses are read separately from the administrator-only `llm-trace` endpoint. Prompts, source-derived model text, response values, credentials, and hidden reviewer data are never placed on the WebSocket plane.

`llm.token` streams Research's draft answer while a run is generating (`rag.chat_complete(on_delta=)`), on `job:<id>` only, to the job's owner or an administrator (`rag.jobs.own`). Each event carries a monotonic `seq`, a bounded `delta`, a `gap` flag (text was dropped upstream: the client must stop appending and wait) and a `final` flag. The frontend's `useResearchDraft` composable renders this as a clearly labelled, citations-not-yet-bound draft pane and always replaces it with the authoritative REST answer once the job completes; token text is never persisted event-by-event in SQLite.

`activity.changed` reports background work that is not a tracked job (currently only the Gutenberg offline-collection download/catalogue on `activity:gutenberg`; see `ACTIVITY_KINDS` in `realtime/subscriptions.py`), replacing that view's fixed-interval status poll.

`resource.changed` is the one event for page data that is not a job or build: it says that one registered data resource (`DATA_RESOURCES` in `realtime/resources.py`, mirrored in `web/src/realtime/resourceKeys.ts`) is stale, on `data:<resource>` only. It carries the resource key and nothing else (no ids or values), is coalescable, and is replayed like other non-ephemeral events. Domain code calls `operation_events.note_resource_changed("<key>")` after the mutation commits; the observer publishes at most one event per key per tick. The frontend follows these through one path: pages read server data with `useDataQuery(resource, fetcher)` (TanStack Query), and `realtime/dataBridge.ts` subscribes to exactly the `data:` topics that have a mounted query, invalidates that resource's queries on each event, invalidates every `data` query on resync, and clears the cache when the client stops (logout or account switch). Pages do not subscribe, poll, or add reload buttons; REST polling happens only inside `useDataQuery` while the socket is unavailable. To add a resource: register the key in both lists, emit the note from the store that owns the mutation, and read it with `useDataQuery`.

### Ephemeral events

`llm.token`, `corpus.llm_progress`, `corpus.record_started`, `corpus.field_checked` and `corpus.record_completed` are **ephemeral** (`EPHEMERAL_EVENT_TYPES` in `protocol.py`): each is a discrete fact, not a latest-value snapshot, so it is never replayed after a reconnect and is the first kind of event dropped under backpressure. A client must treat a gap in these events as "reconcile from REST/GraphQL," not as data loss to recover: Research waits for the final REST answer; per-record progress is recovered by re-reading counts/rows, never by reconstructing missed events.

### Topics and authorization

| Topic                                | Who may subscribe                                                                                                          |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `jobs`                               | Administrators (all jobs); roles with `rag.jobs.own` or `rag.run` (their own Research jobs only)                           |
| `job:<id>`                           | Administrators; a non-administrator only for their own Research (RAG) job. Anything else is 4404.                          |
| `corpus-builds`, `corpus-build:<id>` | Administrators only (Corpus Builder is an administrator workspace)                                                         |
| `activity:<kind>`                    | Administrators only. `<kind>` must be one of `ACTIVITY_KINDS` (currently `gutenberg`); anything else is 4404.              |
| `data:<resource>`                    | Per the resource registry; `users` and `roles` are administrators only (their REST routes are too). Unknown keys are 4404. |

Each topic is authorized independently at subscribe time; every event is also filtered by its audience at delivery (owner, administrator-only, capability). Another user's job is indistinguishable from a missing one. A role with no available topic is refused with 4403.

### Ordering, revisions and resync

- `event_id` is global and monotonic within one API process; `revision` is monotonic per `(resource_type, resource_id)`. These are **delivery-order counters**, not canonical revisions: the job revision domain is independent of REST, and the `corpus_build` domain is independent of Record revisions. Convergence is checked by status/counts: after `job.completed` the REST snapshot reports the same status.
- The client ignores duplicate `event_id`s and stale lower revisions.
- The replay ring holds the last `REALTIME_REPLAY_EVENTS` events, excluding ephemeral ones. A resume inside the ring is replayed (filtered by the reconnecting user's authorization); otherwise the server sends `connection.resync_required` and the client reloads from REST. If `connection.ready` reports a lower `last_event_id` than the client has seen, the server restarted and the client resyncs.
- The first connection of a session always performs one REST resync, closing the gap between the bootstrap listing and the socket becoming ready.

### Backpressure and coalescing

- The observer bounds each resource to `REALTIME_PROGRESS_MAX_HZ` samples per second; stage, warning and terminal transitions are emitted on the next sample (≤ 125 ms by default).
- Each connection has a bounded queue (`REALTIME_MAX_QUEUE_EVENTS`). A newer coalescable event (`job.progress`, `llm.progress`, `corpus.progress`, `corpus.metadata_progress`, `corpus.review_queue_changed`, `activity.changed`) replaces its pending predecessor and moves to the tail, preserving `event_id` order.
- When full, droppable events (coalescable or ephemeral) are discarded first, oldest first. If only essential events remain, the queue is discarded and `connection.resync_required` (`reason: "backpressure"`) is sent: terminal and warning events are never silently lost.
- Client messages are limited to `REALTIME_MAX_CLIENT_MESSAGE_BYTES`, 10/s (burst 30), and 64 topics per connection.

### Fallback polling

The client never makes the product unusable when a proxy blocks WebSockets:

| Socket state                                           | Global job feed                  | A resource a view is watching (build, job dialog, translation, Gutenberg activity) |
| ------------------------------------------------------ | -------------------------------- | ---------------------------------------------------------------------------------- |
| Connected                                              | No polling; events drive updates | No polling (Corpus Builder reconciles every 15 s for model-load state)             |
| Briefly reconnecting                                   | Wait                             | Poll every 5 s                                                                     |
| Unavailable after 3 failed attempts, or refused (4403) | Poll every 25 s                  | Poll every 5 s                                                                     |
| Not started                                            | Former 4 s polling               | Former cadence                                                                     |

Reconnects use exponential backoff with jitter (1 s base, 30 s cap), reset after 10 s of stable connection. On recovery the client performs one authoritative REST resync and stops fallback polling. The Operations panel shows a quiet connection line (not a live region) so transient reconnects never interrupt anyone.

## Frontend

- `web/src/realtime/client.ts` — the only place that opens a socket. Subscription registry, sequencing, duplicate/stale suppression, heartbeat, backoff, fallback flag, auth hooks.
- `web/src/realtime/follow.ts` — `followResource()` for a view watching one resource: event-driven throttled REST refresh, fallback timer while the socket is down. Used for corpus builds, and for `activity:gutenberg` in `CorpusLibrarySearch.vue` (replacing a 2 s status poll).
- `web/src/domain/jobsWorkspace.ts` — REST snapshots and job events both flow through `reconcileJobs`, so toasts, desktop notifications (once per job), upsert receipts, the Operations panel and Research progress update identically whichever transport delivered the change. Terminal events trigger one REST snapshot for results and errors.
- `web/src/features/research/useResearchDraft.ts` — follows `llm.token` on `job:<id>` for one Research job at a time, appending deltas in sequence order and stopping on a reported gap; `ResearchView.vue` clears it as soon as the job has an authoritative result.
- `web/src/features/corpus-builder/composables/useCorpusBuildLifecycleController.ts` — `startPolling()` follows `corpus-build:<id>` for build-level refresh and separately subscribes to `corpus.record_completed` to refresh one review-queue row without a full page reload.

Views never call `new WebSocket()`; they subscribe through the client or `followResource`.

## Page and feature audit

| Surface                                | GraphQL                                                                                                                                                                     | WebSocket                                                                                                                                                                                                                                         |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dashboard `/`                          | Deferred: no duplicated REST composition to remove yet                                                                                                                      | **Adopted** via the shared job feed (Operations card, corpus-build card, Research activity)                                                                                                                                                       |
| Records `/records`                     | Deferred: needs paginated `records` root with researcher-safe projection                                                                                                    | **Adopted** indirectly: LLM review/auto-improve/upsert completion reconciles through the job feed                                                                                                                                                 |
| Record `/record`                       | **Adopted**: cELF model and Record traceability graph                                                                                                                       | Adopted indirectly (job feed); collaborative review not requested                                                                                                                                                                                 |
| Relationship browser `/relationships`  | **Adopted**: `record_graph`/`celf_model`, plus `vector_store.record(chroma_id)` (`StoredRecordTrace`) for a stored-record trace                                             | Not useful yet: no provenance-change events exist to invalidate on                                                                                                                                                                                |
| Works `/works`                         | Deferred (candidate for `works` root)                                                                                                                                       | Adopted indirectly: upsert completion refreshes stores via the job feed                                                                                                                                                                           |
| Search `/search`                       | Deferred: search stays REST; hydration via GraphQL later                                                                                                                    | Not useful: ordinary searches are short                                                                                                                                                                                                           |
| Annotations `/annotations`             | Deferred                                                                                                                                                                    | Not useful until collaborative annotation is requested                                                                                                                                                                                            |
| Corpus Builder `/pdf`                  | **Adopted** for the review queue and Records (`corpus_build.review_queue`/`rows`/`record`/`records`/`metadata_facets`); build composition (manifest, validation) stays REST | **Adopted**: `corpus-build:<id>` events replace 1.4 s polling; metadata/task progress, per-record completion, review counts, stage, model activity, and text-free model-call progress. Opt-in live model text remains an authenticated REST read. |
| Compare `/compare`                     | Deferred (good candidate for multi-Record reads)                                                                                                                            | Not useful                                                                                                                                                                                                                                        |
| Vector stores `/databases`             | **Adopted**: `vector_store.works`/`records` (`VectorStoreBrowse`) replace the REST works+records pair for this view                                                         | **Adopted** via upsert job events; counts/stores refresh on completion                                                                                                                                                                            |
| Research `/rag`                        | Backend root (`research_run`) exists; the frontend workspace still reads jobs over REST                                                                                     | **Adopted**: queued/running/stage/warning/terminal via the job feed, plus a streamed draft answer via `llm.token`                                                                                                                                 |
| Response Library `/faq`                | Deferred (response → claims → support)                                                                                                                                      | Adopted indirectly: Research completion reconciles the job feed; no historical payloads over the socket                                                                                                                                           |
| Response cache `/response-cache`       | Not useful: operational cache administration                                                                                                                                | Not useful                                                                                                                                                                                                                                        |
| System Data `/system-data`             | Backend root (`metadata_exemplars`) exists; the frontend view still reads REST. Generic database consoles stay REST.                                                        | Deferred: projection rebuilds are not background jobs yet                                                                                                                                                                                         |
| Providers `/providers`                 | Not useful                                                                                                                                                                  | Deferred: warmup is not a tracked job; no API keys may ever be sent                                                                                                                                                                               |
| Metadata schemas `/schemas`            | Not useful yet                                                                                                                                                              | Not useful: no long-running schema actions are jobs                                                                                                                                                                                               |
| Metadata memory `/metadata-memory`     | Deferred (`metadata_exemplar` root)                                                                                                                                         | Deferred: exemplar reprojection is not a tracked job                                                                                                                                                                                              |
| Help `/help`                           | None                                                                                                                                                                        | None                                                                                                                                                                                                                                              |
| Settings `/settings`                   | Not useful                                                                                                                                                                  | Adopted indirectly (active jobs via the job feed); preferences are not realtime                                                                                                                                                                   |
| Users `/users`, Roles `/roles`         | Not useful                                                                                                                                                                  | Role changes close the socket (4403 + `auth.permissions_changed`) on the next heartbeat                                                                                                                                                           |
| Languages `/languages`                 | Not useful                                                                                                                                                                  | **Adopted**: translation and content-policy jobs follow `job:<id>` instead of 1.2–2 s polling                                                                                                                                                     |
| Authentication                         | None                                                                                                                                                                        | **Adopted**: connect after login, close on logout/expiry, 4401 dispatches the auth-expiry flow, no reconnect loop                                                                                                                                 |
| Operations panel (global)              | None (history stays REST)                                                                                                                                                   | **Adopted**: central consumer; live-region policy, undo, desktop notifications and relative-time clock unchanged                                                                                                                                  |
| LLM review workspace/dialog            | Deferred                                                                                                                                                                    | **Adopted**: the review dialog follows `job:<id>` instead of 4 s polling; decisions stay REST                                                                                                                                                     |
| Corpus model activity                  | None                                                                                                                                                                        | **Adopted**: `llm.*` events refresh the build; the per-second elapsed counter stays a local clock                                                                                                                                                 |
| Source import / Gutenberg / Wikisource | Not useful                                                                                                                                                                  | **Adopted**: the offline Gutenberg collection's status follows `activity:gutenberg` instead of a 2 s poll; Wikisource search stays request/response                                                                                               |
| Backup / Restore / Nuke                | None                                                                                                                                                                        | Deferred until backup/restore become jobs; nuke invalidates sessions, which closes sockets on the next heartbeat                                                                                                                                  |

Timers that only drive relative time, elapsed counters, announcement delays, debounce, animation or undo windows are intentionally unchanged.

## Adding an event

1. Emit a transport-neutral note from domain code (`operation_events.py`) or extend `job_realtime_summary`; never import realtime code into a manager. Discrete per-record facts belong in a bounded ring (`note_record_metadata`); latest-value summaries replace their previous entry (`note_corpus_build`, `note_activity`).
2. Map it to a public type in `realtime/events.py`, add the type to `protocol.py`'s `RESOURCE_EVENT_TYPES` (and to `COALESCABLE_EVENT_TYPES` only if a newer instance fully supersedes an older one, or `EPHEMERAL_EVENT_TYPES` if it is a discrete fact that must never be replayed), and set an `Audience` that matches the REST authorization for the same data.
3. Keep payloads bounded and free of source text, prompts, model output, secrets and hidden reviewer values; send identifiers and let clients read details over REST/GraphQL.
4. Mirror the type in `web/src/realtime/protocol.ts` (including `topicsForEvent`), bump `PROTOCOL_VERSION` only for incompatible changes (clients ignore unknown event types), and add backend and frontend tests.

## Deployment

nginx proxies `/api/ws/` with `proxy_http_version 1.1`, `Upgrade`/`Connection: upgrade` headers and a 120 s read timeout (longer than the heartbeat). The Vite dev server proxies `/api/ws` with `ws: true`. No additional container is required. Connection metadata (connection id, user id, role, subscription count, queue depth, coalesced/dropped counts, close code) is logged; cookies, payloads, source text, prompts and secrets are not.

Configuration: `REALTIME_ENABLED`, `REALTIME_MAX_CLIENT_MESSAGE_BYTES`, `REALTIME_MAX_QUEUE_EVENTS`, `REALTIME_REPLAY_EVENTS`, `REALTIME_PROGRESS_MAX_HZ`, `REALTIME_HEARTBEAT_SECONDS`, `REALTIME_IDLE_TIMEOUT_SECONDS`, `REALTIME_ALLOWED_ORIGINS` (see `.env.example`).

The in-memory broker assumes the single API process DerridAI already requires for job execution.
