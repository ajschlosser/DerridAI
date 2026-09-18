# DerridAI Corpus Viewer 0.49.0

**0.49.0 — Hungry Hippo** streamlines Corpus Builder review around a simple rule: deterministic constraints resolve obvious facts, valid LLM proposals arrive as editable defaults, and reviewers spend their time on genuine exceptions. It also adds reversible extracted-text cleanup for recurring headers, page numbers, hyphenation, and whitespace while preserving immutable source text.

## 0.49.0 — Hungry Hippo

- Valid LLM proposals now prefill review controls regardless of confidence; confidence changes the warning treatment, not whether the reviewer must reselect the model's value.
- Added a reusable metadata-field editor and a one-click **Save all suggestions** workflow for unresolved LLM-proposed fields.
- Centralized deterministic metadata constraints. Front matter, back matter, bibliography, index, and paratext cannot be primary text; main text is primary text. The same rule is enforced after LLM, individual human, and bulk edits.
- Added a reversible **Clean text** workflow with side-by-side preview for isolated page numbers, recurring short headers/footers, line-break hyphenation, and extraction whitespace. The immutable extracted source is never changed.
- Recurring header/footer candidates are inferred from repeated short lines across loaded records.
- Decomposed Corpus Builder review further into reusable `CorpusMetadataFieldEditor` and `CorpusTextCleanupDialog` Storybook components.
- New and changed UI is localized in English and Québec French and retains WCAG 2.0 AA-oriented keyboard focus, semantic dialog/status markup, readable typography, and responsive layouts.

### Validation in this packaging environment

- `pytest -q`: **389 passed**.
- Python bytecode compilation, locale-key/placeholder parity, runtime JavaScript syntax, TypeScript/Vue script parsing, WCAG typography-floor audit, and `git diff --check` pass.
- `npm run build` was attempted but frontend dependencies are unavailable in this sandbox (`vue-tsc: not found`).
- `npm run build-storybook` was attempted but Storybook is unavailable in this sandbox (`storybook: not found`).
- Docker is unavailable in this sandbox. The archive therefore remains a build candidate until the normal production frontend, Storybook, and container build gates pass.

## 0.48.1 — Gifted Grungus

- The initialization stepper now visually owns the screen during extraction/segmentation, with a stronger opaque backdrop and stacking above global operation chrome so the handoff is unambiguous.
- Removed the duplicate Source extraction issue panel from the Source inspector; resolution guidance now appears once, above the reviewed record text where the repair action occurs.
- Reviewed record text now has an explicit **Mark reviewed** action and **Save & mark reviewed** workflow. Saving unchanged text records a human review without blocking later LLM enrichment; edit actions remain visible in a sticky footer.
- Metadata review explicitly distinguishes records whose LLM enrichment is still queued/running from records whose model output has settled. Confidence and proposal controls no longer appear to simply stop after the first concurrently processed records.
- Quotation and semantic-indexing responses now request and retain per-field confidence assessments as well as discourse metadata, giving later records the same confidence/preselection path where the model supplies a proposal.
- Moved the LLM preselection indicator into the decision area beside confidence, using a compact badge rather than crowding the field-value row.
- Removed the confusing global “record has settled while enrichment continues” banner; live enrichment status remains in the dedicated metadata status surface.
- Rebuilt Bulk edit metadata as an opaque, focused modal with clearer scope selection, field grouping, enum dropdowns, and autocomplete from values already present in the loaded record set.
- English and Québec French dictionaries include all new review, enrichment-state, and bulk-edit copy.
- Added regression coverage for the 0.48.1 interaction changes and retained the release build/test gates.

### Validation in this packaging environment

- `pytest -q`: **384 passed**.
- Python bytecode compilation succeeds.
- Runtime JavaScript syntax checking succeeds.
- `npm run build` was attempted but frontend dependencies are unavailable in this sandbox (`vue-tsc: not found`).
- `npm run build-storybook` was attempted but Storybook is unavailable in this sandbox (`storybook: not found`).
- Docker is unavailable in this sandbox.

The release remains a build candidate until the normal production frontend, Storybook, and container build gates pass.

## 0.47.1 — Fatso

### UI/UX and component-system changes

- Added reusable `UiButton`, `UiCard`, `UiField`, and `UiStatusBadge` foundation components with Storybook coverage.
- Replaced the older `ActionButton` wrapper with the shared button primitive and refactored empty states, document metadata editing, and field-ownership badges to use current components.
- Removed release-number (`v030`) naming from the active application shell and runtime dashboard CSS/markup.
- Added shared spacing/focus tokens, consistent `:focus-visible` treatment, improved disabled states, a 40px default control target, reduced-motion support, higher-contrast support, and a 12px minimum explicit text floor for dense UI.
- Normalized Storybook organization around Foundations, Shell, Corpus Builder, Record Workspace, Search, Research, Providers, System, and Internationalization.
- Moved the role-permission story beside its component and added missing Brand Mark/foundation stories.
- Kept English and Québec French localization architecture intact; no new user-facing copy bypasses i18n.

### Validation in this packaging environment

- `pytest -q`: **372 passed**.
- Python bytecode compilation succeeds.
- `node --check web/src/runtime/runtime.js` succeeds.
- Production frontend build was attempted and is blocked because frontend dependencies are not installed in this sandbox (`vue-tsc: not found`).
- Storybook build was attempted and is blocked for the same reason (`storybook: not found`).
- Docker is unavailable in this sandbox.

### Release gate

- Backend regression suite, Python compilation, JavaScript syntax checks, translation parity checks, and archive integrity must pass.
- Production Vue/Vite, Storybook, and Docker/container builds remain mandatory before the release is considered ready.

## 0.47.0 — Gregarious Guinea Pig

### Gregarious Guinea Pig changes

- Segmented records are editable as soon as topology is persisted; metadata enrichment no longer has to finish first.
- Human edits establish field-level ownership. Background LLM results merge only into untouched fields and never overwrite human-confirmed values.
- Human text edits or completed review freeze automatic enrichment for that record; queued/running metadata families settle as explicit skips.
- Repeated human-confirmed values from at least two records become conservative build-local editorial context for later prompts without being propagated as truth.
- Reviewed-text drafts are persisted locally and remain pinned while queues update in the background.
- Added selected/all-record bulk metadata editing with PATCH semantics.
- Reworked document metadata editing into grouped, change-only sections and permitted bibliographic corrections while enrichment runs.
- Inherited metadata now appears after interactive record metadata.
- Cancelling enrichment leaves the segmented workspace usable; cancelled builds can be resumed, and the user can explicitly start a new/concurrent build.
- Added Storybook coverage for bulk record metadata editing and retained keyboard/focus/accessibility checks.

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

**0.46.1 — Gray Fox** is a maintenance and interface-quality pass: canonical English and Québec French dictionaries are now first-class locale modules, obsolete migration/backward-compatibility shims and unused Vue components are removed, dense UI typography has an accessible 12px floor, and Storybook is pruned, renamed, reorganized, and wired to automated accessibility checks.
# DerridAI Corpus Viewer 0.46.1

DerridAI Corpus Viewer is a local-first Docker application for editing philosophical JSONL corpora, auditing records with local or OpenAI-compatible LLMs, linking records to source PDFs, managing persistent ChromaDB collections, and running an evidence-grounded DerridAI RAG pipeline.

The UI footer displays:

```text
© 2026 The New England Transcendental Club of California
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


## 0.46.1 — Gray Fox

### Gray Fox changes

- Consolidated the built-in interface dictionaries into canonical `en-US` and `fr-CA` locale modules instead of release-by-release mutation blocks.
- English and Québec French now ship with exactly the same complete key set; literal UI translation keys and placeholder parity are regression-tested.
- Québec French is explicitly treated as the `fr-CA` built-in locale, with Québec naming/terminology in the language UI.
- Removed obsolete client-schema aliases, the deprecated full-record PUT update contract, the old bulk-upsert payload shape, stale-client numeric normalization, historical derived-language collection cleanup, persisted preference-version migrations, locale migration logic, and the old Chroma collection-create fallback.
- Removed unused Vue/Storybook components and the stray Corpus Builder temporary file.
- Renamed the actively used `LegacySurface` component to `RuntimeSurface`, moved the active monolithic frontend runtime from `src/legacy/` to `src/runtime/`, and renamed its translation namespace from `legacy.*` to `runtime.*`.
- Storybook navigation is normalized by product area, version suffixes and placeholder story names are removed, and `@storybook/addon-a11y` is enabled with accessibility violations treated as errors.
- Raised every explicit frontend font size below 12px to a scalable 0.75rem floor while retaining the existing global keyboard-focus, skip-link, and reduced-motion behavior.
- Built-in language lookup now overlays stored administrator edits onto the complete canonical dictionary at read time, so no startup dictionary migration is required.
- Added Gray Fox regression checks for release identity, i18n completeness/placeholder safety, Québec French locale identity, Storybook organization, accessibility typography, and removal of compatibility scaffolding.

## 0.46.0 — Feral Fox

### Feral Fox changes

- Reviewed record text is editable while the immutable PDF extraction is retained as `source_extracted_text`, with revision history and explicit human-correction provenance.
- Record-level source-quality diagnostics now show the concrete problem, severity, affected pages, and available resolution path instead of a generic acceptance warning.
- Human-corrected text can explicitly resolve record-level extraction issues; downstream metadata may then be rerun against the reviewed text without destroying the source audit trail.
- Editing reviewed text reopens any previously accepted record so changed corpus text cannot remain silently accepted without another scholarly review decision.
- Metadata fields expose ownership/provenance (`Inherited`, `Source derived`, `LLM inferred`, `Human confirmed`, `Override`, `Needs review`) and legitimate record metadata can be edited deliberately.
- Document-manifest metadata can be edited from the review workspace once global propagation is safe; settled records may use explicit record-level overrides without racing an active enrichment pass.
- Metadata reruns can target only discourse, quotation, or indexing; rerunning one family preserves human decisions and settled output from the other families.
- Bibliographic values inherited from the document manifest can be overridden at record scope without silently mutating the document manifest; later manifest inheritance does not overwrite human overrides.
- Fast enrichment is deterministic-first and selectively routes discourse, quotation, and indexing work to the LLM. Deep scholarly enrichment remains available when broader semantic analysis is wanted.
- Semantic indexing is optional in Fast mode. Quotation work is skipped when no quotation signal exists, and obvious apparatus can bypass unnecessary discourse calls.
- Source-quality gating is severity-aware: only blocking extraction failures suppress automatic semantic enrichment, while human-corrected text can be enriched and still remain explicitly review-blocked until the source issue is resolved.
- Corpus Builder reports what the LLM actually contributed: useful fields, fields still requiring review, inherited/deterministic/human fields, family calls, elapsed model time, and useful fields per minute.
- Focus View now uses the same review concepts, ownership badges, source-issue diagnostics, editable reviewed text, accessible typography, and actions as the main review workspace.
- Focus View detail tabs use linked tab/tabpanel semantics and keyboard Arrow/Home/End navigation in addition to the dialog focus trap.
- Build configuration remains available during active builds only as an explicit concurrent-build workflow. The UI reports active builds and provider-profile capacity instead of implying accidental parallelism.
- New/updated Storybook components cover metadata ownership and source-issue states, including French-length and accessibility-oriented variants.
- All new UI copy is available through English and French Canadian i18n, and dense Corpus Builder controls retain a 12px minimum type floor plus keyboard/focus semantics.

## 0.45.0 — Energized Elephant

### Energized Elephant changes

### Progressive review record-store hotfix

A first live 0.45.0 review run exposed a concurrency defect: **Accept & next** could overlap a metadata-family checkpoint while both paths rewrote `records.jsonl`. The repository used one shared `records.jsonl.tmp` staging filename, so concurrent writers could truncate or interleave that file and leave the authoritative JSONL malformed, surfacing as HTTP 422 with a JSON decode error. The hotfix serializes record-store writes, uses unique same-directory temp files plus atomic `os.replace`, and serializes all manager-level record read/modify/write review transactions with metadata checkpoints. The completed-worker merge path now takes the same lock. This prevents both malformed JSONL and stale reviewer snapshots from overwriting newer progressive metadata checkpoints.

- Metadata enrichment is durable at the discourse, quotation, and indexing family level; interrupted builds resume only unfinished families.
- Corpus LLM stages now use bounded per-stage read deadlines and do not blindly repeat expensive hard timeouts.
- Metadata task telemetry records queued/running/completed/failed/skipped counts, active tasks, execution timing, and last settled progress.
- Failed or skipped metadata becomes an explicit human-review exception instead of blocking the entire corpus build.
- A stalled enrichment run can be asked to continue with remaining automatic metadata settled as unresolved.
- Corpus Builder status UI was refactored into reusable Storybook components with larger accessible typography, clearer progress hierarchy, scoped transient network warnings, elapsed/ETA and resume-safe checkpoint feedback, and progressive-review status.
- Review navigation now keeps five primary queues (**All / Reviewable / Issues / Accepted / Rejected**) and moves Metadata/Topology/Source into an Issues filter; explicit record selection makes batch rejection safer.
- The source inspector exposes full PDF page context and a one-click **Open in PDF Explorer** action; the review header keeps the build/model identity visible.
- New interface copy is localized in English and French Canadian, and dense Corpus Builder controls use a 12px minimum text floor with visible focus and non-color state labels.
- Release readiness requires Python tests, TypeScript/Vite production build, Storybook build, and container build checks.


Energized Elephant retains Dachshund’s exception-oriented review contract: **extract source → construct records → enrich record metadata → human review → validate → publish**. Deterministic rules own obvious topology and metadata; the LLM is called only for ambiguous semantic boundaries and judgment-heavy scholarly metadata. The human approves the resulting records and resolves only concrete exceptions such as bad extraction, uncertain provenance, or low-confidence metadata.

Human metadata decisions are now durable server-side decisions rather than loosely coupled UI state. A decision writes the value, marks the field `human_confirmed`, records an audit entry, increments the record revision, recomputes the record's blockers and queue membership, persists the record set, and returns the authoritative record/build/queue state. `primary_text` retains true three-state semantics (`true`, `false`, `null`); `false` is never treated as missing. Background enrichment is progressively reviewable: a record unlocks as soon as its own metadata families settle, while in-flight records remain read-only and structural edits remain locked until neighboring enrichment settles.

The active scholarly profile is `derrida-scholarly-v11` and metadata prompt contract is `derridai-record-metadata-v7`; v10 remains registered for existing builds. Review-relevant metadata includes `region_type`, `primary_text`, `discourse_role`, `speaker`, `position_holder`, `target`, `stance`, `proposition_status`, and `claim_scope`. Deterministic classifications are preserved. LLM proposals are constrained to controlled enums/booleans where applicable, source-bound evidence is validated, and any proposal below the profile confidence threshold is routed to human review even if the model fails to request review itself. High-confidence supported proposals remain visible and become human-confirmed when the reviewer accepts the record.

Review queues are derived from authoritative record state rather than independently persisted flags. The primary review navigation is **All**, **Reviewable**, **Issues**, **Accepted**, and **Rejected**; **Metadata**, **Topology**, and **Source problem** are issue-type filters rather than equally prominent tabs. Clean pending records have no source/topology/metadata blockers and can be approved individually with **Accept & next** or safely in bulk with **Accept clean**. Destructive batch rejection requires explicit record selection. Source extraction problems (including fragmented-glyph/layout artifacts) and uncertain provenance remain exception records with explicit reasons. Queue membership, metadata completeness, and publication eligibility are recalculated from the same persisted records so a confirmed field cannot reappear merely because a stale counter or client filter disagrees.

The review workspace is now the primary surface once records exist. Build configuration and technical diagnostics collapse out of the way; a compact session header shows review progress, a narrow queue provides navigation, the proposed record receives the majority of readable space, and a secondary inspector switches between **Metadata**, **Evidence**, and **Source**. Metadata decisions use typed controls with explicit Confirm/Saving/Saved feedback. Record acceptance/rejection is an atomic backend command returning the updated build, queue counts, and next review target; the frontend no longer chains several refreshes to decide what happened. Review mutations preserve viewport position.

The UI remains English/fr-CA localized, uses semantic native controls and visible text states rather than color-only signaling, preserves keyboard focus, supports reduced motion, and expands the Storybook review/queue/metadata states. Regression tests cover durable human metadata, `primary_text=false`, low-confidence LLM routing, automatic-enrichment review locking, atomic accept/advance, clean-vs-exception queues, source-problem routing, bilingual strings, and Storybook surfaces.


## 0.42.1 — Bunny Rabbit - Again

Bunny Rabbit finishes the post-construction workflow around six independently visible stages: **source extraction → corpus construction → scholarly enrichment → record review → final validation → publication**. Each stage now exposes an explicit state and the build carries a machine-readable `publication_readiness` object with blockers and a single next action. Completing record review hands the user into a dedicated **Finish corpus** workspace rather than leaving the review controls on screen.

The Finish corpus workspace summarizes accepted/rejected/pending records, required metadata issues, source fidelity, extraction quality, final validation, and publication readiness. If publication is blocked, the primary action goes directly to the relevant queue. Once all required gates pass, publication becomes an explicit final action that creates an immutable JSONL snapshot.

Metadata resolution is now field-level rather than a vague build-level retry. The active profile is `derrida-scholarly-v10` and metadata prompt contract is `derridai-record-metadata-v6`; `derrida-scholarly-v9` remains registered for existing builds. Record review now includes the LLM-proposed scholarly metadata itself: high-confidence evidence-bound proposals are shown for confirmation when the record is accepted, while uncertain fields such as `position_holder`, `stance`, and `proposition_status` are queued for explicit human resolution. `region_type`, `primary_text`, and `discourse_role` remain publication-critical hybrid fields. Deterministic inference is retained when strong; otherwise the LLM performs constrained classification against the controlled enum/boolean schema. Python validates values and source evidence before accepting them. Each field records whether it is deterministic, LLM-inferred, human-confirmed, unresolved, or invalid.

The metadata issue summary now distinguishes operational failures, invalid values, evidence failures, ambiguity, source-quality problems, and fields that have not yet run. Automatically retryable issues are separated from fields requiring human judgment. **Retry metadata** targets only the affected records/fields, records its own operation ID/provider/model/progress, and does not rerun successful enrichment or corpus topology. Ambiguous fields open a dedicated metadata-resolution queue with the current value, provenance, confidence, source-evidence navigation, and constrained controls for confirming a replacement. Structural record acceptance remains separate from metadata resolution.

Extraction quality is checked before scholarly enrichment. Strong corruption indicators such as Unicode replacement characters or unexpected control characters block automatic LLM interpretation for affected pages; sparse pages are warnings rather than automatic failures. Unicode source text remains NFC-normalized without ASCII transliteration or stripping. Published JSONL is UTF-8 with `ensure_ascii=False`.

Publication now validates a versioned public-record contract, `derridai-corpus-jsonl-v1`, before bytes are written. Every record must retain stable record/source identifiers and its build provenance is namespaced under `corpus_build_details`, including the publication schema version. Controlled metadata enums and `primary_text` types are revalidated at publication time.

The review workspace remains reload-safe: build, queue, and selected record are represented in route state, and persisted intermediate records are hydrated automatically after refresh without requiring a checkbox or form interaction. Selecting metadata evidence synchronizes the source viewer to the bound PDF page. Focus Review remains a record-first full-screen decision workspace.

Storybook coverage now includes Finish corpus states, field-level metadata resolution, metadata retry progress, the six-stage lifecycle, Focus Review, and publication readiness. New interface text is localized in English and Canadian French. The controls continue to use semantic elements, visible state text in addition to color, deliberate focus movement, keyboard-compatible interactions, responsive layouts, and reduced-motion handling in support of the WCAG 2.2 AA target.

Release validation includes the full Python regression suite, Python compilation, TypeScript/Vue script syntax checks, Git whitespace checks, and explicit production Vue/Storybook build attempts. A successful dependency-backed Vue/Storybook production build remains a mandatory release gate in environments where the npm dependency graph is available; this source archive does not represent an unavailable toolchain as a passing build.

## 0.40.10 — Corpus of Engineers

Version 0.40.10 finishes the topology-quality phase of Corpus Builder. The current profile is `derrida-scholarly-v7` with segmentation provenance `derridai-local-boundaries-v7`. Semantic segmentation remains deterministic-first and conservative, but a separate deterministic normalization stage now optimizes the resulting topology for retrieval-sized records without pretending that record length is semantic evidence.

The default sizing policy targets **1,750 characters with ±200 characters of flexibility**, allows coherent long-record exceptions to **3,500 characters**, and uses **6,000 characters as an absolute safety ceiling**. These values are configurable per build. Existing semantic boundaries are preserved; size-optimized boundaries are explicitly marked as retrieval boundaries (`semantic_boundary: false`) with the policy and local seam evidence recorded in provenance. Protected attribution/syntax seams outrank sizing, and only an unavoidable protected split at the absolute ceiling creates boundary review.

Corpus Builder now runs deterministic topology normalization/repair before metadata enrichment, emits machine-readable topology findings, checks source-block coverage/overlap/order, reports P10/median/P90/max record sizes and preferred-range exceptions, and exposes the quality report in the UI. New Storybook states cover record-sizing controls and healthy/long-exception/source-failure quality summaries. The release also fixes release-local i18n synchronization so bundled English and Canadian French strings are installed before `SystemStore` initialization.

Acceptance coverage now includes prose, dialogue/interview, and quotation-heavy extracted-layout fixtures, asserting source conservation, sane size ceilings, and zero ordinary boundary-review burden. Release validation: **266 Python tests pass** and all modified API modules compile. Frontend dependency installation was attempted in the release environment but timed out before `vue-tsc`/Vite became available, so this package does not claim a completed production frontend build.

## 0.40.9 — Enter Sandman

Version 0.40.9 makes automatic corpus topology the normal outcome rather than turning model ambiguity into user cleanup. The current profile is `derrida-scholarly-v6` and segmentation provenance is `derridai-local-boundaries-v6`. Boundary construction is deterministic-first: protected attribution/syntax seams resolve to KEEP, obvious structural seams can split without inference, weak candidates never reach a model, and only a bounded high-value subset is adjudicated. Adjudication is batched with a binary SPLIT/KEEP schema; omission, malformed output, provider failure, low confidence, or attempted uncertainty all conservatively resolve to KEEP.

Length no longer creates an LLM candidate. When a span exceeds the hard safety size, DerridAI searches nearby source transitions for the best non-protected seam and records the result as a provisional engineering split without requiring human review. A boundary review is created only in the exceptional case where every nearby seam is provenance-sensitive and the size guard must force a protected split. Topology receives a deterministic sanity check before any record-metadata enrichment begins, preventing expensive enrichment work on an obviously broken record set. Local boundary decisions are checkpointed with a prompt/model/evidence fingerprint so incompatible historical decisions are not silently reused.

Corpus Builder now reports segmentation telemetry: candidate transitions, deterministic splits, bounded LLM adjudications, batch-call count, model splits, safety splits, classifier failures that defaulted to KEEP, and genuinely review-required boundaries. The telemetry is implemented as a reusable Storybook component using semantic definition lists, text labels rather than color alone, keyboard/focus-compatible native semantics, logical layout properties, reduced-motion-safe progress behavior, and localized English/Canadian French strings. This release continues DerridAI's i18n-first UI contract and WCAG-oriented accessible status/progress reporting.

Regression coverage includes soft-length non-candidacy, deterministic heading routing, protected-transition KEEP behavior, binary uncertainty/failure fallback, LLM budget enforcement, safe hard-size splitting without review, forced protected-seam review, topology preflight before enrichment, cache fingerprinting, telemetry contract, and release identity.

Release validation: **258 Python tests pass**, all API modules compile, and `runtime.js` passes Node syntax checking. The frontend dependency installation was attempted in the release environment but timed out before `vue-tsc`/Vite became available, so this package does not claim a completed production frontend build.

## 0.40.8 — Coming Around the Mountain

Version 0.40.8 changes Corpus Builder topology ownership. PDF layout blocks remain immutable provenance units and are conservatively reconstructed into semantic atoms. Python generates a finite set of plausible boundary candidates from structural signals such as headings, speaker labels, quotation-frame changes, and sparse size-review points. The LLM no longer partitions a book or returns a book-scale boundary list; it receives only local left/right split/keep/uncertain classification tasks.

Malformed, failed, omitted, uncertain, or low-confidence local classifications deterministically default to **KEEP**. Human review is reserved for demonstrated provenance hazards rather than ordinary model uncertainty. When a semantic span exceeds the hard safety size, Python searches for the best nearby safe seam and records the split as provisional; a review item is created only when the fallback is forced through a protected transition. Boundary review belongs to the transition itself: neighboring records are not marked `needs_review` merely because they touch a provisional boundary. Corpus construction and metadata enrichment continue regardless, while publication remains gated by any remaining boundary review and validation. The current profile is `derrida-scholarly-v6` and the segmentation provenance identifier is `derridai-local-boundaries-v6`; `derrida-scholarly-v5` remains available for resuming 0.40.8 builds.

Works metadata continues to model books, journal articles, chapters in edited books, and other container-based formats, including MLA rendering. **Populate metadata with LLM** uses Open Library, Google Books, and Crossref as source-aware catalogue inputs. Mixed JSONL files can be separated by work, and the **Create JSONL subset** workflow supports saved reusable filter profiles.

Regression coverage includes boundary-review isolation, deterministic KEEP behavior after classifier failure, explicit uncertain-boundary persistence, semantic-atom provenance, MLA formatting, multi-catalog metadata lookup, work separation, saved subset profiles, and release identity. The Python suite contains 247 passing tests; Python modules compile and `runtime.js` passes Node syntax checking. The exact frontend production build command was attempted, but dependencies are not installed in this environment and the npm install attempt timed out, so `vue-tsc`/Vite could not run here.


## 0.40.5 — Record Extraction Pipeline Corrections

Version 0.40.5 corrects the PDF Corpus Builder around real book-scale extraction rather than treating malformed or empty LLM segmentation output as a usable record topology. Segmentation now uses compact typed boundary schemas, token-budgeted overlapping windows, bounded structured-output repair, recursive window reduction, and pairwise transition classification as the final model fallback. If semantic topology still cannot be validated, the build stops in a resumable **Segmentation blocked** state with zero generated records instead of collapsing the entire PDF into one giant fallback record. Large provisional semantic units are also treated as topology-review blockers; character counts remain validation guards only and never create boundaries.

Metadata extraction is split into smaller typed discourse/attribution, quotation-relation, and semantic-indexing tasks. Successful families are retained independently, source text remains deterministic and immutable, individual metadata failures produce reviewable records rather than aborting the book, and each populated attribution-bearing field must carry source-block evidence above the configured confidence threshold. Completed records are checkpointed incrementally, and corpus builds can resume with a different provider or execution envelope without discarding validated work.

Corpus Builder now exposes per-build provider execution controls — context window, temperature, Top K/Top P/Min P, repeat penalty, seed, thinking mode, Mirostat, metadata concurrency, semantic-window size, and stage-specific structured-output budgets — while preserving centrally managed provider profiles. The UI preflights explicit context limits before a build starts and reports the effective execution envelope. PDF corpus builds are normalized into DerridAI's global Background Operations feed on Home, including provider/model, current stage, progress, unresolved segmentation regions, cancellation, and direct navigation back to the build.

The PDF workflow is reorganized around persistent Source → Analyze structure → Build & enrich → Review & publish phases, a build-quality summary, explicit blocked/recovery states, and targeted resume controls. New reusable Vue components for workflow state, execution settings, and quality gates include Storybook stories. New and touched UI strings are available in English and Québec French; controls use native semantics, non-color status text, focus-visible treatment, logical properties, live regions, reduced-motion handling, and responsive layouts.

Regression coverage now includes malformed structured output, recursive segmentation recovery, empty-boundary topology guards, metadata-family failure isolation, impossible context preflight, global Operations integration, provider override controls, Storybook/i18n/WCAG requirements, and the no-giant-record invariant that failed on *On Cosmopolitanism and Forgiveness*.

Release validation: 227 automated tests pass, Python application modules compile, `runtime.js` passes Node syntax checking, and `git diff --check` is clean. The full Vue/Vite/Storybook production build could not be executed in the release environment because frontend dependencies are unavailable and `npm install` times out; this release does not represent that build as verified.

## 0.40.1 — Dorar the Explorah

Version 0.40.1 completes the PDF Corpus Builder reliability pass. Corpus LLM calls now use provider-native JSON Schema when available, strict Pydantic validation, syntax-only JSON repair, and bounded corrective retries instead of failing a book-length build on one malformed response. Semantic boundaries are confidence-gated and uncertain/window-seam boundaries receive a second reconciliation pass before they can alter record topology. Metadata extraction receives neighboring semantic context, requires block-level evidence for attribution-bearing fields, fills the canonical DerridAI metadata contract, and continues as a reviewable record rather than aborting the entire build when one model call cannot be validated.

Corpus builds now checkpoint the document manifest, accepted semantic boundaries, deterministic records, and each completed metadata record. Interrupted or failed builds are resumable from their last completed checkpoint. Researcher-approved provider profiles are resolved server-side; administrator provider profiles are consumed directly from the same saved LLM Providers configuration without requiring them to be separately enabled for researchers, and API keys are excluded from public build manifests. Validation now checks source coverage, exact normalized text fidelity, source ordering, physical PDF page mapping, citation completeness, required attribution evidence, and metadata-schema integrity. Build observability records LLM calls, corrective retries, structured-output failures, and escalation-provider use. The review workspace navigates the PDF by physical PDF page while retaining printed scholarly page numbers for citations, supports field-specific evidence highlighting and human evidence rebinding, exposes recoverable build warnings and detailed validation state, and uses optimistic record revisions to avoid silent concurrent metadata overwrites.

The PDF workspace and Corpus Builder were also brought onto DerridAI's i18n system with English and Québec French strings, logical CSS properties for bidirectional layouts, explicit labels and live regions, keyboard-visible focus treatment, reduced-motion handling, semantic progress reporting, and non-color status text. The review workspace now lets a human correct field-to-source evidence bindings directly against immutable source blocks; structural merge/split edits preserve scholarly printed-page labels separately from physical PDF pages, and deterministic/system-owned metadata cannot be accidentally overwritten in the JSON editor. Reusable Corpus Build Progress, Field Evidence, PDF Evidence Viewer, Printed-Page Mapping, and Document Manifest components are covered in Storybook.

Post-release hotfix: Corpus Builder now reads the administrator's configured LLM Provider profiles as well as the server-side researcher allow-list. This fixes the false **No LLM provider profiles are configured** state when normal provider profiles existed but none were marked for researcher access, and preserves direct administrator profile settings for primary and escalation providers without persisting API keys in build manifests.

Release validation after the hotfix: 210 automated tests pass, Python application modules compile, `runtime.js` passes Node syntax checking, and `git diff --check` is clean. The full Vue/Vite/Storybook production build could not be executed in the release environment because frontend dependencies are not installed; the source package therefore does not claim that build as verified.

## 0.40.0 — Pdffffffffft.

Version 0.40.0 turns PDF Explorer into the front end of an auditable corpus-production pipeline. PDFs are now content-addressed, persisted server-side, decomposed into layout-aware source blocks with adaptive OCR fallback, and processed by durable background builds. An LLM proposes semantic record boundaries based on discourse relations — speaker, position holder, stance, target, quotation frame, discourse role, and argumentative move — rather than page or character counts. DerridAI then constructs record text deterministically from immutable source blocks, infers source-supported record metadata, binds metadata fields to block-level evidence, validates source coverage and text fidelity, and routes uncertain records to human review.

A new native Vue Corpus Builder provides source-PDF comparison, review filtering, evidence-bound metadata inspection, merge/split operations, JSON editing, acceptance states, build provenance, validation status, and JSONL publication/download. Builds record source SHA-256, app/schema/profile versions, provider/model, prompt versions, source spans, validation metrics, and publication hashes. Generated record sets can be opened directly in the local DerridAI workspace after publication.

## 0.37.1 — Disoriented

Version 0.37.1 streamlines the Vector Stores workspace around a persistent collection rail, compact status header, and five task-focused sections: Overview, Data, Retrieval, Builds, and Settings. Redundant KPI/management cards are removed, collections are searchable from the rail, record actions use progressive disclosure, records open in a contextual inspector drawer, retrieval modes can be compared side-by-side, and infrastructure storage is reduced to a compact backend control instead of competing with collection work.

Research pipeline resilience is also improved. The logical `_response_cache` now validates and creates its Chroma-safe physical alias correctly, fixing cache writes that failed on the public leading-underscore name. Background LLM review jobs no longer call vector-upsert spool methods or persist provider credentials to disk; they execute through their intended provider concurrency gates. Auto-grade treats transient upstream 408/425/429/5xx failures as retryable, retries once by default, preserves full diagnostics for audit, and reports a concise recoverable warning when the grading provider remains unavailable without turning a completed Research answer into a failed pipeline.

## 0.37.0 — New Direction

Version 0.37.0 rebuilds Vector Stores around explicit, reproducible retrieval contracts rather than treating a Chroma collection as an opaque mutable container. Collection creation now uses a Source → Retrieval → Review & build workflow with strict create semantics, embedding preflight, recorded vector dimension and distance metric, hybrid retrieval as the recommended default, deletion protection, source/build provenance, and background synchronization for collections of every size. Existing collection names return a conflict instead of being silently reused.

Vector Stores now foreground collection health and provenance: status, embedding contract, source snapshot, current build, synchronization time, build history, and protection state are visible alongside the data browser. The retrieval test can compare hybrid, semantic, lexical, and MMR behavior. Large synchronization no longer requires the Vector Stores tab to remain open; builds are handled by the persistent operations system, and completed builds finalize a manifest with source fingerprint and build history. Infrastructure storage controls are intentionally demoted to an advanced system-storage section.

This release also hardens embedding compatibility. Generated embeddings are probed before collection creation, the resolved dimension becomes part of the collection contract, upserts reject dimension drift before Chroma writes the batch, and manifest-backed embedding settings are immutable. Precomputed-vector collections may establish their dimension on first ingest and remain usable for lexical and hybrid retrieval even when query embedding is unavailable.

## 0.36.11 — Peekaboo

Version 0.36.11 stabilizes the native Search workspace and applies several small UI consistency fixes. Loaded-record Search now uses one fixed table contract — DB status, Work, Page Start, Needs Review, Extracted Text, and Actions — rather than inheriting stale column configuration from other Search scopes or saved browser state. Column configuration and manual resizing remain available only for database-search tables. Citation menus now render as overlay popovers above following content instead of expanding the table row or card.

Works gains a final **Add a JSONL file** card that opens the existing corpus-file picker. Response FAQ is renamed **Response Library** throughout the user-facing interface while retaining the existing `/faq` route and internal cache identifiers for compatibility. The application copyright name is corrected to **The New England Transcendental Club of California**.

## 0.36.10 — In Search of Lost Time

- Rebuilt Search as a native Vue scholarly-exploration workspace rather than a legacy configuration surface. The page now centers a persistent query composer, corpus scope, facets, results, and evidence-oriented record actions in one coherent workflow.
- Search scope is expressed as **Loaded records** or **Corpus database**. Semantic strategy is subordinate to database search options: Similarity, MMR, or metadata-only filtering, with MMR candidate-pool and relevance-weight controls kept in advanced options.
- Added faceted refinement for common scholarly metadata and record state, while preserving the field/condition/value builder as an advanced filter tool with corpus-derived value autocomplete. Active filters appear as removable chips.
- Local JSONL search updates as the user types; database search remains an explicit operation. Database results expose relevance, matched metadata, and an inspectable “Why this result” explanation without presenting vector similarity as probability or confidence.
- Simplified the resting results toolbar. Review, auto-improve, and bulk-edit controls now appear only when records are selected. Table results add sticky headers/status/actions, user-resizable columns, expandable highlighted extracts, horizontal overflow, and distinct compact/comfortable reading densities. Card results retain citation, evidence, and record actions without irrelevant column configuration.
- Added browser-local **Saved views** and **Recent searches**. Saved views preserve DerridAI's shareable Search URL, including corpus scope, query, filters, sort, columns, layout, and pagination configuration; Copy link exposes the same state for collaboration.
- Search now routes directly to corpus-database creation when database-backed exploration is required and no database exists, including a completely empty Search workspace.
- Search strings are fully backed by the English and Canadian French dictionaries. The native workspace includes keyboard-visible focus treatment, labelled controls and regions, reduced-motion handling, responsive facet drawers, keyboard-scrollable result overflow, and bounded modal scrolling.
- Storybook now includes reusable Search workspace header, facet panel, and contextual selection-bar components.

## 0.36.4 — Oops You Did It Again

- Reverted the 0.36.3 native-file-picker export treatment. JSONL export is back to the compact download menu, with no overwrite toggle or File System Access API workflow.
- Record Inspector page/page-range information now appears as a normal metadata row immediately below Region Author instead of a separate context card.
- Single-work analytics replace Speakers and Position holders with **Discourse targets** and **Discourse roles**. Targets use a top-five ranking; discourse roles use an accessible share pie showing the top roles as a percentage of all recorded role occurrences, with the remainder grouped as Other. The reusable Storybook work-insights component mirrors the same ranking/pie model.
- Record-table actions consolidate Inline and Full citation copying under an accessible **Get Citation** submenu. Comfortable Search tables use a larger Extracted Text type size for sustained reading.
- Search now defaults only to DB status, Work, Page Start, Needs Review, Extracted Text, plus the dedicated Actions column. Card layout continues to omit column configuration.
- Semantic Search no longer strands users at “No corpus database available.” When the current role can manage databases, Search routes directly to the database-creation workflow, matching Research behavior; roles without that permission retain the explanatory empty state.
- Added matching English and Canadian French strings and preserved keyboard/focus behavior for the revised controls.


## 0.36.3 — All The Little Things

- File export can use the browser's system file/folder picker to save directly to disk and, after the browser/OS confirmation, overwrite an existing same-name JSONL file. Browsers without the File System Access API keep the non-destructive download behavior.
- Reviewed bounded scrolling across inspectors and dialogs: the record inspector now permits natural wheel chaining at its boundaries, metadata-variant dialogs own their scroll region, and open dialogs prevent the page behind them from moving.
- Records/Search makes Extracted Text another 15% narrower, hides Columns configuration in card layout, and routes DB-backed workspace records into the canonical database-evidence selection path.
- Record Inspector now displays the source page/page range in its context overview. Response Library uses a neutral empty-state icon treatment rather than the green accent tile.
- Create JSONL subset condition values now expose per-file autocomplete suggestions derived from unique field values, while intentionally excluding large text-like fields.
- Installed-language changes propagate through a shared UI event so navigation and language selectors update without a page refresh, including completion of background translation jobs.
- The Annotations page now supports deletion: administrators/edit-capable users can remove local JSONL annotations (with audit history), while shared-annotation deletion remains restricted to the annotation owner or an administrator and is enforced by the API.
- Storybook adds the neutral empty-state variant and the affected components retain keyboard/focus semantics and bilingual English / Canadian French strings.


## 0.36.2 — Bugs in the Machine

- URL state is now the authoritative share contract for view configuration: record-table search/filter/sort/page/columns, global search modes and database search settings, Works search/selection, Annotations search/view, Dashboard metric selection, Record find state, and Response Library search/page are encoded into the URL. Breadcrumb history snapshots preserve the same state. JSONL file identities are content-derived so the same file can resolve the same shared Records URL on another browser after that file is loaded.
- Shared local-JSONL links no longer silently substitute a different locally cached file. If the linked JSONL is not present, the Records page explicitly asks the recipient to load the same file and then restores the encoded filters/view state. The JSONL contents themselves are intentionally not embedded in the URL.
- The Records table now scrolls horizontally when needed, uses a compact Page Start column and narrower Extracted Text column, and defaults to DB status, Work, Page Start, Needs Review, Extracted Text, plus the dedicated Record Actions column.
- Fixed the empty-workspace **Choose JSONL files** call to action.
- Works metadata marked **Mixed** now has an inspectable, accessible variants dialog showing every distinct value, its frequency, and contributing source files before a user decides whether to bulk-edit. Work-card record/review counts now open Global Search with the corresponding filters applied.
- When exactly one JSONL work is loaded, Dashboard corpus-wide charts are replaced by reusable work-level top-five views for persons, concepts, topics, speakers, and position holders. The same insight panel is also embedded in the Work overview and represented as a reusable Storybook component.
- LLM Review Workspace provider selection now truncates safely instead of overflowing. Endpoint/API-key configuration is no longer duplicated in the review modal; connection details are consumed from the centralized provider profile, with a direct **Manage provider profiles** action.
- Added WCAG focus states, keyboard-scrollable table overflow, accessible mixed-value inspection, and matching English / Canadian French strings for the new interactions.

See `docs/SHAREABLE_STATE_AND_DATA_MODEL_0.36.2.md` for the URL-sharing contract and the distinction between JSONL records, JSONL files, and database records.


## 0.36.1 — Fresh-start SQLite cleanup

- Removed the 0.36.0 JSON-to-SQLite import path and all startup inspection/renaming of `derridai-system.json`. 0.36.1 initializes the current SQLite store directly and assumes a clean installation.
- Removed the `schema_migrations` and generic `system_meta` tables. The system database now contains only the tables the current application uses: provider profiles, annotations, languages, and durable jobs.
- Removed built-in language dictionary revision/update machinery. English 🇺🇸 and Français 🇨🇦 are seeded directly when the system database is empty, and existing database values are left alone on normal restarts.
- Removed the authentication `ALTER TABLE` upgrade path. `last_login` and `login_count` are part of the current `users` schema from first creation.
- `/api/system/storage` now reports the active SQLite backend, path, journal mode, and size without exposing a migration/schema-version concept.
- This release intentionally has **no storage upgrade path**. Run it from a clean data directory rather than reusing databases or `derridai-system.json` from an older release.

See `docs/STORAGE_0.36.1.md` for the fresh-install storage contract.


## 0.36.0 — The SQL Prequel

- Replaced the monolithic `derridai-system.json` runtime store with a durable SQLite database at `SYSTEM_DB_PATH` (default `/data/.home/derridai-system.sqlite3`). Provider profiles, annotations, installed language dictionaries, translation reports, and system metadata now sit behind a repository abstraction instead of whole-file JSON rewrites.
- Existing installations migrate automatically and non-destructively: when the new SQLite store is empty, DerridAI imports `derridai-system.json` in one transaction and preserves the legacy file as `derridai-system.migrated-v0.36.0.json` when the filesystem permits.
- Added a durable SQLite operation ledger for LLM review, RAG, LLM-tool/translation, and Chroma upsert jobs. Finished operations survive API restarts; jobs interrupted by a restart are retained as failed/interrupted records rather than disappearing or being silently replayed.
- Language dictionary translation now writes resumable checkpoints to SQLite after validated batches, so a process restart loses at most the in-flight model call rather than the completed portion of a long translation. Hidden partial dictionaries remain server-side and are never exposed through the public operations API.
- Full backup/restore now includes LLM-tool operations, including incomplete resumable language translations, in addition to the existing LLM, RAG, and upsert operation histories.
- SQLite uses WAL mode, foreign keys, a busy timeout, indexed operation/annotation lookups, and explicit schema migrations. Authentication remains in its existing SQLite database and Chroma remains the vector store; this release intentionally does not add Redis or migrate vectors.
- Added an administrator-only `/api/system/storage` diagnostic endpoint so deployments can verify the active backend, database path, journal mode, schema version, and approximate database size without exposing that filesystem detail to non-admin accounts.

This is the deliberately low-risk intermediate storage architecture: local/single-host deployments gain transactional durability and restart-safe operation history now, while the repository boundary keeps a future PostgreSQL backend feasible without coupling application logic directly to SQLite.


## 0.35.17 — Lingua Franca

- Hardened Research request construction so stale UI state is normalized before submission; Research validation conflicts now return semantic 422 responses rather than opaque 400 Bad Request responses. HTTP failures retain the status code, full server message/body, request path, method, and a bounded local diagnostics history.
- Improved language installation resilience with smaller translation batches, conservative JSON repair, recursive retry/bisection, resumable partial dictionaries, and a plain-text single-string fallback for models that translate competently but emit unreliable JSON.
- Built-in languages are displayed as **English** 🇺🇸 and **Français** 🇨🇦. The country/symbol picker is teleported outside dialogs so it cannot be clipped. Unicode does not define a standardized Québec flag emoji; DerridAI offers the Unicode fleur-de-lis (⚜️) as an explicit symbol alternative without mislabeling it as a flag.
- Annotation selection actions close with Escape. Highlighted annotation text now exposes an accessible hover/focus tooltip with note, tags, author, and date.
- Response Library now renders saved LLM grades as a structured evaluation report with category scores and analyses, strengths, weaknesses, risky claims, and a secondary raw-output disclosure for auditability.
- Expanded Storybook coverage for the floating flag picker and structured evaluation report, with additional WCAG/i18n copy in English and professional Canadian French.

## 0.35.16 — Tongue Tied Again

- Languages & internationalization now keeps table headers in the table flow, aligns locale identity fields from the top, warns about higher-risk translation model families, tolerates fewer than 10% unsafe translation keys with explicit English fallbacks, and preserves partial dictionaries so failed or cancelled jobs can be resumed without retranslating validated strings.
- Research now routes an empty installation directly into the corpus-database creation workflow while preserving Back navigation.
- LLM grading retains the complete structured evaluation — category scores, category analyses, overall analysis, lists, and the raw model output — in response-cache grade history and exposes the saved output in Response Library.
- Built-in English and Québec French dictionaries were revised together for the new recovery, warning, and provenance UI.

## 0.35.12 — Tongue Twister

Languages & internationalization is now a native localization studio with a bilingual English-source/target editor, locale search and status filters, translation coverage metrics, a searchable country-flag library, BCP 47 locale support, RTL document direction, and expanded Storybook coverage. New language installation now translates the complete canonical English interface dictionary in bounded LLM batches, validates key and placeholder fidelity, rejects effectively untranslated output, and installs atomically only after the complete translation succeeds. Provider navigation warns before discarding the install form and preserves a working back breadcrumb. Dialog focus handling and localized accessible labels were also strengthened for WCAG 2.2.

## 0.35.10 — Record Player
### 0.35.10 maintenance — Response Library polish

This maintenance patch fixes the Record Provenance Vue/TypeScript prop declaration that prevented `vue-tsc` from completing. It also redesigns Response Library as a research library rather than an administrative cache browser: saved questions include answer previews and evidence/model context, selected results retain the full Research answer/evidence presentation, run metadata is summarized in readable cards and definition grids, and raw technical metadata is kept behind progressive disclosure. The archive remains responsive, keyboard accessible, reduced-motion aware, and fully localized in English and professional Québec French.


Version 0.35.10 replaces the legacy Record View renderer with a Vue-native scholarly record workspace. The record identity and reading surface now dominate the page, while a resizable inspector organizes Overview, Provenance, Indexing, PDFs, Annotations, and History. Text selection exposes contextual annotation actions; annotation quotations are visibly anchored in the reading surface; the structured speaker → position holder → stance → target relation is presented as a first-class provenance component; and metadata editing now uses a side sheet that sends only changed fields into the existing audit trail.

The release also reduces toolbar overload through primary actions plus an overflow menu, adds focus mode and in-record find, preserves role/capability boundaries for every exposed action, keeps researcher records read-only except for explicitly granted evidence/annotation operations, and expands Storybook coverage for the new Record Workspace components. English and professional Québec French strings are maintained in exact built-in dictionary parity, with WCAG-oriented focus states, semantic controls, appropriately sized targets, reduced-motion handling, and responsive layouts.

## 0.35.5 — RAGety Anne

Version 0.35.5 unifies RAG-result presentation across Research, background Operations, and Response Library. Opening a completed RAG operation now routes the result into the same Vue-native Research result workspace instead of a separate legacy modal, so answer typography, clickable citation bindings, evidence inspection, provenance metadata, grading actions, reruns, accessibility, and localization remain consistent everywhere.

Response Library is rebuilt as a native research archive with searchable saved responses, a persistent response browser, the shared Research answer/evidence presentation, source-bound citation inspection, retained run provenance, and saved-grade history. Overlay stacking is also corrected so ordinary notifications and background-operation notifications render above the sidebar. Storybook gains reusable unified-result and cached-response browser components, and the new interface strings are added to both built-in English and Québec French dictionaries without overwriting existing administrator customizations.


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
vector-store synchronization, source-binding robustness, Response Library batch
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
- Response Library entries are collapsed by default, remember per-response expanded
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
- Response Library and Response Cache now use a dedicated logical cache reader that merges legacy `_response_cache` and current `derridai_response_cache` physical collections, deduplicates by logical response ID, sorts deterministically, supports question filtering, and exposes total/matched counts.
- Record Comparison autocomplete now anchors its result popover inside the picker, scopes DOM lookups to the active view, supports pointer selection plus keyboard navigation, and avoids the misplaced/unclickable dropdown behavior caused by the result list being outside its positioned container.

## 0.21.0 — performance and regression fixes

Version 0.21.0 focuses on frontend responsiveness and fixes regressions found after the Vue compatibility migration.

- Vector Stores remains selectable for administrators even when no corpus collection exists yet, so the first collection/storage location can always be created or repaired; only actions that truly require an existing collection stay disabled.
- PDF Explorer restores the known-good PDF.js legacy worker integration and uses the cached record autocomplete index instead of the removed `recordOptions()` helper.
- Works action menus overlay surrounding cards instead of being clipped by the card boundary.
- Works and Response Library cards render progressively in small batches with loading skeletons; dashboard KPIs render first while charts/rankings/recent activity fill during idle frames, and asynchronous Vector Stores/corpus search views show explicit loading states.
- Record fingerprints are cached, preference/file persistence is less eager, pending-upsert derivation is short-lived cached, and dense card lists are excluded from the generic layout-measurement pass.
- Background **Analyze & grade RAG response** results use a delegated result opener with explicit render/fetch error handling.
- Response Library queries the response cache directly, recovers from stale persisted page numbers, clearly identifies saved searches with zero matches, and resolves both legacy `_response_cache` and current `derridai_response_cache` physical collections so retained responses remain visible across upgrades.

## 0.20.0 — Vue 3 frontend migration

Version 0.20.0 moves the application shell to Vue 3 with TypeScript, Pinia, and Vue Router while preserving the existing Python/FastAPI API and the validated corpus/RAG feature runtime. The migration is intentionally compatibility-first: routed Vue views and reusable shell components own navigation, top-level state, disabled-action tooltips, file tabs, and lifecycle; mature feature renderers remain behind `web/src/runtime/runtime.js` and can be converted view-by-view without changing backend contracts.

Frontend structure now includes `components/`, `views/`, `stores/`, `router/`, `api/`, `composables/`, and `runtime/`. Routes use readable paths such as `/records`, `/works`, `/databases`, `/rag`, and `/settings`, while selected file/record/store state remains encoded in query parameters for deep links.

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
- The logical `_response_cache` is now a system cache rather than a corpus vector store. It is excluded from Vector Stores, corpus DB counts, collection pickers, language mirroring, and RAG source selection. A dedicated **Response Cache** page manages cache status/history separately, while **Response Library** remains the answer/evidence browsing interface.
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
- Completed RAG responses are automatically cached in the logical `_response_cache` collection and browsable from **Response Library**. Because Chroma collection names must begin with a lowercase letter or digit, the physical collection is stored as `derridai_response_cache`; DerridAI exposes it consistently as `_response_cache` through its API/UI.
- Response Library provides question/answer browsing, retained evidence and retrieval details, rerun-with-parameters, and LLM response grading.
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

0.47.1 Gregarious Guinea Pig validation in this packaging environment:

- **369 Python regression tests pass**;
- Python bytecode compilation succeeds for `api` and `tests`;
- `node --check web/src/runtime/runtime.js` succeeds;
- the regression suite covers English/Québec French key parity, collaborative human/LLM field ownership, bulk metadata editing, cancellation recovery, durable text drafts, Storybook integration, and WCAG-oriented UI checks;
- `npm run build` and `npm run build-storybook` were explicitly attempted.

This sandbox has no frontend `node_modules`, so the dependency-backed Vue/Vite production build stops at `vue-tsc: not found`. Storybook likewise stops at `storybook: not found`, and Docker is unavailable in the sandbox. **Accordingly, this package is a 0.47.1 build candidate, not a release-ready build.** Per the project release gate, a development environment with the frontend dependencies and Docker available must still complete the production frontend, Storybook, and normal Docker/container builds successfully before 0.47.1 is declared ready.

## Current limitations

- background-job state is process-local and does not survive API restart;
- browser workspace persistence is origin-specific;
- image-only PDFs do not receive built-in OCR;
- first use of a cross-encoder can require a model download;
- simultaneous independent writers to the same Chroma persistence path are unsupported;
- cancelling a Chroma upsert waits for the current batch to return;
- vector/reranker calls that do not expose a cancellable stream stop at the next pipeline checkpoint;
- clearing `updates` permanently removes that local audit history.
