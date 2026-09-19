# Changelog

## 0.58.5 — Radical Rex

DerridAI 0.58.5 establishes the provenance-first research workspace as the primary product surface.

### Research and provenance

- Adds hybrid MMR/similarity candidate retrieval, metadata filtering, stable deduplication, conservative lexical targeting, and cross-encoder reranking.
- Adds source-language and canonical-work restrictions.
- Adds researcher-selected evidence mode that bypasses retrieval and synthesizes only from chosen records.
- Returns structured evidence with speaker, quoted speaker, position holder, stance, discourse role, pages, record identity, retrieval signals, and deterministic citations.
- Keeps evidence tags visible in generated answers while resolving human-readable citations deterministically.
- Adds provenance validation and visible warnings for missing or inconsistent source metadata.
- Sends compact task-specific evidence packets to the LLM rather than complete record objects.

### i18n and accessibility

- Adds catalog-driven English and French interface localization, locale persistence, and document lang/dir updates.
- Replaces user-facing API phase prose with localizable machine phase keys.
- Reworks the research UI around semantic landmarks, fieldsets and legends, explicit labels, live status/error regions, keyboard focus management, skip links, and 44px interaction targets.
- Adds visible focus styles, reduced-motion handling, higher-contrast behavior, dark-mode support, and color-independent validation severity labels.
- Adds contract tests for translation-key parity and the WCAG 2.0 AA implementation baseline.

### API and operations

- Versions the API and application as 0.58.5 while retaining hidden 0.1.0 query aliases for transitional compatibility.
- Adds a capabilities endpoint for supported research modes and locales.
- Fixes Redis job-key double-prefixing and persists failed jobs with machine-readable errors.
- Makes arbitrary Ollama model identifiers configurable instead of requiring a hard-coded enum member.
- Changes default generation parameters toward deterministic scholarly processing while keeping them environment-configurable.
- Mounts the complete static web directory so translation and stylesheet assets are served correctly.

### Scope

This release implements the research/provenance foundation against the repository available at the 0.58.5 branch point. Corpus-builder administration, provider-profile CRUD, work/edition management, annotations, and persisted grading dashboards require stores and product surfaces not present in that baseline and are not falsely represented here as complete.
