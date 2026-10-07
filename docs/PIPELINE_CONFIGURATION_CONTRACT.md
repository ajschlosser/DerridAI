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

# Pipeline Configuration Contract

This document defines how DerridAI keeps Pipeline Studio, the web application,
the API, the headless CLI, and native binaries on one executable pipeline
contract.

The central rule is simple:

> Pipeline semantics are owned by the backend pipeline contracts and strategy
> registry. User interfaces and command-line tools are clients of those
> contracts, not independent implementations of them.

This is a compatibility and ownership contract, not only a UI design rule.

## Current foundation

DerridAI already has most of the primitives needed for this architecture:

- `PipelineDefinition` is the versioned declarative graph stored and executed by
  the backend.
- `PipelineStageDefinition` carries strategy identity, stage configuration,
  graph edges, fallbacks, and explicit input bindings.
- `StrategySpec` is code-owned and declares the strategy version, family,
  scholarly effect, capabilities, ports, complexity, and `config_schema`.
- `PipelinePurposeSpec` defines what a whole pipeline is for, its consuming
  feature, run inputs, output semantics, guarantees, and authority semantics.
- `StrategyRegistry` is a closed server-owned registry. Saved pipeline data
  cannot introduce executable code.
- Pipeline Studio already consumes a server-derived catalog of purposes,
  strategies, definitions, assignments, and workflow vocabulary.
- Storybook/Vitest catalog fixtures are already generated from the live pipeline
  contracts rather than being independently hand-authored.
- `PipelineConfigOverrideSet` already binds configuration overrides to an
  immutable pipeline ID/version and forbids topology/strategy changes.
- Pipeline execution records the resolved pipeline identity/hash in run traces.

The native CLI must converge on these existing contracts rather than establishing
another pipeline model.

## Authority and ownership

The ownership boundary is:

```text
Backend Python domain
  PipelineDefinition
  PipelinePurposeSpec
  StrategySpec/config_schema
  PipelineConfigOverrideSet
  strategy registry
  validators/executors
          |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
    Pipeline Studio       Web feature UI      Native CLI
          |                  |                  |
          +------------------+------------------+
                             |
                             v
                    shared pipeline executor
```

The following are authoritative:

| Concern                                  | Authority                                     |
| ---------------------------------------- | --------------------------------------------- |
| Which pipeline purposes exist            | `PipelinePurposeSpec` / purpose registry      |
| Which strategies may execute             | `StrategyRegistry`                            |
| Strategy configuration fields and bounds | `StrategySpec.config_schema`                  |
| Stage graph and fallback semantics       | `PipelineDefinition`                          |
| Input/output port semantics              | strategy/purpose contracts                    |
| Override eligibility                     | purpose/assignment/override contracts         |
| Runtime validation                       | backend pipeline validators                   |
| Scholarly/provenance guarantees          | purpose + strategy scholarly-effect contracts |
| Corpus metadata schema                   | MetadataSchema / FieldAssertion domain        |
| Presentation, labels, layout             | UI/i18n layer                                 |
| CLI argument spelling                    | CLI adapter                                   |

No web component, TypeScript type, YAML parser, or binary packaging module may
become the semantic authority for a pipeline setting.

## Pipeline Studio is an editor, not a second pipeline engine

Pipeline Studio edits and analyzes `PipelineDefinition` data against the live
purpose and strategy catalogs.

A setting shown in Pipeline Studio must come from one of these server-owned
sources:

1. a `PipelineDefinition` field;
2. a `StrategySpec.config_schema` property;
3. a `PipelinePurposeSpec` constraint;
4. a typed assignment/override contract;
5. UI-only presentation metadata that is explicitly non-semantic.

Pipeline Studio may add display behavior such as grouping, descriptions,
tooltips, ordering, control selection, and visualization. It must not invent a
second default, range, enum, capability, or execution meaning.

If richer presentation metadata is needed, extend the strategy/purpose contract
with presentation-safe metadata rather than reproducing execution rules in Vue.

## The CLI configuration is an envelope around the same pipelines

The headless CLI needs settings that are not themselves pipeline graph settings:
source ingestion, workspace selection, metadata schema selection, credentials,
automatic settlement, and output profile.

Therefore the durable CLI file is an envelope, not a replacement for
`PipelineDefinition`.

Target shape:

```yaml
format: derridai-corpus-run
version: 2

source:
  ocr_mode: auto
  ocr_languages: eng+fra+deu

pipelines:
  assignments:
    corpus_document_manifest:
      definition:
        pipeline_id: corpus.document_manifest.current
        version: 1
        name: Corpus document manifest — current
        purpose: corpus_document_manifest
        status: active
        entry_stage_ids: [primary]
        stages: [...]
      pipeline_hash: "..."
      required_strategies:
        llm.document_manifest: 1
      overrides: null

    corpus_metadata_enrichment:
      definition:
        pipeline_id: corpus.metadata_enrichment.current
        version: 2
        name: Corpus metadata enrichment — validation-driven escalation
        purpose: corpus_metadata_enrichment
        status: active
        entry_stage_ids: [primary]
        stages: [...]
      pipeline_hash: "..."
      required_strategies:
        llm.structured_metadata: 1
      overrides:
        pipeline_id: corpus.metadata_enrichment.current
        pipeline_version: 2
        stages: { ... }

metadata:
  schema_id: default
  work: {}
  document: {}
  guidance: {}

provider:
  type: ollama
  model: qwen3:14b

review:
  mode: automatic

publication:
  profile: research
```

Corpus Builder already executes several independently versioned feature pipelines, so the portable
run envelope is a feature-to-definition bundle rather than one synthetic "corpus builder" pipeline.
The exact feature set may evolve as more Corpus Builder work moves onto the generic pipeline
executor.

Each portable binding carries the canonical definition, its canonical hash, and the strategy
implementation versions required to execute it. Optional run overrides remain bound to that exact
definition ID/version. The current native CLI embeds definitions so a file is self-describing; a
future server-attached import surface may additionally support immutable references, but it must
resolve and freeze them before execution begins.

## Transitional status of CorpusProcessingConfig

The current `CorpusProcessingConfig` and its `build_request()` adapter are a
bootstrap layer. They are useful now, but they must not become a permanent
parallel source of pipeline semantics.

During migration:

- source, metadata, provider-secret, review, publication, and workspace concerns
  may remain CLI-envelope fields;
- settings that correspond to a registered pipeline stage should move into
  `PipelineDefinition` stage configuration or a typed
  `PipelineConfigOverrideSet`;
- the CLI adapter may translate legacy v1 YAML into the shared contract;
- new Pipeline Studio stage settings should not require a new bespoke CLI
  mapping when the setting already exists in `StrategySpec.config_schema`.

The migration is complete when adding a normal configurable pipeline-stage
property requires changing the backend strategy contract and its implementation,
but not hand-editing a second CLI schema.

## Format version versus pipeline version

DerridAI must keep these identities separate:

1. **run-envelope format version** — the serialization shape of the CLI/import
   file;
2. **pipeline ID/version** — the immutable saved definition;
3. **strategy ID/version** — the implementation contract referenced by stages;
4. **DerridAI application version** — the release containing compatible
   implementations.

Do not overload one integer for all four.

A native binary must reject unsupported contract combinations explicitly. A
typical diagnostic should be actionable:

```text
Pipeline corpus-builder v14 requires strategy metadata.deep_extract v5.
This DerridAI binary provides metadata.deep_extract through v4.
Upgrade DerridAI or use a compatible pipeline definition.
```

Silent dropping, defaulting, or reinterpretation of unknown stage settings is
not allowed.

## Migrations

Run-envelope migrations and pipeline-definition migrations have different
responsibilities.

### Run-envelope migrations

A run-envelope migrator may:

- rename an envelope field;
- move a setting from the legacy CLI section into a shared pipeline override;
- convert a former shorthand into an explicit structure;
- preserve the original format version in diagnostics/provenance.

It may not change scholarly meaning without an explicit migration note.

### Pipeline migrations

Pipeline definitions are versioned historical objects. Existing saved versions
must remain immutable. Migration normally creates a new definition/version.

When a strategy configuration contract changes incompatibly, the strategy
version must change and validation must identify definitions requiring migration.

## Catalog/capability contract

The server should expose one machine-readable catalog sufficient for all clients
to understand the pipeline surface.

The existing Pipeline Studio catalog already provides most of this:

- purposes;
- workflow vocabulary;
- strategies;
- strategy `config_schema`;
- definitions;
- assignments.

The compatibility surface should additionally expose a small contract identity:

```json
{
  "pipeline_contract_version": 1,
  "minimum_readable_pipeline_version": 1,
  "application_version": "0.82.0",
  "strategies": {
    "metadata.deep_extract": {
      "version": 4
    }
  }
}
```

This identity is about compatibility, not presentation.

Native binaries should expose the same information through
`derridai doctor --json` and/or a dedicated
`derridai pipeline capabilities --json` command.

## UI controls from strategy schemas

`StrategySpec.config_schema` is the semantic configuration schema.

Pipeline Studio should render ordinary stage controls from it whenever practical:

- boolean -> toggle;
- enum -> select/autocomplete;
- bounded integer/number -> numeric control with bounds;
- string -> text/select control according to schema metadata;
- arrays -> multi-value controls;
- descriptions/defaults -> labels, help text, and initial values.

Specialized components are allowed when a field benefits from a richer editor,
but the component still consumes the server-owned schema and may not redefine
its legal values.

If JSON Schema alone is insufficient for good UX, add a non-semantic
`presentation` annotation to the server-owned strategy specification instead
of hard-coding the same knowledge in several clients.

## Export/import and round-trip behavior

Pipeline Studio must be able to export a definition suitable for the CLI.

Target workflows:

```text
Pipeline Studio
    -> Export pipeline/run configuration
    -> corpus-run.yaml
    -> derridai corpus build --source book.pdf --config corpus-run.yaml
```

and:

```text
derridai pipeline export ...
    -> pipeline definition
    -> Pipeline Studio import
```

Round-trip requirements:

- pipeline ID/version remain unchanged unless the user explicitly clones;
- stage IDs and strategy IDs remain unchanged;
- stage configuration values remain unchanged;
- graph topology and input bindings remain unchanged;
- unknown fields are rejected rather than discarded;
- secret values are never exported;
- UI-only state is not serialized into the executable definition;
- importing and exporting without edits preserves the canonical pipeline hash.

The CLI may add run-envelope settings around the pipeline; those settings are
not part of the pipeline hash.

## UI-specific and CLI-specific fields

Every configurable field associated with the corpus workflow must have an
explicit ownership classification:

- **shared** — semantic setting exposed through the backend contract;
- **ui_only** — presentation state with no execution effect;
- **cli_only** — transport/runtime concern such as output path or quiet mode;
- **internal** — implementation setting unavailable to users.

There is no implicit fifth category.

A field that affects execution cannot be marked `ui_only`.

Examples:

| Field                        | Class    |
| ---------------------------- | -------- |
| stage rerank limit           | shared   |
| metadata enrichment strategy | shared   |
| stage timeout/config option  | shared   |
| graph edge/fallback          | shared   |
| Pipeline Studio panel width  | ui_only  |
| selected editor tab          | ui_only  |
| CLI output path              | cli_only |
| CLI `--quiet`                | cli_only |
| internal checkpoint key      | internal |

## CI drift gates

CI must make contract drift difficult to introduce accidentally.

### 1. Backend contract snapshot

Generate a normalized machine-readable pipeline catalog from the live backend
contracts. The existing catalog-fixture exporter is the starting point.

The snapshot includes at minimum:

- purpose IDs and guarantees;
- strategy IDs and versions;
- strategy configuration schemas;
- typed ports;
- pipeline definitions;
- assignment identities.

### 2. Frontend contract check

Frontend tests must consume the generated catalog fixture or live API shape and
must not maintain a second hand-authored strategy vocabulary.

A CI check should fail if Pipeline Studio references:

- an unknown strategy;
- an unknown purpose;
- a config property not present in `config_schema`;
- a stale enum/bound/default that conflicts with the backend catalog.

### 3. CLI contract check

For every shared corpus-pipeline configuration property, CI should prove one of:

- the CLI directly serializes the canonical pipeline definition;
- the CLI legacy migrator deterministically maps it to the canonical property;
- the property is explicitly unavailable in this binary contract version and
  validation rejects it with a compatibility error.

A newly added shared strategy property must not require an untracked manual edit
to a parallel CLI schema.

### 4. Round-trip test

For representative built-in and saved definitions:

```text
backend PipelineDefinition
  -> exported JSON/YAML
  -> CLI/import parser
  -> PipelineDefinition
```

must preserve the canonical pipeline hash.

### 5. Execution parity test

For deterministic fixtures, execute the same resolved definition through the
server/application path and the headless path and compare:

- resolved pipeline hash;
- stage order and strategy IDs;
- deterministic outputs;
- validation/conformance result;
- source/provenance bindings.

Provider-dependent prose need not be byte-identical unless deterministic
settings and provider behavior guarantee it.

### 6. Binary capability test

Each compiled binary must report the strategy versions it contains. CI validates
the report against the source-tree catalog used to compile it.

This prevents a binary that builds successfully while silently omitting a
dynamically imported strategy.

## Change protocol

When adding or changing a Pipeline Studio/corpus pipeline setting:

1. change the authoritative Python strategy/purpose/pipeline contract;
2. change the shared executor/handler implementation;
3. add or update backend contract tests;
4. regenerate/check the pipeline catalog fixture;
5. update Pipeline Studio presentation only as needed;
6. verify CLI import/export or legacy migration behavior;
7. run round-trip and execution-parity tests;
8. update contract version/strategy version when compatibility requires it;
9. rebuild native-binary capability tests.

A pull request is incomplete if an execution-affecting setting exists only in a
web component or only in CLI YAML.

## Compatibility with native binaries

A released binary is a frozen implementation of a known contract catalog.

The binary cannot automatically gain a newly implemented strategy merely because
a newer Pipeline Studio can describe it. Therefore:

- exported definitions include immutable strategy identities;
- the binary validates all referenced strategies before source processing;
- unsupported strategy versions fail before expensive work;
- installers make upgrading the binary straightforward;
- `derridai doctor` reports the binary's application version, contract version,
  and strategy catalog;
- release notes call out pipeline-contract compatibility changes.

A newer UI may export a pipeline that an older binary cannot execute. That is an
expected compatibility condition and must produce a precise error, not a partial
run.

## Corpus Builder migration direction

Corpus Builder currently still has orchestration/settings that predate the
generic pipeline system. Migration should be incremental.

Do not pause binary work until every Corpus Builder stage is represented as a
generic pipeline node. Instead:

1. keep the existing shared Corpus Builder implementation authoritative;
2. identify settings already represented by registered strategies and route
   those through `PipelineDefinition`/overrides;
3. move additional execution-affecting choices into registered strategies as
   the generic pipeline executor gains equivalent semantics;
4. retain extraction/workspace/publication concerns in the run envelope;
5. remove corresponding fields from the bespoke CLI mapping only after parity
   tests exist.

This preserves behavior while reducing the long-term synchronization burden.

## Required invariants

The following invariants are release-blocking:

1. The UI, CLI, and server cannot assign different execution meanings to the
   same pipeline field.
2. Unknown execution fields are rejected, never silently ignored.
3. Pipeline Studio cannot execute user-authored code.
4. A CLI/binary cannot bypass pipeline scholarly/provenance guarantees.
5. Model output never gains human authority through serialization or migration.
6. Pipeline export/import preserves immutable identity and canonical hash.
7. Secrets never enter exported pipeline definitions.
8. A binary reports the exact pipeline capabilities compiled into it.
9. New shared pipeline settings are covered by drift/parity tests.
10. Saved historical pipeline versions remain auditable after newer UI/CLI
    versions are released.

## Current CLI migration boundary

Version 2 embeds the exact definitions, canonical hashes, strategy versions, and typed overrides
used by the unattended Corpus Builder feature set. The headless runner persists those bindings in
the build request, and migrated pipeline adapters resolve the frozen run binding before consulting
mutable system assignments. A v2 run therefore keeps its pipeline identity even if an administrator
changes the system assignment after the run starts. Legacy v1 input is still accepted by
deterministically freezing the current/default bundle before execution.

## Implementation sequence

Status values are `DONE`, `IN PROGRESS`, `TODO`, and `BLOCKED`.

| Step                              | Status      | Work                                                                                                                                                            |
| --------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C0. Establish authority boundary  | DONE        | Existing `PipelineDefinition`, purpose registry, strategy registry, and generated Pipeline Studio catalog are declared canonical.                               |
| C1. Document shared contract      | DONE        | This document defines ownership, versioning, migration, export/import, and drift rules.                                                                         |
| C2. Contract identity             | DONE        | The API catalog and native CLI expose one application/contract/strategy-version compatibility identity.                                                         |
| C3. CLI v2 envelope               | DONE        | The v2 envelope embeds exact definitions, hashes, strategy versions, and typed overrides; headless execution resolves the frozen run bindings.                  |
| C4. Legacy CLI migration          | DONE        | `derridai config migrate` deterministically wraps v1 settings with the currently resolved Corpus Builder pipeline bundle.                                       |
| C5. Pipeline Studio export/import | DONE        | Pipeline Studio/API export and strict idempotent import preserve canonical definitions; headless corpus definitions can also export a secret-free run envelope. |
| C6. Generated frontend contracts  | IN PROGRESS | Continue replacing hand-maintained workflow semantics with server-derived catalog/types/fixtures.                                                               |
| C7. Drift CI                      | IN PROGRESS | Backend/CLI tests cover compatibility identity, migration, hashes, and required strategies; broader frontend/property drift gates remain.                       |
| C8. Round-trip CI                 | DONE        | Backend and frontend/CLI coverage preserve canonical hashes through portable export/import and reject tampering or unknown executable fields.                   |
| C9. Execution parity CI           | TODO        | Run the same resolved definitions through server and headless paths and compare semantics.                                                                      |
| C10. Binary capability CI         | DONE        | Native build manifests record the source-tree contract; each compiled binary must report the identical contract in smoke CI.                                    |
| C11. Corpus Builder convergence   | IN PROGRESS | Incrementally move execution-affecting Corpus Builder settings onto registered pipeline strategies without behavior regressions.                                |