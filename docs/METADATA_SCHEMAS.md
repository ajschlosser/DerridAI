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

## Status

The schema model, the built-in schema (tested to reproduce today's prompts), generated output shapes, saved schemas, import and export and the API exist. The build pipeline does not read a schema yet, so nothing about a build changes.
