/* Copyright 2026 Aaron John Schlosser, PhD. */

import { bindCopy } from "../i18n/bindCopy";
import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

/** Markup + copy for the LLM review / auto-improve dialog. */
export function llmReviewDialogHtml(
  input: {
    job: Any;
    flattened: Any[];
    unchanged: Any[];
    failures: Any[];
    selections: Set<number>;
    successful: Any[];
    active: boolean;
    remaining: number;
    pendingResults: number;
    pendingChanges: number;
    noChangeCount: number;
    statusText: string;
  },
  deps: {
    tr: Tr;
    trf: Trf;
    label: (key: string) => string;
    reviewDiffSides: (current: unknown, proposed: unknown) => { left: string; right: string };
    reviewKey: (file: Any, index: number) => string;
  },
): string {
  const { tr, trf, label, reviewDiffSides, reviewKey } = { ...deps, ...bindCopy(deps.tr, deps.trf) };
  const {
    job,
    flattened,
    unchanged,
    failures,
    selections,
    successful,
    active,
    remaining,
    pendingResults,
    pendingChanges,
    noChangeCount,
    statusText,
  } = input;
  const selected = selections.size;
  const changeTable = flattened.length
    ? `<div class="job-change-table-wrap"><table class="job-change-table"><thead><tr><th></th><th>${esc(tr("jobs.review.record_col"))}</th><th>${esc(tr("works.field"))}</th><th>${esc(tr("jobs.review.current"))}</th><th>${esc(tr("jobs.review.proposed"))}</th><th>${esc(tr("jobs.review.rationale"))}</th></tr></thead><tbody>${flattened
        .map((item, index) => {
          const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
          const diff = reviewDiffSides(item.current, item.proposed);
          return `<tr class="${item.stale ? "stale-change" : ""}"><td><input type="checkbox" data-job-change="${index}" ${selections.has(index) ? "checked" : ""}></td><td><div class="job-record-cell"><b>${esc(rid)}</b>${item.local ? `<button class="btn tiny" data-copy-row-key="${esc(reviewKey(item.local.file, item.local.index))}">${icon("copy")}${esc(tr("ui.copy"))}</button>` : ""}<button class="btn tiny" data-preview-result="${index}">${esc(tr("jobs.review.preview"))}</button>${item.stale ? `<span class="stale-badge">${esc(tr("jobs.review.stale"))}</span>` : ""}</div></td><td><b>${esc(label(item.field))}</b></td><td><pre class="change-diff current-diff">${diff.left}</pre></td><td><pre class="change-diff proposed-diff">${diff.right}</pre></td><td>${esc(item.rationale || tr("jobs.review.no_rationale"))}</td></tr>`;
        })
        .join("")}</tbody></table></div>`
    : `<section class="review-no-changes-empty"><div class="review-no-changes-icon">✓</div><div><h3>${esc(active ? tr("jobs.review.no_pending_yet") : tr("jobs.review.no_changes"))}</h3><p>${esc(active ? trf("jobs.review.still_running", { completed: job.completed.toLocaleString(), remaining: remaining.toLocaleString() }) : trf("jobs.review.none_proposed", { count: noChangeCount.toLocaleString() }))}</p></div></section>`;

  const unchangedSection = noChangeCount
    ? `<details class="unchanged-review-list" ${flattened.length ? "" : "open"}><summary><span><b>${esc(trf("jobs.review.no_change_count", { count: noChangeCount.toLocaleString() }))}</b><small>${esc(tr("jobs.review.expand_inspect"))}</small></span></summary><div class="unchanged-review-grid">${unchanged
        .map((item, index) => {
          const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
          return `<div class="unchanged-review-row"><div><b>${esc(rid)}</b><span>${esc(item.local?.record?.work || "")}${item.stale ? ` · ${esc(tr("jobs.review.stale_review"))}` : ""}</span></div><button class="btn tiny" data-preview-unchanged="${index}">${esc(tr("jobs.review.preview"))}</button></div>`;
        })
        .join("")}</div></details>`
    : "";

  const title =
    job.mode === "auto"
      ? tr("jobs.review.auto_title")
      : tr("jobs.review.title");
  const subtitle = trf("jobs.review.subtitle",
    {
      completed: job.completed,
      total: job.total,
      pendingResults,
      pendingChanges,
      remaining,
      failures: failures.length,
      status: statusText,
    },
  );

  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(subtitle)}</div></div><div class="tools">${active ? `<span class="job-status running">${esc(tr("jobs.review.live"))}</span>` : ""}<button class="btn icon-only" data-close>${icon("close")}</button></div></div>
    <div class="db job-change-review">
      <div class="job-resolution-summary">
        <span><b>${job.accepted_results || 0}</b> ${esc(tr("jobs.review.accepted_results"))}</span>
        <span><b>${job.accepted_fields || 0}</b> ${esc(tr("jobs.review.accepted_fields"))}</span>
        <span><b>${job.rejected_results || 0}</b> ${esc(tr("jobs.review.rejected_results"))}</span>
        <span><b>${job.rejected_fields || 0}</b> ${esc(tr("jobs.review.rejected_fields"))}</span>
        <span><b>${esc(tr(`operations.decision.${job.resolution_state || "pending"}`, String(job.resolution_state || "pending").replaceAll("_", " ")))}</b> ${esc(tr("jobs.review.decision_state"))}</span>
      </div>
      ${flattened.length ? `<div class="job-change-toolbar"><button class="btn small" id="jobSelectAll">${esc(tr("jobs.review.select_all"))}</button><button class="btn small" id="jobSelectNone">${esc(tr("jobs.review.select_none"))}</button><button class="btn small danger" id="jobRejectSelected">${esc(tr("jobs.review.reject_selected"))}</button><span class="note"><b id="jobSelectedCount">${selected}</b> ${esc(tr("jobs.review.selected_help"))}</span></div>` : ""}
      ${failures.length ? `<div class="info warn">${failures.map((result: Any) => `${esc(result.record_id || result.key)}: ${esc(result.error?.message || tr("jobs.review.failed"))}`).join("<br>")}</div>` : ""}
      ${changeTable}
      ${unchangedSection}
    </div>
    <div class="da">
      <button class="btn" data-close>${esc(tr("ui.close"))}</button>
      ${active && remaining > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}${esc(tr("jobs.review.stop_discard"))}</button>` : pendingResults > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}${esc(tr("jobs.review.discard_remove"))}</button>` : ""}
      ${active ? `<button class="btn" id="refreshLiveResults">${icon("refresh")}${esc(tr("jobs.review.refresh"))}</button>` : ""}
      ${successful.length ? `<button class="btn" id="markJobReviewed">${icon("check")}${esc(tr("jobs.review.mark_reviewed"))}</button>${flattened.length ? `<button class="btn primary" id="applyJobSelected" ${selected ? "" : "disabled"}>${icon("check")}${esc(tr("jobs.review.apply_selected"))}</button><button class="btn soft" id="applyJobAll">${icon("check")}${esc(tr("jobs.review.accept_all"))}</button>` : ""}` : ""}
    </div>`;
}
