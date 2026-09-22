/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

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
  | "uid"
  | "upsertRows";
type Deps = { state: Loose; fileTimers: Map<string, ReturnType<typeof setTimeout>> } & Record<
  Helper,
  Fn
>;

/** The groups of fields the record editor shows, in order. */
const EDITOR_GROUPS = [
  {
    name: "Source",
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
    name: "Discourse",
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
    name: "Quotation provenance",
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
  { name: "Indexing", fields: ["topics", "concepts", "persons", "works_referenced"] },
  {
    name: "Quality / review",
    fields: [
      "attribution_confidence",
      "semantic_classification_confidence",
      "extraction_quality",
      "needs_review",
      "review_reason",
    ],
  },
  {
    name: "Language / translation",
    fields: ["document_language", "original_language", "document_is_translation", "translator"],
  },
  { name: "Citation", fields: ["inline_citation", "full_citation"] },
  { name: "Text", fields: ["text", "text_length"] },
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
    uid,
    upsertRows,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function openMergeDialog() {
    if (state.files.length < 2) return toast("Open at least two JSONL files to merge");
    const dialog = document.createElement("dialog");
    dialog.className = "merge-dialog";
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Merge JSONL tabs</h2><div class="dialog-subtitle">Choose any subset. The selected source tabs will be replaced in the workspace by the merged tab.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">Select all</button><button class="btn small" id="mergeSelectNone">Clear</button></div><div class="merge-file-list">${state.files.map((file: Any) => `<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${file.records.length.toLocaleString()} records</small></span></label>`).join("")}</div><div class="field"><label>Merged file name</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>Download merged JSONL immediately</span></label><div class="info">Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mergeCreate">Merge and replace selected tabs</button></div>`;
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
      if (!files.length) return toast("Select at least one file");
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
      toast(
        `Merged and replaced ${files.length} tabs · ${records.length.toLocaleString()} records`,
      );
    };
  }
  function openBulkFieldEditor({ rows = null, title = "Bulk edit one field" } = {}) {
    if (!state.files.length) return toast("Load JSONL records first");
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
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">Apply one field value consistently across a selected record set. Every actual change is audited.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${fixedRows ? `<div class="info">${fixedRows.length.toLocaleString()} records are in this operation.</div>` : `<div class="field"><label>Target records</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope === "selected" ? "selected" : ""} ${selectedCount ? "" : "disabled"}>Selected records (${selectedCount.toLocaleString()})</option><option value="active" ${defaultScope === "active" ? "selected" : ""}>Active JSONL (${activeCount.toLocaleString()})</option>${currentWork ? `<option value="work">Current work: ${esc(currentWork)}</option>` : ""}<option value="all">All loaded records (${allRows().length.toLocaleString()})</option></select></div>`}
    <div class="field"><label>Field</label><select class="control" id="bulkFieldName">${fields.map((field: Any) => `<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("")}</select></div>
    <div class="field"><label>New value</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="Enter the new value. Arrays/objects use JSON. Enter __NULL__ for null."></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>Only modify records whose value actually differs</span></label>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyBulkField">${icon("check")}Apply field update</button></div>`;
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
      dialog.querySelector("#bulkFieldHint").textContent =
        `${target.length.toLocaleString()} target records · ${values.length} distinct current value${values.length === 1 ? "" : "s"}${values.length > 8 ? " (sampled)" : ""}`;
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
      if (!target.length) return toast("No records are in the selected scope");
      const field = dialog.querySelector("#bulkFieldName").value;
      let value;
      try {
        value = parseBulkFieldValue(field, dialog.querySelector("#bulkFieldValue").value, target);
      } catch (error: Any) {
        return toast(error.message);
      }
      const changing = target.filter((row: Any) => !sameValue(row.record?.[field], value));
      if (!changing.length) return toast("Every target record already has that value");
      if (
        !(await openMessageModal({
          title: "Apply bulk field update?",
          message: `Set ${field} on ${changing.length.toLocaleString()} record${changing.length === 1 ? "" : "s"}?`,
          confirmLabel: "Apply update",
          cancelLabel: "Cancel",
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
        `Updated ${field} on ${changing.length.toLocaleString()} records · ${fieldChanges.toLocaleString()} audited changes`,
      );
    };
  }
  function openOcrCleanupDialog() {
    if (!state.files.length) return toast("Load JSONL records first");
    const dialog = document.createElement("dialog");
    const selected = selectedReviewItems();
    const active = activeFile();
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Clean OCR Artifacts</h2><div class="dialog-subtitle">Conservative ligature, zero-width character, and broken line-hyphen cleanup. No paraphrasing.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active ? "" : "disabled"}><b>Active JSONL tab</b><span>${active ? `${active.records.length.toLocaleString()} records · ${esc(active.name)}` : "No active tab"}</span></button><button class="scope-card" data-scope="selected" ${selected.length ? "" : "disabled"}><b>Selected records</b><span>${selected.length.toLocaleString()} currently selected</span></button><button class="scope-card" data-scope="review"><b>Needs-review records</b><span>${needsReviewItems().length.toLocaleString()} flagged records</span></button><button class="scope-card" data-scope="all"><b>All loaded records</b><span>${allRows().length.toLocaleString()} records across ${state.files.length} tabs</span></button></div><div class="da"><button class="btn" data-close>Cancel</button></div>`;
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
          if (!rows.length) return toast("No records in that scope");
          close();
          if (
            await openMessageModal({
              title: "Run OCR cleanup?",
              message: `Run conservative OCR cleanup on ${rows.length.toLocaleString()} records?`,
              confirmLabel: "Run cleanup",
              cancelLabel: "Cancel",
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
        `<section class="editor-section"><h3>${esc(group.name)}</h3><div class="editor-grid">${fields.map((k: Any) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    }
    const other = Object.keys(r).filter((k) => !used.has(k) && k !== "updates");
    if (other.length)
      groups.push(
        `<section class="editor-section"><h3>Other fields</h3><div class="editor-grid">${other.map((k) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    dialog.innerHTML = `<form><div class="dh"><div><h2 class="dialog-title">Edit record</h2><div class="dialog-subtitle">${esc(r.record_id || "")} · ${esc(r.work || f.name)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${groups.join("")}</div><div class="da"><div class="llm-footer-note">Changes stay local until you export or upsert them.</div><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save changes</button></div></form>`;
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
          title: "Could not save record",
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
        ? toast(`Saved ${count} tracked change${count === 1 ? "" : "s"}`, { tone: "success" })
        : toast("No changes to save");
    };
  }
  function openStoreRecordEditor(record: Any) {
    const chromaId = record._chroma_id;
    if (!chromaId) return toast(tr("record.no_storage_id", "This Chroma record has no storage ID"));
    const dialog = document.createElement("dialog");
    const editable = Object.keys(record).filter(
      (k) =>
        k !== "_chroma_id" &&
        k !== "updates" &&
        k !== "_updates_count" &&
        !k.startsWith("_researcher_"),
    );
    dialog.innerHTML = `<form><div class="dh"><div><h2 class="dialog-title">Edit Chroma record</h2><div class="dialog-subtitle">${esc(chromaId)} · ${esc(state.activeStore)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">Saving updates this record in place under the same Chroma ID and regenerates its embedding when the configured embedding provider allows it.</div><section class="editor-section"><h3>Record</h3><div class="editor-grid">${editable.map((k) => fieldEditor(k, record[k])).join("")}</div></section></div><div class="da"><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save to Chroma</button></div></form>`;
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
          title: "Could not parse edited record",
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
        toast("Chroma record updated", { tone: "success" });
        renderView();
      } catch (error: Any) {
        toast(`Chroma update failed: ${error.message}`, { tone: "danger" });
      }
    };
  }
  function openRecordHistoryBrowser(file: Any, index: Any) {
    const record = file?.records?.[index];
    if (!record) return;
    let versions = recordHistoryVersions(record);
    if (versions.length <= 1) return toast("This record has no update history");
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
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Record history</h2><div class="dialog-subtitle">${esc(file.records[index]?.record_id || `Record ${index + 1}`)} · ${versions.length - 1} saved change set${versions.length - 1 === 1 ? "" : "s"}</div></div><button class="btn icon-only" data-close title="${esc(tr("ui.close", "Close"))}" aria-label="${esc(tr("ui.close", "Close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${cursor <= 0 ? `disabled data-disabled-reason="Already at the original record."` : ""}>← Older</button>
          <div class="history-version-position"><b>${esc(version.label)}${isCurrent ? " · Current" : ""}</b><span>${version.timestamp ? esc(formatTimestamp(version.timestamp)) : "Before tracked edits"}${version.source ? ` · ${esc(version.source)}` : ""}${version.model ? ` · ${esc(version.model)}` : ""}</span></div>
          <button class="btn" id="historyNewer" ${cursor >= currentIndex ? `disabled data-disabled-reason="Already at the newest version."` : ""}>Newer →</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> field${changed.length === 1 ? "" : "s"} changed in this version</span><span><b>${text.trim() ? text.trim().split(/\s+/).length : 0}</b> words</span><span><b>${text.length.toLocaleString()}</b> characters</span></div>
        ${changed.length ? `<div class="history-version-diffs">${changed.map((field: Any) => `<details class="history-version-diff"><summary><b>${esc(label(field))}</b><span>changed</span></summary><div class="history-diff-values"><div><small>Previous</small><pre>${esc(jsonPretty(previous?.record?.[field]))}</pre></div><div><small>This version</small><pre>${esc(jsonPretty(version.record?.[field]))}</pre></div></div></details>`).join("")}</div>` : `<div class="info">This is the reconstructed original state before tracked updates.</div>`}
        <details class="history-record-preview"><summary>Preview this version</summary><div class="history-preview-meta"><b>${esc(version.record.work || "Untitled work")}</b><span>${esc(version.record.document_author || "")} · ${esc(version.record.year || "")}</span></div><div class="history-preview-text">${esc(text.slice(0, 5000))}${text.length > 5000 ? "…" : ""}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">Delete audit history…</button><span class="dialog-action-spacer"></span><button class="btn" data-close>Close</button><button class="btn" id="historyUndoAll" ${cursor === 0 && isCurrent ? "disabled" : ""}>Restore original</button><button class="btn primary" id="historyRestore" ${isCurrent ? `disabled data-disabled-reason="This is already the current version."` : ""}>Restore this version</button></div>`;
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
        if (!count) return toast("No record fields needed restoring");
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(`Restored ${count} field${count === 1 ? "" : "s"} from ${version.label}`);
      };
      dialog.querySelector("#historyUndoAll").onclick = async () => {
        const original = versions[0];
        if (
          !(await openMessageModal({
            title: "Restore original record?",
            message:
              "Restore every field to its state before the tracked update history? The restoration itself will be recorded, so you can move forward again later.",
            confirmLabel: "Restore original",
            cancelLabel: "Cancel",
          }))
        )
          return;
        const count = restoreRecordHistoryVersion(file, index, original);
        if (!count) return toast("The record already matches its original tracked state");
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(`Restored original record state · ${count} fields changed`);
      };
      dialog.querySelector("#historyClear").onclick = async () => {
        if (!(await clearRecordUpdates(file, index))) return;
        close();
        shell();
        renderView();
        toast("Record update history cleared");
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
        title: "Vector database required",
        message: dbUnavailableReason(),
        confirmLabel: "OK",
      });
    if (!state.activeStore) return toast("Select a Chroma collection first");
    if (allRows().length) await refreshPresenceForRows(allRows());
    const _rows = pendingUpsertRows();
    const dialog = document.createElement("dialog");
    dialog.className = "queue-dialog wide-queue-dialog";

    const render = () => {
      const currentRows = pendingUpsertRows();
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("vector.unsynced_changes", "Unsynced local changes"))}</h2><div class="dialog-subtitle">${esc(state.activeStore)} · ${currentRows.length} ${esc(tr("dynamic.records", "records"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db">
      <div class="queue-explainer"><b>${esc(tr("vector.unsynced_changes_what", "What is this list?"))}</b><p>${esc(tr("vector.unsynced_changes_help", "These are browser-workspace records that changed since their last confirmed sync, plus records DerridAI has confirmed are missing from the selected collection. Removing an item suppresses only its current version; a later change queues it again."))}</p></div><div class="queue-bulk-actions">${currentRows.length ? `<button class="btn small" id="queueSelectAll">${esc(tr("ui.select_all", "Select all"))}</button><button class="btn small" id="queueSelectNone">${esc(tr("ui.clear_selection", "Clear selection"))}</button>` : ""}</div>
      <div class="upsert-queue-list">${
        currentRows
          .map((row: Any) => {
            const info = recordDbStatus(row.file, row.index, row.record);
            const key = localRecordKey(row.file, row.index);
            const changes = pendingChangesForRow(row);
            return `<section class="upsert-queue-card">
          <div class="upsert-queue-head">
            <label class="upsert-queue-item"><input type="checkbox" data-upsert-key="${esc(key)}" checked><span><b>${esc(row.record.record_id || `Record ${row.index + 1}`)}</b><small>${esc(row.record.work || row.file.name)} · ${esc(row.file.name)}</small></span><span class="db-status ${info.kind}"><i></i>${esc(info.label)}</span></label>
            <div class="tools"><button class="btn small" data-review-queue="${esc(key)}">Review ${changes.length} change${changes.length === 1 ? "" : "s"}</button><button class="btn small danger" data-remove-queue="${esc(key)}">Remove from queue</button></div>
          </div>
          <div class="queue-change-list hidden" data-queue-changes="${esc(key)}">${changes.map((change: Any) => `<div class="queue-change-row"><b>${esc(label(change.field_name || "field"))}</b><span>${esc(change.source || "manual")}${change.timestamp ? ` · ${esc(formatTimestamp(change.timestamp))}` : ""}</span><details><summary>Values</summary><div class="queue-change-values"><pre>${esc(jsonPretty(change.old_value))}</pre><span>→</span><pre>${esc(jsonPretty(change.new_value))}</pre></div></details></div>`).join("")}</div>
        </section>`;
          })
          .join("") ||
        `<div class="llm-empty">${esc(tr("vector.no_unsynced_changes", "No confirmed unsynced local changes."))}</div>`
      }</div>
    </div>
    <div class="da"><button class="btn" data-close>Close</button>${currentRows.length ? `<button class="btn primary" id="upsertQueued">${icon("database")}${esc(tr("vector.sync_selected", "Sync selected"))}</button>` : ""}</div>`;

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
        if (!chosen.length) return toast("Select at least one queued record");
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
