# DerridAI 0.36.1 — fresh-start SQLite persistence

## Scope

0.36.1 keeps DerridAI's local-first persistence split simple:

- authentication and roles: `derridai-auth.sqlite3`
- system metadata and operation ledger: `derridai-system.sqlite3`
- vector/search collections and Response FAQ cache: Chroma
- browser-only workspace/preferences: IndexedDB/localStorage

This release is intentionally **fresh-install only**. It does not import, transform, rename, or inspect storage from older DerridAI versions. There are no schema-migration tables, versioned migration steps, JSON-to-SQLite conversion routines, or startup `ALTER TABLE` paths.

## System database

Default path:

```text
/data/.home/derridai-system.sqlite3
```

Override with:

```env
SYSTEM_DB_PATH=/data/.home/derridai-system.sqlite3
```

The current schema is created directly on first start:

- `researcher_provider_profiles`
- `annotations`
- `languages`
- `jobs`

SQLite uses WAL journaling, foreign keys, `synchronous=NORMAL`, and a busy timeout. The schema initializer creates the current tables and indexes only.

The built-in locale dictionaries are seeded directly into an empty system database as **English** 🇺🇸 and **Français** 🇨🇦. Once data exists, ordinary restarts leave it unchanged.

## Authentication database

The authentication database also creates its current schema directly on first start. Current user columns, including `last_login` and `login_count`, are part of the initial `CREATE TABLE` statement. There is no startup schema-repair or upgrade path.

## Background operations

LLM review, RAG, LLM-tool/language-translation, and Chroma upsert jobs are mirrored to the `jobs` table while they run. Finished operation history survives API restarts.

A process restart never automatically replays side-effecting work. Jobs left in `queued`, `running`, or `cancelling` are marked `failed` with an `interrupted` event. Language-translation jobs retain validated partial translations so they can be explicitly resumed.

## Backup and restore

Portable full backup remains logical rather than copying live SQLite files. `system.json` is generated from the current repository snapshot, while `operations.json` includes LLM, LLM-tool, RAG, and upsert operation histories.

## Fresh-install contract

Do not point 0.36.1 at databases or system JSON files from an older DerridAI release. Start with a clean data directory (or new database paths). This is deliberate: the release removes upgrade scaffolding so the runtime contains only the schema and behavior required by a new installation.

The repository boundary remains useful for a possible future PostgreSQL backend, but such a change should be implemented as a separate architecture version rather than as dormant migration machinery in the current runtime.
