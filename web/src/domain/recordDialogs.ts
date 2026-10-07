/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { recordEditorField } from "./recordEditorFields";
import { createRecordDialogCopy } from "./recordDialogCopy";
import { openBulkFieldEditorDialog } from "../composables/bulkFieldEditorDialog";
import { openMergeFilesDialog } from "../composables/mergeFilesDialog";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { openOcrCleanupDialog as openOcrCleanupDialogHost } from "../composables/ocrCleanupDialog";
import { openRecordFieldEditorDialog } from "../composables/recordFieldEditorDialog";
import { openUpsertQueueDialog } from "../composables/upsertQueueDialog";
import { openRecordHistoryDialog } from "../composables/recordHistoryDialog";

// The dialogs for editing, merging, subsetting and cleaning records and for the upsert queue, drawn as HTML strings. Moved
// verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "allRows"
  | "api"
  | "applyRecordChanges"
  | "bulkEditRowsForScope"
  | "cleanRows"
  | "clearRecordUpdates"
  | "cloneAuditValue"
  | "dbUnavailableReason"
  | "download"
  | "fileJsonl"
  | "formatTimestamp"
  | "hasCorpusDb"
  | "historyVersionChanges"
  | "idbDelete"
  | "invalidateCorpusCache"
  | "jsonPretty"
  | "label"
  | "localRecordKey"
  | "navigateTo"
  | "needsReviewItems"
  | "parseBulkFieldValue"
  | "pendingChangesForRow"
  | "pendingUpsertRows"
  | "persistFileNow"
  | "persistCorpusPreferences"
  | "persistJobPreferences"
  | "persistListPreferences"
  | "persistReviewPreferences"
  | "recordDbStatus"
  | "recordFields"
  | "recordHistoryVersions"
  | "refreshPresenceForRows"
  | "removeFromUpsertQueue"
  | "renderView"
  | "restoreRecordHistoryVersion"
  | "sameValue"
  | "selectedRecord"
  | "selectedReviewItems"
  | "shell"
  | "tr"
  | "trf"
  | "uid"
  | "upsertRows";
type Deps = { state: Loose; fileTimers: Map<string, ReturnType<typeof setTimeout>> } & Record<
  Helper,
  Fn
>;

export function createRecordDialogs(deps: Deps) {
  const {
    state,
    activeFile,
    allRows,
    api,
    applyRecordChanges,
    bulkEditRowsForScope,
    cleanRows,
    clearRecordUpdates,
    cloneAuditValue,
    dbUnavailableReason,
    download,
    fileJsonl,
    fileTimers,
    formatTimestamp,
    hasCorpusDb,
    historyVersionChanges,
    idbDelete,
    invalidateCorpusCache,
    jsonPretty,
    label,
    localRecordKey,
    navigateTo,
    needsReviewItems,
    parseBulkFieldValue,
    pendingChangesForRow,
    pendingUpsertRows,
    persistFileNow,
    persistCorpusPreferences,
    persistJobPreferences,
    persistListPreferences,
    persistReviewPreferences,
    recordDbStatus,
    recordFields,
    recordHistoryVersions,
    refreshPresenceForRows,
    removeFromUpsertQueue,
    renderView,
    restoreRecordHistoryVersion,
    sameValue,
    selectedRecord,
    selectedReviewItems,
    shell,
    tr,
    trf,
    uid,
    upsertRows,
  } = deps;
  const copy = createRecordDialogCopy(tr, trf);
  function openMergeDialog() {
    if (state.files.length < 2) return toast(copy.mergeNeedTwo, { tone: "warning" });
    openMergeFilesDialog({
      files: state.files.map((file: Any) => ({
        id: String(file.id),
        name: String(file.name),
        recordCount: file.records.length,
      })),
      defaultName: "derridai-merged.jsonl",
      merge: async ({ fileIds: ids, name: rawName, download: wantsDownload }) => {
        const files = state.files.filter((file: Any) => ids.includes(file.id));
        if (!files.length) {
          toast(copy.selectFile, { tone: "warning" });
          return false;
        }
        const firstIndex = Math.min(...files.map((file: Any) => state.files.indexOf(file)));
        const name = (rawName.trim() || "derridai-merged.jsonl").replace(/\s+/g, "-");
        const records = files.flatMap((file: Any) =>
          file.records.map((record: Any) => cloneAuditValue(record)),
        );
        const merged = {
          id: uid(),
          name: name.endsWith(".jsonl") ? name : `${name}.jsonl`,
          records,
          errors: files.flatMap((file: Any) => file.errors || []),
          dirty: new Set(records.map((_: Any, index: Any) => index)),
          imported_at: new Date().toISOString(),
          merged_from: files.map((file: Any) => file.name),
        };

        const removedIds = new Set<Any>(files.map((file: Any) => file.id));
        state.files = state.files.filter((file: Any) => !removedIds.has(file.id));
        state.files.splice(firstIndex, 0, merged);

        for (const id of removedIds) {
          delete state.selected[id];
          delete state.searches[id];
          delete state.pages[id];
          delete state.sorts[id];
          if (fileTimers.has(id)) {
            clearTimeout(fileTimers.get(id));
            fileTimers.delete(id);
          }
          await idbDelete("files", id).catch((error: Any) =>
            console.error("Could not remove merged source tab from IndexedDB", error),
          );
        }
        state.reviewSelection = new Set(
          [...state.reviewSelection].filter((key) => !removedIds.has(String(key).split("::")[0])),
        );
        for (const store of Object.keys(state.upsertState || {})) {
          for (const key of Object.keys(state.upsertState[store] || {})) {
            if (removedIds.has(String(key).split("::")[0])) delete state.upsertState[store][key];
          }
        }
        for (const store of Object.keys(state.upsertIgnored || {})) {
          for (const key of Object.keys(state.upsertIgnored[store] || {})) {
            if (removedIds.has(String(key).split("::")[0])) delete state.upsertIgnored[store][key];
          }
        }
        for (const bucket of [state.storePresence, state.storePresenceIds]) {
          for (const store of Object.keys(bucket || {})) {
            for (const key of Object.keys(bucket[store] || {})) {
              if (removedIds.has(String(key).split("::")[0])) delete bucket[store][key];
            }
          }
        }

        invalidateCorpusCache(merged.id, true);
        await persistFileNow(merged);
        state.activeFileId = merged.id;
        if (wantsDownload) download(merged.name, fileJsonl(merged));
        persistCorpusPreferences();
        persistListPreferences();
        persistReviewPreferences();
        persistJobPreferences();
        navigateTo("list", { fileId: merged.id });
        toast(copy.merged(files.length, records.length.toLocaleString()), { tone: "success" });
        return true;
      },
    });
  }
  function openBulkFieldEditor({ rows = null, title = copy.bulkEditTitle } = {}) {
    if (!state.files.length) return toast(copy.loadFirst, { tone: "warning" });
    const fixedRows: Any = Array.isArray(rows) ? rows : null;
    const selectedCount = selectedReviewItems().length;
    const rowsFor = (scope: string) => fixedRows || bulkEditRowsForScope(scope || "active");
    openBulkFieldEditorDialog({
      title,
      fixedCount: fixedRows ? fixedRows.length : null,
      defaultScope: fixedRows ? "fixed" : selectedCount ? "selected" : "active",
      selectedCount,
      activeCount: activeFile()?.records.length || 0,
      currentWork: selectedRecord()?.work || "",
      allCount: allRows().length,
      fields: recordFields()
        .filter((field: Any) => field !== "updates" && !field.startsWith("_"))
        .map((field: Any) => ({ id: String(field), label: String(label(field)) })),
      inspect: (scope, field) => {
        const target = rowsFor(scope);
        const rawValues = target.slice(0, 300).map((row: Any) => row.record?.[field]);
        const distinct = new Set(rawValues.map((value: Any) => JSON.stringify(value))).size;
        const only = rawValues[0];
        return {
          targets: target.length,
          distinct,
          only:
            only === null
              ? "__NULL__"
              : Array.isArray(only) || (only && typeof only === "object")
                ? JSON.stringify(only, null, 2)
                : String(only ?? ""),
        };
      },
      apply: async ({ scope, field, text }) => {
        const target = rowsFor(scope);
        if (!target.length) {
          toast(copy.noScope, { tone: "warning" });
          return false;
        }
        let value;
        try {
          value = parseBulkFieldValue(field, text, target);
        } catch (error: Any) {
          toast(error.message, { tone: "danger" });
          return false;
        }
        const changing = target.filter((row: Any) => !sameValue(row.record?.[field], value));
        if (!changing.length) {
          toast(copy.alreadyValue, { tone: "warning" });
          return false;
        }
        if (
          !(await openMessageDialog({
            title: copy.bulkTitle,
            message: copy.bulkMessage(field, changing.length.toLocaleString()),
            confirmLabel: copy.bulkConfirm,
            cancelLabel: tr("common.cancel"),
          }))
        )
          return false;
        const batchId = uid();
        let fieldChanges = 0;
        const touchedFiles = new Map<string, Any>();
        for (const row of changing) {
          const changed = applyRecordChanges(
            row.file,
            row.index,
            { [field]: cloneAuditValue(value) },
            {
              source: "bulk_field_edit",
              batchId,
              reason: `Bulk edit ${field}`,
              deferCommit: true,
            },
          );
          fieldChanges += changed;
          if (changed) touchedFiles.set(String(row.file.id), row.file);
        }
        for (const file of touchedFiles.values()) {
          invalidateCorpusCache(file.id);
          await persistFileNow(file);
        }
        shell();
        renderView();
        toast(
          copy.bulkUpdated(field, changing.length.toLocaleString(), fieldChanges.toLocaleString()),
          { tone: "success" },
        );
        return true;
      },
    });
  }
  function openOcrCleanupDialog() {
    if (!state.files.length) return toast(copy.loadFirst, { tone: "warning" });
    const selected = selectedReviewItems();
    const active = activeFile();
    openOcrCleanupDialogHost({
      active: active ? { name: String(active.name), recordCount: active.records.length } : null,
      selectedCount: selected.length,
      reviewCount: needsReviewItems().length,
      allCount: allRows().length,
      fileCount: state.files.length,
      choose: async (scope) => {
        let rows = [];
        if (scope === "active" && active)
          rows = active.records.map((record: Any, index: Any) => ({
            file: active,
            record,
            index,
          }));
        else if (scope === "selected")
          rows = selected.map((item: Any) => ({
            file: item.file,
            record: item.record,
            index: item.index,
          }));
        else if (scope === "review")
          rows = needsReviewItems().map((item: Any) => ({
            file: item.file,
            record: item.record,
            index: item.index,
          }));
        else rows = allRows();
        if (!rows.length) {
          toast(copy.noScopeOcr, { tone: "warning" });
          return;
        }
        if (
          await openMessageDialog({
            title: copy.ocrTitle,
            message: copy.ocrMessage(rows.length.toLocaleString()),
            confirmLabel: copy.ocrConfirm,
            cancelLabel: tr("common.cancel"),
          })
        )
          cleanRows(rows);
      },
    });
  }
  function openStoreRecordEditor(record: Any) {
    const chromaId = record._chroma_id;
    if (!chromaId) return toast(tr("record.no_storage_id"), { tone: "warning" });
    const editable = Object.keys(record).filter(
      (k) =>
        k !== "_chroma_id" &&
        k !== "updates" &&
        k !== "_updates_count" &&
        !k.startsWith("_researcher_"),
    );
    openRecordFieldEditorDialog({
      title: tr("records.chroma.edit"),
      subtitle: `${chromaId} · ${state.activeStore}`,
      help: tr("records.chroma.help"),
      footerNote: "",
      saveLabel: tr("records.chroma.save"),
      parseErrorTitle: copy.parseFailed,
      sections: [
        {
          title: tr("records.chroma.section"),
          fields: editable.map((k) => recordEditorField(k, record[k], label)),
        },
      ],
      save: async (values) => {
        const raw = { ...record };
        delete raw._chroma_id;
        const changes: Any = {};
        for (const [field, value] of Object.entries(values))
          if (!sameValue(raw[field], value)) changes[field] = value;
        if (!Object.keys(changes).length) return true;
        const timestamp = new Date().toISOString(),
          batchId = uid();
        const auditEntries = Object.entries(changes).map(([field, newValue]) => ({
          field_name: field,
          old_value: cloneAuditValue(raw[field]),
          new_value: cloneAuditValue(newValue),
          timestamp,
          source: "chroma_manual",
          batch_id: batchId,
          initiated_by: state.userContext?.username || null,
        }));
        try {
          await api(
            `/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(chromaId)}`,
            {
              method: "PATCH",
              body: JSON.stringify({
                changes,
                audit_entries: auditEntries,
                document_field: "text",
                embedding_field: "embedding",
              }),
            },
          );
        } catch (error: Any) {
          toast(copy.chromaFailed(error.message), { tone: "danger" });
          return false;
        }
        state.storeWorksStore = "";
        toast(copy.chromaUpdated, { tone: "success" });
        renderView();
        return true;
      },
    });
  }
  function openRecordHistoryBrowser(file: Any, index: Any) {
    const record = file?.records?.[index];
    if (!record) return;
    if (recordHistoryVersions(record).length <= 1)
      return toast(copy.noHistory, { tone: "warning" });
    const versions = () => recordHistoryVersions(file.records[index]);
    // The caller owns the domain work; the dialog only browses and asks.
    const restoreTo = (version: Any, done: (count: number) => string, none: string) => {
      const count = restoreRecordHistoryVersion(file, index, version);
      if (!count) {
        toast(none, { tone: "warning" });
        return false;
      }
      shell();
      renderView();
      toast(done(count), { tone: "success" });
      return true;
    };
    openRecordHistoryDialog({
      recordId: record.record_id || trf("dashboard.record_n", { n: index + 1 }),
      versions: () => versions().map((version: Any) => ({ ...version })),
      changedFields: (previous, current) => historyVersionChanges(previous, current),
      fieldLabel: (field) => String(label(field)),
      formatValue: (value) => String(jsonPretty(value)),
      formatTimestamp: (value) => String(formatTimestamp(value)),
      restore: async (version) =>
        restoreTo(
          version,
          (count) => copy.restoredFields(count, version.label),
          copy.nothingToRestore,
        ),
      restoreOriginal: async () => {
        if (
          !(await openMessageDialog({
            title: copy.restoreOriginalTitle,
            message: copy.restoreOriginalMessage,
            confirmLabel: copy.restoreOriginalConfirm,
            cancelLabel: tr("common.cancel"),
          }))
        )
          return false;
        return restoreTo(versions()[0], copy.restoredOriginal, copy.alreadyOriginal);
      },
      clear: async () => {
        if (!(await clearRecordUpdates(file, index))) return false;
        shell();
        renderView();
        toast(copy.historyCleared, { tone: "success" });
        return true;
      },
    });
  }
  async function openUpsertQueue() {
    if (!hasCorpusDb())
      return openMessageDialog({
        title: copy.vectorRequired,
        message: dbUnavailableReason(),
        confirmLabel: "OK",
      });
    if (!state.activeStore) return toast(copy.selectCollection, { tone: "warning" });
    if (allRows().length) await refreshPresenceForRows(allRows());
    const itemFor = (row: Any) => {
      const info = recordDbStatus(row.file, row.index, row.record);
      return {
        key: String(localRecordKey(row.file, row.index)),
        recordId: String(row.record.record_id || `Record ${row.index + 1}`),
        source: `${row.record.work || row.file.name} · ${row.file.name}`,
        status: { kind: String(info.kind), label: String(info.label) },
        changes: pendingChangesForRow(row).map((change: Any) => ({
          field: String(label(change.field_name || "field")),
          source: String(change.source || tr("jobs.preview.manual")),
          when: change.timestamp ? String(formatTimestamp(change.timestamp)) : "",
          oldValue: String(jsonPretty(change.old_value)),
          newValue: String(jsonPretty(change.new_value)),
        })),
      };
    };
    const rowByKey = (key: string) =>
      pendingUpsertRows().find((row: Any) => String(localRecordKey(row.file, row.index)) === key);
    openUpsertQueueDialog({
      store: String(state.activeStore),
      items: () => pendingUpsertRows().map(itemFor),
      remove: (key) => {
        const row = rowByKey(key);
        if (!row) return;
        removeFromUpsertQueue(row);
        shell();
      },
      sync: async (keys) => {
        const wanted = new Set(keys);
        const chosen = pendingUpsertRows().filter((row: Any) =>
          wanted.has(String(localRecordKey(row.file, row.index))),
        );
        await upsertRows(chosen, "queued records");
        shell();
        renderView();
      },
    });
  }
  return {
    openMergeDialog,
    openBulkFieldEditor,
    openOcrCleanupDialog,
    openStoreRecordEditor,
    openRecordHistoryBrowser,
    openUpsertQueue,
  };
}
