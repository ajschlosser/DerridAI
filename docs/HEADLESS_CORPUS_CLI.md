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

# Headless corpus CLI

This document is the implementation contract and progress tracker for a
non-interactive, cross-platform Corpus Builder command. It is a focused current
architecture document, not a release note.

## Product goal

DerridAI should ship an operating-system-native command named `derridai` that can
take a supported source plus a versioned YAML processing configuration and produce
a finished corpus without requiring the web application or interactive review.

Canonical invocation:

```bash
derridai corpus build \
  --source heidegger.pdf \
  --config corpus-processing.yaml \
  --output heidegger.jsonl.zst
```

A compatibility shorthand may also be supported:

```bash
derridai --source heidegger.pdf --config corpus-processing.yaml
```

The executable must be distributable for:

- Ubuntu Linux;
- Windows 11;
- macOS on Apple Silicon and Intel, either as separate artifacts or a validated
  universal artifact where all native dependencies permit it.

## Distribution decision

The CLI is implemented in Python alongside the existing corpus engine and compiled
into native executables with Nuitka. The corpus engine is **not** being rewritten in
C or C++.

Nuitka is appropriate because it compiles Python through generated C and supports
standalone/onefile deployment on Linux, Windows, and macOS. The build still contains
the CPython runtime semantics and native extension libraries needed by dependencies;
"native binary" here means that users run an OS-native executable and do not install
Python or DerridAI's Python packages themselves.

The packaging sequence is deliberately conservative:

1. make `--mode=standalone` pass on each target OS;
2. test source ingestion and corpus publication from that distribution;
3. only then enable `--mode=onefile` where it is reliable.

Nuitka itself recommends validating standalone mode before onefile mode. Onefile
extracts its payload at runtime, so a single-file executable is a distribution
convenience rather than an architectural requirement.

Builds are produced on the target operating system in CI. We do not assume a single
Linux build host can emit trustworthy Windows/macOS artifacts.

Build-time reference:
<https://nuitka.net/user-documentation/user-manual.html>

## Binary boundary

The binary is a second frontend to the existing corpus engine. It must not:

- automate the browser;
- call DerridAI's own HTTP API;
- duplicate extraction, segmentation, enrichment, or publication logic;
- turn model suggestions into human-confirmed assertions;
- flatten provenance merely to simplify binary packaging.

The intended dependency direction is:

```text
source + CorpusRunConfig
              |
              v
      HeadlessCorpusRunner
              |
              v
       shared corpus engine
 ingest -> extract -> segment -> enrich -> validate
              |
              v
        output projector
        /             \
 research corpus    cELF publication
```

FastAPI and the native CLI translate transport-specific inputs into shared
application-level requests. Neither is the implementation of the pipeline itself.

## External executables and model resources

A native DerridAI executable does not imply that every optional research dependency
must be linked into the same file.

The current source pipeline can use external tools such as Tesseract and FFmpeg, and
some Document Intelligence providers use large language/model data. Packaging these
blindly into one executable would create a large, difficult-to-audit artifact and
complicate third-party licensing.

The initial distribution policy is:

- native PDF/text processing required for the basic corpus workflow is part of the
  distribution;
- media-specific executable helpers are treated as explicit managed companions or
  optional system dependencies until their redistribution/license/update policy is
  settled;
- language/NLP model packs remain data resources, not compiled application code;
- an LLM provider remains an external runtime service unless a later execution
  profile explicitly embeds one;
- `derridai doctor` will eventually report which optional capabilities are
  available and why a requested configuration cannot run.

A requested pipeline must fail before expensive work when one of its required
runtime capabilities is unavailable.

## YAML configuration contract

The YAML document is a versioned application contract independent of the web form and REST request
model. Version 1 remains a compatibility input. Version 2 is the preferred run envelope: it retains
the same source/provider/review/publication settings while embedding the exact resolved Corpus
Builder pipeline definitions, canonical hashes, and required strategy versions. `derridai config
migrate` converts a v1 file using the current installed assignments.

Legacy v1 shape:

```yaml
version: 1

source:
  ocr_mode: auto
  ocr_languages: eng+fra+deu
  detect_page_numbers: true
  audio_diarization: true

processing:
  profile_id: derrida-scholarly-v12

  segmentation:
    mode: semantic
    preferred_record_chars: 1750
    record_length_tolerance: 200
    long_record_chars: 3500
    absolute_record_chars: 6000

  text:
    clean: true
    llm_touchup: false

  document_intelligence:
    profile: scholarly
    provider: auto
    include_events: false

metadata:
  schema_id: default
  work: {}
  document: {}
  guidance: {}

enrichment:
  mode: deep
  semantic_indexing: false
  passes: 1

provider:
  type: ollama
  model: qwen3:14b
  base_url: http://localhost:11434
  concurrency: 1

review:
  mode: automatic
  min_confidence: 0.8
  unresolved: best_guess

publication:
  profile: research
  compression: zstd
```

Rules:

- unknown keys fail validation;
- the configuration version is mandatory;
- validation completes before source extraction;
- relative paths resolve relative to the YAML file, not the current working
  directory;
- secrets are accepted through environment variables/credential mechanisms rather
  than being required in YAML;
- the fully resolved non-secret configuration is retained with the run for
  reproducibility.

## Output profiles

### `research`

The research projection is optimized for downstream retrieval and analysis. Each
JSONL row contains:

- stable `record_id`;
- authoritative Record `text`;
- minimal source location needed for traceability/citation;
- materialized fields from the selected metadata schema.

It excludes review/UI state, execution ledgers, prompt traces, caches, derived NLP
annotations, and other implementation details. It is an explicit allow-list
projection; it must not become "cELF minus whatever keys happened to look internal."

### `celf`

The cELF projection retains the durable identity, assertion, provenance, evidence,
revision, publication, warning, and conformance information required by the cELF
profiles DerridAI claims.

The existing compact `.jsonl.zst` publication is the first supported artifact. A
later packaging milestone may add a corpus package for publication-level objects
such as the metadata-contract snapshot and conformance report without duplicating
those objects into every Record.

`--celf` is a command-line override for `publication.profile: celf`. Internally
this is an output profile rather than a boolean.

A v2 build performs pipeline compatibility preflight before source extraction. It rejects missing
strategies and an installed assignment whose ID/version/hash differs from the embedded binding.
Direct execution from embedded definitions is still a migration step; until that lands, the
preflight is a drift guard rather than a claim that system assignments cannot change during an
already-running build.

## Automatic review semantics

Headless operation must make review policy explicit.

`review.mode: automatic` means:

- suggestions may be selected into the immutable publication snapshot;
- selected model values retain model derivation and unreviewed/autonomous authority;
- policy admission never becomes `human_confirmed`;
- deterministic schema, evidence, text-conservation, and source-mapping validators
  remain blocking;
- unresolved states remain explicit where the selected publication profile supports
  them;
- the research projection may omit epistemic machinery from the serialized row, but
  it must be built from a validated canonical build state, not from unvalidated
  model output.

The existing `accept_unreviewed` publication path is the compatibility baseline,
but the CLI will expose the policy in configuration instead of hiding it in a
transport flag.

## Command contract

Planned stable commands:

```text
derridai --version
derridai config validate --config FILE
derridai config migrate --config FILE [--output FILE] [--json]
derridai pipeline capabilities [--json]
derridai pipeline export --pipeline-id ID --version N [--output FILE]
derridai pipeline validate --config FILE [--json]
derridai corpus build --source FILE --config FILE [--output FILE] [--celf]
derridai doctor [--json]
```

Operational rules:

- human-readable progress goes to stderr;
- the final machine-readable result can be emitted to stdout with `--json`;
- non-zero exit codes are stable categories, not arbitrary exception values;
- SIGINT/console cancellation requests a clean pipeline cancellation and leaves
  resumable checkpoints where safe;
- output replacement is atomic;
- a failed build never leaves a partially written file at the requested final path.

Initial exit-code categories:

| Code | Meaning                         |
| ---: | ------------------------------- |
|    0 | success                         |
|    2 | command/configuration error     |
|    3 | unsupported or unsafe source    |
|    4 | missing runtime capability      |
|    5 | extraction/segmentation failure |
|    6 | provider/enrichment failure     |
|    7 | validation/publication failure  |
|    8 | output I/O failure              |

## Implementation phases and progress

Status values are `DONE`, `IN PROGRESS`, `TODO`, and `BLOCKED`.

| Phase                                | Status      | Work                                                                                                                                                                                   |
| ------------------------------------ | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0. Architecture                      | DONE        | Establish native-binary/Nuitka direction, shared-engine boundary, output profiles, automatic-authority rules, and versioned YAML contract.                                             |
| 1. CLI/config spine                  | IN PROGRESS | v1 validation/build wiring is implemented; v2 embeds pipeline definitions/hashes/strategy versions and v1 migration is implemented; direct embedded-definition execution remains.      |
| 2. Headless runner                   | IN PROGRESS | Synchronous source-to-publication orchestration through the shared Corpus Builder is implemented; compiled-binary end-to-end acceptance remains.                                       |
| 3. Automatic settlement              | IN PROGRESS | The headless runner uses shared autonomous settlement without granting human authority; broader end-to-end regression coverage remains.                                                |
| 4. Research projection               | IN PROGRESS | Schema-driven allow-list research `.jsonl.zst` output and atomic replacement are implemented; a research reproducibility/integrity sidecar remains.                                    |
| 5. cELF projection                   | IN PROGRESS | cELF output routes through canonical publication/conformance and copies the canonical integrity sidecar; compiled-binary acceptance remains.                                           |
| 6. Runtime diagnostics               | IN PROGRESS | `derridai doctor` reports platform, writable paths, helpers, NLP resources, source-kind readiness and pipeline bindings; provider reachability is intentionally not probed by default. |
| 7. Native packaging                  | IN PROGRESS | Add Nuitka build configuration and target-OS CI matrix; prove standalone artifacts first, then evaluate onefile.                                                                       |
| 8. Cross-platform acceptance         | TODO        | Run the same deterministic fixture corpus on Ubuntu, Windows 11-compatible runner, macOS x86_64, and macOS arm64; compare semantic output/integrity expectations.                      |
| 9. Documentation/release integration | TODO        | Update README, USER_GUIDE, ARCHITECTURE, CONTRIBUTING, release gates, artifact signing/checksums, and installation instructions.                                                       |

## Acceptance criteria

The feature is complete when all of the following are true:

1. A user can download a DerridAI executable for a supported OS and run it without a
   separately installed Python interpreter.
2. The same YAML and source produce equivalent canonical Record content across
   supported platforms, allowing for explicitly documented extractor/platform
   differences.
3. A PDF with a native text layer can complete source ingestion through publication
   without the API server or browser.
4. Metadata enrichment can run unattended through a configured Ollama or
   OpenAI-compatible provider.
5. `publication.profile: research` emits only the intended research Record surface.
6. `publication.profile: celf` emits the cELF publication surface and a deterministic
   conformance report.
7. Automatic decisions never claim human authority.
8. Text-conservation/source-mapping failures remain hard publication blockers.
9. The binary returns stable exit codes and never prints provider credentials.
10. CI builds and smoke-tests target-native artifacts on Linux, Windows, and macOS.

## Testing strategy

The CLI core is tested without invoking Nuitka:

- Pydantic/YAML validation and unknown-key rejection;
- path resolution;
- secret redaction;
- CLI parsing and exit-code behavior;
- headless-runner orchestration using the existing repository/build test fixtures;
- research/cELF projection golden fixtures;
- cancellation and atomic-output behavior.

Binary acceptance is a separate CI layer. Each OS runner builds the executable with
Nuitka and runs smoke/integration tests against the compiled artifact. This keeps
compiler/packager failures distinct from Python-domain regressions.

## Known risks

### Dependency closure

DerridAI imports libraries with native modules and package data. Nuitka package
configuration may need explicit handling. The solution is to keep the CLI import
graph narrow and to test standalone mode before attempting onefile mode.

### Artifact size

The API environment contains dependencies the CLI does not need for every workflow.
The CLI should not import FastAPI, web authentication, GraphQL, or unrelated job
surfaces merely because they share a repository. Optional NLP/model resources should
stay external data where practical.

### Linux portability

A Linux executable is not automatically portable to every distribution/glibc
baseline. The supported Ubuntu baseline must be explicit and the release artifact
must be built/tested against that baseline.

### macOS architecture and signing

Apple Silicon and Intel dependencies must be validated independently unless a
universal artifact is proven end-to-end. Release packaging eventually needs
codesigning/notarization rather than treating an unsigned CI executable as the final
distribution.

### Onefile behavior

Onefile executables unpack at runtime. Temporary-path semantics, antivirus behavior,
startup cost, bundled companion executables, and data-file discovery must be tested
before onefile becomes the default distribution format.
