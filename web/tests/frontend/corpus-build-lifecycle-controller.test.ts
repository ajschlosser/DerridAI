/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  listBuilds: vi.fn(),
  build: vi.fn(),
  createBuild: vi.fn(),
  resume: vi.fn(),
  retryMetadata: vi.fn(),
  confirmManifest: vi.fn(),
  cancel: vi.fn(),
  settleMetadata: vi.fn(),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

const runtime = vi.hoisted(() => ({
  registerExternalJob: vi.fn(),
}));

vi.mock("../../src/runtime/runtime.js", () => runtime);

const follow = vi.hoisted(() => ({
  calls: [] as Array<Record<string, any>>,
  stop: vi.fn(),
}));
vi.mock("../../src/realtime/follow", async () => {
  const actual = await vi.importActual<typeof import("../../src/realtime/follow")>(
    "../../src/realtime/follow",
  );
  return {
    followResource: (options: Record<string, any>) => {
      follow.calls.push(options);
      const stopReal = actual.followResource(options as any);
      return () => {
        follow.stop();
        stopReal();
      };
    },
  };
});

import { useCorpusBuildLifecycleController } from "../../src/features/corpus-builder/composables/useCorpusBuildLifecycleController";
import { realtime } from "../../src/realtime";

function spyOnRealtimeSubscribe() {
  return vi.spyOn(realtime, "subscribe");
}

/** The controller's build-topic subscription, created by followResource and fed through its
 * event reducer before deciding whether an authoritative read is required. */
function lastRecordEventSubscription(spy: ReturnType<typeof spyOnRealtimeSubscribe>) {
  const call = spy.mock.calls.at(-1);
  return call ? { topic: call[0] as string, handler: call[1] as (event: any) => void } : undefined;
}

function build(id = "build-1") {
  return {
    build_id: id,
    asset_id: "asset-1",
    status: "awaiting_review",
    stage: "review",
    source_filename: "source.pdf",
    record_count: 2,
    request: {},
  } as any;
}

function setup(
  requestedBuildId = "",
  documentMetadata: Record<string, unknown> = {},
  topologyPolicy: Record<string, unknown> = {},
) {
  const builds = ref<any[]>([]);
  const buildsTotal = ref(0);
  const selectedBuildId = ref("");
  const currentBuild = ref<any | null>(null);
  const selectedAssetId = ref("asset-1");
  const assets = ref<any[]>([{ asset_id: "asset-1", block_count: 10 }]);
  const busy = ref("");
  const schemaId = ref("schema-1");
  const providerPayload = computed(() => ({ provider_profile_id: "local" }));
  const handsFree = ref<any>({
    enabled: false,
    passes: 1,
    min_confidence: 0.8,
    unresolved: "best_guess",
    accept_records: true,
    publish: false,
  });
  const hydratedTopologyCount = ref(0);
  const hydratedMetadataCount = ref(0);
  const selectedRecordId = ref("");
  const canRetryMetadata = computed(() => true);
  const metadataIssueCount = computed(() => 0);
  const resetReviewForBuildStart = vi.fn();
  const refreshRecords = vi.fn(async () => undefined);
  const refreshRows = vi.fn(async () => undefined);
  const refreshRecord = vi.fn(async () => undefined);
  const applyBuildRequest = vi.fn();
  const setMessage = vi.fn();

  const controller = useCorpusBuildLifecycleController({
    builds,
    buildsTotal,
    selectedBuildId,
    currentBuild,
    selectedAssetId,
    assets,
    busy,
    schemaId,
    providerPayload,
    handsFree,
    hydratedTopologyCount,
    hydratedMetadataCount,
    selectedRecordId,
    canRetryMetadata,
    metadataIssueCount,
    requestedBuildId: () => requestedBuildId,
    runGuidancePayload: () => ({ speaker: "Derrida" }),
    documentMetadataPayload: () => documentMetadata,
    topologyPolicyPayload: () => topologyPolicy,
    applyBuildRequest,
    setMessage,
    resetReviewForBuildStart,
    refreshRecords,
    refreshRows,
    refreshRecord,
    t: (key) => key,
    tf: (key) => key,
  });

  return {
    controller,
    builds,
    buildsTotal,
    selectedBuildId,
    selectedRecordId,
    currentBuild,
    busy,
    resetReviewForBuildStart,
    applyBuildRequest,
    setMessage,
    refreshRecords,
    refreshRows,
    refreshRecord,
  };
}

describe("Corpus Builder lifecycle controller", () => {
  let subscribeSpy: ReturnType<typeof spyOnRealtimeSubscribe>;
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    subscribeSpy = spyOnRealtimeSubscribe();
  });

  afterEach(() => {
    subscribeSpy.mockRestore();
    vi.useRealTimers();
  });

  it("selects the requested build while refreshing the build rail", async () => {
    corpusBuilderApi.listBuilds.mockResolvedValue({
      items: [build("build-1"), build("build-2")],
      total: 2,
    });
    const state = setup("build-2");

    await state.controller.refreshBuilds();

    expect(state.buildsTotal.value).toBe(2);
    expect(state.selectedBuildId.value).toBe("build-2");
  });

  it("starts a build from the shared configuration payload and resets review state first", async () => {
    corpusBuilderApi.createBuild.mockResolvedValue(build("build-new"));
    corpusBuilderApi.listBuilds.mockResolvedValue({
      items: [build("build-new")],
      total: 1,
    });
    const state = setup();

    await state.controller.startBuild();

    expect(state.resetReviewForBuildStart).toHaveBeenCalledTimes(1);
    expect(corpusBuilderApi.createBuild).toHaveBeenCalledWith({
      asset_id: "asset-1",
      auto_enrich_work_metadata: true,
      schema_id: "schema-1",
      run_guidance: { speaker: "Derrida" },
      provider_profile_id: "local",
    });
    expect(state.selectedBuildId.value).toBe("build-new");
    expect(state.currentBuild.value?.build_id).toBe("build-new");
    expect(runtime.registerExternalJob).toHaveBeenCalledTimes(1);
    expect(state.setMessage).toHaveBeenCalledWith("pdf_corpus.build_started");

    state.controller.stopPolling();
  });

  it("sends the explicit SourceUnit topology policy with a new build", async () => {
    corpusBuilderApi.createBuild.mockResolvedValue(build("build-new"));
    corpusBuilderApi.listBuilds.mockResolvedValue({ items: [build("build-new")], total: 1 });
    const state = setup(
      "",
      {},
      {
        mode: "source_units",
        source_units_per_record: 1,
        records_per_page: 4,
      },
    );

    await state.controller.startBuild();

    expect(corpusBuilderApi.createBuild).toHaveBeenCalledWith(
      expect.objectContaining({
        topology_policy: {
          mode: "source_units",
          source_units_per_record: 1,
          records_per_page: 4,
        },
      }),
    );
    state.controller.stopPolling();
  });

  it("sends reviewer-supplied document fields only when there are any", async () => {
    corpusBuilderApi.createBuild.mockResolvedValue(build("build-new"));
    corpusBuilderApi.listBuilds.mockResolvedValue({ items: [build("build-new")], total: 1 });
    const state = setup("", { document_author: "Jacques Derrida" });

    await state.controller.startBuild();

    expect(corpusBuilderApi.createBuild).toHaveBeenCalledWith(
      expect.objectContaining({ document_metadata: { document_author: "Jacques Derrida" } }),
    );
    state.controller.stopPolling();
  });

  it("rehydrates provider settings when refreshing the selected build", async () => {
    const selected = build("build-1");
    selected.request = { provider_profile_id: "profile-2" };
    corpusBuilderApi.build.mockResolvedValue(selected);
    const state = setup();
    state.selectedBuildId.value = "build-1";

    await state.controller.refreshBuild();

    expect(state.applyBuildRequest).toHaveBeenCalledWith({
      provider_profile_id: "profile-2",
    });
    expect(state.currentBuild.value?.build_id).toBe("build-1");
  });

  it("applies websocket progress in place without fetching the build snapshot", async () => {
    const running = { ...build("build-1"), status: "running", stage: "enriching", progress: 0.1 };
    const state = setup();
    state.selectedBuildId.value = "build-1";
    state.currentBuild.value = running;

    state.controller.startPolling();
    const subscription = lastRecordEventSubscription(subscribeSpy);
    subscription?.handler({
      type: "corpus.metadata_progress",
      resource_type: "corpus_build",
      resource_id: "build-1",
      payload: {
        build: {
          id: "build-1",
          raw_status: "running",
          stage: "enriching",
          progress: 0.5,
          record_count: 2,
          accepted_count: 0,
          rejected_count: 0,
          review_queue_counts: { all: 2, ready: 1, issues: 1, pending: 2 },
          metadata_total: 2,
          metadata_completed: 1,
          metadata_enriched_count: 1,
          metadata_tasks_total: 6,
          metadata_tasks_completed: 3,
          metadata_tasks_running: 2,
          metadata_tasks_queued: 1,
          metadata_active_tasks: [
            {
              record_id: "record-1",
              task: "discourse",
              started_at: "2026-10-02T04:00:00Z",
            },
            {
              record_id: "record-2",
              task: "quotation",
              started_at: "2026-10-02T04:00:01Z",
            },
          ],
          review_count: 1,
        },
      },
    });

    await vi.advanceTimersByTimeAsync(0);
    expect(corpusBuilderApi.build).not.toHaveBeenCalled();
    expect(state.currentBuild.value?.progress).toBe(0.5);
    expect(state.currentBuild.value?.metadata_enriched_count).toBe(1);
    expect(state.currentBuild.value?.metadata_completed).toBe(1);
    expect(state.currentBuild.value?.metadata_tasks_completed).toBe(3);
    expect(state.currentBuild.value?.metadata_active_tasks).toEqual([
      { record_id: "record-1", task: "discourse", started_at: "2026-10-02T04:00:00Z" },
      { record_id: "record-2", task: "quotation", started_at: "2026-10-02T04:00:01Z" },
    ]);
    expect(state.currentBuild.value?.needs_review_count).toBe(1);
    expect(state.currentBuild.value?.review_queue_counts?.issues).toBe(1);

    state.controller.stopPolling();
  });

  it("does not poll records while build-state watchers own incremental hydration", async () => {
    const running = { ...build("build-1"), status: "running", stage: "enriching", record_count: 2 };
    corpusBuilderApi.build.mockResolvedValue(running);
    const state = setup();
    state.selectedBuildId.value = "build-1";
    state.currentBuild.value = running;

    state.controller.startPolling();
    await vi.advanceTimersByTimeAsync(1400);

    expect(corpusBuilderApi.build).toHaveBeenCalledTimes(1);
    expect(state.refreshRecords).not.toHaveBeenCalled();

    state.controller.stopPolling();
  });

  it("follows the running build's realtime topic and stops once it settles", async () => {
    follow.calls.length = 0;
    const running = { ...build("build-1"), status: "running", stage: "enriching" };
    const settled = { ...build("build-1"), status: "awaiting_review" };
    corpusBuilderApi.build.mockResolvedValueOnce(settled);
    corpusBuilderApi.listBuilds.mockResolvedValue({ items: [settled], total: 1 });
    const state = setup();
    state.selectedBuildId.value = "build-1";
    state.currentBuild.value = running;

    state.controller.startPolling();
    expect(follow.calls.at(-1)?.topic).toBe("corpus-build:build-1");

    // A corpus-build event (or fallback tick) runs the same refresh.
    await follow.calls.at(-1)?.refresh();
    expect(state.currentBuild.value?.status).toBe("awaiting_review");
    expect(state.refreshRecords).toHaveBeenCalledTimes(1);
    expect(follow.calls.at(-1)?.isDone()).toBe(true);
    state.controller.stopPolling();
  });

  it("re-reads the open Record on reconciliation so a missed realtime note cannot leave it stale", async () => {
    const running = { ...build("build-1"), status: "running", stage: "enriching" };
    const state = setup();
    state.selectedBuildId.value = "build-1";
    state.currentBuild.value = running;
    state.selectedRecordId.value = "r7";

    state.controller.startPolling();
    await follow.calls.at(-1)?.refresh();
    expect(state.refreshRecord).toHaveBeenCalledWith("r7");
    state.refreshRecord.mockClear();
    // Reconciliation is bounded: an immediate second pass does not re-read again.
    await follow.calls.at(-1)?.refresh();
    expect(state.refreshRecord).not.toHaveBeenCalled();
    state.controller.stopPolling();
  });

  it("refreshes just the finished record's row on corpus.record_completed", async () => {
    const running = { ...build("build-1"), status: "running", stage: "enriching" };
    const state = setup();
    state.selectedBuildId.value = "build-1";
    state.currentBuild.value = running;

    state.controller.startPolling();
    const subscription = lastRecordEventSubscription(subscribeSpy);
    expect(subscription?.topic).toBe("corpus-build:build-1");

    subscription?.handler({
      type: "corpus.progress",
      resource_id: "build-1",
      payload: { build: {} },
    });
    expect(state.refreshRows).not.toHaveBeenCalled();

    subscription?.handler({
      type: "corpus.record_completed",
      resource_id: "build-1",
      payload: { metadata: { record_id: "r7" } },
    });
    expect(state.refreshRows).toHaveBeenCalledWith(["r7"]);
    expect(state.refreshRecord).not.toHaveBeenCalled();

    state.selectedRecordId.value = "r7";
    subscription?.handler({
      type: "corpus.record_completed",
      resource_id: "build-1",
      payload: { metadata: { record_id: "r7" } },
    });
    expect(state.refreshRecord).toHaveBeenCalledWith("r7");

    state.controller.stopPolling();
  });
});
