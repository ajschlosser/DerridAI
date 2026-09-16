# 0.30.11 packet discipline — ONLY SEND WHAT IS NEEDED

0.30.11 treats large record objects as **storage objects**, not universal transport objects. API operations now use purpose-specific payloads and omit audit history unless the operation explicitly changes or exports that history.

## Record history rule

`updates` is opt-in at API boundaries.

- Record list/search responses omit `updates` and may expose `_updates_count` instead.
- Single-record reads omit `updates` by default. Admin callers must explicitly request `include_updates=true` when they need history.
- New/sync upserts omit the full `updates` array by default. Chroma preserves existing history server-side and accepts only newly appended audit entries. A full replacement is used only when history itself is explicitly initialized, cleared, or replaced.
- Clearing/replacing history is explicit: include `updates` in the record and opt in with `include_updates=true`.
- Full corpus exports are an explicit history-bearing operation and retain `updates`.
- Researcher responses never receive the raw history.

## Operation-specific transports

| Operation | Transport | Deliberately omitted |
| --- | --- | --- |
| Chroma edit | `PATCH {changes, audit_entries}` | Unchanged fields, existing `updates` history |
| LLM touchup | Selected review fields + small provenance/context field set | `updates`, unrelated record metadata |
| RAG selected DB evidence | `{collection, chroma_id}` | Entire record; server rehydrates it |
| RAG selected workspace evidence | Evidence/provenance field projection | `updates`, UI-only/private fields |
| RAG grading | Evidence id/citations + `{record_id, work, text}` | Full record metadata, `updates` |
| Upsert | Record minus `updates` + only unsynced `audit_entries` when needed | Historical audit entries already stored server-side |
| RAG job summary | Selected-evidence references | Duplicated full selected records |
| Response cache | Nested records compacted before storage/serving | Nested `updates` histories |
| Explicit export/history | Full record | Nothing required for fidelity |

## Sparse Chroma edits

The Chroma record editor no longer fetches and resubmits a whole record merely to change one field. It computes changed fields in the browser and sends:

```json
{
  "changes": {
    "speaker": "Jacques Derrida"
  },
  "audit_entries": [
    {
      "field_name": "speaker",
      "old_value": null,
      "new_value": "Jacques Derrida",
      "timestamp": "...",
      "source": "chroma_editor"
    }
  ],
  "document_field": "text",
  "embedding_field": "embedding"
}
```

The API loads the authoritative stored record and existing audit trail, applies the sparse changes, appends the new audit entries, and writes the result. Existing history therefore stays server-side for the entire edit.

## Compatibility

Legacy full-record `PUT` remains available. Unless `include_updates=true` is explicitly set, the API preserves the existing stored audit trail even if the client does not send it. This prevents older clients from accidentally deleting history while keeping 0.30.11 clients on the sparse `PATCH` path.

## Fingerprints and retained jobs

Record synchronization fingerprints exclude `updates` and `_updates_count`: appending an audit entry does not make an otherwise unchanged record appear semantically out of sync. RAG job summaries retain only lightweight selected-evidence references; the pipeline still receives the evidence required for execution, but completed-job metadata no longer duplicates full record objects.
