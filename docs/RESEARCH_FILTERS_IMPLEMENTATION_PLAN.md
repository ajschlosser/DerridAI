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

# Research filters and instruction interpretation

## Purpose

Research currently accepts a free-text question plus optional free-text instructions. The generation model sees the instructions, and the Research retrieval path has a narrow deterministic safeguard for explicitly named works/authors, but the application does not yet represent user retrieval constraints as a typed execution contract.

This plan introduces a single auditable **Research filter plan** that can be produced by three user-facing paths:

1. explicit Chroma-style metadata/document filters for expert users;
2. a small deterministic expression language with autocomplete and inline validation;
3. bounded natural-language interpretation for common phrases such as “only”, “exclude”, “before”, “after”, and “one of”.

All paths compile to the same server-validated filter plan. The filter plan constrains candidate eligibility before ranking; it never becomes scholarly evidence and never changes canonical corpus state.

The design also creates the scope boundary needed by later coverage-aware Research modes such as whole-work overview, balanced comparison, or “survey each selected work before answering”.

## Current behavior and problem statement

On current Research runs:

- `RAGRunRequest.instructions` is free text.
- Query decomposition returns `prompt_query`, `prompt_query_fr`, `prompt_instructions`, and response language. It does not return typed inclusion/exclusion predicates.
- The final answer prompt receives `prompt_instructions`, so instructions can influence generation after evidence has already been selected.
- `rag.py` separately scans the question and instructions for explicitly named corpus works/authors and reserves bounded evidence coverage for those scopes.
- Mention detection is not constraint parsing. “Only Work A”, “include Work A”, and “exclude Work A” all contain the same work name; the current safeguard cannot reliably distinguish those meanings.
- The generic store-search pipeline already accepts Chroma `where` filters, and `ChromaStore.lexical_search()` / `mmr_candidates()` already accept metadata filters, but Research does not expose a first-class filter plan.
- The System Data Chroma console already has a deliberately small read-only CLI parser with `--where` and `--where-document`, plus validation/explanation endpoints. Reuse its lessons and common helpers rather than introducing a second unrelated filter dialect.

The key invariant is:

> A user instruction that changes which Records may be retrieved must be represented and enforced as typed scope data before ranking. A user instruction that changes only answer form or emphasis must remain a generation/retrieval preference, not be silently promoted to a hard filter.

## Architectural rules

### One canonical filter plan

Introduce one request-level contract, conceptually:

```text
ResearchFilterPlan
  metadata_filter       # Chroma-compatible where expression, or null
  document_filter       # Chroma-compatible where_document expression, or null
  source                # explicit | deterministic_natural_language | model_assisted
  original_text         # optional source instruction for audit
  remaining_instruction # text that was not converted into a hard filter
```

Exact field names may evolve during implementation, but there must be one execution contract rather than separate frontend/backend filter shapes.

### Deterministic code owns execution

The browser may suggest or compile a plan, but the server validates it again before a run starts. The LLM, if later used, may propose a plan; deterministic code owns:

- allowed fields;
- field identity resolution;
- allowed operators per field type;
- value normalization;
- work/author/entity resolution against the actual corpus;
- Chroma filter compilation;
- application of filters to every applicable retrieval leg;
- run-trace persistence;
- rejection of malformed, unsupported, contradictory, or unsafe filters.

### Filter before ranking

The intended execution order is:

```text
question + instructions
        ↓
filter interpretation / explicit filter
        ↓
server validation + field/value resolution
        ↓
candidate eligibility filter
        ↓
semantic / lexical / MMR candidate generation
        ↓
fusion / reranking / coverage selection
        ↓
evidence packing
        ↓
generation
        ↓
deterministic source binding
```

Do not retrieve the full corpus and remove disallowed Records after reranking unless a storage capability makes prefiltering impossible and the fallback is explicit in the trace.

### Derived filter plans are not evidence

A parsed filter or model-assisted interpretation is operational state. It cannot:

- establish a scholarly proposition;
- establish speaker/position-holder identity;
- count as evidence;
- override canonical FieldAssertions;
- silently change the corpus.

The final answer remains bound to actual evidence Records.

### Preserve semantic identity boundaries

Do not hard-code mutable metadata field names into Research policy. The filter UI may show schema field labels, but resolution should pass through a field/semantic registry and then compile to the indexed Chroma projection key appropriate to the selected collection.

The existing `research_semantics.py` compatibility boundary is the direction to follow. Work identity is still partly represented by the historical `work` projection; new code should isolate that compatibility assumption rather than spreading it.

## User-facing modes

### 1. Explicit Chroma filter JSON

Expert users may enter an explicit filter expression, for example:

```json
{
  "$and": [{ "work": { "$eq": "Of Grammatology" } }, { "page_start": { "$gte": 100 } }]
}
```

This is a filter value, not arbitrary code. Never evaluate JavaScript/Python or allow mutation commands.

A document-content filter may be represented separately, for example:

```json
{ "$contains": "pharmakon" }
```

### 2. Small deterministic expression language

Add a browser-side expression syntax intended for ordinary expert use:

```text
work = "Of Grammatology"
and page_start >= 100
and speaker != "Heidegger"
```

Minimum grammar:

- parentheses;
- `and` / `or`;
- `=`, `!=`, `>`, `>=`, `<`, `<=`;
- `in (...)` / `not in (...)`;
- quoted strings;
- numbers;
- booleans;
- field identifiers from the selected collection/schema.

Do not support arbitrary function calls or code execution.

Implementation preference: start with a small DerridAI-owned tokenizer/recursive-descent parser because the grammar is intentionally tiny and the repository currently has no runtime parser dependency. If the grammar grows materially, migrate the parser behind the same interface to a dedicated parser library rather than allowing ad hoc regex accumulation.

### 3. Deterministic natural-language interpretation

Recognize only phrases whose semantics can be mapped with high confidence to hard constraints. Initial examples:

- “only use Work A”
- “use only Work A and Work B”
- “exclude Work C”
- “speaker is Derrida”
- “speaker is not Heidegger”
- “pages after 100”
- “pages 100 to 140”
- “before 1970”
- “language is French”

Natural-language parsing should use:

1. simple normalized tokens/phrases;
2. the actual field registry;
3. the actual work/author/value inventory for the selected corpus;
4. explicit negation and scope rules.

Do not treat phrases such as “focus mainly on”, “especially”, “where useful”, “early works”, or “representative passages” as hard filters unless the user confirms a concrete interpretation.

A general browser NLP library is optional. It may assist tokenization or noun-phrase detection, but it must not own filter semantics.

### 4. Optional model-assisted interpretation

Only after deterministic parsing reports ambiguity, an optional local/browser model may propose a structured filter plan from a closed field/operator/value vocabulary.

The model-assisted path must:

- be optional;
- never execute its output without deterministic validation;
- expose that the interpretation was model-assisted;
- preserve the original instruction;
- surface unresolved phrases;
- never invent fields or values;
- never silently convert soft emphasis into hard exclusion.

Do not make model inference part of per-keystroke feedback.

## Near-instant preview UX

The Research composer should separate **answer instructions** from **retrieval scope** even if both begin in one instructions textarea.

While the user types, debounce local interpretation and show an “Interpreted retrieval scope” panel.

Example:

```text
Instructions
Only use Of Grammatology. Exclude Heidegger as speaker.

Interpreted retrieval scope
✓ Work       is exactly   Of Grammatology
✓ Speaker    is not       Heidegger

Other instructions
None

[Edit filters] [View Chroma expression]
```

Ambiguous input must remain visible instead of being guessed:

```text
“Focus especially on Derrida's early works.”

Could not safely convert “early works” into a hard filter.
Keep as an instruction, or choose concrete works.
```

Local parsing should be immediate. A short debounced server preview then verifies the plan against the current collection contract and returns authoritative diagnostics.

## Backend contract

### Shared Chroma filter validation

Create a focused backend module that owns validation/normalization of metadata and document filters.

It should support the stable subset DerridAI uses across its supported Chroma range.

Metadata:

- direct scalar equality;
- `$eq`, `$ne`;
- numeric `$gt`, `$gte`, `$lt`, `$lte`;
- homogeneous non-empty `$in`, `$nin`;
- nested `$and`, `$or`.

Document:

- `$contains`;
- `$not_contains` only if supported by the minimum Chroma version selected for DerridAI;
- nested logical operators only when supported by the compatibility contract.

Do not call undocumented Chroma internals as the long-term validation API. It is acceptable to use Chroma itself as a final execution validator, but DerridAI should own the request contract and actionable error messages.

### Preview endpoint

Add a non-mutating Research endpoint that accepts:

- selected collection;
- raw/compiled metadata filter;
- raw/compiled document filter;
- optional interpretation source.

Return:

- `valid`;
- normalized filter plan;
- fields referenced;
- collection filter fields;
- unsupported fields/operators;
- plain-language explanation;
- warnings;
- optional bounded sample/count information only when it can be obtained cheaply and without scanning an unbounded collection.

The endpoint must enforce normal Research authorization and must not expose hidden/system collections or source text beyond what the current role can already access.

### RAG request

Add the filter plan to `RAGRunRequest`. The request model must reject malformed executable filters before spawning a background job.

Persist the exact resolved plan with the run/job request so reruns and audit views reproduce the same eligibility scope.

### Retrieval propagation

Apply the normalized filter to every applicable candidate-generation leg:

- semantic similarity;
- lexical/BM25-style retrieval;
- MMR candidate generation or the semantic candidate pool used by Research's MMR leg;
- explicit work/author seed retrieval;
- any future filter-only or coverage-first stage.

A user filter must not be bypassed by the explicit-scope rescue path. When a named-work seed adds a work predicate, combine it with the user's filter using deterministic `$and` composition.

Selected evidence is separate. The first implementation should keep explicitly pinned evidence visible even when it lies outside the retrieval filter, but the UI/run trace must label that exception. Later product policy may add “filter selected evidence too” as an explicit option; do not silently change current pinned-evidence semantics.

## Frontend contract

### Field catalog

Research already receives each collection's `filter_fields`. Extend this into a typed field catalog rather than adding hard-coded Research field names.

The eventual catalog should carry:

- display label / i18n key;
- stable schema field identity or semantic identity;
- indexed Chroma projection key;
- value type;
- allowed operators;
- optional enumerated values;
- autocomplete source;
- compatibility/deprecation status.

Custom metadata schema fields should become filterable through the same mechanism when indexed.

### Parser module

Place framework-independent parsing/compilation in `web/src/domain/`, not in the Vue component.

Suggested API:

```ts
parseResearchFilterExpression(text, fieldCatalog);
interpretResearchInstructionFilters(text, corpusInventory, fieldCatalog);
compileResearchFilterPlan(ast);
explainResearchFilterPlan(plan, fieldCatalog);
```

Keep Vue responsible for lifecycle, debouncing, focus, rendering, and API calls.

### Component

Create a reusable Research filter preview/editor component with Storybook coverage.

Acceptance criteria:

- keyboard accessible;
- visible focus;
- semantic error/status messaging;
- no color-only meaning;
- narrow/reflow layout;
- EN/FR copy parity;
- raw filter JSON available progressively, not as the only interface;
- does not block ordinary Research when the user supplies no filter.

## Pipeline integration

The long-term representation should be visible in Pipeline Studio as a scope/filter stage rather than hidden inside `rag.py`.

Add/extend a registered strategy concept such as:

```text
filter.research_scope
```

with scholarly effect `scope_constraint`.

Pipeline execution must record:

- input candidate count when measurable;
- output candidate count;
- filter source;
- field identities involved;
- fallback/degradation reason;
- whether storage prefiltering or postfiltering was required.

Do not make filter predicates tunable constants in a saved pipeline. The pipeline declares that a filter stage exists; the request supplies the researcher's filter plan.

## Relationship to whole-work / coverage-aware Research

This filter work is a prerequisite for broader Research modes.

A future “Whole-work overview” stage should first resolve the selected work(s) through the same scope contract, then perform coverage-aware analysis over those eligible Records before generating grounded retrieval subqueries.

The intended future chain is:

```text
resolved work scope
  → representative/complete work coverage
  → derived advisory work map
  → grounded query expansion
  → exact evidence retrieval within the same scope
  → coverage-aware packing
  → answer generation
```

The advisory work map must never become evidence. Final claims bind to the underlying Records.

## Phased implementation

### Phase 0 — contract and plan

Status: complete in this document.

### Phase 1 — explicit backend filters

Status: complete on master. Run diagnostics label pinned evidence that bypasses the filter (`selected_evidence_exempt_count`).

Deliverables:

- shared backend validation/normalization for Chroma-style filters;
- typed Research filter plan on `RAGRunRequest`;
- metadata/document filters propagated to Research semantic and lexical candidate generation;
- explicit-scope seed retrieval combined with the user filter rather than bypassing it;
- run diagnostics include the applied scope;
- regression tests for validation, propagation, exclusion, and seed interaction.

No new frontend UI is required to complete Phase 1.

### Phase 2 — preview API

Status: implemented as `POST /api/research/filters/preview` (`routers/research_filters.py`, `research_filter_preview.py`). Diagnostics are structured codes plus parameters for the browser to localize. Field checking uses the collection's declared `filter_fields`; no collection scan, so no counts yet.

Deliverables:

- authenticated non-mutating Research filter-preview endpoint;
- field/operator diagnostics;
- plain-language explanation;
- authoritative collection compatibility check;
- bounded cost; no unbounded corpus scan.

Tests cover valid/invalid filters, unknown fields, hidden/system collection isolation, researcher authorization, no mutation, and structured diagnostics.

### Phase 3 — explicit frontend editor

Status: implemented (`web/src/domain/researchFilters.ts`, `ResearchFilterEditor.vue`, `api/researchFilters.ts`; wired into `ResearchComposer`/`ResearchView`). Deviations and gaps: the grammar adds `document contains` / `document not contains` for the document filter; autocomplete covers fields, operators and connectives but not values (the preview does not return a value inventory); field types are `any` until the catalog carries types; a failed-turn retry sends no composer filter and does not yet reuse the turn's original plan; the expression is not persisted in the draft.

Deliverables:

- framework-independent expression parser;
- field/operator/value autocomplete from the collection/schema catalog;
- local compile/validation;
- debounced server preview;
- “View Chroma expression” disclosure;
- Storybook + Vitest + Playwright/axe coverage;
- EN/FR copy.

### Phase 4 — deterministic natural-language filters

Status: implemented (`web/src/domain/researchInstructionFilters.ts`, `ResearchScopeSuggestions.vue`, `POST /api/research/filters/inventory`). Interpretation is local and proposal-only: a phrase becomes a hard filter only after the researcher presses "Add to filter", and a confirmed plan is sent with `source: deterministic_natural_language`. Works/authors resolve from a bounded, names-only inventory (500 works; fetched lazily once instructions are non-empty and cached per collection); field keys resolve through the collection's catalog, so an undeclared field yields an unresolved note instead of a proposal. Gaps: speaker values are taken literally from the wording (`verified: false`; there is no speaker inventory); "language is …" is reported as unsupported because language values are not inventoried; a named author resolves to that author's works, as the existing named-scope safeguard does, and is not treated as a speaker; EN phrases plus a small FR subset; the inventory endpoint runs `work_stats` (a collection scan, as the named-scope safeguard already does per run), so a cheaper cached inventory is a follow-up.

Deliverables:

- bounded phrase grammar;
- work/author/value resolution from corpus inventory;
- hard-vs-soft instruction classification;
- unresolved phrase reporting;
- user confirmation when interpretation is ambiguous.

Required negation regressions include “only Work A”, “exclude Work A”, “use Work A but not Work B”, “do not exclude Work A”, “speaker is not Heidegger”, and “not only Work A”.

### Phase 5 — optional model-assisted ambiguity resolver

Deliverables:

- optional browser/local model adapter behind a stable interface;
- closed output schema;
- deterministic validator;
- provenance label `model_assisted`;
- no per-keystroke inference;
- latency/download/capability UX.

This phase is optional and must not block deterministic explicit filters.

### Phase 6 — Pipeline Studio scope stage

Deliverables:

- registered Research scope strategy;
- trace integration;
- candidate-count diagnostics;
- pipeline comparison/benchmark support;
- migration away from ad hoc filter application once the Research adapter honours the stage wiring.

### Phase 7 — coverage-aware Research modes

Deliverables:

- whole-work overview;
- per-work survey;
- balanced comparison;
- cached advisory work maps keyed to source/Record-set digest and analysis contract version;
- coverage metrics and benchmark fixtures.

## Testing matrix

Backend:

- recursive filter grammar validation;
- type/operator validation;
- homogeneous `$in` / `$nin`;
- malformed logical groups;
- semantic candidate propagation;
- lexical candidate propagation;
- document-filter propagation;
- explicit-scope seed respects user filter;
- selected evidence remains pinned and is labelled as an override;
- request persistence/rerun retains exact plan;
- no filter preserves current behavior.

Frontend:

- parser precedence and parentheses;
- negation;
- quoted Unicode values;
- autocomplete from dynamic field catalog;
- unknown field/operator/value errors;
- stale preview response rejection after collection/instruction changes;
- keyboard and screen-reader behavior;
- EN/FR parity;
- narrow layout;
- no hidden raw JSON requirement for ordinary use.

End to end:

- “only Work A” never retrieves Work B;
- “exclude Work A” never reintroduces Work A through explicit-scope seeding;
- filtered semantic, lexical, and MMR routes agree on eligibility;
- rerun uses identical resolved filter;
- filtering cannot produce citations to excluded Records unless the Record was explicitly pinned and the run visibly records that exception.

## Benchmark and evaluation additions

Add fixed Research cases that measure:

- scope leakage rate;
- exclusion violation rate;
- requested-work coverage;
- per-work balance for comparisons;
- section/region coverage for overviews;
- evidence diversity after filtering;
- citation/source-binding fidelity;
- latency added by interpretation/preview;
- deterministic parser accuracy on a curated instruction set.

Filter correctness should be evaluated independently from final answer quality. A fluent answer does not compensate for scope leakage.

## Migration and compatibility

- Existing Research requests without a filter plan must behave exactly as before.
- Existing saved/rerunnable runs without the new field deserialize with no filter.
- Do not reinterpret historical free-text instructions on rerun; only newly compiled filter plans execute as hard constraints.
- Preserve the current explicit named-work/author safeguard until equivalent typed scope behavior has regression coverage.
- Do not remove the System Data Chroma console. Share validation helpers where safe, but keep its system-collection authorization boundary distinct from Research corpus filtering.
- If the minimum Chroma version is raised to support additional filter operators, change `api/requirements.txt`, document the compatibility reason, and add a regression test.

## Agent handoff rules

Agents continuing this work should:

1. start from current `master` and inspect concurrent PRs before modifying shared RAG/pipeline files;
2. keep each phase independently reviewable;
3. add behavior tests with every execution change;
4. avoid introducing a frontend NLP/model dependency before deterministic parsing exists;
5. keep semantic field resolution schema-driven;
6. never let filter interpretation establish evidence or scholarly authority;
7. preserve selected-evidence behavior unless an explicit product decision changes it;
8. update this document when a contract decision changes, not for routine progress narration;
9. update `docs/USER_GUIDE.md` once user-visible filter controls ship;
10. update `docs/ARCHITECTURE.md` when the scope stage becomes part of the executable Research pipeline.
