/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { createVectorState, vectorState } from "../../src/state/workspaceState";

const runtime = vi.hoisted(() => ({
  setSearchScope: vi.fn(async () => ({})),
  notifyToast: vi.fn(),
  openCollectionCreationWizard: vi.fn(),
  persistPrefs: vi.fn(),
  pendingUpsertRows: vi.fn(() => []),
  upsertRows: vi.fn(),
  exportStoreJsonl: vi.fn(),
  triggerUpsertQueue: vi.fn(),
  getShellSnapshot: vi.fn(() => ({})),
  // Only the runtime-owned fields; the shared Vector Stores fields come from the vector store.
  state: {
    files: [],
    activeFileId: null,
    llmStatus: null,
    health: null,
    appConfig: {},
  },
}));
vi.mock("../../src/runtime/runtime.js", () => ({
  ...runtime,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));

const chromaApi = vi.hoisted(() => ({
  health: vi.fn(),
  collections: vi.fn(),
  probe: vi.fn(),
  setConnection: vi.fn(),
  search: vi.fn(),
  setLanguages: vi.fn(),
  setEmbedding: vi.fn(),
  setProtection: vi.fn(),
  remove: vi.fn(),
  deriveLanguages: vi.fn(),
}));
vi.mock("../../src/api/chroma", () => ({ chromaApi }));

const vectorBrowseReads = vi.hoisted(() => ({
  browse: vi.fn(),
}));
vi.mock("../../src/features/vector-stores/api/browseReads", () => ({ vectorBrowseReads }));

const systemApi = vi.hoisted(() => ({
  researcherProviders: vi.fn(),
}));
vi.mock("../../src/api/system", () => ({ systemApi }));

import VectorStoresView from "../../src/views/VectorStoresView.vue";
import { useAuthStore } from "../../src/stores/auth";

const readyHealth = {
  available: true,
  mode: "embedded" as const,
  path: "/data/chroma",
  host_path_hint: "./data/chroma",
  data_root: "/data",
  url: null,
  tenant: null,
  database: null,
  token_configured: false,
  writable: true,
  heartbeat_ok: true,
  chroma_version: "1.1.0",
  collection_count: 0,
  identity: "Local Chroma · ./data/chroma",
  error: null,
};

async function mountView(role: "admin" | "researcher") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.user = {
    id: 1,
    username: "u",
    role,
    capabilities: role === "admin" ? [] : ["page.search", "page.vector"],
  } as never;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/databases", name: "vector", component: VectorStoresView },
      { path: "/search", name: "global", component: { template: "<div>search</div>" } },
    ],
  });
  await router.push("/databases");
  await router.isReady();
  const wrapper = mount(VectorStoresView, {
    attachTo: document.body,
    global: { plugins: [pinia, router, [VueQueryPlugin, { queryClient }]] },
  });
  await flushPromises();
  return { wrapper, router };
}

describe("VectorStoresView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    Object.assign(vectorState, createVectorState());
    chromaApi.health.mockResolvedValue(readyHealth);
    chromaApi.collections.mockResolvedValue([]);
    systemApi.researcherProviders.mockResolvedValue({ profiles: [] });
    vectorBrowseReads.browse.mockResolvedValue({ works: [], page: null });
  });

  it("sends researchers to Search with database scope", async () => {
    const { wrapper, router } = await mountView("researcher");
    expect(runtime.setSearchScope).toHaveBeenCalledWith("database");
    expect(router.currentRoute.value.path).toBe("/search");
    expect(chromaApi.collections).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("shows a first-collection empty state for administrators", async () => {
    const { wrapper } = await mountView("admin");
    expect(wrapper.get(".accessible-empty-state h2").text()).toContain("first corpus collection");
    await wrapper.get(".accessible-empty-state button").trigger("click");
    expect(runtime.openCollectionCreationWizard).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("browses records through the GraphQL projection instead of full REST Records", async () => {
    chromaApi.collections.mockResolvedValue([{ name: "derrida", count: 2, status: "ready" }]);
    vectorBrowseReads.browse.mockResolvedValue({
      works: [{ work: "Of Grammatology", count: 2 }],
      page: null,
    });
    const { wrapper } = await mountView("admin");

    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();

    vectorBrowseReads.browse.mockResolvedValue({
      works: [{ work: "Of Grammatology", count: 2 }],
      page: {
        rows: [
          {
            chroma_id: "chroma-1",
            record_id: "record-1",
            work: "Of Grammatology",
            page_start: "12",
            page_end: "13",
            text_summarized: false,
            text_preview: "There is nothing outside the text…",
          },
        ],
        total: 1,
        offset: 0,
        limit: 50,
        hasNextPage: false,
      },
    });
    await wrapper.get("#vector-browse-tab-records").trigger("click");
    await flushPromises();

    expect(vectorBrowseReads.browse).toHaveBeenLastCalledWith(
      "derrida",
      expect.objectContaining({ includeRecords: true, offset: 0, limit: 50 }),
    );
    expect(wrapper.get(".store-table").text()).toContain("There is nothing outside the text…");
    expect(wrapper.get(".store-table").text()).toContain("record-1");
    wrapper.unmount();
  });

  it("opens connection settings from the workspace header", async () => {
    const { wrapper } = await mountView("admin");
    const buttons = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("Connection settings"));
    expect(buttons.length).toBeGreaterThan(0);
    await buttons[0].trigger("click");
    await flushPromises();
    expect(document.body.textContent || "").toContain("Storage backend");
    expect(document.body.textContent || "").toContain("Local filesystem");
    wrapper.unmount();
  });
});
function pending<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
describe("Vector Stores loading boundaries", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    queryClient.clear();
    queryClient.setDefaultOptions({ queries: { retry: false, staleTime: 30_000 } });
    Object.assign(vectorState, createVectorState());
    chromaApi.health.mockResolvedValue(readyHealth);
    chromaApi.collections.mockResolvedValue([{ name: "collection-a", count: 2, status: "ready" }]);
    systemApi.researcherProviders.mockResolvedValue({ profiles: [] });
    vectorBrowseReads.browse.mockResolvedValue({ works: [], page: null });
    runtime.pendingUpsertRows.mockReturnValue([]);
  });
  it("shows the title before collections resolve without a false empty state", async () => {
    const read = pending<unknown[]>();
    chromaApi.collections.mockReturnValueOnce(read.promise);
    const { wrapper } = await mountView("admin");
    expect(wrapper.find("#vector-page-title").exists()).toBe(true);
    expect(wrapper.find(".accessible-empty-state").exists()).toBe(false);
    read.resolve([]);
    await flushPromises();
    expect(wrapper.find(".accessible-empty-state").exists()).toBe(true);
    wrapper.unmount();
  });
  it.each(["health", "providers"])("shows collections while %s is pending", async (region) => {
    const read = pending<unknown>();
    if (region === "health") chromaApi.health.mockReturnValueOnce(read.promise);
    else systemApi.researcherProviders.mockReturnValueOnce(read.promise);
    const { wrapper } = await mountView("admin");
    expect(wrapper.find(".vector-collection-list").exists()).toBe(true);
    expect(wrapper.text()).toContain("collection-a");
    read.resolve(region === "health" ? readyHealth : { profiles: [] });
    await flushPromises();
    wrapper.unmount();
  });
  it("reports provider failure without clearing collections", async () => {
    systemApi.researcherProviders.mockRejectedValue(new Error("provider discovery offline"));
    const { wrapper } = await mountView("admin");
    expect(wrapper.text()).toContain("provider discovery offline");
    expect(wrapper.find(".vector-collection-list").exists()).toBe(true);
    wrapper.unmount();
  });
  it("retains collection DOM and filter on a failed refresh", async () => {
    const { wrapper } = await mountView("admin");
    const rail = wrapper.get(".vector-collection-list").element;
    await wrapper.get("#vector-collection-filter").setValue("collection");
    chromaApi.collections.mockRejectedValueOnce(new Error("collections offline"));
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(wrapper.get(".vector-collection-list").element).toBe(rail);
    expect(wrapper.get<HTMLInputElement>("#vector-collection-filter").element.value).toBe(
      "collection",
    );
    expect(wrapper.text()).toContain("collections offline");
    wrapper.unmount();
  });
  it("clears a refresh error when identical cached collections are successfully revalidated", async () => {
    const { wrapper } = await mountView("admin");
    chromaApi.collections.mockRejectedValueOnce(new Error("temporary offline"));
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(wrapper.text()).toContain("temporary offline");
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(wrapper.text()).not.toContain("temporary offline");
    expect(wrapper.find(".vector-collection-list").exists()).toBe(true);
    wrapper.unmount();
  });
  it("hydrates a warm revisit and reuses each region's fresh cached read", async () => {
    const first = await mountView("admin");
    first.wrapper.unmount();
    const second = await mountView("admin");
    expect(second.wrapper.find(".vector-collection-list").exists()).toBe(true);
    expect(chromaApi.collections).toHaveBeenCalledTimes(1);
    expect(chromaApi.health).toHaveBeenCalledTimes(1);
    expect(systemApi.researcherProviders).toHaveBeenCalledTimes(1);
    second.wrapper.unmount();
  });
  it("clears retained collections when refresh loses authorization", async () => {
    const { wrapper } = await mountView("admin");
    chromaApi.collections.mockRejectedValueOnce(
      Object.assign(new Error("Forbidden"), { status: 403 }),
    );
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(wrapper.find(".vector-collection-list").exists()).toBe(false);
    expect(wrapper.text()).toContain("Forbidden");
    wrapper.unmount();
  });
  it("keeps an unsaved provider/model draft during collection invalidation", async () => {
    const collection = {
      name: "collection-a",
      count: 0,
      embedding_provider: "profile:p",
      embedding_model: "original",
      status: "empty",
    };
    chromaApi.collections.mockResolvedValue([collection]);
    systemApi.researcherProviders.mockResolvedValue({ profiles: [{ id: "p", name: "Provider" }] });
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-settings").trigger("click");
    const model = wrapper.get<HTMLInputElement>('input[placeholder="bge-m3:latest"]');
    await model.setValue("unsaved-model");
    chromaApi.collections.mockResolvedValue([{ ...collection, description: "updated" }]);
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(model.element.value).toBe("unsaved-model");
    wrapper.unmount();
  });

  it("keeps the works panel pending instead of showing an empty collection", async () => {
    const read = pending<{ works: { work: string; count: number }[] }>();
    vectorBrowseReads.browse.mockReturnValue(read.promise);
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Loading works");
    expect(wrapper.text()).not.toContain("No work metadata was found");
    read.resolve({ works: [{ work: "Of Grammatology", count: 2 }] });
    await flushPromises();
    expect(wrapper.text()).toContain("Of Grammatology");
    wrapper.unmount();
  });

  it("shows a local browse error and retries without treating failure as an empty collection", async () => {
    vectorBrowseReads.browse.mockRejectedValueOnce(new Error("browse offline"));
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("browse offline");
    expect(wrapper.text()).not.toContain("No work metadata was found");
    vectorBrowseReads.browse.mockResolvedValueOnce({
      works: [{ work: "Of Grammatology", count: 1 }],
    });
    const retry = wrapper
      .findAll("button")
      .find(
        (button) =>
          button.text() === "Retry" && button.element.closest("#vector-browse-panel-works"),
      );
    expect(retry).toBeTruthy();
    await retry!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Of Grammatology");
    expect(wrapper.text()).not.toContain("browse offline");
    wrapper.unmount();
  });

  it("retains works when a same-collection refresh fails", async () => {
    vectorBrowseReads.browse.mockResolvedValue({
      works: [{ work: "Of Grammatology", count: 2 }],
    });
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    vectorBrowseReads.browse.mockRejectedValueOnce(new Error("browse offline"));
    await queryClient.invalidateQueries({ queryKey: ["data", "vector_collections"] });
    await flushPromises();
    expect(wrapper.text()).toContain("Of Grammatology");
    expect(wrapper.text()).toContain("browse offline");
    expect(wrapper.text()).toContain("Previously loaded content is shown");
    wrapper.unmount();
  });

  it("ignores a slow browse after the selected collection changes", async () => {
    chromaApi.collections.mockResolvedValue([
      { name: "collection-a", count: 2, status: "ready" },
      { name: "collection-b", count: 2, status: "ready" },
    ]);
    const first = pending<{ works: { work: string; count: number }[] }>();
    const second = pending<{ works: { work: string; count: number }[] }>();
    vectorBrowseReads.browse.mockImplementation((name: string) =>
      name === "collection-a" ? first.promise : second.promise,
    );
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    await wrapper
      .findAll(".storeitem")
      .find((button) => button.text().includes("collection-b"))!
      .trigger("click");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    first.resolve({ works: [{ work: "Of Grammatology", count: 1 }] });
    await flushPromises();
    expect(wrapper.text()).not.toContain("Of Grammatology");
    expect(wrapper.text()).toContain("Loading works");
    second.resolve({ works: [{ work: "Writing and Difference", count: 1 }] });
    await flushPromises();
    expect(wrapper.text()).toContain("Writing and Difference");
    expect(wrapper.text()).not.toContain("Of Grammatology");
    wrapper.unmount();
  });

  it("hides the previous record page until the requested page resolves", async () => {
    vectorBrowseReads.browse.mockResolvedValue({
      works: [{ work: "Of Grammatology", count: 60 }],
      page: {
        rows: [
          {
            chroma_id: "row-1",
            record_id: "record-1",
            work: "Of Grammatology",
            page_start: "1",
            page_end: "1",
            text_preview: "page-one text",
          },
        ],
        total: 60,
      },
    });
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-data").trigger("click");
    await flushPromises();
    await wrapper.get("#vector-browse-tab-records").trigger("click");
    await flushPromises();
    expect(wrapper.get(".store-table").text()).toContain("page-one text");
    const nextPage = pending<{
      works: { work: string; count: number }[];
      page: { rows: unknown[]; total: number };
    }>();
    vectorBrowseReads.browse.mockReturnValueOnce(nextPage.promise);
    const next = wrapper
      .findAll("#vector-browse-panel-records button")
      .find((button) => button.text() === "Next");
    await next!.trigger("click");
    await flushPromises();
    expect(wrapper.find(".store-table").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("page-one text");
    expect(wrapper.text()).toContain("Loading records");
    nextPage.resolve({
      works: [{ work: "Of Grammatology", count: 60 }],
      page: {
        rows: [
          {
            chroma_id: "row-2",
            record_id: "record-2",
            work: "Of Grammatology",
            page_start: "2",
            page_end: "2",
            text_preview: "page-two text",
          },
        ],
        total: 60,
      },
    });
    await flushPromises();
    expect(wrapper.get(".store-table").text()).toContain("page-two text");
    expect(wrapper.get(".store-table").text()).not.toContain("page-one text");
    wrapper.unmount();
  });

  it("labels the previous query until the newer search resolves and ignores the stale response", async () => {
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-retrieval").trigger("click");
    chromaApi.search.mockResolvedValueOnce({
      results: [{ id: "1", record: { work: "ALPHA", text: "alpha passage" } }],
    });
    await wrapper.get("#vector-store-query").setValue("first query");
    await wrapper.get("form.vector-search-config").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("ALPHA");
    const newer = pending<{ results: { id: string; record: { work: string; text: string } }[] }>();
    const stale = pending<{ results: { id: string; record: { work: string; text: string } }[] }>();
    chromaApi.search.mockImplementation((_store: string, body: { query: string }) =>
      body.query === "second query" ? newer.promise : stale.promise,
    );
    await wrapper.get("#vector-store-query").setValue("second query");
    await wrapper.get("form.vector-search-config").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("These results are for the previous query: first query");
    expect(wrapper.text()).toContain("ALPHA");
    stale.resolve({ results: [{ id: "stale", record: { work: "STALE", text: "old passage" } }] });
    await flushPromises();
    expect(wrapper.text()).not.toContain("STALE");
    newer.resolve({ results: [{ id: "2", record: { work: "BETA", text: "beta passage" } }] });
    await flushPromises();
    expect(wrapper.text()).toContain("BETA");
    expect(wrapper.text()).not.toContain("previous query");
    expect(wrapper.text()).not.toContain("ALPHA");
    wrapper.unmount();
  });

  it("distinguishes an empty search from the idle prompt and keeps a failed refresh", async () => {
    const { wrapper } = await mountView("admin");
    await wrapper.get("#vector-section-tab-retrieval").trigger("click");
    expect(wrapper.text()).toContain("Search results will appear here.");
    chromaApi.search.mockResolvedValueOnce({ results: [] });
    await wrapper.get("#vector-store-query").setValue("nothing");
    await wrapper.get("form.vector-search-config").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("No records matched this query.");
    expect(wrapper.text()).not.toContain("Search results will appear here.");
    chromaApi.search.mockResolvedValueOnce({
      results: [{ id: "1", record: { work: "ALPHA", text: "alpha passage" } }],
    });
    await wrapper.get("#vector-store-query").setValue("again");
    await wrapper.get("form.vector-search-config").trigger("submit");
    await flushPromises();
    chromaApi.search.mockRejectedValueOnce(new Error("search offline"));
    await wrapper.get("form.vector-search-config").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("ALPHA");
    expect(wrapper.text()).toContain("search offline");
    expect(wrapper.text()).toContain("Previously loaded content is shown");
    wrapper.unmount();
  });
});
