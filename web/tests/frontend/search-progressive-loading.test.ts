/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";

const runtime = vi.hoisted(() => ({
  getSearchWorkspaceSnapshot: vi.fn(),
  runSearchWorkspace: vi.fn(),
  setSearchScope: vi.fn(),
  restoreSearchViewFromHref: vi.fn(),
  updateSearchQuery: vi.fn(),
  setSearchQueryDraft: vi.fn(),
  setSearchMmrOptions: vi.fn(),
  setSearchStore: vi.fn(),
  setSearchMethod: vi.fn(),
  setSearchLayout: vi.fn(),
  setSearchPageSize: vi.fn(),
  setSearchPage: vi.fn(),
  setSearchSort: vi.fn(),
  setSearchColumns: vi.fn(),
  setSearchAdvancedOpen: vi.fn(),
  toggleSearchFacet: vi.fn(),
  clearSearchFacetFilters: vi.fn(),
  clearSearchAllFilters: vi.fn(),
  addSearchAdvancedFilter: vi.fn(),
  removeSearchAdvancedFilter: vi.fn(),
  searchResultAction: vi.fn(),
  setSearchResultSelected: vi.fn(),
  setSearchPageSelected: vi.fn(),
  clearSearchSelection: vi.fn(),
  runSearchSelectionAction: vi.fn(),
  getSearchShareHref: vi.fn(() => "http://localhost/search"),
  notifyToast: vi.fn(),
  getShellSnapshot: vi.fn(() => ({})),
}));
// Vue's template proxy probes the namespace for reactivity flags; a strict module
// mock throws on unknown keys, so declare them.
vi.mock("../../src/domain/sharedSearchWorkspace", () => ({ searchWorkspace: runtime }));
vi.mock("../../src/domain/sharedSearchQuery", () => ({
  setSearchQueryDraft: runtime.setSearchQueryDraft,
  updateSearchQuery: runtime.updateSearchQuery,
}));
vi.mock("../../src/domain/shellSnapshot", () => ({
  getShellSnapshot: (...args: unknown[]) =>
    (runtime.getShellSnapshot as (...a: unknown[]) => unknown)(...args),
}));
vi.mock("../../src/domain/appBootstrap", () => ({
  ...runtime,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));
vi.mock("../../src/api/metadataSchemas", () => ({
  metadataSchemasApi: { list: vi.fn(async () => ({ items: [] })), get: vi.fn(async () => null) },
}));
vi.mock("../../src/composables/useNewerData", () => ({
  useNewerData: () => ({ hasNewer: { value: false }, acknowledge: vi.fn() }),
}));

import SearchView from "../../src/views/SearchView.vue";
import { useAuthStore } from "../../src/stores/auth";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function result(id: string) {
  return {
    key: `workspace:${id}`,
    kind: "workspace",
    record_id: id,
    work: "Of Grammatology",
    page_span: "12",
    text: `passage ${id}`,
    record: { record_id: id, work: "Of Grammatology" },
    selected: false,
    evidence_selected: false,
    evidence_available: false,
    distance: null,
    similarity: null,
    mmr_score: null,
    match_reasons: [],
  };
}

function snapshot(overrides: Record<string, unknown> = {}) {
  return {
    ready: true,
    is_researcher: false,
    scope: "loaded",
    query: "",
    method: "similarity",
    fetch_k: 100,
    lambda_mult: 0.7,
    advanced_open: false,
    stores: [{ name: "corpus", count: 2, filter_fields: [], schema_id: "" }],
    active_store: "corpus",
    has_database: true,
    has_loaded_records: true,
    total_loaded_records: 2,
    results: [result("R-1")],
    total: 1,
    page: 1,
    page_size: 50,
    pages: 1,
    layout: "compact",
    sort: { key: "__file", dir: 1 },
    columns: [{ key: "work", label: "Work" }],
    available_columns: [{ key: "work", label: "Work" }],
    facets: [],
    filters: [],
    filter_fields: [{ key: "work", label: "Work" }],
    filter_suggestions: {},
    selection_count: 0,
    selected_evidence_count: 0,
    loading: false,
    search_has_run: true,
    search_error: "",
    capabilities: {
      can_select: false,
      can_review: false,
      can_bulk_edit: false,
      can_manage_database: true,
      can_select_evidence: false,
    },
    ...overrides,
  };
}

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: "/search", name: "search", component: SearchView },
    { path: "/", component: { template: "<div/>" } },
  ],
});

async function mountSearch() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.user = { id: 1, username: "u", role: "admin", capabilities: [] } as never;
  await router.push("/search");
  await router.isReady();
  return mount(SearchView, {
    global: { plugins: [pinia, router, [VueQueryPlugin, { queryClient }]] },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  runtime.getSearchWorkspaceSnapshot.mockResolvedValue(snapshot());
  runtime.getSearchShareHref.mockReturnValue("http://localhost/search");
  runtime.getShellSnapshot.mockReturnValue({});
});

describe("Search workspace loading boundaries", () => {
  it("keeps keystrokes on draft state until the loaded-record debounce commits URL state", async () => {
    vi.useFakeTimers();
    try {
      const wrapper = await mountSearch();
      await flushPromises();
      const input = wrapper.get(".search-command-surface input[type='search']");

      await input.setValue("hospitality");

      expect(runtime.setSearchQueryDraft).toHaveBeenLastCalledWith("hospitality");
      expect(runtime.updateSearchQuery).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(149);
      expect(runtime.updateSearchQuery).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(1);
      expect(runtime.updateSearchQuery).toHaveBeenCalledWith("hospitality", { replace: true });
      wrapper.unmount();
    } finally {
      vi.useRealTimers();
    }
  });

  it("renders the page frame before the first read lands instead of hiding the page", async () => {
    const read = deferred<ReturnType<typeof snapshot>>();
    runtime.getSearchWorkspaceSnapshot.mockReturnValueOnce(read.promise);
    const wrapper = await mountSearch();
    await flushPromises();

    expect(wrapper.find("#search-page-title").exists()).toBe(true);
    expect(wrapper.find(".search-workspace-header").exists()).toBe(true);
    expect(wrapper.find(".search-command-surface").exists()).toBe(true);
    expect(wrapper.get("input[type='search']").attributes("disabled")).toBeDefined();
    expect(wrapper.find("[data-search-loading]").exists()).toBe(true);
    expect(wrapper.findAll(".search-scope-switch small").every((item) => item.text() === "—")).toBe(
      true,
    );

    read.resolve(snapshot());
    await flushPromises();
    expect(wrapper.find("[data-search-loading]").exists()).toBe(false);
    expect(wrapper.get("input[type='search']").attributes("disabled")).toBeUndefined();
    expect(wrapper.find(".search-results-panel").exists()).toBe(true);
    wrapper.unmount();
  });

  it("keeps the search frame visible after a failed first read", async () => {
    runtime.getSearchWorkspaceSnapshot.mockRejectedValueOnce(new Error("Search unavailable"));
    const wrapper = await mountSearch();
    await flushPromises();

    expect(wrapper.find("#search-page-title").exists()).toBe(true);
    expect(wrapper.find(".search-workspace-header").exists()).toBe(true);
    expect(wrapper.find(".search-command-surface").exists()).toBe(true);
    expect(wrapper.get("input[type='search']").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".search-page-error").attributes("role")).toBe("alert");
    expect(wrapper.get(".search-page-error").text()).toContain("Search unavailable");
    expect(wrapper.text()).not.toContain("No matching records");

    wrapper.unmount();
  });

  it("keeps the workspace mounted and reports a failed refresh in place", async () => {
    const wrapper = await mountSearch();
    await flushPromises();
    const panel = wrapper.get(".search-results-panel").element;

    const read = deferred<ReturnType<typeof snapshot>>();
    runtime.getSearchWorkspaceSnapshot.mockReturnValueOnce(read.promise);
    await router.push("/search?page=2");
    await flushPromises();
    expect(wrapper.get(".search-results-panel").element).toBe(panel);

    read.reject(new Error("offline"));
    await flushPromises();
    expect(wrapper.get(".search-results-panel").element).toBe(panel);
    const status = wrapper.get(".search-workspace-status");
    expect(status.attributes("role")).toBe("alert");
    expect(status.text()).toContain("offline");
    expect(status.find("button").exists()).toBe(true);
    expect(wrapper.find(".search-page-error").exists()).toBe(false);
    wrapper.unmount();
  });

  it("clears retained content when access is withdrawn", async () => {
    const wrapper = await mountSearch();
    await flushPromises();
    expect(wrapper.find(".search-results-panel").exists()).toBe(true);

    runtime.getSearchWorkspaceSnapshot.mockRejectedValueOnce(
      Object.assign(new Error("Forbidden"), { status: 403 }),
    );
    await router.push("/search?page=3");
    await flushPromises();

    expect(wrapper.find(".search-results-table").exists()).toBe(false);
    expect(wrapper.find("[data-search-loading]").exists()).toBe(true);
    expect(wrapper.get(".search-page-error").text()).toContain("Forbidden");
    wrapper.unmount();
  });

  it("drops a superseded workspace read instead of applying its results", async () => {
    const stale = deferred<ReturnType<typeof snapshot>>();
    runtime.getSearchWorkspaceSnapshot.mockReturnValueOnce(stale.promise);
    const wrapper = await mountSearch();
    await flushPromises();

    runtime.getSearchWorkspaceSnapshot.mockImplementation(() =>
      Promise.resolve(snapshot({ layout: "cards", results: [result("NEW")], total: 1 })),
    );
    await router.push("/search?page=4");
    await flushPromises();
    expect(wrapper.text()).toContain("NEW");

    stale.resolve(snapshot({ layout: "cards", results: [result("OLD")], total: 1 }));
    await flushPromises();

    expect(wrapper.text()).toContain("NEW");
    expect(wrapper.text()).not.toContain("OLD");
    wrapper.unmount();
  });
});

describe("Search result identity", () => {
  const databaseSnapshot = (overrides: Record<string, unknown> = {}) =>
    snapshot({ scope: "database", query: "ancient", search_has_run: true, ...overrides });

  it("does not present a failed corpus-database search as zero matches", async () => {
    runtime.getSearchWorkspaceSnapshot.mockResolvedValue(
      databaseSnapshot({ results: [], total: 0, search_error: "Chroma is unreachable" }),
    );
    const wrapper = await mountSearch();
    await flushPromises();

    expect(wrapper.get("#search-results-title").text()).toContain("Result count unavailable");
    const status = wrapper.get(".search-results-status");
    expect(status.attributes("role")).toBe("alert");
    expect(status.text()).toContain("Chroma is unreachable");
    expect(wrapper.text()).not.toContain("No matching records");
    wrapper.unmount();
  });

  it("marks the visible results as belonging to the last submitted query", async () => {
    runtime.getSearchWorkspaceSnapshot.mockResolvedValue(databaseSnapshot());
    const wrapper = await mountSearch();
    await flushPromises();
    expect(wrapper.find(".search-results-identity").exists()).toBe(false);

    await wrapper.get("input[type='search']").setValue("différance");
    await flushPromises();

    expect(wrapper.get(".search-results-identity").text()).toContain("ancient");
    wrapper.unmount();
  });

  it("replaces the previous rows with a searching state while a new query is in flight", async () => {
    runtime.getSearchWorkspaceSnapshot.mockResolvedValue(databaseSnapshot());
    const wrapper = await mountSearch();
    await flushPromises();
    expect(wrapper.find(".search-results-table").exists()).toBe(true);

    const search = deferred<ReturnType<typeof snapshot>>();
    runtime.runSearchWorkspace.mockReturnValueOnce(search.promise);
    await wrapper.get("input[type='search']").setValue("différance");
    await wrapper.get("form.search-command-row").trigger("submit");
    await flushPromises();

    expect(wrapper.find(".search-results-table").exists()).toBe(false);
    expect(wrapper.get(".search-results-loading").text()).toContain("Searching");

    search.resolve(databaseSnapshot({ query: "différance", results: [result("R-2")], total: 1 }));
    await flushPromises();
    expect(wrapper.find(".search-results-table").exists()).toBe(true);
    expect(wrapper.find(".search-results-identity").exists()).toBe(false);
    wrapper.unmount();
  });
});
