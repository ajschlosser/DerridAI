<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Metadata schemas

A metadata schema says which fields a JSONL record has, what each may hold, and what the model is told to look for in each. Builds target a schema; the built-in one describes the fields DerridAI has always produced.

## Versioning and field identity

Schemas are semantic-versioned independently of the application and corpus contracts. New schemas start at `1.0.0`; an unchanged save retains its version; adding fields increments the minor version, removing fields increments the major version, and other definition changes increment the patch version. Each field has a stable `field_id` separate from its display name, so a deliberate rename can retain semantic/provenance identity.

## What a schema contains

- **Groups.** Each group is one model call per record. It has an opening text, an optional heading for its field list, notes, a trailer, and a footer with the evidence and assessment instructions. The footer may use `{fields}` and `{assessed_fields}`.
- **Fields.** Flat, not nested. Each has a stable semantic identity plus name/label, type (`text`, `number`, `boolean`, `choice`, `list`), a group, and the instruction the model receives (`{values}` is replaced by allowed values). A deliberate rename may preserve the stable field identity so compatible reviewed precedents remain attached to the same semantic field. A `choice` field has allowed values, each with an optional definition; `strict` makes them the only values the model may return. `evidence` requires source binding, `assess` requests confidence, and `review` keeps a record from being accepted while the field is unresolved. Fields may also define POS/NER guidance and reviewed-precedent retrieval policy.

## The locked core

`region_type`, `primary_text` and `discourse_role` are in every schema, in the `discourse` group, and cannot be changed or removed: DerridAI's page-range and document-layout logic depends on them. Their prompt lines and values come from the code. Names DerridAI itself uses (the record's source fields, the document-level fields records inherit, computed fields) cannot be field names either.

## NLP hints

Schema fields can provide deterministic autocomplete for Universal POS tags and the supported NER tag vocabulary. These tags are prompt/search guidance about what linguistic forms to notice; they do not themselves populate metadata, prove that a value applies, or replace evidence requirements.

## Reviewed-precedent retrieval

A field or group can allow evidence-bound reviewed precedents to guide later enrichment. A field-level profile overrides its group's profile; otherwise the group profile applies, including to locked core fields. The active retrieval profile contains only:

- `enabled`;
- `max_items` (maximum precedents);
- `min_similarity`;
- `include_corrections`;
- `include_confirmed_absence`.

Corrections keep the rejected model value as negative evidence; it must never be taught as the correct answer. Confirmed absence is reusable only when a reviewer explicitly bound source evidence to that no-value decision. Locked core fields can inherit group policy.

These controls affect advisory enrichment context only. They do not modify canonical reviewed records, change assertion authority, or route metadata exemplars into Research response/claim memory. See [METADATA_MEMORY.md](METADATA_MEMORY.md).

## Run-specific field guidance

Corpus Builder can add per-build guidance after schema selection: an instruction and/or names, titles, concepts, or variants to watch for. This guidance is saved with the build, not the schema. Exact phrase matches may become review cues and prompt context, but they do not change allowed values or count as evidence.

## One schema per build, fixed

A build copies its schema when it starts. Editing or deleting a saved schema afterwards cannot change it, and a build is never re-run against another schema.

## Sharing

Export writes one JSON file: `{"derridai_metadata_schema": 1, "sha256": …, "schema": …}`. Import validates the file like anything typed into an editor; the checksum catches damage or edits after export, and is not a signature.

## API (administrators)

`GET/POST /api/pdf/metadata-schemas`, `GET/PUT/DELETE /api/pdf/metadata-schemas/{id}`, `GET …/{id}/export`, `POST /api/pdf/metadata-schemas/import`.

## Using it

- **Choose one for a build:** step 5 of the build setup ("Metadata schema"). The build keeps its own copy.
- **Edit schemas:** administrators use **System → Metadata schemas**. "Manage schemas…" in Corpus Builder opens the same editor in a dialog, with a link to that page. The editor lists saved schemas, groups/instructions, fields, allowed values, evidence/assessment/review requirements, NLP hints, and Memory & retrieval controls, plus duplicate/delete/export/import actions. Researcher accounts cannot open the page or change schemas.
- **Try one:** the editor's "Try it on a passage" shows the prompt a group produces, or runs it on a passage with a model. A real build adds the document details, editorial memory and neighbouring records to that prompt.

## What follows the schema

Prompts and the shape of the model's answer; which fields the model may set and which need cited evidence; which fields keep a record from being accepted; what a person may edit and how it is checked; the review panel (fields, labels, controls) and bulk edit; the enrichment dialog's groups. The built-in schema reproduces today's behaviour, and a test compares the prompts it builds with the ones DerridAI has always used.

## Not covered

- Fixed fields that sit outside the schema (the document-level ones records inherit) are unchanged and not configurable.
- A build made before this release has no schema copy and uses the built-in one.
- Compatibility loaders may accept older schema representations, but new documentation/code should use the current field identity and retrieval-profile contract rather than reviving migrated legacy flags.
