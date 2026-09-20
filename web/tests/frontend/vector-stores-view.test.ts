import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

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
  state: {
    activeStore: "",
    vectorTab: "overview",
    vectorCollectionFilter: "",
    vectorAutoCreateRequested: false,
    files: [],
    activeFileId: null,
    storeBrowseMode: "works",
    storePage: 1,
    storePageSize: 50,
    storeWork: "",
    storeQuery: "",
    storeSearchMode: "",
    llmStatus: null,
    health: null,
    appConfig: {},
    stores: [],
  },
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime, __v_isRef: false, __v_isReadonly: false, __v_isShallow: false, __v_skip: true, __v_raw: undefined }));

const chromaApi = vi.hoisted(() => ({
  health: vi.fn(),
  collections: vi.fn(),
  probe: vi.fn(),
  setConnection: vi.fn(),
  works: vi.fn(),
  records: vi.fn(),
  search: vi.fn(),
  setLanguages: vi.fn(),
  setEmbedding: vi.fn(),
  setProtection: vi.fn(),
  remove: vi.fn(),
  deriveLanguages: vi.fn(),
}));
vi.mock("../../src/api/chroma", () => ({ chromaApi }));

import VectorStoresView from "../../src/views/VectorStoresView.vue";
import { useAuthStore } from "../../src/stores/auth";

const readyHealth = {
  available: true, mode: "embedded" as const, path: "/data/chroma", host_path_hint: "./data/chroma", data_root: "/data",
  url: null, tenant: null, database: null, token_configured: false, writable: true, heartbeat_ok: true,
  chroma_version: "1.1.0", collection_count: 0, identity: "Local Chroma · ./data/chroma", error: null,
};

async function mountView(role: "admin" | "researcher") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.user = { id: 1, username: "u", role, capabilities: role === "admin" ? [] : ["page.search", "page.vector"] } as never;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/databases", name: "vector", component: VectorStoresView },
      { path: "/search", name: "global", component: { template: "<div>search</div>" } },
    ],
  });
  await router.push("/databases");
  await router.isReady();
  const wrapper = mount(VectorStoresView, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return { wrapper, router };
}

describe("VectorStoresView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runtime.state.vectorAutoCreateRequested = false;
    runtime.state.activeStore = "";
    chromaApi.health.mockResolvedValue(readyHealth);
    chromaApi.collections.mockResolvedValue([]);
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

  it("opens connection settings from the workspace header", async () => {
    const { wrapper } = await mountView("admin");
    const buttons = wrapper.findAll("button").filter(button => button.text().includes("Connection settings"));
    expect(buttons.length).toBeGreaterThan(0);
    await buttons[0].trigger("click");
    await flushPromises();
    expect(document.body.textContent || "").toContain("Storage backend");
    expect(document.body.textContent || "").toContain("Local filesystem");
    wrapper.unmount();
  });
});
