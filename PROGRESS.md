# Progress

## Corpus Builder generic media

Status: deterministic check passed. Source ingest is now its own component.

`SPECIFICATION.md` is not in this repository. This section follows `docs/REFACTOR_PLAN_0.61.md` (extract UI from the builder monolith; do not restyle unrelated files in the same change) and the release requirements for English/Québec French strings, keyboard access, visible focus, and WCAG-oriented checks.

Corpus Builder ingest covers plain text, rich text, Word (`.docx`), images, audio, URLs, and Project Gutenberg. On load, a deterministic check fills `document_author`, `speaker`, title, and related fields, and records source quality. The illegibility slider stays before Choose source PDF.

The setup controls live in `CorpusSourceIngest.vue`, with a Storybook story (`Corpus Builder/Source/Ingest`) and `web/tests/frontend/corpus-source-ingest.test.ts`. Labels, slider value text, a non-tabbable file input, 24px minimum targets, and visible focus are in that component. `aria-busy` is set only while a load is running. The saved-source menu no longer says the library is PDF-only. New strings are in both locale dictionaries.

Ingest implementation is split so none of the new modules is a monolith: `source_media.py` detects the file and keeps the public API; `source_text.py` handles text, Word, HTML, and deterministic metadata; `source_audio.py` transcribes the whole file with OpenAI Whisper, then uses whisperx, then writes spans; `source_gutenberg.py` searches and loads texts. `source_kinds.py` holds the shared suffix sets.

There is no Prettier config or CI format step, so the new component is formatted for reading. Running Prettier across `PdfCorpusBuilder.vue` would rewrite unrelated lines.

Checks: `tests/test_0610_warbling_wombat.py` passed (10). Mypy on the five source modules passed. The ingest component tests passed (2). ESLint on `CorpusSourceIngest.vue` passed.
