/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const pdfCorpusApi = vi.hoisted(() => ({
  listAssets: vi.fn(),
  profiles: vi.fn(),
  listBuilds: vi.fn(),
  assetContentUrl: vi.fn((assetId: string) => `/api/pdf/assets/${assetId}/content`),
}));

vi.mock("../../src/api/pdfCorpus", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/pdfCorpus")>(
    "../../src/api/pdfCorpus",
  );
  return { ...actual, pdfCorpusApi };
});

const systemApi = vi.hoisted(() => ({
  researcherProviders: vi.fn(),
  researcherProviderAvailability: vi.fn(),
}));

vi.mock("../../src/api/system", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/system")>("../../src/api/system");
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

describe("PdfCorpusBuilder characterization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pdfCorpusApi.listAssets.mockResolvedValue({ items: [] });
    pdfCorpusApi.profiles.mockResolvedValue({ items: [] });
    pdfCorpusApi.listBuilds.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
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

    expect(wrapper.get("#pdf-corpus-builder-title").text()).toBe(
      "Build auditable records from source media",
    );
    expect(wrapper.findComponent({ name: "CorpusWorkflowStepper" }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: "CorpusSourceIngest" }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: "CorpusBuildReadiness" }).exists()).toBe(true);
    expect(wrapper.get("#pdf-corpus-source-title").text()).toBe("Source document");

    wrapper.unmount();
  });
});
