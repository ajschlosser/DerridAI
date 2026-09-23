/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";
import { llmReviewDialogHtml } from "./jobReviewMarkup";
import { recordPreviewDialogHtml } from "./recordPreviewMarkup";
import { createJobDialogCopy } from "./jobDialogCopy";
import {
  llmTaskLauncherHtml,
  llmToolResultBody,
  llmToolResultDialogHtml,
  pdfDraftRecordHtml,
} from "./llmToolMarkup";

// The dialogs opened from background jobs and LLM tasks: job details and results, RAG results, record previews, the LLM
// task launcher and the touch-up, drawn as HTML strings. Moved verbatim from the legacy runtime; the runtime's state
// object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "applyPdfLinkMatch"
  | "applyRecordChanges"
  | "canAccessPage"
  | "cancelBackgroundJob"
  | "cloneAuditValue"
  | "formatTimestamp"
  | "fullCitation"
  | "isResearcher"
  | "jobLabel"
  | "jsonPretty"
  | "label"
  | "navSnapshot"
  | "navigateTo"
  | "normalizeTouchupItems"
  | "openMessageModal"
  | "openWorkMetadataProposalResult"
  | "pages"
  | "persistFileNow"
  | "persistPrefs"
  | "providerDisplayName"
  | "providerProfile"
  | "providerProfiles"
  | "providerRequestConfig"
  | "pruneClientJobState"
  | "ragGradeHtml"
  | "recordFingerprint"
  | "recordStores"
  | "refreshJobs"
  | "refreshRagProgressPanel"
  | "refreshStores"
  | "renderView"
  | "reviewDiffSides"
  | "reviewItemFromKey"
  | "reviewKey"
  | "sanitizeResearchGeneration"
  | "shell"
  | "shellRefreshHook"
  | "showAppModal"
  | "startJobPolling"
  | "syncJobProgressToasts"
  | "toast"
  | "tr"
  | "trf"
  | "uid"
  | "upsertRecordPayload"
  | "getUrlSyncHook"
  | "warmupProviderProfile";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createJobDialogs(deps: Deps) {
  const {
    state,
    api,
    applyPdfLinkMatch,
    applyRecordChanges,
    canAccessPage,
    cancelBackgroundJob,
    cloneAuditValue,
    formatTimestamp,
    fullCitation,
    isResearcher,
    jobLabel,
    jsonPretty,
    label,
    navSnapshot,
    navigateTo,
    normalizeTouchupItems,
    openMessageModal,
    openWorkMetadataProposalResult,
    pages,
    persistFileNow,
    persistPrefs,
    providerDisplayName,
    providerProfile,
    providerProfiles,
    providerRequestConfig,
    pruneClientJobState,
    ragGradeHtml,
    recordFingerprint,
    recordStores,
    refreshJobs,
    refreshRagProgressPanel,
    refreshStores,
    renderView,
    reviewDiffSides,
    reviewItemFromKey,
    reviewKey,
    sanitizeResearchGeneration,
    shell,
    shellRefreshHook,
    showAppModal,
    startJobPolling,
    syncJobProgressToasts,
    toast,
    tr,
    trf,
    uid,
    upsertRecordPayload,
    getUrlSyncHook,
    warmupProviderProfile,
  } = deps;
  const copy = createJobDialogCopy(tr, trf);
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function openJobDetails(jobId: Any) {
    let job: Any;
    try {
      job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
    } catch (error: Any) {
      if (String(error?.message || "").includes("404")) {
        pruneClientJobState(jobId);
        persistPrefs();
        if (state.view === "rag") refreshRagProgressPanel();
        return toast(copy.operationRemoved);
      }
      return toast(copy.loadDetailsFailed(error.message));
    }
    const dialog = document.createElement("dialog");
    dialog.className = "job-details-dialog";
    const events = job.events || [];
    const request = job.request || {};
    const safeRequest = cloneAuditValue(request);
    if (safeRequest && typeof safeRequest === "object") delete safeRequest.api_key;

    const resultSummary =
      job.type === "llm"
        ? {
            pending_result_count: job.pending_result_count ?? (job.results || []).length,
            pending_proposed_changes:
              job.pending_change_count ??
              (job.results || []).reduce(
                (sum: Any, result: Any) => sum + Object.keys(result.proposal?.changes || {}).length,
                0,
              ),
            accepted_results: job.accepted_results || 0,
            accepted_fields: job.accepted_fields || 0,
            rejected_results: job.rejected_results || 0,
            rejected_fields: job.rejected_fields || 0,
            resolution_state: job.resolution_state || "pending",
            unprocessed_records:
              job.remaining_record_count ?? Math.max(0, (job.total || 0) - (job.completed || 0)),
            failures: (job.results || []).filter((result: Any) => result.error).length,
          }
        : job.type === "upsert"
          ? {
              committed: job.completed || 0,
              requested: job.total || 0,
              target_collection: job.store_name,
              language_mirrors: job.mirrored || {},
              receipt_count: (job.results || []).length,
            }
          : job.type === "pdf_corpus"
            ? {
                source_pdf: job.source_filename || null,
                build_id: job.build_id || job.id,
                raw_status: job.raw_status || job.status,
                stage: job.stage || null,
                record_count: job.record_count || 0,
                review_count: job.review_count || 0,
                unresolved_regions: job.unresolved_regions || 0,
              }
            : job.type === "llm_tool"
              ? {
                  operation: job.label || job.tool || job.mode,
                  provider_profile_id: job.provider_profile_id || null,
                  max_concurrent_requests: job.max_concurrent_requests || null,
                  has_result: Boolean(job.result),
                  result_keys:
                    job.result && typeof job.result === "object" ? Object.keys(job.result) : [],
                }
              : {
                  has_result: Boolean(job.result),
                  evidence_count: job.result?.evidence?.length || 0,
                  elapsed_seconds: job.result?.elapsed_seconds ?? null,
                  collections: job.result?.collections || [],
                  response_cache: job.result?.response_cache || job.response_cache || null,
                };

    dialog.innerHTML = `<div class="dh">
    <div><h2 class="dialog-title">${esc(trf("operations.details_title", "{label} details", { label: jobLabel(job) }))}</h2><div class="dialog-subtitle">${esc(job.id)} · ${esc(tr(`operations.status.${job.status}`, String(job.status || "")))} · ${esc(trf("operations.created", "created {when}", { when: formatTimestamp(job.created_at) }))}</div></div>
    <button class="btn icon-only" data-close>${icon("close")}</button>
  </div>
  <div class="db job-details-body">
    <section class="job-detail-summary">
      ${
        [
          [tr("operations.fact.operation", "Operation"), job.type],
          [tr("operations.fact.started_by", "Started by"), job.owner || "—"],
          [tr("operations.fact.status", "Status"), tr(`operations.status.${job.status}`, String(job.status || ""))],
          [tr("operations.fact.provider", "Provider"), job.provider],
          [tr("operations.fact.model", "Model"), job.model],
          [tr("operations.fact.progress", "Progress"), `${job.completed}/${job.total}`],
          [tr("operations.fact.failed", "Failed"), job.failed || 0],
          [tr("operations.fact.started", "Started"), job.started_at ? formatTimestamp(job.started_at) : "—"],
          [tr("operations.fact.finished", "Finished"), job.finished_at ? formatTimestamp(job.finished_at) : "—"],
          [
            tr("operations.fact.cancel_requested", "Cancel requested"),
            job.cancel_requested_at ? formatTimestamp(job.cancel_requested_at) : "—",
          ],
        ]
          .map(([name, value]) => `<div><span>${esc(name)}</span><b>${esc(value ?? "—")}</b></div>`)
          .join("")
      }
    </section>
    ${job.fatal_error ? `<div class="info error">${esc(job.fatal_error)}</div>` : ""}
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>${esc(tr("operations.request_config", "Request configuration"))}</b><div class="note">${esc(tr("operations.api_keys_omitted", "API keys are intentionally omitted."))}</div></div></div>
      <pre class="job-detail-json">${esc(JSON.stringify(safeRequest, null, 2))}</pre>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>${esc(tr("operations.timeline", "Operation timeline"))}</b><div class="note">${esc(trf("operations.recorded_events", "{count} recorded events", { count: events.length }))}</div></div></div>
      <div class="job-event-list">${events.map((event: Any, index: Any) => `<div class="job-event ${index === events.length - 1 ? "latest" : ""}"><time>${esc(formatTimestamp(event.timestamp))}</time><b>${esc(label(event.stage || "event"))}</b><span>${event.current != null && event.total != null ? `${event.current}/${event.total} · ` : ""}${esc(event.detail || "")}</span></div>`).join("") || `<div class="note">${esc(tr("operations.no_events", "No events recorded."))}</div>`}</div>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><b>${esc(tr("operations.result_summary", "Result summary"))}</b></div>
      <pre class="job-detail-json">${esc(JSON.stringify(resultSummary, null, 2))}</pre>
    </section>
  </div>
  <div class="da">
    <button class="btn" data-close>${esc(tr("ui.close", "Close"))}</button>
    ${["queued", "running", "cancelling"].includes(job.status) ? (job.cancel_requested || job.status === "cancelling" ? `<button class="btn" disabled>${esc(tr("operations.cancelling", "Cancelling…"))}</button>` : `<button class="btn danger" id="detailsCancelJob">${esc(tr("operations.cancel_operation", "Cancel operation"))}</button>`) : ""}
    ${job.type === "llm" && (job.pending_result_count ?? (job.results || []).length) > 0 ? `<button class="btn primary" id="detailsOpenResult">${esc(["queued", "running", "cancelling"].includes(job.status) ? tr("operations.panel.action_review_partial", "Review available results") : tr("operations.panel.action_review", "Review results"))}</button>` : ""}
    ${(["rag", "llm_tool"].includes(job.type) && job.status === "completed") || (job.type === "pdf_corpus" && ["completed", "blocked"].includes(job.status)) ? `<button class="btn primary" id="detailsOpenResult">${job.type === "pdf_corpus" ? esc(tr("pdf_corpus.open_build", "Open corpus build")) : esc(tr("operations.panel.action_open_result", "Open result"))}</button>` : ""}
  </div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelector("#detailsCancelJob")?.addEventListener("click", async () => {
      const updated = await cancelBackgroundJob(job.id);
      if (updated) {
        close();
        openJobDetails(job.id);
      }
    });
    dialog.querySelector("#detailsOpenResult")?.addEventListener("click", () => {
      close();
      openJobResults(job.id);
    });
  }
  async function openJobResults(jobId: Any) {
    let job: Any;
    try {
      job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
    } catch (error: Any) {
      if (String(error?.message || "").includes("404")) {
        pruneClientJobState(jobId);
        persistPrefs();
        if (state.view === "rag") refreshRagProgressPanel();
        return toast(copy.operationRemoved);
      }
      await openMessageModal({
        title: copy.openResultFailed,
        message: error.message || String(error),
        tone: "danger",
      });
      return;
    }
    try {
      if (job.type === "rag") return openRagResult(job);
      if (job.type === "llm_tool") return openLlmToolResult(job);
      if (job.type === "upsert") return openJobDetails(job.id);
      if (job.type === "pdf_corpus") {
        window.dispatchEvent(
          new CustomEvent("derridai:navigate-native", {
            detail: {
              path: `/pdf?mode=builder&build=${encodeURIComponent(job.build_id || job.id)}`,
              runtimeView: "pdf",
            },
          }),
        );
        return;
      }
    } catch (error: Any) {
      console.error("Could not render operation result", error, job);
      await openMessageModal({
        title: copy.renderResultFailed,
        message: error.message || String(error),
        detail: jobLabel(job),
        tone: "danger",
      });
      return;
    }

    const dialog = document.createElement("dialog");
    dialog.className = "job-results-dialog";
    document.body.appendChild(dialog);
    showAppModal(dialog);
    let liveTimer: Any = null;

    async function refreshJob() {
      try {
        job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
        const idx = state.jobs.findIndex((item: Any) => item.id === job.id);
        if (idx >= 0) state.jobs[idx] = { ...state.jobs[idx], ...job };
        return true;
      } catch (error: Any) {
        toast(copy.refreshFailed(error.message));
        return false;
      }
    }

    function buildData() {
      const successful = (job.results || []).filter(
        (result: Any) => !result.error && result.proposal,
      );
      const failures = (job.results || []).filter((result: Any) => result.error);
      const unchanged = [];
      const flattened = [];
      for (const result of successful) {
        const local = reviewItemFromKey(result.key);
        const currentRecord = local?.file.records[local.index];
        const stale = Boolean(
          local && result.fingerprint && recordFingerprint(currentRecord) !== result.fingerprint,
        );
        const changes = Object.entries(result.proposal?.changes || {});
        if (!changes.length) {
          unchanged.push({ result, local, stale });
          continue;
        }
        for (const [field, proposed] of changes) {
          flattened.push({
            result,
            local,
            field,
            current: currentRecord?.[field],
            proposed,
            rationale: result.proposal?.rationale?.[field] || "",
            stale,
          });
        }
      }
      return { successful, failures, unchanged, flattened };
    }

    let selections = new Set<Any>();

    function initializeSelections(flattened: Any) {
      const valid = [...selections].filter((index) => index < flattened.length);
      selections = new Set(valid);
      if (!selections.size) {
        flattened.forEach((item: Any, index: Any) => {
          if (item.field !== "text") selections.add(index);
        });
      }
    }

    async function resolveOnServer(action: Any, items: Any, { dismissJob = false } = {}) {
      return api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/resolve`, {
        method: "POST",
        body: JSON.stringify({ action, items, dismiss_job: dismissJob }),
      });
    }

    async function rejectAndDismiss() {
      if (
        !(await openMessageModal({
          title: copy.discardTitle,
          message: copy.discardMessage,
          tone: "danger",
          confirmLabel: copy.discardConfirm,
          cancelLabel: copy.discardCancel,
        }))
      )
        return;
      try {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/reject`, {
          method: "POST",
          body: JSON.stringify({ dismiss: true }),
        });
        dialog.close();
        dialog.remove();
        await refreshJobs({ rerender: state.view === "home" });
        toast(copy.rejectedRemoved);
      } catch (error: Any) {
        toast(copy.rejectFailed(error.message));
      }
    }

    async function apply(mode: Any) {
      const { successful, unchanged, flattened } = buildData();
      const batchId = uid();
      let fieldsApplied = 0;
      let _fullyReviewed = 0;
      const resolveItems = [];
      const byKey = new Map();

      for (const result of successful) {
        const local = reviewItemFromKey(result.key);
        if (local) {
          byKey.set(result.key, {
            item: local,
            result,
            fields: [],
            allFields: Object.keys(result.proposal?.changes || {}),
            rationale: result.proposal?.rationale || {},
            resolveRecord: false,
          });
        }
      }

      if (mode === "review") {
        for (const entry of byKey.values()) entry.resolveRecord = true;
      } else if (mode === "all") {
        for (const entry of byKey.values()) {
          entry.fields = [...entry.allFields];
          entry.resolveRecord = true;
        }
      } else {
        flattened.forEach((entry, index) => {
          if (!selections.has(index) || !entry.local) return;
          const target = byKey.get(entry.result.key);
          if (target) target.fields.push(entry.field);
        });
        for (const target of byKey.values()) {
          if (target.fields.length && target.fields.length === target.allFields.length) {
            target.resolveRecord = true;
          }
        }
      }

      for (const [key, target] of byKey.entries()) {
        if (mode === "selected" && !target.fields.length) continue;
        const record = target.item.file.records[target.item.index];
        const changes: Any = {};
        if (mode !== "review") {
          const sourceChanges = target.result.proposal?.changes || {};
          for (const field of target.fields) {
            if (field in sourceChanges) changes[field] = sourceChanges[field];
          }
        }

        // Clear needs_review only when the full pending proposal for this record
        // is being resolved, or the user explicitly chose "mark reviewed only".
        if (target.resolveRecord) {
          if (record.needs_review !== false) changes.needs_review = false;
          if (record.review_reason != null && record.review_reason !== "")
            changes.review_reason = null;
        }
        fieldsApplied += applyRecordChanges(target.item.file, target.item.index, changes, {
          source: "llm_review",
          model: job.model,
          batchId,
          rationale: target.rationale,
        });
        if (target.resolveRecord) _fullyReviewed++;

        resolveItems.push({
          key,
          fields: target.resolveRecord ? null : target.fields,
          resolve_record: target.resolveRecord,
        });
      }

      if (mode === "review") {
        for (const entry of unchanged) {
          if (!entry.local) continue;
          const record = entry.local.file.records[entry.local.index];
          const changes: Any = {};
          if (record.needs_review !== false) changes.needs_review = false;
          if (record.review_reason != null && record.review_reason !== "")
            changes.review_reason = null;
          fieldsApplied += applyRecordChanges(entry.local.file, entry.local.index, changes, {
            source: "llm_review",
            model: job.model,
            batchId,
            rationale: {},
          });
          _fullyReviewed++;
          resolveItems.push({ key: entry.result.key, fields: null, resolve_record: true });
        }
      } else if (mode === "all") {
        for (const entry of unchanged) {
          if (!entry.local) continue;
          const record = entry.local.file.records[entry.local.index];
          const changes: Any = {};
          if (record.needs_review !== false) changes.needs_review = false;
          if (record.review_reason != null && record.review_reason !== "")
            changes.review_reason = null;
          fieldsApplied += applyRecordChanges(entry.local.file, entry.local.index, changes, {
            source: "llm_review",
            model: job.model,
            batchId,
            rationale: {},
          });
          _fullyReviewed++;
          resolveItems.push({ key: entry.result.key, fields: null, resolve_record: true });
        }
      }

      if (!resolveItems.length) return toast(copy.noResultsSelected);

      try {
        job = await resolveOnServer("accept", resolveItems);
        state.jobApplied[job.id] = new Date().toISOString();
        persistPrefs();
        shell();
        renderView();
        await refreshJobs({ rerender: state.view === "home" });
        selections.clear();
        render({ preserveScroll: true });
        toast(
          copy.accepted(
            resolveItems.length,
            fieldsApplied,
            job.pending_result_count || 0,
          ),
        );
      } catch (error: Any) {
        toast(copy.localAppliedQueueFailed(error.message));
      }
    }

    async function rejectSelected() {
      const { flattened } = buildData();
      const grouped = new Map();
      flattened.forEach((entry, index) => {
        if (!selections.has(index)) return;
        if (!grouped.has(entry.result.key)) grouped.set(entry.result.key, []);
        grouped.get(entry.result.key).push(entry.field);
      });
      const items = [...grouped.entries()].map(([key, fields]) => ({
        key,
        fields,
        resolve_record: false,
      }));
      if (!items.length) return toast(copy.selectToReject);
      try {
        job = await resolveOnServer("reject", items);
        selections.clear();
        await refreshJobs({ rerender: state.view === "home" });
        render({ preserveScroll: true });
        toast(copy.rejectedRemain(job.pending_change_count || 0));
      } catch (error: Any) {
        toast(copy.rejectSelectedFailed(error.message));
      }
    }

    function render({ preserveScroll = false } = {}) {
      const tableBefore = dialog.querySelector(".job-change-table-wrap");
      const scrollState = preserveScroll
        ? {
            dialog: dialog.scrollTop,
            tableTop: tableBefore?.scrollTop || 0,
            tableLeft: tableBefore?.scrollLeft || 0,
          }
        : null;
      const { successful, failures, unchanged, flattened } = buildData();
      initializeSelections(flattened);
      const noChangeCount = unchanged.length;
      const active = ["queued", "running", "cancelling"].includes(job.status);
      const statusText =
        job.status === "cancelled"
          ? tr("jobs.review.cancelled_partial", "cancelled with partial results")
          : job.status;
      const pendingResults = job.pending_result_count ?? successful.length;
      const pendingChanges = job.pending_change_count ?? flattened.length;
      const remaining =
        job.remaining_record_count ?? Math.max(0, (job.total || 0) - (job.completed || 0));

      dialog.innerHTML = llmReviewDialogHtml(
        {
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
        },
        { tr, trf, label, reviewDiffSides, reviewKey },
      );

      const close = () => {
        if (liveTimer) clearInterval(liveTimer);
        dialog.close();
        dialog.remove();
      };
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      const syncSelectionUi = () => {
        dialog.querySelectorAll("[data-job-change]").forEach((box: Any) => {
          box.checked = selections.has(+box.dataset.jobChange);
        });
        const count = dialog.querySelector("#jobSelectedCount");
        if (count) count.textContent = String(selections.size);
        const applyButton = dialog.querySelector("#applyJobSelected");
        if (applyButton) applyButton.disabled = !selections.size;
      };
      dialog.querySelector("#jobSelectAll")?.addEventListener("click", () => {
        flattened.forEach((_, index) => selections.add(index));
        syncSelectionUi();
      });
      dialog.querySelector("#jobSelectNone")?.addEventListener("click", () => {
        selections.clear();
        syncSelectionUi();
      });
      dialog.querySelector("#jobRejectSelected")?.addEventListener("click", rejectSelected);
      dialog.querySelector("#rejectJob")?.addEventListener("click", rejectAndDismiss);
      dialog.querySelector("#refreshLiveResults")?.addEventListener("click", async () => {
        if (await refreshJob()) render({ preserveScroll: true });
      });
      dialog.querySelectorAll("[data-job-change]").forEach(
        (box: Any) =>
          (box.onchange = () => {
            const index = +box.dataset.jobChange;
            box.checked ? selections.add(index) : selections.delete(index);
            syncSelectionUi();
          }),
      );
      dialog.querySelectorAll("[data-preview-result]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const entry = flattened[+button.dataset.previewResult];
            if (entry?.local) openReviewRecordPreview(entry.local, entry.result);
            else toast(copy.sourceGone);
          }),
      );
      dialog.querySelectorAll("[data-preview-unchanged]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const entry = unchanged[+button.dataset.previewUnchanged];
            if (entry?.local) openReviewRecordPreview(entry.local, entry.result);
            else toast(copy.sourceGone);
          }),
      );
      dialog.querySelector("#markJobReviewed")?.addEventListener("click", () => apply("review"));
      dialog.querySelector("#applyJobSelected")?.addEventListener("click", () => apply("selected"));
      dialog.querySelector("#applyJobAll")?.addEventListener("click", () => apply("all"));
      if (scrollState)
        requestAnimationFrame(() => {
          dialog.scrollTop = scrollState.dialog;
          const table = dialog.querySelector(".job-change-table-wrap");
          if (table) {
            table.scrollTop = scrollState.tableTop;
            table.scrollLeft = scrollState.tableLeft;
          }
        });
    }

    render();
    if (["queued", "running", "cancelling"].includes(job.status)) {
      liveTimer = setInterval(async () => {
        if (!dialog.isConnected) {
          clearInterval(liveTimer);
          return;
        }
        const before = job.completed;
        const pendingBefore = job.pending_result_count;
        if (await refreshJob()) {
          if (
            job.completed !== before ||
            job.pending_result_count !== pendingBefore ||
            !["queued", "running", "cancelling"].includes(job.status)
          ) {
            render({ preserveScroll: true });
          }
          if (!["queued", "running", "cancelling"].includes(job.status)) {
            clearInterval(liveTimer);
            liveTimer = null;
          }
        }
      }, 4000);
    }
  }
  async function openRagResult(job: Any) {
    if (!job?.id)
      return toast(
        tr("research.result_unavailable", "This Research run has no result identifier."),
        { tone: "warn" },
      );
    if (!canAccessPage("rag"))
      return toast(
        tr("permissions.research_result_denied", "Your role cannot open Research results."),
        { tone: "warn" },
      );
    // v0.35.5: a RAG result is a research object, not a legacy modal. Open it in
    // the same native result workspace used by Research so typography, source
    // binding, evidence inspection, accessibility, and i18n stay identical no
    // matter where the result was launched (Operations, job history, etc.).
    state.view = "rag";
    persistPrefs();
    shellRefreshHook?.();
    const href = `/rag?job=${encodeURIComponent(job.id)}`;
    // The hook is assigned later by the app shell, so it is read when needed.
    const urlSyncHook = getUrlSyncHook();
    if (urlSyncHook) {
      urlSyncHook(href, { replace: false, snapshot: navSnapshot() });
      return;
    }
    location.assign(href);
  }
  function openReviewRecordPreview(local: Any, result: Any) {
    const record = local?.file?.records?.[local.index];
    if (!record) return toast(copy.sourceGoneWorkspace);

    const proposal = result?.proposal || {};
    const proposedFields = Object.keys(proposal.changes || {});
    const important = [
      "work",
      "document_author",
      "edition",
      "year",
      "page_start",
      "page_end",
      "region_type",
      "region_author",
      "speaker",
      "position_holder",
      "target",
      "discourse_role",
      "proposition_status",
      "semantic_function",
      "stance",
      "claim_scope",
      "is_direct_quote",
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
      "quoted_addressee",
      "quoted_referent",
      "quotation_chain",
      "topics",
      "concepts",
      "persons",
      "works_referenced",
      "document_language",
      "original_language",
      "inline_citation",
      "full_citation",
      "needs_review",
      "review_reason",
    ].filter((field) => record[field] !== undefined);

    const dialog = document.createElement("dialog");
    dialog.className = "record-preview-dialog";
    const stale = Boolean(result?.fingerprint && recordFingerprint(record) !== result.fingerprint);
    const updates = Array.isArray(record.updates) ? record.updates.slice(-8).reverse() : [];

    dialog.innerHTML = recordPreviewDialogHtml(
      { record, local, result, stale, important, proposedFields, proposal, updates },
      { tr, trf, label, pages, fullCitation, jsonPretty, formatTimestamp, reviewKey },
    );

    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelector("#previewOpenRecord").onclick = () => {
      close();
      navigateTo("record", { fileId: local.file.id, index: local.index });
    };
  }
  function openLlmToolResult(job: Any) {
    const result = job.result;
    if (!result)
      return openMessageModal({
        title: copy.resultUnavailableTitle,
        message: copy.resultUnavailable,
        tone: "danger",
      });
    const dialog = document.createElement("dialog");
    dialog.className = "llm-tool-result-dialog";
    const task = job.tool || job.mode;
    if (task === "work_metadata") {
      dialog.remove();
      return openWorkMetadataProposalResult(job);
    }
    let { body, actions } = llmToolResultBody(task, job, result, { tr, trf, ragGradeHtml });
    dialog.innerHTML = llmToolResultDialogHtml(
      { title: jobLabel(job), job, result, body, actions },
      tr,
    );
    document.body.appendChild(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    showAppModal(dialog);
    dialog.querySelector("#useToolText")?.addEventListener("click", () => {
      state.pdf.text = result.text || "";
      state.pdf.extractionSource = trf("jobs.tool.cleanup_source", "LLM cleanup · {model}", {
        model: job.model || result.model || tr("jobs.tool.model_fallback", "model"),
      });
      close();
      if (state.view === "pdf")
        window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"));
    });
    dialog.querySelector("#openToolDraft")?.addEventListener("click", () => {
      close();
      openPdfDraftRecord(result.record || {});
    });
    dialog.querySelector("#applyToolLink")?.addEventListener("click", async () => {
      await applyPdfLinkMatch(result.match || {});
      close();
    });
  }
  function openLlmTaskLauncher({
    task,
    title,
    description = "",
    contextText = "",
    payload = {},
    generationProvider = null,
    generationModel = null,
    onForegroundResult = null,
  }: Any = {}) {
    const profiles = providerProfiles();
    if (!profiles.length) return toast(copy.configureProvider);
    let profileId = state.appConfig.default_provider_profile || profiles[0].id;
    if (task === "rag_grade" && generationModel) {
      const independent = profiles.find(
        (item: Any) =>
          !(
            item.type === generationProvider && String(item.model || "") === String(generationModel)
          ),
      );
      if (independent) profileId = independent.id;
    }
    let runMode =
      task === "rag_grade_batch" ? "background" : isResearcher() ? "foreground" : "background";
    const dialog = document.createElement("dialog");
    dialog.className = "llm-tool-launcher";

    const render = () => {
      const profile = providerProfile(profileId);
      const status = state.providerStatuses?.[profile.id] || {};
      const sameModel = Boolean(
        generationModel &&
          String(profile.model || "") === String(generationModel) &&
          (!generationProvider || profile.type === generationProvider),
      );
      dialog.innerHTML = llmTaskLauncherHtml(
        {
          title,
          description,
          contextText,
          sameModel,
          profiles,
          profile,
          status,
          task,
          runMode,
          isResearcher: isResearcher(),
          providerDisplayName,
        },
        tr,
      );
      const close = () => {
        dialog.close();
        dialog.remove();
      };
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      dialog.querySelector("#toolProvider").onchange = (e: Any) => {
        profileId = e.target.value;
        render();
      };
      dialog.querySelector("#toolRunMode").onchange = (e: Any) => {
        runMode = e.target.value;
        render();
      };
      dialog.querySelector("#toolProviders")?.addEventListener("click", () => {
        close();
        navigateTo("providers");
      });
      dialog.querySelector("#toolWarm").onclick = async () => {
        const el = dialog.querySelector("#toolStatus");
        el.textContent = tr("providers.warming", "Warming...");
        await warmupProviderProfile(profileId);
        el.textContent = state.providerWarmups?.[profileId]?.message || tr("jobs.tool.warmup_requested", "Warmup requested");
      };
      dialog.querySelector("#runLlmTask").onclick = async () => {
        const active = providerProfile(profileId);
        if (!active) return toast(copy.chooseProfile);
        if (!["ollama", "openai"].includes(String(active.type || "")))
          return toast(copy.profileUnsupported);
        const config = providerRequestConfig(active, { textReview: true });
        let extra: Any = {};
        try {
          extra = JSON.parse(dialog.querySelector("#toolExtra").value || "{}");
          if (!extra || Array.isArray(extra) || typeof extra !== "object")
            throw new Error("Advanced options must be an object");
        } catch (error: Any) {
          return toast(error.message);
        }
        const n = (id: Any) => {
          const raw = dialog.querySelector(`#${id}`)?.value;
          if (raw === "" || raw == null) return null;
          const value = Number(raw);
          return Number.isFinite(value) ? value : null;
        };
        let think = false;
        if (active.type === "ollama") {
          const raw = dialog.querySelector("#toolThink")?.value || "false";
          think = raw === "true" ? true : ["low", "medium", "high"].includes(raw) ? raw : false;
        }
        const generation = sanitizeResearchGeneration({
          ...config.ollama,
          num_ctx: active.type === "ollama" ? n("toolCtx") : null,
          num_predict: n("toolPredict") ?? 4096,
          think,
          temperature: n("toolTemp") ?? 0,
          top_p: n("toolTopP") ?? 1,
          seed: n("toolSeed"),
          extra_options: extra,
        });
        const model =
          active.type === "openai" && active.model_mode === "auto"
            ? "auto"
            : String(dialog.querySelector("#toolModel")?.value || "").trim();
        if (!model) return toast(copy.selectModel);
        if (
          task === "rag_grade" &&
          (!String(payload.question || "").trim() || !String(payload.answer || "").trim())
        )
          return toast(copy.gradeRequiresQa);
        const direct = {
          ...payload,
          provider: active.type,
          model,
          base_url: active.base_url || null,
          api_key: active.type === "openai" ? active.api_key || "" : null,
          generation,
        };
        const button = dialog.querySelector("#runLlmTask");
        button.disabled = true;
        button.textContent = runMode === "background" ? tr("jobs.tool.starting", "Starting…") : tr("jobs.tool.running", "Running…");
        try {
          if (runMode === "background") {
            const body = {
              task,
              label: title,
              provider_profile_id: active.id,
              max_concurrent_requests: Math.max(
                1,
                Math.min(64, Number(active.max_concurrent_requests) || 1),
              ),
              pdf: task.startsWith("pdf_") ? direct : null,
              grade: task === "rag_grade" ? direct : null,
              grade_batch:
                task === "rag_grade_batch"
                  ? {
                      provider: direct.provider,
                      model: direct.model,
                      base_url: direct.base_url,
                      api_key: direct.api_key,
                      generation: direct.generation,
                      provider_profile_id: active.id,
                      max_concurrent_requests: Math.max(
                        1,
                        Math.min(64, Number(active.max_concurrent_requests) || 1),
                      ),
                    }
                  : null,
            };
            const job = await api("/api/jobs/llm-tool", {
              method: "POST",
              body: JSON.stringify(body),
            });
            state.jobs = [job, ...state.jobs.filter((item: Any) => item.id !== job.id)];
            syncJobProgressToasts();
            startJobPolling();
            close();
            toast(copy.startedBackground(title));
          } else {
            if (task === "rag_grade_batch")
              throw new Error("Cache-wide grading runs as a background operation.");
            const endpoint = task === "rag_grade" ? "/api/rag/grade" : "/api/pdf/llm";
            const result = await api(endpoint, { method: "POST", body: JSON.stringify(direct) });
            close();
            if (onForegroundResult) await onForegroundResult(result);
          }
        } catch (error: Any) {
          button.disabled = false;
          button.innerHTML = `${icon("spark")}${runMode === "background" ? tr("jobs.tool.start_background", "Start background operation") : tr("jobs.tool.run_now", "Run now")}`;
          toast(copy.failed(title, error.message));
        }
      };
    };
    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  function openPdfDraftRecord(record: Any) {
    const dialog = document.createElement("dialog");
    dialog.className = "pdf-draft-dialog";
    const files = state.files;
    const stores = recordStores();
    dialog.innerHTML = pdfDraftRecordHtml(
      {
        title: state.pdf.title || state.pdf.name,
        page: state.pdf.page,
        recordJson: JSON.stringify(record, null, 2),
        files,
        stores,
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
    dialog.querySelector("#savePdfDraft").onclick = async () => {
      let draft: Any;
      try {
        draft = JSON.parse(dialog.querySelector("#pdfDraftJson").value);
        if (!draft || typeof draft !== "object" || Array.isArray(draft))
          throw new Error("Draft must be one JSON object.");
      } catch (error: Any) {
        return toast(copy.invalidDraft(error.message));
      }
      if (!draft.record_id) draft.record_id = `pdf-draft-${Date.now()}`;
      draft.needs_review = true;
      draft.updates = Array.isArray(draft.updates) ? draft.updates : [];
      draft.pdf_file = state.pdf.name || draft.pdf_file || null;
      draft.pdf_pages = [
        ...new Set([...(Array.isArray(draft.pdf_pages) ? draft.pdf_pages : []), state.pdf.page]),
      ].sort((a, b) => a - b);
      draft.text_length = String(draft.text || "").length;

      const fileId = dialog.querySelector("#pdfDraftFile").value;
      const storeName = dialog.querySelector("#pdfDraftStore").value;
      if (!fileId && !storeName) return toast(copy.chooseDestination);

      if (fileId) {
        const file = state.files.find((item: Any) => item.id === fileId);
        if (!file) return toast(copy.jsonlGone);
        file.records.push(cloneAuditValue(draft));
        file.dirty.add(file.records.length - 1);
        await persistFileNow(file);
      }
      if (storeName) {
        try {
          await api(`/api/stores/${encodeURIComponent(storeName)}/records`, {
            method: "POST",
            body: JSON.stringify({ record: upsertRecordPayload(draft) }),
          });
          await refreshStores();
        } catch (error: Any) {
          return toast(copy.chromaUpsertFailed(error.message));
        }
      }
      close();
      shell();
      renderView();
      toast(
        fileId && storeName
          ? copy.draftAddedBoth(draft.record_id)
          : fileId
            ? copy.draftAddedJsonl(draft.record_id)
            : copy.draftAddedChroma(draft.record_id),
        { tone: "success" },
      );
    };
  }
  function openTouchup(inputItems = null, initialMode = "foreground") {
    const items = normalizeTouchupItems(inputItems);
    if (!items.length) return;
    window.dispatchEvent(
      new CustomEvent("derridai:open-touchup", { detail: { items, initialMode } }),
    );
  }
  return {
    openJobDetails,
    openJobResults,
    openRagResult,
    openReviewRecordPreview,
    openLlmToolResult,
    openLlmTaskLauncher,
    openPdfDraftRecord,
    openTouchup,
  };
}
