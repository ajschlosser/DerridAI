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

# Frontend domain layer

`web/src/domain/` contains the frontend's framework-light domain helpers: workspace state models, transformations, formatting, presenters, validation helpers, URL/state codecs, and rules that are easier to test outside Vue components.

The directory is intentionally broad, but it should not become a dumping ground. Group behavior by the product concept it represents and keep network/DOM effects at outer layers whenever practical. Follow [`docs/CODE_READABILITY.md`](../../../docs/CODE_READABILITY.md) for naming and behavior-preserving refactor conventions.

## Architectural role

```mermaid
flowchart LR
    API["api/ + realtime/"]
    Stores["stores/ + composables/"]
    Domain["domain/<br/>state rules · presenters · codecs · transforms"]
    Components["components/"]
    Views["views/"]
    Tests["tests/frontend/*-domain.test.ts"]

    API --> Stores
    Stores --> Domain
    Domain --> Components
    Domain --> Views
    Domain --> Tests
```

Some compatibility modules still bridge older runtime behavior, so this diagram expresses the target dependency direction rather than pretending every existing file is side-effect free.

## Major topic families

The flat namespace currently groups related modules by filename prefix:

- `record*`, `records*`, `pastedRecord.ts` — record editing, formatting, querying, workspace state, subsets, mutation queues, and table helpers.
- `research*`, `evidenceSelection.ts`, `citations.ts` — Research request/response state and evidence presentation.
- `search*` — query, facets, filter schema, and Search workspace state.
- `pipeline*` — Pipeline Studio graph, bindings, presentation, workflows, and analysis presentation.
- `metadata*`, `fieldAssertions.ts`, `documentFields.ts`, `nlpTags.ts` — metadata field, evidence, assertion, precedent, and schema-facing behavior.
- `corpus*`, `reviewPresentation.ts`, `touchupFields.ts`, `documentLayoutRegions.ts` — Corpus Builder and review-facing helpers that are shared beyond its feature package.
- `provider*`, `sharedProviderProfiles.ts` — provider model/profile behavior.
- `navigation*`, `urlState*`, `workspace*`, `shared*` — cross-workspace state and navigation contracts.
- `semantic*` and `relations/` — semantic-map/graph presentation and relation primitives.

## What belongs here

Good candidates are deterministic transformations, selectors, serializers/codecs, presentation models, validation helpers, and state transition rules that do not require a Vue component to exist.

Prefer `composables/` for Vue lifecycle/reactivity orchestration, `api/` for network calls, `components/` for rendering and direct interaction, and `stores/` for application-wide reactive state.

When adding a large new domain, consider a focused subdirectory rather than extending the flat namespace indefinitely. Preserve existing public imports when refactoring and add focused Vitest coverage.

## Naming and documentation

Domain code is read frequently during debugging because it sits between raw API/state shapes and visible behavior. Optimize it for inspection:

- Prefer names that expose the transformation (`normalizedFieldText`, `recordsByWork`, `previousValue`) over one-letter temporaries outside conventional index/math loops.
- Use JSDoc on exported algorithms when the type signature does not explain semantics such as determinism, scoring, ordering, rollback, or authority.
- Comment the reason for compatibility branches, heuristics, stable ordering, and defensive fallbacks. Do not comment obvious mapping/filtering syntax.
- Prefer guard clauses and named predicates over nested ternaries. If the same non-obvious state reconstruction appears twice, extract a small typed helper rather than duplicating the loop.
- New modules should define narrow local interfaces instead of defaulting to `type Loose = Record<string, any>`. Existing `Loose` boundaries are migration debt; keep them contained rather than spreading them into new APIs.
- Remove migration-history comments such as “moved verbatim” once the implementation is materially rewritten. Git preserves that history; source comments should explain the current contract.

For tests, place pure-domain coverage in `web/tests/frontend/` near the concept being exercised. Use Playwright only when browser composition, accessibility, routing, or integration behavior is essential to the assertion.

For readability, use names that expose the rule being computed (`normalizedRuleValue`, `recordsByWork`, `candidateCount`) rather than carrying short names from the legacy runtime. Comments should explain compatibility behavior, reconstruction logic, ranking semantics, or stale-state rules rather than restating an expression.
