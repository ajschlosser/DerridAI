/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

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
    uid,
    upsertRecordPayload,
    getUrlSyncHook,
    warmupProviderProfile,
  } = deps;
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
        return toast("This operation was removed and has been cleared from the activity view");
      }
      return toast(`Could not load operation details: ${error.message}`);
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
    <div><h2 class="dialog-title">${esc(jobLabel(job))} details</h2><div class="dialog-subtitle">${esc(job.id)} · ${esc(job.status)} · created ${esc(formatTimestamp(job.created_at))}</div></div>
    <button class="btn icon-only" data-close>${icon("close")}</button>
  </div>
  <div class="db job-details-body">
    <section class="job-detail-summary">
      ${[
        ["Type", job.type],
        ["Started by", job.owner || "—"],
        ["Status", job.status],
        ["Provider", job.provider],
        ["Model", job.model],
        ["Progress", `${job.completed}/${job.total}`],
        ["Failed", job.failed || 0],
        ["Started", job.started_at ? formatTimestamp(job.started_at) : "—"],
        ["Finished", job.finished_at ? formatTimestamp(job.finished_at) : "—"],
        [
          "Cancel requested",
          job.cancel_requested_at ? formatTimestamp(job.cancel_requested_at) : "—",
        ],
      ]
        .map(([name, value]) => `<div><span>${esc(name)}</span><b>${esc(value ?? "—")}</b></div>`)
        .join("")}
    </section>
    ${job.fatal_error ? `<div class="info error">${esc(job.fatal_error)}</div>` : ""}
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Request configuration</b><div class="note">API keys are intentionally omitted.</div></div></div>
      <pre class="job-detail-json">${esc(JSON.stringify(safeRequest, null, 2))}</pre>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Operation timeline</b><div class="note">${events.length} recorded events</div></div></div>
      <div class="job-event-list">${events.map((event: Any, index: Any) => `<div class="job-event ${index === events.length - 1 ? "latest" : ""}"><time>${esc(formatTimestamp(event.timestamp))}</time><b>${esc(label(event.stage || "event"))}</b><span>${event.current != null && event.total != null ? `${event.current}/${event.total} · ` : ""}${esc(event.detail || "")}</span></div>`).join("") || '<div class="note">No events recorded.</div>'}</div>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><b>Result summary</b></div>
      <pre class="job-detail-json">${esc(JSON.stringify(resultSummary, null, 2))}</pre>
    </section>
  </div>
  <div class="da">
    <button class="btn" data-close>Close</button>
    ${["queued", "running", "cancelling"].includes(job.status) ? (job.cancel_requested || job.status === "cancelling" ? '<button class="btn" disabled>Cancelling…</button>' : `<button class="btn danger" id="detailsCancelJob">Cancel operation</button>`) : ""}
    ${job.type === "llm" && (job.pending_result_count ?? (job.results || []).length) > 0 ? `<button class="btn primary" id="detailsOpenResult">${["queued", "running", "cancelling"].includes(job.status) ? "Review available results" : "Review results"}</button>` : ""}
    ${(["rag", "llm_tool"].includes(job.type) && job.status === "completed") || (job.type === "pdf_corpus" && ["completed", "blocked"].includes(job.status)) ? `<button class="btn primary" id="detailsOpenResult">${job.type === "pdf_corpus" ? esc(tr("pdf_corpus.open_build", "Open corpus build")) : "Open result"}</button>` : ""}
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
        return toast("This operation was removed and has been cleared from the activity view");
      }
      await openMessageModal({
        title: "Could not open operation result",
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
        title: "Could not render operation result",
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
        toast(`Could not refresh review results: ${error.message}`);
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
          title: "Discard pending LLM review?",
          message:
            "Discard all currently pending proposed changes, stop the review if it is still running, and remove this operation from the queue?",
          tone: "danger",
          confirmLabel: "Discard pending & remove",
          cancelLabel: "Keep review",
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
        toast("LLM review rejected and removed from the operations queue");
      } catch (error: Any) {
        toast(`Could not reject LLM review: ${error.message}`);
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

      if (!resolveItems.length) return toast("No LLM results selected");

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
          `Accepted ${resolveItems.length} pending result${resolveItems.length === 1 ? "" : "s"} · ${fieldsApplied} tracked field changes · ${job.pending_result_count || 0} pending`,
        );
      } catch (error: Any) {
        toast(
          `Local changes were applied, but the operation queue could not be updated: ${error.message}`,
        );
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
      if (!items.length) return toast("Select proposed changes to reject");
      try {
        job = await resolveOnServer("reject", items);
        selections.clear();
        await refreshJobs({ rerender: state.view === "home" });
        render({ preserveScroll: true });
        toast(
          `Rejected selected proposed changes · ${job.pending_change_count || 0} pending changes remain`,
        );
      } catch (error: Any) {
        toast(`Could not reject selected changes: ${error.message}`);
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
      const selected = selections.size;
      const _changedRecords = new Set(flattened.map((item) => item.result.key)).size;
      const noChangeCount = unchanged.length;
      const active = ["queued", "running", "cancelling"].includes(job.status);
      const statusText = job.status === "cancelled" ? "cancelled with partial results" : job.status;
      const pendingResults = job.pending_result_count ?? successful.length;
      const pendingChanges = job.pending_change_count ?? flattened.length;
      const remaining =
        job.remaining_record_count ?? Math.max(0, (job.total || 0) - (job.completed || 0));

      const changeTable = flattened.length
        ? `<div class="job-change-table-wrap"><table class="job-change-table"><thead><tr><th></th><th>Record</th><th>Field</th><th>Current</th><th>Proposed</th><th>Rationale</th></tr></thead><tbody>${flattened
            .map((item, index) => {
              const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
              const diff = reviewDiffSides(item.current, item.proposed);
              return `<tr class="${item.stale ? "stale-change" : ""}"><td><input type="checkbox" data-job-change="${index}" ${selections.has(index) ? "checked" : ""}></td><td><div class="job-record-cell"><b>${esc(rid)}</b>${item.local ? `<button class="btn tiny" data-copy-row-key="${esc(reviewKey(item.local.file, item.local.index))}">${icon("copy")}Copy</button>` : ""}<button class="btn tiny" data-preview-result="${index}">Preview record</button>${item.stale ? '<span class="stale-badge">local record changed since job started</span>' : ""}</div></td><td><b>${esc(label(item.field))}</b></td><td><pre class="change-diff current-diff">${diff.left}</pre></td><td><pre class="change-diff proposed-diff">${diff.right}</pre></td><td>${esc(item.rationale || "No rationale supplied.")}</td></tr>`;
            })
            .join("")}</tbody></table></div>`
        : `<section class="review-no-changes-empty"><div class="review-no-changes-icon">✓</div><div><h3>${active ? "No pending changes yet" : "No changes proposed"}</h3><p>${active ? `The review is still running. ${job.completed.toLocaleString()} records have completed and ${remaining.toLocaleString()} remain unprocessed.` : `The model reviewed ${noChangeCount.toLocaleString()} record${noChangeCount === 1 ? "" : "s"} and did not propose metadata/text edits.`}</p></div></section>`;

      const unchangedSection = noChangeCount
        ? `<details class="unchanged-review-list" ${flattened.length ? "" : "open"}><summary><span><b>${noChangeCount.toLocaleString()} record${noChangeCount === 1 ? "" : "s"} with no proposed changes</b><small>Expand to inspect or preview these records</small></span></summary><div class="unchanged-review-grid">${unchanged
            .map((item, index) => {
              const rid = item.local?.record?.record_id || item.result.record_id || item.result.key;
              return `<div class="unchanged-review-row"><div><b>${esc(rid)}</b><span>${esc(item.local?.record?.work || "")}${item.stale ? " · local record changed since review" : ""}</span></div><button class="btn tiny" data-preview-unchanged="${index}">Preview record</button></div>`;
            })
            .join("")}</div></details>`
        : "";

      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${job.mode === "auto" ? "Auto-improve changes" : "LLM review changes"}</h2><div class="dialog-subtitle">${job.completed}/${job.total} processed · ${pendingResults} pending result${pendingResults === 1 ? "" : "s"} · ${pendingChanges} pending change${pendingChanges === 1 ? "" : "s"} · ${remaining} unprocessed · ${failures.length} failures · ${esc(statusText)}</div></div><div class="tools">${active ? '<span class="job-status running">live</span>' : ""}<button class="btn icon-only" data-close>${icon("close")}</button></div></div>
    <div class="db job-change-review">
      <div class="job-resolution-summary">
        <span><b>${job.accepted_results || 0}</b> accepted results</span>
        <span><b>${job.accepted_fields || 0}</b> accepted fields</span>
        <span><b>${job.rejected_results || 0}</b> rejected results</span>
        <span><b>${job.rejected_fields || 0}</b> rejected fields</span>
        <span><b>${esc((job.resolution_state || "pending").replaceAll("_", " "))}</b> decision state</span>
      </div>
      ${flattened.length ? `<div class="job-change-toolbar"><button class="btn small" id="jobSelectAll">Select all changes</button><button class="btn small" id="jobSelectNone">Select none</button><button class="btn small danger" id="jobRejectSelected">Reject selected</button><span class="note"><b id="jobSelectedCount">${selected}</b> selected · accepted changes are removed from this pending queue immediately</span></div>` : ""}
      ${failures.length ? `<div class="info warn">${failures.map((result: Any) => `${esc(result.record_id || result.key)}: ${esc(result.error?.message || "failed")}`).join("<br>")}</div>` : ""}
      ${changeTable}
      ${unchangedSection}
    </div>
    <div class="da">
      <button class="btn" data-close>Close</button>
      ${active && remaining > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Stop review & discard pending</button>` : pendingResults > 0 ? `<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Discard pending & remove operation</button>` : ""}
      ${active ? `<button class="btn" id="refreshLiveResults">${icon("refresh")}Refresh available results</button>` : ""}
      ${successful.length ? `<button class="btn" id="markJobReviewed">${icon("check")}Mark all available reviewed</button>${flattened.length ? `<button class="btn primary" id="applyJobSelected" ${selected ? "" : "disabled"}>${icon("check")}Apply selected</button><button class="btn soft" id="applyJobAll">${icon("check")}Accept all available</button>` : ""}` : ""}
    </div>`;

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
            else toast("The source record is no longer loaded");
          }),
      );
      dialog.querySelectorAll("[data-preview-unchanged]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const entry = unchanged[+button.dataset.previewUnchanged];
            if (entry?.local) openReviewRecordPreview(entry.local, entry.result);
            else toast("The source record is no longer loaded");
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
    if (!record) return toast("The source record is no longer loaded in this workspace");

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

    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Record preview</h2><div class="dialog-subtitle">${esc(record.record_id || `Record ${local.index + 1}`)} · ${esc(record.work || local.file.name)} · ${esc(local.file.name)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db record-preview-body">
    ${stale ? '<div class="info warn">This local record changed after the LLM job started. Current values below may differ from the values originally reviewed.</div>' : ""}
    <section class="record-preview-summary">
      <div><span>Record ID</span><b>${esc(record.record_id || "—")}</b></div>
      <div><span>Work</span><b>${esc(record.work || "—")}</b></div>
      <div><span>Pages</span><b>${esc(pages(record))}</b></div>
      <div><span>Citation</span><b>${esc(fullCitation(record) || "—")}</b></div>
      <div><span>LLM proposals</span><b>${proposedFields.length}</b></div>
      <div><span>Needs review</span><b>${record.needs_review ? "Yes" : "No"}</b></div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Metadata</b><span>${important.length} populated fields</span></div>
      <div class="record-preview-metadata">${important.map((field) => `<div class="record-preview-field ${proposedFields.includes(field) ? "proposed-field" : ""}"><span>${esc(label(field))}${proposedFields.includes(field) ? "<i>proposed change</i>" : ""}</span><pre>${esc(jsonPretty(record[field]))}</pre></div>`).join("")}</div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Text</b><span>${String(record.text || "").length.toLocaleString()} characters</span></div>
      <pre class="record-preview-text">${esc(record.text || "")}</pre>
    </section>

    ${proposedFields.length ? `<section class="record-preview-section"><div class="record-preview-heading"><b>Proposed changes for this record</b><span>${proposedFields.length}</span></div><div class="record-preview-proposals">${proposedFields.map((field) => `<div><b>${esc(label(field))}</b><div class="record-preview-proposal-grid"><pre>${esc(jsonPretty(record[field]))}</pre><span>→</span><pre>${esc(jsonPretty(proposal.changes[field]))}</pre></div>${proposal.rationale?.[field] ? `<small>${esc(proposal.rationale[field])}</small>` : ""}</div>`).join("")}</div></section>` : ""}

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Recent audit history</b><span>${updates.length} shown</span></div>
      <div class="record-preview-history">${updates.map((update: Any) => `<div><time>${esc(formatTimestamp(update.timestamp))}</time><b>${esc(label(update.field_name || "field"))}</b><span>${esc(update.source || "manual")}${update.initiated_by ? ` · ${esc(update.initiated_by)}` : ""}</span></div>`).join("") || '<div class="note">No audit history recorded.</div>'}</div>
    </section>
  </div>
  <div class="da"><button class="btn" data-close>Close preview</button><button class="btn" data-copy-row-key="${esc(reviewKey(local.file, local.index))}">${icon("copy")}Copy entire record</button><button class="btn primary" id="previewOpenRecord">${icon("arrow")}Open full Record view</button></div>`;

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
        title: "Result unavailable",
        message:
          "This completed LLM operation does not contain a retained result. Open full details to inspect the operation.",
        tone: "danger",
      });
    const dialog = document.createElement("dialog");
    dialog.className = "llm-tool-result-dialog";
    const task = job.tool || job.mode;
    if (task === "work_metadata") {
      dialog.remove();
      return openWorkMetadataProposalResult(job);
    }
    let body = "",
      actions = "";
    if (task === "pdf_clean_text") {
      body = `<section class="card-inset"><div class="cardhead"><b>Cleaned page text</b></div><pre class="llm-tool-text">${esc(result.text || "")}</pre></section>`;
      actions = '<button class="btn primary" id="useToolText">Use as current page text</button>';
    } else if (task === "pdf_draft_record") {
      body = `<pre class="rag-json">${esc(JSON.stringify(result.record || {}, null, 2))}</pre>`;
      actions = '<button class="btn primary" id="openToolDraft">Review / add draft</button>';
    } else if (task === "pdf_link_record") {
      body = `<div class="llm-tool-match"><b>${esc(result.match?.record_id || "No supported match")}</b><p>${esc(result.match?.reason || "")}</p></div>`;
      actions = result.match?.key
        ? '<button class="btn primary" id="applyToolLink">Review & link page</button>'
        : "";
    } else if (task === "rag_grade") {
      const question = job.request?.question || "";
      body = `${question ? `<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(question)}</p></section>` : ""}${result.response_cache_error ? `<div class="info warn">The grade completed, but saving it to the response cache failed: ${esc(result.response_cache_error)}</div>` : ""}${ragGradeHtml(result.grade || {})}`;
    } else if (task === "rag_grade_batch") {
      body = `<section class="bulk-grade-result"><div class="compare-result-summary"><div><strong>${Number(result.graded || 0).toLocaleString()}</strong><span>graded</span></div><div><strong>${Number(result.failed || 0).toLocaleString()}</strong><span>failed</span></div><div><strong>${Number(result.total || 0).toLocaleString()}</strong><span>responses</span></div></div>${Array.isArray(result.errors) && result.errors.length ? `<details><summary>Errors (${result.errors.length})</summary><pre class="rag-json">${esc(JSON.stringify(result.errors, null, 2))}</pre></details>` : '<div class="info">All cached responses were processed.</div>'}</section>`;
    } else body = `<pre class="rag-json">${esc(JSON.stringify(result, null, 2))}</pre>`;
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(jobLabel(job))}</h2><div class="dialog-subtitle">${esc(job.provider || "")} · ${esc(job.model || result.model || "")}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${body}</div><div class="da"><button class="btn" data-close>Close</button>${actions}</div>`;
    document.body.appendChild(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    showAppModal(dialog);
    dialog.querySelector("#useToolText")?.addEventListener("click", () => {
      state.pdf.text = result.text || "";
      state.pdf.extractionSource = `LLM cleanup · ${job.model || result.model || "model"}`;
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
    if (!profiles.length) return toast("Configure an LLM provider first");
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
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(description)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db llm-tool-body">
      ${contextText ? `<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(contextText)}</p></section>` : ""}
      ${sameModel ? `<div class="info warn"><b>Same-model grading warning.</b> This provider/model was also used to generate the RAG answer. Self-grading can be systematically biased; use a different model for a more independent evaluation.</div>` : ""}
      <div class="llm-tool-grid">
        <div class="field field-wide"><label>Provider profile</label><select class="control" id="toolProvider">${profiles.map((item: Any) => `<option value="${esc(item.id)}" ${item.id === profile.id ? "selected" : ""}>${esc(providerDisplayName(item))} · ${item.type === "ollama" ? "Ollama" : "OpenAI-compatible"}</option>`).join("")}</select></div>
        <div class="field"><label>Run mode</label><select class="control" id="toolRunMode" ${isResearcher() || task === "rag_grade_batch" ? "disabled" : ""}>${task === "rag_grade_batch" ? '<option value="background" selected>Background operation</option>' : isResearcher() ? '<option value="foreground" selected>Interactive foreground</option>' : `<option value="background" ${runMode === "background" ? "selected" : ""}>Background operation</option><option value="foreground" ${runMode === "foreground" ? "selected" : ""}>Interactive foreground</option>`}</select></div>
        <div class="field field-wide"><label>Model</label><input class="control" id="toolModel" value="${esc(profile.type === "openai" && profile.model_mode === "auto" ? "auto" : profile.model || "")}" ${profile.type === "openai" && profile.model_mode === "auto" ? "disabled" : ""}></div>
        <div class="field"><label>Max concurrent requests</label><input class="control" value="${esc(profile.max_concurrent_requests ?? 1)}" disabled></div>
        ${
          profile.type === "ollama"
            ? `<div class="field"><label>Context</label><input class="control" id="toolCtx" type="number" value="${esc(profile.num_ctx ?? 16384)}"></div><div class="field"><label>Think</label><select class="control" id="toolThink">${[
                ["false", "Off"],
                ["true", "On"],
                ["low", "Low"],
                ["medium", "Medium"],
                ["high", "High"],
              ]
                .map(
                  ([v, l]) =>
                    `<option value="${v}" ${String(profile.think ?? "false") === v ? "selected" : ""}>${l}</option>`,
                )
                .join("")}</select></div>`
            : ""
        }
        <div class="field"><label>Max output tokens</label><input class="control" id="toolPredict" type="number" value="${esc(profile.num_predict ?? 4096)}"></div>
        <div class="field"><label>Temperature</label><input class="control" id="toolTemp" type="number" step="0.01" value="${esc(profile.temperature ?? 0)}"></div>
        <div class="field"><label>top_p</label><input class="control" id="toolTopP" type="number" step="0.01" value="${esc(profile.top_p ?? 1)}"></div>
        <div class="field"><label>Seed</label><input class="control" id="toolSeed" type="number" value="${esc(profile.seed ?? "")}"></div>
        <div class="field field-wide"><label>Advanced options JSON</label><textarea id="toolExtra" spellcheck="false">${esc(profile.extra_options || "{}")}</textarea></div>
      </div>
      <div class="tools llm-tool-profile-actions"><button class="btn small" id="toolWarm">${icon("spark")}Warm this provider</button>${isResearcher() ? "" : `<button class="btn small" id="toolProviders">${icon("gear")}Manage providers</button>`}<span class="note" id="toolStatus">${status.available ? "Endpoint ready" : status.error || "Not verified"}</span></div>
    </div>
    <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="runLlmTask">${icon("spark")}${runMode === "background" ? "Start background operation" : "Run now"}</button></div>`;
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
        el.textContent = "Warming…";
        await warmupProviderProfile(profileId);
        el.textContent = state.providerWarmups?.[profileId]?.message || "Warmup requested";
      };
      dialog.querySelector("#runLlmTask").onclick = async () => {
        const active = providerProfile(profileId);
        if (!active) return toast("Choose an available provider profile before continuing.");
        if (!["ollama", "openai"].includes(String(active.type || "")))
          return toast("The selected provider profile is not supported by this operation.");
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
        if (!model) return toast("Select a model before continuing.");
        if (
          task === "rag_grade" &&
          (!String(payload.question || "").trim() || !String(payload.answer || "").trim())
        )
          return toast("A completed Research question and answer are required before grading.");
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
        button.textContent = runMode === "background" ? "Starting…" : "Running…";
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
            toast(`${title} started in background`);
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
          button.innerHTML = `${icon("spark")}${runMode === "background" ? "Start background operation" : "Run now"}`;
          toast(`${title} failed: ${error.message}`);
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
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Draft record from PDF page</h2><div class="dialog-subtitle">${esc(state.pdf.title || state.pdf.name)} · page ${state.pdf.page} · unsaved draft</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db pdf-draft-body">
    <div class="info warn">This is a draft generated by an LLM. Review attribution, page metadata, quotation provenance, and text before saving.</div>
    <textarea class="pdf-draft-json" id="pdfDraftJson" spellcheck="false">${esc(JSON.stringify(record, null, 2))}</textarea>
    <div class="pdf-draft-targets">
      <div class="field"><label>JSONL destination</label><select class="control" id="pdfDraftFile"><option value="">Do not add to JSONL</option>${files.map((file: Any) => `<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length} records</option>`).join("")}</select></div>
      <div class="field"><label>Chroma destination</label><select class="control" id="pdfDraftStore" ${stores.length ? "" : `disabled data-disabled-reason="Create or restore a corpus vector database before upserting PDF drafts." title="Create or restore a corpus vector database before upserting PDF drafts."`}><option value="">${stores.length ? "Do not upsert to Chroma" : "No corpus database available"}</option>${stores.map((store: Any) => `<option value="${esc(store.name)}">${esc(store.name)} · ${Number(store.count || 0).toLocaleString()} records</option>`).join("")}</select></div>
    </div>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="savePdfDraft">${icon("check")}Add draft</button></div>`;
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
        return toast(`Invalid draft JSON: ${error.message}`);
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
      if (!fileId && !storeName) return toast("Choose a JSONL file, a Chroma collection, or both.");

      if (fileId) {
        const file = state.files.find((item: Any) => item.id === fileId);
        if (!file) return toast("Selected JSONL file is no longer loaded");
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
          return toast(
            `Draft was added to JSONL where selected, but Chroma upsert failed: ${error.message}`,
          );
        }
      }
      close();
      shell();
      renderView();
      toast(
        `Draft ${draft.record_id} added${fileId && storeName ? " to JSONL and Chroma" : fileId ? " to JSONL" : " to Chroma"}`,
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
