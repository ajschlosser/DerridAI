<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.
-->

# Current implementation progress and handoff

Checkpoint: 2026-10-07.

## Active handoff: native/headless corpus CLI and shared pipeline contract

The native CLI and shared Pipeline Studio/API/CLI contract work from
[BINARY_PIPELINE_PLAN.md](BINARY_PIPELINE_PLAN.md),
[PIPELINE_CONFIGURATION_CONTRACT.md](PIPELINE_CONFIGURATION_CONTRACT.md), and
[HEADLESS_CORPUS_CLI.md](HEADLESS_CORPUS_CLI.md) is now on `master`.

The major merged milestones are:

- PR #530 established the native/Nuitka packaging spine, strict v1 YAML contract,
  non-HTTP `HeadlessCorpusRunner`, research/cELF output paths, installers, and
  four-target standalone CI.
- PR #583 added the shared pipeline capability identity, strict portable pipeline
  documents, Pipeline Studio/API/CLI import/export, the v2 corpus-run envelope,
  deterministic v1 -> v2 migration, hash-preserving import behavior, and compiled
  capability checks.
- PR #586 fixed contract-version binding after #583. New v2 run envelopes persist
  `pipeline_contract_version`; portable documents are accepted across the
  runtime's declared readable contract range and newer-than-runtime contracts fail
  closed.

### Current CLI surface

The code on `master` currently provides:

```text
derridai --version
derridai config validate --config FILE [--json]
derridai config migrate --config FILE [--output FILE] [--json]
derridai pipeline capabilities [--json]
derridai pipeline export --pipeline-id ID --version N [--output FILE]
derridai pipeline validate --config FILE [--json]
derridai doctor [--json]
derridai corpus build --source FILE --config FILE [--output FILE] [--workspace DIR] [--celf] [--json] [--quiet]
```

The CLI remains a thin frontend over the shared Corpus Builder. It does not call
DerridAI's own HTTP API and does not own a second extraction, enrichment, review,
or publication implementation.

### Native binary validation

The most recent pipeline-contract merge with a complete native run is commit
`024be25d0ebebbaa9df2dd6aeae13312a3408ddc` (PR #586). GitHub Actions run
`37678019463` passed all four standalone jobs:

- Linux x86_64;
- Windows x86_64;
- macOS arm64;
- macOS x86_64.

That workflow compiles the target-native Nuitka standalone distribution, runs the
focused CLI test suite, checks `--version`, validates the compiled pipeline
capability catalog against the binary manifest, runs `doctor --json`, validates
a minimal configuration, and uploads the complete standalone directory.

The uploaded standalone artifacts are directory distributions. The executable is
inside `derridai_cli.dist/`:

```text
Linux/macOS: derridai_cli.dist/derridai
Windows:     derridai_cli.dist\derridai.exe
```

Do not copy only that executable out of its `.dist` directory; Nuitka standalone
dependencies live beside it.

At this checkpoint, the newest overall `master` commit is
`8783db171e6d4bf92480f5769ac77321ea37e951` from unrelated Research work.
Its latest general quality-gate run fails only backend Ruff `I001` import
ordering while backend tests, backend types, and the frontend aggregate pass.
Treat that as current `master` baseline drift rather than evidence that the
native CLI regression suite failed.

## What is still unfinished

The durable remaining work is the portion still marked `IN PROGRESS` or `TODO`
in the two plan documents. In particular:

1. **Compiled source-to-corpus acceptance (B9).** The current `master`
   `.github/workflows/binary-cli.yml` smoke-tests the executable surface but
   does not yet build a deterministic source all the way through
   `derridai corpus build` on all four compiled artifacts. Add a small,
   deterministic fixture/provider harness and compare the intended semantic
   outputs/provenance across targets.
2. **Onefile acceptance and size measurement (B10/B12).** Current `master`
   validates standalone mode only. Build onefile after standalone corpus
   acceptance is reliable, run the same suite, measure final artifact sizes, and
   use those measurements for the release-only vs repository-binary decision.
3. **Release engineering (B11/B13).** Finish immutable release assets, aggregate
   manifests/checksums, signing/notarization policy, installer release resolution,
   and user/developer documentation.
4. **Execution parity (pipeline contract C9/B14).** Expand deterministic
   server/headless fixtures so the same resolved definitions demonstrate matching
   pipeline hash, stage/strategy order, deterministic outputs, validation result,
   and source/provenance bindings.
5. **Corpus Builder convergence (C11).** Continue moving execution-affecting
   settings that still live in transitional corpus configuration into registered
   strategy configuration without changing scholarly behavior.
6. **Embedded-definition execution.** The v2 envelope already freezes and
   validates canonical pipeline definitions and strategy versions, but the
   headless path still uses compatibility preflight/drift checks for portions of
   Corpus Builder that resolve system assignments internally. Finish immutable
   per-run binding so the embedded definitions drive those resolutions for the
   run lifetime.
7. **Runtime diagnostics.** `derridai doctor` now reports platform, writable
   paths, helper availability, NLP resources, source-kind readiness, pipeline
   contract identity, and frozen headless bindings. Provider reachability remains
   deliberately unprobed by the default command; add explicit opt-in probing only
   if it is useful and can remain secret-safe.

## Recommended next sequence

Start from current `master`, not from the old
`task/binary-pipeline-continuation` branch. That branch contains superseded
experiments and is no longer the integration source of truth.

Before adding features:

1. make the current `master` quality gate green or confirm any failure is an
   unrelated baseline issue;
2. run the focused CLI tests from `.github/workflows/binary-cli.yml`;
3. manually exercise a downloaded standalone artifact on the development host;
4. implement compiled source-to-corpus acceptance on one target first;
5. generalize the same fixture to all four target jobs;
6. only then introduce onefile packaging and distribution-size decisions.

When changing a pipeline-visible setting, keep the authority chain intact:
`StrategySpec.config_schema` / purpose / canonical `PipelineDefinition` first,
shared executor second, generated/typed UI contract third, CLI compatibility and
migration last. Unknown executable settings must fail instead of being silently
dropped, and automatic/model decisions must never acquire human authority through
serialization or migration.

## Manual standalone binary trial

A known-good set of short-lived CI artifacts is attached to Native corpus CLI run
`37678019463` (PR #586 merge). Select the artifact matching the local platform,
download and extract the whole archive, then run the executable from
`derridai_cli.dist`.

Useful first commands are:

```text
derridai --version
derridai pipeline capabilities --json
derridai doctor --json
derridai config validate --config corpus-processing.yaml
```

A minimal validation-only configuration is:

```yaml
version: 1
```

For an actual `corpus build`, supply a real configured provider/model. A local
Ollama example is documented in [HEADLESS_CORPUS_CLI.md](HEADLESS_CORPUS_CLI.md).
Keep the first manual corpus small and retain `--workspace` so failures can be
inspected.

## Historical completed checkpoint: progressive loading UX

Checkpoint: 2026-10-06.

## Current state

The workspace-by-workspace progressive-loading audit is complete. The authoritative detailed record is [PROGRESSIVE_LOADING_UX_PLAN.md](PROGRESSIVE_LOADING_UX_PLAN.md); the corresponding navigation work is tracked in [CORPUS_BUILDER_NAVIGATION_PLAN.md](CORPUS_BUILDER_NAVIGATION_PLAN.md).

Every route surface is now classified. Independently useful server-data regions own their first-read, retained-refresh, changed-identity, and failure states. Changed resource identities do not silently inherit old rows, record text, evidence, schema drafts, source facts, or PDF page labels. Long-running mutations and jobs remain separate from read hydration.

The remaining aggregate dependencies are intentional: authentication/authorization may gate the authorized application shell; Pipeline Studio requires its definition catalog as structural vocabulary; Roles keeps roles/capabilities/account assignments atomic for membership-sensitive mutations. Semantic Map, Help, and initial Provider state are synchronous/local and therefore do not need artificial network loading states. Settings keeps asynchronous audio and pipeline reads local to their sections.

The final Corpus Builder/Source Explorer check binds PDF preview accessibility metadata, captions, and source-box overlays to the page that actually finished rendering rather than the page merely requested.

## Validation

Historical focused validation for Works, Record, Vector Stores, Search, Research, Response Library, Records, Annotations, Languages, Relationships, Users/Roles, Metadata Memory, Operations, Compare, System Data, Pipeline Studio, Sources, and Metadata Schemas is recorded in the detailed plan. Those checks include synthetic delayed reads, same-resource refresh failures, changed-identity races, authorization loss, request counts, retained DOM/drafts, narrow layouts, reduced motion, localization, Storybook/build/type checks, and WCAG scans where documented.

The completion branch adds a focused PDF evidence-viewer regression for requested-page versus rendered-page identity. Repository CI is the final merge gate for this branch. Synthetic readiness checks demonstrate behavior; they are not a production-latency benchmark or a claim of measured speedup.

Known accessibility exceptions explicitly recorded in historical checkpoints remain separate product debt; the progressive-loading work does not hide or disable those findings.

## Resume

No further workspace-loading boundary is queued. If CI finds a regression, fix the failing contract on the completion branch. Otherwise the audit is ready to merge. Future work should treat new loading boundaries as ordinary feature requirements rather than reopening this migration wholesale.
