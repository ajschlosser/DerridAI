/* Copyright 2026 Aaron John Schlosser, PhD. */

import { bindCopy } from "../i18n/bindCopy";
import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function recordEditorHtml(input: { subtitle: string; groups: string }, tr: Tr): string {
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
