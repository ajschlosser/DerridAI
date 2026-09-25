import { computed, type Ref } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import type { ReviewQueue } from "../types/corpus";

/** Derive review/finish navigation from server authority and local queue choice. */
export function useCorpusBuildLifecycle(
  currentBuild: Ref<CorpusBuild | null>,
  recordTotal: Ref<number>,
  reviewQueue: Ref<ReviewQueue>,
) {
  const reviewQueueCounts = computed(() => currentBuild.value?.review_queue_counts || {});
  const reviewRemaining = computed(() =>
    Math.max(
      0,
      Number(currentBuild.value?.record_count || 0) -
        Number(currentBuild.value?.accepted_count || 0) -
        Number(currentBuild.value?.rejected_count || 0),
    ),
  );
  const pendingCount = computed(() =>
    Number(reviewQueueCounts.value.pending ?? reviewRemaining.value),
  );
  const issueCount = computed(() =>
    Number(reviewQueueCounts.value.issues ?? currentBuild.value?.needs_review_count ?? 0),
  );
  const readyCount = computed(() =>
    Number(reviewQueueCounts.value.ready ?? Math.max(0, pendingCount.value - issueCount.value)),
  );
  const topologyIssueCount = computed(() => Number(reviewQueueCounts.value.topology ?? 0));
  const buildRunning = computed(() =>
    Boolean(currentBuild.value && ["queued", "running"].includes(currentBuild.value.status)),
  );
  const reviewCompatibleStages = new Set([
    "enriching",
    "metadata_retry",
    "metadata_enrichment_rerun",
  ]);
  const reviewLocked = computed(() =>
    Boolean(
      buildRunning.value && !reviewCompatibleStages.has(String(currentBuild.value?.stage || "")),
    ),
  );
  const structuralReviewLocked = computed(
    () =>
      buildRunning.value &&
      !["enriching", "metadata_retry", "metadata_enrichment_rerun", "review"].includes(
        String(currentBuild.value?.stage || ""),
      ),
  );
  const canResume = computed(() =>
    Boolean(
      currentBuild.value?.resumable &&
        !buildRunning.value &&
        ["failed", "interrupted", "cancelled", "blocked"].includes(
          String(currentBuild.value.status),
        ),
    ),
  );
  const segmentationNeedsReview = computed(() =>
    Boolean(
      currentBuild.value?.segmentation_degraded &&
        !buildRunning.value &&
        (currentBuild.value?.segmentation_unresolved_regions?.length || 0) > 0,
    ),
  );
  const retryingSegmentation = computed(() =>
    Boolean(buildRunning.value && currentBuild.value?.retrying_segmentation),
  );
  const canRetryMetadata = computed(() =>
    Boolean(
      currentBuild.value &&
        !currentBuild.value.publication &&
        !buildRunning.value &&
        Number(currentBuild.value.metadata_issue_summary?.auto_retry_fields || 0) > 0,
    ),
  );
  const metadataIssueCount = computed(() =>
    Number(currentBuild.value?.metadata_issue_summary?.records_incomplete ?? 0),
  );
  const metadataFieldIssueCount = computed(() =>
    Number(currentBuild.value?.metadata_issue_summary?.fields_unresolved ?? 0),
  );
  const metadataRetryRunning = computed(() =>
    Boolean(buildRunning.value && currentBuild.value?.stage === "metadata_retry"),
  );
  const awaitingManifestReview = computed(
    () => currentBuild.value?.status === "awaiting_manifest_review",
  );
  const hasRecordTopology = computed(() =>
    Boolean(
      currentBuild.value &&
        !awaitingManifestReview.value &&
        (Boolean(currentBuild.value.publication) ||
          Number(currentBuild.value.record_count || 0) > 0 ||
          recordTotal.value > 0),
    ),
  );
  const showBuildConfiguration = computed(
    () => !currentBuild.value || (!buildRunning.value && !hasRecordTopology.value),
  );
  const reviewComplete = computed(() =>
    Boolean(
      currentBuild.value &&
        Number(currentBuild.value.record_count || 0) > 0 &&
        reviewRemaining.value === 0,
    ),
  );
  const finishPhase = computed(() =>
    Boolean(currentBuild.value && (reviewComplete.value || currentBuild.value.publication)),
  );
  const showReviewWorkspace = computed(() =>
    Boolean(hasRecordTopology.value && (!finishPhase.value || reviewQueue.value !== "all")),
  );
  return {
    reviewQueueCounts,
    reviewRemaining,
    pendingCount,
    issueCount,
    readyCount,
    topologyIssueCount,
    buildRunning,
    reviewLocked,
    structuralReviewLocked,
    canResume,
    segmentationNeedsReview,
    retryingSegmentation,
    canRetryMetadata,
    metadataIssueCount,
    metadataFieldIssueCount,
    metadataRetryRunning,
    awaitingManifestReview,
    hasRecordTopology,
    showBuildConfiguration,
    reviewComplete,
    finishPhase,
    showReviewWorkspace,
  };
}
