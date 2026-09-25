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
  const actual = await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi };
});

const runtime = vi.hoisted(() => ({
  registerExternalJob: vi.fn(),
}));

vi.mock("../../src/runtime/runtime.js", () => runtime);

import { useCorpusBuildLifecycleController } from "../../src/features/corpus-builder/composables/useCorpusBuildLifecycleController";

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

function setup(requestedBuildId = "") {
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
    applyBuildRequest,
    setMessage,
    resetReviewForBuildStart,
    refreshRecords,
    t: (key) => key,
    tf: (key) => key,
  });

  return {
    controller,
    builds,
    buildsTotal,
    selectedBuildId,
    currentBuild,
    busy,
    resetReviewForBuildStart,
    applyBuildRequest,
    setMessage,
  };
}

describe("Corpus Builder lifecycle controller", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
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
});
