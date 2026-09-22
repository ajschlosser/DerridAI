<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Backend test suite

Run from the repository root (see [CONTRIBUTING.md](../CONTRIBUTING.md) for the environment variables that point the tests at a scratch data directory):

```bash
pytest -q
```

The tests need no Docker, Ollama, GPU, or real ChromaDB. Files that import `app.corpus_builder`, `app.chroma_store`, or `app.rag` install a stub `chromadb` (or `app.rag`) module first.

## How to read a test file

Every file starts with a module docstring saying **what area it covers, why it exists, and how it tests it**. Every test function then has a docstring with the specific scenario and, where it is not obvious, the reason the behavior matters. Helper functions and fake classes are documented too.

## Naming

File names describe the behavior under test (for example `test_review_queues.py`, `test_boundary_adjudication.py`); they do not encode a release. Add a test to the file for its subject, or create a new topical file.

## Areas

| Area | Files |
| --- | --- |
| Corpus Builder: segmentation and topology | `test_corpus_build_resilience`, `test_segmentation_default_keep`, `test_segmentation_candidates`, `test_record_topology`, `test_boundary_suspects_and_undo`, `test_boundary_adjudication` |
| Corpus Builder: metadata, provenance, review | `test_hybrid_metadata`, `test_profile_identity_and_metadata_gating`, `test_primary_text_editing`, `test_review_decisions`, `test_review_queues`, `test_metadata_stage_checkpoints`, `test_human_overrides_and_reruns`, `test_human_metadata_ownership`, `test_bulk_review_during_enrichment`, `test_metadata_constraints`, `test_editorial_memory_and_provider_switch`, `test_corpus_provider_credentials`, `test_reviewer_document_structure`, `test_confident_autofill` |
| Corpus Builder: text, layout, publication | `test_semantic_atoms_and_mla_citations`, `test_source_quality_and_publication_schema`, `test_publication_lifecycle`, `test_text_cleanup_and_adaptive_enrichment`, `test_verse_cleanup_and_rejected_records`, `test_document_layout` |
| Failure handling | `test_failure_visibility` |
| Authentication, roles, researcher policy | `test_roles_and_rag_request_validation`, `test_researcher_profile_generation_options`, `test_auth_hardening`, `test_researcher_rag_profile`, `test_researcher_text_policy`, `test_content_filter_false_positives`, `test_language_content_policy`, `test_researcher_route_policy` |
| Persistence and vector store | `test_sqlite_persistence`, `test_collection_name_schema`, `test_packet_reduction`, `test_chroma_connection` |
| Languages and translation | `test_locale_dictionaries`, `test_language_translation_validation`, `test_language_translation_resume`, `test_language_translation_repair`, `test_locale_and_accessibility_floor` |
| Release housekeeping | `test_release_consistency` |

## Conventions

- Test behavior, not source text. A few older tests still check that a hook exists in a source file; their docstrings say so.
- Do not hard-code the release version in tests; `test_release_consistency.py` is the one place that checks version agreement. Tests that pin the corpus *profile* or *prompt* version ids (for example `test_profile_and_prompt_ids_are_pinned`) do so deliberately, and must be updated when those ids are bumped.
- Prefer temporary directories (`tmp_path`) and monkeypatching over real services.
- `tests/fixtures/` holds JSON inputs (for example `corpus_builder/topology_cases.json`). Add a case there to extend coverage without new test code.
