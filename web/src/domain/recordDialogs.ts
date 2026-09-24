/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";
import {
  bulkFieldEditorHtml,
  chromaRecordEditorHtml,
  mergeDialogHtml,
  ocrCleanupDialogHtml,
  recordEditorHtml,
  recordHistoryDialogHtml,
} from "./recordDialogMarkup";
import { createRecordDialogCopy } from "./recordDialogCopy";

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
  | "decorateDisabledControls"
  | "download"
  | "fieldEditor"
  | "fileJsonl"
  | "formatTimestamp"
  | "hasCorpusDb"
  | "historyVersionChanges"
  | "idbDelete"
  | "jsonPretty"
  | "label"
  | "localRecordKey"
  | "navigateTo"
  | "needsReviewItems"
  | "openMessageModal"
  | "parseBulkFieldValue"
  | "parseEditor"
  | "pendingChangesForRow"
  | "pendingUpsertRows"
  | "persistFileNow"
  | "persistPrefs"
  | "recordDbStatus"
  | "recordFields"
  | "recordHistoryVersions"
  | "refreshPresenceForRows"
  | "removeFromUpsertQueue"
  | "renderView"
  | "restoreRecordHistoryVersion"
  | "sameValue"
  | "selectedIndex"
  | "selectedRecord"
  | "selectedReviewItems"
  | "shell"
  | "showAppModal"
  | "toast"
  | "tr"
  | "trf"
  | "uid"
  | "upsertRows";
type Deps = { state: Loose; fileTimers: Map<string, ReturnType<typeof setTimeout>> } & Record<
  Helper,
  Fn
>;

/** The groups of fields the record editor shows, in order. */
const EDITOR_GROUPS = [
  {
    key: "record.group_source",
    fallback: "Source",
    fields: [
      "record_id",
      "work",
      "document_author",
      "edition",
      "year",
      "page_start",
      "page_end",
      "region_type",
      "region_author",
      "primary_text",
      "canonical_work_id",
      "pdf_file",
      "pdf_pages",
    ],
  },
  {
    key: "record.group_discourse",
    fallback: "Discourse",
    fields: [
      "speaker",
      "position_holder",
      "target",
      "discourse_role",
      "proposition_status",
      "semantic_function",
      "stance",
      "claim_scope",
    ],
  },
  {
    key: "record.group_quotation",
    fallback: "Quotation provenance",
    fields: [
      "is_direct_quote",
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
      "quoted_addressee",
      "quoted_referent",
      "quotation_chain",
    ],
  },
  { key: "record.group_indexing", fallback: "Indexing", fields: ["topics", "concepts", "persons", "works_referenced"] },
  {
    key: "record.group_quality",
    fallback: "Quality & review",
    fields: [
      "attribution_confidence",
      "semantic_classification_confidence",
      "extraction_quality",
      "needs_review",
      "review_reason",
    ],
  },
  {
    key: "record.group_language",
    fallback: "Language & translation",
    fields: ["document_language", "original_language", "document_is_translation", "translator"],
  },
  { key: "record.group_citation", fallback: "Citation", fields: ["inline_citation", "full_citation"] },
  { key: "record.group_text", fallback: "Text", fields: ["text", "text_length"] },
];

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
    decorateDisabledControls,
    download,
    fieldEditor,
    fileJsonl,
    fileTimers,
    formatTimestamp,
    hasCorpusDb,
    historyVersionChanges,
    idbDelete,
    jsonPretty,
    label,
    localRecordKey,
    navigateTo,
    needsReviewItems,
    openMessageModal,
    parseBulkFieldValue,
    parseEditor,
    pendingChangesForRow,
    pendingUpsertRows,
    persistFileNow,
    persistPrefs,
    recordDbStatus,
    recordFields,
    recordHistoryVersions,
    refreshPresenceForRows,
    removeFromUpsertQueue,
    renderView,
    restoreRecordHistoryVersion,
    sameValue,
    selectedIndex,
    selectedRecord,
    selectedReviewItems,
    shell,
    showAppModal,
    toast,
    tr,
    trf,
    uid,
    upsertRows,
  } = deps;
  const copy = createRecordDialogCopy(tr, trf);
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function openMergeDialog() {
    if (state.files.length < 2) return toast(copy.mergeNeedTwo);
    const dialog = document.createElement("dialog");
    dialog.className = "merge-dialog";
    dialog.innerHTML = mergeDialogHtml(state.files, { tr, trf });
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((x: Any) => (x.onclick = close));
    dialog.querySelector("#mergeSelectAll").onclick = () =>
      dialog.querySelectorAll("[data-merge-file]").forEach((x: Any) => (x.checked = true));
    dialog.querySelector("#mergeSelectNone").onclick = () =>
      dialog.querySelectorAll("[data-merge-file]").forEach((x: Any) => (x.checked = false));
    dialog.querySelector("#mergeCreate").onclick = async () => {
      const ids = [...dialog.querySelectorAll("[data-merge-file]:checked")].map(
        (x) => x.dataset.mergeFile,
      );
      const files = state.files.filter((file: Any) => ids.includes(file.id));
      if (!files.length) return toast(copy.selectFile);
      const firstIndex = Math.min(...files.map((file: Any) => state.files.indexOf(file)));
      const name = (
        dialog.querySelector("#mergeName").value.trim() || "derridai-merged.jsonl"
      ).replace(/\s+/g, "-");
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

      await persistFileNow(merged);
      state.activeFileId = merged.id;
      if (dialog.querySelector("#mergeDownload").checked) download(merged.name, fileJsonl(merged));
      persistPrefs();
      close();
      navigateTo("list", { fileId: merged.id });
      toast(copy.merged(files.length, records.length.toLocaleString()));
    };
  }
  function openBulkFieldEditor({ rows = null, title = copy.bulkEditTitle } = {}) {
    if (!state.files.length) return toast(copy.loadFirst);
    const dialog = document.createElement("dialog");
    dialog.className = "bulk-field-dialog";
    const fields = recordFields().filter(
      (field: Any) => field !== "updates" && !field.startsWith("_"),
    );
    const selectedCount = selectedReviewItems().length;
    const activeCount = activeFile()?.records.length || 0;
    const currentWork = selectedRecord()?.work || "";
    const fixedRows: Any = Array.isArray(rows) ? rows : null;
    const defaultScope = fixedRows ? "fixed" : selectedCount ? "selected" : "active";
    dialog.innerHTML = bulkFieldEditorHtml(
      {
        title,
        fixedRows,
        defaultScope,
        selectedCount,
        activeCount,
        currentWork,
        allCount: allRows().length,
        fieldOptions: fields
          .map((field: Any) => `<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`)
          .join(""),
      },
      { tr, trf },
    );
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));

    const currentRows = () =>
      fixedRows || bulkEditRowsForScope(dialog.querySelector("#bulkFieldScope")?.value || "active");
    let lastHintField = "";
    const updateHint = () => {
      const field = dialog.querySelector("#bulkFieldName").value;
      const target = currentRows();
      const rawValues = target.slice(0, 300).map((row: Any) => row.record?.[field]);
      const values = [...new Set(rawValues.map((value: Any) => JSON.stringify(value)))];
      dialog.querySelector("#bulkFieldHint").textContent = trf("records.bulk.hint", {
          targets: target.length.toLocaleString(),
          values: values.length,
          sampled: values.length > 8 ? tr("records.bulk.sampled", " (sampled)") : "",
        });
      const input = dialog.querySelector("#bulkFieldValue");
      if (values.length === 1 && (lastHintField !== field || !input.value.trim())) {
        const only = rawValues[0];
        input.value =
          only === null
            ? "__NULL__"
            : Array.isArray(only) || (only && typeof only === "object")
              ? JSON.stringify(only, null, 2)
              : String(only ?? "");
      } else if (lastHintField !== field && values.length !== 1) input.value = "";
      lastHintField = field;
    };
    dialog.querySelector("#bulkFieldScope")?.addEventListener("change", updateHint);
    dialog.querySelector("#bulkFieldName").addEventListener("change", updateHint);
    updateHint();

    dialog.querySelector("#applyBulkField").onclick = async () => {
      const target = currentRows();
      if (!target.length) return toast(copy.noScope);
      const field = dialog.querySelector("#bulkFieldName").value;
      let value;
      try {
        value = parseBulkFieldValue(field, dialog.querySelector("#bulkFieldValue").value, target);
      } catch (error: Any) {
        return toast(error.message);
      }
      const changing = target.filter((row: Any) => !sameValue(row.record?.[field], value));
      if (!changing.length) return toast(copy.alreadyValue);
      if (
        !(await openMessageModal({
          title: copy.bulkTitle,
          message: copy.bulkMessage(field, changing.length.toLocaleString()),
          confirmLabel: copy.bulkConfirm,
          cancelLabel: tr("common.cancel"),
        }))
      )
        return;
      const batchId = uid();
      let fieldChanges = 0;
      for (const row of changing) {
        fieldChanges += applyRecordChanges(
          row.file,
          row.index,
          { [field]: cloneAuditValue(value) },
          {
            source: "bulk_field_edit",
            batchId,
            reason: `Bulk edit ${field}`,
          },
        );
      }
      close();
      shell();
      renderView();
      toast(
        copy.bulkUpdated(
          field,
          changing.length.toLocaleString(),
          fieldChanges.toLocaleString(),
        ),
      );
    };
  }
  function openOcrCleanupDialog() {
    if (!state.files.length) return toast(copy.loadFirst);
    const dialog = document.createElement("dialog");
    const selected = selectedReviewItems();
    const active = activeFile();
    dialog.innerHTML = ocrCleanupDialogHtml(
      {
        active,
        selectedCount: selected.length,
        reviewCount: needsReviewItems().length,
        allCount: allRows().length,
        fileCount: state.files.length,
      },
      { tr, trf },
    );
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelectorAll("[data-scope]").forEach(
      (button: Any) =>
        (button.onclick = async () => {
          let rows = [];
          if (button.dataset.scope === "active" && active)
            rows = active.records.map((record: Any, index: Any) => ({
              file: active,
              record,
              index,
            }));
          else if (button.dataset.scope === "selected")
            rows = selected.map((item: Any) => ({
              file: item.file,
              record: item.record,
              index: item.index,
            }));
          else if (button.dataset.scope === "review")
            rows = needsReviewItems().map((item: Any) => ({
              file: item.file,
              record: item.record,
              index: item.index,
            }));
          else rows = allRows();
          if (!rows.length) return toast(copy.noScopeOcr);
          close();
          if (
            await openMessageModal({
              title: copy.ocrTitle,
              message: copy.ocrMessage(rows.length.toLocaleString()),
              confirmLabel: copy.ocrConfirm,
              cancelLabel: tr("common.cancel"),
            })
          )
            cleanRows(rows);
        }),
    );
  }
  function openEditor() {
    const f = activeFile(),
      i = selectedIndex(f),
      r = selectedRecord();
    if (!r) return;
    const dialog = document.createElement("dialog");
    const used = new Set();
    const groups = [];
    for (const group of EDITOR_GROUPS) {
      const fields = group.fields.filter((k: Any) => k in r);
      if (!fields.length) continue;
      fields.forEach((k: Any) => used.add(k));
      groups.push(
        `<section class="editor-section"><h3>${esc(tr(group.key, group.fallback))}</h3><div class="editor-grid">${fields.map((k: Any) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    }
    const other = Object.keys(r).filter((k) => !used.has(k) && k !== "updates");
    if (other.length)
      groups.push(
        `<section class="editor-section"><h3>${esc(tr("record.group_other"))}</h3><div class="editor-grid">${other.map((k) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    dialog.innerHTML = recordEditorHtml(
      { subtitle: `${r.record_id || ""} · ${r.work || f.name}`, groups: groups.join("") },
      tr,
    );
    document.body.appendChild(dialog);
    showAppModal(dialog);
    dialog.querySelectorAll("[data-close]").forEach(
      (b: Any) =>
        (b.onclick = () => {
          dialog.close();
          dialog.remove();
        }),
    );
    dialog.querySelector("form").onsubmit = (e: Any) => {
      e.preventDefault();
      const next = { ...r };
      try {
        dialog
          .querySelectorAll("[data-key]")
          .forEach((el: Any) => (next[el.dataset.key] = parseEditor(el)));
      } catch (error: Any) {
        openMessageModal({
          title: copy.saveFailed,
          message: error.message,
          tone: "danger",
        });
        return;
      }
      if ("text_length" in next) next.text_length = String(next.text || "").length;
      const changes: Any = {};
      for (const [field, value] of Object.entries(next))
        if (field !== "updates" && !sameValue(r[field], value)) changes[field] = value;
      const count = applyRecordChanges(f, i, changes, { source: "manual" });
      dialog.close();
      dialog.remove();
      shell();
      renderView();
      count
        ? toast(copy.saved(count), { tone: "success" })
        : toast(copy.noChanges);
    };
  }
  function openStoreRecordEditor(record: Any) {
    const chromaId = record._chroma_id;
    if (!chromaId) return toast(tr("record.no_storage_id"));
    const dialog = document.createElement("dialog");
    const editable = Object.keys(record).filter(
      (k) =>
        k !== "_chroma_id" &&
        k !== "updates" &&
        k !== "_updates_count" &&
        !k.startsWith("_researcher_"),
    );
    dialog.innerHTML = chromaRecordEditorHtml(
      {
        chromaId,
        store: state.activeStore,
        fields: editable.map((k) => fieldEditor(k, record[k])).join(""),
      },
      tr,
    );
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((b: Any) => (b.onclick = close));
    dialog.querySelector("form").onsubmit = async (e: Any) => {
      e.preventDefault();
      const raw = { ...record };
      delete raw._chroma_id;
      const changes: Any = {};
      try {
        dialog.querySelectorAll("[data-key]").forEach((el: Any) => {
          const value = parseEditor(el);
          if (!sameValue(raw[el.dataset.key], value)) changes[el.dataset.key] = value;
        });
      } catch (error: Any) {
        openMessageModal({
          title: copy.parseFailed,
          message: error.message,
          tone: "danger",
        });
        return;
      }
      if (!Object.keys(changes).length) return close();
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
        state.storeWorksStore = "";
        close();
        toast(copy.chromaUpdated, { tone: "success" });
        renderView();
      } catch (error: Any) {
        toast(copy.chromaFailed(error.message), { tone: "danger" });
      }
    };
  }
  function openRecordHistoryBrowser(file: Any, index: Any) {
    const record = file?.records?.[index];
    if (!record) return;
    let versions = recordHistoryVersions(record);
    if (versions.length <= 1) return toast(copy.noHistory);
    let cursor = versions.length - 1;
    const dialog = document.createElement("dialog");
    dialog.className = "record-history-dialog";
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    const render = () => {
      versions = recordHistoryVersions(file.records[index]);
      cursor = Math.max(0, Math.min(cursor, versions.length - 1));
      const version = versions[cursor];
      const previous = cursor > 0 ? versions[cursor - 1] : null;
      const changed = previous ? historyVersionChanges(previous.record, version.record) : [];
      const currentIndex = versions.length - 1;
      const isCurrent = cursor === currentIndex;
      const text = String(version.record.text || "");
      const diffs = changed
        .map(
          (field: Any) =>
            `<details class="history-version-diff"><summary><b>${esc(label(field))}</b><span>${esc(tr("records.history.changed"))}</span></summary><div class="history-diff-values"><div><small>${esc(tr("records.history.previous"))}</small><pre>${esc(jsonPretty(previous?.record?.[field]))}</pre></div><div><small>${esc(tr("records.history.this_version"))}</small><pre>${esc(jsonPretty(version.record?.[field]))}</pre></div></div></details>`,
        )
        .join("");
      dialog.innerHTML = recordHistoryDialogHtml(
        {
          recordId:
            file.records[index]?.record_id ||
            trf("dashboard.record_n", { n: index + 1 }),
          changeSets: versions.length - 1,
          olderDisabled: cursor <= 0,
          newerDisabled: cursor >= currentIndex,
          versionLabel: version.label,
          isCurrent,
          versionMeta: `${version.timestamp ? formatTimestamp(version.timestamp) : tr("records.history.before_edits")}${version.source ? ` · ${version.source}` : ""}${version.model ? ` · ${version.model}` : ""}`,
          changed,
          words: text.trim() ? text.trim().split(/\s+/).length : 0,
          chars: text.length.toLocaleString(),
          diffs,
          work: version.record.work || tr("records.history.untitled"),
          authorYear: `${version.record.document_author || ""} · ${version.record.year || ""}`,
          preview: `${text.slice(0, 5000)}${text.length > 5000 ? "…" : ""}`,
          restoreOriginalDisabled: cursor === 0 && isCurrent,
          restoreDisabled: isCurrent,
        },
        { tr, trf },
      );
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      dialog.querySelector("#historyOlder").onclick = () => {
        cursor--;
        render();
      };
      dialog.querySelector("#historyNewer").onclick = () => {
        cursor++;
        render();
      };
      dialog.querySelector("#historyRestore").onclick = async () => {
        if (isCurrent) return;
        const count = restoreRecordHistoryVersion(file, index, version);
        if (!count) return toast(copy.nothingToRestore);
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(copy.restoredFields(count, version.label));
      };
      dialog.querySelector("#historyUndoAll").onclick = async () => {
        const original = versions[0];
        if (
          !(await openMessageModal({
            title: copy.restoreOriginalTitle,
            message: copy.restoreOriginalMessage,
            confirmLabel: copy.restoreOriginalConfirm,
            cancelLabel: tr("common.cancel"),
          }))
        )
          return;
        const count = restoreRecordHistoryVersion(file, index, original);
        if (!count) return toast(copy.alreadyOriginal);
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(copy.restoredOriginal(count));
      };
      dialog.querySelector("#historyClear").onclick = async () => {
        if (!(await clearRecordUpdates(file, index))) return;
        close();
        shell();
        renderView();
        toast(copy.historyCleared);
      };
      decorateDisabledControls(dialog);
    };
    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  async function openUpsertQueue() {
    if (!hasCorpusDb())
      return openMessageModal({
        title: copy.vectorRequired,
        message: dbUnavailableReason(),
        confirmLabel: "OK",
      });
    if (!state.activeStore) return toast(copy.selectCollection);
    if (allRows().length) await refreshPresenceForRows(allRows());
    const _rows = pendingUpsertRows();
    const dialog = document.createElement("dialog");
    dialog.className = "queue-dialog wide-queue-dialog";

    const render = () => {
      const currentRows = pendingUpsertRows();
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("vector.unsynced_changes"))}</h2><div class="dialog-subtitle">${esc(state.activeStore)} · ${currentRows.length} ${esc(tr("dynamic.records"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db">
      <div class="queue-explainer"><b>${esc(tr("vector.unsynced_changes_what"))}</b><p>${esc(tr("vector.unsynced_changes_help"))}</p></div><div class="queue-bulk-actions">${currentRows.length ? `<button class="btn small" id="queueSelectAll">${esc(tr("ui.select_all"))}</button><button class="btn small" id="queueSelectNone">${esc(tr("ui.clear_selection"))}</button>` : ""}</div>
      <div class="upsert-queue-list">${
        currentRows
          .map((row: Any) => {
            const info = recordDbStatus(row.file, row.index, row.record);
            const key = localRecordKey(row.file, row.index);
            const changes = pendingChangesForRow(row);
            return `<section class="upsert-queue-card">
          <div class="upsert-queue-head">
            <label class="upsert-queue-item"><input type="checkbox" data-upsert-key="${esc(key)}" checked><span><b>${esc(row.record.record_id || `Record ${row.index + 1}`)}</b><small>${esc(row.record.work || row.file.name)} · ${esc(row.file.name)}</small></span><span class="db-status ${info.kind}"><i></i>${esc(info.label)}</span></label>
            <div class="tools"><button class="btn small" data-review-queue="${esc(key)}">${esc(trf("records.upsert.review_n", { count: changes.length }))}</button><button class="btn small danger" data-remove-queue="${esc(key)}">${esc(tr("records.upsert.remove"))}</button></div>
          </div>
          <div class="queue-change-list hidden" data-queue-changes="${esc(key)}">${changes.map((change: Any) => `<div class="queue-change-row"><b>${esc(label(change.field_name || "field"))}</b><span>${esc(change.source || tr("jobs.preview.manual"))}${change.timestamp ? ` · ${esc(formatTimestamp(change.timestamp))}` : ""}</span><details><summary>${esc(tr("records.upsert.values"))}</summary><div class="queue-change-values"><pre>${esc(jsonPretty(change.old_value))}</pre><span>→</span><pre>${esc(jsonPretty(change.new_value))}</pre></div></details></div>`).join("")}</div>
        </section>`;
          })
          .join("") ||
        `<div class="llm-empty">${esc(tr("vector.no_unsynced_changes"))}</div>`
      }</div>
    </div>
      <div class="da"><button class="btn" data-close>${esc(tr("common.close"))}</button>${currentRows.length ? `<button class="btn primary" id="upsertQueued">${icon("database")}${esc(tr("vector.sync_selected"))}</button>` : ""}</div>`;

      const close = () => {
        dialog.close();
        dialog.remove();
      };
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      dialog
        .querySelector("#queueSelectAll")
        ?.addEventListener("click", () =>
          dialog.querySelectorAll("[data-upsert-key]").forEach((box: Any) => (box.checked = true)),
        );
      dialog
        .querySelector("#queueSelectNone")
        ?.addEventListener("click", () =>
          dialog.querySelectorAll("[data-upsert-key]").forEach((box: Any) => (box.checked = false)),
        );
      dialog.querySelectorAll("[data-review-queue]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const panel = dialog.querySelector(
              `[data-queue-changes="${CSS.escape(button.dataset.reviewQueue)}"]`,
            );
            panel?.classList.toggle("hidden");
          }),
      );
      dialog.querySelectorAll("[data-remove-queue]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const row = currentRows.find(
              (item: Any) => localRecordKey(item.file, item.index) === button.dataset.removeQueue,
            );
            if (row) {
              removeFromUpsertQueue(row);
              render();
              shell();
            }
          }),
      );
      dialog.querySelector("#upsertQueued")?.addEventListener("click", async () => {
        const selected = new Set(
          [...dialog.querySelectorAll("[data-upsert-key]:checked")].map((x) => x.dataset.upsertKey),
        );
        const chosen = currentRows.filter((row: Any) =>
          selected.has(localRecordKey(row.file, row.index)),
        );
        if (!chosen.length) return toast(copy.selectQueued);
        close();
        await upsertRows(chosen, "queued records");
        shell();
        renderView();
      });
    };

    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  return {
    openMergeDialog,
    openBulkFieldEditor,
    openOcrCleanupDialog,
    openEditor,
    openStoreRecordEditor,
    openRecordHistoryBrowser,
    openUpsertQueue,
  };
}
