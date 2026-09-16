# DerridAI 0.36.0 — SQLite persistence architecture

## Scope

0.36.0 moves server-owned application metadata and important background-operation state into SQLite while deliberately leaving the two storage systems that already fit their jobs in place:

- authentication/roles: `derridai-auth.sqlite3`
- system metadata + operation ledger: `derridai-system.sqlite3`
- vector/search collections and Response FAQ cache: Chroma
- browser-only workspace/preferences: IndexedDB/localStorage

Redis is not introduced. It would add deployment and failure modes without solving DerridAI's present durable-relational storage need. PostgreSQL remains a future multi-user/server deployment option behind the repository boundary.

## System database

Default path:

```text
/data/.home/derridai-system.sqlite3
```

Override with:

```env
SYSTEM_DB_PATH=/data/.home/derridai-system.sqlite3
```

Tables are intentionally small and explicit:

- `schema_migrations`
- `system_meta`
- `researcher_provider_profiles`
- `annotations`
- `languages`
- `jobs`

SQLite runs with WAL journaling, foreign keys, `synchronous=NORMAL`, and a busy timeout. Job and annotation lookup indexes are created during schema initialization.

## Legacy migration

On first 0.36.0 startup, if the SQLite system store has no application data and a legacy `derridai-system.json` exists beside it, DerridAI:

1. parses the legacy payload;
2. writes the complete payload to SQLite in one transaction;
3. verifies success by completing the transaction;
4. renames the source to `derridai-system.migrated-v0.36.0.json` when the filesystem permits.

If the rename is not permitted, the old JSON file is left untouched; SQLite is still the active store. The JSON file is never used as the ongoing source of truth after a populated SQLite store exists.

## Background operations

LLM review, RAG, LLM-tool/language-translation, and Chroma upsert jobs keep an in-process working copy while executing, but every operation is mirrored to the `jobs` table and checkpointed during execution. Finished operation history therefore survives API restarts.

A process restart never automatically replays a side-effecting job. Any job left in `queued`, `running`, or `cancelling` is marked `failed` with an `interrupted` event on startup. This preserves an auditable state boundary and avoids duplicate writes or duplicate model calls.

Language translation is special because it is safely resumable. Validated partial translations and failed-key checkpoints are persisted server-side after translation batches. After a restart, the interrupted operation can be explicitly resumed from that retained partial dictionary.

## Backup and restore

The portable full-backup format remains logical rather than copying live SQLite files. `system.json` is still generated from the repository snapshot for backward-compatible backup portability. `operations.json` now includes:

- `llm`
- `llm_tool`
- `rag`
- `upsert`

This means incomplete/resumable language translation operations are now included in full backups as well.

## PostgreSQL path

Application code should depend on repository methods rather than SQLite SQL outside `persistence.py`. A future PostgreSQL backend can implement the same system/job repository contracts while leaving the current API and manager behavior largely unchanged. Chroma/pgvector consolidation, if ever desired, should remain a separate migration with its own benchmarks and rollback plan.
