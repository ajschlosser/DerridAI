# DerridAI User Guide

Feature reference for the current release. See the [README](../README.md) for installation and [release notes](notes/) for per-version changes. The sign-in screen, the account menu, Settings → Workspace → About DerridAI, and the browser tab title show the release version. The git commit that built this instance is shown on sign-in and to administrators.

## Users and roles

DerridAI uses built-in local authentication backed by SQLite (`AUTH_DB_PATH`, default `/data/.home/derridai-auth.sqlite3`). There are no packaged default credentials. On the first browser launch, DerridAI asks you to create the first administrator account. Administrators then manage accounts from **System → Users** and what each role can do from **System → Roles & permissions**. Settings → Security also links to both pages.

Two built-in roles ship with the application:

- **Administrator** — full access. Administrator permissions are locked so administrative control cannot be removed by accident.
- **Researcher** — the default non-admin role. It can use Research, researcher-safe corpus browsing and search, annotations, and appearance settings. The API enforces the same boundary as the UI: corpus mutation, database management, and export endpoints are rejected, RAG jobs are scoped to their owner, and researcher sessions cannot open administrative routes.

### Annotations

Annotations can target selected text, an entire Record, or an entire work. Selected-text annotations retain the quoted passage; Record and work annotations retain their durable target without requiring a quotation. From an annotation form, add comma-separated Record IDs to link the same discussion to additional records. Linked and work-scoped annotations appear in each applicable Record and in the global Annotations workspace without creating duplicate annotation identities.

Replies are stored as part of an annotation thread. Threads with replies start collapsed and can be expanded. Deleting a thread root preserves a visible deleted-root placeholder so the replies and discussion history remain understandable. Annotation visibility and linked-record access are enforced by the API for the selected corpus store.

Administrators can create additional **custom roles**. A custom role starts from Researcher (or another non-admin role) and then enables or disables individual researcher-safe pages and features. Administration capabilities — Users, Roles, Languages, LLM profiles, loaded-record management, PDF tools, the Response Library, corpus mutation, and similar — cannot be granted to any non-admin role. Custom roles cannot be deleted while accounts still use them; reassign those users first.

Role capabilities are enforced by both navigation and the API. Unsaved permission changes stay visible until you save, and leaving the page or switching roles asks for confirmation.

Researcher-visible corpus text is transformed on the API before it is returned to the browser. `text` is passed through a dependency-free Edmundson-style extractive summarizer with values from `topics`, `concepts`, and `persons` treated as bonus terms. Summaries contain at most 2–3 selected sentence extracts joined by `[...]` and respect `RESEARCHER_TEXT_MAX_CHARS` (default `1600`). Text-valued entries inside the record `updates` audit history are sanitized by the same policy. The full corpus text remains available internally to the RAG pipeline for retrieval/generation, but is not exposed in researcher job results or read-only corpus search.

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

## Corpus term map

This map is separate from the Record review **Semantic map** tab, which walks entities and relations inside a corpus build. The corpus term map draws concepts, topics, and persons that occur together in the corpus you can already see. It does not show record text. Drag the background to move the map, drag a term to reposition it, use the map controls to zoom, fit, or reset the layout, and drag the resize handle to change the map height. Arrow keys pan the map, plus and minus change the zoom, 0 resets the view, and Alt+Arrow nudges a focused term.

Open it from **Record view** or from **More tools → Semantic map**. Administrators can open it immediately. A new installation includes it for the Researcher role. On an installation that already has roles, turn on **Semantic map** under **Roles & permissions**. The placement control keeps the same map in one of four places:

- **Sidebar** — a panel beside the current page
- **Above the record** — a band on the record you are reading
- **Large dialog** — a wide overlay you can dismiss
- **Dedicated view** — the Semantic map page

The choice is remembered in this browser.

## Relationship-map controls

DerridAI uses the same interaction model for relational diagrams even when the domain and layout differ. The corpus term map uses movable chips, the build-wide semantic content graph uses a force layout with entity dots, the Record semantic map uses a radial layout, Traceability uses source-to-claim lanes with cards, and Pipeline Studio uses a directed stage graph. Their domain meanings remain separate; moving a card or node changes only the presentation, not the Record, cELF relationship, semantic assertion, pipeline definition, or other authoritative data.

On these maps and diagrams:

- drag empty background space to pan;
- drag a node or card to reposition it while its connected edges stay attached;
- use the mouse wheel/trackpad or the map controls to zoom;
- use **Fit** to frame the current content and **Reset layout** to discard manual node positions and return to the deterministic layout;
- drag the resize handle to change the map height; the resize handle is keyboard-operable with the arrow keys;
- when the map itself has focus, use Arrow keys to pan, plus/minus to zoom, and 0 to reset the view;
- when a node has focus, use Alt+Arrow to nudge it without a pointer.

These controls are presentation state only. They do not rewrite scholarly provenance or graph-domain data.

## Background operations

Background operations are managed from Dashboard and also appear in the global operations dock. The dock is attached to the top bar by default whenever there is something to show.

Click the docked status control to expand or collapse the operation stack without leaving the top bar. Double-click the docked control to undock it into floating mode; double-click the floating handle to dock it again. In floating mode, drag the handle to move the stack. The expanded stack lets you cancel work, open a result, dismiss a finished item, or use **Clear finished**; dismissals are reflected on Dashboard as well. Only the floating mode adds extra page scroll room so it cannot permanently cover controls. The global operations dock still shows a corpus build as "N% overall" because that percentage blends several stages. Open Corpus Builder → **Build** for the detailed build monitor: it reports the current sub-operation plus real boundary or metadata-task counts when those stages have meaningful item totals.

### The Operations panel

The Dashboard's **Background operations** panel groups work by what needs you:

- **Needs attention**: failed or blocked operations, and finished ones whose results still await a decision. A failure shows what went wrong right on the row.
- **In progress**: running and queued operations, with a progress bar, elapsed time, and an estimated time remaining when the rate is steady (not shown for PDF corpus builds, whose progress blends several stages).
- **History**: everything else, grouped by day and capped to the most recent few; **Show all** reveals the rest.

The filter chips (**All**, **Running**, **Needs attention**, **Finished**) show live counts and narrow the list. Each row offers one primary action for its outcome (**Open result**, **Open corpus build**, **Review results**), plus **Details** and **Cancel** or **Remove**.

**Remove** and **Clear finished** are undoable instead of asking for confirmation: the rows disappear at once, an **Undo** button stays for a few seconds, and the deletion is only sent to the server afterwards (or immediately if you leave the page). **Clear finished** never removes running operations.

Operations update live: the page keeps one connection to the server and changes appear as they happen, without reloading. A small line under the panel heading says whether live updates are on. If a network or proxy blocks the connection, DerridAI keeps working and refreshes the list every 25 seconds instead (a watched corpus build, job dialog or translation every 5 seconds), then switches back automatically when the connection returns. Signing out closes the connection.

Search, Record and Compare never swap what you are reading. When another change to the corpus arrives (a record is saved, a build is published or a record is deleted), a short notice says **Newer data is available**; select **Load newer** when you are ready. Signed-in researchers see the same notice, which carries no record text.

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

Background job execution is process-local, but job snapshots/history are durably mirrored to the system database. If the API restarts while work is queued, running, or cancelling, that interrupted job is marked failed rather than automatically replayed; completed history remains inspectable.

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

The LLM Providers page lists each profile as one row: status, name, type, model, and a **Test** button. Open a row for its essentials (name, endpoint, model, API key, researcher access); **Capacity** and **Advanced** fold away further settings. One profile is the default, but run dialogs can switch profiles before launch. Test, Warm, and Set default never discard unsaved edits. When you have unsaved changes, a **Save** / **Discard** bar appears at the bottom of the page and writes every profile at once. Open **Bulk values** to copy context tokens, output limits, sampling, and other shared parameters onto every profile or a selection, then save.

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

**Works** is the corpus library. The page header offers **Add files** and a **More actions** menu (separate works into JSONL, populate metadata for all works, create a research site). Below it, two panels keep the data domains apart: **Loaded workspace** (the source files and Records open in this browser) and **Corpus database** (the searchable, indexed copy). Changing the corpus database does not change the loaded workspace, and **Sync workspace to database** lives with the database because it changes derived index state, not the loaded library. Researcher accounts see the same layout with the database panel only, and no corpus-management actions.

The library toolbar searches by title and offers progressively disclosed filters (needs review, database status, author), sorting (title, record count, records needing review, year where defined) and a **Cards / Compact** density toggle. The page-wide counts do not change as you search; the result summary shows how many works match. Search, sort, filters, density and the selected work are saved in the Works URL, so reload, back/forward and copied links restore them.

Select a work with its card; the card is a button, so it works from the keyboard. On wide screens the work's details open in an inspector beside the library without moving the list; on narrow screens they open in a dialog. The inspector shows the cover, bibliographic metadata, citation and database status, with **Open records**, **Review records** (when records need review) and **Edit metadata** up front. Populate metadata, semantic map, annotations and per-work sync are in **More actions**, and **Work insights** is collapsed by default. A card's **Actions** menu holds the same secondary operations, including **Remove entire work**, which still asks for confirmation.

- **Columns** chooses, orders and sizes the table's columns. Each shown column has a width as a percentage of the table; the widths always total 100%, so widening one column narrows the others in proportion (no column goes below 5%). **Even widths** splits the space equally, and **Reset defaults** restores the default columns and widths. Search uses the same column dialog for choosing and ordering columns, including loaded-record results. Advanced Search filters are a condition builder: each row is field, operator, and value, joined with Where / And. Fields come from the metadata schema associated with the selected corpus, or from a schema you choose if none is associated.
- **Comfortable** rows show the full extracted text. **Compact** rows are tighter, narrow the text column, and show the text on one line; where it is cut off, **Expand** shows the rest of that row's text.
- **Get Citation** copies an inline or full citation. The notification quotes exactly what was copied. The menu closes on a choice, on Escape, or on a click elsewhere.
- **Copy view link** copies a link that reopens this table as shown: file name, search, column filters, sort, page and columns. JSONL records stay in this browser, so whoever opens the link is asked for the same file. The notification shows the copied link.
- Notifications name their kind (success, information, warning or error) in text and with a symbol, not by colour alone, and are announced politely by screen readers. Success, information and warning notifications disappear after a time that grows with the message length, and pause while the pointer or keyboard focus is on them. Error notifications stay until dismissed with their close button or Escape.

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

## Create a static research site

The administrator **Works** page includes **Create site** when a corpus database is selected. Choose any number of indexed works, give the site a title and optional description, then choose an export format. **Two-file static site** is the standard and default export. The export dialog also lets you include **all or any subset of the interface languages currently installed in DerridAI** (at least one is required) and choose whether to copy the current derived semantic vectors into the publication. **Build vectors in each browser** omits those vectors while retaining the source embedding contract; visitors can then let the static site download a browser-compatible model and build its own derived IndexedDB index. Every site includes Transformers.js (see [In-browser embeddings](#in-browser-embeddings-and-the-local-index)). No endpoint or API token is exported.

The generated reference site is fully internationalized from the selected DerridAI dictionaries. Its language menu contains only the languages included in that export. Publication is blocked if any selected language is missing a required static-site translation; DerridAI does not silently fall back to English for a selected language. Locale direction is applied at runtime for both left-to-right and right-to-left scripts.

### Record metadata in a site

The **Record metadata** choice in the export dialog sets how much metadata each Record carries, and so how large the files are.

- **Complete** (the default) packages every public Record field, including FieldAssertions: how each value was derived, evaluated, reviewed, and supported by evidence. It carries the cELF Core Record and the Scholarly Assertion layer.
- **Reader-optimized (smaller files)** keeps every metadata value, bibliographic, attribution, quotation, semantic, and indexing, along with Record text, source spans, and citation, and omits only the FieldAssertion layer: the per-field evidence, reasoning, and history that a reading site does not use. That layer is most of a Record's size, so the files shrink substantially. Because the assertions are gone, each kept value that had one carries a short `field_authority` summary (derivation, evaluation, and authority) so that a model-proposed, unreviewed value does not read as settled.

The dialog states the cELF status of each choice, and the published manifest records it under `celf_conformance`. Both choices are cELF Core Record-compliant: every published Record keeps `record_id`, `source_document_id`, `text`, and `source_spans`, and export fails rather than publish a Record that has lost one. Only **Complete** also carries FieldAssertions, so a reader-optimized site is not a full cELF publication and its metadata provenance cannot be inspected in the site.

### Two-file static site

Choose **Two-file static site** for the standard DerridAI publication. The ZIP contains exactly `index.html` and `derridai-site.js`. The JavaScript file contains the immutable publication package, progressive work chunks, the framework-neutral DerridAI browser SDK, and the reference interface. The same two files can be opened locally or served unchanged by an ordinary static HTTP/HTTPS host. No DerridAI application server is required.

### Single HTML file

Choose **Single HTML file** for direct local use. DerridAI downloads one `.html` file containing the immutable publication package, the DerridAI SDK, and the reference interface. Open the file directly from disk in a modern browser.

The document remains self-contained for corpus browsing and research logic. Its Content Security Policy permits direct `http:` and `https:` connections so a visitor's OpenAI-compatible endpoint can be reached, and it allows WebAssembly so Transformers.js can run. Keyword search, Record browsing, filtering, local annotations, citations, and evidence retrieval remain local. Semantic query embedding runs in the browser. Research answers call an OpenAI-compatible endpoint only when the visitor saves one in the **Models** workspace. An API token stays in memory for the current tab unless the visitor chooses to store it on that device. Normal browser CORS and mixed-content rules still apply to those external calls; a page opened from `file://` has an opaque origin, so serving the site over HTTP (for example with the nginx bundle) is the most predictable way to reach an endpoint.

### nginx Docker bundle

Choose **nginx Docker bundle** when the site will be served over HTTP. The ZIP contains:

- `index.html`
- `derridai-site.js`
- `Dockerfile`
- `nginx.conf`
- `start.sh`
- `stop.sh`
- `README.txt`

The ZIP also contains `vendor/transformers/` (the runtime and its notices). The embedding model is not in the image: a visitor's browser downloads it once into Cache Storage.

The Dockerfile uses a single `nginx:1.27-alpine` image and copies only the Web assets: `index.html`, `derridai-site.js`, and `vendor/`. The JavaScript file contains the publication package, the reusable DerridAI browser SDK, and the reference interface. There is no DerridAI API container, Node runtime, Python runtime, reverse proxy to the application, or Docker Compose dependency.

After extracting the ZIP:

```bash
./start.sh
```

serves the site at `http://localhost:8080` by default. Stop and remove the container with:

```bash
./stop.sh
```

Set `DERRIDAI_SITE_PORT` to choose another host port. `DERRIDAI_SITE_IMAGE` and `DERRIDAI_SITE_CONTAINER` optionally override the generated image and container names. The nginx configuration also exposes `/healthz` for container health checks.

When **Provider proxy** is enabled for the nginx export, the generated nginx configuration also exposes `/provider/` as a same-origin bridge to one OpenAI-compatible provider API base. For example, enter `http://localhost:11434/v1` for a host Ollama service; the bundle rewrites loopback hosts to `host.docker.internal`, and `start.sh` adds Docker's `host-gateway` mapping so Linux Docker can reach the host as well. In the published site's **Models** workspace, save `/provider` as the endpoint. A browser request such as `/provider/chat/completions` is then forwarded server-side to the configured upstream path, so provider-side browser CORS configuration is unnecessary and an HTTPS site can proxy privately to an HTTP provider without mixed-content errors in the browser. The generated route allows only GET and POST and disables nginx response buffering for streamed model output.

The provider proxy is deliberately off by default. Enabling it makes the model API reachable to anyone who can reach the site's `/provider/` path; the upstream URL is deployment configuration written into `nginx.conf`, but API tokens and model credentials are not exported. Before exposing a proxy-enabled site beyond a trusted machine or network, put authentication or network access controls in front of `/provider/` (or otherwise restrict access to the site).

### Reference-site accessibility, appearance, and tutorial

The reference site provides light and dark themes plus a high-contrast mode. Theme, contrast, and language controls are keyboard operable and persist locally when browser storage is available. The interface includes a skip-to-content link, visible focus treatment, semantic page landmarks, labelled form controls, native modal dialogs, live status regions for asynchronous operations, reduced reliance on color alone, responsive layouts, and forced-colors support. The static-site accessibility regression suite runs axe against WCAG 2.2 A/AA rules in light, dark, and high-contrast states.

On first use, a guided tour walks through the site. It dims the page, outlines one real element at a time, and explains what that element does and what it means: the five workspaces, Works, Search and its mode and filters, the method disclosure, Research, the Models workspace, evidence and citations, annotations, and the language, theme, and contrast controls. The tour switches to the relevant workspace as it goes and returns you to where you started. Move with **Next** and **Previous** or the arrow keys, finish it, or choose **Skip tutorial** (or press Escape); finishing or skipping is remembered locally. The tour is a modal dialog, so the page behind it is inert while it runs, and the spotlight respects reduced motion and forced colors. The **Tutorial** button in the header replays it at any time.

Every search and Research screen includes a persistent method disclosure showing whether the current operation uses **Text search**, **Vector search (embeddings)**, and/or **LLM answer generation**. As an operation runs, the live status message also names embedding and generation stages. If semantic retrieval falls back to text search or generation is unavailable, the final status states that explicitly rather than silently changing methods.

### Models in a published site

The **Models** workspace is where a visitor chooses the embedding model that runs in the browser, and, optionally, a named OpenAI-compatible endpoint for another model. Nothing there is part of the publication.

Embeddings run in the browser through Transformers.js. The default browser profile is the pinned `Xenova/multilingual-e5-small` revision used by DerridAI's browser embedding contract, with q8 weights, `query: ` / `passage: ` prefixes, mean pooling, normalization, and **WebAssembly** as the compatibility-first execution path. **WebGPU** remains an explicit advanced option and falls back to WebAssembly when unavailable. `Xenova/all-MiniLM-L6-v2` remains available as a smaller English-focused alternative. **Download / test model** is optional; building a browser index downloads the selected model automatically when it is not already cached. **Delete cached model** removes those model files so they can be downloaded again.

For any other OpenAI-compatible model, save a named endpoint: a name, an endpoint URL (or a same-origin path beginning with `/`, such as `/provider` in a proxy-enabled nginx export), and an optional API token. **Store the token on this device** keeps the token in this browser; otherwise it stays in memory for the tab. **Discover models** lists what the endpoint reports, with a filter, and choosing one fills the model field. Mark the endpoint **Use for embeddings** and/or **Use for Research answers**. A failure of that endpoint never erases locally retrieved evidence: Research still returns the auditable evidence packet when generation is unavailable.

### In-browser embeddings and the local index

Query vectors are only comparable to document vectors from the same model. The site therefore applies one rule: the vectors shipped in the publication are used **only when the visitor's embedding model is exactly the model that embedded the publication**. With any other model, semantic and hybrid search fall back to keyword results and say that a local index is needed.

When the browser needs its own index, **Search** and **Research** show **Enable semantic search** beside the local-index explanation. DerridAI first tries a Transformers.js-compatible form of the embedding model recorded in the publication. For the default DerridAI `bge-m3:latest` source collection, that means the browser BGE-M3 profile; if no known browser form exists, the site falls back to the pinned multilingual E5 profile. The one action downloads/caches that model if needed, embeds every published Record, and stores the derived vectors in IndexedDB; there is no separate provider test or model-download step. The same control is available in Models for advanced configuration. The index is keyed by publication and the embedding fingerprint (provider type, model, revision, pooling/normalization and vector-changing variants such as prefixes/dtype), so vectors from another contract are never silently reused. Building shows model-download and Record progress, can be cancelled, and resumes where it stopped; the index can be cleared at any time. It never changes or replaces the publication's own vectors or Records. If IndexedDB is unavailable the index lives in memory for that tab only, and the page says so.

**Transformers.js** is included in every site. DerridAI does not ship it in the application image. The first export downloads the pinned runtime files once (about 15 MB) from a fixed HTTPS source, verifies each file's size and SHA-256, and caches them under `site_runtime/` in the data directory. The Create site dialog shows that download's progress. **Delete cached runtime** removes the server copy; the next export, or **Download Transformers.js**, fetches it again. If the download fails, the export stops with an error. The runtime is embedded in the two-file and single-file sites (the dialog states the added size) and served as separate files by the nginx bundle. Model weights are not included in the publication; the selected browser model is downloaded once into Cache Storage when the local index first needs it. DerridAI defaults to single-threaded WebAssembly so a merely-present `navigator.gpu` does not send the site into an incompatible ONNX WebGPU path.

In the reference site, search-term highlighting is a **Keyword-mode only** affordance. Keyword results highlight whole matching terms (case-insensitively) and the whole phrase when it appears verbatim, and a long Record snippet is centered around the first lexical match. Semantic and Hybrid results are not term-highlighted because their ranking is not evidence that the literal query words occur in the Record.

### Publication architecture

Both export formats use the same immutable publication snapshot. Authoritative published Records remain structurally separate from vectors. Records and vectors are grouped by work and decoded only when an SDK operation needs them, and the SDK yields to the browser between substantial chunks so large publications do not have to be materialized synchronously at startup.

The **DerridAI SDK** owns publication access, Record loading, metadata filtering, lexical/semantic/hybrid retrieval, embedding-contract validation, MMR diversification, evidence-packet construction, deterministic citation formatting, local annotations, progress events, cancellation, and Research orchestration. The SDK does not render the site DOM and does not depend on Vue, React, Pinia, Vue Router, or the DerridAI application server.

AI execution inside the SDK remains transport-neutral. A custom host application may inject embedding and generation capabilities as JavaScript objects, and an optional `vectorIndex` store for locally computed vectors (IndexedDB by default). The generated reference site additionally runs Transformers.js in the browser and can call an OpenAI-compatible endpoint the visitor names, without changing the SDK contract. `client.index.status()`, `client.index.build()`, and `client.index.clear()` manage the local index.

Without a usable embedding capability (none configured, or a model that needs a local index that has not been built), the reference site continues to provide keyword search and metadata filtering and labels the fallback. Without a generation capability, **Research still performs retrieval and returns the auditable evidence packet**; it simply does not synthesize an answer.

### Bring your own Web application

The generated reference interface is optional presentation. A custom site can load the publication and SDK, omit `derridai-site.js`, and render SDK results however it wants:

```html
<script src="/research/derridai-publication.js"></script>
<script src="/research/derridai-sdk.js"></script>
<script>
  const client = await DerridAI.createClient({
    dataSource: DerridAI.dataSources.inline(window.__DERRIDAI_SITE_PACKAGE__),
    embeddings: window.myResearchHost?.embeddings,
    generation: window.myResearchHost?.generation,
  });

  const results = await client.search({
    query: "unconditional hospitality",
    mode: window.myResearchHost?.embeddings ? "hybrid" : "keyword",
    filters: { work: ["Of Hospitality"] },
  });
</script>
```

TypeScript applications can also consume the SDK as an ESM package. From the DerridAI repository, `cd web && npm run build:sdk:package` emits ESM JavaScript and TypeScript declarations to `web/sdk/dist`; `npm run pack:sdk` creates an installable `@derridai/sdk` tarball. The public contract is the same one used by the reference published site.

Annotations remain local to the browser unless the host supplies another storage implementation. Creating a later site export creates a new immutable publication snapshot; it does not mutate an earlier downloaded site.

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

| Mode                                                   | When to use                                              | How                                                                                                       |
| ------------------------------------------------------ | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Local filesystem** (`CHROMA_MODE=embedded`, default) | Local-first install                                      | `PersistentClient` on `CHROMA_PATH` (`./data/chroma`)                                                     |
| **Bundled Chroma container**                           | Process isolation, or sharing the store with other tools | `docker compose --profile chroma up -d`, then `CHROMA_MODE=http` and `CHROMA_BASE_URL=http://chroma:8000` |
| **Running Chroma server**                              | A server already on the host or in the lab               | `CHROMA_MODE=http` and `CHROMA_BASE_URL=http://host.docker.internal:8001` (or the lab URL)                |

Vector Stores → Connection settings can probe and switch backends at runtime. Switching does **not** move collections. Do not point embedded storage and a Chroma server at the same directory (one writer per path). NUKE in HTTP mode deletes collections on that server; it does not empty a leftover local `chroma` folder. Backups always go through the client API and preserve embeddings.

Embedding choices are explicit per collection:

- **Chroma default** for Chroma-managed embeddings;
- **Precomputed** when vectors are supplied by the caller;
- **Configured provider profile + embedding model** when DerridAI should call an Ollama or OpenAI-compatible endpoint.

Provider-profile collections persist the profile identity and embedding model as part of the collection contract, so retrieval uses the same configured endpoint/credentials instead of falling back to the global Ollama URL. Embedding configuration can change while a collection is empty and is locked once records exist.

DerridAI-owned derived vector collections, including the reviewed metadata-example index, use the same server-owned embedding default. If that default changes, derived collections whose stored embedding contract no longer matches are rebuilt from canonical data rather than mixing vectors from different providers or models. Existing installations with the legacy `ollama` default resolve to the configured Ollama provider profile when one is available; an explicitly saved default remains authoritative.

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

Corpus Builder accepts PDF, plain-text/HTML/Markdown, DOCX, RTF, PNG/JPEG, audio,
URL, Project Gutenberg, and Wikisource sources. File format is detected from the
selected file rather than chosen from a separate source-type selector. Extraction
and review remain media-aware: paged documents can retain page locations, images
can use OCR, and audio review uses playback with timed speaker spans. Audio
citations use time ranges and available speaker labels, never synthetic page
numbers. Correcting a transcript creates a record revision and retains the
original transcription.

For a local PDF or image upload, the builder first stages the selected file,
then offers its OCR strategy before ingestion: use embedded text when available,
prefer OCR for difficult scans, or always OCR. Non-image files ingest directly
without OCR controls, and already-ingested sources do not expose extraction
settings that can no longer affect them. Printed-page detection runs automatically
during source ingestion using deterministic extraction, with the configured model
used only as a fallback when no credible sequence is found.

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

**Search digital libraries** finds a text in Project Gutenberg or Wikisource
without leaving the dialog. Results follow what you type (Enter searches at
once); `↓` moves from the search box into the results and `↑` back. Errors and
"no results" appear in the dialog, the result being imported says so on its
row, and a successful import closes the dialog with the new source selected.

Gutenberg search lists separate eBook IDs and languages. Choose an exact entry;
imports retain its ID, edition label, catalog metadata, exact download URL,
encoding, retrieval time, and original-byte digest. Gutenberg answers a format
link with one redirect to its cache file; that single hop is followed only when
it stays on gutenberg.org and names the same eBook. Any other redirect, missing
text, mismatched identity, timeout, or undecodable content fails visibly. The
importer does not guess another download or substitute another edition. Two
editions with identical text remain distinct assets. The catalogue is required
for search, but the full local text archive is optional for an individual import:
when that archive is absent, DerridAI downloads and verifies the selected eBook
directly instead of disabling the result. The dialog still offers the local
collection for offline/repeated use. A paused or failed collection download
resumes from the bytes already on disk, and a download that had in fact finished
moves straight on to unpacking; **Redownload** (after a confirmation) deletes the
file and starts over.

Wikisource search covers one language edition at a time (English, French,
German, and others; French is preselected in the French interface). A work's
main page on Wikisource is usually its title page and contents, with the text on
subpages, so results are grouped by work: **Import whole work** fetches the
contents page and then every subpage it lists, in order, and **Only this part**
imports a single chapter. The stored source keeps each chapter in a section
named after its Wikisource page. Wikisource page chrome (header, navigation
arrows, maintenance notices, hidden metadata) is not extracted as text. A work
larger than the upload limit fails with a message suggesting its parts instead.
Available Wikisource language editions come from the API's current project list;
if Wikimedia's project list is temporarily unavailable, DerridAI labels the
bounded fallback rather than presenting it as authoritative.

### Corpus Capture and Sources

**Sources** is the registry of documentary sources already acquired by DerridAI.
It shows source identity, provider, document and original language, edition or
translation information, contribution role, acquisition state, build state, and
when the source was added. The table is server-paginated and server-sorted, with
filters for provider, language, capture, build state, relationship, and role.
Inspecting a row shows provenance without loading the source text into the table.

**Import an author** is available from Sources and Corpus Builder. It resolves a
person through Wikidata, then lets the researcher choose Project Gutenberg and/or
Wikisource, contribution roles, original works or translations, and language
scope. Available languages discovered from the author are offered as
autocomplete suggestions, but a researcher may enter another language. When
translations are disabled, language scope is locked to the detected original
language; if no original language is available, one language must be entered.
Discovery records provider coverage and groups candidate editions by canonical
work and language for review, but each edition remains its own selectable
candidate. Nothing is downloaded merely because discovery found it.

After review, **Capture selected** acquires only the selected candidates and
registers successful acquisitions as sources. Acquisition does not start a corpus
build. **Use in Corpus Builder** hands the resulting source IDs to the builder,
where the researcher still chooses what to build. Closing the capture dialog does
not cancel an active background job; reopening the capture resumes from its
durable status. Failed acquisitions remain visible and can be retried, while
registered sources remain distinct from capture/job bookkeeping.

When **let a model help find page numbers** is on, an import uses the selected
provider profile the same way a build does; a profile the server cannot resolve
fails the import with that reason rather than being ignored.

Text, HTML, Word, and RTF sources receive page numbers even when the file has
no PDF pages. Gutenberg and Wikisource page anchors (including Wikisource
`pagenum` marks) are used when they are present. Wikisource DjVu scan pages are
saved beside the transcription, up to a bounded number of page images. Word and
RTF page breaks, including a declared starting page number, are used next.
Otherwise DerridAI looks for a printed page-number pattern. If none of those
succeed, pages are estimated at 300 words. Corpus Builder then asks whether to
keep that length and whether each estimated page should be its own record; both
default to yes (300 words, one record per page). Audio still uses time ranges
and is not given page numbers.

On source load, Corpus Builder first attempts a bounded deterministic language
signal from the extracted text when embedded or catalogue language metadata is
absent. The resulting value remains a reviewable assertion. If no reliable
language is available, the configured language model may propose one from a
bounded excerpt. The researcher must explicitly save that language or skip the
field; skipping is retained as a confirmed absence rather than silently
re-running the prompt.

The same source-load checkpoint exposes deterministic front-matter and NLP
metadata candidates (title, author, publisher, edition, ISBN, translator, and
publication location/year) before record enrichment. Candidates retain their
method, confidence, and source span. Researchers can submit explicit
source-level metadata decisions or mark unresolved fields absent; those choices
are stored as human provenance and are not overwritten by later enrichment.
Reviewed metadata exemplars remain advisory guidance, never replacement source
evidence. Audio sources use time and speaker locators only and do not acquire
synthetic PDF page semantics.

### Corpus Builder review saves

Review edits are applied to the open record immediately so navigation and
repetitive review work do not wait for the API response. The changed record
is then persisted in the background. Saves for the same record remain ordered
so revision checks are safe, while saves for different records can proceed
independently. A failed background save leaves the local edit visible and
reports the affected field or record rather than discarding unrelated edits.
Acceptance remains server-confirmed because metadata and source-quality rules
can block it.

## Corpus Builder metadata population

The LLM returns each metadata field (or `null` when unsupported) together with a per-field confidence. The response schema requires every field, so a model cannot return confidence assessments without values.

- Every schema-valid non-empty LLM value is populated into the record so the reviewer can see it; population does **not** imply verification.
- `autofilled=true` is reserved for the calibrated autofill policy (90% blended confidence by default, valid cited evidence, and no suspension from poor reviewer precision). Values that do not pass calibrated autofill remain **pending review**, even when they exceed the ordinary metadata-confidence floor.
- Deterministic values (for example reviewer-defined document structure) stay selected; the LLM check either corroborates them or records a disagreement for review.
- If the model reports more than the threshold in confidence for a speaker, position holder, target, stance, or proposition status but returns **no value**, the field is marked unresolved with reason `no_value_returned` rather than shown as an inference. Use **No supported value** to confirm a genuine absence.
- Reviewer-confirmed values are never overwritten by later enrichment.
- Reviewed metadata decisions are persisted with provenance in durable application
  state. Eligible evidence-bound decisions are projected into a rebuildable
  semantic metadata-exemplar index. Later enrichment may retrieve diverse similar
  examples with similarity/MMR, filtered by field/schema policy, as advisory
  prompt context. The current Record's evidence remains authoritative; metadata
  memory never auto-applies a value or replaces the exact adjudication cache.
- After a pass finishes, **Run another pass** is available in the review workspace immediately. You do not need to accept every record first. The next pass is given what the last pass inferred (working conventions on this build) and any reviewer decisions already made.
- Enrichment is persisted record by record, not only at the end. The live operation reports the selected provider, model, pass, and processed-record count; a later run can target all records, an accepted/pending scope, or an explicit subset.
- Each record keeps activity telemetry for human opens and saves, LLM reviews, enrichment passes, and the last provider/model that touched it. This is audit information, not a replacement for field-level provenance.
- How each metadata group's model call runs is set by the pipeline assigned to _Corpus metadata enrichment_ in Pipeline Studio. The built-in `corpus.metadata_enrichment.current@2` makes one primary-provider attempt after DerridAI has already reduced the task to unresolved fields; the response is conservatively syntax-repaired and schema-validated. Only a failed validation, provider error, or timeout follows the pipeline edge to one review-provider attempt when a review provider is configured. Version 1 remains available as a disabled historical pipeline for reproducing the earlier two-primary-plus-two-review retry chain. A clone can change the number of attempts, let the review provider answer first, or drop escalation; it cannot retry a timed-out provider on itself or change the task, which comes from the active metadata schema. Every answer is still validated, and review, evidence and autofill rules apply afterwards. Each group's execution ledger names the pipeline version, its trace, the exact requested field contract, and which stages ran. The trace keeps provider, model, attempt counts and failure codes, but never the prompt or the model's answer.
- How the builder's boundary questions run is set by the pipeline assigned to _Corpus segmentation_ in Pipeline Studio. There are two: the batch classifier (split or keep a transition that deterministic routing left ambiguous) and the second reader (whether a suspicious record seam should stay or move, asked during the build and from the **Boundary second reader** panel's **Check with LLM** button in review). The built-in `corpus.segmentation.current@1` runs them like metadata enrichment: two attempts on the primary provider, then two on the review provider if one is configured. A clone can change attempts, let the review provider answer first, or drop escalation. It cannot change routing, the confidence threshold, or the rule that a failed, omitted or low-confidence answer keeps the boundary. If the assigned pipeline cannot be resolved, no model is asked, ambiguous boundaries are kept, and the build shows a warning. Each cached boundary decision and each second-reader verdict names the pipeline version and its trace.
- How the document analysis runs is set by the pipeline assigned to _Corpus document manifest_ in Pipeline Studio. The model is asked for the document's details (bibliography, language, main-text pages) once when a build starts and again when you choose **Analyse the document again**. The built-in `corpus.document_manifest.current@1` runs it like metadata enrichment: two attempts on the primary provider, then two on the review provider if one is configured. A clone can change attempts, let the review provider answer first, or drop escalation. It cannot change the document sample, the prompt, or the rule that embedded file metadata, a confident start-page inference and reviewer-confirmed structure outrank the answer. If the analysis fails, or the assigned pipeline cannot be resolved (then no model is asked), the manifest uses the file's embedded metadata and the build shows a warning naming the reason; **Analyse the document again** retries. Each analysis's pipeline version and trace are kept beside the manifest, not in it.
- When a PDF is loaded, the builder scores each page for **illegibility** (0% = still looks like words in a writing system; 100% = unreadable) and, when a page has an embedded scan, **raster DPI**. A warning dialog appears if too much of the source looks unusable; afterward the finding lives as a clickable warning icon on affected Record Review rows. Names, bilingual pages, and coinages are allowed; interior punctuation, letter–digit soup, and scans below about 150 DPI are not. A build setting (default 45%) counts pages and Records at or above that noise as unusable. Those Records feed the existing **>10%** source-quality warning, skip metadata enrichment, and appear in the source-problem queue. The optional **LLM extraction-quality second opinion** runs **after you start a build** and may only **raise** the deterministic score. That second opinion is currently PDF-only because its page-level decision combines PDF text-layer/OCR noise with scan/raster characteristics; other media use their format-specific deterministic extraction or transcription quality checks instead.
- Pixelation is measured from the embedded image’s pixel size versus the rectangle it occupies on the page. Native vector/text pages with no image are not scored as scans.
- **Use suggestions as-is & publish.** Once a build has finished processing, the Publish phase offers **Use suggestions as-is & publish…** until a publication exists. The action opens a focused publication decision dialog rather than an inline warning. It shows the remaining review scope and explains the authority consequences before anything is published. If you proceed, DerridAI applies its autonomous-selection compatibility policy to eligible non-rejected records without changing the canonical build review state. Values you confirmed or corrected are never replaced, rejected records stay excluded, and out-of-vocabulary or failed proposals are not silently made valid. Each selected value retains its original derivation, evaluation, authority, confidence, evidence, and value state; an autonomous publication decision is recorded separately and does not turn the assertion into a human-confirmed one. cELF Core and Publication conformance are evaluated independently from whether decisions were autonomous, reviewed, or hybrid. A metadata contract may still require evidence or human review for particular fields, and those contract requirements can block conformance. Text conservation is never skipped: missing, duplicated, reordered, or altered source text still blocks publication.
- **Messages and warnings.** Every message has its own × and a group of several also has a × for all of them. Messages and pre-build notices simply close. Build warnings (a failed text touch-up, records that look unusable) are part of how the corpus was made, so their × **acknowledges** them instead: the warning is kept, your name and the time are recorded with the build (shown under technical details), and at publication a warning about a record is published in that record's `provenance_warnings`, while build-wide warnings, with their acknowledgements, are kept in the publication's provenance. Explanatory "i" tooltips open above the page, so no pane or the record viewer can hide them.
- The Source PDF step reports extracted **SourceUnits** (addressable PDF/OCR layout units), not Records. `OCR page(s)` counts pages where OCR was used; zero means the native PDF text layer was used. Image-only pages remain visible as source-quality findings instead of disappearing from the 10% check.
- **Record size and source units.** Record sizes are in characters, counting spaces and punctuation (about 6 per word in English and French prose, so 250 characters is roughly 40 words). A record is made of whole source units, and a unit is never cut. The record size is authoritative for how units are grouped: the target range is what the segmenter aims for, the ceiling is a hard limit, and the step that keeps records from starting or ending mid-sentence may move or remove a boundary only when every record stays within that ceiling. A boundary it cannot place on a sentence end is kept and reported rather than silently producing a larger record. Headings and contents lines ("Contents", "Chapter II") count as clean ends. With **Automatic** units (the default), a paragraph longer than the build's long-record size is divided into sentences when the build starts, so records can be as small as you ask; the original source is kept, and the build records which derived source it used. Choosing **Every paragraph** (or another policy) explicitly is respected, and the Structure step says when that choice makes the requested size unreachable. A single unit larger than the ceiling (one very long sentence, or a paragraph under **Every paragraph**) becomes a record of its own. Sentence and **Automatic** units are language-aware: DerridAI uses documentary-language metadata when available and otherwise chooses a conservative Unicode-script profile for boundary rules. The deterministic splitter recognizes script-appropriate terminal punctuation (including CJK, Arabic, Indic, Armenian, Ethiopic, Myanmar, and Tibetan forms), avoids treating caseless scripts as lowercase continuations, and uses language-specific abbreviation/heading conventions where a profile exists. Script inference is only a segmentation aid; it does not assert or overwrite the document's scholarly language metadata. **Every paragraph** remains structural: it preserves the extractor/source format's paragraph units rather than pretending that a universal grammatical definition of paragraph exists. The selected/inferred segmentation profile and engine are retained with derived-unit and boundary provenance.
- When embedded PDF metadata contains an author, the builder carries it forward as a deterministic, reviewable document-author assertion. It is not silently treated as an LLM inference.
- **Clean all Record text before enrichment** is deterministic preprocessing and is disabled by default. **Use LLM to touch-up text as part of enrichment** creates a conservative, reviewable proposal for extraction errata, diacritics, formatting, quotations, and line breaks. The proposal does not change authoritative reviewed text until a person reviews and saves it. How the touch-up call runs, from enrichment or from a Record's text touch-up action, is set by the pipeline assigned to _Corpus text touch-up_ in Pipeline Studio. The built-in `corpus.text_touchup.current@1` runs it like metadata enrichment (two attempts on the primary provider, then two on the review provider if one is configured). A clone can change attempts, let the review provider answer first, or drop escalation, but not the prompt or the check against the source text. If the pipeline cannot be resolved no model is asked and the touch-up fails with the reason. Each proposal names the pipeline version and its trace.
- The Metadata schemas page lists built-in profiles and saved project schemas in a table with **New schema** and **Import a schema…** above it. DerridAI ships the historical scholarly default plus **Fiction** and **Non-fiction** profiles. Built-ins are read-only to keep their contract stable, but **Duplicate** creates an editable project copy. The selected schema has a sticky bar (state, version, Duplicate, Export, Delete, Save; Ctrl/Cmd+S saves) and four tabs: **Fields** (a filterable table per group; a row expands into the full field form and shows its evidence, confidence, review and memory policy), **Document fields**, **Prompts** (one group's prompt at a time) and **Try it** (preview or run a group on a passage).
- Each field has a scope, **Where the value lives**: on each record (the default) or once for the corpus. A corpus-scoped value is shared by every record of the corpus and can be supplied before segmentation.
- **Document fields** sets the policy for the bibliographic fields DerridAI defines (title, author, translator, edition, year and so on). You cannot add or rename them, but each holds one value for the whole corpus, and for each one you choose whether a missing value blocks citing a record as evidence or publishing the build. Values are detected when the source loads; you are asked to supply one only when a required field could not be detected. By default the title and author are required for both; publication readiness reads these requirements from the schema the build was started with. Schema files from before this change (format 1) import with these defaults, and a field that was marked as applying to the whole work becomes corpus-scoped.
- Metadata schemas are defined at **System → Metadata schemas** (administrators only). Corpus Builder step 5 chooses which schema profile a build copies and can open the editor in a dialog. The scholarly default preserves the established discourse/quotation/indexing contract; Fiction adds narratological, storyworld, dialogue and literary fields; Non-fiction adds claim/evidence, source, entity, rhetorical-structure, recommendation and conclusion fields. Every domain-profile field carries field-specific extraction guidance and evidence/assessment requirements. Schemas are semantic-versioned independently of the application and corpus contracts. New saved schemas start at `1.0.0`; unchanged saves retain their version; adding fields increments the minor version, removing fields increments the major version, and changing existing definitions increments the patch version.
- Each schema field has a stable identity separate from its display name. A deliberate rename can retain that identity, so reviewed precedents continue to belong to the same semantic field. Field-level **Memory & retrieval** settings control whether evidence-bound reviewed values, corrections, and confirmed absences may guide later metadata enrichment. **Maximum precedents** bounds the field's ordinary precedents in the prompt packet and **Maximum corrections** gives reviewed corrections their own quota, so neither crowds out the other; **Minimum similarity** rejects weaker semantic matches. **Prefer precedents that agree on** optionally names other fields (by stable identity): precedents whose reviewed value for those fields equals the current record's reviewed value come first, ones that differ are left out, and a field that is unreviewed on either side is simply not compared. DerridAI assumes nothing about which fields a schema has. Corrections retain the rejected model value as negative evidence, and confirmed absence is reusable only when a reviewer has explicitly bound source evidence to that no-value decision. These controls do not alter the canonical reviewed Record or route metadata exemplars into Research response/claim memory.
- Each field also has a value-matching policy (`equivalence_profile`; see [METADATA_SCHEMAS.md](METADATA_SCHEMAS.md#value-matching)). It decides when a value you type is the same value the model proposed, only written differently: `J.P. Dingus` and `J. P. Dingus`, or (with a spaCy language model installed) `pushing the boundaries` and `push the boundaries`. Such an edit saves exactly what you typed and keeps the field's evidence. It counts as accepting the model's value, so it is not remembered as a correction and does not lower the model's calibration. A different value is still a correction. When DerridAI cannot tell (`J. Dingus` and `John Dingus`), your value is saved and the decision is scored as neither accepted nor corrected. Related is not the same: `critique of metaphysics` and `deconstruction of metaphysics` stay different. Set the policy under **Value matching** when editing a field. **DerridAI default for this field** follows DerridAI's policy for the field's meaning, or else its type. You can also choose list order, and an identity kind that lets fields share identities, for example `person` for every field that names people.
- **Reviewed identities** (Corpus Builder review, below the semantic map) records which names or phrases refer to the same person, work or concept in this corpus: a preferred form, its other forms, and an optional note. DerridAI then treats them as one value when scoring your edits, grouping reviewed precedents, voting on pre-fill suggestions and drawing the semantic map; no record's value is rewritten. To keep two similar-looking names apart (two different people called `J. P. Dingus` and `JP Dingus`), give each its own identity. A form can belong to only one identity of a kind. **Edit** saves a new version and keeps the old one in the build's history, and **Retire** asks first and also keeps it. **Import from another corpus…** lists other builds that have reviewed identities; choose a build and the identities to bring in. They are copied into this corpus and marked with where they came from, so later changes in that corpus do not change this one. Anything whose forms already belong to an identity here, or that you already imported, is skipped and listed. In the semantic map, values that are one identity share one node that lists every form it was written in.
- In **How well is enrichment working?**, **Accepted (same value)** counts values you kept, including restatements; **Accepted as restated** is the share you kept but wrote differently; **Undecided comparisons** counts decisions DerridAI could not score either way.
- **Run-specific field guidance** is configured beside schema selection and is saved only with that build. For any field, add an instruction and/or names, titles, concepts, or variants to look for. Exact phrase matches are shown as review cues and passed to the corresponding field group's LLM task; they do not change the schema, restrict the allowed values, or count as evidence that the value applies. The model must still use this record's context and bind evidence where the schema requires it.

### Document Intelligence and relationship maps

The **Enrichment** setup workspace includes **Document intelligence**. It analyzes the complete reviewed document before per-Record metadata calls and makes document-scale entity/coreference/quotation structure available as advisory context.

Choose **Scholarly / non-fiction** for philosophical, critical, historical, and other non-fiction texts. The resulting index combines document-level people/entities with the schema's reviewed or proposed `persons`, `concepts`, `works_referenced`, and `topics`. Choose **Fiction / characters** when person/coreference clusters should be presented as characters. **General** keeps the analysis genre-neutral. **Off** skips whole-document analysis.

**Automatic** is the default analyzer: spaCy for every language, with BookNLP's richer English coreference and quotation attribution when its optional worker is set up. **spaCy only** skips BookNLP; **BookNLP only** records the analysis as unavailable for a language BookNLP cannot serve rather than silently changing providers. A missing Document Intelligence provider never aborts the corpus build. Administrators install analyzer models from **Settings → System → Language packs**, which lists spaCy models for 24 languages plus a multilingual entity model used for any other language, the English BookNLP packs, and reference sources for literary pipelines in other languages (Propp for French, LLpro for German); it shows download progress and accepts additional pinned packs. A newly installed spaCy language is used by the next analysis without a restart. See [DOCUMENT_INTELLIGENCE.md](DOCUMENT_INTELLIGENCE.md) for model and service setup. After the stage runs, the Build workspace reports the requested analyzer, the analyzer actually used, model/provider version when available, capabilities, counts, fallback status, and warnings so an automatic fallback is never invisible.

Entity aliases, coreference clusters, quotation-speaker candidates, and optional event output are model-derived navigation/enrichment hints. They do not count as source evidence, do not confirm who holds a proposition, and do not become human-confirmed metadata automatically. Metadata prompts label these as attention cues rather than candidate answers, and the built-in Non-fiction evidence-type/evidence-item fields are evaluated from the passage instead of receiving raw POS/NER candidate lists.

In Record Review, open **Entities & relationships** to inspect the build-wide content map. Large corpora can hold tens of thousands of entities, so the map never loads or draws them all: the server returns a ranked, size-capped view and says how much it left out. The panel includes:

- a filter bar: search across labels and aliases, entity-type chips with counts (multi-select), a **Relationships** switch (All / Semantic / Observational), **Minimum mentions**, and **Map density** (top 40–250 entities);
- a status line ("Showing 80 of 12,430 entities · 312 of 95,004 relationships") and a notice when the drawing is partial;
- an interactive relationship map: circle size reflects mentions, colour reflects entity type, solid lines are evidence-aware semantic relations, dashed lines are computational observations, and dotted red lines are disputed relations. Use **Compact**, **Standard**, or **Wide** card spacing when more room is needed for arrows and labels. Hover or keyboard focus highlights an entity's neighbours; drag the background to pan, drag an entity to reposition it, scroll or use the map controls to zoom, use **Fit** to frame the current view, **Reset graph layout** to discard manual positions, and the resize handle to change the map height;
- **Explore neighbourhood** (or double-click an entity, or pick one from the index) to redraw the map around that entity with its strongest connections, with a breadcrumb back to the overview;
- an inspector with aliases, mention/Record/connection counts, and — in a neighbourhood — the entity's relations grouped into evidence-aware relations (with Reviewer confirmed / Unreviewed / Disputed status and evidence-reference counts) and computational observations;
- a complete, paged entity/concept index (50 per page) sortable by mentions, connections, Records, or name.

Observational relationships such as co-occurrence and dialogue proximity are drawn separately because they do not assert friendship, influence, agreement, addressee, or another stronger relation.

For fiction, the index supplies the requested character list and the graph provides a character network without turning simple proximity into a literary claim. For scholarly/non-fiction text, the index supplies people, concepts, works, topics and other named entities, while existing fields such as `position_holder`, `target`, `stance`, `speaker`, `quoted_speaker`, `quoted_author`, and `quoted_work` contribute evidence-aware semantic edges.

Every Record also has its own map. In Record Review (and in the focus view), open the Record's **Semantic map** tab to see:

- the Record's **annotated text**, with Document Intelligence entities and quotations and the local spaCy **NER** entities and **POS** noun/proper-noun terms highlighted as exact spans with their tags; each layer can be hidden, and selecting a highlighted span walks to its node;
- a diagram centred on the Record: the nodes it contains on the inner ring, the relations it supports, and fainter outward relations to nodes found in other Records;
- the Record's nodes grouped by type, and **Linked records**, ranked by the nodes they share (rarer nodes count more; a shared semantic relation counts most), each with a short preview and the shared nodes.

Select any node, shared node, or relation endpoint to **walk** to it: a node view lists its relations (semantic relations first, with their authority state) and every Record it occurs or takes part in. From there, **Explore map** walks into another Record's map and **Open in review** makes that Record the one under review. The exploration path above the map keeps each step, so **Back** or any earlier step returns along the walk. POS/NER terms that name an existing entity or concept join that node; other terms link Records only by the same surface form, and the diagram hides plain POS terms unless **Show POS terms in the diagram** is on. Like the build-wide map, a shared node or term is navigation, not evidence that two Records make the same claim.

The POS/NER term layer is computed per Record when Document Intelligence runs (and when a Record is split or merged). Builds analysed before it existed show the layer as **Not analysed yet** until **Reanalyse document** is run; a Record whose text changed shows it as **Stale**.

If reviewed text changes after analysis, the panel marks Document Intelligence **stale**. Select **Reanalyse document** to refresh text-bound annotations and the relationship map. Stale document annotations are not used to build the current graph.

Records enriched before this behavior existed are not changed automatically. **Retry metadata** skips completed metadata families by design, so it will not repopulate them. To repopulate an affected record, use **Run metadata enrichment again** (or **Rerun** on a family) and choose **Discourse / attribution**; this clears only LLM-owned values in that family and keeps reviewer-owned, deterministic, and inherited values. Rebuilding also works.

## Corpus Builder Setup, Build & review, and Publish phases

Corpus Builder presents three researcher-facing phases for one durable workflow — **Setup → Build & review → Publish**. Build and Review are deliberately grouped because they can overlap: as soon as Record topology exists, you can keep watching automated work or start adjudicating Records while enrichment continues. With a build open, the header is one compact row (the page title is already in the tab and breadcrumb): the source filename, one lifecycle badge (Configuring, Building, Enriching metadata, Reviewing, Ready to publish, Published, Needs attention or Stopped), and the three phase controls. Inside **Build & review**, a smaller Build / Review switch moves between the live monitor and the Record workspace without changing the selected build. The raw build ID remains secondary metadata under **Build details** and in **Builds**, the canonical build selector.

- **Setup** (when a build already exists, a note says that changes apply to the next build you start) is a configuration workspace with **Source**, **Structure**, **Metadata**, **Enrichment**, and **Run settings**. Each section has a status and one-line summary; only one is open at a time. On wider screens, a sticky **Build plan** sits beside the settings and continuously summarizes the source, structure, schema, enrichment mode, provider/model, Record size, and warnings. It holds the launch decision instead of duplicating it in a bottom command bar. If setup is blocked, **Fix** is the primary action and opens the section that can repair the blocker; otherwise **Build record set** is primary. Run settings are normally optional, but a context/execution problem there is shown as incomplete rather than optional. Structure and source facts remain medium-aware, so non-paginated media do not acquire PDF/page controls.
- When the chosen metadata schema requires a document field (by default the title and author) that could not be detected when the source loaded — from embedded metadata, header lines, bylines or catalogue data — those fields are shown in Metadata as soon as a source is selected, and clicking **Build record set** opens **Not detected in this source** as a final checkpoint if any are still empty. Nothing is asked for a value that was detected. A supplied value applies to every Record of the corpus, outranks model and catalogue inference, and records that it was supplied by the reviewer. **Skip for now** continues without values; the gap stays flagged for review and blocks publication if the schema requires it.
- **Build** is the live side of **Build & review**. It shows the lifecycle state, current operation from real pipeline telemetry, coarse overall progress, Record count, provider/model, and the five machine-stage groups (Prepare, Structure, Construct, Enrich, Finalize). **Pause**, **Cancel**, and **Resume** are available here. As soon as ready Records exist, the monitor promotes **Review N ready Records** and explicitly says that review can begin while automated work continues in the background. Warnings and failures that need action stay in the main view; audit detail remains under **Run details**.
- **Review** is the researcher side of the same phase. It opens as soon as Record topology exists and uses the queue, Record reader, metadata/evidence/source inspector, and decision dock. The compact background-run control stays visible while you work and includes **Pause** for an active corpus build and **Resume** for a resumable one. **Accept clean (N)** appears only when ready Records exist and opens an accessible confirmation explaining that accepting them records human review decisions while exceptions remain queued. Selecting Records reveals a contextual selection bar for selection-specific edit/reject actions instead of making those commands compete with navigation all the time.
- **Publish** is the conclusion and repair surface; its main button always acts (with nothing more specific to do it opens the first blocker), and a gate that has already passed is a single line while the ones still blocking take the space. Before publication it leads with one readiness statement and three summary quantities: Records pending review, unresolved metadata fields, and validation blockers. The readiness rows below correspond to **Records**, **Required metadata**, and **Source & validation**, with direct actions back to the relevant review context. **Publish corpus** is the ordinary reviewed path. **Use suggestions as-is & publish…** is the explicit skip-review publication path: its dialog explains that eligible suggestions are selected only in the immutable publication snapshot, their derivation/evaluation/authority/confidence/evidence remain intact, and no human-review claim is created. Source/text-conservation validation and other mandatory publication gates still apply. After publication, readiness counters disappear and the workspace shows the completed publication snapshot and download action.

The UI presents three phases, but the URL intentionally retains the four internal workspace values `workspace=setup|build|review|publish` plus build/Record/queue identifiers. That keeps Build and Review independently deep-linkable and preserves refresh, Back/Forward, and durable lifecycle behavior while avoiding a false sequential handoff in the interface.

### Document structure and pagination

For a PDF, **Document structure & pagination** is where you say how the pages are arranged before a build. Choose a page pattern: one column, facing pages, a margin column, an inset box, or a quotation band. Facing pages still map one PDF page onto two printed pages, with a reading order and a thread for each side.

A margin, infobox, running header, or other text that is not the main column is a **region**: a rectangle on the page, with a role and a thread. The rectangle applies to every page unless you limit it to odd pages, even pages, a range, or the page you are looking at. Drag its edges, or select it and use the arrow keys (Shift plus an arrow key resizes it). One region covers a repeating layout. Rectangles are used because columns, margins, and boxes repeat across a book; a shape drawn around every paragraph would not. When one page wraps around a figure, limit that rectangle to that page.

Text in a separate region is read after the main text, in page order, and becomes its own records, so a marginal gloss or a parallel column is not braided into the argument on every sheet. A block quotation can stay in the main text instead. Running headers marked as their own region stay out of the body. Each block keeps its page. Printed page numbers, front matter, and the bibliography are still set with the page anchors and the mapping review. A document can have at most 24 regions.

### Build monitor and Model activity

The **Build** primary status is the progress surface rather than a hidden technical-details disclosure. It follows the actual current pipeline stages, including preparation/resume, document structure/review, segmentation, Record construction, Document Intelligence, metadata enrichment, and final review preparation. During segmentation it reports candidate progress; during enrichment it reports the active Record/family and settled/running/queued task counts. The overall percentage remains a coarse cross-stage indicator and is not presented as an item-count estimate or ETA.

Build-state notifications use the shared authenticated realtime connection, with REST/GraphQL remaining authoritative after reconnects. Per-Record metadata and model-call progress events contain identifiers/counters only. Source text, prompts, field values, and raw model output are not sent through Corpus Builder WebSocket events.

After an API restart, unfinished execution is marked **Interrupted**; it is never restarted automatically. Choose **Resume** to continue from the saved manifest, segmentation, Records, and metadata checkpoints. Resume preserves the build's source scope, topology policy, metadata contract, and run guidance; only explicitly supplied execution settings change. Human-reviewed text and decisions remain authoritative. An orphaned metadata operation is marked failed rather than left permanently running, and failed submission remains visible and resumable.

Validated Records become readable before optional source indexing, metadata-memory prefill, and Document Intelligence finish. During preparation the review controls remain locked; readable topology is not a claim that metadata enrichment or publication validation has finished.

When a build uses an LLM, expand **Run details → Model activity** to inspect each build-local call. It records the rendered prompt, provider/model, response schema, generation settings, attempt, raw completed output, validated structured result, and errors. While the inspector is open, provisional output from active calls is refreshed through an administrator-authenticated REST read in response to text-free realtime progress notifications. The provisional text can be incomplete or invalid JSON; only the completed response after schema validation is used by the corpus pipeline. API keys, authorization headers, and provider credentials are never included in the trace.

## Corpus Builder review workspace

Once a build has records, the review workspace fits below the top bar: the queue on the left, the record in the middle, and the details (metadata, evidence, source) on the right. Each pane has one primary scroll surface, and the record's title and its decisions stay in view while you read. The remembered workspace height is clamped to the available window; phones and very short windows use normal page flow.

The queue loads lightweight previews, then opens the selected Record through an indexed read. Nearby Records are prefetched into a small cache; opening a Record no longer requests a metadata cache entry for every schema field. Loading, missing Records, and read failures are distinct states, with **Retry** for a failed read. A response for an older build or selection cannot replace the current Record.

Explicit Record, page, queue, build, and route navigation protects unsaved text and metadata edits with **Save and continue**, **Discard and continue**, or **Stay here**. Save waits for persistence, and a failed save leaves the dialog open. Background updates and search preserve the active draft rather than silently replacing it. Metadata drafts remain mounted when changing inspector tabs.

One header sits above the panes: a progress meter ("8 of 60 accepted", with the remaining count; the filters below carry the other counts), a compact **background enrichment** status (shown only while a run is active or needs attention, with the run diagnostics and warnings behind it; otherwise **Run another pass**), **Focus view**, and a **View: Record | Metadata | Source** switch that only changes the Review layout. Below it are the queue filters — **All**, **Ready**, **Needs attention** (with an **All issues / Metadata / Topology / Source** sub-filter), **Accepted**, **Rejected** — then search, **Accept clean** and bulk actions, and paging. A queue row leads with the Record's short sequence number ("#12"; the full ID is its tooltip and is read by screen readers), its page locator and one status label, then a two-line preview and the length; a small spark marks a Record the enrichment run has processed.

**Evidence suggestions.** In the Evidence tab, choose a field and select **Suggest spans** to rank the record's source blocks by deterministic text matching (exact match ignoring case, accents and punctuation, then weighted term overlap; no stopwords are removed, so negations count) and a local semantic match using the field's schema label/instruction and proposed value. The panel distinguishes text, local semantic, and combined signals; if semantic retrieval is unavailable it shows the fallback and keeps the text suggestions. **Ask the model** (when a provider is selected) asks the model to choose among those same blocks; unknown block IDs are discarded, and a model choice with no text match is labelled so you can check it. Suggestions are advisory and read-only: nothing is bound as evidence until you use a span. How **Ask the model** runs is set by the pipeline assigned to _Reviewer evidence choice_ in Pipeline Studio. The built-in `corpus.reviewer_evidence_choice.current@1` gives the primary provider two attempts, then the review provider two if one is configured. A clone can change attempts, let the review provider answer first, or drop escalation; it cannot skip the block-ID checks. If the pipeline cannot be resolved no model is asked and the request fails with the reason. Each model suggestion names the pipeline version and its trace. **Suggest spans** keeps its own _Reviewer evidence suggestion_ assignment.

**Evidence from other records.** In the Evidence tab, **Cite other records…** opens the same source browser as the field editor for the chosen field, with the spans it already cites from other records of the source ticked. Confirming replaces only those other-record spans; the field's value and its spans in this record stay as they are, and the tab counts other-record spans separately. Ticking or clearing the record's own spans keeps spans cited from other records.

**Evidence for model-proposed values.** `METADATA_EVIDENCE_MODE` (default `with_value`) controls how a model-proposed value for an evidence-bearing field gets its source blocks. In `with_value` mode the model must cite blocks in the same answer; a value without a valid citation stays pending review. In `backfill` mode the model proposes only the value and DerridAI then attaches the best-matching blocks by text match (at least a 50% weighted match, at most two blocks). Backfilled evidence is marked as such, has no confidence, keeps the field pending review, and is never eligible for autofill. A build request may override the setting with `evidence_mode`. When enrichment leaves an evidence-bearing value without cited blocks, or you confirm or save a value that has no bound evidence yet, DerridAI runs **evidence recovery** over the record's own blocks, using the pipeline assigned to _Evidence recovery_ in Pipeline Studio. Each stage runs only if the one before it found nothing. Three built-in versions are available. `evidence.recovery.celf@1` is the lean direct-support chain: it tries deterministic textual support and, if enabled, a closed-choice model over the Record's source units; it does not use embeddings or a cross-encoder. `evidence.recovery.cascade@1` is retained for reproducibility and is non-cELF-guaranteed because semantic/CrossEncoder/MMR relevance could reach provenance without a support decision. The built-in system assignment now uses `evidence.recovery.cascade@2`. Version 2 keeps the richer recall but changes the authority boundary: direct support still wins immediately; otherwise semantic retrieval, CrossEncoder reranking and MMR only produce a bounded candidate shortlist. Those relevance scores can never establish evidence by themselves. A candidate reaches provenance only after deterministic direct-support validation or a closed-choice model decision over at most four ranked candidates; when semantic retrieval is unavailable, that model may fall back to the Record's source units. The result is still advisory, confidence-free and pending review until a reviewer binds it. The closed-choice stage is enabled by default during enrichment (`METADATA_EVIDENCE_CASCADE_LLM_ENABLED=true`) and runs only after cheaper support/retrieval stages fail to settle the field; set it to false to disable the final model fallback. Confirming or saving a value never spends a model call. By default the model stage asks the primary provider and then, if it gives no valid answer, the review provider, two attempts each. A Pipeline Studio clone can choose the provider and the number of attempts for each model stage, change the candidate scope/limit, or ask one provider and fall back to the other through a second model stage. The stage's trace records the candidate count and names the model that answered. Any result names the pipeline version and trace. If a record has no source-document identity, recovery does not run and the field stays pending review with that reason in the log. Evidence you bound yourself is left alone. Pipeline Studio computes the guarantee boundary from the graph: only support-validated or closed-choice candidates may feed provenance for a cELF-compliant recovery pipeline, and the provenance check cannot be removed.

- **Deciding metadata.** The **Metadata** tab lists the fields still to decide first, each open with its proposed value, its source, and the model's reason. Fields the record cannot be accepted without come first and say **Required to accept**. A proposed value sits in its value control, so you can change it in place and the usual decision is one press of **Confirm**. The evidence tools (**Select from text**, **Select all text**, **I know this**, **Cite other records…**, **Evidence**) are in the field's **Cite evidence** menu. Every field has the same two buttons in the same place: **Confirm** (or **Save value** once you change it) and **No value**. A model-supported absence is shown as a starred **No value** suggestion; the scholarly field remains empty, and confirming it records cELF `no_supported_value` / confirmed absence rather than inserting placeholder text. `Ctrl+Enter` (`⌘Enter` on Apple platforms) confirms from inside the field. Decisions update the review state optimistically before the persistence request finishes, so focus can move immediately to the next field. In the **Metadata** queue, finishing the last metadata decision advances to the next record; in other queues, it hands focus to **Accept & next** because completing metadata does not itself accept the record. A decided field folds to one line where it was, so nothing below it moves. Fields that already have values, fields you can add, and inherited document metadata are one-line rows under their own headings; **Edit** opens a row, **Cancel** closes it unchanged. **Save with selection** saves the value with the selected record text as its evidence. Cache, document-metadata and raw-JSON tools are under **Advanced metadata**.
- **Evidence confidence.** A percentage beside bound evidence is confidence in those cited source spans, not confidence in the metadata value by itself. If no valid span is bound, the Evidence tab says **No evidence yet** and shows no evidence percentage; an unbound model score is not treated as evidence confidence.
- **Save all suggestions.** When the model has proposed values for fields still awaiting review, the Metadata tab offers **Save all suggestions**. It saves every such value on the current record at once, as your decisions, in one revision, exactly as if you had confirmed each field: disputes are resolved and each value can become a reviewed precedent. It has no settings. A field held for a blind second opinion is not changed, and the status message says so.
- **Similar reviewed precedents.** Under each field still awaiting a decision, **Similar reviewed precedents** shows how reviewers decided the same field on similar passages in other records, with the evidence they cited there: ordinary answers, corrections (the model's rejected value and the reviewer's value), and confirmed absences. Metadata enrichment keeps the precedents it retrieved for its prompt, so the control can show the retained count before you open it; when the record is opened those references are checked again against current reviewed records, and precedents that changed or are hidden while you owe a blind second opinion are omitted and counted as stale. **Search again** runs a fresh search that includes newer reviews. The panel says whether matching used meaning or, when embeddings are unavailable, shared words; each precedent keeps the redesigned kind badge, similarity meter, source line, and warning for an excerpt that is not reviewed evidence, and a failed load offers **Try again**. **Use this value** only fills the field draft and saves nothing. Where this record has passages resembling a precedent's evidence, they are listed as possible support by page, time range, or passage; **Like reviewed precedents** in the Evidence tab offers the same passages as suggestions. A precedent's own evidence is never cited for this record: the reviewer still chooses this record's evidence before saving.
- **Research claims citing this record.** Also on the Metadata tab, this lists claims a reviewer validated in the Research Workspace that cite the record, with their citation. A claim bound to an earlier revision is marked as such. It is context only and never suggests metadata.
- **Deciding the record.** One bar runs along the bottom of the workspace. On the left it says how many metadata decisions still block the record and which fields; click it, or press `M`, to jump to the first one. Then come **Undo** and **Redo**, **More actions**, **Skip**, **Reject & next** (`R`), and **Accept & next** (`A`). While you edit the record text, the bar holds **Cancel** and **Save and mark reviewed** instead.
- **More actions** (in that bar) holds **Combine with previous record**, **Combine with next record**, **Split or create record** and **Preview JSONL**. An action that is not available stays in the list and says why, for example that there is no previous record to combine with.
- **Splitting, combining and creating records.** These edits are only possible inside a Corpus Build, before publication. They never edit a Record in place: the affected Records are _retired_ (kept as lineage, their IDs never reused) and new Records with new IDs take their place. Text is conserved, so no text is lost, invented, duplicated or reordered, and an edit that would change it is refused. New Records start unreviewed and are queued for enrichment; metadata confirmed on a retired Record is kept with it and is not copied across.
  - **Combine with previous / next** retires two Records and creates one.
  - **Split or create record** opens a dialog. Click to place a cursor and choose **Split at cursor**: one Record is retired and two are created. Or select text and choose **Create record from selection**: the selection becomes a new Record, and the text before and after it either joins the previous / next Record (which is then also replaced by a new Record) or becomes a separate Record of its own.
  - Each new Record carries a lineage note naming its parents; retired Records are listed at `/api/pdf/corpus-builds/{build_id}/retired-records`. Undo restores the original Records.
- **Undo** and **Redo** (`Z`, `Shift+Z`) are in the decision bar.
- **The queue** shows each record's state as an icon and a name (Accepted, Rejected, Reviewable, Metadata, Topology, Source problem). Above it, the queue tabs filter by state, **Bulk actions** holds **Bulk edit metadata** and **Reject selected**, and **Accept clean** accepts every reviewable record at once.
- **Resizing.** Drag the divider between panes or the workspace-height divider, or focus it and use the arrow keys (Shift for bigger steps, Home and End for the limits); double-click to reset. Widths and height are remembered in this browser and cannot force the decision bar below the desktop viewport.
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

The record header keeps navigation available while the text or inspector is scrolled. In Record View and Focus Review, `Alt+Left` / `Alt+Right` moves to the previous or next record without moving the page. In Focus Review, `Escape` closes the review surface and `Ctrl+S` (`⌘S` on Apple platforms) saves reviewed text while the text editor is active. In the Corpus Builder review workspace, `J` / `K` move through the queue, `A` accepts, `R` rejects, `M` jumps to the first metadata field to decide, `F` opens Focus view, and `Ctrl+Enter` confirms the metadata field you are in. Shortcuts are ignored while typing in another editable control. The `?` control beside record actions lists the shortcuts available in the current surface.

Focus view uses the same panels and decision dock as the review workspace: the record with its surrounding context, the Metadata / Evidence / Source tabs, and one dock with what still blocks the record, undo/redo, More actions, and skip / reject / accept. A slim bar under the header shows how much of the build is accepted. Accepting a record with open metadata decisions keeps you in Focus view and moves to the first open field. The surrounding-context window fits itself to the record: a long record shows few or no neighbours, a short one shows more. In the Evidence tab, pick a field (fields with a value but no evidence come first), then tick the source spans that support it; filter the list by text or to the selected spans. While editing a field, text you select in the record is previewed as the evidence "Save with selection as evidence" will cite. Where a field has a fixed list of values, the model's proposal is listed first and marked "Suggested".

## Vector Store search

Each database search method runs a versioned Pipeline Studio pipeline of the same name: **Similarity** (`store_search.similarity`), **MMR** (`store_search.mmr`), **Hybrid** (`store_search.hybrid`), **Lexical** (`store_search.lexical`), **Keyword** (`store_search.keyword`) and **Filter** (`store_search.filter`). Results are unchanged by this; what changed is that each method's steps and fallbacks are visible in Pipeline Studio and every search records a trace. Hybrid search lists records by filter when the query is empty, continues with its lexical leg when a collection cannot embed queries, and uses record-text matching when the query has no searchable words; Lexical search uses record-text matching for an empty query or one with no searchable words. The response names the pipeline version and trace that produced it. The trace keeps the collection, embedding model, counts and score types, and the names of filtered fields, but never the query text or filter values. An API request may use `mode: "assigned"` to run the _Vector Store search_ assignment (the similarity pipeline unless an administrator changes it), and administrators may name an exact saved version with `pipeline_id` and `pipeline_version`. Permissions, researcher text limits and collection visibility are enforced by DerridAI, not by the pipeline.

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
- **Automatic sizing** (optional; manual count-based sizing remains the default)
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

While a run is generating its answer, the workspace streams a live draft of the text as the model produces it, clearly labelled as an unverified preview whose citations are not yet bound. The draft is replaced by the final, source-bound answer as soon as the run completes; if the stream is interrupted the draft simply stops updating and the final answer still arrives normally.

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
- prior-response memory (optional advisory guidance)
- prior-claim provenance memory (optional advisory guidance)

With **Automatic sizing** enabled, `k` and `fetch_k` remain bounded baselines rather than fixed evidence-size assumptions. Research samples the collection's median Record length, increases candidate depth only for unusually short Records, collapses short consecutive same-document hits into bounded reranking regions, and then restores the constituent/adjacent Records as separately identified context after reranking. Neighbors keep their own Record IDs and provenance. The rerank top-N and total evidence-character budget remain capped, and neighbor context is limited to a fraction of the existing evidence budget. This avoids giving finely segmented corpora less documentary coverage merely because they contain more, smaller Records. Enable it for a run under **Research → Expert settings → Retrieval**; the same browser default is available under **Settings → RAG pipeline defaults**.

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
- generated claims with explicit evidence-marker support bindings when the answer contains `[[E0]]`-style markers. These bindings are re-resolved against the canonical Record revision before they are treated as current; prior answers and claims never become current source evidence.
- an inline **Review generated claims** section directly beneath the completed answer. Each citation-bound claim shows its current audit status, bound evidence, and **Validate claim**, **Reject claim**, **Mark unresolved**, or **Reopen** actions. Selecting a bound citation focuses that evidence in the Research evidence panel. The older Record → Traceability claim-audit path remains available for provenance inspection.
- **Re-run with parameters**, which repopulates RAG Research with the original run configuration so it can be modified before launch
- **Analyze & grade**, which asks the selected LLM provider to evaluate query relevance, source binding, claim traceability, attribution/source discrimination, claim/evidence fidelity, conceptual precision, coverage, interpretive usefulness, and overall quality

### Response Library

Every successfully completed RAG answer is written to the logical `_response_cache` Chroma collection as an eighth pipeline stage. The cache uses deterministic local vectors so writing a completed answer does not depend on Ollama or another embedding service being online.

Research memory is stored separately from that deterministic response cache. Two independent Research settings, both off by default, use it:

- **Use cached responses to steer answers** finds earlier answers to questions similar in meaning to the new one and shows them to the model as advisory context. Only answers graded at or above `RESEARCH_MEMORY_MIN_GRADE` (overall score out of 10, default 7) are eligible; ungraded answers never steer, and an answer graded by the model that wrote it is labelled self-graded. Grades are stored with the durable response, so re-grading an answer can add it to or remove it from this memory.
- **Use cached provenance to steer claims** finds reviewer-validated claims similar to the question, with the citations their support bindings recorded, and checks each cited record against the run's evidence: present, revised since validation, or absent. The model is told that support absent from the current evidence cannot be cited. A claim cannot be validated, indexed in validated-claim memory, or rebuilt into that memory unless it has at least one usable support binding to a Record; legacy or malformed validated rows without usable support are ignored by the projection.

Neither setting adds remembered text to the evidence packet or lets it supply a citation. Both match by meaning through derived, rebuildable projections; if the embedding service is unavailable they fall back to shared-word matching and the run's warnings say so. The run records which prior responses and claims steered it.

The **Response Library** page provides:

- question/answer browsing
- search over cached questions
- provider/model/time/evidence-count context
- retained query decomposition and retrieval diagnostics
- retained evidence records
- persisted grades when a response has been analyzed
- re-run with the original parameters
- re-grade with any configured LLM provider

## Pipeline Studio

Pipeline Studio is an administrator workspace at **AI & Automation → Pipeline Studio**. It separates two questions: what a pipeline is **for** (its purpose, grouped into Research, Evidence, Search, Metadata, Memory and Corpus processing workflows) and **how** each stage does its part (the stage's strategy). The same strategy, such as semantic retrieval or cross-encoder reranking, can appear in several workflows; retrieving or ranking a passage never makes it evidence. Pipeline Studio has four sections, chosen with the tabs under the page heading; the selected section, pipeline version, strategy, execution, filters and Operations tab are kept in the page address, so Back and Forward restore them. **Help** opens a dialog that explains how the Studio is organized, its core terms (pipeline, used for, purpose, stage, strategy, scholarly effect, connection, assignment, execution trace), the pipeline lifecycle and how to read a pipeline graph. The catalog, metrics and execution list update on their own when pipelines, assignments or execution traces change; there is no Refresh button, and updates never change what you have selected.

- **Pipelines** lists each pipeline once, grouped under **Used for** workflows, with its precise purpose (for example Evidence → _Reviewer evidence suggestion_ and _Evidence recovery_) and its active and latest versions; expand **N versions** to choose an exact immutable version. Search, **Used for**, and **Status** narrow the list. Selecting a pipeline opens its assigned version, else its highest active executable version, else its latest. The selected version starts with its name, version and status badges (**Active assignment** or **Not assigned**, **Executable** or **Inspect only**, **Valid** or **Invalid**); the raw pipeline ID, what it was derived from and whether it is built in are under **Technical details**. A runtime or validation problem is explained directly below. **What this pipeline does** follows: the workflow and purpose, where DerridAI uses it, its input and output, what its output establishes and its required guarantees. The pipeline diagram comes next, with **Fit diagram**, **Zoom out**, **Zoom in** and a **Layout** menu (horizontal or vertical, compact, standard or wide spacing, reset layout); stages are draggable cards, the background pans, and the viewport can be resized. Solid arrows are the normal path, unavailable fallbacks use a dash-dot line, and timeout fallbacks use a round dotted line. Select a stage to read its strategy, family, scholarly effect, input and output; each stage states its effect, such as **Produces candidates — not evidence**, **Relevance ranking only — does not establish support**, **Evidence eligibility gate** or **Provenance gate**. **Stage details** gives the full list. **Clone & edit** prepares a new immutable version that keeps the source pipeline's purpose (to build a pipeline for another workflow, start from a pipeline of that workflow). The editor is graph-first: choose a stage in the diagram or the **Stages** list (**Add stage** and each row's **⋯** menu move or add stages; connections, not list order, define how execution flows), and edit it in the stage panel beside the graph — its ID, strategy, enabled and entry flags, normal and fallback connections, and configuration. **Version details** holds the pipeline ID, version, name, status and notes, and opens by itself when one is missing. The strategy picker lists operations the workflow's runtime supports first; under **Advanced**, **Show operations this workflow cannot run** reveals the others, which keep a saved version inspect-only, and operations that would change what the workflow returns are listed but cannot be chosen. A status badge shows **Not validated**, **Valid · Executable**, **Valid · Inspect only** or **N changes required**, and **Changed since last validation** once you edit after validating. **Validate** and **Save version** check the draft on the server; saving never activates it. **Make active** changes the system assignment for the feature that consumes the purpose without rewriting past runs; it is unavailable, with the reason shown, for versions that are not active or not executable.
- **Strategies** lists every operation a stage can run in a table with its family, computation (deterministic, learned model, generative model), input and output, scholarly effect and how many pipelines use it. Search, **Family** and **Scholarly effect** are always visible; **Filters** adds computation, required capability and the workflow that uses it, and shows how many are active. Selecting a row opens the strategy panel: an overview, **Inputs, outputs and cost** (each input and output with its data type, the declared time and space cost, and observed latency, time per candidate and per-model timings from recent runs), the pipelines that use it (each opens that exact version in Pipelines), and **Technical details** with its ID, data types and settings.
- **Executions** queries the full run history. A list of runs (started, used for, pipeline, status, duration) sits beside the selected run; each run leads with its workflow and purpose, and the raw feature ID, pipeline version, resolved hash, run ID and owner are under **Technical details**. Search, **Used for** and **Status** are always visible and **Filters** adds purpose, pipeline and owner; filtering runs when you choose **Apply filters**. Selecting a run draws the same stage graph with runtime status, timing and counts, and **Open configuration** returns to the saved version. A row's **⋯** menu opens the configuration or deletes that one trace (**Delete execution**); **More → Clear execution history** removes every trace. Definitions and assignments stay in place.
- **Operations** has three tabs: **Health**, **Compare** and **Benchmarks**. **Health** shows sampled runs, failures, runs with fallbacks and 95th-percentile time, then **Needs attention**: the workflows and strategies with failures, issues or fallbacks, worst first. A workflow row opens the matching Executions filter; a strategy row opens that strategy, because executions cannot yet be filtered by strategy. **Compare** runs two saved Research pipelines against the same question and corpus without generating an answer, and lists the final evidence aligned by Record so you can see what each pipeline ranked, and what only one of them selected. **Benchmarks** lists saved cases; **New benchmark case** records a question, retrieval controls and the corpus/index fingerprint in a dialog, and a saved case is never edited (use a new version). Running a case compares two pipelines on it, refuses to run if the corpus or index has drifted, and shows the same aligned result with the case, run ID, fingerprint and pipeline hashes under **Provenance**. Neither comparison declares a better pipeline. Health figures describe computational health (runs, failures, fallbacks, latency); a faster or more reliable workflow is not a better scholarly one.

### Building a pipeline, and reading its inputs, latency and cost

**New pipeline** (above the pipeline list) builds a pipeline from scratch. Choose the workflow it is for; the dialog shows what that workflow hands every run (its **run inputs**, for example a query), what the pipeline must return, and the guarantees always enforced. You start with one valid stage and add the rest, so there is never a blank, unsaveable canvas. A pipeline is for one workflow and that does not change; to build for another workflow, start a new pipeline.

- **Add a stage** opens a searchable palette. Each stage shows what it **takes** and what it **gives** as typed data (query, candidates, context packet, model output, evaluation), its declared cost, whether it calls a language model, and how long it typically takes from recorded runs. Choose where it goes: as a next step after the selected stage, between the selected stage and what follows it, or as a new starting point fed by the workflow. By default only stages that can receive what that position provides are listed, and a count says how many were hidden; clear the filter to see the rest, each with the reason it does not fit.
- **Inputs and outputs** in the stage editor lists every input the stage declares, its type, whether it is required, and where it comes from. By default an input is wired automatically from the stage's connections (the first input takes what the previous stage gives; a starting stage takes the workflow's own input; other inputs such as the query take the workflow input of that name). **Source** replaces that with any earlier stage's output of a compatible type, or a workflow input. Choosing a stage that does not yet run before this one adds the connection that makes it so; a stage that runs _after_ this one cannot be chosen, because that would form a cycle. Outputs list which stages use them.
- **Inputs are guaranteed, not assumed.** Validation refuses to save a version in which a required input has no source, a source is the wrong type, several sources feed an input that takes one, or an explicit binding points at a stage that does not run first or no longer exists. Renaming a stage updates the bindings that name it; removing one drops them; changing a stage's strategy clears its explicit bindings because ports belong to the strategy. The diagram marks stages whose inputs cannot be satisfied.
- **Runtime adapters take their inputs from the connections.** A version that only restates the automatic wiring runs as before. A version that rewires an input to a different source runs for **Vector Store search** and **Evidence recovery**. For every other workflow it is saved and can be inspected and compared, but stays **Inspect only** and cannot be made active, and the editor says so; those workflows' runners are still code that assembles its own steps.
- **Fixed values.** A tuning input (the result limit on **Top-K selection** and **MMR**, MMR's diversity weight, the fusion constant, and a retriever's candidate depth) can be set to **A fixed number** in its **Source** menu; a number field appears with the allowed range. A fixed value can only narrow a result count, never raise it above what the request asked for. Query, candidate and other data inputs never take a fixed value. A version that uses one is inspect-only everywhere except Vector Store search.
- **Run warnings and edge labels.** A run whose explicit bindings differ from the diagram's own connections says so above its trace (**This run used explicit input bindings…**). In the diagram, focusing or hovering a stage labels the data type its connections carry, and an arrow that only makes one stage run before another (it hands over no data) is drawn dashed and labelled **Runs first (no data)**.
- **Latency** (a tab beside **Complexity**, below the diagram) estimates how long the pipeline takes from recorded executions. **Typical** sums each stage's median, counting a fallback stage only as often as it was reached; **Slow day** sums each stage's 90th percentile (an over-estimate, since stages are rarely all slow at once); **Longest chain** is the slowest unbroken path, the lower bound if parallel branches overlap; **Measured whole runs** are actual end-to-end times of completed runs of this exact pipeline. Every stage says where its figure came from (this exact pipeline, the same stage in other versions, or the strategy in any pipeline) and its sample size, marks thin samples, and shows time per candidate and per-model timings where recorded. Stages with no recorded runs count as unknown, not zero, and the totals are labelled lower bounds. Latency is operational measurement only; it says nothing about whether a result is right.
- **Complexity** also shows measured growth against the size of the collection searched (shown as N), once enough runs of different collection sizes have been recorded; traces record only the collection's item count for this. It states what the pipeline's cost depends on, using the letters n (candidates a stage receives), N (items in the collection or Record scope it searches), k (items kept), L (text length per item), q (query length), g and P (tokens generated and in the prompt), d (embedding size) and S (source units in the Record). It names the costliest step, which stages grow with the size of the collection, how many candidates any later stage can receive (from the limits set on retrieval; when a retrieval stage has no limit, the request sets it and the panel says so), and worst-case model calls by kind. Costs are declared per strategy from its implementation, not measured; **Measured growth** fits elapsed time against the candidates a stage received when enough runs exist, so a declared cost and observed behavior can be compared.
- The diagram's **Structure / Latency / Complexity** switch shows the typical time or the declared cost on every stage. The **Strategies** panel shows each strategy's inputs, outputs, declared cost and observed latency.

## Compare

Compare is a Vue-native two-column workspace at **Tools → Compare**. Each column can independently show a **library** record (loaded JSONL files for administrators, corpus-database summaries for researchers) or an **editable copy**. Use **Load into editor** to populate A or B from any existing record, then edit the JSON/JSONL without changing the source until you copy it elsewhere. **Copy A into B** makes a working duplicate. Field differences update as soon as both sides parse as a single JSON object. Audit `updates` history is excluded from the comparison. Researcher accounts cannot mutate corpus records from this page.

## Help center

The **?** button in the top bar opens a short help dialog; **Open the help center** opens the full Help Center. It now has three coordinated ways to find an answer:

- **Guides for every page** — every application route that renders a page has a Help Center guide explaining what that page is for and its main tasks. A separate **What this affects** callout appears only where actions on that page can persist, publish, configure, or otherwise change downstream state. Read-only and explanatory guides do not repeat an artificial impact section. The list follows the same role and capability boundaries as the application, so administrator-only workspaces are not advertised to users who cannot open them.
- **Glossary & parameter reference** — technical concepts used by Search, Research, Corpus Builder, Pipeline Studio, metadata memory, and vector storage are defined for non-technical academic users. Concepts such as LLMs, embeddings, RAG, MMR, reranking, cross-encoders, reciprocal-rank fusion, provenance, FieldAssertion, SourceSpan, Chroma, and derived indexes are shown as scan-first definitions. Tunable controls such as `top_k`, `fetch_k`, MMR lambda, similarity thresholds, and evidence budgets are separated into a parameter reference that explains what each control changes and its typical trade-off.
- **Common workflow questions** — the FAQ covers recurring user tasks and failure modes as well as provenance-sensitive decisions: when to use Search versus Research, why Search returns nothing, how evidence selection works, retrieval modes, missing citations, reruns, model choice, slow runs, provider/model unavailability, Corpus Builder review states, missing confidence, retry versus rerun, requeueing, publication visibility, metadata failures, record review, memory, grading, and claim validation. Downstream-impact callouts appear only when the action actually changes later behavior.

One search box searches page titles and descriptions, page tasks and downstream effects, glossary concepts and parameter definitions (including aliases such as “cross-encoder” and “nucleus sampling”), and workflow questions. Concept filters narrow definitions to AI & models, retrieval & ranking, evidence & provenance, or storage & indexes; parameter settings remain in their own reference section. Search result counts are announced to assistive technology, the page has keyboard-visible focus states, and the layout collapses to one column on smaller screens.

## Settings

Settings is a Vue-native control center at **System → Settings**. A contents rail (a collapsible **Contents** control on smaller screens) groups:

- **Workspace and appearance** — accent theme, light/dark/system color scheme, contrast, and **About DerridAI** (copyright and release identity, including the version and codename; administrators also see the git commit, and the sign-in screen shows it for build identification). Theme choices are stored in this browser workspace, not on the server.
- **Language and accessibility** — interface language, applied immediately. Dictionary editing remains on **Languages**.
- **Research defaults** — response language for generated answers. Per-run generation still lives on **Research**.
- **Review and AI behavior** — default provider profile, review preset, and interactive vs background LLM review.
- **Providers and models** — readiness summary only; credentials and endpoints stay on **LLM Providers**.
- Record field definitions live on **System → Metadata schemas**, not in Settings. Corpus Builder still offers **Manage schemas…** as a shortcut to the same editor.
- **Vector stores and retrieval** — the default embedding provider/model is server-owned and shared by ordinary Chroma collection creation and DerridAI's rebuildable internal vector projections; RAG retrieval budgets remain browser workspace preferences, with advanced MMR/RRF options behind a disclosure. Named provider profiles can be selected as the embedding default so endpoint credentials and model identity stay aligned. The current Chroma path is read-only here; change the backend on **Vector Stores**. **Test embedding model** embeds one short string with the values on screen (saved or not) and reports whether the provider and model are reachable, the vector size, the latency, and, on failure, the error with a suggested fix (for example a model that must be pulled, or `localhost` that means the container itself). The same check runs when the page opens.
- **Security, users, and permissions** — links to **Users** and **Roles & permissions**.
- **System and operations** — backup/restore, data retention, viewer resets, desktop notifications, and NUKE.
- **Data retention** (System and operations, administrators) — how long operational history is kept: pipeline traces (one store per feature), pipeline benchmark results, finished job history, and saved Research responses (the Response Library). The system-wide policy keeps everything, removes records older than N days, or caps each store at N gigabytes (1 GB = 1,000,000,000 bytes of stored data), removing the oldest records first; each store can use that policy or its own. The default keeps everything. Corpus records and sources, review decisions, field assertions, metadata precedents, validated claims, response memory, pipeline definitions, benchmark cases, and user accounts never expire. A Research pipeline trace is kept while its Research job exists, and running jobs are never removed. The table shows each store's records, size, oldest record, and what the saved policy would remove now; **Apply now…** asks for confirmation before removing anything, and a saved policy is also applied automatically every hour. Removed records free space inside the system database; **Reclaim disk space…** compacts it so the file shrinks.

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
4. corpus source assets, builds, publications, and backup/restore temp directories;
5. browser IndexedDB workspace state and DerridAI `localStorage` keys.

Installed Ollama / embedding model files under `data/models` and `data/ollama` are not deleted.

## Dashboard details

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

**System Data** is an administrator-only storage workspace with five bookmarkable
sections: **Overview**, **Responses**, **Metadata examples**, **Databases**, and
**Advanced**. The overview explains the role and current availability of each
store without treating every store as a database.

- **Application data** (`system`) is durable application state such as provider
  profiles, annotations, installed languages, and jobs.
- **Identity and access** (`auth`) contains sensitive authentication and
  authorization state such as users, roles/permissions, sessions, and login
  security data.
- The Storage overview, Saved responses, Metadata examples, Metadata memory, Response Library and Vector Stores pages update on their own when the underlying data changes (for administrators, over the live connection); they have no Refresh buttons. The Databases and Advanced inspectors read raw tables on demand and keep **Refresh**.
- **Saved responses** are generated research responses and their grades. They are
  operational history, not a corpus or research source; use **Response Library**
  for normal reading.
- **Metadata examples** are evidence-bound, derived projections from reviewed
  corpus metadata. The detail view preserves field/value, review authority,
  source record and revision, build/scope, schema, evidence blocks, hash, and
  bounded evidence context.
- **Metadata memory** (its own System page) is the audit view over the same
  index: each precedent is joined to its record revision, bound evidence, and
  whether the source is still current. Filters apply as you change them, and
  long evidence expands on demand. **Metadata examples** shows the raw index
  rows without those joins, for debugging the index itself.
- **semantic_memory_outbox** (Databases) is the refresh queue: after a review
  changes, the record waits there until its examples are re-embedded, so a
  backlog means Metadata memory can lag the reviewed corpus. Every table in the
  Databases workspace has an info tooltip explaining what it holds.
- **Internal vector collections** are DerridAI-owned derived projections. The
  Advanced workspace exposes only these system collections through a restricted,
  read-only command console; corpus collections and mutation commands remain
  unavailable there.

The database browser is intentionally inspection-first and read-only by default.
Its backend exposes explicit per-table/per-operation permissions; generic raw JSON
insert/update/delete is not enabled merely because a table exists. Changes to
users, roles, providers, languages, or other managed objects should use their
purpose-built administration surfaces so domain validation and audit behavior
remain intact. Sensitive credential and session material stays redacted.

Each workspace loads independently. A vector-backend failure does not prevent
inspection of SQLite data or saved responses, and empty, unavailable, not-built,
and no-match states are shown separately. The former **Response Cache** URL remains
a compatibility alias and opens the Responses workspace.

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

- in-flight background execution is process-local; durable job history survives restart, while interrupted work is marked failed rather than automatically replayed;
- browser workspace persistence is origin-specific;
- PDF Explorer's ad hoc extraction does not OCR image-only pages; Corpus Builder can explicitly OCR PDF/image sources;
- first use of a cross-encoder can require a model download;
- simultaneous independent writers to the same Chroma persistence path are unsupported;
- cancelling a Chroma upsert waits for the current batch to return;
- vector/reranker calls that do not expose a cancellable stream stop at the next pipeline checkpoint;
- clearing `updates` permanently removes that local audit history.
