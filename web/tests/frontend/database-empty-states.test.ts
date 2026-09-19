import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const runtime = vi.hoisted(() => ({
  getResearchWorkspaceSnapshot: vi.fn(),
  getSearchWorkspaceSnapshot: vi.fn(),
  openDatabaseCreationFromResearch: vi.fn(),
  notifyToast: vi.fn(),
  updateSearchQuery: vi.fn(),
  getResearchJob: vi.fn(),
  getShellSnapshot: vi.fn(() => ({})),
}));
// Vue's template proxy probes the namespace for reactivity flags; a strict module
// mock throws on unknown keys, so declare them.
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime, __v_isRef: false, __v_isReadonly: false, __v_isShallow: false, __v_skip: true, __v_raw: undefined }));

import ResearchView from "../../src/views/ResearchView.vue";
import SearchView from "../../src/views/SearchView.vue";
import { useAuthStore } from "../../src/stores/auth";

async function mountView(component: object, path: string, role: "admin" | "researcher") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.user = { id: 1, username: "u", role, capabilities: role === "admin" ? [] : ["page.search"] } as never;
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/rag", name: "rag", component }, { path: "/search", name: "search", component }, { path: "/", component: { template: "<div/>" } }] });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(component, { global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

const searchSnapshot = (capabilities: Record<string, boolean>) => ({
  has_database: false, has_loaded_records: false, scope: "global", query: "", advanced_open: false,
  filter_fields: [{ key: "work", label: "Work" }], capabilities,
});

describe("missing corpus database", () => {
  beforeEach(() => vi.clearAllMocks());

  it("explains Research in place for an administrator and offers to create a collection", async () => {
    runtime.getResearchWorkspaceSnapshot.mockResolvedValue({ stores: [] });
    const wrapper = await mountView(ResearchView, "/rag", "admin");

    expect(wrapper.get(".accessible-empty-state h2").text()).toContain("corpus database");
    expect(runtime.notifyToast).not.toHaveBeenCalled();
    expect(runtime.openDatabaseCreationFromResearch).not.toHaveBeenCalled();
    await wrapper.get(".accessible-empty-state button").trigger("click");
    expect(runtime.openDatabaseCreationFromResearch).toHaveBeenCalledTimes(1);
  });

  it("does not offer creation to a researcher without database access", async () => {
    runtime.getResearchWorkspaceSnapshot.mockResolvedValue({ stores: [] });
    const wrapper = await mountView(ResearchView, "/rag", "researcher");

    expect(wrapper.find(".accessible-empty-state").exists()).toBe(true);
    expect(wrapper.find(".accessible-empty-state button").exists()).toBe(false);
    expect(runtime.openDatabaseCreationFromResearch).not.toHaveBeenCalled();
  });

  it("explains Search in place instead of redirecting when nothing is searchable", async () => {
    runtime.getSearchWorkspaceSnapshot.mockResolvedValue(searchSnapshot({ can_manage_database: true }));
    const wrapper = await mountView(SearchView, "/search", "admin");

    expect(wrapper.find(".accessible-empty-state").exists()).toBe(true);
    expect(runtime.notifyToast).not.toHaveBeenCalled();
    expect(runtime.openDatabaseCreationFromResearch).not.toHaveBeenCalled();
    await wrapper.get(".accessible-empty-state button").trigger("click");
    expect(runtime.openDatabaseCreationFromResearch).toHaveBeenCalledTimes(1);
  });
});
