/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc } from "./html";

// Whether a record already exists in a vector database (presence), and the pending-upsert queue and command that syncs
// records into one. Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in as
// dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "api"
  | "candidateChromaIds"
  | "corpusStoreExists"
  | "dbUnavailableReason"
  | "formatTimestamp"
  | "hasCorpusDb"
  | "localRecordKey"
  | "notifyVectorStoresChanged"
  | "openMessageModal"
  | "persistPrefs"
  | "recordFingerprint"
  | "refreshOperationsPanelOnly"
  | "reviewItemFromKey"
  | "selectedReviewItems"
  | "startJobPolling"
  | "storeReceipt"
  | "syncJobProgressToasts"
  | "toast"
  | "tr"
  | "trf"
  | "upsertAuditDelta"
  | "upsertRecordPayload"
  | "workIndex";
type Deps = { state: Loose; corpusCache: Loose } & Record<Helper, Fn>;

let pendingUpsertCache: Any = { key: "", at: 0, rows: [] };
export function createDbPresenceUpsert(deps: Deps) {
  const {
    state,
    allRows,
    api,
    candidateChromaIds,
    corpusCache,
    corpusStoreExists,
    dbUnavailableReason,
    formatTimestamp,
    hasCorpusDb,
    localRecordKey,
    notifyVectorStoresChanged,
    openMessageModal,
    persistPrefs,
    recordFingerprint,
    refreshOperationsPanelOnly,
    reviewItemFromKey,
    selectedReviewItems,
    startJobPolling,
    storeReceipt,
    syncJobProgressToasts,
    toast,
    tr,
    trf,
    upsertAuditDelta,
    upsertRecordPayload,
    workIndex,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function recordDbStatus(file: Any, index: Any, record: Any, store = state.activeStore) {
    if (!hasCorpusDb()) return { kind: "none", label: "No database", title: dbUnavailableReason() };
    if (!store)
      return { kind: "none", label: "No collection", title: "Select a Chroma collection" };
    if (!corpusStoreExists(store))
      return {
        kind: "none",
        label: "No collection",
        title: "The selected collection no longer exists",
      };
    const key = localRecordKey(file, index);
    const receipt = state.upsertState?.[store]?.[key] || null;
    const presence = state.storePresence?.[store]?.[key];
    const fingerprint = recordFingerprint(record);
    if (receipt && receipt.fingerprint === fingerprint && presence !== false)
      return {
        kind: "synced",
        label: "Synced",
        title: `Upserted ${formatTimestamp(receipt.timestamp)}`,
      };
    if (receipt && receipt.fingerprint !== fingerprint)
      return { kind: "changed", label: "Pending", title: "Changed since last upsert" };
    if (presence === true)
      return {
        kind: "exists",
        label: "In DB",
        title: "Record exists in the selected collection; local sync time is unknown",
      };
    if (presence === false)
      return {
        kind: "absent",
        label: "Not in DB",
        title: "Record was not found in the selected collection",
      };
    return {
      kind: "unknown",
      label: "Unknown",
      title: "Database presence has not been checked yet",
    };
  }
  function workDbStatus(rows: Any, workName = null) {
    if (!hasCorpusDb()) return { kind: "none", label: "No database" };
    if (!state.activeStore) return { kind: "none", label: "No collection" };
    if (!corpusStoreExists(state.activeStore)) return { kind: "none", label: "No collection" };
    const receipts = rows.map(
      (row: Any) =>
        state.upsertState?.[state.activeStore]?.[localRecordKey(row.file, row.index)] || null,
    );
    if (
      rows.some(
        (row: Any, index: Any) =>
          receipts[index] && receipts[index].fingerprint !== recordFingerprint(row.record),
      )
    )
      return { kind: "changed", label: "Pending changes" };
    if (
      rows.length &&
      rows.every(
        (row: Any, index: Any) => receipts[index]?.fingerprint === recordFingerprint(row.record),
      )
    )
      return { kind: "synced", label: "Synced" };
    if (state.storeWorksStore === state.activeStore) {
      const name = workName ?? String(rows[0]?.record?.work || "(Untitled work)");
      const stat = (state.storeWorkStats || []).find(
        (item: Any) => String(item.work || "(Untitled work)") === String(name),
      );
      const dbCount = Number(stat?.count || 0);
      if (dbCount >= rows.length && rows.length) return { kind: "exists", label: "In DB" };
      if (dbCount > 0) return { kind: "exists", label: `Partly in DB (${dbCount}/${rows.length})` };
      return { kind: "absent", label: "Not in DB" };
    }
    return { kind: "unknown", label: "DB status loading" };
  }
  async function refreshPresenceForRows(rows: Any, { force = false } = {}) {
    const store = state.activeStore;
    if (!hasCorpusDb() || !store || !rows.length) return;
    if (!state.storePresence[store]) state.storePresence[store] = {};
    if (!state.storePresenceIds[store]) state.storePresenceIds[store] = {};
    if (!state.storePresenceCheckedAt[store]) state.storePresenceCheckedAt[store] = {};
    const now = Date.now(),
      ttl = 15000;
    const staleRows = force
      ? rows
      : rows.filter(
          (row: Any) =>
            now -
              Number(
                state.storePresenceCheckedAt[store][localRecordKey(row.file, row.index)] || 0,
              ) >
            ttl,
        );
    if (!staleRows.length) return;
    const ids = [
      ...new Set(
        staleRows.flatMap((row: Any) => candidateChromaIds(row.file, row.index, row.record)),
      ),
    ];
    if (!ids.length) return;
    const found = new Set();
    try {
      for (let start = 0; start < ids.length; start += 500) {
        const data = await api(`/api/stores/${encodeURIComponent(store)}/records/status`, {
          method: "POST",
          body: JSON.stringify({ ids: ids.slice(start, start + 500) }),
        });
        for (const id of data.existing_ids || []) found.add(id);
      }
      for (const row of staleRows) {
        const key = localRecordKey(row.file, row.index);
        const candidates = candidateChromaIds(row.file, row.index, row.record);
        const matchedId = candidates.find((id: Any) => found.has(id)) || "";
        state.storePresence[store][key] = Boolean(matchedId);
        state.storePresenceIds[store][key] = matchedId;
        state.storePresenceCheckedAt[store][key] = now;
      }
      pendingUpsertCache.key = "";
      updateDbStatusElements();
    } catch (error: Any) {
      console.warn("Could not refresh Chroma presence", error);
    }
  }
  function updateDbStatusElements() {
    document.querySelectorAll("[data-db-status-key]").forEach((el: Any) => {
      const item = reviewItemFromKey(el.dataset.dbStatusKey);
      if (!item) return;
      const info = recordDbStatus(item.file, item.index, item.file.records[item.index]);
      el.className = `db-status ${info.kind}`;
      el.title = info.title;
      el.innerHTML = `<i></i>${esc(info.label)}`;
    });
    document.querySelectorAll("[data-work-status]").forEach((el: Any) => {
      const work = el.dataset.workStatus;
      const rows = workIndex().get(work)?.rows || [];
      const info = workDbStatus(rows, work);
      el.className = `db-status ${info.kind}`;
      el.innerHTML = `<i></i>${esc(info.label)}`;
    });
  }
  function ignoredFingerprint(store: Any, file: Any, index: Any) {
    return state.upsertIgnored?.[store]?.[localRecordKey(file, index)] || null;
  }
  function pendingUpsertRows() {
    if (!hasCorpusDb() || !state.activeStore) return [];
    const dirtyCount = state.files.reduce(
      (sum: Any, file: Any) => sum + (file.dirty?.size || 0),
      0,
    );
    const key = `${state.activeStore}|${corpusCache.version}|${dirtyCount}|${Number(state.upsertJobApplied ? Object.values(state.upsertJobApplied).reduce((a: Any, b) => a + Number(b || 0), 0) : 0)}`;
    const now = performance.now();
    if (pendingUpsertCache.key === key && now - pendingUpsertCache.at < 750)
      return pendingUpsertCache.rows;
    const rows = allRows().filter((row: Any) => {
      const fingerprint = recordFingerprint(row.record);
      if (ignoredFingerprint(state.activeStore, row.file, row.index) === fingerprint) return false;
      const info = recordDbStatus(row.file, row.index, row.record);
      return (
        info.kind === "changed" ||
        info.kind === "absent" ||
        (row.file.dirty.has(row.index) && info.kind !== "synced")
      );
    });
    pendingUpsertCache = { key, at: now, rows };
    return rows;
  }
  function pendingChangesForRow(row: Any) {
    const store = state.activeStore;
    const receipt = storeReceipt(store, row.file, row.index);
    const since = receipt?.timestamp ? new Date(receipt.timestamp).getTime() : 0;
    const updates = Array.isArray(row.record.updates) ? row.record.updates : [];
    const changed = updates.filter((update: Any) => {
      const time = new Date(update.timestamp || 0).getTime();
      return !since || Number.isNaN(time) || time > since;
    });
    if (changed.length) return changed;
    if (!receipt)
      return [
        {
          field_name: "record",
          old_value: null,
          new_value: "Not previously upserted from this workspace",
          source: "workspace",
          timestamp: null,
        },
      ];
    return [
      {
        field_name: "record",
        old_value: "Last upserted fingerprint",
        new_value: "Current record differs",
        source: "fingerprint",
        timestamp: null,
      },
    ];
  }
  function removeFromUpsertQueue(row: Any) {
    const store = state.activeStore;
    if (!store) return;
    if (!state.upsertIgnored[store]) state.upsertIgnored[store] = {};
    state.upsertIgnored[store][localRecordKey(row.file, row.index)] = recordFingerprint(row.record);
    persistPrefs();
  }
  async function buildUpsertItems(rows: Any, store: Any, { yieldEvery = 0 } = {}) {
    const idCounts = new Map();
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i],
        id = String(row.file.records[row.index]?.record_id ?? "");
      idCounts.set(id, (idCounts.get(id) || 0) + 1);
      if (yieldEvery && i && i % yieldEvery === 0)
        await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
    }
    const items = [];
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i],
        current = row.file.records[row.index],
        logical = String(current?.record_id ?? ""),
        receipt = storeReceipt(store, row.file, row.index),
        chromaId =
          receipt?.chroma_id ||
          ((idCounts.get(logical) || 0) > 1 ? `${row.file.name}::${logical}` : logical);
      const key = localRecordKey(row.file, row.index);
      const audit = upsertAuditDelta(current, receipt, state.storePresence?.[store]?.[key]);
      items.push({
        key,
        record: current,
        fingerprint: recordFingerprint(current),
        chroma_id: chromaId,
        file_name: row.file.name,
        ...audit,
      });
      if (yieldEvery && i && i % yieldEvery === 0)
        await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
    }
    return items;
  }
  async function upsertRows(rows: Any, labelText = "records", { largeSyncConfirmed = false } = {}) {
    if (!hasCorpusDb())
      return openMessageModal({
        title: "Vector database required",
        message: dbUnavailableReason(),
        confirmLabel: "OK",
      });
    if (!state.activeStore) return toast("Select a Chroma collection first");
    if (!rows.length) return toast("No records selected for upsert");
    const activeUpsert = state.jobs.find(
      (job: Any) =>
        job.type === "upsert" && ["queued", "running", "cancelling"].includes(job.status),
    );
    if (activeUpsert)
      return openMessageModal({
        title: tr("operations.vector_sync_active_title", "A vector sync is already active"),
        message: trf(
          "operations.vector_sync_active_help",
          "{label} must finish or be cancelled before another collection build starts.",
          { label: activeUpsert.label || activeUpsert.store_name || "The current sync" },
        ),
        confirmLabel: "OK",
      });
    const store = state.activeStore;
    await refreshPresenceForRows(rows, { force: true });
    if (rows.length > 500 && !largeSyncConfirmed) {
      const approved = await openMessageModal({
        title: tr("operations.large_sync_background_title", "Build collection in the background?"),
        message: trf(
          "operations.large_sync_background_help",
          "{count} records will be prepared once, then DerridAI will build and validate the collection as a background operation. You may continue working in this tab while the build runs.",
          { count: rows.length.toLocaleString() },
        ),
        confirmLabel: tr("operations.start_background_build", "Start background build"),
        cancelLabel: tr("ui.cancel", "Cancel"),
      });
      if (!approved) return false;
    }
    const items = await buildUpsertItems(rows, store, { yieldEvery: rows.length > 500 ? 80 : 0 });
    try {
      const transportItems = items.map((item) => ({
        key: item.key,
        record: upsertRecordPayload(item.record),
        fingerprint: item.fingerprint,
        chroma_id: item.chroma_id,
        file_name: item.file_name,
        audit_entries: item.audit_entries || [],
        replace_updates: item.replace_updates,
        updates_count: item.updates_count,
      }));
      const sourceWorks = [
        ...new Set(
          rows
            .map((row: Any) =>
              String(row.record?.work || row.file?.records?.[row.index]?.work || "").trim(),
            )
            .filter(Boolean),
        ),
      ];
      const job = await api("/api/jobs/upsert", {
        method: "POST",
        body: JSON.stringify({
          store_name: store,
          items: transportItems,
          document_field: "text",
          embedding_field: "embedding",
          batch_size: 500,
          mirror_languages: true,
          label: labelText,
          source_kind: "browser_workspace",
          source_label: labelText,
          source_works: sourceWorks,
        }),
      });
      state.jobs = [job, ...state.jobs.filter((existing: Any) => existing.id !== job.id)];
      syncJobProgressToasts();
      startJobPolling();
      toast(
        trf(
          "operations.vector_build_queued",
          "Queued {count} records for background build of {store}",
          { count: rows.length.toLocaleString(), store },
        ),
        { tone: "success" },
      );
      notifyVectorStoresChanged();
      if (state.view === "home") refreshOperationsPanelOnly();
      return true;
    } catch (error: Any) {
      toast(`Could not start vector build: ${error.message}`);
      return false;
    }
  }
  function rowsFromReviewSelection() {
    return selectedReviewItems().map((item: Any) => ({
      file: item.file,
      record: item.file.records[item.index],
      index: item.index,
    }));
  }
  return {
    recordDbStatus,
    workDbStatus,
    refreshPresenceForRows,
    updateDbStatusElements,
    ignoredFingerprint,
    pendingUpsertRows,
    pendingChangesForRow,
    removeFromUpsertQueue,
    buildUpsertItems,
    upsertRows,
    rowsFromReviewSelection,
  };
}
