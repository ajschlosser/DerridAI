<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Metadata schemas

A metadata schema says which fields a JSONL record has, what each may hold, and what the model is told to look for in each. Builds target a schema; the built-in one describes the fields DerridAI has always produced.

## What a schema contains

- **Groups.** Each group is one model call per record. It has an opening text, an optional heading for its field list, notes, a trailer, and a footer with the evidence and assessment instructions. The footer may use `{fields}` and `{assessed_fields}`.
- **Fields.** Flat, not nested. Each has a name, label, type (`text`, `number`, `boolean`, `choice`, `list`), a group, and the instruction the model receives (`{values}` is replaced by the allowed values). A `choice` field has allowed values, each with an optional definition; `strict` makes them the only values the model may return. `evidence` requires the model to cite source blocks, `assess` requires a confidence, `review` keeps a record from being accepted while the field is unresolved.

## The locked core

`region_type`, `primary_text` and `discourse_role` are in every schema, in the `discourse` group, and cannot be changed or removed: DerridAI's page-range and document-layout logic depends on them. Their prompt lines and values come from the code. Names DerridAI itself uses (the record's source fields, the document-level fields records inherit, computed fields) cannot be field names either.

## One schema per build, fixed

A build copies its schema when it starts. Editing or deleting a saved schema afterwards cannot change it, and a build is never re-run against another schema.

## Sharing

Export writes one JSON file: `{"derridai_metadata_schema": 1, "sha256": …, "schema": …}`. Import validates the file like anything typed into an editor; the checksum catches damage or edits after export, and is not a signature.

## API (administrators)

`GET/POST /api/pdf/metadata-schemas`, `GET/PUT/DELETE /api/pdf/metadata-schemas/{id}`, `GET …/{id}/export`, `POST /api/pdf/metadata-schemas/import`.

## Using it

- **Choose one for a build:** step 5 of the build setup ("Metadata schema"). The build keeps its own copy.
- **Edit schemas:** administrators use **System → Metadata schemas**. "Manage schemas…" in Corpus Builder opens the same editor in a dialog, with a link to that page. The editor lists saved schemas, groups and their instructions, fields (type, allowed values with definitions, what the model should look for, evidence, confidence, review), duplicate, delete, export and import. Researcher accounts cannot open the page or change schemas.
- **Try one:** the editor's "Try it on a passage" shows the prompt a group produces, or runs it on a passage with a model. A real build adds the document details, editorial memory and neighbouring records to that prompt.

## What follows the schema

Prompts and the shape of the model's answer; which fields the model may set and which need cited evidence; which fields keep a record from being accepted; what a person may edit and how it is checked; the review panel (fields, labels, controls) and bulk edit; the enrichment dialog's groups. The built-in schema reproduces today's behaviour, and a test compares the prompts it builds with the ones DerridAI has always used.

## Not covered

- Fixed fields that sit outside the schema (the document-level ones records inherit) are unchanged and not configurable.
- A build made before this release has no schema copy and uses the built-in one.
- Metrics and the ledger record fields by name; they do not yet record which schema a build used (the build's `schema_hash` does).
