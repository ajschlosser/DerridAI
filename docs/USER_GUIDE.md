# DerridAI User Guide

Feature reference for the current release. See the [README](../README.md) for installation and [release notes](notes/) for per-version changes. The sign-in screen, the account menu, Settings → Workspace → About DerridAI, and the browser tab title show the release version. The git commit that built this instance is shown on sign-in and to administrators.

## Users and roles

DerridAI uses built-in local authentication backed by SQLite (`AUTH_DB_PATH`, default `/data/.home/derridai-auth.sqlite3`). There are no packaged default credentials. On the first browser launch, DerridAI asks you to create the first administrator account. Administrators then manage accounts from **System → Users** and what each role can do from **System → Roles & permissions**. Settings → Security also links to both pages.

Two built-in roles ship with the application:

- **Administrator** — full access. Administrator permissions are locked so administrative control cannot be removed by accident.
- **Researcher** — the default non-admin role. It can use Research, researcher-safe corpus browsing and search, annotations, and appearance settings. The API enforces the same boundary as the UI: corpus mutation, database management, and export endpoints are rejected, RAG jobs are scoped to their owner, and researcher sessions cannot open administrative routes.

Administrators can create additional **custom roles**. A custom role starts from Researcher (or another non-admin role) and then enables or disables individual researcher-safe pages and features. Administration capabilities — Users, Roles, Languages, LLM profiles, loaded-record management, PDF tools, the Response Library, corpus mutation, and similar — cannot be granted to any non-admin role. Custom roles cannot be deleted while accounts still use them; reassign those users first.

Role capabilities are enforced by both navigation and the API. Unsaved permission changes stay visible until you save, and leaving the page or switching roles asks for confirmation.

Researcher-visible corpus text is transformed on the API before it is returned to the browser. `text` is passed through a dependency-free Edmundson-style extractive summarizer with values from `topics`, `concepts`, and `persons` treated as bonus terms. Summaries contain at most 2–3 selected sentence extracts joined by ` [...] ` and respect `RESEARCHER_TEXT_MAX_CHARS` (default `1600`). Text-valued entries inside the record `updates` audit history are sanitized by the same policy. The full corpus text remains available internally to the RAG pipeline for retrieval/generation, but is not exposed in researcher job results or read-only corpus search.

### Sign-in protection

Repeated failed sign-ins lock that username for a fixed period (`AUTH_LOGIN_MAX_FAILURES`, default `5`; `AUTH_LOGIN_LOCKOUT_SECONDS`, default `300`). The counter is stored in the authentication database, is keyed by the case-folded username, and applies equally to usernames that do not exist, so the response never reveals whether an account exists. A locked username receives HTTP 429 with a `Retry-After` header, and the sign-in form says how many minutes to wait; this response is identical for existing and unknown usernames, and the correct password is also refused until the lock expires. A successful sign-in clears the counter. The lock is per username, not per IP address, so someone who knows a username can lock that account out for the lockout period.

Session cookies are `HttpOnly` and `SameSite=Lax`. Set `SESSION_COOKIE_SECURE=true` only when browsers reach DerridAI through an HTTPS reverse proxy; leave it `false` (the default) for plain-HTTP local or Docker use, or browsers will not send the cookie.

Browser workspace persistence is isolated for researcher accounts so a researcher using the same browser profile does not inherit an administrator's loaded JSONL files, provider credentials, or other IndexedDB workspace state. Full backups include the logical user database (roles and password hashes, but not active session tokens), so backup ZIPs should be treated as credential-sensitive.

Researcher-authored text (queries, notes, tags, and filters) is checked against a per-locale forbidden-term policy. Those terms are not shipped in the application source. After the first administrator account exists, generate a policy for each built-in locale from **System → Languages** using a provider profile. Installing a new interface language generates a policy as part of that job. Until at least one locale has a ready policy, the API rejects researcher-authored text. Enforcement uses the union of every generated locale list, so English and French (or any later locale) are checked together. Administrators can review, edit, and regenerate the stored terms; researcher sessions receive only hashed terms for immediate browser feedback.

The **Languages** dictionary editor groups keys by their dotted namespace, so administrators can work category by category instead of scanning the complete dictionary. The editor can export the full dictionary or the selected category as JSON, and can import a validated JSON dictionary for review before saving. Researcher text-policy terms are intentionally hidden until the administrator explicitly expands the sensitive-terms section.

A policy is generated **in the language it is for**. The request names the installed language (for example "Français (fr)") and asks for terms in six categories: vulgarities, sexual insults, racial and ethnic slurs, religious slurs, homophobic and transphobic slurs, and ableist slurs, at least three each. A second, narrower question then audits every candidate ("is this a word of this language?"). Terms that also appear in another installed language's policy must be affirmatively confirmed, since that overlap is the usual sign of English leaking into another language. Rejected terms are removed, and only the categories still short are requested again (up to three rounds), with the rejected terms listed so the model does not repeat them. Wrong-language terms are never saved. If the model still cannot fill a category, the policy is saved with a "Coverage is incomplete for: …" note so you can add terms yourself; if fewer than eight acceptable terms exist, generation fails with an explanation. The card shows how many attempts were needed and how many terms the language check removed. The check uses the same model, so it reduces the problem rather than eliminating it; review a generated list before relying on it.

## Dashboard

Dashboard shows:

- loaded records
- distinct works
- records currently needing review
- loaded JSONL files
- ChromaDB collection count
- total records across databases
- tracked changes
- per-database record count, role, language tags, and embedding model
- top topics, persons, works referenced, speakers, and position holders
- ten most recent audited changes
- background LLM, RAG, and Chroma upsert operations

Dashboard charts include legends, graded horizontal axes/gridlines, and date/year labels for:

- records loaded over the last 30 days
- audit changes over the last 30 days
- LLM review activity over the last 30 days
- records needing review over the last 30 days
- top five works with records needing review over the last 30 days
- RAG pipeline runs over the last 30 days, split between Ollama and FreeLLM/OpenAI-compatible providers
- records by publication year
- works as a percentage of total loaded records

The `needs_review` historical chart reconstructs prior state from the current record plus audited `needs_review` changes when that history exists.

## Background operations

Background operations are managed from Dashboard and also appear in a floating operations dock.

The dock appears only while there is something to show. It sits at the bottom-center of the page; drag it anywhere, and double-click the handle to recenter it. Collapse it to a status pill, or expand it to cancel work, open a result, or dismiss a finished item. Dismissing a finished operation — or using **Clear finished** on Dashboard or in the dock — removes it from both surfaces. While the dock is shown, the page keeps extra scroll room beneath the content so it does not permanently cover controls. Progress for a PDF corpus build is shown as "N% overall" because its overall progress blends several stages and has no meaningful item count. The Corpus Builder's metadata card shows its real count as "settled / total tasks".

### The Operations panel

The Dashboard's **Background operations** panel groups work by what needs you:

- **Needs attention**: failed or blocked operations, and finished ones whose results still await a decision. A failure shows what went wrong right on the row.
- **In progress**: running and queued operations, with a progress bar, elapsed time, and an estimated time remaining when the rate is steady (not shown for PDF corpus builds, whose progress blends several stages).
- **History**: everything else, grouped by day and capped to the most recent few; **Show all** reveals the rest.

The filter chips (**All**, **Running**, **Needs attention**, **Finished**) show live counts and narrow the list. Each row offers one primary action for its outcome (**Open result**, **Open corpus build**, **Review results**), plus **Details** and **Cancel** or **Remove**.

**Remove** and **Clear finished** are undoable instead of asking for confirmation: the rows disappear at once, an **Undo** button stays for a few seconds, and the deletion is only sent to the server afterwards (or immediately if you leave the page). **Clear finished** never removes running operations.

The panel is built for keyboard and screen-reader use: real headings and lists, a labelled progress bar per operation, buttons named after their row ("Cancel PDF corpus build"), status shown as text plus an icon, and one polite announcement when an operation completes, fails, or is cancelled. Updates never move keyboard focus. Motion follows the "reduce motion" system setting, and the panel adapts to high-contrast (forced colors) modes.

Supported operation types:

- LLM review
- Auto-improve
- PDF LLM tools
- RAG response grading
- RAG
- Chroma upsert

Each operation exposes:

- status: `queued`, `running`, `cancelling`, `completed`, `cancelled`, or `failed`
- provider/model or Chroma target
- progress
- current record or RAG stage
- elapsed/total time
- failure count
- request configuration with API keys omitted
- timestamped operation/event timeline
- result summary

The expanded dock shows a compact row for each operation: status, progress, the current stage, and the next action. Full request details, event timelines, and result summaries remain on Dashboard and in the operation inspector.

The dock can be dragged anywhere. When it is expanded from a spot near the right or bottom edge, it slides back so the whole panel stays on screen; collapsing it returns it to where you left it.

### Cancellation semantics

Cancellation is deliberately explicit:

- queued jobs cancel immediately;
- background Ollama/OpenAI-compatible LLM generations are streamed so closing the stream can interrupt the current generation;
- RAG model-generation calls are likewise interruptible, while vector retrieval/reranking stops at the next safe pipeline checkpoint;
- Chroma upserts stop after the currently executing batch returns.

While an in-flight call or batch is winding down, status is shown as `cancelling` rather than pretending cancellation has already completed.

Background job state is process-local and does not survive an API-container restart.

## LLM review run modes

Every review dialog exposes three run modes.

### Interactive foreground

This is the default mode.

- records are reviewed sequentially in the open dialog;
- completed record cards expand as soon as proposals arrive;
- current/proposed values and rationale are immediately visible;
- reviewers can select arbitrary proposals;
- reviewers can accept all, apply selected, or mark reviewed without accepting proposals.

### Background review

The review is submitted to the API job manager and the dialog closes. The user can continue working elsewhere in the application.

### Background Auto-improve

The selected set is processed in the background and presented at completion as one flat change list rather than a growing stack of proposal cards.

Successful review application or explicit **Mark reviewed only** clears:

```json
{
  "needs_review": false,
  "review_reason": null
}
```

when applicable. The changes are recorded with `source: "llm_review"`.

## Background LLM result review

**Review results** now handles changed and unchanged records separately.

Changed values use word-level red/green diffing:

- removed/current material is red and struck through;
- inserted/proposed material is green;
- stale records retain a separate warning state rather than making the entire diff yellow.

If a model proposes no changes, the dialog shows a dedicated successful no-change state instead of an empty six-column table. Unchanged records can be expanded and previewed individually, and they can still be marked reviewed.

**Preview record** exposes:

- record ID/work/pages/citation
- speaker / position holder / target / stance
- discourse/proposition metadata
- quotation provenance
- topics/concepts/persons/works referenced
- language fields
- complete record text
- proposals and rationales
- recent audit history
- direct navigation to full Record view

## Provider configuration

Configuration supports any number of named LLM provider profiles. Each profile is independently saved and can be selected from LLM Review, RAG Research, and RAG response grading.

Provider profiles can be added/removed without overwriting other endpoints.

### Ollama profile fields

- profile name
- endpoint
- model
- `num_ctx`
- metadata output limit
- OCR/text output limit
- think mode
- temperature
- `top_k`
- `top_p`
- `min_p`
- repeat penalty
- seed
- mirostat / mirostat eta / mirostat tau
- `keep_alive`
- advanced Ollama options JSON
- model test/discovery and warmup

### FreeLLM / OpenAI-compatible profile fields

- profile name
- endpoint
- API key
- auto/discovered/manual model selection
- model-kind filter
- model ID
- max output tokens
- temperature
- `top_p`
- seed
- advanced OpenAI-compatible options JSON
- model discovery/test and warmup

One provider profile is designated as the default, but run dialogs can switch profiles before launch. **Save provider profiles** stays locked at the bottom of the page and writes every profile at once. Cards can be collapsed after that save so the registry is easier to scan. Use **Set fields across profiles** to copy context tokens, output limits, sampling, and other shared parameters onto every profile or a selection, then save.

Dashboard LLM readiness reports every configured profile rather than only the most recently used endpoint.

Model-kind filters remain a UI discovery aid; the backend still sends a standard OpenAI-compatible `model` identifier.

## Startup model warmup

After workspace restoration and API health checks, the configured default model receives a minimal warmup request. Ollama warmup respects `keep_alive`.

## JSONL workspace

Multiple JSONL files remain open as a local working set and persist through browser IndexedDB, including:

- unsaved edits
- active file/view/record
- searches and filters
- table-column choices
- review selection
- LLM/RAG configuration
- Chroma synchronization receipts
- sidebar state

Persistence is browser-origin-specific.

**Records** is a Vue-native workspace at **Tools → Records**. The table keeps DB status, work, pages, review flags, and extracted text, with citation and evidence actions that stay fully labeled. Text search, column filters, page size, collection choice, and bulk LLM/upsert actions remain; overflow tools sit in **More** so the primary scan line stays clear. Loaded JSONL files appear in a local-file rail on this page, with origin (imported, subset, merge, split by work, or from a collection) and whether the file has been edited since it was loaded. Administrators open, merge, subset, export, and close files from that rail, or from the empty state. Researcher accounts do not use this page.

- **Columns** chooses, orders and sizes the table's columns. Each shown column has a width as a percentage of the table; the widths always total 100%, so widening one column narrows the others in proportion (no column goes below 5%). **Even widths** splits the space equally, and **Reset defaults** restores the default columns and widths. Search uses the same column dialog for choosing and ordering columns, including loaded-record results. Advanced Search filters are a condition builder: each row is field, operator, and value, joined with Where / And. Fields come from the metadata schema associated with the selected corpus, or from a schema you choose if none is associated.
- **Comfortable** rows show the full extracted text. **Compact** rows are tighter, narrow the text column, and show the text on one line; where it is cut off, **Expand** shows the rest of that row's text.
- **Get Citation** copies an inline or full citation. The notification quotes exactly what was copied. The menu closes on a choice, on Escape, or on a click elsewhere.
- **Copy view link** copies a link that reopens this table as shown: file name, search, column filters, sort, page and columns. JSONL records stay in this browser, so whoever opens the link is asked for the same file. The notification shows the copied link.

### Create a JSONL subset

**Create subset** in the local-file rail makes a new local JSONL file from the records that match a filter. The source file is not changed, and each copied record keeps its record ID and audit history. The source can be the active file, all loaded files, or one file; the match count updates as you edit the filter.

A filter is a list of conditions (field, comparison, value) joined by AND or OR, where AND binds before OR. A group is evaluated as one condition, like parentheses, and matches when any or all of its conditions match. **Case-sensitive** is off by default, so `derrida` also matches `Derrida`; turn it on to require the same capitals. It applies to the equals, contains, list and regular-expression comparisons. The new file records the filter, whether matching was case-sensitive, and which file it came from.

Saved filter profiles are kept in this browser. **Save current…** names the filter (saving under an existing name updates that profile). **Export all profiles** saves them as one JSON file; **Import profiles** reads such a file, replaces profiles with the same name, and adds the rest. A profile with a condition that cannot be read is skipped whole rather than imported with the condition dropped, and the notification says how many were added, replaced or skipped.

### Merge files

Users can merge all loaded JSONL files or any subset. Selected source files are replaced in the workspace by the merged file; unselected files remain. Source files on disk are not deleted.

## Record audit history

The record inspector **Configure fields** control sets which fields appear in Overview, Provenance, and Indexing, their order, and category headings. The layout is stored in this browser.

Record changes use the flat `updates` array.

Example:

```json
{
  "field_name": "quoted_speaker",
  "old_value": [],
  "new_value": ["Emmanuel Levinas"],
  "timestamp": "2026-09-10T20:00:00.000Z",
  "source": "llm_review",
  "batch_id": "...",
  "model": "gemma4:e2b",
  "reason": "..."
}
```

Users can clear `updates` for one record or for every loaded record. Clearing history is intentionally destructive and does not create another update-history entry.

## Work-level metadata editing

Works view includes **Edit metadata**.

The editor aggregates every loaded record associated with the selected work and allows the user to choose exactly which work-level fields should be propagated across the set.

Supported/common fields include:

- work/title
- document title / short title / original title
- document author
- edition
- year / publication year
- publisher
- publication place
- translator
- document language
- original language
- translation flag
- canonical work ID
- ISBN
- full citation
- additional detected `document_*`, `publication_*`, and canonical work metadata fields

**Populate metadata with LLM** and **Populate all metadata with LLM** are source-aware. A work containing multiple
source types is partitioned before lookup so book records are not matched as though they were audio, image, video, or
web records. Books use Open Library, Google Books, and Crossref; journal articles, chapters, and theses use scholarly
metadata services such as Crossref and OpenAlex; webpages use declared page metadata; and unsupported media types retain
their source-derived metadata rather than being sent to a book catalogue. Only fields applicable to the source type are
proposed. The selected provider profile chooses the LLM used for candidate matching, and every proposal remains
reviewable before it is copied across the scoped records.

Mixed values are visibly identified. Array/object values are edited as JSON. Every applied field change is recorded in each associated record's `updates` history with `source: "work_metadata"`.

Because the affected record fingerprints change, records previously synchronized to Chroma become `Pending` until the next upsert.

## ChromaDB

Chroma is derived data. The corpus JSONL/PDF pipeline is the source of truth; collections can be deleted and rebuilt. DerridAI can use Chroma in three ways, analogous to how Ollama is either a host process or the compose service, plus the extra local-filesystem mode that is still the default:

| Mode | When to use | How |
| --- | --- | --- |
| **Local filesystem** (`CHROMA_MODE=embedded`, default) | Local-first install | `PersistentClient` on `CHROMA_PATH` (`./data/chroma`) |
| **Bundled Chroma container** | Process isolation, or sharing the store with other tools | `docker compose --profile chroma up -d`, then `CHROMA_MODE=http` and `CHROMA_BASE_URL=http://chroma:8000` |
| **Running Chroma server** | A server already on the host or in the lab | `CHROMA_MODE=http` and `CHROMA_BASE_URL=http://host.docker.internal:8001` (or the lab URL) |

Vector Stores → Connection settings can probe and switch backends at runtime. Switching does **not** move collections. Do not point embedded storage and a Chroma server at the same directory (one writer per path). NUKE in HTTP mode deletes collections on that server; it does not empty a leftover local `chroma` folder. Backups always go through the client API and preserve embeddings.

Default embeddings:

```text
Provider: Ollama
Model:    bge-m3:latest
```

Collections support Ollama embeddings, Chroma default embeddings, and precomputed vectors. Embedding configuration can change while a collection is empty and is locked once records exist.

## English / French vector-store model

Chroma language collections use only:

```text
en
fr
```

The UI does not create separate US/UK English databases. Regional source metadata such as `en-US`, `en-GB`, `American English`, and `British English` all route to `en`. French variants route to `fr`.

Collection roles:

- `primary`
- `general`
- `language`

Typical collections:

```text
chroma_primary
chroma_primary_en
chroma_primary_fr
```

Language-specific collections cannot recursively generate more language collections.

## Primary → language synchronization

If `chroma_primary_en` and/or `chroma_primary_fr` were derived from a primary collection, subsequent writes to that primary collection automatically synchronize the derivatives.

For each primary upsert:

1. the primary record is written and embedded;
2. its stored primary embedding is reused for matching language collections;
3. `document_language` / `document_languages` determines whether the record belongs in `en`, `fr`, or both;
4. records are removed from a derived language collection when their language metadata no longer matches;
5. the API reports which language stores were synchronized;
6. browser synchronization receipts are updated for both the primary and mirrored collections.

Direct primary-collection record edits and deletes also synchronize derived language collections.

## Chroma upserts as background operations

Upserting records no longer blocks the main UI.

An upsert creates a background job with:

- target collection
- record count
- batch progress
- current record/batch
- elapsed time
- derived-language mirror counts
- cancellation
- timestamped event history

The dashboard and operations dock update while batches commit. Synchronization receipts are applied incrementally, so local records can change from `Pending` to `Synced` before the entire job has finished.

If a local record changes after its batch was written, its stored fingerprint remains the older one and the UI correctly returns that record to `Pending`.

## Pending upsert queue

The queue tracks records whose current fingerprint differs from their last successful upsert.

Users can:

- inspect audited changes since the prior upsert
- inspect old/new values
- select arbitrary records
- batch upsert
- remove the current fingerprint from the queue

Suppressing a queue entry applies only to that record version; a later edit re-queues it.

## JSONL ↔ ChromaDB round trip

Into ChromaDB:

- active JSONL
- all loaded JSONL
- selected records
- Record/Works/List/search workflows
- pending queue

Back to JSONL:

- load/download entire collection
- load/download one work
- load current database page

Export removes Chroma's internal `_chroma_id` field.

## Corpus Builder source formats

Choose the source format before choosing a file. PDF and image sources offer OCR;
PDF/image pagination controls are unavailable for text, Word, RTF, Gutenberg, and
audio sources. The review pane shows source text, the source image, or audio
playback with timed speaker spans. Audio citations use time ranges and available
speaker labels, never synthetic page numbers. Correcting a transcript creates a
record revision and retains the original transcription.

For PDF and image sources, choose an OCR strategy before selecting the source:
use embedded text when available, prefer OCR for difficult scans, or always OCR.
The difficult-scan choice uses the existing intermediate OCR threshold; always
OCR forces OCR for every page.

Ingestion rejects malformed or unsupported files and embedded Word/RTF active
content; it never runs document macros, fields, or linked objects. Non-PDF files
are limited to 32 MiB (RTF to 8 MiB), Word archives to 2,048 entries and 64 MiB
expanded, individual XML parts to 8 MiB, and expansion ratios to 200:1. Images
must be single-frame PNG or JPEG, at most 20 million pixels. Extractor contract,
Python/library versions, and source digest are saved with the asset.

Audio is optional: the Docker API image includes FFmpeg (including `ffprobe`);
local/non-Docker API environments must install FFmpeg separately. Configure
`OPENAI_API_KEY` for full-file Whisper transcription. `whisperx` and its model
runtime remain optional and must be installed separately if speaker diarization
is required; configure `HF_TOKEN` where the diarization model requires access.
Files must be at most 24 MiB and
four hours. Unsupported codecs, probe timeouts, failed transcription, empty
transcripts, and missing/invalid timestamps stop ingestion. Diarization failure
preserves the transcript with a visible warning and no invented speaker.
The model, provider endpoint, duration, and diarization status are retained.

Gutenberg search lists separate eBook IDs and languages. Choose an exact entry;
imports retain its ID, edition label, catalog metadata, exact download URL,
encoding, retrieval time, and original-byte digest. Missing text, mismatched
identity, redirects, timeouts, and undecodable content fail visibly. The importer
does not guess another download or substitute another edition. Two editions
with identical text remain distinct assets.

## Corpus Builder metadata population

The LLM returns each metadata field (or `null` when unsupported) together with a per-field confidence. The response schema requires every field, so a model cannot return confidence assessments without values.

- Every schema-valid non-empty LLM value is populated into the record so the reviewer can see it; population does **not** imply verification.
- `autofilled=true` is reserved for the calibrated autofill policy (90% blended confidence by default, valid cited evidence, and no suspension from poor reviewer precision). Values that do not pass calibrated autofill remain **pending review**, even when they exceed the ordinary metadata-confidence floor.
- Deterministic values (for example reviewer-defined document structure) stay selected; the LLM check either corroborates them or records a disagreement for review.
- If the model reports more than the threshold in confidence for a speaker, position holder, target, stance, or proposition status but returns **no value**, the field is marked unresolved with reason `no_value_returned` rather than shown as an inference. Use **No supported value** to confirm a genuine absence.
- Reviewer-confirmed values are never overwritten by later enrichment.
- Confirmed metadata decisions are also stored in a rebuildable, derived semantic
  reviewer-memory collection. Later enrichment may retrieve diverse similar
  examples with similarity/MMR, filtered by field and schema version, as
  advisory prompt context. The current Record's evidence remains authoritative;
  semantic memory never auto-applies a value or replaces the exact text-hash
  cache.
- After a pass finishes, **Run another pass** is available in the review workspace immediately. You do not need to accept every record first. The next pass is given what the last pass inferred (working conventions on this build) and any reviewer decisions already made.
- Enrichment is persisted record by record, not only at the end. The live operation reports the selected provider, model, pass, and processed-record count; a later run can target all records, an accepted/pending scope, or an explicit subset.
- Each record keeps activity telemetry for human opens and saves, LLM reviews, enrichment passes, and the last provider/model that touched it. This is audit information, not a replacement for field-level provenance.
- When a PDF is loaded, the builder scores each page for **illegibility** (0% = still looks like words in a writing system; 100% = unreadable) and, when a page has an embedded scan, **raster DPI**. A warning dialog appears if too much of the source looks unusable; afterward the finding lives as a clickable warning icon on affected Record Review rows. Names, bilingual pages, and coinages are allowed; interior punctuation, letter–digit soup, and scans below about 150 DPI are not. A build setting (default 45%) counts pages and Records at or above that noise as unusable. Those Records feed the existing **>10%** source-quality warning, skip metadata enrichment, and appear in the source-problem queue. An optional LLM second-read runs **after you start a build** and may only **raise** the deterministic score.
- Pixelation is measured from the embedded image’s pixel size versus the rectangle it occupies on the page. Native vector/text pages with no image are not scored as scans.
- The Source PDF step reports extracted **SourceUnits** (addressable PDF/OCR layout units), not Records. `OCR page(s)` counts pages where OCR was used; zero means the native PDF text layer was used. Image-only pages remain visible as source-quality findings instead of disappearing from the 10% check.
- When embedded PDF metadata contains an author, the builder carries it forward as a deterministic, reviewable document-author assertion. It is not silently treated as an LLM inference.
- **Clean all Record text before enrichment** is deterministic preprocessing. **Use LLM to touch-up text as part of enrichment** creates a conservative, reviewable proposal for extraction errata, diacritics, formatting, quotations, and line breaks. The proposal does not change authoritative reviewed text until a person reviews and saves it.
- Metadata schemas are defined at **System → Metadata schemas** (administrators only). Corpus Builder step 5 still chooses which schema a build copies and can open the editor in a dialog. Schemas are semantic-versioned independently of the application and corpus contracts. New schemas start at `1.0.0`; unchanged saves retain their version; adding fields increments the minor version, removing fields increments the major version, and changing existing definitions increments the patch version.
- **Run-specific field guidance** is configured beside schema selection and is saved only with that build. For any field, add an instruction and/or names, titles, concepts, or variants to look for. Exact phrase matches are shown as review cues and passed to the corresponding field group's LLM task; they do not change the schema, restrict the allowed values, or count as evidence that the value applies. The model must still use this record's context and bind evidence where the schema requires it.

Records enriched before this behavior existed are not changed automatically. **Retry metadata** skips completed metadata families by design, so it will not repopulate them. To repopulate an affected record, use **Run metadata enrichment again** (or **Rerun** on a family) and choose **Discourse / attribution**; this clears only LLM-owned values in that family and keeps reviewer-owned, deterministic, and inherited values. Rebuilding also works.

## Corpus Builder review workspace

Once a build has records, the review workspace fills the screen under the top bar: the queue on the left, the record in the middle, and the details (metadata, evidence, source) on the right. Each pane scrolls on its own, and the record's title and its decisions stay in view while you read.

- **Deciding.** The bar under the record is one row: **Skip**, **Reject & next**, and **Accept & next**. If required metadata is unresolved, a note above the bar says which fields, and **Accept & next** stays unavailable until you confirm them.
- **More actions** (the ⋯ button at the left of that bar) holds **Combine with previous record**, **Combine with next record**, **Slice record** and **Preview JSONL**. An action that is not available stays in the list and says why, for example that there is no previous record to combine with.
- **Slicing.** Cursor mode moves text to one neighboring Record. Selecting a chunk and choosing **Keep selected** leaves the selection in the current Record, moves the preceding text to the previous Record, and moves the following text to the next Record. Affected Records retain slice lineage, reopen metadata review, and are re-enqueued for enrichment.
- **Undo** and **Redo** are at the top of the record, next to **Focus view**.
- **The queue** shows each record's state as an icon and a name (Accepted, Rejected, Reviewable, Metadata, Topology, Source problem). Above it, the queue tabs filter by state, **Bulk actions** holds **Bulk edit metadata** and **Reject selected**, and **Accept clean** accepts every reviewable record at once.
- **Resizing.** Drag the divider between panes, or focus it and use the arrow keys (Shift for bigger steps, Home and End for the limits); double-click to reset. Each width is remembered in this browser.
- **Smaller screens.** On a laptop the details sit under the queue and record. On a phone the workspace is an ordinary page.

## PDF Explorer

PDF Explorer reads embedded PDF title/author metadata when available and presents the loaded PDF as a source → work → record relationship rather than as an isolated document viewer.

It supports:

- PDF.js rendering with browser fallback
- page rotation in 90° increments
- current-page extraction
- all-text extraction
- API/PyMuPDF extraction fallback
- monospace extracted text
- LLM cleanup of the current extracted page without paraphrasing it
- LLM-assisted draft-record creation from the current page
- explicit review/edit of the generated draft before saving
- saving a draft to any loaded JSONL file, any Chroma collection, or both
- LLM-assisted page-to-record matching against loaded JSONL records
- searchable record autocomplete
- multiple PDF pages linked to one record
- unlink one page or every PDF link from a record
- current-page linked records
- every record linked anywhere in the loaded PDF
- direct PDF page ↔ record navigation
- embedded PDF title/author context when available

LLM page-to-record matching pre-ranks candidate records by PDF title/work overlap, page ranges, existing PDF links, and page/record text overlap before asking the selected provider to adjudicate the best match.

Image-only PDFs still require an external OCR/vision workflow; DerridAI does not fabricate text when a page has no extractable text layer.

## Empty states and shortcuts

When there is nothing to search (no loaded JSONL records and no corpus database), **Search** and **Research** explain that on the page instead of redirecting you. Administrators see a **Create a collection** button; researchers are told to ask an administrator. The command search in the top bar focuses with `Ctrl K` (`⌘K` on Apple platforms). **Help** opens a short orientation dialog (not Response Library). JSONL file actions for administrators live on **Records**. Interface language is a named control showing the language, not a flag. The account menu shows your translated role, Settings, and Sign out. On a narrow screen, language and help move into that account menu rather than disappearing. The sidebar's **More tools** section is open by default for administrators; if you close or open it yourself, DerridAI remembers your choice in this browser. The menu is complete as soon as you sign in, before the workspace has finished loading.

### Record review shortcuts

The record header keeps navigation available while the text or inspector is scrolled. In Record View and Focus Review, `Alt+Left` / `Alt+Right` moves to the previous or next record without moving the page. In Focus Review, `Escape` closes the review surface and `Ctrl+S` (`⌘S` on Apple platforms) saves reviewed text while the text editor is active. Shortcuts are ignored while typing in another editable control. The `?` control beside record actions lists the shortcuts available in the current surface.

## RAG Research

RAG runs as a background operation and exposes the pipeline itself rather than hiding it.

Visible stages:

1. Query decomposition
2. Vector retrieval
3. Deduplication / reciprocal-rank fusion
4. Reranking
5. Evidence packaging
6. Answer generation
7. Citation/source binding
8. Response cache write

### Pipeline Activity

Each active/recent RAG card shows:

- research prompt
- source collection
- provider/model
- English/French scope
- MMR/similarity routes
- `k`
- `fetch_k`
- MMR lambda
- RRF `k`
- rerank top N
- reranker
- generation context/output limits
- current stage
- current-stage detail
- stage rail
- start time
- elapsed time while active
- total time when finished
- cancellation
- Details/timeline
- Open result

### Retrieval controls

Per run:

- source collection
- `en` / `fr`
- MMR and/or similarity
- `k`
- `fetch_k`
- MMR lambda
- RRF `k`
- rerank top N
- reranker mode
- cross-encoder model
- query decomposition
- query-decomposition output limit
- response language
- maximum chars per evidence record
- total evidence-character budget
- citation binding
- Works Cited

Default cross encoder:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

If unavailable, reranking falls back to lexical/vector scoring.

### Language routing

RAG routes only `en` and `fr`.

If matching derived collections exist, they are used. Missing language derivatives fall back to the selected source collection, filter by `document_language(s)`, and retain separate English/French retrieval routes.

### Generation controls

RAG exposes provider-specific per-run generation parameters.

Ollama includes context, output tokens, thinking, temperature, top-k/top-p/min-p, repeat penalty, seed, mirostat, keep-alive, and advanced options.

FreeLLM/OpenAI-compatible includes model routing, model-kind filtering, output tokens, temperature, top-p, seed, and advanced options.

### RAG results

**Open result** shows:

- final source-bound answer
- raw evidence-tagged answer
- query decomposition
- retrieval diagnostics/routes
- selected collections
- warnings
- pipeline timings
- every reranked evidence record
- attribution/provenance metadata
- exact evidence text
- citations
- load evidence into a new JSONL file
- cached-response identifier
- **Re-run with parameters**, which repopulates RAG Research with the original run configuration so it can be modified before launch
- **Analyze & grade**, which asks the selected LLM provider to evaluate query relevance, source binding, claim traceability, attribution/source discrimination, claim/evidence fidelity, conceptual precision, coverage, interpretive usefulness, and overall quality

### Response Library

Every successfully completed RAG answer is written to the logical `_response_cache` Chroma collection as an eighth pipeline stage. The cache uses deterministic local vectors so writing a completed answer does not depend on Ollama or another embedding service being online.

The **Response Library** page provides:

- question/answer browsing
- search over cached questions
- provider/model/time/evidence-count context
- retained query decomposition and retrieval diagnostics
- retained evidence records
- persisted grades when a response has been analyzed
- re-run with the original parameters
- re-grade with any configured LLM provider

## Compare

Compare is a Vue-native two-column workspace at **Tools → Compare**. Each column can independently show a **library** record (loaded JSONL files for administrators, corpus-database summaries for researchers) or an **editable copy**. Use **Load into editor** to populate A or B from any existing record, then edit the JSON/JSONL without changing the source until you copy it elsewhere. **Copy A into B** makes a working duplicate. Field differences update as soon as both sides parse as a single JSON object. Audit `updates` history is excluded from the comparison. Researcher accounts cannot mutate corpus records from this page.

## Settings

Settings is a Vue-native control center at **System → Settings**. A contents rail (a collapsible **Contents** control on smaller screens) groups:

- **Workspace and appearance** — accent theme, light/dark/system color scheme, contrast, and **About DerridAI** (copyright and version; administrators also see the git commit). Theme choices are stored in this browser workspace, not on the server.
- **Language and accessibility** — interface language, applied immediately. Dictionary editing remains on **Languages**.
- **Research defaults** — response language for generated answers. Per-run generation still lives on **Research**.
- **Review and AI behavior** — default provider profile, review preset, and interactive vs background LLM review.
- **Providers and models** — readiness summary only; credentials and endpoints stay on **LLM Providers**.
- Record field definitions live on **System → Metadata schemas**, not in Settings. Corpus Builder still offers **Manage schemas…** as a shortcut to the same editor.
- **Vector stores and retrieval** — default embedding provider/model (browser-local) and RAG retrieval budgets, with advanced MMR/RRF options behind a disclosure. The current Chroma path is read-only here; change the backend on **Vector Stores**.
- **Security, users, and permissions** — links to **Users** and **Roles & permissions**.
- **System and operations** — backup/restore, viewer resets, desktop notifications, and NUKE.

Each group saves on its own. Unsaved changes warn before leaving the page. Search matches translated labels. Researcher accounts see appearance (when permitted), language, and research defaults. Administrative retrieval, providers, security, backup, and NUKE stay off that account.

## Configuration reset

Configuration includes:

- table-column reset
- sidebar expansion
- upsert suppression reset
- clear all record update histories
- Dashboard / Vector Stores / RAG navigation

### NUKE

Typing `NUKE` enables a full reset to a first-run install. It deletes:

1. every Chroma collection and the persistence files under the current Chroma path (the catalog itself is recreated empty);
2. authentication (users, sessions, lockouts, and custom roles), so the next load asks you to create the first administrator account;
3. provider profiles, annotations, installed-language edits, researcher text policies, and job history;
4. PDF corpus assets, builds, publications, and backup/restore temp directories;
5. browser IndexedDB workspace state and DerridAI `localStorage` keys.

Installed Ollama / embedding model files under `data/models` and `data/ollama` are not deleted.

## Dashboard additions in 0.9.0

Dashboard charts include graded axes and legends.

New time-series views include:

- **RAG pipeline runs over the last 30 days**
  - Ollama
  - FreeLLM / OpenAI-compatible
- **Top 5 works needing review over the last 30 days**
  - one line per work
  - works are ranked by the current number of records carrying `needs_review`
  - prior counts are reconstructed from audited `needs_review` transitions when available

Accepted RAG launches are retained in local browser workspace history for charting, independently of whether finished operation cards are later cleared from the API process.

### LLM readiness

The Dashboard LLM readiness card now shows:

- configured provider
- endpoint
- configured model
- endpoint reachability
- whether the selected model is confirmed available
- number of discovered models
- warmup state
- last warmup completion time and elapsed time
- per-provider maximum concurrent requests and current Ollama RAG activity where applicable
- model parameter size and quantization when the provider reports them
- endpoint/status errors

The card includes explicit **Refresh all** and independent per-provider warm controls.

## RAG concurrency

RAG scheduling is controlled by the selected **LLM provider profile**. Each profile exposes **Max concurrent requests** on the dedicated **LLM Providers** page. The limit applies independently to jobs using that profile, so one FreeLLM endpoint can run at a high concurrency while a local Ollama profile remains limited to one or two requests.

### FreeLLM / OpenAI-compatible

Each submitted RAG job receives its own daemon thread, but execution waits behind that profile's configurable concurrency gate. The default for newly created OpenAI-compatible / FreeLLM profiles is **32** concurrent requests, adjustable from **1–64**. This preserves high parallelism without forcing unrelated provider profiles through one shared global worker pool.

### Ollama

Ollama profiles default to **1** concurrent request because parallel local model contexts can consume substantial VRAM. Their selected profile limit is passed to the RAG scheduler's Ollama execution gate, and queued jobs remain visible with an explicit waiting-for-provider-slot state.

The legacy environment default:

```env
RAG_OLLAMA_MAX_CONCURRENT=1
```

still establishes the server's initial Ollama gate before browser provider-profile settings are applied.

## Full backup & restore

Configuration contains a **Backup & restore** section.

**Download full backup** creates one ZIP archive containing:

- every loaded JSONL file and unsaved browser-workspace record state
- record audit histories / `updates`
- UI preferences, table columns, filters, navigation state, and RAG question/run history
- all configured LLM provider profiles and their generation defaults
- provider API keys when they are present in the browser configuration
- retained finished LLM/RAG/upsert operation objects and LLM pending results
- the currently loaded PDF, if any
- every Chroma collection, its collection metadata/configuration when exposed by Chroma, documents, metadata, IDs, and the exact stored embedding vectors

Backups are blocked while background operations are active so the archive is internally consistent. Large archives are assembled under the host-mounted `./data` tree rather than inside the container overlay filesystem.

**Load from backup** validates the manifest and ZIP member paths before making changes. The API first creates a logical rollback snapshot of the current Chroma database; if Chroma restoration fails, the current vector database is restored from that rollback. After a successful server restore, the browser IndexedDB workspace and current PDF are replaced and the UI reloads.

**System Data** is the administrative surface for the logical `_response_cache`
and the durable application databases. The response cache remains a Chroma
system collection, while the database browser exposes tables and rows through a
backend-neutral contract; SQLite is the current adapter, not a UI-level
requirement. Sensitive credentials, password material, and session tokens are
redacted or protected from mutation. The former **Response Cache** route remains
available as a compatibility alias.
Chroma itself does not permit collection names beginning with `_`, so the
physical cache collection is `derridai_response_cache`.

Full backups can contain credentials. Treat them as sensitive files.

## Diagnostics

Linux/WSL:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

Manual checks:

```bash
docker compose ps
curl http://localhost:8181/healthz
curl http://localhost:8000/api/live
curl http://localhost:8000/api/health
```

If older releases created root-owned data:

```bash
./scripts/fix-data-permissions.sh
```

## Rebuild after upgrade

```bash
docker compose down
docker compose up -d --build
```

## Current limitations

- background-job state is process-local and does not survive API restart;
- browser workspace persistence is origin-specific;
- image-only PDFs do not receive built-in OCR;
- first use of a cross-encoder can require a model download;
- simultaneous independent writers to the same Chroma persistence path are unsupported;
- cancelling a Chroma upsert waits for the current batch to return;
- vector/reranker calls that do not expose a cancellable stream stop at the next pipeline checkpoint;
- clearing `updates` permanently removes that local audit history.
