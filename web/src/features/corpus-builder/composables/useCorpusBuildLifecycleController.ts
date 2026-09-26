/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick, type ComputedRef, type Ref } from "vue";
import {
  corpusBuilderApi,
  type AutonomousPolicy,
  type CorpusBuild,
  type PdfAsset,
} from "../../../api/corpus";
import * as runtime from "../../../runtime/runtime.js";

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
  applyBuildRequest: (request: Record<string, unknown>) => void;
  setMessage: (message: string, tone?: MessageTone) => void;
  resetReviewForBuildStart: () => void;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}

export function useCorpusBuildLifecycleController(options: CorpusBuildLifecycleControllerOptions) {
  let pollTimer: number | undefined;

  function buildRunning(build = options.currentBuild.value): boolean {
    return Boolean(build && ["queued", "running"].includes(String(build.status || "")));
  }

  function syncBuildInRail(build: CorpusBuild) {
    const index = options.builds.value.findIndex((item) => item.build_id === build.build_id);
    if (index >= 0) {
      options.builds.value.splice(index, 1, { ...options.builds.value[index], ...build });
    } else {
      options.builds.value.unshift(build);
    }
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
      options.currentBuild.value = await corpusBuilderApi.build(options.selectedBuildId.value);
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
    if (pollTimer !== undefined) {
      clearInterval(pollTimer);
      pollTimer = undefined;
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(async () => {
      if (!options.selectedBuildId.value) return;

      // Build polling owns build-state freshness only. PdfCorpusBuilder's build-state
      // watcher is the single owner of incremental record hydration. Keeping record
      // reads out of this timer prevents the poll callback and the watcher from
      // independently issuing the same /records request every 1.4 seconds.
      const wasRunning = buildRunning();
      await refreshBuild();

      if (wasRunning && !buildRunning()) {
        stopPolling();
        await refreshBuilds();
        // One terminal refresh is still useful because completion can settle queue
        // membership without changing record_count/metadata_enriched_count.
        await nextTick();
        await options.refreshRecords(false, options.selectedRecordId.value);
      }
    }, 1400);
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
      const payload = {
        asset_id: options.selectedAssetId.value,
        auto_enrich_work_metadata: true,
        schema_id: options.schemaId.value,
        run_guidance: options.runGuidancePayload(),
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
    settleMetadata,
  };
}
