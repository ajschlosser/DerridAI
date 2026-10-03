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

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { metadataMemoryApi, type MetadataMemoryPayload } from "../../src/api/metadataMemory";
import { queryClient } from "../../src/realtime/dataQuery";
import { dataKey } from "../../src/realtime/resourceKeys";
import { useI18nStore } from "../../src/stores/i18n";
import MetadataMemoryView from "../../src/views/MetadataMemoryView.vue";

const dictionary = {
  "section.ai_automation": "AI & Automation",
  "metadata_memory.title": "Metadata memory",
  "metadata_memory.help": "Inspect reviewed precedents.",
  "metadata_memory.authority_title": "Authority:",
  "metadata_memory.authority_help": "Reviewed corpus metadata remains authoritative.",
  "metadata_memory.summary": "Metadata memory summary",
  "metadata_memory.entries": "Precedents",
  "metadata_memory.evidence_bound": "Evidence-bound",
  "metadata_memory.corrections": "Corrections",
  "metadata_memory.fields": "Fields",
  "metadata_memory.unavailable": "Metadata memory is unavailable",
  "metadata_memory.read_failed": "Could not load metadata memory: {message}",
  "metadata_memory.refresh_failed": "Metadata memory may be out of date. Refresh failed: {message}",
  "metadata_memory.search": "Search",
  "metadata_memory.search_placeholder": "Search memory",
  "metadata_memory.filters_label": "Filter metadata precedents",
  "metadata_memory.filter_chip": "{label}: {value}",
  "metadata_memory.active_filters": "Active filters",
  "metadata_memory.remove_filter": "Remove filter: {label}",
  "metadata_memory.field": "Field",
  "metadata_memory.all_fields": "All fields",
  "metadata_memory.kind": "Precedent type",
  "metadata_memory.all_kinds": "All types",
  "metadata_memory.build": "Corpus build",
  "metadata_memory.all_builds": "All builds",
  "metadata_memory.language": "Language",
  "metadata_memory.all_languages": "All languages",
  "metadata_memory.clear_filters": "Clear filters",
  "metadata_memory.precedents": "Learned precedents",
  "metadata_memory.showing": "Showing {start}–{end} of {total}",
  "metadata_memory.loading": "Loading metadata memory…",
  "metadata_memory.updating": "Updating…",
  "metadata_memory.pagination": "Metadata precedent pagination",
  "metadata_memory.table_scroll": "Metadata precedents table",
  "metadata_memory.field_value": "Field / reviewed value",
  "metadata_memory.authority": "Review authority",
  "metadata_memory.source": "Source record",
  "metadata_memory.scope": "Scope",
  "metadata_memory.evidence": "Evidence and indexed context",
  "metadata_memory.rejected_value": "Rejected model value",
  "metadata_memory.bound": "Evidence-bound",
  "metadata_memory.page": "Page",
  "metadata_memory.record_revision": "{record} · r{revision}",
  "metadata_memory.source_stale": "Source revision could not be confirmed.",
  "metadata_memory.evidence_unresolved": "Evidence could not be resolved.",
  "metadata_memory.context_only": "Context-only reviewer memory.",
  "metadata_memory.blocks": "Evidence blocks",
  "metadata_memory.indexed_context": "Indexed context",
  "metadata_memory.empty": "No metadata precedents match these filters.",
  "metadata_memory.empty_none": "No precedents yet.",
  "metadata_memory.show_details": "Show details",
  "metadata_memory.hide_details": "Hide details",
  "metadata_memory.kind_positive": "Reviewed precedent",
  "metadata_memory.kind_correction": "Correction / negative precedent",
  "common.previous": "Previous",
  "common.next": "Next",
  "ui.retry": "Retry",
};

const RouterLink = { props: ["to"], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' };
const mounted: VueWrapper[] = [];

function currentPayload(overrides: Partial<MetadataMemoryPayload> = {}): MetadataMemoryPayload {
  return {
    items: [
      {
        id: "mex-1",
        memory_type: "evidence_bound",
        kind: "correction",
        field: "position_holder",
        value: "Levinas",
        rejected_value: "Derrida",
        authority: "human_override",
        review_method: "human_review_of_llm_proposal",
        record_id: "r1",
        record_revision: 4,
        build_id: "build-1",
        source_document_id: "asset-1",
        schema_id: "derrida",
        schema_version: "v1",
        language: "en",
        region_type: "main_text",
        page_start: 12,
        page_end: 12,
        evidence_bound: true,
        evidence_hash: "hash",
        evidence_block_ids: ["b2"],
        evidence_text: "For Levinas, responsibility precedes freedom.",
        context_text: "Context around the evidence.",
        source_current: true,
      },
    ],
    total: 1,
    offset: 0,
    limit: 50,
    summary: { entries: 1, evidence_bound: 1, corrections: 1, fields: 1, backends: 1 },
    facets: {
      fields: ["position_holder"],
      kinds: ["correction"],
      languages: ["en"],
      builds: ["build-1"],
    },
    derived: true,
    authoritative_source: "reviewed corpus metadata and evidence",
    available: true,
    error: "",
    ...overrides,
  };
}

function emptyPayload(): MetadataMemoryPayload {
  return currentPayload({
    items: [],
    total: 0,
    summary: { entries: 0, evidence_bound: 0, corrections: 0, fields: 0, backends: 1 },
    facets: { fields: [], kinds: [], languages: [], builds: [] },
  });
}

function unavailablePayload(message = "projection unavailable"): MetadataMemoryPayload {
  return currentPayload({
    items: [],
    total: 0,
    summary: { entries: 0, evidence_bound: 0, corrections: 0, fields: 0, backends: 1 },
    facets: { fields: [], kinds: [], languages: [], builds: [] },
    available: false,
    error: message,
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}

async function mountView(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/metadata-memory",
        name: "metadatamemory",
        component: { template: "<div />" },
      },
    ],
  });
  await router.push({ name: "metadatamemory", query });
  await router.isReady();
  const wrapper = mount(MetadataMemoryView, {
    attachTo: document.body,
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]], stubs: { RouterLink } },
  });
  mounted.push(wrapper);
  return { wrapper, router };
}

describe("Metadata memory page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryClient.clear();
    vi.restoreAllMocks();
    useI18nStore().dictionary = dictionary;
    vi.spyOn(metadataMemoryApi, "list").mockResolvedValue(currentPayload());
  });

  afterEach(() => {
    vi.useRealTimers();
    mounted.splice(0).forEach((wrapper) => wrapper.unmount());
    queryClient.clear();
  });

  it("refetches the current page on a metadata_exemplars invalidation and has no Refresh button", async () => {
    const { wrapper } = await mountView({ field: "position_holder" });
    await flushPromises();
    expect(wrapper.findAll("button").some((button) => button.text() === "Refresh")).toBe(false);
    const before = vi.mocked(metadataMemoryApi.list).mock.calls.length;
    await queryClient.invalidateQueries({ queryKey: dataKey("metadata_exemplars") });
    await flushPromises();
    expect(vi.mocked(metadataMemoryApi.list).mock.calls.length).toBe(before + 1);
    expect(vi.mocked(metadataMemoryApi.list).mock.calls.at(-1)?.[0]).toMatchObject({
      field: "position_holder",
    });
  });

  it("presents learned metadata as auditable scholarly memory", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.get("#metadata-memory-title").text()).toBe("Metadata memory");
    expect(wrapper.text()).toContain("position_holder");
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("Derrida");
    expect(wrapper.text()).toContain("Correction / negative precedent");
    expect(wrapper.text()).toContain("For Levinas, responsibility precedes freedom.");
    expect(wrapper.text()).toContain("r1 · r4");
    expect(wrapper.text()).not.toContain("derridai_metadata_exemplars");
  });

  it("applies select filters immediately, shows removable chips, and debounces search", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    const { wrapper } = await mountView();
    await flushPromises();
    list.mockClear();

    await wrapper.findAll("select")[0].setValue("position_holder");
    await flushPromises();
    expect(list).toHaveBeenCalledTimes(1);
    expect(list.mock.calls[0][0]).toMatchObject({ field: "position_holder", offset: 0 });
    expect(wrapper.find(".filter-chips").text()).toContain("position_holder");

    vi.useFakeTimers();
    await wrapper.get("input[type=search]").setValue("levinas");
    expect(list).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(350);
    await flushPromises();
    expect(list).toHaveBeenCalledTimes(2);
    expect(list.mock.calls[1][0]).toMatchObject({ q: "levinas" });
    vi.useRealTimers();

    await wrapper.findAll(".chip")[1].trigger("click");
    await flushPromises();
    expect(list.mock.calls.at(-1)?.[0]).toMatchObject({ q: "levinas", field: "" });
  });

  it("restores filters from the URL and keeps filter state shareable", async () => {
    vi.mocked(metadataMemoryApi.list).mockResolvedValue(currentPayload({ total: 101, offset: 50 }));
    const { wrapper, router } = await mountView({
      q: "levinas",
      field: "position_holder",
      kind: "correction",
      build: "build-1",
      language: "en",
      offset: "50",
    });
    await flushPromises();

    const searchInput = wrapper.get("input[type=search]").element as HTMLInputElement;
    const fieldSelect = wrapper.findAll("select")[0].element as HTMLSelectElement;
    expect(searchInput.value).toBe("levinas");
    expect(fieldSelect.value).toBe("position_holder");
    expect(metadataMemoryApi.list).toHaveBeenCalledWith(
      expect.objectContaining({
        q: "levinas",
        field: "position_holder",
        kind: "correction",
        build_id: "build-1",
        language: "en",
        offset: 50,
      }),
    );

    await wrapper.findAll("select")[0].setValue("");
    await flushPromises();
    expect(router.currentRoute.value.query.field).toBeUndefined();
    expect(router.currentRoute.value.query.q).toBe("levinas");
  });

  it("links related System Data surfaces and exposes details with explicit control semantics", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    const targets = wrapper
      .findAll(".memory-relations a")
      .map((anchor) => anchor.attributes("data-to"));
    expect(targets.join()).toContain("semantic_memory_outbox");
    expect(targets.join()).toContain("system-data-metadata");

    const toggle = wrapper.get(".details-toggle");
    const detailsId = toggle.attributes("aria-controls");
    expect(detailsId).toBe("metadata-memory-details-mex-1");
    expect(wrapper.find(`#${detailsId}`).exists()).toBe(false);
    await toggle.trigger("click");
    expect(wrapper.text()).toContain("Context around the evidence.");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(`#${detailsId}`).text()).toContain("Context around the evidence.");
    expect(wrapper.get("table caption").text()).toBe("Metadata precedents table");
  });

  it("renders the page frame and loading state without claiming an empty memory on a delayed first read", async () => {
    const read = deferred<MetadataMemoryPayload>();
    vi.mocked(metadataMemoryApi.list).mockReturnValue(read.promise);
    const { wrapper } = await mountView();

    expect(wrapper.get("#metadata-memory-title").text()).toBe("Metadata memory");
    expect(wrapper.get('form[role="search"]').attributes("aria-label")).toBe(
      "Filter metadata precedents",
    );
    expect(wrapper.text()).toContain("Loading metadata memory");
    expect(wrapper.text()).not.toContain("No precedents yet");

    read.resolve(currentPayload());
    await flushPromises();
    expect(wrapper.text()).toContain("Levinas");
  });

  it("revalidates a cached empty result on remount instead of displaying it as latest data", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    list.mockResolvedValueOnce(emptyPayload());

    const first = await mountView();
    await flushPromises();
    expect(first.wrapper.text()).toContain("No precedents yet");
    first.wrapper.unmount();

    list.mockResolvedValue(currentPayload());
    const second = await mountView();
    expect(second.wrapper.text()).toContain("Loading metadata memory");
    expect(second.wrapper.text()).not.toContain("No precedents yet");
    await flushPromises();

    expect(list).toHaveBeenCalledTimes(2);
    expect(second.wrapper.text()).toContain("Levinas");
    expect(second.wrapper.text()).not.toContain("No precedents yet");
  });

  it("reports an unavailable first read and retries without presenting a false empty result", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    list.mockResolvedValueOnce(unavailablePayload("projection read failed"));
    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.get(".memory-read-error").text()).toContain("projection read failed");
    expect(wrapper.text()).not.toContain("No precedents yet");
    expect(wrapper.find(".memory-table").exists()).toBe(false);

    list.mockResolvedValue(currentPayload());
    await wrapper.get(".memory-read-error button").trigger("click");
    await flushPromises();

    expect(wrapper.find(".memory-read-error").exists()).toBe(false);
    expect(wrapper.text()).toContain("Levinas");
  });

  it("retains the last successful table when a refresh cannot read the projection", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    const { wrapper } = await mountView();
    await flushPromises();
    const table = wrapper.get(".memory-table").element;

    list.mockResolvedValue(unavailablePayload("projection temporarily unavailable"));
    await queryClient.invalidateQueries({ queryKey: dataKey("metadata_exemplars") });
    await flushPromises();

    expect(wrapper.get(".memory-table").element).toBe(table);
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.get(".memory-read-error").text()).toContain("may be out of date");
    expect(wrapper.get(".memory-read-error").text()).toContain(
      "projection temporarily unavailable",
    );

    list.mockResolvedValue(currentPayload());
    await wrapper.get(".memory-read-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".memory-read-error").exists()).toBe(false);
    expect(wrapper.get(".memory-table").element).toBe(table);
  });

  it("repairs an out-of-range bookmarked page instead of showing a successful empty slice", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    list.mockImplementation(async (filters) =>
      filters?.offset === 50
        ? currentPayload({ items: [], total: 1, offset: 50 })
        : currentPayload({ offset: 0 }),
    );
    const { wrapper, router } = await mountView({ offset: "50" });
    await flushPromises();

    expect(list.mock.calls.some(([filters]) => filters?.offset === 50)).toBe(true);
    expect(list.mock.calls.some(([filters]) => filters?.offset === 0)).toBe(true);
    expect(router.currentRoute.value.query.offset).toBeUndefined();
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).not.toContain("No precedents yet");
  });
});
