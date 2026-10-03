/* Copyright 2026 Aaron John Schlosser, PhD. */

import { openMessageDialog } from "../composables/messageDialog";
import { icon } from "./html";
import { realtime } from "../realtime";
import { followResource } from "../realtime/follow";
import {
  openJobReviewDialog,
  type JobReviewApplyMode,
  type JobReviewHandle,
  type JobReviewView,
} from "../composables/jobReviewDialog";
import { openRecordPreviewDialog } from "../composables/recordPreviewDialog";
import { createJobDialogCopy } from "./jobDialogCopy";
import { llmTaskLauncherHtml } from "./llmToolMarkup";
import { openPdfDraftRecordDialog } from "../composables/pdfDraftRecordDialog";
import {
  openLlmToolResultDialog,
  type LlmToolResultBody,
  type LlmToolResultRequest,
} from "../composables/llmToolResultDialog";
import { openJobDetailsDialog } from "../composables/jobDetailsDialog";
import { toast } from "../composables/notifications";

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
        return toast(copy.operationRemoved, { tone: "success" });
      }
      return toast(copy.loadDetailsFailed(error.message), { tone: "danger" });
    }
    const events = job.events || [];
    const request = job.request || {};
    const safeRequest = cloneAuditValue(request);
    if (safeRequest && typeof safeRequest === "object") delete safeRequest.api_key;

    let resultSummary: Any;
    if (job.type === "llm") {
      resultSummary = {
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
      };
    } else if (job.type === "upsert") {
      resultSummary = {
        committed: job.completed || 0,
        requested: job.total || 0,
        target_collection: job.store_name,
        language_mirrors: job.mirrored || {},
        receipt_count: (job.results || []).length,
      };
    } else if (job.type === "corpus_capture") {
      resultSummary = {
        capture_id: job.capture_id || job.id,
        mode: job.mode || null,
        raw_status: job.status || null,
        candidate_count: job.result?.candidate_count ?? job.candidate_count ?? null,
        has_capture_state: Boolean(job.capture_id),
        error_count: (job.errors || []).length,
      };
    } else if (job.type === "pdf_corpus") {
      resultSummary = {
        source_pdf: job.source_filename || null,
        build_id: job.build_id || job.id,
        raw_status: job.raw_status || job.status,
        stage: job.stage || null,
        record_count: job.record_count || 0,
        review_count: job.review_count || 0,
        unresolved_regions: job.unresolved_regions || 0,
      };
    } else if (job.type === "llm_tool") {
      resultSummary = {
        operation: job.label || job.tool || job.mode,
        provider_profile_id: job.provider_profile_id || null,
        max_concurrent_requests: job.max_concurrent_requests || null,
        has_result: Boolean(job.result),
        result_keys: job.result && typeof job.result === "object" ? Object.keys(job.result) : [],
      };
    } else {
      resultSummary = {
        has_result: Boolean(job.result),
        evidence_count: job.result?.evidence?.length || 0,
        elapsed_seconds: job.result?.elapsed_seconds ?? null,
        collections: job.result?.collections || [],
        response_cache: job.result?.response_cache || job.response_cache || null,
      };
    }

    const active = ["queued", "running", "cancelling"].includes(job.status);
    const reviewable =
      job.type === "llm" && (job.pending_result_count ?? (job.results || []).length) > 0;
    const openable =
      (["rag", "llm_tool"].includes(job.type) && job.status === "completed") ||
      (job.type === "pdf_corpus" && ["completed", "blocked"].includes(job.status));
    const openLabel = reviewable
      ? active
        ? tr("operations.panel.action_review_partial")
        : tr("operations.panel.action_review")
      : job.type === "pdf_corpus"
        ? tr("pdf_corpus.open_build")
        : tr("operations.panel.action_open_result");
    const when = (value: Any) => (value ? formatTimestamp(value) : "—");
    openJobDetailsDialog({
      title: trf("operations.details_title", { label: jobLabel(job) }),
      subtitle: `${job.id} · ${tr(`operations.status.${job.status}`, String(job.status || ""))} · ${trf("operations.created", { when: formatTimestamp(job.created_at) })}`,
      facts: (
        [
          [tr("operations.fact.operation"), job.type],
          [tr("operations.fact.started_by"), job.owner || "—"],
          [
            tr("operations.fact.status"),
            tr(`operations.status.${job.status}`, String(job.status || "")),
          ],
          [tr("operations.fact.provider"), job.provider],
          [tr("operations.fact.model"), job.model],
          [tr("operations.fact.progress"), `${job.completed}/${job.total}`],
          [tr("operations.fact.failed"), job.failed || 0],
          [tr("operations.fact.started"), when(job.started_at)],
          [tr("operations.fact.finished"), when(job.finished_at)],
          [tr("operations.fact.cancel_requested"), when(job.cancel_requested_at)],
        ] as Any[]
      ).map(([name, value]) => ({ name: String(name), value: String(value ?? "—") })),
      fatalError: job.fatal_error ? String(job.fatal_error) : "",
      requestJson: JSON.stringify(safeRequest, null, 2),
      events: events.map((event: Any, index: Any) => ({
        when: formatTimestamp(event.timestamp),
        stage: label(event.stage || "event"),
        detail: `${event.current != null && event.total != null ? `${event.current}/${event.total} · ` : ""}${event.detail || ""}`,
        latest: index === events.length - 1,
      })),
      resultJson: JSON.stringify(resultSummary, null, 2),
      cancel: !active
        ? "none"
        : job.cancel_requested || job.status === "cancelling"
          ? "cancelling"
          : "cancel",
      onCancel: async () => {
        if (await cancelBackgroundJob(job.id)) openJobDetails(job.id);
      },
      openResult:
        reviewable || openable ? { label: openLabel, run: () => openJobResults(job.id) } : null,
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
        return toast(copy.operationRemoved, { tone: "success" });
      }
      await openMessageDialog({
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
              path: `/corpus-builder?build=${encodeURIComponent(job.build_id || job.id)}`,
              runtimeView: "pdf",
            },
          }),
        );
        return;
      }
    } catch (error: Any) {
      console.error("Could not render operation result", error, job);
      await openMessageDialog({
        title: copy.renderResultFailed,
        message: error.message || String(error),
        detail: jobLabel(job),
        tone: "danger",
      });
      return;
    }

    let liveTimer: Any = null;
    let handle: JobReviewHandle | null = null;
    const isLive = () => ["queued", "running", "cancelling"].includes(job.status);

    async function refreshJob() {
      try {
        job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
        const idx = state.jobs.findIndex((item: Any) => item.id === job.id);
        if (idx >= 0) state.jobs[idx] = { ...state.jobs[idx], ...job };
        return true;
      } catch (error: Any) {
        toast(copy.refreshFailed(error.message), { tone: "danger" });
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

    async function resolveOnServer(action: Any, items: Any, { dismissJob = false } = {}) {
      return api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/resolve`, {
        method: "POST",
        body: JSON.stringify({ action, items, dismiss_job: dismissJob }),
      });
    }

    async function rejectAndDismiss() {
      if (
        !(await openMessageDialog({
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
        handle?.close();
        await refreshJobs({ rerender: state.view === "home" });
        toast(copy.rejectedRemoved, { tone: "success" });
      } catch (error: Any) {
        toast(copy.rejectFailed(error.message), { tone: "danger" });
      }
    }

    async function apply(mode: JobReviewApplyMode, selected: number[]): Promise<boolean> {
      selections = new Set(selected);
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

      if (!resolveItems.length) {
        toast(copy.noResultsSelected, { tone: "warning" });
        return false;
      }

      try {
        job = await resolveOnServer("accept", resolveItems);
        state.jobApplied[job.id] = new Date().toISOString();
        persistPrefs();
        shell();
        renderView();
        await refreshJobs({ rerender: state.view === "home" });
        publish();
        toast(copy.accepted(resolveItems.length, fieldsApplied, job.pending_result_count || 0), {
          tone: "success",
        });
        return true;
      } catch (error: Any) {
        toast(copy.localAppliedQueueFailed(error.message), { tone: "danger" });
        return false;
      }
    }

    async function rejectSelected(selected: number[]): Promise<boolean> {
      selections = new Set(selected);
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
      if (!items.length) {
        toast(copy.selectToReject, { tone: "warning" });
        return false;
      }
      try {
        job = await resolveOnServer("reject", items);
        await refreshJobs({ rerender: state.view === "home" });
        publish();
        toast(copy.rejectedRemain(job.pending_change_count || 0), { tone: "warning" });
        return true;
      } catch (error: Any) {
        toast(copy.rejectSelectedFailed(error.message), { tone: "danger" });
        return false;
      }
    }

    // The reviewer's selection is indices into the rows built here, in this order.
    function buildView(): JobReviewView {
      const { successful, failures, unchanged, flattened } = buildData();
      const active = isLive();
      const pendingResults = job.pending_result_count ?? successful.length;
      const pendingChanges = job.pending_change_count ?? flattened.length;
      const remaining =
        job.remaining_record_count ?? Math.max(0, (job.total || 0) - (job.completed || 0));
      const statusText =
        job.status === "cancelled" ? tr("jobs.review.cancelled_partial") : job.status;
      const recordId = (item: Any) =>
        String(item.local?.record?.record_id || item.result.record_id || item.result.key);
      const state_ = job.resolution_state || "pending";
      return {
        title: job.mode === "auto" ? tr("jobs.review.auto_title") : tr("jobs.review.title"),
        subtitle: trf("jobs.review.subtitle", {
          completed: job.completed,
          total: job.total,
          pendingResults,
          pendingChanges,
          remaining,
          failures: failures.length,
          status: statusText,
        }),
        active,
        completed: job.completed || 0,
        remaining,
        noChangeCount: unchanged.length,
        resolution: {
          acceptedResults: job.accepted_results || 0,
          acceptedFields: job.accepted_fields || 0,
          rejectedResults: job.rejected_results || 0,
          rejectedFields: job.rejected_fields || 0,
          state: tr(`operations.decision.${state_}`, String(state_).replaceAll("_", " ")),
        },
        failures: failures.map(
          (result: Any) =>
            `${result.record_id || result.key}: ${result.error?.message || tr("jobs.review.failed")}`,
        ),
        rows: flattened.map((item: Any) => {
          const diff = reviewDiffSides(item.current, item.proposed);
          return {
            recordId: recordId(item),
            copyKey: item.local ? String(reviewKey(item.local.file, item.local.index)) : "",
            stale: item.stale,
            isText: item.field === "text",
            field: String(label(item.field)),
            currentHtml: diff.left,
            proposedHtml: diff.right,
            rationale: item.rationale || "",
          };
        }),
        unchanged: unchanged.map((item: Any) => ({
          recordId: recordId(item),
          work: String(item.local?.record?.work || ""),
          stale: item.stale,
        })),
        discard: active && remaining > 0 ? "stop" : pendingResults > 0 ? "remove" : "none",
        hasSuccessful: successful.length > 0,
      };
    }
    const publish = () => handle?.update(buildView());

    handle = openJobReviewDialog(buildView(), {
      apply,
      rejectSelected,
      discard: rejectAndDismiss,
      refresh: async () => {
        if (await refreshJob()) publish();
      },
      previewRow: (index) => {
        const entry = buildData().flattened[index];
        if (entry?.local) openReviewRecordPreview(entry.local, entry.result);
        else toast(copy.sourceGone, { tone: "danger" });
      },
      previewUnchanged: (index) => {
        const entry = buildData().unchanged[index];
        if (entry?.local) openReviewRecordPreview(entry.local, entry.result);
        else toast(copy.sourceGone, { tone: "danger" });
      },
      onClose: () => {
        if (liveTimer) liveTimer();
      },
    });
    if (isLive()) {
      // Follow this job's realtime events; REST polling only while the socket is unavailable.
      liveTimer = followResource({
        topic: `job:${job.id}`,
        fallbackMs: realtime.status === "idle" ? 4000 : undefined,
        isDone: () => !handle?.isOpen() || !isLive(),
        refresh: async () => {
          if (!handle?.isOpen()) return;
          const before = job.completed;
          const pendingBefore = job.pending_result_count;
          if (await refreshJob()) {
            if (
              job.completed !== before ||
              job.pending_result_count !== pendingBefore ||
              !isLive()
            ) {
              publish();
            }
          }
        },
      });
    }
  }
  async function openRagResult(job: Any) {
    if (!job?.id) return toast(tr("research.result_unavailable"), { tone: "warning" });
    if (!canAccessPage("rag"))
      return toast(tr("permissions.research_result_denied"), { tone: "warning" });
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
    if (!record) return toast(copy.sourceGoneWorkspace, { tone: "danger" });

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

    const stale = Boolean(result?.fingerprint && recordFingerprint(record) !== result.fingerprint);
    const updates = Array.isArray(record.updates) ? record.updates.slice(-8).reverse() : [];
    openRecordPreviewDialog({
      recordId: record.record_id || trf("dashboard.record_n", { n: local.index + 1 }),
      subtitle: `${record.work || local.file.name} · ${local.file.name}`,
      stale,
      summary: {
        work: record.work || "—",
        pages: String(pages(record)),
        citation: fullCitation(record) || "—",
        proposalCount: proposedFields.length,
        needsReview: Boolean(record.needs_review),
      },
      fields: important.map((field) => ({
        key: field,
        label: String(label(field)),
        value: String(jsonPretty(record[field])),
        proposed: proposedFields.includes(field),
      })),
      text: String(record.text || ""),
      proposals: proposedFields.map((field) => ({
        label: String(label(field)),
        current: String(jsonPretty(record[field])),
        proposed: String(jsonPretty(proposal.changes[field])),
        rationale: String(proposal.rationale?.[field] || ""),
      })),
      history: updates.map((update: Any) => ({
        when: String(formatTimestamp(update.timestamp)),
        field: String(label(update.field_name || "field")),
        source: `${update.source || tr("jobs.preview.manual")}${update.initiated_by ? ` · ${update.initiated_by}` : ""}`,
      })),
      copyKey: String(reviewKey(local.file, local.index)),
      openFull: () => navigateTo("record", { fileId: local.file.id, index: local.index }),
    });
  }
  function openLlmToolResult(job: Any) {
    const result = job.result;
    if (!result)
      return openMessageDialog({
        title: copy.resultUnavailableTitle,
        message: copy.resultUnavailable,
        tone: "danger",
      });
    const task = job.tool || job.mode;
    if (task === "work_metadata") return openWorkMetadataProposalResult(job);
    const subtitle = `${job.provider || ""} \u00b7 ${job.model || result.model || ""}`;
    const json = (value: Any) => JSON.stringify(value, null, 2);
    let body: LlmToolResultBody = { kind: "raw", json: json(result) };
    let action: LlmToolResultRequest["action"] = null;
    if (task === "pdf_clean_text") {
      body = { kind: "clean_text", text: result.text || "" };
      action = {
        label: tr("jobs.tool.use_page_text"),
        run: () => {
          state.pdf.text = result.text || "";
          state.pdf.extractionSource = trf("jobs.tool.cleanup_source", {
            model: job.model || result.model || tr("jobs.tool.model_fallback", "model"),
          });
          if (state.view === "pdf")
            window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"));
        },
      };
    } else if (task === "pdf_draft_record") {
      body = { kind: "draft_record", json: json(result.record || {}) };
      action = {
        label: tr("jobs.tool.review_draft"),
        run: () => openPdfDraftRecord(result.record || {}),
      };
    } else if (task === "pdf_link_record") {
      body = {
        kind: "link_record",
        recordId: result.match?.record_id || "",
        reason: result.match?.reason || "",
      };
      if (result.match?.key)
        action = {
          label: tr("jobs.tool.review_link"),
          run: () => applyPdfLinkMatch(result.match || {}),
        };
    } else if (task === "rag_grade") {
      body = {
        kind: "rag_grade",
        question: job.request?.question || "",
        cacheError: result.response_cache_error || "",
        gradeHtml: ragGradeHtml(result.grade || {}),
      };
    } else if (task === "rag_grade_batch") {
      const errors = Array.isArray(result.errors) ? result.errors : [];
      body = {
        kind: "rag_grade_batch",
        graded: Number(result.graded || 0),
        failed: Number(result.failed || 0),
        total: Number(result.total || 0),
        errorsJson: errors.length ? json(errors) : "",
        errorCount: errors.length,
      };
    }
    openLlmToolResultDialog({ title: jobLabel(job), subtitle, body, action });
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
    if (!profiles.length) return toast(copy.configureProvider, { tone: "warning" });
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
        el.textContent = tr("providers.warming");
        await warmupProviderProfile(profileId);
        el.textContent =
          state.providerWarmups?.[profileId]?.message || tr("jobs.tool.warmup_requested");
      };
      dialog.querySelector("#runLlmTask").onclick = async () => {
        const active = providerProfile(profileId);
        if (!active) return toast(copy.chooseProfile, { tone: "warning" });
        if (!["ollama", "openai"].includes(String(active.type || "")))
          return toast(copy.profileUnsupported, { tone: "warning" });
        const config = providerRequestConfig(active, { textReview: true });
        let extra: Any = {};
        try {
          extra = JSON.parse(dialog.querySelector("#toolExtra").value || "{}");
          if (!extra || Array.isArray(extra) || typeof extra !== "object")
            throw new Error("Advanced options must be an object");
        } catch (error: Any) {
          return toast(error.message, { tone: "danger" });
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
        if (!model) return toast(copy.selectModel, { tone: "warning" });
        if (
          task === "rag_grade" &&
          (!String(payload.question || "").trim() || !String(payload.answer || "").trim())
        )
          return toast(copy.gradeRequiresQa, { tone: "warning" });
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
        button.textContent =
          runMode === "background" ? tr("jobs.tool.starting") : tr("jobs.tool.running");
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
            toast(copy.startedBackground(title), { tone: "success" });
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
          button.innerHTML = `${icon("spark")}${runMode === "background" ? tr("jobs.tool.start_background") : tr("jobs.tool.run_now")}`;
          toast(copy.failed(title, error.message), { tone: "danger" });
        }
      };
    };
    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  function openPdfDraftRecord(record: Any) {
    openPdfDraftRecordDialog({
      title: state.pdf.title || state.pdf.name,
      page: state.pdf.page,
      recordJson: JSON.stringify(record, null, 2),
      files: state.files.map((file: Any) => ({
        id: file.id,
        name: file.name,
        count: file.records.length,
      })),
      stores: recordStores().map((store: Any) => ({
        id: store.name,
        name: store.name,
        count: Number(store.count || 0),
      })),
      save: async ({ json, fileId, storeName }) => {
        let draft: Any;
        try {
          draft = JSON.parse(json);
          if (!draft || typeof draft !== "object" || Array.isArray(draft))
            throw new Error("Draft must be one JSON object.");
        } catch (error: Any) {
          toast(copy.invalidDraft(error.message), { tone: "danger" });
          return false;
        }
        if (!draft.record_id) draft.record_id = `pdf-draft-${Date.now()}`;
        draft.needs_review = true;
        draft.updates = Array.isArray(draft.updates) ? draft.updates : [];
        draft.pdf_file = state.pdf.name || draft.pdf_file || null;
        draft.pdf_pages = [
          ...new Set([...(Array.isArray(draft.pdf_pages) ? draft.pdf_pages : []), state.pdf.page]),
        ].sort((a, b) => a - b);
        draft.text_length = String(draft.text || "").length;

        if (!fileId && !storeName) {
          toast(copy.chooseDestination, { tone: "warning" });
          return false;
        }
        if (fileId) {
          const file = state.files.find((item: Any) => item.id === fileId);
          if (!file) {
            toast(copy.jsonlGone, { tone: "danger" });
            return false;
          }
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
            toast(copy.chromaUpsertFailed(error.message), { tone: "danger" });
            return false;
          }
        }
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
        return true;
      },
    });
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
