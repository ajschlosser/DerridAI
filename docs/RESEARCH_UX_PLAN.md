# Research reading workspace — integrated UX changes

PR #615 originally proposed a new Research thread rail and a replacement for the single-run workspace, based on a much older version of DerridAI. The current master branch already has persistent multi-turn Research Threads, pinned turns, export, comparison, source-aware attribution, saved URL state and compact follow-up composition. Reintroducing the legacy navigation would remove those features.

## Integrated

- Evidence gets half the available reading width. Container queries stack answer and inspector in genuinely narrow *nested* workspaces, rather than depending only on the browser viewport.
- The evidence inspector puts passage text and a full citation before attribution fields, leaving retrieval diagnostics in a disclosure.
- Answer ↔ evidence highlighting is linked by the existing ambiguity-aware citation resolver. Hover and keyboard focus preview the same evidence link without changing selection.
- The run header reports collection, recorded preset, cited/retrieved evidence, model, duration and response-cache provenance.
- Citation totals count only unambiguously bound evidence in the answer body, not ambiguous citations, unsupported markers, or Works Cited references.

## Preserved from the current application

The ResearchThreadBrowser, ResearchThreadNavigation, ResearchComposer, ResearchThreadAnswer, ResearchTurnInspector, research filters, history, retries, pinned turns, export and current citation validation remain authoritative. Older thread-list replacements, snapshot baselines and top-level view rewrites are intentionally not reintroduced.

## Follow-up validation

CI includes frontend unit tests, formatting, types, accessibility, Playwright, and backend locale parity. Manual screen-reader and nested-width visual assessment remain separate release tasks.
