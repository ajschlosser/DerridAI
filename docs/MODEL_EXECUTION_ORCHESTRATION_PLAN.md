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

# Internal Model Execution Orchestration Plan

Status: proposed implementation plan  
Base: master@206a6c9e32b431222d44962272b4242714aa21ee (2026-10-04)  
Primary scope: provider delegation, metadata enrichment, validation-driven escalation, fan-out,
adjudication, observability, and Pipeline Studio integration.  
Related architecture: [ARCHITECTURE.md](ARCHITECTURE.md),
[CONCURRENCY_ARCHITECTURE_PLAN.md](CONCURRENCY_ARCHITECTURE_PLAN.md),
[PIPELINE_MIGRATION_HANDOFF.md](PIPELINE_MIGRATION_HANDOFF.md), and
[requirements/LLM_PROVIDERS.md](requirements/LLM_PROVIDERS.md).

## Decision summary

DerridAI should implement model delegation internally rather than depend on an external routing
framework.

The new abstraction is a versioned **model execution policy** owned by DerridAI. Provider profiles
continue to answer "how do I call this endpoint/model and how much capacity does it have?" Execution
policies answer "which configured targets should run for this task, in what order or parallelism,
under which escalation conditions, and how should their validated results be combined?"

The design must reuse the execution primitives DerridAI already has:

- named Ollama/OpenAI-compatible provider profiles;
- process-wide provider capacity coordination;
- structured-output repair/retry/schema validation;
- Pipeline Studio's server-owned DAG execution;
- deterministic scholarly validators;
- FieldAssertion/evidence/provenance authority rules;
- durable job/build telemetry and cancellation.

It must not create a second provider stack, a second concurrency authority, or an alternate
scholarly authority path.

The intended deployment includes cases such as:

```text
local embedding model
        │
        └── pinned, high-throughput vector work

local generation model
        │
        └── inexpensive first-pass metadata proposals
                    │
                    ▼
          deterministic validators
                    │
             clean / ambiguous
               │         │
               │         ▼
               │    cloud fan-out
               │    through one or more
               │    provider profiles
               │         │
               │         ▼
               │    candidate comparison
               │         │
               │    agree / conflict
               │       │      │
               │       │      ▼
               │       │  adjudicator
               │       │      │
               └───────┴──────┘
                       │
                       ▼
                 final validators
                       │
                       ▼
               reviewable proposal
```

An OpenAI-compatible gateway such as FreeLLMAPI is simply another provider profile. DerridAI owns
fan-out, candidate comparison, adjudication, provenance, validation, cancellation, and final
selection. No feature-specific FreeLLMAPI branch is required.

## Why this belongs in DerridAI

Generic model routers typically optimize cost, latency, or a prediction of prompt difficulty.
DerridAI has stronger task-specific signals available after the first model attempt:

- structured-output validity;
- required-field completeness;
- exact evidence availability;
- citation/source-span validity;
- attribution and position-holder ambiguity;
- speaker/quoted-speaker conflicts;
- proposition-status conflicts;
- negation/modality concerns;
- disagreement with deterministic document metadata;
- candidate disagreement;
- reviewer-history and calibrated confidence signals.

Those signals are materially more useful than a generic "easy versus hard prompt" classifier.
DerridAI can therefore route based on scholarly risk and validator output rather than only model
quality tiers.

This also preserves the architectural division of labor already established in the project:
deterministic code owns authority, provenance, citation resolution, schema checks, and evidence
sufficiency; models generate proposals, interpretations, and bounded adjudication.

## Current baseline

The current architecture already provides most of the substrate required by this plan.

### Provider profiles

DerridAI uses named provider profiles for Ollama and OpenAI-compatible endpoints. Profiles carry
endpoint/model configuration, generation settings, secret-safe identity, and
max_concurrent_requests. Provider type is intentionally abstracted from scholarly workflows.

This remains the only provider configuration concept.

### Shared capacity

api/app/concurrency.py is the process-wide capacity authority. Provider generation callers derive a
stable provider capacity key and acquire provider_generation capacity through the shared
coordinator. Local Ollama may additionally consume an ollama_runtime constraint.

The orchestrator must use these gates. It must not create a private semaphore that allows one
feature to overrun the same provider while Corpus Builder, RAG, or another job is active.

### Pipeline execution

api/app/pipelines/graph_execution.py provides bounded opt-in concurrent waves and deterministic
fan-in for server-owned handlers. Pipeline definitions select registered strategies and settings;
they do not inject executable code.

This should be the graph execution foundation for fan-out and fan-in.

### Structured model calls

api/app/pipelines/structured_llm_stage.py and feature adapters such as
api/app/pipelines/corpus_metadata_enrichment.py currently model a structured task as one primary
provider role and, optionally, one review-provider fallback.

Structured completion, bounded repair/retry, schema validation, truncation handling, transport
classification, and provider failure semantics already exist outside the graph itself.

The implementation should preserve those paths rather than reproduce them in a new service.

### Corpus Builder UI

Corpus Builder currently exposes a primary provider and an optional escalation provider. This maps
directly to the current two-role runtime. The new UI should evolve this concept into execution-policy
selection while keeping simple local-only workflows easy to configure.

## Goals

1. Allow one task to execute against one or more configured model targets without changing provider
   adapters or scholarly authority semantics.
2. Keep cheap/high-throughput work local when desired while allowing selective cloud escalation.
3. Support fixed fan-out for benchmarking and ensemble use cases.
4. Support validator-driven adaptive escalation for production metadata enrichment.
5. Preserve independent candidate provenance through comparison and adjudication.
6. Reuse the existing process-wide capacity coordinator for every provider call.
7. Make execution reproducible through versioned policy identity and resolved target snapshots.
8. Preserve historical Pipeline Studio behavior and existing pipeline versions.
9. Keep embedding model identity pinned and vector-space-safe.
10. Keep model failure distinct from "no supported scholarly value."
11. Ensure deterministic final state for fixed provider outputs regardless of completion order.
12. Make the execution path inspectable in Pipeline Studio and operation telemetry.

## Non-goals

This plan does not:

- introduce RouteLLM or another external model router;
- add a second provider configuration system;
- make provider agreement an evidence authority;
- allow majority vote to bypass source binding or FieldAssertion validation;
- route individual embedding calls dynamically across incompatible embedding models;
- create an external Redis/Celery-style durable queue as part of the first implementation;
- replace Pipeline Studio's GraphExecutor;
- make raw model candidates canonical scholarly state;
- allow pipeline JSON to carry executable Python or arbitrary endpoint credentials;
- retry indefinitely across providers;
- silently switch models when reproducibility requires a pinned identity.

An external worker/queue architecture may be evaluated later if process-local execution becomes a
fault-tolerance or throughput limitation. The contracts in this plan should make such a migration
possible without changing scholarly semantics.

## Non-negotiable invariants

1. Human-confirmed state outranks every automatic candidate.
2. A stale model result may never overwrite a Record whose relevant revision/fingerprint changed
   while the model was running.
3. Model agreement does not establish evidence.
4. Every candidate that can influence a final proposal passes the appropriate schema and
   source/evidence validation.
5. Provider outage, timeout, malformed output, and "no supported value" remain distinct states.
6. Secrets never enter pipeline definitions, traces, model-execution snapshots, Record metadata, or
   shareable URLs.
7. Provider concurrency is process-wide and keyed by the actual configured provider profile or
   normalized fallback identity.
8. Policy-level max_parallel may lower effective concurrency but may never raise a provider's shared
   capacity.
9. Fixed provider outputs yield equivalent final scholarly state regardless of execution completion
   order.
10. Fan-out and adjudication are bounded. A policy cannot recursively spawn an unbounded sequence of
    models.
11. Historical pipeline versions retain their behavior for reproducibility.
12. Embedding collections never mix incompatible vector identities.

## Target architecture

### Separation of provider and execution policy

Keep ProviderProfile unchanged in responsibility.

A ProviderProfile owns:

- profile ID and display name;
- provider type;
- endpoint/base URL;
- secret reference/API key handling;
- default model or model discovery mode;
- generation defaults;
- context-window configuration;
- max concurrent requests;
- readiness/warmup state.

A ModelExecutionPolicy owns:

- stable policy ID;
- version;
- strategy;
- primary target;
- optional fan-out targets;
- optional adjudicator target;
- policy-local concurrency throttle;
- escalation predicates;
- bounded retry/fan-out/adjudication rules.

A ModelTarget references a provider profile plus an optional model override. An override changes the
model requested from that provider; it does not create a new provider-capacity pool.

### Initial execution strategies

Implement four strategies.

#### single

One configured target runs once through existing structured completion behavior.

Use cases:

- local-only enrichment;
- Research generation;
- deterministic benchmark baselines;
- provider-specific troubleshooting.

#### fallback

Run one target. If a configured failure class occurs, try the next target.

This is the generalized form of today's primary -> review provider behavior.

Fallback is for operational or structured-output failure, not for hiding a valid but epistemically
weak result. Validator-driven escalation belongs in adaptive.

#### fan_out

Execute several targets independently, subject to:

- policy max_parallel;
- each provider profile's process-wide capacity;
- cancellation;
- task deadline/budget;
- deterministic target ordering.

Collect independently validated candidates and pass them to deterministic comparison.

#### adaptive

Run a primary target first. Pass its candidate through DerridAI validators. Only when configured
escalation predicates are triggered does the policy execute additional targets.

Typical flow:

```text
primary candidate
      │
      ▼
validators
      │
      ├── valid + ordinary risk ───────────────► final proposal
      │
      └── escalation signal
                 │
                 ▼
             fan-out
                 │
                 ▼
       deterministic comparison
                 │
           ┌─────┴─────┐
           ▼           ▼
        resolved    ambiguous
           │           │
           │           ▼
           │       adjudicator
           │           │
           └─────┬─────┘
                 ▼
          final validators
                 │
                 ▼
       proposal or human review
```

Adaptive should become the recommended production strategy for metadata only after fixed fan-out,
comparison, and adjudication are proven.

## Core contracts

Create a focused backend package, tentatively:

```text
api/app/model_execution/
    __init__.py
    contracts.py
    policies.py
    resolver.py
    service.py
    candidates.py
    comparison.py
    adjudication.py
    telemetry.py
```

Names may change during implementation, but responsibilities should remain separated.

### ModelTarget

Conceptual contract:

```python
@dataclass(frozen=True)
class ModelTarget:
    provider_profile_id: str
    model_override: str | None = None
    label: str | None = None
```

Target resolution produces the same secret-safe provider/model identity and runtime request
configuration already used by existing provider-profile code.

### ModelExecutionPolicy

Conceptual contract:

```python
class ModelExecutionPolicy(BaseModel):
    policy_id: str
    version: int
    strategy: Literal["single", "fallback", "fan_out", "adaptive"]

    primary: ModelTarget
    fallbacks: list[ModelTarget] = []
    fanout: list[ModelTarget] = []
    adjudicator: ModelTarget | None = None

    max_parallel: int = 1
    max_total_model_calls: int
    escalation_predicates: list[str] = []
```

Policy validation must reject contradictory or unbounded configurations. For example:

- fan_out requires at least two total candidate targets;
- an adjudicator cannot recursively invoke the same policy;
- max_total_model_calls must be sufficient for the configured path and have a server-owned upper
  bound;
- a policy target must resolve to an allowed provider profile;
- researcher-visible policy selection must honor role permissions;
- duplicate target/profile/model combinations are either rejected or deliberately deduplicated.

### ExecutionRequest

ExecutionRequest is the task-scoped runtime input. It should carry identity and requirements, not
provider secrets.

Conceptually:

```python
@dataclass(frozen=True)
class ExecutionRequest:
    task_type: str
    response_contract: str
    policy_id: str
    policy_version: int | None

    record_id: str | None
    source_revision: str | None
    metadata_family: str | None
    pipeline_trace_id: str | None

    prompt: str
    structured_response_model: type[BaseModel]
    deadline: datetime | None
    cancelled: Callable[[], bool]
```

The actual implementation should avoid serializing raw prompt/source text into operational traces.
This contract is runtime-only.

### ModelCandidate

A candidate is an execution artifact, not a canonical FieldAssertion.

It needs enough identity for deterministic comparison and audit:

```python
@dataclass(frozen=True)
class ModelCandidate:
    candidate_id: str
    target_ordinal: int

    provider_profile_id: str
    provider: str
    model: str

    parsed_output: dict[str, Any]
    validation: CandidateValidation
    evidence_bindings: tuple[EvidenceBinding, ...]

    elapsed_ms: int
    attempt_count: int
    disposition: str
```

The candidate may contain source-derived content in task-local memory. Durable telemetry should store
only the minimum needed for audit and reproducibility unless the existing canonical proposal store
already requires the value/evidence payload.

### ExecutionResult

ExecutionResult separates candidates from the selected result:

```python
@dataclass(frozen=True)
class ExecutionResult:
    policy_snapshot: ResolvedExecutionPolicy
    candidates: tuple[ModelCandidate, ...]
    comparison: CandidateComparison
    adjudication: ModelCandidate | None
    selected: ModelCandidate | None
    disposition: str
```

Possible top-level dispositions should be coded and enumerable, such as:

- selected;
- unresolved_disagreement;
- unsupported_evidence;
- provider_failure;
- cancelled;
- stale_source;
- budget_exhausted.

Do not store raw exception messages when they may contain model/source text.

## Policy persistence and versioning

Execution policies need stable identity and immutable/versioned semantics similar to pipeline
definitions.

Recommended rules:

- policy_id is stable across versions;
- editing a policy creates a new version rather than mutating historical semantics;
- active/default assignment is a separate pointer;
- a run resolves one concrete policy version before provider calls begin;
- the resolved policy hash is recorded in execution telemetry;
- provider secrets are resolved at runtime and excluded from the snapshot;
- target model overrides are recorded because they are part of reproducibility.

Policies should live in durable application state, not in Chroma and not inside corpus Record JSON.

A future export/import format may be useful, but initial implementation can use existing system
persistence patterns.

## Provider resolution and capacity

ModelExecutionService must resolve every target through existing provider-profile resolution.

For each call:

1. resolve provider profile and optional model override;
2. derive the existing provider_capacity_key;
3. derive the effective provider_limit;
4. apply a policy/operation throttle if lower;
5. acquire provider_generation capacity from the shared coordinator;
6. if applicable, acquire the shared ollama_runtime constraint;
7. execute the existing completion path;
8. release all permits on success, failure, cancellation, and timeout.

If multiple targets use one FreeLLMAPI/OpenAI-compatible profile, they share that profile's capacity.

Example:

```text
FreeLLM profile max_concurrent_requests = 16

fan-out target model-a ─┐
fan-out target model-b ─┼── all consume profile:freellm capacity
fan-out target model-c ─┘

three concurrent calls => active 3 / 16
```

Defining three model overrides must never trick the scheduler into thinking there are three
independent endpoint quotas.

Separate profiles may execute independently if their provider keys differ.

## Structured output reuse

The orchestration layer must not implement its own ad hoc JSON extraction.

Every structured target call should use the same bounded completion contract already required by
PRD-LLM-014:

- local repair before another model call where safe;
- syntax/schema classification;
- targeted structured retries;
- truncation handling;
- bounded transport retries;
- explicit timeout classification;
- validated output before domain application.

This gives every candidate the same minimum syntactic and schema quality regardless of provider.

The execution policy controls which targets run. The existing structured-completion subsystem
controls whether an individual target produced a valid structured answer.

## Candidate validation and scholarly authority

A schema-valid answer is still only a proposal.

For metadata enrichment, each candidate must pass the same domain validation that would apply to a
single-provider proposal:

- field schema/value validation;
- null/absence semantics;
- evidence requirement checks;
- evidence binding validation;
- source/revision identity;
- protected deterministic values;
- reviewer-owned values;
- attribution relation constraints;
- confidence/autofill policy;
- contradiction handling;
- any cELF/metadata-specific invariants.

The comparison layer consumes validated candidate interpretations. It must not compare raw prose
answers and then bypass the domain validators.

### Field-level rather than whole-response comparison

Metadata ensemble comparison should be field-aware.

For each requested field, classify candidate outcomes such as:

- unanimous;
- compatible;
- conflicting;
- unsupported;
- invalid;
- missing.

The exact taxonomy should be represented by enums and covered by tests.

Agreement must use the field's normalization/equivalence contract where available. String equality
alone is insufficient for entities, lists, structured relations, normalized citations, or values
with aliases.

### Agreement is not evidence

Three models proposing the same value is useful confidence information but never independent source
support.

For example:

```text
A: position_holder = Heidegger
B: position_holder = Heidegger
C: position_holder = Heidegger
```

is still inadmissible if the source evidence does not support Heidegger as the position holder.

Candidate comparison therefore asks two separate questions:

1. do models agree on the proposal?
2. does valid source evidence support the proposal?

Only the second can satisfy evidence authority.

## Deterministic comparison

Implement deterministic comparison before any adjudicator call.

The comparison service should:

1. order candidates by configured target ordinal, never completion time;
2. normalize each field through the schema/domain equivalence rules;
3. discard candidates that cannot satisfy minimum validation for that field;
4. group compatible values;
5. compare their evidence bindings;
6. produce a coded comparison disposition;
7. either select an unambiguous validated result or request adjudication.

Do not implement "first successful result wins" for fan-out.

Do not implement a simple majority vote as the final authority.

A majority may be one signal in comparison, but a minority candidate with stronger valid evidence may
be preferable. The explicit comparison contract should make this testable.

Tie-breaking must be stable and documented.

## Adjudication

Adjudication is a separate, explicit model task used only when deterministic comparison cannot
resolve material disagreement.

The adjudicator receives:

- the bounded source context required for the disputed fields;
- schema/field definitions;
- the independently validated candidate values;
- candidate evidence references;
- a coded explanation of the disagreement.

It should not receive unbounded raw provider transcripts.

Its structured output must support, per disputed field:

- choose candidate A/B/C;
- reject all candidates;
- return another source-supported value when permitted by the field contract;
- return no supported value;
- bind evidence for the decision.

The adjudicator output passes through the same domain validators as every other candidate.

If adjudication remains unsupported or contradictory, the final state is unresolved/pending human
review. It does not recursively invoke more models.

## Adaptive escalation predicates

Adaptive routing should be driven by server-owned, coded signals.

Initial metadata escalation predicates should be conservative and auditable. Candidate examples:

- structured_output_failure;
- required_field_missing;
- invalid_evidence_binding;
- evidence_insufficient;
- attribution_ambiguous;
- source_role_ambiguous;
- proposition_relation_conflict;
- negation_or_modality_risk;
- deterministic_metadata_conflict;
- low_calibrated_confidence;
- reviewer_sensitive_field;
- candidate_disagreement.

Not every signal should be enabled by default.

The first implementation should distinguish:

- **operational failure** — provider unavailable, timeout, invalid structured output;
- **epistemic risk** — model returned something valid but validators found ambiguity or insufficient
  support;
- **ordinary valid proposal** — no escalation needed.

Fallback handles operational failure. Adaptive handles epistemic risk.

## Metadata-specific recommended default

After fixed fan-out and adjudication are proven, a sensible production policy can be:

```text
Strategy: adaptive

Primary:
  local Ollama profile
  fast/small structured model

Escalate when:
  evidence binding fails
  attribution/source role is ambiguous
  required high-risk field is unresolved
  deterministic conflict exists

Fan-out:
  2-3 cloud targets through configured OpenAI-compatible profile(s)

Adjudicator:
  one explicitly configured stronger model

Bounds:
  provider profile capacity is authoritative
  policy max_parallel is lower or equal
  one adjudication maximum
  explicit total call budget
```

This is an example, not a universal built-in model choice. DerridAI should not hard-code vendor/model
names.

## Embeddings and rerankers

Embedding execution must remain deliberately different from generative delegation.

A vector collection's embedding identity is part of its compatibility contract. Calls for one
collection must remain pinned to the configured provider/model/dimension identity. Dynamic routing
across embedding models would mix vector spaces and invalidate retrieval semantics even if models
return the same dimensionality.

Therefore:

| Operation                    | Delegation contract                                   |
| ---------------------------- | ----------------------------------------------------- |
| Embedding                    | pinned provider/profile/model per collection          |
| Derived embedding projection | pinned build contract; rebuild on incompatible change |
| Cross-encoder/reranker       | pinned unless an explicit pipeline version changes it |
| Structured metadata          | single/fallback/fan-out/adaptive                      |
| Research generation          | single/fallback initially                             |
| Adjudication                 | explicit target                                       |
| Deterministic NLP            | no model routing                                      |

Embedding throughput should be improved through batching, configured local concurrency, and the
existing shared embedding/model resource policy, not per-call routing.

## Pipeline Studio integration

Pipeline Studio should remain the authoritative visual/executable graph for model execution paths.

### Preserve historical structured pipelines

Existing structured-stage pipelines that use provider_role primary/review must remain reproducible.

Do not reinterpret old versions as ensemble policies.

Instead introduce a new strategy/version that explicitly selects an execution policy.

Conceptually:

```text
llm.structured_metadata          historical primary/review semantics
llm.execute_metadata_policy      new execution-policy semantics
```

Exact strategy naming should follow the existing registry conventions.

### Fan-out graph

The execution-aware metadata pipeline can represent:

```text
                  prepared task
                 /     |      \
                /      |       \
               ▼       ▼        ▼
          target A  target B  target C
               \       |        /
                \      |       /
                 ▼     ▼      ▼
                   compare
                     │
              ┌──────┴──────┐
              ▼             ▼
          resolved       ambiguous
              │             │
              │             ▼
              │         adjudicate
              │             │
              └──────┬──────┘
                     ▼
                 validate
```

Use GraphExecutor concurrency for independent target stages or a server-owned execution-policy
handler that internally submits bounded target work through the shared scheduling primitives.
Whichever implementation is chosen must preserve deterministic graph traces and must not create a
second independent provider capacity pool.

Prefer the representation that keeps the actual execution path visible in Pipeline Studio.

### Trace requirements

A resolved trace should make delegation inspectable without exposing source text or secrets.

Example:

```text
metadata.discourse
  local/qwen-small              completed
  validation                    escalation: attribution_ambiguous
  cloud/model-a                 completed
  cloud/model-b                 completed
  cloud/model-c                 completed
  candidate comparison          conflict: position_holder
  cloud/strong-model            completed
  final validation              completed
```

Trace fields should include:

- execution policy ID/version/hash;
- target ordinal/role;
- provider profile ID or secret-safe identity;
- resolved provider/model;
- elapsed time;
- wait time where available;
- status;
- coded failure/escalation reason;
- candidate count;
- comparison disposition;
- adjudication used/not used.

## Corpus Builder UX

The normal Corpus Builder should not require the user to manually design a provider DAG.

Replace or evolve the current primary/escalation controls into an execution-policy selector with a
clear summary.

Example:

```text
Metadata execution

Policy
  Adaptive — local first, cloud when needed

Primary
  Local Ollama · qwen-small

When difficult/ambiguous
  Cloud ensemble · 3 targets

Adjudicator
  Cloud · strong-model

Effective capacity
  Local provider: 2
  Cloud provider: 16
```

### UX requirements

- Reuse existing UI component wrappers and design-system components.
- All controls and explanatory text are fully internationalized.
- WCAG 2.2 AA remains a release gate.
- Show provider capacity separately from operation/policy max_parallel.
- Explain that increasing local GPU concurrency is not necessarily faster.
- Explain that an ensemble increases cost/latency and does not itself establish evidence.
- Support keyboard-only configuration.
- Do not expose provider secrets in the policy editor.
- Show validation errors before a run begins.
- Make the simple single-provider path the least complex option.

Advanced configuration may expose target models, fan-out width, adjudicator, and escalation
conditions.

## Provider administration UX

Execution policies should reference provider profiles rather than duplicate endpoint settings.

The Providers page may gain a read-only "used by policies" relationship, but profile editing remains
where endpoint credentials/concurrency/model discovery are managed.

An OpenAI-compatible profile can be used for many model overrides when the endpoint supports them.

Example:

```text
Provider profile: FreeLLM gateway
  base URL: ...
  capacity: 16

Execution policy targets:
  model-a
  model-b
  model-c
  strong-model
```

All four share the same profile capacity unless intentionally configured as separate provider
profiles with genuinely independent endpoint quotas.

## Persistence and audit

Raw candidates are execution artifacts. They should not all become canonical FieldAssertions.

The selected model proposal continues through the existing review workflow. Human-reviewed state
remains canonical.

However, enough execution provenance must be durable to answer:

- which policy/version was used?
- which providers/models actually ran?
- which candidates were valid or rejected?
- why did the system escalate?
- why was adjudication invoked?
- which candidate or adjudication output became the proposal?
- which evidence bindings were associated with that selected proposal?

Recommended durable structure:

```text
model_execution_run
  run_id
  policy_id
  policy_version
  policy_hash
  task_type
  build/job ID
  Record ID
  source revision/fingerprint
  started/finished timestamps
  final disposition

model_execution_candidate
  run_id
  candidate ordinal
  provider profile ID
  provider
  model
  status
  elapsed
  attempt count
  validation disposition
  candidate content hash
  evidence identity/hash summary

model_execution_decision
  run_id
  comparison disposition
  selected candidate ordinal
  adjudication candidate ordinal
  escalation reason codes
```

This may be implemented through existing durable application persistence rather than literal tables
with these names. The important part is separation from canonical Record authority.

Avoid duplicating full raw source text/prompts in execution history if they can be reconstructed from
the source revision, schema/version, run guidance, precedent identities, and policy/pipeline
snapshots.

## Security and privacy

1. Policy documents store provider profile IDs, never API keys.
2. Runtime resolution injects credentials only at the final provider-call boundary.
3. Pipeline traces and operation telemetry use secret-safe profile identities.
4. Provider exception text is sanitized/coded before persistence because it may include response or
   source content.
5. Researcher-safe APIs expose only provider/policy fields allowed by role policy.
6. Policy import/export must reject embedded credentials.
7. Model target overrides must be validated against provider/profile permissions where applicable.
8. No fan-out target may bypass existing content-policy/security boundaries merely because another
   provider is used.

## Cancellation, timeouts, and failure semantics

The policy service must be cancellation-aware at every stage:

- before target admission;
- while waiting for shared capacity;
- while waiting for futures;
- before adjudication;
- before final persistence.

Cancellation must stop admitting new fan-out work and cancel queued futures where possible.
Already-running HTTP calls follow the existing provider cancellation/timeout behavior.

Failures are classified, not flattened.

At minimum distinguish:

- unavailable;
- timed_out;
- transport_failed;
- structured_output_failed;
- invalid_candidate;
- evidence_insufficient;
- cancelled;
- stale_source;
- budget_exhausted.

A policy may configure which operational failure classes trigger fallback. Epistemic conditions are
handled separately by adaptive escalation.

## Determinism under concurrency

Concurrency may change completion order but not final semantics.

Required rules:

- targets have stable ordinals derived from the resolved policy;
- candidate arrays are ordered by target ordinal;
- comparisons iterate in stable order;
- equivalent ties use deterministic rules;
- graph traces are definition/policy ordered rather than completion ordered;
- authoritative Record writes remain guarded by source/revision identity;
- provider completion time is telemetry, not a selection signal unless a policy explicitly declares
  a latency race strategy in a future version.

A latency-race strategy is out of scope for the initial implementation.

## Observability

Add model-execution telemetry to existing operational surfaces.

Per call:

- execution run ID;
- provider profile ID;
- provider/model;
- task/family;
- target ordinal;
- capacity resource/key;
- configured provider limit;
- policy max_parallel;
- queue wait;
- service time;
- attempt count;
- cancellation/failure class.

Per policy run:

- candidate count;
- number valid/invalid;
- escalation reason(s);
- adjudication used;
- total model calls;
- wall-clock time;
- estimated/known provider cost if a provider exposes safe accounting;
- final disposition.

Corpus Builder live state should be able to summarize active local/cloud calls and waiting capacity
without representing this as scholarly metadata.

Pipeline Studio should expose the detailed trace.

## API surface

The first implementation likely needs administrative CRUD for execution policies and read endpoints
for allowable selection.

Conceptual routes:

```text
GET    /api/model-execution/policies
POST   /api/model-execution/policies
GET    /api/model-execution/policies/{policy_id}/{version}
POST   /api/model-execution/policies/{policy_id}/versions
POST   /api/model-execution/policies/{policy_id}/{version}/validate
GET    /api/model-execution/runs/{run_id}
```

Exact route placement should follow current router decomposition and route-policy conventions.

Corpus build/run request contracts should refer to policy identity rather than embed all policy
configuration once policy persistence exists.

For backwards compatibility, existing provider_profile_id and review_provider_profile_id request
fields remain accepted during migration and are translated to an ephemeral equivalent single/fallback
policy at the boundary.

## Backwards compatibility and migration

### Existing requests

Current callers that provide:

```text
provider_profile_id
review_provider_profile_id
```

must continue to work during the migration.

The server can resolve those fields into an internal ephemeral policy:

```text
primary only                         => single
primary + review on failure          => fallback
```

No persisted policy is required for legacy calls.

### Existing pipelines

Historical pipeline definitions retain their current primary/review behavior.

Do not mutate stored pipeline JSON to new semantics.

New built-in pipeline versions may opt into execution-policy stages after the new runtime is proven.

### Existing builds

An in-progress or persisted build must retain the provider/pipeline semantics with which it began.
Do not retroactively attach a new global default policy to an old build.

### Existing audit records

No migration should rewrite old provider/model audit records. New execution-run provenance is
additive.

## Implementation phases

### Phase 1 — contracts and parity

Goal: introduce the execution-policy abstraction without changing user-visible model behavior.

Work:

- add model_execution contracts and service boundary;
- add policy validation for single/fallback;
- add target resolution through existing provider profiles;
- route target calls through existing structured completion code;
- use existing ConcurrencyCoordinator for all calls;
- adapt metadata primary/review behavior to an ephemeral policy internally;
- preserve current pipeline versions;
- add execution identity/telemetry;
- add tests proving equivalent provider call order and output.

Exit criteria:

- all current metadata provider/escalation tests pass unchanged or with trace-only updates;
- no direct behavior regression;
- one process-wide provider limit still governs Corpus Builder/RAG/tools/execution service;
- no secret appears in execution snapshots.

### Phase 2 — fixed fan-out

Goal: run independent targets concurrently and collect deterministic candidate sets.

Work:

- add fan_out strategy;
- add model overrides per target;
- add policy max_parallel and max_total_model_calls;
- reuse bounded scheduling/GraphExecutor primitives;
- create ModelCandidate and coded candidate validation;
- preserve stable target ordering;
- add cancellation and deadline behavior;
- persist secret-safe candidate execution provenance.

Exit criteria:

- N targets overlap when provider capacity allows;
- same-profile targets share one aggregate capacity limit;
- separate providers can overlap independently;
- completion order does not change candidate order;
- cancellation leaks no capacity permits.

### Phase 3 — metadata candidate comparison

Goal: make ensemble results meaningful for schema-defined metadata.

Work:

- add field-level candidate normalization/equivalence;
- classify unanimous/compatible/conflicting/unsupported/invalid/missing outcomes;
- compare evidence bindings separately from value agreement;
- select only deterministically resolvable validated proposals;
- integrate with metadata reconciliation without making raw candidates canonical;
- add Pipeline Studio comparison/fan-in strategy and trace presentation.

Exit criteria:

- agreement cannot bypass evidence validation;
- majority vote alone cannot make unsupported metadata admissible;
- deterministic comparison is stable across target completion order;
- selected proposal enters the same review/autofill path as a single-provider proposal.

### Phase 4 — adjudication

Goal: resolve material candidate disagreement with one bounded additional model task.

Work:

- add adjudicator target to policy;
- construct bounded adjudication prompt/context from validated candidates;
- require structured field-level decision + evidence;
- validate adjudicator output through ordinary metadata validators;
- persist adjudication identity/disposition;
- unresolved adjudication becomes human review.

Exit criteria:

- at most one adjudication occurs per policy run;
- invalid adjudicator output never becomes authoritative;
- no recursive model cascade is possible;
- disagreement remains visible in audit data.

### Phase 5 — adaptive validator-driven escalation

Goal: avoid expensive cloud fan-out when the local result is already good enough.

Work:

- formalize coded escalation predicates;
- map current metadata validator outputs to those predicates;
- distinguish operational fallback from epistemic escalation;
- run primary locally first;
- invoke configured fan-out only when predicate(s) fire;
- expose escalation reasons in traces and live telemetry;
- benchmark local-first quality/latency/cost.

Exit criteria:

- ordinary valid cases stop after the primary call;
- configured high-risk/ambiguous cases escalate reproducibly;
- policy snapshots make escalation behavior reproducible;
- validator signal changes are versioned/tested.

### Phase 6 — UI and administration

Goal: make policies understandable and safe to configure.

Work:

- add administrative model-execution policy management;
- add reusable policy selector UI component;
- evolve Corpus Builder primary/escalation UI to policy selection;
- retain simple single-provider UX;
- show target summary and effective capacity;
- expose advanced fan-out/adjudication controls;
- add Pipeline Studio visualization/editor support;
- add Storybook stories;
- complete i18n in all supported UI locales;
- run WCAG 2.2 AA and long-string/reflow coverage.

Exit criteria:

- no feature-specific provider configuration duplication;
- all UI uses standard DerridAI component wrappers;
- keyboard navigation and screen-reader naming are complete;
- policy validation errors are understandable before execution.

### Phase 7 — reliability and performance hardening

Goal: prove the architecture under realistic local/cloud workloads.

Work:

- benchmark local-only, fixed fan-out, and adaptive policies;
- test high-concurrency OpenAI-compatible gateways;
- test Ollama capacity 1/2 and mixed local/cloud execution;
- test process-wide contention with RAG/tools/Corpus Builder;
- test stale source revisions during fan-out;
- test provider partial failure;
- test restart/interruption semantics for persisted operation state;
- update requirements and traceability matrix;
- update ARCHITECTURE.md and USER_GUIDE.md once behavior ships.

Exit criteria:

- no provider-capacity oversubscription;
- no authoritative state divergence at concurrency 1 versus N for fixed outputs;
- no stale candidate overwrite;
- no unsupported evidence regression;
- benchmark results justify default policy recommendations.

## Proposed PR sequence

Keep implementation changes small enough to review and bisect.

### PR 1 — Model execution contracts and parity

- model_execution package;
- policy contracts/validation;
- single/fallback execution;
- legacy primary/review adapter;
- shared-capacity integration;
- parity tests;
- initial telemetry.

No new fan-out behavior.

### PR 2 — Parallel target execution

- fan_out strategy;
- model override targets;
- bounded concurrency;
- cancellation/deadline handling;
- candidate provenance;
- deterministic ordering.

No adaptive routing yet.

### PR 3 — Metadata ensemble comparison

- FieldAssertion-aware candidate normalization;
- evidence-aware deterministic comparison;
- metadata reconciliation integration;
- Pipeline Studio fan-in support;
- traces and tests.

### PR 4 — Adjudication

- bounded adjudicator;
- candidate packet contract;
- final validation;
- unresolved-to-human-review behavior;
- audit trail.

### PR 5 — Adaptive routing

- validator escalation predicates;
- local-first behavior;
- operational fallback versus epistemic escalation;
- policy defaults/benchmarks.

### PR 6 — UI and policy administration

- policy CRUD UI/API;
- Corpus Builder policy selection;
- reusable components;
- Pipeline Studio editor/presentation;
- i18n/WCAG/Storybook.

### PR 7 — hardening and documentation

- load/stress tests;
- failure/cancellation/restart tests;
- requirements/specification links;
- architecture/user-guide updates;
- traceability-matrix coverage;
- benchmark documentation.

If implementation reveals a clean smaller split, PRs may be subdivided, but do not combine all
phases into one monolithic change.

## Test plan

### Contract tests

- policy schema accepts valid single/fallback/fan-out/adaptive definitions;
- invalid/unbounded definitions are rejected;
- missing provider profile is explicit;
- model override resolution is reproducible;
- secrets never serialize.

### Capacity tests

- same provider profile never exceeds N aggregate concurrent calls;
- targets with different model overrides still share the same profile limit;
- independent profiles can each reach their own limit;
- policy max_parallel lowers but never raises provider capacity;
- cancellation while waiting leaks no permit;
- failure after acquisition releases the permit;
- Ollama runtime constraints compose with provider capacity.

### Structured-output tests

- each target independently uses shared repair/retry/schema validation;
- invalid structured output is a candidate/provider failure, not a null metadata value;
- truncation, timeout, and transport failures remain distinguishable;
- fallback rules trigger only on configured classes.

### Comparison tests

- exact equivalent values become unanimous;
- normalized aliases become compatible when the field contract permits;
- conflicting values remain conflicting;
- unsupported agreement remains unsupported;
- valid minority evidence can prevent blind majority selection;
- completion order does not affect the result;
- all candidate ordering is stable.

### Adjudication tests

- adjudicator receives only bounded validated candidate information;
- adjudicator may choose/reject/replace according to field contract;
- adjudicator must bind required evidence;
- invalid adjudication becomes unresolved;
- at most one adjudication runs.

### Metadata authority tests

- reviewer-confirmed value is never overwritten;
- stale Record revision invalidates in-flight candidate results;
- deterministic document metadata keeps priority;
- no candidate bypasses FieldAssertion authority rules;
- no provider failure becomes confirmed absence;
- evidence/citation checks remain mandatory.

### Pipeline tests

- historical metadata pipeline versions retain current primary/review behavior;
- new execution-policy strategy validates only supported config;
- fan-out/fan-in graph traces remain deterministic;
- unsupported strategy combinations fail validation before execution;
- Pipeline Studio dry runs exercise actual routing without persistence.

### Frontend tests

- policy editor uses standard components;
- Corpus Builder defaults remain understandable for one-provider users;
- provider capacity and policy parallelism are visually distinct;
- invalid policy cannot start a build;
- keyboard navigation works;
- all strings come from i18n;
- long translations/reflow are covered;
- axe/WCAG release checks pass;
- Storybook covers single, fallback, fan-out, adaptive, unavailable-provider, and validation-error
  states.

## Benchmark plan

Measure at least:

- local primary only;
- local primary + cloud fallback;
- fixed cloud fan-out 2/3/4 targets;
- adaptive local-first with observed escalation rate;
- local Ollama concurrency 1/2 where supported;
- remote provider capacities 4/8/16/32 where supported.

Report separately:

- total wall-clock time;
- time to first reviewable Record;
- Record p50/p95 completion;
- provider queue wait p50/p95;
- provider service time p50/p95;
- capacity utilization;
- model calls per Record;
- escalation percentage;
- adjudication percentage;
- structured-output failure rate;
- evidence insufficiency rate;
- attribution/source-role correction rate;
- reviewer accept/correct/reject rate;
- estimated/known provider cost;
- CPU/memory pressure;
- persistence/merge time.

Quality must be evaluated alongside throughput. A faster policy that increases unsupported
FieldAssertions or reviewer correction load is not an improvement.

## Acceptance criteria for the complete feature

The architecture is considered complete only when all of the following are true:

1. One DerridAI-owned execution policy can select single, fallback, fan-out, or adaptive execution.
2. Existing provider profiles remain the only endpoint/credential configuration abstraction.
3. FreeLLMAPI or another OpenAI-compatible gateway works without feature-specific code.
4. Same-profile multi-model fan-out respects one shared capacity limit.
5. Local embeddings remain pinned to their collection embedding contract.
6. Every metadata candidate uses shared structured-output validation.
7. Candidate agreement cannot bypass evidence validation.
8. Deterministic comparison occurs before adjudication.
9. At most one bounded adjudication step occurs.
10. Unresolved disagreement becomes human review.
11. Stale source/revision results cannot overwrite newer state.
12. Human-confirmed values remain authoritative.
13. Historical pipeline versions remain reproducible.
14. Policy version/hash and actual provider/model identities are auditable.
15. Secrets are absent from persisted execution traces/snapshots.
16. Fixed outputs produce equivalent scholarly state at concurrency 1 and N.
17. Pipeline Studio visibly represents the resolved delegation path.
18. Corpus Builder exposes a comprehensible policy-oriented UX.
19. New UI is fully internationalized and WCAG 2.2 AA compliant.
20. Requirements/specification/test traceability is updated before release.

## Likely code touch points

This is a planning map, not a mandate to make these files larger. Prefer focused modules and extract
new responsibilities rather than growing existing monoliths.

Backend:

- api/app/concurrency.py — reuse only; extend metrics/resources only if required.
- api/app/llm.py and structured-completion helpers — reuse provider call path.
- api/app/provider_profile_options.py — provider/target resolution integration.
- api/app/pipelines/graph_execution.py — reuse bounded fan-out/fan-in; extend only when generic graph
  behavior is genuinely missing.
- api/app/pipelines/structured_llm_stage.py — preserve historical semantics.
- api/app/pipelines/corpus_metadata_enrichment.py — bridge to new execution-policy strategy.
- api/app/pipelines/registry.py — register new server-owned strategies/settings.
- api/app/pipelines/defaults.py — add new built-in versions only when ready.
- api/app/corpus_metadata_enrichment_execution.py — adapt candidate/validator integration.
- api/app/models.py — request/response contracts as needed.
- api/app/routers/ — policy CRUD/read APIs.
- api/app/system_store.py or focused execution-policy persistence module — durable policy/run state.
- new api/app/model_execution/\* modules — orchestration domain.

Frontend:

- web/src/api/ — execution policy/run contracts.
- web/src/components/corpus-builder/CorpusEnrichmentConfiguration.vue — evolve provider selection.
- web/src/components/providers/ — shared provider/target presentation where appropriate.
- web/src/components/pipelines/ — strategy configuration and run trace presentation.
- web/src/domain/ — execution-policy presentation/service logic.
- web/src/i18n/ and Python locale dictionaries — complete localization.
- Storybook and frontend tests for all reusable controls.

Documentation/requirements:

- docs/ARCHITECTURE.md;
- docs/USER_GUIDE.md;
- docs/requirements/LLM_PROVIDERS.md;
- relevant Corpus Builder/Pipeline requirements;
- SPECIFICATION.md where normative contracts change;
- requirements-to-test traceability documentation.

## Implementation discipline

During implementation:

- do not hard-code metadata field names where schema/FieldAssertion abstractions already exist;
- do not put new provider routing decisions inside feature UI code;
- do not duplicate capacity accounting;
- do not introduce hidden fallback behavior outside policy/pipeline identity;
- keep provider failures coded and visible;
- keep functions/classes named for responsibilities rather than implementation accidents;
- decompose new modules before they become monolithic;
- document non-obvious concurrency, determinism, and authority logic;
- use standard TypeScript/Python documentation conventions;
- add tests with each phase rather than after the architecture is complete;
- keep README/architecture/specification claims aligned with implemented state, not planned state.

## Open design questions to resolve during PR 1-3

These questions should be answered by tests and the smallest stable contract, not by speculative
abstraction.

1. Should execution policies be globally versioned resources immediately, or should the first
   single/fallback implementation use an internal immutable snapshot and add CRUD persistence with
   the UI phase?
2. Should fixed fan-out be represented as explicit sibling Pipeline stages or one generic
   execution-policy strategy whose internal calls are surfaced as child trace entries?
3. What is the canonical field-equivalence hook for arbitrary schema-defined fields, especially
   entity/list/structured relation values?
4. Which existing validator outputs are stable enough to become public adaptive escalation reason
   codes?
5. Which candidate details must be durable for scholarly audit versus task-local and reconstructable?
6. Should adjudicator targets be prohibited from matching any candidate target, or merely warned
   about lack of independence?
7. What server-owned maximum should cap fan-out width and max_total_model_calls?
8. Which roles may create/edit policies versus only select administrator-approved policies?
9. How should policy defaults interact with per-build explicit provider overrides during the
   compatibility period?

None of these questions should weaken the core invariants: deterministic authority, evidence
requirements, bounded execution, secret safety, and reproducible resolved identity.

## Final architectural rule

The orchestrator decides **where and how many times to ask models**.

Providers decide **how to call a configured endpoint/model**.

Pipelines decide **which server-owned execution strategy is active and how stages connect**.

Deterministic DerridAI validators decide **whether a candidate is admissible**.

Human review and canonical scholarly state decide **what is authoritative**.

Those responsibilities must remain separate throughout implementation.
