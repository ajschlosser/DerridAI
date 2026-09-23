/* Copyright 2026 Aaron John Schlosser, PhD. */

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
  const { tr, trf, label, reviewDiffSides, reviewKey } = deps;
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
    ? `<div class="job-change-table-wrap"><table class="job-change-table"><thead><tr><th></th><th>${esc(tr("jobs.review.record_col", "Record"))}</th><th>${esc(tr("works.field", "Field"))}</th><th>${esc(tr("jobs.review.current", "Current"))}</th><th>${esc(tr("jobs.review.proposed", "Proposed"))}</th><th>${esc(tr("jobs.review.rationale", "Rationale"))}</th></tr></thead><tbody>${flattened
        .map((item, index) => {
          const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
          const diff = reviewDiffSides(item.current, item.proposed);
          return `<tr class="${item.stale ? "stale-change" : ""}"><td><input type="checkbox" data-job-change="${index}" ${selections.has(index) ? "checked" : ""}></td><td><div class="job-record-cell"><b>${esc(rid)}</b>${item.local ? `<button class="btn tiny" data-copy-row-key="${esc(reviewKey(item.local.file, item.local.index))}">${icon("copy")}${esc(tr("ui.copy", "Copy"))}</button>` : ""}<button class="btn tiny" data-preview-result="${index}">${esc(tr("jobs.review.preview", "Preview record"))}</button>${item.stale ? `<span class="stale-badge">${esc(tr("jobs.review.stale", "local record changed since job started"))}</span>` : ""}</div></td><td><b>${esc(label(item.field))}</b></td><td><pre class="change-diff current-diff">${diff.left}</pre></td><td><pre class="change-diff proposed-diff">${diff.right}</pre></td><td>${esc(item.rationale || tr("jobs.review.no_rationale", "No rationale supplied."))}</td></tr>`;
        })
        .join("")}</tbody></table></div>`
    : `<section class="review-no-changes-empty"><div class="review-no-changes-icon">✓</div><div><h3>${esc(active ? tr("jobs.review.no_pending_yet", "No pending changes yet") : tr("jobs.review.no_changes", "No changes proposed"))}</h3><p>${esc(active ? trf("jobs.review.still_running", "The review is still running. {completed} records have completed and {remaining} remain unprocessed.", { completed: job.completed.toLocaleString(), remaining: remaining.toLocaleString() }) : trf("jobs.review.none_proposed", "The model reviewed {count} record(s) and did not propose metadata/text edits.", { count: noChangeCount.toLocaleString() }))}</p></div></section>`;

  const unchangedSection = noChangeCount
    ? `<details class="unchanged-review-list" ${flattened.length ? "" : "open"}><summary><span><b>${esc(trf("jobs.review.no_change_count", "{count} record(s) with no proposed changes", { count: noChangeCount.toLocaleString() }))}</b><small>${esc(tr("jobs.review.expand_inspect", "Expand to inspect or preview these records"))}</small></span></summary><div class="unchanged-review-grid">${unchanged
        .map((item, index) => {
          const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
          return `<div class="unchanged-review-row"><div><b>${esc(rid)}</b><span>${esc(item.local?.record?.work || "")}${item.stale ? ` · ${esc(tr("jobs.review.stale_review", "local record changed since review"))}` : ""}</span></div><button class="btn tiny" data-preview-unchanged="${index}">${esc(tr("jobs.review.preview", "Preview record"))}</button></div>`;
        })
        .join("")}</div></details>`
    : "";

  const title =
    job.mode === "auto"
      ? tr("jobs.review.auto_title", "Auto-improve changes")
      : tr("jobs.review.title", "LLM review changes");
  const subtitle = trf(
    "jobs.review.subtitle",
    "{completed}/{total} processed · {pendingResults} pending result(s) · {pendingChanges} pending change(s) · {remaining} unprocessed · {failures} failures · {status}",
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

  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(subtitle)}</div></div><div class="tools">${active ? `<span class="job-status running">${esc(tr("jobs.review.live", "live"))}</span>` : ""}<button class="btn icon-only" data-close>${icon("close")}</button></div></div>
    <div class="db job-change-review">
      <div class="job-resolution-summary">
        <span><b>${job.accepted_results || 0}</b> ${esc(tr("jobs.review.accepted_results", "accepted results"))}</span>
        <span><b>${job.accepted_fields || 0}</b> ${esc(tr("jobs.review.accepted_fields", "accepted fields"))}</span>
        <span><b>${job.rejected_results || 0}</b> ${esc(tr("jobs.review.rejected_results", "rejected results"))}</span>
        <span><b>${job.rejected_fields || 0}</b> ${esc(tr("jobs.review.rejected_fields", "rejected fields"))}</span>
        <span><b>${esc(tr(`operations.decision.${job.resolution_state || "pending"}`, String(job.resolution_state || "pending").replaceAll("_", " ")))}</b> ${esc(tr("jobs.review.decision_state", "decision state"))}</span>
      </div>
      ${flattened.length ? `<div class="job-change-toolbar"><button class="btn small" id="jobSelectAll">${esc(tr("jobs.review.select_all", "Select all changes"))}</button><button class="btn small" id="jobSelectNone">${esc(tr("jobs.review.select_none", "Select none"))}</button><button class="btn small danger" id="jobRejectSelected">${esc(tr("jobs.review.reject_selected", "Reject selected"))}</button><span class="note"><b id="jobSelectedCount">${selected}</b> ${esc(tr("jobs.review.selected_help", "selected · accepted changes are removed from this pending queue immediately"))}</span></div>` : ""}
      ${failures.length ? `<div class="info warn">${failures.map((result: Any) => `${esc(result.record_id || result.key)}: ${esc(result.error?.message || tr("jobs.review.failed", "failed"))}`).join("<br>")}</div>` : ""}
      ${changeTable}
      ${unchangedSection}
    </div>
    <div class="da">
      <button class="btn" data-close>${esc(tr("ui.close", "Close"))}</button>
      ${active && remaining > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}${esc(tr("jobs.review.stop_discard", "Stop review & discard pending"))}</button>` : pendingResults > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}${esc(tr("jobs.review.discard_remove", "Discard pending & remove operation"))}</button>` : ""}
      ${active ? `<button class="btn" id="refreshLiveResults">${icon("refresh")}${esc(tr("jobs.review.refresh", "Refresh available results"))}</button>` : ""}
      ${successful.length ? `<button class="btn" id="markJobReviewed">${icon("check")}${esc(tr("jobs.review.mark_reviewed", "Mark all available reviewed"))}</button>${flattened.length ? `<button class="btn primary" id="applyJobSelected" ${selected ? "" : "disabled"}>${icon("check")}${esc(tr("jobs.review.apply_selected", "Apply selected"))}</button><button class="btn soft" id="applyJobAll">${icon("check")}${esc(tr("jobs.review.accept_all", "Accept all available"))}</button>` : ""}` : ""}
    </div>`;
}
