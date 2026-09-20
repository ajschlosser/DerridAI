/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

function baseSnapshot() {
  return {
    available: true,
    shared: false,
    files: [{ id: "f1", name: "tab.jsonl", count: 2, dirty: 0, active: true }],
    file: { id: "f1", name: "tab.jsonl", count: 2, dirty: 0 },
    query: "",
    rows: [
      {
        index: 0,
        key: "f1::0",
        record_id: "r-1",
        work: "Glas",
        selected: false,
        evidence_selected: false,
        db_status: { kind: "synced", label: "Synced", title: "ok" },
        cells: [
          {
            key: "__db_status",
            kind: "status",
            text: "Synced",
            status_kind: "synced",
            title: "ok",
          },
          { key: "work", kind: "plain", text: "Glas" },
          { key: "text", kind: "text", text: "différance" },
        ],
      },
    ],
    columns: [
      { key: "__db_status", label: "DB status" },
      { key: "work", label: "Work" },
      { key: "text", label: "Text" },
    ],
    available_columns: [
      { key: "__db_status", label: "DB status" },
      { key: "work", label: "Work" },
      { key: "text", label: "Text" },
      { key: "speaker", label: "Speaker" },
    ],
    sort: { key: "page_start", dir: 1 },
    filters: {},
    page: 1,
    pages: 3,
    page_size: 100,
    start: 0,
    end: 1,
    matched: 1,
    total: 2,
    flagged: 0,
    selection_count: 0,
    page_selected: false,
    stores: [{ name: "derrida-primary", count: 10 }],
    active_store: "derrida-primary",
    has_database: true,
    db_unavailable_reason: "",
    capabilities: {
      can_select: true,
      can_review: true,
      can_bulk_edit: true,
      can_upsert: true,
      can_import: true,
      can_select_evidence: true,
    },
  };
}

const runtime = vi.hoisted(() => ({
  state: { view: "home" },
  getRecordsListSnapshot: vi.fn(),
  getShellSnapshot: vi.fn(() => ({ files: [] })),
  setRecordsListQuery: vi.fn(),
  recordsListCommand: vi.fn(async () => undefined),
  getRecordsListShareHref: vi.fn(() => "http://localhost/records?file=f1"),
  setRecordsListColumns: vi.fn(),
  resetRecordsListColumns: vi.fn(),
  openRecordsListRecord: vi.fn(),
  setRecordsListRowSelected: vi.fn(),
  setRecordsListPageSelected: vi.fn(),
  setRecordsListSort: vi.fn(),
  setRecordsListFilter: vi.fn(),
  setRecordsListStore: vi.fn(),
  setRecordsListPage: vi.fn(),
  setRecordsListPageSize: vi.fn(),
  toggleRecordsListEvidence: vi.fn(),
  copyRecordsListCitation: vi.fn(),
  recordsListMetadataSearch: vi.fn(),
  selectRecordsListMatches: vi.fn(),
  clearRecordsListFilters: vi.fn(),
  clearRecordsListSelection: vi.fn(),
  setTranslationDictionary: vi.fn(),
  sync: vi.fn(),
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime }));

import RecordsView from "../../src/views/RecordsView.vue";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";

HTMLDialogElement.prototype.showModal = function showModal() {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function close() {
  this.removeAttribute("open");
};

async function mountRecords() {
  const wrapper = mount(RecordsView, { attachTo: document.body });
  await flushPromises();
  return wrapper;
}

describe("RecordsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    const snap = baseSnapshot();
    runtime.getRecordsListSnapshot.mockReturnValue(snap);
    runtime.getShellSnapshot.mockReturnValue({ files: snap.files });
    useI18nStore().languages = [
      { code: "en-US", name: "English", flag: "" },
      { code: "fr-CA", name: "Français", flag: "" },
    ] as never;
    useShellStore().snapshot.files = snap.files;
  });

  it("renders the loaded table and opens a record from the row", async () => {
    const wrapper = await mountRecords();
    expect(wrapper.get("#records-page-title").text()).toContain("Records");
    expect(wrapper.text()).toContain("Glas");
    expect(wrapper.text()).toContain("Add evidence");
    expect(wrapper.get(".actions-col").text()).not.toMatch(/Evider/);
    await wrapper.get("tbody tr").trigger("click");
    expect(runtime.openRecordsListRecord).toHaveBeenCalledWith(0);
    wrapper.unmount();
  });

  it("searches, filters, sorts, and paginates through the snapshot API", async () => {
    vi.useFakeTimers();
    const wrapper = await mountRecords();
    await wrapper.get(".records-search input").setValue("différance");
    await vi.advanceTimersByTimeAsync(100);
    expect(runtime.setRecordsListQuery).toHaveBeenCalledWith("différance");
    await wrapper.get("#records-filter-work").setValue("Glas");
    expect(runtime.setRecordsListFilter).toHaveBeenCalledWith("work", "Glas");
    await wrapper.get(".records-sort").trigger("click");
    expect(runtime.setRecordsListSort).toHaveBeenCalledWith("work");
    const pageButtons = wrapper.findAll(".records-pagination button");
    await pageButtons[2].trigger("click");
    expect(runtime.setRecordsListPage).toHaveBeenCalledWith(2);
    await wrapper.get(".records-page-size select").setValue("50");
    expect(runtime.setRecordsListPageSize).toHaveBeenCalledWith(50);
    vi.useRealTimers();
    wrapper.unmount();
  });

  it("runs selection actions including upsert", async () => {
    runtime.getRecordsListSnapshot.mockReturnValue({
      ...baseSnapshot(),
      selection_count: 3,
      page_selected: true,
    });
    const wrapper = await mountRecords();
    expect(wrapper.text()).toContain("Review with LLM");
    expect(wrapper.text()).toContain("Auto-improve");
    expect(wrapper.text()).toContain("Bulk edit");
    expect(wrapper.text()).toContain("Upsert selected");
    await wrapper.get(".search-selection-actions .btn.soft").trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("reviewSelected");
    const actionButtons = wrapper.findAll(".search-selection-actions button");
    await actionButtons[1].trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("improveSelected");
    await actionButtons[2].trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("bulkSelected");
    await wrapper.get(".records-upsert-selected button").trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("upsertSelected");
    wrapper.unmount();
  });

  it("toggles evidence without treating the action as a row open", async () => {
    const wrapper = await mountRecords();
    await wrapper.get(".records-row-actions button[aria-pressed]").trigger("click");
    expect(runtime.toggleRecordsListEvidence).toHaveBeenCalledWith(0);
    expect(runtime.openRecordsListRecord).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("shows the empty workspace and shared-file restore copy", async () => {
    runtime.getRecordsListSnapshot.mockReturnValue({
      ...baseSnapshot(),
      available: false,
      file: null,
      rows: [],
      total: 0,
      matched: 0,
    });
    const wrapper = await mountRecords();
    expect(wrapper.text()).toContain("Open a corpus workspace");
    await wrapper.get(".accessible-empty-state button").trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("import");
    wrapper.unmount();

    runtime.getRecordsListSnapshot.mockReturnValue({
      ...baseSnapshot(),
      available: false,
      shared: true,
      file: null,
      rows: [],
      total: 0,
      matched: 0,
    });
    const shared = await mountRecords();
    expect(shared.text()).toContain("Open the shared corpus workspace");
    expect(shared.text()).toContain("browser-local");
    shared.unmount();
  });

  it("localizes status chips and search when the dictionary is French", async () => {
    const i18n = useI18nStore();
    i18n.locale = "fr-CA";
    i18n.dictionary = {
      "records.search_in_file": "Rechercher le texte dans ce fichier",
      "records.status.synced": "Synchronisée",
      "records.filter_placeholder": "Filtrer…",
      "records.column.work": "Œuvre",
      "records.sort_column": "Trier par {column}",
      "ui.add_evidence": "Ajouter aux preuves",
    };
    const wrapper = await mountRecords();
    expect(wrapper.get(".records-search input").attributes("placeholder")).toBe(
      "Rechercher le texte dans ce fichier",
    );
    expect(wrapper.get(".db-status").text()).toBe("Synchronisée");
    expect(wrapper.get("#records-filter-work").attributes("placeholder")).toBe("Filtrer…");
    expect(wrapper.get(".records-sort").text()).toContain("Œuvre");
    wrapper.unmount();
  });

  it("exposes sortable table headers to assistive technology", async () => {
    const wrapper = await mountRecords();
    const workHeader = wrapper.get("thead tr:first-child th:nth-child(3)");
    expect(workHeader.attributes("scope")).toBe("col");
    expect(workHeader.attributes("aria-sort")).toBe("none");
    await wrapper.get(".records-sort").trigger("click");
    expect(runtime.setRecordsListSort).toHaveBeenCalledWith("work");
    wrapper.unmount();
  });

  it("opens a record from the keyboard and operates selection and columns", async () => {
    const wrapper = await mountRecords();
    await wrapper.get("tbody tr").trigger("keydown", { key: "Enter" });
    expect(runtime.openRecordsListRecord).toHaveBeenCalledWith(0);
    await wrapper.get(".select-col input").setValue(true);
    expect(runtime.setRecordsListPageSelected).toHaveBeenCalledWith(true);
    await wrapper.get("tbody .select-col input").setValue(true);
    expect(runtime.setRecordsListRowSelected).toHaveBeenCalledWith(0, true);
    await wrapper.get(".records-hero-actions button:nth-child(2)").trigger("click");
    expect(wrapper.get("dialog").attributes("open")).toBeDefined();
    expect(wrapper.get("#records-columns-title").text()).toContain("Configure columns");
    await wrapper.get(".records-columns-add").trigger("click");
    await wrapper.get(".records-columns-foot .btn.primary").trigger("click");
    expect(runtime.setRecordsListColumns).toHaveBeenCalledWith([
      "__db_status",
      "work",
      "text",
      "speaker",
    ]);
    wrapper.unmount();
  });

  it("keeps the search icon from growing with the search field", async () => {
    const wrapper = await mountRecords();
    expect(wrapper.get(".records-search-icon").classes()).toContain("records-search-icon");
    wrapper.unmount();
  });
});
