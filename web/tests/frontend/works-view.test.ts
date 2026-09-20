import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const runtime = vi.hoisted(() => ({
  state: {workOverview: "", activeStore: "corpus"},
  getWorksWorkspaceSnapshot: vi.fn(() => ({
    activeStore: "corpus",
    selectedWork: runtime.state.workOverview,
    works: [
      {work: "The Ear of the Other", count: 206, review: 4, files: ["ear.jsonl"], authors: ["Jacques Derrida"], years: [1985], cover: "", status: "synced", metadata: [], citation: "", insights: []},
      {work: "Writing and Difference", count: 84, review: 0, files: ["writing.jsonl"], authors: ["Jacques Derrida"], years: [1967], cover: "", status: "exists", metadata: [], citation: "", insights: []},
    ],
  })),
  persistPrefs: vi.fn(),
  hasCorpusDb: vi.fn(() => true),
  openWorksSearch: vi.fn(),
  openWorksMetadataEditor: vi.fn(),
  openWorksMetadataLlm: vi.fn(),
  syncWorks: vi.fn(async () => true),
  getProviderProfilesForUi: vi.fn(() => [{id: "p1"}]),
  openWorksSeparate: vi.fn(),
  openWorksBulkMetadataLlm: vi.fn(),
  openWorksRemove: vi.fn(),
  openWorksAnnotations: vi.fn(),
}));
vi.mock("../../src/runtime/runtime.js", () => ({...runtime}));

import WorksView from "../../src/views/WorksView.vue";

async function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{path: "/works", component: WorksView}],
  });
  await router.push("/works");
  await router.isReady();
  const wrapper = mount({template: "<RouterView />"}, {global: {plugins: [pinia, router]}});
  await flushPromises();
  return wrapper;
}

describe("WorksView", () => {
  beforeEach(() => {
    runtime.state.workOverview = "";
    runtime.getWorksWorkspaceSnapshot.mockClear();
    runtime.persistPrefs.mockClear();
  });

  it("filters the work library by title", async () => {
    const wrapper = await mountView();
    expect(wrapper.findAll(".work-card")).toHaveLength(2);
    await wrapper.get(".works-search input").setValue("Writing");
    expect(wrapper.findAll(".work-card")).toHaveLength(1);
    expect(wrapper.get(".work-card-copy strong").text()).toBe("Writing and Difference");
  });

  it("selects a work and exposes its selected-work actions", async () => {
    const wrapper = await mountView();
    await wrapper.findAll(".work-card-select")[0].trigger("click");
    expect(runtime.state.workOverview).toBe("The Ear of the Other");
    expect(runtime.persistPrefs).toHaveBeenCalled();
    expect(wrapper.get(".works-selection h2").text()).toBe("The Ear of the Other");
    await wrapper.get(".works-selection").get("button").trigger("click");
    expect(runtime.openWorksSearch).toHaveBeenCalledWith("The Ear of the Other", {needsReview: false});
  });
});
