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

# Source ingestion safety and fidelity

Corpus Builder accepts multiple source-media kinds. This document is the current ingestion contract: source content is untrusted input, extracted source identity must remain auditable, and controls/evidence coordinates must match the selected medium rather than inherit PDF assumptions.

## Cross-format rules

Every ingestion path must:

- validate format before expensive processing;
- bound upload/download bytes and format-specific resource expansion;
- never execute embedded macros, scripts, fields, active objects, external relationships, or document-provided commands;
- reject unsupported or unsafe media rather than attempting a permissive best-effort parse;
- use timeouts/bounds around probes, extraction, OCR, transcription, downloads, and other external/tool work;
- preserve extractor/tool/version and source-identity provenance;
- preserve an immutable extracted/source representation alongside later human cleanup/transcription revisions;
- conserve source text/content through segmentation except for explicitly defined, auditable normalization;
- surface extraction/probe/transcription failures instead of converting them into apparently valid empty records.

## Format boundaries

| Source kind       | Required safety/fidelity behavior                                                                                                                                                                                                                                                                               |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PDF               | Validate the file; use native text and bounded OCR fallback where needed; preserve physical-page and printed-page distinctions; retain extraction/page-label warnings; never treat embedded active content as executable.                                                                                       |
| DOCX              | Treat as an archive/XML container; reject malformed structures, dangerous entity/expansion behavior, active objects/fields and external relationships; enforce compressed/uncompressed resource bounds; preserve extracted text and extractor provenance.                                                       |
| RTF               | Validate header/group structure and nesting; reject embedded objects/active fields and pathological depth/size; extract text without executing control content.                                                                                                                                                 |
| Plain text        | Enforce byte/encoding limits and preserve source text; do not invent page semantics.                                                                                                                                                                                                                            |
| Images            | Decode only supported inert formats; enforce byte and pixel/dimension limits before OCR; reject unsupported active/vector formats where the safe path does not support them; image metadata is data, not executable content.                                                                                    |
| Audio             | Validate codec/container through bounded probing; enforce byte/duration/time limits; request word and segment timestamps; align words when the provider supplies only segments; diarize independently; bind speakers to aligned words before reconstructing timed speaker turns; preserve provider transcript, diarization labels, timing, uncertainty, and reviewed speaker identity as distinct provenance; allow human transcript/speaker revisions without overwriting extraction history. |
| URL               | Fetch only through the supported bounded ingestion path; preserve requested/final source identity and extraction provenance; do not treat remote page scripts as executable application content.                                                                                                                |
| Project Gutenberg | Resolve edition identity explicitly; preserve selected edition/source URL/digest/metadata; enforce network/encoding/size limits; identical text from different editions must not collapse scholarly source identity.                                                                                            |

## Media-specific evidence and controls

UI and API behavior must follow the media kind.

- PDF/document workflows may expose OCR, page navigation, printed-page mapping, and page-based layout controls when those concepts actually exist.
- Audio exposes playback/time ranges, transcript/speaker evidence, and audio-specific diagnostics. Time spans are evidence coordinates; they are not disguised page numbers.
- Text, image, URL, and Gutenberg sources must omit PDF-only controls unless the extractor has produced a real paged-document representation with an explicit contract.
- APIs must reject invalid cross-media mutations (for example, page-layout edits against an audio source) rather than silently accepting irrelevant fields.

## Regression coverage

The ingestion boundary suite should cover at least:

- malformed input for every supported parser;
- oversized input and decompression/expansion/resource bombs;
- unsupported media/codec/encoding cases;
- embedded active content and external relationships;
- missing optional audio/tool dependencies;
- probe/extraction/transcription/download timeouts;
- image pixel limits;
- audio duration limits, invalid/empty transcripts, word-alignment fallbacks, speaker changes inside transcription segments, and ambiguous speaker overlaps;
- Project Gutenberg lookup/edition/identity/digest behavior;
- extractor provenance persistence;
- source-text conservation and human revision behavior;
- media-specific API/UI constraints.

The exact test count is intentionally not documented here; it changes as coverage grows. CI and the focused tests are the authority for current validation status.

## Release-readiness note

Passing parser/unit tests is not equivalent to full release readiness or WCAG conformance. A source-ingestion change that affects UI behavior must also pass the repository's frontend type/unit/build gates and relevant Playwright/axe WCAG 2.2 AA coverage; dependency/tool changes must be exercised in the environments they affect. Document any gate that could not be run in the PR/release note rather than in this evergreen contract.
