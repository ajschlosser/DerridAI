# DerridAI 0.36.2: shareable state and corpus data model

> Historical release design note. This records the 0.36.2 state/data-model contract. For current behavior, use [ARCHITECTURE.md](ARCHITECTURE.md) and [USER_GUIDE.md](USER_GUIDE.md).

## URL state

DerridAI treats the URL as the public/shareable description of a view. The `ts`
query parameter is a compact encoded object containing the state relevant to the
current page: filters, search text, sort order, pagination, column selection,
search mode and database-search configuration where applicable. Native/legacy
breadcrumbs snapshot the same view state so Back restores the page the user
actually left rather than just its route name.

For browser-local JSONL workspaces, a file identity is derived from SHA-256 of
the source file contents. Two users who load the identical JSONL file therefore
receive the same `file=` identity and can use the same Records URL. If a shared
Records URL is opened before its source JSONL is loaded, DerridAI shows the
workspace loader; loading the matching file applies the pending URL state.

The URL deliberately does **not** contain the JSONL document itself. Shareable
view state is small; corpus data is not. A recipient of a local-JSONL Records
link must have or load the same JSONL source. A link to a server-backed corpus
database instead resolves against the common server collection.

## JSONL record

A JSONL record is one parsed JSON object from a loaded JSONL file. It is the
editable source object used by the browser workspace. Local edits mutate this
workspace copy and append to the record's `updates` history where the editing
workflow requires provenance. Records are persisted browser-side as part of
their JSONL workspace so the local editing session can survive a refresh.

## JSONL file

A JSONL file is the browser-workspace container for many JSONL records. DerridAI
parses the file line by line (or accepts a JSON array), retains its filename,
parse issues, records and dirty state, and stores that workspace in IndexedDB.
A JSONL file is not itself a Chroma collection and loading it does not upload its
records to the server corpus database.

In 0.36.2 newly loaded files use a content-derived identity rather than a random
UUID. That identity is what makes a Records URL portable between browsers once
the same file is present on both sides.

## Database record

A database record is the server-side corpus representation created by an
explicit upsert/sync operation. Corpus database records live in Chroma, with a
Chroma identifier, document text, flattened metadata and embedding/vector state.
They are not a live reference to their originating browser JSONL object. Editing
a JSONL record does not modify the database copy until it is synced again, and
editing a database record does not rewrite a local source file unless a separate
workflow explicitly does so.

`DB status` in the Records workspace exists to make this boundary visible: it
compares the local source record with the selected corpus database and reports
whether a database copy is absent, current, or needs synchronization.

## Where SQLite fits

SQLite in the 0.36.x architecture is the durable application/system store, not
the corpus-record store. It holds system/application data such as provider
profiles, annotations, installed language dictionaries and durable background
jobs. Authentication uses its own SQLite database. Chroma remains responsible
for corpus database records and vectors; IndexedDB/localStorage remain
responsible for browser-local workspace/preferences.
