/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;

export function recordEditorHtml(input: { subtitle: string; groups: string }, tr: Tr): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("record.edit"))}</h2><div class="dialog-subtitle">${esc(input.subtitle)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${input.groups}</div><div class="da"><div class="llm-footer-note">${esc(tr("records.editor.local_note"))}</div><button class="btn" type="button" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.editor.save"))}</button></div></form>`;
}

export function chromaRecordEditorHtml(
  input: { chromaId: string; store: string; fields: string },
  tr: Tr,
): string {
  return `<form><div class="dh"><div><h2 class="dialog-title">${esc(tr("records.chroma.edit"))}</h2><div class="dialog-subtitle">${esc(input.chromaId)} · ${esc(input.store)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">${esc(tr("records.chroma.help"))}</div><section class="editor-section"><h3>${esc(tr("records.chroma.section"))}</h3><div class="editor-grid">${input.fields}</div></section></div><div class="da"><button class="btn" type="button" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary">${icon("check")}${esc(tr("records.chroma.save"))}</button></div></form>`;
}
