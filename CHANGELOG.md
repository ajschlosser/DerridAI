<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Changelog

Release history for DerridAI, newest first. Each entry links to the full release note in [`docs/notes/`](docs/notes/). The README describes only the current release.

## 0.80.5 — Cambridge

Cambridge completes the canonical FieldAssertion migration, tightens metadata
review and Research prompt-metadata configuration, substantially decomposes and
modernizes Corpus Builder, aligns `SPECIFICATION.md` with DERRIDAI Core
Specification 1.0, and adds the first walkable DERRIDAI object-graph explorer.
It also adds multilingual README coverage, AGPLv3 licensing, and stronger
repository-format/handoff discipline. See
[0.80.5](docs/notes/0.80.5.md) for the complete release note.

## 0.80.0 — Beverly

The release since 0.70.0 consolidates the canonical metadata and provenance
migration, the continuing Corpus Builder and native Vue decomposition, and the
application's system-data and research-workspace improvements. See
[0.80.0](docs/notes/0.80.0.md) for the complete release note.

- **Corpus Builder and ingestion:** decomposed build lifecycle, segmentation,
  enrichment, review, publication, source-quality, and reviewer transport
  responsibilities; added broader source-media ingestion; and improved
  document-structure, record-quality, enrichment-rerun, and publication
  readiness workflows.
- **Canonical metadata assertions:** introduced durable `FieldAssertion`
  records with independent derivation, evaluation, authority, value-state,
  confidence, evidence, revision, and identity fields; migrated legacy
  metadata lazily and idempotently while retaining compatibility projections;
  preserved unresolved, invalid, confirmed-absent, model-inferred, and
  human-confirmed states; and kept model derivation and confidence when a
  reviewer confirms the assertion.
- **Provenance, review, and retrieval:** integrated assertions with SQLite
  persistence, enrichment, autonomous settlement, review state, publication,
  provenance memory, evidence binding, and dynamic search facets; hardened
  blind and second-opinion review; made custom fields first-class in RAG
  evidence payloads and Search facets; and kept retrieval, vector indexes,
  caches, and generated output separate from authoritative corpus records.
- **Frontend and administration:** continued the native Vue migration across
  core research surfaces and redesigned System Data into typed,
  URL-addressable workspaces for databases, response caches, metadata
  examples, and advanced administration. Built-in structural semantics remain
  explicit where they govern segmentation and publication, while the Record
  Inspector, touch-up workflow, Search, and Research evidence presentation now
  discover schema-defined metadata through canonical assertions instead of
  requiring each custom field to be added to presentation constants.
- **Reliability and governance:** expanded API contracts, backend regression
  coverage, typed frontend tests, parallel CI, Playwright/axe coverage,
  accessibility and design-token checks, locale parity, backup/restore
  coverage, authentication boundaries, and researcher access restrictions.

## 0.70.0 — Amesbury

A consolidation release covering the Vue/runtime and Corpus Builder decomposition, specification-aligned assertion status vocabulary, metadata-schema/review improvements, search/provider/theme/internationalization work, and related reliability changes. See [0.70.0](docs/notes/0.70.0.md).

## 0.62.19 — Configurable Chameleon

Metadata schemas: define which fields JSONL records have, their allowed values and what the model looks for in each; save, share and choose one per build. See [0.62.19](docs/notes/0.62.19.md).

## 0.62.18 — Hands-free Heron

A hands-free mode, and fixes to review: a quoted speaker can be added, Save & mark reviewed stays in reach, the review screen is more compact, and the default model is no longer loaded unasked. See [0.62.18](docs/notes/0.62.18.md).

## 0.62.17 — Watertight Weasel

Closes the remaining ways a second reviewer could see the first reviewer's answer, and repairs master's failing checks. See [0.62.17](docs/notes/0.62.17.md).

## 0.62.16 — Discreet Dormouse

The changes an enrichment pass makes are now shown, and a second reviewer's blind answer is hidden in every response. See [0.62.16](docs/notes/0.62.16.md).

## 0.62.15 — Patient Pelican

The build says what it is waiting for, a model load is no longer abandoned, dropped connections are retried, and the providers page has its model list back. See [0.62.15](docs/notes/0.62.15.md).

## 0.62.14 — Tidy Tern

Corpus Builder fixes: preparing the workspace no longer blocks the page, a redesigned bulk edit, no more clipped record text or cut-off menus, working LLM touch-up, and no placeholder values. See [0.62.14](docs/notes/0.62.14.md).

## 0.62.13 — Fair Falcon

Human reliability can now be measured: reviewer re-checks, blind second opinions and reviewer ids in the ledger. See [0.62.13](docs/notes/0.62.13.md).

## 0.62.12 — Rigorous Robin

Enrichment experiments can be run and analysed: conditions are recorded on every event, ablations and arms are real switches, there is a frozen gold set, more measures with intervals, and a CSV export. See [0.62.12](docs/notes/0.62.12.md).

## 0.62.11 — Measured Marmot

Enrichment is now measured: every model proposal and call is ledgered, ten measures are computed per model and field, runs carry ids, and concurrent runs are limited. See [0.62.11](docs/notes/0.62.11.md).

## 0.62.10 — Careful Crane

Records no longer start or end mid-sentence, the main-text start page has one source of truth and is suggested from the document's own structure, and confident LLM values are filled in with an audit trail. See [0.62.10](docs/notes/0.62.10.md).

## 0.62.9 — Steady Swift

Scrolling no longer gets stuck in the review workspace, and edits to document metadata are no longer lost or refused. See [0.62.9](docs/notes/0.62.9.md).

## 0.62.8 — Spacious Stork

The Corpus Builder review workspace fills the screen, keeps its decisions in one row within reach, and its panes can be resized from the keyboard. See [0.62.8](docs/notes/0.62.8.md).

## 0.62.7 — Nocturnal Newt

The Languages, Response Library, Record, Settings and Compare views follow the theme, so dark mode works there too, and four layout and accessibility defects found on the way are fixed. See [0.62.7](docs/notes/0.62.7.md).

## 0.62.6 — Luminous Lynx

The Corpus Builder and the shared components are built on design tokens, so dark mode, increased contrast and forced colors now work there, and its accessibility is checked in both colour schemes. See [0.62.6](docs/notes/0.62.6.md).

## 0.62.5 — Iterative Ibis

Metadata enrichment can run as a chain of passes while you keep reviewing, and later passes learn from your decisions and from earlier passes. See [0.62.5](docs/notes/0.62.5.md).

## 0.62.4 — Whimsical Wombat

The Home Operations panel is rebuilt for keyboard and screen-reader use and to be easier to read, and the remaining accessibility problems on the Home page and sign-in screen are fixed. See [0.62.4](docs/notes/0.62.4.md).

## 0.62.3 — Vigilant Viper

Vector Stores can use a running Chroma server as well as the local filesystem, and the workspace is a Vue page. See [0.62.3](docs/notes/0.62.3.md).

## 0.62.2 — Vexing Vixen

The sidebar is complete as soon as you sign in, researcher text policies are generated in the language they are for, and the language and policy screens lose their regional special cases. See [0.62.2](docs/notes/0.62.2.md).

## 0.62.1 — Factory Reset

NUKE now returns DerridAI to a first-run install: users, corpora, vector stores, and job history are deleted, and the next load asks for a new administrator. The sign-in screen, footer, and API health endpoints show the git commit next to the version. See [0.62.1](docs/notes/0.62.1.md).

## 0.62.0 — Vociferous Vulture

Researcher forbidden-term lists move out of the application source into generated per-locale policies, stored with the language in the system database. See [0.62.0](docs/notes/0.62.0.md).

## Earlier releases

- [0.61.0](docs/notes/0.61.0.md) — Undulating Umbrellabird
- [0.60.0](docs/notes/0.60.0.md) — Testy Titmouse
- [0.59.0](docs/notes/0.59.0.md) — Serious Sandpipers
- [0.58.0](docs/notes/0.58.0.md) — Righteous Rhinoceros
- [0.56.0](docs/notes/0.56.0.md) — Perilous Penguins
- [0.54.0](docs/notes/0.54.0.md) — Neurotic Gnat
- [0.53.0](docs/notes/0.53.0.md) — Manic Monkey
- [0.51.0](docs/notes/0.51.0.md) — Krazy Kangaroo
- [0.50.1](docs/notes/0.50.1.md) — Ignoble Insect
- [0.50.0](docs/notes/0.50.0.md) — Ingenious Iguana
- [0.49.0](docs/notes/0.49.0.md) — Hungry Hippo
- [0.48.1](docs/notes/0.48.1.md) — Gifted Grungus
- [0.47.1](docs/notes/0.47.1.md) — Fatso
- [0.47.0](docs/notes/0.47.0.md) — Gregarious Guinea Pig
- [0.46.1](docs/notes/0.46.1.md) — Gray Fox
- [0.46.0](docs/notes/0.46.0.md) — Feral Fox
- [0.45.0](docs/notes/0.45.0.md) — Energized Elephant
- [0.42.1](docs/notes/0.42.1.md) — Bunny Rabbit - Again
- [0.40.10](docs/notes/0.40.10.md) — Corpus of Engineers
- [0.40.9](docs/notes/0.40.9.md) — Enter Sandman
- [0.40.8](docs/notes/0.40.8.md) — Coming Around the Mountain
- [0.40.5](docs/notes/0.40.5.md) — Record Extraction Pipeline Corrections
- [0.40.1](docs/notes/0.40.1.md) — Dorar the Explorah
- [0.40.0](docs/notes/0.40.0.md) — Pdffffffffft.
- [0.37.1](docs/notes/0.37.1.md) — Disoriented
- [0.37.0](docs/notes/0.37.0.md) — New Direction
- [0.36.11](docs/notes/0.36.11.md) — Peekaboo
- [0.36.10](docs/notes/0.36.10.md) — In Search of Lost Time
- [0.36.4](docs/notes/0.36.4.md) — Oops You Did It Again
- [0.36.3](docs/notes/0.36.3.md) — All The Little Things
- [0.36.2](docs/notes/0.36.2.md) — Bugs in the Machine
- [0.36.1](docs/notes/0.36.1.md) — Fresh-start SQLite cleanup
- [0.36.0](docs/notes/0.36.0.md) — The SQL Prequel
- [0.35.17](docs/notes/0.35.17.md) — Lingua Franca
- [0.35.16](docs/notes/0.35.16.md) — Tongue Tied Again
- [0.35.12](docs/notes/0.35.12.md) — Tongue Twister
- [0.35.10](docs/notes/0.35.10.md) — Record Player
- [0.35.5](docs/notes/0.35.5.md) — RAGety Anne
- [0.35.0](docs/notes/0.35.0.md)
- [0.31.3](docs/notes/0.31.3.md)
- [0.31.0](docs/notes/0.31.0.md) — The Pretty Release
- [0.30.13](docs/notes/0.30.13.md) — Bits and Bobs
- [0.30.12](docs/notes/0.30.12.md) — All the Little Things
- [0.30.11](docs/notes/0.30.11.md) — Big Packet Reduction
- [0.30.10](docs/notes/0.30.10.md) — Searching for Answers Fix
- [0.30.8](docs/notes/0.30.8.md) — Dashboard search, Works, annotations, and user-provider cleanup
- [0.30.7](docs/notes/0.30.7.md) — Dashboard Cleanup
- [0.30.6](docs/notes/0.30.6.md) — Vector Store Cleanup
- [0.30.5](docs/notes/0.30.5.md) — Bibliographic metadata workflows, annotation organization, and aligned forms
- [0.30.3](docs/notes/0.30.3.md) — Restored research-workspace baseline
- [0.23.0](docs/notes/0.23.0.md) — Evidence workflows, researcher policy, i18n, and shareable table state
- [0.22.0](docs/notes/0.22.0.md) — RAG grading, FAQ workflow, UI, and frontend development
- [0.21.1](docs/notes/0.21.1.md) — FAQ, grading, and comparison bug fixes
- [0.21.0](docs/notes/0.21.0.md) — performance and regression fixes
- [0.20.0](docs/notes/0.20.0.md) — Vue 3 frontend migration
- [0.10.1](docs/notes/0.10.1.md) — highlights
- [0.10.0](docs/notes/0.10.0.md) — highlights
- [0.9.0](docs/notes/0.9.0.md) — highlights
