/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const snapshot = {
  available: true,
  shared: false,
  files: [{id: "f1", name: "tab.jsonl", count: 2, dirty: 0, active: true}],
  file: {id: "f1", name: "tab.jsonl", count: 2, dirty: 0},
  query: "",
  rows: [{
    index: 0, key: "f1::0", record_id: "r-1", work: "Glas", selected: false, evidence_selected: false,
    db_status: {kind: "synced", label: "Synced", title: "ok"},
    cells: [
      {key: "__db_status", kind: "status", text: "Synced", status_kind: "synced", title: "ok"},
      {key: "work", kind: "plain", text: "Glas"},
      {key: "text", kind: "text", text: "différance"},
    ],
  }],
  columns: [{key: "__db_status", label: "DB status"}, {key: "work", label: "Work"}, {key: "text", label: "Text"}],
  available_columns: [{key: "__db_status", label: "DB status"}, {key: "work", label: "Work"}, {key: "text", label: "Text"}],
  sort: {key: "page_start", dir: 1},
  filters: {},
  page: 1, pages: 1, page_size: 100, start: 0, end: 1, matched: 1, total: 2, flagged: 0, selection_count: 0, page_selected: false,
  stores: [{name: "derrida-primary", count: 10}],
  active_store: "derrida-primary",
  has_database: true,
  db_unavailable_reason: "",
  capabilities: {can_select: true, can_review: true, can_bulk_edit: true, can_upsert: true, can_import: true, can_select_evidence: true},
};

const runtime = vi.hoisted(() => ({
  state: {view: "home"},
  getRecordsListSnapshot: vi.fn(() => snapshot),
  getShellSnapshot: vi.fn(() => ({files: snapshot.files})),
  setRecordsListQuery: vi.fn(),
  recordsListCommand: vi.fn(async () => undefined),
  getRecordsListShareHref: vi.fn(() => "http://localhost/records"),
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
}));
vi.mock("../../src/runtime/runtime.js", () => ({...runtime}));

import RecordsView from "../../src/views/RecordsView.vue";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";

describe("RecordsView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().languages = [{code: "en-US", name: "English", flag: ""}] as never;
    useShellStore().snapshot.files = snapshot.files;
    runtime.getRecordsListSnapshot.mockReturnValue(snapshot);
  });

  it("renders the loaded table and opens a record from the row", async () => {
    const wrapper = mount(RecordsView, {attachTo: document.body});
    await flushPromises();
    expect(wrapper.get("#records-page-title").text()).toContain("Records");
    expect(wrapper.text()).toContain("Glas");
    expect(wrapper.text()).toContain("Add evidence");
    await wrapper.get("tbody tr").trigger("click");
    expect(runtime.openRecordsListRecord).toHaveBeenCalledWith(0);
    wrapper.unmount();
  });

  it("shows the empty workspace when no JSONL is loaded", async () => {
    runtime.getRecordsListSnapshot.mockReturnValue({...snapshot, available: false, file: null, rows: [], total: 0, matched: 0});
    const wrapper = mount(RecordsView, {attachTo: document.body});
    await flushPromises();
    expect(wrapper.text()).toContain("Open a corpus workspace");
    wrapper.unmount();
  });
});
