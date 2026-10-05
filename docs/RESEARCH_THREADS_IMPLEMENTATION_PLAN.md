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

# Research Threads and Follow-Up Questions — Implementation Plan

## Purpose

This document is an implementation handoff for converting Research from a sequence
of independent one-off questions into durable research threads with follow-up
questions, while preserving DerridAI's evidence, provenance, reproducibility, and
Pipeline Studio contracts.

The first-question experience on **Research** should remain substantially as it is
today. The change begins after the first answer: the user remains in the same
research workspace, can ask a follow-up question, and can continue an explicit
thread of inquiry. The **Research Library** should become a library of threads
rather than a flat archive of cached answers.

This is not a request to turn Research into an ordinary chat interface. Every
assistant answer remains a separate auditable Research operation with its own
retrieval, evidence packet, generation, claims, support bindings, pipeline
identity, validation, grade, and timing.

Before editing code, re-read the current versions of:

- [AGENTS.md](../AGENTS.md)
- [SPECIFICATION.md](../SPECIFICATION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [USER_GUIDE.md](USER_GUIDE.md)
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)
- [requirements/RESEARCH_RETRIEVAL_AND_EVIDENCE.md](requirements/RESEARCH_RETRIEVAL_AND_EVIDENCE.md)
- [requirements/MEMORY_AND_PRECEDENTS.md](requirements/MEMORY_AND_PRECEDENTS.md)
- [requirements/PIPELINES_AND_SYSTEM_DATA.md](requirements/PIPELINES_AND_SYSTEM_DATA.md)
- [PIPELINE_STUDIO_BUILDER_HANDOFF.md](PIPELINE_STUDIO_BUILDER_HANDOFF.md)

Verify all file names, symbols, schemas, and APIs against the current branch before
editing. This plan was written against the architecture in `master` at the time
of writing; do not treat a stale path or function name as authoritative if the
code has moved.

## Core design decision

Use the following relationship:

```text
ResearchThread
  └── ResearchTurn 1
        └── ResearchRun 1
  └── ResearchTurn 2
        └── ResearchRun 2
  └── ResearchTurn 3
        └── ResearchRun 3
```

A **ResearchThread** is an application-level interaction container. It is not a
new cELF scholarly object and must not be presented as documentary authority.

A **ResearchTurn** is one user research question plus the answer produced for that
question. It connects the conversational UI to one independently auditable
Research operation.

A **ResearchRun** remains the cELF-aligned audit view of one research operation.
Do not collapse several turns into one long ResearchRun merely because they were
asked in the same thread.

The key invariant is:

> Threads provide continuity of inquiry; ResearchRuns preserve independence of
> evidence.

## Non-negotiable scholarly invariants

The implementation is unacceptable if any of the following are violated.

1. Prior thread text is **advisory context, not evidence**.
2. A prior answer does not become an `EvidenceRef`, `EvidencePacket` entry, or
   `SupportBinding` merely because it is supplied to a later prompt.
3. A generated claim in turn N may be represented as supported only by evidence
   acquired or researcher-selected for turn N and resolved through the current
   evidence packet.
4. Prior claims promoted into current support must still follow the existing
   revision-aware re-resolution rules against current Record/RecordRevision or
   SourceSpan state.
5. Thread context must remain distinguishable from Research response/claim memory.
6. Thread context must remain distinguishable from metadata exemplar memory.
7. Thread context must remain distinguishable from retrieval candidates and
   documentary evidence.
8. Deterministic code continues to own source binding, citation rendering,
   EvidenceRef identity, exact-quote checks, claim/evidence relations, and stale
   revision checks.
9. Thread configuration may tune computation, but it must not weaken required
   evidence/provenance gates.
10. Existing one-off Research runs must remain readable and migratable.
11. No default change may silently add extra LLM calls merely to support a
    follow-up question.
12. Pipeline traces may record thread/turn IDs, counts, budgets, and selection
    metadata, but must not copy full prior questions/answers into operational
    telemetry.
13. Researcher authorization remains owner-scoped at the API boundary.
14. Researcher-visible thread/run payloads must use the same text/evidence
    sanitization policy as current researcher RAG results.
15. Existing `E0`/`E1` inline citation and SupportBinding behavior must remain
    unchanged.

The relevant existing product requirements remain in force, especially
`PRD-RES-001` through `PRD-RES-010`. Add thread-specific requirements rather
than weakening or rewriting those requirements around a conversational model.

## Current architecture to preserve

At the time of writing:

- `web/src/views/ResearchView.vue` owns the native Research workspace and already
  composes `ResearchComposer`, `ResearchResultPresentation`,
  `ResearchSettingsDrawer`, `ResearchRunsDrawer`, and
  `ResearchPipelineBar`.
- `web/src/domain/researchWorkspace.ts` constructs Research requests and the
  current one-run draft over Settings-owned defaults.
- `POST /api/jobs/rag` validates a `RAGRunRequest`, resolves the assigned
  Research pipeline, applies server-owned researcher profile policy, and starts
  `RAGJobManager`.
- `api/app/job_rag.py` owns the RAG job lifecycle, response-cache write,
  durable response/claim-memory write, and optional grading.
- `api/app/rag.py` owns the concrete Research execution path and prompt/context
  construction.
- `api/app/pipelines/research.py` compiles the current Research pipeline.
- Research pipeline execution is still intentionally more constrained than
  `vector_store_search` and `evidence_recovery`. Do not set
  `PurposeAdapter.honours_bindings=True` merely to implement threads.
- The logical `_response_cache` is an operational cache/history store.
- Research response/claim memory is separate durable SQLite-backed state used for
  advisory semantic memory.
- The current Response Library is implemented as a response-oriented archive and
  must be migrated to a thread-oriented Research Library without making the
  response cache authoritative.

Do not reintroduce a second ad hoc RAG path outside the assigned Research
pipeline.

## Target user experience

### Starting a thread

When the Research page has no active thread, preserve the current composer-first
experience:

1. The user enters a question.
2. The user may adjust the existing Research settings.
3. Starting Research creates a new thread and its first turn as part of the run.
4. The current answer streams/renders exactly as Research does today.
5. When the answer completes, the composer remains available below the thread.

Do not persist empty threads when a user merely opens Research and leaves.

### Asking a follow-up

After a completed answer:

1. The composer changes its semantic role from "start research" to
   "ask a follow-up" while preserving the same underlying component where
   practical.
2. Starting another run appends a new turn to the active thread.
3. The previous turn is supplied as bounded advisory context according to the
   resolved thread-context policy.
4. The new turn performs its own retrieval/evidence packaging and generates its
   own answer.
5. The previous answer never appears in the new turn's EvidencePacket.
6. The page scrolls to the new turn and keeps the composer available for another
   follow-up.

### Inspecting older turns

A thread is linear in the first implementation.

Selecting an older turn for inspection must not silently change the ancestry of
the next follow-up. A new follow-up always appends after the latest turn in the
thread.

Do not implement implicit branching. If branching is added later, make it an
explicit **Fork from here** operation that creates a new thread with declared
lineage.

### New thread

Add a clear **New thread** action.

It resets the active thread and question draft but should preserve the user's
current Research defaults/settings unless the existing product contract says
otherwise.

### Thread title

Do not spend an LLM call to title a thread.

Create the initial title deterministically from the first question, using a
bounded normalized prefix. Allow the user to rename the thread later. Renaming a
thread must not mutate any turn, ResearchRun, prompt, or evidence state.

## Domain model

Add application-domain objects with explicit ownership.

### ResearchThread

Recommended durable fields:

```text
thread_id          stable UUID/string primary key
owner              required username/account identity
title              required display title
title_source       auto | user
created_at         timestamp
updated_at         timestamp
archived_at        nullable timestamp
```

Optional future fields may be added only when needed. Do not copy run-level
provider/model/retrieval configuration onto the thread; those belong to each
ResearchRun/turn.

Indexes:

- `(owner, updated_at DESC)`
- `(owner, archived_at, updated_at DESC)`

### ResearchTurn

Recommended durable fields:

```text
turn_id            stable UUID/string primary key
thread_id          foreign key/reference to ResearchThread
ordinal            positive integer, unique within thread
question           immutable user question
instructions       immutable per-turn instructions, if supplied
answer             nullable until completion; immutable after completion
job_id             nullable/unique job reference
response_id        nullable response-memory/cache identity
status             preparing | queued | running | completed | failed |
                   cancelled | interrupted
created_at         timestamp
started_at         nullable timestamp
completed_at       nullable timestamp
failure_detail     nullable bounded diagnostic text
```

Use a unique constraint on `(thread_id, ordinal)`.

The turn owns the durable conversational transcript needed to reconstruct thread
context. Keep the existing response-memory answer during this migration for
compatibility; do not try to normalize every existing persistence path in the
same change. The completion path should write one answer value through one domain
operation so `research_turns.answer` and the existing durable response-memory row
cannot drift.

Do not make thread/turn rows a substitute for cELF ResearchRun state. Run-level
evidence, generation configuration, validators, grades, pipeline identity, and
claim bindings continue to live in their existing run/provenance structures.

### Relationship to generated claims and memory

Add `thread_id` and `turn_id` references where useful for navigation, but keep
existing `run_id`, `response_record_id`, claim ID, and SupportBinding identity
unchanged.

Research response/claim memory must remain its own subsystem:

```text
ResearchThread / ResearchTurn
    explicit conversation lineage
    deterministic owner/thread membership
    no quality threshold required

Research response/claim memory
    semantic similarity retrieval
    may retrieve material from another thread owned by the same user
    existing grade/validation eligibility rules
    optional advisory memory
```

A turn being part of a thread does not automatically make it eligible for
semantic response memory.

## Persistence and migration

Implement thread persistence in System SQLite through the existing repository /
`system_store` architecture. Do not create a separate SQLite file unless current
persistence ownership has changed and there is a demonstrated reason.

### Schema migration

Add idempotent creation/migration for `research_threads` and
`research_turns`. Follow the current SQLite migration conventions in
`api/app/persistence.py`.

All methods must be owner-aware. Recommended repository operations:

- `create_research_thread(...)`
- `get_research_thread(thread_id, owner=None)`
- `list_research_threads(owner, query, archived, limit, offset)`
- `rename_research_thread(...)`
- `archive_research_thread(...)`
- `create_research_turn(...)`
- `set_research_turn_job(...)`
- `mark_research_turn_running(...)`
- `complete_research_turn(...)`
- `fail_research_turn(...)`
- `list_research_turns(thread_id, owner)`
- `get_research_turn(turn_id, owner)`

Keep raw SQL in the repository layer. Keep thread selection/prompt policy in a
domain service, not in persistence methods.

### Legacy response migration

Existing flat responses must continue to appear after the change.

Implement an idempotent compatibility migration with this order:

1. For existing durable response-memory rows not already linked to a turn,
   create one legacy thread containing one completed turn.
2. Use the existing question and answer as the turn transcript.
3. Preserve the existing response ID, run/job IDs, grades, claims, evidence,
   provider/model metadata, and cache identity.
4. For older cache records that predate a durable response-memory row, create a
   legacy one-turn thread from the saved response-cache record if enough data is
   available.
5. Mark migrated rows with a schema/migration flag or a deterministic mapping so
   the migration cannot duplicate threads on the next start.
6. Do not rewrite generated claim IDs or SupportBindings.
7. Do not delete the old response cache as part of migration.

If scanning the complete Chroma response cache at startup would be unbounded for
large installations, split the migration:

- migrate SQLite response-memory rows eagerly;
- expose remaining cache-only rows through a read-only virtual one-turn-thread
  compatibility adapter;
- materialize them lazily or through a bounded migration job.

Do not make application startup depend on an unbounded Chroma scan.

### Backup/restore

Thread/turn state is durable application/research state, not disposable
operational telemetry.

Ensure full backup/restore includes the new tables and preserves:

- thread IDs;
- owner;
- turn order;
- question/answer transcript;
- links to response/run/claim state;
- archive state.

Add referential-integrity checks after restore.

## Research thread service

Create a focused backend domain service, for example
`api/app/research_threads.py` if that name is still appropriate.

Do not put thread orchestration into `routers/jobs.py`,
`job_rag.py`, or `persistence.py`.

The service should own:

- creating or validating a thread for the current owner;
- allocating the next turn ordinal safely;
- creating the pending turn;
- selecting prior thread context;
- producing a typed ThreadContextPacket;
- attaching a job ID after RAG job creation;
- updating turn lifecycle state;
- completing the turn with one answer/response identity;
- migration/legacy helpers that are genuinely domain-specific.

### Starting a turn

Refactor the current RAG job route enough that one shared domain path can start
both first questions and follow-ups.

Recommended flow:

```text
POST /api/jobs/rag
  -> validate auth/content policy
  -> resolve provider profile and Research pipeline as today
  -> ResearchThreadService.prepare_turn(owner, optional thread_id, question)
       -> create thread if absent
       -> validate ownership if present
       -> create pending turn
       -> select advisory prior-turn context
  -> rag_jobs.create(..., thread_ref, thread_context_packet)
  -> attach job ID to turn
  -> return job + thread_id + turn_id
```

If job creation fails after a turn is prepared:

- do not leave the turn in `queued`;
- mark it failed with a bounded reason or roll it back according to the
  repository transaction pattern;
- if this was the first turn of a newly created thread and no useful state was
  produced, remove the empty thread.

Avoid races in which a worker begins generation before its thread/turn/context
identity exists.

### Job lifecycle integration

Add `thread_id` and `turn_id` to RAG job state and durable job snapshots.

On transitions:

- queued -> turn queued;
- running -> turn running;
- completed -> turn completed with answer/response ID;
- failed -> turn failed;
- cancelled -> turn cancelled;
- restart interruption -> turn interrupted.

If current job persistence can finish in a different process lifecycle than the
thread update, add an idempotent reconciliation operation at startup rather than
silently leaving a permanently running turn.

Thread lifecycle updates must not interfere with existing cancellation,
provider-concurrency, realtime, or job-retention behavior.

## ThreadContextPacket

Introduce a dedicated typed structure. Do not reuse `EvidencePacket`.

A reasonable shape is:

```json
{
  "thread_id": "thread-...",
  "current_turn_id": "turn-...",
  "strategy": "last_turn",
  "selected_turns": [
    {
      "turn_id": "turn-...",
      "ordinal": 1,
      "question": "...",
      "answer": "...",
      "response_id": "..."
    }
  ],
  "retrieval_context": "...",
  "generation_context": "...",
  "max_turns": 1,
  "max_chars": 8000,
  "truncated": false
}
```

This example is a contract sketch, not a requirement to expose every field over
HTTP.

### Default policy

The initial production default should be conservative:

- strategy: `last_turn`;
- maximum prior turns: `1`;
- bounded character/token budget;
- include the previous user question in retrieval contextualization;
- include previous user question + previous assistant answer in generation
  advisory context;
- do not put the prior assistant answer directly into lexical/dense retrieval
  text by default;
- no additional LLM call solely for follow-up rewriting.

The initial exact character budget may be adjusted to existing provider/context
budget conventions, but it must be explicit, bounded, traced, and tested. If
`8000` characters conflicts with current generation budgets, choose a safer
value and document it in the strategy config rather than introducing a hidden
constant.

### Deterministic truncation

When the selected prior turn exceeds the advisory-context budget:

1. Never truncate the current question.
2. Preserve the prior user question before the prior answer.
3. Truncate the prior answer deterministically.
4. Include an explicit truncation marker in model-facing context.
5. Record the original length, supplied length, and truncation flag in
   reproducibility state.
6. Do not summarize the prior answer with another LLM as the default truncation
   mechanism.

A future summarization strategy may be implemented as an explicit Pipeline Studio
strategy with its own model call and trace, not as hidden prompt compression.

### Eligible turns

For `last_turn`, select the immediate prior ordinal in the same thread.

- Always retain its user question.
- Include its assistant answer only if the turn completed with an answer.
- Never cross thread ownership.
- Never retrieve another thread merely because it is semantically similar; that
  remains the job of optional Research response/claim memory.
- The current turn is never eligible as its own context.

For future `recent_window` mode, preserve chronological order.

For future semantic `relevant` or `hybrid` selection, use rebuildable
similarity projections and keep the explicit thread lineage authoritative.

## Prompt and retrieval behavior

### Separate advisory thread context from evidence

Model-facing generation must contain clearly separated sections equivalent to:

```text
THREAD CONTEXT — advisory, non-evidentiary
Previous user question: ...
Previous answer: ...

CURRENT QUESTION
...

CURRENT EVIDENCE — only this section is eligible to support current claims
[E0] ...
[E1] ...
```

Exact wording should follow existing prompt-contract conventions and must remain
corpus-neutral.

Add tests that fail if prior-answer text is inserted into the EvidencePacket or
if a prior answer can resolve an evidence marker.

### Query contextualization

Do not add a default extra LLM call.

Use the existing Research query-decomposition stage
(`query.research_decompose` at the time of writing) when enabled:

- provide the selected ThreadContextPacket as a separately labelled advisory
  input;
- ask the existing decomposition operation to resolve the current question in
  light of that context;
- retain the original current question unchanged;
- retain the derived/standalone query in normal ResearchRun diagnostics;
- bump the relevant prompt/contract version because the semantics changed.

When query decomposition is disabled, construct a deterministic retrieval input
that includes the current question and the selected prior **user question(s)**,
but excludes prior assistant answer prose from direct retrieval text.

This gives follow-ups such as "What about Levinas?" enough lexical/semantic
context without allowing generated prose to become a retrieval corpus.

### Generation

The generation stage receives:

- current question;
- current EvidencePacket;
- bounded ThreadContextPacket;
- optional existing response/claim memory blocks;
- existing runtime authorship/attribution context.

Keep each source labelled by role. Do not merge thread history, response memory,
claim memory, or evidence into one undifferentiated "context" string before
validation/tracing.

### Reproducibility

For each turn, retain enough information to reconstruct which prior-turn context
was supplied:

- thread ID;
- current turn ID;
- selected prior turn IDs/ordinals;
- thread-context strategy/config;
- supplied character/token budget;
- truncation state;
- content digests and/or deterministic references to immutable turn text;
- original and derived query;
- prompt-contract version.

Operational pipeline traces should keep IDs/counts/budgets/digests, not full
question/answer bodies.

## Pipeline Studio integration

Thread identity and turn storage are application domain state. Pipeline Studio
must not own thread creation, title, ownership, ordering, archive state, or
library behavior.

Pipeline Studio **should** own how thread history participates in Research
computation.

### Add a thread-context strategy

Add a server-owned registered strategy representing bounded thread-context
selection. A likely ID is `context.thread_history`; verify current registry
naming before settling the final identifier.

The strategy should be:

- purpose-compatible with `research`;
- scholarly effect: advisory/context selection, never support;
- deterministic for `none`, `last_turn`, and `recent_window`;
- bounded;
- owner-aware through the run context, not through arbitrary pipeline data;
- `concurrency=safe` if it performs only local reads/selection;
- incapable of changing source/evidence authority.

Suggested config keys:

```text
mode                  none | last_turn | recent_window
max_turns             bounded positive integer
max_chars             bounded positive integer
include_answers        boolean
retrieval_questions   boolean
```

Do not expose `relevant`/semantic mode until it is actually implemented and
traced.

### Typed ports

If a new stage is added, extend `api/app/pipelines/contracts.py` with explicit
typed ports. Do not pass thread history through a generic candidate/evidence port.

Introduce a distinct output type such as `thread_context`.

Downstream Research query transformation and generation may accept the
thread-context input as optional.

Keep invalid cross-type bindings impossible at validation time.

### Research adapter limitation

Do **not** use this feature as justification for claiming the Research purpose
supports arbitrary rewiring.

At the time of writing, `api/app/pipelines/research.py` compiles a constrained
Research shape and the Research purpose intentionally remains inspect-only when
explicit bindings change wiring that the runtime does not honor.

Implement thread-context support in the current compiled Research plan:

1. recognize the supported thread-context stage/config;
2. execute it in the expected fixed position;
3. pass its typed result to query decomposition and generation;
4. preserve the existing rules for unsupported rewiring;
5. keep `PurposeAdapter.honours_bindings` unchanged unless the entire Research
   executor is separately migrated and parity-tested.

### Built-in Research pipelines

Update code-owned built-in Research pipeline definitions to include the new
thread-context stage without changing first-turn behavior.

For a first turn, the stage returns an empty ThreadContextPacket and the rest of
the pipeline should produce the same behavior as before, aside from explicitly
recorded empty thread-context metadata.

Any pipeline definition/version/hash change must follow the existing immutable
pipeline-version rules. Do not silently mutate a recorded historical definition
under the same content hash.

### Pipeline Studio UI

Pipeline Studio should explain the stage in plain language:

- it supplies earlier turns as advisory conversational context;
- it does not make earlier answers evidence;
- it does not create claim support;
- the current run still requires current evidence.

Expose configuration through normal stage editing/inspection components rather
than a Research-page-only hidden setting.

If per-run override is allowed, expose it through the existing Research settings
drawer using the same layered configuration rules:

```text
Pipeline Studio definition
  -> Settings override
  -> one-run Research override
```

Do not create a second independent thread-context configuration store.

## API contract

### RAG start request

Extend the Research start contract additively with an optional
`thread_id`.

The client supplies only the thread ID it wants to continue. The server:

- validates ownership;
- creates the next turn ID;
- allocates the ordinal;
- selects prior-turn context;
- returns canonical thread/turn IDs.

Do not trust client-supplied owner, turn ordinal, prior-turn IDs, or context text.

### RAG job response

Add:

```json
{
  "thread_id": "...",
  "turn_id": "...",
  "turn_ordinal": 2
}
```

to job summaries/details where appropriate.

### Thread endpoints

Add owner-scoped REST endpoints under a focused Research namespace, for example:

```text
GET    /api/research/threads
GET    /api/research/threads/{thread_id}
PATCH  /api/research/threads/{thread_id}
POST   /api/research/threads/{thread_id}/archive
POST   /api/research/threads/{thread_id}/restore
```

The list endpoint should support bounded:

- text search;
- archived filter;
- limit/offset or the repository's standard pagination convention;
- administrator owner filter, if current permission policy allows it.

Do not put full evidence text for every turn in the thread-list response.

The detail endpoint may return turn summaries plus links/IDs used to fetch the
existing run details. For researcher accounts, use the same sanitization contract
as `sanitize_rag_job`.

### Permissions

Change the product model so ordinary Research users can access **their own**
thread history even though the legacy Response Library has historically been an
administrator surface.

Required behavior:

- researcher/custom role with Research permission: list/open/rename/archive own
  threads only;
- administrator: may inspect all threads according to current admin policy;
- unauthorized access to another user's thread returns the same not-found style
  behavior used by current owner-scoped RAG jobs;
- thread IDs must never be enough to bypass owner checks.

Update role capability copy/tests deliberately. Do not accidentally expose the
old administrator-only cache browser to researchers; expose the new
research-thread domain API instead.

## Research Library migration

Rename the user-facing concept from **Response Library** to **Research Library**.

The Research Library lists threads, not individual cache records.

Recommended row/card information:

- thread title;
- first question or a short preview;
- last activity;
- turn count;
- archive state;
- owner for administrators;
- compact last-run provider/model/evidence context where useful.

Opening a thread should navigate to Research with the thread active.

### Routing

Use a canonical Research URL such as:

```text
/rag?thread=<thread_id>&turn=<turn_id>
```

The `turn` parameter is for inspection/scroll position; it must not change the
parent of the next follow-up.

Keep legacy `?job=<job_id>` support long enough to resolve old links. When a
legacy job is linked to a migrated turn, normalize the URL to the canonical
thread/turn form.

Create a canonical Research Library route, for example
`/research/library`, while retaining the historical `/faq`/Response Library
route as a redirect/compatibility alias for at least one migration window.

Do not put question/answer text into URLs.

### Response cache after migration

Keep `_response_cache` as operational run/cache history.

After thread migration:

- clearing response cache must not delete Research threads;
- retention of saved response-cache rows must not erase thread transcript;
- System Data copy must explain the distinction;
- response cache may still be useful for compatibility, rerun metadata, and
  operational inspection;
- Research Library must not depend on Chroma being available merely to list
  threads.

Update `api/app/data_retention.py`, System Data help/copy, and tests so this
distinction is explicit.

## Frontend implementation

### ResearchView decomposition

Do not grow `ResearchView.vue` into another monolith.

Keep it as orchestration and extract thread-specific behavior into focused
modules/components.

Suggested additions:

```text
web/src/components/research/ResearchThreadHeader.vue
web/src/components/research/ResearchThreadTimeline.vue
web/src/components/research/ResearchTurn.vue
web/src/components/research/ResearchThreadList.vue
web/src/features/research/useResearchThread.ts
web/src/api/researchThreads.ts
```

Use the project's existing UI wrappers rather than raw bespoke controls where a
wrapper exists.

### Research timeline

The timeline should render:

- user question;
- assistant answer;
- turn status;
- generated answer citations;
- per-turn evidence access;
- per-turn grade/claim actions where the current product already exposes them.

Avoid eagerly loading all heavy evidence/run detail for a long thread.

Recommended behavior:

- list/detail API returns lightweight turn summaries;
- active/expanded turn lazily loads full existing RAG job/result detail;
- completed answer text needed for normal reading is available without fetching
  every EvidencePacket;
- opening evidence for one turn must not replace another turn's evidence state.

Reuse `ResearchResultPresentation` by extracting smaller presentation pieces if
necessary rather than copy/pasting its citation/evidence logic.

### Composer behavior

Preserve `ResearchComposer`.

It should accept enough state to present:

- first-question mode;
- follow-up mode;
- disabled/running state;
- active thread title/identity for accessible description.

Submitting in follow-up mode passes the active `thread_id`.

After successful submission:

- clear only the prompt text needed for the next follow-up;
- do not clear the thread;
- do not silently reset pipeline/provider settings;
- focus/scroll to the newly created turn using accessible focus management.

### Existing run drawer

Do not conflate operational job history with thread navigation.

If `ResearchRunsDrawer` remains useful, keep it as run/job history. Add thread
navigation separately or replace the primary ordinary-user entry point with a
thread list while keeping run history under diagnostics/advanced controls.

### Research Library view

Replace the current response-centric library implementation with a
thread-centric component/view.

If renaming `ResponseFaqView.vue` would create excessive routing churn in one
change, a temporary compatibility wrapper is acceptable:

```text
ResponseFaqView.vue -> redirects/composes ResearchLibraryView.vue
```

Do not leave two separate sources of truth.

## Streaming and realtime

Current live generation deltas are job-scoped. Keep that model.

Add thread/turn IDs to the bounded realtime job summary metadata if needed for
the frontend to route deltas to the correct turn, but do not broadcast prompt,
answer, evidence text, or thread transcript in notification payloads.

A live delta updates only the current active turn's draft answer.

On final completion, replace live draft state with the persisted completed turn
and normal run result.

Cancellation must leave a visible cancelled turn; it must not remove earlier
turns or corrupt the next ordinal.

## Grading, claims, rerun, and validation

### Grading

Grades remain per ResearchRun/turn.

A thread has no synthesized "overall grade" in the first implementation.

Do not average turn grades into a thread score.

### Claim validation

Generated claims remain per run.

Add navigation from a claim to its thread/turn if useful, but do not change claim
authority semantics.

Validated claim memory may later guide another turn through the existing claim
memory channel, which remains separate from explicit thread context.

### Rerun with parameters

Existing **Re-run with parameters** behavior should not silently rewrite a
historical turn.

In the first implementation, rerunning a historical turn should prefill a new
Research run and create a **new thread** unless the user explicitly chooses to
append it as a new current turn.

Do not create hidden branching semantics.

### Continue from an old turn

Do not implement this implicitly.

A future explicit **Fork from here** action may:

1. create a new thread;
2. record `forked_from_thread_id` / `forked_from_turn_id` as application
   lineage;
3. copy no evidence authority;
4. continue with normal new-turn ResearchRuns.

This is out of scope for the first implementation unless required by a product
requirement added during implementation.

## Internationalization and accessibility

All new user-facing strings require complete `en-US` and `fr-CA` parity.

Required accessibility behavior includes:

- semantic heading order through long threads;
- keyboard-accessible thread selection and menus;
- visible focus;
- meaningful busy/status announcements for a running follow-up;
- no focus loss when streaming completes;
- accessible labels distinguishing "new thread" from "new follow-up";
- evidence/citation controls remain keyboard accessible per turn;
- 12px minimum text;
- WCAG 2.2 AA in light and dark;
- reduced-motion-safe scrolling/transitions.

Add Storybook stories for new thread/timeline components, including:

- empty/new thread;
- one completed turn;
- several completed turns;
- running follow-up;
- failed/cancelled turn;
- long title/question;
- long thread context indicator;
- archived thread/library card;
- researcher vs administrator affordances.

Run axe through the existing Storybook/E2E gates.

## Product requirements and documentation

During implementation, add explicit thread requirements to
`docs/requirements/RESEARCH_RETRIEVAL_AND_EVIDENCE.md`.

Suggested requirement topics:

- Research supports durable owner-scoped threads of independently auditable
  turns.
- Every assistant turn maps to one ResearchRun rather than sharing evidence state
  with earlier turns.
- Thread context is advisory and must remain separate from EvidencePacket and
  SupportBinding state.
- The selected prior turns and context policy are reproducibly recorded.
- Research Library lists threads while legacy one-off responses migrate as
  one-turn threads.
- Researchers can access only their own thread history.
- Pipeline Studio controls context-selection computation, not thread identity or
  ownership.

Add requirement IDs using the next available `PRD-RES-###` numbers on the
implementation branch; do not guess numbers before checking concurrent edits.

Update:

- `docs/requirements/README.md` if its scope/index needs a thread concept;
- `docs/requirements/TRACEABILITY_MATRIX.md` through the project's normal
  traceability workflow;
- `docs/USER_GUIDE.md` for actual shipped behavior;
- `docs/ARCHITECTURE.md` for the new thread persistence/service boundary and
  cache/memory distinction;
- `docs/PROJECT_CONTEXT.md` implemented/intended matrix;
- `AGENTS.md` only if a new durable invariant future agents must obey is not
  already captured;
- release notes when the implementation is actually included in a release.

Do not edit documentation ahead of implemented behavior in a way that makes an
intended capability look shipped.

## Testing plan

Write behavior tests before or alongside implementation. Do not test only copy or
the presence of source strings.

### Backend persistence tests

Add tests covering:

- create thread;
- owner-scoped fetch/list;
- deterministic first title;
- rename;
- archive/restore;
- create turns with strictly increasing ordinals;
- concurrent turn creation cannot duplicate ordinals;
- immutable completed question/answer;
- migration is idempotent;
- one legacy response becomes exactly one one-turn thread;
- backup/restore preserves threads and turn links.

### Thread-context selection tests

Add focused tests for the selector/service:

- first turn -> empty context;
- second turn -> last turn selected;
- current turn never selects itself;
- wrong owner cannot be selected;
- previous question is preserved;
- completed previous answer included when configured;
- failed/cancelled previous answer not invented;
- deterministic truncation;
- max-turn/max-char bounds;
- recent-window ordering if implemented;
- no semantic cross-thread retrieval in `last_turn`.

### Prompt/evidence separation tests

These are high-severity regression tests.

Prove that:

- prior answer text is not an EvidencePacket entry;
- prior answer text cannot satisfy an evidence marker;
- a current claim cannot bind to a prior turn unless the cited source is
  re-acquired/resolved into current evidence;
- prompt formatting labels thread context as advisory/non-evidentiary;
- current evidence remains the only support-bearing channel;
- unknown evidence markers still fail/stand unresolved exactly as today.

Extend the existing RAG evidence-sufficiency and unified
memory/provenance tests instead of duplicating their validators.

### Query tests

Test:

- decomposition receives bounded thread context;
- original current question is retained;
- derived standalone query is retained;
- decomposition disabled -> deterministic retrieval query contains previous user
  question but not previous assistant answer;
- no extra default model call is introduced.

### Pipeline tests

Update:

- `tests/test_pipeline_contracts.py`;
- `tests/test_pipeline_workflow_semantics.py`;
- `tests/test_pipeline_wiring_and_analysis.py`;
- Research pipeline tests;
- pipeline catalog fixture tests.

Verify:

- thread-context strategy has typed ports;
- strategy contract has bounded config;
- scholarly effect is advisory, not support;
- built-in Research pipeline compiles;
- first-turn behavior remains parity-equivalent;
- changed explicit wiring is still inspect-only unless separately supported;
- operational trace contains IDs/counts/budgets but no thread transcript.

Regenerate `pipelineCatalogContract.json` only with the repository script.

### Job/API tests

Test:

- first run creates thread + turn;
- follow-up appends to same thread;
- response returns canonical thread/turn IDs;
- foreign thread ID returns not found/denied;
- researcher cannot spoof owner/turn ordinal/context;
- completion updates turn;
- failure/cancellation updates turn;
- restart reconciliation marks interrupted state correctly;
- existing clients with no `thread_id` still work.

### Frontend unit tests

Extend the Research tests for:

- composer unchanged in first-question mode;
- first answer establishes active thread;
- follow-up submission carries `thread_id`;
- follow-up appears without replacing earlier answer;
- selecting older turn does not change append target;
- New thread clears active thread but keeps settings;
- canonical URL updates with thread/turn;
- legacy `job=` link resolves;
- evidence selection is turn-local;
- progressive loading does not show prior turn evidence under a new answer;
- access loss clears retained thread data.

Add Research Library tests for:

- thread search/pagination;
- one-turn migrated response;
- multi-turn preview;
- owner filter for admin;
- researcher own-only behavior;
- archive/restore;
- opening a thread returns to Research.

### E2E/accessibility tests

Cover a complete path:

1. create first question;
2. wait for answer;
3. ask follow-up;
4. verify both turns remain visible;
5. open a citation in second turn;
6. verify evidence belongs to second turn;
7. refresh;
8. verify thread restores;
9. open Research Library;
10. reopen thread.

Add axe checks in light/dark and keyboard-only coverage.

## Performance constraints

Do not solve follow-ups by sending an ever-growing raw transcript.

Required bounds:

- context selector has max turns;
- context selector has max chars/tokens;
- thread-list APIs are paginated;
- library does not fetch every EvidencePacket;
- old turn heavy details are lazy;
- realtime payloads remain bounded;
- response-cache migration is bounded/lazy if needed;
- no additional default LLM call;
- no additional default retrieval depth solely because a thread exists.

Measure long-thread rendering with at least 25 turns and library rendering with a
large enough fixture to detect obvious N+1 API patterns.

## Security and privacy

Thread state is user-authored and may contain sensitive research questions.

- Authorize every thread read/write server-side.
- Do not place thread transcript in pipeline traces, logs, realtime events, or
  URLs.
- Apply the existing researcher forbidden-term/content policy to each newly
  submitted question/instructions exactly as today.
- Do not expose administrator-only raw corpus text through thread persistence.
- Use existing researcher RAG sanitization for evidence/run detail.
- Preserve browser workspace isolation between users.
- Treat thread transcript as part of backup-sensitive application data.

## Retention and deletion semantics

In the first implementation, prefer **archive/restore** over destructive
thread deletion.

Do not make operational retention automatically delete a thread because:

- pipeline traces expired;
- finished jobs expired;
- `_response_cache` rows expired or were cleared.

If hard deletion is added later, it must define behavior for:

- validated claims originating from the turn;
- grades;
- response memory;
- audit/provenance references;
- fork lineage;
- backups.

Until those dependencies are designed, archive is the safe product operation.

## GraphQL and SDK compatibility

The existing cELF GraphQL facade may continue to expose ResearchRuns without
making ResearchThread a cELF first-class object.

If thread navigation is useful in GraphQL, expose it only as an explicitly
application-specific type/extension and preserve read-only semantics. Do not add
a GraphQL mutation.

Keep the web SDK/static research client backward compatible:

- existing one-off research calls continue to work;
- additive optional `thread_id` may be exposed;
- do not require thread support for clients that only need one result.

Regenerate GraphQL artifacts only if the schema actually changes.

## Implementation sequence for the coding agent

Use focused commits and keep the branch mergeable. Do not push speculative UI
before persistence/contract tests establish the model.

### Phase 0 — Characterize current behavior

1. Update local branch from current `master`.
2. Read the files listed at the top of this plan.
3. Run the existing focused Research, memory, pipeline, Response Library, and
   provenance tests.
4. Capture current first-run behavior in characterization tests where coverage is
   missing.
5. Identify current response-cache and response-memory migrations before adding
   new tables.
6. Confirm exact current Research pipeline strategy IDs and compiler shape.

Do not change behavior in this phase.

### Phase 1 — Durable thread/turn domain

1. Add SQLite tables and repository methods.
2. Add `research_threads.py` domain service.
3. Add backend types/models.
4. Add persistence/ownership/archive tests.
5. Add idempotent legacy response-memory migration.
6. Add backup/restore coverage.

No frontend work yet.

### Phase 2 — RAG job integration

1. Add optional `thread_id` to Research start input.
2. Create/prepare the turn before job execution.
3. Attach canonical thread/turn IDs to job state.
4. Update lifecycle state on running/completion/failure/cancel/interruption.
5. Persist completed answer through one domain completion operation.
6. Add API/job tests.
7. Preserve clients that omit `thread_id`.

At the end of this phase, two direct API calls should be able to create a
two-turn thread even before the UI supports it.

### Phase 3 — ThreadContextPacket and prompt separation

1. Implement typed ThreadContextPacket.
2. Implement `last_turn` selector.
3. Add deterministic truncation.
4. Feed previous user question into retrieval contextualization.
5. Feed prior Q+A into generation as labelled advisory context.
6. Update query decomposition prompt contract/version.
7. Record selected turn IDs/config/digests in reproducibility state.
8. Add evidence-isolation tests.

Do not proceed if a test can make prior answer prose appear as current evidence.

### Phase 4 — Pipeline Studio strategy

1. Register the bounded thread-context strategy.
2. Add typed contracts/ports.
3. Extend the constrained Research compiler/runtime to execute it.
4. Update built-in Research pipeline versions.
5. Add config schemas/tooltips/locale copy.
6. Keep free-form Research rewiring inspect-only.
7. Regenerate the pipeline catalog fixture.
8. Run pipeline contract/workflow/analysis tests.

### Phase 5 — Thread REST API and frontend data layer

1. Add thread list/detail/rename/archive/restore endpoints.
2. Add owner/admin authorization.
3. Add `web/src/api/researchThreads.ts`.
4. Add thread types.
5. Add `useResearchThread` or equivalent composable.
6. Add canonical URL handling for thread/turn.
7. Add legacy job-link resolution.

Keep payloads bounded.

### Phase 6 — Research timeline UI

1. Extract thread header/timeline/turn components.
2. Preserve the existing first-question composer.
3. Append follow-up runs to active thread.
4. Keep historical answers visible.
5. Lazy-load heavy run/evidence detail.
6. Make evidence state local to each selected turn.
7. Add New thread.
8. Add rename/archive affordances where appropriate.
9. Add Storybook and frontend tests.

Do not redesign unrelated Research settings in this phase.

### Phase 7 — Research Library

1. Add canonical Research Library route/view.
2. Convert the archive list from response rows to thread rows.
3. Open threads back into Research.
4. Add search/pagination/archive.
5. Support researcher own-thread access.
6. Add admin owner filtering if consistent with current permissions.
7. Keep legacy Response Library route as a compatibility redirect.
8. Update System Data so response cache is clearly operational, not the library
   authority.

### Phase 8 — Migration polish and long-thread behavior

1. Add cache-only legacy compatibility.
2. Verify one-off historical responses show as one-turn threads.
3. Test 25+ turn thread rendering.
4. Test large library pagination.
5. Test cache clearing/retention does not remove threads.
6. Test backup/restore.
7. Test restart interruption reconciliation.

### Phase 9 — Requirements, docs, and release integration

After behavior is implemented and tested:

1. add `PRD-RES` requirements;
2. update traceability matrix;
3. update Architecture;
4. update User Guide;
5. update Project Context;
6. update role/help text;
7. add release note when version/release work is requested;
8. run repository formatting and focused/full validation per `AGENTS.md`.

## Likely files to touch

This is a guide, not a license to edit every file listed.

Backend:

```text
api/app/models.py
api/app/persistence.py
api/app/system_store.py
api/app/research_threads.py                 # new, if boundary still appropriate
api/app/routers/jobs.py
api/app/routers/...                         # focused Research thread router
api/app/job_rag.py
api/app/rag.py
api/app/research_memory.py                  # references only; keep subsystem separate
api/app/claim_memory.py                     # references/navigation only if needed
api/app/researcher_view.py
api/app/data_retention.py
api/app/pipelines/registry.py
api/app/pipelines/contracts.py
api/app/pipelines/research.py
api/app/pipelines/workflows.py              # only if purpose contract needs extension
```

Frontend:

```text
web/src/views/ResearchView.vue
web/src/views/ResponseFaqView.vue           # compatibility or migration wrapper
web/src/views/ResearchLibraryView.vue       # likely new
web/src/components/research/*
web/src/features/research/*
web/src/types/research.ts
web/src/api/researchThreads.ts              # likely new
web/src/domain/researchWorkspace.ts
web/src/domain/researchActions.ts
web/src/router/*
web/src/state/workspaceState.ts             # only if route/workspace persistence needs it
web/src/components/system-data/*
web/src/components/pipelines/*
web/src/domain/pipeline*
web/src/locales/* or current locale modules
```

Tests:

```text
tests/test_research_threads.py               # likely new focused domain tests
tests/test_research_memory.py
tests/test_unified_memory_provenance.py
tests/test_rag_evidence_sufficiency.py
tests/test_pipeline_contracts.py
tests/test_pipeline_workflow_semantics.py
tests/test_pipeline_wiring_and_analysis.py
tests/test_pipeline_tracing.py
tests/test_data_retention.py
tests/test_backup_restore.py                 # or current owning persistence test
web/tests/frontend/research-*.test.ts
web/tests/frontend/response-*.test.ts        # migrate/rename as appropriate
web/tests/frontend/pipeline-*.test.ts
web/tests/e2e/*
```

Generated artifacts only when their source contracts change:

```text
web/src/components/pipelines/fixtures/pipelineCatalogContract.json
web/src/api/graphql/schema.graphql
web/src/api/graphql/generated.ts
```

Use the repository generation scripts; never hand-edit generated output.

## Anti-patterns to avoid

Do not:

- send the entire thread on every turn;
- treat a thread as one growing EvidencePacket;
- cite a previous assistant answer;
- let `response_memory` semantic retrieval stand in for explicit thread lineage;
- merge thread context and Research memory into one generic memory subsystem;
- retrieve other threads for `last_turn`;
- add hidden LLM summarization of the transcript;
- add a hidden follow-up-rewrite LLM call;
- make the response cache the source of truth for the Research Library;
- delete thread history when operational cache retention runs;
- trust client-provided turn IDs, ordinals, owner, or prior context;
- add thread transcript text to pipeline traces or realtime events;
- mutate a prior turn when rerunning;
- silently branch from an older selected turn;
- claim the Research pipeline honors arbitrary changed bindings when it does not;
- bypass the assigned Research pipeline with a special follow-up code path;
- duplicate citation/source-binding code in the new timeline UI;
- create hard-coded English-only strings;
- defer accessibility or Storybook coverage until after merge.

## Definition of done

The work is complete when all of the following are true:

- A user can ask an initial Research question with substantially the current UX.
- The completed answer remains on the Research page.
- The user can ask a follow-up in the same thread.
- The follow-up uses bounded prior-turn context.
- The follow-up performs its own retrieval/evidence acquisition.
- Prior answer prose is not current evidence.
- Each answer remains independently auditable as its own ResearchRun.
- Thread-context strategy/configuration is inspectable through Pipeline Studio.
- No default extra model call was introduced for follow-up handling.
- Research Library lists threads.
- Existing one-off responses appear as one-turn threads.
- Researchers can access only their own threads.
- Administrators retain appropriate inspection capability.
- Clearing/retaining `_response_cache` does not remove thread history.
- Refresh/back/forward restore the active thread/turn.
- Citation-to-evidence links remain turn-correct.
- Claim validation and grading remain turn/run scoped.
- Pipeline trace and reproducibility records identify the selected thread context
  without leaking transcript text into operational telemetry.
- Backup/restore preserves threads and links.
- New UI is fully localized in English and Canadian French.
- Storybook and axe coverage exists for new components.
- Backend, frontend, typecheck, build, and relevant E2E tests pass.
- Requirements, traceability, Architecture, User Guide, and Project Context match
  the implementation that actually shipped.
