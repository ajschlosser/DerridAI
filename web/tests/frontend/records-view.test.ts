/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

function baseSnapshot() {
  return {
    available: true,
    shared: false,
    files: [
      {
        id: "f1",
        name: "tab.jsonl",
        count: 2,
        dirty: 0,
        active: true,
        origin: "imported",
        origin_detail: "",
      },
    ],
    file: {
      id: "f1",
      name: "tab.jsonl",
      count: 2,
      dirty: 0,
      active: true,
      origin: "imported",
      origin_detail: "",
    },
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
  triggerMerge: vi.fn(),
  subsetSources: vi.fn(() => [
    { id: "active", name: "tab.jsonl", count: 2 },
    { id: "all", name: "", count: 2 },
    { id: "f1", name: "tab.jsonl", count: 2 },
  ]),
  subsetFields: vi.fn(() => [
    { key: "document_author", label: "Document author" },
    { key: "work", label: "Work" },
  ]),
  subsetSourceRecords: vi.fn(() => [
    { record_id: "r-1", document_author: "Jacques Derrida", work: "Glas" },
    { record_id: "r-2", document_author: "Paul de Man", work: "Allegories" },
  ]),
  defaultSubsetName: vi.fn(() => "tab-subset.jsonl"),
  createSubsetFile: vi.fn(async () => ({ name: "tab-subset.jsonl", count: 1 })),
  triggerExport: vi.fn(),
  getRecordsListShareHref: vi.fn(() => "http://localhost/records?file=f1"),
  activateFile: vi.fn(),
  closeWorkspaceFile: vi.fn(async () => undefined),
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
    useShellStore().snapshot.files = snap.files as never;
  });

  it("renders the loaded table and opens a record from the row", async () => {
    const wrapper = await mountRecords();
    expect(wrapper.get("#records-page-title").text()).toContain("Records");
    expect(wrapper.text()).toContain("Glas");
    expect(wrapper.text()).toContain("Add to evidence");
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
      files: [],
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
      files: [],
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
    expect(wrapper.get(".db-status").text()).toContain("Synchronisée");
    expect(wrapper.get("#records-filter-work").attributes("placeholder")).toBe("Filtrer…");
    expect(wrapper.get(".records-sort").text()).toContain("Œuvre");
    wrapper.unmount();
  });

  it("exposes sortable table headers to assistive technology", async () => {
    const wrapper = await mountRecords();
    const workHeader = wrapper.get("thead tr:first-child th:nth-child(3)");
    expect(workHeader.attributes("scope")).toBe("col");
    expect(workHeader.attributes("aria-sort")).toBe("none");
    expect(wrapper.get(".records-table-scroll").attributes("role")).toBe("region");
    expect(wrapper.get(".db-status").attributes("data-tone")).toBe("success");
    await wrapper.get(".records-sort").trigger("click");
    expect(runtime.setRecordsListSort).toHaveBeenCalledWith("work");
    wrapper.unmount();
  });

  it("makes an unavailable corpus database explicit", async () => {
    runtime.getRecordsListSnapshot.mockReturnValue({
      ...baseSnapshot(),
      stores: [],
      active_store: "",
      has_database: false,
      db_unavailable_reason: "The local database is still starting.",
    });
    const wrapper = await mountRecords();
    expect(wrapper.get(".records-database-state").text()).toContain("No corpus collection");
    expect(wrapper.get(".records-database-state").text()).toContain(
      "The local database is still starting.",
    );
    expect(wrapper.get(".records-store select").attributes("disabled")).toBeDefined();
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
    await flushPromises();
    const dialog = document.body.querySelector<HTMLElement>("[role=dialog]")!;
    expect(dialog.textContent).toContain("Configure columns");
    dialog.querySelector<HTMLButtonElement>(".ui-columns-add")!.click();
    await flushPromises();
    dialog.querySelector<HTMLButtonElement>(".ui-dialog-footer .btn.primary")!.click();
    await flushPromises();
    expect(runtime.setRecordsListColumns).toHaveBeenCalledWith([
      "__db_status",
      "work",
      "text",
      "speaker",
    ]);
    // The shown columns' widths are saved with them and always total 100%.
    const widths = JSON.parse(localStorage.getItem("derridai.records.columnWidths.v1") || "{}");
    expect(Object.keys(widths)).toEqual(["__db_status", "work", "text", "speaker"]);
    expect(Object.values(widths as Record<string, number>).reduce((a, b) => a + b, 0)).toBeCloseTo(
      100,
      5,
    );
    wrapper.unmount();
  });

  it("compact rows show the text on one line with an Expand control where it is cut off", async () => {
    const scrollWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollWidth");
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", {
      configurable: true,
      get() {
        return (this as HTMLElement).classList.contains("records-text") ? 500 : 0;
      },
    });
    try {
      const wrapper = await mountRecords();
      expect(wrapper.find(".records-text-toggle").exists()).toBe(false);
      const compact = wrapper.findAll(".records-density button")[1];
      await compact.trigger("click");
      await flushPromises();
      expect(wrapper.get(".records-table").classes()).toContain("compact");
      expect(wrapper.get(".records-text").classes()).toContain("clamped");
      const toggle = wrapper.get(".records-text-toggle");
      expect(toggle.text()).toBe("Expand");
      expect(toggle.attributes("aria-expanded")).toBe("false");
      expect(toggle.attributes("aria-controls")).toBe(
        wrapper.get(".records-text").attributes("id"),
      );
      await toggle.trigger("click");
      expect(wrapper.get(".records-text").classes()).not.toContain("clamped");
      expect(wrapper.get(".records-text-toggle").text()).toBe("Collapse");
      // Expanding the text is not a row open.
      expect(runtime.openRecordsListRecord).not.toHaveBeenCalled();
      wrapper.unmount();
    } finally {
      if (scrollWidth) Object.defineProperty(HTMLElement.prototype, "scrollWidth", scrollWidth);
      else delete (HTMLElement.prototype as { scrollWidth?: number }).scrollWidth;
      localStorage.removeItem("derridai.records.density.v1");
    }
  });

  it("selects a local JSONL file from the Records rail", async () => {
    const wrapper = await mountRecords();
    expect(wrapper.text()).toContain("Local JSONL");
    expect(wrapper.text()).toContain("Imported");
    await wrapper.get(".records-file-select").trigger("click");
    expect(runtime.activateFile).toHaveBeenCalledWith("f1");
    wrapper.unmount();
  });

  it("opens, merges, subsets, exports, and closes files from the Records rail", async () => {
    const extra = {
      id: "f2",
      name: "subset.jsonl",
      count: 1,
      dirty: 0,
      active: false,
      origin: "subset",
      origin_detail: "tab.jsonl",
    };
    runtime.getRecordsListSnapshot.mockReturnValue({
      ...baseSnapshot(),
      files: [...baseSnapshot().files, extra],
    });
    const wrapper = await mountRecords();
    const byLabel = (label: string) =>
      wrapper
        .findAll(".records-file-actions button")
        .find((button) => button.text().includes(label));
    await byLabel("Open JSONL")?.trigger("click");
    expect(runtime.recordsListCommand).toHaveBeenCalledWith("import");
    await byLabel("Merge files")?.trigger("click");
    expect(runtime.triggerMerge).toHaveBeenCalled();
    await byLabel("Create subset")?.trigger("click");
    await flushPromises();
    const subset = document.body.querySelector<HTMLElement>("[role=dialog]")!;
    expect(subset.textContent).toContain("Create JSONL subset");
    // The default condition (document author equals Jacques Derrida) matches one of two records.
    expect(subset.querySelector("[role=status]")?.textContent).toContain(
      "1 of 2 source records match",
    );
    [...subset.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent?.trim() === "Create subset file")!
      .click();
    await flushPromises();
    expect(runtime.createSubsetFile).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "tab-subset.jsonl",
        source: "active",
        caseSensitive: false,
        download: false,
        expression: [
          {
            type: "rule",
            join: "AND",
            rule: { field: "document_author", operator: "equals", value: "Jacques Derrida" },
          },
        ],
      }),
    );
    expect(document.body.querySelector("[role=dialog]")).toBeNull();
    await byLabel("Export")?.trigger("click");
    expect(runtime.triggerExport).toHaveBeenCalled();
    await wrapper.get(".records-file-close").trigger("click");
    expect(runtime.closeWorkspaceFile).toHaveBeenCalledWith("f1");
    wrapper.unmount();
  });

  it("keeps the search icon from growing with the search field", async () => {
    const wrapper = await mountRecords();
    expect(wrapper.get(".records-search-icon").classes()).toContain("records-search-icon");
    wrapper.unmount();
  });
});
