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

# Research Threads Implementation Plan

This document is an implementation plan for converting DerridAI Research from a one-question/one-answer workflow into a threaded scholarly research workspace with follow-up questions. It is intended to be executable by an AI coding agent from beginning to end.

It is a focused current-state planning document, not a release note. Verify every file path, API shape, model, and invariant against the current branch before editing. Preserve unrelated work and follow [AGENTS.md](../AGENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [USER_GUIDE.md](USER_GUIDE.md), [SPECIFICATION.md](../SPECIFICATION.md), the requirements under [docs/requirements](requirements/), and the current Pipeline Studio contracts.

## 1. Product decision

Research becomes a thread-oriented workspace.

A **Research thread** is a durable user-owned inquiry containing an ordered sequence of user questions and assistant answers. A thread provides conversational continuity. It does **not** replace the existing audit unit.

Each assistant answer remains the output of its own independently auditable **ResearchRun**. A follow-up question therefore creates a new ResearchRun with its own:

- original user question;
- derived/contextualized retrieval query where applicable;
- retrieval configuration;
- selected candidates and evidence packet;
- model/provider and generation settings;
- exact pipeline identity and effective configuration;
- prompt contract;
- generated output;
- claim/support bindings;
- validation and grading state;
- timing and warnings.

The core invariant is:

> **Threads provide continuity of inquiry; ResearchRuns preserve independence of evidence.**

Do not implement a thread as one ever-growing opaque prompt or one long-lived ResearchRun.

## 2. Non-negotiable scholarly semantics

### 2.1 Thread context is advisory, not evidence

Prior user turns and prior generated answers may be supplied to the next run as **thread context**. They must remain structurally and semantically distinct from documentary evidence.

A prior answer MUST NOT become an EvidenceRef, SupportBinding, citation source, or claim support merely because it appears in the next prompt.

If a prior claim is deliberately promoted into current evidentiary support, the normal cELF rule applies: resolve it back to the current authoritative Record/RecordRevision or SourceSpan and expose stale/incompatible state. Do not shortcut this through thread history.

The generation contract must make the distinction explicit, conceptually:

```text
<THREAD_CONTEXT advisory="true" evidentiary="false">
...
</THREAD_CONTEXT>

<CURRENT_QUESTION>
...
</CURRENT_QUESTION>

<EVIDENCE>
...
</EVIDENCE>
```

Only the current run's EvidencePacket may ground citations/support.

### 2.2 Thread context is not Research response memory

Keep these systems separate:

- **Thread context**: deterministic lineage inside one explicitly selected thread.
- **Research response memory**: semantic retrieval over eligible prior responses, potentially from other threads.
- **Research claim memory**: semantic retrieval over validated prior claims and provenance.
- **Response Library/cache**: operational saved-response history/cache.
- **Metadata memory**: unrelated reviewed metadata precedents.

Thread context must not require a prior response to be graded. It follows the explicit thread/turn relationship, not semantic similarity.

Existing response/claim memory remains independently configurable. A run may use both thread context and Research memory, but the run trace/result must identify them separately.

### 2.3 Preserve original and derived questions

A follow-up such as “What about Levinas?” may require contextualization before retrieval.

Persist:

- the exact original user question;
- the selected prior thread context;
- the derived standalone retrieval question, if one is produced;
- the contextualization strategy and model/configuration used.

Never overwrite the user's original wording with the derived query.

### 2.4 First-question UX should remain effectively unchanged

The current Research prompt/composer area is already successful. Preserve it.

A new thread initially looks like the current Research experience. After the first answer, the same workspace remains open and the composer continues below/after the conversation so the user can ask a follow-up.

Do not redesign the first-turn composer as part of this project unless required for thread navigation or accessibility.

## 3. Target domain model

Introduce a durable thread/turn model in authoritative application storage. Do not use Chroma as the authoritative store for thread structure.

Recommended logical model:

```text
ResearchThread
  thread_id
  owner
  title
  created_at
  updated_at
  archived_at?
  deleted_at?
  originating_response_record_id?   # optional migration/audit link
  metadata/version fields as needed

ResearchTurn
  turn_id
  thread_id
  ordinal
  user_question
  user_instructions?
  created_at
  research_run_id?                  # null while queued/failed before run creation if necessary
  job_id?
  response_record_id?
  assistant_answer?                 # optional denormalized/read model; authoritative run/cache linkage preferred
  status
  parent_turn_id?                   # optional, for future branching; linear v1 still uses previous turn
  contextualized_query?
  context_selection_snapshot?       # immutable audit snapshot or resolvable reference
```

Prefer immutable or append-oriented turn history. Editing an old user question should not silently mutate the meaning of already-completed later ResearchRuns. If edit-and-rerun is added later, create a new branch/new turn lineage rather than rewriting historical input.

### 3.1 Linear v1, branch-capable identity

Implement v1 as a linear thread, but choose IDs/relations that do not preclude future branching.

The default parent of a new turn is the preceding completed user/assistant turn. Do not build a branching UI now.

### 3.2 Ownership and authorization

Thread ownership follows Research job ownership.

Non-admin users:

- may list/open only their own threads;
- may add turns only to their own threads;
- may not use another user's thread context;
- may not retrieve full corpus text through thread APIs;
- remain subject to existing Research text/content policy and capability checks.

Administrators may retain the existing broader operational access only where current permissions already allow it. Do not expand administrative access implicitly.

### 3.3 Deletion/retention semantics

Decide and implement explicit semantics; do not cascade-delete scholarly provenance accidentally.

Recommended behavior:

- deleting a thread removes or tombstones the thread/turn workspace history;
- deletion does **not** delete canonical corpus data, RecordRevisions, validated claims, SupportBindings, or other authoritative provenance;
- response-cache retention remains governed by its existing owner/retention rules;
- if a response record remains after thread deletion, its thread linkage may become null/tombstoned but the ResearchRun remains auditable.

Coordinate this with `data_retention.py` and existing Response Library retention. Preserve the current distinction between operational saved responses and authoritative provenance.

## 4. Storage design

Use System SQLite / existing durable application persistence for ResearchThread and ResearchTurn authority.

Do not make `_response_cache` the authoritative thread database.

The current response cache can continue to store completed answer artifacts for browsing/replay and may gain thread metadata fields such as:

- `thread_id`;
- `turn_id`;
- `turn_ordinal`;
- `parent_turn_id`.

These are indexes/linkage, not the sole authoritative thread structure.

### 4.1 Schema/migration requirements

Add a migration that:

1. creates thread and turn tables with indexes on owner, updated time, thread/ordinal, job ID, run ID, and response record ID;
2. enforces unique `(thread_id, ordinal)`;
3. prevents cross-owner thread/turn association at the domain/service layer;
4. supports idempotent migration and rollback-safe startup behavior according to existing persistence conventions;
5. does not require Chroma to be online.

### 4.2 Existing saved responses migration

Existing one-off saved responses should become **singleton threads** from the user's perspective.

Do not physically rewrite every response in Chroma unless necessary.

Preferred migration/read-model approach:

- when listing thread history, identify legacy completed responses with no `thread_id`;
- deterministically or transactionally materialize a singleton ResearchThread + ResearchTurn linkage for them;
- store the linkage in SQLite;
- keep the legacy response record intact;
- make migration idempotent;
- avoid creating duplicate threads when the same legacy response is encountered again.

A background/administrative migration is acceptable if startup latency would otherwise become large. In either design, old Research Library content must remain visible.

## 5. Backend service boundary

Create a focused Research thread domain/service rather than embedding thread CRUD directly into `rag.py`, `job_rag.py`, or a router.

Suggested modules, subject to current repository conventions:

- `api/app/research_threads.py` — domain/service operations;
- `api/app/research_thread_store.py` or existing `system_store.py` extension — persistence;
- `api/app/research_context.py` — context-selection and prompt-packet construction if large enough to justify separation.

Do not grow `rag.py` or `job_rag.py` into monoliths.

Core service operations should include:

- create thread;
- list threads for owner with bounded pagination/search;
- get one thread with ordered turns;
- rename thread;
- archive/unarchive if included;
- delete/tombstone thread according to retention policy;
- append user turn atomically;
- bind a created Research job/run/result to the turn;
- fail/cancel a turn without corrupting sequence state;
- derive/display title;
- materialize legacy singleton threads.

## 6. API contract

Add explicit Research thread endpoints rather than overloading the Response Library API.

Exact route names should match current router conventions. A reasonable shape is:

```text
GET    /api/research/threads
POST   /api/research/threads
GET    /api/research/threads/{thread_id}
PATCH  /api/research/threads/{thread_id}
DELETE /api/research/threads/{thread_id}

POST   /api/research/threads/{thread_id}/turns
GET    /api/research/threads/{thread_id}/turns/{turn_id}
```

If the repository currently exposes Research routes elsewhere, place these alongside the existing Research API rather than creating an inconsistent namespace.

### 6.1 Start-run request changes

Extend `RAGRunRequest` or introduce a small wrapper so a Research run can carry:

- `thread_id: str | None`;
- `turn_id: str | None`;
- an explicit context strategy override only if one-run override is supported;
- no raw client-supplied prior assistant content.

The server, not the browser, must load authoritative thread context for a supplied thread/turn. Do not trust the frontend to submit historical answer text because that enables tampering, cross-thread leakage, and audit divergence.

For a new-thread first question:

1. create thread;
2. append turn;
3. create Research job bound to that turn.

Make this atomic enough that failures do not leave ambiguous duplicate turns. If full DB/job atomicity is impossible because jobs are process-local, persist a clear pending/failed state and make retries idempotent.

### 6.2 Idempotency

Double-clicks, reconnects, and client retries must not create duplicate turns/runs.

Add a client-generated or server-issued idempotency token for turn submission, or reuse a robust existing request ID pattern if one exists.

Enforce uniqueness for an idempotency key within the owner/thread scope.

### 6.3 Thread list payload

Return only what the library/navigation UI needs:

- thread ID;
- title;
- owner-visible status;
- turn count;
- first/last question preview;
- created/updated timestamps;
- last run status;
- optional model/evidence-count summary;
- archived state.

Do not send every evidence packet when listing threads.

### 6.4 Thread detail payload

Return turn summaries plus enough result linkage for progressive loading. Avoid one huge response containing all full evidence packets for a long thread.

Prefer:

- thread metadata + ordered turn shells;
- selected/current turn detail loaded independently;
- existing Research result endpoint reused where possible.

This aligns with the current progressive-loading direction in `docs/PROGRESSIVE_LOADING_UX_PLAN.md`.

## 7. Thread context selection

Implement context selection as a deterministic, testable server-owned stage before query decomposition/generation.

### 7.1 Default v1 strategy

Use a conservative hybrid default:

1. always include the immediately preceding completed user/assistant turn;
2. if budget remains, select older relevant turns by semantic similarity to the current question;
3. preserve chronological order in the final context packet;
4. never cross thread boundaries;
5. exclude failed/cancelled turns with no authoritative answer;
6. never treat selected thread context as evidence.

If semantic selection cannot run, fall back deterministically to the most recent prior turns and emit a warning/trace note. Do not silently change behavior.

### 7.2 Context budget

Add an explicit bounded budget independent of the EvidencePacket budget.

Recommended configurable dimensions:

- maximum prior turns;
- maximum thread-context characters or tokens;
- maximum individual prior-answer characters;
- whether prior assistant answers are included;
- whether older semantic selection is enabled.

Defaults should be conservative for local models.

Do not allow context selection to consume the evidence budget or silently truncate evidence to make room.

### 7.3 Context packet structure

Represent context as structured objects internally, not one concatenated string:

```python
ThreadContextItem(
    turn_id=...,
    ordinal=...,
    role="user" | "assistant",
    text=...,
    source="immediate_previous" | "semantic_relevance" | "pinned",
    score=...,
)
```

Only serialize to prompt text at the final prompt-construction boundary.

Retain the selected turn IDs and selection reasons in the ResearchRun/audit result. Pipeline traces may record bounded IDs/counts/strategy but must continue to avoid storing full prompt/response bodies.

### 7.4 Future pinning support

Do not require user pinning in the first PR unless scope permits, but keep the context-selection model extensible for:

- pin turn as context;
- exclude turn from future context;
- “start a new thread from here”;
- branch from an earlier turn.

## 8. Follow-up contextualization / standalone query resolution

Add a distinct step that can turn an elliptical follow-up into a standalone retrieval question.

Examples:

- “What about Levinas?”
- “How does that change the argument?”
- “Is the same distinction present in the French text?”

### 8.1 Contract

Input:

- current original user question;
- bounded selected thread context;
- current user instructions;
- response language preferences as needed.

Output:

```json
{
  "standalone_query": "...",
  "standalone_query_fr": "...",
  "used_context_turn_ids": ["..."],
  "reason": "brief machine-audit explanation"
}
```

Use the shared structured completion helper and schema validation. Preserve philosophical terminology and negation.

### 8.2 Do not answer during contextualization

The contextualizer only resolves references and produces retrieval queries. It must not produce the scholarly answer.

### 8.3 Fallback

If contextualization fails:

- retain the original current question as the retrieval query;
- preserve the thread context for generation;
- emit an explicit warning;
- do not fail the whole Research run unless the existing query-decomposition contract requires it.

### 8.4 Relationship to current query decomposition

Do not create two redundant LLM calls if the current `QUERY_TEMPLATE` can be evolved cleanly to handle thread-aware contextualization and bilingual query derivation in one structured operation.

Prefer one well-defined stage that produces:

- original question preserved separately;
- contextualized standalone query;
- English/French retrieval forms;
- user instructions;
- response language.

If semantics change, bump the relevant prompt/contract version identifier and update reproducibility metadata.

## 9. Research pipeline and Pipeline Studio

### 9.1 Domain state versus pipeline configuration

Pipeline Studio must **not** own:

- thread identity;
- thread title;
- ownership;
- turn ordering;
- thread deletion/archive semantics;
- historical turn persistence.

Those are application-domain state.

Pipeline Studio **may** own computational policy for how thread context participates in a Research run.

### 9.2 Add explicit Research pipeline stages/strategies

Represent these as first-class server-owned strategies/pipeline stages if this can be done without pretending Research supports arbitrary rewiring:

1. **thread-context selection**
2. **follow-up contextualization / query resolution**

Then continue with the existing Research stages:

- query decomposition/contextualized query output;
- retrieval;
- fusion;
- reranking/diversity;
- provenance gate;
- evidence packaging;
- generation;
- citation/source binding;
- evaluation/cache.

### 9.3 Typed channels

Define separate typed channels in `pipelines/contracts.py`:

- `thread_context`;
- `research_query` / derived query;
- existing evidence/candidate/context channels.

The evidence packer and provenance gate must never accept `thread_context` as documentary evidence input.

Generation may receive both:

- evidence packet;
- thread context packet.

This separation should be enforced by types/validation, not only prompt wording.

### 9.4 Keep Research inspect-only for changed free-form bindings

Current Pipeline Studio documentation correctly classifies Research as not yet safe for arbitrary changed bindings.

Do **not** set `PurposeAdapter.honours_bindings=True` as part of adding threads unless the Research runtime is genuinely migrated to resolved wiring.

The thread feature must not depend on that migration.

Add the new stages to the fixed supported Research shape first. Preserve current domain guarantees:

- provenance gate exists;
- final ranking feeds the gate;
- context/evidence packer is fed only by approved current evidence;
- generation receives packed evidence;
- citation binding follows generation;
- evaluation follows citation binding;
- fallback rejoins before the provenance gate.

If thread context reaches generation through an additional port, ensure it cannot bypass or masquerade as the evidence path.

### 9.5 Pipeline Studio configuration

Expose thread-context computation in Pipeline Studio/admin settings with clear descriptions:

- strategy: previous turn / recent window / relevant turns / hybrid;
- maximum prior turns;
- context budget;
- include prior assistant answers;
- semantic older-turn selection;
- contextualization enabled/disabled;
- contextualization provider role/model if the architecture supports provider roles.

Prefer pipeline stage configuration and existing Settings → run override precedence. Do not add unrelated duplicate controls on the Research page unless they are appropriate one-run overrides.

### 9.6 Tracing

Research pipeline traces should record:

- context strategy;
- number of prior turns considered;
- selected turn IDs/ordinals;
- context character/token count;
- whether contextualization ran;
- whether fallback occurred;
- derived-query presence/hash or bounded diagnostic, not full sensitive text if trace policy forbids it;
- exact pipeline identity/configuration provenance.

Continue the rule that pipeline traces do not copy full prompts, source text, response bodies, secrets, or sealed values.

The ResearchRun/result/audit record may retain the actual original/derived query and context snapshot where required for process reproducibility.

## 10. Prompt construction

Refactor prompt construction so thread context is an explicit field rather than ad hoc string concatenation.

The final generation prompt should have independently identifiable sections for:

- master/current question;
- current user instructions;
- response language;
- thread context marked advisory/non-evidentiary;
- Research response memory marked advisory/non-evidentiary;
- validated claim memory marked advisory/non-evidentiary unless re-resolved;
- current EvidencePacket;
- citation/binding instructions.

Add instructions stating:

- do not cite thread context;
- do not cite remembered prior answers;
- only evidence markers from the current EvidencePacket are eligible;
- if a prior answer conflicts with current evidence, current evidence governs;
- attribute claims according to current evidence metadata.

Add tests that deliberately put a false “citation” or fabricated claim in prior thread context and verify it cannot resolve to evidence/support.

## 11. Job lifecycle changes

Extend `RAGJobManager` so each Research job can be linked to `thread_id` and `turn_id`.

On creation:

- persist job/turn linkage;
- expose IDs in safe request/job summaries;
- do not duplicate historical context text inside the job record unless necessary for reproducibility.

On completion:

1. save/cache response as currently;
2. persist generated claims/support as currently;
3. associate the response record and run ID with the ResearchTurn;
4. mark turn completed;
5. update thread timestamp/title metadata;
6. publish realtime invalidation/event for the thread.

On failure/cancellation:

- mark the turn failed/cancelled;
- retain the user's question;
- allow retry without creating duplicate visible user turns unless the user explicitly submits a new turn.

### 11.1 Streaming

The existing live draft remains advisory and unverified.

Associate the streamed draft with both job ID and turn ID in frontend state. A user should see the draft in the correct conversation position.

Once REST returns the authoritative source-bound result, replace the draft in that turn.

Do not let streamed text become thread context for another turn before the current run reaches a stable completed state.

## 12. Frontend architecture

### 12.1 Research page

Keep `ResearchView.vue` as the main workspace but decompose thread-specific behavior into focused modules/components instead of expanding the view indefinitely.

Suggested components/composables:

- `ResearchThreadList` or navigation drawer;
- `ResearchConversation`;
- `ResearchTurn`;
- `ResearchFollowUpComposer` only if the existing `ResearchComposer` cannot be reused cleanly;
- `useResearchThreads`;
- `useResearchThread`;
- `useResearchTurnSubmission`.

Reuse `ResearchResultPresentation` for assistant answer/evidence presentation instead of building a second result renderer.

### 12.2 Workspace behavior

New-thread flow:

1. user lands on Research;
2. current composer/settings appear as today;
3. user submits;
4. thread is created;
5. user question appears immediately;
6. streaming answer appears beneath it;
7. final source-bound result replaces draft;
8. composer remains available for follow-up.

Existing-thread flow:

1. route identifies selected thread;
2. thread shell/turn list loads;
3. latest turn is visible;
4. older full result detail is progressive/lazy;
5. composer submits a new follow-up into that thread.

### 12.3 URL state

Give threads canonical shareable/navigation-safe URLs, for example:

```text
/research?thread=<id>
```

or a named route such as `/research/<thread_id>`, consistent with current router conventions.

Do not serialize prompt draft text, sensitive thread content, API keys, or generation secrets into URL state.

Back/Forward must restore thread selection.

### 12.4 Concurrent jobs

Decide and enforce v1 behavior.

Recommended: permit only one active generation per thread, while allowing Research jobs in different threads subject to existing provider concurrency limits.

Reason: allowing two unresolved follow-ups in the same linear thread makes parent/context semantics ambiguous.

If a thread has a queued/running turn, disable follow-up submission for that thread with a clear status. Do not globally block the Research page from working with another thread if existing concurrency permits it.

### 12.5 Failure/retry UX

A failed turn remains in the conversation with:

- the original user question;
- failure status;
- bounded diagnostic already allowed by current job UX;
- Retry action.

Retry should either reuse the same turn identity with a new run-attempt record or create a clearly linked attempt without duplicating the visible question. Choose one pattern and test it.

### 12.6 Evidence interaction

Each completed assistant turn has its own evidence/result presentation.

Evidence links must target that turn's current ResearchRun/evidence packet, not a thread-global evidence state.

Never let selecting evidence in an older answer overwrite the active follow-up's evidence state accidentally.

## 13. Research Library conversion

Change the user-facing library concept from a flat list of saved responses to a list of **Research threads**.

Do not remove access to the per-run audit/result detail.

### 13.1 Library list

Display:

- thread title;
- first/last question preview;
- turn count;
- updated date;
- optional source/model/evidence summary;
- archived state if supported.

Search should match thread titles and user questions. If answer-text search already exists and is affordable, preserve it where possible, but do not require loading every full answer into the list query.

### 13.2 Thread detail

Opening a library item should open the thread conversation and allow continuing it if permissions permit.

Each assistant turn retains:

- source-bound answer;
- evidence;
- query decomposition/contextualized query;
- retrieval diagnostics;
- pipeline trace/details;
- grades;
- claim provenance;
- rerun/regrade where currently allowed.

### 13.3 Rerun semantics

Existing “Re-run with parameters” must be made explicit:

- **Rerun this turn as a new run** should not silently rewrite the historical answer.
- If rerunning inside the same thread, append a new turn/attempt or create a branch-like continuation with clear lineage.
- A simple v1 option is “Start a new thread from this run” or “Use these parameters for a new question.”
- Do not mutate historical evidence/provenance.

Document the chosen behavior.

## 14. Thread titles

Provide useful titles without introducing a required extra model call.

Default title should be deterministic, based on the first user question, truncated cleanly.

Optionally allow a later background/model-generated title only if it does not add a default LLM call and the user can rename it. Do not make thread creation depend on title generation.

## 15. Response cache changes

Keep the current `cache_rag_response` lifecycle.

Extend saved response metadata with thread/turn linkage where safe.

Response cache continues to be:

- operational history/cache;
- useful for Response Library compatibility;
- distinct from Research response/claim memory;
- not canonical corpus truth;
- not authoritative for thread structure.

Any cache rebuild/loss should not destroy Research thread identity if the authoritative SQLite thread state still exists. If a cached answer is missing, surface the missing artifact rather than silently attaching another response.

## 16. Research memory interaction

A thread-aware run can use three advisory sources:

1. explicit thread context;
2. prior-response memory;
3. prior-claim memory.

Build prompt sections and audit metadata so these remain distinguishable.

Recommended precedence for interpretation:

- thread context resolves conversational references;
- current evidence determines scholarly support;
- response memory may suggest framing;
- validated claim memory may suggest previously supported propositions, but only current evidence can support current citations unless provenance is re-resolved according to existing rules.

Avoid retrieving the immediately preceding answer again through semantic response memory when it is already in explicit thread context. Deduplicate advisory material by response/run ID where possible.

## 17. cELF / provenance requirements

Update cELF mapping and specification/requirements where needed.

At minimum, ensure every follow-up ResearchRun can reconstruct:

- thread ID and turn ID;
- original question;
- derived/contextualized query;
- selected thread-context turn IDs and strategy;
- advisory-memory use separately;
- corpus snapshot/publication state;
- retrieval configuration;
- exact current evidence or deterministic reconstruction;
- generation model/configuration;
- prompt contract/version;
- result;
- validation;
- grading.

The thread itself is an application-level interaction container; do not invent a new cELF evidence authority for it.

If a new cELF extension object is unnecessary, keep thread identity as implementation/domain metadata referencing ResearchRuns.

## 18. Requirements and documentation updates

Before or alongside implementation:

- add product requirements for threads, follow-ups, advisory context/evidence separation, migration, ownership, and reproducibility;
- connect each requirement to specification keys and tests;
- update `SPECIFICATION.md` where normative behavior is new;
- update `docs/ARCHITECTURE.md` with thread/domain/storage relationships;
- update `docs/USER_GUIDE.md` only when behavior is implemented;
- update Pipeline Studio documentation to show thread-context/contextualization stages;
- update GraphQL/read APIs only if Research threads are intentionally exposed there; do not expand scope automatically.

Do not add release notes until the release cut.

## 19. Internationalization and accessibility

All user-facing copy must be localized in English and professional Canadian French with key parity.

Required accessible behavior:

- conversation turns have semantic grouping and meaningful headings/labels;
- streaming state is announced without repeatedly reading the entire generated draft;
- new answer completion has a non-disruptive live-region announcement;
- thread navigation is keyboard operable;
- current thread/turn state is conveyed without color alone;
- focus moves predictably after creating/selecting a thread;
- follow-up submit disabled reasons are available to assistive technology;
- menus/dialogs return focus correctly;
- reduced-motion preferences are respected;
- mobile/narrow layouts remain usable;
- WCAG 2.2 AA passes in light/dark/high-contrast paths already covered by the app.

Use existing UI wrappers/components and design tokens. Add Storybook stories for new reusable components.

## 20. Security/privacy

Treat thread text as researcher-authored content and apply the same relevant content-policy/authorization rules as Research prompts.

Server must validate:

- thread owner;
- turn owner through thread;
- capability to run Research;
- referenced job/run/response belongs to the same authorized owner/thread;
- no arbitrary client-provided historical assistant text is trusted as context.

Do not include:

- API keys;
- provider secrets;
- full hidden corpus text for researcher accounts;
- another user's thread text;
- raw sealed values;

in thread list or trace payloads.

## 21. Realtime invalidation

Extend existing realtime resources/events rather than adding polling-only thread state.

Potential resources:

- `research-threads` list;
- `research-thread:<id>`.

Events should allow the frontend to refresh:

- created thread;
- appended turn;
- turn/job status;
- completed result linkage;
- rename/archive/delete.

Do not stream full evidence packets through broad list events. Continue using REST for authoritative final results.

## 22.0 Implementation status

Update this section as phases land; it is the single place that records progress.

- **Phase B (persistence): done on `feature/research-threads`.** `api/app/research_thread_store.py` owns the `research_threads` / `research_turns` tables on the system SQLite database (owner-scoped CRUD, atomic ordinals, idempotent append via `(thread_id, idempotency_key)`, one active turn per thread, job/run/response linkage, failed/cancelled turns, in-place retry that increments `attempt` rather than duplicating the visible question, tombstone deletion that drops turns and keeps the legacy-materialization key, and idempotent legacy singleton materialization from caller-supplied response summaries). Covered by `tests/test_research_thread_store.py`.
- **Decisions made in Phase B:** non-owners (including administrators) get `ThreadNotFound`; no admin widening. Retry reuses the same turn identity with a new attempt. Deleting a thread never touches the response cache or canonical provenance.
- **Not started:** Phase A requirements/spec entries and first-turn characterization tests, and Phases C through J. Next is Phase C (router, `RAGJobManager` linkage, realtime invalidation); legacy materialization still needs a caller that lists completed responses from the response cache.

## 22. Detailed implementation sequence

The agent should implement in small reviewable commits. Do not combine architectural storage, prompt changes, and large UI changes in one commit.

### Phase A — characterization and requirements

1. Read current:
   - `AGENTS.md`;
   - `SPECIFICATION.md`;
   - `docs/ARCHITECTURE.md`;
   - `docs/USER_GUIDE.md`;
   - Research requirements;
   - Pipeline Studio requirements/handoff;
   - `api/app/rag.py`;
   - `api/app/job_rag.py`;
   - `api/app/models.py`;
   - Research routers/services;
   - response cache implementation;
   - `ResearchView.vue`;
   - `ResearchResultPresentation.vue`;
   - `ResearchComposer.vue`;
   - Response Library view;
   - existing Research frontend domain/actions/types.
2. Record characterization tests for current first-turn behavior before refactoring.
3. Add requirements/spec entries for thread semantics and evidence separation.
4. Decide exact persistence API and migration mechanism using existing repository patterns.

Done when the current one-turn behavior is pinned by tests and the new invariants are written down.

### Phase B — authoritative thread persistence

1. Add thread/turn persistence schema.
2. Add domain models and store operations.
3. Add authorization/ownership checks.
4. Add idempotent append-turn operation.
5. Add legacy singleton-thread materialization.
6. Add backend unit tests for CRUD, ownership, ordering, migration, deletion semantics.

Do not touch prompt generation yet.

Done when threads can be created/listed/read and old responses can be represented as one-turn threads without changing RAG output.

### Phase C — API and job linkage

1. Add thread endpoints.
2. Extend run/start request to carry server-validated thread/turn IDs.
3. Create thread + turn in the start flow.
4. Link `RAGJobManager` jobs to turns.
5. On completion, bind run/response IDs and mark turn complete.
6. Handle failure/cancel/retry.
7. Add realtime invalidation.
8. Add API contract tests.

Done when a normal one-turn Research run is persisted inside a thread with no prompt semantic changes.

### Phase D — frontend thread shell

1. Add Research thread types/API client.
2. Add thread navigation/list.
3. Route current thread in URL state.
4. Render ordered turns.
5. Reuse current result presentation per assistant turn.
6. Keep composer available for follow-up.
7. Associate live draft with the correct turn.
8. Add failure/retry UI.
9. Add Storybook, Vitest, Playwright/axe coverage.

At this stage, a follow-up may still run as an isolated question if context work is not complete. If so, guard the feature behind an internal flag or do not expose follow-up submission until Phase E lands. Do not ship misleading “follow-up” behavior without context.

### Phase E — thread-context selection

1. Implement structured ThreadContextItem model.
2. Implement immediate-previous-turn selection.
3. Add bounded recent/semantic older-turn selection.
4. Add fallback behavior.
5. Persist selection snapshot/IDs.
6. Add trace metadata.
7. Add tests for budget, ordering, cross-thread isolation, missing/failed turns.

Done when the server can deterministically produce a bounded advisory context packet for a follow-up.

### Phase F — contextualized retrieval query

1. Evolve query decomposition or add contextualization stage.
2. Use structured output helper.
3. Persist original + derived query.
4. Preserve bilingual routing.
5. Add failure fallback.
6. Bump prompt/contract version.
7. Add regression tests for pronouns, ellipsis, French, negation, philosophical names, and no-context first turn.

Done when “What about Levinas?” can retrieve as a meaningful standalone query while the original wording remains auditable.

### Phase G — generation prompt separation

1. Add explicit THREAD_CONTEXT prompt section.
2. Keep prior-response and prior-claim memory separate.
3. Keep EvidencePacket separate.
4. Add instruction that thread/advisory memory cannot be cited.
5. Ensure citation binding only accepts current evidence markers.
6. Add adversarial tests where thread context contains fake citations or unsupported claims.

Done when prior generated content cannot become support merely through prompt inclusion.

### Phase H — Pipeline Studio integration

1. Register thread-context/contextualization strategies.
2. Add typed input/output ports.
3. Add them to the fixed Research pipeline shape.
4. Add stage config schemas/descriptions/i18n.
5. Surface effective settings and trace data in Pipeline Studio.
6. Keep changed arbitrary Research bindings inspect-only.
7. Regenerate pipeline catalog fixture.
8. Add pipeline contract/workflow tests.

Done when admins can understand/configure the computational context policy without changing thread authority or weakening evidence gates.

### Phase I — Research Library migration

1. Replace flat saved-response list presentation with thread list.
2. Open a thread into the conversation workspace.
3. Preserve per-turn audit/result detail.
4. Preserve grading/rerun access with clarified semantics.
5. Ensure legacy records appear as singleton threads.
6. Update search/filter/pagination and URL state.
7. Add migration and compatibility tests.

Done when no saved historical Research answer disappears and the primary library object is the thread.

### Phase J — documentation, cleanup, validation

1. Update current-state docs.
2. Remove obsolete flat-response assumptions from UI/domain code.
3. Decompose any files pushed beyond readable size.
4. Run formatters and static checks.
5. Run backend tests.
6. Run frontend unit/type/build/Storybook.
7. Run relevant Playwright/axe tests in CI/approved environment.
8. Verify Docker build if release-readiness is being claimed.

## 23. Test plan

### 23.1 Backend unit tests

Add focused tests for:

- create/list/get/rename/delete thread;
- owner isolation;
- append turn ordering;
- duplicate idempotency key;
- one active turn per thread if adopted;
- job linkage;
- completion linkage;
- failure/cancel/retry;
- legacy singleton materialization;
- cache loss does not destroy thread authority;
- deletion does not remove canonical provenance;
- context selection immediate previous turn;
- semantic older-turn selection;
- context budget;
- failed turn excluded;
- cross-thread turn never selected;
- original question preserved;
- derived query persisted;
- contextualization fallback;
- advisory context never becomes evidence;
- fake evidence markers in thread context do not bind;
- prior response memory remains separate;
- current evidence wins over conflicting prior answer;
- Research pipeline trace identifies selected context without copying full content.

### 23.2 Pipeline tests

Add/extend tests for:

- strategy contracts declare typed ports;
- thread_context cannot feed evidence/provenance-gate input;
- generation may receive thread_context and evidence through distinct ports;
- fixed built-in Research pipeline compiles/runs;
- existing first-turn output path is unchanged when no thread context exists;
- Research remains inspect-only for changed bindings unless separately migrated;
- config precedence Pipeline Studio → Settings → run remains correct.

### 23.3 Frontend unit tests

Cover:

- empty Research/new thread;
- first submission creates thread;
- follow-up stays in same thread;
- thread switch restores correct turns;
- active job blocks same-thread follow-up as designed;
- different thread remains usable;
- streamed draft appears in correct turn;
- final result replaces draft;
- failed turn retry;
- thread rename/archive/delete;
- evidence belongs to the correct turn;
- Back/Forward thread URL restoration;
- progressive loading does not blank existing conversation;
- legacy singleton thread rendering.

### 23.4 Accessibility/E2E

Cover keyboard-only:

- create thread;
- submit first question;
- submit follow-up;
- move between threads;
- open evidence from an older turn;
- retry failed turn;
- rename/delete dialogs.

Run axe on:

- empty Research;
- active generation;
- completed multi-turn thread;
- Research Library thread list;
- thread detail;
- dark/light modes.

### 23.5 Migration tests

Create fixtures representing:

- legacy response cache only;
- partially materialized singleton thread;
- normal new multi-turn thread;
- missing cache response with surviving thread linkage;
- restored backup.

Verify idempotency across restart/restore.

## 24. Acceptance criteria

The feature is complete only when all of the following are true:

1. A user can ask an initial Research question using essentially the current composer UX.
2. The completed answer remains visible and the user can ask a follow-up in the same thread.
3. The follow-up uses explicit prior thread context.
4. The system preserves the exact original follow-up wording and any derived standalone query.
5. Each answer remains a separate ResearchRun with its own evidence/provenance.
6. Prior generated answers are never treated as evidence merely because they are thread context.
7. Citations/support bind only to current resolved evidence.
8. Thread context, prior-response memory, and prior-claim memory are independently identifiable in audit state.
9. Existing saved one-off responses remain accessible as singleton threads.
10. Research Library is thread-oriented without losing per-run details, grades, evidence, rerun, or provenance.
11. Thread authority survives response-cache rebuild/loss according to the documented storage contract.
12. Authorization prevents cross-user thread/context access.
13. Pipeline Studio exposes context computation without owning thread domain state.
14. Research free-form rewiring is not falsely marked executable.
15. First-turn Research regression tests remain green.
16. EN/FR localization parity passes.
17. WCAG 2.2 AA coverage passes for new surfaces.
18. Backend, frontend unit/type/build, Storybook, and relevant CI suites pass.
19. Current docs and requirements match implemented behavior.
20. No implementation path weakens provenance, source binding, reviewer authority, or cELF traceability.

## 25. Explicit non-goals for v1

Do not expand scope to:

- arbitrary tree/branch UI;
- collaborative multi-user threads;
- editing historical turns in place;
- using thread history as a new corpus/vector collection;
- treating model-generated conversation summaries as authoritative state;
- globally enabling arbitrary Research pipeline rewiring;
- replacing current response/claim memory;
- replacing the response cache;
- changing canonical corpus/evidence semantics;
- introducing cloud-only dependencies.

These can be future work once the linear threaded foundation is stable.

## 26. Implementation cautions for the agent

- Verify the current branch before every major phase; this area is under active development.
- Preserve unrelated changes and concurrent agents' work.
- Prefer domain/service modules over adding more logic to `ResearchView.vue`, `rag.py`, or `job_rag.py`.
- Keep deterministic code responsible for IDs, ownership, ordering, citation resolution, provenance, and evidence eligibility.
- Never submit browser-supplied historical answer text as trusted thread context.
- Do not create an extra default LLM call solely for thread titles.
- Do not silently summarize/truncate away the immediately preceding turn.
- Do not let context budget steal from the current EvidencePacket budget.
- Do not store full prompts/answers in Pipeline Studio traces.
- Do not make a prior answer citable because it contains citation-looking text.
- Do not alter `PurposeAdapter.honours_bindings` for Research without a separate verified resolved-wiring migration.
- Regenerate generated pipeline fixtures rather than editing them manually.
- Keep source files documented/readable and decompose monoliths as touched.
- Add comments where context/evidence separation or retry/idempotency logic is non-obvious.
- Update current-state documentation after behavior lands; release notes wait for the release cut.
