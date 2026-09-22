/* Copyright 2026 Aaron John Schlosser, PhD. */

// Applying, clearing and restoring per-record edits, and the change history behind them. Moved verbatim from the legacy
// runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "cloneAuditValue"
  | "invalidateCorpusCache"
  | "label"
  | "openMessageModal"
  | "persistFile"
  | "renderView"
  | "sameValue"
  | "shell"
  | "toast"
  | "uid";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createRecordEditing(deps: Deps) {
  const {
    state,
    allRows,
    cloneAuditValue,
    invalidateCorpusCache,
    label,
    openMessageModal,
    persistFile,
    renderView,
    sameValue,
    shell,
    toast,
    uid,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  function applyRecordChanges(
    file: Any,
    index: Any,
    changes: Any,
    { source = "manual", model = null, batchId = null, rationale = null }: Any = {},
  ) {
    const current = file.records[index];
    if (!current) return 0;
    const pending: Any = {};
    for (const [field, newValue] of Object.entries(changes || {})) {
      if (field === "updates") continue;
      if (!sameValue(current[field], newValue)) pending[field] = newValue;
    }
    if ("text" in pending && "text_length" in current && !("text_length" in pending)) {
      const length = String(pending.text ?? "").length;
      if (!sameValue(current.text_length, length)) pending.text_length = length;
    }
    const entries = Object.entries(pending);
    if (!entries.length) return 0;
    const timestamp = new Date().toISOString();
    const operationId = batchId || uid();
    const history = Array.isArray(current.updates) ? current.updates.map(cloneAuditValue) : [];
    const next = { ...current };
    for (const [field, newValue] of entries) {
      const entry: Any = {
        field_name: field,
        old_value: cloneAuditValue(current[field]),
        new_value: cloneAuditValue(newValue),
        timestamp,
        source,
        batch_id: operationId,
        initiated_by: state.userContext?.username || null,
      };
      if (model) entry.model = model;
      if (rationale?.[field]) entry.reason = String(rationale[field]);
      history.push(entry);
      next[field] = newValue;
    }
    next.updates = history;
    file.records[index] = next;
    file.dirty.add(index);
    invalidateCorpusCache();
    persistFile(file);
    if (state.view === "record" && typeof window !== "undefined")
      window.dispatchEvent(new CustomEvent("derridai:record-updated"));
    return entries.length;
  }
  async function clearRecordUpdates(file: Any, index: Any, { confirmFirst = true } = {}) {
    const record = file?.records?.[index];
    const count = Array.isArray(record?.updates) ? record.updates.length : 0;
    if (!record || !count) {
      toast("This record has no updates history");
      return false;
    }
    if (
      confirmFirst &&
      !(await openMessageModal({
        title: "Clear record update history?",
        message: `Clear all ${count} updates entries from ${record.record_id || `record ${index + 1}`}? This history cannot be reconstructed automatically.`,
        tone: "danger",
        confirmLabel: "Clear history",
        cancelLabel: "Cancel",
      }))
    )
      return false;
    file.records[index] = { ...record, updates: [] };
    file.dirty.add(index);
    persistFile(file);
    return true;
  }
  async function clearAllUpdates({ confirmed = false } = {}) {
    const rows = allRows().filter(
      (row: Any) => Array.isArray(row.record.updates) && row.record.updates.length,
    );
    if (!rows.length) return toast("No loaded records have updates history");
    const entries = rows.reduce((sum: Any, row: Any) => sum + row.record.updates.length, 0);
    if (
      !confirmed &&
      !(await openMessageModal({
        title: "Clear all update histories?",
        message: `Clear ${entries.toLocaleString()} updates entries from ${rows.length.toLocaleString()} loaded records? This permanently removes the local audit histories.`,
        tone: "danger",
        confirmLabel: "Clear all histories",
        cancelLabel: "Cancel",
      }))
    )
      return;
    const files = new Set();
    for (const row of rows) {
      row.file.records[row.index] = { ...row.record, updates: [] };
      row.file.dirty.add(row.index);
      files.add(row.file);
    }
    for (const file of files) persistFile(file);
    shell();
    renderView();
    toast(`Cleared updates history from ${rows.length.toLocaleString()} records`);
  }
  function historyVersionChanges(previous: Any, current: Any) {
    const keys = new Set([...Object.keys(previous || {}), ...Object.keys(current || {})]);
    return [...keys]
      .filter(
        (key) =>
          key !== "updates" && !key.startsWith("_") && !sameValue(previous?.[key], current?.[key]),
      )
      .sort((a, b) => label(a).localeCompare(label(b)));
  }
  function restoreRecordHistoryVersion(file: Any, index: Any, version: Any) {
    const current = file?.records?.[index];
    if (!current || !version?.record) return 0;
    const keys = new Set([...Object.keys(current), ...Object.keys(version.record)]);
    const changes: Any = {};
    for (const field of keys) {
      if (field === "updates" || field.startsWith("_")) continue;
      const value = Object.prototype.hasOwnProperty.call(version.record, field)
        ? cloneAuditValue(version.record[field])
        : null;
      if (!sameValue(current[field], value)) changes[field] = value;
    }
    return applyRecordChanges(file, index, changes, {
      source: "history_restore",
      batchId: uid(),
      rationale: Object.fromEntries(
        Object.keys(changes).map((field) => [field, `Restored from ${version.label}`]),
      ),
    });
  }
  return {
    applyRecordChanges,
    clearRecordUpdates,
    clearAllUpdates,
    historyVersionChanges,
    restoreRecordHistoryVersion,
  };
}
