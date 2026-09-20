/* Copyright 2026 Aaron John Schlosser, PhD. */
import { cloneAuditValue } from "./recordValues";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Audit-history helpers for corpus records, moved verbatim from the legacy runtime.

export function recordHistoryVersions(record: Loose | null | undefined) {
  const updates = Array.isArray(record?.updates) ? record.updates : [];
  const cleanSnapshot = (value: unknown): Loose => {
    const copy = (cloneAuditValue(value) || {}) as Loose;
    if (copy && typeof copy === "object") delete copy.updates;
    return copy;
  };
  const baseline = cleanSnapshot(record);
  for (let index = updates.length - 1; index >= 0; index--) {
    const update = updates[index] || {};
    if (!update.field_name) continue;
    baseline[update.field_name] = cloneAuditValue(update.old_value);
  }
  const versions: Loose[] = [
    {
      index: 0,
      label: "Original",
      timestamp: null,
      source: "original",
      changes: [],
      record: cleanSnapshot(baseline),
    },
  ];
  const groups: Array<{ key: string; items: Loose[] }> = [];
  for (let index = 0; index < updates.length; index++) {
    const update = updates[index] || {};
    const key = update.batch_id || update.timestamp || `change-${index}`;
    const previous = groups.at(-1);
    if (previous && previous.key === key) previous.items.push(update);
    else groups.push({ key, items: [update] });
  }
  let snapshot = cleanSnapshot(baseline);
  for (const group of groups) {
    snapshot = cleanSnapshot(snapshot);
    for (const update of group.items) {
      if (update?.field_name) snapshot[update.field_name] = cloneAuditValue(update.new_value);
    }
    const last = group.items.at(-1) || {};
    versions.push({
      index: versions.length,
      label: `Version ${versions.length}`,
      timestamp: last.timestamp || null,
      source: last.source || "manual",
      model: last.model || null,
      changes: group.items,
      record: cleanSnapshot(snapshot),
    });
  }
  return versions;
}

export function upsertAuditDelta(
  record: Loose | null | undefined,
  receipt: Loose | null | undefined,
  presence: boolean | undefined,
) {
  const updates = Array.isArray(record?.updates) ? record.updates : [];
  const updatesCount = updates.length;
  if (
    receipt &&
    receipt.updates_count !== null &&
    receipt.updates_count !== undefined &&
    Number.isInteger(Number(receipt.updates_count))
  ) {
    const previousCount = Math.max(0, Number(receipt.updates_count));
    if (updatesCount < previousCount) {
      return {
        audit_entries: [],
        replace_updates: updates.map(cloneAuditValue),
        updates_count: updatesCount,
      };
    }
    if (updatesCount > previousCount) {
      return {
        audit_entries: updates.slice(previousCount).map(cloneAuditValue),
        replace_updates: null,
        updates_count: updatesCount,
      };
    }
    return { audit_entries: [], replace_updates: null, updates_count: updatesCount };
  }
  // Upgrade path for receipts created before 0.30.11: use the receipt timestamp
  // to send only audit entries created after the last successful sync.
  if (receipt?.timestamp) {
    const syncedAt = Date.parse(receipt.timestamp);
    if (Number.isFinite(syncedAt)) {
      const delta = updates.filter((entry) => {
        const timestamp = Date.parse(entry?.timestamp || "");
        return Number.isFinite(timestamp) && timestamp > syncedAt;
      });
      return {
        audit_entries: delta.map(cloneAuditValue),
        replace_updates: null,
        updates_count: updatesCount,
      };
    }
  }
  // A genuinely new Chroma row needs its existing local history initialized
  // once. Existing rows with no receipt preserve their server-side history.
  if (presence === false && updatesCount) {
    return {
      audit_entries: [],
      replace_updates: updates.map(cloneAuditValue),
      updates_count: updatesCount,
    };
  }
  return { audit_entries: [], replace_updates: null, updates_count: updatesCount };
}
