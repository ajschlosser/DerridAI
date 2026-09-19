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

Most files are named after the release they were written for, for example `test_0450_energized_elephant.py` is release 0.45.0 ("Energized Elephant") and `test_03516_tongue_tied_again.py` is 0.35.16. The name records *when* the behavior was introduced; the docstring says *what* it is. Newer topical files (`test_0610_*`, `test_packet_reduction.py`, `test_release_consistency.py`) are named for their subject.

## Areas

| Area | Files |
| --- | --- |
| Corpus Builder: segmentation and topology | `test_0401`, `test_0408`, `test_0409`, `test_04010`, `test_0540`, `test_0550` |
| Corpus Builder: metadata, provenance, review | `test_0410`, `test_0421`, `test_0430`, `test_0435`, `test_0440`, `test_0450`, `test_0460`, `test_0470`, `test_0480`, `test_0490`, `test_0500`, `test_0600`, `test_0610_confident_autofill` |
| Corpus Builder: text, layout, publication | `test_0407`, `test_0420`, `test_04025`, `test_0520`, `test_0530`, `test_0575` |
| Failure handling | `test_0610_failure_visibility` |
| Authentication, roles, researcher policy | `test_0313`, `test_03510`, `test_0610_auth_hardening`, `test_0610_research_profile`, `test_all_the_little_things`, `test_bits_and_bobs` |
| Persistence and vector store | `test_0361`, `test_0370`, `test_packet_reduction` |
| Languages and translation | `test_0350`, `test_03512`, `test_03516`, `test_03517`, `test_0461` |
| Release housekeeping | `test_release_consistency` |

## Conventions

- Test behavior, not source text. A few older tests still check that a hook exists in a source file; their docstrings say so.
- Do not hard-code the release version in tests; `test_release_consistency.py` is the one place that checks version agreement. Tests that pin the corpus *profile* or *prompt* version ids do so deliberately, and must be updated when those ids are bumped.
- Prefer temporary directories (`tmp_path`) and monkeypatching over real services.
- Many files define a `text(path)` helper that is unused; it is documented as such and can be removed.
- `tests/fixtures/` holds JSON inputs (for example `corpus_builder/topology_cases.json`). Add a case there to extend coverage without new test code.
