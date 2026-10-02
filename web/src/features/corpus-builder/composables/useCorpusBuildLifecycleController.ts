/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick, type ComputedRef, type Ref } from "vue";
import {
  corpusBuilderApi,
  type AutonomousPolicy,
  type CorpusBuild,
  type PdfAsset,
} from "../../../api/corpus";
import * as runtime from "../../../runtime/runtime.js";
import { followResource } from "../../../realtime/follow";
import type {
  CorpusBuildEvent,
  CorpusBuildSummary,
  CorpusRecordEvent,
  RealtimeEvent,
} from "../../../realtime/protocol";

type MessageTone = "error" | "notice";

interface CorpusBuildLifecycleControllerOptions {
  builds: Ref<CorpusBuild[]>;
  buildsTotal: Ref<number>;
  selectedBuildId: Ref<string>;
  currentBuild: Ref<CorpusBuild | null>;
  selectedAssetId: Ref<string>;
  assets: Ref<PdfAsset[]>;
  busy: Ref<string>;
  schemaId: Ref<string>;
  providerPayload: ComputedRef<Record<string, unknown>>;
  handsFree: Ref<AutonomousPolicy>;
  hydratedTopologyCount: Ref<number>;
  hydratedMetadataCount: Ref<number>;
  selectedRecordId: Ref<string>;
  canRetryMetadata: ComputedRef<boolean>;
  metadataIssueCount: ComputedRef<number>;
  requestedBuildId: () => string;
  runGuidancePayload: () => Record<string, unknown>;
  /** Reviewer-supplied document fields that detection on source load missed. */
  documentMetadataPayload?: () => Record<string, unknown>;
  topologyPolicyPayload?: () => Record<string, unknown>;
  applyBuildRequest: (request: Record<string, unknown>) => void;
  setMessage: (message: string, tone?: MessageTone) => void;
  resetReviewForBuildStart: () => void;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  /** Patch one review-queue row in place from the server (see useCorpusReviewRecords). */
  refreshRows: (recordIds: string[]) => Promise<void>;
  /** Refresh the full selected Record after its enrichment result is durable. */
  refreshRecord: (recordId: string) => Promise<void>;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}

export function useCorpusBuildLifecycleController(options: CorpusBuildLifecycleControllerOptions) {
  let stopFollowing: (() => void) | undefined;

  function buildRunning(build = options.currentBuild.value): boolean {
    return Boolean(build && ["queued", "running"].includes(String(build.status || "")));
  }

  function syncBuildInRail(build: CorpusBuild) {
    const index = options.builds.value.findIndex((item) => item.build_id === build.build_id);
    if (index >= 0) {
      // Preserve object identity so progress updates do not remount/repaint the build rail.
      Object.assign(options.builds.value[index], build);
    } else {
      options.builds.value.unshift(build);
    }
  }

  function applyRealtimeBuildSummary(summary: CorpusBuildSummary) {
    const build = options.currentBuild.value;
    if (!build || build.build_id !== summary.id) return;
    const patch: Partial<CorpusBuild> = {};
    if (summary.raw_status !== undefined)
      patch.status = summary.raw_status as CorpusBuild["status"];
    if (summary.stage !== undefined) patch.stage = summary.stage as CorpusBuild["stage"];
    if (summary.progress !== undefined) patch.progress = summary.progress;
    if (summary.record_count !== undefined) patch.record_count = summary.record_count;
    if (summary.accepted_count !== undefined) patch.accepted_count = summary.accepted_count;
    if (summary.rejected_count !== undefined) patch.rejected_count = summary.rejected_count;
    if (summary.review_count !== undefined) patch.needs_review_count = summary.review_count;
    if (summary.review_queue_counts !== undefined)
      patch.review_queue_counts = { ...summary.review_queue_counts };
    if (summary.metadata_total !== undefined) patch.metadata_total = summary.metadata_total;
    if (summary.metadata_completed !== undefined)
      patch.metadata_completed = summary.metadata_completed;
    if (summary.metadata_enriched_count !== undefined)
      patch.metadata_enriched_count = summary.metadata_enriched_count;
    if (summary.metadata_tasks_total !== undefined)
      patch.metadata_tasks_total = summary.metadata_tasks_total;
    if (summary.metadata_tasks_completed !== undefined)
      patch.metadata_tasks_completed = summary.metadata_tasks_completed;
    if (summary.metadata_tasks_failed !== undefined)
      patch.metadata_tasks_failed = summary.metadata_tasks_failed;
    if (summary.metadata_tasks_skipped !== undefined)
      patch.metadata_tasks_skipped = summary.metadata_tasks_skipped;
    if (summary.metadata_tasks_running !== undefined)
      patch.metadata_tasks_running = summary.metadata_tasks_running;
    if (summary.metadata_tasks_queued !== undefined)
      patch.metadata_tasks_queued = summary.metadata_tasks_queued;
    if (summary.metadata_active_tasks !== undefined)
      patch.metadata_active_tasks = summary.metadata_active_tasks.map((task) => ({ ...task }));
    Object.assign(build, patch);
    syncBuildInRail(build);
  }

  function registerBuildOperation(build: CorpusBuild) {
    const asset = options.assets.value.find((item) => item.asset_id === build.asset_id);
    const total = Math.max(1, Number(asset?.block_count || 1));
    const progress = Math.max(0, Math.min(1, Number(build.progress || 0)));
    runtime.registerExternalJob?.({
      id: build.build_id,
      build_id: build.build_id,
      type: "pdf_corpus",
      kind: "pdf_corpus",
      label: `${options.t("pdf_corpus.corpus_builder")} · ${build.source_filename || ""}`,
      status: ["queued", "running"].includes(build.status)
        ? build.status
        : build.status === "blocked"
          ? "blocked"
          : "completed",
      raw_status: build.status,
      stage: build.stage,
      stage_detail: build.stage,
      source_filename: build.source_filename,
      progress,
      total,
      completed: Math.min(total, Math.round(total * progress)),
      record_count: Number(build.record_count || 0),
      review_count: Number(build.needs_review_count || 0),
      unresolved_regions: Number(build.segmentation_unresolved_regions?.length || 0),
      created_at: build.created_at,
      started_at: build.started_at,
      finished_at: build.finished_at,
    });
  }

  async function refreshBuilds() {
    const result = await corpusBuilderApi.listBuilds(0, 100);
    options.builds.value = result.items;
    options.buildsTotal.value = result.total;
    const requested = options.requestedBuildId();
    if (requested && options.builds.value.some((build) => build.build_id === requested)) {
      options.selectedBuildId.value = requested;
    } else if (
      (!options.selectedBuildId.value ||
        !options.builds.value.some((build) => build.build_id === options.selectedBuildId.value)) &&
      options.builds.value[0]
    ) {
      options.selectedBuildId.value = options.builds.value[0].build_id;
    } else if (!options.builds.value.length) {
      options.selectedBuildId.value = "";
      options.currentBuild.value = null;
    }
  }

  async function refreshBuild() {
    if (!options.selectedBuildId.value) {
      options.currentBuild.value = null;
      return;
    }
    try {
      const refreshed = await corpusBuilderApi.build(options.selectedBuildId.value);
      if (options.currentBuild.value?.build_id === refreshed.build_id) {
        // Reconcile into the existing reactive object so a background authoritative read
        // cannot remount the active workspace or reset child component state.
        Object.assign(options.currentBuild.value, refreshed);
      } else {
        options.currentBuild.value = refreshed;
      }
      syncBuildInRail(options.currentBuild.value);
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
      return;
    }
    if (options.currentBuild.value?.asset_id) {
      options.selectedAssetId.value = options.currentBuild.value.asset_id;
    }
    options.applyBuildRequest(
      (options.currentBuild.value?.request || {}) as Record<string, unknown>,
    );
  }

  function stopPolling() {
    stopFollowing?.();
    stopFollowing = undefined;
  }

  /**
   * Follow the selected build. Bounded WebSocket summaries are applied directly so counters,
   * stages, model activity and per-record completion update without replacing the workspace.
   * REST is reserved for reconnect/fallback reconciliation and one terminal authoritative read.
   */
  function startPolling() {
    stopPolling();
    const buildId = options.selectedBuildId.value;
    if (!buildId) return;
    let finished = false;
    let terminalPending = false;
    let lastRecordReconcile = 0;

    function handleRealtimeEvent(event: RealtimeEvent): boolean {
      if (event.resource_id !== buildId) return false;
      if (event.type.startsWith("corpus.") && "build" in event.payload) {
        const wasRunning = buildRunning();
        applyRealtimeBuildSummary((event as CorpusBuildEvent).payload.build);
        if (wasRunning && !buildRunning()) {
          terminalPending = true;
          return true;
        }
        return false;
      }
      if (
        event.type === "llm.started" ||
        event.type === "llm.progress" ||
        event.type === "llm.completed"
      ) {
        // The bounded event intentionally omits provider-load state and elapsed time. Re-read
        // the authoritative build snapshot for those few activity transitions, but reconcile
        // it into the existing object so the workspace never remounts or visibly reloads.
        return true;
      }
      if (
        event.type === "corpus.record_started" ||
        event.type === "corpus.field_checked" ||
        event.type === "corpus.record_completed"
      ) {
        if (event.type === "corpus.record_completed") {
          const recordId = String((event as CorpusRecordEvent).payload.metadata.record_id || "");
          if (recordId) {
            void options.refreshRows([recordId]);
            if (recordId === options.selectedRecordId.value) void options.refreshRecord(recordId);
          }
        }
        return false;
      }
      // Text-free generation hints are consumed by the Model activity inspector.
      if (event.type === "corpus.llm_progress") return false;
      return true;
    }

    const stopFollowingBuild = followResource({
      topic: `corpus-build:${buildId}`,
      minIntervalMs: 700,
      // Healthy sockets carry the visible progress. This slow read is only a safety
      // reconciliation for state that is intentionally not present on the realtime plane.
      reconcileMs: 30_000,
      isDone: () => finished,
      onEvent: handleRealtimeEvent,
      refresh: async () => {
        if (!options.selectedBuildId.value) return;
        const wasRunning = buildRunning() || terminalPending;
        await refreshBuild();
        // A realtime note can be missed (reconnect, dropped under backpressure, sent before the
        // Record was open). Reconcile the open Record on the slow path, at most every 10s.
        const openRecordId = options.selectedRecordId.value;
        if (wasRunning && openRecordId && Date.now() - lastRecordReconcile > 10_000) {
          lastRecordReconcile = Date.now();
          void options.refreshRecord(openRecordId);
        }
        if (wasRunning && !buildRunning()) {
          terminalPending = false;
          finished = true;
          await refreshBuilds();
          // Completion can settle filtered queue membership; reconcile in place without
          // resetting selection, scroll position, or the selected Record cache.
          await nextTick();
          await options.refreshRecords(false, options.selectedRecordId.value);
        }
      },
    });
    stopFollowing = stopFollowingBuild;
  }

  async function startBuild() {
    if (!options.selectedAssetId.value) {
      options.setMessage(options.t("pdf_corpus.choose_pdf_before_build"), "error");
      return;
    }
    options.busy.value = "build";
    options.setMessage("");
    options.resetReviewForBuildStart();
    try {
      const documentMetadata = options.documentMetadataPayload?.() ?? {};
      const topologyPolicy = options.topologyPolicyPayload?.() ?? {};
      const payload = {
        asset_id: options.selectedAssetId.value,
        ...(Object.keys(topologyPolicy).length ? { topology_policy: topologyPolicy } : {}),
        auto_enrich_work_metadata: true,
        schema_id: options.schemaId.value,
        run_guidance: options.runGuidancePayload(),
        ...(Object.keys(documentMetadata).length ? { document_metadata: documentMetadata } : {}),
        ...options.providerPayload.value,
        ...(options.handsFree.value.enabled ? { autonomous: { ...options.handsFree.value } } : {}),
      };
      const build = await corpusBuilderApi.createBuild(payload);
      options.selectedBuildId.value = build.build_id;
      options.currentBuild.value = build;
      registerBuildOperation(build);
      await refreshBuilds();
      startPolling();
      options.setMessage(options.t("pdf_corpus.build_started"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function resumeBuild() {
    if (!options.currentBuild.value) return;
    if (buildRunning()) {
      options.setMessage(options.t("pdf_corpus.already_running"));
      return;
    }
    options.busy.value = "build";
    try {
      options.currentBuild.value = await corpusBuilderApi.resume(
        options.currentBuild.value.build_id,
        options.providerPayload.value,
      );
      syncBuildInRail(options.currentBuild.value);
      registerBuildOperation(options.currentBuild.value);
      startPolling();
      options.setMessage(options.t("pdf_corpus.build_resumed"));
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : String(exc);
      if (message.includes("already running")) {
        await refreshBuild();
        if (options.currentBuild.value) registerBuildOperation(options.currentBuild.value);
        options.setMessage(options.t("pdf_corpus.already_running"));
      } else {
        options.setMessage(message, "error");
      }
    } finally {
      options.busy.value = "";
    }
  }

  async function retryIncompleteMetadata() {
    if (!options.currentBuild.value || !options.canRetryMetadata.value) return;
    const fields = Number(
      options.currentBuild.value.metadata_issue_summary?.auto_retry_fields || 0,
    );
    const recordsCount = Number(
      options.currentBuild.value.metadata_issue_summary?.auto_retry_records ||
        options.metadataIssueCount.value,
    );
    if (fields < 1) {
      options.setMessage(options.t("pdf_corpus.no_retryable_metadata"));
      return;
    }
    options.busy.value = "metadata-retry";
    try {
      options.currentBuild.value = await corpusBuilderApi.retryMetadata(
        options.currentBuild.value.build_id,
        options.providerPayload.value,
      );
      syncBuildInRail(options.currentBuild.value);
      registerBuildOperation(options.currentBuild.value);
      startPolling();
      options.setMessage(
        options.tf("pdf_corpus.metadata_retry_start_fields", {
          fields,
          records: recordsCount,
        }),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function confirmManifest() {
    if (!options.currentBuild.value) return;
    options.busy.value = "manifest";
    try {
      options.currentBuild.value = await corpusBuilderApi.confirmManifest(
        options.currentBuild.value.build_id,
        options.providerPayload.value,
      );
      syncBuildInRail(options.currentBuild.value);
      registerBuildOperation(options.currentBuild.value);
      startPolling();
      options.setMessage(options.t("pdf_corpus.manifest_confirmed"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function cancelBuild() {
    if (!options.currentBuild.value) return;
    await corpusBuilderApi.cancel(options.currentBuild.value.build_id);
    options.setMessage(options.t("pdf_corpus.cancel_requested"));
    startPolling();
  }

  async function pauseBuild() {
    if (!options.currentBuild.value) return;
    try {
      options.currentBuild.value = await corpusBuilderApi.pause(
        options.currentBuild.value.build_id,
      );
      options.setMessage(options.t("pdf_corpus.pause_requested"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    }
    startPolling();
  }

  async function deleteBuild() {
    const build = options.currentBuild.value;
    if (!build) return;
    try {
      await corpusBuilderApi.deleteBuild(build.build_id);
      options.builds.value = options.builds.value.filter(
        (item) => item.build_id !== build.build_id,
      );
      options.buildsTotal.value = Math.max(0, options.buildsTotal.value - 1);
      options.selectedBuildId.value = options.builds.value[0]?.build_id || "";
      options.currentBuild.value = null;
      options.setMessage(options.t("pdf_corpus.build_deleted"));
      await refreshBuilds();
      await refreshBuild();
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    }
  }

  async function settleMetadata() {
    if (!options.currentBuild.value) return;
    options.busy.value = "settle";
    try {
      options.currentBuild.value = await corpusBuilderApi.settleMetadata(
        options.currentBuild.value.build_id,
      );
      syncBuildInRail(options.currentBuild.value);
      options.setMessage(options.t("pdf_corpus.settle_requested_notice"));
      startPolling();
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  return {
    registerBuildOperation,
    syncBuildInRail,
    refreshBuilds,
    refreshBuild,
    startPolling,
    stopPolling,
    startBuild,
    resumeBuild,
    retryIncompleteMetadata,
    confirmManifest,
    cancelBuild,
    pauseBuild,
    deleteBuild,
    settleMetadata,
  };
}
