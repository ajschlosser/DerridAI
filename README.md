<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# DerridAI Corpus Viewer 0.35.10

DerridAI Corpus Viewer is a local-first Docker application for editing philosophical JSONL corpora, auditing records with local or OpenAI-compatible LLMs, linking records to source PDFs, managing persistent ChromaDB collections, and running an evidence-grounded DerridAI RAG pipeline.

The UI footer displays:

```text
© 2026 The New England Transcendentalist Club of California
```

Source files carry:

```text
Copyright 2026 Aaron John Schlosser, PhD.
```

## Start

```bash
cp .env.example .env
docker compose down
docker compose up -d --build
```

Open:

```text
http://localhost:8181
```

API documentation:

```text
http://localhost:8000/docs
```

Storybook frontend development server (opt-in Docker profile):

```bash
docker compose --profile dev up storybook
```

Open `http://localhost:6006`. The Storybook service bind-mounts `web/` for
frontend iteration and keeps its container-managed `node_modules` in a separate
volume. You can also run `npm run storybook` directly from `web/` after
installing frontend dependencies.

PowerShell:

```powershell
Copy-Item .env.example .env
docker compose down
docker compose up -d --build
```

## Default models

```env
EMBEDDING_PROVIDER=ollama
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
```

The default LLM review preset remains **OCR / text cleanup**. The default review run mode is now **Interactive foreground**.



## 0.35.10 — Record Player
### 0.35.10 maintenance — Response FAQ polish

This maintenance patch fixes the Record Provenance Vue/TypeScript prop declaration that prevented `vue-tsc` from completing. It also redesigns Response FAQ as a research library rather than an administrative cache browser: saved questions include answer previews and evidence/model context, selected results retain the full Research answer/evidence presentation, run metadata is summarized in readable cards and definition grids, and raw technical metadata is kept behind progressive disclosure. The archive remains responsive, keyboard accessible, reduced-motion aware, and fully localized in English and professional Québec French.


Version 0.35.10 replaces the legacy Record View renderer with a Vue-native scholarly record workspace. The record identity and reading surface now dominate the page, while a resizable inspector organizes Overview, Provenance, Indexing, PDFs, Annotations, and History. Text selection exposes contextual annotation actions; annotation quotations are visibly anchored in the reading surface; the structured speaker → position holder → stance → target relation is presented as a first-class provenance component; and metadata editing now uses a side sheet that sends only changed fields into the existing audit trail.

The release also reduces toolbar overload through primary actions plus an overflow menu, adds focus mode and in-record find, preserves role/capability boundaries for every exposed action, keeps researcher records read-only except for explicitly granted evidence/annotation operations, and expands Storybook coverage for the new Record Workspace components. English and professional Québec French strings are maintained in exact built-in dictionary parity, with WCAG-oriented focus states, semantic controls, appropriately sized targets, reduced-motion handling, and responsive layouts.

## 0.35.5 — RAGety Anne

Version 0.35.5 unifies RAG-result presentation across Research, background Operations, and Response FAQ. Opening a completed RAG operation now routes the result into the same Vue-native Research result workspace instead of a separate legacy modal, so answer typography, clickable citation bindings, evidence inspection, provenance metadata, grading actions, reruns, accessibility, and localization remain consistent everywhere.

Response FAQ is rebuilt as a native research archive with searchable saved responses, a persistent response browser, the shared Research answer/evidence presentation, source-bound citation inspection, retained run provenance, and saved-grade history. Overlay stacking is also corrected so ordinary notifications and background-operation notifications render above the sidebar. Storybook gains reusable unified-result and cached-response browser components, and the new interface strings are added to both built-in English and Québec French dictionaries without overwriting existing administrator customizations.


## 0.35.0

Version 0.35.0 restores first-class concurrent Research workflows to the Vue-native workspace: every submitted RAG job remains independently visible and pollable while new questions can be launched, with actual execution still governed by provider-profile and Ollama concurrency limits. Expert Settings is rebuilt as a centered, sectioned settings studio with dedicated Retrieval, Evidence & citations, and Generation workspaces rather than a narrow side drawer.

The built-in French localization is now explicitly professional Canadian French for Québec (`fr-CA`). English and French dictionaries are kept in exact key parity, new Vue-native strings are fully localized, the compatibility renderer continues exact-label translation for legacy surfaces, and the dictionary translation workflow instructs models to use Québec/OQLF terminology, French typographic conventions, and context-appropriate Canadian usage rather than merely inferring style from the locale code.

## 0.31.3

Version 0.31.3 fixes Research startup and navigation, tooltip stacking, and expands Roles & permissions beyond the built-in Researcher role. Research now redirects users to Corpus database when no database exists (while respecting the role's database-page permission), numeric RAG settings are normalized before submission to prevent invalid-number 422 responses, and the Research page heading hierarchy is no longer duplicated. Administrators can create custom non-admin roles from a researcher-safe template, assign them to users, and configure their capabilities while preserving the same protected data boundary as the default Researcher role.

## 0.31.0 — The Pretty Release

Version 0.31.0 replaces the Research route with a Vue-native scholarly workspace centered on the research question, answer, and inspectable evidence. The answer remains inline rather than opening in a result modal; evidence occupies a persistent companion pane; common retrieval behavior is expressed through named presets; prompt recall is searchable; and expert retrieval, evidence, citation, grading, and generation controls move into a dedicated settings drawer. RAG run telemetry moves into a separate Runs drawer. The implementation keeps the 0.30.11 sparse-packet discipline, the 0.30.13 roles/capabilities contract, researcher-only provider restrictions, server-side text policy enforcement, and corpus/annotation access boundaries. New Research components are represented in Storybook and use semantic labels, native dialogs, keyboard focus states, responsive layouts, and translation keys with English/French defaults.

## 0.30.13 — Bits and Bobs

Version 0.30.13 adds configurable roles and permissions across page and API feature boundaries, makes researcher annotation/activity visibility respect the active corpus database, restores researcher record-search reliability, improves contextual foul-language screening to avoid harmless substring and proper-name false positives, streamlines Research with progressive disclosure, modernizes researcher access controls on LLM profiles, fixes Record View badge sizing and collection-wizard alignment, and expands Storybook with the role-permission matrix. Dashboard background operations are fixed open, the annotation trend graph is removed, and researcher dashboards use appearance controls instead of language administration. New UI preserves keyboard focus, semantic controls, localization fallbacks, and responsive WCAG-oriented layouts.

## 0.30.12 — All the Little Things

Version 0.30.12 is a broad UI/UX and reliability pass. It corrects citations and field-aware Global Search operators, adds dashboard work-share and annotation charts, improves Record View badges/history controls, modernizes translated-dictionary installation as a background job, adds model discovery for OpenAI-compatible providers, enforces the lowest concurrency limit across Ollama profiles sharing an endpoint, integrates researcher LLM access into the main LLM Profiles page, and standardizes researcher/admin corpus surfaces. Researcher-authored text is screened client-side for immediate warning and again server-side on researcher-writable/search/RAG endpoints.

## 0.30.11 — Big Packet Reduction

Version 0.30.11 adopts an **ONLY SEND WHAT IS NEEDED** transport rule. Record audit history (`updates`) is no longer included in ordinary LLM review, RAG evidence, Chroma search/list, or record-edit packets. Chroma record edits use sparse PATCH requests (`changes` plus only the new audit entries) instead of round-tripping entire records and their complete histories. JSONL→Chroma syncs likewise send only newly appended audit entries (or an explicit one-time replacement when history itself is being initialized/cleared), while existing Chroma history remains server-side. RAG job summaries retain lightweight selected-evidence references rather than duplicating full selected records, record fingerprints ignore audit history, and full update histories are reserved for explicit history/export operations.

## 0.30.10 — Searching for Answers Fix

Version 0.30.10 fixes the Dashboard semantic-search handoff so clicking **Search** opens Global Search with the query populated and the database search already running. Global Search now supports persisted compact-table, comfortable-table, and card result layouts for both record and database searches. Filterable metadata values are actionable search links, and generated inline/full citations use one MLA-style formatter across record, database, and work-overview surfaces. All upserts are sent in batches of at most 500 records; operations above 500 require confirmation and run in a blocking foreground progress dialog with cancellation.

Record View receives a new annotation-card layout with clearer evidence context, note content, authorship/time metadata, and actions; the missing **Clear** label is restored. Researcher Topics, Concepts, Persons, and related index values use the same resilient badge layout as the administrator record view. Compare moves pasted-record guidance into a contextual callout beside the paste workflow instead of leaving awkward informational text at the bottom.

Research is reorganized as a 2026-style workspace: the question/instructions workflow is visually primary, evidence and corpus/retrieval controls are grouped, summary settings are compact, and advanced generation/retrieval options no longer compete with the main task. Page-level access is now centralized separately from feature capabilities so shared routes can keep one page model while privileged controls remain role-gated. The release also continues the WCAG font/readability/grid pass, English/French i18n parity, and Storybook expansion with reusable Record Annotation Card and Research Workspace Header components.

## 0.30.8 — Dashboard search, Works, annotations, and user-provider cleanup

Version 0.30.8 fixes Dashboard semantic search handoff, aligns the Advanced Filters layout, changes the slogan to **“Search. Compare. Annotate. Always already.”**, tightens Corpus Overview spacing, and stabilizes the Operations Refresh/Clear Finished action area. Semantic searches launched from Dashboard now use the same one-shot auto-run contract as Global Search, so the destination opens with results already executing instead of landing empty.

Works now uses a denser overview grid, removes redundant Close actions, clarifies which corpus database synchronization status/actions refer to, and warns before metadata enrichment navigates away to provider management. The bibliographic workflow summary is reorganized into aligned status cards. Compare receives a structured explanatory header rather than an orphaned footer note. Users & Roles now manages researcher LLM profiles with reusable provider cards, provider-aware endpoint defaults, model discovery/testing, concurrency controls, secret handling, and a focused add-provider dialog.

Researchers can now create shared annotations from Record View. Selecting text opens an annotation action beside the selection and the editor itself is positioned adjacent to that passage; shared annotations are persisted server-side, organized on the Annotations page, surfaced on Dashboard, and can reopen their database record. The release also removes step-connector rules that sliced multi-step modal labels, continues the WCAG font/focus/grid pass, expands English/French dictionaries in parity, and adds a reusable **Selection Annotation Popover** Storybook component.

## 0.30.7 — Dashboard Cleanup

Version 0.30.7 cleans up the Dashboard and finishes the second Vector Stores design pass. Vector Stores now hides the redundant page-level create button in the first-run state, moves Create/Refresh into a dedicated collection workspace toolbar when collections exist, replaces the old path accordion with conventional storage settings, and repairs all three collection-wizard layouts. The Dashboard fixes duplicate language flags, runs semantic searches directly instead of landing on an empty results page, restores prominent Corpus Overview icons, adds a three-chart work-metrics carousel (average record length, total words, and record count), and previews the last viewed record with a random corpus fallback. Works carousel controls receive a modern treatment, and LLM bibliographic enrichment no longer proposes canonical work IDs. Native Vue pages now participate in breadcrumb back/forward navigation, so Dashboard → Manage Languages → Back returns to Dashboard. The release also adds aggregate work word metrics to Chroma work statistics, more localized strings, stronger accessible carousel/focus semantics, and Storybook components for work-metric carousels, storage settings, and collection-creation steppers.



## 0.30.6 — Vector Store Cleanup

Version 0.30.6 modernizes the administrator Vector Stores workspace. The collection list is always visible, first-run installations receive a branded create-collection call to action, and collection creation is now a three-step workflow for role/language, embedding configuration, and optional initial work synchronization. Loaded works can be selected during creation; selections above 400 records explicitly run in foreground batches and all other >400-record upserts display the same foreground-sync warning. Storage-path controls move into an explained advanced section, the old Hide collections control is removed, and JSONL/Chroma round-trip actions are renamed and documented around their actual import/export behavior. Pending upserts are presented as **Unsynced local changes** with explicit inclusion semantics. More tools uses the full sidebar height and opens by default for administrators. In-page tab changes preserve the current page scroll position rather than jumping to the top.

## 0.30.5 — Bibliographic metadata workflows, annotation organization, and aligned forms

**Startup hotfix:** read-only language dictionaries are available before authentication, authentication is resolved before protected runtime bootstrap, expired sessions return to sign-in without reloading the page, background polling stops on session expiry, and no-op Vue Router navigations are suppressed. This prevents the initial localization/authentication sequence from entering a reload/render loop.

Version 0.30.5 is based on the 0.30.3 research-workspace refactor and preserves its shell, researcher routes, unified search, Works carousel/overview, operations dragging, large-sync behavior, accessibility work, reusable Vue components, and Unicode language flags. It makes the language dictionary editor more translation-focused by narrowing the descriptive reference column and expanding the translation editor. The dictionary-install workflow now uses the same configured LLM provider profiles as the rest of DerridAI, and its workflow shell is reused by the new Works metadata-enrichment flow. Works can launch one background bibliographic lookup or a batch lookup for every loaded work; DerridAI searches Open Library, asks the selected LLM to identify the best matching edition, and returns field-level proposals for publisher, publication year/place, edition, translator, ISBN, language, canonical ID, citation, and cover image. Proposed values are reviewable, editable, selectable, and then applied across all records for that work with normal audit-history tracking. The Work overview now exposes richer bibliographic metadata and provides direct edit/populate/search actions. The Annotations page groups annotations by work by default while retaining a chronological Recent view, and the Dashboard now surfaces the latest annotation. This release also aligns labels, controls, and helper text across form grids and extends English/French internationalization for the new surfaces.

## 0.30.3 — Restored research-workspace baseline

The 0.30.3 baseline introduces the current DerridAI light research-workspace shell and is the direct ancestor of 0.30.5. It includes the branded sidebar/topbar, back/forward navigation history, persistent command search, configurable green/blue/slate appearance themes, Home dashboard, main **Research** navigation, Compare under More tools, single sign-out location, draggable Operations stack, and WCAG-oriented focus/readability improvements. Researcher and administrator routes share the newer Works, Record View, Compare, Global Search, Annotations, and Settings UX wherever permissions allow.

- Dashboard Works is a horizontal carousel of all works and displays saved cover art when available.
- Works opens an overview before entering search/browse, and researcher-visible works/records are sourced from the selected corpus database with 2–3-sentence Edmundson summaries.
- Global Search provides traditional/record search and semantic DB search with similarity, MMR, and metadata filters.
- Record View keeps find-in-text state, provides citation/evidence controls, and turns indexing badges into search links.
- Large upserts above 400 records use sequential foreground batches with progress/yields rather than one heavyweight background payload.
- Operations dragging uses pointer events, requestAnimationFrame, GPU transforms, keyboard repositioning, and persistent placement.
- Built-in locale symbols are standardized as 🇺🇸 and 🇨🇦.
- Reusable Storybook components include command search, language flag, work-cover card, metadata badge group, accessible empty state, action buttons, and provider-profile selection.

## 0.23.0 — Evidence workflows, researcher policy, i18n, and shareable table state

Version 0.23.0 adds multi-record evidence selection and selected-evidence-only RAG, citation copy actions, passage annotations, role/capability hardening, researcher-managed static provider profiles with provider-side concurrency waiting, user/login audit metadata, sortable researcher corpus search with highlighted terms and similarity guidance, compressed table configuration in URLs, editable language dictionaries with built-in en-US and fr-CA plus LLM-assisted locale installation, and dashboard/PDF layout refinements. Researcher-visible text now uses 2–3-sentence Edmundson summaries.

- Researcher Corpus Search has explicit loading/progress messaging, sortable table results, bolded query terms, similarity-score guidance, citation copy controls, and evidence selection.
- Inline/full citation and evidence controls are available from primary record tables, record detail, vector-store records/search, researcher corpus search, Compare, and PDF-linked record surfaces.
- Selected evidence is a first-class RAG input. Runs can pin selected records alongside retrieval or bypass vector retrieval entirely and use only the selected evidence packet.
- Admin record detail supports text selection on extracted text, source/discourse metadata, and indexing chips to attach arbitrary notes and tags; audit entries retain the initiating username.
- User administration records last login and login count. Researchers receive an explicit capability set and all unlisted API functionality remains admin-only by default.
- Admins can create server-owned researcher LLM profiles whose secrets are never returned to researcher browsers. Provider-profile concurrency limits queue researcher RAG work instead of oversubscribing a local model.
- Internationalization includes editable server-side dictionaries, en-US with a U.S. flag, fr-CA with a Unicode Canada flag, locale installation by language-location code through an LLM, and a compatibility translation bridge for legacy UI labels.
- Dashboard background operations are near the top and remain collapsible. Work-share legends show complete titles and chart points, pie slices, and bars expose hover details.
- PDF Explorer returned to natural fit-width rendering; page text and linking tools now sit below the PDF rather than forcing a wide two-column viewer.
- List/Search/Vector table configuration, filters, sorting, pagination, and query state are packed into a compact `ts` URL parameter so table views can be shared without long query strings.

## 0.22.0 — RAG grading, FAQ workflow, UI, and frontend development

Version 0.22.0 is a minor release focused on RAG grading flexibility, safer
vector-store synchronization, source-binding robustness, Response FAQ batch
workflows, comparison/PDF usability, and a documented Storybook development
environment.

- Work/record synchronization badges now verify that the selected physical
  collection still exists before treating old local upsert receipts as synced.
- Chroma upserts are limited to one active job. Both API and client reject a
  second heavyweight sync until the first finishes/cancels, avoiding duplicate
  full-work payloads competing for RAM/CPU/embedding resources. Work sync
  operation labels include the work name.
- Dashboard record-import history was replaced by a bar chart of average text
  length for the five works with the most records. Top-topic/person/work/speaker
  rankings now open corpus search for the clicked term.
- RAG auto-grade can use an independently selected provider profile. When more
  than one profile exists, the runner defaults to a grader different from answer
  generation. RAG operation cards show provider profile plus model.
- Evidence binding defaults to `[[E0]]` and accepts `(E0)`, `((E0))`, `[E0]`,
  `[[E0]]`, `{E0}`, `{{E0}}`, including multi-ID groups.
- RAG grading launch/result dialogs show the original research question.
- Response FAQ entries are collapsed by default, remember per-response expanded
  state, provide Expand all / Collapse all controls, and can grade/re-grade the
  complete response cache as one background job with a chosen provider/model/
  generation configuration.
- PDF Explorer renders its page canvas at about 80% of fit width by default and
  sends a bounded pre-ranked packet to PDF-to-record matching, reducing
  provider context-limit/HTTP 400 failures.
- HTTP failures use a dedicated failed toast state and retain the HTTP status in
  the visible diagnostic.
- Record Comparison received a larger, cleaner picker and summary layout plus
  substantially more readable side-by-side A/B field/text diffs.
- Storybook is included for the native Vue components with a Docker development
  service (`docker compose --profile dev up storybook`) and component stories
  for ActionButton, AppIcon, AuthScreen, and the Vue/legacy compatibility
  surface.



## 0.21.1 — FAQ, grading, and comparison bug fixes

Version 0.21.1 fixes three post-0.21.0 regressions: background RAG grade result rendering, response-cache FAQ visibility, and record-comparison autocomplete behavior.

- RAG grade rendering now normalizes common model JSON variations (including scalar/object list fields and nested score objects), so a non-canonical but usable grader response cannot crash the result modal. New grades are normalized server-side before being cached, while the frontend remains tolerant of older cached shapes.
- Progressive card rendering isolates item-level render errors instead of allowing one malformed cached record/grade to blank an entire view.
- Response FAQ and Response Cache now use a dedicated logical cache reader that merges legacy `_response_cache` and current `derridai_response_cache` physical collections, deduplicates by logical response ID, sorts deterministically, supports question filtering, and exposes total/matched counts.
- Record Comparison autocomplete now anchors its result popover inside the picker, scopes DOM lookups to the active view, supports pointer selection plus keyboard navigation, and avoids the misplaced/unclickable dropdown behavior caused by the result list being outside its positioned container.

## 0.21.0 — performance and regression fixes

Version 0.21.0 focuses on frontend responsiveness and fixes regressions found after the Vue compatibility migration.

- Vector Stores remains selectable for administrators even when no corpus collection exists yet, so the first collection/storage location can always be created or repaired; only actions that truly require an existing collection stay disabled.
- PDF Explorer restores the known-good PDF.js legacy worker integration and uses the cached record autocomplete index instead of the removed `recordOptions()` helper.
- Works action menus overlay surrounding cards instead of being clipped by the card boundary.
- Works and Response FAQ cards render progressively in small batches with loading skeletons; dashboard KPIs render first while charts/rankings/recent activity fill during idle frames, and asynchronous Vector Stores/corpus search views show explicit loading states.
- Record fingerprints are cached, preference/file persistence is less eager, pending-upsert derivation is short-lived cached, and dense card lists are excluded from the generic layout-measurement pass.
- Background **Analyze & grade RAG response** results use a delegated result opener with explicit render/fetch error handling.
- Response FAQ queries the response cache directly, recovers from stale persisted page numbers, clearly identifies saved searches with zero matches, and resolves both legacy `_response_cache` and current `derridai_response_cache` physical collections so retained responses remain visible across upgrades.

## 0.20.0 — Vue 3 frontend migration

Version 0.20.0 moves the application shell to Vue 3 with TypeScript, Pinia, and Vue Router while preserving the existing Python/FastAPI API and the validated corpus/RAG feature runtime. The migration is intentionally compatibility-first: routed Vue views and reusable shell components own navigation, top-level state, disabled-action tooltips, file tabs, and lifecycle; mature feature renderers remain behind `web/src/legacy/runtime.js` and can be converted view-by-view without changing backend contracts.

Frontend structure now includes `components/`, `views/`, `stores/`, `router/`, `api/`, `composables/`, and `legacy/`. Routes use readable paths such as `/records`, `/works`, `/databases`, `/rag`, and `/settings`, while selected file/record/store state remains encoded in query parameters for deep links.

The production build now runs `vue-tsc --noEmit` before Vite, and Vite separates Vue and PDF.js vendor chunks.

### Users and roles

0.20.0 adds built-in local authentication backed by SQLite (`AUTH_DB_PATH`, default `/data/.home/derridai-auth.sqlite3`). There are no packaged default credentials. On the first browser launch, DerridAI asks you to create the first administrator account. Administrators can then manage accounts from **System → Users & roles**.

Two roles are currently available:

- **Admin** — full access to JSONL workspaces, record editing/history, vector databases, providers, PDF tools, RAG, configuration, backups, and user administration.
- **Researcher** — RAG Research plus read-only corpus database/work browsing and semantic search. The API enforces the restriction as well as the UI: corpus mutation/database-management/export endpoints are rejected, RAG jobs are scoped to their owner, and researcher sessions cannot open editable corpus/editor/system routes.

Researcher-visible corpus text is transformed on the API before it is returned to the browser. `text` is passed through a dependency-free Edmundson-style extractive summarizer with values from `topics`, `concepts`, and `persons` treated as bonus terms. Summaries contain at most 2–3 selected sentence extracts joined by ` [...] ` and respect `RESEARCHER_TEXT_MAX_CHARS` (default `1600`). Text-valued entries inside the record `updates` audit history are sanitized by the same policy. The full corpus text remains available internally to the RAG pipeline for retrieval/generation, but is not exposed in researcher job results or read-only corpus search.

Browser workspace persistence is isolated for researcher accounts so a researcher using the same browser profile does not inherit an administrator's loaded JSONL tabs, provider credentials, or other IndexedDB workspace state. Full backups include the logical user database (roles and password hashes, but not active session tokens), so backup ZIPs should be treated as credential-sensitive.

## 0.10.1 highlights

Version 0.10.1 refines the 0.10.0 architecture and adds:

- A dedicated **LLM Providers** page. Create any number of named Ollama or OpenAI-compatible/FreeLLM profiles and configure endpoint, credentials, model/model-routing mode, generation defaults, advanced parameters, and **maximum concurrent requests**.
- Provider profiles are reused throughout LLM review, Auto-improve, RAG generation, PDF LLM tools, and RAG-response grading. A workflow can select a provider without silently changing the application-wide default.
- Each provider can be tested/discovered and warmed independently. Dashboard readiness retains warmup/readiness state separately for every configured profile.
- Background LLM review, PDF LLM tools, RAG grading, and RAG generation respect provider-profile concurrency limits. Ollama remains suitable for conservative GPU-local limits, while FreeLLM/OpenAI-compatible profiles can be assigned high independent limits.
- RAG grading is treated as normal LLM functionality: provider/model/parameters are selectable and grading can run interactively or as a cancellable background operation.
- RAG grade results are persisted on the same response-cache entry as the original query, instructions, run parameters, answer, evidence, and retrieval diagnostics. Multiple grades are retained as history with grader provider/model and timestamp.
- The grading launcher explicitly warns when the selected grader is the same provider/model that generated the answer, because self-grading is not an independent evaluation.
- The logical `_response_cache` is now a system cache rather than a corpus vector store. It is excluded from Vector Stores, corpus DB counts, collection pickers, language mirroring, and RAG source selection. A dedicated **Response Cache** page manages cache status/history separately, while **Response FAQ** remains the answer/evidence browsing interface.
- JSONL files can be subsetted deterministically with multiple arbitrary field rules (`equals`, `contains`, array membership, missing/existing, truthy/falsy, regex, and others), using ALL/ANY matching. Subsets become new editable JSONL tabs and can also be downloaded.
- Bulk-field editing pre-populates the new-value input when the selected records already share exactly one value.
- LLM proposed-change selection no longer rerenders the whole result dialog, preventing checkbox selection from jumping the scroll position to the top. Live updates preserve the current review scroll position.
- Destructive LLM-job discard is no longer presented as the natural next step after accepting changes; pending-discard actions are explicit and visually secondary.
- Completed operation cards remain visible until explicitly dismissed and provide result/details actions where applicable.
- PDF Explorer uses a compact document command bar rather than the previous oversized/redundant header. Page navigation, rotation, text extraction, PDF/work/record context, and LLM tools are grouped by function.
- PDF LLM cleanup, draft-record creation, and record linking now use the same provider/model/parameter/run-mode launcher as other LLM features and can run as cancellable background operations.
- PDF record-link confirmation and newly touched error/confirmation surfaces use in-app dialogs rather than browser alerts.
- Whole-record JSON copying is available across the primary JSONL table/detail/review surfaces, Chroma record rows, Compare, PDF-related records, and RAG evidence.
- Dashboard Vector Stores are summarized compactly and Recent RAG Pipelines is a space-efficient table.
- Collapse controls are only added where collapsing removes more than half of the element's height. A collapsed card shrinks to its minimum header height and shows only its title plus the expand control.

## 0.10.0 highlights

Version 0.10.0 adds the following:

- Background LLM result review is live. Completed proposals can be accepted or rejected while the remaining records continue processing. Accepted proposals are removed from the pending-result queue immediately.
- LLM operations track `accepted`, `partially accepted`, `rejected`, and `partially rejected` decision state. Rejecting a job can dismiss it from the operations queue.
- Configuration supports any number of named Ollama and OpenAI-compatible/FreeLLM provider profiles. LLM review and RAG can switch among those profiles independently.
- Dashboard LLM readiness shows every configured provider rather than only the last-used provider.
- Operation toasts can be minimized without losing track of running work; details and cancellation remain available.
- Browser desktop notifications can be enabled for completion/failure of background jobs.
- Chroma record-table columns are configurable, sortable, and independently filterable.
- The Chroma collections rail is compact and collapsible.
- Primary-collection background upserts continue to mirror corresponding `en` / `fr` language collections.
- Completed RAG responses are automatically cached in the logical `_response_cache` collection and browsable from **Response FAQ**. Because Chroma collection names must begin with a lowercase letter or digit, the physical collection is stored as `derridai_response_cache`; DerridAI exposes it consistently as `_response_cache` through its API/UI.
- Response FAQ provides question/answer browsing, retained evidence and retrieval details, rerun-with-parameters, and LLM response grading.
- RAG result grading reports query relevance, source binding, claim traceability, attribution/source discrimination, claim/evidence fidelity, conceptual precision, coverage, interpretive usefulness, and an overall score.
- URL query parameters now carry primary application location/state (view, loaded file/record, Chroma collection/work/page, browse mode, and PDF page), and breadcrumbs support both Back and Forward.
- Compare supports either two loaded workspace records or two pasted JSON/JSONL records with the same red/green field diff used in review.
- Work metadata editing propagates changes such as title/author/publication metadata across associated records, and a general **Bulk edit field** action can update one field across selected records, an active JSONL file, the current work, or every loaded record.
- Cards, charts, tables, and inset sections receive collapsible controls, with a Configuration reset to expand everything again.
- PDF Explorer has a reorganized source → work → record layout, page rotation, LLM text cleanup, LLM draft-record generation, and LLM-assisted page-to-record matching.
- LLM-generated PDF draft records remain unsaved until explicitly added to a selected JSONL tab and/or Chroma collection.
- Dashboard adds a work-share pie chart and a five-most-recent RAG-pipelines panel; top-needs-review chart labels are shortened while retaining full-title tooltips.
- Full **Backup & restore** creates one ZIP containing loaded JSONL data, audit history, browser/UI/configuration state, provider profiles, RAG history, retained finished operation results, the current PDF, and every Chroma collection including stored embeddings. Restore validates the archive and keeps a logical Chroma rollback snapshot until restoration succeeds.
- Full backups can contain provider API keys and therefore must be treated as sensitive files.

## 0.9.0 highlights

Version 0.9.0 adds or changes the following:

- Interactive foreground review is the default LLM run mode.
- Interactive, background, and background Auto-improve modes remain switchable before every review.
- Background-review results have a redesigned no-change state and red/green word-level diffs for changed values.
- Background cancellation is explicit: jobs enter `cancelling`, show what is still in flight, and then become `cancelled`.
- Ollama/OpenAI-compatible background model calls use streaming connections when cancellability is needed, allowing cancellation to interrupt an active generation rather than always waiting for the entire generation to finish.
- RAG model generations use the same streamed cancellation behavior; vector/rerank work stops at the next safe checkpoint.
- Chroma upserts are background jobs visible from Dashboard and operation toasts.
- Upserting a primary collection automatically synchronizes matching records into its derived `en` / `fr` collections and removes records from a language collection when their language metadata no longer matches.
- Direct primary-collection record edits and deletes also synchronize derived language collections.
- Upsert receipts update local `Synced`/`Pending` status incrementally as batches complete.
- Operation toasts have expandable details, event history, elapsed time, and Cancel/Open-details controls.
- Dashboard operation cards expose model, fields/stage, target collection, current record, language mirrors, progress, and elapsed/total time.
- RAG Pipeline Activity shows generation model/provider, retrieval parameters, language scope, reranker settings, output limits, stage progress, elapsed/total time, and current stage detail.
- Works view can bulk-edit work-level metadata and propagate selected fields across every loaded record associated with that work.

## Dashboard

Dashboard shows:

- loaded records
- distinct works
- records currently needing review
- loaded JSONL tabs
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

Background operations are managed from Dashboard and also appear as stacked operation toasts.

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

Operation toasts can be expanded without navigating away from the current view. They expose a compact parameter/status summary, recent events, a full-details link, and a cancellation button while the operation is active.

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

One provider profile is designated as the default, but run dialogs can switch profiles before launch. Dashboard LLM readiness reports every configured profile rather than only the most recently used endpoint.

Model-kind filters remain a UI discovery aid; the backend still sends a standard OpenAI-compatible `model` identifier.

## Startup model warmup

After workspace restoration and API health checks, the configured default model receives a minimal warmup request. Ollama warmup respects `keep_alive`.

## JSONL workspace

Multiple JSONL files remain open as editable tabs and persist through browser IndexedDB, including:

- unsaved edits
- active file/view/record
- searches and filters
- table-column choices
- review selection
- LLM/RAG configuration
- Chroma synchronization receipts
- sidebar state

Persistence is browser-origin-specific.

### Merge tabs

Users can merge all tabs or any subset. Selected source tabs are replaced in the workspace by the merged tab; unselected tabs remain. Source files on disk are not deleted.

## Record audit history

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

Mixed values are visibly identified. Array/object values are edited as JSON. Every applied field change is recorded in each associated record's `updates` history with `source: "work_metadata"`.

Because the affected record fingerprints change, records previously synchronized to Chroma become `Pending` until the next upsert.

## ChromaDB

ChromaDB uses persistent local storage under the host-mounted data directory.

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

The dashboard and operation toast update while batches commit. Synchronization receipts are applied incrementally, so local records can change from `Pending` to `Synced` before the entire job has finished.

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
- saving a draft to any loaded JSONL tab, any Chroma collection, or both
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
- load evidence into a new JSONL tab
- cached-response identifier
- **Re-run with parameters**, which repopulates RAG Research with the original run configuration so it can be modified before launch
- **Analyze & grade**, which asks the selected LLM provider to evaluate query relevance, source binding, claim traceability, attribution/source discrimination, claim/evidence fidelity, conceptual precision, coverage, interpretive usefulness, and overall quality

### Response FAQ

Every successfully completed RAG answer is written to the logical `_response_cache` Chroma collection as an eighth pipeline stage. The cache uses deterministic local vectors so writing a completed answer does not depend on Ollama or another embedding service being online.

The **Response FAQ** page provides:

- question/answer browsing
- search over cached questions
- provider/model/time/evidence-count context
- retained query decomposition and retrieval diagnostics
- retained evidence records
- persisted grades when a response has been analyzed
- re-run with the original parameters
- re-grade with any configured LLM provider

## Configuration reset

Configuration includes:

- table-column reset
- sidebar expansion
- upsert suppression reset
- clear all record update histories
- Dashboard / Vector Stores / RAG navigation

### NUKE

Typing `NUKE` enables deletion of:

1. all collections in the current Chroma persistence database;
2. browser IndexedDB workspace state.

Installed Ollama model files are not deleted.


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

- every loaded JSONL tab and unsaved browser-workspace record state
- record audit histories / `updates`
- UI preferences, table columns, filters, navigation state, and RAG question/run history
- all configured LLM provider profiles and their generation defaults
- provider API keys when they are present in the browser configuration
- retained finished LLM/RAG/upsert operation objects and LLM pending results
- the currently loaded PDF, if any
- every Chroma collection, its collection metadata/configuration when exposed by Chroma, documents, metadata, IDs, and the exact stored embedding vectors

Backups are blocked while background operations are active so the archive is internally consistent. Large archives are assembled under the host-mounted `./data` tree rather than inside the container overlay filesystem.

**Load from backup** validates the manifest and ZIP member paths before making changes. The API first creates a logical rollback snapshot of the current Chroma database; if Chroma restoration fails, the current vector database is restored from that rollback. After a successful server restore, the browser IndexedDB workspace and current PDF are replaced and the UI reloads.

The logical FAQ collection is exposed as `_response_cache` in DerridAI. Chroma itself does not permit collection names beginning with `_`, so its physical collection name is `derridai_response_cache` and carries system metadata identifying it as the response cache.

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

## Release validation

The packaged 0.10.1 source was checked with:

- `node --check web/src/main.js`;
- Python compilation of every `api/app/*.py` module;
- FastAPI import/route smoke tests with a stub Chroma module;
- background LLM provider-concurrency lifecycle tests;
- background PDF/RAG-grade tool-job lifecycle tests;
- RAG eight-stage lifecycle plus `_response_cache` persistence tests;
- response-cache grade-history persistence tests;
- Docker Compose YAML parsing;
- CSS brace-balance and package/version checks.

A full `npm install` / Vite production build was attempted in the packaging sandbox but the dependency install timed out before completion. The JavaScript syntax check passed; build the web image normally through Docker on a networked development machine.

## Current limitations

- background-job state is process-local and does not survive API restart;
- browser workspace persistence is origin-specific;
- image-only PDFs do not receive built-in OCR;
- first use of a cross-encoder can require a model download;
- simultaneous independent writers to the same Chroma persistence path are unsupported;
- cancelling a Chroma upsert waits for the current batch to return;
- vector/reranker calls that do not expose a cancellable stream stop at the next pipeline checkpoint;
- clearing `updates` permanently removes that local audit history.
