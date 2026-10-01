/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
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
    scopeWorks: [{ work: item.work }],
    selected: null,
    query: "",
    selectedWork: "",
    stores: [{ name: "derrida-primary", count: 40 }],
    activeStore: "derrida-primary",
    activeStoreCount: 40,
    indexFreshness: {
      state: "current",
      totalRecords: 12,
      currentRecords: 12,
      changedRecords: 0,
      presentRecords: 0,
      absentRecords: 0,
      unknownRecords: 0,
      unavailableRecords: 0,
    },
    totalWorks: 1,
    visibleWorks: 1,
    totalRecords: 12,
    sourceFileCount: 1,
    totalReview: 2,
    authors: ["Jacques Derrida"],
    sort: "title-asc",
    filters: { needsReview: false, dbStatus: "", author: "" },
    viewMode: "cards",
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
  ensureCorpusWorkspaceLoaded: vi.fn(async () => undefined),
  prepareWorksWorkspace: vi.fn(async () => ({ error: "" })),
  getShellSnapshot: vi.fn(() => ({
    files: [{ id: "f1", name: "glas.jsonl", count: 12, dirty: 0, active: true }],
  })),
  setWorksSearch: vi.fn(),
  setWorksOverview: vi.fn(),
  setWorksView: vi.fn(),
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
  listSemanticMapSources: vi.fn(() => ({
    records: [{ id: "record-1", work: "Glas", concepts: [], topics: ["writing"], persons: [] }],
    focusId: "record-1",
  })),
  setTranslationDictionary: vi.fn(),
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime }));

const siteApi = vi.hoisted(() => ({
  exportOptions: vi.fn(),
  exportSite: vi.fn(),
}));
vi.mock("../../src/api/sites", () => ({ sitesApi: siteApi }));
vi.mock("../../src/api/corpus", () => ({
  corpusBuildsApi: {
    workSemanticMapRecords: vi.fn(async () => ({ records: [] })),
  },
}));

import WorksView from "../../src/views/WorksView.vue";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";
import { useAuthStore } from "../../src/stores/auth";

HTMLDialogElement.prototype.showModal = function showModal() {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function close() {
  this.removeAttribute("open");
  this.dispatchEvent(new Event("close"));
};

async function waitForCards() {
  await flushPromises();
  await new Promise<void>((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
  );
  await flushPromises();
}

/** Opens the menu whose trigger has this accessible name and chooses an item. */
async function chooseMenuItem(wrapper: VueWrapper, trigger: string, item: string) {
  const button = wrapper
    .findAll("button.ui-menu-trigger")
    .find((candidate) => (candidate.attributes("aria-label") || candidate.text()) === trigger);
  expect(button, `menu trigger ${trigger}`).toBeDefined();
  await button!.trigger("click");
  const entry = wrapper.findAll("[role='menuitem']").find((node) => node.text().includes(item));
  expect(entry, `menu item ${item}`).toBeDefined();
  await entry!.trigger("click");
  await flushPromises();
}

function setViewportWide(wide: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string) => ({
      matches: wide,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  });
}

async function mountWorks() {
  const wrapper = mount(WorksView, { attachTo: document.body });
  await waitForCards();
  return wrapper;
}

describe("WorksView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setViewportWide(true);
    siteApi.exportOptions.mockResolvedValue({
      languages: [
        { code: "en-US", name: "English", flag: "🇺🇸" },
        { code: "fr-CA", name: "Français", flag: "🇨🇦" },
      ],
      provider_profiles: [
        {
          id: "openai-main",
          name: "OpenAI-compatible lab",
          type: "openai",
          base_url: "https://models.example.edu/v1",
          model: "gpt-oss:20b",
        },
      ],
    });
    siteApi.exportSite.mockResolvedValue({
      blob: new Blob(["site"], { type: "application/zip" }),
      filename: "glas-site.zip",
      publicationId: "sitepub-1",
      recordCount: 12,
      workCount: 1,
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:site"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
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
    expect(wrapper.get("h1").text()).toBe("Works");
    expect(wrapper.find(".ui-page-header").exists()).toBe(true);
    expect(wrapper.find("#worksSearch").exists()).toBe(true);
    expect(wrapper.text()).toContain("Glas");
    expect(wrapper.get("[data-work-status='Glas']").attributes("data-tone")).toBe("success");
    // The per-card Sync no longer outranks review and Records: it lives in the card menu.
    expect(wrapper.get(".works-card-footer").text()).not.toMatch(/\bSync\b/);
    await wrapper.get(".works-card-select").trigger("click");
    expect(runtime.setWorksOverview).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });

  it("separates the loaded workspace from the corpus database and keeps sync with the database", async () => {
    const wrapper = await mountWorks();
    const loaded = wrapper.get("[data-works-context='loaded']");
    expect(loaded.text()).toContain("1 source files · 12 records");
    const database = wrapper.get("[data-works-context='database']");
    expect(database.text()).toContain("40 records");
    await database
      .findAll("button")
      .find((button) => button.text().includes("Sync workspace to database"))!
      .trigger("click");
    expect(runtime.syncAllWorks).toHaveBeenCalled();
    // The page header holds one direct action and one menu, and no sync.
    const header = wrapper.get(".ui-page-header-actions");
    expect(header.text()).not.toMatch(/Sync/);
    expect(header.findAll("button.ui-button")).toHaveLength(1);
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
    const inspector = wrapper.get(".works-inspector-pane");
    await inspector
      .findAll("button")
      .find((button) => button.text().includes("Open records"))!
      .trigger("click");
    expect(runtime.searchWorkOverview).toHaveBeenCalledWith("Glas");
    await chooseMenuItem(wrapper, "More actions", "Populate all metadata with LLM");
    expect(runtime.populateAllWorksMetadata).toHaveBeenCalled();
    await chooseMenuItem(wrapper, "More actions", "Separate works");
    expect(runtime.openSeparateWorksModal).toHaveBeenCalled();
    await chooseMenuItem(wrapper, "Actions for Glas", "Sync this work to database");
    expect(runtime.syncWork).toHaveBeenCalledWith("Glas");
    await chooseMenuItem(wrapper, "Actions for Glas", "Semantic map");
    await chooseMenuItem(wrapper, "Actions for Glas", "Edit metadata");
    expect(runtime.openWorkMetadataEditor).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });

  it("opens the records that need review from the review count", async () => {
    const wrapper = await mountWorks();
    await wrapper.get("[data-work-review='Glas']").trigger("click");
    expect(runtime.searchWorkRecords).toHaveBeenCalledWith("Glas", { needsReview: true });
    await wrapper.get("[data-work-records='Glas']").trigger("click");
    expect(runtime.searchWorkRecords).toHaveBeenCalledWith("Glas", { needsReview: false });
    wrapper.unmount();
  });

  it("selects a work with the keyboard-operable card button and keeps the library in place", async () => {
    const wrapper = await mountWorks();
    const select = wrapper.get(".works-card-select");
    expect(select.element.tagName).toBe("BUTTON");
    expect(select.attributes("aria-pressed")).toBe("false");
    const scroll = vi.spyOn(window, "scrollTo");
    await select.trigger("click");
    expect(scroll).not.toHaveBeenCalled();
    expect(wrapper.find("article[role], article[tabindex]").exists()).toBe(false);
    wrapper.unmount();
  });

  it("places the selected work in a stable inspector beside the library, not above it", async () => {
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({ selected: workItem(), selectedWork: "Glas" }),
    );
    const wrapper = await mountWorks();
    const layout = wrapper.get(".works-layout");
    expect(layout.classes()).toContain("has-inspector");
    const children = Array.from(layout.element.children).map((node) => node.className);
    expect(children[0]).toContain("works-library");
    expect(children[1]).toContain("works-inspector-pane");
    expect(wrapper.get(".works-inspector-pane h2").text()).toBe("Glas");
    await wrapper.get("button[aria-label='Close work details']").trigger("click");
    expect(runtime.setWorksOverview).toHaveBeenCalledWith("");
    wrapper.unmount();
  });

  it("opens the selected work in an accessible dialog on narrow screens", async () => {
    setViewportWide(false);
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({ selected: workItem(), selectedWork: "Glas" }),
    );
    const wrapper = await mountWorks();
    expect(wrapper.find(".works-inspector-pane").exists()).toBe(false);
    expect(wrapper.get(".works-layout").classes()).not.toContain("has-inspector");
    const dialog = document.body.querySelector("[role='dialog']");
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
    expect(dialog?.textContent).toContain("Glas");
    expect(dialog?.textContent).toContain("Open records");
    expect(wrapper.findAll("h1")).toHaveLength(1);
    wrapper.unmount();
  });

  it("does not change page-wide totals when a search narrows the library", async () => {
    runtime.getWorksWorkspaceSnapshot.mockReturnValue(
      adminSnapshot({
        works: [],
        visibleWorks: 0,
        totalWorks: 64,
        totalRecords: 3218,
        totalReview: 7,
      }),
    );
    const wrapper = await mountWorks();
    expect(wrapper.get("[data-works-context='loaded']").text()).toContain("3,218 records");
    expect(wrapper.get(".works-toolbar-summary").text()).toContain("0 of 64 works");
    expect(wrapper.get(".works-toolbar-summary").text()).toContain("7 need review");
    expect(wrapper.text()).toContain("No works match the current search and filters.");
    wrapper.unmount();
  });

  it("sends sort, filter and view-mode changes through the typed command", async () => {
    const wrapper = await mountWorks();
    await wrapper.get("#worksSort").setValue("records-desc");
    expect(runtime.setWorksView).toHaveBeenCalledWith({ sort: "records-desc" });
    await wrapper.get(".works-toolbar-views .ui-button-wrap:last-child button").trigger("click");
    expect(runtime.setWorksView).toHaveBeenCalledWith({ viewMode: "compact" });
    const filters = wrapper.findAll("button").find((button) => button.text().includes("Filters"))!;
    await filters.trigger("click");
    await wrapper.get("#works-filter-panel input[type='checkbox']").setValue(true);
    expect(runtime.setWorksView).toHaveBeenCalledWith({ needsReview: true });
    wrapper.unmount();
  });

  it("creates a static site from selected works in the active corpus database", async () => {
    const wrapper = await mountWorks();
    await chooseMenuItem(wrapper, "More actions", "Create site");

    const dialog = wrapper.get(".create-site-dialog");
    expect(dialog.attributes("open")).toBeDefined();
    expect(dialog.text()).toContain("Glas");

    await dialog.get("[data-site-work='Glas']").setValue(true);
    await dialog.get("input[placeholder='Research collection']").setValue("Glas research site");
    await dialog.get("form").trigger("submit");
    await flushPromises();

    expect(siteApi.exportSite).toHaveBeenCalledWith({
      store: "derrida-primary",
      works: ["Glas"],
      title: "Glas research site",
      description: "",
      locale: "en-US",
      languages: ["en-US", "fr-CA"],
      provider_profile_ids: ["openai-main"],
      export_format: "two-file",
    });
    expect(URL.createObjectURL).toHaveBeenCalled();
    wrapper.unmount();
  });

  it("exports any selected subset of installed languages and provider profiles", async () => {
    const wrapper = await mountWorks();
    await chooseMenuItem(wrapper, "More actions", "Create site");

    const dialog = wrapper.get(".create-site-dialog");
    await dialog.get("[data-site-work='Glas']").setValue(true);
    await dialog.get("[data-site-language='fr-CA']").setValue(false);
    await dialog.get("[data-site-provider='openai-main']").setValue(false);
    await dialog.get("input[placeholder='Research collection']").setValue("English-only Glas");
    await dialog.get("form").trigger("submit");
    await flushPromises();

    expect(siteApi.exportSite).toHaveBeenCalledWith({
      store: "derrida-primary",
      works: ["Glas"],
      title: "English-only Glas",
      description: "",
      locale: "en-US",
      languages: ["en-US"],
      provider_profile_ids: [],
      export_format: "two-file",
    });
    wrapper.unmount();
  });

  it("can export the research site as a single-container nginx bundle", async () => {
    const wrapper = await mountWorks();
    await chooseMenuItem(wrapper, "More actions", "Create site");

    const dialog = wrapper.get(".create-site-dialog");
    await dialog.get("[data-site-work='Glas']").setValue(true);
    await dialog.get("input[value='nginx-docker']").setValue(true);
    await dialog.get("input[placeholder='Research collection']").setValue("Hosted Glas");
    await dialog.get("form").trigger("submit");
    await flushPromises();

    expect(siteApi.exportSite).toHaveBeenCalledWith({
      store: "derrida-primary",
      works: ["Glas"],
      title: "Hosted Glas",
      description: "",
      locale: "en-US",
      languages: ["en-US", "fr-CA"],
      provider_profile_ids: ["openai-main"],
      export_format: "nginx-docker",
    });
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
    // Same header grammar as the admin variant, without corpus-management controls.
    expect(wrapper.find(".ui-page-header").exists()).toBe(true);
    expect(wrapper.find(".ui-page-header-actions").exists()).toBe(false);
    expect(wrapper.find("[data-works-context='loaded']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Sync workspace to database");
    expect(wrapper.find("[data-work-review]").exists()).toBe(false);
    expect(wrapper.get(".works-card").text()).toContain("Glas");
    await wrapper
      .get(".works-inspector-pane")
      .findAll("button")
      .find((button) => button.text().includes("Browse records"))!
      .trigger("click");
    expect(runtime.browseResearcherWork).toHaveBeenCalledWith("Glas");
    wrapper.unmount();
  });

  it("opens the canonical semantic map when no persisted build is available", async () => {
    const wrapper = await mountWorks();
    await chooseMenuItem(wrapper, "Actions for Glas", "Semantic map");
    await flushPromises();

    expect(wrapper.find(".works-semantic-map-dialog").attributes("open")).toBeDefined();
    expect(wrapper.find(".semantic-map-frame").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("A semantic map is not available");
    wrapper.unmount();
  });
});
