# Static-analysis follow-ups (0.61.0)

The initial gates run across `api/app` and `web/src`; they do not replace any
runtime tests. These items are tracked debt, not evidence that the underlying
code is correct. Resolve each with an isolated change and remove its suppression.

## Backend

- [ ] SA-01: expand compact Python statements per module (Ruff E701/E702).
- [ ] SA-02: enable mypy strict optional checking after typing nullable payloads.
- [ ] SA-03: type Pydantic literal-list default factories (`models`).
- [ ] SA-04: annotate lazy Chroma clients and accumulators; remove branch-local redefinitions.
- [ ] SA-05: give RAG query/evidence payloads TypedDict contracts.
- [ ] SA-06: validate and type external catalog/provider JSON in `llm_tools`.
- [ ] SA-07: type enrichment schema families and checkpoint dictionaries.
- [ ] SA-08: qualify builtin list types shadowed by job-manager methods; type mixin locks.
- [ ] SA-09: use covariant sequence interfaces at language-store boundaries.

`mypy.ini` scopes temporary error-code suppressions to these modules. Undefined
names and other enabled diagnostics still fail. Missing third-party stubs are
ignored; untyped definitions are allowed. Newly extracted modules inherit no
module-specific suppressions and should opt into strict optional checking.

## Frontend

- [ ] SA-10: remove unused helpers from the legacy runtime after tracing exported/event callbacks.
- [ ] SA-11: repair missing `openSharedAnnotationRecord`, `wireEvidenceButtons`,
  and stale `selectedPayload`/`scope` references with workflow-level regression tests.
- [ ] SA-12: audit legacy browser persistence/refresh/clipboard fallbacks; expose
  actionable failures without turning harmless teardown failures into alerts.
- [ ] SA-13: remove unused setup bindings as their workflows are extracted.
- [ ] SA-14: simplify redundant regex/string escapes with matching fixtures.
- [ ] SA-15: verify OCR Unicode character-class intent against real extraction cases.
- [ ] SA-16: replace sparse Storybook casts with reusable typed partial-data builders.

Production explicit-any escapes were replaced with typed API results, PDF.js
handles, the existing DocumentLayoutPlan, direct runtime exports, and unknown
dictionary values. Storybook's remaining casts deliberately model incomplete
fixtures; each has a local explanation and lint suppression. Vue's no-undef rule
is delegated to strict vue-tsc because ESLint otherwise mistakes DOM types for
runtime variables. Correctness lint remains enabled in the JavaScript runtime.

## Initial frontend suppression inventory

Line numbers refer to the initial 0.61.0 scan (comments shift later lines).

| File | Initial line | Rule | Rationale / tracking |
| --- | ---: | --- | --- |
| `web/src/components/CorpusBoundaryAdjudication.stories.ts` | 7 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusBoundaryAdjudication.stories.ts` | 8 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusBuildHistoryMenu.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusBuildHistoryMenu.vue` | 4 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/CorpusBuildLifecycleCard.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusBuildTimeline.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusBulkMetadataEditor.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusFinishWorkspace.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusInitializationDialog.stories.ts` | 15 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusInitializationDialog.stories.ts` | 7 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusLlmTextTouchupDialog.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusMetadataIssues.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusMetadataResolutionPanel.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusProviderSwitcher.stories.ts` | 4 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/CorpusSourceSummary.vue` | 5 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/DocumentStructureConfigurator.stories.ts` | 2 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/LlmExecutionControl.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/MetadataEnrichmentDialog.stories.ts` | 1 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/PdfCorpusBuilder.vue` | 204 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/PdfCorpusBuilder.vue` | 205 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/PdfCorpusBuilder.vue` | 233 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/PdfCorpusBuilder.vue` | 234 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/components/PdfCorpusBuilder.vue` | 544 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfCorpusBuilder.vue` | 550 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfCorpusBuilder.vue` | 715 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfCorpusBuilder.vue` | 727 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfCorpusBuilder.vue` | 869 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfCorpusBuilder.vue` | 870 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/PdfEvidenceViewer.vue` | 15 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/ProviderProfileSelect.stories.ts` | 6 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/SourceTranscriptionDialog.stories.ts` | 3 | @typescript-eslint/no-explicit-any | SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields. |
| `web/src/components/record/RecordReadingPane.vue` | 59 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/components/research/ResponseFaqSelectionBar.vue` | 6 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/domain/textCleanup.ts` | 68 | no-misleading-character-class | SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics. |
| `web/src/domain/textCleanup.ts` | 7 | no-useless-escape | SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it. |
| `web/src/runtime/runtime.js` | 10343 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 10345 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 10352 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 1345 | no-useless-escape | SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it. |
| `web/src/runtime/runtime.js` | 185 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 2469 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 2594 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 2954 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 3076 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 3086 | no-undef | SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage. |
| `web/src/runtime/runtime.js` | 4946 | no-undef | SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage. |
| `web/src/runtime/runtime.js` | 5144 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 5145 | no-undef | SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage. |
| `web/src/runtime/runtime.js` | 6216 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 627 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6379 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6387 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6388 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6391 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6401 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 6429 | no-undef | SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage. |
| `web/src/runtime/runtime.js` | 6447 | no-undef | SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage. |
| `web/src/runtime/runtime.js` | 6788 | no-misleading-character-class | SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics. |
| `web/src/runtime/runtime.js` | 7720 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 7731 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 8071 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 833 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 8580 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 8952 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 9168 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/runtime/runtime.js` | 9173 | no-useless-escape | SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it. |
| `web/src/runtime/runtime.js` | 9174 | no-useless-escape | SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it. |
| `web/src/views/ResearchView.vue` | 43 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/views/SearchView.vue` | 158 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/views/SearchView.vue` | 54 | @typescript-eslint/no-unused-vars | SA-13: preserve legacy setup binding until its owning workflow is extracted. |
| `web/src/views/SearchView.vue` | 63 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/views/SearchView.vue` | 68 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
| `web/src/views/SearchView.vue` | 69 | no-empty | SA-12: legacy best-effort fallback; audit user-visible failure handling separately. |
