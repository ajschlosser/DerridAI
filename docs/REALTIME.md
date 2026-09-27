<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Realtime operations plane

`WS /api/ws/events` is one authenticated WebSocket per browser session. It tells the browser **that** background work changed so the page can update immediately instead of polling. It is a notification channel, not a store:

- canonical state stays in the corpus/build files, SQLite job snapshots/history, and canonical Record/FieldAssertion/evidence structures;
- commands (create, cancel, pause, resume, review, publish) stay on REST;
- losing the socket never loses or stops a job, and every page can resynchronize from REST/GraphQL.

GraphQL is the read façade for scholarly data ([GRAPHQL.md](GRAPHQL.md)); it has no subscriptions. The socket is plain JSON over native WebSockets (no Socket.IO, no extra service). WebSockets were chosen over Server-Sent Events because one connection must carry many dynamically (un)subscribed topics with client acknowledgements and heartbeats, and because future interactive model/tool control needs a client→server channel on the same authenticated connection.

## Server components

| Module                      | Role                                                                                                                                               |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `realtime/protocol.py`      | Envelope, event taxonomy, client messages, topic grammar, close codes.                                                                             |
| `realtime/auth.py`          | Session-cookie authentication and origin check (HTTP middleware does not run for WebSockets).                                                      |
| `realtime/subscriptions.py` | Per-topic authorization.                                                                                                                           |
| `realtime/broker.py`        | Stamps `event_id`/`revision`, keeps a bounded replay ring, fans out to authorized subscribers.                                                     |
| `realtime/coalescing.py`    | Bounded per-connection queue with coalescing and overflow → resync.                                                                                |
| `realtime/events.py`        | The observer: samples shared job state and domain change notes and publishes normalized events.                                                    |
| `realtime/router.py`        | The socket endpoint: handshake, reader/writer/heartbeat tasks, limits, logging.                                                                    |
| `job_state.py`              | `job_realtime_summary` / `PersistentJobStateMixin.realtime_job_summaries`: the one bounded, text-free view of live job state every manager shares. |
| `operation_events.py`       | Transport-neutral notes from domain code (`save_build`, model-call start/end). No socket imports.                                                  |

Job managers never call the socket. The observer thread reads `realtime_job_summaries()` from the LLM, RAG, LLM-tool (languages, work metadata, grading) and upsert managers plus corpus-build/model-activity notes at most `REALTIME_PROGRESS_MAX_HZ` times per second, diffs against what it last published and emits events. A failing manager, a publish error, or a slow browser therefore cannot stall, fail or corrupt a job, and SQLite checkpointing is untouched.

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

| Type                                                                                                                                                                                                                   | Topic(s)                             | Payload                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------- |
| `job.snapshot`, `job.created`, `job.queued`, `job.started`, `job.stage_changed`, `job.progress`, `job.warning`, `job.needs_attention`, `job.cancelling`, `job.cancelled`, `job.completed`, `job.failed`, `job.removed` | `jobs`, `job:<id>`                   | `job` summary (+ `previous_status`)                |
| `corpus.build_changed`, `corpus.stage_changed`, `corpus.progress`, `corpus.metadata_progress`, `corpus.review_queue_changed`                                                                                           | `corpus-builds`, `corpus-build:<id>` | `build` summary (status, stage, counts)            |
| `llm.started`, `llm.progress`, `llm.completed`                                                                                                                                                                         | `corpus-builds`, `corpus-build:<id>` | `activity`: calls in flight, task, provider, model |

Job summaries contain only bounded, text-free fields (status, stage, a truncated stage detail, counts, timestamps, warning count, `has_error`, pending-result count). They never contain requests, prompts, results, evidence, answers, diagnostics, API keys or owners. Clients read details through the owner-scoped REST endpoints; for example upsert receipts are fetched from `GET /api/jobs/{id}` when the completed count rises.

`corpus.metadata_progress` carries the build's task counters (total, completed, failed, skipped, running, queued) and review count. Per-record/per-field detail (`record_id`, `field_id`, precedents used) and `corpus.record_started`/`corpus.record_completed`/`corpus.field_checked` are deferred: the enrichment executor does not yet expose that state outside its worker, and adding it must not put field values or evidence text into events.

`llm.token` is **reserved but not emitted**: Research generation is currently a single blocking provider call per stage, so there is no token stream to forward. When streaming lands it must be sequence-numbered, bounded, sent only on `job:<id>` to clients authorised to read that text, and never persisted token-by-token; after a reconnect the client fetches the final response over REST instead of reconstructing missed tokens.

### Topics and authorization

| Topic                                | Who may subscribe                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `jobs`                               | Administrators (all jobs); roles with `rag.jobs.own` or `rag.run` (their own Research jobs only)  |
| `job:<id>`                           | Administrators; a non-administrator only for their own Research (RAG) job. Anything else is 4404. |
| `corpus-builds`, `corpus-build:<id>` | Administrators only (Corpus Builder is an administrator workspace)                                |

Each topic is authorized independently at subscribe time; every event is also filtered by its audience at delivery (owner, administrator-only, capability). Another user's job is indistinguishable from a missing one. A role with no available topic is refused with 4403.

### Ordering, revisions and resync

- `event_id` is global and monotonic within one API process; `revision` is monotonic per `(resource_type, resource_id)`. These are **delivery-order counters**, not canonical revisions: the job revision domain is independent of REST, and the `corpus_build` domain is independent of Record revisions. Convergence is checked by status/counts: after `job.completed` the REST snapshot reports the same status.
- The client ignores duplicate `event_id`s and stale lower revisions.
- The replay ring holds the last `REALTIME_REPLAY_EVENTS` events. A resume inside the ring is replayed (filtered by the reconnecting user's authorization); otherwise the server sends `connection.resync_required` and the client reloads from REST. If `connection.ready` reports a lower `last_event_id` than the client has seen, the server restarted and the client resyncs.
- The first connection of a session always performs one REST resync, closing the gap between the bootstrap listing and the socket becoming ready.

### Backpressure and coalescing

- The observer bounds each resource to `REALTIME_PROGRESS_MAX_HZ` samples per second; stage, warning and terminal transitions are emitted on the next sample (≤ 125 ms by default).
- Each connection has a bounded queue (`REALTIME_MAX_QUEUE_EVENTS`). A newer coalescable event (`job.progress`, `llm.progress`, `corpus.progress`, `corpus.metadata_progress`, `corpus.review_queue_changed`) replaces its pending predecessor and moves to the tail, preserving `event_id` order.
- When full, the oldest coalescable event is dropped first. If only essential events remain, the queue is discarded and `connection.resync_required` (`reason: "backpressure"`) is sent: terminal and warning events are never silently lost.
- Client messages are limited to `REALTIME_MAX_CLIENT_MESSAGE_BYTES`, 10/s (burst 30), and 64 topics per connection.

### Fallback polling

The client never makes the product unusable when a proxy blocks WebSockets:

| Socket state                                           | Global job feed                  | A resource a view is watching (build, job dialog, translation)         |
| ------------------------------------------------------ | -------------------------------- | ---------------------------------------------------------------------- |
| Connected                                              | No polling; events drive updates | No polling (Corpus Builder reconciles every 15 s for model-load state) |
| Briefly reconnecting                                   | Wait                             | Poll every 5 s                                                         |
| Unavailable after 3 failed attempts, or refused (4403) | Poll every 25 s                  | Poll every 5 s                                                         |
| Not started                                            | Former 4 s polling               | Former cadence                                                         |

Reconnects use exponential backoff with jitter (1 s base, 30 s cap), reset after 10 s of stable connection. On recovery the client performs one authoritative REST resync and stops fallback polling. The Operations panel shows a quiet connection line (not a live region) so transient reconnects never interrupt anyone.

## Frontend

- `web/src/realtime/client.ts` — the only place that opens a socket. Subscription registry, sequencing, duplicate/stale suppression, heartbeat, backoff, fallback flag, auth hooks.
- `web/src/realtime/follow.ts` — `followResource()` for a view watching one resource: event-driven throttled REST refresh, fallback timer while the socket is down.
- `web/src/domain/jobsWorkspace.ts` — REST snapshots and job events both flow through `reconcileJobs`, so toasts, desktop notifications (once per job), upsert receipts, the Operations panel and Research progress update identically whichever transport delivered the change. Terminal events trigger one REST snapshot for results and errors.

Views never call `new WebSocket()`; they subscribe through the client or `followResource`.

## Page and feature audit

| Surface                                | GraphQL                                                                                           | WebSocket                                                                                                              |
| -------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Dashboard `/`                          | Deferred: no duplicated REST composition to remove yet                                            | **Adopted** via the shared job feed (Operations card, corpus-build card, Research activity)                            |
| Records `/records`                     | Deferred: needs paginated `records` root with researcher-safe projection                          | **Adopted** indirectly: LLM review/auto-improve/upsert completion reconciles through the job feed                      |
| Record `/record`                       | **Adopted**: cELF model and Record traceability graph                                             | Adopted indirectly (job feed); collaborative review not requested                                                      |
| Relationship browser `/relationships`  | **Adopted**: uses the same `record_graph`/`celf_model` operations; typed traversal roots deferred | Not useful yet: no provenance-change events exist to invalidate on                                                     |
| Works `/works`                         | Deferred (candidate for `works` root)                                                             | Adopted indirectly: upsert completion refreshes stores via the job feed                                                |
| Search `/search`                       | Deferred: search stays REST; hydration via GraphQL later                                          | Not useful: ordinary searches are short                                                                                |
| Annotations `/annotations`             | Deferred                                                                                          | Not useful until collaborative annotation is requested                                                                 |
| Corpus Builder `/pdf`                  | Deferred (build composition)                                                                      | **Adopted**: `corpus-build:<id>` events replace 1.4 s polling; metadata progress, review counts, stage, model activity |
| Compare `/compare`                     | Deferred (good candidate for multi-Record reads)                                                  | Not useful                                                                                                             |
| Vector stores `/databases`             | Deferred                                                                                          | **Adopted** via upsert job events; counts/stores refresh on completion                                                 |
| Research `/rag`                        | Deferred: `research_run` root after pilot                                                         | **Adopted**: queued/running/stage/warning/terminal via the job feed; token streaming deferred (see `llm.token`)        |
| Response Library `/faq`                | Deferred (response → claims → support)                                                            | Adopted indirectly: Research completion reconciles the job feed; no historical payloads over the socket                |
| Response cache `/response-cache`       | Not useful: operational cache administration                                                      | Not useful                                                                                                             |
| System Data `/system-data`             | Not useful for generic consoles; exemplar subset deferred                                         | Deferred: projection rebuilds are not background jobs yet                                                              |
| Providers `/providers`                 | Not useful                                                                                        | Deferred: warmup is not a tracked job; no API keys may ever be sent                                                    |
| Metadata schemas `/schemas`            | Not useful yet                                                                                    | Not useful: no long-running schema actions are jobs                                                                    |
| Metadata memory `/metadata-memory`     | Deferred (`metadata_exemplar` root)                                                               | Deferred: exemplar reprojection is not a tracked job                                                                   |
| Help `/help`                           | None                                                                                              | None                                                                                                                   |
| Settings `/settings`                   | Not useful                                                                                        | Adopted indirectly (active jobs via the job feed); preferences are not realtime                                        |
| Users `/users`, Roles `/roles`         | Not useful                                                                                        | Role changes close the socket (4403 + `auth.permissions_changed`) on the next heartbeat                                |
| Languages `/languages`                 | Not useful                                                                                        | **Adopted**: translation and content-policy jobs follow `job:<id>` instead of 1.2–2 s polling                          |
| Authentication                         | None                                                                                              | **Adopted**: connect after login, close on logout/expiry, 4401 dispatches the auth-expiry flow, no reconnect loop      |
| Operations panel (global)              | None (history stays REST)                                                                         | **Adopted**: central consumer; live-region policy, undo, desktop notifications and relative-time clock unchanged       |
| LLM review workspace/dialog            | Deferred                                                                                          | **Adopted**: the review dialog follows `job:<id>` instead of 4 s polling; decisions stay REST                          |
| Corpus model activity                  | None                                                                                              | **Adopted**: `llm.*` events refresh the build; the per-second elapsed counter stays a local clock                      |
| Source import / Gutenberg / Wikisource | Not useful                                                                                        | Deferred: archive download/unpack status is not a tracked job, so its 2 s status poll remains while it changes         |
| Backup / Restore / Nuke                | None                                                                                              | Deferred until backup/restore become jobs; nuke invalidates sessions, which closes sockets on the next heartbeat       |

Timers that only drive relative time, elapsed counters, announcement delays, debounce, animation or undo windows are intentionally unchanged.

## Adding an event

1. Emit a transport-neutral note from domain code (`operation_events.py`) or extend `job_realtime_summary`; never import realtime code into a manager.
2. Map it to a public type in `realtime/events.py`, add the type to `protocol.py` (and to `COALESCABLE_EVENT_TYPES` only if a newer instance fully supersedes an older one), and set an `Audience` that matches the REST authorization for the same data.
3. Keep payloads bounded and free of source text, prompts, model output, secrets and hidden reviewer values; send identifiers and let clients read details over REST/GraphQL.
4. Mirror the type in `web/src/realtime/protocol.ts`, bump `PROTOCOL_VERSION` only for incompatible changes (clients ignore unknown event types), and add backend and frontend tests.

## Deployment

nginx proxies `/api/ws/` with `proxy_http_version 1.1`, `Upgrade`/`Connection: upgrade` headers and a 120 s read timeout (longer than the heartbeat). The Vite dev server proxies `/api/ws` with `ws: true`. No additional container is required. Connection metadata (connection id, user id, role, subscription count, queue depth, coalesced/dropped counts, close code) is logged; cookies, payloads, source text, prompts and secrets are not.

Configuration: `REALTIME_ENABLED`, `REALTIME_MAX_CLIENT_MESSAGE_BYTES`, `REALTIME_MAX_QUEUE_EVENTS`, `REALTIME_REPLAY_EVENTS`, `REALTIME_PROGRESS_MAX_HZ`, `REALTIME_HEARTBEAT_SECONDS`, `REALTIME_IDLE_TIMEOUT_SECONDS`, `REALTIME_ALLOWED_ORIGINS` (see `.env.example`).

The in-memory broker assumes the single API process DerridAI already requires for job execution.
