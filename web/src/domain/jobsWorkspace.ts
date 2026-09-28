/* Copyright 2026 Aaron John Schlosser, PhD. */

// Background jobs on the client: loading the job list, following it live over the realtime socket (with fallback
// polling), cancelling, removing and clearing jobs, applying finished upserts, submitting LLM jobs and the progress
// toasts and desktop notifications they raise. The runtime's state object and helpers are passed in as dependencies.
import { icon } from "./html";
import { isActiveJobStatus, jobIdsToPruneFromDock } from "./operationsDock";
import { FALLBACK_POLL_MS, realtime as defaultRealtime } from "../realtime";
import type { RealtimeClient } from "../realtime/client";
import { TERMINAL_JOB_STATUSES, type JobEvent } from "../realtime/protocol";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "announceOperationDock"
  | "api"
  | "ensureJobProgressCard"
  | "jobLabel"
  | "jobProviderSummary"
  | "navigateTo"
  | "notifyOperationsChanged"
  | "persistPrefs"
  | "recordFingerprint"
  | "refreshCorpusBuildsHomeCardOnly"
  | "refreshOperationsPanelOnly"
  | "refreshRagProgressPanel"
  | "refreshStores"
  | "reviewItemFromKey"
  | "reviewKey"
  | "shell"
  | "toast"
  | "touchupRecordPayload"
  | "trf"
  | "updateDbStatusElements"
  | "updateOperationStackCount";
type Deps = { state: Loose; realtime?: RealtimeClient } & Record<Helper, Fn>;

/** Legacy interval, used only when realtime has not been started at all. */
const LEGACY_POLL_MS = 4000;

export function createJobsWorkspace(deps: Deps) {
  const realtime = deps.realtime ?? defaultRealtime;
  const {
    state,
    announceOperationDock,
    api,
    ensureJobProgressCard,
    jobLabel,
    jobProviderSummary,
    navigateTo,
    notifyOperationsChanged,
    persistPrefs,
    recordFingerprint,
    refreshCorpusBuildsHomeCardOnly,
    refreshOperationsPanelOnly,
    refreshRagProgressPanel,
    refreshStores,
    reviewItemFromKey,
    reviewKey,
    shell,
    toast,
    touchupRecordPayload,
    trf,
    updateDbStatusElements,
    updateOperationStackCount,
  } = deps;
  // Which finished jobs already raised a notification, and the timers that hide their completion toasts.
  const jobCompletionNotified: Record<string, boolean> = {};
  const completedJobToastTimers: Record<string, ReturnType<typeof setTimeout>> = {};
  /**
   * The single reconciliation path for job state. REST snapshots (bootstrap, resync, fallback polling,
   * explicit refresh) and realtime job events both end here, so toasts, desktop notifications,
   * upsert receipts and the Operations panel behave identically whichever transport delivered the change.
   */
  async function reconcileJobs(nextJobs: Any[], { rerender = false, fromSnapshot = false } = {}) {
    const previousJobs = [...state.jobs];
    const previous = new Map(previousJobs.map((job) => [job.id, job.status]));
    state.jobs = nextJobs;
    if (fromSnapshot) state.jobsLastFetched = Date.now();
    const knownJobIds = new Set(state.jobs.map((job: Any) => job.id));
    const disappearedRagIds = previousJobs
      .filter((job) => job.type === "rag" && !knownJobIds.has(job.id))
      .map((job) => job.id);
    if (disappearedRagIds.length && Array.isArray(state.ragConfig.run_history)) {
      const removed = new Set(disappearedRagIds);
      state.ragConfig.run_history = state.ragConfig.run_history.filter(
        (item: Any) => !removed.has(item.job_id),
      );
      for (const id of disappearedRagIds) pruneClientJobState(id, { removeHistory: false });
      persistPrefs();
    }
    for (const id of Object.keys(state.jobApplied || {}))
      if (!knownJobIds.has(id)) delete state.jobApplied[id];
    for (const id of Object.keys(state.upsertJobApplied || {}))
      if (!knownJobIds.has(id)) delete state.upsertJobApplied[id];
    for (const job of state.jobs) await syncUpsertJobReceipts(job);
    syncJobProgressToasts(previous);
    const operationsButton = document.querySelector("#operationsBtn");
    if (operationsButton) {
      const active = state.jobs.filter((job: Any) =>
        ["queued", "running", "cancelling"].includes(job.status),
      ).length;
      operationsButton.classList.toggle("soft", active > 0);
      operationsButton.innerHTML = `${icon("history")}Operations <span class="button-count">${active}</span>`;
    }
    notifyOperationsChanged();
    if (rerender && state.view === "home") refreshCorpusBuildsHomeCardOnly();
    if (state.view === "rag") refreshRagProgressPanel();
    return state.jobs;
  }
  async function refreshJobs({ rerender = false } = {}) {
    try {
      const payload = await api("/api/jobs");
      return await reconcileJobs(payload.jobs || [], { rerender, fromSnapshot: true });
    } catch (error) {
      console.warn("Could not refresh background jobs", error);
      return state.jobs;
    }
  }
  /** How long until the next REST poll, or null when no server-state polling should run. */
  function pollDelay(): number | null {
    if (realtime.live) return null; // healthy socket: events replace polling
    if (realtime.fallbackActive) return FALLBACK_POLL_MS; // socket repeatedly unavailable
    if (realtime.status === "idle") return LEGACY_POLL_MS; // realtime never started
    return null; // briefly reconnecting: wait; a status change re-arms polling
  }
  function startJobPolling() {
    if (state.jobsPollTimer) return;
    // Never create an idle polling loop. A one-time bootstrap refresh discovers
    // restored server jobs; thereafter only known active jobs schedule polling.
    if (!state.jobs.some((job: Any) => ["queued", "running", "cancelling"].includes(job.status)))
      return;
    const delay = pollDelay();
    if (delay === null) return;
    const poll = async () => {
      state.jobsPollTimer = null;
      if (!state.jobs.some((job: Any) => ["queued", "running", "cancelling"].includes(job.status)))
        return;
      if (pollDelay() === null) return;
      await refreshJobs({ rerender: state.view === "home" });
      const active = state.jobs.some((job: Any) =>
        ["queued", "running", "cancelling"].includes(job.status),
      );
      const next = pollDelay();
      if (active && next !== null) state.jobsPollTimer = setTimeout(poll, next);
    };
    state.jobsPollTimer = setTimeout(poll, delay);
  }
  function stopJobPolling() {
    if (state.jobsPollTimer) {
      clearTimeout(state.jobsPollTimer);
      state.jobsPollTimer = null;
    }
  }
  // ---- realtime ---------------------------------------------------------------------------------
  let realtimeBound = false;
  let resyncTimer: ReturnType<typeof setTimeout> | null = null;
  /** Coalesce bursts (terminal events, reconnects) into one authoritative REST snapshot. */
  function scheduleJobsResync(delay = 250) {
    if (resyncTimer) return;
    resyncTimer = setTimeout(async () => {
      resyncTimer = null;
      await refreshJobs({ rerender: state.view === "home" });
      startJobPolling();
    }, delay);
  }
  async function applyJobEvent(event: JobEvent) {
    const summary = event.payload.job;
    const known = state.jobs.some((job: Any) => job.id === summary.id);
    if (event.type === "job.removed" || !known) {
      // Removal or a job this page has not loaded yet: fetch the owner-scoped REST snapshot.
      scheduleJobsResync();
      return;
    }
    const next = state.jobs.map((job: Any) =>
      job.id === summary.id ? { ...job, ...summary } : job,
    );
    await reconcileJobs(next, { rerender: state.view === "home" });
    // Terminal events carry only a summary; results, errors and pending proposals come from REST.
    if (summary.status && TERMINAL_JOB_STATUSES.has(summary.status)) scheduleJobsResync();
  }
  /** Connect the realtime socket (after authentication) and follow the job feed. */
  function startRealtime() {
    if (!realtimeBound) {
      realtimeBound = true;
      realtime.subscribe("jobs", (event) => {
        if (event.resource_type === "job") void applyJobEvent(event as JobEvent);
      });
      realtime.onResync(() => scheduleJobsResync(0));
      realtime.onStatus((status) => {
        if (status === "idle") return; // paused (logout/expiry): nothing may re-arm polling
        if (realtime.live) stopJobPolling();
        else startJobPolling();
      });
    }
    realtime.start();
  }
  function pauseRuntime() {
    stopJobPolling();
    if (resyncTimer) {
      clearTimeout(resyncTimer);
      resyncTimer = null;
    }
    // Logout, session expiry and account switches all pause the runtime: close the socket too.
    realtime.stop();
  }
  function pruneClientJobState(jobId: Any, { removeHistory = true } = {}) {
    state.jobs = state.jobs.filter((job: Any) => job.id !== jobId);
    delete state.jobApplied?.[jobId];
    delete state.upsertJobApplied?.[jobId];
    delete jobCompletionNotified[jobId];
    clearTimeout(completedJobToastTimers[jobId]);
    delete completedJobToastTimers[jobId];
    document.querySelector(`[data-job-operation="${CSS.escape(jobId)}"]`)?.remove();
    if (removeHistory && Array.isArray(state.ragConfig.run_history)) {
      state.ragConfig.run_history = state.ragConfig.run_history.filter(
        (item: Any) => item.job_id !== jobId,
      );
    }
    updateOperationStackCount();
  }
  async function removeFinishedJob(jobId: Any, { refresh = true } = {}) {
    try {
      await api(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
      pruneClientJobState(jobId);
      persistPrefs();
      if (refresh) await refreshJobs({ rerender: state.view === "home" });
      else updateOperationStackCount();
    } catch (error) {
      toast(
        trf("operations.remove_failed", {
          message: (error as Error).message,
        }),
      );
    }
  }
  async function clearFinishedOperations() {
    try {
      await api("/api/jobs", { method: "DELETE" });
      document
        .querySelectorAll("#operationProgressStack [data-operation-id].operation-complete")
        .forEach((panel) => {
          delete state.operationProgress[(panel as HTMLElement).dataset.operationId!];
          panel.remove();
        });
      await refreshJobs({ rerender: true });
      updateOperationStackCount();
    } catch (error) {
      toast(
        trf("operations.clear_failed", {
          message: (error as Error).message,
        }),
      );
    }
  }
  async function syncUpsertJobReceipts(job: Any) {
    if (job.type !== "upsert" || Number(job.completed || 0) <= 0) return;
    const applied = Number(state.upsertJobApplied?.[job.id] || 0);
    if (Number(job.completed || 0) <= applied) return;
    let detail;
    try {
      detail = await api(`/api/jobs/${encodeURIComponent(job.id)}`);
    } catch (error) {
      console.warn("Could not fetch upsert receipts", error);
      return;
    }
    const results = detail.results || [];
    if (!state.upsertJobApplied) state.upsertJobApplied = {};
    for (const result of results.slice(applied)) {
      const item = reviewItemFromKey(result.key);
      const stores = [result.store_name, ...(result.mirrored_stores || [])].filter(Boolean);
      for (const store of stores) {
        if (!state.upsertState[store]) state.upsertState[store] = {};
        if (!state.storePresence[store]) state.storePresence[store] = {};
        if (!state.storePresenceIds[store]) state.storePresenceIds[store] = {};
        state.upsertState[store][result.key] = {
          fingerprint: result.fingerprint,
          timestamp: result.completed_at || new Date().toISOString(),
          chroma_id: result.chroma_id,
          job_id: job.id,
          updates_count: result.updates_count,
        };
        state.storePresence[store][result.key] = true;
        state.storePresenceIds[store][result.key] = result.chroma_id || "";
        if (state.upsertIgnored?.[store]) delete state.upsertIgnored[store][result.key];
      }
      // If the local record changed while the background upsert was running, the
      // stored fingerprint intentionally remains the older one, so status becomes Pending.
      if (item && result.fingerprint !== recordFingerprint(item.file.records[item.index])) {
        // no-op: fingerprint mismatch is the pending-state signal
      }
    }
    state.upsertJobApplied[job.id] = results.length;
    persistPrefs();
    updateDbStatusElements();
    if (!["queued", "running", "cancelling"].includes(detail.status)) {
      try {
        await refreshStores();
      } catch {
        // Best effort: keep going with what we have.
      }
    }
  }
  async function cancelBackgroundJob(jobId: Any, { refresh = true } = {}) {
    const job = state.jobs.find((item: Any) => item.id === jobId);
    if (job?.cancel_requested) return;
    try {
      const updated = await api(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, {
        method: "POST",
        body: "{}",
      });
      state.jobs = state.jobs.map((item: Any) => (item.id === jobId ? updated : item));
      syncJobProgressToasts();
      if (refresh) {
        if (state.view === "home") refreshOperationsPanelOnly();
        if (state.view === "rag") refreshRagProgressPanel();
      }
      const cancellationMessage =
        updated.type === "llm" || updated.type === "llm_tool"
          ? "interrupting the active model stream"
          : updated.type === "rag"
            ? "interrupting model streaming or stopping at the next vector/rerank checkpoint"
            : updated.type === "upsert"
              ? "finishing the current Chroma batch, then stopping"
              : "stopping at the next safe checkpoint";
      toast(
        updated.status === "cancelled"
          ? `${jobLabel(updated)} cancelled`
          : `Cancellation requested for ${jobLabel(updated)} · ${cancellationMessage}.`,
      );
      return updated;
    } catch (error) {
      toast(`Cancel failed: ${(error as Error).message}`);
      return null;
    }
  }
  async function submitBackgroundLlmJob(
    items: Any,
    config: Any,
    fields: Any,
    instructions: Any,
    mode: Any,
  ) {
    const payload = {
      items: items.map((item: Any) => ({
        key: item.key || reviewKey(item.file, item.index),
        record: touchupRecordPayload(item.file.records[item.index], fields),
        fingerprint: recordFingerprint(item.file.records[item.index]),
      })),
      fields: [...fields],
      instructions: instructions || "",
      model: config.model,
      provider: config.provider,
      base_url: config.base_url,
      api_key: config.api_key,
      provider_profile_id: config.provider_profile_id,
      max_concurrent_requests: config.max_concurrent_requests,
      ollama: config.ollama,
      mode: mode === "auto" ? "auto" : "review",
    };
    const job = await api("/api/jobs/llm", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.jobs = [job, ...state.jobs.filter((existing: Any) => existing.id !== job.id)];
    syncJobProgressToasts();
    startJobPolling();
    toast(
      `${mode === "auto" ? "Auto-improve" : "LLM review"} started in background · ${items.length} records`,
    );
    return job;
  }
  function registerExternalJob(job: Any) {
    if (!job?.id) return;
    state.jobs = [job, ...state.jobs.filter((existing: Any) => existing.id !== job.id)];
    syncJobProgressToasts();
    startJobPolling();
    shell();
  }
  function maybeDesktopNotify(job: Any) {
    if (!state.appConfig.desktop_notifications) return;
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    try {
      const notification = new Notification(`${jobLabel(job)} ${job.status}`, {
        body:
          job.type === "rag"
            ? `${job.prompt || "RAG pipeline"} · ${job.stage_detail || job.status}`
            : job.type === "llm"
              ? `${job.completed}/${job.total} records processed · ${job.pending_result_count || 0} pending results`
              : job.type === "llm_tool"
                ? `${job.label || "LLM operation"} · ${job.status}`
                : `${job.label || job.store_name || "Chroma sync"} · ${job.completed}/${job.total} records committed`,
        tag: `derridai-job-${job.id}`,
      });
      notification.onclick = () => {
        window.focus();
        navigateTo("home");
        notification.close();
      };
    } catch (error) {
      console.warn("Desktop notification failed", error);
    }
  }
  function syncJobProgressToasts(previous = new Map()) {
    for (const job of state.jobs) {
      if (isActiveJobStatus(job.status)) {
        if (previous.size && !previous.has(job.id)) {
          announceOperationDock(trf("operations.live_started", { label: jobLabel(job) }));
        }
        ensureJobProgressCard(job);
        continue;
      }
      const transitioned =
        previous.get(job.id) &&
        previous.get(job.id) !== job.status &&
        ["completed", "cancelled", "failed"].includes(job.status);
      const panel = document.querySelector(`[data-job-operation="${CSS.escape(job.id)}"]`);
      if (panel || transitioned) ensureJobProgressCard(job);
      if (transitioned && !jobCompletionNotified[job.id]) {
        jobCompletionNotified[job.id] = true;
        if (
          job.status === "completed" &&
          job.type === "llm_tool" &&
          (job.tool || job.mode) === "language_dictionary"
        ) {
          window.dispatchEvent(
            new CustomEvent("derridai:languages-changed", {
              detail: { source: "translation-job", jobId: job.id },
            }),
          );
        }
        {
          const providerSummary = jobProviderSummary(job);
          const unit =
            job.type === "rag"
              ? " stages"
              : job.type === "llm_tool" && (job.tool || job.mode) === "work_metadata"
                ? " works"
                : " records";
          toast(
            `${jobLabel(job)}${providerSummary ? ` · ${providerSummary}` : ""} ${job.status}: ${job.completed}/${job.total}${unit}`,
          );
        }
        const liveKey =
          job.status === "failed"
            ? "operations.live_failed"
            : job.status === "cancelled"
              ? "operations.live_cancelled"
              : "operations.live_completed";
        const liveFallback =
          job.status === "failed"
            ? "{label} failed"
            : job.status === "cancelled"
              ? "{label} cancelled"
              : "{label} completed";
        announceOperationDock(trf(liveKey, liveFallback, { label: jobLabel(job) }));
        maybeDesktopNotify(job);
      }
    }
    const liveIds = state.jobs.map((job: Any) => job.id);
    const visibleIds = [...document.querySelectorAll("[data-job-operation]")].map(
      (panel) => (panel as HTMLElement).dataset.jobOperation as string,
    );
    for (const id of jobIdsToPruneFromDock(visibleIds, liveIds)) {
      document.querySelector(`[data-job-operation="${CSS.escape(id)}"]`)?.remove();
    }
    updateOperationStackCount();
  }
  return {
    refreshJobs,
    reconcileJobs,
    applyJobEvent,
    startRealtime,
    startJobPolling,
    pauseRuntime,
    pruneClientJobState,
    removeFinishedJob,
    clearFinishedOperations,
    syncUpsertJobReceipts,
    cancelBackgroundJob,
    submitBackgroundLlmJob,
    registerExternalJob,
    maybeDesktopNotify,
    syncJobProgressToasts,
  };
}
