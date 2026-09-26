/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const pdfCorpusApi = vi.hoisted(() => ({
  listAssets: vi.fn(),
  profiles: vi.fn(),
  listBuilds: vi.fn(),
  build: vi.fn(),
  records: vi.fn(),
  blocks: vi.fn(),
  markViewed: vi.fn(),
  patchText: vi.fn(),
  patchMetadata: vi.fn(),
  reviewDecision: vi.fn(),
  assetContentUrl: vi.fn((assetId: string) => `/api/pdf/assets/${assetId}/content`),
}));

vi.mock("../../src/api/corpus", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/corpus")>("../../src/api/corpus");
  return { ...actual, corpusBuilderApi: pdfCorpusApi };
});

const systemApi = vi.hoisted(() => ({
  researcherProviders: vi.fn(),
  researcherProviderAvailability: vi.fn(),
}));

vi.mock("../../src/api/system", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/system")>("../../src/api/system");
  return { ...actual, systemApi };
});

const metadataSchemasApi = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
}));

vi.mock("../../src/api/metadataSchemas", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/metadataSchemas")>(
    "../../src/api/metadataSchemas",
  );
  return { ...actual, metadataSchemasApi };
});

const runtime = vi.hoisted(() => ({
  getProviderProfilesForUi: vi.fn(() => []),
  getProviderRequestConfigForUi: vi.fn(() => null),
  getDefaultProviderProfileId: vi.fn(() => ""),
  state: { pdf: { file: null } },
}));

vi.mock("../../src/runtime/runtime.js", () => ({
  ...runtime,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));

import PdfCorpusBuilder from "../../src/components/PdfCorpusBuilder.vue";
import { useI18nStore } from "../../src/stores/i18n";

const defaultSchema = {
  format_version: 1,
  id: "default",
  name: "Default",
  description: "Default metadata schema",
  groups: [],
  fields: [],
};

async function mountBuilder() {
  const pinia = createPinia();
  setActivePinia(pinia);
  useI18nStore().dictionary = {};
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/pdf", component: { template: "<div />" } }],
  });
  await router.push("/pdf?mode=builder");
  await router.isReady();
  const wrapper = shallowMount(PdfCorpusBuilder, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  });
  await flushPromises();
  return wrapper;
}

const reviewBuild = {
  build_id: "build-1",
  asset_id: "asset-1",
  status: "awaiting_review",
  stage: "review",
  record_count: 1,
  metadata_total: 1,
  schema: defaultSchema,
  request: {},
};

const reviewRecord = {
  record_id: "record-1",
  record_revision: 1,
  text: "Original text",
  text_length: 13,
  source_block_ids: ["block-1"],
  source_spans: [{ block_id: "block-1", page: 1 }],
  metadata_field_status: {},
  metadata_evidence: {},
  review_disposition: "pending",
  needs_review: true,
  accepted: false,
  rejected: false,
};

describe("PdfCorpusBuilder characterization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pdfCorpusApi.listAssets.mockResolvedValue({ items: [] });
    pdfCorpusApi.profiles.mockResolvedValue({ items: [] });
    pdfCorpusApi.listBuilds.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
    pdfCorpusApi.build.mockResolvedValue(reviewBuild);
    pdfCorpusApi.records.mockResolvedValue({
      items: [reviewRecord],
      total: 1,
      offset: 0,
      limit: 50,
      queue_counts: {},
      metadata_values: {},
    });
    pdfCorpusApi.blocks.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 500 });
    pdfCorpusApi.markViewed.mockResolvedValue({});
    systemApi.researcherProviders.mockResolvedValue({ profiles: [] });
    systemApi.researcherProviderAvailability.mockResolvedValue({
      available: false,
      model_available: false,
    });
    metadataSchemasApi.list.mockResolvedValue({
      items: [
        {
          id: "default",
          name: "Default",
          description: "Default metadata schema",
          builtin: true,
          field_count: 0,
          groups: [],
          hash: "default",
        },
      ],
    });
    metadataSchemasApi.get.mockResolvedValue(defaultSchema);
  });

  it("loads the empty workspace and exposes the source/configuration workflow", async () => {
    const wrapper = await mountBuilder();

    expect(pdfCorpusApi.listAssets).toHaveBeenCalledTimes(1);
    expect(pdfCorpusApi.profiles).toHaveBeenCalledTimes(1);
    expect(pdfCorpusApi.listBuilds).toHaveBeenCalledWith(0, 100);
    expect(systemApi.researcherProviders).toHaveBeenCalledTimes(1);
    expect(metadataSchemasApi.list).toHaveBeenCalledTimes(1);
    expect(metadataSchemasApi.get).toHaveBeenCalledWith("default");

    expect(wrapper.findComponent({ name: "CorpusBuilderWorkspaceHeader" }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: "CorpusWorkflowStepper" }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: "CorpusSourceIngest" }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: "CorpusBuildReadiness" }).exists()).toBe(true);
    expect(wrapper.get("#pdf-corpus-source-title").text()).toBe("Source document");

    wrapper.unmount();
  });

  it("keeps working on the built-in schema when the schema list comes back without items", async () => {
    metadataSchemasApi.list.mockResolvedValue({} as never);
    const wrapper = await mountBuilder();
    // Before the fix the list became undefined and reading the chosen schema threw.
    const exposed = wrapper.vm as unknown as { schemaChoices: unknown[]; chosenSchema: unknown };
    expect(exposed.schemaChoices).toEqual([]);
    expect(exposed.chosenSchema).toBeUndefined();
    expect(metadataSchemasApi.get).toHaveBeenCalledWith("default");
    wrapper.unmount();
  });

  it("applies text edits before the unresolved persistence request settles", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.patchText.mockReturnValue(new Promise(() => undefined));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      saveTextFromFocus: (text: string, resolve: boolean) => Promise<void>;
    };

    await exposed.saveTextFromFocus("Edited immediately", false);

    expect(exposed.selectedRecord.text).toBe("Edited immediately");
    expect(exposed.selectedRecord.record_revision).toBe(2);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(pdfCorpusApi.patchText).toHaveBeenCalledWith(
      "build-1",
      "record-1",
      "Edited immediately",
      1,
      false,
    );
    wrapper.unmount();
  });

  it("keeps the local edit and scopes a persistence error to its record and field", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.patchText.mockRejectedValue(new Error("offline"));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      saveTextFromFocus: (text: string, resolve: boolean) => Promise<void>;
      error: string;
    };

    await exposed.saveTextFromFocus("Edited locally", false);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(exposed.selectedRecord.text).toBe("Edited locally");
    expect(exposed.error).toContain("record-1");
    expect(exposed.error).toContain("text");
    expect(exposed.error).toContain("offline");
    expect(pdfCorpusApi.patchText).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it("shows acceptance immediately while authoritative review persistence is pending", async () => {
    pdfCorpusApi.listBuilds.mockResolvedValue({
      items: [reviewBuild],
      total: 1,
      offset: 0,
      limit: 100,
    });
    pdfCorpusApi.listAssets.mockResolvedValue({
      items: [{ asset_id: "asset-1", filename: "source.pdf", page_count: 1 }],
    });
    pdfCorpusApi.blocks.mockResolvedValue({
      items: [{ block_id: "block-1", page: 1, text: "Original text" }],
      total: 1,
      offset: 0,
      limit: 500,
    });
    pdfCorpusApi.reviewDecision.mockReturnValue(new Promise(() => undefined));
    const wrapper = await mountBuilder();
    const exposed = wrapper.vm as unknown as {
      selectedRecord: typeof reviewRecord;
      setDisposition: (disposition: "accepted") => Promise<void>;
    };

    await exposed.setDisposition("accepted");

    expect(exposed.selectedRecord.review_disposition).toBe("accepted");
    expect(exposed.selectedRecord.accepted).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(pdfCorpusApi.reviewDecision).toHaveBeenCalledWith(
      "build-1",
      "record-1",
      "accepted",
      "",
      1,
      "all",
    );
    wrapper.unmount();
  });
});
