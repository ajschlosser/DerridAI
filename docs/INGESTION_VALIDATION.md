<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Source ingestion validation

Base: master `18866bfd272cdcdd99b5e55709562b52b2f02ea9`.

The changes implement the SourceDocument/SourceSpan, source-text fidelity,
RecordRevision, and visible-failure requirements in SPECIFICATION.md.

| Boundary | Regression coverage |
| --- | --- |
| DOCX | Malformed ZIP/XML, entity declarations, expansion bombs, active objects/fields and external relationships, upload limit, entity-preserving text extraction, persisted extractor provenance |
| RTF | Bad header, unbalanced/deep groups, embedded objects/fields, upload limit |
| Images | Malformed input, unsupported GIF/SVG, pixel limit, upload limit, valid PNG conversion, inert script-like PNG metadata |
| Audio | Missing optional diarizer/ffprobe/credentials, unsupported codec/format, probe timeout, byte/duration limits, empty/unlocated/invalid transcripts, transcription timeout, real multipart serialization, diarization failure, text conservation, timed speaker citations, human text revisions |
| Gutenberg | Failed lookup, no results, multiple editions, timeout, encoding, metadata and selected identity, wrong file edition, size limits, exact download digest/URL, distinct assets for identical text from different editions |
| Media controls | Audio/text omit OCR, PDF navigation, layout readiness and manifest page bounds; audio playback and timed speaker evidence; API rejects page edits for audio |

Validation completed locally:

- Full backend suite: 512 passed. One additional PNG metadata regression was then added; the final ingestion boundary suite passed all 49 tests.
- Frontend: 551 tests passed in 107 files.
- Ruff, mypy, Python compilation, frontend lint and TypeScript checks passed.
- Production and Storybook builds passed. Vite reports the existing large-bundle warning.
- Changed Vue/TypeScript files were formatted with Prettier; English/French locale parity is covered by regression tests.

Limits: browser accessibility/E2E checks could not run because Playwright's
Chromium download was truncated. Docker is unavailable. Remote CI was not run:
these changes are uncommitted and have not been pushed. Audio/provider and
Gutenberg network responses are simulated in deterministic tests; no live
Whisper/whisperx model session was run. This validation does not assert full
WCAG conformance or release readiness.

Audio still uses legacy navigation slots inside the extraction workspace.
Published record spans and citation locations use time ranges and speakers;
those navigation slots are not evidence page numbers. New non-PDF extraction
identities include the extraction contract version, so old cached extraction
results do not bypass the new checks. Historical assets are not rewritten.
