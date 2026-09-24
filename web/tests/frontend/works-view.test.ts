/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WorksItem, WorksSnapshot } from "../../src/types/works";

function biblio(overrides: Partial<WorksItem["publisher"]> = {}) {
  return { field_label: "Publisher", value: "", mixed: false, unique_count: 0, ...overrides };
}

function workItem(overrides: Partial<WorksItem> = {}): WorksItem {
  return {
    work: "Glas",
    count: 12,
    review: 2,
    annotations: 1,
    files: ["glas.jsonl"],
    authors: ["Jacques Derrida"],
    years: ["1974"],
    cover: "",
    citation: "Derrida, Jacques. Glas.",
    year_label: "1974",
    subtitle: "Jacques Derrida · 1974",
    publisher: biblio({ value: "Galilée" }),
    translator: biblio({ field_label: "Translator" }),
    metadata: [
      {
        field: "document_author",
        field_label: "Document author",
        value: "Jacques Derrida",
        mixed: false,
        unique_count: 0,
      },
    ],
    status: { kind: "synced", label: "Synced" },
    insights: [
      {
        id: "topics",
        field: "topics",
        title: "Top 5 topics in the work",
        heading: "Top 5 topics",
        type: "bars",
        values: [{ key: "writing", value: 4 }],
      },
    ],
    ...overrides,
  };
}

function adminSnapshot(overrides: Partial<WorksSnapshot> = {}): WorksSnapshot {
  const item = workItem();
  return {
    mode: "admin",
    available: true,
    shared: false,
    error: "",
    works: [item],
    selected: null,
    query: "",
    selectedWork: "",
    stores: [{ name: "derrida-primary", count: 40 }],
    activeStore: "derrida-primary",
    activeStoreCount: 40,
    totalWorks: 1,
    totalRecords: 12,
    dbUnavailableReason: "",
    storesEmptyLabel: "No corpus Chroma collections",
    citationLabel: "Full citation",
    populateDisabledReason: "",
    syncAllDisabledReason: "",
    corpusManageDeniedReason: "Your role cannot load corpus files.",
    hasProviderProfiles: true,
    capabilities: { canManageCorpus: true, canSync: true, canSyncAll: true, canPopulate: true },
    ...overrides,
  };
}

const runtime = vi.hoisted(() => ({
  state: { view: "home" },
  getWorksWorkspaceSnapshot: vi.fn(),
  prepareWorksWorkspace: vi.fn(async () => ({ error: "" })),
  getShellSnapshot: vi.fn(() => ({
    files: [{ id: "f1", name: "glas.jsonl", count: 12, dirty: 0, active: true }],
  })),
  setWorksSearch: vi.fn(),
  setWorksOverview: vi.fn(),
  setWorksStore: vi.fn(async () => undefined),
  syncWork: vi.fn(async () => true),
  syncAllWorks: vi.fn(async () => true),
  openSeparateWorksModal: vi.fn(),
  populateAllWorksMetadata: vi.fn(),
  openWorkMetadataLlmDialog: vi.fn(),
  openWorkMetadataEditor: vi.fn(),
  openWorkAnnotations: vi.fn(),
  searchWorkOverview: vi.fn(),
  searchWorkRecords: vi.fn(),
  inspectWorksMixedField: vi.fn(),
  searchWorksInsight: vi.fn(),
  reviewFlaggedWork: vi.fn(),
  autoImproveWork: vi.fn(),
  removeEntireWork: vi.fn(),
  browseResearcherWork: vi.fn(),
  decorateDisabledControls: vi.fn(),
  setTranslationDictionary: vi.fn(),
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime }));

import WorksView from "../../src/views/WorksView.vue";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";
import { useAuthStore } from "../../src/stores/auth";

async function waitForCards() {
  await flushPromises();
  await new Promise<void>((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
  );
  await flushPromises();
}

async function mountWorks() {
  const wrapper = mount(WorksView, { attachTo: document.body });
  await waitForCards();
  return wrapper;
}

describe("WorksView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    const snap = adminSnapshot();
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(snap);
    useI18nStore().languages = [
      { code: "en-US", name: "English", flag: "" },
      { code: "fr-CA", name: "Français", flag: "" },
    ] as never;
    useAuthStore().user = { id: 1, username: "admin", role: "admin", capabilities: [] } as never;
    useShellStore().snapshot.files = [
      { id: "f1", name: "glas.jsonl", count: 12, dirty: 0, active: true, origin: "imported" },
    ];
  });

  it("renders the admin library from the snapshot and selects a work", async () => {
    const wrapper = await mountWorks();
    expect(runtime.prepareWorksWorkspace).toHaveBeenCalled();
    expect(runtime.state.view).toBe("works");
    expect(wrapper.find("#worksSearch").exists()).toBe(true);
    expect(wrapper.text()).toContain("Glas");
    expect(wrapper.text()).toContain("Sync all works");
    expect(wrapper.get("[data-work-status='Glas']").attributes("data-tone")).toBe("success");
    expect(wrapper.get(".work-library-card").text()).not.toMatch(/Synchroniser/);
    await wrapper.get(".work-library-card").trigger("click");
    expect(runtime.setWorksOverview).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });

  it("keeps bibliographic and corpus actions on the runtime command surface", async () => {
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({
        selected: workItem(),
        selectedWork: "Glas",
      }),
    );
    const wrapper = await mountWorks();
    await wrapper.get("#overviewSearchWork").trigger("click");
    expect(runtime.searchWorkOverview).toHaveBeenCalledWith("Glas");
    await wrapper.get("#populateAllWorks").trigger("click");
    expect(runtime.populateAllWorksMetadata).toHaveBeenCalled();
    await wrapper.get("#syncAllWorks").trigger("click");
    expect(runtime.syncAllWorks).toHaveBeenCalled();
    await wrapper.get("[data-upsert-work='Glas']").trigger("click");
    expect(runtime.syncWork).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });

  it("shows the JSONL drop zone when no corpus files are loaded", async () => {
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({
        available: false,
        works: [],
        totalWorks: 0,
        totalRecords: 0,
        capabilities: {
          canManageCorpus: true,
          canSync: false,
          canSyncAll: false,
          canPopulate: false,
        },
      }),
    );
    const wrapper = await mountWorks();
    expect(wrapper.get(".empty h1").text()).toContain("Open a corpus workspace");
    await wrapper.get("#choose").trigger("click");
    wrapper.unmount();
  });

  it("renders the researcher database menu and browses the selected work", async () => {
    useAuthStore().user = {
      id: 2,
      username: "reader",
      role: "researcher",
      capabilities: ["page.works"],
    } as never;
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({
        mode: "researcher",
        selected: workItem({ files: [], review: 0, publisher: biblio(), translator: biblio() }),
        selectedWork: "Glas",
        capabilities: {
          canManageCorpus: false,
          canSync: false,
          canSyncAll: false,
          canPopulate: false,
        },
      }),
    );
    const wrapper = await mountWorks();
    expect(wrapper.get("#works-page-title").text()).toContain("Works");
    expect(wrapper.get(".researcher-work-menu-card").text()).toContain("Glas");
    await wrapper.get("#browseResearchWork").trigger("click");
    expect(runtime.browseResearcherWork).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });
});
