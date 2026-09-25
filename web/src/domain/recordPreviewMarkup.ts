/* Copyright 2026 Aaron John Schlosser, PhD. */

import { bindCopy } from "../i18n/bindCopy";
import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

/** Markup + copy for the record preview dialog used by LLM review. */
export function recordPreviewDialogHtml(
  input: {
    record: Any;
    local: Any;
    result: Any;
    stale: boolean;
    important: string[];
    proposedFields: string[];
    proposal: Any;
    updates: Any[];
  },
  deps: {
    tr: Tr;
    trf: Trf;
    label: (key: string) => string;
    pages: (record: Any) => string;
    fullCitation: (record: Any) => string;
    jsonPretty: (value: unknown) => string;
    formatTimestamp: (value: unknown) => string;
    reviewKey: (file: Any, index: number) => string;
  },
): string {
  const { tr, trf, label, pages, fullCitation, jsonPretty, formatTimestamp, reviewKey } = {
    ...deps,
    ...bindCopy(deps.tr, deps.trf),
  };
  const { record, local, stale, important, proposedFields, proposal, updates } = input;
  const titleId = record.record_id || trf("dashboard.record_n", { n: local.index + 1 });
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("jobs.preview.title"))}</h2><div class="dialog-subtitle">${esc(titleId)} · ${esc(record.work || local.file.name)} · ${esc(local.file.name)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db record-preview-body">
    ${stale ? `<div class="info warn">${esc(tr("jobs.preview.stale"))}</div>` : ""}
    <section class="record-preview-summary">
      <div><span>${esc(tr("jobs.preview.record_id"))}</span><b>${esc(record.record_id || "—")}</b></div>
      <div><span>${esc(tr("jobs.preview.work"))}</span><b>${esc(record.work || "—")}</b></div>
      <div><span>${esc(tr("jobs.preview.pages"))}</span><b>${esc(pages(record))}</b></div>
      <div><span>${esc(tr("jobs.preview.citation"))}</span><b>${esc(fullCitation(record) || "—")}</b></div>
      <div><span>${esc(tr("jobs.preview.llm_proposals"))}</span><b>${proposedFields.length}</b></div>
      <div><span>${esc(tr("jobs.preview.needs_review"))}</span><b>${record.needs_review ? esc(tr("common.yes")) : esc(tr("common.no"))}</b></div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>${esc(tr("jobs.preview.metadata"))}</b><span>${esc(trf("jobs.preview.populated_fields", { count: important.length }))}</span></div>
      <div class="record-preview-metadata">${important.map((field) => `<div class="record-preview-field ${proposedFields.includes(field) ? "proposed-field" : ""}"><span>${esc(label(field))}${proposedFields.includes(field) ? `<i>${esc(tr("jobs.preview.proposed_change"))}</i>` : ""}</span><pre>${esc(jsonPretty(record[field]))}</pre></div>`).join("")}</div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>${esc(tr("jobs.preview.text"))}</b><span>${esc(trf("jobs.preview.characters", { count: String(record.text || "").length.toLocaleString() }))}</span></div>
      <pre class="record-preview-text">${esc(record.text || "")}</pre>
    </section>

    ${proposedFields.length ? `<section class="record-preview-section"><div class="record-preview-heading"><b>${esc(tr("jobs.preview.proposed_for_record"))}</b><span>${proposedFields.length}</span></div><div class="record-preview-proposals">${proposedFields.map((field) => `<div><b>${esc(label(field))}</b><div class="record-preview-proposal-grid"><pre>${esc(jsonPretty(record[field]))}</pre><span>→</span><pre>${esc(jsonPretty(proposal.changes[field]))}</pre></div>${proposal.rationale?.[field] ? `<small>${esc(proposal.rationale[field])}</small>` : ""}</div>`).join("")}</div></section>` : ""}

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>${esc(tr("jobs.preview.audit"))}</b><span>${esc(trf("jobs.preview.shown", { count: updates.length }))}</span></div>
      <div class="record-preview-history">${updates.map((update: Any) => `<div><time>${esc(formatTimestamp(update.timestamp))}</time><b>${esc(label(update.field_name || "field"))}</b><span>${esc(update.source || tr("jobs.preview.manual"))}${update.initiated_by ? ` · ${esc(update.initiated_by)}` : ""}</span></div>`).join("") || `<div class="note">${esc(tr("jobs.preview.no_audit"))}</div>`}</div>
    </section>
  </div>
  <div class="da"><button class="btn" data-close>${esc(tr("jobs.preview.close"))}</button><button class="btn" data-copy-row-key="${esc(reviewKey(local.file, local.index))}">${icon("copy")}${esc(tr("pdf.copy_entire"))}</button><button class="btn primary" id="previewOpenRecord">${icon("arrow")}${esc(tr("jobs.preview.open_full"))}</button></div>`;
}
