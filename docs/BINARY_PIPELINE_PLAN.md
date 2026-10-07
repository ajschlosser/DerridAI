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

# Binary corpus pipeline plan

This document is the implementation contract and progress tracker for shipping the
headless DerridAI document-to-corpus pipeline as a native command-line executable on
Ubuntu, Windows 11, and macOS.

It complements [HEADLESS_CORPUS_CLI.md](HEADLESS_CORPUS_CLI.md). That document
defines the headless corpus semantics and YAML contract. This document owns binary
packaging, distribution, installation, cross-platform acceptance, artifact size,
release engineering, and the work required to keep the binary a thin frontend over
the shared corpus engine.

## Goal

A user should be able to obtain one executable, place it on PATH, and run:

```bash
derridai corpus build \
  --source heidegger.pdf \
  --config corpus-processing.yaml \
  --output heidegger.jsonl.zst
```

The command must not require:

- a separately installed Python interpreter;
- a virtual environment;
- the DerridAI web UI;
- the FastAPI server;
- Docker;
- a browser.

The command may depend on an explicitly configured external LLM service such as
Ollama or an OpenAI-compatible endpoint. Media-specific helper programs and large NLP
model resources are handled as capabilities rather than silently bundled into every
binary.

## Architectural decision

The corpus pipeline remains Python. The native executable is compiled/package-managed
with Nuitka.

This is intentionally **not** a C/C++ rewrite. A second implementation of source
ingestion, segmentation, FieldAssertion handling, enrichment, provenance, review
authority, publication, and cELF validation would create two scholarly truth paths.
The binary instead imports the same application-layer engine used by the web/API
surface.

The boundary is:

```text
                     +----------------------+
source + YAML ------>| HeadlessCorpusRunner |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | shared corpus engine |
                     | ingest               |
                     | extract              |
                     | segment              |
                     | enrich               |
                     | validate             |
                     | publish              |
                     +----------+-----------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
      research .jsonl.zst             cELF publication
```

FastAPI and the CLI are transport adapters. Neither owns the corpus algorithm.

## Shared Pipeline Studio / CLI configuration contract

The binary must not evolve a second configuration language that shadows Pipeline
Studio. The synchronization and compatibility rules are defined in
[PIPELINE_CONFIGURATION_CONTRACT.md](PIPELINE_CONFIGURATION_CONTRACT.md).

The existing backend pipeline system is the authority:

- `PipelineDefinition` owns the versioned executable graph;
- `PipelinePurposeSpec` owns workflow meaning, run inputs, guarantees, and
  authority semantics;
- `StrategySpec.config_schema` owns legal stage configuration;
- the server-owned strategy registry owns executable capability;
- `PipelineConfigOverrideSet` owns bounded per-definition configuration
  overrides.

The current `CorpusProcessingConfig` remains a transitional run envelope for
source ingestion, metadata/schema selection, provider credentials, review policy,
and publication settings. Execution-affecting settings that correspond to pipeline
stages must progressively move into canonical pipeline definitions/overrides rather
than being duplicated in CLI-only Pydantic fields.

Native releases are frozen capability catalogs. A binary must validate an imported
pipeline definition against the strategy IDs/versions compiled into that binary
before expensive source processing. A newer Pipeline Studio may therefore export a
definition that requires a newer binary; this is an explicit compatibility error,
not a partial or best-effort run.

CI must eventually fail when Pipeline Studio, the API, and the CLI drift. Required
gates include catalog/schema coverage, export-import hash round trips, server/headless
execution parity, and compiled-binary capability reporting.

## Supported targets

The first release target matrix is:

| Target              | Artifact key     | Executable     |
| ------------------- | ---------------- | -------------- |
| Ubuntu x86_64       | `linux-x86_64`   | `derridai`     |
| Windows x86_64      | `windows-x86_64` | `derridai.exe` |
| macOS Apple Silicon | `macos-arm64`    | `derridai`     |
| macOS Intel         | `macos-x86_64`   | `derridai`     |

The build is target-native. We do not treat Linux-to-Windows or Linux-to-macOS
cross-compilation as a release path.

Windows CI may use GitHub-hosted Windows Server runners for compiler/build smoke
coverage. Release acceptance still includes a Windows 11 execution check before the
binary is advertised as Windows 11 supported.

## Standalone first, onefile second

Nuitka standalone mode is the first packaging milestone because it exposes missing
DLLs, dylibs, shared objects, package data, and plugin configuration directly.

The sequence is:

1. compile a standalone distribution;
2. run `derridai --version`;
3. run `derridai config validate`;
4. run deterministic source-ingestion/corpus fixtures;
5. inspect packaged dependency closure and size;
6. only then build onefile;
7. run the same acceptance suite against onefile;
8. make onefile the preferred downloadable artifact only if it is reliable.

A single-file binary is desirable, not a prerequisite for the architecture. The
hard product contract is "download an OS-native DerridAI command and run it without
installing Python."

## Distribution policy

### Preferred channel: release assets

The default release channel is GitHub release assets because generated binaries are
build products rather than source. A release publishes:

```text
derridai-linux-x86_64
derridai-windows-x86_64.exe
derridai-macos-arm64
derridai-macos-x86_64
derridai-linux-x86_64.sha256
derridai-windows-x86_64.exe.sha256
derridai-macos-arm64.sha256
derridai-macos-x86_64.sha256
binary-manifest.json
```

The release tag carries the version while the asset filename stays stable. This makes `releases/latest/download/<asset>` usable directly by curl/wget without forcing binary churn into Git history.

Example final installation shape:

```bash
curl -fsSL https://raw.githubusercontent.com/ajschlosser/DerridAI/master/scripts/install-derridai.sh | sh
```

The installer resolves the current release, selects the local OS/architecture,
downloads the matching artifact and checksum, verifies it, installs it into a
writable PATH directory, and prints the installed version.

A direct no-installer flow is also supported:

```bash
curl -fL -o derridai <release-asset-url>
chmod +x derridai
./derridai --version
```

`wget` is supported equivalently.

Windows receives a PowerShell installer with the same checksum-verification rules.

### Optional channel: binaries committed in the repository

If the final onefile artifacts are genuinely small, committing them under `bin/`
is acceptable, but it is a measured decision rather than an assumption.

Initial decision gate:

- each compressed target artifact should be no larger than 10 MiB;
- the total tracked binary budget across all targets should be no larger than 50 MiB;
- the artifact must not contain bundled model weights or mutable runtime data;
- builds must be reproducible enough that CI can verify a committed binary against
  its source revision;
- normal source-only clones must not become materially slower to fetch/update;
- every committed binary must have a checked-in SHA-256 manifest and source commit.

If the full pipeline exceeds that budget, binaries stay in releases. The curl/wget
installation experience is unchanged.

The 10/50 MiB thresholds are repository policy, not claims about Nuitka. They can be
revised after real measurements, but no binary is committed before measurements
exist.

## Binary contents and capability tiers

The binary must keep its import/dependency closure narrow. The API server's entire
runtime should not be pulled into the executable merely because it exists in the
same repository.

### Tier 0: always present

Required for a basic PDF/text corpus run:

- CLI/config parser;
- source safety checks;
- PDF/text extraction implementation and required native libraries;
- corpus repository/workspace;
- segmentation/topology code;
- metadata schema/FieldAssertion logic;
- enrichment client code;
- publication/ledger/cELF validation;
- zstd output;
- deterministic validators;
- YAML parser.

### Tier 1: managed optional helpers

Capabilities that may rely on companion executables:

- OCR via Tesseract;
- audio probing/transcoding via FFmpeg;
- other format-specific helpers where a library cannot be embedded safely.

The binary must discover these explicitly and `derridai doctor` must say whether
they are available.

### Tier 2: large data/model resources

Large language/NLP model packs remain resources rather than compiled program code:

- spaCy model packages;
- BookNLP/model weights;
- future optional local inference model files.

The binary must not silently download models during a corpus build. Installation or
configuration is a separate administrative action.

### Tier 3: external services

LLM providers remain external unless an explicit future local-model execution
profile is introduced:

- Ollama;
- OpenAI-compatible endpoints;
- other configured providers.

Provider credentials are runtime secrets and must never be compiled into an
artifact, retained in the public YAML snapshot, or printed in diagnostics.

## Binary-specific module boundaries

The desired code layout is:

```text
api/app/
  corpus_cli.py                 argument parsing and process exit contract
  corpus_cli_config.py          versioned YAML contract
  headless_corpus_runner.py     synchronous application service
  corpus_output_profiles.py     research vs cELF projection
  corpus_capabilities.py        runtime capability detection
  corpus_binary_manifest.py     build/runtime identity helpers

api/
  derridai_cli.py               Nuitka compilation entry point

scripts/
  build_cli_binary.py           target-native build driver
  install-derridai.sh           Linux/macOS installer
  install-derridai.ps1          Windows installer
```

No module in this layer may reproduce corpus logic that already has an authoritative
implementation elsewhere.

## Headless runner contract

`HeadlessCorpusRunner` owns one end-to-end invocation.

Input:

- source path;
- validated `CorpusRunConfig` (v1 compatibility or v2 run envelope);
- output path;
- optional workspace path;
- optional progress callback.

Responsibilities:

1. validate source/config/runtime capabilities before expensive work;
2. create or select an isolated corpus workspace;
3. register the source through the shared source-ingestion implementation;
4. resolve the metadata schema and provider execution settings;
5. execute the shared corpus build synchronously;
6. settle automatic review policy without granting human authority;
7. enforce deterministic validation/publication blockers;
8. project the requested output profile;
9. atomically publish the final artifact;
10. emit a machine-readable run result.

It does **not**:

- call DerridAI's own HTTP routes;
- poll the FastAPI server;
- launch a browser;
- reinterpret unreviewed suggestions as human review;
- bypass source-conservation or publication validation.

## CLI command contract

Planned stable interface:

```text
derridai --version

derridai config validate --config FILE [--json]

derridai corpus build
  --source FILE
  --config FILE
  [--output FILE]
  [--workspace DIR]
  [--celf]
  [--json]
  [--quiet]

derridai doctor [--json]
```

The shorthand:

```text
derridai --source FILE --config FILE
```

may be added only after the explicit subcommand path is stable.

### stdout/stderr

Normal progress and diagnostics go to stderr. Machine-readable final results go to
stdout when `--json` is used.

Example final result:

```json
{
  "status": "ok",
  "build_id": "build-...",
  "source": "heidegger.pdf",
  "records": 842,
  "output": "/research/heidegger.jsonl.zst",
  "sha256": "...",
  "publication_profile": "research",
  "celf_conformant": null
}
```

### Exit codes

| Code | Category                                     |
| ---: | -------------------------------------------- |
|    0 | success                                      |
|    2 | command/configuration error                  |
|    3 | unsupported/unsafe source                    |
|    4 | missing runtime capability                   |
|    5 | extraction/segmentation/pipeline failure     |
|    6 | provider/enrichment failure                  |
|    7 | validation/publication failure               |
|    8 | output I/O failure                           |
|  130 | user cancellation on POSIX-compatible shells |

The implementation may map platform-specific interruption mechanisms into the same
semantic cancellation result even where the shell does not expose 130 literally.

## Output profiles

### research

The research output is an allow-list projection, not "the normal Record with some
keys removed."

Each row keeps:

- stable `record_id`;
- text;
- minimum source locator required for traceability;
- materialized values from the selected metadata schema.

It omits:

- review workflow state;
- execution ledger state;
- prompt/model traces;
- UI/cache state;
- derived Document Intelligence annotations;
- assertion history when the selected research profile does not require it.

### celf

The cELF output uses the existing publication and conformance machinery. Model
assertions retain their true derivation/evaluation/authority state. Automatic
publication may select unreviewed values without rewriting them as human-confirmed.

The initial cELF binary artifact may remain the existing compact
`.jsonl.zst`. A richer multi-file package is a later portability enhancement and
is not required to make the command useful.

## Workspace and resumability

Default workspace:

- Linux/macOS: platform-appropriate user cache/data root, with a
  `derridai/runs/<run-id>` subdirectory;
- Windows: platform-appropriate local application data root.

A user may override it with `--workspace`.

The first complete milestone supports one-shot runs and retains enough state to
diagnose failure. Resume is a follow-up milestone:

```text
derridai corpus resume --workspace <run>
```

Temporary files are never written beside the requested output unless required for
atomic replacement on that filesystem.

## Runtime capability checks

`derridai doctor` reports:

- binary version and source commit;
- OS and architecture;
- writable workspace/output status;
- Tesseract availability/version;
- FFmpeg availability/version;
- configured NLP resources;
- provider reachability only when explicitly requested/configured;
- supported source kinds for the current installation.

A build runs preflight capability checks based on the requested source kind and
configuration. A PDF with embedded text should not fail merely because FFmpeg is
absent.

## Build manifest

Every compiled artifact has a manifest containing at least:

```json
{
  "schema_version": 1,
  "app_version": "0.82.0",
  "git_commit": "...",
  "target": "linux-x86_64",
  "packaging": "nuitka-standalone",
  "python": "3.12.x",
  "nuitka": "...",
  "created_at": "...",
  "artifact": "derridai-0.82.0-linux-x86_64",
  "sha256": "...",
  "size_bytes": 12345678
}
```

The manifest is machine-generated. Release automation aggregates target manifests
into `binary-manifest.json`.

## Build pipeline

Each target-native CI job:

1. checks out the exact source commit;
2. installs the pinned supported Python version;
3. installs CLI runtime/build dependencies;
4. runs focused Python CLI tests;
5. compiles Nuitka standalone;
6. smoke-tests the compiled executable;
7. runs deterministic binary integration fixtures;
8. reports artifact size and dependency closure;
9. computes SHA-256;
10. uploads the standalone artifact for inspection;
11. if standalone is green, builds onefile;
12. runs the same smoke/integration fixtures against onefile;
13. uploads the candidate onefile artifact and target manifest.

Release jobs additionally sign/notarize as appropriate, aggregate checksums, and
attach artifacts to the GitHub release.

## Size accounting

Binary size must be measured in CI rather than guessed.

Report:

- executable size;
- standalone directory total size;
- compressed release size;
- largest packaged files;
- top-level package contribution where practical;
- change from the last release artifact.

The build fails only on a deliberately configured hard ceiling. Early milestones
report size without enforcing a ceiling so the data can inform the distribution
decision.

The repo-commit gate is evaluated only against final onefile release artifacts.

## Installation

### Linux/macOS shell installer

`scripts/install-derridai.sh` will:

1. detect Linux vs Darwin;
2. detect x86_64 vs arm64/aarch64;
3. resolve an explicit version or latest release;
4. require `curl` or `wget`;
5. download the binary plus checksum metadata;
6. verify SHA-256 before installation;
7. choose `/usr/local/bin` when writable, otherwise `~/.local/bin`;
8. set executable permissions;
9. run `derridai --version`;
10. print PATH guidance when necessary.

It never executes the downloaded binary before checksum verification.

### Windows PowerShell installer

`scripts/install-derridai.ps1` will:

- resolve the x86_64 Windows artifact;
- verify SHA-256;
- install under the user's local application/bin directory unless an explicit
  destination is supplied;
- update user PATH only with explicit consent/flag;
- run `derridai.exe --version`.

### Pinned installs

Both installers support a version parameter. Scientific/research environments should
be able to pin a binary version rather than implicitly move with latest.

## Security and supply-chain requirements

Release artifacts are treated as executable software, not convenience attachments.

Required controls:

- SHA-256 for every artifact;
- source commit recorded in the manifest;
- build on GitHub-hosted or explicitly trusted runners;
- no credentials in build logs or manifests;
- dependency versions constrained by repository requirements;
- source content remains inert data;
- no build-time execution of corpus inputs;
- macOS signing/notarization before broad release;
- Windows Authenticode signing before broad release when signing infrastructure is
  available;
- release assets are immutable for a published version;
- installers refuse checksum mismatches.

Longer term, add provenance/attestation (for example GitHub artifact attestations or
equivalent) once the binary shape is stable.

## Reproducibility policy

Bit-for-bit reproducibility is desirable but not assumed in the first milestone
because native compilers, timestamps, signing, platform toolchains, and onefile
packing may introduce nondeterminism.

The initial reproducibility contract is semantic:

- same DerridAI version;
- same source bytes;
- same YAML;
- same provider/model and deterministic settings where supported;
- same metadata schema;
- equivalent canonical Record identities/text/source mapping;
- equivalent publication validation result.

The binary manifest records enough build identity to diagnose native packaging
differences separately from scholarly output differences.

## Cross-platform corpus acceptance

The same deterministic fixture suite runs on every target.

Minimum fixture set:

1. native-text PDF requiring no OCR;
2. plain UTF-8 text source;
3. malformed/unsupported input rejection;
4. source with page/source locators;
5. metadata-schema projection fixture;
6. publication with unreviewed automatic assertions;
7. cELF conformance fixture;
8. cancellation/partial-output safety fixture.

Tests must compare semantics, not unstable absolute paths or platform-specific
temporary directories.

No target is considered supported solely because `--version` runs.

## Test layers

### Python-domain tests

Fast tests cover:

- YAML schema validation;
- unknown-key rejection;
- config-to-engine mapping;
- secret resolution/redaction;
- output-profile projection;
- exit-code mapping;
- workspace selection;
- capability detection;
- installer/manifest helpers where practical.

### Headless integration tests

These call `HeadlessCorpusRunner` directly with temporary storage and existing
corpus fixtures. They must not require FastAPI or the frontend.

### Compiled-binary smoke tests

Every native artifact runs:

```text
derridai --version
derridai config validate --config <fixture>
derridai doctor --json
```

### Compiled-binary corpus tests

A small deterministic source is built through the actual executable and the
resulting publication is validated.

## Packaging traps to avoid

- importing `app.application` or `app.main` from the CLI, which would drag the
  web server and unrelated routes into the binary;
- importing all of `chromadb`/sentence-transformers for a corpus build that does
  not need vector indexing;
- bundling NLP model weights into the executable by accident;
- using onefile before standalone dependency closure is correct;
- using hidden Nuitka inclusion flags as a substitute for fixing unclear dynamic
  imports;
- resolving configuration relative to the current working directory rather than
  the YAML file;
- writing API keys into a retained run manifest;
- letting platform-specific packaging differences change canonical scholarly
  semantics;
- committing generated binaries to Git before size/reproducibility measurements.

## Milestones and progress

Status values are `DONE`, `IN PROGRESS`, `TODO`, and `BLOCKED`.

| Milestone                              | Status      | Deliverable                                                                                                                                                                                                                 |
| -------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B0. Architecture                       | DONE        | Python shared-engine + Nuitka native-binary direction; standalone-first policy; four target keys; release-vs-repo binary gate.                                                                                              |
| B1. Versioned CLI config               | IN PROGRESS | Strict v1/v2 validation, stable exit categories, secret-by-environment resolution, v1 migration, and pipeline-bound v2 envelopes are implemented; direct execution from embedded definitions remains.                       |
| B2. Binary build spine                 | IN PROGRESS | Target identity helpers, Nuitka entry point/build script, artifact naming, manifest/checksum generation, compiled-binary smoke harness, and four-target standalone CI are implemented; onefile/release publication remains. |
| B3. Installer spine                    | IN PROGRESS | curl/wget shell installer and Windows PowerShell installer with checksum verification and pinned/latest release resolution are implemented; they become end-to-end testable once release assets exist.                      |
| B4. Headless runner                    | IN PROGRESS | Synchronous source-to-canonical-build application service is implemented without an HTTP dependency; actual compiled-binary end-to-end corpus acceptance remains.                                                           |
| B5. Automatic settlement               | IN PROGRESS | The headless runner invokes the shared autonomous settlement policy and publishes unreviewed values without granting human authority; end-to-end regression coverage remains.                                               |
| B6. Research output                    | IN PROGRESS | Explicit allow-list research projection and atomic `.jsonl.zst` writing are implemented and unit-tested; compiled-binary fixture acceptance remains.                                                                        |
| B7. cELF output                        | IN PROGRESS | The CLI uses the canonical publication/conformance path and rejects requested cELF output that is non-conformant; compiled-binary fixture acceptance remains.                                                               |
| B8. Capability doctor                  | IN PROGRESS | `doctor` now reports platform, writable paths, helpers, NLP resources, source-kind readiness, pipeline compatibility, and frozen headless bindings; network provider probing remains opt-in/future work.                    |
| B9. Native standalone acceptance       | TODO        | Full deterministic compiled-artifact fixture suite on all four target keys.                                                                                                                                                 |
| B10. Onefile acceptance                | TODO        | Onefile artifacts pass the same suite; size report determines release/repo distribution.                                                                                                                                    |
| B11. Signing/release                   | TODO        | Checksums, manifests, signing/notarization, immutable release assets, installer release resolution.                                                                                                                         |
| B12. Repo-binary decision              | TODO        | Use measured onefile sizes to decide whether `bin/` artifacts are committed.                                                                                                                                                |
| B13. Documentation/release integration | TODO        | README/USER_GUIDE/ARCHITECTURE/CONTRIBUTING and release process updated after behavior is implemented.                                                                                                                      |
| B14. Shared pipeline contract          | IN PROGRESS | Compatibility identity, frozen v2 execution, v1 migration, portable Studio/API/CLI interchange, round-trip checks, and compiled capability gates are implemented; broader execution-parity coverage remains.                |

## Definition of done

The binary pipeline is complete when:

1. A user on each supported target can obtain DerridAI without installing Python.
2. A native-text PDF can be transformed into a post-Corpus-Builder
   `.jsonl.zst` without FastAPI, the browser, or Docker.
3. The same YAML contract controls extraction, topology, metadata enrichment,
   automatic settlement, and publication.
4. Research output contains only the intended research surface.
5. cELF output uses canonical publication/conformance code rather than a second
   serializer.
6. Automatic model decisions never claim human authority.
7. Source/text-conservation failures remain blockers.
8. Binary runs return stable exit categories and never expose credentials.
9. Every release artifact has a checksum and source/build manifest.
10. Linux, Windows, macOS arm64, and macOS x86_64 artifacts pass compiled-binary
    corpus fixtures.
11. Installation can be performed with a small curl/wget or PowerShell bootstrap.
12. The decision to commit binaries to the repository is based on measured final
    artifact size and reproducibility, not convenience alone.

## Immediate implementation sequence

The next work items are deliberately ordered to de-risk packaging before deep CLI
orchestration:

1. keep the current headless runner/research/cELF behavior green while `master`
   continues to evolve;
2. finish immutable per-build pipeline pinning so v2 embedded definitions drive
   every Corpus Builder pipeline resolution for the lifetime of the run;
3. add Pipeline Studio/API/CLI export-import round-trip tests that preserve the
   canonical pipeline hash;
4. add server/headless execution-parity fixtures for representative corpus
   pipeline definitions;
5. add compiled-binary capability checks so dynamically packaged strategy coverage
   cannot silently drift;
6. add actual compiled source-to-corpus fixtures on all target platforms;
7. expand `derridai doctor` from pipeline identity into source/helper/NLP/provider
   capability checks;
8. build onefile on all targets and measure final artifact size;
9. decide release-only versus repository-committed binaries, then finish
   signing/notarization and release integration.
