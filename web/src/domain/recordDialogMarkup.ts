/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function mergeDialogHtml(files: Any[], deps: { tr: Tr; trf: Trf }): string {
  const { tr, trf } = deps;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("records.merge.title", "Merge JSONL tabs"))}</h2><div class="dialog-subtitle">${esc(tr("records.merge.subtitle", "Choose any subset. The selected source tabs will be replaced in the workspace by the merged tab."))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">${esc(tr("ui.select_all", "Select all"))}</button><button class="btn small" id="mergeSelectNone">${esc(tr("ui.clear", "Clear"))}</button></div><div class="merge-file-list">${files.map((file: Any) => `<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${esc(trf("records.merge.file_records", "{count} records", { count: file.records.length.toLocaleString() }))}</small></span></label>`).join("")}</div><div class="field"><label>${esc(tr("records.merge.filename", "Merged file name"))}</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>${esc(tr("records.merge.download", "Download merged JSONL immediately"))}</span></label><div class="info">${esc(tr("records.merge.help", "Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted."))}</div></div><div class="da"><button class="btn" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary" id="mergeCreate">${esc(tr("records.merge.create", "Merge and replace selected tabs"))}</button></div>`;
}

export function bulkFieldEditorHtml(
  input: {
    title: string;
    fixedRows: Any;
    defaultScope: string;
    selectedCount: number;
    activeCount: number;
    currentWork: string;
    allCount: number;
    fieldOptions: string;
  },
  deps: { tr: Tr; trf: Trf },
): string {
  const { tr, trf } = deps;
  const {
    title,
    fixedRows,
    defaultScope,
    selectedCount,
    activeCount,
    currentWork,
    allCount,
    fieldOptions,
  } = input;
  const scope = fixedRows
    ? `<div class="info">${esc(trf("records.bulk.in_operation", "{count} records are in this operation.", { count: fixedRows.length.toLocaleString() }))}</div>`
    : `<div class="field"><label>${esc(tr("records.bulk.target", "Target records"))}</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope === "selected" ? "selected" : ""} ${selectedCount ? "" : "disabled"}>${esc(trf("records.bulk.selected", "Selected records ({count})", { count: selectedCount.toLocaleString() }))}</option><option value="active" ${defaultScope === "active" ? "selected" : ""}>${esc(trf("records.bulk.active", "Active JSONL ({count})", { count: activeCount.toLocaleString() }))}</option>${currentWork ? `<option value="work">${esc(trf("records.bulk.work", "Current work: {work}", { work: currentWork }))}</option>` : ""}<option value="all">${esc(trf("records.bulk.all", "All loaded records ({count})", { count: allCount.toLocaleString() }))}</option></select></div>`;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(tr("records.bulk.subtitle", "Apply one field value consistently across a selected record set. Every actual change is audited."))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${scope}
    <div class="field"><label>${esc(tr("works.field", "Field"))}</label><select class="control" id="bulkFieldName">${fieldOptions}</select></div>
    <div class="field"><label>${esc(tr("records.bulk.new_value", "New value"))}</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="${esc(tr("records.bulk.placeholder", "Enter the new value. Arrays/objects use JSON. Enter __NULL__ for null."))}"></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>${esc(tr("records.bulk.only_different", "Only modify records whose value actually differs"))}</span></label>
  </div>
  <div class="da"><button class="btn" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary" id="applyBulkField">${icon("check")}${esc(tr("records.bulk.apply", "Apply field update"))}</button></div>`;
}

export function ocrCleanupDialogHtml(
  input: { active: Any; selectedCount: number; reviewCount: number; allCount: number; fileCount: number },
  deps: { tr: Tr; trf: Trf },
): string {
  const { tr, trf } = deps;
  const { active, selectedCount, reviewCount, allCount, fileCount } = input;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("ui.clean_ocr", "Clean OCR Artifacts"))}</h2><div class="dialog-subtitle">${esc(tr("records.ocr.subtitle", "Conservative ligature, zero-width character, and broken line-hyphen cleanup. No paraphrasing."))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active ? "" : "disabled"}><b>${esc(tr("records.ocr.active_tab", "Active JSONL tab"))}</b><span>${active ? esc(trf("records.ocr.active_meta", "{count} records · {name}", { count: active.records.length.toLocaleString(), name: active.name })) : esc(tr("records.ocr.no_tab", "No active tab"))}</span></button><button class="scope-card" data-scope="selected" ${selectedCount ? "" : "disabled"}><b>${esc(tr("records.ocr.selected", "Selected records"))}</b><span>${esc(trf("records.ocr.selected_meta", "{count} currently selected", { count: selectedCount.toLocaleString() }))}</span></button><button class="scope-card" data-scope="review"><b>${esc(tr("records.ocr.review", "Needs-review records"))}</b><span>${esc(trf("records.ocr.review_meta", "{count} flagged records", { count: reviewCount.toLocaleString() }))}</span></button><button class="scope-card" data-scope="all"><b>${esc(tr("records.ocr.all", "All loaded records"))}</b><span>${esc(trf("records.ocr.all_meta", "{count} records across {tabs} tabs", { count: allCount.toLocaleString(), tabs: fileCount }))}</span></button></div><div class="da"><button class="btn" data-close>${esc(tr("common.cancel", "Cancel"))}</button></div>`;
}

export function recordEditorHtml(
  input: { subtitle: string; groups: string },
  tr: Tr,
): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("record.edit", "Edit record"))}</h2><div class="dialog-subtitle">${esc(input.subtitle)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${input.groups}</div><div class="da"><div class="llm-footer-note">${esc(tr("records.editor.local_note", "Changes stay local until you export or upsert them."))}</div><button class="btn" type="button" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.editor.save", "Save changes"))}</button></div></form>`;
}

export function chromaRecordEditorHtml(
  input: { chromaId: string; store: string; fields: string },
  tr: Tr,
): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("records.chroma.edit", "Edit Chroma record"))}</h2><div class="dialog-subtitle">${esc(input.chromaId)} · ${esc(input.store)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">${esc(tr("records.chroma.help", "Saving updates this record in place under the same Chroma ID and regenerates its embedding when the configured embedding provider allows it."))}</div><section class="editor-section"><h3>${esc(tr("records.chroma.section", "Record"))}</h3><div class="editor-grid">${input.fields}</div></section></div><div class="da"><button class="btn" type="button" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.chroma.save", "Save to Chroma"))}</button></div></form>`;
}

export function recordHistoryDialogHtml(
  input: {
    recordId: string;
    changeSets: number;
    olderDisabled: boolean;
    newerDisabled: boolean;
    versionLabel: string;
    isCurrent: boolean;
    versionMeta: string;
    changed: Any[];
    words: number;
    chars: string;
    diffs: string;
    work: string;
    authorYear: string;
    preview: string;
    restoreOriginalDisabled: boolean;
    restoreDisabled: boolean;
  },
  deps: { tr: Tr; trf: Trf },
): string {
  const { tr, trf } = deps;
  const {
    recordId,
    changeSets,
    olderDisabled,
    newerDisabled,
    versionLabel,
    isCurrent,
    versionMeta,
    changed,
    words,
    chars,
    diffs,
    work,
    authorYear,
    preview,
    restoreOriginalDisabled,
    restoreDisabled,
  } = input;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("records.history.title", "Record history"))}</h2><div class="dialog-subtitle">${esc(recordId)} · ${esc(trf("records.history.changesets", "{count} saved change set(s)", { count: changeSets }))}</div></div><button class="btn icon-only" data-close title="${esc(tr("common.close", "Close"))}" aria-label="${esc(tr("common.close", "Close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${olderDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.at_original", "Already at the original record."))}"` : ""}>${esc(tr("records.history.older", "← Older"))}</button>
          <div class="history-version-position"><b>${esc(versionLabel)}${isCurrent ? ` · ${esc(tr("records.history.current", "Current"))}` : ""}</b><span>${esc(versionMeta)}</span></div>
          <button class="btn" id="historyNewer" ${newerDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.at_newest", "Already at the newest version."))}"` : ""}>${esc(tr("records.history.newer", "Newer →"))}</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> ${esc(trf("records.history.fields_changed", "{count} field(s) changed in this version", { count: changed.length }))}</span><span><b>${words}</b> ${esc(tr("records.history.words", "words"))}</span><span><b>${chars}</b> ${esc(tr("records.history.characters", "characters"))}</span></div>
        ${changed.length ? `<div class="history-version-diffs">${diffs}</div>` : `<div class="info">${esc(tr("records.history.original_state", "This is the reconstructed original state before tracked updates."))}</div>`}
        <details class="history-record-preview"><summary>${esc(tr("records.history.preview", "Preview this version"))}</summary><div class="history-preview-meta"><b>${esc(work)}</b><span>${esc(authorYear)}</span></div><div class="history-preview-text">${esc(preview)}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">${esc(tr("records.history.delete_audit", "Delete audit history…"))}</button><span class="dialog-action-spacer"></span><button class="btn" data-close>${esc(tr("common.close", "Close"))}</button><button class="btn" id="historyUndoAll" ${restoreOriginalDisabled ? "disabled" : ""}>${esc(tr("records.history.restore_original", "Restore original"))}</button><button class="btn primary" id="historyRestore" ${restoreDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.already_current", "This is already the current version."))}"` : ""}>${esc(tr("records.history.restore_version", "Restore this version"))}</button></div>`;
}
