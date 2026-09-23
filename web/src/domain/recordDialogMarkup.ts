/* Copyright 2026 Aaron John Schlosser, PhD. */

import { bindCopy } from "../i18n/bindCopy";
import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function mergeDialogHtml(files: Any[], deps: { tr: Tr; trf: Trf }): string {
  const { tr, trf } = { ...deps, ...bindCopy(deps.tr, deps.trf) };
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("records.merge.title"))}</h2><div class="dialog-subtitle">${esc(tr("records.merge.subtitle"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">${esc(tr("ui.select_all"))}</button><button class="btn small" id="mergeSelectNone">${esc(tr("ui.clear"))}</button></div><div class="merge-file-list">${files.map((file: Any) => `<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${esc(trf("records.merge.file_records", { count: file.records.length.toLocaleString() }))}</small></span></label>`).join("")}</div><div class="field"><label>${esc(tr("records.merge.filename"))}</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>${esc(tr("records.merge.download"))}</span></label><div class="info">${esc(tr("records.merge.help"))}</div></div><div class="da"><button class="btn" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary" id="mergeCreate">${esc(tr("records.merge.create"))}</button></div>`;
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
  const { tr, trf } = { ...deps, ...bindCopy(deps.tr, deps.trf) };
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
    ? `<div class="info">${esc(trf("records.bulk.in_operation", { count: fixedRows.length.toLocaleString() }))}</div>`
    : `<div class="field"><label>${esc(tr("records.bulk.target"))}</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope === "selected" ? "selected" : ""} ${selectedCount ? "" : "disabled"}>${esc(trf("records.bulk.selected", { count: selectedCount.toLocaleString() }))}</option><option value="active" ${defaultScope === "active" ? "selected" : ""}>${esc(trf("records.bulk.active", { count: activeCount.toLocaleString() }))}</option>${currentWork ? `<option value="work">${esc(trf("records.bulk.work", { work: currentWork }))}</option>` : ""}<option value="all">${esc(trf("records.bulk.all", { count: allCount.toLocaleString() }))}</option></select></div>`;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(tr("records.bulk.subtitle"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${scope}
    <div class="field"><label>${esc(tr("works.field"))}</label><select class="control" id="bulkFieldName">${fieldOptions}</select></div>
    <div class="field"><label>${esc(tr("records.bulk.new_value"))}</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="${esc(tr("records.bulk.placeholder"))}"></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>${esc(tr("records.bulk.only_different"))}</span></label>
  </div>
  <div class="da"><button class="btn" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary" id="applyBulkField">${icon("check")}${esc(tr("records.bulk.apply"))}</button></div>`;
}

export function ocrCleanupDialogHtml(
  input: { active: Any; selectedCount: number; reviewCount: number; allCount: number; fileCount: number },
  deps: { tr: Tr; trf: Trf },
): string {
  const { tr, trf } = { ...deps, ...bindCopy(deps.tr, deps.trf) };
  const { active, selectedCount, reviewCount, allCount, fileCount } = input;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("ui.clean_ocr"))}</h2><div class="dialog-subtitle">${esc(tr("records.ocr.subtitle"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active ? "" : "disabled"}><b>${esc(tr("records.ocr.active_tab"))}</b><span>${active ? esc(trf("records.ocr.active_meta", { count: active.records.length.toLocaleString(), name: active.name })) : esc(tr("records.ocr.no_tab"))}</span></button><button class="scope-card" data-scope="selected" ${selectedCount ? "" : "disabled"}><b>${esc(tr("records.ocr.selected"))}</b><span>${esc(trf("records.ocr.selected_meta", { count: selectedCount.toLocaleString() }))}</span></button><button class="scope-card" data-scope="review"><b>${esc(tr("records.ocr.review"))}</b><span>${esc(trf("records.ocr.review_meta", { count: reviewCount.toLocaleString() }))}</span></button><button class="scope-card" data-scope="all"><b>${esc(tr("records.ocr.all"))}</b><span>${esc(trf("records.ocr.all_meta", { count: allCount.toLocaleString(), tabs: fileCount }))}</span></button></div><div class="da"><button class="btn" data-close>${esc(tr("common.cancel"))}</button></div>`;
}

export function recordEditorHtml(
  input: { subtitle: string; groups: string },
  tr: Tr,
): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("record.edit"))}</h2><div class="dialog-subtitle">${esc(input.subtitle)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${input.groups}</div><div class="da"><div class="llm-footer-note">${esc(tr("records.editor.local_note"))}</div><button class="btn" type="button" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.editor.save"))}</button></div></form>`;
}

export function chromaRecordEditorHtml(
  input: { chromaId: string; store: string; fields: string },
  tr: Tr,
): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("records.chroma.edit"))}</h2><div class="dialog-subtitle">${esc(input.chromaId)} · ${esc(input.store)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">${esc(tr("records.chroma.help"))}</div><section class="editor-section"><h3>${esc(tr("records.chroma.section"))}</h3><div class="editor-grid">${input.fields}</div></section></div><div class="da"><button class="btn" type="button" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.chroma.save"))}</button></div></form>`;
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
  const { tr, trf } = { ...deps, ...bindCopy(deps.tr, deps.trf) };
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
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("records.history.title"))}</h2><div class="dialog-subtitle">${esc(recordId)} · ${esc(trf("records.history.changesets", { count: changeSets }))}</div></div><button class="btn icon-only" data-close title="${esc(tr("common.close"))}" aria-label="${esc(tr("common.close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${olderDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.at_original"))}"` : ""}>${esc(tr("records.history.older"))}</button>
          <div class="history-version-position"><b>${esc(versionLabel)}${isCurrent ? ` · ${esc(tr("records.history.current"))}` : ""}</b><span>${esc(versionMeta)}</span></div>
          <button class="btn" id="historyNewer" ${newerDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.at_newest"))}"` : ""}>${esc(tr("records.history.newer"))}</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> ${esc(trf("records.history.fields_changed", { count: changed.length }))}</span><span><b>${words}</b> ${esc(tr("records.history.words"))}</span><span><b>${chars}</b> ${esc(tr("records.history.characters"))}</span></div>
        ${changed.length ? `<div class="history-version-diffs">${diffs}</div>` : `<div class="info">${esc(tr("records.history.original_state"))}</div>`}
        <details class="history-record-preview"><summary>${esc(tr("records.history.preview"))}</summary><div class="history-preview-meta"><b>${esc(work)}</b><span>${esc(authorYear)}</span></div><div class="history-preview-text">${esc(preview)}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">${esc(tr("records.history.delete_audit"))}</button><span class="dialog-action-spacer"></span><button class="btn" data-close>${esc(tr("common.close"))}</button><button class="btn" id="historyUndoAll" ${restoreOriginalDisabled ? "disabled" : ""}>${esc(tr("records.history.restore_original"))}</button><button class="btn primary" id="historyRestore" ${restoreDisabled ? `disabled data-disabled-reason="${esc(tr("records.history.already_current"))}"` : ""}>${esc(tr("records.history.restore_version"))}</button></div>`;
}
